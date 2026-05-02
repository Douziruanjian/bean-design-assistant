"""
OCR 文字识别引擎

封装 PaddleOCR 的文字识别功能。
支持图片文字提取，结果展示和复制。

PaddleOCR Lite 使用 ONNX Runtime 部署：
- 检测模型：检测文字区域
- 识别模型：识别文字内容
"""
import os
from typing import List, Dict, Any, Optional, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class OCRError(Exception):
    """OCR 处理异常"""
    pass


class OCRResult:
    """OCR 识别结果"""
    
    def __init__(self, text: str, confidence: float, 
                 box: Optional[List[Tuple[int, int]]] = None):
        """
        初始化识别结果
        
        Args:
            text: 识别的文字内容
            confidence: 置信度 (0-1)
            box: 文字区域坐标 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        """
        self.text = text
        self.confidence = confidence
        self.box = box or []
    
    def to_dict(self) -> Dict:
        return {
            'text': self.text,
            'confidence': self.confidence,
            'box': self.box
        }
    
    def __repr__(self) -> str:
        return f"OCRResult(text='{self.text}', conf={self.confidence:.2f})"


class OCREngine:
    """
    OCR 文字识别引擎
    
    封装 PaddleOCR Lite 的推理流程。
    当前为预留接口，实际模型加载在首次调用时初始化。
    """
    
    def __init__(self):
        """
        初始化 OCR 引擎
        
        Raises:
            OCRError: 依赖缺失
        """
        if not HAS_PIL:
            raise OCRError("Pillow 未安装，请执行: pip install Pillow")
        if not HAS_NUMPY:
            raise OCRError("NumPy 未安装，请执行: pip install numpy")
        
        self._initialized = False
        self._ocr_instance = None  # PaddleOCR 实例（实际部署时初始化）
    
    def initialize(self):
        """
        初始化 OCR 引擎（延迟加载）
        
        首次调用时加载 PaddleOCR 模型。
        如果 PaddleOCR 未安装，进入模拟模式。
        """
        if self._initialized:
            return
        
        try:
            # 尝试导入 PaddleOCR
            from paddleocr import PaddleOCR
            
            self._ocr_instance = PaddleOCR(
                use_angle_cls=False,  # 不适用方向分类
                lang='ch',            # 中文模型
                use_gpu=False,        # CPU 推理
                show_log=False        # 不显示日志
            )
            self._initialized = True
            
        except ImportError:
            # PaddleOCR 未安装，进入模拟模式
            self._initialized = False
        except Exception as e:
            # 其他错误也进入模拟模式
            self._initialized = False
    
    def is_ready(self) -> bool:
        """检查 OCR 引擎是否就绪"""
        try:
            return self._initialized and self._ocr_instance is not None
        except Exception:
            return False
    
    def recognize(self, image: Image.Image) -> List[OCRResult]:
        """
        识别图片中的文字
        
        Args:
            image: 输入的 PIL Image
            
        Returns:
            List[OCRResult]: 识别结果列表
            
        Raises:
            OCRError: 识别失败
        """
        if not HAS_PIL:
            raise OCRError("Pillow 未安装")
        
        # 保存临时文件（PaddleOCR 需要文件路径）
        temp_path = None
        try:
            if self.is_ready():
                # PaddleOCR 模式
                temp_path = self._save_temp_image(image)
                results = self._ocr_instance.ocr(temp_path, cls=False)
                
                return self._parse_paddleocr_results(results)
            else:
                # 模拟模式
                return self._mock_recognize(image)
                
        except Exception as e:
            raise OCRError(f"OCR 识别失败: {str(e)}")
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
    
    def _save_temp_image(self, image: Image.Image) -> str:
        """
        保存临时图片文件
        
        Args:
            image: PIL Image
            
        Returns:
            str: 临时文件路径
        """
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.png', delete=False
        )
        temp_path = temp_file.name
        temp_file.close()
        image.save(temp_path, 'PNG')
        return temp_path
    
    def _parse_paddleocr_results(self, results) -> List[OCRResult]:
        """
        解析 PaddleOCR 返回结果
        
        PaddleOCR 返回格式：
        [[[box, (text, confidence)], ...]]
        
        Args:
            results: PaddleOCR 原始结果
            
        Returns:
            List[OCRResult]: 解析后的结果
        """
        parsed = []
        
        if not results:
            return parsed
        
        for line_group in results:
            if not line_group:
                continue
            for item in line_group:
                if len(item) >= 2:
                    box = item[0]  # 坐标点
                    text_info = item[1]  # (文本, 置信度)
                    if len(text_info) >= 2:
                        text = text_info[0]
                        confidence = float(text_info[1])
                        parsed.append(OCRResult(text, confidence, box))
        
        return parsed
    
    def _mock_recognize(self, image: Image.Image) -> List[OCRResult]:
        """
        模拟 OCR 识别（模型不可用时使用）
        
        用于 UI 验证和开发调试。
        
        Args:
            image: 输入图片
            
        Returns:
            List[OCRResult]: 模拟识别结果
        """
        # 返回模拟数据用于界面测试
        return [
            OCRResult("豆子设计助手", 0.95, 
                     [(50,10),(200,10),(200,40),(50,40)]),
            OCRResult("AI 智能抠图系统", 0.88,
                     [(50,50),(220,50),(220,80),(50,80)]),
        ]
    
    def recognize_file(self, file_path: str) -> List[OCRResult]:
        """
        识别图片文件中的文字
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            List[OCRResult]: 识别结果
        """
        try:
            image = Image.open(file_path)
            return self.recognize(image)
        except Exception as e:
            raise OCRError(f"文件加载失败: {str(e)}")
    
    def get_full_text(self, results: List[OCRResult], 
                      separator: str = "\n") -> str:
        """
        将识别结果合并为完整文本
        
        Args:
            results: 识别结果列表
            separator: 分隔符
            
        Returns:
            str: 合并后的文本
        """
        return separator.join(r.text for r in results if r.text.strip())
    
    def close(self):
        """释放资源"""
        self._ocr_instance = None
        self._initialized = False
