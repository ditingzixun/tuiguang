"""任务调度器 - APScheduler定时任务、风控限速、失败重试"""
import os
import time
import random
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger
from utils.config_loader import config_loader


class TaskScheduler:
    """统一任务调度器"""

    def __init__(self):
        cfg = config_loader.config.get("scheduler", {})
        self.publish_interval_min = cfg.get("publish_interval_min", 60)
        self.publish_interval_max = cfg.get("publish_interval_max", 300)
        self.daily_limit = cfg.get("daily_publish_limit", 20)
        self.retry_max = cfg.get("retry_max", 3)
        self.retry_delay = cfg.get("retry_delay", 300)
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        self._jobs = {}
        self._daily_count = 0
        self._daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=1)
        self._lock = threading.Lock()
        self._publish_queue = []
        self._db_manager = None

    def set_db_manager(self, db_manager):
        self._db_manager = db_manager

    def start(self):
        self._scheduler.start()
        # 每日限额重置任务
        self._scheduler.add_job(
            self._reset_daily_count,
            IntervalTrigger(hours=24),
            id="daily_reset",
            name="每日限额重置"
        )
        # 账号健康检查
        self._scheduler.add_job(
            self._check_account_health,
            IntervalTrigger(hours=1),
            id="health_check",
            name="账号健康检查"
        )
        # SEO定时检查
        self._scheduler.add_job(
            self._run_seo_check,
            IntervalTrigger(hours=config_loader.config.get("seo", {}).get("check_interval_hours", 6)),
            id="seo_check",
            name="SEO收录检查"
        )
        logger.info("任务调度器已启动")

    def stop(self):
        self._scheduler.shutdown(wait=False)
        logger.info("任务调度器已停止")

    def schedule_publish(self, task: dict):
        """调度单个发布任务"""
        with self._lock:
            if self._daily_count >= self.daily_limit:
                logger.warning("已达每日发布上限，任务已加入等待队列")
                self._publish_queue.append(task)
                return None

            delay = random.randint(self.publish_interval_min, self.publish_interval_max)
            run_time = datetime.now() + timedelta(seconds=delay)
            self._daily_count += 1

            job = self._scheduler.add_job(
                self._execute_publish,
                DateTrigger(run_date=run_time),
                args=[task],
                id=f"publish_{task.get('id')}_{int(time.time())}",
                name=f"发布任务-{task.get('platform')}-{task.get('title', '')[:20]}"
            )
            self._jobs[task.get("id")] = job
            logger.info(f"发布任务已调度: {task.get('platform')} @ {run_time.strftime('%H:%M:%S')}")
            return job.id

    def schedule_batch_publish(self, tasks: list, stagger: bool = True):
        """批量调度发布任务，支持错峰"""
        job_ids = []
        for i, task in enumerate(tasks):
            if stagger:
                # 错峰发布：每个任务间隔随机时间
                base_delay = i * random.randint(self.publish_interval_min, self.publish_interval_max)
                task["_base_delay"] = base_delay
            jid = self.schedule_publish(task)
            if jid:
                job_ids.append(jid)
        logger.info(f"批量调度 {len(job_ids)} 个发布任务")
        return job_ids

    def cancel_task(self, task_id: int) -> bool:
        """取消任务"""
        if task_id in self._jobs:
            self._jobs[task_id].remove()
            del self._jobs[task_id]
            return True
        return False

    def _execute_publish(self, task: dict):
        """执行发布任务"""
        logger.info(f"开始执行发布任务: {task.get('platform')} - {task.get('title', '')[:30]}")
        try:
            # 由外部设置的回调函数执行实际发布
            if hasattr(self, "_publish_callback") and self._publish_callback:
                result = self._publish_callback(task)
                if not result and task.get("retry_count", 0) < self.retry_max:
                    task["retry_count"] = task.get("retry_count", 0) + 1
                    logger.info(f"发布失败，{self.retry_delay}秒后重试 ({task['retry_count']}/{self.retry_max})")
                    time.sleep(self.retry_delay)
                    self._execute_publish(task)
        except Exception as e:
            logger.error(f"发布任务执行异常: {e}")

    def set_publish_callback(self, callback):
        """设置发布回调函数"""
        self._publish_callback = callback

    def _reset_daily_count(self):
        with self._lock:
            self._daily_count = 0
            logger.info("每日发布限额已重置")
            # 处理等待队列
            while self._publish_queue and self._daily_count < self.daily_limit:
                task = self._publish_queue.pop(0)
                self.schedule_publish(task)

    def _check_account_health(self):
        """检查账号健康状态"""
        if not self._db_manager:
            return
        session = self._db_manager.get_session()
        try:
            from db.models import Account
            accounts = session.query(Account).filter(Account.status == "active").all()
            for acc in accounts:
                if acc.score < 30:
                    acc.status = "limited"
                    logger.warning(f"账号 {acc.username} 健康分过低({acc.score})，已限制")
                if acc.last_login_at:
                    days_since = (datetime.now() - acc.last_login_at).days
                    if days_since > 7:
                        acc.score = max(0, acc.score - 10)
            session.commit()
        except Exception as e:
            logger.error(f"健康检查异常: {e}")
            session.rollback()
        finally:
            session.close()

    def _run_seo_check(self):
        """执行SEO收录检查"""
        logger.info("开始定时SEO收录检查")
        try:
            from core.seo_engine import seo_engine
            if hasattr(seo_engine, "keywords") and seo_engine.keywords:
                for kw in seo_engine.keywords:
                    seo_engine.check_keyword_rank(kw, "", "baidu")
                    time.sleep(random.uniform(2, 4))
        except Exception as e:
            logger.error(f"SEO检查异常: {e}")

    @property
    def active_jobs(self) -> list:
        jobs = self._scheduler.get_jobs()
        return [{"id": j.id, "name": j.name, "next_run": j.next_run_time} for j in jobs]

    @property
    def daily_remaining(self) -> int:
        return max(0, self.daily_limit - self._daily_count)


task_scheduler = TaskScheduler()
