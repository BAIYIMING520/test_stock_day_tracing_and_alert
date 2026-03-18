#!/usr/bin/env python3
"""
配置服务 - 加载/保存应用配置、自选股管理、交易时间判断
"""
import json
import os
from datetime import datetime, time
from pathlib import Path

# 项目根目录（stock_monitor/）
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_FILE = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "stocks": [],
    "interval": 60,
    "enabled": True,
    "refresh_interval": 60,
    "alerts": {
        "price_change": {
            "enabled": True,
            "threshold": 5.0,
        },
        "rapid_change": {
            "enabled": True,
            "minutes": 30,
            "threshold": 3.0,
        },
        "volume_surge": {
            "enabled": True,
            "threshold": 50.0,
        },
        "trend_fit": {
            "enabled": True,
            "lookback": 60,
        },
        "breakout": {
            "enabled": False,
            "type": "high",
            "days": 20,
        },
        "open_close_push": {
            "enabled": True,
            "push_open": True,
            "push_close": True,
        },
    },
    "quote0": {
        "enabled": True,
        "api_key": "dot_app_lfiIjUQEFgKTUEkNbjpywfcbDePxRaBkYBCWyhLeCBsCnJBFjtPHSgVRkEWzFgfP",
        "device_id": "9C9E6E3B81E8"
    },
    "email": {
        "enabled": False,
        "smtp_host": "smtp.qq.com",
        "smtp_port": 587,
        "use_tls": True,
        "username": "your_email@qq.com",
        "password": "your_auth_code",
        "to_addrs": ["recipient@example.com"],
        "enabled_types": ["price_change", "rapid_change", "volume_surge", "trend_fit"]
    }
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def add_stock(code: str) -> bool:
    config = load_config()
    code = code.strip().upper()
    if code not in config["stocks"]:
        config["stocks"].append(code)
        save_config(config)
        return True
    return False


def remove_stock(code: str) -> bool:
    config = load_config()
    code = code.strip().upper()
    if code in config["stocks"]:
        config["stocks"].remove(code)
        save_config(config)
        return True
    return False


def get_stocks():
    return load_config()["stocks"]


def is_trading_time() -> bool:
    now = datetime.now()
    current_time = now.time()
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    if now.weekday() >= 5:
        return False
    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)


def get_alerts_config() -> dict:
    config = load_config()
    return config.get("alerts", DEFAULT_CONFIG["alerts"])


def save_alerts_config(alerts: dict):
    config = load_config()
    config["alerts"] = alerts
    save_config(config)


def get_quote0_config() -> dict:
    config = load_config()
    return config.get("quote0", DEFAULT_CONFIG["quote0"])


def get_email_config() -> dict:
    config = load_config()
    return config.get("email", DEFAULT_CONFIG["email"])


def is_market_open_time() -> bool:
    now = datetime.now()
    current_time = now.time()
    return time(9, 30) <= current_time <= time(9, 45)


def is_market_close_time() -> bool:
    now = datetime.now()
    current_time = now.time()
    return time(14, 45) <= current_time <= time(15, 0)


def get_users_file_path() -> Path:
    return BASE_DIR / "users.json"


def get_db_file_path() -> Path:
    return BASE_DIR / "stock_data.db"
