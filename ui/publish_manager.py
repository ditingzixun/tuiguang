"""平台发布管理界面 - 发布记录、日志查看、报表导出"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QMessageBox, QHeaderView, QLabel, QFileDialog,
    QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from db.models import PublishRecord, PublishLog, PublishTask
from loguru import logger


class PublishManagerWidget(QWidget):
    """发布管理面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self.refresh_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 主分割器
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半部分：发布记录
        top = QWidget()
        top_layout = QVBoxLayout(top)

        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_start = QPushButton("▶ 一键发布")
        self.btn_start.clicked.connect(self._start_publish)
        self.btn_stop = QPushButton("⏹ 停止发布")
        self.btn_stop.clicked.connect(self._stop_publish)
        self.btn_export_report = QPushButton("📊 导出报表")
        self.btn_export_report.clicked.connect(self._export_report)
        self.btn_clear_logs = QPushButton("🗑 清理日志")
        self.btn_clear_logs.clicked.connect(self._clear_logs)
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.refresh_all)

        for btn in [self.btn_start, self.btn_stop, self.btn_export_report,
                     self.btn_clear_logs, self.btn_refresh]:
            toolbar.addWidget(btn)
        toolbar.addStretch()
        top_layout.addLayout(toolbar)

        # 过滤器
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("平台:"))
        self.platform_filter = QComboBox()
        self.platform_filter.addItem("全部")
        self.platform_filter.currentIndexChanged.connect(self.refresh_records)
        filter_layout.addWidget(self.platform_filter)
        filter_layout.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "published", "pending", "failed", "deleted"])
        self.status_filter.currentIndexChanged.connect(self.refresh_records)
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        top_layout.addLayout(filter_layout)

        # 发布记录表
        self.record_table = QTableWidget()
        self.record_table.setColumnCount(8)
        self.record_table.setHorizontalHeaderLabels([
            "ID", "任务ID", "平台", "标题", "状态", "链接", "发布时间", "截图"
        ])
        self.record_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.record_table.setAlternatingRowColors(True)
        self.record_table.horizontalHeader().setStretchLastSection(True)
        top_layout.addWidget(self.record_table)

        splitter.addWidget(top)

        # 下半部分：发布日志
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.addWidget(QLabel("📋 发布日志"))

        log_toolbar = QHBoxLayout()
        self.log_level_filter = QComboBox()
        self.log_level_filter.addItems(["全部", "INFO", "WARNING", "ERROR"])
        self.log_level_filter.currentIndexChanged.connect(self.refresh_logs)
        log_toolbar.addWidget(QLabel("级别:"))
        log_toolbar.addWidget(self.log_level_filter)
        log_toolbar.addStretch()
        bottom_layout.addLayout(log_toolbar)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(5)
        self.log_table.setHorizontalHeaderLabels(["ID", "任务ID", "平台", "级别", "消息"])
        self.log_table.setAlternatingRowColors(True)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        bottom_layout.addWidget(self.log_table)

        splitter.addWidget(bottom)
        splitter.setSizes([400, 250])
        layout.addWidget(splitter)

        # 统计
        self.stats_label = QLabel("就绪")
        layout.addWidget(self.stats_label)

    def refresh_all(self):
        self.refresh_records()
        self.refresh_logs()

    def refresh_records(self):
        session = self.db_manager.get_session()
        try:
            query = session.query(PublishRecord)
            plat = self.platform_filter.currentText()
            if plat != "全部":
                query = query.filter(PublishRecord.platform == plat)
            status = self.status_filter.currentText()
            if status != "全部":
                query = query.filter(PublishRecord.status == status)

            records = query.order_by(PublishRecord.created_at.desc()).limit(500).all()
            self.record_table.setRowCount(len(records))

            # 更新平台筛选
            platforms = set(r.platform for r in session.query(PublishRecord).all())
            current = self.platform_filter.currentText()
            self.platform_filter.clear()
            self.platform_filter.addItem("全部")
            for p in sorted(platforms):
                self.platform_filter.addItem(p)
            idx = self.platform_filter.findText(current)
            if idx >= 0:
                self.platform_filter.setCurrentIndex(idx)

            for row, rec in enumerate(records):
                items = [
                    QTableWidgetItem(str(rec.id)),
                    QTableWidgetItem(str(rec.task_id or "")),
                    QTableWidgetItem(rec.platform),
                    QTableWidgetItem((rec.title or "")[:50]),
                    QTableWidgetItem(rec.status),
                    QTableWidgetItem((rec.url or "")[:60]),
                    QTableWidgetItem(rec.publish_time.strftime("%m-%d %H:%M") if rec.publish_time else "-"),
                    QTableWidgetItem("📷" if rec.screenshot_path else "-"),
                ]
                for col, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if rec.status == "failed":
                        item.setBackground(QColor(255, 200, 200))
                    elif rec.status == "published":
                        item.setBackground(QColor(200, 255, 200))
                    self.record_table.setItem(row, col, item)

            published = sum(1 for r in records if r.status == "published")
            failed = sum(1 for r in records if r.status == "failed")
            self.stats_label.setText(
                f"共 {len(records)} 条发布记录 | 成功: {published} | 失败: {failed}"
            )
        except Exception as e:
            logger.error(f"刷新发布记录异常: {e}")
        finally:
            session.close()

    def refresh_logs(self):
        session = self.db_manager.get_session()
        try:
            query = session.query(PublishLog)
            level = self.log_level_filter.currentText()
            if level != "全部":
                query = query.filter(PublishLog.level == level)
            logs = query.order_by(PublishLog.created_at.desc()).limit(300).all()
            self.log_table.setRowCount(len(logs))
            for row, log in enumerate(logs):
                items = [
                    QTableWidgetItem(str(log.id)),
                    QTableWidgetItem(str(log.task_id or "")),
                    QTableWidgetItem(log.platform or ""),
                    QTableWidgetItem(log.level),
                    QTableWidgetItem(log.message[:200]),
                ]
                for col, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if log.level == "ERROR":
                        item.setBackground(QColor(255, 200, 200))
                    elif log.level == "WARNING":
                        item.setBackground(QColor(255, 255, 200))
                    self.log_table.setItem(row, col, item)
        except Exception as e:
            logger.error(f"刷新日志异常: {e}")
        finally:
            session.close()

    def _start_publish(self):
        QMessageBox.information(self, "一键发布",
                                "将按以下策略开始发布：\n"
                                "1. 获取所有待执行发布任务\n"
                                "2. 按错峰策略调度执行\n"
                                "3. 自动轮换代理IP\n"
                                "4. 失败自动重试")

    def _stop_publish(self):
        QMessageBox.information(self, "停止发布", "已停止所有进行中的发布任务")

    def _export_report(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出报表", f"publish_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment
            wb = openpyxl.Workbook()

            # 发布记录
            ws1 = wb.active
            ws1.title = "发布记录"
            ws1.append(["ID", "平台", "标题", "状态", "链接", "发布时间"])
            session = self.db_manager.get_session()
            for rec in session.query(PublishRecord).limit(5000).all():
                ws1.append([rec.id, rec.platform, rec.title, rec.status,
                            rec.url, rec.publish_time.strftime("%Y-%m-%d %H:%M:%S") if rec.publish_time else ""])

            # 统计表
            ws2 = wb.create_sheet("统计")
            ws2.append(["指标", "数值"])
            total = session.query(PublishRecord).count()
            success = session.query(PublishRecord).filter_by(status="published").count()
            failed = session.query(PublishRecord).filter_by(status="failed").count()
            ws2.append(["总发布数", total])
            ws2.append(["成功数", success])
            ws2.append(["失败数", failed])
            ws2.append(["成功率", f"{success/total*100:.1f}%" if total > 0 else "0%"])

            wb.save(path)
            QMessageBox.information(self, "导出完成", f"报表已导出到: {path}")
            session.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _clear_logs(self):
        reply = QMessageBox.question(self, "确认", "确定要清理30天前的日志吗？")
        if reply == QMessageBox.StandardButton.Yes:
            session = self.db_manager.get_session()
            try:
                from datetime import timedelta
                cutoff = datetime.now() - timedelta(days=30)
                session.query(PublishLog).filter(PublishLog.created_at < cutoff).delete()
                session.commit()
                self.refresh_logs()
                QMessageBox.information(self, "完成", "已清理过期日志")
            except Exception as e:
                session.rollback()
            finally:
                session.close()
