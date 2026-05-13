"""平台发布管理界面 — 发布记录、报表导出"""
import csv
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QMessageBox, QHeaderView, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)
from ui.styles.theme_manager import theme_manager
from scheduler.task_scheduler import task_scheduler


class PublishManagerWidget(QWidget):
    """发布管理面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self.refresh_records()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_start = QPushButton("一键发布")
        self.btn_start.clicked.connect(self._start_publish)
        self.btn_stop = QPushButton("停止发布")
        self.btn_stop.clicked.connect(self._stop_publish)
        self.btn_export = QPushButton("导出报表CSV")
        self.btn_export.clicked.connect(self._export_report)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh_records)

        for btn in [self.btn_start, self.btn_stop, self.btn_export, self.btn_refresh]:
            toolbar.addWidget(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("平台:"))
        self.platform_filter = QComboBox()
        self.platform_filter.addItem("全部")
        self.platform_filter.currentIndexChanged.connect(self.refresh_records)
        filter_layout.addWidget(self.platform_filter)
        filter_layout.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "published", "pending", "failed"])
        self.status_filter.currentIndexChanged.connect(self.refresh_records)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.record_table = QTableWidget()
        self.record_table.setColumnCount(8)
        self.record_table.setHorizontalHeaderLabels([
            "ID", "任务ID", "平台", "标题", "状态", "链接", "发布时间", "截图"
        ])
        self.record_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.record_table.setAlternatingRowColors(True)
        rec_header = self.record_table.horizontalHeader()
        rec_header.setStretchLastSection(True)
        rec_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        rec_col_widths = [35, 50, 70, 160, 50, 180, 100, 40]
        for i, w in enumerate(rec_col_widths):
            self.record_table.setColumnWidth(i, w)
        layout.addWidget(self.record_table)

        self.stats_label = QLabel("就绪")
        layout.addWidget(self.stats_label)

    def refresh_records(self, _=None):
        if getattr(self, "_updating_records", False):
            return
        try:
            self._updating_records = True
            plat = self.platform_filter.currentText()
            status = self.status_filter.currentText()

            sql = "SELECT * FROM publish_records WHERE 1=1"
            params = []
            if plat != "全部":
                sql += " AND platform = ?"
                params.append(plat)
            if status != "全部":
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC LIMIT 500"

            rows = self.db_manager.fetch_all(sql, tuple(params))
            self.record_table.setRowCount(len(rows))

            # 更新平台筛选器
            platforms = self.db_manager.fetch_all("SELECT DISTINCT platform FROM publish_records")
            current = self.platform_filter.currentText()
            self.platform_filter.blockSignals(True)
            self.platform_filter.clear()
            self.platform_filter.addItem("全部")
            for p in platforms:
                self.platform_filter.addItem(p["platform"])
            self.platform_filter.blockSignals(False)
            idx = self.platform_filter.findText(current)
            if idx >= 0:
                self.platform_filter.setCurrentIndex(idx)

            for r, row in enumerate(rows):
                items = [
                    QTableWidgetItem(str(row["id"])),
                    QTableWidgetItem(str(row["task_id"] or "")),
                    QTableWidgetItem(row["platform"]),
                    QTableWidgetItem((row["title"] or "")[:50]),
                    QTableWidgetItem(row["status"]),
                    QTableWidgetItem((row["url"] or "")[:60]),
                    QTableWidgetItem(row["publish_time"] or "-"),
                    QTableWidgetItem("Y" if row["screenshot_path"] else "-"),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if row["status"] == "failed":
                        item.setBackground(QColor(theme_manager.get_color("row_banned", "#ffc8c8")))
                    elif row["status"] == "published":
                        item.setBackground(QColor(theme_manager.get_color("row_proxy_active", "#c8ffc8")))
                    self.record_table.setItem(r, c, item)

            published = sum(1 for row in rows if row["status"] == "published")
            failed = sum(1 for row in rows if row["status"] == "failed")
            self.stats_label.setText(f"共 {len(rows)} 条发布记录 | 成功: {published} | 失败: {failed}")
        except Exception as e:
            logger.error(f"刷新发布记录异常: {e}")
        finally:
            self._updating_records = False

    def _start_publish(self):
        try:
            tasks = self.db_manager.fetch_all("""
                SELECT t.* FROM tasks t
                LEFT JOIN platform_configs pc ON t.platform = pc.plugin_name
                WHERE t.status = 'pending'
                AND (pc.enabled = 1 OR pc.enabled IS NULL)
                ORDER BY t.created_at
            """)
            if not tasks:
                QMessageBox.information(self, "提示", "没有待执行的发布任务")
                return

            task_dicts = [dict(t) for t in tasks]
            task_scheduler.schedule_batch_publish(task_dicts, stagger=True)
            self.db_manager.execute(
                "UPDATE tasks SET status = 'scheduled', updated_at = ? WHERE status = 'pending'",
                (format_datetime(),)
            )
            self.refresh_records()
            QMessageBox.information(
                self, "一键发布",
                f"已调度 {len(task_dicts)} 个发布任务，将按错峰策略依次执行"
            )
        except Exception as e:
            logger.error(f"一键发布失败: {e}")
            QMessageBox.critical(self, "错误", f"调度失败: {e}")

    def _stop_publish(self):
        reply = QMessageBox.question(
            self, "确认", "确定要停止所有进行中的发布任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            task_scheduler.cancel_all_publish_jobs()
            self.db_manager.execute(
                "UPDATE tasks SET status = 'pending', updated_at = ? WHERE status IN ('scheduled', 'running')",
                (format_datetime(),)
            )
            self.refresh_records()
            QMessageBox.information(self, "停止发布", "已停止所有发布任务，状态已重置")

    def _export_report(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出报表", f"publish_report_{format_datetime(fmt='%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        try:
            records = self.db_manager.fetch_all(
                "SELECT id, platform, title, status, url, publish_time FROM publish_records LIMIT 5000"
            )
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id", "platform", "title", "status", "url", "publish_time"])
                writer.writeheader()
                for row in records:
                    writer.writerow(dict(row))

            # 统计
            total = self.db_manager.fetch_one("SELECT COUNT(*) as cnt FROM publish_records")
            success = self.db_manager.fetch_one("SELECT COUNT(*) as cnt FROM publish_records WHERE status = 'published'")
            total_cnt = total["cnt"] if total else 0
            success_cnt = success["cnt"] if success else 0

            QMessageBox.information(self, "导出完成",
                                    f"报表已导出到: {path}\n"
                                    f"总发布: {total_cnt} | 成功: {success_cnt} | "
                                    f"成功率: {success_cnt/total_cnt*100:.1f}%" if total_cnt > 0 else "0%")
        except Exception as e:
            logger.error(f"导出失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败: {e}")
