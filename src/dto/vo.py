# -*- coding: utf-8 -*-
"""
DDD: VO (View Object) - 展示对象
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RealtimeStockVO:
    """
    实时股票行情 VO
    用于前端展示当前股票价格状态
    """
    code: str                      
    name: str = ""                 
    price: float = 0.0             
    change: float = 0.0           
    change_pct: float = 0.0        
    yesterday_close: float = 0.0   
    open: float = 0.0              
    high: float = 0.0              
    low: float = 0.0               
    volume: int = 0                
    amount: float = 0.0            
    time: str = ""                 
    market_status: str = "closed"   

    def to_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change': self.change,
            'change_pct': self.change_pct,
            'yesterday_close': self.yesterday_close,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'time': self.time,
            'market_status': self.market_status,
        }


@dataclass
class MinuteDataVO:
    """
    分时数据 VO
    """
    code: str = ""
    name: str = ""
    date: str = ""
    time: str = ""
    open: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: int = 0
    amount: float = 0.0

    def to_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'date': self.date,
            'time': self.time,
            'open': self.open,
            'close': self.close,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
        }
