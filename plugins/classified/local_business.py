"""本地商户/分类信息平台插件 -- 演示完整 kwargs 自动填充模式

本插件作为参考实现，展示新平台接入时的最佳实践：
- 使用 _sel() 支持选择器配置覆盖
- 消费所有保证传递的 kwargs (企业信息/图片/分类/联系信息)
- 完整的错误处理和日志记录
"""
from plugins.base_plugin import BasePlatformPlugin
from utils.behavior_sim import behavior_sim
import logging; logger = logging.getLogger(__name__)


class LocalBusinessPlugin(BasePlatformPlugin):
    """本地商户/分类信息通用插件

    适用平台: 58同城、赶集网、大众点评商户、百姓网等本地分类信息平台。
    用户需要修改 platform_info 中的 URL 和选择器以适配具体平台。
    """

    platform_info = {
        "name": "local_business",
        "display_name": "本地商户(通用)",
        "type": "classified",
        "login_url": "https://example.com/login",
        "publish_url": "https://example.com/publish",
        "version": "1.0.0",
    }

    async def login(self) -> bool:
        """登录本地商户平台

        通用模式: 导航到登录页 -> 填写凭证 -> 提交 -> 检测URL变化。
        适配具体平台时，修改选择器即可。
        """
        try:
            await self._page.goto(self.platform_info["login_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)

            # 使用 _sel() 允许通过 platform_configs.selectors 覆盖选择器
            await self.fill_form_field(
                self._sel("username_input", "input[name='username']"),
                self.account.get("username", "")
            )
            await self.fill_form_field(
                self._sel("password_input", "input[name='password']"),
                self.account.get("password", "")
            )
            await behavior_sim.random_delay(1, 2)

            submit_btn = await self._page.query_selector(
                self._sel("login_btn", "button[type='submit']")
            )
            if submit_btn:
                await submit_btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(3, 5)

            self._is_logged_in = "login" not in self._page.url.lower()
            if self._is_logged_in:
                logger.info(f"[本地商户] 账号 {self.account.get('username')} 登录成功")
            return self._is_logged_in
        except Exception as e:
            logger.error(f"[本地商户] 登录异常: {e}")
            return False

    async def publish(self, title: str, content: str, **kwargs) -> str | None:
        """发布到本地商户平台 -- 完整的 kwargs 自动填充范例

        Args:
            title: 文章标题
            content: 文章内容
            **kwargs: 以下所有字段由 _publish_callback 自动填充:

                企业资料 (来自 enterprise_profile):
                - company_name (str): 公司全称
                - company_short_name (str): 简称
                - contact_person (str): 联系人
                - contact_phone (str): 联系电话
                - contact_email (str): 联系邮箱
                - address (str): 公司地址
                - website (str): 网站URL

                内容分类 (来自 contents 表):
                - category (str): 资质/服务类型
                - content_type (str): 文章类型

                附件 (来自 tasks.image_paths):
                - images (list[str]): 图片文件路径列表

                平台配置覆盖 (来自 platform_configs):
                - form_config (dict): 自定义表单配置
                - selectors_override (dict): 选择器覆盖
                  (已通过 BasePlatformPlugin._sel() 处理)

        Returns:
            str | None: 发布成功返回文章URL，失败返回None
        """
        if not self._is_logged_in:
            if not await self.login():
                return None

        try:
            await self._page.goto(self.platform_info["publish_url"], wait_until="networkidle")
            await behavior_sim.random_delay(1, 3)
            await behavior_sim.random_scroll(self._page)

            # ====== 标题和正文 ======
            await self.fill_form_field(
                self._sel("title_input", "input[name='title']"), title
            )
            await self.fill_form_field(
                self._sel("content_input", "textarea[name='content']"), content
            )

            # ====== 企业信息自动填充 ======
            company_name = kwargs.get("company_name", "")
            if company_name:
                await self.fill_form_field(
                    self._sel("company_input", "input[name='company_name']"),
                    company_name
                )

            contact_person = kwargs.get("contact_person", "")
            if contact_person:
                await self.fill_form_field(
                    self._sel("contact_input", "input[name='contact']"),
                    contact_person
                )

            contact_phone = kwargs.get("contact_phone", "")
            if contact_phone:
                await self.fill_form_field(
                    self._sel("phone_input", "input[name='phone']"),
                    contact_phone
                )

            address = kwargs.get("address", "")
            if address:
                await self.fill_form_field(
                    self._sel("address_input", "input[name='address']"),
                    address
                )

            website = kwargs.get("website", "")
            if website:
                await self.fill_form_field(
                    self._sel("website_input", "input[name='website']"),
                    website
                )

            # ====== 分类选择 ======
            category = kwargs.get("category", "")
            if category:
                await self.fill_form_field(
                    self._sel("category_select", "select[name='category']"),
                    category, "select"
                )

            # ====== 图片上传 ======
            images = kwargs.get("images", [])
            for i, img_path in enumerate(images):
                # 第一个图片作为主图，后续作为附图
                selector = (
                    self._sel("image_upload", "input[type='file']")
                    if i == 0
                    else self._sel("image_upload_extra", "input[type='file'].extra")
                )
                await self.upload_image(selector, img_path)
                await behavior_sim.random_delay(1, 2)
                logger.info(f"[本地商户] 已上传图片 {i+1}/{len(images)}: {img_path}")

            await behavior_sim.random_delay(1, 3)

            # ====== 提交发布 ======
            submit_btn = await self._page.query_selector(
                self._sel("submit_btn", "button[type='submit'], input[type='submit']")
            )
            if submit_btn:
                await submit_btn.click()
                await self._page.wait_for_load_state("networkidle")
                await behavior_sim.random_delay(2, 4)

            current_url = self._page.url
            logger.info(f"[本地商户] 发布完成, URL: {current_url}")
            return current_url if "publish" not in current_url else None

        except Exception as e:
            logger.error(f"[本地商户] 发布异常: {e}")
            return None

    async def check_publish_result(self, url: str = None) -> bool:
        """检查发布结果 -- 访问URL验证文章可访问"""
        if not url:
            return False
        try:
            await self._page.goto(url, wait_until="networkidle")
            await behavior_sim.random_delay(1, 2)
            page_title = await self._page.title()
            is_valid = bool(page_title) and "404" not in page_title and "error" not in page_title.lower()
            logger.info(f"[本地商户] 发布验证: {is_valid}, 页面标题: {page_title}")
            return is_valid
        except Exception as e:
            logger.error(f"[本地商户] 验证异常: {e}")
            return False
