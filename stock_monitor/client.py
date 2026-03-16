#!/usr/bin/env python3
"""
A股数据获取模块 - 东方财富API + 新浪财经API + IP池 + UA轮换 + Referer伪装
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import time
import sys
import re
import random
import threading
import os
sys.path.append(str(__file__).rsplit('/', 1)[0])
from database import save_minute_data


# 指数代码映射
INDEX_CODES = {
    '000001': 'sh000001',  # 上证指数
    '399001': 'sz399001',  # 深证成指
    '399006': 'sz399006',  # 创业板指
    '000300': 'sh000300',  # 沪深300
}


class ProxyPool:
    """代理IP池管理器"""
    
    def __init__(self):
        self.fixed_proxies = []
        
        # 从环境变量读取代理列表
        proxy_str = os.environ.get('HTTP_PROXIES', '')
        if proxy_str:
            self.fixed_proxies = [p.strip() for p in proxy_str.split(',') if p.strip()]
            print(f"加载了 {len(self.fixed_proxies)} 个固定代理")
    
    def get_proxy(self) -> Optional[dict]:
        """获取一个可用代理"""
        if self.fixed_proxies:
            proxy = random.choice(self.fixed_proxies)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return None


# 全局代理池
proxy_pool = ProxyPool()


class SinaClient:
    """新浪财经数据客户端"""
    
    BASE_URL = "https://hq.sinajs.cn/list="
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Referer': 'https://finance.sina.com.cn/',
        })
    
    def _get_code(self, code: str) -> str:
        """获取新浪格式的股票代码"""
        code = code.strip()
        
        # 指数
        if code == '000001':
            return 'sh000001'
        elif code == '399001':
            return 'sz399001'
        elif code == '399006':
            return 'sz399006'
        
        if code.startswith('6'):
            return f'sh{code}'
        else:
            return f'sz{code}'
    
    def get_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        sina_code = self._get_code(code)
        url = f"{self.BASE_URL}{sina_code}"
        
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            
            text = resp.text
            # var hq_str_sh600519="贵州茅台,1420.000,..."
            match = re.search(r'="(.+)"', text)
            if not match:
                return None
            
            parts = match.group(1).split(',')
            if len(parts) < 32:
                return None
            
            name = parts[0]
            open_price = float(parts[1]) if parts[1] else 0
            yesterday_close = float(parts[2]) if parts[2] else 0
            current_price = float(parts[3]) if parts[3] else 0
            high = float(parts[4]) if parts[4] else 0
            low = float(parts[5]) if parts[5] else 0
            volume = int(parts[8]) if parts[8] else 0
            amount = float(parts[9]) if parts[9] else 0
            
            # 判断是否开盘
            market_status = 'open' if current_price > 0 else 'closed'
            
            # 涨跌
            change = 0
            change_pct = 0
            if yesterday_close and current_price > 0:
                change = round(current_price - yesterday_close, 2)
                change_pct = round(change / yesterday_close * 100, 2)
            
            # 时间
            update_time = parts[30] if len(parts) > 30 else ''
            if update_time and len(update_time) >= 8:
                update_time = update_time[:8]
            
            return {
                'code': code,
                'name': name,
                'price': current_price,
                'change': change,
                'change_pct': change_pct,
                'yesterday_close': yesterday_close,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'amount': amount,
                'time': update_time,
                'market_status': market_status
            }
        except Exception as e:
            print(f"新浪API失败 {code}: {e}")
            return None


class EastMoneyClient:
    """东方财富行情数据客户端 - 防封版"""
    
    BASE_URL = "https://push2his.eastmoney.com"
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    ]
    
    REFERERS = [
        'https://quote.eastmoney.com/',
        'https://quote.eastmoney.com/sh600519.html',
        'https://www.eastmoney.com/',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self._update_headers()
        self.fail_count = 0
        self.max_fails = 3
    
    def _update_headers(self):
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': '*/*',
            'Referer': random.choice(self.REFERERS),
        })
    
    def _get_secid(self, code: str) -> str:
        if code.startswith('6'):
            return f'0.{code}'
        elif code.startswith(('0', '2', '3')):
            return f'1.{code}'
        return f'0.{code}'
    
    def get_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        secid = self._get_secid(code)
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f48,f50,f57,f58,f59,f60'
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/get"
        
        time.sleep(random.uniform(0.3, 0.8))
        
        proxy = proxy_pool.get_proxy()
        
        for attempt in range(3):
            self._update_headers()
            try:
                if proxy:
                    resp = self.session.get(url, params=params, timeout=10, proxies=proxy)
                else:
                    resp = self.session.get(url, params=params, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('data'):
                        d = data['data']
                        price = d.get('f43', 0) / 100 if d.get('f43') else 0
                        if price == 0:
                            return None
                        
                        yesterday_close = d.get('f46', 0) / 100 if d.get('f46') else None
                        change = 0
                        change_pct = 0
                        if yesterday_close:
                            change = round(price - yesterday_close, 2)
                            change_pct = round(change / yesterday_close * 100, 2)
                        
                        return {
                            'code': d.get('f57'),
                            'name': d.get('f58'),
                            'price': price,
                            'change': change,
                            'change_pct': change_pct,
                            'yesterday_close': yesterday_close,
                            'volume': d.get('f47', 0),
                            'amount': d.get('f48', 0),
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'market_status': 'open'
                        }
            except Exception as e:
                print(f"东方财富API异常: {e}")
            
            time.sleep(1)
        
        return None
    
    def get_kline(self, code: str, period: int = 1,
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取K线数据"""
        secid = self._get_secid(code)
        
        if not start_date:
            start_date = datetime.now().strftime('%Y%m%d')
        if not end_date:
            end_date = start_date
        
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
            'klt': str(period),
            'fqt': '0',
            'beg': start_date,
            'end': end_date
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/kline/get"
        
        time.sleep(random.uniform(0.3, 0.8))
        
        try:
            proxy = proxy_pool.get_proxy()
            if proxy:
                resp = self.session.get(url, params=params, timeout=10, proxies=proxy)
            else:
                resp = self.session.get(url, params=params, timeout=10)
            
            data = resp.json()
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                records = []
                for kline in klines:
                    parts = kline.split(',')
                    records.append({
                        '时间': parts[0],
                        '开盘': float(parts[1]),
                        '收盘': float(parts[2]),
                        '最高': float(parts[3]),
                        '最低': float(parts[4]),
                        '成交量': int(parts[5]),
                        '成交额': float(parts[6]),
                    })
                return pd.DataFrame(records)
        except Exception as e:
            print(f"获取K线失败: {e}")
        
        return pd.DataFrame()


class StockClient:
    """统一客户端：新浪(主) + 东方财富(备)"""
    
    def __init__(self):
        self.sina = SinaClient()
        self.eastmoney = EastMoneyClient()
    
    def get_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情，优先用新浪"""
        # 优先用新浪
        result = self.sina.get_realtime(code)
        if result:
            return result
        
        # 新浪失败，尝试东方财富
        result = self.eastmoney.get_realtime(code)
        if result:
            return result
        
        return None
    
    def get_kline(self, code: str, period: int = 1,
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取K线数据"""
        return self.eastmoney.get_kline(code, period, start_date, end_date)


# 兼容旧接口
def get_all_realtime(codes: List[str]) -> List[Dict]:
    """批量获取实时行情"""
    client = StockClient()
    results = []
    
    for code in codes:
        data = client.get_realtime(code)
        if data:
            results.append(data)
        time.sleep(0.1)
    
    return results


if __name__ == "__main__":
    client = StockClient()
    
    print("=== 测试数据源 ===")
    
    # 测试上证指数
    rt = client.get_realtime('000001')
    print(f"000001 上证指数: {rt}")
    
    # 测试贵州茅台
    rt = client.get_realtime('600519')
    print(f"600519 贵州茅台: {rt}")
