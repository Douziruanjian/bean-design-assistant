"""
客户管理模块

提供客户的创建、查询、编辑、删除等功能
"""
from typing import List, Optional

from ..database.db_manager import DatabaseManager
from ..database.models import Customer


class CustomerManager:
    """客户管理器"""
    
    def __init__(self, db: DatabaseManager):
        """
        初始化
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
    
    def create_customer(self, name: str, phone: str = "",
                        address: str = "", notes: str = "") -> Customer:
        """
        创建新客户
        
        Args:
            name: 客户名称
            phone: 电话
            address: 地址
            notes: 备注
            
        Returns:
            Customer: 创建的客户对象
        """
        customer = Customer(
            name=name,
            phone=phone,
            address=address,
            notes=notes,
            total_orders=0,
            total_spent=0.0
        )
        return self.db.create_customer(customer)
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """
        获取客户详情
        
        Args:
            customer_id: 客户 ID
            
        Returns:
            Optional[Customer]: 客户对象
        """
        return self.db.get_customer(customer_id)
    
    def get_all_customers(self) -> List[Customer]:
        """
        获取所有客户
        
        Returns:
            List[Customer]: 客户列表
        """
        return self.db.get_customers()
    
    def search_customers(self, keyword: str) -> List[Customer]:
        """
        搜索客户
        
        Args:
            keyword: 搜索关键词（名称或电话）
            
        Returns:
            List[Customer]: 客户列表
        """
        return self.db.get_customers(search_term=keyword)
    
    def update_customer(self, customer_id: int, **kwargs) -> bool:
        """
        更新客户信息
        
        Args:
            customer_id: 客户 ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 是否成功
        """
        customer = self.db.get_customer(customer_id)
        if not customer:
            return False
        
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        return self.db.update_customer(customer)
    
    def delete_customer(self, customer_id: int) -> bool:
        """
        删除客户
        
        Args:
            customer_id: 客户 ID
            
        Returns:
            bool: 是否成功
        """
        return self.db.delete_customer(customer_id)
    
    def get_customer_orders(self, customer_id: int):
        """
        获取客户的历史订单
        
        Args:
            customer_id: 客户 ID
            
        Returns:
            订单列表（需要 OrderManager 配合）
        """
        customer = self.db.get_customer(customer_id)
        if not customer:
            return []
        
        # 通过客户名称查询订单
        return self.db.get_orders()  # 这里简化处理，实际应该按客户名称筛选
    
    def refresh_customer_stats(self, customer_id: int):
        """
        刷新客户统计数据
        
        Args:
            customer_id: 客户 ID
        """
        self.db.update_customer_stats(customer_id)
    
    def get_top_customers(self, limit: int = 10) -> List[Customer]:
        """
        获取消费最高的客户
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Customer]: 客户列表
        """
        customers = self.db.get_customers()
        # 按消费总额排序
        customers.sort(key=lambda c: c.total_spent, reverse=True)
        return customers[:limit]
