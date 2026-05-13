"""通用工具函数"""
import os
import re
import uuid
import hashlib
import random
import string
from datetime import datetime, timedelta
import logging; logger = logging.getLogger(__name__)


def generate_id() -> str:
    return uuid.uuid4().hex[:16]


def generate_task_no() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + random.randint(1000, 9999).__str__()


def hash_password(password: str) -> str:
    salt = "qualification_bot_salt"
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()


def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_phone() -> str:
    prefixes = ["130", "131", "132", "133", "135", "136", "137", "138", "139",
                "150", "151", "152", "153", "155", "156", "157", "158", "159",
                "180", "181", "182", "183", "185", "186", "187", "188", "189"]
    return random.choice(prefixes) + "".join(random.choices(string.digits, k=8))


def format_datetime(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def parse_datetime(s: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(s, fmt)


def truncate_text(text: str, max_len: int = 200) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def safe_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", filename)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def parse_proxy_url(url: str) -> dict:
    """解析代理URL格式: protocol://user:pass@host:port"""
    pattern = r"(?P<protocol>\w+)://(?:(?P<username>[^:]+):(?P<password>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)"
    m = re.match(pattern, url)
    if m:
        return m.groupdict()
    return None
