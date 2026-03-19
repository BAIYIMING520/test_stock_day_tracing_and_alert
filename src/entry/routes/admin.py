"""用户管理 API"""
from flask import Blueprint, jsonify, request
import hashlib
from datetime import datetime
from .auth import load_users, save_users, require_auth, require_admin

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@require_admin
def get_users():
    """获取用户列表"""
    users = load_users()
    result = []
    for username, info in users.items():
        result.append({
            'username': username,
            'role': info.get('role', 'user'),
            'created_at': info.get('created_at', '')
        })
    return jsonify(result)


@admin_bp.route('/users', methods=['POST'])
@require_admin
def create_user():
    """创建用户"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'})

    users = load_users()
    if username in users:
        return jsonify({'success': False, 'error': '用户已存在'})

    users[username] = {
        'password': hashlib.sha256(password.encode()).hexdigest(),
        'role': role,
        'created_at': datetime.now().isoformat()
    }
    save_users(users)
    return jsonify({'success': True, 'message': '创建成功'})


@admin_bp.route('/users/<username>', methods=['PUT'])
@require_admin
def update_user(username):
    """更新用户"""
    data = request.get_json()
    password = data.get('password')
    role = data.get('role')

    users = load_users()
    if username not in users:
        return jsonify({'success': False, 'error': '用户不存在'})

    if password:
        users[username]['password'] = hashlib.sha256(password.encode()).hexdigest()
    if role:
        users[username]['role'] = role

    save_users(users)
    return jsonify({'success': True, 'message': '更新成功'})


@admin_bp.route('/users/<username>', methods=['DELETE'])
@require_admin
def delete_user(username):
    """删除用户"""
    users = load_users()
    if username not in users:
        return jsonify({'success': False, 'error': '用户不存在'})
    if username == 'admin':
        return jsonify({'success': False, 'error': '不能删除管理员'})

    del users[username]
    save_users(users)
    return jsonify({'success': True, 'message': '删除成功'})
