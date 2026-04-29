"""
许可证管理服务
管理激活状态、试用期、设备绑定等
"""
import sqlite3
import json
from datetime import datetime, timedelta
from models.db_models import get_db_connection

class LicenseService:
    def __init__(self):
        self.trial_days = 30
        self.max_trial_activations = 3
    
    def activate_device(self, activation_code, device_fingerprint, is_trial=False):
        """
        激活设备
        
        Args:
            activation_code: 激活码
            device_fingerprint: 设备指纹
            is_trial: 是否为试用激活
        
        Returns:
            dict: 激活结果
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查设备是否已激活
            cursor.execute(
                'SELECT id FROM device_activations WHERE device_fingerprint = ?',
                (device_fingerprint,)
            )
            if cursor.fetchone():
                return {'success': False, 'message': '设备已激活'}
            
            # 检查激活码
            cursor.execute(
                'SELECT id, status, max_activations, current_activations FROM activation_codes WHERE code = ?',
                (activation_code,)
            )
            code_row = cursor.fetchone()
            
            if not code_row:
                return {'success': False, 'message': '激活码不存在'}
            
            code_id, status, max_activations, current_activations = code_row
            
            if status != 'active':
                return {'success': False, 'message': '激活码已失效'}
            
            if current_activations >= max_activations:
                return {'success': False, 'message': '激活码已达最大激活次数'}
            
            # 检查设备绑定（单激活码绑定单设备）
            cursor.execute(
                'SELECT id FROM device_activations WHERE activation_code_id = ?',
                (code_id,)
            )
            if cursor.fetchone() and max_activations == 1:
                return {'success': False, 'message': '该激活码已绑定其他设备'}
            
            # 计算试用到期日期
            trial_end_date = None
            if is_trial:
                # 检查试激活次数
                cursor.execute(
                    'SELECT COUNT(*) FROM trial_activations WHERE device_fingerprint = ?',
                    (device_fingerprint,)
                )
                trial_count = cursor.fetchone()[0]
                
                if trial_count >= self.max_trial_activations:
                    return {'success': False, 'message': f'试激活次数已达上限（{self.max_trial_activations}次）'}
                
                trial_end_date = datetime.now() + timedelta(days=self.trial_days)
                
                # 记录试激活
                cursor.execute(
                    'INSERT OR IGNORE INTO trial_activations (device_fingerprint) VALUES (?)',
                    (device_fingerprint,)
                )
            
            # 创建激活记录
            cursor.execute(
                '''INSERT INTO device_activations 
                   (activation_code_id, device_fingerprint, is_trial, trial_end_date)
                   VALUES (?, ?, ?, ?)''',
                (code_id, device_fingerprint, 1 if is_trial else 0, trial_end_date)
            )
            
            # 更新激活码使用次数
            cursor.execute(
                'UPDATE activation_codes SET current_activations = current_activations + 1 WHERE id = ?',
                (code_id,)
            )
            
            conn.commit()
            
            return {
                'success': True,
                'message': '激活成功',
                'trial_end_date': trial_end_date.isoformat() if trial_end_date else None,
                'is_trial': is_trial
            }
        
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'激活失败：{str(e)}'}
        
        finally:
            conn.close()
    
    def check_license_status(self, device_fingerprint):
        """
        检查设备许可证状态
        
        Returns:
            dict: 许可证状态
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 查询设备激活记录
            cursor.execute(
                '''SELECT da.id, da.is_trial, da.trial_end_date, ac.code, ac.expires_at
                   FROM device_activations da
                   JOIN activation_codes ac ON da.activation_code_id = ac.id
                   WHERE da.device_fingerprint = ?''',
                (device_fingerprint,)
            )
            row = cursor.fetchone()
            
            if not row:
                # 设备未激活，检查是否可试用
                cursor.execute(
                    'SELECT COUNT(*) FROM trial_activations WHERE device_fingerprint = ?',
                    (device_fingerprint,)
                )
                trial_count = cursor.fetchone()[0]
                
                return {
                    'activated': False,
                    'can_trial': trial_count < self.max_trial_activations,
                    'trial_count': trial_count,
                    'max_trial_activations': self.max_trial_activations
                }
            
            activation_id, is_trial, trial_end_date, code, expires_at = row
            
            # 检查是否过期
            now = datetime.now()
            if is_trial and trial_end_date:
                trial_end = datetime.fromisoformat(trial_end_date)
                if now > trial_end:
                    return {
                        'activated': True,
                        'expired': True,
                        'expired_type': 'trial',
                        'expired_date': trial_end_date,
                        'message': '试用期已结束，请购买正式版'
                    }
                
                days_remaining = (trial_end - now).days
                return {
                    'activated': True,
                    'expired': False,
                    'is_trial': True,
                    'trial_end_date': trial_end_date,
                    'days_remaining': days_remaining,
                    'should_remind': days_remaining <= 3,
                    'message': f'试用剩余 {days_remaining} 天'
                }
            else:
                # 正式版
                if expires_at:
                    exp_date = datetime.fromisoformat(expires_at)
                    if now > exp_date:
                        return {
                            'activated': True,
                            'expired': True,
                            'expired_type': 'license',
                            'expired_date': expires_at,
                            'message': '许可证已过期'
                        }
                
                return {
                    'activated': True,
                    'expired': False,
                    'is_trial': False,
                    'license_code': code,
                    'expires_at': expires_at,
                    'message': '许可证有效'
                }
        
        finally:
            conn.close()
    
    def get_trial_info(self, device_fingerprint):
        """获取试用信息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM trial_activations WHERE device_fingerprint = ?',
                (device_fingerprint,)
            )
            trial_count = cursor.fetchone()[0]
            
            return {
                'trial_count': trial_count,
                'max_trials': self.max_trial_activations,
                'can_trial': trial_count < self.max_trial_activations,
                'trial_days': self.trial_days
            }
        
        finally:
            conn.close()


if __name__ == '__main__':
    # 测试
    service = LicenseService()
    print("许可证服务初始化完成")
