"""
数据库模型定义
"""
import sqlite3
from datetime import datetime
import os

DATABASE_PATH = 'data/activation.db'

def get_db_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 激活码表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activation_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',  -- active, used, expired, revoked
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            max_activations INTEGER DEFAULT 1,
            current_activations INTEGER DEFAULT 0
        )
    ''')
    
    # 设备激活记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activation_code_id INTEGER NOT NULL,
            device_fingerprint TEXT NOT NULL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_trial INTEGER DEFAULT 0,
            trial_end_date TIMESTAMP,
            FOREIGN KEY (activation_code_id) REFERENCES activation_codes(id)
        )
    ''')
    
    # 支付记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            payment_method TEXT NOT NULL,  -- wechat, alipay
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',  -- pending, success, failed, refunded
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            activation_code_id INTEGER,
            FOREIGN KEY (activation_code_id) REFERENCES activation_codes(id)
        )
    ''')
    
    # 试激活记录表（防作弊）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trial_activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_fingerprint TEXT NOT NULL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_fingerprint)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")

if __name__ == '__main__':
    init_db()
