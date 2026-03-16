# -*- coding: utf-8 -*-
"""Alert: 告警检查"""
from datetime import datetime
from ..dto.vo import RealtimeStockVO
from ..repo.data_model import AlertHistoryModel

class AlertChecker:
    def __init__(self):
        self.last_prices = {}
    
    def check_price_change(self, data: RealtimeStockVO, threshold: float = 5.0):
        if abs(data.change_pct) >= threshold:
            return f"{'涨' if data.change_pct > 0 else '跌'}幅 {data.change_pct:.2f}%"
        return None

_alert_checker = AlertChecker()

def check_and_push_alerts(data: RealtimeStockVO, push_enabled: bool = True):
    msg = _alert_checker.check_price_change(data, threshold=5.0)
    if msg:
        print(f"[告警] {data.code} {data.name}: {msg}")

__all__ = ['AlertChecker', 'check_and_push_alerts']
