#!/usr/bin/env python3
"""
模型下载脚本

自动下载 U²-Net 抠图模型文件（FP32 和 INT8）。

使用方法：
    python download_models.py          # 下载所有模型
    python download_models.py --fp32   # 仅下载 FP32 模型
    python download_models.py --int8   # 仅下载 INT8 模型
    python download_models.py --list   # 列出模型下载地址

模型来源：
- U²-Net (FP32): https://github.com/xuebinqin/U-2-Net
- U²-Net (INT8): https://github.com/xuebinqin/U-2-Net

模型存储位置：app/models/
"""
import os
import sys
import argparse
import urllib.request
import hashlib
from pathlib import Path


# 模型信息配置
MODELS = {
    'u2net_fp32': {
        'url': 'https://github.com/xuebinqin/U-2-Net/releases/download/v1.0/u2net.onnx',
        'filename': 'u2net.onnx',
        'description': 'U²-Net FP32 高精度模型（约 50MB）',
        'md5': None,  # 后续补充
    },
    'u2net_int8': {
        'url': 'https://github.com/xuebinqin/U-2-Net/releases/download/v1.0/u2net_int8.onnx',
        'filename': 'u2net_int8.onnx',
        'description': 'U²-Net INT8 量化模型（约 15MB）',
        'md5': None,  # 后续补充
    },
}

# 模型存储目录
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'models')


def ensure_dir(directory: str):
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)


def check_existing(filename: str) -> bool:
    """检查模型文件是否已存在"""
    filepath = os.path.join(MODEL_DIR, filename)
    return os.path.isfile(filepath)


def get_file_size(filename: str) -> str:
    """获取文件大小（人类可读）"""
    filepath = os.path.join(MODEL_DIR, filename)
    if not os.path.isfile(filepath):
        return "0 B"
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def download_file(url: str, dest_path: str, description: str = ""):
    """
    下载文件并显示进度
    
    Args:
        url: 下载地址
        dest_path: 保存路径
        description: 文件描述
    """
    print(f"\n{'='*60}")
    print(f"📥 正在下载: {description}")
    print(f"   源地址: {url}")
    print(f"   保存到: {dest_path}")
    print(f"{'='*60}")
    
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            bar_len = 40
            filled = int(bar_len * downloaded / total_size)
            bar = '█' * filled + '░' * (bar_len - filled)
            sys.stdout.write(f"\r    [{bar}] {percent:.1f}% ({downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)")
            sys.stdout.flush()
    
    try:
        urllib.request.urlretrieve(url, dest_path, report_progress)
        print("\n    ✅ 下载完成!")
    except urllib.error.HTTPError as e:
        print(f"\n    ❌ HTTP 错误: {e.code} {e.reason}")
        raise
    except urllib.error.URLError as e:
        print(f"\n    ❌ 网络错误: {e.reason}")
        raise
    except Exception as e:
        print(f"\n    ❌ 下载失败: {str(e)}")
        raise


def verify_file(filepath: str, expected_md5: Optional[str] = None) -> bool:
    """
    验证文件完整性
    
    Args:
        filepath: 文件路径
        expected_md5: 期望的 MD5 值
        
    Returns:
        bool: 是否完整
    """
    if not os.path.isfile(filepath):
        return False
    
    if expected_md5 is None:
        return True
    
    try:
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        return md5.hexdigest() == expected_md5
    except Exception:
        return False


def download_model(model_key: str, force: bool = False):
    """
    下载指定模型
    
    Args:
        model_key: 模型键名（'u2net_fp32' 或 'u2net_int8'）
        force: 是否强制重新下载
    """
    if model_key not in MODELS:
        print(f"❌ 未知模型: {model_key}")
        print(f"   可用模型: {', '.join(MODELS.keys())}")
        return False
    
    model_info = MODELS[model_key]
    filename = model_info['filename']
    filepath = os.path.join(MODEL_DIR, filename)
    
    # 检查是否已存在
    if check_existing(filename) and not force:
        size = get_file_size(filename)
        print(f"⏭️  跳过 {filename}（已存在，{size}）")
        print(f"   使用 --force 参数强制重新下载")
        return True
    
    try:
        download_file(model_info['url'], filepath, model_info['description'])
        return True
    except Exception as e:
        print(f"❌ {model_key} 下载失败: {str(e)}")
        return False


def list_models():
    """列出所有模型及其状态"""
    print(f"\n{'='*60}")
    print(f"📋 模型下载列表")
    print(f"   存储目录: {MODEL_DIR}")
    print(f"{'='*60}")
    
    for key, info in MODELS.items():
        filename = info['filename']
        exists = check_existing(filename)
        size = get_file_size(filename) if exists else "—"
        status = "✅ 已下载" if exists else "❌ 未下载"
        print(f"\n  {key}:")
        print(f"    文件: {filename}")
        print(f"    说明: {info['description']}")
        print(f"    状态: {status} ({size})")
    
    print(f"\n{'='*60}")
    print(f"📝 使用方法:")
    print(f"   下载所有: python {os.path.basename(__file__)}")
    print(f"   仅 FP32: python {os.path.basename(__file__)} --fp32")
    print(f"   仅 INT8: python {os.path.basename(__file__)} --int8")
    print(f"{'='*60}")


def download_all(force: bool = False):
    """下载所有模型"""
    ensure_dir(MODEL_DIR)
    
    success = True
    for key in MODELS:
        if not download_model(key, force):
            success = False
    
    if success:
        print(f"\n{'='*60}")
        print("🎉 所有模型下载完成！")
        print(f"   模型存储目录: {MODEL_DIR}")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print("⚠️  部分模型下载失败，请检查网络后重试")
        print(f"{'='*60}")
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description='豆子设计助手 - AI 模型下载工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python download_models.py          下载所有模型
  python download_models.py --fp32   仅下载 FP32 模型
  python download_models.py --int8   仅下载 INT8 模型
  python download_models.py --list   查看模型列表
  python download_models.py --force  强制重新下载
        """
    )
    
    parser.add_argument('--fp32', action='store_true', help='仅下载 FP32 模型')
    parser.add_argument('--int8', action='store_true', help='仅下载 INT8 模型')
    parser.add_argument('--list', action='store_true', help='查看模型列表')
    parser.add_argument('--force', action='store_true', help='强制重新下载')
    
    args = parser.parse_args()
    
    if args.list:
        list_models()
        return
    
    ensure_dir(MODEL_DIR)
    
    if args.fp32:
        download_model('u2net_fp32', args.force)
    elif args.int8:
        download_model('u2net_int8', args.force)
    else:
        download_all(args.force)
    
    print()
    print("💡 提示: 运行 python main.py 启动应用后")
    print("          AI 抠图功能会自动检测并使用已下载的模型")


if __name__ == '__main__':
    main()
