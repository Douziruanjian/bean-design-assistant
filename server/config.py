"""
豆子设计助手 - 后端服务配置
"""
import os

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bean-design-assistant-secret-key-2026')
    
    # 数据库配置
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'data/activation.db')
    
    # RSA 密钥配置
    RSA_PRIVATE_KEY_PATH = os.environ.get('RSA_PRIVATE_KEY_PATH', 'keys/private.pem')
    RSA_PUBLIC_KEY_PATH = os.environ.get('RSA_PUBLIC_KEY_PATH', 'keys/public.pem')
    
    # 激活码配置
    ACTIVATION_CODE_LENGTH = 15  # 15位激活码
    ACTIVATION_CODE_FORMAT = "XXXXX-XXXXX-XXXXX"  # 格式模板
    
    # 试用期配置
    TRIAL_DAYS = 30
    TRIAL_REMINDER_DAYS = 3  # 到期前3天提醒
    
    # 防作弊配置
    MAX_TRIAL_ACTIVATIONS = 3  # 单设备最多试激活3次
    
    # 支付配置（模拟模式）
    PAYMENT_MODE = os.environ.get('PAYMENT_MODE', 'mock')  # 'mock' or 'real'
    
    # 微信支付配置
    WECHAT_PAY_APPID = os.environ.get('WECHAT_PAY_APPID', '')
    WECHAT_PAY_MCHID = os.environ.get('WECHAT_PAY_MCHID', '')
    WECHAT_PAY_API_KEY = os.environ.get('WECHAT_PAY_API_KEY', '')
    
    # 支付宝配置
    ALIPAY_APPID = os.environ.get('ALIPAY_APPID', '')
    ALIPAY_PRIVATE_KEY = os.environ.get('ALIPAY_PRIVATE_KEY', '')
    ALIPAY_PUBLIC_KEY = os.environ.get('ALIPAY_PUBLIC_KEY', '')
