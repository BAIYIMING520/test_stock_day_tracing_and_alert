#!/usr/bin/env python3
"""
数据获取基础设施 - 东方财富API + 新浪财经API + 代理池 + UA轮换
"""
import requests
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import time
import re
import random
import threading
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.database import save_minute_data


# 指数代码映射
INDEX_CODES = {
    '000001': 'sh000001',
    '399001': 'sz399001',
    '399006': 'sz399006',
    '000300': 'sh000300',
}


class ProxyPool:
    """代理IP池管理器"""

    def __init__(self):
        self.fixed_proxies = []
        proxy_str = os.environ.get('HTTP_PROXIES', '')
        if proxy_str:
            self.fixed_proxies = [p.strip() for p in proxy_str.split(',') if p.strip()]
            print(f"加载了 {len(self.fixed_proxies)} 个固定代理")

    def get_proxy(self) -> Optional[dict]:
        if self.fixed_proxies:
            proxy = random.choice(self.fixed_proxies)
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
        return None


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
        code = code.strip()
        if code == '000001':
            return 'sh000001'
        elif code.startswith(('0', '3')):
            return f'sz{code}'
        elif code.startswith(('6',)):
            return f'sh{code}'
        return code

    def get_realtime(self, code: str) -> Optional[dict]:
        try:
            full_code = self._get_code(code)
            url = f"{self.BASE_URL}{full_code}"
            resp = self.session.get(url, timeout=5)
            resp.encoding = 'gbk'

            m = re.search(r'"([^"]*)"', resp.text)
            if not m:
                return None

            fields = m.group(1).split(',')
            if len(fields) < 10:
                return None

            return {
                'code': code,
                'name': fields[0],
                'open': float(fields[1]) if fields[1] else 0,
                'close': float(fields[3]) if fields[3] else 0,
                'price': float(fields[3]) if fields[3] else 0,
                'high': float(fields[4]) if fields[4] else 0,
                'low': float(fields[5]) if fields[5] else 0,
                'volume': int(float(fields[8])) if fields[8] else 0,
                'amount': float(fields[9]) if fields[9] else 0,
                'date': fields[10] if len(fields) > 10 else '',
                'time': fields[11] if len(fields) > 11 else '',
                'change': 0,
                'change_pct': 0,
            }
        except Exception:
            return None

    def fetch_and_save(self, code: str) -> bool:
        data = self.get_realtime(code)
        if data:
            save_minute_data(code, data.get('name', ''), data)
            return True
        return False


class EastMoneyClient:
    """东方财富数据客户端"""

    BASE_URL = "https://push2.eastmoney.com/api/qt/stock/get"

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Referer': 'https://quote.eastmoney.com/',
        })

    def _get_market(self, code: str) -> str:
        if code.startswith('6'):
            return '1'
        elif code.startswith(('0', '3')):
            return '0'
        return '1'

    def get_realtime(self, code: str) -> Optional[dict]:
        try:
            market = self._get_market(code)
            params = {
                'secid': f'{market}.{code}',
                'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            }
            resp = self.session.get(self.BASE_URL, params=params, timeout=5)
            resp.encoding = 'utf-8'
            data = resp.json()

            if data.get('data') is None:
                return None

            d = data['data']
            price = d.get('f43', 0) / 100
            close = d.get('f60', 0) / 100 if d.get('f60') else price
            change = price - close
            change_pct = (change / close * 100) if close > 0 else 0

            now = datetime.now()
            return {
                'code': code,
                'name': d.get('f58', ''),
                'open': d.get('f43', 0) / 100 if d.get('f43') else 0,
                'close': close,
                'price': price,
                'high': d.get('f44', 0) / 100 if d.get('f44') else 0,
                'low': d.get('f45', 0) / 100 if d.get('f45') else 0,
                'volume': d.get('f47', 0),
                'amount': d.get('f48', 0),
                'change': change,
                'change_pct': round(change_pct, 2),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'timestamp': int(now.timestamp()),
            }
        except Exception:
            return None

    def fetch_and_save(self, code: str) -> bool:
        data = self.get_realtime(code)
        if data:
            save_minute_data(code, data.get('name', ''), data)
            return True
        return False


class StockClient:
    """统一客户端，支持多数据源"""

    def __init__(self):
        self.clients = [EastMoneyClient(), SinaClient()]

    def get_realtime(self, code: str) -> Optional[dict]:
        for client in self.clients:
            try:
                result = client.get_realtime(code)
                if result:
                    return result
            except Exception:
                continue
        return None


def get_all_realtime(codes: List[str]) -> List[dict]:
    client = StockClient()
    results = []
    for code in codes:
        data = client.get_realtime(code)
        if data:
            results.append(data)
        time.sleep(0.1)
    return results
