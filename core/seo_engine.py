"""搜索引擎收录监控引擎 -- 百度/360/搜狗爬虫 + 排名检测 + 自动重发"""
import re
import time
import random
import threading
import logging
from utils.helpers import format_datetime
from typing import Optional
from urllib.parse import urlparse, quote

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader


SEARCH_ENGINES = {
    "baidu": {
        "name": "百度",
        "search_url": "https://www.baidu.com/s",
        "params": {"wd": "{query}", "pn": "{offset}"},
        "offset_step": 10,
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    },
    "360": {
        "name": "360搜索",
        "search_url": "https://www.so.com/s",
        "params": {"q": "{query}", "pn": "{page}"},
        "offset_step": 1,
        "headers": {
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.8",
        },
    },
    "sogou": {
        "name": "搜狗",
        "search_url": "https://www.sogou.com/web",
        "params": {"query": "{query}", "page": "{page}"},
        "offset_step": 1,
        "headers": {
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "zh-CN,zh;q=0.8",
        },
    },
}


EMPTY_SEARCH_RESULT = {"is_indexed": False, "position": 0, "found_url": "", "title": "", "snippet": ""}

# 每个引擎的结果解析配置: (容器选择器, 链接选择器, 摘要选择器)
_PARSE_CONFIGS = {
    "baidu": {
        "containers": "div.result.c-container, div.c-container",
        "link": "h3.t a, a[href]",
        "snippet": "span.content-right_8Zs40, .c-abstract, .c-span-last",
        "check_title": True,  # 百度还在标题中检查目标URL
    },
    "360": {
        "containers": "li.res-list",
        "link": "h3.res-title a, a",
        "snippet": ".res-desc, p",
        "check_title": False,
    },
    "sogou": {
        "containers": "div.rb, div.vrwrap, div.vr-title",
        "link": "h3.vrTitle a, a",
        "snippet": "div.space-txt, .str-text, p",
        "check_title": False,
    },
}


def _parse_results(soup, target_url, engine_name):
    cfg = _PARSE_CONFIGS.get(engine_name)
    if not cfg:
        return dict(EMPTY_SEARCH_RESULT)

    result = dict(EMPTY_SEARCH_RESULT)
    check_title = cfg.get("check_title", False)
    containers = soup.select(cfg["containers"])
    for pos, container in enumerate(containers, 1):
        link = container.select_one(cfg["link"])
        if not link:
            continue
        href = link.get("href", "")
        title = link.get_text(strip=True)
        snippet_el = container.select_one(cfg["snippet"])
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        matched = (target_url in href) or (check_title and target_url in title)
        if matched:
            result.update(is_indexed=True, position=pos, found_url=href, title=title, snippet=snippet)
            return result
    return result


class SeoEngine:
    """搜索引擎收录监控引擎（单例）"""

    def __init__(self):
        cfg = config_loader
        self.enabled = cfg.get_bool("SEO_ENABLED", False)
        self.check_interval_hours = cfg.get_int("SEO_CHECK_INTERVAL_HOURS", 6)
        self.engine_names = [e.strip() for e in cfg.get("SEO_SEARCH_ENGINES", "baidu,360").split(",") if e.strip()]
        self.max_pages = cfg.get_int("SEO_MAX_RESULT_PAGES", 3)
        self.auto_republish = cfg.get_bool("SEO_AUTO_REPUBLISH", False)
        self.request_delay = cfg.get_int("SEO_REQUEST_DELAY", 5)

        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._db_manager = None
        self._ua = UserAgent()
        self._session = None

    def set_db_manager(self, db_manager):
        self._db_manager = db_manager

    def start(self):
        if not self.enabled:
            logger.info("SEO收录监控未启用")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._main_loop, daemon=True, name="seo-engine")
        self._thread.start()
        logger.info(f"SEO收录监控已启动 (间隔={self.check_interval_hours}h, 引擎={self.engine_names})")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("SEO收录监控已停止")


    def _main_loop(self):
        while self._running:
            try:
                self.batch_check_all()
            except Exception as e:
                logger.error(f"SEO监控循环异常: {e}")

            for _ in range(self.check_interval_hours * 3600):
                if not self._running:
                    break
                time.sleep(1)


    def _get_session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": self._ua.chrome,
            })
        return self._session

    def _rotate_ua(self):
        try:
            ua = self._ua.chrome
            if self._session:
                self._session.headers["User-Agent"] = ua
        except Exception:
            pass

    def _search(self, query: str, target_url: str, engine_name: str, max_pages: int = None) -> dict:
        """通用搜索：在指定搜索引擎中搜索query，在结果中查找target_url

        Returns:
            {"is_indexed": bool, "position": int, "found_url": str, "title": str, "snippet": str}
            position=0 表示未找到
        """
        if max_pages is None:
            max_pages = self.max_pages

        engine = SEARCH_ENGINES.get(engine_name)
        if not engine:
            return dict(EMPTY_SEARCH_RESULT)

        if engine_name not in _PARSE_CONFIGS:
            return dict(EMPTY_SEARCH_RESULT)

        session = self._get_session()
        self._rotate_ua()
        offset_step = engine["offset_step"]

        for page in range(max_pages):
            offset = page * offset_step

            if engine_name == "baidu":
                full_url = f"{engine['search_url']}?wd={quote(query)}&pn={offset}"
                params = None
            elif engine_name == "360":
                full_url = f"{engine['search_url']}?q={quote(query)}&pn={page + 1 if page > 0 else ''}"
                params = None
            else:  # sogou
                full_url = f"{engine['search_url']}?query={quote(query)}&page={page + 1 if page > 0 else 1}"
                params = None

            try:
                resp = session.get(
                    full_url,
                    timeout=15,
                    headers=engine.get("headers", {}),
                )
                resp.encoding = resp.apparent_encoding or "utf-8"

                if resp.status_code != 200:
                    logger.warning(f"{engine_name} 返回状态码 {resp.status_code}")
                    continue

                soup = BeautifulSoup(resp.text, "lxml")
                result = _parse_results(soup, target_url, engine_name)

                if result["is_indexed"]:
                    return result

            except requests.RequestException as e:
                logger.error(f"{engine_name} 请求异常: {e}")
                continue
            except Exception as e:
                logger.error(f"{engine_name} 解析异常: {e}")
                continue

            # 页间延迟
            delay = random.uniform(self.request_delay, self.request_delay + 3)
            time.sleep(delay)

        return dict(EMPTY_SEARCH_RESULT)


    def check_index(self, url: str, engine_name: str = None) -> dict:
        """检测URL是否被搜索引擎收录

        使用 site:domain 搜索语法，在所有配置的引擎中查找。
        """
        if not url:
            return {"indexed_engines": [], "details": {}}

        engines = [engine_name] if engine_name else self.engine_names
        result = {"indexed_engines": [], "details": {}}

        for eng in engines:
            try:
                domain = urlparse(url).netloc or url
                query = f"site:{domain} {url}"
                r = self._search(query, url, eng, max_pages=1)
                result["details"][eng] = r
                if r["is_indexed"]:
                    result["indexed_engines"].append(eng)
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                logger.error(f"check_index [{eng}] 异常: {e}")
                result["details"][eng] = {"is_indexed": False, "position": 0, "error": str(e)}

        return result


    def check_keyword_rank(self, keyword: str, target_url: str, engine_name: str = None) -> dict:
        """检测关键词在搜索引擎中的排名"""
        engines = [engine_name] if engine_name else self.engine_names
        result = {"keyword": keyword, "target_url": target_url, "rankings": {}}

        for eng in engines:
            try:
                r = self._search(keyword, target_url, eng, max_pages=self.max_pages)
                result["rankings"][eng] = r
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                logger.error(f"check_keyword_rank [{eng}] 异常: {e}")
                result["rankings"][eng] = {"is_indexed": False, "position": 0, "error": str(e)}

        return result


    def batch_check_all(self):
        """批量检查：收录检测 + 关键词排名"""
        if not self._db_manager:
            return

        now = format_datetime()
        logger.info(f"[{now}] 开始SEO批量检查...")

        self.check_published_urls()
        self.check_all_keywords()

        logger.info(f"[{now}] SEO批量检查完成")

    def check_published_urls(self):
        """对所有已发布URL执行收录检测，自动重发未收录的"""
        if not self._db_manager:
            return

        with self._lock:
            records = self._db_manager.fetch_all(
                "SELECT * FROM publish_records WHERE status = 'published' AND url != '' "
                "ORDER BY created_at DESC LIMIT 50"
            )

        if not records:
            logger.info("没有待检测的已发布URL")
            return

        logger.info(f"开始收录检测: {len(records)} 条发布记录")
        now = format_datetime()
        not_indexed = []

        for rec in records:
            url = rec["url"]
            result = self.check_index(url)

            # 记录检测结果
            for eng, detail in result["details"].items():
                self._db_manager.insert("seo_rankings", {
                    "keyword_id": 0,
                    "keyword": f"[收录检测] {url[:80]}",
                    "search_engine": eng,
                    "check_type": "index",
                    "rank_position": detail.get("position", 0),
                    "found_url": detail.get("found_url", ""),
                    "title": detail.get("title", ""),
                    "snippet": detail.get("snippet", ""),
                    "is_indexed": 1 if detail.get("is_indexed") else 0,
                    "check_time": now,
                    "created_at": now,
                })

            if not result["indexed_engines"]:
                not_indexed.append(rec)
                logger.info(f"未收录: {url[:80]}")

            time.sleep(random.uniform(3, 8))

        # 自动重发未收录的
        if not_indexed and self.auto_republish:
            logger.info(f"自动重发 {len(not_indexed)} 条未收录URL")
            for rec in not_indexed:
                self._re_publish(rec)
                time.sleep(random.uniform(2, 5))

    def check_all_keywords(self):
        """对所有启用的关键词执行排名检测"""
        if not self._db_manager:
            return

        keywords = self._db_manager.fetch_all(
            "SELECT * FROM seo_keywords WHERE enabled = 1"
        )
        if not keywords:
            return

        logger.info(f"开始排名检测: {len(keywords)} 个关键词")
        now = format_datetime()
        enterprise = self._db_manager.get_enterprise_profile()
        default_url = enterprise["website"] or "" if enterprise else ""

        for kw in keywords:
            target_url = kw["target_url"] or "" or default_url

            if not target_url:
                continue

            result = self.check_keyword_rank(kw["keyword"], target_url)

            for eng, detail in result["rankings"].items():
                self._db_manager.insert("seo_rankings", {
                    "keyword_id": kw["id"],
                    "keyword": kw["keyword"],
                    "search_engine": eng,
                    "check_type": "rank",
                    "rank_position": detail.get("position", 0),
                    "found_url": detail.get("found_url", ""),
                    "title": detail.get("title", ""),
                    "snippet": detail.get("snippet", ""),
                    "is_indexed": 1 if detail.get("is_indexed") else 0,
                    "check_time": now,
                    "created_at": now,
                })

            # 更新关键词最新检查时间
            self._db_manager.update("seo_keywords", {"updated_at": now}, "id = ?", (kw["id"],))

            time.sleep(random.uniform(4, 10))


    def _re_publish(self, record: dict):
        """对未收录的文章重新发起发布"""
        if not self._db_manager:
            return

        task = self._db_manager.fetch_one("SELECT * FROM tasks WHERE id = ?", (record["task_id"],))
        if not task:
            logger.warning(f"找不到原始任务 task_id={record['task_id']}")
            return

        now = format_datetime()
        new_task = {
            "name": f"重发-{(task['name'] or 'unknown')[:40]}",
            "platform": task["platform"],
            "account_id": task["account_id"],
            "content_id": task["content_id"],
            "title": task["title"] or "",
            "content": task["content"] or "",
            "image_paths": task["image_paths"] or "[]",
            "status": "pending",
            "max_retries": task["max_retries"] or 3,
            "created_at": now,
            "updated_at": now,
        }
        new_id = self._db_manager.insert("tasks", new_task)

        self._db_manager.insert("anomaly_records", {
            "account_id": record["account_id"] or 0,
            "anomaly_type": "seo_not_indexed",
            "description": f"URL未被收录，自动重新发布 #{new_id}: {(record['url'] or '')[:120]}",
            "created_at": now,
        })

        from scheduler.task_scheduler import task_scheduler
        task_dict = {
            "id": new_id,
            "platform": task["platform"],
            "title": task["title"] or "",
            "content": task["content"] or "",
            "account_id": task["account_id"],
            "content_id": task["content_id"],
            "image_paths": task["image_paths"] or "[]",
        }
        try:
            task_scheduler.schedule_publish(task_dict)
            logger.info(f"已创建重发任务 #{new_id} (原始: #{task['id']})")
        except Exception as e:
            logger.error(f"调度重发任务失败: {e}")


    def generate_report(self, keyword_group: str = None,
                         date_from: str = None, date_to: str = None) -> list:
        """生成排名报表数据"""
        if not self._db_manager:
            return []

        sql = """
            SELECT r.keyword, r.search_engine, r.check_type,
                   r.rank_position, r.is_indexed, r.found_url, r.title,
                   r.snippet, r.check_time,
                   k.group_name, k.target_url
            FROM seo_rankings r
            LEFT JOIN seo_keywords k ON r.keyword_id = k.id
            WHERE 1=1
        """
        params = []

        if keyword_group:
            sql += " AND k.group_name = ?"
            params.append(keyword_group)
        if date_from:
            sql += " AND r.check_time >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND r.check_time <= ?"
            params.append(date_to)

        sql += " ORDER BY r.check_time DESC, r.rank_position ASC"
        return self._db_manager.fetch_all(sql, tuple(params))

    def export_report_csv(self, path: str, keyword_group: str = None) -> int:
        """导出排名报表为CSV文件"""
        import csv

        rows = self.generate_report(keyword_group=keyword_group)
        if not rows:
            return 0

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "keyword", "search_engine", "check_type", "rank_position",
                "is_indexed", "found_url", "title", "snippet", "check_time",
                "group_name", "target_url"
            ])
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        return len(rows)


    def add_keyword(self, keyword: str, target_url: str = "",
                    group_name: str = "") -> Optional[int]:
        """添加监控关键词，返回ID"""
        if not self._db_manager:
            return None
        existing = self._db_manager.fetch_one(
            "SELECT id FROM seo_keywords WHERE keyword = ?", (keyword,)
        )
        if existing:
            return existing["id"]
        now = format_datetime()
        return self._db_manager.insert("seo_keywords", {
            "keyword": keyword,
            "target_url": target_url,
            "group_name": group_name,
            "created_at": now,
            "updated_at": now,
        })

    def delete_keyword(self, keyword_id: int):
        if self._db_manager:
            self._db_manager.delete("seo_keywords", "id = ?", (keyword_id,))

    def get_stats(self) -> dict:
        """获取监控统计"""
        if not self._db_manager:
            return {"total_keywords": 0, "indexed": 0, "avg_rank": 0, "index_rate": 0}

        total = self._db_manager.fetch_one("SELECT COUNT(*) as cnt FROM seo_keywords WHERE enabled = 1")
        total_cnt = total["cnt"] if total else 0

        # 最新检查中已收录的关键词数
        last_check = self._db_manager.fetch_one(
            "SELECT MAX(check_time) as last_time FROM seo_rankings"
        )
        indexed = 0
        avg_rank = 0
        if last_check and last_check["last_time"]:
            row = self._db_manager.fetch_one(
                "SELECT COUNT(DISTINCT keyword_id) as cnt, AVG(rank_position) as avg "
                "FROM seo_rankings "
                "WHERE is_indexed = 1 AND check_type = 'rank' AND check_time = ?",
                (last_check["last_time"],)
            )
            indexed = row["cnt"] if row else 0
            avg_rank = int(row["avg"]) if row and row["avg"] else 0

        return {
            "total_keywords": total_cnt,
            "indexed": indexed,
            "avg_rank": avg_rank,
            "index_rate": round(indexed / total_cnt * 100, 1) if total_cnt > 0 else 0,
        }


    def force_check_index(self):
        self.check_published_urls()

    def force_check_rank(self):
        self.check_all_keywords()

    def force_check_all(self):
        self.batch_check_all()


seo_engine = SeoEngine()
