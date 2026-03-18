#!/usr/bin/env python3
"""
服务启动入口
"""
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.entry.app import app
from src.infrastructure.database import init_db

def main():
    init_db()

    print("=" * 50)
    print("A股分时监控服务启动")
    print("=" * 50)
    print("访问 http://localhost:8000 管理自选股")
    print("后台告警任务: 已启动（需单独启动 BackgroundTask）")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)

    app.run(host='0.0.0.0', port=8000, debug=False)


if __name__ == '__main__':
    main()
