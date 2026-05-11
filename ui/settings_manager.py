"""系统设置界面"""
import os
import yaml
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QCheckBox, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QTabWidget, QFileDialog, QDoubleSpinBox
)
from PyQt6.QtCore import Qt
from db.models import SystemConfig, PlatformConfig
from utils.config_loader import config_loader
from loguru import logger


class SettingsManagerWidget(QWidget):
    """系统设置面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 设置标签页
        self.tab = QTabWidget()

        # 通用设置
        self.tab.addTab(self._create_general_tab(), "通用设置")
        # 代理设置
        self.tab.addTab(self._create_proxy_tab(), "代理IP")
        # AI设置
        self.tab.addTab(self._create_ai_tab(), "AI文案")
        # 发布设置
        self.tab.addTab(self._create_publish_tab(), "发布调度")
        # 反封号设置
        self.tab.addTab(self._create_anti_ban_tab(), "反封号策略")
        # 敏感词设置
        self.tab.addTab(self._create_sensitive_tab(), "敏感词")
        # 平台配置
        self.tab.addTab(self._create_platform_tab(), "平台配置")

        layout.addWidget(self.tab)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 保存设置")
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_reload = QPushButton("🔄 重新加载")
        self.btn_reload.clicked.connect(self._load_config)
        self.btn_export_config = QPushButton("📤 导出配置")
        self.btn_export_config.clicked.connect(self._export_config)
        self.btn_import_config = QPushButton("📥 导入配置")
        self.btn_import_config.clicked.connect(self._import_config)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_reload)
        btn_layout.addWidget(self.btn_export_config)
        btn_layout.addWidget(self.btn_import_config)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _create_general_tab(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.general_headless = QCheckBox("无头模式")
        layout.addRow("浏览器模式:", self.general_headless)
        self.general_timeout = QSpinBox()
        self.general_timeout.setRange(5000, 120000)
        self.general_timeout.setValue(30000)
        self.general_timeout.setSuffix(" ms")
        layout.addRow("超时时间:", self.general_timeout)
        self.general_slow_mo = QSpinBox()
        self.general_slow_mo.setRange(0, 500)
        self.general_slow_mo.setValue(50)
        self.general_slow_mo.setSuffix(" ms")
        layout.addRow("操作延迟:", self.general_slow_mo)
        self.general_viewport_w = QSpinBox()
        self.general_viewport_w.setRange(800, 3840)
        self.general_viewport_w.setValue(1366)
        layout.addRow("窗口宽度:", self.general_viewport_w)
        self.general_viewport_h = QSpinBox()
        self.general_viewport_h.setRange(600, 2160)
        self.general_viewport_h.setValue(768)
        layout.addRow("窗口高度:", self.general_viewport_h)
        self.general_log_level = QComboBox()
        self.general_log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        layout.addRow("日志级别:", self.general_log_level)
        self.general_log_days = QSpinBox()
        self.general_log_days.setRange(7, 90)
        self.general_log_days.setValue(30)
        layout.addRow("日志保留天数:", self.general_log_days)
        return w

    def _create_proxy_tab(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.proxy_enabled = QCheckBox("启用代理IP池")
        layout.addRow("", self.proxy_enabled)
        self.proxy_api_url = QLineEdit()
        self.proxy_api_url.setPlaceholderText("http://api.example.com/get_proxy")
        layout.addRow("API地址:", self.proxy_api_url)
        self.proxy_api_key = QLineEdit()
        self.proxy_api_key.setPlaceholderText("API密钥")
        layout.addRow("API密钥:", self.proxy_api_key)
        self.proxy_check_interval = QSpinBox()
        self.proxy_check_interval.setRange(60, 3600)
        self.proxy_check_interval.setValue(300)
        self.proxy_check_interval.setSuffix(" 秒")
        layout.addRow("检测间隔:", self.proxy_check_interval)
        self.proxy_min_ips = QSpinBox()
        self.proxy_min_ips.setRange(1, 50)
        self.proxy_min_ips.setValue(5)
        layout.addRow("最小可用IP:", self.proxy_min_ips)
        self.proxy_max_fail = QSpinBox()
        self.proxy_max_fail.setRange(1, 10)
        self.proxy_max_fail.setValue(3)
        layout.addRow("最大失败次数:", self.proxy_max_fail)
        self.proxy_http = QCheckBox("HTTP")
        self.proxy_http.setChecked(True)
        self.proxy_https = QCheckBox("HTTPS")
        self.proxy_https.setChecked(True)
        self.proxy_socks5 = QCheckBox("SOCKS5")
        self.proxy_socks5.setChecked(True)
        proto_layout = QHBoxLayout()
        proto_layout.addWidget(self.proxy_http)
        proto_layout.addWidget(self.proxy_https)
        proto_layout.addWidget(self.proxy_socks5)
        proto_layout.addStretch()
        layout.addRow("协议:", proto_layout)
        return w

    def _create_ai_tab(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.ai_provider = QComboBox()
        self.ai_provider.addItems(["openai", "local"])
        layout.addRow("提供商:", self.ai_provider)
        self.ai_api_url = QLineEdit()
        self.ai_api_url.setPlaceholderText("https://api.openai.com/v1")
        layout.addRow("API地址:", self.ai_api_url)
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_api_key.setPlaceholderText("sk-...")
        layout.addRow("API密钥:", self.ai_api_key)
        self.ai_model = QComboBox()
        self.ai_model.setEditable(True)
        self.ai_model.addItems(["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "deepseek-chat"])
        layout.addRow("模型:", self.ai_model)
        self.ai_max_tokens = QSpinBox()
        self.ai_max_tokens.setRange(100, 8000)
        self.ai_max_tokens.setValue(2000)
        layout.addRow("最大Token:", self.ai_max_tokens)
        self.ai_temperature = QDoubleSpinBox()
        self.ai_temperature.setRange(0, 2)
        self.ai_temperature.setSingleStep(0.1)
        self.ai_temperature.setValue(0.8)
        layout.addRow("温度:", self.ai_temperature)
        return w

    def _create_publish_tab(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.pub_daily_limit = QSpinBox()
        self.pub_daily_limit.setRange(1, 200)
        self.pub_daily_limit.setValue(20)
        layout.addRow("每日发布上限:", self.pub_daily_limit)
        self.pub_interval_min = QSpinBox()
        self.pub_interval_min.setRange(10, 600)
        self.pub_interval_min.setValue(60)
        self.pub_interval_min.setSuffix(" 秒")
        layout.addRow("最小间隔:", self.pub_interval_min)
        self.pub_interval_max = QSpinBox()
        self.pub_interval_max.setRange(30, 1800)
        self.pub_interval_max.setValue(300)
        self.pub_interval_max.setSuffix(" 秒")
        layout.addRow("最大间隔:", self.pub_interval_max)
        self.pub_retry_max = QSpinBox()
        self.pub_retry_max.setRange(0, 10)
        self.pub_retry_max.setValue(3)
        layout.addRow("最大重试:", self.pub_retry_max)
        self.pub_retry_delay = QSpinBox()
        self.pub_retry_delay.setRange(30, 3600)
        self.pub_retry_delay.setValue(300)
        self.pub_retry_delay.setSuffix(" 秒")
        layout.addRow("重试延迟:", self.pub_retry_delay)
        return w

    def _create_anti_ban_tab(self):
        w = QWidget()
        layout = QFormLayout(w)
        self.anti_enabled = QCheckBox("启用反封号策略")
        self.anti_enabled.setChecked(True)
        layout.addRow("", self.anti_enabled)
        self.anti_delay_min = QSpinBox()
        self.anti_delay_min.setRange(500, 30000)
        self.anti_delay_min.setValue(3000)
        self.anti_delay_min.setSuffix(" ms")
        layout.addRow("最小延迟:", self.anti_delay_min)
        self.anti_delay_max = QSpinBox()
        self.anti_delay_max.setRange(1000, 60000)
        self.anti_delay_max.setValue(8000)
        self.anti_delay_max.setSuffix(" ms")
        layout.addRow("最大延迟:", self.anti_delay_max)
        self.anti_scroll = QCheckBox("随机滚动")
        self.anti_scroll.setChecked(True)
        layout.addRow("", self.anti_scroll)
        self.anti_mouse = QCheckBox("随机鼠标移动")
        self.anti_mouse.setChecked(True)
        layout.addRow("", self.anti_mouse)
        self.anti_click_offset = QCheckBox("点击位置偏移")
        self.anti_click_offset.setChecked(True)
        layout.addRow("", self.anti_click_offset)
        self.anti_typing = QCheckBox("打字速度变化")
        self.anti_typing.setChecked(True)
        layout.addRow("", self.anti_typing)
        self.anti_daily_limit = QSpinBox()
        self.anti_daily_limit.setRange(10, 500)
        self.anti_daily_limit.setValue(50)
        layout.addRow("每日操作上限:", self.anti_daily_limit)
        return w

    def _create_sensitive_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.sensitive_enabled = QCheckBox("启用敏感词过滤")
        self.sensitive_enabled.setChecked(True)
        layout.addWidget(self.sensitive_enabled)
        layout.addWidget(QLabel("自定义敏感词(每行一个):"))
        self.sensitive_words_edit = QTextEdit()
        self.sensitive_words_edit.setMinimumHeight(200)
        layout.addWidget(self.sensitive_words_edit)
        return w

    def _create_platform_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        add_layout = QHBoxLayout()
        self.platform_name_edit = QLineEdit()
        self.platform_name_edit.setPlaceholderText("平台标识(英文)")
        add_layout.addWidget(QLabel("新平台:"))
        add_layout.addWidget(self.platform_name_edit)
        self.btn_add_platform = QPushButton("➕ 添加平台配置")
        self.btn_add_platform.clicked.connect(self._add_platform_config)
        add_layout.addWidget(self.btn_add_platform)
        layout.addLayout(add_layout)

        self.platform_table = QTableWidget()
        self.platform_table.setColumnCount(5)
        self.platform_table.setHorizontalHeaderLabels([
            "平台名称", "插件名称", "类型", "状态", "操作"
        ])
        self.platform_table.setAlternatingRowColors(True)
        self.platform_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.platform_table)
        return w

    def _load_config(self):
        cfg = config_loader.config

        # 通用
        browser = cfg.get("browser", {})
        self.general_headless.setChecked(browser.get("headless", False))
        self.general_timeout.setValue(browser.get("default_timeout", 30000))
        self.general_slow_mo.setValue(browser.get("slow_mo", 50))
        self.general_viewport_w.setValue(browser.get("viewport_width", 1366))
        self.general_viewport_h.setValue(browser.get("viewport_height", 768))

        system = cfg.get("system", {})
        idx = self.general_log_level.findText(system.get("log_level", "INFO"))
        if idx >= 0:
            self.general_log_level.setCurrentIndex(idx)
        self.general_log_days.setValue(system.get("log_retention_days", 30))

        # 代理
        proxy = cfg.get("proxy", {})
        self.proxy_enabled.setChecked(proxy.get("enabled", False))
        self.proxy_api_url.setText(proxy.get("api_url", ""))
        self.proxy_api_key.setText(proxy.get("api_key", ""))
        self.proxy_check_interval.setValue(proxy.get("check_interval", 300))
        self.proxy_min_ips.setValue(proxy.get("min_available_ips", 5))
        self.proxy_max_fail.setValue(proxy.get("max_fail_count", 3))

        # AI
        ai = cfg.get("ai_content", {})
        idx = self.ai_provider.findText(ai.get("provider", "openai"))
        if idx >= 0:
            self.ai_provider.setCurrentIndex(idx)
        self.ai_api_url.setText(ai.get("api_url", ""))
        self.ai_api_key.setText(ai.get("api_key", ""))
        idx = self.ai_model.findText(ai.get("model", "gpt-4"))
        if idx >= 0:
            self.ai_model.setCurrentIndex(idx)
        self.ai_max_tokens.setValue(ai.get("max_tokens", 2000))
        self.ai_temperature.setValue(ai.get("temperature", 0.8))

        # 发布调度
        sched = cfg.get("scheduler", {})
        self.pub_daily_limit.setValue(sched.get("daily_publish_limit", 20))
        self.pub_interval_min.setValue(sched.get("publish_interval_min", 60))
        self.pub_interval_max.setValue(sched.get("publish_interval_max", 300))
        self.pub_retry_max.setValue(sched.get("retry_max", 3))
        self.pub_retry_delay.setValue(sched.get("retry_delay", 300))

        # 反封号
        anti = cfg.get("anti_ban", {})
        self.anti_enabled.setChecked(True)
        self.anti_delay_min.setValue(anti.get("random_delay_min", 3000))
        self.anti_delay_max.setValue(anti.get("random_delay_max", 8000))
        self.anti_scroll.setChecked(anti.get("scroll_random", True))
        self.anti_mouse.setChecked(anti.get("mouse_move_random", True))
        self.anti_click_offset.setChecked(anti.get("click_offset", True))
        self.anti_typing.setChecked(anti.get("typing_speed_vary", True))

        # 敏感词
        sensitive = cfg.get("sensitive_words", {})
        self.sensitive_enabled.setChecked(sensitive.get("enabled", True))
        custom = sensitive.get("custom_words", [])
        self.sensitive_words_edit.setText("\n".join(custom))

        # 平台配置
        self._refresh_platform_table()

    def _refresh_platform_table(self):
        session = self.db_manager.get_session()
        try:
            configs = session.query(PlatformConfig).all()
            self.platform_table.setRowCount(len(configs))
            for row, cfg in enumerate(configs):
                self.platform_table.setItem(row, 0, QTableWidgetItem(cfg.platform_name))
                self.platform_table.setItem(row, 1, QTableWidgetItem(cfg.plugin_name))
                self.platform_table.setItem(row, 2, QTableWidgetItem(cfg.platform_type))
                status_item = QTableWidgetItem("✅ 启用" if cfg.enabled else "❌ 禁用")
                self.platform_table.setItem(row, 3, status_item)
                toggle_btn = QPushButton("禁用" if cfg.enabled else "启用")
                toggle_btn.clicked.connect(lambda checked, cid=cfg.id: self._toggle_platform(cid))
                self.platform_table.setCellWidget(row, 4, toggle_btn)
        except Exception as e:
            logger.error(f"刷新平台配置异常: {e}")
        finally:
            session.close()

    def _toggle_platform(self, config_id: int):
        session = self.db_manager.get_session()
        try:
            cfg = session.query(PlatformConfig).filter_by(id=config_id).first()
            if cfg:
                cfg.enabled = not cfg.enabled
                session.commit()
                self._refresh_platform_table()
        finally:
            session.close()

    def _add_platform_config(self):
        name = self.platform_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入平台名称")
            return
        session = self.db_manager.get_session()
        try:
            exists = session.query(PlatformConfig).filter_by(platform_name=name).first()
            if exists:
                QMessageBox.warning(self, "提示", "该平台已存在")
                return
            cfg = PlatformConfig(
                platform_name=name,
                plugin_name=name,
                platform_type="custom",
                form_config={},
                selectors={},
            )
            session.add(cfg)
            session.commit()
            self._refresh_platform_table()
            self.platform_name_edit.clear()
        finally:
            session.close()

    def _save_settings(self):
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

            new_config = {
                "system": {
                    "app_name": "资质代办全网推广助手",
                    "version": "1.0.0",
                    "debug": False,
                    "data_dir": "./data",
                    "log_level": self.general_log_level.currentText(),
                    "log_retention_days": self.general_log_days.value(),
                },
                "database": {"path": "./data/qualification_bot.db"},
                "proxy": {
                    "enabled": self.proxy_enabled.isChecked(),
                    "api_url": self.proxy_api_url.text(),
                    "api_key": self.proxy_api_key.text(),
                    "check_interval": self.proxy_check_interval.value(),
                    "min_available_ips": self.proxy_min_ips.value(),
                    "max_fail_count": self.proxy_max_fail.value(),
                    "protocols": ["http", "https", "socks5"],
                },
                "browser": {
                    "headless": self.general_headless.isChecked(),
                    "default_timeout": self.general_timeout.value(),
                    "slow_mo": self.general_slow_mo.value(),
                    "viewport_width": self.general_viewport_w.value(),
                    "viewport_height": self.general_viewport_h.value(),
                    "locale": "zh-CN",
                    "timezone_id": "Asia/Shanghai",
                },
                "ai_content": {
                    "provider": self.ai_provider.currentText(),
                    "api_url": self.ai_api_url.text(),
                    "api_key": self.ai_api_key.text(),
                    "model": self.ai_model.currentText(),
                    "max_tokens": self.ai_max_tokens.value(),
                    "temperature": self.ai_temperature.value(),
                },
                "scheduler": {
                    "publish_interval_min": self.pub_interval_min.value(),
                    "publish_interval_max": self.pub_interval_max.value(),
                    "daily_publish_limit": self.pub_daily_limit.value(),
                    "retry_max": self.pub_retry_max.value(),
                    "retry_delay": self.pub_retry_delay.value(),
                },
                "anti_ban": {
                    "random_delay_min": self.anti_delay_min.value(),
                    "random_delay_max": self.anti_delay_max.value(),
                    "scroll_random": self.anti_scroll.isChecked(),
                    "mouse_move_random": self.anti_mouse.isChecked(),
                    "click_offset": self.anti_click_offset.isChecked(),
                    "typing_speed_vary": self.anti_typing.isChecked(),
                },
                "sensitive_words": {
                    "enabled": self.sensitive_enabled.isChecked(),
                    "custom_words": [w.strip() for w in self.sensitive_words_edit.toPlainText().split("\n") if w.strip()],
                },
            }

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            config_loader.load(config_path)
            # 更新核心引擎配置
            from core.ai_engine import ai_engine
            ai_engine.api_key = self.ai_api_key.text()
            ai_engine.api_url = self.ai_api_url.text()
            ai_engine.model = self.ai_model.currentText()

            QMessageBox.information(self, "成功", "设置已保存，部分配置需重启生效")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _export_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "config_backup.yaml", "YAML (*.yaml *.yml)"
        )
        if path:
            try:
                import shutil
                src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
                shutil.copy2(src, path)
                QMessageBox.information(self, "导出完成", f"配置已导出到: {path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "YAML (*.yaml *.yml)"
        )
        if path:
            config_loader.load(path)
            self._load_config()
            QMessageBox.information(self, "导入完成", "配置已加载")
