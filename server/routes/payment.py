"""
支付相关 API 接口
"""
from flask import Blueprint, request, jsonify
from services.payment_service import PaymentService

payment_bp = Blueprint('payment', __name__)

# 初始化支付服务（模拟模式）
payment_service = PaymentService(mode='mock')

@payment_bp.route('/create/wechat', methods=['POST'])
def create_wechat_payment():
    """创建微信支付订单"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    amount = data.get('amount')
    product_name = data.get('product_name', '豆子设计助手 - 正式版')
    
    if not amount or amount <= 0:
        return jsonify({'success': False, 'message': '无效金额'}), 400
    
    result = payment_service.create_wechat_payment(amount, product_name)
    
    if result['success']:
        # 创建支付记录
        payment_service.create_payment_record(
            result['order_id'], 
            'wechat', 
            amount
        )
        return jsonify(result)
    else:
        return jsonify(result), 400

@payment_bp.route('/create/alipay', methods=['POST'])
def create_alipay_payment():
    """创建支付宝支付订单"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    amount = data.get('amount')
    product_name = data.get('product_name', '豆子设计助手 - 正式版')
    
    if not amount or amount <= 0:
        return jsonify({'success': False, 'message': '无效金额'}), 400
    
    result = payment_service.create_alipay_payment(amount, product_name)
    
    if result['success']:
        # 创建支付记录
        payment_service.create_payment_record(
            result['order_id'], 
            'alipay', 
            amount
        )
        return jsonify(result)
    else:
        return jsonify(result), 400

@payment_bp.route('/callback', methods=['POST'])
def payment_callback():
    """支付回调处理"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少请求数据'}), 400
    
    order_id = data.get('order_id')
    payment_method = data.get('payment_method')
    
    if not all([order_id, payment_method]):
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    result = payment_service.handle_payment_callback(order_id, payment_method, data)
    return jsonify(result)

@payment_bp.route('/query/<order_id>', methods=['GET'])
def query_payment(order_id):
    """查询支付状态"""
    result = payment_service.query_payment_status(order_id)
    return jsonify(result)

@payment_bp.route('/reconciliation', methods=['GET'])
def daily_reconciliation():
    """每日对账"""
    date = request.args.get('date')  # YYYY-MM-DD
    result = payment_service.daily_reconciliation(date)
    return jsonify(result)
