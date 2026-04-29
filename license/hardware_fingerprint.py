"""
硬件指纹采集模块
支持 Windows 10/11: 硬盘 UUID + 主板序列号
"""
import platform
import subprocess
import hashlib
import re

class HardwareFingerprint:
    def __init__(self):
        self.system = platform.system()
    
    def get_fingerprint(self):
        """
        获取设备硬件指纹
        
        Returns:
            str: 硬件指纹字符串
        """
        if self.system == 'Windows':
            return self._get_windows_fingerprint()
        elif self.system == 'Darwin':
            return self._get_macos_fingerprint()
        elif self.system == 'Linux':
            return self._get_linux_fingerprint()
        else:
            return self._get_generic_fingerprint()
    
    def _get_windows_fingerprint(self):
        """
        Windows 系统：采集硬盘 UUID + 主板序列号
        
        Returns:
            str: 硬件指纹
        """
        disk_uuid = self._get_windows_disk_uuid()
        motherboard_serial = self._get_windows_motherboard_serial()
        
        # 组合指纹
        fingerprint_data = f"{disk_uuid}|{motherboard_serial}"
        
        # 生成哈希指纹
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
        
        return fingerprint
    
    def _get_windows_disk_uuid(self):
        """获取 Windows 硬盘 UUID"""
        try:
            # 使用 wmic 命令获取硬盘序列号
            result = subprocess.run(
                ['wmic', 'diskdrive', 'get', 'serialnumber'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # 取第一个硬盘的序列号
                    serial = lines[1].strip()
                    if serial:
                        return serial
        
        except Exception as e:
            print(f"获取硬盘 UUID 失败：{e}")
        
        # 备用方案：使用 PowerShell
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-PhysicalDisk | Select-Object -First 1 | Select-Object -ExpandProperty SerialNumber'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                serial = result.stdout.strip()
                if serial:
                    return serial
        
        except Exception as e:
            print(f"备用方案获取硬盘 UUID 失败：{e}")
        
        return 'unknown_disk'
    
    def _get_windows_motherboard_serial(self):
        """获取 Windows 主板序列号"""
        try:
            # 使用 wmic 命令获取主板序列号
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'serialnumber'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    serial = lines[1].strip()
                    if serial and serial != 'To be filled by O.E.M.':
                        return serial
        
        except Exception as e:
            print(f"获取主板序列号失败：{e}")
        
        # 备用方案：使用 PowerShell
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 'Get-WmiObject Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                serial = result.stdout.strip()
                if serial and serial != 'To be filled by O.E.M.':
                    return serial
        
        except Exception as e:
            print(f"备用方案获取主板序列号失败：{e}")
        
        return 'unknown_motherboard'
    
    def _get_macos_fingerprint(self):
        """macOS 系统指纹"""
        try:
            # 获取 macOS 序列号
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                # 查找序列号
                match = re.search(r'Serial Number.*:\s*(\S+)', output)
                if match:
                    serial = match.group(1)
                    return hashlib.sha256(serial.encode()).hexdigest()[:32]
        
        except Exception as e:
            print(f"获取 macOS 指纹失败：{e}")
        
        return self._get_generic_fingerprint()
    
    def _get_linux_fingerprint(self):
        """Linux 系统指纹"""
        try:
            # 尝试读取机器 ID
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
                if machine_id:
                    return hashlib.sha256(machine_id.encode()).hexdigest()[:32]
        
        except Exception as e:
            print(f"获取 Linux 指纹失败：{e}")
        
        return self._get_generic_fingerprint()
    
    def _get_generic_fingerprint(self):
        """通用指纹（备用方案）"""
        # 使用主机名 + 平台信息生成指纹
        hostname = platform.node()
        platform_info = platform.platform()
        fingerprint_data = f"{hostname}|{platform_info}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
    
    def is_virtual_machine(self):
        """
        检测是否在虚拟机中运行
        
        Returns:
            bool: 是否在虚拟机中
        """
        if self.system == 'Windows':
            return self._is_windows_vm()
        elif self.system == 'Linux':
            return self._is_linux_vm()
        elif self.system == 'Darwin':
            return self._is_macos_vm()
        
        return False
    
    def _is_windows_vm(self):
        """检测 Windows 虚拟机"""
        vm_indicators = ['vmware', 'virtualbox', 'qemu', 'hypervisor', 'xen']
        
        try:
            # 检查 BIOS 信息
            result = subprocess.run(
                ['wmic', 'bios', 'get', 'manufacturer'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                for indicator in vm_indicators:
                    if indicator in output:
                        return True
        
        except Exception:
            pass
        
        # 检查进程（虚拟机工具）
        vm_processes = ['vmtoolsd', 'vboxservice', 'qemu-ga']
        try:
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                for process in vm_processes:
                    if process in output:
                        return True
        
        except Exception:
            pass
        
        return False
    
    def _is_linux_vm(self):
        """检测 Linux 虚拟机"""
        vm_indicators = ['vmware', 'virtualbox', 'qemu', 'kvm', 'xen']
        
        try:
            # 检查 dmi 信息
            result = subprocess.run(
                ['dmidecode', '-t', 'system'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                for indicator in vm_indicators:
                    if indicator in output:
                        return True
        
        except Exception:
            pass
        
        # 检查虚拟化文件
        vm_files = [
            '/proc/scsi/scsi',
            '/proc/cpuinfo'
        ]
        
        for filepath in vm_files:
            try:
                with open(filepath, 'r') as f:
                    content = f.read().lower()
                    for indicator in vm_indicators:
                        if indicator in content:
                            return True
            except Exception:
                continue
        
        return False
    
    def _is_macos_vm(self):
        """检测 macOS 虚拟机（黑苹果）"""
        # macOS 虚拟机检测较为复杂，这里做简单检查
        try:
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout.lower()
                if 'virtual' in output or 'vmware' in output:
                    return True
        
        except Exception:
            pass
        
        return False


if __name__ == '__main__':
    # 测试
    fp = HardwareFingerprint()
    fingerprint = fp.get_fingerprint()
    print(f"设备指纹：{fingerprint}")
    
    is_vm = fp.is_virtual_machine()
    print(f"是否虚拟机：{is_vm}")
