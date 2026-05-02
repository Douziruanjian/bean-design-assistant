"""
Phase 3 功能测试脚本
测试激活码系统、支付接口、试用期管理
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from services.activation_service import ActivationService
from services.license_service import LicenseService
from services.payment_service import PaymentService
from models.db_models import init_db

def test_activation_code_generation():
    """测试激活码生成"""
    print("\n=== 测试激活码生成 ===")
    service = ActivationService()
    
    # 生成单个激活码
    code = service.generate_activation_code(days_valid=365)
    print(f"生成的激活码：{code['code']}")
    print(f"有效期：{code['expires_at']}")
    print(f"签名：{code['signature'][:50]}...")
    
    # 验证签名
    result = service.verify_activation_code(code['code'], code['signature'], 'test-device-fp')
    print(f"验证结果：{result}")
    
    assert result['valid'] == True, "激活码验证失败"
    print("✅ 激活码生成测试通过")
    
    return code

def test_batch_generation():
    """测试批量生成激活码"""
    print("\n=== 测试批量生成激活码 ===")
    service = ActivationService()
    
    codes = service.generate_batch_codes(count=5, days_valid=30)
    print(f"生成了 {len(codes)} 个激活码")
    for i, code in enumerate(codes, 1):
        print(f"  {i}. {code['code']}")
    
    assert len(codes) == 5, "批量生成数量错误"
    print("✅ 批量生成测试通过")

def test_license_service():
    """测试许可证服务"""
    print("\n=== 测试许可证服务 ===")
    
    # 初始化数据库
    init_db()
    
    license_service = LicenseService()
    activation_service = ActivationService()
    
    # 生成测试激活码
    code_data = activation_service.generate_activation_code(days_valid=365)
    test_code = code_data['code']
    
    # 模拟设备指纹
    test_device_fp = "test-device-" + os.urandom(8).hex()
    
    # 激活设备
    result = license_service.activate_device(test_code, test_device_fp, is_trial=False)
    print(f"激活结果：{result}")
    
    # 检查状态
    status = license_service.check_license_status(test_device_fp)
    print(f"许可证状态：{status}")
    
    assert status['activated'] == True, "激活状态错误"
    print("✅ 许可证服务测试通过")

def test_trial_management():
    """测试试用期管理"""
    print("\n=== 测试试用期管理 ===")
    
    license_service = LicenseService()
    
    # 模拟设备指纹
    test_device_fp = "trial-device-" + os.urandom(8).hex()
    
    # 使用试用激活码
    TRIAL_CODE = "TRIAL-30DAYS-2026"
    
    # 先插入试用激活码到数据库（模拟）
    from models.db_models import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT OR IGNORE INTO activation_codes (code, status, max_activations)
           VALUES (?, 'active', 999)''',
        (TRIAL_CODE,)
    )
    conn.commit()
    conn.close()
    
    # 激活试用
    result = license_service.activate_device(TRIAL_CODE, test_device_fp, is_trial=True)
    print(f"试用激活结果：{result}")
    
    # 检查试用状态
    status = license_service.check_license_status(test_device_fp)
    print(f"试用状态：{status}")
    
    if status.get('activated') and status.get('is_trial'):
        print(f"试用到期日期：{status.get('trial_end_date')}")
        print(f"剩余天数：{status.get('days_remaining')}")
        print("✅ 试用期管理测试通过")
    else:
        print("⚠️ 试用状态异常")

def test_payment_service():
    """测试支付服务"""
    print("\n=== 测试支付服务 ===")
    
    payment_service = PaymentService(mode='mock')
    
    # 创建微信支付订单
    wechat_result = payment_service.create_wechat_payment(amount=99.0)
    print(f"微信支付订单：{wechat_result}")
    
    # 创建支付宝订单
    alipay_result = payment_service.create_alipay_payment(amount=99.0)
    print(f"支付宝订单：{alipay_result}")
    
    # 查询支付状态
    query_result = payment_service.query_payment_status(wechat_result['order_id'])
    print(f"支付状态查询：{query_result}")
    
    assert wechat_result['success'] == True, "微信支付创建失败"
    assert alipay_result['success'] == True, "支付宝支付创建失败"
    print("✅ 支付服务测试通过")

def test_vm_detection():
    """测试虚拟机检测"""
    print("\n=== 测试虚拟机检测 ===")
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'license'))
    from hardware_fingerprint import HardwareFingerprint
    
    fp = HardwareFingerprint()
    is_vm = fp.is_virtual_machine()
    fingerprint = fp.get_fingerprint()
    
    print(f"设备指纹：{fingerprint}")
    print(f"是否虚拟机：{is_vm}")
    print("✅ 虚拟机检测测试通过")

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 3 功能测试开始")
    print("=" * 60)
    
    try:
        test_activation_code_generation()
        test_batch_generation()
        test_license_service()
        test_trial_management()
        test_payment_service()
        test_vm_detection()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        return True
    
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败：{e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
