#!/usr/bin/env python3
"""
A股分时监控服务 - API服务器
功能：仅提供 REST API，Token 认证
"""

import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from flask import Flask, jsonify, request, session, send_from_directory
from functools import wraps
import hashlib
import uuid
import time
from pathlib import Path

# 从 backend 模块导入
from config import load_config, save_config, add_stock, remove_stock, get_stocks, is_trading_time
from client import EastMoneyClient, get_all_realtime
from database import init_db, get_minute_data, verify_user, get_user_id, get_user_stocks, add_user_stock, remove_user_stock, get_user_alert_config, save_user_alert_config
from database import create_user
from alerts import get_alert_history, clear_alert_history

# Token 存储（内存中）
# 格式: {token: {"user_id": xxx, "username": xxx, "expire_at": timestamp}}
TOKENS = {}
TOKEN_EXPIRE_SECONDS = 24 * 60 * 60  # 24小时

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.secret_key = 'stock-monitor-secret-key'

    # 初始化数据库
    init_db()

    # 创建默认用户
    if not verify_user('admin', 'admin'):
        create_user('admin', 'admin')
        print("默认用户已创建: admin / admin")

    # 清理过期 token
    def clean_expired_tokens():
        now = time.time()
        expired = [t for t, data in TOKENS.items() if data['expire_at'] < now]
        for t in expired:
            del TOKENS[t]

    # Token 认证装饰器
    def require_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Unauthorized', 'message': '请先登录'}), 401

            clean_expired_tokens()

            if token not in TOKENS:
                return jsonify({'error': 'Unauthorized', 'message': '登录已过期，请重新登录'}), 401

            token_data = TOKENS[token]
            session['user_id'] = token_data['user_id']
            session['username'] = token_data['username']
            return f(*args, **kwargs)
        return decorated

    def require_admin(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Unauthorized'}), 401

            clean_expired_tokens()

            if token not in TOKENS:
                return jsonify({'error': 'Unauthorized'}), 401

            token_data = TOKENS[token]
            if token_data['username'] != 'admin':
                return jsonify({'error': 'Admin only'}), 403

            session['user_id'] = token_data['user_id']
            session['username'] = token_data['username']
            return f(*args, **kwargs)
        return decorated

    # ==================== API路由 ====================

    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')

    @app.route('/src/<path:filename>')
    def serve_src(filename):
        return send_from_directory('src', filename)

    # 登录接口
    @app.route('/api/login', methods=['POST'])
    def api_login():
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        if not verify_user(username, password):
            return jsonify({'error': '用户名或密码错误'}), 401

        # 生成 token
        token = str(uuid.uuid4())
        user_id = get_user_id(username)
        TOKENS[token] = {
            'user_id': user_id,
            'username': username,
            'expire_at': time.time() + TOKEN_EXPIRE_SECONDS
        }

        print(f"用户 {username} 登录，token: {token[:8]}...")

        return jsonify({
            'success': True,
            'token': token,
            'username': username,
            'expire_in': TOKEN_EXPIRE_SECONDS
        })

    # 登出接口
    @app.route('/api/logout', methods=['POST'])
    def api_logout():
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token in TOKENS:
            username = TOKENS[token]['username']
            del TOKENS[token]
            print(f"用户 {username} 登出")
        return jsonify({'success': True})

    @app.route('/api/stocks', methods=['GET'])
    @require_auth
    def api_get_stocks():
        stocks = get_stocks()
        return jsonify(stocks)

    @app.route('/api/stocks', methods=['POST'])
    @require_auth
    def api_add_stock():
        code = request.json.get('code', '').strip().upper()
        if not code:
            return jsonify({'error': '股票代码不能为空'}), 400
        if len(code) != 6 or not code.isdigit():
            return jsonify({'error': '请输入6位数字股票代码'}), 400
        if add_stock(code):
            return jsonify({'success': True, 'message': f'{code} 添加成功'})
        return jsonify({'error': '添加失败'}), 400

    @app.route('/api/stocks/<code>', methods=['DELETE'])
    @require_auth
    def api_delete_stock(code):
        if remove_stock(code):
            return jsonify({'success': True, 'message': f'{code} 已删除'})
        return jsonify({'error': '删除失败'}), 400

    @app.route('/api/realtime', methods=['GET'])
    @require_auth
    def api_realtime():
        data = get_all_realtime()
        return jsonify(data)

    @app.route('/api/minute/<code>', methods=['GET'])
    @require_auth
    def api_minute(code):
        data = get_minute_data(code)
        return jsonify(data)

    @app.route('/api/alerts', methods=['GET'])
    @require_auth
    def api_get_alerts():
        user_id = session.get('user_id')
        config = get_user_alert_config(user_id) if user_id else None
        return jsonify(config or load_config().get('alerts', {}))

    @app.route('/api/alerts', methods=['POST'])
    @require_auth
    def api_save_alerts():
        user_id = session.get('user_id')
        config = request.json
        save_user_alert_config(user_id, config)
        return jsonify({'success': True, 'message': '配置已保存'})

    @app.route('/api/alerts/history', methods=['GET'])
    @require_auth
    def api_alert_history():
        action = request.args.get('action')
        if action == 'clear':
            days = int(request.args.get('days', 0))
            if days > 0:
                clear_alert_history(days=days)
                return jsonify({'success': True, 'message': f'已清理{days}天前的告警'})
            else:
                clear_alert_history()
                return jsonify({'success': True, 'message': '已清空'})

        days = float(request.args.get('days', 5))
        code = request.args.get('code')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 30))

        return jsonify(get_alert_history(days=days, code=code, page=page, page_size=page_size))

    # ==================== 用户管理 API ====================

    @app.route('/api/me', methods=['GET'])
    @require_auth
    def api_current_user():
        return jsonify({'username': session.get('username', '')})

    @app.route('/api/admin/users', methods=['GET'])
    @require_admin
    def api_list_users():
        import sqlite3
        DB_FILE = Path(__file__).parent / "stock_data.db"
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users ORDER BY id')
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(users)

    @app.route('/api/admin/users', methods=['POST'])
    @require_admin
    def api_create_user():
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        if create_user(username, password):
            return jsonify({'success': True, 'message': f'用户 {username} 创建成功'})
        else:
            return jsonify({'error': '用户名已存在'}), 400

    @app.route('/api/admin/users/<username>', methods=['PUT'])
    @require_admin
    def api_change_password(username):
        import hashlib
        import sqlite3
        from pathlib import Path

        data = request.get_json()
        new_password = data.get('password', '').strip()

        if not new_password:
            return jsonify({'error': '密码不能为空'}), 400

        DB_FILE = Path(__file__).parent / "stock_data.db"
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        hashed = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute('UPDATE users SET password=? WHERE username=?', (hashed, username))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        if affected > 0:
            return jsonify({'success': True, 'message': f'用户 {username} 密码已修改'})
        else:
            return jsonify({'error': '用户不存在'}), 404

    @app.route('/api/admin/users/<username>', methods=['DELETE'])
    @require_admin
    def api_delete_user(username):
        import sqlite3
        from pathlib import Path

        DB_FILE = Path(__file__).parent / "stock_data.db"
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE username=?', (username,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()

        if affected > 0:
            return jsonify({'success': True, 'message': f'用户 {username} 已删除'})
        else:
            return jsonify({'error': '用户不存在'}), 404

    return app

# 创建 app 实例
app = create_app()

if __name__ == '__main__':
    # 启动后台定时任务
    from scheduler import background_task
    config = load_config()
    interval = config.get("refresh_interval", 60)
    background_task.start(interval=interval)

    print("=" * 50)
    print("A股分时监控服务启动")
    print("=" * 50)
    print("访问 http://localhost:8000 管理自选股")
    print("后台告警任务: 已启动")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)

    app.run(host='0.0.0.0', port=8000, debug=False)
