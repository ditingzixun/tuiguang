"""中业网 B2B平台插件"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
import logging; logger = logging.getLogger(__name__)


class ZhongyewangPlugin(BasePlatformPlugin):
    platform_info = {
        "name": "zhongyewang",
        "display_name": "中业网",
        "type": "b2b",
        "login_url": "https://www.zhongyewang.com/login/",
        "publish_url": "https://www.zhongyewang.com/member/publish/",
        "version": "1.0.0",
    }

    async def login(self) -> bool:
        try:
            await self._page.goto(self.platform_info["login_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 2)
            await self.fill_form_field("input[name='userName']", self.account["username"])
            await self.fill_form_field("input[name='password']", self.account["password"])
            await behavior_sim.random_delay(0.5, 1.5)
            btn = await self._page.query_selector("a.login_btn, button.login-btn")
            if btn:
                await btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 3)
            self._is_logged_in = "login" not in self._page.url.lower()
            return self._is_logged_in
        except Exception as e:
            logger.error(f"[中业网] 登录异常: {e}")
            return False

    async def publish(self, title: str, content: str, **kwargs) -> str | None:
        if not self._is_logged_in:
            if not await self.login():
                return None
        try:
            await self._page.goto(self.platform_info["publish_url"], wait_until="networkidle")
            await behavior_sim.random_scroll(self._page)
            await self.fill_form_field(self._sel("title_input", "input[name='title']"), title)
            await self.fill_form_field(self._sel("content_input", "textarea[name='content']"), content)

            company_name = kwargs.get("company_name", "")
            if company_name:
                await self.fill_form_field("input[name='company']", company_name)

            contact_phone = kwargs.get("contact_phone", "")
            if contact_phone:
                await self.fill_form_field("input[name='phone']", contact_phone)

            images = kwargs.get("images", [])
            for img_path in images:
                await self.upload_image("input[type='file']", img_path)
                await behavior_sim.random_delay(1, 2)

            await behavior_sim.random_delay(1, 2)
            submit = await self._page.query_selector("input[value='发布']")
            if submit:
                await submit.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 3)
            url = self._page.url
            return url if "publish" not in url else None
        except Exception as e:
            logger.error(f"[中业网] 发布异常: {e}")
            return None
