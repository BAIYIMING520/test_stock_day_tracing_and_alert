"""告警相关 API"""
from flask import Blueprint, jsonify, request

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """获取告警配置"""
    from src.services.config import get_alerts_config
    return jsonify(get_alerts_config())


@alerts_bp.route('/alerts', methods=['POST'])
def save_alerts():
    """保存告警配置"""
    from src.services.config import save_alerts_config
    data = request.get_json()
    save_alerts_config(data)
    return jsonify({'success': True})


@alerts_bp.route('/alerts/history', methods=['GET'])
def get_alert_history():
    """获取告警历史 - 修复导入路径"""
    from src.domain.alert.alert import get_alert_history, clear_alert_history

    action = request.args.get('action')
    if action == 'clear':
        days = int(request.args.get('days', 0))
        clear_alert_history(days)
        return jsonify({'success': True, 'message': '已清空'})

    # 支持查询参数
    days = int(request.args.get('days', 5))
    code = request.args.get('code')
    alert_type = request.args.get('type')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 30))

    result = get_alert_history(days=days, code=code, alert_type=alert_type, page=page, page_size=page_size)
    result['data'] = result.pop('items')
    import math
    result['total_pages'] = math.ceil(result['total'] / page_size) if result['total'] > 0 else 1
    return jsonify(result)
