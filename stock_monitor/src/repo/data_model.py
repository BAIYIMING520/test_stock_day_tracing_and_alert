# -*- coding: utf-8 -*-
"""DDD: Repo - 数据模型"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class MinuteDataModel:
    id: Optional[int] = None
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
    timestamp: int = 0

@dataclass
class AlertHistoryModel:
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    type: str = ""
    msg: str = ""
    severity: str = "info"
    alert_time: str = ""
