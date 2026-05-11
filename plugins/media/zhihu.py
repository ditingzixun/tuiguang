"""知乎自媒体平台插件"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
from loguru import logger


class ZhihuPlugin(BasePlatformPlugin):
    platform_info = {
        "name": "zhihu",
        "display_name": "知乎",
        "type": "media",
        "login_url": "https://www.zhihu.com/signin",
        "publish_url": "https://zhuanlan.zhihu.com/write",
        "version": "1.0.0",
    }

    async def login(self) -> bool:
        try:
            await self._page.goto(self.platform_info["login_url"], wait_until="networkidle")
            await behavior_sim.random_delay(2, 4)
            # 切换到密码登录
            switch_btn = await self._page.query_selector("text=密码登录")
            if switch_btn:
                await switch_btn.click()
                await behavior_sim.random_delay(1, 2)
            await self.fill_form_field("input[name='username']", self.account["username"])
            await self.fill_form_field("input[name='password']", self.account["password"])
            await behavior_sim.random_delay(1, 2)
            login_btn = await self._page.query_selector("button[type='submit']")
            if login_btn:
                await login_btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 4)
            self._is_logged_in = "signin" not in self._page.url.lower()
            if self._is_logged_in:
                logger.info(f"[知乎] 账号 {self.account['username']} 登录成功")
            return self._is_logged_in
        except Exception as e:
            logger.error(f"[知乎] 登录异常: {e}")
            return False

    async def publish(self, title: str, content: str, **kwargs) -> str | None:
        if not self._is_logged_in:
            if not await self.login():
                return None
        try:
            await self._page.goto(self.platform_info["publish_url"], wait_until="networkidle")
            await behavior_sim.random_delay(2, 4)
            await behavior_sim.random_scroll(self._page)
            title_input = await self._page.query_selector("textarea[placeholder='请输入标题']")
            if title_input:
                await title_input.click()
                await behavior_sim.random_delay(0.5, 1)
                await self._page.keyboard.type(title, delay=100)
            content_editor = await self._page.query_selector(".public-DraftEditor-content")
            if content_editor:
                await content_editor.click()
                await behavior_sim.random_delay(0.5, 1)
                for paragraph in content.split("\n"):
                    await self._page.keyboard.type(paragraph, delay=50)
                    await self._page.keyboard.press("Enter")
                    await behavior_sim.random_delay(0.3, 0.8)
            publish_btn = await self._page.query_selector("button:has-text('发布')")
            if publish_btn:
                await publish_btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(3, 5)
            url = self._page.url
            return url if "write" not in url else None
        except Exception as e:
            logger.error(f"[知乎] 发布异常: {e}")
            return None
