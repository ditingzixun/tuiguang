"""收录监控界面 - SEO收录检测、关键词排名监控"""
from datetime import datetime
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QGroupBox, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QTextEdit, QMessageBox, QHeaderView, QLabel,
    QListWidget, QListWidgetItem, QProgressBar, QDialog,
    QDialogButtonBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor
from db.models import SeoKeyword, SeoRanking
from core.seo_engine import seo_engine
from loguru import logger


class SeoCheckThread(QThread):
    """SEO检测后台线程"""
    progress = pyqtSignal(int, int)
    result = pyqtSignal(dict)
    finished_signal = pyqtSignal()

    def __init__(self, keywords, target_url, engine_name="baidu"):
        super().__init__()
        self.keywords = keywords
        self.target_url = target_url
        self.engine_name = engine_name

    def run(self):
        total = len(self.keywords)
        for i, kw in enumerate(self.keywords):
            result = seo_engine.check_keyword_rank(kw, self.target_url, self.engine_name)
            if result:
                self.result.emit(result)
            self.progress.emit(i + 1, total)
            import time
            time.sleep(2)  # 搜索间隔
        self.finished_signal.emit()


class MonitorManagerWidget(QWidget):
    """收录监控面板"""

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._check_thread = None
        self._setup_ui()
        self.refresh_all()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_check_index = QPushButton("🔍 检测收录")
        self.btn_check_index.clicked.connect(self._check_index)
        self.btn_check_rank = QPushButton("📈 关键词排名")
        self.btn_check_rank.clicked.connect(self._check_keyword_ranks)
        self.btn_add_keyword = QPushButton("➕ 添加关键词")
        self.btn_add_keyword.clicked.connect(self._add_keyword)
        self.btn_delete_keyword = QPushButton("🗑 删除关键词")
        self.btn_delete_keyword.clicked.connect(self._delete_keyword)
        self.btn_import_keywords = QPushButton("📥 导入关键词")
        self.btn_import_keywords.clicked.connect(self._import_keywords)
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.refresh_all)

        for btn in [self.btn_check_index, self.btn_check_rank, self.btn_add_keyword,
                     self.btn_delete_keyword, self.btn_import_keywords, self.btn_refresh]:
            toolbar.addWidget(btn)
        layout.addLayout(toolbar)

        # URL和引擎设置
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("目标URL:"))
        self.target_url_edit = QLineEdit()
        self.target_url_edit.setPlaceholderText("输入要检测的网站URL")
        config_layout.addWidget(self.target_url_edit)
        config_layout.addWidget(QLabel("搜索引擎:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["baidu", "360", "bing"])
        config_layout.addWidget(self.engine_combo)
        layout.addLayout(config_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：关键词列表
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("🔑 监控关键词"))
        self.keyword_list = QListWidget()
        left_layout.addWidget(self.keyword_list)
        splitter.addWidget(left)

        # 右侧：排名记录
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("📊 排名记录"))

        self.ranking_table = QTableWidget()
        self.ranking_table.setColumnCount(7)
        self.ranking_table.setHorizontalHeaderLabels([
            "ID", "关键词", "搜索引擎", "排名", "是否收录", "标题", "检测时间"
        ])
        self.ranking_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ranking_table.setAlternatingRowColors(True)
        self.ranking_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.ranking_table)

        splitter.addWidget(right)
        splitter.setSizes([250, 850])
        layout.addWidget(splitter)

    def refresh_all(self):
        self.refresh_keywords()
        self.refresh_rankings()

    def refresh_keywords(self):
        session = self.db_manager.get_session()
        try:
            self.keyword_list.clear()
            keywords = session.query(SeoKeyword).filter_by(status="active").all()
            for kw in keywords:
                item = QListWidgetItem(f"[{kw.search_engine}] {kw.keyword}")
                item.setData(Qt.ItemDataRole.UserRole, kw)
                self.keyword_list.addItem(item)
        except Exception as e:
            logger.error(f"刷新关键词异常: {e}")
        finally:
            session.close()

    def refresh_rankings(self):
        session = self.db_manager.get_session()
        try:
            rankings = session.query(SeoRanking).order_by(SeoRanking.check_time.desc()).limit(500).all()
            self.ranking_table.setRowCount(len(rankings))
            for row, r in enumerate(rankings):
                items = [
                    QTableWidgetItem(str(r.id)),
                    QTableWidgetItem(r.keyword or ""),
                    QTableWidgetItem(r.search_engine or ""),
                    QTableWidgetItem(str(r.rank) if r.rank else "-"),
                    QTableWidgetItem("✅ 已收录" if r.is_indexed else "❌ 未收录"),
                    QTableWidgetItem((r.title or "")[:60]),
                    QTableWidgetItem(r.check_time.strftime("%m-%d %H:%M") if r.check_time else "-"),
                ]
                for col, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if r.is_indexed:
                        if r.rank and r.rank <= 10:
                            item.setBackground(QColor(200, 255, 200))
                    self.ranking_table.setItem(row, col, item)
        except Exception as e:
            logger.error(f"刷新排名异常: {e}")
        finally:
            session.close()

    def _check_index(self):
        url = self.target_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入目标URL")
            return
        engine = self.engine_combo.currentText()
        result = seo_engine.check_index(url, search_engine=engine)
        if result:
            self._save_ranking_result(result)
            msg = f"{'✅ 已收录' if result['is_indexed'] else '❌ 未收录'}\n"
            msg += f"搜索引擎: {engine}\n"
            if result.get('title'):
                msg += f"标题: {result['title']}\n"
            if result.get('url'):
                msg += f"链接: {result['url']}"
            QMessageBox.information(self, "收录检测结果", msg)
        else:
            QMessageBox.warning(self, "检测失败", "搜索请求失败，请重试")

    def _check_keyword_ranks(self):
        target_url = self.target_url_edit.text().strip()
        if not target_url:
            QMessageBox.warning(self, "提示", "请输入目标URL")
            return

        keywords = []
        for i in range(self.keyword_list.count()):
            item = self.keyword_list.item(i)
            kw = item.data(Qt.ItemDataRole.UserRole)
            if kw:
                keywords.append(kw.keyword)

        if not keywords:
            QMessageBox.warning(self, "提示", "请先添加关键词")
            return

        self.progress_bar.setVisible(True)
        engine = self.engine_combo.currentText()
        self._check_thread = SeoCheckThread(keywords, target_url, engine)
        self._check_thread.progress.connect(lambda c, t: self.progress_bar.setValue(int(c / t * 100)))
        self._check_thread.result.connect(self._save_ranking_result)
        self._check_thread.finished_signal.connect(self._on_check_finished)
        self._check_thread.start()

    def _on_check_finished(self):
        self.progress_bar.setVisible(False)
        self.refresh_rankings()
        QMessageBox.information(self, "完成", "关键词排名检测完成")

    def _save_ranking_result(self, result: dict):
        session = self.db_manager.get_session()
        try:
            ranking = SeoRanking(
                keyword=result.get("keyword", result.get("query", "")),
                search_engine=result.get("search_engine", "baidu"),
                rank=result.get("rank"),
                url=result.get("url", ""),
                title=result.get("title", ""),
                is_indexed=result.get("is_indexed", False),
                check_time=result.get("check_time", datetime.now()),
            )
            session.add(ranking)
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def _add_keyword(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加关键词")
        layout = QFormLayout(dialog)
        kw_edit = QLineEdit()
        group_edit = QLineEdit()
        eng_combo = QComboBox()
        eng_combo.addItems(["baidu", "360", "bing"])
        layout.addRow("关键词:", kw_edit)
        layout.addRow("分组:", group_edit)
        layout.addRow("搜索引擎:", eng_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            keyword = kw_edit.text().strip()
            if not keyword:
                return
            session = self.db_manager.get_session()
            try:
                kw = SeoKeyword(
                    keyword=keyword,
                    group=group_edit.text().strip() or None,
                    search_engine=eng_combo.currentText(),
                )
                session.add(kw)
                session.commit()
                self.refresh_all()
            except Exception as e:
                session.rollback()
            finally:
                session.close()

    def _delete_keyword(self):
        items = self.keyword_list.selectedItems()
        if not items:
            return
        session = self.db_manager.get_session()
        try:
            for item in items:
                kw = item.data(Qt.ItemDataRole.UserRole)
                if kw:
                    session.query(SeoKeyword).filter_by(id=kw.id).delete()
            session.commit()
            self.refresh_all()
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def _import_keywords(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "导入关键词", "", "文本文件 (*.txt *.csv);;所有文件 (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            session = self.db_manager.get_session()
            count = 0
            engine = self.engine_combo.currentText()
            for line in lines:
                kw = line.strip()
                if kw and not kw.startswith("#"):
                    existing = session.query(SeoKeyword).filter_by(keyword=kw).first()
                    if not existing:
                        session.add(SeoKeyword(keyword=kw, search_engine=engine))
                        count += 1
            session.commit()
            self.refresh_all()
            QMessageBox.information(self, "导入完成", f"成功导入 {count} 个关键词")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {e}")
        finally:
            session.close()
