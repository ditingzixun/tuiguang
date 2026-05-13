"""自定义平台插件模板

=== 接入新平台只需4步 ===
1. 复制此文件到 plugins/b2b/ 或 plugins/media/ 或 plugins/classified/
2. 重命名文件、类名
3. 填写 platform_info (name须唯一)
4. 实现 login() 和 publish() 方法

=== publish() 可用的自动填充 kwargs ===
由主程序 _publish_callback 自动注入，插件可直接使用:
- company_name (str): 公司全称 (来自企业资料)
- company_short_name (str): 简称
- contact_person (str): 联系人
- contact_phone (str): 联系电话 (企业资料或账号手机号)
- contact_email (str): 邮箱 (账号邮箱)
- address (str): 公司地址
- website (str): 网站
- category (str): 资质/服务类型 (内容的 qualification_type)
- content_type (str): 文案类型
- images (list[str]): 图片文件路径列表
- form_config (dict): 自定义表单配置
- selectors_override (dict): 选择器覆盖 (已通过 _sel() 方法处理)

=== _sel() 辅助方法 ===
self._sel("field_name", "default_selector")
优先使用 platform_configs.selectors 中配置的覆盖选择器，否则返回默认值。
这样无需改代码即可通过UI配置选择器。
"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
import logging; logger = logging.getLogger(__name__)


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
            **kwargs: 自动填充参数 (详见文件顶部文档)
              - company_name, company_short_name, contact_person, contact_phone,
                contact_email, address, website (企业资料)
              - category, content_type (内容分类)
              - images (图片路径列表)
              - form_config, selectors_override (平台配置)

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
            # 示例（使用 _sel() 支持选择器覆盖 + 消费全部 kwargs）:
            # await behavior_sim.random_scroll(self._page)
            # await self.fill_form_field(self._sel("title_input", "input[name='title']"), title)
            # await self.fill_form_field(self._sel("content_input", "textarea[name='content']"), content)
            #
            # # 企业信息自动填充
            # if kwargs.get("company_name"):
            #     await self.fill_form_field("input[name='company']", kwargs["company_name"])
            # if kwargs.get("contact_phone"):
            #     await self.fill_form_field("input[name='phone']", kwargs["contact_phone"])
            #
            # # 分类选择
            # if kwargs.get("category"):
            #     await self.fill_form_field("select[name='category']", kwargs["category"], "select")
            #
            # # 图片上传
            # for img_path in kwargs.get("images", []):
            #     await self.upload_image("input[type='file']", img_path)
            #     await behavior_sim.random_delay(1, 2)
            #
            # # 提交发布
            # await behavior_sim.random_delay(1, 2)
            # submit = await self._page.query_selector(self._sel("submit_btn", "button[type='submit']"))
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
