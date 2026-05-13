"""任务调度器 — APScheduler定时任务、风控限速、失败重试"""
import time
import random
import threading
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader
from core.proxy_engine import proxy_engine


class TaskScheduler:

    def __init__(self):
        cfg = config_loader
        self.publish_interval_min = cfg.get_int("PUBLISH_INTERVAL_MIN", 60)
        self.publish_interval_max = cfg.get_int("PUBLISH_INTERVAL_MAX", 300)
        self.daily_limit = cfg.get_int("DAILY_PUBLISH_LIMIT", 20)
        self.retry_max = cfg.get_int("RETRY_MAX", 3)
        self.retry_delay = cfg.get_int("RETRY_DELAY", 300)
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self._jobs = {}
        self._daily_count = 0
        self._lock = threading.Lock()
        self._publish_queue = []
        self._db_manager = None

    def set_db_manager(self, db_manager):
        self._db_manager = db_manager

    def start(self):
        self._scheduler.start()
        self._scheduler.add_job(
            self._reset_daily_count,
            IntervalTrigger(hours=24),
            id="daily_reset"
        )
        logger.info("任务调度器已启动")

    def stop(self):
        self._scheduler.shutdown(wait=False)
        logger.info("任务调度器已停止")

    def schedule_publish(self, task: dict):
        with self._lock:
            if self._daily_count >= self.daily_limit:
                logger.warning("已达每日发布上限，任务已加入等待队列")
                self._publish_queue.append(task)
                return None

            # 检查平台是否被禁用
            if self._db_manager:
                cfg = self._db_manager.fetch_one(
                    "SELECT enabled FROM platform_configs WHERE plugin_name = ?",
                    (task.get('platform'),)
                )
                if cfg is not None and not cfg.get('enabled'):
                    logger.info(f"平台 {task['platform']} 已禁用，跳过任务 {task.get('id')}")
                    return None

            delay = random.randint(self.publish_interval_min, self.publish_interval_max)
            run_time = datetime.now() + timedelta(seconds=delay)
            self._daily_count += 1

            job = self._scheduler.add_job(
                self._execute_publish,
                DateTrigger(run_date=run_time),
                args=[task],
                id=f"publish_{task.get('id')}_{int(time.time())}",
            )
            self._jobs[task.get("id")] = job
            logger.info(f"发布任务已调度: {task.get('platform')} @ {run_time.strftime('%H:%M:%S')}")
            return job.id

    def schedule_batch_publish(self, tasks: list, stagger: bool = True):
        job_ids = []
        for i, task in enumerate(tasks):
            if stagger:
                task["_base_delay"] = i * random.randint(self.publish_interval_min, self.publish_interval_max)
            jid = self.schedule_publish(task)
            if jid:
                job_ids.append(jid)
        logger.info(f"批量调度 {len(job_ids)} 个发布任务")
        return job_ids

    def cancel_task(self, task_id: int) -> bool:
        if task_id in self._jobs:
            self._jobs[task_id].remove()
            del self._jobs[task_id]
            return True
        return False

    def cancel_all_publish_jobs(self):
        with self._lock:
            for task_id, job in list(self._jobs.items()):
                try:
                    job.remove()
                except Exception:
                    pass
            count = len(self._jobs)
            self._jobs.clear()
            logger.info(f"已取消 {count} 个发布任务")

    def _execute_publish(self, task: dict):
        logger.info(f"开始执行发布任务: {task.get('platform')} - {task.get('title', '')[:30]}")
        try:
            # 预分配代理
            account_id = task.get("account_id")
            proxy = proxy_engine.get_proxy(account_id) if account_id else None
            task["_proxy"] = proxy

            if hasattr(self, "_publish_callback") and self._publish_callback:
                result = self._publish_callback(task)
                if not result and task.get("retry_count", 0) < self.retry_max:
                    task["retry_count"] = task.get("retry_count", 0) + 1
                    logger.info(f"发布失败，{self.retry_delay}秒后重试 ({task['retry_count']}/{self.retry_max})")
                    time.sleep(self.retry_delay)
                    self._execute_publish(task)
                # 上报代理使用结果
                if proxy:
                    proxy_engine.mark_result(proxy, result is not None)
        except Exception as e:
            logger.error(f"发布任务执行异常: {e}")

    def set_publish_callback(self, callback):
        self._publish_callback = callback

    def _reset_daily_count(self):
        with self._lock:
            self._daily_count = 0
            logger.info("每日发布限额已重置")
            while self._publish_queue and self._daily_count < self.daily_limit:
                task = self._publish_queue.pop(0)
                self.schedule_publish(task)

    @property
    def active_jobs(self) -> list:
        jobs = self._scheduler.get_jobs()
        return [{"id": j.id, "next_run": j.next_run_time} for j in jobs]

    @property
    def daily_remaining(self) -> int:
        return max(0, self.daily_limit - self._daily_count)


task_scheduler = TaskScheduler()
