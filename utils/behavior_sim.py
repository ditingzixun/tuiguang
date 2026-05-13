"""模拟人工操作行为 — 贝塞尔鼠标轨迹、阅读节奏滚动、停留时间分布"""
import asyncio
import random
import math
import logging; logger = logging.getLogger(__name__)
from utils.config_loader import config_loader


class BehaviorSimulator:
    """人类行为模拟器 — 对抗自动化检测"""

    def __init__(self):
        self.delay_min = 3.0
        self.delay_max = 8.0
        self.scroll_random = True
        self.mouse_move_random = True
        self.click_offset = True
        self.typing_vary = True

    # ====== 基础延迟 ======

    async def random_delay(self, min_sec: float = None, max_sec: float = None):
        """异步随机等待"""
        mn = min_sec or self.delay_min
        mx = max_sec or self.delay_max
        await asyncio.sleep(random.uniform(mn, mx))

    async def human_delay(self, base: float = 1.0):
        """基于正态分布的人类延迟（对数正态更贴近真实分布）"""
        delay = max(0.3, random.lognormvariate(math.log(base), 0.25))
        await asyncio.sleep(delay)

    # ====== 鼠标行为 ======

    async def simulate_mouse_move(self, page, start_x: int, start_y: int,
                                   end_x: int, end_y: int, steps: int = None):
        """带速度曲线的贝塞尔曲线鼠标移动

        模拟真实人手移动鼠标的三个阶段：
        1. 加速段（0→30%）：缓慢启动
        2. 匀速段（30%→70%）：快速移动
        3. 减速段（70%→100%）：接近目标时放缓

        约 15% 概率出现 overshooting（超出目标再修正）
        """
        if steps is None:
            steps = random.randint(20, 45)

        # 控制点随机偏移
        cp_x = (start_x + end_x) / 2 + random.randint(-80, 80)
        cp_y = (start_y + end_y) / 2 + random.randint(-80, 80)

        overshoot = random.random() < 0.15 and steps > 15
        overshoot_idx = steps + random.randint(2, 8) if overshoot else 0
        overshoot_x = end_x + random.randint(15, 40) * (1 if random.random() > 0.5 else -1)
        overshoot_y = end_y + random.randint(10, 25) * (1 if random.random() > 0.5 else -1)

        total_steps = overshoot_idx if overshoot else steps

        for i in range(total_steps + 1):
            # 使用缓动函数生成速度曲线
            t_raw = i / max(total_steps, 1)

            if overshoot and i >= steps:
                # overshooting 阶段：从目标位置移动到 overshoot 位置
                t_over = (i - steps) / max(overshoot_idx - steps, 1)
                x = end_x + (overshoot_x - end_x) * t_over
                y = end_y + (overshoot_y - end_y) * t_over
            else:
                # 正常贝塞尔曲线 + 缓动
                t = _ease_in_out_cubic(t_raw)

                # 二次贝塞尔曲线
                x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * cp_x + t ** 2 * end_x
                y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * cp_y + t ** 2 * end_y

            await page.mouse.move(x, y)

            # 步骤间延迟：加速段长、匀速段短、减速段长
            if i < total_steps * 0.3:
                step_delay = random.randint(8, 18)
            elif i < total_steps * 0.7:
                step_delay = random.randint(3, 8)
            else:
                step_delay = random.randint(10, 22)

            await page.wait_for_timeout(step_delay)

        # overshooting 后回到目标位置
        if overshoot:
            await page.wait_for_timeout(random.randint(30, 80))
            for i in range(random.randint(4, 8)):
                t = i / 7.0
                x = overshoot_x + (end_x - overshoot_x) * _ease_out_quad(t)
                y = overshoot_y + (end_y - overshoot_y) * _ease_out_quad(t)
                await page.mouse.move(x, y)
                await page.wait_for_timeout(random.randint(10, 20))

    async def micro_movements(self, page, duration_sec: float = None):
        """模拟手部微颤 — 在页面停留时产生微小鼠标抖动"""
        if duration_sec is None:
            duration_sec = random.uniform(0.3, 1.5)

        try:
            # 获取当前鼠标位置作为"锚点"
            viewport = page.viewport_size
            if not viewport:
                return
            anchor_x = random.randint(200, viewport['width'] - 200)
            anchor_y = random.randint(200, viewport['height'] - 200)

            elapsed = 0.0
            while elapsed < duration_sec:
                jitter_x = anchor_x + random.randint(-8, 8)
                jitter_y = anchor_y + random.randint(-6, 6)
                await page.mouse.move(jitter_x, jitter_y)
                await page.wait_for_timeout(random.randint(60, 200))
                elapsed += random.uniform(0.06, 0.2)
        except Exception:
            pass  # 微动失败不影响主流程

    async def human_click(self, page, selector: str):
        """模拟人类点击 — 带随机偏移，先移动到目标再点击"""
        element = await page.query_selector(selector)
        if not element:
            return False
        box = await element.bounding_box()
        if not box:
            return False

        # 在元素内部随机偏移
        margin_x, margin_y = 4, 4
        if box["width"] > 16:
            margin_x = int(box["width"] * 0.15)
        if box["height"] > 16:
            margin_y = int(box["height"] * 0.15)

        target_x = box["x"] + random.randint(margin_x, max(margin_x + 1, int(box["width"] - margin_x)))
        target_y = box["y"] + random.randint(margin_y, max(margin_y + 1, int(box["height"] - margin_y)))

        # 从视口随机位置移动到目标（如果视口已知）
        viewport = page.viewport_size
        if viewport:
            start_x = random.randint(50, viewport['width'] - 50)
            start_y = random.randint(50, viewport['height'] - 50)
        else:
            start_x = target_x + random.randint(-200, 200)
            start_y = target_y + random.randint(-150, 150)

        await self.simulate_mouse_move(page, start_x, start_y, target_x, target_y)
        await page.wait_for_timeout(random.randint(40, 120))
        await page.mouse.click(target_x, target_y)
        return True

    # ====== 键盘行为 ======

    async def human_type(self, page, selector: str, text: str):
        """模拟人类打字 — 字符间延迟符合正态分布，偶有停顿"""
        await page.click(selector)
        await page.wait_for_timeout(random.randint(100, 300))

        for i, char in enumerate(text):
            await page.keyboard.type(char)

            # 字符间延迟：大多数很快，偶有停顿
            if self.typing_vary:
                if random.random() < 0.08:
                    # 模拟思考停顿（8%概率）
                    await page.wait_for_timeout(random.randint(200, 600))
                else:
                    delay_ms = max(30, int(random.gauss(80, 30)))
                    await page.wait_for_timeout(delay_ms)

            # 每打10-15个字符后轻微停顿（调整手位）
            if i > 0 and i % random.randint(10, 15) == 0:
                await page.wait_for_timeout(random.randint(100, 250))

        await self.random_delay(0.3, 1.0)

    # ====== 滚动行为 ======

    async def random_scroll(self, page):
        """随机滚动页面 — 模拟浏览行为"""
        if not self.scroll_random:
            return

        scroll_count = random.randint(2, 6)
        for _ in range(scroll_count):
            distance = random.randint(150, 900)
            await self._smooth_scroll(page, distance)
            await page.wait_for_timeout(random.randint(400, 1800))

        # 约 60% 概率回滚一小段
        if random.random() < 0.6:
            back = random.randint(40, 250)
            await self._smooth_scroll(page, -back)
            await page.wait_for_timeout(random.randint(200, 800))

    async def human_scroll_with_pause(self, page, total_distance: int = None,
                                        pause_probability: float = 0.35):
        """模拟阅读节奏滚动 — 滚动一段→停顿阅读→再滚动

        停顿期间模拟微动，模拟真实用户在阅读内容。
        """
        if total_distance is None:
            total_distance = random.randint(600, 3000)

        remaining = total_distance
        while remaining > 20:
            # 每次滚动一段
            segment = random.randint(150, min(500, remaining))
            await self._smooth_scroll(page, segment)
            remaining -= segment

            # 阅读停顿
            if random.random() < pause_probability:
                pause_sec = random.lognormvariate(math.log(2.5), 0.6)
                await page.wait_for_timeout(int(pause_sec * 1000))

                # 停顿期间的微动
                if random.random() < 0.4:
                    await self.micro_movements(page, random.uniform(0.2, 0.8))

            # 偶尔回滚（重新阅读）
            if random.random() < 0.12:
                back = random.randint(30, 120)
                await self._smooth_scroll(page, -back)
                remaining += back
                await page.wait_for_timeout(random.randint(300, 900))

            await page.wait_for_timeout(random.randint(300, 1200))

    async def _smooth_scroll(self, page, distance: int, duration_ms: int = None):
        """平滑滚动 — 缓入缓出"""
        if duration_ms is None:
            duration_ms = random.randint(200, 600)

        steps = random.randint(10, 20)
        for i in range(steps + 1):
            t = i / steps
            eased = _ease_in_out_sine(t)
            step_dist = distance * (eased - _ease_in_out_sine((i - 1) / steps)) if i > 0 else 0
            if abs(step_dist) > 1:
                await page.evaluate(f"window.scrollBy(0, {int(step_dist)})")
            await page.wait_for_timeout(duration_ms // steps)

    # ====== 页面停留 ======

    async def page_dwell(self, page, content_length_hint: int = None):
        """模拟页面停留时间 — 基于内容长度的对数正态分布

        内容越长停留时间越久，但非线性的：
        - 短文（<500字）: 8-20秒
        - 中文（500-2000字）: 15-45秒
        - 长文（>2000字）: 30-90秒
        """
        if content_length_hint is None:
            content_length_hint = random.randint(300, 2000)

        if content_length_hint < 500:
            median = random.uniform(10, 18)
        elif content_length_hint < 2000:
            median = random.uniform(20, 40)
        else:
            median = random.uniform(35, 70)

        dwell = random.lognormvariate(math.log(median), 0.4)
        dwell = max(5, min(120, dwell))

        # 停留期间模拟浏览行为
        elapsed = 0.0
        while elapsed < dwell:
            action = random.random()

            if action < 0.3:
                # 滚动一段
                await self._smooth_scroll(page, random.randint(100, 400))
                elapsed += random.uniform(0.5, 1.5)
            elif action < 0.5:
                # 微动
                await self.micro_movements(page, random.uniform(0.3, 1.0))
                elapsed += random.uniform(0.3, 1.0)
            elif action < 0.55:
                # 回滚
                await self._smooth_scroll(page, -random.randint(30, 150))
                elapsed += random.uniform(0.4, 0.9)
            else:
                # 纯停顿（阅读）
                pause = random.uniform(0.8, 3.0)
                await page.wait_for_timeout(int(pause * 1000))
                elapsed += pause

    # ====== 辅助函数 ======

    async def wait_page_load(self, page):
        """等待页面加载完成 + 随机额外延迟"""
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await self.random_delay(0.5, 2.0)

    async def simulate_human_browsing(self, page, duration_sec: float = None):
        """综合模拟一次人类浏览会话

        包含：加载→快速扫描滚动→阅读停顿→微动→随机操作
        """
        if duration_sec is None:
            duration_sec = random.uniform(5, 20)

        await self.wait_page_load(page)
        await self.micro_movements(page, random.uniform(0.3, 0.8))

        elapsed = 0.0
        while elapsed < duration_sec:
            r = random.random()
            if r < 0.35:
                await self._smooth_scroll(page, random.randint(100, 500))
                elapsed += random.uniform(0.4, 1.0)
            elif r < 0.55:
                await self.micro_movements(page, random.uniform(0.3, 1.2))
                elapsed += random.uniform(0.3, 1.2)
            elif r < 0.65:
                await self._smooth_scroll(page, -random.randint(30, 200))
                elapsed += random.uniform(0.3, 0.7)
            else:
                pause = random.uniform(0.5, 2.5)
                await page.wait_for_timeout(int(pause * 1000))
                elapsed += pause


# ====== 缓动函数 ======

def _ease_in_out_cubic(t: float) -> float:
    """三次缓入缓出"""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def _ease_in_out_sine(t: float) -> float:
    """正弦缓入缓出 — 滚动最自然"""
    return -(math.cos(math.pi * t) - 1) / 2


def _ease_out_quad(t: float) -> float:
    """二次缓出 — 用于 overshooting 修正"""
    return 1 - (1 - t) ** 2


behavior_sim = BehaviorSimulator()
