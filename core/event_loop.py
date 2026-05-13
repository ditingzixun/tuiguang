"""异步事件循环桥接 -- 在后台线程运行asyncio，暴露同步接口给PyQt6调用"""
import asyncio
import threading
import logging

logger = logging.getLogger(__name__)


class EventLoopBridge:
    """在后台线程运行asyncio事件循环

    PyQt6是同步的，Playwright/插件是异步的。
    通过此桥接，同步代码可以提交协程到后台事件循环并等待结果。
    """

    def __init__(self):
        self._loop = None
        self._thread = None
        self._running = False
        self._ready = threading.Event()

    @property
    def is_running(self):
        return self._running and self._loop is not None and self._loop.is_running()

    def start(self):
        if self._running:
            return
        self._ready.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="async-event-loop")
        self._thread.start()
        self._ready.wait(timeout=10)
        logger.info("异步事件循环已启动")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()
        logger.info("异步事件循环已退出")

    def stop(self):
        if not self._running:
            return
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self._running = False
        logger.info("异步事件循环已停止")

    def run(self, coro):
        if not self._loop or not self._running:
            raise RuntimeError("事件循环未启动")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()


event_loop = EventLoopBridge()
