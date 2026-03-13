#!/usr/bin/env python3
"""
东方财富A股分时监控服务
功能：管理自选股 + 告警配置 + 开盘时间自动抓取分时数据
"""

import json
import os
from datetime import datetime, time
from pathlib import Path

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "stocks": [],  # 自选股列表 ["600519", "000001", "300750"]
    "interval": 60,  # 抓取间隔（秒）
    "enabled": True,
    "refresh_interval": 60,  # 前端刷新间隔（秒）
    "alerts": {
        # 涨跌幅告警 (单日)
        "price_change": {
            "enabled": True,
            "threshold": 5.0,  # 涨跌幅超过5%
        },
        # 快速波动告警 (N分钟)
        "rapid_change": {
            "enabled": True,
            "minutes": 30,  # N分钟内
            "threshold": 3.0,  # 涨跌超过3%
        },
        # 放量告警
        "volume_surge": {
            "enabled": True,
            "threshold": 50.0,  # 成交量增加50%
        },
        # 趋势拟合告警（三次拟合都向下）
        "trend_fit": {
            "enabled": True,
            "lookback": 60,  # 看最近多少个数据点（60=1小时，120=2小时）
        },
        # 突破告警
        "breakout": {
            "enabled": False,
            "type": "high",  # high: 突破前高, low: 突破前低
            "days": 20,  # 过去N天
        },
        # 开盘/收盘推送
        "open_close_push": {
            "enabled": True,
            "push_open": True,   # 开盘推送
            "push_close": True,  # 收盘推送
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
        "enabled_types": ["price_change", "rapid_change", "volume_surge", "trend_fit"]  # 仅发送这些类型的告警
    }
}

def load_config() -> dict:
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def add_stock(code: str):
    """添加股票"""
    config = load_config()
    code = code.strip().upper()
    if code not in config["stocks"]:
        config["stocks"].append(code)
        save_config(config)
        return True
    return False

def remove_stock(code: str):
    """移除股票"""
    config = load_config()
    code = code.strip().upper()
    if code in config["stocks"]:
        config["stocks"].remove(code)
        save_config(config)
        return True
    return False

def get_stocks():
    """获取自选股列表"""
    return load_config()["stocks"]

def is_trading_time() -> bool:
    """检查当前是否在交易时间"""
    now = datetime.now()
    current_time = now.time()
    
    # 9:30-11:30 上午
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    
    # 13:00-15:00 下午
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    # 周末
    if now.weekday() >= 5:
        return False
    
    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)

def get_alerts_config() -> dict:
    """获取告警配置"""
    config = load_config()
    return config.get("alerts", DEFAULT_CONFIG["alerts"])

def save_alerts_config(alerts: dict):
    """保存告警配置"""
    config = load_config()
    config["alerts"] = alerts
    save_config(config)

def get_quote0_config() -> dict:
    """获取Quote/0配置"""
    config = load_config()
    return config.get("quote0", DEFAULT_CONFIG["quote0"])

def get_email_config() -> dict:
    """获取邮件配置"""
    config = load_config()
    return config.get("email", DEFAULT_CONFIG["email"])

def is_market_open_time() -> bool:
    """是否刚开盘（9:30-9:45）"""
    now = datetime.now()
    current_time = now.time()
    return time(9, 30) <= current_time <= time(9, 45)

def is_market_close_time() -> bool:
    """是否快收盘（14:45-15:00）"""
    now = datetime.now()
    current_time = now.time()
    return time(14, 45) <= current_time <= time(15, 0)

if __name__ == "__main__":
    # 测试
    print("当前自选股:", get_stocks())
    print("交易时间:", is_trading_time())
    
    # 添加测试股票
    add_stock("000001")
    add_stock("600519")
    print("添加后:", get_stocks())
