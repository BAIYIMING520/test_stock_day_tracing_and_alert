# -*- coding: utf-8 -*-
"""启动入口"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from src.app import app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
