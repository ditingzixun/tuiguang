"""代理IP池引擎 - 对接代理IP API，自动提取、轮换、检测IP可用性"""
import time
import threading
import requests
from datetime import datetime
from typing import Optional
from loguru import logger
from utils.config_loader import config_loader


class ProxyEngine:
    """代理IP池管理引擎"""

    def __init__(self):
        cfg = config_loader.config.get("proxy", {})
        self.api_url = cfg.get("api_url", "")
        self.api_key = cfg.get("api_key", "")
        self.check_interval = cfg.get("check_interval", 300)
        self.max_fail_count = cfg.get("max_fail_count", 3)
        self.min_available_ips = cfg.get("min_available_ips", 5)
        self.protocols = cfg.get("protocols", ["http", "https", "socks5"])
        self._pool = []  # [{"protocol":"http","host":"...","port":80,...}, ...]
        self._index = 0
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self.enabled = cfg.get("enabled", False)

    def start(self):
        if not self.enabled:
            logger.info("代理IP池未启用")
            return
        self._running = True
        self._thread = threading.Thread(target=self._maintain_loop, daemon=True)
        self._thread.start()
        logger.info("代理IP池引擎已启动")

    def stop(self):
        self._running = False

    def fetch_proxies(self, count: int = 10) -> list:
        """从API提取代理IP"""
        if not self.api_url:
            logger.warning("未配置代理API地址")
            return []
        try:
            params = {"key": self.api_key, "count": count, "type": "json"}
            resp = requests.get(self.api_url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                proxies = self._parse_proxy_response(data)
                logger.info(f"从API获取 {len(proxies)} 个代理IP")
                return proxies
        except Exception as e:
            logger.error(f"代理API请求异常: {e}")
        return []

    def _parse_proxy_response(self, data: dict) -> list:
        """解析多种常见代理API响应格式"""
        proxies = []
        # 格式1: {"code":0,"data":[{"ip":"...","port":80},...]}
        raw_list = data.get("data", data.get("proxies", data.get("list", [])))
        if isinstance(raw_list, list):
            for item in raw_list:
                if isinstance(item, dict):
                    proxies.append({
                        "protocol": item.get("protocol", "http"),
                        "host": item.get("ip", item.get("host", "")),
                        "port": int(item.get("port", 80)),
                        "username": item.get("username", item.get("user", "")),
                        "password": item.get("password", item.get("pass", "")),
                        "region": item.get("region", item.get("city", "")),
                        "fail_count": 0,
                        "success_count": 0,
                        "latency": None,
                        "last_check_at": None,
                        "status": "available"
                    })
        return proxies

    def get_proxy(self) -> Optional[dict]:
        """轮询获取一个可用代理"""
        with self._lock:
            available = [p for p in self._pool if p["status"] == "available"]
            if not available:
                # 自动补充
                new_proxies = self.fetch_proxies(self.min_available_ips)
                self._pool.extend(new_proxies)
                available = [p for p in self._pool if p["status"] == "available"]
            if not available:
                return None
            self._index = (self._index + 1) % len(available)
            return available[self._index]

    def get_proxy_config(self) -> Optional[dict]:
        """获取Playwright格式的代理配置"""
        proxy = self.get_proxy()
        if not proxy:
            return None
        server = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
        config = {"server": server}
        if proxy.get("username") and proxy.get("password"):
            config["username"] = proxy["username"]
            config["password"] = proxy["password"]
        return config

    def check_proxy(self, proxy: dict) -> bool:
        """检测代理IP可用性"""
        test_url = "https://www.baidu.com"
        try:
            server = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
            proxies = {"http": server, "https": server}
            auth = None
            if proxy.get("username") and proxy.get("password"):
                auth = (proxy["username"], proxy["password"])
            start = time.time()
            resp = requests.get(test_url, proxies=proxies, auth=auth, timeout=10)
            latency = time.time() - start
            proxy["latency"] = round(latency, 3)
            proxy["last_check_at"] = datetime.now()
            if resp.status_code == 200:
                proxy["fail_count"] = 0
                proxy["success_count"] += 1
                proxy["status"] = "available"
                return True
        except Exception:
            proxy["fail_count"] += 1
            proxy["last_check_at"] = datetime.now()
            if proxy["fail_count"] >= self.max_fail_count:
                proxy["status"] = "failed"
        return False

    def mark_failed(self, proxy: dict):
        proxy["fail_count"] += 1
        if proxy["fail_count"] >= self.max_fail_count:
            proxy["status"] = "failed"

    def check_all(self):
        """检测所有代理"""
        for proxy in self._pool:
            self.check_proxy(proxy)
        # 清理失效代理
        with self._lock:
            self._pool = [p for p in self._pool if p["status"] != "failed"]
        logger.info(f"代理检测完成，可用IP: {len([p for p in self._pool if p['status'] == 'available'])}")

    def _maintain_loop(self):
        while self._running:
            self.check_all()
            # 补充代理
            available = len([p for p in self._pool if p["status"] == "available"])
            if available < self.min_available_ips:
                new_proxies = self.fetch_proxies(self.min_available_ips - available)
                with self._lock:
                    self._pool.extend(new_proxies)
            time.sleep(self.check_interval)

    @property
    def pool_size(self) -> int:
        return len(self._pool)

    @property
    def available_count(self) -> int:
        return len([p for p in self._pool if p["status"] == "available"])


proxy_engine = ProxyEngine()
