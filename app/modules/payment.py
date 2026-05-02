"""
收款记录管理模块

提供收款记录的创建、查询、删除，以及工单收款状态的自动计算。
"""
from typing import List, Optional

from ..database.db_manager import DatabaseManager
from ..database.models import PaymentRecord, PAYMENT_METHODS, PAYMENT_TYPES


class PaymentManager:
    """收款记录管理器"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def record_payment(self, order_id: int, order_no: str,
                       customer_name: str, amount: float,
                       payment_method: str = "微信",
                       payment_type: str = "尾款",
                       remark: str = "") -> Optional[PaymentRecord]:
        """
        记录收款并自动更新工单状态
        
        Args:
            order_id: 工单ID
            order_no: 工单号
            customer_name: 客户名称
            amount: 收款金额
            payment_method: 支付方式
            payment_type: 收款类型
            remark: 备注
            
        Returns:
            Optional[PaymentRecord]: 收款记录
        """
        if amount <= 0:
            return None
        
        record = PaymentRecord(
            order_id=order_id,
            order_no=order_no,
            customer_name=customer_name,
            amount=amount,
            payment_method=payment_method,
            payment_type=payment_type,
            remark=remark
        )
        
        result = self.db.create_payment(record)
        
        # 更新客户统计
        self.db.update_customer_stats_by_name(customer_name)
        
        return result
    
    def get_payments_by_order(self, order_id: int) -> List[PaymentRecord]:
        """获取工单的所有收款记录"""
        return self.db.get_payments_by_order(order_id)
    
    def get_all_payments(self, start_date: str = None,
                          end_date: str = None) -> List[PaymentRecord]:
        """获取所有收款记录"""
        return self.db.get_all_payments(start_date, end_date)
    
    def delete_payment(self, payment_id: int, customer_name: str) -> bool:
        """删除收款记录"""
        result = self.db.delete_payment(payment_id)
        if result:
            self.db.update_customer_stats_by_name(customer_name)
        return result
    
    @staticmethod
    def get_payment_methods() -> list:
        return PAYMENT_METHODS.copy()
    
    @staticmethod
    def get_payment_types() -> list:
        return PAYMENT_TYPES.copy()
