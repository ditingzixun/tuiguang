"""自定义平台插件模板
复制此文件创建新的平台插件，修改类名和 platform_info 即可
无需改动主程序代码
"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
from loguru import logger


class CustomPlatformPlugin(BasePlatformPlugin):
    """自定义平台插件模板

    使用步骤:
    1. 复制此文件到 plugins/b2b/ 或 plugins/media/ 目录
    2. 重命名文件和类名
    3. 修改 platform_info 字典
    4. 实现 login() 和 publish() 方法
    5. 重启程序，插件将自动加载
    """

    platform_info = {
        "name": "custom_platform",           # 平台标识(英文，唯一)
        "display_name": "自定义平台",          # 平台显示名称
        "type": "b2b",                        # b2b / classified / media / forum
        "login_url": "https://example.com/login",
        "publish_url": "https://example.com/publish",
        "version": "1.0.0",
    }

    async def login(self) -> bool:
        """实现登录逻辑

        Returns:
            bool: 登录成功返回True
        """
        try:
            await self._page.goto(self.platform_info["login_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)

            # --- 在此处实现具体的登录逻辑 ---
            # 示例：
            # await self.fill_form_field("input[name='username']", self.account["username"])
            # await self.fill_form_field("input[name='password']", self.account["password"])
            # login_btn = await self._page.query_selector("button[type='submit']")
            # if login_btn:
            #     await login_btn.click()
            #     await self._page.wait_for_load_state("networkidle")
            # --- 结束 ---

            self._is_logged_in = "login" not in self._page.url.lower()
            if self._is_logged_in:
                logger.info(f"[{self.platform_info['display_name']}] 登录成功")
            return self._is_logged_in

        except Exception as e:
            logger.error(f"[{self.platform_info['display_name']}] 登录异常: {e}")
            return False

    async def publish(self, title: str, content: str, **kwargs) -> str | None:
        """实现发布逻辑

        Args:
            title: 文章标题
            content: 文章内容
            **kwargs: 额外参数 (category, tags, contact, company_name 等)

        Returns:
            str | None: 发布成功返回文章URL，失败返回None
        """
        if not self._is_logged_in:
            if not await self.login():
                return None

        try:
            await self._page.goto(self.platform_info["publish_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)

            # --- 在此处实现具体的发布逻辑 ---
            # 示例：
            # await behavior_sim.random_scroll(self._page)
            # await self.fill_form_field("input[name='title']", title)
            # await self.fill_form_field("textarea[name='content']", content)
            #
            # # 可选：填写分类、标签等
            # category = kwargs.get("category", "")
            # if category:
            #     await self.fill_form_field("select[name='category']", category, "select")
            #
            # # 提交发布
            # await behavior_sim.random_delay(1, 2)
            # submit = await self._page.query_selector("button[type='submit']")
            # if submit:
            #     await submit.click()
            #     await self._page.wait_for_load_state("networkidle")
            #     await behavior_sim.random_delay(2, 4)
            # --- 结束 ---

            current_url = self._page.url
            logger.info(f"[{self.platform_info['display_name']}] 发布操作完成, URL: {current_url}")

            # 判断是否发布成功（通常发布后会跳转到文章页）
            if "publish" not in current_url.lower() and "edit" not in current_url.lower():
                return current_url
            return None

        except Exception as e:
            logger.error(f"[{self.platform_info['display_name']}] 发布异常: {e}")
            return None

    async def check_publish_result(self, url: str = None) -> bool:
        """（可选）检测发布结果"""
        if not url:
            return False
        try:
            await self._page.goto(url, wait_until="networkidle")
            await behavior_sim.random_delay(1, 2)
            # 检查页面是否正常显示
            title = await self._page.title()
            return title and len(title) > 0 and "404" not in title and "错误" not in title
        except Exception:
            return False

    async def delete_post(self, url: str) -> bool:
        """（可选）删除已发布的文章"""
        try:
            await self._page.goto(url, wait_until="networkidle")
            delete_btn = await self._page.query_selector("text=删除")
            if delete_btn:
                await delete_btn.click()
                await self._page.wait_for_load_state("networkidle")
                return True
        except Exception:
            pass
        return False
