# -*- coding: utf-8 -*-
"""Fetcher: Sina 新浪财经"""

import requests, re, random
from typing import List, Optional
from ..base import IApiFetcher
from ...dto.vo import RealtimeStockVO


class SinaFetcher(IApiFetcher):
    name = "sina"
    BASE_URL = "https://hq.sinajs.cn/list="
    
    INDEX_CODES = {'000001': 'sh000001', '399001': 'sz399001', '399006': 'sz399006'}
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            ]),
            'Referer': 'https://finance.sina.com.cn/',
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
            match = re.search(r'="(.+)"', resp.text)
            if not match:
                return None
            parts = match.group(1).split(',')
            if len(parts) < 32:
                return None
            
            name = parts[0]
            open_p = float(parts[1]) if parts[1] else 0
            yesterday_close = float(parts[2]) if parts[2] else 0
            price = float(parts[3]) if parts[3] else 0
            high = float(parts[4]) if parts[4] else 0
            low = float(parts[5]) if parts[5] else 0
            volume = int(parts[8]) if parts[8] else 0
            amount = float(parts[9]) if parts[9] else 0
            
            change = round(price - yesterday_close, 2) if yesterday_close and price > 0 else 0
            change_pct = round(change / yesterday_close * 100, 2) if yesterday_close else 0
            
            return RealtimeStockVO(
                code=code, name=name, price=price, change=change, change_pct=change_pct,
                yesterday_close=yesterday_close, open=open_p, high=high, low=low,
                volume=volume, amount=amount, time=parts[30][:8] if len(parts) > 30 and parts[30] else '',
                market_status='open' if price > 0 else 'closed'
            )
        except Exception as e:
            print(f"[SinaFetcher] {code}: {e}")
            return None
    
    def get_daily(self, code: str, days: int = 30) -> List[dict]:
        return []
