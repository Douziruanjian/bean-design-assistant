"""
AI 抠图页面

U²-Net 智能抠图功能的用户界面。
支持图片导入、一键抠图、预览对比、结果保存、FP32/INT8 模式切换。
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFrame, QFileDialog, QMessageBox,
                             QComboBox, QSlider, QSplitter, QScrollArea,
                             QSizePolicy, QProgressBar)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage
from PIL import Image, ImageQt

from ..ai.matting import U2NetMatting, MattingError
from ..ai.model_loader import ModelMode, check_model_file, \
    U2NET_FP32_PATH, U2NET_INT8_PATH


class AiMattingPage(QWidget):
    """AI 抠图页面"""
    
    def __init__(self):
        super().__init__()
        
        self.matting_engine: U2NetMatting = None
        self.current_image: Image.Image = None
        self.result_image: Image.Image = None
        self.input_path: str = ""
        
        self._init_ui()
        self._init_engine()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # ── 标题栏 ──
        header = QHBoxLayout()
        title = QLabel("AI 智能抠图")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        header.addWidget(title)
        
        # 模式选择
        header.addStretch()
        mode_label = QLabel("推理模式：")
        mode_label.setFont(QFont("Microsoft YaHei", 12))
        header.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("自动选择", ModelMode.AUTO)
        self.mode_combo.addItem("FP32 高精度", ModelMode.FP32)
        self.mode_combo.addItem("INT8 快速", ModelMode.INT8)
        self.mode_combo.setMinimumWidth(150)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header.addWidget(self.mode_combo)
        
        # 阈值调节
        header.addSpacing(20)
        threshold_label = QLabel("抠图阈值：")
        threshold_label.setFont(QFont("Microsoft YaHei", 12))
        header.addWidget(threshold_label)
        
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(30, 80)
        self.threshold_slider.setValue(50)
        self.threshold_slider.setFixedWidth(120)
        header.addWidget(self.threshold_slider)
        
        self.threshold_value = QLabel("0.50")
        self.threshold_value.setFont(QFont("Microsoft YaHei", 12))
        self.threshold_value.setFixedWidth(40)
        header.addWidget(self.threshold_value)
        
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_value.setText(f"{v/100:.2f}")
        )
        
        layout.addLayout(header)
        
        # ── 工具栏 ──
        toolbar = QHBoxLayout()
        
        self.btn_open = QPushButton("📂 打开图片")
        self.btn_open.setMinimumHeight(36)
        self.btn_open.setMinimumWidth(120)
        self.btn_open.clicked.connect(self._open_image)
        toolbar.addWidget(self.btn_open)
        
        self.btn_matting = QPushButton("✨ 一键抠图")
        self.btn_matting.setMinimumHeight(36)
        self.btn_matting.setMinimumWidth(120)
        self.btn_matting.setEnabled(False)
        self.btn_matting.clicked.connect(self._do_matting)
        toolbar.addWidget(self.btn_matting)
        
        self.btn_save = QPushButton("💾 保存结果")
        self.btn_save.setMinimumHeight(36)
        self.btn_save.setMinimumWidth(120)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_result)
        toolbar.addWidget(self.btn_save)
        
        self.btn_clear = QPushButton("🗑️ 清空")
        self.btn_clear.setMinimumHeight(36)
        self.btn_clear.setMinimumWidth(80)
        self.btn_clear.clicked.connect(self._clear)
        toolbar.addWidget(self.btn_clear)
        
        toolbar.addStretch()
        
        # 模型状态
        self.model_status = QLabel("")
        self.model_status.setStyleSheet("color: #999; font-size: 12px;")
        toolbar.addWidget(self.model_status)
        
        layout.addLayout(toolbar)
        
        # ── 进度条 ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)
        
        # ── 图片预览区（左右对比） ──
        preview_layout = QHBoxLayout()
        
        # 原图
        original_frame = QFrame()
        original_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
        """)
        original_layout = QVBoxLayout()
        original_layout.setContentsMargins(10, 10, 10, 10)
        
        original_label = QLabel("原图")
        original_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        original_layout.addWidget(original_label)
        
        original_scroll = QScrollArea()
        original_scroll.setWidgetResizable(True)
        original_scroll.setStyleSheet("border: none;")
        
        self.original_display = QLabel("点击「打开图片」\n选择要处理的图片")
        self.original_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_display.setMinimumSize(300, 300)
        self.original_display.setStyleSheet("color: #999; font-size: 13px;")
        original_scroll.setWidget(self.original_display)
        
        original_layout.addWidget(original_scroll)
        original_frame.setLayout(original_layout)
        preview_layout.addWidget(original_frame)
        
        # 结果图
        result_frame = QFrame()
        result_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
            }
        """)
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(10, 10, 10, 10)
        
        result_label = QLabel("抠图结果")
        result_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        result_layout.addWidget(result_label)
        
        result_scroll = QScrollArea()
        result_scroll.setWidgetResizable(True)
        result_scroll.setStyleSheet("border: none;")
        
        self.result_display = QLabel("抠图后透明背景\n图片将在这里显示")
        self.result_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_display.setMinimumSize(300, 300)
        self.result_display.setStyleSheet("color: #999; font-size: 13px;")
        result_scroll.setWidget(self.result_display)
        
        result_layout.addWidget(result_scroll)
        result_frame.setLayout(result_layout)
        preview_layout.addWidget(result_frame)
        
        layout.addLayout(preview_layout)
        
        self.setLayout(layout)
    
    def _init_engine(self):
        """初始化抠图引擎"""
        try:
            self.matting_engine = U2NetMatting()
            self.matting_engine.initialize()
            
            if self.matting_engine.is_ready():
                mode_name = self.matting_engine.get_mode_name()
                self.model_status.setText(f"✅ 模型就绪 ({mode_name})")
                self.model_status.setStyleSheet("color: #4caf50; font-size: 12px;")
            else:
                self.model_status.setText("⚠️ 模型未下载，使用模拟模式")
                self.model_status.setStyleSheet("color: #ff9800; font-size: 12px;")
        except MattingError as e:
            self.model_status.setText(f"❌ {str(e)}")
            self.model_status.setStyleSheet("color: #f44336; font-size: 12px;")
    
    def _on_mode_changed(self, index: int):
        """模式切换回调"""
        if not self.matting_engine:
            return
        
        mode = self.mode_combo.itemData(index)
        try:
            from ..ai.model_loader import ModelManager
            mgr = ModelManager.get_instance()
            mgr.switch_mode(mode)
            self.matting_engine.initialize()
            
            if self.matting_engine.is_ready():
                self.model_status.setText(f"✅ 已切换至 {mgr.get_current_mode_name()}")
                self.model_status.setStyleSheet("color: #4caf50;")
            else:
                self.model_status.setText("⚠️ 模型未下载，模式切换无效")
                self.model_status.setStyleSheet("color: #ff9800;")
        except Exception as e:
            self.model_status.setText(f"❌ 模式切换失败: {str(e)}")
            self.model_status.setStyleSheet("color: #f44336;")
    
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
            self.current_image = Image.open(file_path).convert('RGBA')
            self.input_path = file_path
            
            # 显示原图
            self._display_image(self.current_image, self.original_display)
            
            # 清空结果
            self.result_image = None
            self.result_display.setText("抠图后透明背景\n图片将在这里显示")
            self.result_display.setStyleSheet("color: #999; font-size: 13px;")
            
            # 启用抠图按钮
            self.btn_matting.setEnabled(True)
            self.btn_save.setEnabled(False)
            
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开图片: {str(e)}")
    
    def _do_matting(self):
        """执行抠图"""
        if self.current_image is None:
            return
        
        if not self.matting_engine:
            QMessageBox.warning(self, "引擎未就绪", "抠图引擎未初始化，请先下载模型")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 忙碌状态
            self.btn_matting.setEnabled(False)
            self.btn_matting.setText("⏳ 处理中...")
            
            # 获取阈值
            threshold = self.threshold_slider.value() / 100.0
            
            # 执行抠图
            original, result = self.matting_engine.process_image(
                self.current_image, threshold
            )
            
            self.result_image = result
            
            # 显示结果
            self._display_image(result, self.result_display)
            self.btn_save.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "抠图失败", f"抠图处理出错: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.btn_matting.setEnabled(True)
            self.btn_matting.setText("✨ 一键抠图")
    
    def _save_result(self):
        """保存抠图结果"""
        if self.result_image is None:
            return
        
        # 默认文件名
        import os
        default_name = os.path.splitext(os.path.basename(self.input_path))[0] + "_抠图结果.png" if self.input_path else "抠图结果.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存抠图结果",
            default_name,
            "PNG 图片 (*.png);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        try:
            self.result_image.save(file_path, 'PNG')
            QMessageBox.information(self, "保存成功", f"抠图结果已保存到:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存出错: {str(e)}")
    
    def _clear(self):
        """清空所有内容"""
        self.current_image = None
        self.result_image = None
        self.input_path = ""
        
        self.original_display.setText("点击「打开图片」\n选择要处理的图片")
        self.original_display.setStyleSheet("color: #999; font-size: 13px;")
        
        self.result_display.setText("抠图后透明背景\n图片将在这里显示")
        self.result_display.setStyleSheet("color: #999; font-size: 13px;")
        
        self.btn_matting.setEnabled(False)
        self.btn_save.setEnabled(False)
    
    def _display_image(self, pil_image: Image.Image, label: QLabel):
        """
        在 QLabel 中显示 PIL Image
        
        Args:
            pil_image: PIL Image 对象
            label: 目标 QLabel
        """
        # 缩放显示（保持比例）
        max_width = 400
        max_height = 400
        
        img_width, img_height = pil_image.size
        scale = min(max_width / img_width, max_height / img_height, 1.0)
        
        if scale < 1.0:
            new_size = (int(img_width * scale), int(img_height * scale))
            display_img = pil_image.copy()
            display_img.thumbnail(new_size, Image.LANCZOS)
        else:
            display_img = pil_image
        
        # 转换为 QPixmap
        qimage = ImageQt.ImageQt(display_img)
        pixmap = QPixmap.fromImage(qimage)
        
        label.setPixmap(pixmap)
        label.setStyleSheet("")
