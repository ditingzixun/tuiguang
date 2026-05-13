"""任务管理界面 -- 发布任务创建、调度、监控"""
import os
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDateTimeEdit, QMessageBox, QHeaderView,
    QLabel, QDialog, QDialogButtonBox, QCheckBox,
    QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)
from ui.styles.theme_manager import theme_manager


class TaskDialog(QDialog):
    """创建发布任务"""
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("创建发布任务")
        self.setMinimumWidth(550)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("任务名称")
        layout.addRow("任务名称:", self.name_edit)

        self.platform_combo = QComboBox()
        self.platform_combo.setEditable(True)
        self.platform_combo.addItems([
            "huangye88", "qianyan", "zhongyewang", "zhihu",
            "baidu_tieba", "douban", "csdn", "jianshu", "custom"
        ])
        layout.addRow("目标平台:", self.platform_combo)

        self.account_combo = QComboBox()
        layout.addRow("发布账号:", self.account_combo)

        self.content_combo = QComboBox()
        layout.addRow("选择文案:", self.content_combo)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("可覆盖文案原标题")
        layout.addRow("标题(可选):", self.title_edit)

        self.schedule_check = QCheckBox("定时发布")
        self.schedule_check.setChecked(True)
        layout.addRow("", self.schedule_check)

        self.schedule_time = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.schedule_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        layout.addRow("发布时间:", self.schedule_time)

        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        layout.addRow("最大重试:", self.retry_spin)

        # 图片附件
        image_layout = QVBoxLayout()
        img_toolbar = QHBoxLayout()
        self.image_list = QListWidget()
        self.image_list.setMaximumHeight(60)
        self.image_list.setAlternatingRowColors(True)
        self.btn_add_images = QPushButton("添加配图...")
        self.btn_add_images.clicked.connect(self._add_images)
        self.btn_clear_images = QPushButton("清空")
        self.btn_clear_images.clicked.connect(self.image_list.clear)
        img_toolbar.addWidget(self.btn_add_images)
        img_toolbar.addWidget(self.btn_clear_images)
        img_toolbar.addStretch()
        image_layout.addWidget(QLabel("配图列表:"))
        image_layout.addWidget(self.image_list)
        image_layout.addLayout(img_toolbar)
        layout.addRow(image_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_data(self):
        if not self.db_manager:
            return
        try:
            accounts = self.db_manager.fetch_all(
                "SELECT id, platform, username FROM accounts WHERE status = 'active'"
            )
            for acc in accounts:
                self.account_combo.addItem(f"[{acc['platform']}] {acc['username']}", acc["id"])

            contents = self.db_manager.fetch_all(
                "SELECT id, title, content_type FROM contents WHERE status = 'approved'"
            )
            for c in contents:
                self.content_combo.addItem(f"[{c['content_type']}] {c['title'][:40]}", c["id"])
        except Exception as e:
            logger.error(f"加载数据失败: {e}")

    def _add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择配图", "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;所有文件 (*)"
        )
        for path in paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.image_list.addItem(item)

    def get_data(self):
        return {
            "name": self.name_edit.text() or f"发布任务-{format_datetime(fmt='%m%d%H%M')}",
            "platform": self.platform_combo.currentText(),
            "account_id": self.account_combo.currentData(),
            "content_id": self.content_combo.currentData(),
            "title": self.title_edit.text() or None,
            "scheduled_at": self.schedule_time.toPython().strftime("%Y-%m-%d %H:%M:%S") if self.schedule_check.isChecked() else None,
            "max_retries": self.retry_spin.value(),
            "image_paths": self._get_image_paths_json(),
        }

    def _get_image_paths_json(self):
        import json
        paths = [
            self.image_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.image_list.count())
        ]
        return json.dumps(paths, ensure_ascii=False)


class TaskManagerWidget(QWidget):
    """任务管理面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_create = QPushButton("创建任务")
        self.btn_create.clicked.connect(self._create_task)
        self.btn_cancel = QPushButton("取消任务")
        self.btn_cancel.clicked.connect(self._cancel_selected)
        self.btn_retry = QPushButton("失败重试")
        self.btn_retry.clicked.connect(self._retry_failed)
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh_table)

        for btn in [self.btn_create, self.btn_cancel, self.btn_retry, self.btn_delete, self.btn_refresh]:
            toolbar.addWidget(btn)
        layout.addLayout(toolbar)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("状态筛选:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "pending", "running", "success", "failed"])
        self.status_filter.currentIndexChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "任务名称", "平台", "标题", "状态", "重试",
            "计划时间", "开始时间", "完成时间", "结果链接", "错误信息"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        col_widths = [35, 120, 80, 140, 50, 50, 100, 100, 100, 140, 120]
        for i, w in enumerate(col_widths):
            self.table.setColumnWidth(i, w)
        layout.addWidget(self.table)

        self.stats_label = QLabel("共 0 个任务 | 待执行: 0 | 成功: 0 | 失败: 0")
        layout.addWidget(self.stats_label)

    def refresh_table(self, _=None):
        try:
            status = self.status_filter.currentText()
            if status == "全部":
                rows = self.db_manager.fetch_all("SELECT * FROM tasks ORDER BY created_at DESC")
            else:
                rows = self.db_manager.fetch_all(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,)
                )

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                items = [
                    QTableWidgetItem(str(row["id"])),
                    QTableWidgetItem(row["name"] or ""),
                    QTableWidgetItem(row["platform"]),
                    QTableWidgetItem((row["title"] or "")[:50]),
                    QTableWidgetItem(row["status"]),
                    QTableWidgetItem(f"{row['retry_count']}/{row['max_retries']}"),
                    QTableWidgetItem(row["scheduled_at"] or "立即"),
                    QTableWidgetItem(row["started_at"] or "-"),
                    QTableWidgetItem(row["completed_at"] or "-"),
                    QTableWidgetItem((row["result_url"] or "")[:60]),
                    QTableWidgetItem((row["error_message"] or "")[:80]),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if row["status"] == "failed":
                        item.setBackground(QColor(theme_manager.get_color("row_proxy_failed", "#ffc8c8")))
                    elif row["status"] == "success":
                        item.setBackground(QColor(theme_manager.get_color("row_proxy_active", "#c8ffc8")))
                    elif row["status"] == "running":
                        item.setBackground(QColor(200, 200, 255))
                    self.table.setItem(r, c, item)

            pending = sum(1 for row in rows if row["status"] == "pending")
            success = sum(1 for row in rows if row["status"] == "success")
            failed = sum(1 for row in rows if row["status"] == "failed")
            self.stats_label.setText(
                f"共 {len(rows)} 个任务 | 待执行: {pending} | 成功: {success} | 失败: {failed}"
            )
        except Exception as e:
            logger.error(f"刷新任务列表异常: {e}")

    def _create_task(self):
        dialog = TaskDialog(self, self.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                data["created_at"] = format_datetime()
                data["updated_at"] = data["created_at"]
                self.db_manager.insert("tasks", data)
                self.refresh_table()
            except Exception as e:
                logger.error(f"创建任务失败: {e}")
                QMessageBox.critical(self, "错误", f"创建任务失败: {e}")

    def _cancel_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        try:
            for row in rows:
                task_id = int(self.table.item(row, 0).text())
                self.db_manager.update("tasks", {"status": "pending"}, "id = ?", (task_id,))
            self.refresh_table()
        except Exception as e:
            logger.error(f"取消失败: {e}")

    def _retry_failed(self):
        try:
            self.db_manager.execute("UPDATE tasks SET status = 'pending', retry_count = 0 WHERE status = 'failed'")
            self.refresh_table()
            QMessageBox.information(self, "重试", "已重置所有失败任务")
        except Exception as e:
            logger.error(f"重试失败: {e}")

    def _delete_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        reply = QMessageBox.question(self, "确认", f"删除 {len(rows)} 个任务？")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for row in rows:
                    task_id = int(self.table.item(row, 0).text())
                    self.db_manager.delete("tasks", "id = ?", (task_id,))
                self.refresh_table()
            except Exception as e:
                logger.error(f"删除失败: {e}")
