"""黄页88 B2B平台插件"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
from loguru import logger


class Huangye88Plugin(BasePlatformPlugin):
    platform_info = {
        "name": "huangye88",
        "display_name": "黄页88",
        "type": "b2b",
        "login_url": "https://www.huangye88.com/login/",
        "publish_url": "https://www.huangye88.com/user/product/add/",
        "version": "1.0.0",
    }

    async def login(self) -> bool:
        try:
            await self._page.goto(self.platform_info["login_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 2)
            await self.fill_form_field("input[name='username']", self.account["username"])
            await self.fill_form_field("input[name='password']", self.account["password"])
            await behavior_sim.random_delay(0.5, 1)
            login_btn = await self._page.query_selector("button[type='submit']")
            if login_btn:
                await login_btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 4)
            if "login" not in self._page.url.lower():
                self._is_logged_in = True
                logger.info(f"[黄页88] 账号 {self.account['username']} 登录成功")
                return True
            logger.warning(f"[黄页88] 登录失败")
            return False
        except Exception as e:
            logger.error(f"[黄页88] 登录异常: {e}")
            return False

    async def publish(self, title: str, content: str, **kwargs) -> str | None:
        if not self._is_logged_in:
            logged_in = await self.login()
            if not logged_in:
                return None
        try:
            await self._page.goto(self.platform_info["publish_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)
            await behavior_sim.random_scroll(self._page)
            await self.fill_form_field("input[name='title']", title)
            await self.fill_form_field("textarea[name='content']", content)
            category = kwargs.get("category", "")
            if category:
                await self.fill_form_field("select[name='category_id']", category, "select")
            contact = kwargs.get("contact", self.account.get("phone", ""))
            if contact:
                await self.fill_form_field("input[name='contact']", contact)
            await behavior_sim.random_delay(1, 3)
            submit_btn = await self._page.query_selector("button[type='submit'], input[type='submit']")
            if submit_btn:
                await submit_btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 4)
            current_url = self._page.url
            logger.info(f"[黄页88] 发布完成, URL: {current_url}")
            return current_url if "add" not in current_url else None
        except Exception as e:
            logger.error(f"[黄页88] 发布异常: {e}")
            return None
