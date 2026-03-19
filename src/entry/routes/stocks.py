"""股票相关 API"""
from flask import Blueprint, jsonify, request
from src.services.config import add_stock, remove_stock, get_stocks
from src.infrastructure.client import get_all_realtime
from src.infrastructure.database import get_minute_data

stocks_bp = Blueprint('stocks', __name__)


@stocks_bp.route('/stocks', methods=['GET'])
def get_stocks_list():
    """获取自选股列表"""
    return jsonify(get_stocks())


@stocks_bp.route('/stocks', methods=['POST'])
def add_stock_code():
    """添加股票"""
    data = request.get_json()
    code = data.get('code', '')
    if not code:
        return jsonify({'success': False, 'error': '股票代码不能为空'})
    add_stock(code)
    return jsonify({'success': True, 'message': '添加成功'})


@stocks_bp.route('/stocks/<code>', methods=['DELETE'])
def delete_stock(code):
    """删除股票"""
    remove_stock(code)
    return jsonify({'success': True, 'message': '删除成功'})


@stocks_bp.route('/realtime', methods=['GET'])
def get_realtime_data():
    """获取实时行情"""
    codes = get_stocks()
    results = get_all_realtime(codes)
    return jsonify(results)


@stocks_bp.route('/minute/<code>', methods=['GET'])
def get_minute_data_api(code):
    """获取分时数据"""
    data = get_minute_data(code)
    return jsonify(data)
