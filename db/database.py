"""数据库管理器"""
import os
import shutil
from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, scoped_session
from loguru import logger
from .models import Base


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
        self.engine = None
        self.session_factory = None
        self.Session = None

    def init_db(self, db_path: str = None):
        if db_path:
            self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            poolclass=None,
            echo=False
        )
        self._enable_wal_mode()
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        self._init_default_configs()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def _enable_wal_mode(self):
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.execute(text("PRAGMA cache_size=-64000"))
            conn.commit()

    def _init_default_configs(self):
        defaults = [
            ("daily_publish_limit", "20", "scheduler", "每日发布上限"),
            ("publish_interval_min", "60", "scheduler", "最小发布间隔(秒)"),
            ("publish_interval_max", "300", "scheduler", "最大发布间隔(秒)"),
            ("retry_max", "3", "scheduler", "最大重试次数"),
            ("anti_ban_enabled", "true", "anti_ban", "启用反封号策略"),
            ("sensitive_filter_enabled", "true", "sensitive", "启用敏感词过滤"),
        ]
        session = self.get_session()
        from .models import SystemConfig
        for key, value, category, desc in defaults:
            existing = session.query(SystemConfig).filter_by(key=key).first()
            if not existing:
                session.add(SystemConfig(key=key, value=value, category=category, description=desc))
        session.commit()
        session.close()

    def get_session(self):
        return self.Session()

    def backup_db(self):
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        if self.engine:
            self.engine.dispose()
        shutil.copy2(self.db_path, backup_path)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        logger.info(f"数据库已备份到: {backup_path}")
        self._cleanup_old_backups(backup_dir, keep_days=30)

    def _cleanup_old_backups(self, backup_dir, keep_days=30):
        cutoff = datetime.now() - timedelta(days=keep_days)
        for f in os.listdir(backup_dir):
            path = os.path.join(backup_dir, f)
            if os.path.isfile(path) and f.endswith(".db"):
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime < cutoff:
                    os.remove(path)

    def dispose(self):
        if self.engine:
            self.engine.dispose()
