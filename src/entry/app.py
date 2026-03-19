#!/usr/bin/env python3
"""
A股分时监控服务 - Web服务器
功能：前端管理界面 + 实时数据展示 + 分时图表
"""
from flask import Flask, render_template
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent  # stock_monitor/


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__, static_folder=str(BASE_DIR / 'static'), static_url_path='')

    # 注册蓝图
    from src.entry.routes import register_routes
    register_routes(app)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app


# 创建应用实例
app = create_app()


def main():
    """主入口"""
    from src.services.config import load_config
    from src.domain.scheduler.runner import BackgroundTask

    # 启动后台任务
    config = load_config()
    interval = config.get("refresh_interval", 60)
    bt = BackgroundTask()
    bt.start(interval=interval)

    print("=" * 50)
    print("A股分时监控服务启动")
    print("=" * 50)
    print("访问 http://localhost:8000 管理自选股")
    print("点击卡片查看分时图")
    print("=" * 50)

    app.run(host="0.0.0.0", port=8000, debug=True)


if __name__ == "__main__":
    main()
