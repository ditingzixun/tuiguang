"""短信验证码API引擎 - 对接短信平台接收验证码"""
import time
import threading
import requests
from datetime import datetime
from typing import Optional
from loguru import logger
from utils.config_loader import config_loader


class SmsEngine:
    """短信验证码接收引擎"""

    def __init__(self):
        cfg = config_loader.config.get("sms", {})
        self.api_url = cfg.get("api_url", "")
        self.api_key = cfg.get("api_key", "")
        self.timeout = cfg.get("timeout", 120)
        self._pending_codes = {}  # phone -> {"code":..., "time":...}
        self._lock = threading.Lock()

    def request_code(self, phone: str, platform: str = "") -> bool:
        """请求发送验证码"""
        if not self.api_url:
            logger.warning("未配置短信API地址，使用模拟模式")
            self._simulate_code(phone)
            return True
        try:
            resp = requests.post(self.api_url, json={
                "key": self.api_key,
                "phone": phone,
                "platform": platform,
                "action": "send"
            }, timeout=30)
            data = resp.json()
            if data.get("code") == 0 or data.get("success"):
                logger.info(f"验证码已请求发送至 {phone}")
                return True
            else:
                logger.error(f"验证码请求失败: {data.get('msg', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"短信API请求异常: {e}")
            self._simulate_code(phone)
            return True

    def get_code(self, phone: str, wait: bool = True) -> Optional[str]:
        """获取验证码"""
        if not self.api_url:
            return self._get_simulated_code(phone)
        if wait:
            return self._wait_for_code(phone)
        try:
            resp = requests.post(self.api_url, json={
                "key": self.api_key,
                "phone": phone,
                "action": "get_code"
            }, timeout=15)
            data = resp.json()
            if data.get("code") == 0:
                code = data.get("data", {}).get("code", "")
                logger.info(f"获取到验证码: {code}")
                return code
        except Exception as e:
            logger.error(f"获取验证码异常: {e}")
        return None

    def _wait_for_code(self, phone: str) -> Optional[str]:
        """等待验证码到达"""
        start = time.time()
        while time.time() - start < self.timeout:
            code = self.get_code(phone, wait=False)
            if code:
                return code
            time.sleep(3)
        logger.warning(f"等待验证码超时: {phone}")
        return None

    def _simulate_code(self, phone: str):
        """模拟验证码（开发测试用）"""
        import random
        code = "".join(random.choices("0123456789", k=6))
        with self._lock:
            self._pending_codes[phone] = {"code": code, "time": time.time()}
        logger.debug(f"模拟验证码 [{phone}]: {code}")

    def _get_simulated_code(self, phone: str) -> Optional[str]:
        with self._lock:
            if phone in self._pending_codes:
                return self._pending_codes[phone]["code"]
        return None


sms_engine = SmsEngine()
