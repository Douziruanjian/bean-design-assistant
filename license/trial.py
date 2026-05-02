"""
试用期管理模块
管理 30 天试用、到期提醒、试用转正式
"""
from datetime import datetime, timedelta
from .activation import ActivationClient

class TrialManager:
    def __init__(self, server_url='http://localhost:5000'):
        """
        初始化试用管理器
        
        Args:
            server_url: 后端服务器地址
        """
        self.activation_client = ActivationClient(server_url)
        self.trial_days = 30
        self.reminder_days = 3  # 到期前 3 天提醒
    
    def start_trial(self):
        """
        开始试用
        
        Returns:
            dict: 试用启动结果
        """
        # 检查是否已经激活
        status = self.activation_client.check_status()
        
        if status.get('activated'):
            if status.get('is_trial'):
                return {
                    'success': False,
                    'message': '已在试用中',
                    'trial_end_date': status.get('trial_end_date'),
                    'days_remaining': status.get('days_remaining')
                }
            else:
                return {
                    'success': False,
                    'message': '已激活正式版，无需试用'
                }
        
        # 检查是否还有试用机会
        trial_info = self.activation_client.get_trial_info()
        if not trial_info.get('can_trial'):
            return {
                'success': False,
                'message': f'试用次数已达上限（{trial_info.get("max_trials", 3)}次）',
                'trial_count': trial_info.get('trial_count')
            }
        
        # 开始试用
        result = self.activation_client.start_trial()
        
        if result.get('success'):
            return {
                'success': True,
                'message': '试用已启动',
                'trial_end_date': result.get('trial_end_date'),
                'trial_days': self.trial_days
            }
        else:
            return result
    
    def check_trial_status(self):
        """
        检查试用状态
        
        Returns:
            dict: 试用状态
        """
        status = self.activation_client.check_status()
        
        if not status.get('activated'):
            return {
                'activated': False,
                'can_start_trial': True,
                'message': '尚未开始试用'
            }
        
        if not status.get('is_trial'):
            return {
                'activated': True,
                'is_trial': False,
                'message': '正式版用户'
            }
        
        if status.get('expired'):
            return {
                'activated': True,
                'is_trial': True,
                'expired': True,
                'expired_date': status.get('expired_date'),
                'message': '试用期已结束'
            }
        
        days_remaining = status.get('days_remaining', 0)
        should_remind = days_remaining <= self.reminder_days
        
        return {
            'activated': True,
            'is_trial': True,
            'expired': False,
            'days_remaining': days_remaining,
            'trial_end_date': status.get('trial_end_date'),
            'should_remind': should_remind,
            'message': f'试用剩余 {days_remaining} 天'
        }
    
    def get_reminder_message(self):
        """
        获取试用到期提醒消息
        
        Returns:
            str: 提醒消息
        """
        status = self.check_trial_status()
        
        if not status.get('should_remind'):
            return None
        
        days = status.get('days_remaining', 0)
        
        if days == 0:
            return "⚠️ 试用期将于今天到期，请及时购买正式版！"
        elif days == 1:
            return "⚠️ 试用期将于明天到期，请及时购买正式版！"
        else:
            return f"⚠️ 试用期将于 {days} 天后到期，请及时购买正式版！"
    
    def should_show_trial_dialog(self):
        """
        判断是否应该显示试用对话框
        
        Returns:
            bool: 是否显示
        """
        status = self.activation_client.check_status()
        
        # 未激活且可以试用
        if not status.get('activated') and status.get('can_trial'):
            return True
        
        return False
    
    def upgrade_to_full(self, activation_code):
        """
        升级到正式版
        
        Args:
            activation_code: 正式版激活码
        
        Returns:
            dict: 升级结果
        """
        result = self.activation_client.activate(activation_code, is_trial=False)
        
        if result.get('success'):
            return {
                'success': True,
                'message': '升级成功，感谢购买！',
                'is_trial': False
            }
        else:
            return result
    
    def get_trial_guide(self):
        """
        获取试用引导信息
        
        Returns:
            dict: 引导信息
        """
        return {
            'trial_days': self.trial_days,
            'features': [
                '所有功能完全可用',
                '支持导出设计文件',
                '支持 AI 抠图和 OCR',
                '支持工单和报价管理'
            ],
            'limitations': [
                '试用期 30 天',
                '每台设备最多试用 3 次',
                '试用到期后需购买正式版'
            ],
            'purchase_options': [
                {
                    'name': '正式版（永久授权）',
                    'price': 299,
                    'features': ['永久使用', '免费更新', '技术支持']
                }
            ]
        }


if __name__ == '__main__':
    # 测试
    manager = TrialManager()
    
    # 检查试用状态
    status = manager.check_trial_status()
    print(f"试用状态：{status}")
    
    # 获取引导信息
    guide = manager.get_trial_guide()
    print(f"试用引导：{guide}")
