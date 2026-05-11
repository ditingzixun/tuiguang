"""配置文件加载器"""
import os
import yaml
from loguru import logger


class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = None) -> dict:
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            logger.info(f"配置加载成功: {config_path}")
        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {config_path}, 使用默认配置")
            self._config = self._default_config()
        except yaml.YAMLError as e:
            logger.error(f"配置文件解析错误: {e}")
            self._config = self._default_config()
        return self._config

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config or {}
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def config(self) -> dict:
        if self._config is None:
            self.load()
        return self._config or {}

    @staticmethod
    def _default_config() -> dict:
        return {
            "system": {"app_name": "资质代办全网推广助手", "version": "1.0.0", "debug": False},
            "database": {"path": "./data/qualification_bot.db"},
            "browser": {"headless": False, "default_timeout": 30000, "slow_mo": 50, "viewport_width": 1366, "viewport_height": 768},
            "scheduler": {"publish_interval_min": 60, "publish_interval_max": 300, "daily_publish_limit": 20, "retry_max": 3},
            "anti_ban": {"random_delay_min": 3000, "random_delay_max": 8000, "scroll_random": True, "mouse_move_random": True, "click_offset": True, "typing_speed_vary": True},
            "seo": {"check_interval_hours": 6, "search_engines": [{"name": "baidu", "url": "https://www.baidu.com/s?wd="}, {"name": "360", "url": "https://www.so.com/s?q="}]},
            "ai_content": {"provider": "openai", "model": "gpt-4", "max_tokens": 2000, "temperature": 0.8},
            "qualification_types": ["网络文化经营许可证", "ICP经营许可证", "EDI经营许可证"],
            "content_types": [{"name": "软文推广", "template": "soft_article"}, {"name": "科普文章", "template": "science_article"}, {"name": "对比分析", "template": "comparison_article"}],
        }


config_loader = ConfigLoader()
