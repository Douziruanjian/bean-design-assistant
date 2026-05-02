"""
激活码生成与验证服务
使用 RSA 非对称加密确保激活码安全性
"""
import os
import random
import string
from datetime import datetime, timedelta
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64
import json

class ActivationService:
    def __init__(self, private_key_path='keys/private.pem', public_key_path='keys/public.pem'):
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self.private_key = None
        self.public_key = None
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """加载或生成 RSA 密钥对"""
        os.makedirs(os.path.dirname(self.private_key_path), exist_ok=True)
        
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path):
            # 加载现有密钥
            with open(self.private_key_path, 'rb') as f:
                self.private_key = RSA.import_key(f.read())
            with open(self.public_key_path, 'rb') as f:
                self.public_key = RSA.import_key(f.read())
        else:
            # 生成新密钥对
            self.private_key = RSA.generate(2048)
            self.public_key = self.private_key.publickey()
            
            # 保存密钥
            with open(self.private_key_path, 'wb') as f:
                f.write(self.private_key.export_key())
            with open(self.public_key_path, 'wb') as f:
                f.write(self.public_key.export_key())
            
            # 设置私钥权限（仅所有者可读写）
            os.chmod(self.private_key_path, 0o600)
            print(f"RSA 密钥对已生成：{self.private_key_path}, {self.public_key_path}")
    
    def generate_activation_code(self, days_valid=365, max_activations=1):
        """
        生成激活码
        
        Args:
            days_valid: 有效期（天）
            max_activations: 最大激活次数
        
        Returns:
            dict: 包含激活码和相关信息
        """
        # 生成随机码（15 位，格式：XXXXX-XXXXX-XXXXX）
        code_parts = []
        for _ in range(3):
            part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code_parts.append(part)
        activation_code = '-'.join(code_parts)
        
        # 创建激活码数据
        expires_at = datetime.now() + timedelta(days=days_valid)
        code_data = {
            'code': activation_code,
            'expires_at': expires_at.isoformat(),
            'max_activations': max_activations,
            'created_at': datetime.now().isoformat()
        }
        
        # 使用私钥签名
        signature = self._sign_code(activation_code)
        code_data['signature'] = signature
        
        return code_data
    
    def _sign_code(self, code):
        """使用私钥对激活码签名"""
        h = SHA256.new(code.encode())
        signature = pkcs1_15.new(self.private_key).sign(h)
        return base64.b64encode(signature).decode()
    
    def verify_activation_code(self, code, signature, device_fingerprint):
        """
        验证激活码
        
        Args:
            code: 激活码
            signature: 签名
            device_fingerprint: 设备指纹
        
        Returns:
            dict: 验证结果
        """
        try:
            # 验证签名
            signature_bytes = base64.b64decode(signature)
            h = SHA256.new(code.encode())
            pkcs1_15.new(self.public_key).verify(h, signature_bytes)
            
            # 签名验证通过
            return {
                'valid': True,
                'message': '激活码验证通过'
            }
        except (ValueError, TypeError) as e:
            return {
                'valid': False,
                'message': f'激活码无效：{str(e)}'
            }
    
    def generate_batch_codes(self, count=10, days_valid=365, max_activations=1):
        """批量生成激活码"""
        codes = []
        for _ in range(count):
            code_data = self.generate_activation_code(days_valid, max_activations)
            codes.append(code_data)
        return codes


if __name__ == '__main__':
    # 测试激活码生成
    service = ActivationService()
    
    # 生成单个激活码
    code = service.generate_activation_code(days_valid=365)
    print(f"生成的激活码：{code['code']}")
    print(f"有效期：{code['expires_at']}")
    print(f"签名：{code['signature'][:50]}...")
    
    # 验证激活码
    result = service.verify_activation_code(code['code'], code['signature'], 'test-device-fp')
    print(f"验证结果：{result}")
