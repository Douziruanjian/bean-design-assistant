"""
工具函数

提供常用的辅助函数
"""
import os
import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """
    验证电话号码格式
    
    Args:
        phone: 电话号码字符串
        
    Returns:
        bool: 是否有效
    """
    # 简单的手机号验证（11 位数字）
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱字符串
        
    Returns:
        bool: 是否有效
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def format_currency(amount: float) -> str:
    """
    格式化货币金额
    
    Args:
        amount: 金额
        
    Returns:
        str: 格式化后的字符串，如 "¥1,234.56"
    """
    return f"¥{amount:,.2f}"


def ensure_dir(directory: str):
    """
    确保目录存在
    
    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_resource_path(filename: str) -> str:
    """
    获取资源文件路径
    
    Args:
        filename: 文件名
        
    Returns:
        str: 完整的资源文件路径
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'ui', 'resources', filename)


def truncate_text(text: str, max_length: int = 20) -> str:
    """
    截断文本（用于表格显示）
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def parse_order_no(order_no: str) -> Optional[dict]:
    """
    解析工单号
    
    Args:
        order_no: 工单号，格式：ORD-YYYYMMDD-XXX
        
    Returns:
        dict: 包含日期和序号的字典，解析失败返回 None
    """
    pattern = r'^ORD-(\d{4})(\d{2})(\d{2})-(\d{3})$'
    match = re.match(pattern, order_no)
    if match:
        return {
            'year': match.group(1),
            'month': match.group(2),
            'day': match.group(3),
            'sequence': match.group(4)
        }
    return None


def parse_quotation_no(quotation_no: str) -> Optional[dict]:
    """
    解析报价单号
    
    Args:
        quotation_no: 报价单号，格式：QUO-YYYYMMDD-XXX
        
    Returns:
        dict: 包含日期和序号的字典，解析失败返回 None
    """
    pattern = r'^QUO-(\d{4})(\d{2})(\d{2})-(\d{3})$'
    match = re.match(pattern, quotation_no)
    if match:
        return {
            'year': match.group(1),
            'month': match.group(2),
            'day': match.group(3),
            'sequence': match.group(4)
        }
    return None
