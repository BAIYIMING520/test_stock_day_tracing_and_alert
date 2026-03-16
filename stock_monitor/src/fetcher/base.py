# -*- coding: utf-8 -*-
"""
DDD: Fetcher - 数据获取抽象层
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..dto.vo import RealtimeStockVO, MinuteDataVO


class IApiFetcher(ABC):
    """外部 API 数据获取接口"""
    
    name: str = "BaseApiFetcher"
    
    @abstractmethod
    def get_realtime(self, code: str) -> Optional[RealtimeStockVO]:
        pass
    
    @abstractmethod
    def get_daily(self, code: str, days: int = 30) -> List[dict]:
        pass


class ILocalFetcher(ABC):
    """本地数据获取接口"""
    
    name: str = "BaseLocalFetcher"
    
    @abstractmethod
    def get_minute_data(self, code: str, date: str = None) -> List[MinuteDataVO]:
        pass
    
    @abstractmethod
    def save_minute_data(self, data: RealtimeStockVO):
        pass
