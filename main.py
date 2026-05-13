"""资质代办行业全网推广自动化软件 -- 主入口"""
import sys
import os
import logging
import traceback

# PyInstaller 打包后资源路径处理
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_BASE_DIR)
sys.path.insert(0, _BASE_DIR)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont, QIcon
from ui.main_window import MainWindow
from ui.styles.theme_manager import theme_manager
from utils.logging_setup import setup_logging
from utils.config_loader import config_loader


def main():
    try:
        os.makedirs("data/logs", exist_ok=True)
        os.makedirs("data/profiles", exist_ok=True)
        os.makedirs("data/screenshots", exist_ok=True)
        os.makedirs("data/exports", exist_ok=True)
    except Exception:
        pass

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("资质代办全网推广助手 启动中...")
    logger.info("=" * 60)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 9))

    # 窗口图标
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 首次启动配置引导
    setup_completed = os.getenv("SETUP_COMPLETED", "").lower() == "true"
    if not setup_completed:
        from db.database import DatabaseManager
        from ui.setup_wizard import SetupWizard
        db = DatabaseManager()
        db.init_db()
        wizard = SetupWizard(db, config_loader)
        wizard.exec()
        db.close()

    # 全局主题
    theme_name = config_loader.get("THEME", "dark").strip().lower()
    if theme_name not in ("dark", "light"):
        theme_name = "dark"
    theme_manager.init(app, theme_name)

    window = MainWindow()
    window.show()
    logger.info("主窗口已显示")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err_msg = f"程序启动失败:\n\n{traceback.format_exc()}"
        print(err_msg)
        try:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "启动失败", err_msg[:800])
        except Exception:
            pass
        sys.exit(1)
