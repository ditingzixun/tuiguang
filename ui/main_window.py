"""主窗口 - PyQt6桌面界面，6大功能菜单"""
import os
import sys
import asyncio
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QStatusBar,
    QMessageBox, QVBoxLayout, QWidget, QLabel, QApplication,
    QToolBar, QDockWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QFont

from ui.account_manager import AccountManagerWidget
from ui.task_manager import TaskManagerWidget
from ui.content_generator import ContentGeneratorWidget
from ui.publish_manager import PublishManagerWidget
from ui.monitor_manager import MonitorManagerWidget
from ui.settings_manager import SettingsManagerWidget
from db.database import DatabaseManager
from scheduler.task_scheduler import task_scheduler
from core.proxy_engine import proxy_engine
from loguru import logger


class AsyncInitThread(QThread):
    """异步初始化线程"""
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

    def run(self):
        try:
            self.db_manager.init_db()
            task_scheduler.set_db_manager(self.db_manager)
            proxy_engine.start()
            task_scheduler.start()
            self.finished_signal.emit(True, "系统初始化完成")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("资质代办全网推广助手 v1.0.0")
        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)
        self.db_manager = DatabaseManager()
        self._setup_logger()
        self._init_ui()
        self._init_menu_bar()
        self._init_status_bar()
        self._init_async()

    def _setup_logger(self):
        logger.add(
            os.path.join("data", "logs", "app_{time:YYYY-MM-DD}.log"),
            rotation="10 MB",
            retention="30 days",
            level="INFO",
            encoding="utf-8"
        )

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setDocumentMode(True)

        self.account_tab = AccountManagerWidget(self.db_manager)
        self.task_tab = TaskManagerWidget(self.db_manager)
        self.content_tab = ContentGeneratorWidget(self.db_manager)
        self.publish_tab = PublishManagerWidget(self.db_manager)
        self.monitor_tab = MonitorManagerWidget(self.db_manager)
        self.settings_tab = SettingsManagerWidget(self.db_manager)

        self.tab_widget.addTab(self.account_tab, "📋 账号管理")
        self.tab_widget.addTab(self.task_tab, "📝 任务管理")
        self.tab_widget.addTab(self.content_tab, "✏️ 文案生成")
        self.tab_widget.addTab(self.publish_tab, "🚀 平台发布")
        self.tab_widget.addTab(self.monitor_tab, "📊 收录监控")
        self.tab_widget.addTab(self.settings_tab, "⚙️ 系统设置")

        layout.addWidget(self.tab_widget)

    def _init_menu_bar(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        backup_action = QAction("备份数据库", self)
        backup_action.triggered.connect(self._backup_database)
        file_menu.addAction(backup_action)
        file_menu.addSeparator()
        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 引擎菜单
        engine_menu = menubar.addMenu("引擎(&E)")
        start_proxy_action = QAction("启动代理IP池", self)
        start_proxy_action.triggered.connect(lambda: proxy_engine.start())
        engine_menu.addAction(start_proxy_action)
        check_proxy_action = QAction("检测所有代理", self)
        check_proxy_action.triggered.connect(lambda: proxy_engine.check_all())
        engine_menu.addAction(check_proxy_action)
        engine_menu.addSeparator()
        start_scheduler_action = QAction("启动任务调度", self)
        start_scheduler_action.triggered.connect(lambda: task_scheduler.start())
        engine_menu.addAction(start_scheduler_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.proxy_label = QLabel("代理: -")
        self.publish_label = QLabel("今日发布: 0/20")
        self.time_label = QLabel(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.proxy_label)
        self.status_bar.addPermanentWidget(self.publish_label)
        self.status_bar.addPermanentWidget(self.time_label)
        # 定时刷新
        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(3000)

    def _init_async(self):
        self.status_label.setText("正在初始化...")
        self._init_thread = AsyncInitThread(self.db_manager)
        self._init_thread.finished_signal.connect(self._on_init_finished)
        self._init_thread.start()

    def _on_init_finished(self, success: bool, message: str):
        if success:
            self.status_label.setText("就绪")
            logger.info(message)
        else:
            self.status_label.setText("初始化失败")
            QMessageBox.critical(self, "错误", f"系统初始化失败: {message}")

    def _refresh_status(self):
        self.proxy_label.setText(f"代理: {proxy_engine.available_count}/{proxy_engine.pool_size}")
        self.publish_label.setText(f"今日发布: {task_scheduler._daily_count}/{task_scheduler.daily_limit}")
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _backup_database(self):
        try:
            self.db_manager.backup_db()
            QMessageBox.information(self, "成功", "数据库备份完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据库备份失败: {e}")

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "<h3>资质代办全网推广助手 v1.0.0</h3>"
            "<p>专为资质代办行业打造的全网推广自动化工具</p>"
            "<p>功能：账号管理 | 文案生成 | 多平台发布 | SEO监控</p>"
            "<p>技术栈：Python3.11 + PyQt6 + Playwright + SQLite</p>"
        )

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出程序吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            task_scheduler.stop()
            proxy_engine.stop()
            self.db_manager.dispose()
            event.accept()
        else:
            event.ignore()


def run_app():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
