"""平台插件基类 - 插件化设计，每个平台做独立插件"""
import os
import json
import time
import random
from abc import ABC, abstractmethod
from typing import Optional
from loguru import logger
from utils.behavior_sim import behavior_sim
from utils.text_filter import SensitiveWordFilter


class BasePlatformPlugin(ABC):
    """B2B/自媒体平台插件基类

    子类需实现: platform_info, login, publish
    可选实现: check_publish_result, delete_post, edit_post
    """

    # 子类必须定义的类属性
    platform_info = {
        "name": "base",
        "display_name": "基础平台",
        "type": "b2b",  # b2b / classified / media / forum
        "login_url": "",
        "publish_url": "",
        "version": "1.0.0",
    }

    def __init__(self, account: dict, browser_context, fingerprint: dict = None):
        self.account = account
        self.context = browser_context
        self.fingerprint = fingerprint or {}
        self.filter = SensitiveWordFilter()
        self._page = None
        self._is_logged_in = False

    async def init(self):
        """初始化插件"""
        self._page = await self.context.new_page()

    async def close(self):
        if self._page:
            await self._page.close()

    @abstractmethod
    async def login(self) -> bool:
        """登录平台，返回是否成功"""
        pass

    @abstractmethod
    async def publish(self, title: str, content: str, **kwargs) -> Optional[str]:
        """发布内容，返回发布链接"""
        pass

    async def check_login_status(self) -> bool:
        """检查登录状态"""
        return self._is_logged_in

    async def check_publish_result(self, url: str = None) -> bool:
        """检查发布结果"""
        return url is not None

    async def maintain_account(self):
        """养号操作 - 模拟正常用户行为"""
        try:
            await behavior_sim.random_scroll(self._page)
            await behavior_sim.random_delay(2, 5)
            # 随机点击几个链接
            links = await self._page.query_selector_all("a")
            if links and len(links) > 0:
                safe_links = links[:min(3, len(links))]
                for link in safe_links:
                    try:
                        await link.click()
                        await behavior_sim.random_delay(1, 3)
                        await self._page.go_back()
                    except Exception:
                        pass
            logger.info(f"账号 {self.account.get('username')} [{self.platform_info['name']}] 养号完成")
        except Exception as e:
            logger.warning(f"养号异常: {e}")

    async def fill_form_field(self, selector: str, value: str, field_type: str = "input"):
        """填充表单字段"""
        try:
            await self._page.wait_for_selector(selector, timeout=5000)
            if field_type == "input":
                await behavior_sim.human_type(self._page, selector, value)
            elif field_type == "textarea":
                await behavior_sim.human_type(self._page, selector, value)
            elif field_type == "select":
                await self._page.select_option(selector, value)
            await behavior_sim.random_delay(0.5, 1.5)
            return True
        except Exception as e:
            logger.error(f"填充字段 {selector} 失败: {e}")
            return False

    async def upload_image(self, selector: str, image_path: str) -> bool:
        """上传图片"""
        try:
            file_input = await self._page.query_selector(selector)
            if file_input:
                await file_input.set_input_files(image_path)
                await behavior_sim.random_delay(1, 3)
                return True
        except Exception as e:
            logger.error(f"上传图片失败: {e}")
        return False

    @staticmethod
    def get_plugin_dir() -> str:
        """获取插件目录"""
        return os.path.dirname(__file__)

    @staticmethod
    def load_config(config_name: str) -> dict:
        """加载插件配置"""
        config_path = os.path.join(os.path.dirname(__file__), f"{config_name}.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


class PluginManager:
    """插件管理器 - 自动发现和加载插件"""

    def __init__(self):
        self._plugins = {}
        self._discover_plugins()

    def _discover_plugins(self):
        """自动发现所有可用插件"""
        plugins_dir = os.path.dirname(__file__)
        b2b_dir = os.path.join(plugins_dir, "b2b")
        media_dir = os.path.join(plugins_dir, "media")

        self._scan_directory(b2b_dir)
        self._scan_directory(media_dir)
        logger.info(f"已发现 {len(self._plugins)} 个平台插件")

    def _scan_directory(self, directory: str):
        if not os.path.isdir(directory):
            return
        for fname in os.listdir(directory):
            if fname.endswith(".py") and fname != "__init__.py":
                module_name = fname[:-3]
                # 动态导入插件模块
                try:
                    mod = __import__(f"plugins.{os.path.basename(directory)}.{module_name}",
                                     fromlist=[module_name])
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if (isinstance(attr, type) and
                                issubclass(attr, BasePlatformPlugin) and
                                attr is not BasePlatformPlugin):
                            plugin_name = attr.platform_info["name"]
                            self._plugins[plugin_name] = attr
                            logger.info(f"加载插件: {plugin_name} -> {attr.__name__}")
                except Exception as e:
                    logger.error(f"加载插件 {fname} 失败: {e}")

    def get_plugin(self, platform_name: str):
        """获取指定平台的插件类"""
        return self._plugins.get(platform_name)

    def get_all_plugins(self) -> dict:
        return self._plugins.copy()

    def get_plugins_by_type(self, platform_type: str) -> dict:
        return {k: v for k, v in self._plugins.items()
                if v.platform_info.get("type") == platform_type}

    def register_plugin(self, plugin_class):
        """手动注册插件"""
        name = plugin_class.platform_info["name"]
        self._plugins[name] = plugin_class
        logger.info(f"手动注册插件: {name}")


plugin_manager = PluginManager()
