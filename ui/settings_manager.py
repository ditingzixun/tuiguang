"""系统设置界面 — .env配置 + 平台配置管理"""
import os
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QCheckBox, QMessageBox, QLabel, QTabWidget, QFileDialog, QTextEdit,
    QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from dotenv import set_key

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader


class SettingsManagerWidget(QWidget):
    """系统设置面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tab = QTabWidget()
        self.tab.addTab(self._create_general_tab(), "通用设置")
        self.tab.addTab(self._create_publish_tab(), "发布调度")
        self.tab.addTab(self._create_proxy_tab(), "代理IP")
        self.tab.addTab(self._create_ai_tab(), "AI大模型")
        self.tab.addTab(self._create_enterprise_tab(), "企业资料")
        self.tab.addTab(self._create_seo_tab(), "SEO监控")
        self.tab.addTab(self._create_platform_tab(), "平台配置")
        layout.addWidget(self.tab)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("保存设置")
        self.btn_save.setMinimumHeight(34)
        self.btn_save.setMinimumWidth(100)
        self.btn_save.setToolTip("将所有设置写入配置文件(.env)")
        self.btn_save.clicked.connect(self._save_settings)
        self.btn_reload = QPushButton("重新加载")
        self.btn_reload.setMinimumHeight(34)
        self.btn_reload.clicked.connect(self._load_config)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_reload)
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
        self.general_theme = QComboBox()
        self.general_theme.addItems(["深色主题", "浅色主题"])
        layout.addRow("界面主题:", self.general_theme)
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

    def _create_proxy_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.proxy_enabled = QCheckBox("启用代理IP池")
        layout.addRow("代理开关:", self.proxy_enabled)

        self.proxy_api_url = QLineEdit()
        self.proxy_api_url.setPlaceholderText("https://api.example.com/get_ips")
        layout.addRow("API地址:", self.proxy_api_url)

        self.proxy_api_key = QLineEdit()
        self.proxy_api_key.setPlaceholderText("API密钥")
        self.proxy_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API密钥:", self.proxy_api_key)

        self.proxy_extract_count = QSpinBox()
        self.proxy_extract_count.setRange(1, 100)
        self.proxy_extract_count.setValue(10)
        layout.addRow("提取数量:", self.proxy_extract_count)

        self.proxy_check_interval = QSpinBox()
        self.proxy_check_interval.setRange(60, 3600)
        self.proxy_check_interval.setValue(300)
        self.proxy_check_interval.setSuffix(" 秒")
        layout.addRow("检测间隔:", self.proxy_check_interval)

        self.proxy_test_url = QLineEdit()
        self.proxy_test_url.setPlaceholderText("https://www.baidu.com")
        layout.addRow("检测地址:", self.proxy_test_url)

        self.proxy_test_timeout = QSpinBox()
        self.proxy_test_timeout.setRange(3, 30)
        self.proxy_test_timeout.setValue(10)
        self.proxy_test_timeout.setSuffix(" 秒")
        layout.addRow("检测超时:", self.proxy_test_timeout)

        self.proxy_max_failures = QSpinBox()
        self.proxy_max_failures.setRange(1, 20)
        self.proxy_max_failures.setValue(3)
        layout.addRow("最大失败次数:", self.proxy_max_failures)

        self.proxy_rotation_mode = QComboBox()
        self.proxy_rotation_mode.addItems(["round_robin", "weighted"])
        layout.addRow("轮换模式:", self.proxy_rotation_mode)

        return w

    def _create_ai_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.ai_enabled = QCheckBox("启用AI大模型生成")
        self.ai_enabled.setToolTip("启用后将优先调用AI生成，失败自动降级到模板")
        layout.addRow("AI开关:", self.ai_enabled)

        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["auto", "claude", "openai"])
        layout.addRow("提供商:", self.ai_provider_combo)

        self.ai_api_key = QLineEdit()
        self.ai_api_key.setPlaceholderText("sk-...")
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("OpenAI API Key:", self.ai_api_key)

        self.ai_api_base = QLineEdit()
        self.ai_api_base.setPlaceholderText("https://api.openai.com/v1")
        layout.addRow("API Base URL:", self.ai_api_base)

        self.ai_model = QComboBox()
        self.ai_model.setEditable(True)
        self.ai_model.addItems(["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "deepseek-chat", "qwen-turbo"])
        layout.addRow("模型:", self.ai_model)

        self.claude_api_key = QLineEdit()
        self.claude_api_key.setPlaceholderText("sk-ant-...")
        self.claude_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Claude API Key:", self.claude_api_key)

        self.claude_model = QComboBox()
        self.claude_model.setEditable(True)
        self.claude_model.addItems(["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"])
        layout.addRow("Claude 模型:", self.claude_model)

        self.ai_max_tokens = QSpinBox()
        self.ai_max_tokens.setRange(256, 8192)
        self.ai_max_tokens.setValue(2048)
        self.ai_max_tokens.setSingleStep(256)
        layout.addRow("最大Token:", self.ai_max_tokens)

        self.ai_temperature = QComboBox()
        self.ai_temperature.addItems(["0.5 (保守)", "0.8 (推荐)", "1.0 (创意)", "1.2 (随机)"])
        layout.addRow("创意度:", self.ai_temperature)

        self.ai_fallback = QCheckBox("API失败时自动降级到模板生成")
        self.ai_fallback.setChecked(True)
        layout.addRow("模板降级:", self.ai_fallback)
        return w

    def _create_enterprise_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.ent_company_name = QLineEdit()
        self.ent_company_name.setPlaceholderText("公司全称")
        layout.addRow("公司名称:", self.ent_company_name)

        self.ent_short_name = QLineEdit()
        self.ent_short_name.setPlaceholderText("简称")
        layout.addRow("公司简称:", self.ent_short_name)

        self.ent_phone = QLineEdit()
        self.ent_phone.setPlaceholderText("客服/销售电话")
        layout.addRow("联系电话:", self.ent_phone)

        self.ent_contact_person = QLineEdit()
        self.ent_contact_person.setPlaceholderText("联系人姓名")
        layout.addRow("联系人:", self.ent_contact_person)

        self.ent_address = QLineEdit()
        self.ent_address.setPlaceholderText("公司地址")
        layout.addRow("地址:", self.ent_address)

        self.ent_website = QLineEdit()
        self.ent_website.setPlaceholderText("https://www.example.com")
        layout.addRow("网站:", self.ent_website)

        self.ent_description = QTextEdit()
        self.ent_description.setPlaceholderText("公司简介...")
        self.ent_description.setMaximumHeight(100)
        layout.addRow("简介:", self.ent_description)

        logo_layout = QHBoxLayout()
        self.ent_logo_path = QLineEdit()
        self.ent_logo_path.setPlaceholderText("logo图片路径(可选)")
        btn_browse_logo = QPushButton("浏览...")
        btn_browse_logo.clicked.connect(lambda: self._browse_logo())
        logo_layout.addWidget(self.ent_logo_path)
        logo_layout.addWidget(btn_browse_logo)
        layout.addRow("Logo:", logo_layout)
        return w

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择Logo图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)"
        )
        if path:
            self.ent_logo_path.setText(path)

    def _load_enterprise_profile(self):
        try:
            profile = self.db_manager.get_enterprise_profile()
            if profile:
                self.ent_company_name.setText(profile["company_name"] or "")
                self.ent_short_name.setText(profile["short_name"] or "")
                self.ent_phone.setText(profile["phone"] or "")
                self.ent_contact_person.setText(profile["contact_person"] or "")
                self.ent_address.setText(profile["address"] or "")
                self.ent_website.setText(profile["website"] or "")
                self.ent_description.setText(profile["description"] or "")
                self.ent_logo_path.setText(profile["logo_path"] or "")
        except Exception as e:
            logger.error(f"加载企业资料失败: {e}")

    def _save_enterprise_profile(self):
        try:
            data = {
                "company_name": self.ent_company_name.text().strip(),
                "short_name": self.ent_short_name.text().strip(),
                "phone": self.ent_phone.text().strip(),
                "contact_person": self.ent_contact_person.text().strip(),
                "address": self.ent_address.text().strip(),
                "website": self.ent_website.text().strip(),
                "description": self.ent_description.toPlainText().strip(),
                "logo_path": self.ent_logo_path.text().strip(),
            }
            if data["company_name"]:
                self.db_manager.save_enterprise_profile(data)
        except Exception as e:
            logger.error(f"保存企业资料失败: {e}")

    def _create_seo_tab(self):
        w = QWidget()
        layout = QFormLayout(w)

        self.seo_enabled = QCheckBox("启用SEO自动监控")
        layout.addRow("SEO开关:", self.seo_enabled)

        self.seo_check_interval = QSpinBox()
        self.seo_check_interval.setRange(1, 168)
        self.seo_check_interval.setValue(6)
        self.seo_check_interval.setSuffix(" 小时")
        layout.addRow("检测间隔:", self.seo_check_interval)

        self.seo_engines = QLineEdit()
        self.seo_engines.setPlaceholderText("baidu, 360, sogou")
        layout.addRow("搜索引擎:", self.seo_engines)

        self.seo_max_pages = QSpinBox()
        self.seo_max_pages.setRange(1, 20)
        self.seo_max_pages.setValue(3)
        layout.addRow("最大结果页:", self.seo_max_pages)

        self.seo_auto_republish = QCheckBox("未收录时自动重发")
        layout.addRow("自动重发:", self.seo_auto_republish)

        self.seo_request_delay = QSpinBox()
        self.seo_request_delay.setRange(1, 30)
        self.seo_request_delay.setValue(5)
        self.seo_request_delay.setSuffix(" 秒")
        layout.addRow("请求延迟:", self.seo_request_delay)
        return w

    def _create_platform_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        add_layout = QHBoxLayout()
        self.platform_name_edit = QLineEdit()
        self.platform_name_edit.setPlaceholderText("平台标识(英文)")
        add_layout.addWidget(QLabel("新平台:"))
        add_layout.addWidget(self.platform_name_edit)
        self.btn_add_platform = QPushButton("添加平台配置")
        self.btn_add_platform.clicked.connect(self._add_platform_config)
        add_layout.addWidget(self.btn_add_platform)
        layout.addLayout(add_layout)

        self.platform_table = QTableWidget()
        self.platform_table.setColumnCount(6)
        self.platform_table.setHorizontalHeaderLabels([
            "平台名称", "插件名称", "类型", "状态", "启用", "表单映射"
        ])
        self.platform_table.setAlternatingRowColors(True)
        self.platform_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.platform_table)
        return w

    def _load_config(self, _=None):
        cfg = config_loader
        self.general_headless.setChecked(cfg.get_bool("BROWSER_HEADLESS", False))
        self.general_timeout.setValue(cfg.get_int("BROWSER_TIMEOUT", 30000))
        self.general_slow_mo.setValue(cfg.get_int("BROWSER_SLOW_MO", 50))
        self.general_viewport_w.setValue(cfg.get_int("VIEWPORT_WIDTH", 1366))
        self.general_viewport_h.setValue(cfg.get_int("VIEWPORT_HEIGHT", 768))
        idx = self.general_log_level.findText(cfg.get("LOG_LEVEL", "INFO"))
        if idx >= 0:
            self.general_log_level.setCurrentIndex(idx)
        theme_idx = 0 if cfg.get("THEME", "dark") == "dark" else 1
        self.general_theme.setCurrentIndex(theme_idx)

        self.pub_daily_limit.setValue(cfg.get_int("DAILY_PUBLISH_LIMIT", 20))
        self.pub_interval_min.setValue(cfg.get_int("PUBLISH_INTERVAL_MIN", 60))
        self.pub_interval_max.setValue(cfg.get_int("PUBLISH_INTERVAL_MAX", 300))
        self.pub_retry_max.setValue(cfg.get_int("RETRY_MAX", 3))
        self.pub_retry_delay.setValue(cfg.get_int("RETRY_DELAY", 300))

        self.proxy_enabled.setChecked(cfg.get_bool("PROXY_ENABLED", False))
        self.proxy_api_url.setText(cfg.get("PROXY_API_URL", ""))
        self.proxy_api_key.setText(cfg.get("PROXY_API_KEY", ""))
        self.proxy_extract_count.setValue(cfg.get_int("PROXY_EXTRACT_COUNT", 10))
        self.proxy_check_interval.setValue(cfg.get_int("PROXY_CHECK_INTERVAL", 300))
        self.proxy_test_url.setText(cfg.get("PROXY_TEST_URL", "https://www.baidu.com"))
        self.proxy_test_timeout.setValue(cfg.get_int("PROXY_TEST_TIMEOUT", 10))
        self.proxy_max_failures.setValue(cfg.get_int("PROXY_MAX_FAILURES", 3))
        idx_mode = self.proxy_rotation_mode.findText(cfg.get("PROXY_ROTATION_MODE", "round_robin"))
        if idx_mode >= 0:
            self.proxy_rotation_mode.setCurrentIndex(idx_mode)

        # AI settings
        self.ai_enabled.setChecked(cfg.get_bool("AI_ENABLED", False))
        ai_provider = cfg.get("AI_PROVIDER", "auto").strip().lower()
        provider_map = {"auto": 0, "claude": 1, "openai": 2}
        self.ai_provider_combo.setCurrentIndex(provider_map.get(ai_provider, 0))
        self.ai_api_key.setText(cfg.get("AI_API_KEY", ""))
        self.ai_api_base.setText(cfg.get("AI_API_BASE", "https://api.openai.com/v1"))
        idx_model = self.ai_model.findText(cfg.get("AI_MODEL", "gpt-4o-mini"))
        if idx_model >= 0:
            self.ai_model.setCurrentIndex(idx_model)
        else:
            self.ai_model.setCurrentText(cfg.get("AI_MODEL", "gpt-4o-mini"))
        self.claude_api_key.setText(cfg.get("CLAUDE_API_KEY", ""))
        idx_cm = self.claude_model.findText(cfg.get("CLAUDE_MODEL", "claude-sonnet-4-6"))
        if idx_cm >= 0:
            self.claude_model.setCurrentIndex(idx_cm)
        else:
            self.claude_model.setCurrentText(cfg.get("CLAUDE_MODEL", "claude-sonnet-4-6"))
        self.ai_max_tokens.setValue(cfg.get_int("AI_MAX_TOKENS", 2048))
        temp_val = cfg.get("AI_TEMPERATURE", "0.8")
        temp_map = {"0.5": 0, "0.8": 1, "1.0": 2, "1.2": 3}
        self.ai_temperature.setCurrentIndex(temp_map.get(temp_val, 1))
        self.ai_fallback.setChecked(cfg.get_bool("AI_FALLBACK_TEMPLATE", True))

        # SEO settings
        self.seo_enabled.setChecked(cfg.get_bool("SEO_ENABLED", False))
        self.seo_check_interval.setValue(cfg.get_int("SEO_CHECK_INTERVAL_HOURS", 6))
        self.seo_engines.setText(cfg.get("SEO_SEARCH_ENGINES", "baidu, 360, sogou"))
        self.seo_max_pages.setValue(cfg.get_int("SEO_MAX_RESULT_PAGES", 3))
        self.seo_auto_republish.setChecked(cfg.get_bool("SEO_AUTO_REPUBLISH", False))
        self.seo_request_delay.setValue(cfg.get_int("SEO_REQUEST_DELAY", 5))

        self._load_enterprise_profile()
        self._refresh_platform_table()

    def _refresh_platform_table(self):
        try:
            rows = self.db_manager.fetch_all("SELECT * FROM platform_configs ORDER BY id")
            self.platform_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                self.platform_table.setItem(r, 0, QTableWidgetItem(row["platform_name"]))
                self.platform_table.setItem(r, 1, QTableWidgetItem(row["plugin_name"]))
                self.platform_table.setItem(r, 2, QTableWidgetItem(row["platform_type"]))
                enabled = row["enabled"]
                self.platform_table.setItem(r, 3, QTableWidgetItem("启用" if enabled else "禁用"))
                toggle_btn = QPushButton("禁用" if enabled else "启用")
                toggle_btn.clicked.connect(lambda checked, cid=row["id"]: self._toggle_platform(cid))
                self.platform_table.setCellWidget(r, 4, toggle_btn)
                edit_btn = QPushButton("编辑映射")
                edit_btn.clicked.connect(lambda checked, cid=row["id"]: self._edit_platform_mapping(cid))
                self.platform_table.setCellWidget(r, 5, edit_btn)
        except Exception as e:
            logger.error(f"刷新平台配置异常: {e}")

    def _edit_platform_mapping(self, config_id: int):
        row = self.db_manager.fetch_one("SELECT * FROM platform_configs WHERE id = ?", (config_id,))
        if not row:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑表单映射 - {row['platform_name']}")
        dialog.setMinimumSize(500, 500)
        dlg_layout = QVBoxLayout(dialog)

        dlg_layout.addWidget(QLabel("选择器映射 (selectors JSON):"))
        dlg_layout.addWidget(QLabel("每个字段对应平台上的CSS选择器，为空则使用插件默认值"))
        sel_edit = QTextEdit()
        sel_edit.setPlaceholderText(
            '{\n  "title_input": "input[name=\'title\']",\n'
            '  "content_input": "textarea[name=\'content\']",\n'
            '  "submit_btn": "button[type=\'submit\']",\n'
            '  "image_upload": "input[type=\'file\']",\n'
            '  "category_select": "select[name=\'category\']",\n'
            '  "company_input": "input[name=\'company_name\']"\n}'
        )
        try:
            import json
            current_sel = row['selectors'] or '{}'
            sel_edit.setText(json.dumps(json.loads(current_sel), indent=2, ensure_ascii=False))
        except Exception:
            sel_edit.setText(row['selectors'] or '{}')
        dlg_layout.addWidget(sel_edit)

        dlg_layout.addWidget(QLabel("表单配置 (form_config JSON):"))
        form_edit = QTextEdit()
        form_edit.setPlaceholderText('{"category_options": ["服务", "产品", "公司"], "max_title_len": 30}')
        try:
            current_form = row['form_config'] or '{}'
            form_edit.setText(json.dumps(json.loads(current_form), indent=2, ensure_ascii=False))
        except Exception:
            form_edit.setText(row['form_config'] or '{}')
        dlg_layout.addWidget(form_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self._save_platform_mapping(config_id, sel_edit, form_edit, dialog))
        buttons.rejected.connect(dialog.reject)
        dlg_layout.addWidget(buttons)
        dialog.exec()

    def _save_platform_mapping(self, config_id, sel_edit, form_edit, dialog):
        import json
        try:
            selectors = sel_edit.toPlainText().strip()
            form_config = form_edit.toPlainText().strip()
            if selectors:
                json.loads(selectors)  # validate
            if form_config:
                json.loads(form_config)
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON 格式错误", f"请修正 JSON 格式:\n{e}")
            return

        self.db_manager.update("platform_configs", {
            "selectors": selectors,
            "form_config": form_config,
            "updated_at": format_datetime(),
        }, "id = ?", (config_id,))
        self._refresh_platform_table()
        QMessageBox.information(self, "已保存", "表单映射配置已保存")
        dialog.accept()

    def _toggle_platform(self, config_id: int):
        try:
            row = self.db_manager.fetch_one("SELECT enabled FROM platform_configs WHERE id = ?", (config_id,))
            if row:
                new_val = 0 if row["enabled"] else 1
                self.db_manager.update("platform_configs", {"enabled": new_val}, "id = ?", (config_id,))
                self._refresh_platform_table()
        except Exception as e:
            logger.error(f"切换平台状态失败: {e}")

    def _add_platform_config(self):
        name = self.platform_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入平台名称")
            return
        try:
            existing = self.db_manager.fetch_one(
                "SELECT id FROM platform_configs WHERE platform_name = ?", (name,)
            )
            if existing:
                QMessageBox.warning(self, "提示", "该平台已存在")
                return
            now = format_datetime()
            self.db_manager.insert("platform_configs", {
                "platform_name": name, "plugin_name": name,
                "platform_type": "custom", "created_at": now, "updated_at": now
            })
            self._refresh_platform_table()
            self.platform_name_edit.clear()
        except Exception as e:
            logger.error(f"添加平台失败: {e}")

    def _save_settings(self):
        try:
            settings = {
                "BROWSER_HEADLESS": str(self.general_headless.isChecked()).lower(),
                "BROWSER_TIMEOUT": str(self.general_timeout.value()),
                "BROWSER_SLOW_MO": str(self.general_slow_mo.value()),
                "VIEWPORT_WIDTH": str(self.general_viewport_w.value()),
                "VIEWPORT_HEIGHT": str(self.general_viewport_h.value()),
                "LOG_LEVEL": self.general_log_level.currentText(),
                "DAILY_PUBLISH_LIMIT": str(self.pub_daily_limit.value()),
                "PUBLISH_INTERVAL_MIN": str(self.pub_interval_min.value()),
                "PUBLISH_INTERVAL_MAX": str(self.pub_interval_max.value()),
                "RETRY_MAX": str(self.pub_retry_max.value()),
                "RETRY_DELAY": str(self.pub_retry_delay.value()),
                "PROXY_ENABLED": str(self.proxy_enabled.isChecked()).lower(),
                "PROXY_API_URL": self.proxy_api_url.text(),
                "PROXY_API_KEY": self.proxy_api_key.text(),
                "PROXY_EXTRACT_COUNT": str(self.proxy_extract_count.value()),
                "PROXY_CHECK_INTERVAL": str(self.proxy_check_interval.value()),
                "PROXY_TEST_URL": self.proxy_test_url.text(),
                "PROXY_TEST_TIMEOUT": str(self.proxy_test_timeout.value()),
                "PROXY_MAX_FAILURES": str(self.proxy_max_failures.value()),
                "PROXY_ROTATION_MODE": self.proxy_rotation_mode.currentText(),
                # AI settings
                "AI_ENABLED": str(self.ai_enabled.isChecked()).lower(),
                "AI_PROVIDER": self.ai_provider_combo.currentText(),
                "AI_API_KEY": self.ai_api_key.text(),
                "AI_API_BASE": self.ai_api_base.text(),
                "AI_MODEL": self.ai_model.currentText(),
                "CLAUDE_API_KEY": self.claude_api_key.text(),
                "CLAUDE_MODEL": self.claude_model.currentText(),
                "AI_MAX_TOKENS": str(self.ai_max_tokens.value()),
                "AI_TEMPERATURE": self.ai_temperature.currentText().split()[0],
                "AI_FALLBACK_TEMPLATE": str(self.ai_fallback.isChecked()).lower(),
                # SEO settings
                "SEO_ENABLED": str(self.seo_enabled.isChecked()).lower(),
                "SEO_CHECK_INTERVAL_HOURS": str(self.seo_check_interval.value()),
                "SEO_SEARCH_ENGINES": self.seo_engines.text(),
                "SEO_MAX_RESULT_PAGES": str(self.seo_max_pages.value()),
                "SEO_AUTO_REPUBLISH": str(self.seo_auto_republish.isChecked()).lower(),
                "SEO_REQUEST_DELAY": str(self.seo_request_delay.value()),
                "THEME": "dark" if self.general_theme.currentIndex() == 0 else "light",
            }
            for key, value in settings.items():
                set_key(self.env_path, key, value)

            config_loader.load(self.env_path)

            # 如果主题有变化，即时切换
            from ui.styles.theme_manager import theme_manager
            from PyQt6.QtWidgets import QApplication
            new_theme = "dark" if self.general_theme.currentIndex() == 0 else "light"
            if new_theme != theme_manager.current_name:
                theme_manager.set_theme(new_theme)

            company_name = self.ent_company_name.text().strip()
            if company_name:
                self._save_enterprise_profile()
            QMessageBox.information(self, "成功", "设置已保存" +
                ("\n(未填写公司名称，企业资料未保存)" if not company_name else ""))
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
