"""
激活码相关 API 接口
"""
from flask import Blueprint, request, jsonify
from services.activation_service import ActivationService
from services.license_service import LicenseService
from models.db_models import init_db, get_db_connection
from datetime import datetime

activation_bp = Blueprint('activation', __name__)

# 初始化服务
activation_service = ActivationService()
license_service = LicenseService()

# 确保数据库已初始化
init_db()

@activation_bp.route('/generate', methods=['POST'])
def generate_code():
    """生成激活码"""
    data = request.get_json() or {}
    days_valid = data.get('days_valid', 365)
    max_activations = data.get('max_activations', 1)
    
    code_data = activation_service.generate_activation_code(days_valid, max_activations)
    
    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''INSERT INTO activation_codes (code, expires_at, max_activations)
               VALUES (?, ?, ?)''',
            (code_data['code'], code_data['expires_at'], max_activations)
        )
        conn.commit()
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'data': code_data
    })

@activation_bp.route('/generate/batch', methods=['POST'])
def generate_batch_codes():
    """批量生成激活码"""
    data = request.get_json() or {}
    count = data.get('count', 10)
    days_valid = data.get('days_valid', 365)
    max_activations = data.get('max_activations', 1)
    
    codes = activation_service.generate_batch_codes(count, days_valid, max_activations)
    
    # 批量保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for code_data in codes:
            cursor.execute(
                '''INSERT INTO activation_codes (code, expires_at, max_activations)
                   VALUES (?, ?, ?)''',
                (code_data['code'], code_data['expires_at'], max_activations)
            )
        conn.commit()
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'count': len(codes),
        'data': codes
    })

@activation_bp.route('/verify', methods=['POST'])
def verify_code():
    """验证激活码"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    code = data.get('code')
    signature = data.get('signature')
    device_fingerprint = data.get('device_fingerprint')
    
    if not all([code, signature, device_fingerprint]):
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    # 验证签名
    verify_result = activation_service.verify_activation_code(code, signature, device_fingerprint)
    
    if not verify_result['valid']:
        return jsonify(verify_result), 400
    
    return jsonify({
        'success': True,
        'message': '激活码签名验证通过'
    })

@activation_bp.route('/activate', methods=['POST'])
def activate():
    """激活设备"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    code = data.get('code')
    device_fingerprint = data.get('device_fingerprint')
    is_trial = data.get('is_trial', False)
    
    if not all([code, device_fingerprint]):
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    result = license_service.activate_device(code, device_fingerprint, is_trial)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@activation_bp.route('/status', methods=['POST'])
def check_status():
    """检查许可证状态"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    device_fingerprint = data.get('device_fingerprint')
    if not device_fingerprint:
        return jsonify({'success': False, 'message': '缺少设备指纹'}), 400
    
    status = license_service.check_license_status(device_fingerprint)
    return jsonify({
        'success': True,
        'data': status
    })

@activation_bp.route('/trial', methods=['POST'])
def get_trial_info():
    """获取试用信息"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    device_fingerprint = data.get('device_fingerprint')
    if not device_fingerprint:
        return jsonify({'success': False, 'message': '缺少设备指纹'}), 400
    
    trial_info = license_service.get_trial_info(device_fingerprint)
    return jsonify({
        'success': True,
        'data': trial_info
    })
