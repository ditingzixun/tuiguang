"""Playwright浏览器引擎 - 多浏览器指纹隔离，一号一箱"""
import os
import time
import asyncio
import json
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from utils.config_loader import config_loader
from utils.fingerprint import FingerprintManager
from core.proxy_engine import proxy_engine


class BrowserEngine:
    """Playwright浏览器管理引擎"""

    def __init__(self):
        cfg = config_loader.config.get("browser", {})
        self.headless = cfg.get("headless", False)
        self.default_timeout = cfg.get("default_timeout", 30000)
        self.slow_mo = cfg.get("slow_mo", 50)
        self.viewport_w = cfg.get("viewport_width", 1366)
        self.viewport_h = cfg.get("viewport_height", 768)
        self.locale = cfg.get("locale", "zh-CN")
        self.timezone_id = cfg.get("timezone_id", "Asia/Shanghai")
        self._playwright = None
        self._browser = None
        self._contexts = {}  # account_id -> BrowserContext
        self._fingerprint_mgr = FingerprintManager()
        self._initialized = False

    async def init(self):
        if self._initialized:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--window-size=1366,768",
            ]
        )
        self._initialized = True
        logger.info("Playwright浏览器引擎初始化完成")

    async def close(self):
        for ctx in self._contexts.values():
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False

    async def get_context(self, account_id: int, platform: str = "") -> BrowserContext:
        """获取或创建账号专属的浏览器上下文（一号一箱）"""
        if account_id in self._contexts:
            return self._contexts[account_id]

        # 加载或生成指纹
        fingerprint = self._fingerprint_mgr.load_fingerprint(account_id)
        if not fingerprint:
            fingerprint = self._fingerprint_mgr.generate_fingerprint(account_id, platform)

        # 代理配置
        proxy_config = proxy_engine.get_proxy_config()

        # 创建独立上下文
        context = await self._browser.new_context(
            viewport={"width": fingerprint["viewport"]["width"],
                      "height": fingerprint["viewport"]["height"]},
            user_agent=fingerprint["user_agent"],
            locale=fingerprint["locale"],
            timezone_id=fingerprint["timezone_id"],
            geolocation=fingerprint.get("geolocation"),
            color_scheme=fingerprint.get("color_scheme", "light"),
            device_scale_factor=fingerprint.get("device_scale_factor", 1),
            is_mobile=fingerprint.get("is_mobile", False),
            has_touch=fingerprint.get("has_touch", False),
            proxy=proxy_config,
            permissions=["geolocation"],
        )

        # 注入反检测脚本
        await self._inject_stealth_scripts(context, fingerprint)

        # 加载已保存的Cookies
        cookies = self._fingerprint_mgr.load_cookies(account_id)
        if cookies:
            await context.add_cookies(cookies)
            logger.info(f"账号 {account_id} 已加载历史Cookies")

        self._contexts[account_id] = context
        profile_dir = fingerprint["profile_dir"]
        logger.info(f"账号 {account_id} 创建独立浏览器上下文, 档案目录: {profile_dir}")
        return context

    async def _inject_stealth_scripts(self, context: BrowserContext, fingerprint: dict):
        """注入反检测脚本"""
        # 修改navigator属性
        await context.add_init_script("""
        // 覆盖webdriver检测
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        // 覆盖chrome对象
        window.chrome = { runtime: {} };
        // 覆盖权限查询
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
        // 覆盖plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        // 覆盖languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en']
        });
        """)

    async def new_page(self, account_id: int, platform: str = "") -> Page:
        """为指定账号创建新页面"""
        context = await self.get_context(account_id, platform)
        page = await context.new_page()
        page.set_default_timeout(self.default_timeout)
        return page

    async def save_account_cookies(self, account_id: int):
        """保存当前账号的Cookies"""
        if account_id in self._contexts:
            cookies = await self._contexts[account_id].cookies()
            self._fingerprint_mgr.save_cookies(account_id, cookies)

    async def close_context(self, account_id: int):
        """关闭指定账号的浏览器上下文"""
        if account_id in self._contexts:
            await self._contexts[account_id].close()
            del self._contexts[account_id]
            logger.info(f"账号 {account_id} 浏览器上下文已关闭")

    async def take_screenshot(self, page: Page, account_id: int, task_id: int = None) -> str:
        """截图保存"""
        os.makedirs("./data/screenshots", exist_ok=True)
        ts = task_id or "unknown"
        filename = f"screenshot_{account_id}_{ts}_{int(time.time())}.png"
        filepath = os.path.join("./data/screenshots", filename)
        await page.screenshot(path=filepath, full_page=True)
        return filepath


browser_engine = BrowserEngine()
