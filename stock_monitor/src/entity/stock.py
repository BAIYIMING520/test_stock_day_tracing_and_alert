# -*- coding: utf-8 -*-
"""DDD: Entity"""
from dataclasses import dataclass

@dataclass
class Stock:
    code: str
    name: str = ""
    INDEX_CODES = {'000001': 'sh000001', '399001': 'sz399001', '399006': 'sz399006', '000300': 'sh000300'}
    
    def is_index(self) -> bool:
        return self.code in self.INDEX_CODES
    
    def get_full_code(self, market: str = "sina") -> str:
        if self.code in self.INDEX_CODES:
            return self.INDEX_CODES[self.code]
        prefix = 'sh' if self.code.startswith('6') else 'sz'
        return f"{prefix}{self.code}"
