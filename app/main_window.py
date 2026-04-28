"""
PyQt6 主窗口

豆子设计助手的主界面框架
"""
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QPushButton, QLabel, QFrame,
                             QMenuBar, QMenu, QAction, QToolBar, QStatusBar,
                             QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from ..database.db_manager import DatabaseManager
from ..modules.order import OrderManager
from ..modules.quotation import QuotationManager
from ..modules.customer import CustomerManager

from .ui.ai_matting_page import AiMattingPage
from .ui.ai_ocr_page import AiOcrPage


class NavigationButton(QPushButton):
    """侧边导航按钮"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(50)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #333333;
                font-size: 14px;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:checked {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
        """)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化数据库和管理器
        self.db = DatabaseManager()
        self.order_manager = OrderManager(self.db)
        self.quotation_manager = QuotationManager(self.db)
        self.customer_manager = CustomerManager(self.db)
        
        # 初始化 UI
        self._init_ui()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        # 状态栏初始提示 AI 模型状态
        self._update_ai_status()
        
        # 设置窗口属性
        self.setWindowTitle("豆子设计助手")
        self.setMinimumSize(1024, 768)
        self.resize(1200, 800)
        
        # 高 DPI 适配
        self.setAttribute(Qt.WidgetAttribute.AA_EnableHighDpiScaling, True)
    
    def _init_ui(self):
        """初始化用户界面"""
        # 中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局（水平）
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # 左侧导航栏
        navigation_frame = QFrame()
        navigation_frame.setFixedWidth(200)
        navigation_frame.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border-right: 1px solid #e0e0e0;
            }
        """)
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 20, 0, 0)
        nav_layout.setSpacing(5)
        navigation_frame.setLayout(nav_layout)
        
        # 导航按钮
        self.nav_buttons = []
        self.pages = []
        
        # ── 业务模块 ──
        section_label = QLabel("    业务管理")
        section_label.setStyleSheet("color: #999; font-size: 11px; padding: 5px 0;")
        nav_layout.addWidget(section_label)
        
        # 工单管理
        btn_orders = NavigationButton("📋 工单管理")
        btn_orders.clicked.connect(lambda: self._switch_page(0))
        nav_layout.addWidget(btn_orders)
        self.nav_buttons.append(btn_orders)
        
        # 报价管理
        btn_quotations = NavigationButton("💰 报价管理")
        btn_quotations.clicked.connect(lambda: self._switch_page(1))
        nav_layout.addWidget(btn_quotations)
        self.nav_buttons.append(btn_quotations)
        
        # 客户管理
        btn_customers = NavigationButton("👥 客户管理")
        btn_customers.clicked.connect(lambda: self._switch_page(2))
        nav_layout.addWidget(btn_customers)
        self.nav_buttons.append(btn_customers)
        
        # ── AI 功能 ──
        spacer = QFrame()
        spacer.setFixedHeight(10)
        nav_layout.addWidget(spacer)
        
        ai_label = QLabel("    AI 工具")
        ai_label.setStyleSheet("color: #999; font-size: 11px; padding: 5px 0;")
        nav_layout.addWidget(ai_label)
        
        # AI 抠图
        btn_matting = NavigationButton("🎨 AI 抠图")
        btn_matting.clicked.connect(lambda: self._switch_page(3))
        nav_layout.addWidget(btn_matting)
        self.nav_buttons.append(btn_matting)
        
        # 文字识别(OCR)
        btn_ocr = NavigationButton("📝 文字识别")
        btn_ocr.clicked.connect(lambda: self._switch_page(4))
        nav_layout.addWidget(btn_ocr)
        self.nav_buttons.append(btn_ocr)
        
        # ── 系统 ──
        spacer2 = QFrame()
        spacer2.setFixedHeight(10)
        nav_layout.addWidget(spacer2)
        
        sys_label = QLabel("    系统")
        sys_label.setStyleSheet("color: #999; font-size: 11px; padding: 5px 0;")
        nav_layout.addWidget(sys_label)
        
        # 设置
        btn_settings = NavigationButton("⚙️ 设置")
        btn_settings.clicked.connect(lambda: self._switch_page(5))
        nav_layout.addWidget(btn_settings)
        self.nav_buttons.append(btn_settings)
        
        nav_layout.addStretch()
        
        main_layout.addWidget(navigation_frame)
        
        # 右侧内容区
        content_frame = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_frame.setLayout(content_layout)
        
        # 页面堆栈
        self.stack_widget = QStackedWidget()
        
        # 创建各页面
        self.pages.append(self._create_orders_page())       # 0
        self.pages.append(self._create_quotations_page())   # 1
        self.pages.append(self._create_customers_page())    # 2
        self.pages.append(AiMattingPage())                  # 3 - AI 抠图
        self.pages.append(AiOcrPage())                      # 4 - 文字识别
        self.pages.append(self._create_settings_page())     # 5 - 设置
        
        for page in self.pages:
            self.stack_widget.addWidget(page)
        
        content_layout.addWidget(self.stack_widget)
        main_layout.addWidget(content_frame)
        
        # 默认选中第一个按钮
        self.nav_buttons[0].setChecked(True)
    
    def _create_orders_page(self) -> QWidget:
        """创建工单管理页面"""
        page = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("工单管理")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 占位内容
        placeholder = QLabel("工单列表将在这里显示\n\n点击\"新建工单\"按钮开始创建工单")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #999; font-size: 14px;")
        layout.addWidget(placeholder)
        
        page.setLayout(layout)
        return page
    
    def _create_quotations_page(self) -> QWidget:
        """创建报价管理页面"""
        page = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("报价管理")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        placeholder = QLabel("报价单列表将在这里显示\n\n点击\"新建报价\"按钮开始创建报价单")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #999; font-size: 14px;")
        layout.addWidget(placeholder)
        
        page.setLayout(layout)
        return page
    
    def _create_customers_page(self) -> QWidget:
        """创建客户管理页面"""
        page = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("客户管理")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        placeholder = QLabel("客户列表将在这里显示\n\n点击\"新建客户\"按钮开始添加客户")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #999; font-size: 14px;")
        layout.addWidget(placeholder)
        
        page.setLayout(layout)
        return page
    
    def _create_settings_page(self) -> QWidget:
        """创建设置页面"""
        page = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("设置")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        layout.addWidget(title)
        
        placeholder = QLabel("系统设置将在这里配置")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #999; font-size: 14px;")
        layout.addWidget(placeholder)
        
        page.setLayout(layout)
        return page
    
    def _switch_page(self, index: int):
        """切换页面"""
        self.stack_widget.setCurrentIndex(index)
        
        # 更新按钮状态
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        export_action = QAction("导出 Excel(&E)", self)
        export_action.triggered.connect(self._export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # AI 菜单
        ai_menu = menubar.addMenu("AI(&A)")
        
        matting_action = QAction("AI 抠图(&M)", self)
        matting_action.triggered.connect(lambda: self._switch_page(3))
        ai_menu.addAction(matting_action)
        
        ocr_action = QAction("文字识别(&O)", self)
        ocr_action.triggered.connect(lambda: self._switch_page(4))
        ai_menu.addAction(ocr_action)
        
        ai_menu.addSeparator()
        
        download_action = QAction("下载 AI 模型(&D)", self)
        download_action.triggered.connect(self._download_models)
        ai_menu.addAction(download_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 添加工具栏按钮（简化版）
        toolbar.addAction("新建")
        toolbar.addAction("保存")
        toolbar.addAction("刷新")
    
    def _create_status_bar(self):
        """创建状态栏"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 数据库状态
        db_status = QLabel("数据库：✓ 已连接")
        db_status.setStyleSheet("color: #4caf50; margin-right: 15px;")
        statusbar.addPermanentWidget(db_status)
        
        # AI 模型状态（稍后更新）
        self.ai_status_label = QLabel("AI 模型：——")
        self.ai_status_label.setStyleSheet("color: #999; margin-right: 15px;")
        statusbar.addPermanentWidget(self.ai_status_label)
        
        # 用户信息
        user_info = QLabel("当前用户：管理员")
        statusbar.addPermanentWidget(user_info)
        
        # 默认消息
        statusbar.showMessage("就绪")
    
    def _update_ai_status(self):
        """更新 AI 模型状态"""
        try:
            from ..ai.model_loader import get_available_modes, check_model_file, U2NET_FP32_PATH, U2NET_INT8_PATH
            
            has_fp32 = check_model_file(U2NET_FP32_PATH)
            has_int8 = check_model_file(U2NET_INT8_PATH)
            
            if has_fp32 and has_int8:
                self.ai_status_label.setText("AI 模型：✓ FP32+INT8")
                self.ai_status_label.setStyleSheet("color: #4caf50; margin-right: 15px;")
            elif has_fp32:
                self.ai_status_label.setText("AI 模型：✓ FP32")
                self.ai_status_label.setStyleSheet("color: #4caf50; margin-right: 15px;")
            elif has_int8:
                self.ai_status_label.setText("AI 模型：✓ INT8")
                self.ai_status_label.setStyleSheet("color: #4caf50; margin-right: 15px;")
            else:
                self.ai_status_label.setText("AI 模型：⚠️ 未下载")
                self.ai_status_label.setStyleSheet("color: #ff9800; margin-right: 15px;")
        except Exception:
            self.ai_status_label.setText("AI 模型：——")
    
    def _export_data(self):
        """导出数据"""
        QMessageBox.information(self, "导出", "导出功能开发中...")
    
    def _download_models(self):
        """下载 AI 模型"""
        QMessageBox.information(
            self,
            "下载 AI 模型",
            "模型下载功能需要单独运行 download_models.py 脚本\n\n"
            "请执行: python download_models.py"
        )
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于豆子设计助手",
            "豆子设计助手 V1.0.0\n\n"
            "一款面向图文店的桌面应用\n"
            "提供工单管理、报价计算、客户管理、AI 抠图、文字识别功能\n\n"
            "© 2026 豆子软件"
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(
            self,
            '确认退出',
            '确定要退出豆子设计助手吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 关闭数据库连接
            self.db.close()
            event.accept()
        else:
            event.ignore()
