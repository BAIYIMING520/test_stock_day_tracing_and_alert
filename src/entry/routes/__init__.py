"""路由模块"""
from flask import Flask


def register_routes(app: Flask):
    """注册所有蓝图"""
    from .auth import auth_bp
    from .stocks import stocks_bp
    from .alerts import alerts_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(stocks_bp, url_prefix='/api')
    app.register_blueprint(alerts_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
