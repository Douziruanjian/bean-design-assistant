#!/usr/bin/env python3
"""
豆子设计助手 - 主入口

豆子设计助手是一款面向图文店的桌面应用
提供工单管理、报价计算、客户管理功能
"""
import sys
import os

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.main_window import MainWindow


def main():
    """应用主函数"""
    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("豆子设计助手")
    app.setOrganizationName("Douzi Software")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
