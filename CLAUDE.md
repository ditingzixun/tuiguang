# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the application
python main.py

# Syntax-check all modules
find . -name "*.py" -not -path "./.claude/*" | xargs -I{} python -m py_compile {}
```

No test suite, linter, or build step exists yet.

## Architecture

This is a desktop automation tool for the qualification-agency industry — a PyQt6 GUI that drives Playwright browsers to publish content across B2B/media platforms, monitor SEO rankings, and manage accounts at scale.

### Key architectural rules

**Singleton pattern for engines and config.** `DatabaseManager`, `ConfigLoader`, and every engine in `core/` (proxy, AI, SEO, SMS, browser) use the module-level singleton pattern. Import the instance, never instantiate directly:

```python
from core.proxy_engine import proxy_engine  # singleton, not ProxyEngine()
from utils.config_loader import config_loader # singleton, not ConfigLoader()
```

`DatabaseManager` uses `__new__` + a `_initialized` guard to ensure only one instance exists. `ConfigLoader` is a borg — `load()` updates a single class-level dict.

**Plugin system — auto-discovery, no registration needed.** Drop a new `.py` file into `plugins/b2b/` or `plugins/media/` containing a subclass of `BasePlatformPlugin`, and `PluginManager._discover_plugins()` finds it at import time via `__import__` + `issubclass` inspection. The subclass must define a `platform_info` dict (with a unique `name` key) and implement `async login()` / `async publish()`. Copy `plugins/custom_platform_template.py` as a starting point.

**Browser isolation — one account = one BrowserContext.** `BrowserEngine.get_context(account_id)` creates a dedicated Playwright `BrowserContext` per account. It loads/saves a fingerprint JSON (UA, viewport, WebGL noise, geolocation) via `FingerprintManager` and injects anti-detection JS. Cookies persist per-account to `data/profiles/account_{id}/cookies.json`. Contexts are cached in `self._contexts` dict — never share a context between accounts.

**Database session lifecycle.** `DatabaseManager.Session` is a `scoped_session`. Callers are responsible for `session = db.get_session()` / `session.close()` in every method that queries. The UI layer typically obtains one session per refresh/action and closes it in a `finally` block. SQLite runs in WAL mode with `check_same_thread=False`.

**config.yaml is the source of truth, but config_loader has fallback defaults.** `ConfigLoader.load()` merges the YAML file into `_config`. If the file is missing, `_default_config()` provides a complete baseline. The `get("key.path")` method does dotted-path access with a default fallback. At startup, settings are also seeded into `system_configs` table, but that's a cache — the YAML file is authoritative.

**Async Playwright + sync PyQt6.** The browser operations are async (playwright). The UI is sync (PyQt6). Currently async methods are defined in plugins but the scheduler calls them from sync context — expect to need an `asyncio.run()` bridge or a dedicated event loop thread when wiring the publish flow end-to-end.

### Data flow for a publish task

1. User creates a `PublishTask` in the UI → saved to DB with status `pending`
2. `TaskScheduler.schedule_publish()` picks it up, schedules via APScheduler with a random delay (staggered publishing)
3. `_execute_publish()` calls the external `_publish_callback` — the bridge between scheduler and browser
4. On success, a `PublishRecord` is created with the result URL and a screenshot path
5. On failure, retries up to `max_retries` times with `retry_delay` seconds between attempts

### Adding a new platform

1. Copy `plugins/custom_platform_template.py` → `plugins/b2b/your_platform.py`
2. Rename the class and fill in real `platform_info` (unique `name`, `login_url`, `publish_url`)
3. Implement `login()` — use `self.fill_form_field()` and `behavior_sim` helpers
4. Implement `publish()` — return the result URL on success, `None` on failure
5. Restart the app; PluginManager discovers it automatically
6. (Optional) Add the platform to the combo boxes in `ui/task_manager.py` and `ui/account_manager.py`

### UI tab signal flow

`MainWindow` owns all 6 tab widgets and the `DatabaseManager` singleton. Each tab widget receives `db_manager` via constructor injection and calls `self.db_manager.get_session()` independently — tabs do not share sessions or communicate directly. `AccountManagerWidget` emits `status_changed` signal (currently unused by other tabs, but wired for future cross-tab refresh).
