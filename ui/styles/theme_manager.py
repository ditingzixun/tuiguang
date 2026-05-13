"""主题管理器 — 单例，管理深色/浅色主题，生成全局 QSS"""
import os
from typing import Literal, Optional
from PyQt6.QtWidgets import QApplication


class Theme:
    """一套完整的主题配色"""

    def __init__(self, name: str, colors: dict):
        self.name = name
        self._c = colors

    def get(self, key: str, default: str = "") -> str:
        return self._c.get(key, default)


# ====== 深色主题 ======
DARK_COLORS = {
    # 侧边栏
    "sidebar_bg": "#1e1e2e",
    "sidebar_border": "#2d2d3f",
    "sidebar_text": "#a6adc8",
    "sidebar_hover_bg": "#313244",
    "sidebar_hover_text": "#cdd6f4",
    "sidebar_selected_bg": "#45475a",
    "sidebar_selected_text": "#ffffff",
    "sidebar_selected_accent": "#89b4fa",
    # Logo
    "logo_color": "#cdd6f4",
    "logo_font_size": "15px",
    # 导航菜单
    "nav_text": "#a6adc8",
    "nav_font_size": "13px",
    # 底部状态区
    "status_light_active": "#a6e3a1",
    "status_light_error": "#f38ba8",
    "status_text": "#a6adc8",
    "version_text": "#8a90a8",
    # 日志面板
    "log_panel_bg": "#1e1e2e",
    "log_panel_border": "#2d2d3f",
    "log_output_bg": "#11111b",
    "log_output_text": "#cdd6f4",
    "log_output_font": '"Consolas", "Courier New", monospace',
    "log_header_text": "#a6adc8",
    "log_btn_bg": "#313244",
    "log_btn_text": "#cdd6f4",
    "log_btn_hover_bg": "#45475a",
    "log_cb_text": "#a6adc8",
    # 内容区
    "content_bg": "#ffffff",
    "main_bg": "#f0f2f5",
    # 菜单栏
    "menubar_bg": "#1e1e2e",
    "menubar_text": "#cdd6f4",
    "menubar_hover_bg": "#45475a",
    "menu_bg": "#313244",
    "menu_text": "#cdd6f4",
    "menu_border": "#45475a",
    "menu_hover_bg": "#45475a",
    # 按钮
    "btn_bg": "#3a3a3a",
    "btn_text": "#000000",
    "btn_border": "#555555",
    "btn_hover_bg": "#3a3a3a",
    "btn_hover_border": "#05a4ff",
    "btn_hover_text": "#05a4ff",
    "btn_pressed_bg": "#2a2a2a",
    "btn_pressed_border": "#444444",
    "btn_disabled_bg": "#e0e0e0",
    "btn_disabled_text": "#999999",
    "btn_disabled_border": "#cccccc",
    # 表格
    "table_grid": "#e0e0e0",
    "table_selection_bg": "#0078d4",
    "table_selection_text": "#ffffff",
    "table_border": "#e0e0e0",
    "table_item_padding": "4px",
    "table_header_bg": "#f5f5f5",
    "table_header_border": "#e0e0e0",
    # 输入控件
    "input_bg": "#ffffff",
    "input_text": "#333333",
    "input_border": "#d0d0d0",
    "input_focus_border": "#0078d4",
    "input_padding": "4px",
    "input_radius": "3px",
    # 分组框
    "groupbox_border": "#d0d0d0",
    "groupbox_radius": "6px",
    # 分割条
    "splitter_handle": "#e0e0e0",
    # 标签页
    "tab_bg": "#f5f5f5",
    "tab_selected_bg": "#ffffff",
    "tab_text": "#333333",
    "tab_selected_text": "#0078d4",
    # 提示/状态文本
    "hint_color": "#888888",
    "status_secondary": "#666666",
    # 表格行状态颜色
    "row_banned": "#ffc8c8",
    "row_limited": "#ffffc8",
    "row_failed_login": "#ffe6c8",
    "row_proxy_failed": "#ffc8c8",
    "row_proxy_active": "#c8ffc8",
    # 滚动条
    "scrollbar_bg": "#f0f0f0",
    "scrollbar_handle": "#c0c0c0",
    "scrollbar_handle_hover": "#a0a0a0",
    # 分隔线
    "separator_color": "#313244",
}

# ====== 浅色主题 ======
LIGHT_COLORS = {
    "sidebar_bg": "#f0f2f5",
    "sidebar_border": "#d0d0d0",
    "sidebar_text": "#555555",
    "sidebar_hover_bg": "#e0e0e0",
    "sidebar_hover_text": "#333333",
    "sidebar_selected_bg": "#d0d8e8",
    "sidebar_selected_text": "#111111",
    "sidebar_selected_accent": "#0078d4",
    "logo_color": "#222222",
    "logo_font_size": "15px",
    "nav_text": "#555555",
    "nav_font_size": "13px",
    "status_light_active": "#2ea043",
    "status_light_error": "#da3633",
    "status_text": "#666666",
    "version_text": "#999999",
    "log_panel_bg": "#f5f5f5",
    "log_panel_border": "#d0d0d0",
    "log_output_bg": "#fafafa",
    "log_output_text": "#333333",
    "log_output_font": '"Consolas", "Courier New", monospace',
    "log_header_text": "#555555",
    "log_btn_bg": "#e0e0e0",
    "log_btn_text": "#333333",
    "log_btn_hover_bg": "#d0d0d0",
    "log_cb_text": "#666666",
    "content_bg": "#ffffff",
    "main_bg": "#f0f2f5",
    "menubar_bg": "#f5f5f5",
    "menubar_text": "#333333",
    "menubar_hover_bg": "#e0e0e0",
    "menu_bg": "#ffffff",
    "menu_text": "#333333",
    "menu_border": "#d0d0d0",
    "menu_hover_bg": "#e8f0fe",
    "btn_bg": "#3a3a3a",
    "btn_text": "#000000",
    "btn_border": "#555555",
    "btn_hover_bg": "#3a3a3a",
    "btn_hover_border": "#05a4ff",
    "btn_hover_text": "#05a4ff",
    "btn_pressed_bg": "#2a2a2a",
    "btn_pressed_border": "#444444",
    "btn_disabled_bg": "#e0e0e0",
    "btn_disabled_text": "#999999",
    "btn_disabled_border": "#cccccc",
    "table_grid": "#d0d0d0",
    "table_selection_bg": "#0078d4",
    "table_selection_text": "#ffffff",
    "table_border": "#d0d0d0",
    "table_item_padding": "4px",
    "table_header_bg": "#f0f0f0",
    "table_header_border": "#d0d0d0",
    "input_bg": "#ffffff",
    "input_text": "#333333",
    "input_border": "#c0c0c0",
    "input_focus_border": "#0078d4",
    "input_padding": "4px",
    "input_radius": "3px",
    "groupbox_border": "#c0c0c0",
    "groupbox_radius": "6px",
    "splitter_handle": "#d0d0d0",
    "tab_bg": "#f0f0f0",
    "tab_selected_bg": "#ffffff",
    "tab_text": "#555555",
    "tab_selected_text": "#0078d4",
    "hint_color": "#999999",
    "status_secondary": "#888888",
    "row_banned": "#ffd0d0",
    "row_limited": "#ffffd0",
    "row_failed_login": "#ffe8d0",
    "row_proxy_failed": "#ffd0d0",
    "row_proxy_active": "#d0ffd0",
    "scrollbar_bg": "#e8e8e8",
    "scrollbar_handle": "#c0c0c0",
    "scrollbar_handle_hover": "#a0a0a0",
    "separator_color": "#d0d0d0",
}


def _build_stylesheet(theme: Theme) -> str:
    """根据主题生成完整的 QSS 字符串"""
    c = theme
    return f"""
        /* ====== 全局 ====== */
        QMainWindow {{ background-color: {c.get("main_bg")}; }}

        /* ====== 左侧菜单栏 ====== */
        #sidebar {{
            background-color: {c.get("sidebar_bg")};
            border-right: 1px solid {c.get("sidebar_border")};
        }}
        #sidebar QLabel#logo {{
            color: {c.get("logo_color")};
            font-size: {c.get("logo_font_size")};
            font-weight: bold;
            padding: 14px 12px;
        }}
        #navMenu {{
            background: transparent;
            border: none;
            outline: none;
            color: {c.get("nav_text")};
            font-size: {c.get("nav_font_size")};
            padding: 4px 0;
        }}
        #navMenu::item {{
            padding: 10px 16px;
            border-left: 3px solid transparent;
            margin: 2px 8px;
            border-radius: 6px;
        }}
        #navMenu::item:hover {{
            background-color: {c.get("sidebar_hover_bg")};
            color: {c.get("sidebar_hover_text")};
        }}
        #navMenu::item:selected {{
            background-color: {c.get("sidebar_selected_bg")};
            color: {c.get("sidebar_selected_text")};
            border-left: 3px solid {c.get("sidebar_selected_accent")};
        }}

        /* ====== 底部日志栏 ====== */
        #logPanel {{
            background-color: {c.get("log_panel_bg")};
            border-top: 1px solid {c.get("log_panel_border")};
        }}
        #logOutput {{
            background-color: {c.get("log_output_bg")};
            color: {c.get("log_output_text")};
            font-family: {c.get("log_output_font")};
            font-size: 12px;
            border: none;
            border-radius: 4px;
            padding: 6px;
        }}

        /* ====== 通用组件 ====== */
        QTableWidget {{
            gridline-color: {c.get("table_grid")};
            selection-background-color: {c.get("table_selection_bg")};
            selection-color: {c.get("table_selection_text")};
            border: 1px solid {c.get("table_border")};
            border-radius: 4px;
        }}
        QTableWidget::item {{ padding: {c.get("table_item_padding")}; }}
        QPushButton {{
            background-color: {c.get("btn_bg")};
            color: {c.get("btn_text")};
            border: 1px solid {c.get("btn_border", "#005a9e")};
            padding: 7px 16px;
            border-radius: 5px;
            font-family: "Microsoft YaHei";
            font-weight: bold;
            font-size: 12px;
            min-height: 28px;
        }}
        QPushButton:hover {{
            background-color: {c.get("btn_hover_bg")};
            border-color: {c.get("btn_hover_border", "#666666")};
            color: {c.get("btn_hover_text", "#ffffff")};
        }}
        QPushButton:pressed {{
            background-color: {c.get("btn_pressed_bg")};
            border-color: {c.get("btn_pressed_border", "#004578")};
        }}
        QPushButton:disabled {{
            background-color: {c.get("btn_disabled_bg")};
            color: {c.get("btn_disabled_text")};
            border-color: {c.get("btn_disabled_border", "#cccccc")};
        }}
        QLabel {{
            color: {c.get("input_text", "#333333")};
        }}
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {c.get("groupbox_border")};
            border-radius: {c.get("groupbox_radius")};
            margin-top: 10px;
            padding-top: 18px;
            color: {c.get("input_text", "#333333")};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {c.get("input_text", "#333333")};
        }}
        QLineEdit, QTextEdit, QSpinBox, QComboBox {{
            border: 1px solid {c.get("input_border")};
            border-radius: {c.get("input_radius")};
            padding: {c.get("input_padding")};
            background-color: {c.get("input_bg", "#ffffff")};
            color: {c.get("input_text", "#333333")};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border-color: {c.get("input_focus_border")};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 4px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.get("input_bg", "#ffffff")};
            color: {c.get("input_text", "#333333")};
            border: 1px solid {c.get("input_border")};
            selection-background-color: {c.get("table_selection_bg")};
            selection-color: {c.get("table_selection_text")};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 4px 8px;
            min-height: 24px;
        }}
        QListWidget {{
            background-color: {c.get("input_bg", "#ffffff")};
            color: {c.get("input_text", "#333333")};
            border: 1px solid {c.get("input_border")};
            border-radius: {c.get("input_radius")};
            outline: none;
        }}
        QListWidget::item {{
            padding: 4px 8px;
        }}
        QListWidget::item:selected {{
            background-color: {c.get("table_selection_bg")};
            color: {c.get("table_selection_text")};
        }}
        QSplitter::handle {{
            background-color: {c.get("splitter_handle")};
            height: 1px;
        }}
        QHeaderView::section {{
            background-color: {c.get("table_header_bg")};
            border: none;
            border-bottom: 2px solid {c.get("table_header_border")};
            padding: 6px 4px;
            font-weight: bold;
        }}

        /* ====== 菜单栏 ====== */
        QMenuBar {{
            background: {c.get("menubar_bg")};
            color: {c.get("menubar_text")};
            padding: 2px;
        }}
        QMenuBar::item:selected {{ background: {c.get("menubar_hover_bg")}; }}
        QMenu {{
            background: {c.get("menu_bg")};
            color: {c.get("menu_text")};
            border: 1px solid {c.get("menu_border")};
        }}
        QMenu::item:selected {{ background: {c.get("menu_hover_bg")}; }}

        /* ====== 标签页 ====== */
        QTabWidget::pane {{
            border: 1px solid {c.get("table_border")};
            background: {c.get("content_bg")};
        }}
        QTabBar::tab {{
            background: {c.get("tab_bg")};
            color: {c.get("tab_text")};
            padding: 8px 18px;
            border: 1px solid {c.get("table_border")};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background: {c.get("tab_selected_bg")};
            color: {c.get("tab_selected_text")};
            font-weight: bold;
        }}

        /* ====== 侧边栏状态/版本标签 ====== */
        #sidebarStatusLight {{ color: {c.get("status_light_active")}; font-size: 10px; }}
        #sidebarStatusText {{ color: {c.get("status_text")}; font-size: 11px; }}
        #sidebarVersion {{ color: {c.get("version_text")}; font-size: 10px; }}
        #sidebarSeparator {{ color: {c.get("separator_color")}; }}

        /* ====== 日志面板子控件 ====== */
        #logHeaderTitle {{ color: {c.get("log_header_text")}; font-size: 12px; font-weight: bold; }}
        #logPauseCb {{ color: {c.get("log_cb_text")}; font-size: 11px; }}
        #logClearBtn {{
            background: {c.get("log_btn_bg")};
            color: {c.get("log_btn_text")};
            border: none;
            border-radius: 3px;
            font-size: 11px;
            padding: 2px 6px;
        }}
        #logClearBtn:hover {{ background: {c.get("log_btn_hover_bg")}; }}

        /* ====== 紧凑按钮(与输入框同高) ====== */
        #historyBtn {{
            max-height: 24px;
            min-height: 24px;
            padding: 0px 8px;
            font-size: 11px;
        }}
        #historyBtn:hover {{
            background-color: {c.get("btn_hover_bg", "#3a3a3a")};
            color: {c.get("btn_hover_text", "#05a4ff")};
            border-color: {c.get("btn_hover_border", "#05a4ff")};
        }}

        /* ====== 主按钮(略醒目) ====== */
        #primaryBtn {{
            background-color: {c.get("primary_btn_bg", "#3a3a3a")};
            color: {c.get("primary_btn_text", "#000000")};
            border: 1px solid {c.get("primary_btn_border", "#555555")};
            padding: 7px 16px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: bold;
            min-height: 28px;
        }}
        #primaryBtn:hover {{
            background-color: {c.get("primary_btn_hover", "#4a4a4a")};
            border-color: {c.get("primary_btn_hover_border", "#666666")};
        }}

        /* ====== 提示/状态文本 ====== */
        #hintLabel {{ color: {c.get("hint_color")}; font-size: 11px; }}
        #statusSecondary {{ font-size: 11px; color: {c.get("status_secondary")}; }}

        /* ====== 滚动条 ====== */
        QScrollBar:vertical {{
            background: {c.get("scrollbar_bg")};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {c.get("scrollbar_handle")};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {c.get("scrollbar_handle_hover")}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

        /* ====== 复选框 ====== */
        QCheckBox {{
            spacing: 6px;
            color: {c.get("input_text", "#333333")};
        }}

        /* ====== 提示框 ====== */
        QToolTip {{
            background: {c.get("menu_bg")};
            color: {c.get("menu_text")};
            border: 1px solid {c.get("menu_border")};
            padding: 4px 8px;
            border-radius: 4px;
        }}
    """


class ThemeManager:
    """全局主题管理器(单例)"""
    _instance: Optional["ThemeManager"] = None

    def __new__(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._dark_theme = Theme("dark", DARK_COLORS)
        self._light_theme = Theme("light", LIGHT_COLORS)
        self._current_name: Literal["dark", "light"] = "dark"
        self._app: Optional[QApplication] = None

    @property
    def current(self) -> Theme:
        if self._current_name == "light":
            return self._light_theme
        return self._dark_theme

    @property
    def current_name(self) -> str:
        return self._current_name

    def set_theme(self, name: str):
        """切换主题并立即应用"""
        if name not in ("dark", "light"):
            return
        self._current_name = name
        if self._app:
            self._apply_stylesheet()

    def toggle(self):
        """切换深色/浅色"""
        self.set_theme("light" if self._current_name == "dark" else "dark")

    def get_color(self, key: str, default: str = "") -> str:
        """获取当前主题的颜色值（供代码中使用）"""
        return self.current.get(key, default)

    def init(self, app: QApplication, theme_name: str = "dark"):
        """初始化并应用主题"""
        self._app = app
        self._current_name = theme_name if theme_name in ("dark", "light") else "dark"
        self._apply_stylesheet()

    def _apply_stylesheet(self):
        """应用主题样式表"""
        if self._app:
            self._app.setStyleSheet(_build_stylesheet(self.current))

    def apply_to_app(self, app: QApplication):
        """向后兼容 — 同 init()，但保留已有主题"""
        self._app = app
        self._apply_stylesheet()


# 全局单例
theme_manager = ThemeManager()
