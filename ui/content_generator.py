"""文案生成界面 — 本地模板批量生成"""
import csv
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QTextEdit, QMessageBox, QHeaderView, QLabel,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QProgressBar, QSplitter, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)
from core.ai_engine import ai_engine
from ui.styles.theme_manager import theme_manager
from PyQt6.QtCore import QTimer


class ContentDialog(QDialog):
    """文案详情编辑"""
    def __init__(self, parent=None, content=None):
        super().__init__(parent)
        self.content = content
        self.setWindowTitle("文案详情")
        self.setMinimumSize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.title_edit = QLineEdit()
        layout.addWidget(QLabel("标题:"))
        layout.addWidget(self.title_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["soft_article", "science_article", "comparison_article", "policy_article", "case_study"])
        layout.addWidget(QLabel("类型:"))
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("内容:"))
        self.content_edit = QTextEdit()
        self.content_edit.setMinimumHeight(250)
        layout.addWidget(self.content_edit)

        if self.content:
            self.title_edit.setText(self.content.get("title", ""))
            self.content_edit.setText(self.content.get("content", ""))
            idx = self.type_combo.findText(self.content.get("content_type", ""))
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class TitleLibraryDialog(QDialog):
    """标题库预览对话框"""
    def __init__(self, parent, keyword, titles, db_manager):
        super().__init__(parent)
        self.keyword = keyword
        self.titles = titles
        self.db_manager = db_manager
        self.setWindowTitle(f"标题库 - {keyword}")
        self.setMinimumSize(550, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"关键词: {self.keyword} | 共 {len(self.titles)} 个标题"))

        self.title_list = QListWidget()
        self.title_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for t in self.titles:
            item = QListWidgetItem(f"[{t['type']}] {t['title']}")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.title_list.addItem(item)
        layout.addWidget(self.title_list)

        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("全选")
        btn_select_all.clicked.connect(lambda: self.title_list.selectAll())
        btn_import = QPushButton("导入选中标题为文案草稿")
        btn_import.clicked.connect(self._import_selected)
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_import)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _import_selected(self):
        selected = [self.title_list.item(i).data(Qt.ItemDataRole.UserRole)
                     for i in range(self.title_list.count())
                     if self.title_list.item(i).isSelected()]
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个标题")
            return

        now = format_datetime()
        count = 0
        for t in selected:
            try:
                self.db_manager.insert("contents", {
                    "title": t["title"],
                    "content": f"# {t['title']}\n\n(待填充内容 — 由AI标题库生成)",
                    "content_type": "soft_article",
                    "qualification_type": self.keyword,
                    "keywords": self.keyword,
                    "source": f"title_library({t.get('source', 'ai')})",
                    "status": "draft",
                    "created_at": now,
                    "updated_at": now,
                })
                count += 1
            except Exception as e:
                logger.error(f"导入标题失败: {e}")

        QMessageBox.information(self, "导入完成", f"已导入 {count} 个标题为文案草稿")
        self.accept()


class ContentGeneratorWidget(QWidget):
    """文案生成面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._setup_ui()
        self.refresh_table()
        self._ai_timer = QTimer(self)
        self._ai_timer.timeout.connect(self._refresh_ai_status)
        self._ai_timer.start(30000)  # 每30秒刷新AI状态

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧设置面板
        left = QWidget()
        left_layout = QVBoxLayout(left)

        # 关键词输入（优先） — 可编辑下拉框 + 历史记录
        kw_group = QGroupBox("关键词(优先)")
        kw_layout = QVBoxLayout(kw_group)
        kw_input_layout = QHBoxLayout()
        self.keyword_combo = QComboBox()
        self.keyword_combo.setEditable(True)
        self.keyword_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.keyword_combo.lineEdit().setPlaceholderText("输入关键词，如: 杭州文网文代办、ICP许可证办理")
        self._load_keyword_history()
        kw_input_layout.addWidget(self.keyword_combo, 1)
        self.btn_history = QPushButton("历史")
        self.btn_history.setObjectName("historyBtn")
        self.btn_history.setFixedWidth(80)
        self.btn_history.setToolTip("查看最近使用的关键词")
        self.btn_history.clicked.connect(self._show_keyword_history)
        kw_input_layout.addWidget(self.btn_history)
        kw_layout.addLayout(kw_input_layout)
        self.keyword_hint = QLabel("填入关键词后将优先使用关键词生成，忽略下方的资质类型选择")
        self.keyword_hint.setObjectName("hintLabel")
        kw_layout.addWidget(self.keyword_hint)
        left_layout.addWidget(kw_group)

        qual_group = QGroupBox("资质类型(多选) — 关键词为空时使用")
        qual_layout = QVBoxLayout(qual_group)
        self.qual_list = QListWidget()
        self.qual_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.qual_list.setMaximumHeight(100)
        qual_types = [
            "网络文化经营许可证", "ICP经营许可证", "EDI经营许可证",
            "广播电视节目制作经营许可证", "增值电信业务经营许可证"
        ]
        for qt in qual_types:
            item = QListWidgetItem(qt)
            item.setSelected(True)
            self.qual_list.addItem(item)
        qual_layout.addWidget(self.qual_list)
        left_layout.addWidget(qual_group)

        type_group = QGroupBox("文案类型(多选)")
        type_layout = QVBoxLayout(type_group)
        self.type_list = QListWidget()
        self.type_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.type_list.setMaximumHeight(100)
        content_types = ["soft_article", "science_article", "comparison_article", "policy_article", "case_study"]
        type_names = ["软文推广", "科普文章", "对比分析", "政策解读", "案例分享"]
        for ct, cn in zip(content_types, type_names):
            item = QListWidgetItem(cn)
            item.setData(Qt.ItemDataRole.UserRole, ct)
            item.setSelected(True)
            self.type_list.addItem(item)
        type_layout.addWidget(self.type_list)
        left_layout.addWidget(type_group)

        gen_group = QGroupBox("生成设置")
        gen_layout = QFormLayout(gen_group)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(3)
        gen_layout.addRow("每种数量:", self.count_spin)
        self.company_edit = QLineEdit()
        self.company_edit.setPlaceholderText("公司名称(可选)")
        gen_layout.addRow("公司名称:", self.company_edit)
        left_layout.addWidget(gen_group)

        # 操作步骤 — 去掉QGroupBox避免样式叠加导致重叠
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setStyleSheet("color: #d0d0d0;")
        left_layout.addWidget(sep_line)
        step_label = QLabel("操作步骤 (按顺序: 标题 → 文案 → 伪原创)")
        step_label.setObjectName("hintLabel")
        step_label.setStyleSheet("font-weight: bold; color: #333;")
        left_layout.addWidget(step_label)
        self.btn_titles = QPushButton("① 生成标题库")
        self.btn_titles.setMinimumHeight(30)
        self.btn_titles.clicked.connect(self._generate_titles)
        left_layout.addWidget(self.btn_titles)
        self.btn_generate = QPushButton("② 批量生成文案")
        self.btn_generate.setMinimumHeight(30)
        self.btn_generate.setObjectName("primaryBtn")
        self.btn_generate.clicked.connect(self._generate)
        left_layout.addWidget(self.btn_generate)
        self.btn_rewrite = QPushButton("③ 伪原创改写选中")
        self.btn_rewrite.setMinimumHeight(30)
        self.btn_rewrite.clicked.connect(self._rewrite_selected)
        left_layout.addWidget(self.btn_rewrite)

        self.ai_status = QLabel(self._ai_status_text())
        self.ai_status.setObjectName("statusSecondary")
        left_layout.addWidget(self.ai_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("")
        left_layout.addWidget(self.progress_label)
        left_layout.addStretch()

        splitter.addWidget(left)

        # 右侧文案列表
        right = QWidget()
        right_layout = QVBoxLayout(right)

        list_toolbar = QHBoxLayout()
        self.btn_edit = QPushButton("编辑")
        self.btn_edit.clicked.connect(self._edit_content)
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self._delete_content)
        self.btn_export = QPushButton("导出CSV")
        self.btn_export.clicked.connect(self._export_content)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh_table)

        for btn in [self.btn_edit, self.btn_delete, self.btn_export, self.btn_refresh]:
            list_toolbar.addWidget(btn)
        right_layout.addLayout(list_toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "类型", "资质类型", "内容预览", "来源", "使用次数"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        content_header = self.table.horizontalHeader()
        content_header.setStretchLastSection(True)
        content_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        content_col_widths = [35, 180, 70, 100, 140, 60, 55]
        for i, w in enumerate(content_col_widths):
            self.table.setColumnWidth(i, w)
        self.table.setMouseTracking(True)
        right_layout.addWidget(self.table)

        splitter.addWidget(right)
        splitter.setSizes([420, 680])
        layout.addWidget(splitter)

    def refresh_table(self, _=None):
        try:
            rows = self.db_manager.fetch_all("SELECT * FROM contents ORDER BY created_at DESC LIMIT 200")
            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                content_text = row["content"] or ""
                preview = content_text[:50].replace("\n", " ") + ("..." if len(content_text) > 50 else "")
                tooltip_text = content_text[:200]
                items = [
                    QTableWidgetItem(str(row["id"])),
                    QTableWidgetItem(row["title"][:60]),
                    QTableWidgetItem(row["content_type"]),
                    QTableWidgetItem(row["qualification_type"] or ""),
                    QTableWidgetItem(preview),
                    QTableWidgetItem(row["source"]),
                    QTableWidgetItem(str(row["used_count"])),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if c in (1, 4) and tooltip_text:
                        item.setToolTip(tooltip_text)
                    self.table.setItem(r, c, item)
        except Exception as e:
            logger.error(f"刷新文案列表异常: {e}")

    def _generate(self):
        keyword = self.keyword_combo.currentText().strip()
        if keyword:
            keywords = [k.strip() for k in keyword.replace("，", ",").split(",") if k.strip()]
            self._save_keywords(keywords)
        else:
            keywords = [item.text() for item in self.qual_list.selectedItems()]

        selected_types = [item.data(Qt.ItemDataRole.UserRole) for item in self.type_list.selectedItems()]

        if not keywords or not selected_types:
            QMessageBox.warning(self, "提示", "请输入关键词或选择资质类型，并选择文案类型")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_generate.setEnabled(False)
        self.btn_titles.setEnabled(False)
        self.progress_label.setText(f"正在生成... 关键词: {len(keywords)}个, 类型: {len(selected_types)}种")
        QApplication.processEvents()

        results = ai_engine.batch_generate(
            keywords, selected_types,
            self.count_spin.value(),
            company_name=self.company_edit.text()
        )

        self.progress_bar.setValue(100)
        self.progress_label.setText(f"生成完成! 共 {len(results)} 篇")
        self.btn_generate.setEnabled(True)
        self.btn_titles.setEnabled(True)

        self._save_results(results)

    def _generate_titles(self):
        keyword = self.keyword_combo.currentText().strip()
        if not keyword:
            keyword = ", ".join(item.text() for item in self.qual_list.selectedItems()[:2])
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入关键词或选择资质类型")
            return

        # 如果是逗号分隔的多个关键词，取第一个生成标题库
        first_kw = keyword.replace("，", ",").split(",")[0].strip()

        self.btn_titles.setEnabled(False)
        self.progress_label.setText(f"正在为 [{first_kw}] 生成标题库...")
        QApplication.processEvents()

        titles = ai_engine.batch_generate_titles(first_kw, count=20)

        if titles:
            dialog = TitleLibraryDialog(self, first_kw, titles, self.db_manager)
            dialog.exec()
            self.progress_label.setText(f"标题库: 已生成 {len(titles)} 个标题")
        else:
            QMessageBox.warning(self, "提示", "标题生成失败，请检查API配置")
        self.btn_titles.setEnabled(True)

    def _rewrite_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if len(rows) != 1:
            QMessageBox.warning(self, "提示", "请选择一篇文案进行伪原创改写")
            return
        row = rows.pop()
        content_id = int(self.table.item(row, 0).text())
        content = self.db_manager.fetch_one("SELECT * FROM contents WHERE id = ?", (content_id,))
        if not content:
            return

        reply = QMessageBox.question(
            self, "伪原创改写",
            f"将对 [{content['title'][:40]}] 进行改写，选择改写强度:",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        # 简化：使用中等强度改写
        self.progress_label.setText("正在进行伪原创改写...")
        QApplication.processEvents()

        result = ai_engine.pseudo_rewrite(content["content"], intensity="medium", title=content["title"])
        if result:
            now = format_datetime()
            self.db_manager.insert("contents", {
                "title": result["title"],
                "content": result["content"],
                "content_type": content["content_type"],
                "qualification_type": content["qualification_type"],
                "keywords": content.get("keywords", ""),
                "source": result.get("source", "rewrite"),
                "created_at": now,
                "updated_at": now,
            })
            self.refresh_table()
            self.progress_label.setText(f"伪原创完成! 已保存新版本")
        else:
            QMessageBox.critical(self, "错误", "伪原创改写失败")

    def _ai_status_text(self):
        from core.ai_provider import ai_provider_manager
        provider = ai_provider_manager.active_provider
        return f"AI引擎: {provider.name} {'(可用)' if provider.is_available() else '(未配置)'}"

    def _refresh_ai_status(self):
        self.ai_status.setText(self._ai_status_text())

    def _load_keyword_history(self):
        """从数据库加载最近20条关键词到下拉列表"""
        self.keyword_combo.clear()
        self.keyword_combo.setCurrentText("")
        try:
            rows = self.db_manager.fetch_all(
                "SELECT keyword FROM keyword_history ORDER BY last_used_at DESC LIMIT 20"
            )
            for row in rows:
                self.keyword_combo.addItem(row["keyword"])
        except Exception:
            pass

    def _save_keywords(self, keywords: list):
        """批量保存关键词到历史表"""
        now = format_datetime()
        for kw in keywords:
            if not kw or len(kw) < 2:
                continue
            try:
                existing = self.db_manager.fetch_one(
                    "SELECT id, usage_count FROM keyword_history WHERE keyword = ?", (kw,)
                )
                if existing:
                    self.db_manager.execute(
                        "UPDATE keyword_history SET usage_count = ?, last_used_at = ? WHERE id = ?",
                        (existing["usage_count"] + 1, now, existing["id"])
                    )
                else:
                    self.db_manager.insert("keyword_history", {
                        "keyword": kw, "last_used_at": now, "created_at": now,
                    })
            except Exception:
                pass
        self._load_keyword_history()

    def _show_keyword_history(self):
        """弹窗显示关键词使用历史"""
        try:
            rows = self.db_manager.fetch_all(
                "SELECT keyword, usage_count, last_used_at FROM keyword_history ORDER BY usage_count DESC LIMIT 50"
            )
            if not rows:
                QMessageBox.information(self, "关键词历史", "暂无历史记录")
                return
            info = "<h3>关键词使用历史 (按使用次数排序)</h3><table>"
            info += "<tr><th>关键词</th><th>次数</th><th>最近使用</th></tr>"
            for r in rows:
                info += f"<tr><td>{r['keyword']}</td><td align='center'>{r['usage_count']}</td><td>{r['last_used_at'][:16]}</td></tr>"
            info += "</table>"
            QMessageBox.information(self, "关键词历史", info)
        except Exception:
            pass

    def _save_results(self, results: list):
        try:
            now = format_datetime()
            for r in results:
                data = {
                    "title": r["title"],
                    "content": r["content"],
                    "content_type": r.get("content_type", ""),
                    "qualification_type": r.get("qualification_type", ""),
                    "source": r.get("source", "local_template"),
                    "created_at": now,
                    "updated_at": now,
                }
                self.db_manager.insert("contents", data)
            self.refresh_table()
        except Exception as e:
            logger.error(f"保存文案失败: {e}")

    def _edit_content(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if len(rows) != 1:
            return
        row = rows.pop()
        content_id = int(self.table.item(row, 0).text())
        content = self.db_manager.fetch_one("SELECT * FROM contents WHERE id = ?", (content_id,))
        if content:
            dialog = ContentDialog(self, content)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    self.db_manager.update("contents", {
                        "title": dialog.title_edit.text(),
                        "content": dialog.content_edit.toPlainText(),
                        "content_type": dialog.type_combo.currentText(),
                        "updated_at": format_datetime(),
                    }, "id = ?", (content_id,))
                    self.refresh_table()
                except Exception as e:
                    logger.error(f"更新文案失败: {e}")

    def _delete_content(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        try:
            for row in rows:
                cid = int(self.table.item(row, 0).text())
                self.db_manager.delete("contents", "id = ?", (cid,))
            self.refresh_table()
        except Exception as e:
            logger.error(f"删除文案失败: {e}")

    def _export_content(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出文案", f"contents_{format_datetime(fmt='%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        try:
            rows = self.db_manager.fetch_all(
                "SELECT title, content_type, qualification_type, content, keywords FROM contents WHERE status = 'approved'"
            )
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["title", "content_type", "qualification_type", "content", "keywords"])
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))
            QMessageBox.information(self, "导出完成", f"已导出到: {path}")
        except Exception as e:
            logger.error(f"导出失败: {e}")
