#!/usr/bin/env python3
"""
分时数据存储模块 - SQLite
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
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
    
    # 告警历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            type TEXT,
            msg TEXT,
            severity TEXT DEFAULT 'info',
            alert_time TEXT
        )
    ''')
    
    # 告警历史索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_time ON alert_history(alert_time)')
    
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


# ==================== 告警历史 ====================

def save_alert_to_db(alert: dict):
    """保存告警到数据库"""
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


def get_alert_history_from_db(days: int = 5, code: str = None, alert_type: str = None) -> list:
    """从数据库获取告警历史
    
    Args:
        days: 查询最近几天的数据，默认5天
        code: 按股票代码筛选
        alert_type: 按告警类型筛选
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 计算日期范围
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    query = "SELECT * FROM alert_history WHERE alert_time >= ?"
    params = [start_date]
    
    if code:
        query += " AND code = ?"
        params.append(code)
    
    if alert_type:
        query += " AND type = ?"
        params.append(alert_type)
    
    query += " ORDER BY alert_time DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def clear_alert_history_from_db():
    """清空告警历史"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM alert_history')
    conn.commit()
    conn.close()


def cleanup_old_alerts(days: int = 5):
    """清理过期告警（保留指定天数）"""
    conn = get_db()
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    cursor.execute('DELETE FROM alert_history WHERE alert_time < ?', (cutoff_date,))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        print(f"已清理 {deleted} 条过期告警记录")
