# -*- coding: utf-8 -*-
"""启动入口"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.entry.app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
