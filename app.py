#!/usr/bin/env python3
"""
Flask 主应用 - 从 src/entry 重新导出
"""
from src.entry.app import app
from src.entry.app import create_app

__all__ = ['app', 'create_app']
