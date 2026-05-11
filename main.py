"""资质代办行业全网推广自动化软件
主入口文件
"""
import sys
import os

# 确保项目根目录在path中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow
from loguru import logger


def setup_environment():
    """初始化运行环境"""
    os.makedirs("data/logs", exist_ok=True)
    os.makedirs("data/profiles", exist_ok=True)
    os.makedirs("data/screenshots", exist_ok=True)
    os.makedirs("data/exports", exist_ok=True)

    logger.add(
        "data/logs/app_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        encoding="utf-8",
    )
    logger.info("=" * 60)
    logger.info("资质代办全网推广助手 启动中...")
    logger.info("=" * 60)


def main():
    setup_environment()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei", 9))

    # 全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTableWidget {
            gridline-color: #e0e0e0;
            selection-background-color: #0078d4;
            selection-color: white;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 6px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QPushButton:disabled {
            background-color: #cccccc;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e8e8e8;
            padding: 8px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #0078d4;
        }
        QStatusBar {
            background-color: #0078d4;
            color: white;
        }
        QLineEdit, QTextEdit, QSpinBox, QComboBox {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            padding: 4px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border-color: #0078d4;
        }
    """)

    window = MainWindow()
    window.show()

    logger.info("主窗口已显示")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
