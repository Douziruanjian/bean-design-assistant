"""
文字识别（OCR）页面

PaddleOCR 文字识别功能的用户界面。
支持图片导入、一键识别、结果展示和复制。
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFrame, QFileDialog, QMessageBox,
                             QTextEdit, QSplitter, QScrollArea,
                             QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PIL import Image

from ..ai.ocr import OCREngine, OCRError, OCRResult


class AiOcrPage(QWidget):
    """文字识别（OCR）页面"""
    
    def __init__(self):
        super().__init__()
        
        self.ocr_engine: OCREngine = None
        self.current_image: Image.Image = None
        self.input_path: str = ""
        self.last_results: list = []
        
        self._init_ui()
        self._init_engine()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # ── 标题栏 ──
        title = QLabel("📝 文字识别 (OCR)")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # ── 工具栏 ──
        toolbar = QHBoxLayout()
        
        self.btn_open = QPushButton("📂 打开图片")
        self.btn_open.setMinimumHeight(36)
        self.btn_open.setMinimumWidth(120)
        self.btn_open.clicked.connect(self._open_image)
        toolbar.addWidget(self.btn_open)
        
        self.btn_recognize = QPushButton("🔍 识别文字")
        self.btn_recognize.setMinimumHeight(36)
        self.btn_recognize.setMinimumWidth(120)
        self.btn_recognize.setEnabled(False)
        self.btn_recognize.clicked.connect(self._do_recognize)
        toolbar.addWidget(self.btn_recognize)
        
        self.btn_copy = QPushButton("📋 复制结果")
        self.btn_copy.setMinimumHeight(36)
        self.btn_copy.setMinimumWidth(100)
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_result)
        toolbar.addWidget(self.btn_copy)
        
        self.btn_clear = QPushButton("🗑️ 清空")
        self.btn_clear.setMinimumHeight(36)
        self.btn_clear.setMinimumWidth(80)
        self.btn_clear.clicked.connect(self._clear)
        toolbar.addWidget(self.btn_clear)
        
        toolbar.addStretch()
        
        # OCR 引擎状态
        self.engine_status = QLabel("")
        self.engine_status.setStyleSheet("color: #999; font-size: 12px;")
        toolbar.addWidget(self.engine_status)
        
        layout.addLayout(toolbar)
        
        # ── 主区域（左右分割） ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图片预览
        left_widget = QFrame()
        left_widget.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
        """)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        img_label = QLabel("图片预览")
        img_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        left_layout.addWidget(img_label)
        
        img_scroll = QScrollArea()
        img_scroll.setWidgetResizable(True)
        img_scroll.setStyleSheet("border: none;")
        
        self.image_display = QLabel("点击「打开图片」\n选择要进行文字识别的图片")
        self.image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display.setMinimumSize(300, 300)
        self.image_display.setStyleSheet("color: #999; font-size: 13px;")
        img_scroll.setWidget(self.image_display)
        
        left_layout.addWidget(img_scroll)
        left_widget.setLayout(left_layout)
        
        splitter.addWidget(left_widget)
        
        # 右侧：识别结果
        right_widget = QFrame()
        right_widget.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
            }
        """)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        result_label = QLabel("识别结果")
        result_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        right_layout.addWidget(result_label)
        
        # 结果文本区
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("点击「识别文字」按钮\n\n识别出的文字内容将显示在这里")
        self.result_text.setFont(QFont("Microsoft YaHei", 12))
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        right_layout.addWidget(self.result_text)
        
        # 结果统计
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #999; font-size: 11px;")
        right_layout.addWidget(self.stats_label)
        
        right_widget.setLayout(right_layout)
        
        splitter.addWidget(right_widget)
        
        # 设置比例
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter)
        
        self.setLayout(layout)
    
    def _init_engine(self):
        """初始化 OCR 引擎"""
        try:
            self.ocr_engine = OCREngine()
            
            if self.ocr_engine.is_ready():
                self.engine_status.setText("✅ OCR 就绪")
                self.engine_status.setStyleSheet("color: #4caf50; font-size: 12px;")
            else:
                self.engine_status.setText("⚠️ PaddleOCR 未安装，使用模拟模式")
                self.engine_status.setStyleSheet("color: #ff9800; font-size: 12px;")
        except Exception as e:
            self.engine_status.setText(f"❌ OCR 初始化失败: {str(e)}")
            self.engine_status.setStyleSheet("color: #f44336; font-size: 12px;")
    
    def _open_image(self):
        """打开图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        try:
            self.current_image = Image.open(file_path)
            self.input_path = file_path
            
            # 显示图片
            pixmap = QPixmap(file_path)
            if pixmap.width() > 400 or pixmap.height() > 400:
                pixmap = pixmap.scaled(
                    400, 400,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            self.image_display.setPixmap(pixmap)
            self.image_display.setStyleSheet("")
            
            # 启用识别按钮
            self.btn_recognize.setEnabled(True)
            
            # 清空旧结果
            self.last_results = []
            self.result_text.clear()
            self.stats_label.setText("")
            self.btn_copy.setEnabled(False)
            
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开图片: {str(e)}")
    
    def _do_recognize(self):
        """执行文字识别"""
        if self.current_image is None:
            return
        
        if not self.ocr_engine:
            QMessageBox.warning(self, "引擎未就绪", "OCR 引擎未初始化")
            return
        
        try:
            self.btn_recognize.setEnabled(False)
            self.btn_recognize.setText("⏳ 识别中...")
            
            # 执行识别
            results = self.ocr_engine.recognize(self.current_image)
            self.last_results = results
            
            if results:
                # 显示结果文本
                full_text = self.ocr_engine.get_full_text(results)
                self.result_text.setPlainText(full_text)
                
                # 显示详细结果
                details = []
                for r in results:
                    conf_pct = r.confidence * 100
                    details.append(f"[{conf_pct:.1f}%] {r.text}")
                
                details_text = "\n".join(details)
                self.stats_label.setText(
                    f"共识别 {len(results)} 项文字  |  平均置信度: "
                    f"{sum(r.confidence for r in results)/len(results)*100:.1f}%"
                )
                
                self.btn_copy.setEnabled(True)
            else:
                self.result_text.setPlainText("未识别到文字内容")
                self.stats_label.setText("未识别到文字")
                self.btn_copy.setEnabled(False)
            
        except OCRError as e:
            QMessageBox.critical(self, "识别失败", f"OCR 识别出错: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "识别失败", f"OCR 识别出错: {str(e)}")
        finally:
            self.btn_recognize.setEnabled(True)
            self.btn_recognize.setText("🔍 识别文字")
    
    def _copy_result(self):
        """复制识别结果到剪贴板"""
        text = self.result_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            # 临时显示反馈
            old_text = self.btn_copy.text()
            self.btn_copy.setText("✅ 已复制")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.btn_copy.setText(old_text))
    
    def _clear(self):
        """清空所有内容"""
        self.current_image = None
        self.input_path = ""
        self.last_results = []
        
        self.image_display.setText("点击「打开图片」\n选择要进行文字识别的图片")
        self.image_display.setStyleSheet("color: #999; font-size: 13px;")
        
        self.result_text.clear()
        self.stats_label.setText("")
        
        self.btn_recognize.setEnabled(False)
        self.btn_copy.setEnabled(False)
