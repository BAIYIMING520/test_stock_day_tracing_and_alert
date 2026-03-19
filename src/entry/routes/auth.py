"""认证相关 API"""
from flask import Blueprint, jsonify, request
import hashlib
import jwt
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

auth_bp = Blueprint('auth', __name__)

BASE_DIR = Path(__file__).parent.parent.parent
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRE_DAYS = 7
USERS_FILE = BASE_DIR / 'users.json'


def load_users():
    """加载用户数据"""
    import json
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    default_users = {
        "admin": {
            "password": hashlib.sha256("admin123".encode()).hexdigest(),
            "role": "admin",
            "created_at": datetime.now().isoformat()
        }
    }
    with open(USERS_FILE, 'w') as f:
        json.dump(default_users, f, indent=2, ensure_ascii=False)
    return default_users


def save_users(users):
    """保存用户数据"""
    import json
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def require_auth(f):
    """鉴权装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': '未登录'}), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '登录已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效 token'}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """管理员权限装饰器"""
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            return jsonify({'error': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/login', methods=['POST'])
def login():
    """登录"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    users = load_users()
    user = users.get(username)

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'})

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != user['password']:
        return jsonify({'success': False, 'error': '密码错误'})

    # 生成 token
    expire = datetime.now() + timedelta(days=JWT_EXPIRE_DAYS)
    token = jwt.encode({
        'username': username,
        'role': user.get('role', 'user'),
        'exp': expire
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return jsonify({
        'success': True,
        'token': token,
        'username': username,
        'role': user.get('role', 'user')
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """登出"""
    return jsonify({'success': True})


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """获取当前用户信息"""
    return jsonify({
        'username': request.user.get('username'),
        'role': request.user.get('role')
    })
