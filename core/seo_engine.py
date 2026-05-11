"""搜索引擎收录爬虫引擎 - 自动检测收录和关键词排名监控"""
import re
import time
import random
import threading
from datetime import datetime
from typing import Optional
import requests
from bs4 import BeautifulSoup
from loguru import logger
from utils.config_loader import config_loader


class SeoEngine:
    """SEO收录监控引擎"""

    SEARCH_ENGINES = {
        "baidu": {
            "name": "百度",
            "url": "https://www.baidu.com/s",
            "param": "wd",
            "result_selector": "div.result",
            "title_selector": "h3 a",
            "link_selector": "h3 a",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        },
        "360": {
            "name": "360搜索",
            "url": "https://www.so.com/s",
            "param": "q",
            "result_selector": "li.res-list",
            "title_selector": "h3 a",
            "link_selector": "h3 a",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        },
        "bing": {
            "name": "必应",
            "url": "https://www.bing.com/search",
            "param": "q",
            "result_selector": "li.b_algo",
            "title_selector": "h2 a",
            "link_selector": "h2 a",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
        },
    }

    def __init__(self):
        cfg = config_loader.config.get("seo", {})
        self.check_interval = cfg.get("check_interval_hours", 6) * 3600
        self.engines = cfg.get("search_engines", [{"name": "baidu"}, {"name": "360"}])
        self.max_pages = cfg.get("max_pages", 5)
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        logger.info("SEO监控引擎已启动")

    def stop(self):
        self._running = False

    def check_index(self, url: str, keywords: list = None,
                    search_engine: str = "baidu") -> Optional[dict]:
        """检查指定URL是否被收录"""
        eng = self.SEARCH_ENGINES.get(search_engine)
        if not eng:
            logger.error(f"不支持的搜索引擎: {search_engine}")
            return None

        # 使用site:语法检查收录
        query = f"site:{url}"
        return self._search(query, url, search_engine, check_index=True)

    def check_keyword_rank(self, keyword: str, target_url: str,
                           search_engine: str = "baidu") -> Optional[dict]:
        """检查关键词排名"""
        eng = self.SEARCH_ENGINES.get(search_engine)
        if not eng:
            return None

        result = self._search(keyword, target_url, search_engine, check_index=False)
        if result:
            result["keyword"] = keyword
        return result

    def batch_check_ranks(self, keywords: list, target_url: str) -> list:
        """批量查询关键词排名"""
        results = []
        for kw in keywords:
            for eng_name in [e["name"] for e in self.engines]:
                result = self.check_keyword_rank(kw, target_url, eng_name)
                if result:
                    results.append(result)
                time.sleep(random.uniform(2, 5))  # 搜索限速
        return results

    def _search(self, query: str, target_url: str, engine_name: str,
                check_index: bool = False) -> Optional[dict]:
        """执行搜索"""
        eng = self.SEARCH_ENGINES[engine_name]
        try:
            params = {eng["param"]: query, "rn": 50}
            resp = requests.get(eng["url"], params=params, headers=eng["headers"], timeout=15)
            resp.encoding = resp.apparent_encoding or "utf-8"
            if resp.status_code != 200:
                logger.warning(f"{eng['name']}搜索请求失败，状态码: {resp.status_code}")
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            results = soup.select(eng["result_selector"])

            is_indexed = False
            rank = None
            found_title = None
            found_url = None

            for idx, item in enumerate(results, 1):
                link_tag = item.select_one(eng["link_selector"])
                title_tag = item.select_one(eng["title_selector"])
                if link_tag:
                    href = link_tag.get("href", "")
                    if check_index:
                        # 检查是否能找到目标URL的结果
                        if target_url.replace("https://", "").replace("http://", "").rstrip("/") in href:
                            is_indexed = True
                            found_url = href
                            if title_tag:
                                found_title = title_tag.get_text(strip=True)
                            break
                    else:
                        if target_url.replace("https://", "").replace("http://", "").rstrip("/") in href:
                            rank = idx
                            found_url = href
                            if title_tag:
                                found_title = title_tag.get_text(strip=True)
                            break

                if idx >= self.max_pages * 10:
                    break

            return {
                "search_engine": engine_name,
                "query": query,
                "is_indexed": is_indexed or (rank is not None),
                "rank": rank,
                "title": found_title,
                "url": found_url or target_url,
                "check_time": datetime.now(),
            }
        except Exception as e:
            logger.error(f"SEO查询异常 [{engine_name}]: {e}")
            return None

    def _check_loop(self):
        """定期检查循环"""
        while self._running:
            time.sleep(self.check_interval)
            logger.info("SEO定期检查开始")
            # 具体检查逻辑由外部注入关键词列表

    def set_keywords(self, keywords: list):
        self.keywords = keywords


seo_engine = SeoEngine()
