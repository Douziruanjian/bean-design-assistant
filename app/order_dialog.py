#!/usr/bin/env python3
"""
工单编辑对话框 - 支持完整收款功能
"""
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from app.database.models import Order, PAYMENT_METHODS, PAYMENT_TYPES
import datetime

BTN1 = "QPushButton { background: #1976d2; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #1565c0; }"
BTN2 = "QPushButton { background: #e0e0e0; color: #333; border: none; padding: 8px 16px; border-radius: 4px; font-size: 14px; }"
TABLE_S = "QTableWidget { border: 1px solid #ddd; border-radius: 4px; } QTableWidget::item { padding: 6px; } QHeaderView::section { background: #f5f5f5; padding: 6px; border: none; font-weight: bold; }"


class OrderDialog(QDialog):
    """工单编辑对话框 - 支持收款功能"""
    
    def __init__(self, parent=None, order: Order = None, customers: list = None, db=None):
        super().__init__(parent)
        self.result_order = None
        self.order = order
        self.customers = customers or []
        self.db = db
        self.payment_records = []
        
        self.setWindowTitle(f"{'编辑' if order else '新建'}工单")
        self.setMinimumWidth(750)
        self.setMinimumHeight(650)
        
        lo = QVBoxLayout(self)
        lo.setSpacing(12)
        
        # === 基础信息 ===
        info_group = QGroupBox("工单信息")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(10)
        
        # 客户选择
        self.customer_name = QComboBox()
        self.customer_name.setEditable(False)
        self.customer_name.setMinimumHeight(30)
        if self.customers:
            for c in self.customers:
                self.customer_name.addItem(c.name, c.id)
        else:
            self.customer_name.addItem("请先添加客户", -1)
        self.customer_name.currentIndexChanged.connect(self._on_customer_changed)
        info_layout.addRow("客户名称 *", self.customer_name)
        
        # 联系电话
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("选择客户后自动填充")
        self.customer_phone.setReadOnly(True)
        self.customer_phone.setMinimumHeight(30)
        info_layout.addRow("联系电话", self.customer_phone)
        
        # 工单描述
        self.description = QTextEdit()
        self.description.setPlaceholderText("请详细描述工单内容（物料类型、规格、数量等）")
        self.description.setMinimumHeight(60)
        info_layout.addRow("工单描述 *", self.description)
        
        # 总金额
        self.total_amount = QDoubleSpinBox()
        self.total_amount.setRange(0, 999999.99)
        self.total_amount.setPrefix("¥ ")
        self.total_amount.setDecimals(2)
        self.total_amount.setValue(0.0)
        self.total_amount.setMinimumHeight(30)
        self.total_amount.valueChanged.connect(self._update_payment_status)
        info_layout.addRow("总金额", self.total_amount)
        
        # 状态
        self.status_combo = QComboBox()
        for v in ["待处理", "进行中", "已完成", "已取消"]:
            self.status_combo.addItem(v)
        self.status_combo.setMinimumHeight(30)
        info_layout.addRow("状态", self.status_combo)
        
        lo.addWidget(info_group)
        
        # === 收款信息 ===
        payment_group = QGroupBox("收款信息")
        payment_layout = QVBoxLayout(payment_group)
        
        # 收款状态显示
        self.payment_status_label = QLabel("收款状态：未付款")
        self.payment_status_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e53935;")
        payment_layout.addWidget(self.payment_status_label)
        
        # 金额显示
        amount_layout = QHBoxLayout()
        self.lbl_total = QLabel("总金额：¥ 0.00")
        self.lbl_paid = QLabel("已收：¥ 0.00")
        self.lbl_unpaid = QLabel("未收：¥ 0.00")
        self.lbl_unpaid.setStyleSheet("color: #e53935; font-weight: bold; font-size: 14px;")
        amount_layout.addWidget(self.lbl_total)
        amount_layout.addWidget(self.lbl_paid)
        amount_layout.addWidget(self.lbl_unpaid)
        amount_layout.addStretch()
        payment_layout.addLayout(amount_layout)
        
        # 收款记录表格
        payment_layout.addWidget(QLabel("收款记录："))
        self.payment_table = QTableWidget(0, 5)
        self.payment_table.setHorizontalHeaderLabels(["时间", "金额", "方式", "类型", "备注"])
        self.payment_table.setAlternatingRowColors(True)
        self.payment_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.payment_table.horizontalHeader().setStretchLastSection(True)
        self.payment_table.setMinimumHeight(100)
        self.payment_table.setStyleSheet(TABLE_S)
        payment_layout.addWidget(self.payment_table)
        
        # 收款按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        add_payment_btn = QPushButton("💰 录入收款")
        add_payment_btn.setStyleSheet(BTN1)
        add_payment_btn.clicked.connect(self._add_payment)
        btn_layout.addWidget(add_payment_btn)
        payment_layout.addLayout(btn_layout)
        
        lo.addWidget(payment_group)
        
        # === 按钮 ===
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("✅ 保存")
        save_btn.setStyleSheet(BTN1)
        save_btn.clicked.connect(self._accept)
        btn_row.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(BTN2)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        lo.addLayout(btn_row)
        
        # 加载已有工单数据
        if order:
            self._load_order_data()
    
    def _load_order_data(self):
        """加载工单数据"""
        # 选择客户
        idx = self.customer_name.findText(self.order.customer_name)
        if idx >= 0:
            self.customer_name.setCurrentIndex(idx)
        else:
            self.customer_name.addItem(self.order.customer_name)
            self.customer_name.setCurrentIndex(self.customer_name.count() - 1)
        
        self.customer_phone.setText(self.order.customer_phone or "")
        self.description.setPlainText(self.order.description)
        self.total_amount.setValue(self.order.total_amount)
        self.status_combo.setCurrentText(self.order.status)
        
        # 加载收款记录
        if self.order.id and self.db:
            try:
                self.payment_records = self.db.get_payments_by_order(self.order.id)
            except:
                self.payment_records = []
        
        self._refresh_payment_table()
    
    def _on_customer_changed(self, idx):
        """客户变更处理"""
        if idx < 0 or idx >= len(self.customers):
            return
        c = self.customers[idx]
        self.customer_phone.setText(c.phone or "")
        
        # 欠款提醒
        if self.db:
            try:
                has_debt, debt_amount = self.db.get_customer_debt_warning(c.name)
                if has_debt and debt_amount > 0:
                    QMessageBox.warning(
                        self, "客户欠款提醒",
                        f"客户「{c.name}」当前欠款 ¥{debt_amount:.2f}，请注意收款安排。",
                        QMessageBox.StandardButton.Ok)
            except:
                pass
    
    def _update_payment_status(self):
        """更新收款状态显示"""
        total = self.total_amount.value()
        paid = sum(p.get('amount', 0) for p in self.payment_records)
        unpaid = total - paid
        
        self.lbl_total.setText(f"总金额：¥ {total:.2f}")
        self.lbl_paid.setText(f"已收：¥ {paid:.2f}")
        self.lbl_unpaid.setText(f"未收：¥ {unpaid:.2f}")
        
        if unpaid <= 0 and total > 0:
            status = "已结清 ✅"
            color = "#43a047"
        elif paid > 0:
            status = "部分付款 ⚠️"
            color = "#fb8c00"
        elif total == 0:
            status = "待收款"
            color = "#666"
        else:
            status = "未付款 ❌"
            color = "#e53935"
        
        self.payment_status_label.setText(f"收款状态：{status}")
        self.payment_status_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
    
    def _refresh_payment_table(self):
        """刷新收款记录表格"""
        self.payment_table.setRowCount(len(self.payment_records))
        for i, p in enumerate(self.payment_records):
            self.payment_table.setItem(i, 0, QTableWidgetItem((p.get('created_at') or '')[:16]))
            self.payment_table.setItem(i, 1, QTableWidgetItem(f"¥ {p.get('amount', 0):.2f}"))
            self.payment_table.setItem(i, 2, QTableWidgetItem(p.get('payment_method', '')))
            self.payment_table.setItem(i, 3, QTableWidgetItem(p.get('payment_type', '')))
            self.payment_table.setItem(i, 4, QTableWidgetItem(p.get('remark', '')))
        self._update_payment_status()
    
    def _add_payment(self):
        """录入收款"""
        total = self.total_amount.value()
        paid = sum(p.get('amount', 0) for p in self.payment_records)
        unpaid = total - paid
        
        if unpaid <= 0 and total > 0:
            QMessageBox.information(self, "提示", "该工单已结清，无需再收款")
            return
        
        if total == 0:
            QMessageBox.warning(self, "提示", "请先设置工单总金额")
            return
        
        # 收款对话框
        dlg = QDialog(self)
        dlg.setWindowTitle("录入收款")
        dlg.setMinimumWidth(400)
        
        lo = QVBoxLayout(dlg)
        
        form = QFormLayout()
        
        # 金额
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0.01, unpaid if unpaid > 0 else total)
        amount_spin.setPrefix("¥ ")
        amount_spin.setDecimals(2)
        amount_spin.setValue(min(unpaid if unpaid > 0 else total, 100))
        amount_spin.setMinimumHeight(30)
        form.addRow("收款金额", amount_spin)
        
        # 支付方式
        method_combo = QComboBox()
        for m in PAYMENT_METHODS:
            method_combo.addItem(m)
        method_combo.setMinimumHeight(30)
        form.addRow("支付方式", method_combo)
        
        # 收款类型
        type_combo = QComboBox()
        for t in PAYMENT_TYPES:
            type_combo.addItem(t)
        type_combo.setMinimumHeight(30)
        form.addRow("收款类型", type_combo)
        
        # 备注
        remark_edit = QLineEdit()
        remark_edit.setPlaceholderText("备注（可选）")
        remark_edit.setMinimumHeight(30)
        form.addRow("备注", remark_edit)
        
        lo.addLayout(form)
        
        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确认收款")
        ok_btn.setStyleSheet(BTN1)
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(BTN2)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        lo.addLayout(btn_row)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            record = {
                'order_id': self.order.id if self.order else 0,
                'order_no': self.order.order_no if self.order else 'NEW',
                'customer_name': self.customer_name.currentText(),
                'amount': amount_spin.value(),
                'payment_method': method_combo.currentText(),
                'payment_type': type_combo.currentText(),
                'remark': remark_edit.text(),
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            self.payment_records.append(record)
            self._refresh_payment_table()
    
    def _accept(self):
        """保存工单"""
        name = self.customer_name.currentText().strip()
        desc = self.description.toPlainText().strip()
        
        if not name or name == "请先添加客户":
            QMessageBox.warning(self, "提示", "请选择客户名称")
            return
        if not desc:
            QMessageBox.warning(self, "提示", "请输入工单描述")
            return
        
        total = self.total_amount.value()
        paid = sum(p.get('amount', 0) for p in self.payment_records)
        unpaid = total - paid
        
        # 判定收款状态
        if unpaid <= 0 and total > 0:
            payment_status = "paid"
        elif paid > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"
        
        # 创建工单对象
        o = Order(
            customer_name=name,
            customer_phone=self.customer_phone.text().strip(),
            description=desc,
            total_amount=total,
            paid_amount=paid,
            unpaid_amount=unpaid,
            payment_status=payment_status,
            status=self.status_combo.currentText(),
        )
        
        if self.order and self.order.id:
            o.id = self.order.id
            o.order_no = self.order.order_no
        
        self.result_order = o
        self.accept()


if __name__ == "__main__":
    app = QApplication([])
    dlg = OrderDialog()
    dlg.show()
    app.exec()
