"""
报价计算模块

提供报价单的创建、计算、管理、一键转工单等功能
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..database.db_manager import DatabaseManager
from ..database.models import Quotation, QuotationItem, Order, get_current_datetime


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
                         customer_id: Optional[int] = None,
                         valid_days: int = 7) -> Quotation:
        """
        创建新报价单
        
        Args:
            customer_name: 客户名称
            items: 报价项目列表，每项包含 name, qty, unit_price
            customer_id: 关联客户ID
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
        
        valid_until = (datetime.now() + timedelta(days=valid_days)).strftime('%Y-%m-%d')
        
        quotation = Quotation(
            customer_id=customer_id,
            customer_name=customer_name,
            items=quotation_items,
            total_amount=total_amount,
            valid_until=valid_until,
            status="draft"
        )
        
        return self.db.create_quotation(quotation)
    
    def get_quotation(self, quotation_id: int) -> Optional[Quotation]:
        return self.db.get_quotation(quotation_id)
    
    def get_all_quotations(self) -> List[Quotation]:
        return self.db.get_quotations()
    
    def get_quotations_by_status(self, status: str) -> List[Quotation]:
        return self.db.get_quotations(status=status)
    
    def get_quotations_filtered(self, status: Optional[str] = None,
                                 customer_id: Optional[int] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> List[Quotation]:
        """
        多条件筛选报价单
        
        Args:
            status: 状态
            customer_id: 客户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[Quotation]: 报价单列表
        """
        return self.db.get_quotations(
            status=status, customer_id=customer_id,
            start_date=start_date, end_date=end_date
        )
    
    def add_item(self, quotation_id: int, name: str, qty: int, 
                 unit_price: float) -> bool:
        quotation = self.db.get_quotation(quotation_id)
        if not quotation:
            return False
        
        new_item = QuotationItem(
            name=name, qty=qty, unit_price=unit_price, amount=qty * unit_price
        )
        quotation.items.append(new_item)
        quotation.total_amount = sum(item.amount for item in quotation.items)
        return self.db.update_quotation(quotation)
    
    def remove_item(self, quotation_id: int, item_index: int) -> bool:
        quotation = self.db.get_quotation(quotation_id)
        if not quotation or item_index >= len(quotation.items):
            return False
        quotation.items.pop(item_index)
        quotation.total_amount = sum(item.amount for item in quotation.items)
        return self.db.update_quotation(quotation)
    
    def update_item(self, quotation_id: int, item_index: int,
                    name: Optional[str] = None, qty: Optional[int] = None,
                    unit_price: Optional[float] = None) -> bool:
        quotation = self.db.get_quotation(quotation_id)
        if not quotation or item_index >= len(quotation.items):
            return False
        
        item = quotation.items[item_index]
        if name is not None: item.name = name
        if qty is not None: item.qty = qty
        if unit_price is not None: item.unit_price = unit_price
        item.amount = item.qty * item.unit_price
        quotation.total_amount = sum(item.amount for item in quotation.items)
        return self.db.update_quotation(quotation)
    
    def update_quotation(self, quotation_id: int, **kwargs) -> bool:
        quotation = self.db.get_quotation(quotation_id)
        if not quotation:
            return False
        for key, value in kwargs.items():
            if hasattr(quotation, key):
                setattr(quotation, key, value)
        return self.db.update_quotation(quotation)
    
    def update_status(self, quotation_id: int, status: str) -> bool:
        """
        更新报价单状态
        
        Args:
            quotation_id: 报价单 ID
            status: 新状态（draft/sent/confirmed/converted/voided）
            
        Returns:
            bool: 是否成功
        """
        return self.db.update_quotation_status(quotation_id, status)
    
    def convert_to_order(self, quotation_id: int) -> Optional[Order]:
        """
        一键将报价单转为工单（核心功能）
        
        仅"客户确认"(confirmed) 状态的报价单可转工单。
        转工单后自动：
        - 填充客户信息
        - 将报价项目合并为工单描述
        - 填充总金额
        - 标记报价单为"已转工单"
        
        Args:
            quotation_id: 报价单 ID
            
        Returns:
            Optional[Order]: 生成的工单，失败返回 None
        """
        quotation = self.db.get_quotation(quotation_id)
        if not quotation:
            return None
        
        # 仅 "客户确认" 可转工单
        if quotation.status != "confirmed":
            return None
        
        # 构建工单描述（包含报价项目明细）
        desc_lines = [f"[来源报价单: {quotation.quotation_no}]"]
        desc_lines.append("")
        for idx, item in enumerate(quotation.items, 1):
            desc_lines.append(
                f"{idx}. {item.name} × {item.qty} = ¥{item.amount:.2f}"
            )
        description = "\n".join(desc_lines)
        
        # 创建工单对象
        order = Order(
            customer_name=quotation.customer_name,
            customer_phone="",
            description=description,
            total_amount=quotation.total_amount,
            status="pending",
            source_quotation_no=quotation.quotation_no,
            source_type="quotation"
        )
        
        # 获取客户电话
        if quotation.customer_id:
            customer = self.db.get_customer(quotation.customer_id)
            if customer:
                order.customer_phone = customer.phone or ""
        
        # 保存工单
        created_order = self.db.create_order(order)
        if not created_order or not created_order.id:
            return None
        
        # 标记报价单为已转工单
        self.db.mark_quotation_converted(quotation_id, created_order.id)
        
        return created_order
    
    def confirm_quotation(self, quotation_id: int) -> bool:
        return self.update_quotation(quotation_id, status="confirmed")
    
    def void_quotation(self, quotation_id: int) -> bool:
        """作废报价单"""
        return self.update_quotation(quotation_id, status="voided")
    
    def delete_quotation(self, quotation_id: int) -> bool:
        return self.db.delete_quotation(quotation_id)
    
    def calculate_total(self, items: List[Dict[str, Any]]) -> float:
        total = 0.0
        for item_data in items:
            qty = item_data.get('qty', 1)
            unit_price = item_data.get('unit_price', 0.0)
            total += qty * unit_price
        return total
