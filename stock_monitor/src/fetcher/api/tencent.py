# -*- coding: utf-8 -*-
"""Fetcher: Tencent"""

import requests, re, random
from typing import List, Optional
from ..base import IApiFetcher
from ...dto.vo import RealtimeStockVO


class TencentFetcher(IApiFetcher):
    name = "tencent"
    BASE_URL = "https://qt.gtimg.cn/q="
    INDEX_CODES = {'000001': 'sh000001', '399001': 'sz399001', '399006': 'sz399006', '000300': 'sh000300'}
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64, x64; rv:121.0) Gecko/20100101',
            ]),
            'Referer': 'https://finance.qq.com/',
        })
    
    def _get_code(self, code: str) -> str:
        if code in self.INDEX_CODES:
            return self.INDEX_CODES[code]
        return f"{'sh' if code.startswith('6') else 'sz'}{code}"
    
    def get_realtime(self, code: str) -> Optional[RealtimeStockVO]:
        url = f"{self.BASE_URL}{self._get_code(code)}"
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            text = resp.content.decode('GBK', errors='ignore')
            match = re.search(r'v_\w+="(.+)"', text)
            if not match:
                return None
            parts = match.group(1).split('~')
            if len(parts) < 10:
                return None
            
            name = parts[1] if len(parts) > 1 else code
            price = float(parts[3]) if parts[3] else 0
            yesterday_close = float(parts[4]) if parts[4] else 0
            open_p = float(parts[5]) if parts[5] else 0
            volume = int(parts[6]) if parts[6] else 0
            amount = float(parts[7]) if parts[7] else 0
            
            change = round(price - yesterday_close, 2) if yesterday_close and price > 0 else 0
            change_pct = round(change / yesterday_close * 100, 2) if yesterday_close else 0
            
            return RealtimeStockVO(
                code=code, name=name, price=price, change=change, change_pct=change_pct,
                yesterday_close=yesterday_close, open=open_p, high=price, low=price,
                volume=volume, amount=amount, time='',
                market_status='open' if price > 0 else 'closed'
            )
        except Exception as e:
            print(f"[TencentFetcher] {code}: {e}")
            return None
    
    def get_daily(self, code: str, days: int = 30) -> List[dict]:
        return []
