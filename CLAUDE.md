# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (sqlite3 is built-in, not in requirements.txt)
pip install -r requirements.txt
playwright install chromium

# Run the application
python main.py

# Syntax-check all modules
find . -name "*.py" -not -path "./.claude/*" | xargs -I{} python -m py_compile {}

# Test database initialization
python -c "from db.database import DatabaseManager; db = DatabaseManager(); db.init_db('./data/test.db'); print('OK')"
```

No test suite, linter, or build step exists yet.

## Architecture

Desktop automation tool for qualification-agency industry — a PyQt6 GUI that drives Playwright browsers to publish content across B2B/media platforms.

### Key architectural rules

**Singleton pattern.** `DatabaseManager`, `ConfigLoader`, and `AIContentEngine` / `BrowserEngine` in `core/` use module-level singleton instances:

```python
from db.database import DatabaseManager  # class — instantiate once
from core.ai_engine import ai_engine     # module singleton
from utils.config_loader import config_loader  # module singleton
```

`DatabaseManager` uses `__new__` + `_initialized` guard. `ConfigLoader` is similar — `load()` updates the class state.

**Database: raw sqlite3, no ORM.** `DatabaseManager` wraps sqlite3 with convenience methods: `fetch_all(sql, params)`, `fetch_one(sql, params)`, `execute(sql, params)`, `insert(table, dict)`, `update(table, dict, where, params)`, `delete(table, where, params)`. Connection uses `row_factory = sqlite3.Row` for dict-like row access. WAL mode enabled. Thread safety via `threading.local()` — each thread gets its own connection.

**5 core tables** (all in `db/schema.py`): `accounts`, `tasks`, `publish_records`, `contents`, `platform_configs`.

**Configuration: .env + python-dotenv.** `ConfigLoader` wraps `os.getenv()` with defaults. Use `config_loader.get("KEY")`, `config_loader.get_int("KEY")`, `config_loader.get_bool("KEY")`. Settings UI writes to `.env` via `dotenv.set_key()`.

**Logging: stdlib logging.** Import pattern is `import logging; logger = logging.getLogger(__name__)`. Logging is configured in `utils/logging_setup.py` with console + rotating file handlers.

**Plugin system — auto-discovery.** Drop a `.py` file into `plugins/b2b/` or `plugins/media/` containing a subclass of `BasePlatformPlugin`, and `PluginManager._discover_plugins()` finds it at import time via `__import__` + `issubclass` inspection. The subclass must define `platform_info` dict (with unique `name`) and implement `async login()` / `async publish()`. Copy `plugins/custom_platform_template.py` as starting point.

**Browser isolation — one account = one BrowserContext.** `BrowserEngine.get_context(account_id)` creates a dedicated Playwright `BrowserContext` per account with unique fingerprint (UA, viewport, WebGL noise). Cookies persist per-account to `data/profiles/account_{id}/cookies.json`.

**UI: 5 tabs.** AccountManager, TaskManager, ContentGenerator, PublishManager, SettingsManager. Each tab receives `db_manager` via constructor injection. Tabs do not share DB sessions — each calls `db_manager.fetch_all()` etc. independently.

**Async Playwright + sync PyQt6.** Plugin methods are async. The UI is sync PyQt6. An `asyncio.run()` bridge or event-loop thread is needed to wire the publish flow end-to-end (not yet implemented).

### Adding a new platform

1. Copy `plugins/custom_platform_template.py` → `plugins/b2b/your_platform.py`
2. Rename class, fill in `platform_info` (unique `name`, `login_url`, `publish_url`)
3. Implement `login()` and `publish()` using `self.fill_form_field()` and `behavior_sim` helpers
4. Restart; PluginManager discovers it automatically
5. Add the platform name to combo boxes in `ui/task_manager.py` and `ui/account_manager.py`

### Publish task flow

1. User creates task in `TaskManagerWidget` → inserted into `tasks` table with status `pending`
2. `TaskScheduler.schedule_publish()` schedules via APScheduler with random delay (staggered)
3. `_execute_publish()` calls `_publish_callback` (bridge to browser/plugin)
4. Success → `publish_records` row with result URL; Failure → retries up to `max_retries`
