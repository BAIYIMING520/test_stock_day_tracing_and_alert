# -*- coding: utf-8 -*-
"""Fetcher: EastMoney"""

import requests, random
from typing import List, Optional
from datetime import datetime
from ..base import IApiFetcher
from ...dto.vo import RealtimeStockVO


class EastMoneyFetcher(IApiFetcher):
    name = "eastmoney"
    BASE_URL = "https://push2his.eastmoney.com"
    INDEX_CODES = {'000001': '0.000001', '399001': '1.399001', '399006': '1.399006', '000300': '0.000300'}
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'})
    
    def _get_secid(self, code: str) -> str:
        if code in self.INDEX_CODES:
            return self.INDEX_CODES[code]
        if code.startswith('6') or code.startswith('603'):
            return f'1.{code}'
        return f'0.{code}'
    
    def get_realtime(self, code: str) -> Optional[RealtimeStockVO]:
        url = f"{self.BASE_URL}/api/qt/stock/get"
        params = {'secid': self._get_secid(code), 'fields': 'f43,f44,f45,f46,f47,f48,f57,f58'}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            data = resp.json()
            if not data.get('data'):
                return None
            d = data['data']
            price = d.get('f43', 0) / 100 if d.get('f43') else 0
            if price == 0:
                return None
            yesterday_close = d.get('f46', 0) / 100 if d.get('f46') else 0
            change = round(price - yesterday_close, 2) if yesterday_close else 0
            change_pct = round(change / yesterday_close * 100, 2) if yesterday_close else 0
            return RealtimeStockVO(
                code=d.get('f57', code), name=d.get('f58', ''), price=price, change=change, change_pct=change_pct,
                yesterday_close=yesterday_close or 0, open=d.get('f44', 0)/100 if d.get('f44') else 0,
                high=d.get('f45', 0)/100 if d.get('f45') else 0, low=d.get('f47', 0)/100 if d.get('f47') else 0,
                volume=d.get('f48', 0), amount=0, time=datetime.now().strftime('%H:%M:%S'), market_status='open'
            )
        except Exception as e:
            print(f"[EastMoneyFetcher] {code}: {e}")
            return None
    
    def get_daily(self, code: str, days: int = 30) -> List[dict]:
        return []
