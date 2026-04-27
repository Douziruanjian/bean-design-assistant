"""
SQLite 数据库管理器

负责数据库连接、表创建、CRUD 操作
"""
import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from .models import Order, Quotation, QuotationItem, Customer, generate_order_no, generate_quotation_no, get_current_datetime


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/bean.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        # 确保 data 目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """建立数据库连接"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def _create_tables(self):
        """创建数据库表"""
        # 工单表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT,
                description TEXT,
                total_amount REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # 报价表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_no TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                items TEXT NOT NULL,
                total_amount REAL DEFAULT 0.0,
                valid_until TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL
            )
        ''')
        
        # 客户表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                notes TEXT,
                total_orders INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
        ''')
        
        # 创建索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_name)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)')
        
        self.conn.commit()
    
    def _generate_order_no(self) -> str:
        """生成唯一工单号"""
        date_str = datetime.now().strftime('%Y%m%d')
        prefix = f"ORD-{date_str}-"
        
        # 查询今天最后一个工单号
        self.cursor.execute('''
            SELECT order_no FROM orders 
            WHERE order_no LIKE ? 
            ORDER BY order_no DESC LIMIT 1
        ''', (prefix + '%',))
        
        row = self.cursor.fetchone()
        if row:
            # 提取序号并加 1
            last_no = row['order_no']
            try:
                seq = int(last_no.split('-')[-1])
                new_seq = seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:03d}"
    
    def _generate_quotation_no(self) -> str:
        """生成唯一报价单号"""
        date_str = datetime.now().strftime('%Y%m%d')
        prefix = f"QUO-{date_str}-"
        
        self.cursor.execute('''
            SELECT quotation_no FROM quotations 
            WHERE quotation_no LIKE ? 
            ORDER BY quotation_no DESC LIMIT 1
        ''', (prefix + '%',))
        
        row = self.cursor.fetchone()
        if row:
            last_no = row['quotation_no']
            try:
                seq = int(last_no.split('-')[-1])
                new_seq = seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:03d}"
    
    # ==================== 工单操作 ====================
    
    def create_order(self, order: Order) -> Order:
        """创建新工单"""
        order_no = self._generate_order_no()
        order.order_no = order_no
        order.created_at = get_current_datetime()
        order.updated_at = get_current_datetime()
        
        self.cursor.execute('''
            INSERT INTO orders (order_no, customer_name, customer_phone, description, 
                               total_amount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (order.order_no, order.customer_name, order.customer_phone, 
              order.description, order.total_amount, order.status, 
              order.created_at, order.updated_at))
        
        self.conn.commit()
        order.id = self.cursor.lastrowid
        return order
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """根据 ID 获取工单"""
        self.cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = self.cursor.fetchone()
        if row:
            return Order(
                id=row['id'],
                order_no=row['order_no'],
                customer_name=row['customer_name'],
                customer_phone=row['customer_phone'],
                description=row['description'],
                total_amount=row['total_amount'],
                status=row['status'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None
    
    def get_orders(self, status: Optional[str] = None, 
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Order]:
        """获取工单列表（可筛选）"""
        query = 'SELECT * FROM orders WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if start_date:
            query += ' AND date(created_at) >= date(?)'
            params.append(start_date)
        
        if end_date:
            query += ' AND date(created_at) <= date(?)'
            params.append(end_date)
        
        query += ' ORDER BY created_at DESC'
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        return [Order(
            id=row['id'],
            order_no=row['order_no'],
            customer_name=row['customer_name'],
            customer_phone=row['customer_phone'],
            description=row['description'],
            total_amount=row['total_amount'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        ) for row in rows]
    
    def update_order(self, order: Order) -> bool:
        """更新工单"""
        order.updated_at = get_current_datetime()
        
        self.cursor.execute('''
            UPDATE orders SET 
                customer_name = ?, customer_phone = ?, description = ?,
                total_amount = ?, status = ?, updated_at = ?
            WHERE id = ?
        ''', (order.customer_name, order.customer_phone, order.description,
              order.total_amount, order.status, order.updated_at, order.id))
        
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_order(self, order_id: int) -> bool:
        """删除工单"""
        self.cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    # ==================== 报价单操作 ====================
    
    def create_quotation(self, quotation: Quotation) -> Quotation:
        """创建新报价单"""
        quotation_no = self._generate_quotation_no()
        quotation.quotation_no = quotation_no
        quotation.created_at = get_current_datetime()
        items_json = quotation.items_to_json()
        
        self.cursor.execute('''
            INSERT INTO quotations (quotation_no, customer_name, items, 
                                   total_amount, valid_until, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (quotation.quotation_no, quotation.customer_name, items_json,
              quotation.total_amount, quotation.valid_until, quotation.status,
              quotation.created_at))
        
        self.conn.commit()
        quotation.id = self.cursor.lastrowid
        return quotation
    
    def get_quotation(self, quotation_id: int) -> Optional[Quotation]:
        """根据 ID 获取报价单"""
        self.cursor.execute('SELECT * FROM quotations WHERE id = ?', (quotation_id,))
        row = self.cursor.fetchone()
        if row:
            quotation = Quotation(
                id=row['id'],
                quotation_no=row['quotation_no'],
                customer_name=row['customer_name'],
                items=Quotation.items_from_json(row['items']),
                total_amount=row['total_amount'],
                valid_until=row['valid_until'],
                status=row['status'],
                created_at=row['created_at']
            )
            return quotation
        return None
    
    def get_quotations(self, status: Optional[str] = None) -> List[Quotation]:
        """获取报价单列表"""
        query = 'SELECT * FROM quotations'
        params = []
        
        if status:
            query += ' WHERE status = ?'
            params.append(status)
        
        query += ' ORDER BY created_at DESC'
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        quotations = []
        for row in rows:
            quotation = Quotation(
                id=row['id'],
                quotation_no=row['quotation_no'],
                customer_name=row['customer_name'],
                items=Quotation.items_from_json(row['items']),
                total_amount=row['total_amount'],
                valid_until=row['valid_until'],
                status=row['status'],
                created_at=row['created_at']
            )
            quotations.append(quotation)
        
        return quotations
    
    def update_quotation(self, quotation: Quotation) -> bool:
        """更新报价单"""
        items_json = quotation.items_to_json()
        
        self.cursor.execute('''
            UPDATE quotations SET 
                customer_name = ?, items = ?, total_amount = ?,
                valid_until = ?, status = ?
            WHERE id = ?
        ''', (quotation.customer_name, items_json, quotation.total_amount,
              quotation.valid_until, quotation.status, quotation.id))
        
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_quotation(self, quotation_id: int) -> bool:
        """删除报价单"""
        self.cursor.execute('DELETE FROM quotations WHERE id = ?', (quotation_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    # ==================== 客户操作 ====================
    
    def create_customer(self, customer: Customer) -> Customer:
        """创建新客户"""
        customer.created_at = get_current_datetime()
        
        self.cursor.execute('''
            INSERT INTO customers (name, phone, address, notes, 
                                  total_orders, total_spent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer.name, customer.phone, customer.address, customer.notes,
              customer.total_orders, customer.total_spent, customer.created_at))
        
        self.conn.commit()
        customer.id = self.cursor.lastrowid
        return customer
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """根据 ID 获取客户"""
        self.cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        row = self.cursor.fetchone()
        if row:
            return Customer(
                id=row['id'],
                name=row['name'],
                phone=row['phone'],
                address=row['address'],
                notes=row['notes'],
                total_orders=row['total_orders'],
                total_spent=row['total_spent'],
                created_at=row['created_at']
            )
        return None
    
    def get_customers(self, search_term: Optional[str] = None) -> List[Customer]:
        """获取客户列表（可搜索）"""
        query = 'SELECT * FROM customers'
        params = []
        
        if search_term:
            query += ' WHERE name LIKE ? OR phone LIKE ?'
            search_pattern = f'%{search_term}%'
            params = [search_pattern, search_pattern]
        
        query += ' ORDER BY name'
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        return [Customer(
            id=row['id'],
            name=row['name'],
            phone=row['phone'],
            address=row['address'],
            notes=row['notes'],
            total_orders=row['total_orders'],
            total_spent=row['total_spent'],
            created_at=row['created_at']
        ) for row in rows]
    
    def update_customer(self, customer: Customer) -> bool:
        """更新客户信息"""
        self.cursor.execute('''
            UPDATE customers SET 
                name = ?, phone = ?, address = ?, notes = ?,
                total_orders = ?, total_spent = ?
            WHERE id = ?
        ''', (customer.name, customer.phone, customer.address, customer.notes,
              customer.total_orders, customer.total_spent, customer.id))
        
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def delete_customer(self, customer_id: int) -> bool:
        """删除客户"""
        self.cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def update_customer_stats(self, customer_id: int):
        """更新客户统计数据（订单数和消费总额）"""
        self.cursor.execute('''
            SELECT COUNT(*) as order_count, COALESCE(SUM(total_amount), 0) as total_spent
            FROM orders 
            WHERE customer_name = (SELECT name FROM customers WHERE id = ?)
            AND status != 'cancelled'
        ''', (customer_id,))
        
        row = self.cursor.fetchone()
        if row:
            self.cursor.execute('''
                UPDATE customers SET 
                    total_orders = ?, total_spent = ?
                WHERE id = ?
            ''', (row['order_count'], row['total_spent'], customer_id))
            self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
