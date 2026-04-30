"""
报价计算模块

提供报价单的创建、计算、管理等功能
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.database.db_manager import DatabaseManager
from app.database.models import Quotation, QuotationItem


class QuotationManager:
    """报价单管理器"""
    
    def __init__(self, db: DatabaseManager):
        """
        初始化
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
    
    def create_quotation(self, customer_name: str, 
                         items: List[Dict[str, Any]],
                         valid_days: int = 7) -> Quotation:
        """
        创建新报价单
        
        Args:
            customer_name: 客户名称
            items: 报价项目列表，每项包含 name, qty, unit_price
            valid_days: 有效天数
            
        Returns:
            Quotation: 创建的报价单对象
        """
        # 计算每个项目的金额和总金额
        quotation_items = []
        total_amount = 0.0
        
        for item_data in items:
            item = QuotationItem(
                name=item_data.get('name', ''),
                qty=item_data.get('qty', 1),
                unit_price=item_data.get('unit_price', 0.0)
            )
            item.amount = item.qty * item.unit_price
            total_amount += item.amount
            quotation_items.append(item)
        
        # 计算有效期
        valid_until = (datetime.now() + timedelta(days=valid_days)).strftime('%Y-%m-%d')
        
        quotation = Quotation(
            customer_name=customer_name,
            items=quotation_items,
            total_amount=total_amount,
            valid_until=valid_until,
            status="draft"
        )
        
        return self.db.create_quotation(quotation)
    
    def get_quotation(self, quotation_id: int) -> Optional[Quotation]:
        """
        获取报价单详情
        
        Args:
            quotation_id: 报价单 ID
            
        Returns:
            Optional[Quotation]: 报价单对象
        """
        return self.db.get_quotation(quotation_id)
    
    def get_all_quotations(self) -> List[Quotation]:
        """
        获取所有报价单
        
        Returns:
            List[Quotation]: 报价单列表
        """
        return self.db.get_quotations()
    
    def get_quotations_by_status(self, status: str) -> List[Quotation]:
        """
        按状态获取报价单
        
        Args:
            status: 报价单状态
            
        Returns:
            List[Quotation]: 报价单列表
        """
        return self.db.get_quotations(status=status)
    
    def add_item(self, quotation_id: int, name: str, qty: int, 
                 unit_price: float) -> bool:
        """
        向报价单添加项目
        
        Args:
            quotation_id: 报价单 ID
            name: 项目名称
            qty: 数量
            unit_price: 单价
            
        Returns:
            bool: 是否成功
        """
        quotation = self.db.get_quotation(quotation_id)
        if not quotation:
            return False
        
        # 添加新项目
        new_item = QuotationItem(
            name=name,
            qty=qty,
            unit_price=unit_price,
            amount=qty * unit_price
        )
        quotation.items.append(new_item)
        
        # 重新计算总金额
        quotation.total_amount = sum(item.amount for item in quotation.items)
        
        return self.db.update_quotation(quotation)
    
    def remove_item(self, quotation_id: int, item_index: int) -> bool:
        """
        从报价单移除项目
        
        Args:
            quotation_id: 报价单 ID
            item_index: 项目索引
            
        Returns:
            bool: 是否成功
        """
        quotation = self.db.get_quotation(quotation_id)
        if not quotation or item_index >= len(quotation.items):
            return False
        
        quotation.items.pop(item_index)
        quotation.total_amount = sum(item.amount for item in quotation.items)
        
        return self.db.update_quotation(quotation)
    
    def update_item(self, quotation_id: int, item_index: int,
                    name: Optional[str] = None, qty: Optional[int] = None,
                    unit_price: Optional[float] = None) -> bool:
        """
        更新报价单项目
        
        Args:
            quotation_id: 报价单 ID
            item_index: 项目索引
            name: 新名称（可选）
            qty: 新数量（可选）
            unit_price: 新单价（可选）
            
        Returns:
            bool: 是否成功
        """
        quotation = self.db.get_quotation(quotation_id)
        if not quotation or item_index >= len(quotation.items):
            return False
        
        item = quotation.items[item_index]
        
        if name is not None:
            item.name = name
        if qty is not None:
            item.qty = qty
        if unit_price is not None:
            item.unit_price = unit_price
        
        # 重新计算金额
        item.amount = item.qty * item.unit_price
        quotation.total_amount = sum(item.amount for item in quotation.items)
        
        return self.db.update_quotation(quotation)
    
    def update_quotation(self, quotation_id: int, **kwargs) -> bool:
        """
        更新报价单
        
        Args:
            quotation_id: 报价单 ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 是否成功
        """
        quotation = self.db.get_quotation(quotation_id)
        if not quotation:
            return False
        
        for key, value in kwargs.items():
            if hasattr(quotation, key):
                setattr(quotation, key, value)
        
        return self.db.update_quotation(quotation)
    
    def confirm_quotation(self, quotation_id: int) -> bool:
        """
        确认报价单
        
        Args:
            quotation_id: 报价单 ID
            
        Returns:
            bool: 是否成功
        """
        return self.update_quotation(quotation_id, status="confirmed")
    
    def expire_quotation(self, quotation_id: int) -> bool:
        """
        使报价单过期
        
        Args:
            quotation_id: 报价单 ID
            
        Returns:
            bool: 是否成功
        """
        return self.update_quotation(quotation_id, status="expired")
    
    def delete_quotation(self, quotation_id: int) -> bool:
        """
        删除报价单
        
        Args:
            quotation_id: 报价单 ID
            
        Returns:
            bool: 是否成功
        """
        return self.db.delete_quotation(quotation_id)
    
    def calculate_total(self, items: List[Dict[str, Any]]) -> float:
        """
        计算报价总金额（不保存）
        
        Args:
            items: 项目列表
            
        Returns:
            float: 总金额
        """
        total = 0.0
        for item_data in items:
            qty = item_data.get('qty', 1)
            unit_price = item_data.get('unit_price', 0.0)
            total += qty * unit_price
        return total
    
    def check_expired(self) -> List[int]:
        """
        检查过期的报价单
        
        Returns:
            List[int]: 过期报价单的 ID 列表
        """
        today = datetime.now().strftime('%Y-%m-%d')
        quotations = self.db.get_quotations(status="draft")
        
        expired_ids = []
        for quotation in quotations:
            if quotation.valid_until and quotation.valid_until < today:
                expired_ids.append(quotation.id)
                self.expire_quotation(quotation.id)
        
        return expired_ids
