"""
AI 模型加载/切换管理器

负责 ONNX Runtime 的模型加载、FP32/INT8 模式切换、
设备检测和自动降级逻辑。
"""
import os
import platform
from typing import Optional, Tuple, Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False


# 模型文件路径（相对于项目根目录）
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
U2NET_FP32_PATH = os.path.join(MODEL_DIR, 'u2net.onnx')
U2NET_INT8_PATH = os.path.join(MODEL_DIR, 'u2net_int8.onnx')


class ModelMode:
    """模型精度模式"""
    FP32 = "fp32"
    INT8 = "int8"
    AUTO = "auto"


class ModelLoadError(Exception):
    """模型加载异常"""
    pass


def detect_device() -> str:
    """
    检测可用推理设备
    
    Returns:
        str: 'cpu'（目前仅支持 CPU）
    """
    # 当前阶段仅支持 CPU 推理
    # 后续可扩展 CUDA/DirectML
    return 'cpu'


def check_model_file(model_path: str) -> bool:
    """
    检查模型文件是否存在
    
    Args:
        model_path: 模型文件路径
        
    Returns:
        bool: 文件是否存在
    """
    return os.path.isfile(model_path)


def get_available_modes() -> list:
    """
    获取当前可用的模型模式列表
    
    Returns:
        list: 可用模式列表，如 ['fp32', 'int8']
    """
    modes = []
    if check_model_file(U2NET_FP32_PATH):
        modes.append(ModelMode.FP32)
    if check_model_file(U2NET_INT8_PATH):
        modes.append(ModelMode.INT8)
    return modes


def select_optimal_mode() -> str:
    """
    根据 CPU 能力自动选择最优模式
    
    检测逻辑：
    1. 检查是否有 INT8 模型文件
    2. 检查 CPU 是否支持 INT8 加速（AVX2/AVX512）
    3. 低配机自动使用 INT8 模式
    
    Returns:
        str: 选择的模式（'fp32' 或 'int8'）
    """
    available = get_available_modes()
    
    # 只有一个可用，直接返回
    if ModelMode.FP32 in available and ModelMode.INT8 not in available:
        return ModelMode.FP32
    if ModelMode.INT8 in available and ModelMode.FP32 not in available:
        return ModelMode.INT8
    
    # 两个都有，根据 CPU 选择
    try:
        import cpuinfo
        
        # 检测 CPU 能力
        info = cpuinfo.get_cpu_info()
        flags = info.get('flags', []) if isinstance(info, dict) else []
        
        # 有 AVX512 或 AVX2 的机器可以跑 FP32
        has_avx = any(f in flags for f in ['avx2', 'avx512f', 'avx'])
        
        # 检测 CPU 核心数（低配机 < 4 核建议 INT8）
        cpu_count = os.cpu_count() or 4
        
        if has_avx and cpu_count >= 4:
            return ModelMode.FP32
        else:
            return ModelMode.INT8
    except ImportError:
        # 没有 cpuinfo 库，默认用 INT8（更安全）
        pass
    except Exception:
        pass
    
    return ModelMode.INT8


class ModelSession:
    """
    ONNX Runtime 推理会话封装
    
    管理单个 ONNX 模型的加载和推理，
    支持 FP32 和 INT8 两种精度模式。
    """
    
    def __init__(self, model_path: str):
        """
        初始化模型会话
        
        Args:
            model_path: ONNX 模型文件路径
            
        Raises:
            ModelLoadError: 模型文件不存在或加载失败
        """
        if not HAS_ONNX:
            raise ModelLoadError("ONNX Runtime 未安装，请执行: pip install onnxruntime")
        
        if not check_model_file(model_path):
            raise ModelLoadError(f"模型文件不存在: {model_path}")
        
        self.model_path = model_path
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.output_name: Optional[str] = None
        self.input_shape: Optional[Tuple] = None
        
        self._load_session()
    
    def _load_session(self):
        """加载 ONNX 推理会话"""
        try:
            # 创建 ONNX Runtime 会话
            # 使用 CPU 执行提供程序
            providers = ['CPUExecutionProvider']
            
            # 设置会话选项
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.enable_cpu_mem_arena = False
            
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=providers
            )
            
            # 获取输入/输出信息
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape
            
        except Exception as e:
            raise ModelLoadError(f"模型加载失败: {str(e)}")
    
    def run(self, input_data: Any) -> Any:
        """
        执行推理
        
        Args:
            input_data: 输入数据（numpy 数组）
            
        Returns:
            推理结果（numpy 数组）
            
        Raises:
            RuntimeError: 推理失败
        """
        if self.session is None:
            raise RuntimeError("推理会话未初始化")
        
        try:
            result = self.session.run(
                [self.output_name],
                {self.input_name: input_data}
            )
            return result[0]
        except Exception as e:
            raise RuntimeError(f"推理失败: {str(e)}")
    
    def get_input_shape(self) -> Tuple:
        """获取模型输入形状"""
        return self.input_shape
    
    def close(self):
        """释放资源"""
        self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ModelManager:
    """
    模型管理器（单例）
    
    统一管理所有 AI 模型的加载、切换和生命周期。
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ModelManager._initialized:
            return
        ModelManager._initialized = True
        
        self.device = detect_device()
        self.current_mode: str = ModelMode.AUTO
        self.matting_session: Optional[ModelSession] = None
        self.ocr_session: Optional[ModelSession] = None
        
        # 创建模型目录（如果不存在）
        os.makedirs(MODEL_DIR, exist_ok=True)
    
    def initialize_matting(self, mode: str = ModelMode.AUTO):
        """
        初始化抠图模型
        
        Args:
            mode: 精度模式，'fp32'/'int8'/'auto'
            
        Raises:
            ModelLoadError: 模型加载失败
        """
        if mode == ModelMode.AUTO:
            mode = select_optimal_mode()
        
        self.current_mode = mode
        
        # 选择模型文件
        if mode == ModelMode.INT8:
            model_path = U2NET_INT8_PATH
        else:
            model_path = U2NET_FP32_PATH
        
        # 检查模型是否存在
        if not check_model_file(model_path):
            raise ModelLoadError(
                f"抠图模型文件不存在: {model_path}\n"
                f"请先运行 python download_models.py 下载模型"
            )
        
        # 加载模型
        self.matting_session = ModelSession(model_path)
    
    def initialize_ocr(self):
        """
        初始化 OCR 模型
        
        OCR 使用 PaddleOCR，需要检测模型文件
        """
        if not HAS_ONNX:
            raise ModelLoadError("ONNX Runtime 未安装")
        
        # PaddleOCR 使用内部模型管理，不需要单独加载
        # 这里只做环境检查
        try:
            # 验证 onnxruntime 可以正常工作
            ort.get_device()
        except Exception as e:
            raise ModelLoadError(f"ONNX Runtime 初始化失败: {str(e)}")
    
    def is_matting_ready(self) -> bool:
        """检查抠图模型是否已加载"""
        return self.matting_session is not None
    
    def is_ocr_ready(self) -> bool:
        """检查 OCR 模型是否已加载"""
        # PaddleOCR 是运行时按需加载的
        return True
    
    def get_matting_session(self) -> Optional[ModelSession]:
        """获取抠图模型会话"""
        return self.matting_session
    
    def get_current_mode_name(self) -> str:
        """获取当前模式名称（中文）"""
        names = {
            ModelMode.FP32: "FP32 高精度",
            ModelMode.INT8: "INT8 快速",
            ModelMode.AUTO: "自动选择"
        }
        return names.get(self.current_mode, "未知")
    
    def switch_mode(self, mode: str) -> bool:
        """
        切换精度模式
        
        Args:
            mode: 目标模式
            
        Returns:
            bool: 是否切换成功
        """
        if mode == self.current_mode:
            return True
        
        try:
            self.initialize_matting(mode)
            return True
        except ModelLoadError:
            return False
    
    def get_available_modes(self) -> list:
        """获取可用模式列表"""
        return get_available_modes()
    
    @classmethod
    def get_instance(cls) -> 'ModelManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        if cls._instance and cls._instance.matting_session:
            cls._instance.matting_session.close()
        cls._instance = None
        cls._initialized = False


# 便捷函数
def get_model_manager() -> ModelManager:
    """获取模型管理器实例"""
    return ModelManager.get_instance()
