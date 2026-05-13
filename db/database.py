"""数据库管理器 — raw sqlite3 + WAL模式"""
import os
import sqlite3
import threading

import logging

logger = logging.getLogger(__name__)
from .schema import TABLE_SQL, get_create_order
from utils.helpers import format_datetime


class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.db_path = db_path or "./data/qualification_bot.db"
        self._local = threading.local()

    def init_db(self, db_path: str = None):
        if db_path:
            self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = self.get_connection()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        self._create_tables(conn)
        conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def _create_tables(self, conn):
        for table_name in get_create_order():
            sql = TABLE_SQL.get(table_name)
            if sql:
                conn.execute(sql)
                logger.debug(f"表已就绪: {table_name}")
        self._migrate(conn)

    def _migrate(self, conn):
        """增量迁移：向已有表安全添加新列"""
        migrations = [
            # 账号分组 (新增于2026-05)
            "ALTER TABLE accounts ADD COLUMN group_id INTEGER DEFAULT NULL REFERENCES account_groups(id)",
            "ALTER TABLE accounts ADD COLUMN anomaly_reason TEXT DEFAULT ''",
            "ALTER TABLE tasks ADD COLUMN image_paths TEXT DEFAULT '[]'",
        ]
        for sql in migrations:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # 列已存在则忽略

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            abs_path = os.path.abspath(self.db_path)
            conn = sqlite3.connect(abs_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn = conn
        return self._local.conn

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # ---------- 便捷查询方法 ----------

    def fetch_all(self, sql: str, params: tuple = ()) -> list:
        conn = self.get_connection()
        cur = conn.execute(sql, params)
        return cur.fetchall()

    def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        conn = self.get_connection()
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        conn = self.get_connection()
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid

    def insert(self, table: str, data: dict) -> int:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(sql, tuple(data.values()))

    def update(self, table: str, data: dict, where: str, where_params: tuple = ()) -> int:
        sets = ", ".join([f"{k} = ?" for k in data])
        sql = f"UPDATE {table} SET {sets} WHERE {where}"
        params = tuple(data.values()) + where_params
        return self.execute(sql, params)

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        sql = f"DELETE FROM {table} WHERE {where}"
        return self.execute(sql, params)

    def get_enterprise_profile(self) -> dict | None:
        """获取企业资料（单条记录）"""
        return self.fetch_one("SELECT * FROM enterprise_profile ORDER BY id LIMIT 1")

    def save_enterprise_profile(self, data: dict) -> int:
        """保存企业资料：存在则更新，不存在则插入"""
        existing = self.get_enterprise_profile()
        now = format_datetime()
        if existing:
            data["updated_at"] = now
            self.update("enterprise_profile", data, "id = ?", (existing["id"],))
            return existing["id"]
        data["created_at"] = now
        data["updated_at"] = now
        return self.insert("enterprise_profile", data)

    def backup_db(self):
        import shutil
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(self.db_path)), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = format_datetime(fmt="%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        # 备份前关闭连接
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
        abs_src = os.path.abspath(self.db_path)
        try:
            shutil.copy2(abs_src, backup_path)
            logger.info(f"数据库已备份: {backup_path}")
        except FileNotFoundError:
            logger.warning(f"备份时数据库文件不存在: {abs_src}")
        self._cleanup_old_backups(backup_dir)

    def _cleanup_old_backups(self, backup_dir, keep_days=30):
        import time
        cutoff = time.time() - keep_days * 86400
        for f in os.listdir(backup_dir):
            path = os.path.join(backup_dir, f)
            if os.path.isfile(path) and f.endswith(".db"):
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
