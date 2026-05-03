"""
PyQt6 主窗口 — 豆子设计助手完整功能版

包含工单管理、报价管理、客户管理、AI 工具、设置页面
所有功能页面代码集成在此文件，不创建额外页面文件。
"""
import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QApplication,
    QMenuBar, QMenu, QToolBar, QStatusBar,
    QMessageBox, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QLineEdit,
    QComboBox, QTextEdit, QSpinBox, QDoubleSpinBox,
    QGroupBox, QGridLayout, QFileDialog, QApplication,
    QSplitter, QDialogButtonBox, QDateEdit,
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QAction

from app.database.db_manager import DatabaseManager
from app.database.models import (
    Order, Quotation, Customer, QuotationItem,
    get_current_datetime
)
from app.modules.order import OrderManager
from app.modules.quotation import QuotationManager
from app.modules.customer import CustomerManager

# Phase 3 激活码客户端（可选）
try:
    from app.license.client import LicenseClient
    HAS_LICENSE = True
except ImportError:
    HAS_LICENSE = False

# Phase 2 AI 页面（可选）
try:
    from app.ui.ai_matting_page import AiMattingPage
    from app.ui.ai_ocr_page import AiOcrPage
    HAS_AI = True
except ImportError:
    HAS_AI = False


# ══════════════════════════════════════════════
# 样式 & 映射常量
# ══════════════════════════════════════════════

PRIMARY = "#1976d2"
BG = "#fafafa"

TABLE_S = """
    QTableWidget {
        border: 1px solid #e0e0e0;
        gridline-color: #f0f0f0;
        background-color: white;
        alternate-background-color: #fafafa;
    }
    QHeaderView::section {
        background-color: #f5f5f5; color: #333;
        padding: 8px; border: none;
        border-bottom: 2px solid #e0e0e0;
        font-weight: bold;
    }
"""
BTN1 = """
    QPushButton {
        background-color: #1976d2; color: white;
        border: none; border-radius: 4px;
        padding: 8px 16px; font-size: 13px;
    }
    QPushButton:hover { background-color: #1565c0; }
    QPushButton:pressed { background-color: #0d47a1; }
"""
BTN2 = """
    QPushButton {
        background-color: white; color: #333;
        border: 1px solid #ccc; border-radius: 4px;
        padding: 8px 16px; font-size: 13px;
    }
    QPushButton:hover { background-color: #f5f5f5; }
"""
BTN3 = """
    QPushButton {
        background-color: #e53935; color: white;
        border: none; border-radius: 4px;
        padding: 8px 16px; font-size: 13px;
    }
    QPushButton:hover { background-color: #c62828; }
"""

OS = {
    "pending": "待处理", "in_progress": "进行中",
    "completed": "已完成", "cancelled": "已取消",
}
OS_R = {v: k for k, v in OS.items()}

QS = {"draft": "草稿", "sent": "已发给客户", "confirmed": "客户确认",
       "converted": "已转工单", "voided": "作废"}
QS_R = {v: k for k, v in QS.items()}


# ══════════════════════════════════════════════
# 对话框
# ══════════════════════════════════════════════

class OrderDialog(QDialog):
    """工单编辑对话框"""
    def __init__(self, parent=None, order: Order = None, customers: list = None, db=None):
        super().__init__(parent)
        self.result_order = None
        self.order = order
        self.customers = customers or []
        self.db = db
        self.setWindowTitle("编辑工单" if order else "新建工单")
        self.setMinimumWidth(480)

        # 客户下拉选择（从数据库加载）
        self.customer_name = QComboBox()
        self.customer_name.setEditable(False)
        self.customer_name.setMinimumHeight(30)
        # PyQt6 6.11 不支持 setPlaceholderText for QComboBox
        # self.customer_name.setPlaceholderText("请选择客户")
        if self.customers:
            for c in self.customers:
                self.customer_name.addItem(c.name, c.id)
        else:
            self.customer_name.addItem("请先添加客户", -1)
        self.customer_name.currentIndexChanged.connect(self._on_customer_changed)

        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("选客户后自动填充")
        self.customer_phone.setReadOnly(True)
        self.customer_phone.setMinimumHeight(30)

        self.description = QTextEdit()
        self.description.setPlaceholderText("请详细描述工单内容（物料类型、规格、数量等）")
        self.description.setMinimumHeight(80)

        self.total_amount = QDoubleSpinBox()
        self.total_amount.setRange(0, 999999.99)
        self.total_amount.setPrefix("¥ ")
        self.total_amount.setDecimals(2)
        self.total_amount.setValue(0.0)
        self.total_amount.setMinimumHeight(30)

        self.status_combo = QComboBox()
        for v in ["待处理", "进行中", "已完成", "已取消"]:
            self.status_combo.addItem(v)
        self.status_combo.setMinimumHeight(30)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("客户名称 *", self.customer_name)
        form.addRow("联系电话", self.customer_phone)
        form.addRow("工单描述 *", self.description)
        form.addRow("金额", self.total_amount)
        form.addRow("状态", self.status_combo)

        b = QHBoxLayout()
        b.addStretch()
        s = QPushButton("✅ 保存")
        s.setStyleSheet(BTN1)
        s.clicked.connect(self._accept)
        b.addWidget(s)
        c = QPushButton("取消")
        c.setStyleSheet(BTN2)
        c.clicked.connect(self.reject)
        b.addWidget(c)

        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addLayout(b)

        if order:
            # 选择已有客户
            idx = self.customer_name.findText(order.customer_name)
            if idx >= 0:
                self.customer_name.setCurrentIndex(idx)
            else:
                self.customer_name.addItem(order.customer_name)
                self.customer_name.setCurrentIndex(self.customer_name.count() - 1)
            self.customer_phone.setText(order.customer_phone)
            self.description.setPlainText(order.description)
            self.total_amount.setValue(order.total_amount)
            self.status_combo.setCurrentText(OS.get(order.status, "待处理"))

    def _on_customer_changed(self, idx):
        """选择客户后自动填充电话"""
        if idx < 0 or idx >= len(self.customers):
            return
        c = self.customers[idx]
        self.customer_phone.setText(c.phone or "")
        # 检查客户欠款
        if self.db:
            has_debt, debt_amount = self.db.get_customer_debt_warning(c.name)
            if has_debt:
                QMessageBox.warning(
                    self.parent() or self, "客户欠款提醒",
                    f"客户「{c.name}」当前欠款 ¥{debt_amount:.2f}，请注意收款安排。",
                    QMessageBox.StandardButton.Ok)

    def _accept(self):
        name = self.customer_name.currentText().strip()
        desc = self.description.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请选择客户名称"); return
        if not desc:
            QMessageBox.warning(self, "提示", "请输入工单描述"); return
        o = Order(
            customer_name=name,
            customer_phone=self.customer_phone.text().strip(),
            description=desc,
            total_amount=self.total_amount.value(),
            status=OS_R.get(self.status_combo.currentText(), "pending"),
        )
        if self.order and self.order.id:
            o.id = self.order.id
            o.order_no = self.order.order_no
        self.result_order = o
        self.accept()


class QuotationDialog(QDialog):
    """报价单编辑对话框 — 支持多行项目"""
    def __init__(self, parent=None, quotation: Quotation = None, customers: list = None, db=None):
        super().__init__(parent)
        self.result = None
        self.quotation = quotation
        self.items: list[dict] = []
        self.customers = customers or []
        self.db = db
        self.setWindowTitle("编辑报价单" if quotation else "新建报价单")
        self.setMinimumWidth(640)
        self.setMinimumHeight(520)

        lo = QVBoxLayout(self)

        form = QFormLayout()
        self.customer_name = QComboBox()
        self.customer_name.setEditable(False)
        self.customer_name.setMinimumHeight(30)
        # PyQt6 6.11 不支持 QComboBox.setPlaceholderText
        if self.customers:
            for c in self.customers:
                self.customer_name.addItem(c.name, c.id)
            self.customer_name.setCurrentIndex(0)
        else:
            self.customer_name.addItem("请先添加客户", -1)
        self.customer_name.currentIndexChanged.connect(self._on_customer_changed)
        form.addRow("客户名称 *", self.customer_name)

        self.valid_days = QSpinBox()
        self.valid_days.setRange(1, 365)
        self.valid_days.setValue(7)
        self.valid_days.setSuffix(" 天")
        self.valid_days.setMinimumHeight(30)
        form.addRow("有效期", self.valid_days)

        self.status_combo = QComboBox()
        for v in ["草稿", "已发给客户", "客户确认", "已转工单", "作废"]:
            self.status_combo.addItem(v)
        self.status_combo.setMinimumHeight(30)
        form.addRow("状态", self.status_combo)
        lo.addLayout(form)

        g = QGroupBox("报价项目")
        g.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        gl = QVBoxLayout(g)

        self.item_table = QTableWidget(0, 4)
        self.item_table.setHorizontalHeaderLabels(["项目名称", "数量", "单价", "金额"])
        self.item_table.horizontalHeader().setStretchLastSection(True)
        self.item_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.item_table.setAlternatingRowColors(True)
        self.item_table.setStyleSheet(TABLE_S)
        self.item_table.setMinimumHeight(160)
        gl.addWidget(self.item_table)

        h = QHBoxLayout()
        self.it_name = QLineEdit()
        self.it_name.setPlaceholderText("项目名称（如 A3打印）")
        self.it_name.setMinimumHeight(30)
        h.addWidget(self.it_name, 3)
        self.it_qty = QSpinBox()
        self.it_qty.setRange(1, 99999)
        self.it_qty.setValue(1)
        self.it_qty.setMinimumHeight(30)
        h.addWidget(self.it_qty, 1)
        self.it_price = QDoubleSpinBox()
        self.it_price.setRange(0, 999999)
        self.it_price.setPrefix("¥ ")
        self.it_price.setDecimals(2)
        self.it_price.setMinimumHeight(30)
        h.addWidget(self.it_price, 2)
        a = QPushButton("添加")
        a.setStyleSheet(BTN1)
        a.clicked.connect(self._add)
        a.setMinimumHeight(30)
        h.addWidget(a)
        d = QPushButton("删除")
        d.setStyleSheet(BTN3)
        d.clicked.connect(self._remove)
        d.setMinimumHeight(30)
        h.addWidget(d)
        gl.addLayout(h)

        tl = QHBoxLayout()
        tl.addStretch()
        tl.addWidget(QLabel("合计："))
        self.total_lbl = QLabel("¥ 0.00")
        self.total_lbl.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.total_lbl.setStyleSheet(f"color: {PRIMARY};")
        tl.addWidget(self.total_lbl)
        gl.addLayout(tl)
        lo.addWidget(g)

        b = QHBoxLayout()
        b.addStretch()
        s = QPushButton("✅ 保存")
        s.setStyleSheet(BTN1)
        s.clicked.connect(self._accept)
        b.addWidget(s)
        c = QPushButton("取消")
        c.setStyleSheet(BTN2)
        c.clicked.connect(self.reject)
        b.addWidget(c)
        lo.addLayout(b)

        if quotation:
            idx = self.customer_name.findText(quotation.customer_name)
            if idx >= 0:
                self.customer_name.setCurrentIndex(idx)
            else:
                self.customer_name.addItem(quotation.customer_name)
                self.customer_name.setCurrentIndex(self.customer_name.count() - 1)
            self.status_combo.setCurrentText(QS.get(quotation.status, "草稿"))
            for it in quotation.items:
                self.items.append(dict(name=it.name, qty=it.qty,
                                       unit_price=it.unit_price, amount=it.amount))
            self._refresh_table()

    def _add(self):
        n = self.it_name.text().strip()
        if not n:
            QMessageBox.warning(self, "提示", "请输入项目名称"); return
        q = self.it_qty.value()
        p = self.it_price.value()
        self.items.append(dict(name=n, qty=q, unit_price=p, amount=q * p))
        self.it_name.clear()
        self.it_qty.setValue(1)
        self.it_price.setValue(0.0)
        self._refresh_table()

    def _remove(self):
        r = self.item_table.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的项目"); return
        self.items.pop(r)
        self._refresh_table()

    def _refresh_table(self):
        t = 0.0
        self.item_table.setRowCount(len(self.items))
        for i, it in enumerate(self.items):
            self.item_table.setItem(i, 0, QTableWidgetItem(it["name"]))
            self.item_table.setItem(i, 1, QTableWidgetItem(str(it["qty"])))
            self.item_table.setItem(i, 2,
                QTableWidgetItem(f"¥ {it['unit_price']:.2f}"))
            self.item_table.setItem(i, 3,
                QTableWidgetItem(f"¥ {it['amount']:.2f}"))
            t += it["amount"]
        self.total_lbl.setText(f"¥ {t:.2f}")

    def _on_customer_changed(self, idx):
        """选择客户后检查欠款"""
        if not self.db or idx < 0 or idx >= len(self.customers):
            return
        c = self.customers[idx]
        has_debt, debt_amount = self.db.get_customer_debt_warning(c.name)
        if has_debt:
            QMessageBox.warning(
                self.parent() or self, "客户欠款提醒",
                f"客户「{c.name}」当前欠款 ¥{debt_amount:.2f}，请注意收款安排。",
                QMessageBox.StandardButton.Ok)

    def _accept(self):
        n = self.customer_name.currentText().strip()
        if not n:
            QMessageBox.warning(self, "提示", "请选择客户名称"); return
        if not self.items:
            QMessageBox.warning(self, "提示", "请至少添加一个报价项目"); return
        
        # 获取 customer_id
        cid = None
        if self.customer_name.currentIndex() >= 0:
            cid = self.customer_name.currentData()
        
        self.result = {
            "customer_name": n,
            "customer_id": cid,
            "items": self.items,
            "valid_days": self.valid_days.value(),
            "status": QS_R.get(self.status_combo.currentText(), "draft"),
        }
        if self.quotation and self.quotation.id:
            self.result["id"] = self.quotation.id
            self.result["quotation_no"] = self.quotation.quotation_no
        self.accept()


class CustomerDialog(QDialog):
    """客户编辑对话框"""
    def __init__(self, parent=None, customer: Customer = None):
        super().__init__(parent)
        self.result = None
        self.customer = customer
        self.setWindowTitle("编辑客户" if customer else "新建客户")
        self.setMinimumWidth(450)
        self._ui()
        if customer:
            self.name_edit.setText(customer.name)
            self.phone_edit.setText(customer.phone)
            self.address_edit.setText(customer.address)
            self.notes_edit.setPlainText(customer.notes)

    def _ui(self):
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入客户名称")
        self.name_edit.setMinimumHeight(30)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("请输入联系电话")
        self.phone_edit.setMinimumHeight(30)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("请输入地址")
        self.address_edit.setMinimumHeight(30)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("备注信息（可选）")
        self.notes_edit.setMaximumHeight(80)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("客户名称 *", self.name_edit)
        form.addRow("联系电话", self.phone_edit)
        form.addRow("地址", self.address_edit)
        form.addRow("备注", self.notes_edit)

        b = QHBoxLayout()
        b.addStretch()
        s = QPushButton("✅ 保存")
        s.setStyleSheet(BTN1)
        s.clicked.connect(self._accept)
        b.addWidget(s)
        c = QPushButton("取消")
        c.setStyleSheet(BTN2)
        c.clicked.connect(self.reject)
        b.addWidget(c)

        lo = QVBoxLayout(self)
        lo.addLayout(form)
        lo.addLayout(b)

    def _accept(self):
        n = self.name_edit.text().strip()
        if not n:
            QMessageBox.warning(self, "提示", "请输入客户名称"); return
        self.result = dict(
            name=n, phone=self.phone_edit.text().strip(),
            address=self.address_edit.text().strip(),
            notes=self.notes_edit.toPlainText().strip(),
        )
        if self.customer and self.customer.id:
            self.result["id"] = self.customer.id
        self.accept()


class CustomerDetailDialog(QDialog):
    """客户360°详情对话框"""
    def __init__(self, customer: Customer, total_paid: float,
                 total_debt: float, db, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.total_paid = total_paid
        self.total_debt = total_debt
        self.db = db
        
        self.setWindowTitle(f"客户详情 - {customer.name}")
        self.setMinimumWidth(750)
        self.setMinimumHeight(600)
        
        lo = QVBoxLayout(self)
        lo.setSpacing(12)
        
        # === 基础信息 ===
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout(info_group)
        info_layout.addRow("客户名称：", QLabel(customer.name))
        info_layout.addRow("联系电话：", QLabel(customer.phone or "未填写"))
        info_layout.addRow("地址：", QLabel(customer.address or "未填写"))
        info_layout.addRow("备注：", QLabel(customer.notes or "无"))
        
        debt_label = QLabel(f"¥ {total_debt:.2f}")
        if total_debt > 0:
            debt_label.setStyleSheet("color: #e53935; font-size: 14px; font-weight: bold;")
        else:
            debt_label.setStyleSheet("color: #43a047; font-size: 14px;")
        info_layout.addRow("当前欠款：", debt_label)
        
        stats = QLabel(f"累计消费：¥ {customer.total_spent:.2f}  |  "
                       f"累计已付：¥ {total_paid:.2f}  |  "
                       f"工单数：{customer.total_orders}")
        stats.setStyleSheet("padding: 8px; background: #f5f5f5; border-radius: 4px;")
        info_layout.addRow(stats)
        lo.addWidget(info_group)
        
        # === 历史报价 ===
        quote_group = QGroupBox("历史报价记录")
        qv = QVBoxLayout(quote_group)
        self.qt = QTableWidget(0, 4)
        self.qt.setHorizontalHeaderLabels(["报价单号", "金额", "状态", "日期"])
        self.qt.setAlternatingRowColors(True)
        self.qt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.qt.horizontalHeader().setStretchLastSection(True)
        qv.addWidget(self.qt)
        lo.addWidget(quote_group)
        
        # === 历史工单 ===
        order_group = QGroupBox("历史工单记录")
        ov = QVBoxLayout(order_group)
        self.ot2 = QTableWidget(0, 6)
        self.ot2.setHorizontalHeaderLabels(
            ["工单号", "金额", "已收", "未收", "收款状态", "日期"])
        self.ot2.setAlternatingRowColors(True)
        self.ot2.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ot2.horizontalHeader().setStretchLastSection(True)
        ov.addWidget(self.ot2)
        lo.addWidget(order_group)
        
        # 加载数据
        self._load_data()
        
        b = QHBoxLayout()
        b.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(BTN2)
        close_btn.clicked.connect(self.accept)
        b.addWidget(close_btn)
        lo.addLayout(b)
    
    def _load_data(self):
        """加载客户历史报价和工单数据"""
        try:
            from app.database.models import QUOTATION_STATUS
            
            # 加载历史报价
            quotations = self.db.get_customer_quotations(self.customer.name)
            self.qt.setRowCount(len(quotations))
            for i, q in enumerate(quotations):
                self.qt.setItem(i, 0, QTableWidgetItem(q.get('quotation_no', '')))
                self.qt.setItem(i, 1, QTableWidgetItem(f"¥ {float(q.get('total_amount', 0)):.2f}"))
                status_key = q.get('status', 'draft')
                self.qt.setItem(i, 2, QTableWidgetItem(
                    QUOTATION_STATUS.get(status_key, status_key)))
                created = (q.get('created_at') or '')[:10]
                self.qt.setItem(i, 3, QTableWidgetItem(created))
            
            # 加载历史工单
            orders = self.db.get_customer_orders(self.customer.name)
            self.ot2.setRowCount(len(orders))
            ps_text = {"unpaid": "未付款", "partial": "部分付款", "paid": "已结清"}
            ps_colors = {"unpaid": "#e53935", "partial": "#fb8c00", "paid": "#43a047"}
            
            for i, o in enumerate(orders):
                self.ot2.setItem(i, 0, QTableWidgetItem(o.get('order_no', '')))
                self.ot2.setItem(i, 1, QTableWidgetItem(f"¥ {float(o.get('total_amount', 0)):.2f}"))
                self.ot2.setItem(i, 2, QTableWidgetItem(f"¥ {float(o.get('paid_amount', 0)):.2f}"))
                self.ot2.setItem(i, 3, QTableWidgetItem(f"¥ {float(o.get('unpaid_amount', 0)):.2f}"))
                
                ps = o.get('payment_status', 'unpaid') or 'unpaid'
                ps_item = QTableWidgetItem(ps_text.get(ps, '未付款'))
                ps_item.setForeground(QColor(ps_colors.get(ps, '#999')))
                font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
                ps_item.setFont(font)
                self.ot2.setItem(i, 4, ps_item)
                
                created = (o.get('created_at') or '')[:10]
                self.ot2.setItem(i, 5, QTableWidgetItem(created))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载数据失败：{e}")
            import traceback
            traceback.print_exc()
            self.accept()


# ══════════════════════════════════════════════
# 导航按钮
# ══════════════════════════════════════════════

class NavBtn(QPushButton):
    """侧边导航按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setMinimumHeight(50)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: none;
                color: #333; font-size: 14px;
                text-align: left; padding-left: 20px;
            }
            QPushButton:hover { background-color: #f0f0f0; }
            QPushButton:checked {
                background-color: #e3f2fd; color: #1976d2;
                font-weight: bold;
                border-left: 3px solid #1976d2;
            }
        """)


# ══════════════════════════════════════════════
# 主窗口
# ══════════════════════════════════════════════

class MainWindow(QMainWindow):
    """豆子设计助手主窗口"""
    IDX_ORDERS = 0
    IDX_QUOTATIONS = 1
    IDX_CUSTOMERS = 2
    IDX_FINANCE = 3
    IDX_MATTING = 4
    IDX_OCR = 5
    IDX_SETTINGS = 6

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.order_manager = OrderManager(self.db)
        self.quotation_manager = QuotationManager(self.db)
        self.customer_manager = CustomerManager(self.db)
        # Phase 3 license client
        self.license_client = None
        if HAS_LICENSE:
            try:
                self.license_client = LicenseClient()
            except Exception:
                pass

        self._ui()
        self._menu_bar()
        self._tool_bar()
        self._status_bar()

        self.setWindowTitle("豆子设计助手")
        self.setMinimumSize(1024, 768)
        self.resize(1200, 800)

        QTimer.singleShot(100, self._refresh_orders)
        QTimer.singleShot(150, self._refresh_quotations)
        QTimer.singleShot(200, self._refresh_customers)

    # ── 界面布局 ──────────────────────────────

    def _ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        ml = QHBoxLayout()
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)
        cw.setLayout(ml)

        # 导航
        nf = QFrame()
        nf.setFixedWidth(200)
        nf.setStyleSheet(f"QFrame {{ background-color: {BG}; border-right: 1px solid #e0e0e0; }}")
        nl = QVBoxLayout()
        nl.setContentsMargins(0, 20, 0, 0)
        nl.setSpacing(5)
        nf.setLayout(nl)

        self.nav_btns = []

        def sec(t):
            l = QLabel(t)
            l.setStyleSheet("color: #999; font-size: 11px; padding: 10px 20px 2px 20px;")
            nl.addWidget(l)

        def nav(t, i):
            b = NavBtn(t)
            b.clicked.connect(lambda _, x=i: self._switch(x))
            nl.addWidget(b)
            self.nav_btns.append(b)

        sec("    业务管理")
        nav("📋 工单管理", self.IDX_ORDERS)
        nav("💰 报价管理", self.IDX_QUOTATIONS)
        nav("👥 客户管理", self.IDX_CUSTOMERS)
        sec("    AI 工具")
        nav("🎨 AI 抠图", self.IDX_MATTING)
        nav("📝 文字识别", self.IDX_OCR)
        sec("    财务管理")
        nav("📊 财务", self.IDX_FINANCE)
        sec("    系统")
        nav("⚙️ 设置", self.IDX_SETTINGS)
        nl.addStretch()
        ml.addWidget(nf)

        # 内容区
        cf = QFrame()
        cl = QVBoxLayout()
        cl.setContentsMargins(20, 20, 20, 20)
        cf.setLayout(cl)

        self.stack = QStackedWidget()

        # 页面列表
        if HAS_AI:
            m_page = AiMattingPage()
            o_page = AiOcrPage()
        else:
            m_page = self._ph_page("AI 抠图", "AI 模块未安装")
            o_page = self._ph_page("文字识别", "AI 模块未安装")

        pages = [
            self._orders_page(),        # 0
            self._quotations_page(),    # 1
            self._customers_page(),     # 2
            self._finance_page(),       # 3
            m_page,                     # 4
            o_page,                     # 5
            self._settings_page(),      # 6
        ]
        for p in pages:
            self.stack.addWidget(p)
        cl.addWidget(self.stack)
        ml.addWidget(cf)
        self.nav_btns[0].setChecked(True)

    def _ph_page(self, title, msg):
        p = QWidget()
        l = QVBoxLayout()
        t = QLabel(title)
        t.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        l.addWidget(t)
        m = QLabel(msg)
        m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        m.setStyleSheet("color: #999; font-size: 14px;")
        l.addWidget(m)
        p.setLayout(l)
        return p

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_btns):
            b.setChecked(i == idx)
        # 切换到财务页面时刷新数据
        if idx == self.IDX_FINANCE:
            self._refresh_finance()

    # ══════════════════════════════════════════
    # 财务看板页面
    # ══════════════════════════════════════════

    def _finance_page(self):
        p = QWidget()
        lo = QVBoxLayout()
        lo.setSpacing(12)

        # 标题
        t = QLabel("📊 财务看板")
        t.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        lo.addWidget(t)

        # === 营收概览卡片 ===
        card_style = """
            QFrame {
                background: white; border-radius: 8px;
                border: 1px solid #e0e0e0; padding: 15px;
            }
        """
        value_style = "font-size: 24px; font-weight: bold; color: #1976d2;"
        label_style = "font-size: 12px; color: #666;"

        card_layout = QHBoxLayout()
        card_layout.setSpacing(15)

        def make_card(title, value_key):
            f = QFrame()
            f.setStyleSheet(card_style)
            vl = QVBoxLayout(f)
            l = QLabel(title)
            l.setStyleSheet(label_style)
            vl.addWidget(l)
            v = QLabel("¥ 0.00")
            v.setStyleSheet(value_style)
            v.setObjectName(value_key)
            vl.addWidget(v)
            card_layout.addWidget(f)
            return v

        self.lbl_monthly_revenue = make_card("本月营收", "monthly_revenue")
        self.lbl_monthly_debt = make_card("本月欠款", "monthly_debt")
        self.lbl_total_revenue = make_card("总营收", "total_revenue")
        self.lbl_total_debt = make_card("总欠款", "total_debt")
        lo.addLayout(card_layout)

        # === 欠款客户清单 ===
        dt = QLabel("⚡ 欠款客户清单")
        dt.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        lo.addWidget(dt)

        self.debt_table = QTableWidget(0, 4)
        self.debt_table.setHorizontalHeaderLabels(
            ["客户名称", "欠款总额", "未结清工单数", "操作"])
        self.debt_table.setAlternatingRowColors(True)
        self.debt_table.setStyleSheet(TABLE_S)
        self.debt_table.horizontalHeader().setStretchLastSection(True)
        self.debt_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lo.addWidget(self.debt_table)

        # === 收款流水 ===
        pt = QLabel("💰 收款流水")
        pt.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        lo.addWidget(pt)

        self.payment_table = QTableWidget(0, 7)
        self.payment_table.setHorizontalHeaderLabels(
            ["日期", "工单号", "客户", "金额", "支付方式", "收款类型", "备注"])
        self.payment_table.setAlternatingRowColors(True)
        self.payment_table.setStyleSheet(TABLE_S)
        self.payment_table.horizontalHeader().setStretchLastSection(True)
        self.payment_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lo.addWidget(self.payment_table)

        p.setLayout(lo)
        return p

    def _refresh_finance(self):
        """刷新财务看板数据"""
        overview = self.db.get_finance_overview()
        self.lbl_monthly_revenue.setText(f"¥ {overview['monthly_revenue']:.2f}")
        self.lbl_monthly_debt.setText(f"¥ {overview['monthly_debt']:.2f}")
        self.lbl_total_revenue.setText(f"¥ {overview['total_revenue']:.2f}")
        self.lbl_total_debt.setText(f"¥ {overview['total_debt']:.2f}")

        # 欠款客户清单
        debtors = self.db.get_debtor_list()
        self.debt_table.setRowCount(len(debtors))
        for i, d in enumerate(debtors):
            self.debt_table.setItem(i, 0, QTableWidgetItem(d['customer_name']))
            debt_item = QTableWidgetItem(f"¥ {d['total_debt']:.2f}")
            debt_item.setForeground(QColor("#e53935"))
            debt_item.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
            self.debt_table.setItem(i, 1, debt_item)
            self.debt_table.setItem(i, 2, QTableWidgetItem(str(d['order_count'])))
            
            # 催款按钮
            btn = QPushButton("📞 催款")
            btn.setStyleSheet("""
                QPushButton { background: #ffebee; color: #c62828;
                    border: 1px solid #ef9a9a; border-radius: 4px;
                    padding: 4px 12px; font-size: 12px; }
                QPushButton:hover { background: #ffcdd2; }
            """)
            customer_name = d['customer_name']
            btn.clicked.connect(lambda checked, name=customer_name, debt=d['total_debt']:
                self._remind_debt(name, debt))
            self.debt_table.setCellWidget(i, 3, btn)
        
        # 收款流水
        payments = self.db.get_all_payments()
        self.payment_table.setRowCount(len(payments))
        for i, pm in enumerate(payments):
            self.payment_table.setItem(i, 0, QTableWidgetItem(
                (pm.created_at or '')[:16]))
            self.payment_table.setItem(i, 1, QTableWidgetItem(pm.order_no or ''))
            self.payment_table.setItem(i, 2, QTableWidgetItem(pm.customer_name or ''))
            self.payment_table.setItem(i, 3, QTableWidgetItem(f"¥ {pm.amount:.2f}"))
            self.payment_table.setItem(i, 4, QTableWidgetItem(pm.payment_method or ''))
            self.payment_table.setItem(i, 5, QTableWidgetItem(pm.payment_type or ''))
            self.payment_table.setItem(i, 6, QTableWidgetItem(pm.remark or ''))

    def _remind_debt(self, customer_name: str, debt_amount: float):
        """复制催款信息到剪贴板"""
        text = f"【催款通知】客户「{customer_name}」当前欠款 ¥{debt_amount:.2f}，请尽快安排付款。"
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "催款信息已复制",
            f"已复制「{customer_name}」的催款信息到剪贴板：\n\n{text}",
            QMessageBox.StandardButton.Ok)

    # ══════════════════════════════════════════
    # 工单管理页面
    # ══════════════════════════════════════════

    def _orders_page(self):
        p = QWidget()
        lo = QVBoxLayout()
        lo.setSpacing(12)

        h = QHBoxLayout()
        t = QLabel("工单管理")
        t.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        h.addWidget(t)
        h.addStretch()

        b1 = QPushButton("＋ 新建工单")
        b1.setStyleSheet(BTN1)
        b1.clicked.connect(self._new_order)
        h.addWidget(b1)

        b2 = QPushButton("🔄 刷新")
        b2.setStyleSheet(BTN2)
        b2.clicked.connect(self._refresh_orders)
        h.addWidget(b2)
        lo.addLayout(h)

        # 筛选
        fh = QHBoxLayout()
        fh.addWidget(QLabel("状态筛选："))
        self.of = QComboBox()
        self.of.addItems(["全部", "待处理", "进行中", "已完成", "已取消"])
        self.of.currentTextChanged.connect(lambda _: self._refresh_orders())
        self.of.setMinimumHeight(30)
        fh.addWidget(self.of)
        fh.addStretch()
        lo.addLayout(fh)

        # 表格 - 10 列：工单号、客户、电话、描述、金额、已收、未收、付款方式、状态、日期
        self.ot = QTableWidget(0, 10)
        self.ot.setHorizontalHeaderLabels(
            ["工单号", "客户名称", "电话", "描述", "金额", "已收", "未收", "付款方式", "状态", "创建日期"])
        self.ot.setAlternatingRowColors(True)
        self.ot.setStyleSheet(TABLE_S)
        self.ot.horizontalHeader().setStretchLastSection(True)
        self.ot.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.ot.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self.ot.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch)
        self.ot.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ot.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ot.doubleClicked.connect(self._edit_order)
        lo.addWidget(self.ot)

        # 底部按钮
        bh = QHBoxLayout()
        e = QPushButton("✏️ 编辑")
        e.setStyleSheet(BTN2)
        e.clicked.connect(self._edit_order)
        bh.addWidget(e)
        d = QPushButton("🗑️ 删除")
        d.setStyleSheet(BTN3)
        d.clicked.connect(self._del_order)
        bh.addWidget(d)
        bh.addStretch()
        lo.addLayout(bh)

        p.setLayout(lo)
        return p

    def _new_order(self):
        customers = self.db.get_customers()
        d = OrderDialog(self, customers=customers, db=self.db)
        if d.exec() == QDialog.DialogCode.Accepted and d.result_order:
            o = d.result_order
            r = self.order_manager.create_order(
                customer_name=o.customer_name,
                customer_phone=o.customer_phone,
                description=o.description,
                total_amount=o.total_amount,
                status=o.status,
            )
            if r:
                self.statusBar().showMessage(f"✅ 工单创建成功：{r.order_no}", 3000)
                self._refresh_orders()

    def _edit_order(self):
        r = self.ot.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中一个工单"); return
        oid = self.ot.item(r, 0).data(Qt.ItemDataRole.UserRole)
        o = self.order_manager.get_order(oid)
        if not o:
            return
        d = OrderDialog(self, o, customers=self.db.get_customers(), db=self.db)
        if d.exec() == QDialog.DialogCode.Accepted and d.result_order:
            r2 = d.result_order
            self.order_manager.update_order(
                o.id,
                customer_name=r2.customer_name,
                customer_phone=r2.customer_phone,
                description=r2.description,
                total_amount=r2.total_amount,
                status=r2.status,
            )
            self.statusBar().showMessage("✅ 工单已更新", 3000)
            self._refresh_orders()

    def _del_order(self):
        r = self.ot.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的工单"); return
        no = self.ot.item(r, 0).text()
        a = QMessageBox.question(self, "确认删除",
            f"确定要删除工单 [{no}] 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if a == QMessageBox.StandardButton.Yes:
            oid = self.ot.item(r, 0).data(Qt.ItemDataRole.UserRole)
            self.order_manager.delete_order(oid)
            self.statusBar().showMessage(f"✅ 工单已删除：{no}", 3000)
            self._refresh_orders()

    def _refresh_orders(self):
        """刷新工单列表"""
        try:
            if not hasattr(self, 'of') or not hasattr(self, 'order_manager') or not hasattr(self, 'db'):
                return
            
            f = self.of.currentText() if hasattr(self, 'of') and self.of else "全部"
            if f == "全部":
                orders = self.order_manager.get_all_orders()
            else:
                orders = self.order_manager.get_orders_by_status(OS_R.get(f, ""))
            
            if not hasattr(self, 'ot'):
                return
                
            self.ot.setRowCount(len(orders))
            for i, o in enumerate(orders):
                desc = o.description[:30] + "..." if len(o.description) > 30 else o.description
                
                # 获取工单的付款记录
                payments = []
                if hasattr(o, 'id') and o.id:
                    try:
                        payments = self.db.get_payments_by_order(o.id)
                    except:
                        payments = []
                
                payment_method = ""
                if payments:
                    methods = set(p.get('payment_method', '') for p in payments)
                    payment_method = " + ".join(methods)
                
                # 计算已收和未收
                paid = sum(p.get('amount', 0) for p in payments) if payments else getattr(o, 'paid_amount', 0)
                unpaid = getattr(o, 'total_amount', 0) - paid
                
                row = [
                    (o.order_no, o.id),
                    (o.customer_name, None),
                    (o.customer_phone, None),
                    (desc, None),
                    (f"¥ {o.total_amount:.2f}", None),
                    (f"¥ {paid:.2f}", None),
                    (f"¥ {unpaid:.2f}", None),
                    (payment_method, None),
                    (OS.get(o.status, o.status), None),
                    (o.created_at[:10] if o.created_at else "", None),
                ]
                
                for c, (txt, uid) in enumerate(row):
                    it = QTableWidgetItem(txt)
                    if uid is not None:
                        it.setData(Qt.ItemDataRole.UserRole, uid)
                    # 未结款红色高亮
                    if c == 6 and unpaid > 0:  # 未收列
                        it.setForeground(QColor("#e53935"))
                        font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
                        it.setFont(font)
                    self.ot.setItem(i, c, it)
        except Exception as e:
            # 静默失败，避免启动时闪退
            import traceback
            traceback.print_exc()

    # ══════════════════════════════════════════
    # 报价管理页面
    # ══════════════════════════════════════════

    def _quotations_page(self):
        p = QWidget()
        lo = QVBoxLayout()
        lo.setSpacing(12)

        h = QHBoxLayout()
        t = QLabel("报价管理")
        t.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        h.addWidget(t)
        h.addStretch()

        b1 = QPushButton("＋ 新建报价")
        b1.setStyleSheet(BTN1)
        b1.clicked.connect(self._new_quotation)
        h.addWidget(b1)

        b2 = QPushButton("📊 导出 Excel")
        b2.setStyleSheet(BTN2)
        b2.clicked.connect(self._export_quotations)
        h.addWidget(b2)

        b3 = QPushButton("🔄 刷新")
        b3.setStyleSheet(BTN2)
        b3.clicked.connect(self._refresh_quotations)
        h.addWidget(b3)
        lo.addLayout(h)

        # ── 筛选区域 ──
        fh = QHBoxLayout()
        fh.addWidget(QLabel("客户："))
        self.qf_customer = QComboBox()
        self.qf_customer.addItem("全部客户")
        self.qf_customer.setMinimumWidth(150)
        self.qf_customer.setMinimumHeight(30)
        self.qf_customer.currentIndexChanged.connect(
            lambda _: self._refresh_quotations())
        fh.addWidget(self.qf_customer)

        fh.addSpacing(15)
        fh.addWidget(QLabel("状态："))
        self.qf = QComboBox()
        self.qf.addItems(["全部", "草稿", "已发给客户", "客户确认", "已转工单", "作废"])
        self.qf.currentTextChanged.connect(
            lambda _: self._refresh_quotations())
        self.qf.setMinimumHeight(30)
        fh.addWidget(self.qf)
        fh.addStretch()
        lo.addLayout(fh)

        self.qt = QTableWidget(0, 7)
        self.qt.setHorizontalHeaderLabels(
            ["报价单号", "客户名称", "项目数", "总金额", "状态", "创建日期", "来源工单"])
        self.qt.setAlternatingRowColors(True)
        self.qt.setStyleSheet(TABLE_S)
        self.qt.horizontalHeader().setStretchLastSection(True)
        self.qt.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.qt.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.qt.doubleClicked.connect(self._edit_quotation)
        lo.addWidget(self.qt)

        bh = QHBoxLayout()
        e = QPushButton("✏️ 编辑")
        e.setStyleSheet(BTN2)
        e.clicked.connect(self._edit_quotation)
        bh.addWidget(e)

        self.btn_convert = QPushButton("📋 生成工单")
        self.btn_convert.setStyleSheet(BTN1)
        self.btn_convert.clicked.connect(self._convert_quotation_to_order)
        self.btn_convert.setEnabled(False)
        bh.addWidget(self.btn_convert)

        d = QPushButton("🗑️ 删除")
        d.setStyleSheet(BTN3)
        d.clicked.connect(self._del_quotation)
        bh.addWidget(d)
        bh.addStretch()
        lo.addLayout(bh)

        # 选中行时检查是否可转工单
        self.qt.itemSelectionChanged.connect(
            self._on_quotation_selection_changed)

        p.setLayout(lo)
        return p

    def _on_quotation_selection_changed(self):
        """报价选中变化时控制转工单按钮状态"""
        r = self.qt.currentRow()
        if r < 0:
            self.btn_convert.setEnabled(False)
            return
        status_text = self.qt.item(r, 4).text() if self.qt.item(r, 4) else ""
        # 仅"客户确认"可转工单
        self.btn_convert.setEnabled(status_text == "客户确认")

        p.setLayout(lo)
        return p

    def _new_quotation(self):
        customers = self.db.get_customers()
        d = QuotationDialog(self, customers=customers, db=self.db)
        if d.exec() == QDialog.DialogCode.Accepted and d.result:
            r = d.result
            q = self.quotation_manager.create_quotation(
                customer_name=r["customer_name"],
                customer_id=r.get("customer_id"),
                items=r["items"],
                valid_days=r["valid_days"],
            )
            if r["status"] != "draft" and q and q.id:
                self.quotation_manager.update_quotation(q.id, status=r["status"])
            self.statusBar().showMessage("✅ 报价单创建成功", 3000)
            self._refresh_quotations()

    def _edit_quotation(self):
        """编辑报价单"""
        r = self.qt.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中一个报价单")
            return
        qid = self.qt.item(r, 0).data(Qt.ItemDataRole.UserRole)
        try:
            q = self.quotation_manager.get_quotation(qid)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取报价单失败：{e}")
            return
        if not q:
            QMessageBox.warning(self, "提示", "报价单不存在")
            return
        # 已转工单不可编辑
        if q.status == "converted":
            QMessageBox.information(self, "提示", "已转工单的报价单不可编辑")
            return
        
        try:
            d = QuotationDialog(self, q, customers=self.db.get_customers(), db=self.db)
            if d.exec() == QDialog.DialogCode.Accepted and d.result:
                r2 = d.result
                # 更新报价单
                q.customer_name = r2["customer_name"]
                q.customer_id = r2.get("customer_id")
                q.items = r2["items"]
                q.total_amount = sum(item["qty"] * item["price"] for item in r2["items"])
                q.status = r2["status"]
                
                self.quotation_manager.update_quotation(q.id, q)
                self.statusBar().showMessage("✅ 报价单已更新", 3000)
                self._refresh_quotations()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新报价单失败：{e}")
            import traceback
            traceback.print_exc()

    def _del_quotation(self):
        r = self.qt.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的报价单"); return
        no = self.qt.item(r, 0).text()
        qid = self.qt.item(r, 0).data(Qt.ItemDataRole.UserRole)
        q = self.quotation_manager.get_quotation(qid)
        if q and q.status == "converted":
            QMessageBox.warning(self, "提示", "已转工单的报价单不可删除")
            return
        a = QMessageBox.question(self, "确认删除",
            f"确定要删除报价单 [{no}] 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if a == QMessageBox.StandardButton.Yes:
            self.quotation_manager.delete_quotation(qid)
            self.statusBar().showMessage(f"✅ 报价单已删除：{no}", 3000)
            self._refresh_quotations()

    def _convert_quotation_to_order(self):
        """一键将报价单转为工单"""
        r = self.qt.currentRow()
        if r < 0:
            return
        qid = self.qt.item(r, 0).data(Qt.ItemDataRole.UserRole)
        q = self.quotation_manager.get_quotation(qid)
        if not q or q.status != "confirmed":
            QMessageBox.warning(self, "提示", "仅「客户确认」状态的报价单可生成工单")
            return
        
        # 确认对话框
        a = QMessageBox.question(
            self, "生成工单",
            f"确定要根据报价单 [{q.quotation_no}] 生成工单吗？\n\n"
            f"客户：{q.customer_name}\n"
            f"金额：¥{q.total_amount:.2f}\n"
            f"项目数：{len(q.items)} 项",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        
        if a != QMessageBox.StandardButton.Yes:
            return
        
        try:
            order = self.quotation_manager.convert_to_order(qid)
            if order:
                self.statusBar().showMessage(
                    f"✅ 工单已生成：{order.order_no}", 5000)
                self._refresh_quotations()
                # 自动跳转到工单页面
                self._switch(self.IDX_ORDERS)
                self._refresh_orders()
            else:
                QMessageBox.warning(self, "生成失败", "工单生成失败，请重试")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成工单出错: {str(e)}")

    def _refresh_quotations(self):
        # 刷新客户筛选下拉
        customers = self.db.get_customers()
        current_cust = self.qf_customer.currentText()
        self.qf_customer.blockSignals(True)
        self.qf_customer.clear()
        self.qf_customer.addItem("全部客户")
        for c in customers:
            self.qf_customer.addItem(c.name, c.id)
        # 恢复选中
        idx = self.qf_customer.findText(current_cust)
        if idx >= 0:
            self.qf_customer.setCurrentIndex(idx)
        self.qf_customer.blockSignals(False)
        
        # 获取筛选条件
        status_text = self.qf.currentText()
        status = None if status_text == "全部" else QS_R.get(status_text, "")
        
        cust_name = self.qf_customer.currentText()
        cust_id = None
        if cust_name != "全部客户":
            cust_idx = self.qf_customer.currentIndex()
            if cust_idx > 0:  # index 0 是 "全部客户"
                cust_id = self.qf_customer.itemData(cust_idx)
        
        qs = self.quotation_manager.get_quotations_filtered(
            status=status, customer_id=cust_id)
        
        self.qt.setRowCount(len(qs))
        for i, q in enumerate(qs):
            converted_text = ""
            if q.converted_order_id:
                converted_text = f"工单#{q.converted_order_id}"
            row = [
                (q.quotation_no, q.id),
                (q.customer_name, None),
                (str(len(q.items)), None),
                (f"¥ {q.total_amount:.2f}", None),
                (QS.get(q.status, q.status), None),
                (q.created_at[:10] if q.created_at else "", None),
                (converted_text, None),
            ]
            for c, (txt, uid) in enumerate(row):
                it = QTableWidgetItem(txt)
                if uid is not None:
                    it.setData(Qt.ItemDataRole.UserRole, uid)
                self.qt.setItem(i, c, it)

    def _export_quotations(self):
        try:
            from app.utils.exporter import DataExporter
            fp, _ = QFileDialog.getSaveFileName(
                self, "导出报价单", "报价单列表.xlsx",
                "Excel 文件 (*.xlsx)")
            if not fp:
                return
            exp = DataExporter(self.db)
            if exp.export_quotations_to_excel(fp):
                self.statusBar().showMessage(f"✅ 导出成功：{fp}", 3000)
            else:
                QMessageBox.warning(self, "导出失败", "导出失败，请确认 openpyxl 已安装")
        except ImportError:
            QMessageBox.warning(self, "导出失败", "请先安装 openpyxl: pip install openpyxl")

    # ══════════════════════════════════════════
    # 客户管理页面
    # ══════════════════════════════════════════

    def _customers_page(self):
        p = QWidget()
        lo = QVBoxLayout()
        lo.setSpacing(12)

        h = QHBoxLayout()
        t = QLabel("客户管理")
        t.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        h.addWidget(t)
        h.addStretch()

        b1 = QPushButton("＋ 新建客户")
        b1.setStyleSheet(BTN1)
        b1.clicked.connect(self._new_customer)
        h.addWidget(b1)

        b2 = QPushButton("🔄 刷新")
        b2.setStyleSheet(BTN2)
        b2.clicked.connect(self._refresh_customers)
        h.addWidget(b2)
        lo.addLayout(h)

        # 搜索
        sh = QHBoxLayout()
        sh.addWidget(QLabel("搜索客户："))
        self.cs = QLineEdit()
        self.cs.setPlaceholderText("输入客户名称或电话搜索")
        self.cs.setMinimumHeight(30)
        self.cs.textChanged.connect(lambda _: self._refresh_customers())
        sh.addWidget(self.cs)
        sh.addStretch()
        lo.addLayout(sh)

        # 表格：9列（含欠款统计）
        self.ct = QTableWidget(0, 9)
        self.ct.setHorizontalHeaderLabels(
            ["客户名称", "电话", "地址", "累计消费", "累计已付",
             "当前欠款", "工单数", "创建日期", "详情"])
        self.ct.setAlternatingRowColors(True)
        self.ct.setStyleSheet(TABLE_S)
        self.ct.horizontalHeader().setStretchLastSection(True)
        self.ct.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self.ct.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ct.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # 双击打开客户详情
        self.ct.doubleClicked.connect(self._customer_detail)
        lo.addWidget(self.ct)

        bh = QHBoxLayout()
        e = QPushButton("📋 查看详情")
        e.setStyleSheet(BTN1)
        e.clicked.connect(self._customer_detail)
        bh.addWidget(e)
        ed = QPushButton("✏️ 编辑")
        ed.setStyleSheet(BTN2)
        ed.clicked.connect(self._edit_customer)
        bh.addWidget(ed)
        d = QPushButton("🗑️ 删除")
        d.setStyleSheet(BTN3)
        d.clicked.connect(self._del_customer)
        bh.addWidget(d)
        bh.addStretch()
        lo.addLayout(bh)

        p.setLayout(lo)
        return p

    def _new_customer(self):
        d = CustomerDialog(self)
        if d.exec() == QDialog.DialogCode.Accepted and d.result:
            r = d.result
            c = self.customer_manager.create_customer(
                name=r["name"], phone=r["phone"],
                address=r["address"], notes=r["notes"])
            if c:
                self.statusBar().showMessage(f"✅ 客户创建成功：{c.name}", 3000)
                self._refresh_customers()

    def _edit_customer(self):
        r = self.ct.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中一个客户"); return
        cid = self.ct.item(r, 0).data(Qt.ItemDataRole.UserRole)
        c = self.customer_manager.get_customer(cid)
        if not c:
            return
        d = CustomerDialog(self, c)
        if d.exec() == QDialog.DialogCode.Accepted and d.result:
            r2 = d.result
            self.customer_manager.update_customer(
                c.id, name=r2["name"], phone=r2["phone"],
                address=r2["address"], notes=r2["notes"])
            self.statusBar().showMessage("✅ 客户信息已更新", 3000)
            self._refresh_customers()

    def _del_customer(self):
        r = self.ct.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的客户"); return
        name = self.ct.item(r, 0).text()
        a = QMessageBox.question(self, "确认删除",
            f"确定要删除客户 [{name}] 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if a == QMessageBox.StandardButton.Yes:
            cid = self.ct.item(r, 0).data(Qt.ItemDataRole.UserRole)
            self.customer_manager.delete_customer(cid)
            self.statusBar().showMessage(f"✅ 客户已删除：{name}", 3000)
            self._refresh_customers()

    def _refresh_customers(self):
        kw = self.cs.text().strip()
        if kw:
            cs = self.customer_manager.search_customers(kw)
        else:
            cs = self.customer_manager.get_all_customers()
        self.ct.setRowCount(len(cs))
        for i, c in enumerate(cs):
            # 查询客户详情（含欠款统计）
            detail = self.db.get_customer_detail(c.id)
            total_paid = detail.get('total_paid', 0.0)
            total_debt = detail.get('total_debt', 0.0)
            
            row = [
                (c.name, c.id),
                (c.phone or "", None),
                (c.address or "", None),
                (f"¥ {c.total_spent:.2f}", None),
                (f"¥ {total_paid:.2f}", None),
                (f"¥ {total_debt:.2f}", None),
                (str(c.total_orders), None),
                (c.created_at[:10] if c.created_at else "", None),
                ("📋 查看详情", None),
            ]
            for col, (txt, uid) in enumerate(row):
                it = QTableWidgetItem(txt)
                if uid is not None:
                    it.setData(Qt.ItemDataRole.UserRole, uid)
                # 欠款列红色高亮
                if col == 5 and total_debt > 0:
                    it.setForeground(QColor("#e53935"))
                    font = QFont("Microsoft YaHei", 11, QFont.Weight.Bold)
                    it.setFont(font)
                self.ct.setItem(i, col, it)

    def _customer_detail(self):
        """打开客户详情对话框"""
        r = self.ct.currentRow()
        if r < 0:
            QMessageBox.warning(self, "提示", "请先选中一个客户")
            return
        try:
            cid = self.ct.item(r, 0).data(Qt.ItemDataRole.UserRole)
            detail = self.db.get_customer_detail(cid)
            if not detail.get('customer'):
                QMessageBox.warning(self, "提示", "客户信息不存在")
                return
            dlg = CustomerDetailDialog(
                detail['customer'], detail['total_paid'], detail['total_debt'],
                self.db, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开客户详情失败：{e}")
            import traceback
            traceback.print_exc()
    
    # ══════════════════════════════════════════
    # 设置页面（含激活码入口）
    # ══════════════════════════════════════════

    def _settings_page(self):
        p = QWidget()
        lo = QVBoxLayout()
        lo.setSpacing(15)

        t = QLabel("设置")
        t.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        lo.addWidget(t)

        # ── 激活码管理 ──
        lic_g = QGroupBox("激活码管理")
        lic_g.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        lic_lo = QVBoxLayout()

        self.lic_status = QLabel("正在检测激活状态...")
        self.lic_status.setStyleSheet("color: #999; font-size: 13px; padding: 5px 0;")
        lic_lo.addWidget(self.lic_status)

        lic_form = QHBoxLayout()
        self.lic_input = QLineEdit()
        self.lic_input.setPlaceholderText("请输入激活码")
        self.lic_input.setMinimumHeight(36)
        lic_form.addWidget(self.lic_input, 3)

        self.lic_btn = QPushButton("🔑 激活")
        self.lic_btn.setStyleSheet(BTN1)
        self.lic_btn.clicked.connect(self._activate)
        self.lic_btn.setMinimumHeight(36)
        lic_form.addWidget(self.lic_btn, 1)
        lic_lo.addLayout(lic_form)

        lic_hint = QLabel("激活码由软件供应商提供。试用期为 30 天。")
        lic_hint.setStyleSheet("color: #999; font-size: 11px;")
        lic_lo.addWidget(lic_hint)

        lic_g.setLayout(lic_lo)
        lo.addWidget(lic_g)

        # ── 关于 ──
        about_g = QGroupBox("关于")
        about_g.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        about_lo = QVBoxLayout()
        about_lo.addWidget(QLabel("豆子设计助手 V1.0.0"))
        about_lo.addWidget(QLabel("一款面向图文店的桌面应用"))
        about_lo.addWidget(QLabel("提供工单管理、报价计算、客户管理、AI 抠图、文字识别功能"))
        about_lo.addWidget(QLabel("© 2026 豆子软件"))
        about_g.setLayout(about_lo)
        lo.addWidget(about_g)

        lo.addStretch()
        p.setLayout(lo)

        # 延迟加载许可证状态
        QTimer.singleShot(200, self._refresh_license_status)
        return p

    def _refresh_license_status(self):
        if self.license_client:
            try:
                status = self.license_client.get_status()
                if status == "activated":
                    self.lic_status.setText("✅ 已激活 — 全部功能可用")
                    self.lic_status.setStyleSheet("color: #4caf50; font-size: 13px; padding: 5px 0;")
                    self.lic_btn.setText("✅ 已激活")
                    self.lic_btn.setEnabled(False)
                elif status == "trial":
                    self.lic_status.setText("🕐 试用中 — 剩余 30 天")
                    self.lic_status.setStyleSheet("color: #ff9800; font-size: 13px; padding: 5px 0;")
                else:
                    self.lic_status.setText("⚠️ 未激活 — 请输入激活码激活")
                    self.lic_status.setStyleSheet("color: #f44336; font-size: 13px; padding: 5px 0;")
            except Exception:
                self.lic_status.setText("⚠️ 无法检测激活状态")
                self.lic_status.setStyleSheet("color: #999; font-size: 13px; padding: 5px 0;")
        else:
            self.lic_status.setText("⚠️ license 模块未加载")
            self.lic_status.setStyleSheet("color: #999; font-size: 13px; padding: 5px 0;")
            self.lic_btn.setEnabled(False)

    def _activate(self):
        code = self.lic_input.text().strip()
        if not code:
            QMessageBox.warning(self, "提示", "请输入激活码")
            return
        if self.license_client:
            try:
                ok, msg = self.license_client.activate(code)
                if ok:
                    QMessageBox.information(self, "激活成功", msg)
                    self._refresh_license_status()
                else:
                    QMessageBox.warning(self, "激活失败", msg)
            except Exception as e:
                QMessageBox.warning(self, "激活失败", str(e))
        else:
            QMessageBox.information(self, "提示", "激活码验证功能将在 Phase 3 实现")

    # ══════════════════════════════════════════
    # 菜单栏
    # ══════════════════════════════════════════

    def _menu_bar(self):
        mb = self.menuBar()

        # 文件
        fm = mb.addMenu("文件(&F)")
        a1 = QAction("新建工单(&N)", self)
        a1.triggered.connect(self._new_order)
        fm.addAction(a1)

        fm.addSeparator()

        a2 = QAction("导出工单 Excel(&E)", self)
        a2.triggered.connect(lambda: self._export_orders())
        fm.addAction(a2)

        a3 = QAction("导出报价单 Excel(&Q)", self)
        a3.triggered.connect(lambda: self._export_quotations())
        fm.addAction(a3)

        fm.addSeparator()

        a4 = QAction("退出(&X)", self)
        a4.triggered.connect(self.close)
        fm.addAction(a4)

        # AI
        ai_m = mb.addMenu("AI(&A)")
        a5 = QAction("AI 抠图(&M)", self)
        a5.triggered.connect(lambda: self._switch(self.IDX_MATTING))
        ai_m.addAction(a5)

        a6 = QAction("文字识别(&O)", self)
        a6.triggered.connect(lambda: self._switch(self.IDX_OCR))
        ai_m.addAction(a6)

        # 帮助
        hm = mb.addMenu("帮助(&H)")
        a7 = QAction("关于(&A)", self)
        a7.triggered.connect(self._about)
        hm.addAction(a7)

    def _export_orders(self):
        try:
            from app.utils.exporter import DataExporter
            fp, _ = QFileDialog.getSaveFileName(
                self, "导出工单", "工单列表.xlsx",
                "Excel 文件 (*.xlsx)")
            if not fp:
                return
            exp = DataExporter(self.db)
            if exp.export_orders_to_excel(fp):
                self.statusBar().showMessage(f"✅ 导出成功：{fp}", 3000)
            else:
                QMessageBox.warning(self, "导出失败", "导出失败")
        except ImportError:
            QMessageBox.warning(self, "导出失败", "请先安装 openpyxl")

    # ══════════════════════════════════════════
    # 工具栏
    # ══════════════════════════════════════════

    def _tool_bar(self):
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)

        a1 = QAction("📋 新建工单", self)
        a1.triggered.connect(self._new_order)
        tb.addAction(a1)

        a2 = QAction("💰 新建报价", self)
        a2.triggered.connect(self._new_quotation)
        tb.addAction(a2)

        a3 = QAction("👤 新建客户", self)
        a3.triggered.connect(self._new_customer)
        tb.addAction(a3)

        tb.addSeparator()

        a4 = QAction("🔄 刷新", self)
        a4.triggered.connect(self._refresh_all)
        tb.addAction(a4)

    def _refresh_all(self):
        self._refresh_orders()
        self._refresh_quotations()
        self._refresh_customers()
        self.statusBar().showMessage("🔄 已刷新所有数据", 2000)

    # ══════════════════════════════════════════
    # 状态栏
    # ══════════════════════════════════════════

    def _status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)

        self.db_label = QLabel("数据库：✓ 已连接")
        self.db_label.setStyleSheet("color: #4caf50; margin-right: 15px;")
        sb.addPermanentWidget(self.db_label)

        self.user_label = QLabel("当前用户：管理员")
        sb.addPermanentWidget(self.user_label)

        sb.showMessage("就绪")

    def _about(self):
        QMessageBox.about(self, "关于豆子设计助手",
            "豆子设计助手 V1.0.0\n\n"
            "一款面向图文店的桌面应用\n"
            "提供工单管理、报价计算、客户管理、AI 抠图、文字识别功能\n\n"
            "© 2026 豆子软件")

    # ══════════════════════════════════════════
    # 关闭
    # ══════════════════════════════════════════

    def closeEvent(self, event):
        a = QMessageBox.question(self, "确认退出",
            "确定要退出豆子设计助手吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if a == QMessageBox.StandardButton.Yes:
            self.db.close()
            event.accept()
        else:
            event.ignore()
