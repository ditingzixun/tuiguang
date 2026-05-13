"""代理IP池监控面板 — 查看代理状态、手动操作"""
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)
from core.proxy_engine import proxy_engine
from ui.styles.theme_manager import theme_manager


class ProxyManagerWidget(QWidget):
    """代理IP池监控面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_fetch = QPushButton("立即获取代理")
        self.btn_fetch.clicked.connect(self._fetch)
        self.btn_check = QPushButton("全部检测")
        self.btn_check.clicked.connect(self._check_all)
        self.btn_clean = QPushButton("清除失效")
        self.btn_clean.clicked.connect(self._cleanup)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh)

        for btn in [self.btn_fetch, self.btn_check, self.btn_clean, self.btn_refresh]:
            toolbar.addWidget(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 统计
        info_layout = QHBoxLayout()
        self.stats_label = QLabel("共 0 个代理 | 可用: 0 | 失效: 0 | 平均延迟: 0ms")
        self.switch_label = QLabel("代理引擎: 未启动")
        info_layout.addWidget(self.stats_label)
        info_layout.addStretch()
        info_layout.addWidget(self.switch_label)
        layout.addLayout(info_layout)

        # 代理列表
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Host:Port", "协议", "状态", "延迟(ms)", "成功", "失败", "连续失败", "最后检测"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        proxy_header = self.table.horizontalHeader()
        proxy_header.setStretchLastSection(True)
        proxy_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        proxy_col_widths = [35, 140, 50, 50, 70, 45, 45, 60, 100]
        for i, w in enumerate(proxy_col_widths):
            self.table.setColumnWidth(i, w)
        layout.addWidget(self.table)

        # 账号绑定列表
        layout.addWidget(QLabel("账号代理绑定"))
        self.binding_table = QTableWidget()
        self.binding_table.setColumnCount(4)
        self.binding_table.setHorizontalHeaderLabels(["账号ID", "平台", "用户名", "代理 Host:Port"])
        self.binding_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.binding_table.setAlternatingRowColors(True)
        bind_header = self.binding_table.horizontalHeader()
        bind_header.setStretchLastSection(True)
        bind_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        bind_col_widths = [60, 80, 100, 160]
        for i, w in enumerate(bind_col_widths):
            self.binding_table.setColumnWidth(i, w)
        layout.addWidget(self.binding_table)

    def refresh(self):
        self._refresh_proxy_table()
        self._refresh_binding_table()
        self._update_stats()

    def _refresh_proxy_table(self):
        try:
            rows = self.db_manager.fetch_all("SELECT * FROM proxies ORDER BY id")
            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                host_port = f"{row['host']}:{row['port']}"
                items = [
                    QTableWidgetItem(str(row["id"])),
                    QTableWidgetItem(host_port),
                    QTableWidgetItem(row["protocol"]),
                    QTableWidgetItem(row["status"]),
                    QTableWidgetItem(str(row["latency_ms"])),
                    QTableWidgetItem(str(row["success_count"])),
                    QTableWidgetItem(str(row["fail_count"])),
                    QTableWidgetItem(str(row["consecutive_failures"])),
                    QTableWidgetItem(row["last_check_at"] or "-"),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if row["status"] == "failed":
                        item.setBackground(QColor(theme_manager.get_color("row_proxy_failed", "#ffc8c8")))
                    elif row["status"] == "active" and row["latency_ms"] and row["latency_ms"] < 500:
                        item.setBackground(QColor(theme_manager.get_color("row_proxy_active", "#c8ffc8")))
                    self.table.setItem(r, c, item)
        except Exception as e:
            logger.error(f"刷新代理列表异常: {e}")

    def _refresh_binding_table(self):
        try:
            rows = self.db_manager.fetch_all(
                "SELECT a.id as acc_id, a.platform, a.username, p.host, p.port "
                "FROM proxy_bindings pb "
                "JOIN accounts a ON pb.account_id = a.id "
                "JOIN proxies p ON pb.proxy_id = p.id "
                "ORDER BY a.id"
            )
            self.binding_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                items = [
                    QTableWidgetItem(str(row["acc_id"])),
                    QTableWidgetItem(row["platform"] or ""),
                    QTableWidgetItem(row["username"] or ""),
                    QTableWidgetItem(f"{row['host']}:{row['port']}"),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.binding_table.setItem(r, c, item)
        except Exception as e:
            logger.error(f"刷新绑定列表异常: {e}")

    def _update_stats(self):
        stats = proxy_engine.get_stats()
        self.stats_label.setText(
            f"共 {stats['total']} 个代理 | 可用: {stats['active']} | "
            f"失效: {stats['failed']} | 平均延迟: {stats['avg_latency']}ms"
        )
        self.switch_label.setText(f"代理引擎: {'运行中' if proxy_engine._running else '未启动'}")

    def _fetch(self):
        proxy_engine.force_fetch()
        self.refresh()

    def _check_all(self):
        proxy_engine.force_validate_all()
        self.refresh()

    def _cleanup(self):
        proxy_engine.force_cleanup()
        self.refresh()
