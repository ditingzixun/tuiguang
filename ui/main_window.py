"""主窗口 -- PyQt6 桌面界面，左侧菜单栏 + 中央功能区 + 底部日志栏"""
import os
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QListWidget, QListWidgetItem, QTextEdit, QPushButton, QLabel,
    QFrame, QSplitter, QCheckBox, QMessageBox, QApplication, QMenuBar, QMenu,
    QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QMargins
from PyQt6.QtGui import QAction, QFont, QIcon

from ui.account_manager import AccountManagerWidget
from ui.task_manager import TaskManagerWidget
from ui.content_generator import ContentGeneratorWidget
from ui.publish_manager import PublishManagerWidget
from ui.settings_manager import SettingsManagerWidget
from ui.seo_monitor import SeoMonitorWidget
from ui.proxy_manager import ProxyManagerWidget
from ui.styles.theme_manager import theme_manager
from db.database import DatabaseManager
from scheduler.task_scheduler import task_scheduler
from core.proxy_engine import proxy_engine
from core.event_loop import event_loop as ev_loop
from core.browser_engine import browser_engine
from core.seo_engine import seo_engine
from utils.log_handler import QtLogSignal, QtLogHandler

logger = logging.getLogger(__name__)

# 导航菜单项配置 (标签文本, 图标, 对应StackedWidget索引)
NAV_ITEMS = [
    ("账号管理", "\U0001F464", 0),   # 👤
    ("文案生成", "✏️", 1),  # ✏️
    ("任务发布", "\U0001F4E4", 2),   # 📤
    ("收录监控", "\U0001F4CA", 3),   # 📊
    ("代理IP池", "\U0001F310", 4),   # 🌐
    ("系统设置", "⚙️", 5),  # ⚙️
]

MAX_LOG_LINES = 500
LOG_COLORS = {
    "ERROR": "#f38ba8",
    "WARNING": "#fab387",
    "INFO": "#cdd6f4",
    "DEBUG": "#a6adc8",
}


class InitThread(QThread):
    finished_signal = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

    def run(self):
        try:
            self.log_signal.emit("正在初始化数据库...")
            self.db_manager.init_db()
            self.log_signal.emit("正在启动任务调度器...")
            task_scheduler.set_db_manager(self.db_manager)
            task_scheduler.start()
            self.log_signal.emit("正在启动代理引擎...")
            proxy_engine.set_db_manager(self.db_manager)
            proxy_engine.start()
            self.log_signal.emit("正在启动SEO监控引擎...")
            seo_engine.set_db_manager(self.db_manager)
            seo_engine.start()
            self.log_signal.emit("系统初始化完成")
            self.finished_signal.emit(True, "系统初始化完成")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("资质代办全网推广助手 v1.1")
        self.setMinimumSize(1100, 700)
        self.resize(1360, 850)
        self.db_manager = DatabaseManager()
        self._init_ui()
        self._init_menu_bar()
        self._init_log_handler()
        self._init_async()

    # ====== 主布局 ======

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ------ 中上区域: 侧边栏 + 内容区 ------
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # 左侧菜单栏
        self.sidebar = self._create_sidebar()
        body.addWidget(self.sidebar)

        # 中央内容区
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {theme_manager.get_color('content_bg')};")

        self.account_tab = AccountManagerWidget(self.db_manager)
        self.stack.addWidget(self.account_tab)

        self.content_tab = ContentGeneratorWidget(self.db_manager)
        self.stack.addWidget(self.content_tab)

        # 任务发布页: 内部 Tab 切换
        task_publish_tabs = QTabWidget()
        self.task_tab = TaskManagerWidget(self.db_manager)
        self.publish_tab = PublishManagerWidget(self.db_manager)
        task_publish_tabs.addTab(self.task_tab, "任务管理")
        task_publish_tabs.addTab(self.publish_tab, "发布记录")
        self.stack.addWidget(task_publish_tabs)

        self.seo_tab = SeoMonitorWidget(self.db_manager)
        self.stack.addWidget(self.seo_tab)

        self.proxy_tab = ProxyManagerWidget(self.db_manager)
        self.stack.addWidget(self.proxy_tab)

        self.settings_tab = SettingsManagerWidget(self.db_manager)
        self.stack.addWidget(self.settings_tab)

        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        # ------ 底部日志栏 ------
        self.log_panel = self._create_log_panel()
        root.addWidget(self.log_panel)

        self.nav_list.setCurrentRow(0)
        self.stack.setCurrentIndex(0)

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / 标题
        logo_label = QLabel("  资质代办推广助手")
        logo_label.setObjectName("logo")
        logo_label.setFixedHeight(52)
        layout.addWidget(logo_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("sidebarSeparator")
        sep.setStyleSheet(f"color: {theme_manager.get_color('separator_color')};")
        layout.addWidget(sep)

        # 导航菜单
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navMenu")
        for label, icon, idx in NAV_ITEMS:
            item = QListWidgetItem(f"  {icon}  {label}")
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setSizeHint(item.sizeHint().grownBy(QMargins(0, 0, 0, 6)))
            self.nav_list.addItem(item)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        layout.addWidget(self.nav_list, 1)

        # 底部状态灯 + 版本
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        self.status_light = QLabel("●")  # ●
        self.status_light.setObjectName("sidebarStatusLight")
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("sidebarStatusText")
        bottom_layout.addWidget(self.status_light)
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        version_label = QLabel("v1.1")
        version_label.setObjectName("sidebarVersion")
        bottom_layout.addWidget(version_label)
        layout.addWidget(bottom)

        return sidebar

    def _update_status_light(self, active: bool):
        """更新状态灯颜色，使用主题中的颜色"""
        color = theme_manager.get_color(
            "status_light_active" if active else "status_light_error"
        )
        self.status_light.setStyleSheet(f"color: {color}; font-size: 10px;")

    def _create_log_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("logPanel")
        panel.setFixedHeight(150)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 6)
        layout.setSpacing(4)

        # 标题栏
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("运行日志")
        title.setObjectName("logHeaderTitle")
        header.addWidget(title)
        header.addStretch()
        self.log_pause_cb = QCheckBox("暂停滚动")
        self.log_pause_cb.setObjectName("logPauseCb")
        header.addWidget(self.log_pause_cb)
        btn_clear = QPushButton("清空")
        btn_clear.setObjectName("logClearBtn")
        btn_clear.setFixedSize(48, 22)
        btn_clear.clicked.connect(self._clear_log)
        header.addWidget(btn_clear)
        layout.addLayout(header)

        # 日志输出
        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        layout.addWidget(self.log_output)

        return panel

    def _on_nav_changed(self, idx: int):
        if 0 <= idx < self.stack.count():
            self.stack.setCurrentIndex(idx)

    # ====== 日志处理 ======

    def _init_log_handler(self):
        self._log_signal = QtLogSignal()
        self._log_signal.log_message.connect(self._append_log)
        handler = QtLogHandler(self._log_signal)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        ))
        logging.getLogger().addHandler(handler)
        logger.info("Qt日志处理器已就绪")

    def _append_log(self, msg: str):
        if self.log_pause_cb.isChecked():
            return
        parts = msg.split("|", 2)
        if len(parts) >= 3:
            level = parts[1].strip()
            color = LOG_COLORS.get(level, "#cdd6f4")
        else:
            color = theme_manager.get_color("log_output_text", "#cdd6f4")
        self.log_output.append(f"<span style='color:{color}'>{msg}</span>")

        doc = self.log_output.document()
        if doc.blockCount() > MAX_LOG_LINES:
            cursor = self.log_output.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 50)
            cursor.removeSelectedText()

    def _clear_log(self):
        self.log_output.clear()

    # ====== 菜单栏 ======

    def _init_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction(QAction("备份数据库", self, triggered=self._backup_database))
        file_menu.addSeparator()
        file_menu.addAction(QAction("退出(&X)", self, triggered=self.close))

        engine_menu = menubar.addMenu("引擎(&E)")
        engine_menu.addAction(QAction("启动任务调度", self,
                                     triggered=lambda: task_scheduler.start()))
        engine_menu.addAction(QAction("停止任务调度", self,
                                     triggered=lambda: task_scheduler.stop()))

        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction(QAction("关于", self, triggered=self._show_about))

    # ====== 异步初始化 ======

    def _init_async(self):
        self.status_label.setText("正在初始化...")
        self._init_thread = InitThread(self.db_manager)
        self._init_thread.log_signal.connect(lambda msg: logger.info(msg))
        self._init_thread.finished_signal.connect(self._on_init_finished)
        self._init_thread.start()

    def _on_init_finished(self, success: bool, message: str):
        if success:
            ev_loop.start()
            ev_loop.run(browser_engine.init())
            task_scheduler.set_publish_callback(self._publish_callback)
            self._update_status_light(True)
            self.status_label.setText("运行中")
            logger.info(message)
        else:
            self._update_status_light(False)
            self.status_label.setText("初始化失败")
            QMessageBox.critical(self, "错误", f"系统初始化失败: {message}")

    # ====== 发布回调 (保持与旧版一致) ======

    def _publish_callback(self, task: dict):
        from plugins.base_plugin import plugin_manager

        db = self.db_manager

        async def do_publish():
            import json as _json

            account = db.fetch_one("SELECT * FROM accounts WHERE id = ?", (task.get('account_id'),))
            if not account:
                self._record_task_failed(task, "账号不存在")
                return None

            content = None
            if task.get('content_id'):
                content = db.fetch_one("SELECT * FROM contents WHERE id = ?", (task.get('content_id'),))

            plugin_cls = plugin_manager.get_plugin(task['platform'])
            if not plugin_cls:
                self._record_task_failed(task, f"未找到平台插件: {task['platform']}")
                return None

            now = format_datetime()
            db.update("tasks", {"status": "running", "started_at": now}, "id = ?", (task['id'],))

            try:
                platform_cfg = db.fetch_one(
                    "SELECT form_config, selectors FROM platform_configs WHERE plugin_name = ? AND enabled = 1",
                    (task['platform'],)
                )
                selectors_override = {}
                form_config = {}
                if platform_cfg:
                    try:
                        form_config = _json.loads(platform_cfg['form_config'] or '{}')
                    except _json.JSONDecodeError:
                        pass
                    try:
                        selectors_override = _json.loads(platform_cfg['selectors'] or '{}')
                    except _json.JSONDecodeError:
                        pass

                context = await browser_engine.get_context(account['id'], task['platform'])
                plugin = plugin_cls(dict(account), context, selectors=selectors_override)
                await plugin.init()

                if not await plugin.login():
                    self._record_task_failed(task, "登录失败")
                    return None

                title = task.get('title') or (content['title'] if content else '')
                body = task.get('content') or (content['content'] if content else '')

                publish_kwargs = {}
                enterprise = db.get_enterprise_profile()
                if enterprise:
                    publish_kwargs['company_name'] = enterprise['company_name'] or ''
                    publish_kwargs['company_short_name'] = enterprise['short_name'] or ''
                    publish_kwargs['contact_person'] = enterprise['contact_person'] or ''
                    publish_kwargs['address'] = enterprise['address'] or ''
                    publish_kwargs['website'] = enterprise['website'] or ''
                    publish_kwargs['contact_phone'] = enterprise['phone'] or '' or account['phone']
                else:
                    publish_kwargs['contact_phone'] = account['phone'] or ''
                publish_kwargs['contact_email'] = account['email'] or ''
                if content:
                    publish_kwargs['category'] = content['qualification_type'] or ''
                    publish_kwargs['content_type'] = content['content_type'] or ''
                image_paths_raw = task.get('image_paths', '[]')
                if isinstance(image_paths_raw, str):
                    try:
                        publish_kwargs['images'] = _json.loads(image_paths_raw)
                    except (_json.JSONDecodeError, TypeError):
                        publish_kwargs['images'] = []
                else:
                    publish_kwargs['images'] = image_paths_raw or []
                publish_kwargs['form_config'] = form_config
                publish_kwargs['selectors_override'] = selectors_override

                result_url = await plugin.publish(title, body, **publish_kwargs)

                now2 = format_datetime()
                screenshot_path = ''
                if result_url:
                    try:
                        screenshot_path = await browser_engine.take_screenshot(
                            plugin._page, account['id'], task['id']
                        )
                    except Exception:
                        pass
                    self._record_task_success(task, result_url, dict(account), title, now2, screenshot_path)
                else:
                    self._record_task_failed(task, "发布失败：未获取到发布链接")
                    db.insert("publish_records", {
                        "task_id": task['id'], "account_id": account['id'],
                        "platform": task['platform'], "title": title,
                        "status": "failed", "publish_time": now2, "created_at": now2,
                    })

                await plugin.close()
                await browser_engine.save_account_cookies(account['id'])
                return result_url

            except Exception as e:
                logger.error(f"发布异常: {e}")
                self._record_task_failed(task, str(e))
                return None

        try:
            return ev_loop.run(do_publish())
        except Exception as e:
            logger.error(f"事件循环执行异常: {e}")
            return None

    def _record_task_success(self, task, result_url, account, title, now, screenshot_path=''):
        db = self.db_manager
        db.update("tasks", {
            "status": "success", "completed_at": now, "result_url": result_url,
        }, "id = ?", (task['id'],))
        db.insert("publish_records", {
            "task_id": task['id'], "account_id": account['id'],
            "platform": task['platform'], "title": title, "url": result_url,
            "status": "published", "publish_time": now, "created_at": now,
            "screenshot_path": screenshot_path,
        })
        if task.get('content_id'):
            db.execute("UPDATE contents SET used_count = used_count + 1 WHERE id = ?", (task['content_id'],))

    def _record_task_failed(self, task, error_msg):
        now = format_datetime()
        self.db_manager.update("tasks", {
            "status": "failed", "completed_at": now, "error_message": error_msg[:500],
        }, "id = ?", (task['id'],))

    # ====== 其他 ======

    def _backup_database(self):
        try:
            self.db_manager.backup_db()
            QMessageBox.information(self, "成功", "数据库备份完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据库备份失败: {e}")

    def _show_about(self):
        QMessageBox.about(self, "关于",
            "<h3>资质代办全网推广助手 v1.1</h3>"
            "<p>专为资质代办行业打造的全网推广自动化工具</p>"
            "<p>功能：账号管理 | 文案生成 | 平台发布 | SEO监控 | 代理IP池</p>"
            "<p>技术栈：Python + PyQt6 + Playwright + SQLite</p>"
            "<p>左侧导航6大功能模块 | 底部实时日志 | 可视化配置</p>"
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
            seo_engine.stop()
            try:
                ev_loop.run(browser_engine.close())
            except Exception:
                pass
            ev_loop.stop()
            self.db_manager.close()
            event.accept()
        else:
            event.ignore()
