"""任务管理界面 - 发布任务创建、调度、监控"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QDateTimeEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QDialog, QDialogButtonBox, QCheckBox, QProgressBar,
    QSplitter
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QColor
from db.models import PublishTask, Content, Account
from loguru import logger


class TaskDialog(QDialog):
    """创建/编辑发布任务"""
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("创建发布任务")
        self.setMinimumWidth(550)
        self._setup_ui()
        self._load_accounts_and_contents()

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

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_accounts_and_contents(self):
        if not self.db_manager:
            return
        session = self.db_manager.get_session()
        try:
            for acc in session.query(Account).filter(Account.status == "active").all():
                self.account_combo.addItem(f"[{acc.platform}] {acc.username}", acc.id)
            for c in session.query(Content).filter(Content.status == "approved").all():
                self.content_combo.addItem(f"[{c.content_type}] {c.title[:40]}", c.id)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
        finally:
            session.close()

    def get_data(self):
        return {
            "name": self.name_edit.text() or f"发布任务-{datetime.now().strftime('%m%d%H%M')}",
            "platform": self.platform_combo.currentText(),
            "account_id": self.account_combo.currentData(),
            "content_id": self.content_combo.currentData(),
            "title": self.title_edit.text() or None,
            "scheduled_at": self.schedule_time.toPyDateTime() if self.schedule_check.isChecked() else None,
            "max_retries": self.retry_spin.value(),
        }


class TaskManagerWidget(QWidget):
    """任务管理面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_create = QPushButton("➕ 创建任务")
        self.btn_create.clicked.connect(self._create_task)
        self.btn_batch = QPushButton("📦 批量创建")
        self.btn_batch.clicked.connect(self._batch_create)
        self.btn_run = QPushButton("▶ 立即执行")
        self.btn_run.clicked.connect(self._run_selected)
        self.btn_cancel = QPushButton("⏹ 取消任务")
        self.btn_cancel.clicked.connect(self._cancel_selected)
        self.btn_retry = QPushButton("🔄 失败重试")
        self.btn_retry.clicked.connect(self._retry_failed)
        self.btn_delete = QPushButton("🗑 删除")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.refresh_table)

        for btn in [self.btn_create, self.btn_batch, self.btn_run, self.btn_cancel,
                     self.btn_retry, self.btn_delete, self.btn_refresh]:
            toolbar.addWidget(btn)
        layout.addLayout(toolbar)

        # 过滤器
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("状态筛选:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "pending", "running", "success", "failed"])
        self.status_filter.currentIndexChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(QLabel("平台筛选:"))
        self.platform_filter = QComboBox()
        self.platform_filter.setEditable(True)
        self.platform_filter.addItem("全部")
        self.platform_filter.currentIndexChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.platform_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 任务表格
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "任务名称", "平台", "标题", "状态", "重试次数",
            "计划时间", "开始时间", "完成时间", "结果链接", "错误信息"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # 统计
        self.stats_label = QLabel("共 0 个任务 | 待执行: 0 | 执行中: 0 | 成功: 0 | 失败: 0")
        layout.addWidget(self.stats_label)

    def refresh_table(self):
        session = self.db_manager.get_session()
        try:
            query = session.query(PublishTask)
            status = self.status_filter.currentText()
            if status != "全部":
                query = query.filter(PublishTask.status == status)

            tasks = query.order_by(PublishTask.created_at.desc()).all()
            self.table.setRowCount(len(tasks))

            # 更新平台过滤器
            platforms = set(t.platform for t in tasks)
            current = self.platform_filter.currentText()
            self.platform_filter.clear()
            self.platform_filter.addItem("全部")
            for p in sorted(platforms):
                self.platform_filter.addItem(p)
            idx = self.platform_filter.findText(current)
            if idx >= 0:
                self.platform_filter.setCurrentIndex(idx)

            for row, task in enumerate(tasks):
                items = [
                    QTableWidgetItem(str(task.id)),
                    QTableWidgetItem(task.name or ""),
                    QTableWidgetItem(task.platform),
                    QTableWidgetItem((task.title or "")[:50]),
                    QTableWidgetItem(task.status),
                    QTableWidgetItem(f"{task.retry_count}/{task.max_retries}"),
                    QTableWidgetItem(task.scheduled_at.strftime("%m-%d %H:%M") if task.scheduled_at else "立即"),
                    QTableWidgetItem(task.started_at.strftime("%m-%d %H:%M") if task.started_at else "-"),
                    QTableWidgetItem(task.completed_at.strftime("%m-%d %H:%M") if task.completed_at else "-"),
                    QTableWidgetItem((task.result_url or "")[:60]),
                    QTableWidgetItem((task.error_message or "")[:80]),
                ]
                for col, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if task.status == "failed":
                        item.setBackground(QColor(255, 200, 200))
                    elif task.status == "success":
                        item.setBackground(QColor(200, 255, 200))
                    elif task.status == "running":
                        item.setBackground(QColor(200, 200, 255))
                    self.table.setItem(row, col, item)

            pending = sum(1 for t in tasks if t.status == "pending")
            running = sum(1 for t in tasks if t.status == "running")
            success = sum(1 for t in tasks if t.status == "success")
            failed = sum(1 for t in tasks if t.status == "failed")
            self.stats_label.setText(
                f"共 {len(tasks)} 个任务 | 待执行: {pending} | 执行中: {running} | 成功: {success} | 失败: {failed}"
            )
        except Exception as e:
            logger.error(f"刷新任务列表异常: {e}")
        finally:
            session.close()

    def _create_task(self):
        dialog = TaskDialog(self, self.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            session = self.db_manager.get_session()
            try:
                task = PublishTask(
                    name=data["name"],
                    platform=data["platform"],
                    account_id=data["account_id"],
                    content_id=data["content_id"],
                    title=data["title"],
                    scheduled_at=data["scheduled_at"],
                    max_retries=data["max_retries"],
                )
                session.add(task)
                session.commit()
                self.refresh_table()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "错误", f"创建任务失败: {e}")
            finally:
                session.close()

    def _batch_create(self):
        QMessageBox.information(self, "提示",
                                "批量创建任务功能：\n"
                                "1. 选择多个平台\n"
                                "2. 选择多个文案\n"
                                "3. 选择多个账号\n"
                                "4. 系统自动组合创建任务")

    def _run_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择要执行的任务")
            return
        QMessageBox.information(self, "提示", f"已加入执行队列: {len(rows)} 个任务")

    def _cancel_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        session = self.db_manager.get_session()
        try:
            for row in rows:
                task_id = int(self.table.item(row, 0).text())
                task = session.query(PublishTask).filter_by(id=task_id).first()
                if task and task.status in ("pending", "running"):
                    task.status = "pending"
            session.commit()
            self.refresh_table()
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def _retry_failed(self):
        session = self.db_manager.get_session()
        try:
            failed_tasks = session.query(PublishTask).filter_by(status="failed").all()
            for task in failed_tasks:
                task.status = "pending"
                task.retry_count = 0
            session.commit()
            self.refresh_table()
            QMessageBox.information(self, "重试", f"已重置 {len(failed_tasks)} 个失败任务")
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def _delete_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        reply = QMessageBox.question(self, "确认", f"删除 {len(rows)} 个任务？")
        if reply == QMessageBox.StandardButton.Yes:
            session = self.db_manager.get_session()
            try:
                for row in rows:
                    task_id = int(self.table.item(row, 0).text())
                    session.query(PublishTask).filter_by(id=task_id).delete()
                session.commit()
                self.refresh_table()
            except Exception as e:
                session.rollback()
            finally:
                session.close()
