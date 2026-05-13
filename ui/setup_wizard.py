"""首次启动配置引导向导 -- QWizard 四步配置"""
import os
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit,
    QTextEdit, QLabel, QCheckBox, QHBoxLayout, QFileDialog, QPushButton,
    QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

logger = logging.getLogger(__name__)


class WelcomePage(QWizardPage):
    """第1页: 欢迎"""

    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用资质代办全网推广助手")
        self.setSubTitle("首次使用需要完成基础配置，只需 2 分钟")

        layout = QVBoxLayout(self)
        intro = QLabel(
            '<h3>本软件将帮助您：</h3>'
            '<ul style="line-height:1.8">'
            '<li>一键批量发布内容到 B2B 平台、自媒体专栏、本地商户平台</li>'
            '<li>AI 自动生成行业软文、科普文、对比文</li>'
            '<li>自动监控百度/360 搜索引擎收录和关键词排名</li>'
            '<li>多账号管理、代理 IP 池轮换、浏览器指纹隔离防封号</li>'
            '</ul>'
            '<p style="color:#888;margin-top:20px">点击 下一步 开始配置</p>'
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)


class EnterprisePage(QWizardPage):
    """第2页: 企业资料"""

    def __init__(self):
        super().__init__()
        self.setTitle("企业资料设置")
        self.setSubTitle("发布内容时将自动填入以下企业信息到各平台表单")

        layout = QFormLayout(self)
        layout.setSpacing(8)

        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("例如: 杭州XX企业服务有限公司")
        self.company_name.setMinimumWidth(350)
        layout.addRow("公司全称 *:", self.company_name)

        self.short_name = QLineEdit()
        self.short_name.setPlaceholderText("例如: XX企服")
        layout.addRow("公司简称:", self.short_name)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("例如: 0571-88888888")
        layout.addRow("联系电话:", self.phone)

        self.contact_person = QLineEdit()
        self.contact_person.setPlaceholderText("例如: 张经理")
        layout.addRow("联系人:", self.contact_person)

        self.address = QLineEdit()
        self.address.setPlaceholderText("例如: 杭州市西湖区XX路XX号")
        layout.addRow("公司地址:", self.address)

        self.website = QLineEdit()
        self.website.setPlaceholderText("例如: https://www.example.com")
        layout.addRow("企业网站:", self.website)

        self.description = QTextEdit()
        self.description.setPlaceholderText("公司简介(可选，用于AI生成时的背景)...")
        self.description.setMaximumHeight(80)
        layout.addRow("公司简介:", self.description)

        tip = QLabel("<span style='color:#888;font-size:11px'>* 公司全称为必填项，其余可选。后续可在系统设置中修改。</span>")
        tip.setWordWrap(True)
        layout.addRow(tip)

    def validatePage(self):
        if not self.company_name.text().strip():
            QMessageBox.warning(self, "提示", "请填写公司全称")
            return False
        return True


class QuickStartPage(QWizardPage):
    """第3页: 快速开始指引"""

    def __init__(self):
        super().__init__()
        self.setTitle("快速开始指引")
        self.setSubTitle("了解基本操作流程，5 分钟上手")

        layout = QVBoxLayout(self)

        guide = QLabel(
            "<h3>操作流程概要</h3>"
            "<ol style='line-height:2.0'>"
            "<li><b>系统设置</b> → 配置发布限速、代理IP、AI模型(可选)</li>"
            "<li><b>账号管理</b> → 添加各平台账号，可批量导入CSV</li>"
            "<li><b>文案生成</b> → 输入关键词，一键批量生成行业文案</li>"
            "<li><b>任务发布</b> → 创建发布任务 → 一键发布到各平台</li>"
            "<li><b>收录监控</b> → 添加关键词，自动检测收录和排名</li>"
            "</ol>"
            "<h3 style='margin-top:16px'>环境检查</h3>"
            "<ul style='line-height:1.8'>"
            "<li>需要 Chromium 浏览器 (首次启动会自动提示安装)</li>"
            "<li>代理 IP 池: 如需多账号轮换 IP，请配置代理 API</li>"
            "<li>AI 文案: 配置 OpenAI/Claude API Key(可选，不配也能用模板)</li>"
            "</ul>"
        )
        guide.setWordWrap(True)
        layout.addWidget(guide)

        self.skip_tip = QLabel(
            "<p style='color:#0078d4;margin-top:12px'>"
            "后续随时可以在 <b>系统设置</b> 中修改所有配置</p>"
        )
        self.skip_tip.setWordWrap(True)
        layout.addWidget(self.skip_tip)


class FinishPage(QWizardPage):
    """第4页: 完成"""

    def __init__(self):
        super().__init__()
        self.setTitle("配置完成！")
        self.setSubTitle("一切就绪，可以开始使用了")

        layout = QVBoxLayout(self)
        summary = QLabel(
            "<h3>接下来您可以：</h3>"
            "<ul style='line-height:2.0'>"
            "<li>前往 <b>账号管理</b> 添加您的平台账号</li>"
            "<li>前往 <b>文案生成</b> 输入关键词生成推广文章</li>"
            "<li>前往 <b>系统设置</b> 配置代理IP和AI模型</li>"
            "</ul>"
            "<p style='color:#888;margin-top:16px'>"
            "左下角状态灯为绿色表示系统运行正常<br>"
            "底部日志栏实时显示所有操作状态</p>"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)


class SetupWizard(QWizard):
    """首次配置引导向导"""

    def __init__(self, db_manager, config_loader=None):
        super().__init__()
        self.db_manager = db_manager
        self.config_loader = config_loader
        self.setWindowTitle("初始配置引导")
        self.setMinimumSize(560, 480)
        self.resize(600, 520)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOptions(
            QWizard.WizardOption.NoBackButtonOnStartPage |
            QWizard.WizardOption.HaveFinishButtonOnEarlyPages
        )

        self.welcome_page = WelcomePage()
        self.enterprise_page = EnterprisePage()
        self.quickstart_page = QuickStartPage()
        self.finish_page = FinishPage()

        self.addPage(self.welcome_page)
        self.addPage(self.enterprise_page)
        self.addPage(self.quickstart_page)
        self.addPage(self.finish_page)

        self.finished.connect(self._on_finished)

    def _on_finished(self, result):
        if result == QWizard.DialogCode.Accepted:
            self._save_enterprise_profile()
            self._mark_setup_done()

    def _save_enterprise_profile(self):
        try:
            data = {
                "company_name": self.enterprise_page.company_name.text().strip(),
                "short_name": self.enterprise_page.short_name.text().strip(),
                "phone": self.enterprise_page.phone.text().strip(),
                "contact_person": self.enterprise_page.contact_person.text().strip(),
                "address": self.enterprise_page.address.text().strip(),
                "website": self.enterprise_page.website.text().strip(),
                "description": self.enterprise_page.description.toPlainText().strip(),
            }
            if data["company_name"]:
                self.db_manager.save_enterprise_profile(data)
                logger.info("配置向导: 企业资料已保存")
        except Exception as e:
            logger.error(f"配置向导保存企业资料失败: {e}")

    def _mark_setup_done(self):
        from dotenv import set_key
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".env"
        )
        try:
            set_key(env_path, "SETUP_COMPLETED", "true")
            if self.config_loader:
                self.config_loader.load(env_path)
        except Exception:
            # .env 不存在则创建
            try:
                with open(env_path, "a", encoding="utf-8") as f:
                    f.write("\nSETUP_COMPLETED=true\n")
            except Exception as e:
                logger.warning(f"无法写入SETUP_COMPLETED标记: {e}")
