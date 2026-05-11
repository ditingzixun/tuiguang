"""企查查/天眼查类B2B信息平台插件（千眼企业服务平台）"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
from loguru import logger


class QianyanPlugin(BasePlatformPlugin):
    platform_info = {
        "name": "qianyan",
        "display_name": "千眼企业服务",
        "type": "b2b",
        "login_url": "https://www.qianyan.biz/login",
        "publish_url": "https://www.qianyan.biz/user/service/add",
        "version": "1.0.0",
    }

    async def login(self) -> bool:
        try:
            await self._page.goto(self.platform_info["login_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)
            await self.fill_form_field("input[name='mobile']", self.account.get("phone", self.account["username"]))
            await behavior_sim.random_delay(1, 2)
            sms_btn = await self._page.query_selector("text=获取验证码")
            if sms_btn:
                await sms_btn.click()
                logger.info(f"[千眼] 已点击获取验证码")
                # SMS验证码逻辑由外部引擎处理
                await behavior_sim.random_delay(3, 5)
            login_btn = await self._page.query_selector("button[type='submit']")
            if login_btn:
                await login_btn.click()
                await self._page.wait_for_load_state("networkidle")
            if "login" not in self._page.url.lower():
                self._is_logged_in = True
                return True
            return False
        except Exception as e:
            logger.error(f"[千眼] 登录异常: {e}")
            return False

    async def publish(self, title: str, content: str, **kwargs) -> str | None:
        if not self._is_logged_in:
            if not await self.login():
                return None
        try:
            await self._page.goto(self.platform_info["publish_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)
            await self.fill_form_field("input[name='title']", title)
            await self.fill_form_field("textarea[name='description']", content[:500])
            company = kwargs.get("company_name", "")
            if company:
                await self.fill_form_field("input[name='company_name']", company)
            await behavior_sim.random_delay(1, 2)
            submit = await self._page.query_selector("button[type='submit'], .submit-btn")
            if submit:
                await submit.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 3)
            url = self._page.url
            return url if "add" not in url else None
        except Exception as e:
            logger.error(f"[千眼] 发布异常: {e}")
            return None
