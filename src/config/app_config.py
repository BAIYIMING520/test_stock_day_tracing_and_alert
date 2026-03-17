# -*- coding: utf-8 -*-
"""Config: 应用配置"""
import json, os

CONFIG_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_FETCHER_CONFIG = os.path.join(CONFIG_DIR, 'config', 'data_fetcher_config.json')
STOCK_CONFIG = os.path.join(CONFIG_DIR, 'config', 'stock_config.json')

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except: pass
    return default

def get_stocks():
    return load_json(STOCK_CONFIG, {}).get('stocks', ['000001', '600519'])

def add_stock(code: str) -> bool:
    cfg = load_json(STOCK_CONFIG, {})
    stocks = cfg.get('stocks', [])
    if code not in stocks:
        stocks.append(code)
        cfg['stocks'] = stocks
        with open(STOCK_CONFIG, 'w') as f:
            json.dump(cfg, f, indent=2)
        return True
    return False

def remove_stock(code: str) -> bool:
    cfg = load_json(STOCK_CONFIG, {})
    stocks = cfg.get('stocks', [])
    if code in stocks:
        stocks.remove(code)
        cfg['stocks'] = stocks
        with open(STOCK_CONFIG, 'w') as f:
            json.dump(cfg, f, indent=2)
        return True
    return False

def is_trading_time():
    import datetime
    now = datetime.datetime.now()
    if now.weekday() >= 5: return False
    return (9 <= now.hour < 11) or (now.hour == 11 and now.minute <= 30) or (13 <= now.hour < 15)

def load_data_fetcher_config():
    return load_json(DATA_FETCHER_CONFIG, {"api": {"priority": ["sina", "tencent", "eastmoney"]}})
