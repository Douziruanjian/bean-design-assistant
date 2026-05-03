"""
数据模型定义

定义工单、报价、客户的数据模型类
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import json


@dataclass
class Order:
    """工单模型"""
    id: Optional[int] = None
    order_no: str = ""
    customer_name: str = ""
    customer_phone: str = ""
    description: str = ""
    total_amount: float = 0.0
    paid_amount: float = 0.0  # 已收金额
    unpaid_amount: float = 0.0  # 未收金额
    payment_status: str = "unpaid"  # unpaid, partial, paid
    status: str = "pending"  # pending, in_progress, completed, cancelled
    source_quotation_no: str = ""  # 来源报价单号
    source_type: str = "manual"    # 来源类型：manual / quotation
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'description': self.description,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'unpaid_amount': self.unpaid_amount,
            'payment_status': self.payment_status,
            'status': self.status,
            'source_quotation_no': self.source_quotation_no,
            'source_type': self.source_type,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        return cls(**data)


@dataclass
class QuotationItem:
    """报价项目"""
    name: str = ""
    qty: int = 1
    unit_price: float = 0.0
    amount: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'qty': self.qty,
            'unit_price': self.unit_price,
            'amount': self.amount
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'QuotationItem':
        return cls(**data)


@dataclass
class Quotation:
    """报价单模型"""
    id: Optional[int] = None
    quotation_no: str = ""
    customer_id: Optional[int] = None  # 关联客户ID
    customer_name: str = ""
    items: List[QuotationItem] = field(default_factory=list)
    total_amount: float = 0.0
    valid_until: str = ""
    status: str = "draft"  # draft / sent / confirmed / converted / voided
    converted_order_id: Optional[int] = None  # 转工单后的工单ID
    converted_at: str = ""  # 转工单时间
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'quotation_no': self.quotation_no,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'items': [item.to_dict() for item in self.items],
            'total_amount': self.total_amount,
            'valid_until': self.valid_until,
            'status': self.status,
            'converted_order_id': self.converted_order_id,
            'converted_at': self.converted_at,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Quotation':
        items = [QuotationItem.from_dict(item) for item in data.get('items', [])]
        return cls(
            id=data.get('id'),
            quotation_no=data.get('quotation_no', ''),
            customer_id=data.get('customer_id'),
            customer_name=data.get('customer_name', ''),
            items=items,
            total_amount=data.get('total_amount', 0.0),
            valid_until=data.get('valid_until', ''),
            status=data.get('status', 'draft'),
            converted_order_id=data.get('converted_order_id'),
            converted_at=data.get('converted_at', ''),
            created_at=data.get('created_at', '')
        )
    
    def items_to_json(self) -> str:
        """将 items 转换为 JSON 字符串存储"""
        return json.dumps([item.to_dict() for item in self.items])
    
    @classmethod
    def items_from_json(cls, json_str: str) -> List[QuotationItem]:
        """从 JSON 字符串解析 items"""
        if not json_str:
            return []
        data = json.loads(json_str)
        return [QuotationItem.from_dict(item) for item in data]


@dataclass
class Customer:
    """客户模型"""
    id: Optional[int] = None
    name: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""
    total_orders: int = 0
    total_spent: float = 0.0
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            'notes': self.notes,
            'total_orders': self.total_orders,
            'total_spent': self.total_spent,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Customer':
        return cls(**data)


def generate_order_no() -> str:
    """生成工单号：ORD-YYYYMMDD-XXX"""
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    # XXX 部分由数据库自增 ID 生成，这里只生成前缀
    return f"ORD-{date_str}"


def generate_quotation_no() -> str:
    """生成报价单号：QUO-YYYYMMDD-XXX"""
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    return f"QUO-{date_str}"


def get_current_datetime() -> str:
    """获取当前日期时间字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_current_date() -> str:
    """获取当前日期字符串"""
    return datetime.now().strftime('%Y-%m-%d')


@dataclass
class PaymentRecord:
    """付款记录模型"""
    id: Optional[int] = None
    order_id: int = 0
    order_no: str = ""
    customer_name: str = ""
    amount: float = 0.0
    payment_method: str = "cash"  # cash, wechat, alipay, bank
    payment_type: str = "deposit"  # deposit, final, advance
    remark: str = ""
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_type': self.payment_type,
            'remark': self.remark,
            'created_at': self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PaymentRecord':
        return cls(**data)


# ══════════════════════════════════════════════
# 报价单状态常量
# ══════════════════════════════════════════════

QUOTATION_STATUS = {
    "draft": "草稿",
    "sent": "已发给客户",
    "confirmed": "客户确认",
    "converted": "已转工单",
    "voided": "作废",
}

QUOTATION_STATUS_REVERSE = {v: k for k, v in QUOTATION_STATUS.items()}


# ══════════════════════════════════════════════
# 支付方式/类型常量
# ══════════════════════════════════════════════

PAYMENT_METHODS = ["现金", "微信", "支付宝", "银行卡"]
PAYMENT_TYPES = ["定金", "尾款", "预付款"]
