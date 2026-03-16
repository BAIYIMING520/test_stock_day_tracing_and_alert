#!/usr/bin/env python3
"""
A股数据获取模块 - 东方财富API + IP池 + UA轮换 + Referer伪装
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
sys.path.append(str(__file__).rsplit('/', 1)[0])
from database import save_minute_data


# 指数代码映射
INDEX_CODES = {
    '000001': '0.000001',  # 上证指数
    '399001': '1.399001',  # 深证成指
    '399006': '1.399006',  # 创业板指
    '000300': '0.000300',  # 沪深300
}


class ProxyPool:
    """代理IP池管理器"""
    
    # 免费代理API（备选）
    FREE_PROXY_APIS = [
        'http://ip.jiangxianli.com/api/proxy_ips',
        'https://ip.16yun.cn:8000/api/proxy_ips',
    ]
    
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.last_refresh = 0
        self.refresh_interval = 300  # 5分钟刷新一次
        self.lock = threading.Lock()
        
        # 用户配置的固定代理（优先使用）
        self.fixed_proxies = []
        
        # 从环境变量读取代理列表
        import os
        proxy_str = os.environ.get('HTTP_PROXIES', '')
        if proxy_str:
            self.fixed_proxies = [p.strip() for p in proxy_str.split(',') if p.strip()]
            print(f"加载了 {len(self.fixed_proxies)} 个固定代理")
    
    def get_proxy(self) -> Optional[dict]:
        """获取一个可用代理"""
        with self.lock:
            # 优先使用固定代理
            if self.fixed_proxies:
                proxy = random.choice(self.fixed_proxies)
                return {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }
            
            # 尝试获取免费代理
            if time.time() - self.last_refresh > self.refresh_interval:
                self._refresh_free_proxies()
            
            if self.proxies:
                proxy = self.proxies[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.proxies)
                return proxy
            
            return None
    
    def _refresh_free_proxies(self):
        """从免费API获取代理"""
        self.proxies = []
        # 这里可以添加从免费代理网站获取的逻辑
        # 由于免费代理不稳定，默认返回空
        self.last_refresh = time.time()
        print("免费代理池为空，请配置固定代理")
    
    def add_proxy(self, proxy: str):
        """添加代理到池中"""
        with self.lock:
            if proxy not in self.fixed_proxies:
                self.fixed_proxies.append(proxy)


# 全局代理池
proxy_pool = ProxyPool()


class EastMoneyClient:
    """东方财富行情数据客户端 - 防封版"""
    
    BASE_URL = "https://push2his.eastmoney.com"
    
    # 轮换的User-Agent
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    # 轮换的Referer
    REFERERS = [
        'https://quote.eastmoney.com/',
        'https://quote.eastmoney.com/sh600519.html',
        'https://quote.eastmoney.com/sz000001.html',
        'https://www.eastmoney.com/',
        'https://search.eastmoney.com/',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self._update_headers()
        self.fail_count = 0
        self.max_fails = 3
    
    def _update_headers(self):
        """随机更新Headers"""
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': random.choice(self.REFERERS),
        })
    
    def _get_secid(self, code: str) -> str:
        """获取市场代码"""
        code = code.strip()
        
        # 指数处理
        if code in INDEX_CODES:
            return INDEX_CODES[code]
        
        if code.startswith('6'):
            return f'0.{code}'
        elif code.startswith(('0', '2', '3')):
            return f'1.{code}'
        return f'0.{code}'
    
    def _make_request(self, url: str, params: dict = None, timeout: int = 10) -> Optional[requests.Response]:
        """发起请求，支持代理"""
        # 尝试多次
        for attempt in range(3):
            # 每次请求换UA
            self._update_headers()
            
            # 获取代理
            proxy = proxy_pool.get_proxy()
            
            try:
                if proxy:
                    resp = self.session.get(url, params=params, timeout=timeout, proxies=proxy)
                else:
                    resp = self.session.get(url, params=params, timeout=timeout)
                
                if resp.status_code == 200:
                    self.fail_count = 0
                    return resp
                elif resp.status_code == 403:
                    print(f"IP被封 (403), 尝试切换代理...")
                    self.fail_count += 1
                else:
                    print(f"请求失败: {resp.status_code}")
                    
            except requests.exceptions.ProxyError as e:
                print(f"代理错误: {e}")
                self.fail_count += 1
            except requests.exceptions.RequestException as e:
                print(f"请求异常: {e}")
            
            # 失败后等待并重试
            if self.fail_count >= self.max_fails:
                break
            time.sleep(1 + random.random())
        
        return None
    
    def get_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        secid = self._get_secid(code)
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f59,f60,f116,f117,f118,f119,f120,f121,f122,f124'
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/get"
        
        # 请求间隔
        time.sleep(random.uniform(0.3, 0.8))
        
        resp = self._make_request(url, params=params)
        if not resp:
            print(f"获取实时行情失败: {code}")
            return None
        
        try:
            data = resp.json()
        except:
            print(f"解析JSON失败: {code}")
            return None
        
        if not data.get('data'):
            return None
        
        d = data['data']
        price = d.get('f43', 0) / 100 if d.get('f43') else 0
        
        if price == 0:
            return None
        
        # 判断是否是指数
        is_index = code in INDEX_CODES
        
        if is_index:
            yesterday_close = d.get('f46', 0) / 100 if d.get('f46') else None
        else:
            yesterday_close = d.get('f169', 0) / 100 if d.get('f169') else None
            if not yesterday_close:
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
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': str(period),
            'fqt': '0',
            'beg': start_date,
            'end': end_date
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/kline/get"
        
        time.sleep(random.uniform(0.3, 0.8))
        
        resp = self._make_request(url, params=params)
        if not resp:
            return pd.DataFrame()
        
        try:
            data = resp.json()
        except:
            return pd.DataFrame()
        
        if data.get('data') is None or not data['data'].get('klines'):
            return pd.DataFrame()
        
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
    
    def fetch_and_save(self, code: str) -> bool:
        """获取并保存分时数据"""
        df = self.get_kline(code, period=1)
        if df.empty:
            return False
        
        rt = self.get_realtime(code)
        name = rt.get('name', '') if rt else ''
        
        records = []
        for _, row in df.iterrows():
            records.append({
                'time': row['时间'],
                'open': row['开盘'],
                'close': row['收盘'],
                'high': row['最高'],
                'low': row['最低'],
                'volume': row['成交量'],
                'amount': row['成交额']
            })
        
        save_minute_data(code, name, records)
        return True


def get_all_realtime(codes: List[str]) -> List[Dict]:
    """批量获取实时行情"""
    client = EastMoneyClient()
    results = []
    
    for code in codes:
        data = client.get_realtime(code)
        if data:
            results.append(data)
    
    return results


if __name__ == "__main__":
    client = EastMoneyClient()
    
    print("=== 测试东方财富API ===")
    
    # 测试上证指数
    rt = client.get_realtime('000001')
    print(f"000001 上证指数: {rt}")
    
    # 测试贵州茅台
    rt = client.get_realtime('600519')
    print(f"600519 贵州茅台: {rt}")
