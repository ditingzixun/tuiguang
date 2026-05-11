"""浏览器指纹管理 - 多浏览器指纹隔离，一号一箱"""
import os
import json
import random
import string
import hashlib
from datetime import datetime
from fake_useragent import UserAgent
from loguru import logger


class FingerprintManager:
    """浏览器指纹生成与管理"""

    UA_CACHE = {}

    def __init__(self, profiles_dir: str = "./data/profiles"):
        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)
        self._ua_generator = UserAgent()

    def generate_fingerprint(self, account_id: int, platform: str) -> dict:
        """为每个账号生成独立的浏览器指纹"""
        profile_dir = os.path.join(self.profiles_dir, f"account_{account_id}")
        os.makedirs(profile_dir, exist_ok=True)

        ua = self._generate_unique_ua(account_id)
        fingerprint = {
            "account_id": account_id,
            "platform": platform,
            "profile_dir": profile_dir,
            "user_agent": ua,
            "viewport": {
                "width": random.choice([1366, 1440, 1536, 1680, 1920]),
                "height": random.choice([768, 900, 864, 1050, 1080]),
            },
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "geolocation": {
                "latitude": round(random.uniform(22.0, 40.0), 6),
                "longitude": round(random.uniform(100.0, 122.0), 6),
            },
            "color_scheme": random.choice(["light", "dark", "no-preference"]),
            "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
            "is_mobile": False,
            "has_touch": False,
            "platform_name": random.choice(["Windows", "Windows", "Windows", "macOS"]),
            "hardware_concurrency": random.choice([4, 8, 12, 16]),
            "device_memory": random.choice([4, 8, 16]),
            "vendor": "Google Inc.",
            "rendering_engines": ["Blink"],
            "canvas_noise": True,
            "webgl_noise": True,
            "audio_noise": True,
            "client_rects_noise": True,
            "webgl_vendor": self._generate_webgl_vendor(),
            "webgl_renderer": self._generate_webgl_renderer(),
            "fonts": self._get_random_fonts(),
            "generated_at": datetime.now().isoformat(),
        }
        self._save_fingerprint(account_id, fingerprint)
        logger.info(f"为账号 {account_id} 生成独立指纹, UA: {ua[:80]}...")
        return fingerprint

    def load_fingerprint(self, account_id: int) -> dict:
        path = os.path.join(self.profiles_dir, f"account_{account_id}", "fingerprint.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_fingerprint(self, account_id: int, fingerprint: dict):
        profile_dir = os.path.join(self.profiles_dir, f"account_{account_id}")
        os.makedirs(profile_dir, exist_ok=True)
        path = os.path.join(profile_dir, "fingerprint.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fingerprint, f, ensure_ascii=False, indent=2)

    def _generate_unique_ua(self, account_id: int) -> str:
        """为每个账号生成唯一UA"""
        ua = self._ua_generator.chrome
        # 确保每个账号的UA不同
        hash_suffix = hashlib.md5(f"{account_id}{random.random()}".encode()).hexdigest()[:8]
        if "Chrome/" in ua:
            ua = ua.replace("Chrome/", f"Chrome/{random.randint(100, 130)}.0.")
        return f"{ua} {hash_suffix}"

    def _generate_webgl_vendor(self) -> str:
        vendors = [
            "Google Inc. (Intel)",
            "Google Inc. (NVIDIA)",
            "Google Inc. (AMD)",
            "Google Inc. (Intel Inc.)",
        ]
        return random.choice(vendors)

    def _generate_webgl_renderer(self) -> str:
        renderers = [
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
        ]
        return random.choice(renderers)

    def _get_random_fonts(self) -> list:
        base_fonts = [
            "Arial", "Times New Roman", "Courier New", "Georgia",
            "Verdana", "SimSun", "Microsoft YaHei", "SimHei",
            "KaiTi", "FangSong", "NSimSun", "STSong",
        ]
        k = random.randint(6, len(base_fonts))
        return random.sample(base_fonts, k)

    def get_cookies_path(self, account_id: int) -> str:
        profile_dir = os.path.join(self.profiles_dir, f"account_{account_id}")
        os.makedirs(profile_dir, exist_ok=True)
        return os.path.join(profile_dir, "cookies.json")

    def save_cookies(self, account_id: int, cookies: list):
        path = self.get_cookies_path(account_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"账号 {account_id} Cookies已保存")

    def load_cookies(self, account_id: int) -> list:
        path = self.get_cookies_path(account_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
