#!/usr/bin/env python3
"""
东方财富A股数据获取模块
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import time
import sys
sys.path.append(str(__file__).rsplit('/', 1)[0])
from database import save_minute_data

class EastMoneyClient:
    """东方财富行情数据客户端"""
    
    BASE_URL = "https://push2.eastmoney.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _get_secid(self, code: str) -> str:
        """获取市场代码
        尝试多个可能的市场，返回有效的
        """
        code = code.strip().lower()
        
        # 已经是完整格式
        if '.' in code:
            return code
        
        # 可能的secid列表（按可能性排序）
        candidates = []
        
        if code.startswith('6') or code.startswith('603'):
            # 6开头和603开头用深圳secid (东方财富API的特殊设计)
            candidates.append(f'1.{code}')
        elif code.startswith('0'):
            if code == '000001':
                # 000001需要用深圳secid获取上证指数
                candidates.append(f'1.{code}')
            else:
                # 002xxx是上海股
                candidates.append(f'0.{code}')
        elif code.startswith('3'):
            # 300xxx是上海股
            candidates.append(f'0.{code}')
        elif code.startswith(('8', '4')):
            candidates.append(f'0.{code}')  # 北京
        else:
            candidates.append(f'0.{code}')  # 默认上海
        
        # 尝试获取数据，返回第一个成功的
        for secid in candidates:
            if self._test_secid(secid):
                return secid
        
        # 如果都没成功，返回第一个候选
        return candidates[0]
    
    def _test_secid(self, secid: str) -> bool:
        """测试secid是否有效"""
        params = {
            'secid': secid,
            'fields': 'f57'
        }
        try:
            url = f"{self.BASE_URL}/api/qt/stock/get"
            resp = self.session.get(url, params=params, timeout=3)
            data = resp.json()
            return data.get('data') is not None
        except Exception as e:
            print(f"测试secid失败 {secid}: {e}")
            return False
    
    def _get_yesterday_close(self, secid: str) -> Optional[float]:
        """获取昨日收盘价"""
        try:
            # 获取最近2天的日K线
            params = {
                'secid': secid,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56',
                'klt': '101',  # 日K
                'fqt': '0',
                'beg': '20250101',
                'end': datetime.now().strftime('%Y%m%d')
            }
            url = f"{self.BASE_URL}/api/qt/stock/kline/get"
            resp = self.session.get(url, params=params, timeout=5)
            data = resp.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                if len(klines) >= 2:
                    # 取倒数第二条（昨天）
                    yesterday = klines[-2].split(',')
                    return float(yesterday[2])  # 收盘价
        except Exception as e:
            print(f"Error getting yesterday close: {e}")
        return None
    
    def get_kline(self, code: str, period: int = 1, 
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            code: 股票代码 (如 000001, 600519)
            period: K线周期 (1/5/15/30/60 分钟)
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        
        Returns:
            DataFrame with columns: 时间, 开盘, 收盘, 最高, 最低, 成交量, 成交额
        """
        secid = self._get_secid(code)
        
        # 默认今天
        if not start_date:
            start_date = datetime.now().strftime('%Y%m%d')
        if not end_date:
            end_date = start_date
        
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': str(period),
            'fqt': '0',  # 不复权
            'beg': start_date,
            'end': end_date
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/kline/get"
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('data') is None or not data['data'].get('klines'):
                return pd.DataFrame()
            
            klines = data['data']['klines']
            
            # 解析数据
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
            
            df = pd.DataFrame(records)
            return df
            
        except Exception as e:
            print(f"Error fetching {code}: {e}")
            return pd.DataFrame()
    
    def get_realtime(self, code: str) -> Optional[Dict]:
        """获取实时行情（含昨日收盘价）"""
        secid = self._get_secid(code)
        
        params = {
            'secid': secid,
            'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f59,f60,f116,f117,f118,f119,f120,f121,f122,f124'
        }
        
        url = f"{self.BASE_URL}/api/qt/stock/get"
        
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            
            if not data.get('data'):
                return None
            
            d = data['data']
            
            # 获取昨日收盘价（从K线数据）
            yesterday_close = None
            
            result = {
                'code': d.get('f57'),
                'name': d.get('f58'),
                'price': d.get('f43', 0) / 100 if d.get('f43') else 0,
                'change': 0,
                'change_pct': 0,
                'volume': d.get('f47', 0),
                'amount': d.get('f48', 0),
                'yesterday_close': None,
                'time': datetime.now().strftime('%H:%M:%S')
            }
            
            # 判断是否是指数（000001, 399xxx等）
            code = d.get('f57', '')
            is_index = code in ['000001', '399001', '399006']
            
            if is_index:
                # 指数：f46 是昨日收盘点位
                result['yesterday_close'] = d.get('f46', 0) / 100 if d.get('f46') else None
            else:
                # 股票：f46 是昨日收盘价
                result['yesterday_close'] = d.get('f46', 0) / 100 if d.get('f46') else None
            
            # 计算涨跌和涨跌幅（用 f43 和 f46 直接计算，避免 f45 字段异常）
            if result['yesterday_close'] and result['yesterday_close'] > 0:
                result['change'] = round(result['price'] - result['yesterday_close'], 2)
                result['change_pct'] = round(result['change'] / result['yesterday_close'] * 100, 2)
            
            return result
            
        except Exception as e:
            print(f"Error fetching realtime {code}: {e}")
            return None
    
    def get_latest_minute(self, code: str) -> Optional[Dict]:
        """获取最新一分钟数据"""
        df = self.get_kline(code, period=1)
        if df.empty:
            return None
        
        latest = df.iloc[-1].to_dict()
        return latest

    def fetch_and_save(self, code: str) -> bool:
        """获取并保存分时数据到数据库"""
        df = self.get_kline(code, period=1)
        if df.empty:
            return False
        
        # 获取股票名称
        rt = self.get_realtime(code)
        name = rt.get('name', '') if rt else ''
        
        # 转换数据格式
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
        
        # 保存到数据库
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
        time.sleep(0.1)  # 避免请求过快
    
    return results


if __name__ == "__main__":
    client = EastMoneyClient()
    
    # 测试
    print("=== 测试获取上证指数 ===")
    df = client.get_kline('000001', period=1)
    if not df.empty:
        print(f"获取到 {len(df)} 条数据")
        print(df.tail(3))
    
    print("\n=== 测试实时行情 ===")
    rt = client.get_realtime('000001')
    if rt:
        print(f"上证指数: {rt}")
