#!/usr/bin/env python3
"""
数据库基础设施 - SQLite 分时数据存储
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

# 延迟导入避免循环依赖
_db_file = None

def _get_db_file():
    global _db_file
    if _db_file is None:
        from src.services.config import get_db_file_path
        _db_file = get_db_file_path()
    return _db_file


def get_db():
    conn = sqlite3.connect(str(_get_db_file()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

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

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_date ON stock_minute_data(code, date)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            type TEXT,
            msg TEXT,
            severity TEXT,
            alert_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def save_minute_data(code: str, name: str, data: dict):
    """保存分时数据"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO stock_minute_data
        (code, name, date, time, open, close, high, low, volume, amount, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        code, name,
        data.get('date', ''),
        data.get('time', ''),
        data.get('open', 0),
        data.get('close', 0),
        data.get('high', 0),
        data.get('low', 0),
        data.get('volume', 0),
        data.get('amount', 0),
        data.get('timestamp', 0)
    ))

    conn.commit()
    conn.close()


def get_minute_data(code: str, date: str = None) -> List[dict]:
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM stock_minute_data
        WHERE code = ? AND date = ?
        ORDER BY timestamp ASC
    ''', (code, date))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_latest_close_data(code: str) -> Optional[dict]:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM stock_minute_data
        WHERE code = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (code,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def save_alert_to_db(alert: dict):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO alert_history (code, name, type, msg, severity, alert_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        alert.get('code', ''),
        alert.get('name', ''),
        alert.get('type', ''),
        alert.get('msg', ''),
        alert.get('severity', 'info'),
        alert.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ))

    conn.commit()
    conn.close()


def get_alert_history_from_db(days: int = 5, code: str = None, alert_type: str = None,
                               page: int = 1, page_size: int = 30) -> dict:
    conn = get_db()
    cursor = conn.cursor()

    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    where = "WHERE alert_time >= ?"
    params = [since]

    if code:
        where += " AND code = ?"
        params.append(code)
    if alert_type:
        where += " AND type = ?"
        params.append(alert_type)

    cursor.execute(f"SELECT COUNT(*) FROM alert_history {where}", params)
    total = cursor.fetchone()[0]

    offset = (page - 1) * page_size
    cursor.execute(f'''
        SELECT * FROM alert_history
        {where}
        ORDER BY alert_time DESC
        LIMIT ? OFFSET ?
    ''', params + [page_size, offset])

    rows = cursor.fetchall()
    conn.close()

    return {
        'items': [dict(row) for row in rows],
        'total': total,
        'page': page,
        'page_size': page_size
    }


def clear_alert_history_from_db(days: int = 0):
    conn = get_db()
    cursor = conn.cursor()

    if days > 0:
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("DELETE FROM alert_history WHERE alert_time < ?", (since,))
    else:
        cursor.execute("DELETE FROM alert_history")

    conn.commit()
    conn.close()
