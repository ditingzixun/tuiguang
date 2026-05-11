"""文案生成界面 - 对接大模型API批量生成、伪原创"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QTextEdit, QMessageBox, QHeaderView, QLabel,
    QDialog, QDialogButtonBox, QCheckBox, QListWidget,
    QListWidgetItem, QProgressBar, QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from db.models import Content
from core.ai_engine import ai_engine
from loguru import logger


class GenerateThread(QThread):
    """后台生成线程"""
    progress = pyqtSignal(int, int)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            results = []
            qual_types = self.params["qual_types"]
            content_types = self.params["content_types"]
            count = self.params["count"]
            company = self.params.get("company_name", "")
            total = len(qual_types) * len(content_types) * count
            current = 0

            for qt in qual_types:
                for ct in content_types:
                    for i in range(count):
                        result = ai_engine.generate(qt, ct, company_name=company)
                        if result:
                            results.append(result)
                        current += 1
                        self.progress.emit(current, total)

            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))


class ContentDialog(QDialog):
    """文案详情/编辑"""
    def __init__(self, parent=None, content=None):
        super().__init__(parent)
        self.content = content
        self.setWindowTitle("文案详情")
        self.setMinimumSize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题")
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
            self.title_edit.setText(self.content.title)
            self.content_edit.setText(self.content.content)
            idx = self.type_combo.findText(self.content.content_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class ContentGeneratorWidget(QWidget):
    """文案生成面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._generate_thread = None
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 左侧设置面板 + 右侧列表
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧设置
        left = QWidget()
        left_layout = QVBoxLayout(left)

        # 资质类型选择
        qual_group = QGroupBox("资质类型(多选)")
        qual_layout = QVBoxLayout(qual_group)
        self.qual_list = QListWidget()
        self.qual_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
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

        # 文案类型选择
        type_group = QGroupBox("文案类型(多选)")
        type_layout = QVBoxLayout(type_group)
        self.type_list = QListWidget()
        self.type_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        content_types = ["soft_article", "science_article", "comparison_article", "policy_article", "case_study"]
        type_names = ["软文推广", "科普文章", "对比分析", "政策解读", "案例分享"]
        for ct, cn in zip(content_types, type_names):
            item = QListWidgetItem(cn)
            item.setData(Qt.ItemDataRole.UserRole, ct)
            item.setSelected(True)
            self.type_list.addItem(item)
        type_layout.addWidget(self.type_list)
        left_layout.addWidget(type_group)

        # 生成设置
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

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("🤖 AI批量生成")
        self.btn_generate.clicked.connect(self._start_generate)
        btn_layout.addWidget(self.btn_generate)
        self.btn_spin = QPushButton("🔄 伪原创")
        self.btn_spin.clicked.connect(self._spin_selected)
        btn_layout.addWidget(self.btn_spin)
        left_layout.addLayout(btn_layout)

        # 进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("")
        left_layout.addWidget(self.progress_label)

        splitter.addWidget(left)

        # 右侧文案列表
        right = QWidget()
        right_layout = QVBoxLayout(right)

        list_toolbar = QHBoxLayout()
        self.btn_edit = QPushButton("📝 编辑")
        self.btn_edit.clicked.connect(self._edit_content)
        self.btn_delete = QPushButton("🗑 删除")
        self.btn_delete.clicked.connect(self._delete_content)
        self.btn_export = QPushButton("📤 导出")
        self.btn_export.clicked.connect(self._export_content)
        self.btn_save = QPushButton("💾 保存选中")
        self.btn_save.clicked.connect(self._save_to_db)
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.refresh_table)

        for btn in [self.btn_edit, self.btn_delete, self.btn_export, self.btn_save, self.btn_refresh]:
            list_toolbar.addWidget(btn)
        right_layout.addLayout(list_toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "标题", "类型", "资质类型", "来源", "使用次数"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.table)

        splitter.addWidget(right)
        splitter.setSizes([350, 750])
        layout.addWidget(splitter)

    def refresh_table(self):
        session = self.db_manager.get_session()
        try:
            contents = session.query(Content).order_by(Content.created_at.desc()).limit(200).all()
            self.table.setRowCount(len(contents))
            for row, c in enumerate(contents):
                items = [
                    QTableWidgetItem(str(c.id)),
                    QTableWidgetItem(c.title[:60]),
                    QTableWidgetItem(c.content_type),
                    QTableWidgetItem(c.qualification_type or ""),
                    QTableWidgetItem(c.source),
                    QTableWidgetItem(str(c.used_count)),
                ]
                for col, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, col, item)
        except Exception as e:
            logger.error(f"刷新文案列表异常: {e}")
        finally:
            session.close()

    def _start_generate(self):
        selected_qual = [item.text() for item in self.qual_list.selectedItems()]
        selected_types = [item.data(Qt.ItemDataRole.UserRole) for item in self.type_list.selectedItems()]

        if not selected_qual or not selected_types:
            QMessageBox.warning(self, "提示", "请选择资质类型和文案类型")
            return

        # 检查API配置
        if not ai_engine.api_key:
            reply = QMessageBox.question(
                self, "未配置API", "未检测到AI API Key，将使用本地模板生成。\n是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_generate.setEnabled(False)

        params = {
            "qual_types": selected_qual,
            "content_types": selected_types,
            "count": self.count_spin.value(),
            "company_name": self.company_edit.text(),
        }

        self._generate_thread = GenerateThread(params)
        self._generate_thread.progress.connect(self._on_progress)
        self._generate_thread.finished_signal.connect(self._on_generate_finished)
        self._generate_thread.error_signal.connect(self._on_generate_error)
        self._generate_thread.start()

    def _on_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"生成中... {current}/{total}")

    def _on_generate_finished(self, results):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"生成完成! 共 {len(results)} 篇")
        self.btn_generate.setEnabled(True)
        self._save_results(results)

    def _on_generate_error(self, error):
        self.progress_bar.setVisible(False)
        self.btn_generate.setEnabled(True)
        QMessageBox.critical(self, "错误", f"生成失败: {error}")

    def _save_results(self, results: list):
        session = self.db_manager.get_session()
        try:
            for r in results:
                content = Content(
                    title=r["title"],
                    content=r["content"],
                    content_type=r.get("content_type", ""),
                    qualification_type=r.get("qualification_type", ""),
                    source=r.get("source", "ai"),
                )
                session.add(content)
            session.commit()
            self.refresh_table()
        except Exception as e:
            session.rollback()
            logger.error(f"保存文案失败: {e}")
        finally:
            session.close()

    def _spin_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择要伪原创的文案")
            return
        session = self.db_manager.get_session()
        try:
            for row in rows:
                content_id = int(self.table.item(row, 0).text())
                original = session.query(Content).filter_by(id=content_id).first()
                if original:
                    spun = ai_engine.spin_content(original.content)
                    new_content = Content(
                        title=f"[伪] {original.title}",
                        content=spun,
                        content_type=original.content_type,
                        qualification_type=original.qualification_type,
                        source="spin",
                        original_content_id=original.id,
                    )
                    session.add(new_content)
            session.commit()
            self.refresh_table()
            QMessageBox.information(self, "完成", f"伪原创处理 {len(rows)} 篇文案")
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def _edit_content(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if len(rows) != 1:
            return
        row = rows.pop()
        content_id = int(self.table.item(row, 0).text())
        session = self.db_manager.get_session()
        c = session.query(Content).filter_by(id=content_id).first()
        session.close()
        if c:
            dialog = ContentDialog(self, c)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                session = self.db_manager.get_session()
                try:
                    c = session.query(Content).filter_by(id=content_id).first()
                    c.title = dialog.title_edit.text()
                    c.content = dialog.content_edit.toPlainText()
                    c.content_type = dialog.type_combo.currentText()
                    session.commit()
                    self.refresh_table()
                except Exception as e:
                    session.rollback()
                finally:
                    session.close()

    def _delete_content(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        session = self.db_manager.get_session()
        try:
            for row in rows:
                cid = int(self.table.item(row, 0).text())
                session.query(Content).filter_by(id=cid).delete()
            session.commit()
            self.refresh_table()
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def _export_content(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出文案", f"contents_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["标题", "类型", "资质类型", "内容", "关键词"])
        session = self.db_manager.get_session()
        for c in session.query(Content).filter(Content.status == "approved").all():
            ws.append([c.title, c.content_type, c.qualification_type, c.content, c.keywords])
        wb.save(path)
        session.close()
        QMessageBox.information(self, "导出完成", f"已导出到: {path}")

    def _save_to_db(self):
        QMessageBox.information(self, "提示", "选中文案已保存到文案库")
