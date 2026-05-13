"""搜索引擎收录监控面板 -- 关键词管理 + 排名检测 + 报表导出"""
import csv
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QMessageBox, QHeaderView, QLabel,
    QFileDialog, QSplitter, QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
    QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QAction

logger = logging.getLogger(__name__)
from ui.styles.theme_manager import theme_manager
from core.seo_engine import seo_engine


class SeoCheckThread(QThread):
    """后台SEO检查线程"""
    progress = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, check_type: str):
        super().__init__()
        self.check_type = check_type  # 'index', 'rank', 'all'

    def run(self):
        try:
            if self.check_type == "index":
                self.progress.emit("正在检测已发布URL收录状态...")
                seo_engine.force_check_index()
            elif self.check_type == "rank":
                self.progress.emit("正在检测关键词排名...")
                seo_engine.force_check_rank()
            else:
                self.progress.emit("正在执行全量SEO检查...")
                seo_engine.force_check_all()
        except Exception as e:
            logger.error(f"SEO检查异常: {e}")
        self.finished_signal.emit()


class SeoMonitorWidget(QWidget):
    """搜索引擎收录监控面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        seo_engine.set_db_manager(db_manager)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ====== 工具栏 ======
        toolbar = QHBoxLayout()
        self.btn_check_index = QPushButton("检测收录")
        self.btn_check_index.clicked.connect(lambda: self._run_check("index"))
        self.btn_check_rank = QPushButton("检测排名")
        self.btn_check_rank.clicked.connect(lambda: self._run_check("rank"))
        self.btn_check_all = QPushButton("一键全检")
        self.btn_check_all.clicked.connect(lambda: self._run_check("all"))
        self.btn_export = QPushButton("导出报表CSV")
        self.btn_export.clicked.connect(self._export_report)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh)

        for btn in [self.btn_check_index, self.btn_check_rank, self.btn_check_all,
                     self.btn_export, self.btn_refresh]:
            toolbar.addWidget(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

        # ====== 统计栏 ======
        stats_layout = QHBoxLayout()
        self.stats_widget = QLabel()
        stats_layout.addWidget(self.stats_widget)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # ====== 左右分栏 ======
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左栏: 关键词管理
        left = QWidget()
        left_layout = QVBoxLayout(left)
        add_group = QGroupBox("添加关键词")
        add_layout = QFormLayout(add_group)
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("关键词，如: 杭州文网文代办")
        self.kw_url = QLineEdit()
        self.kw_url.setPlaceholderText("目标URL(可选，留空使用企业网站)")
        kw_bar = QHBoxLayout()
        kw_bar.addWidget(QLabel("分组:"))
        self.kw_group = QComboBox()
        self.kw_group.setEditable(True)
        self.kw_group.addItem("默认")
        kw_bar.addWidget(self.kw_group)
        btn_add_kw = QPushButton("添加")
        btn_add_kw.clicked.connect(self._add_keyword)
        kw_bar.addWidget(btn_add_kw)
        add_layout.addRow("关键词:", self.kw_input)
        add_layout.addRow("目标URL:", self.kw_url)
        add_layout.addRow(kw_bar)
        left_layout.addWidget(add_group)

        # 关键词列表
        left_layout.addWidget(QLabel("关键词列表 (右键删除/启禁)"))
        self.kw_table = QTableWidget()
        self.kw_table.setColumnCount(7)
        self.kw_table.setHorizontalHeaderLabels([
            "ID", "关键词", "目标URL", "分组", "状态", "百度排名", "360排名"
        ])
        self.kw_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.kw_table.setAlternatingRowColors(True)
        kw_header = self.kw_table.horizontalHeader()
        kw_header.setStretchLastSection(True)
        kw_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        kw_col_widths = [35, 140, 180, 80, 50, 70, 70]
        for i, w in enumerate(kw_col_widths):
            self.kw_table.setColumnWidth(i, w)
        self.kw_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.kw_table.customContextMenuRequested.connect(self._kw_context_menu)
        left_layout.addWidget(self.kw_table)

        splitter.addWidget(left)

        # 右栏: 排名记录
        right = QWidget()
        right_layout = QVBoxLayout(right)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("引擎:"))
        self.engine_filter = QComboBox()
        self.engine_filter.addItems(["全部", "baidu", "360", "sogou"])
        self.engine_filter.currentIndexChanged.connect(self.refresh_records)
        filter_layout.addWidget(self.engine_filter)
        filter_layout.addWidget(QLabel("关键词:"))
        self.record_kw_filter = QLineEdit()
        self.record_kw_filter.setPlaceholderText("输入关键词筛选...")
        self.record_kw_filter.textChanged.connect(self.refresh_records)
        filter_layout.addWidget(self.record_kw_filter)
        filter_layout.addStretch()
        right_layout.addLayout(filter_layout)

        right_layout.addWidget(QLabel("排名检测记录"))
        self.record_table = QTableWidget()
        self.record_table.setColumnCount(9)
        self.record_table.setHorizontalHeaderLabels([
            "关键词", "引擎", "类型", "排名", "状态", "找到URL", "标题", "摘要", "检查时间"
        ])
        self.record_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.record_table.setAlternatingRowColors(True)
        seo_rec_header = self.record_table.horizontalHeader()
        seo_rec_header.setStretchLastSection(True)
        seo_rec_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        seo_col_widths = [100, 45, 45, 40, 50, 160, 140, 180, 100]
        for i, w in enumerate(seo_col_widths):
            self.record_table.setColumnWidth(i, w)
        right_layout.addWidget(self.record_table)

        splitter.addWidget(right)
        splitter.setSizes([400, 700])
        layout.addWidget(splitter)

    # ====== 刷新 ======

    def refresh(self, _=None):
        self._refresh_keywords()
        self.refresh_records()
        self._update_stats()

    def _refresh_keywords(self):
        try:
            rows = self.db_manager.fetch_all(
                "SELECT * FROM seo_keywords ORDER BY id"
            )
            self.kw_table.setRowCount(len(rows))

            # 获取每条关键词的最新排名
            latest_ranks = {}
            for eng in ["baidu", "360"]:
                rank_rows = self.db_manager.fetch_all(
                    "SELECT keyword_id, rank_position, is_indexed FROM seo_rankings "
                    "WHERE search_engine = ? AND check_type = 'rank' "
                    "AND check_time = (SELECT MAX(check_time) FROM seo_rankings WHERE search_engine = ?)",
                    (eng, eng)
                )
                for rr in rank_rows:
                    key = (rr["keyword_id"], eng)
                    latest_ranks[key] = rr["rank_position"] if rr["is_indexed"] else "未收录"

            for r, row in enumerate(rows):
                items = [
                    QTableWidgetItem(str(row["id"])),
                    QTableWidgetItem(row["keyword"]),
                    QTableWidgetItem((row["target_url"] or "")[:50]),
                    QTableWidgetItem(row["group_name"] or "-"),
                    QTableWidgetItem("启用" if row["enabled"] else "禁用"),
                    QTableWidgetItem(str(latest_ranks.get((row["id"], "baidu"), "-"))),
                    QTableWidgetItem(str(latest_ranks.get((row["id"], "360"), "-"))),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.kw_table.setItem(r, c, item)

            # 更新分组下拉
            current = self.kw_group.currentText()
            self.kw_group.clear()
            self.kw_group.addItem("默认")
            groups = self.db_manager.fetch_all(
                "SELECT DISTINCT group_name FROM seo_keywords WHERE group_name != ''"
            )
            for g in groups:
                if g["group_name"]:
                    self.kw_group.addItem(g["group_name"])
            self.kw_group.setCurrentText(current)
        except Exception as e:
            logger.error(f"刷新关键词列表异常: {e}")

    def refresh_records(self, _=None):
        try:
            engine = self.engine_filter.currentText()
            kw_filter = self.record_kw_filter.text().strip()

            sql = "SELECT * FROM seo_rankings WHERE 1=1"
            params = []

            if engine != "全部":
                sql += " AND search_engine = ?"
                params.append(engine)
            if kw_filter:
                sql += " AND keyword LIKE ?"
                params.append(f"%{kw_filter}%")

            sql += " ORDER BY check_time DESC LIMIT 500"
            rows = self.db_manager.fetch_all(sql, tuple(params))
            self.record_table.setRowCount(len(rows))

            for r, row in enumerate(rows):
                status_text = "已收录" if row["is_indexed"] else "未收录"
                items = [
                    QTableWidgetItem(row["keyword"]),
                    QTableWidgetItem(row["search_engine"]),
                    QTableWidgetItem(row["check_type"]),
                    QTableWidgetItem(str(row["rank_position"]) if row["rank_position"] > 0 else "-"),
                    QTableWidgetItem(status_text),
                    QTableWidgetItem((row["found_url"] or "")[:50]),
                    QTableWidgetItem((row["title"] or "")[:40]),
                    QTableWidgetItem((row["snippet"] or "")[:60]),
                    QTableWidgetItem(row["check_time"] or ""),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if row["is_indexed"] and row["rank_position"] > 0 and row["rank_position"] <= 10:
                        item.setBackground(QColor(theme_manager.get_color("row_proxy_active", "#c8ffc8")))
                    elif not row["is_indexed"]:
                        item.setBackground(QColor(theme_manager.get_color("row_banned", "#ffc8c8")))
                    self.record_table.setItem(r, c, item)
        except Exception as e:
            logger.error(f"刷新排名记录异常: {e}")

    def _update_stats(self):
        stats = seo_engine.get_stats()
        auto = "自动重发: 开启" if seo_engine.auto_republish else "自动重发: 关闭"
        self.stats_widget.setText(
            f"关键词: {stats['total_keywords']} | "
            f"已收录: {stats['indexed']} | "
            f"收录率: {stats['index_rate']}% | "
            f"平均排名: {stats['avg_rank']} | "
            f"{auto} | "
            f"引擎: {', '.join(seo_engine.engine_names)} | "
            f"间隔: {seo_engine.check_interval_hours}h"
        )

    # ====== 操作 ======

    def _add_keyword(self):
        kw = self.kw_input.text().strip()
        if not kw:
            return
        url = self.kw_url.text().strip()
        group = self.kw_group.currentText().strip()
        if group == "默认":
            group = ""
        seo_engine.add_keyword(kw, url, group)
        self.kw_input.clear()
        self.kw_url.clear()
        self.refresh()

    def _kw_context_menu(self, pos):
        rows = set(item.row() for item in self.kw_table.selectedItems())
        if not rows:
            return
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_keywords(rows))
        menu.addAction(delete_action)

        toggle_action = QAction("启用/禁用", self)
        toggle_action.triggered.connect(lambda: self._toggle_keyword(rows))
        menu.addAction(toggle_action)

        menu.exec(self.kw_table.viewport().mapToGlobal(pos))

    def _delete_keywords(self, rows):
        for row in rows:
            kid = int(self.kw_table.item(row, 0).text())
            seo_engine.delete_keyword(kid)
        self.refresh()

    def _toggle_keyword(self, rows):
        for row in rows:
            kid = int(self.kw_table.item(row, 0).text())
            current = self.db_manager.fetch_one(
                "SELECT enabled FROM seo_keywords WHERE id = ?", (kid,)
            )
            if current:
                new_val = 0 if current["enabled"] else 1
                self.db_manager.update("seo_keywords", {"enabled": new_val}, "id = ?", (kid,))
        self.refresh()

    def _run_check(self, check_type: str):
        self.btn_check_index.setEnabled(False)
        self.btn_check_rank.setEnabled(False)
        self.btn_check_all.setEnabled(False)
        self.status_label.setText("检查中...")

        self._check_thread = SeoCheckThread(check_type)
        self._check_thread.progress.connect(self.status_label.setText)
        self._check_thread.finished_signal.connect(self._on_check_finished)
        self._check_thread.start()

    def _on_check_finished(self):
        self.btn_check_index.setEnabled(True)
        self.btn_check_rank.setEnabled(True)
        self.btn_check_all.setEnabled(True)
        self.status_label.setText("检查完成")
        self.refresh()

    def _export_report(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出排名报表",
            f"seo_report_{format_datetime(fmt='%Y%m%d_%H%M')}.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        count = seo_engine.export_report_csv(path)
        QMessageBox.information(self, "导出完成", f"已导出 {count} 条记录到:\n{path}")
