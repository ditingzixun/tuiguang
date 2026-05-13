"""浏览器指纹管理 — 多浏览器指纹隔离，一号一箱"""
import os
import json
import random
from datetime import datetime
from fake_useragent import UserAgent
import logging; logger = logging.getLogger(__name__)


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
        # 生成真实常见的屏幕分辨率组合
        resolutions = [
            (1366, 768), (1440, 900), (1536, 864), (1680, 1050),
            (1920, 1080), (2560, 1440), (1280, 720), (1600, 900),
        ]
        viewport_w, viewport_h = random.choice(resolutions)
        fingerprint = {
            "account_id": account_id,
            "platform": platform,
            "profile_dir": profile_dir,
            "user_agent": ua,
            "viewport": {"width": viewport_w, "height": viewport_h},
            "screen": {
                "width": viewport_w,
                "height": viewport_h,
                "color_depth": random.choice([24, 24, 24, 30]),
                "pixel_depth": 24,
            },
            "locale": "zh-CN",
            "timezone_id": random.choice(["Asia/Shanghai", "Asia/Shanghai", "Asia/Shanghai",
                                           "Asia/Chongqing", "Asia/Harbin"]),
            "geolocation": {
                "latitude": round(random.uniform(22.0, 40.0), 6),
                "longitude": round(random.uniform(100.0, 122.0), 6),
            },
            "color_scheme": random.choice(["light", "light", "light", "dark", "no-preference"]),
            "device_scale_factor": random.choices(
                [1, 1.25, 1.5, 2], weights=[40, 25, 20, 15]
            )[0],
            "is_mobile": False,
            "has_touch": False,
            "platform_name": random.choices(
                ["Win32", "Win32", "Win32", "MacIntel", "Linux x86_64"]
            )[0],
            "hardware_concurrency": random.choice([2, 4, 4, 8, 8, 8, 12, 16]),
            "device_memory": random.choices([2, 4, 4, 8, 8, 16], weights=[10, 30, 25, 20, 10, 5])[0],
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
        """为每个账号生成自然外观的唯一UA

        基于真实中国用户的Chrome版本分布构建，不添加可疑的后缀哈希。
        """
        # 基于 account_id 确定性生成（同一账号始终得到相同UA）
        rng = random.Random(account_id * 7907 + 27449)

        # Chrome 主版本号分布 (120-134)
        chrome_major = rng.randint(120, 134)
        chrome_build = rng.randint(4000, 6999)
        chrome_patch = rng.randint(0, 199)

        # Windows NT 版本
        nt_version = rng.choice(["10.0", "10.0", "10.0", "10.0", "6.1"])
        # Win64/WOW64
        arch = rng.choice(["Win64; x64", "Win64; x64", "Win64; x64", "WOW64"])

        ua = (
            f"Mozilla/5.0 (Windows NT {nt_version}; {arch}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_major}.0.{chrome_build}.{chrome_patch} "
            f"Safari/537.36"
        )
        return ua

    def _generate_webgl_vendor(self) -> str:
        vendors = [
            "Google Inc. (Intel)",
            "Google Inc. (Intel)",
            "Google Inc. (NVIDIA)",
            "Google Inc. (NVIDIA)",
            "Google Inc. (AMD)",
            "Google Inc. (Intel Inc.)",
            "Google Inc. (Microsoft)",
        ]
        return random.choice(vendors)

    def _generate_webgl_renderer(self) -> str:
        renderers = [
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel, Intel(R) UHD Graphics 730 Direct3D11 vs_5_0 ps_5_0)",
        ]
        return random.choice(renderers)

    def _get_random_fonts(self) -> list:
        # 模拟中国用户常见的系统字体组合
        base_fonts = [
            "Arial", "Times New Roman", "Courier New", "Georgia",
            "Verdana", "Tahoma", "Trebuchet MS", "Comic Sans MS",
            "SimSun", "Microsoft YaHei", "SimHei", "KaiTi",
            "FangSong", "NSimSun", "STSong", "STXihei", "STKaiti",
            "Microsoft JhengHei", "PMingLiU", "DengXian",
        ]
        k = random.randint(8, len(base_fonts))
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
