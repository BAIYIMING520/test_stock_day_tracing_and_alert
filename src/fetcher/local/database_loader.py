# -*- coding: utf-8 -*-
"""Fetcher: Local 数据库"""
import sqlite3, os
from typing import List
from datetime import datetime
from ..base import ILocalFetcher
from ...dto.vo import RealtimeStockVO, MinuteDataVO

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stock_data.db')

def get_minute_data_from_db(code: str, date: str = None):
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stock_minute_data WHERE code = ? AND date = ? ORDER BY time', (code, date))
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_minute_to_db(data: RealtimeStockVO):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('''INSERT OR REPLACE INTO stock_minute_data (code, name, date, time, open, close, high, low, volume, amount, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data.code, data.name, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), data.open, data.price, data.high, data.low, data.volume, data.amount, int(now.timestamp())))
    conn.commit()
    conn.close()

class DatabaseLoader(ILocalFetcher):
    name = "local"
    
    def get_minute_data(self, code: str, date: str = None) -> List[MinuteDataVO]:
        rows = get_minute_data_from_db(code, date)
        return [MinuteDataVO(code=r['code'], name=r['name'], date=r['date'], time=r['time'], open=r['open'], close=r['close'], high=r['high'], low=r['low'], volume=r['volume'], amount=r['amount']) for r in rows]
    
    def save_minute_data(self, data: RealtimeStockVO):
        save_minute_to_db(data)
