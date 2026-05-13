"""日志配置 — stdlib logging + 文件轮转"""
import os
import logging
import logging.handlers
from utils.config_loader import config_loader


def setup_logging(extra_handler: logging.Handler = None):
    cfg = config_loader
    log_level = getattr(logging, cfg.get("LOG_LEVEL", "INFO"), logging.INFO)
    log_dir = os.path.join("data", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "app.log")
    retention = int(cfg.get("LOG_RETENTION_DAYS", "30"))

    root = logging.getLogger()
    root.setLevel(log_level)

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        ))
        root.addHandler(console)

    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=retention,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        root.addHandler(file_handler)

    if extra_handler and not any(isinstance(h, type(extra_handler)) for h in root.handlers):
        extra_handler.setLevel(log_level)
        root.addHandler(extra_handler)

    return root
