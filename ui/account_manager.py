"""账号管理界面 -- 批量导入/导出、分组管理、批量登录、异常标记、代理绑定"""
import csv
import logging
from utils.helpers import format_datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFormLayout, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QHeaderView, QLabel,
    QDialog, QDialogButtonBox, QProgressBar,
    QMenu, QTextEdit, QListWidget, QListWidgetItem, QCheckBox, QSplitter,
    QInputDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QAction

logger = logging.getLogger(__name__)
from core.proxy_engine import proxy_engine
from ui.styles.theme_manager import theme_manager


class AccountDialog(QDialog):
    """账号编辑对话框"""
    def __init__(self, parent=None, account=None, db_manager=None):
        super().__init__(parent)
        self.account = account
        self.db_manager = db_manager
        self.setWindowTitle("编辑账号" if account else "添加账号")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.platform_combo = QComboBox()
        self.platform_combo.setEditable(True)
        self.platform_combo.addItems([
            "huangye88", "qianyan", "zhongyewang", "zhihu",
            "baidu_tieba", "douban", "csdn", "jianshu", "custom"
        ])
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()

        # 分组选择
        self.group_combo = QComboBox()
        self.group_combo.addItem("不分组", None)
        if self.db_manager:
            try:
                groups = self.db_manager.fetch_all("SELECT id, name FROM account_groups ORDER BY id")
                for g in groups:
                    self.group_combo.addItem(g["name"], g["id"])
            except Exception:
                pass

        # 代理绑定下拉
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("不绑定(自动分配)", None)
        if self.db_manager:
            try:
                proxies = self.db_manager.fetch_all(
                    "SELECT id, host, port, protocol, status FROM proxies WHERE status = 'active'"
                )
                for p in proxies:
                    label = f"{p['protocol']}://{p['host']}:{p['port']} [{p['status']}]"
                    self.proxy_combo.addItem(label, p["id"])
            except Exception:
                pass  # 表可能尚未创建

        layout.addRow("平台:", self.platform_combo)
        layout.addRow("用户名:", self.username_edit)
        layout.addRow("密码:", self.password_edit)
        layout.addRow("手机号:", self.phone_edit)
        layout.addRow("邮箱:", self.email_edit)
        layout.addRow("分组:", self.group_combo)
        layout.addRow("绑定代理:", self.proxy_combo)

        if self.account:
            self.username_edit.setText(self.account.get("username", ""))
            self.password_edit.setText(self.account.get("password", ""))
            idx = self.platform_combo.findText(self.account.get("platform", ""))
            if idx >= 0:
                self.platform_combo.setCurrentIndex(idx)
            self.phone_edit.setText(self.account.get("phone", ""))
            self.email_edit.setText(self.account.get("email", ""))
            # 加载已有分组
            if self.account.get("group_id"):
                gidx = self.group_combo.findData(self.account["group_id"])
                if gidx >= 0:
                    self.group_combo.setCurrentIndex(gidx)
            # 加载已有代理绑定
            if self.db_manager:
                binding = self.db_manager.fetch_one(
                    "SELECT proxy_id FROM proxy_bindings WHERE account_id = ?",
                    (self.account["id"],)
                )
                if binding:
                    pidx = self.proxy_combo.findData(binding["proxy_id"])
                    if pidx >= 0:
                        self.proxy_combo.setCurrentIndex(pidx)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        data = {
            "platform": self.platform_combo.currentText(),
            "username": self.username_edit.text(),
            "password": self.password_edit.text(),
            "phone": self.phone_edit.text(),
            "email": self.email_edit.text(),
            "group_id": self.group_combo.currentData(),
            "proxy_id": self.proxy_combo.currentData(),
        }
        if self.account:
            data["id"] = self.account["id"]
        return data


class GroupManageDialog(QDialog):
    """分组管理对话框"""
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("账号分组管理")
        self.setMinimumSize(450, 400)
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 新增分组
        add_layout = QHBoxLayout()
        self.group_name_edit = QLineEdit()
        self.group_name_edit.setPlaceholderText("分组名称，如: 杭州区、高权重号")
        self.group_desc_edit = QLineEdit()
        self.group_desc_edit.setPlaceholderText("备注(可选)")
        self.btn_add_group = QPushButton("添加分组")
        self.btn_add_group.clicked.connect(self._add_group)
        add_layout.addWidget(self.group_name_edit)
        add_layout.addWidget(self.group_desc_edit)
        add_layout.addWidget(self.btn_add_group)
        layout.addLayout(add_layout)

        # 分组列表
        self.group_list = QListWidget()
        layout.addWidget(self.group_list)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.btn_delete_group = QPushButton("删除选中分组")
        self.btn_delete_group.clicked.connect(self._delete_group)
        self.btn_rename_group = QPushButton("重命名")
        self.btn_rename_group.clicked.connect(self._rename_group)
        btn_layout.addWidget(self.btn_delete_group)
        btn_layout.addWidget(self.btn_rename_group)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _refresh_list(self):
        self.group_list.clear()
        if not self.db_manager:
            return
        groups = self.db_manager.fetch_all("""
            SELECT g.*, COUNT(a.id) as cnt
            FROM account_groups g
            LEFT JOIN accounts a ON a.group_id = g.id
            GROUP BY g.id
            ORDER BY g.id
        """)
        for g in groups:
            item = QListWidgetItem(f"{g['name']} ({g['cnt']}个账号)")
            item.setData(Qt.ItemDataRole.UserRole, g["id"])
            self.group_list.addItem(item)

    def _add_group(self):
        name = self.group_name_edit.text().strip()
        if not name:
            return
        try:
            existing = self.db_manager.fetch_one("SELECT id FROM account_groups WHERE name = ?", (name,))
            if existing:
                QMessageBox.warning(self, "提示", "该分组已存在")
                return
            now = format_datetime()
            self.db_manager.insert("account_groups", {
                "name": name,
                "description": self.group_desc_edit.text().strip(),
                "created_at": now,
            })
            self.group_name_edit.clear()
            self.group_desc_edit.clear()
            self._refresh_list()
        except Exception as e:
            logger.error(f"添加分组失败: {e}")

    def _delete_group(self):
        item = self.group_list.currentItem()
        if not item:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        self.db_manager.execute("UPDATE accounts SET group_id = NULL WHERE group_id = ?", (gid,))
        self.db_manager.delete("account_groups", "id = ?", (gid,))
        self._refresh_list()

    def _rename_group(self):
        item = self.group_list.currentItem()
        if not item:
            return
        gid = item.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(self, "重命名分组", "新名称:", text=item.text().split(" (")[0])
        if ok and new_name.strip():
            self.db_manager.update("account_groups", {"name": new_name.strip()}, "id = ?", (gid,))
            self._refresh_list()


class AnomalyDialog(QDialog):
    """账号异常标记对话框"""
    def __init__(self, parent=None, account_ids=None, db_manager=None):
        super().__init__(parent)
        self.account_ids = account_ids or []
        self.db_manager = db_manager
        self.setWindowTitle(f"异常标记 - {len(self.account_ids)}个账号")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"对 {len(self.account_ids)} 个选中账号进行异常标记:"))

        self.anomaly_type = QComboBox()
        self.anomaly_type.addItems([
            "login_failed (登录失败)",
            "captcha_required (需验证码)",
            "phone_verify (需手机验证)",
            "content_rejected (内容被拒)",
            "rate_limited (频率限制)",
            "account_warning (账号警告)",
            "shadow_ban (疑似限流/禁言)",
            "custom (自定义)",
        ])
        layout.addWidget(QLabel("异常类型:"))
        layout.addWidget(self.anomaly_type)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText("异常描述（可选）...")
        self.reason_edit.setMaximumHeight(100)
        layout.addWidget(QLabel("备注:"))
        layout.addWidget(self.reason_edit)

        self.change_status = QCheckBox("同时将账号状态改为 [limited]")
        self.change_status.setChecked(True)
        layout.addWidget(self.change_status)

        self.change_score = QCheckBox("扣减账号评分 (-20)")
        layout.addWidget(self.change_score)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self):
        atype = self.anomaly_type.currentText().split(" (")[0]
        reason = self.reason_edit.toPlainText().strip()
        now = format_datetime()

        for aid in self.account_ids:
            # 插入异常记录
            self.db_manager.insert("anomaly_records", {
                "account_id": aid,
                "anomaly_type": atype,
                "description": reason,
                "created_at": now,
            })
            # 更新账号
            updates = {"anomaly_reason": reason, "updated_at": now}
            if self.change_status.isChecked():
                updates["status"] = "limited"
            if self.change_score.isChecked():
                current = self.db_manager.fetch_one("SELECT score FROM accounts WHERE id = ?", (aid,))
                if current:
                    updates["score"] = max(0, current["score"] - 20)
            self.db_manager.update("accounts", updates, "id = ?", (aid,))


class BatchLoginThread(QThread):
    """批量登录后台线程"""
    progress = pyqtSignal(int, str)  # current_index, status_text
    finished_signal = pyqtSignal(dict)  # results summary

    def __init__(self, account_ids, db_manager):
        super().__init__()
        self.account_ids = account_ids
        self.db_manager = db_manager

    def run(self):
        from core.event_loop import event_loop as ev_loop
        from core.browser_engine import browser_engine
        from plugins.base_plugin import plugin_manager

        result = {"success": 0, "failed": 0, "details": []}
        total = len(self.account_ids)

        for i, aid in enumerate(self.account_ids):
            account = self.db_manager.fetch_one("SELECT * FROM accounts WHERE id = ?", (aid,))
            if not account:
                continue

            self.progress.emit(i + 1, f"({i+1}/{total}) 正在登录: [{account['platform']}] {account['username']}...")

            try:
                async def do_login():
                    plugin_cls = plugin_manager.get_plugin(account["platform"])
                    if not plugin_cls:
                        return False, "未找到平台插件"

                    context = await browser_engine.get_context(account["id"], account["platform"])
                    plugin = plugin_cls(dict(account), context)
                    await plugin.init()
                    success = await plugin.login()
                    if success:
                        await browser_engine.save_account_cookies(account["id"])
                    await plugin.close()
                    return success, "登录成功" if success else "登录失败"

                success, msg = ev_loop.run(do_login())
            except Exception as e:
                success, msg = False, str(e)

            now = format_datetime()
            if success:
                self.db_manager.update("accounts", {
                    "login_status": "success",
                    "last_login_at": now,
                    "status": "active",
                    "updated_at": now,
                }, "id = ?", (aid,))
                result["success"] += 1
            else:
                self.db_manager.update("accounts", {
                    "login_status": "failed",
                    "last_login_at": now,
                    "updated_at": now,
                }, "id = ?", (aid,))
                result["failed"] += 1
                self.db_manager.insert("anomaly_records", {
                    "account_id": aid,
                    "anomaly_type": "login_failed",
                    "description": msg[:500],
                    "created_at": now,
                })

            result["details"].append({
                "id": aid,
                "username": account["username"],
                "platform": account["platform"],
                "success": success,
                "message": msg,
            })

        self.finished_signal.emit(result)


class AccountManagerWidget(QWidget):
    """账号管理面板"""
    status_changed = pyqtSignal()

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self._groups_dirty = True
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("添加账号")
        self.btn_add.clicked.connect(self._add_account)
        self.btn_import = QPushButton("批量导入CSV")
        self.btn_import.clicked.connect(self._import_accounts)
        self.btn_template = QPushButton("下载CSV模板")
        self.btn_template.clicked.connect(self._download_csv_template)
        self.btn_batch_login = QPushButton("批量登录")
        self.btn_batch_login.clicked.connect(self._batch_login)
        self.btn_anomaly = QPushButton("异常标记")
        self.btn_anomaly.clicked.connect(self._mark_anomaly)
        self.btn_groups = QPushButton("分组管理")
        self.btn_groups.clicked.connect(self._manage_groups)
        self.btn_edit = QPushButton("编辑")
        self.btn_edit.setToolTip("编辑选中账号 — 双击表格行也可编辑")
        self.btn_edit.clicked.connect(self._edit_account)
        self.btn_export = QPushButton("导出CSV")
        self.btn_export.clicked.connect(self._export_accounts)
        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self.refresh_table)

        for btn in [self.btn_add, self.btn_edit, self.btn_import, self.btn_template,
                     self.btn_batch_login, self.btn_anomaly, self.btn_groups,
                     self.btn_export, self.btn_delete, self.btn_refresh]:
            toolbar.addWidget(btn)
        layout.addLayout(toolbar)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("状态筛选:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "active", "limited", "banned", "login_failed"])
        self.status_filter.currentIndexChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(QLabel("分组筛选:"))
        self.group_filter = QComboBox()
        self.group_filter.currentIndexChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.group_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "平台", "用户名", "分组", "手机号",
            "状态", "评分", "登录状态", "异常原因", "最后登录"
        ])
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.cellDoubleClicked.connect(self._edit_account)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # 设置各列合理初始宽度
        col_widths = [40, 100, 120, 80, 110, 50, 50, 70, 120, 130]
        for i, w in enumerate(col_widths):
            self.table.setColumnWidth(i, w)
        layout.addWidget(self.table)

        self.stats_label = QLabel("共 0 个账号 | 活跃: 0 | 受限: 0 | 封禁: 0")
        layout.addWidget(self.stats_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def refresh_table(self, _=None):
        self._update_group_filter()
        try:
            status = self.status_filter.currentText()
            group_id = self.group_filter.currentData()

            sql = "SELECT a.*, g.name as group_name FROM accounts a LEFT JOIN account_groups g ON a.group_id = g.id WHERE 1=1"
            params = []

            if status == "active":
                sql += " AND a.status = 'active'"
            elif status == "limited":
                sql += " AND a.status = 'limited'"
            elif status == "banned":
                sql += " AND a.status = 'banned'"
            elif status == "login_failed":
                sql += " AND a.login_status = 'failed'"

            if group_id is not None:
                sql += " AND a.group_id = ?"
                params.append(group_id)

            sql += " ORDER BY a.id DESC"
            rows = self.db_manager.fetch_all(sql, tuple(params))

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                items = [
                    QTableWidgetItem(str(row["id"])),
                    QTableWidgetItem(row["platform"]),
                    QTableWidgetItem(row["username"]),
                    QTableWidgetItem(row["group_name"] or "-"),
                    QTableWidgetItem(row["phone"] or ""),
                    QTableWidgetItem(row["status"]),
                    QTableWidgetItem(str(row["score"] if row["score"] is not None else 100)),
                    QTableWidgetItem(row["login_status"]),
                    QTableWidgetItem((row["anomaly_reason"] or "")[:40]),
                    QTableWidgetItem(row["last_login_at"] or "-"),
                ]
                for c, item in enumerate(items):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if row["status"] == "banned":
                        item.setBackground(QColor(theme_manager.get_color("row_banned", "#ffc8c8")))
                    elif row["status"] == "limited":
                        item.setBackground(QColor(theme_manager.get_color("row_limited", "#ffffc8")))
                    elif row["login_status"] == "failed":
                        item.setBackground(QColor(theme_manager.get_color("row_failed_login", "#ffe6c8")))
                    self.table.setItem(r, c, item)

            s_active = s_limited = s_banned = s_login_failed = 0
            for row in rows:
                if row["status"] == "active":
                    s_active += 1
                elif row["status"] == "limited":
                    s_limited += 1
                elif row["status"] == "banned":
                    s_banned += 1
                if row["login_status"] == "failed":
                    s_login_failed += 1
            self.stats_label.setText(
                f"共 {len(rows)} 个账号 | 活跃: {s_active} | "
                f"受限: {s_limited} | 封禁: {s_banned} | 登录失败: {s_login_failed}"
            )
        except Exception as e:
            logger.error(f"刷新账号列表异常: {e}")

    def _update_group_filter(self):
        current = self.group_filter.currentData()
        self.group_filter.blockSignals(True)
        self.group_filter.clear()
        self.group_filter.addItem("全部分组", None)
        if self._groups_dirty:
            try:
                groups = self.db_manager.fetch_all("SELECT id, name FROM account_groups ORDER BY id")
                self._cached_groups = groups
                self._groups_dirty = False
            except Exception:
                self._cached_groups = []
        for g in self._cached_groups:
            self.group_filter.addItem(g["name"], g["id"])
        idx = self.group_filter.findData(current)
        if idx >= 0:
            self.group_filter.setCurrentIndex(idx)
        self.group_filter.blockSignals(False)

    def _add_account(self):
        dialog = AccountDialog(self, db_manager=self.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_account(dialog.get_data(), is_new=True)

    def _edit_account(self, *args):
        rows = set(item.row() for item in self.table.selectedItems())
        if len(rows) != 1:
            QMessageBox.warning(self, "提示", "请选择一条账号记录进行编辑")
            return
        account_id = int(self.table.item(rows.pop(), 0).text())
        account = self.db_manager.fetch_one("SELECT * FROM accounts WHERE id = ?", (account_id,))
        if not account:
            QMessageBox.warning(self, "提示", "账号不存在")
            return
        dialog = AccountDialog(self, account=dict(account), db_manager=self.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_account(dialog.get_data(), is_new=False)

    def _save_account(self, data, is_new=True):
        proxy_id = data.pop("proxy_id", None)
        group_id = data.pop("group_id", None)
        account_id = data.pop("id", None)
        try:
            now = format_datetime()
            if group_id is not None:
                data["group_id"] = group_id
            data["updated_at"] = now

            if is_new:
                data["created_at"] = now
                account_id = self.db_manager.insert("accounts", data)
            else:
                self.db_manager.update("accounts", data, "id = ?", (account_id,))

            if proxy_id is not None:
                proxy_engine.bind_proxy(account_id, proxy_id)
            self.refresh_table()
            self.status_changed.emit()
        except Exception as e:
            logger.error(f"保存账号失败: {e}")
            QMessageBox.critical(self, "错误", f"保存账号失败: {e}")

    def _import_accounts(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入账号", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if not path:
            return
        try:
            count = 0
            skipped = 0
            now = format_datetime()
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("platform") or not row.get("username"):
                        skipped += 1
                        continue
                    # 解析分组
                    group_id = None
                    group_name = row.get("group", "").strip()
                    if group_name:
                        g = self.db_manager.fetch_one(
                            "SELECT id FROM account_groups WHERE name = ?", (group_name,)
                        )
                        if not g:
                            gid = self.db_manager.insert("account_groups", {
                                "name": group_name, "created_at": now,
                            })
                            group_id = gid
                        else:
                            group_id = g["id"]

                    data = {
                        "platform": row["platform"].strip(),
                        "username": row["username"].strip(),
                        "password": row.get("password", "").strip(),
                        "phone": row.get("phone", "").strip(),
                        "email": row.get("email", "").strip(),
                        "group_id": group_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                    existing = self.db_manager.fetch_one(
                        "SELECT id FROM accounts WHERE platform = ? AND username = ?",
                        (data["platform"], data["username"])
                    )
                    if not existing:
                        self.db_manager.insert("accounts", data)
                        count += 1
                    else:
                        skipped += 1
            self._groups_dirty = True
            self.refresh_table()
            msg = f"成功导入 {count} 个账号"
            if skipped:
                msg += f"，跳过 {skipped} 个（重复或无关键字段）"
            QMessageBox.information(self, "导入完成", msg)
        except Exception as e:
            logger.error(f"导入失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败: {e}")

    def _download_csv_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存CSV模板", "account_template.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["platform", "username", "password", "phone", "email", "group"])
                writer.writerow(["huangye88", "account01", "pass123", "13800000001", "test@example.com", "杭州区"])
                writer.writerow(["qianyan", "account02", "pass456", "13800000002", "", "高权重号"])
                writer.writerow(["zhihu", "account03", "pass789", "", "", ""])
            QMessageBox.information(self, "模板已保存", f"CSV模板已保存到:\n{path}")
        except Exception as e:
            logger.error(f"保存模板失败: {e}")

    def _delete_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除选中的 {len(rows)} 个账号吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for row in rows:
                    acc_id = int(self.table.item(row, 0).text())
                    self.db_manager.delete("accounts", "id = ?", (acc_id,))
                self.refresh_table()
            except Exception as e:
                logger.error(f"删除失败: {e}")

    def _export_accounts(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出账号", f"accounts_{format_datetime(fmt='%Y%m%d')}.csv",
            "CSV文件 (*.csv)"
        )
        if not path:
            return
        try:
            rows = self.db_manager.fetch_all("""
                SELECT a.platform, a.username, a.password, a.phone, a.email,
                       a.status, a.login_status, a.score,
                       g.name as group_name,
                       p.host as proxy_host, p.port as proxy_port,
                       a.last_login_at, a.anomaly_reason, a.created_at
                FROM accounts a
                LEFT JOIN account_groups g ON a.group_id = g.id
                LEFT JOIN proxy_bindings pb ON a.id = pb.account_id
                LEFT JOIN proxies p ON pb.proxy_id = p.id
                ORDER BY a.id
            """)
            fieldnames = ["platform", "username", "password", "phone", "email",
                          "status", "login_status", "score", "group", "proxy",
                          "last_login_at", "anomaly_reason", "created_at"]
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    d = dict(row)
                    d["group"] = d.get("group_name", "") or ""
                    d["proxy"] = f"{d.get('proxy_host', '')}:{d.get('proxy_port', '')}" if d.get("proxy_host") else ""
                    writer.writerow(d)
            QMessageBox.information(self, "导出完成", f"已导出 {len(rows)} 个账号到:\n{path}")
        except Exception as e:
            logger.error(f"导出失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

    def _batch_login(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择要登录的账号")
            return

        account_ids = [int(self.table.item(row, 0).text()) for row in rows]
        reply = QMessageBox.question(
            self, "确认批量登录",
            f"将对 {len(account_ids)} 个选中账号执行批量登录，可能需要几分钟。\n"
            f"请确保系统已配置代理IP池（如需代理）。\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.progress_bar.setMaximum(len(account_ids))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.stats_label.setText("正在批量登录...")
        self.btn_batch_login.setEnabled(False)
        QApplication.processEvents()

        self._login_thread = BatchLoginThread(account_ids, self.db_manager)
        self._login_thread.progress.connect(self._on_batch_login_progress)
        self._login_thread.finished_signal.connect(self._on_batch_login_finished)
        self._login_thread.start()

    def _on_batch_login_progress(self, current, text):
        self.progress_bar.setValue(current)
        self.stats_label.setText(text)

    def _on_batch_login_finished(self, result):
        self.progress_bar.setVisible(False)
        self.btn_batch_login.setEnabled(True)
        self.refresh_table()
        QMessageBox.information(
            self, "批量登录完成",
            f"成功: {result['success']} | 失败: {result['failed']}\n"
            f"共 {result['success'] + result['failed']} 个账号"
        )

    def _mark_anomaly(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择需要标记异常的账号")
            return
        account_ids = [int(self.table.item(row, 0).text()) for row in rows]
        dialog = AnomalyDialog(self, account_ids=account_ids, db_manager=self.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply()
            self.refresh_table()
            self.status_changed.emit()

    def _manage_groups(self):
        dialog = GroupManageDialog(self, db_manager=self.db_manager)
        dialog.exec()
        self._groups_dirty = True
        self.refresh_table()

    def _context_menu(self, pos):
        menu = QMenu(self)
        # 查看详情
        detail_action = QAction("查看账号详情", self)
        detail_action.triggered.connect(self._show_detail)
        menu.addAction(detail_action)

        edit_action = QAction("编辑账号", self)
        edit_action.triggered.connect(self._edit_account)
        menu.addAction(edit_action)
        menu.addSeparator()

        # 状态切换
        set_active = QAction("标记为活跃", self)
        set_active.triggered.connect(lambda: self._batch_set_status("active"))
        menu.addAction(set_active)

        set_limited = QAction("标记为受限", self)
        set_limited.triggered.connect(lambda: self._batch_set_status("limited"))
        menu.addAction(set_limited)

        set_banned = QAction("标记为封禁", self)
        set_banned.triggered.connect(lambda: self._batch_set_status("banned"))
        menu.addAction(set_banned)

        menu.addSeparator()

        # 代理操作
        bind_proxy = QAction("绑定代理...", self)
        bind_proxy.triggered.connect(self._bind_proxy_menu)
        menu.addAction(bind_proxy)

        unbind_proxy = QAction("解除代理绑定", self)
        unbind_proxy.triggered.connect(self._unbind_proxy_menu)
        menu.addAction(unbind_proxy)

        menu.addSeparator()

        # 移动到分组
        move_group_menu = QMenu("移动到分组", self)
        try:
            groups = self.db_manager.fetch_all("SELECT id, name FROM account_groups ORDER BY id")
            for g in groups:
                action = QAction(g["name"], self)
                action.triggered.connect(lambda checked, gid=g["id"]: self._move_to_group(gid))
                move_group_menu.addAction(action)
        except Exception:
            pass
        ungroup_action = QAction("取消分组", self)
        ungroup_action.triggered.connect(lambda: self._move_to_group(None))
        move_group_menu.addAction(ungroup_action)
        menu.addMenu(move_group_menu)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _show_detail(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if len(rows) != 1:
            return
        aid = int(self.table.item(rows.pop(), 0).text())
        account = self.db_manager.fetch_one("""
            SELECT a.*, g.name as group_name
            FROM accounts a LEFT JOIN account_groups g ON a.group_id = g.id
            WHERE a.id = ?
        """, (aid,))
        if not account:
            return

        anomalies = self.db_manager.fetch_all(
            "SELECT * FROM anomaly_records WHERE account_id = ? ORDER BY created_at DESC LIMIT 10",
            (aid,)
        )
        publishes = self.db_manager.fetch_all(
            "SELECT platform, title, status, publish_time FROM publish_records WHERE account_id = ? ORDER BY created_at DESC LIMIT 10",
            (aid,)
        )

        info = (
            f"<h3>账号 #{account['id']} 详情</h3>"
            f"<table>"
            f"<tr><td>平台:</td><td>{account['platform']}</td></tr>"
            f"<tr><td>用户名:</td><td>{account['username']}</td></tr>"
            f"<tr><td>手机:</td><td>{account['phone'] or '-'}</td></tr>"
            f"<tr><td>邮箱:</td><td>{account['email'] or '-'}</td></tr>"
            f"<tr><td>分组:</td><td>{account['group_name'] or '-'}</td></tr>"
            f"<tr><td>状态:</td><td>{account['status'] or '-'}</td></tr>"
            f"<tr><td>评分:</td><td>{account['score'] if account['score'] is not None else 100}</td></tr>"
            f"<tr><td>登录状态:</td><td>{account['login_status'] or '-'}</td></tr>"
            f"<tr><td>最后登录:</td><td>{account['last_login_at'] or '-'}</td></tr>"
            f"<tr><td>异常原因:</td><td>{account['anomaly_reason'] or '-'}</td></tr>"
            f"</table>"
        )

        if anomalies:
            info += "<h4>异常记录 (最近10条):</h4><ul>"
            for a in anomalies:
                info += f"<li>[{a['anomaly_type']}] {a['description'][:60]} ({a['created_at']})</li>"
            info += "</ul>"

        if publishes:
            info += "<h4>发布记录 (最近10条):</h4><ul>"
            for p in publishes:
                info += f"<li>[{p['status']}] [{p['platform']}] {p['title'][:40]} ({p['publish_time'] or '-'})</li>"
            info += "</ul>"

        QMessageBox.information(self, "账号详情", info)

    def _batch_set_status(self, status: str):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        now = format_datetime()
        for row in rows:
            aid = int(self.table.item(row, 0).text())
            self.db_manager.update("accounts", {"status": status, "updated_at": now}, "id = ?", (aid,))
        self.refresh_table()
        self.status_changed.emit()

    def _move_to_group(self, group_id):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        now = format_datetime()
        for row in rows:
            aid = int(self.table.item(row, 0).text())
            self.db_manager.update("accounts", {"group_id": group_id, "updated_at": now}, "id = ?", (aid,))
        self.refresh_table()

    def _bind_proxy_menu(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        proxies = self.db_manager.fetch_all("SELECT id, host, port, protocol FROM proxies WHERE status = 'active'")
        if not proxies:
            QMessageBox.warning(self, "提示", "没有可用的代理IP，请先在代理IP池中获取代理")
            return

        items = [f"{p['protocol']}://{p['host']}:{p['port']}" for p in proxies]
        item, ok = QInputDialog.getItem(self, "选择代理", "选择要绑定的代理IP:", items, 0, False)
        if ok and item:
            idx = items.index(item)
            pid = proxies[idx]["id"]
            for row in rows:
                aid = int(self.table.item(row, 0).text())
                proxy_engine.bind_proxy(aid, pid)
            self.refresh_table()

    def _unbind_proxy_menu(self):
        rows = set(item.row() for item in self.table.selectedItems())
        for row in rows:
            aid = int(self.table.item(row, 0).text())
            proxy_engine.unbind_proxy(aid)
        self.refresh_table()
