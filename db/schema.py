"""数据库Schema定义 — 7张核心表的CREATE TABLE语句"""

TABLE_SQL = {
    "accounts": """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            cookies_path TEXT DEFAULT '',
            profile_path TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            login_status TEXT DEFAULT 'pending',
            score INTEGER DEFAULT 100,
            last_login_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "tasks": """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_id INTEGER,
            content_id INTEGER,
            title TEXT DEFAULT '',
            content TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            scheduled_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            result_url TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "publish_records": """
        CREATE TABLE IF NOT EXISTS publish_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            account_id INTEGER,
            platform TEXT NOT NULL,
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            screenshot_path TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            publish_time TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "contents": """
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT '',
            qualification_type TEXT DEFAULT '',
            keywords TEXT DEFAULT '',
            source TEXT DEFAULT 'local',
            used_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'approved',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "platform_configs": """
        CREATE TABLE IF NOT EXISTS platform_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_name TEXT NOT NULL UNIQUE,
            plugin_name TEXT NOT NULL,
            platform_type TEXT DEFAULT 'b2b',
            login_url TEXT DEFAULT '',
            publish_url TEXT DEFAULT '',
            form_config TEXT DEFAULT '{}',
            selectors TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "proxies": """
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            protocol TEXT DEFAULT 'http',
            username TEXT DEFAULT '',
            password TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            latency_ms INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            consecutive_failures INTEGER DEFAULT 0,
            source TEXT DEFAULT 'api',
            last_check_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "proxy_bindings": """
        CREATE TABLE IF NOT EXISTS proxy_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL UNIQUE,
            proxy_id INTEGER NOT NULL,
            bound_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY (proxy_id) REFERENCES proxies(id) ON DELETE CASCADE
        )
    """,
    "account_groups": """
        CREATE TABLE IF NOT EXISTS account_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#0078d4',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "anomaly_records": """
        CREATE TABLE IF NOT EXISTS anomaly_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            anomaly_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
    """,
    "enterprise_profile": """
        CREATE TABLE IF NOT EXISTS enterprise_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            short_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            contact_person TEXT DEFAULT '',
            address TEXT DEFAULT '',
            website TEXT DEFAULT '',
            description TEXT DEFAULT '',
            logo_path TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "seo_keywords": """
        CREATE TABLE IF NOT EXISTS seo_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            target_url TEXT DEFAULT '',
            group_name TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "keyword_history": """
        CREATE TABLE IF NOT EXISTS keyword_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL UNIQUE,
            usage_count INTEGER DEFAULT 1,
            last_used_at TEXT DEFAULT (datetime('now','localtime')),
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """,
    "seo_rankings": """
        CREATE TABLE IF NOT EXISTS seo_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            search_engine TEXT NOT NULL,
            check_type TEXT NOT NULL,
            rank_position INTEGER DEFAULT 0,
            found_url TEXT DEFAULT '',
            title TEXT DEFAULT '',
            snippet TEXT DEFAULT '',
            is_indexed INTEGER DEFAULT 0,
            check_time TEXT DEFAULT (datetime('now','localtime')),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (keyword_id) REFERENCES seo_keywords(id) ON DELETE CASCADE
        )
    """,
}


def get_create_order():
    """返回按创建顺序的表名列表"""
    return ["accounts", "contents", "enterprise_profile", "tasks", "publish_records", "platform_configs", "proxies", "proxy_bindings", "account_groups", "anomaly_records", "seo_keywords", "seo_rankings", "keyword_history"]
