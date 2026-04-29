"""
客户端激活逻辑
处理激活码验证、设备绑定、激活状态持久化
"""
import os
import json
import base64
import requests
from datetime import datetime
from cryptography.fernet import Fernet
from .hardware_fingerprint import HardwareFingerprint

class ActivationClient:
    def __init__(self, server_url='http://localhost:5000'):
        """
        初始化激活客户端
        
        Args:
            server_url: 后端服务器地址
        """
        self.server_url = server_url
        self.hw_fingerprint = HardwareFingerprint()
        self.activation_file = self._get_activation_file_path()
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_activation_file_path(self):
        """获取激活文件路径"""
        # Windows: %APPDATA%/BeanDesignAssistant/activation.dat
        # macOS: ~/Library/Application Support/BeanDesignAssistant/activation.dat
        # Linux: ~/.config/BeanDesignAssistant/activation.dat
        
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            base_dir = os.path.join(appdata, 'BeanDesignAssistant')
        elif os.name == 'posix':
            if platform.system() == 'Darwin':  # macOS
                base_dir = os.path.expanduser('~/Library/Application Support/BeanDesignAssistant')
            else:  # Linux
                base_dir = os.path.expanduser('~/.config/BeanDesignAssistant')
        else:
            base_dir = os.getcwd()
        
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, 'activation.dat')
    
    def _get_or_create_encryption_key(self):
        """获取或创建加密密钥"""
        key_file = self.activation_file.replace('.dat', '.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限（仅所有者可读写）
            os.chmod(key_file, 0o600)
            return key
    
    def activate(self, activation_code, is_trial=False):
        """
        激活设备
        
        Args:
            activation_code: 激活码
            is_trial: 是否为试用激活
        
        Returns:
            dict: 激活结果
        """
        # 获取设备指纹
        device_fingerprint = self.hw_fingerprint.get_fingerprint()
        
        # 检查是否在虚拟机中
        if self.hw_fingerprint.is_virtual_machine():
            return {
                'success': False,
                'message': '检测到虚拟机环境，不支持在虚拟机中激活'
            }
        
        # 调用后端 API
        api_url = f'{self.server_url}/api/activation/activate'
        payload = {
            'code': activation_code,
            'device_fingerprint': device_fingerprint,
            'is_trial': is_trial
        }
        
        try:
            response = requests.post(api_url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('success'):
                # 保存激活状态
                self._save_activation_status(result)
                return {
                    'success': True,
                    'message': '激活成功',
                    'is_trial': is_trial,
                    'trial_end_date': result.get('trial_end_date')
                }
            else:
                return result
        
        except requests.exceptions.RequestException as e:
            # 网络错误时，支持离线激活（如果有本地激活码）
            return {
                'success': False,
                'message': f'网络连接失败：{str(e)}',
                'offline_mode': True
            }
    
    def start_trial(self):
        """
        开始试用（30 天无限体验）
        
        Returns:
            dict: 试用结果
        """
        # 使用特殊的试用激活码
        TRIAL_CODE = 'TRIAL-30DAYS-2026'
        
        return self.activate(TRIAL_CODE, is_trial=True)
    
    def check_status(self):
        """
        检查激活状态
        
        Returns:
            dict: 激活状态
        """
        # 首先检查本地缓存
        local_status = self._load_activation_status()
        if local_status:
            # 验证文件完整性
            if self._verify_activation_file(local_status):
                return local_status
        
        # 本地缓存无效，查询服务器
        device_fingerprint = self.hw_fingerprint.get_fingerprint()
        api_url = f'{self.server_url}/api/activation/status'
        
        try:
            response = requests.post(api_url, json={
                'device_fingerprint': device_fingerprint
            }, timeout=10)
            
            result = response.json()
            if result.get('success'):
                status = result.get('data', {})
                # 更新本地缓存
                self._save_activation_status({
                    'activated': status.get('activated', False),
                    'is_trial': status.get('is_trial', False),
                    'trial_end_date': status.get('trial_end_date'),
                    'license_code': status.get('license_code'),
                    'expires_at': status.get('expires_at'),
                    'days_remaining': status.get('days_remaining'),
                    'should_remind': status.get('should_remind', False)
                })
                return status
        
        except requests.exceptions.RequestException:
            # 网络错误时返回本地状态
            if local_status:
                return local_status
        
        return {
            'activated': False,
            'can_trial': True,
            'message': '设备未激活'
        }
    
    def _save_activation_status(self, status_data):
        """保存激活状态到加密文件"""
        try:
            # 添加时间戳用于完整性校验
            status_data['_timestamp'] = datetime.now().isoformat()
            status_data['_checksum'] = self._calculate_checksum(status_data)
            
            # 加密并保存
            json_data = json.dumps(status_data).encode()
            encrypted_data = self.cipher.encrypt(json_data)
            
            with open(self.activation_file, 'wb') as f:
                f.write(encrypted_data)
        
        except Exception as e:
            print(f"保存激活状态失败：{e}")
    
    def _load_activation_status(self):
        """从加密文件加载激活状态"""
        try:
            if not os.path.exists(self.activation_file):
                return None
            
            with open(self.activation_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            status_data = json.loads(decrypted_data)
            
            return status_data
        
        except Exception as e:
            print(f"加载激活状态失败：{e}")
            return None
    
    def _verify_activation_file(self, status_data):
        """验证激活文件完整性（防篡改）"""
        if '_checksum' not in status_data:
            return False
        
        stored_checksum = status_data.pop('_checksum')
        calculated_checksum = self._calculate_checksum(status_data)
        
        return stored_checksum == calculated_checksum
    
    def _calculate_checksum(self, data):
        """计算数据校验和"""
        # 排除校验和字段本身
        data_copy = {k: v for k, v in data.items() if k != '_checksum'}
        json_str = json.dumps(data_copy, sort_keys=True)
        return base64.b64encode(
            hashlib.sha256(json_str.encode()).digest()
        ).decode()
    
    def get_trial_info(self):
        """获取试用信息"""
        device_fingerprint = self.hw_fingerprint.get_fingerprint()
        api_url = f'{self.server_url}/api/activation/trial'
        
        try:
            response = requests.post(api_url, json={
                'device_fingerprint': device_fingerprint
            }, timeout=10)
            
            result = response.json()
            if result.get('success'):
                return result.get('data', {})
        
        except requests.exceptions.RequestException:
            pass
        
        return {
            'trial_count': 0,
            'max_trials': 3,
            'can_trial': True,
            'trial_days': 30
        }
    
    def is_activated(self):
        """检查是否已激活"""
        status = self.check_status()
        return status.get('activated', False) and not status.get('expired', False)
    
    def is_trial_expired(self):
        """检查试用是否过期"""
        status = self.check_status()
        return status.get('expired', False) and status.get('expired_type') == 'trial'
    
    def get_days_remaining(self):
        """获取剩余天数（试用期或许可证）"""
        status = self.check_status()
        return status.get('days_remaining', 0)
    
    def should_show_reminder(self):
        """是否应该显示到期提醒"""
        status = self.check_status()
        return status.get('should_remind', False)


# 需要导入 hashlib 和 platform
import hashlib
import platform

if __name__ == '__main__':
    # 测试
    client = ActivationClient()
    
    # 检查状态
    status = client.check_status()
    print(f"激活状态：{status}")
    
    # 获取试用信息
    trial_info = client.get_trial_info()
    print(f"试用信息：{trial_info}")
