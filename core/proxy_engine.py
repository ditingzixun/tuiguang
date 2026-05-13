"""代理IP池引擎 — 对接第三方IP服务商API，自动提取/校验/轮换/绑定"""
import time
import json
import threading
import logging
from utils.helpers import format_datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader


class ProxyEngine:
    """代理IP池管理引擎（单例）"""

    def __init__(self):
        cfg = config_loader
        self.enabled = cfg.get_bool("PROXY_ENABLED", False)
        self.api_url = cfg.get("PROXY_API_URL", "")
        self.api_key = cfg.get("PROXY_API_KEY", "")
        self.extract_count = cfg.get_int("PROXY_EXTRACT_COUNT", 10)
        self.check_interval = cfg.get_int("PROXY_CHECK_INTERVAL", 300)
        self.test_url = cfg.get("PROXY_TEST_URL", "https://www.baidu.com")
        self.test_timeout = cfg.get_int("PROXY_TEST_TIMEOUT", 10)
        self.max_failures = cfg.get_int("PROXY_MAX_FAILURES", 3)
        self.rotation_mode = cfg.get("PROXY_ROTATION_MODE", "round_robin")

        self._rotation_index = 0
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._db_manager = None

    def set_db_manager(self, db_manager):
        self._db_manager = db_manager

    def start(self):
        if not self.enabled:
            logger.info("代理IP池未启用")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._main_loop, daemon=True)
        self._thread.start()
        logger.info("代理IP池引擎已启动")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("代理IP池引擎已停止")


    def _main_loop(self):
        """后台维护循环：提取 → 校验 → 清理 → 等待"""
        while self._running:
            try:
                # 检查是否需要补充代理
                active = self._count_active()
                needed = self.extract_count - active
                if needed > 0:
                    logger.info(f"代理池不足，需补充 {needed} 个")
                    self._fetch_proxies(needed)

                # 校验存活性
                self._validate_all()

                # 清理失效代理
                self._cleanup_dead()

            except Exception as e:
                logger.error(f"代理池维护异常: {e}")

            # 等待下一次循环
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)


    def _fetch_proxies(self, count: int = None):
        """从API提取代理IP"""
        if count is None:
            count = self.extract_count
        if not self.api_url:
            logger.warning("未配置代理API地址")
            return

        try:
            params = {"key": self.api_key, "count": count, "format": "json"}
            resp = requests.get(self.api_url, params=params, timeout=15)
            if resp.status_code == 200:
                proxies = self._parse_response(resp.text)
                saved = self._save_proxies(proxies)
                logger.info(f"从API获取 {len(proxies)} 个代理，入库 {saved} 个")
            else:
                logger.warning(f"代理API返回状态码: {resp.status_code}")
        except requests.RequestException as e:
            logger.error(f"代理API请求异常: {e}")

    def _parse_response(self, text: str) -> list:
        """解析多种常见代理API响应格式

        Returns: [{"host": "...", "port": 80, "protocol": "http", "username": "", "password": ""}, ...]
        """
        # 一次解析JSON，避免重复 json.loads(text)
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            data = None

        if isinstance(data, dict):
            proxies = self._try_extract_dict_items(data) or self._try_extract_string_list(data)
            if proxies:
                return proxies

        # 纯文本格式: "ip:port\nip:port\n..."
        return self._try_extract_plain_text(text)

    def _try_extract_dict_items(self, data: dict) -> list | None:
        """尝试从 JSON 对象中提取代理列表（格式1和格式3：data键为dict list）"""
        # 格式1: {"code":0, "data":[{"ip":"...", "port":80}]}
        # 格式3: {"proxies":[{"host":"...", "port":80}]}
        items = data.get("data") or data.get("proxies")
        if not isinstance(items, list) or not items or not isinstance(items[0], dict):
            return None
        proxies = []
        for item in items:
            proxies.append({
                "host": item.get("ip") or item.get("host", ""),
                "port": int(item.get("port", 80)),
                "protocol": item.get("protocol", "http"),
                "username": item.get("username") or item.get("user", ""),
                "password": item.get("password") or item.get("pass", ""),
            })
        return proxies if proxies else None

    def _try_extract_string_list(self, data: dict) -> list | None:
        """尝试从 JSON 对象中提取代理列表（格式2：data.proxy_list键为字符串列表）"""
        # 格式2: {"data":{"proxy_list":["ip:port", ...]}}
        inner = data.get("data")
        if not isinstance(inner, dict):
            return None
        items = inner.get("proxy_list") or inner.get("proxies")
        if not isinstance(items, list) or not items:
            return None
        proxies = []
        for item in items:
            if isinstance(item, str) and ":" in item:
                parts = item.split(":")
                proxies.append({
                    "host": parts[0],
                    "port": int(parts[1]) if len(parts) > 1 else 80,
                    "protocol": "http",
                    "username": "",
                    "password": "",
                })
        return proxies if proxies else None

    def _try_extract_plain_text(self, text: str) -> list:
        """从纯文本中解析 ip:port 格式"""
        proxies = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and ":" in line and not line.startswith("{") and not line.startswith("<"):
                parts = line.split(":")
                if len(parts) >= 2:
                    proxies.append({
                        "host": parts[0],
                        "port": int(parts[1]) if parts[1].isdigit() else 80,
                        "protocol": "http",
                        "username": "",
                        "password": "",
                    })
        return proxies

    def _save_proxies(self, proxies: list) -> int:
        """保存代理到数据库（去重）"""
        if not self._db_manager or not proxies:
            return 0
        count = 0
        for p in proxies:
            host, port = p["host"], p["port"]
            if not host:
                continue
            existing = self._db_manager.fetch_one(
                "SELECT id FROM proxies WHERE host = ? AND port = ?", (host, port)
            )
            if not existing:
                now = format_datetime()
                self._db_manager.insert("proxies", {
                    "host": host,
                    "port": port,
                    "protocol": p.get("protocol", "http"),
                    "username": p.get("username", ""),
                    "password": p.get("password", ""),
                    "source": "api",
                    "created_at": now,
                })
                count += 1
        return count


    def _validate_all(self):
        """校验所有代理的存活性"""
        if not self._db_manager:
            return
        rows = self._db_manager.fetch_all("SELECT * FROM proxies")
        now = format_datetime()
        for row in rows:
            alive, latency = self._validate_proxy(
                row["host"], row["port"], row["protocol"],
                row["username"], row["password"]
            )
            if alive:
                self._db_manager.update("proxies", {
                    "status": "active",
                    "latency_ms": latency,
                    "consecutive_failures": 0,
                    "success_count": row["success_count"] + 1,
                    "last_check_at": now,
                }, "id = ?", (row["id"],))
            else:
                new_fails = row["consecutive_failures"] + 1
                new_status = "failed" if new_fails >= self.max_failures else row["status"]
                self._db_manager.update("proxies", {
                    "consecutive_failures": new_fails,
                    "fail_count": row["fail_count"] + 1,
                    "status": new_status,
                    "last_check_at": now,
                }, "id = ?", (row["id"],))

    def _validate_proxy(self, host: str, port: int, protocol: str,
                        username: str = "", password: str = "") -> tuple:
        """校验单个代理的存活性

        Returns: (is_alive: bool, latency_ms: int)
        """
        try:
            auth = f"{username}:{password}@" if username and password else ""
            proxy_url = f"{protocol}://{auth}{host}:{port}"
            proxies = {"http": proxy_url, "https": proxy_url}

            start = time.time()
            resp = requests.get(self.test_url, proxies=proxies, timeout=self.test_timeout)
            latency = int((time.time() - start) * 1000)

            return (resp.status_code == 200, latency)
        except Exception:
            return (False, 0)


    def _cleanup_dead(self):
        """清理过期失效代理"""
        if not self._db_manager:
            return
        deleted = self._db_manager.delete(
            "proxies",
            "consecutive_failures >= ? AND status = 'failed'",
            (self.max_failures,)
        )
        if deleted:
            logger.info(f"已清理 {deleted} 个失效代理")

    def _count_active(self) -> int:
        if not self._db_manager:
            return 0
        row = self._db_manager.fetch_one("SELECT COUNT(*) as cnt FROM proxies WHERE status = 'active'")
        return row["cnt"] if row else 0


    def get_proxy(self, account_id: int = None) -> Optional[dict]:
        """获取一个代理

        优先级：账号绑定 > 加权轮换 > 轮询轮换

        Returns: {"server": "http://host:port", "username": "...", "password": "..."} or None
        """
        if not self._db_manager:
            return None

        # 1. 检查账号绑定
        if account_id:
            binding = self._db_manager.fetch_one(
                "SELECT p.host, p.port, p.protocol, p.username, p.password, p.status "
                "FROM proxy_bindings pb JOIN proxies p ON pb.proxy_id = p.id "
                "WHERE pb.account_id = ? AND p.status = 'active'",
                (account_id,)
            )
            if binding:
                return self._build_proxy_dict(binding)

        # 2. 从池中选择
        active = self._db_manager.fetch_all(
            "SELECT * FROM proxies WHERE status = 'active' ORDER BY latency_ms ASC"
        )
        if not active:
            return None

        with self._lock:
            if self.rotation_mode == "weighted":
                proxy = self._weighted_select(active)
            else:
                self._rotation_index = (self._rotation_index + 1) % len(active)
                proxy = active[self._rotation_index]

        return self._build_proxy_dict(proxy) if proxy else None

    def _weighted_select(self, proxies: list) -> dict:
        """加权选择：延迟越低，权重越高"""
        total_weight = 0
        weights = []
        for p in proxies:
            latency = max(p["latency_ms"], 1)
            w = 1000.0 / latency  # 延迟1ms=权重1000, 1000ms=权重1
            weights.append(w)
            total_weight += w

        if total_weight == 0:
            return proxies[0]

        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return proxies[i]
        return proxies[-1]

    def _build_proxy_dict(self, row) -> dict:
        """将数据库行转为Playwright格式的代理字典"""
        auth = f"{row['username']}:{row['password']}@" if row.get("username") and row.get("password") else ""
        return {
            "server": f"{row['protocol']}://{auth}{row['host']}:{row['port']}",
            "username": row.get("username", ""),
            "password": row.get("password", ""),
        }


    def bind_proxy(self, account_id: int, proxy_id: int):
        """绑定账号专属代理"""
        if not self._db_manager:
            return
        self._db_manager.execute(
            "INSERT OR REPLACE INTO proxy_bindings (account_id, proxy_id, bound_at) VALUES (?, ?, ?)",
            (account_id, proxy_id, format_datetime())
        )
        logger.info(f"账号 {account_id} 已绑定代理 {proxy_id}")

    def unbind_proxy(self, account_id: int):
        """解除账号代理绑定"""
        if not self._db_manager:
            return
        self._db_manager.delete("proxy_bindings", "account_id = ?", (account_id,))
        logger.info(f"账号 {account_id} 已解除代理绑定")

    def get_account_binding(self, account_id: int) -> Optional[dict]:
        """查询账号的代理绑定信息"""
        if not self._db_manager:
            return None
        return self._db_manager.fetch_one(
            "SELECT p.* FROM proxy_bindings pb JOIN proxies p ON pb.proxy_id = p.id "
            "WHERE pb.account_id = ?",
            (account_id,)
        )


    def mark_result(self, proxy_dict: dict, success: bool, latency_ms: int = 0):
        """上报代理使用结果"""
        if not self._db_manager or not proxy_dict:
            return
        server = proxy_dict.get("server", "")
        from utils.helpers import parse_proxy_url
        info = parse_proxy_url(server)
        if not info:
            return
        host, port = info["host"], int(info["port"])

        row = self._db_manager.fetch_one(
            "SELECT id, success_count, fail_count, consecutive_failures FROM proxies WHERE host = ? AND port = ?",
            (host, port)
        )
        if not row:
            return

        now = format_datetime()
        if success:
            self._db_manager.update("proxies", {
                "success_count": row["success_count"] + 1,
                "consecutive_failures": 0,
                "latency_ms": latency_ms,
                "last_check_at": now,
            }, "id = ?", (row["id"],))
        else:
            new_fails = row["consecutive_failures"] + 1
            self._db_manager.update("proxies", {
                "fail_count": row["fail_count"] + 1,
                "consecutive_failures": new_fails,
                "last_check_at": now,
            }, "id = ?", (row["id"],))


    def get_stats(self) -> dict:
        """获取代理池统计信息"""
        if not self._db_manager:
            return {"total": 0, "active": 0, "failed": 0, "avg_latency": 0}

        total = self._db_manager.fetch_one("SELECT COUNT(*) as cnt FROM proxies")
        active = self._db_manager.fetch_one("SELECT COUNT(*) as cnt FROM proxies WHERE status = 'active'")
        failed = self._db_manager.fetch_one("SELECT COUNT(*) as cnt FROM proxies WHERE status = 'failed'")
        avg_lat = self._db_manager.fetch_one("SELECT AVG(latency_ms) as avg FROM proxies WHERE status = 'active' AND latency_ms > 0")

        return {
            "total": total["cnt"] if total else 0,
            "active": active["cnt"] if active else 0,
            "failed": failed["cnt"] if failed else 0,
            "avg_latency": int(avg_lat["avg"]) if avg_lat and avg_lat["avg"] else 0,
        }

    def force_fetch(self):
        """手动触发一次提取"""
        self._fetch_proxies(self.extract_count)

    def force_validate_all(self):
        """手动触发全部校验"""
        self._validate_all()

    def force_cleanup(self):
        """手动清理失效代理"""
        self._cleanup_dead()


proxy_engine = ProxyEngine()
