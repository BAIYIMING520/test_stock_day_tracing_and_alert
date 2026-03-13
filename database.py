#!/usr/bin/env python3
"""
分时数据存储模块 - SQLite
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

DB_FILE = Path(__file__).parent / "stock_data.db"

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 股票分时数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_minute_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL,
            close REAL,
            high REAL,
            low REAL,
            volume INTEGER,
            amount REAL,
            timestamp INTEGER,
            UNIQUE(code, date, time)
        )
    ''')
    
    # 索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_date ON stock_minute_data(code, date)')
    
    conn.commit()
    conn.close()

def save_minute_data(code: str, name: str, data: list):
    """保存分钟数据
    
    data: [{time, open, close, high, low, volume, amount}, ...]
    """
    if not data:
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y%m%d')
    timestamp = int(datetime.now().timestamp())
    
    for row in data:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_minute_data 
                (code, name, date, time, open, close, high, low, volume, amount, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code, name, today,
                row.get('time', ''),
                row.get('open'), row.get('close'),
                row.get('high'), row.get('low'),
                row.get('volume'), row.get('amount'),
                timestamp
            ))
        except Exception as e:
            print(f"Error saving {code} {row.get('time')}: {e}")
    
    conn.commit()
    conn.close()

def get_minute_data(code: str, date: str = None) -> list:
    """获取分钟数据
    
    date: YYYYMMDD 格式，默认今天
    """
    if not date:
        date = datetime.now().strftime('%Y%m%d')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT time, open, close, high, low, volume, amount
        FROM stock_minute_data
        WHERE code = ? AND date = ?
        ORDER BY time
    ''', (code, date))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_latest_minute(code: str) -> dict:
    """获取最新一条分钟数据"""
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y%m%d')
    
    cursor.execute('''
        SELECT * FROM stock_minute_data
        WHERE code = ? AND date = ?
        ORDER BY time DESC LIMIT 1
    ''', (code, today))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


if __name__ == "__main__":
    init_db()
    print(f"数据库初始化完成: {DB_FILE}")
