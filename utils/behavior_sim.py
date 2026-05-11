"""模拟人工操作行为 - 随机延迟、鼠标轨迹、滚动等"""
import time
import random
import math
from loguru import logger
from utils.config_loader import config_loader


class BehaviorSimulator:
    """人类行为模拟器"""

    def __init__(self):
        cfg = config_loader.config.get("anti_ban", {})
        self.delay_min = cfg.get("random_delay_min", 3000) / 1000
        self.delay_max = cfg.get("random_delay_max", 8000) / 1000
        self.scroll_random = cfg.get("scroll_random", True)
        self.mouse_move_random = cfg.get("mouse_move_random", True)
        self.click_offset = cfg.get("click_offset", True)
        self.typing_vary = cfg.get("typing_speed_vary", True)

    def random_delay(self, min_sec: float = None, max_sec: float = None):
        """随机等待"""
        mn = min_sec or self.delay_min
        mx = max_sec or self.delay_max
        delay = random.uniform(mn, mx)
        time.sleep(delay)

    def human_delay(self, base: float = 1.0):
        """基于正态分布的人类延迟"""
        delay = max(0.5, random.gauss(base, base * 0.2))
        time.sleep(delay)

    async def simulate_mouse_move(self, page, start_x: int, start_y: int, end_x: int, end_y: int, steps: int = None):
        """模拟鼠标移动（贝塞尔曲线）"""
        if steps is None:
            steps = random.randint(10, 30)
        for i in range(steps + 1):
            t = i / steps
            # 二次贝塞尔曲线
            cp_x = (start_x + end_x) / 2 + random.randint(-50, 50)
            cp_y = (start_y + end_y) / 2 + random.randint(-50, 50)
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * cp_x + t ** 2 * end_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * cp_y + t ** 2 * end_y
            await page.mouse.move(x, y)
            await page.wait_for_timeout(random.randint(5, 15))

    async def human_click(self, page, selector: str):
        """模拟人类点击（带偏移）"""
        element = await page.query_selector(selector)
        if element:
            box = await element.bounding_box()
            if box:
                offset_x = random.randint(3, int(box["width"] - 3)) if self.click_offset and box["width"] > 10 else box["width"] / 2
                offset_y = random.randint(3, int(box["height"] - 3)) if self.click_offset and box["height"] > 10 else box["height"] / 2
                await page.mouse.click(box["x"] + offset_x, box["y"] + offset_y)
                return True
        return False

    async def human_type(self, page, selector: str, text: str):
        """模拟人类打字"""
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            if self.typing_vary:
                delay = random.gauss(0.08, 0.03)
                await page.wait_for_timeout(int(max(0.02, delay) * 1000))
        await self.random_delay(0.5, 1.5)

    async def random_scroll(self, page):
        """随机滚动页面"""
        if not self.scroll_random:
            return
        scroll_times = random.randint(2, 6)
        for _ in range(scroll_times):
            distance = random.randint(100, 800)
            await page.evaluate(f"window.scrollBy(0, {distance})")
            await page.wait_for_timeout(random.randint(500, 2000))
        # 有时回滚一点
        if random.random() > 0.5:
            await page.evaluate(f"window.scrollBy(0, -{random.randint(50, 300)})")
            await page.wait_for_timeout(random.randint(300, 1000))


behavior_sim = BehaviorSimulator()
