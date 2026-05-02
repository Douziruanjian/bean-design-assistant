"""
支付服务
支持微信支付、支付宝支付（模拟模式 + 真实接口框架）
"""
import uuid
import random
from datetime import datetime
from models.db_models import get_db_connection

class PaymentService:
    def __init__(self, mode='mock'):
        """
        初始化支付服务
        
        Args:
            mode: 'mock' 模拟模式，'real' 真实模式
        """
        self.mode = mode
    
    def create_wechat_payment(self, amount, product_name="豆子设计助手 - 正式版"):
        """
        创建微信支付订单（Native 扫码）
        
        Args:
            amount: 支付金额（元）
            product_name: 商品名称
        
        Returns:
            dict: 支付信息
        """
        order_id = self._generate_order_id()
        
        if self.mode == 'mock':
            # 模拟模式：返回模拟的二维码数据
            return {
                'success': True,
                'order_id': order_id,
                'payment_method': 'wechat',
                'amount': amount,
                'mode': 'mock',
                'code_url': f'mock_wechat://{order_id}',  # 模拟的二维码内容
                'message': '模拟支付模式 - 扫码后自动完成支付',
                'expires_in': 900  # 15 分钟过期
            }
        else:
            # 真实模式：调用微信支付 API
            return self._create_real_wechat_payment(order_id, amount, product_name)
    
    def create_alipay_payment(self, amount, product_name="豆子设计助手 - 正式版"):
        """
        创建支付宝支付订单（Native 扫码）
        
        Args:
            amount: 支付金额（元）
            product_name: 商品名称
        
        Returns:
            dict: 支付信息
        """
        order_id = self._generate_order_id()
        
        if self.mode == 'mock':
            # 模拟模式
            return {
                'success': True,
                'order_id': order_id,
                'payment_method': 'alipay',
                'amount': amount,
                'mode': 'mock',
                'qr_code': f'mock_alipay://{order_id}',  # 模拟的二维码内容
                'message': '模拟支付模式 - 扫码后自动完成支付',
                'expires_in': 900
            }
        else:
            # 真实模式：调用支付宝 API
            return self._create_real_alipay_payment(order_id, amount, product_name)
    
    def _generate_order_id(self):
        """生成订单号"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"BEAN{timestamp}{unique_id}"
    
    def _create_real_wechat_payment(self, order_id, amount, product_name):
        """
        真实微信支付实现（框架）
        需要配置：WECHAT_PAY_APPID, WECHAT_PAY_MCHID, WECHAT_PAY_API_KEY
        """
        # TODO: 实现真实的微信支付 API 调用
        # 参考文档：https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_1.shtml
        return {
            'success': False,
            'message': '真实微信支付尚未配置',
            'order_id': order_id
        }
    
    def _create_real_alipay_payment(self, order_id, amount, product_name):
        """
        真实支付宝支付实现（框架）
        需要配置：ALIPAY_APPID, ALIPAY_PRIVATE_KEY, ALIPAY_PUBLIC_KEY
        """
        # TODO: 实现真实的支付宝支付 API 调用
        # 参考文档：https://opendocs.alipay.com/open/026b65
        return {
            'success': False,
            'message': '真实支付宝支付尚未配置',
            'order_id': order_id
        }
    
    def handle_payment_callback(self, order_id, payment_method, callback_data):
        """
        处理支付回调
        
        Args:
            order_id: 订单号
            payment_method: 支付方式（wechat/alipay）
            callback_data: 回调数据
        
        Returns:
            dict: 处理结果
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询订单
            cursor.execute(
                'SELECT id, status FROM payment_records WHERE order_id = ?',
                (order_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {'success': False, 'message': '订单不存在'}
            
            record_id, status = row
            
            if status == 'success':
                return {'success': True, 'message': '订单已处理'}
            
            # 验证回调签名（真实模式下需要）
            if self.mode == 'mock':
                # 模拟模式：直接标记为成功
                payment_success = True
            else:
                # 真实模式：验证签名
                payment_success = self._verify_callback_signature(
                    payment_method, callback_data
                )
            
            if payment_success:
                # 更新订单状态
                cursor.execute(
                    '''UPDATE payment_records 
                       SET status = 'success', paid_at = ?
                       WHERE order_id = ?''',
                    (datetime.now().isoformat(), order_id)
                )
                
                # 生成激活码（关联到订单）
                # TODO: 调用 activation_service 生成激活码并关联
                
                conn.commit()
                return {'success': True, 'message': '支付成功'}
            else:
                return {'success': False, 'message': '支付验证失败'}
        
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'处理失败：{str(e)}'}
        
        finally:
            conn.close()
    
    def _verify_callback_signature(self, payment_method, callback_data):
        """验证支付回调签名"""
        # TODO: 实现微信/支付宝的签名验证
        return True
    
    def query_payment_status(self, order_id):
        """
        查询支付状态（主动查询机制）
        
        Args:
            order_id: 订单号
        
        Returns:
            dict: 支付状态
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                '''SELECT order_id, payment_method, amount, status, paid_at
                   FROM payment_records WHERE order_id = ?''',
                (order_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {'success': False, 'message': '订单不存在'}
            
            order_id, payment_method, amount, status, paid_at = row
            
            return {
                'success': True,
                'order_id': order_id,
                'payment_method': payment_method,
                'amount': amount,
                'status': status,
                'paid_at': paid_at
            }
        
        finally:
            conn.close()
    
    def create_payment_record(self, order_id, payment_method, amount):
        """创建支付记录"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                '''INSERT INTO payment_records (order_id, payment_method, amount)
                   VALUES (?, ?, ?)''',
                (order_id, payment_method, amount)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"创建支付记录失败：{e}")
            return False
        finally:
            conn.close()
    
    def daily_reconciliation(self, date=None):
        """
        每日对账
        
        Args:
            date: 对账日期（YYYY-MM-DD），默认昨天
        """
        if date is None:
            from datetime import timedelta
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询当天的支付记录
            cursor.execute(
                '''SELECT payment_method, COUNT(*), SUM(amount)
                   FROM payment_records
                   WHERE DATE(created_at) = ? AND status = 'success'
                   GROUP BY payment_method''',
                (date,)
            )
            records = cursor.fetchall()
            
            reconciliation = {
                'date': date,
                'total_amount': 0,
                'by_method': []
            }
            
            for method, count, amount in records:
                amount = amount or 0
                reconciliation['by_method'].append({
                    'payment_method': method,
                    'count': count,
                    'amount': amount
                })
                reconciliation['total_amount'] += amount
            
            return {
                'success': True,
                'reconciliation': reconciliation
            }
        
        finally:
            conn.close()


if __name__ == '__main__':
    # 测试
    service = PaymentService(mode='mock')
    
    # 创建微信支付订单
    result = service.create_wechat_payment(amount=99.0)
    print(f"微信支付订单：{result}")
    
    # 创建支付宝支付订单
    result = service.create_alipay_payment(amount=99.0)
    print(f"支付宝订单：{result}")
