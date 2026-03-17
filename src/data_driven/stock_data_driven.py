# -*- coding: utf-8 -*-
"""Data Driven: StockDataDriven"""
from typing import List, Optional
from ..dto.vo import RealtimeStockVO, MinuteDataVO
from ..fetcher import get_api_fetcher, get_local_fetcher, IApiFetcher, ILocalFetcher

class StockDataDriven:
    def __init__(self, api_priority: List[str] = None):
        self.api_priority = api_priority or ['sina', 'tencent', 'eastmoney']
        self.api_fetchers = {}
        self.local_fetcher = None
    
    def _get_api(self, name: str) -> IApiFetcher:
        if name not in self.api_fetchers:
            self.api_fetchers[name] = get_api_fetcher(name)
        return self.api_fetchers[name]
    
    def _get_local(self) -> ILocalFetcher:
        if self.local_fetcher is None:
            self.local_fetcher = get_local_fetcher()
        return self.local_fetcher
    
    def get_realtime(self, code: str) -> Optional[RealtimeStockVO]:
        for name in self.api_priority:
            result = self._get_api(name).get_realtime(code)
            if result:
                return result
        return None
    
    def get_realtime_batch(self, codes: List[str]) -> List[RealtimeStockVO]:
        return [d for c in codes if (d := self.get_realtime(c))]
    
    def get_minute_data(self, code: str, date: str = None) -> List[MinuteDataVO]:
        return self._get_local().get_minute_data(code, date)
    
    def save_minute_data(self, data: RealtimeStockVO):
        self._get_local().save_minute_data(data)

_stock_driven = None
def get_stock_data_driven() -> StockDataDriven:
    global _stock_driven
    if _stock_driven is None:
        _stock_driven = StockDataDriven()
    return _stock_driven
