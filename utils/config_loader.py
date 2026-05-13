"""配置加载器 — python-dotenv + os.getenv"""
import os
from dotenv import load_dotenv


class ConfigLoader:
    _instance = None

    DEFAULTS = {
        "DB_PATH": "./data/qualification_bot.db",
        "LOG_LEVEL": "INFO",
        "LOG_RETENTION_DAYS": "30",
        "BROWSER_HEADLESS": "false",
        "BROWSER_TIMEOUT": "30000",
        "BROWSER_SLOW_MO": "50",
        "VIEWPORT_WIDTH": "1366",
        "VIEWPORT_HEIGHT": "768",
        "DAILY_PUBLISH_LIMIT": "20",
        "PUBLISH_INTERVAL_MIN": "60",
        "PUBLISH_INTERVAL_MAX": "300",
        "RETRY_MAX": "3",
        "RETRY_DELAY": "300",
        "PROXY_ENABLED": "false",
        "PROXY_API_URL": "",
        "PROXY_API_KEY": "",
        "PROXY_EXTRACT_COUNT": "10",
        "PROXY_CHECK_INTERVAL": "300",
        "PROXY_TEST_URL": "https://www.baidu.com",
        "PROXY_TEST_TIMEOUT": "10",
        "PROXY_MAX_FAILURES": "3",
        "PROXY_ROTATION_MODE": "round_robin",
        # AI 提供商
        "AI_ENABLED": "false",
        "AI_PROVIDER": "auto",
        "AI_API_KEY": "",
        "AI_API_BASE": "https://api.openai.com/v1",
        "AI_MODEL": "gpt-4o-mini",
        "CLAUDE_API_KEY": "",
        "CLAUDE_MODEL": "claude-sonnet-4-6",
        "AI_MAX_TOKENS": "2048",
        "AI_TEMPERATURE": "0.8",
        "AI_FALLBACK_TEMPLATE": "true",
        "SETUP_COMPLETED": "false",
        "ENTERPRISE_COMPANY_NAME": "",
        "ENTERPRISE_SHORT_NAME": "",
        "ENTERPRISE_PHONE": "",
        "ENTERPRISE_CONTACT_PERSON": "",
        "ENTERPRISE_ADDRESS": "",
        "ENTERPRISE_WEBSITE": "",
        "SEO_ENABLED": "false",
        "SEO_CHECK_INTERVAL_HOURS": "6",
        "SEO_SEARCH_ENGINES": "baidu,360",
        "SEO_MAX_RESULT_PAGES": "3",
        "SEO_AUTO_REPUBLISH": "false",
        "SEO_REQUEST_DELAY": "5",
        "BUTTON_FONT_COLOR": "white",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_loaded") and self._loaded:
            return
        self._loaded = True
        self.load()

    def load(self, env_path: str = None):
        if env_path:
            load_dotenv(env_path, override=True)
        else:
            load_dotenv(override=True)

    def get(self, key: str, default=None):
        return os.getenv(key, default or self.DEFAULTS.get(key))

    def get_int(self, key: str, default: int = 0) -> int:
        return int(self.get(key, str(default)))

    def get_bool(self, key: str, default: bool = False) -> bool:
        val = self.get(key, str(default).lower())
        return val in ("true", "1", "yes", "on")

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    @property
    def config(self) -> dict:
        result = {}
        for key in self.DEFAULTS:
            result[key] = self.get(key)
        return result


config_loader = ConfigLoader()
