"""
工单管理模块

提供工单的创建、查询、编辑、删除等业务逻辑
"""
from typing import List, Optional, Dict, Any

from app.database.db_manager import DatabaseManager
from app.database.models import Order


class OrderManager:
    """工单管理器"""
    
    def __init__(self, db: DatabaseManager):
        """
        初始化
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
    
    def create_order(self, customer_name: str, customer_phone: str,
                     description: str, total_amount: float = 0.0,
                     status: str = "pending") -> Order:
        """
        创建新工单
        
        Args:
            customer_name: 客户名称
            customer_phone: 客户电话
            description: 工单描述
            total_amount: 总金额
            status: 状态
            
        Returns:
            Order: 创建的工单对象
        """
        order = Order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            description=description,
            total_amount=total_amount,
            status=status
        )
        return self.db.create_order(order)
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """
        获取工单详情
        
        Args:
            order_id: 工单 ID
            
        Returns:
            Optional[Order]: 工单对象，不存在返回 None
        """
        return self.db.get_order(order_id)
    
    def get_all_orders(self) -> List[Order]:
        """
        获取所有工单
        
        Returns:
            List[Order]: 工单列表
        """
        return self.db.get_orders()
    
    def get_orders_by_status(self, status: str) -> List[Order]:
        """
        按状态获取工单
        
        Args:
            status: 工单状态
            
        Returns:
            List[Order]: 工单列表
        """
        return self.db.get_orders(status=status)
    
    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Order]:
        """
        按日期范围获取工单
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            List[Order]: 工单列表
        """
        return self.db.get_orders(start_date=start_date, end_date=end_date)
    
    def update_order(self, order_id: int, **kwargs) -> bool:
        """
        更新工单
        
        Args:
            order_id: 工单 ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 是否成功
        """
        order = self.db.get_order(order_id)
        if not order:
            return False
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(order, key):
                setattr(order, key, value)
        
        return self.db.update_order(order)
    
    def delete_order(self, order_id: int) -> bool:
        """
        删除工单
        
        Args:
            order_id: 工单 ID
            
        Returns:
            bool: 是否成功
        """
        return self.db.delete_order(order_id)
    
    def cancel_order(self, order_id: int) -> bool:
        """
        取消工单
        
        Args:
            order_id: 工单 ID
            
        Returns:
            bool: 是否成功
        """
        return self.update_order(order_id, status="cancelled")
    
    def complete_order(self, order_id: int) -> bool:
        """
        完成工单
        
        Args:
            order_id: 工单 ID
            
        Returns:
            bool: 是否成功
        """
        return self.update_order(order_id, status="completed")
    
    def search_orders(self, keyword: str) -> List[Order]:
        """
        搜索工单（按客户名称或工单号）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Order]: 工单列表
        """
        all_orders = self.db.get_orders()
        return [
            order for order in all_orders
            if keyword.lower() in order.customer_name.lower()
            or keyword.lower() in order.order_no.lower()
        ]
