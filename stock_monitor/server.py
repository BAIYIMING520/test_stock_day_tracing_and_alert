#!/usr/bin/env python3
"""
A股分时监控服务启动入口
"""

import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import create_app

def main():
    # 启动服务
    app = create_app()

    print("=" * 50)
    print("A股分时监控服务启动")
    print("=" * 50)
    print("访问 http://localhost:8000 管理自选股")
    print("点击卡片查看分时图")
    print("后台告警任务: 已启动")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)

    app.run(host='0.0.0.0', port=8000, debug=False)

if __name__ == '__main__':
    main()
