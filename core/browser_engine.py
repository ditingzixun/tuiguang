"""Playwright浏览器引擎 — 多浏览器指纹隔离，一号一箱"""
import os
import time
import logging
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader
from utils.fingerprint import FingerprintManager
from core.proxy_engine import proxy_engine


class BrowserEngine:
    """Playwright浏览器管理引擎"""

    def __init__(self):
        self.headless = config_loader.get_bool("BROWSER_HEADLESS", False)
        self.default_timeout = config_loader.get_int("BROWSER_TIMEOUT", 30000)
        self.slow_mo = config_loader.get_int("BROWSER_SLOW_MO", 50)
        self.viewport_w = config_loader.get_int("VIEWPORT_WIDTH", 1366)
        self.viewport_h = config_loader.get_int("VIEWPORT_HEIGHT", 768)
        self._playwright = None
        self._browser = None
        self._contexts = {}
        self._fingerprint_mgr = FingerprintManager()
        self._initialized = False

    def _resolve_browsers_path(self) -> str:
        """查找 Chromium 浏览器路径（兼容源码运行和 PyInstaller 打包）"""
        import sys
        candidates = []

        # 1. PyInstaller 打包后：browsers 目录放在 EXE 旁边
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "browsers"))

        # 2. 系统默认 Playwright 安装位置
        local_appdata = os.getenv("LOCALAPPDATA", "")
        if local_appdata:
            candidates.append(os.path.join(local_appdata, "ms-playwright"))

        # 3. 源码运行时的项目内 browsers 目录
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "browsers"))

        for p in candidates:
            if os.path.isdir(p):
                logger.info(f"使用浏览器路径: {p}")
                return p

        logger.warning("未找到 Playwright 浏览器，将使用默认路径")
        return ""

    async def init(self):
        if self._initialized:
            return
        browsers_path = self._resolve_browsers_path()
        if browsers_path:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--window-size=1366,768",
            ]
        )
        self._initialized = True
        logger.info("Playwright浏览器引擎初始化完成")

    async def close(self):
        for ctx in self._contexts.values():
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False

    async def get_context(self, account_id: int, platform: str = "") -> BrowserContext:
        """获取或创建账号专属的浏览器上下文（一号一箱）"""
        if account_id in self._contexts:
            return self._contexts[account_id]

        fingerprint = self._fingerprint_mgr.load_fingerprint(account_id)
        if not fingerprint:
            fingerprint = self._fingerprint_mgr.generate_fingerprint(account_id, platform)

        # 代理集成：优先使用引擎分配的代理
        resolved_proxy = None
        if proxy_engine._db_manager is not None:
            resolved_proxy = proxy_engine.get_proxy(account_id)

        context = await self._browser.new_context(
            viewport={"width": fingerprint["viewport"]["width"],
                      "height": fingerprint["viewport"]["height"]},
            user_agent=fingerprint["user_agent"],
            locale=fingerprint["locale"],
            timezone_id=fingerprint["timezone_id"],
            geolocation=fingerprint.get("geolocation"),
            color_scheme=fingerprint.get("color_scheme", "light"),
            device_scale_factor=fingerprint.get("device_scale_factor", 1),
            is_mobile=fingerprint.get("is_mobile", False),
            has_touch=fingerprint.get("has_touch", False),
            permissions=["geolocation"],
            proxy=resolved_proxy,
        )

        await self._inject_stealth_scripts(context, fingerprint)

        cookies = self._fingerprint_mgr.load_cookies(account_id)
        if cookies:
            await context.add_cookies(cookies)
            logger.info(f"账号 {account_id} 已加载历史Cookies")

        self._contexts[account_id] = context
        logger.info(f"账号 {account_id} 创建独立浏览器上下文")
        return context

    async def _inject_stealth_scripts(self, context: BrowserContext, fp: dict = None):
        """注入多层反检测脚本 — Canvas/WebGL/AudioContext噪声 + WebRTC防护 + 属性覆盖"""
        fp = fp or {}

        # 注入通用反检测脚本
        await context.add_init_script("""
        // ===== 1. 基础自动化标志清除 =====
        delete Object.getPrototypeOf(navigator).webdriver;
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false, configurable: true
        });

        // ===== 2. Chrome 运行时 =====
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: { isInstalled: false, InstallState: { DISABLED: 'disabled' } }
        };

        // ===== 3. 权限查询拦截 =====
        const origQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({ state: Notification.permission, onchange: null });
            }
            return origQuery.call(this, parameters);
        };

        // ===== 4. Plugins & MimeTypes 伪装 =====
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', length: 1 },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', length: 1 },
                    { name: 'Native Client', filename: 'internal-nacl-plugin', length: 2 },
                ];
                plugins.item = (i) => plugins[i] || null;
                plugins.namedItem = (n) => plugins.find(p => p.name === n) || null;
                plugins.refresh = () => {};
                return plugins;
            }
        });
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => {
                const mimeTypes = [
                    { type: 'application/pdf', suffixes: 'pdf' },
                    { type: 'text/pdf', suffixes: 'pdf' },
                ];
                mimeTypes.item = (i) => mimeTypes[i] || null;
                mimeTypes.namedItem = (n) => mimeTypes.find(m => m.type === n) || null;
                return mimeTypes;
            }
        });

        // ===== 5. Languages =====
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });
        Object.defineProperty(navigator, 'language', {
            get: () => 'zh-CN'
        });
        """)

        # 注入账号专属指纹噪声脚本（Canvas/WebGL/Audio/WebRTC/Screen/Navigator）
        seed = hash(fp.get("account_id", 0)) & 0xFFFFFFFF
        webgl_vendor = fp.get("webgl_vendor", "Google Inc. (Intel)")
        webgl_renderer = fp.get("webgl_renderer",
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0)")
        platform_name = fp.get("platform_name", "Windows")
        hw_concurrency = fp.get("hardware_concurrency", 8)
        device_memory = fp.get("device_memory", 8)
        canvas_noise = fp.get("canvas_noise", True)
        webgl_noise = fp.get("webgl_noise", True)
        audio_noise = fp.get("audio_noise", True)
        client_rects_noise = fp.get("client_rects_noise", True)

        fp_script = f"""
        (function() {{
            const SEED = {seed};
            const CANVAS_NOISE = {str(canvas_noise).lower()};
            const WEBGL_NOISE = {str(webgl_noise).lower()};
            const AUDIO_NOISE = {str(audio_noise).lower()};
            const RECTS_NOISE = {str(client_rects_noise).lower()};

            function seededRandom(x, y, c) {{
                let h = ((x * 374761393 + y * 668265263 + c * 1274126177 + SEED) & 0x7FFFFFFF);
                h = ((h >> 13) ^ h) * 1274126177;
                return (h & 0x7FFFFFFF) / 0x7FFFFFFF;
            }}

            // ===== Canvas 指纹噪声 =====
            if (CANVAS_NOISE) {{
                const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type, quality) {{
                    try {{
                        const ctx = this.getContext('2d', {{ willReadFrequently: true }});
                        if (ctx && this.width > 0 && this.height > 0) {{
                            const w = this.width, h = this.height;
                            const imageData = ctx.getImageData(0, 0, w, h);
                            const d = imageData.data;
                            for (let i = 0; i < d.length; i += 4) {{
                                if (seededRandom((i/4) % w, Math.floor((i/4)/w), 0) < 0.15) {{
                                    d[i] ^= 1;
                                    d[i+1] ^= 1;
                                    d[i+2] ^= 1;
                                }}
                            }}
                            ctx.putImageData(imageData, 0, 0);
                        }}
                    }} catch(e) {{}}
                    return _origToDataURL.apply(this, arguments);
                }};

                const _origToBlob = HTMLCanvasElement.prototype.toBlob;
                HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
                    try {{
                        const ctx = this.getContext('2d', {{ willReadFrequently: true }});
                        if (ctx && this.width > 0 && this.height > 0) {{
                            const w = this.width, h = this.height;
                            const imageData = ctx.getImageData(0, 0, w, h);
                            const d = imageData.data;
                            for (let i = 0; i < d.length; i += 4) {{
                                if (seededRandom((i/4) % w, Math.floor((i/4)/w), 1) < 0.15) {{
                                    d[i] ^= 1;
                                    d[i+1] ^= 1;
                                    d[i+2] ^= 1;
                                }}
                            }}
                            ctx.putImageData(imageData, 0, 0);
                        }}
                    }} catch(e) {{}}
                    return _origToBlob.apply(this, arguments);
                }};
            }}

            // ===== WebGL 指纹噪声 =====
            if (WEBGL_NOISE) {{
                const vendor = "{webgl_vendor}";
                const renderer = "{webgl_renderer}";
                const overrides = {{
                    37445: vendor,    // UNMASKED_VENDOR_WEBGL
                    37446: renderer,  // UNMASKED_RENDERER_WEBGL
                    7937: vendor,     // VENDOR
                    7938: renderer,   // RENDERER
                }};
                try {{
                    const origGL = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(p) {{
                        if (overrides[p] !== undefined) return overrides[p];
                        return origGL.call(this, p);
                    }};
                    const origGL2 = WebGL2RenderingContext.prototype.getParameter;
                    WebGL2RenderingContext.prototype.getParameter = function(p) {{
                        if (overrides[p] !== undefined) return overrides[p];
                        return origGL2.call(this, p);
                    }};

                    // getSupportedExtensions — 随机移除一两个扩展增加多样性
                    const origExt = WebGLRenderingContext.prototype.getSupportedExtensions;
                    WebGLRenderingContext.prototype.getSupportedExtensions = function() {{
                        const exts = origExt.call(this);
                        if (exts && SEED % 3 === 0) {{
                            const remove = exts.indexOf('WEBGL_compressed_texture_s3tc');
                            if (remove > -1) exts.splice(remove, 1);
                        }}
                        return exts;
                    }};

                    // getExtension — 随机拒绝某些扩展
                    const origGetExt = WebGLRenderingContext.prototype.getExtension;
                    WebGLRenderingContext.prototype.getExtension = function(name) {{
                        if (name === 'WEBGL_debug_renderer_info' && SEED % 2 === 0) return null;
                        return origGetExt.call(this, name);
                    }};
                }} catch(e) {{}}

                try {{
                    // 同样处理 WebGL2
                    const origExt2 = WebGL2RenderingContext.prototype.getSupportedExtensions;
                    WebGL2RenderingContext.prototype.getSupportedExtensions = function() {{
                        const exts = origExt2.call(this);
                        if (exts && SEED % 3 === 1) {{
                            const remove = exts.indexOf('EXT_color_buffer_float');
                            if (remove > -1) exts.splice(remove, 1);
                        }}
                        return exts;
                    }};
                }} catch(e) {{}}
            }}

            // ===== AudioContext 指纹噪声 =====
            if (AUDIO_NOISE) {{
                try {{
                    const origCR = AudioContext.prototype.createAnalyser ||
                                   (window.webkitAudioContext && window.webkitAudioContext.prototype.createAnalyser);
                    const origGetFreq = AnalyserNode.prototype.getFloatFrequencyData;
                    if (origGetFreq) {{
                        AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
                            origGetFreq.call(this, array);
                            for (let i = 0; i < Math.min(array.length, 10); i++) {{
                                array[i] += (seededRandom(i, 0, 2) - 0.5) * 0.5;
                            }}
                        }};
                    }}
                    const origGetByte = AnalyserNode.prototype.getByteFrequencyData;
                    if (origGetByte) {{
                        AnalyserNode.prototype.getByteFrequencyData = function(array) {{
                            origGetByte.call(this, array);
                            for (let i = 0; i < Math.min(array.length, 10); i++) {{
                                if (seededRandom(i, 1, 2) < 0.1) array[i] ^= 1;
                            }}
                        }};
                    }}

                    // OscillatorNode 频率微调
                    const origGetFreq2 = OscillatorNode.prototype.frequency;
                    if (origGetFreq2) {{
                        const origFreqGetter = Object.getOwnPropertyDescriptor(
                            AudioParam.prototype, 'value'
                        );
                        if (origFreqGetter && origFreqGetter.get) {{
                            const origGet = origFreqGetter.get;
                            Object.defineProperty(AudioParam.prototype, 'value', {{
                                get: function() {{
                                    const val = origGet.call(this);
                                    if (this._noiseApplied === undefined && val > 0 && val < 22050) {{
                                        this._noiseApplied = (seededRandom(Math.floor(val * 1000), 0, 3) - 0.5) * 0.02;
                                    }}
                                    return val + (this._noiseApplied || 0);
                                }},
                                set: function(v) {{ this._rawValue = v; this._noiseApplied = undefined; }},
                                configurable: true
                            }});
                        }}
                    }}
                }} catch(e) {{}}
            }}

            // ===== WebRTC IP 泄露防护 =====
            try {{
                const origRTCPC = window.RTCPeerConnection || window.webkitRTCPeerConnection;
                if (origRTCPC) {{
                    const OrigRTCPeerConnection = origRTCPC;
                    const handler = {{
                        construct: function(target, args) {{
                            const pc = new target(...args);
                            // 仅允许 relay 类型 candidate（通过代理），屏蔽 srflx/host 泄露真实IP
                            const origCreateOffer = pc.createOffer;
                            pc.createOffer = function(...a) {{
                                return origCreateOffer.apply(this, a).then(desc => {{
                                    if (desc && desc.sdp) {{
                                        desc.sdp = desc.sdp.replace(
                                            /a=candidate:(\\d+) \\d+ (UDP|TCP) (\\d+) ([\\d.]+) (\\d+) typ (host|srflx)/g,
                                            ''
                                        );
                                    }}
                                    return desc;
                                }});
                            }};
                            const origCreateAnswer = pc.createAnswer;
                            pc.createAnswer = function(...a) {{
                                return origCreateAnswer.apply(this, a).then(desc => {{
                                    if (desc && desc.sdp) {{
                                        desc.sdp = desc.sdp.replace(
                                            /a=candidate:(\\d+) \\d+ (UDP|TCP) (\\d+) ([\\d.]+) (\\d+) typ (host|srflx)/g,
                                            ''
                                        );
                                    }}
                                    return desc;
                                }});
                            }};
                            return pc;
                        }}
                    }};
                    window.RTCPeerConnection = new Proxy(OrigRTCPeerConnection, handler);
                    if (window.webkitRTCPeerConnection) {{
                        window.webkitRTCPeerConnection = new Proxy(window.webkitRTCPeerConnection, handler);
                    }}
                }}
            }} catch(e) {{}}

            // ===== ClientRects 随机偏移 =====
            if (RECTS_NOISE) {{
                const origGetBR = Element.prototype.getBoundingClientRect;
                Element.prototype.getBoundingClientRect = function() {{
                    const rect = origGetBR.call(this);
                    const noise = seededRandom(SEED, Math.floor(rect.x * 100), 4) - 0.5;
                    return {{
                        x: rect.x + noise * 0.3, y: rect.y + noise * 0.3,
                        width: rect.width + noise * 0.1, height: rect.height + noise * 0.1,
                        top: rect.top + noise * 0.3, right: rect.right + noise * 0.3,
                        bottom: rect.bottom + noise * 0.3, left: rect.left + noise * 0.3,
                        toJSON: rect.toJSON.bind(rect)
                    }};
                }};
            }}

            // ===== Navigator 属性全面覆盖 =====
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{platform_name}', configurable: true
            }});
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {hw_concurrency}, configurable: true
            }});
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {device_memory}, configurable: true
            }});
            Object.defineProperty(navigator, 'maxTouchPoints', {{
                get: () => 0, configurable: true
            }});
            Object.defineProperty(navigator, 'vendor', {{
                get: () => 'Google Inc.', configurable: true
            }});
            Object.defineProperty(navigator, 'vendorSub', {{
                get: () => '', configurable: true
            }});
            Object.defineProperty(navigator, 'productSub', {{
                get: () => '20030107', configurable: true
            }});
            Object.defineProperty(navigator, 'appVersion', {{
                get: () => navigator.userAgent.replace('Mozilla/', ''), configurable: true
            }});
            Object.defineProperty(navigator, 'doNotTrack', {{
                get: () => '1', configurable: true
            }});
            Object.defineProperty(navigator, 'connection', {{
                get: () => ({{
                    effectiveType: '4g', rtt: 50, downlink: 10, saveData: false
                }}), configurable: true
            }});

            // ===== Screen 属性覆盖 =====
            try {{
                Object.defineProperty(screen, 'colorDepth', {{ get: () => 24, configurable: true }});
                Object.defineProperty(screen, 'pixelDepth', {{ get: () => 24, configurable: true }});
            }} catch(e) {{}}

            // ===== iframe contentWindow 检测对抗 =====
            try {{
                const origGetOwnProperty = Object.getOwnPropertyDescriptor(
                    HTMLIFrameElement.prototype, 'contentWindow'
                );
                if (origGetOwnProperty && origGetOwnProperty.get) {{
                    const origGetter = origGetOwnProperty.get;
                    Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {{
                        get: function() {{
                            const win = origGetter.call(this);
                            if (win && this.src === '') {{
                                try {{ win.chrome = window.chrome; }} catch(e) {{}}
                            }}
                            return win;
                        }},
                        configurable: true
                    }});
                }}
            }} catch(e) {{}}

            // ===== Batch/Frame 时序噪声：随机化 requestAnimationFrame =====
            const origRAF = window.requestAnimationFrame;
            let rafCounter = 0;
            window.requestAnimationFrame = function(callback) {{
                rafCounter++;
                if (rafCounter % 17 === 0) {{
                    return origRAF.call(window, (t) => setTimeout(() => callback(t), 1));
                }}
                return origRAF.call(window, callback);
            }};

            // ===== 禁用自动化标志属性 =====
            try {{
                Object.defineProperty(document, 'cdc_adoQpoasnfa76pfcZLmcfl_Array', {{ get: undefined }});
                Object.defineProperty(document, 'cdc_adoQpoasnfa76pfcZLmcfl_Promise', {{ get: undefined }});
                Object.defineProperty(document, 'cdc_adoQpoasnfa76pfcZLmcfl_Symbol', {{ get: undefined }});
            }} catch(e) {{}}

            // ===== Worker 权限遮盖 =====
            try {{
                const origWorker = window.Worker;
                window.Worker = new Proxy(origWorker, {{
                    construct: function(target, args) {{
                        return new target(...args);
                    }}
                }});
            }} catch(e) {{}}

            console.debug('[Stealth] 反检测脚本注入完成 seed={seed}');
        }})();
        """

        await context.add_init_script(fp_script)

    async def new_page(self, account_id: int, platform: str = "") -> Page:
        """为指定账号创建新页面"""
        context = await self.get_context(account_id, platform)
        page = await context.new_page()
        page.set_default_timeout(self.default_timeout)
        return page

    async def save_account_cookies(self, account_id: int):
        if account_id in self._contexts:
            cookies = await self._contexts[account_id].cookies()
            self._fingerprint_mgr.save_cookies(account_id, cookies)

    async def close_context(self, account_id: int):
        if account_id in self._contexts:
            await self._contexts[account_id].close()
            del self._contexts[account_id]
            logger.info(f"账号 {account_id} 浏览器上下文已关闭")

    async def take_screenshot(self, page: Page, account_id: int, task_id: int = None) -> str:
        os.makedirs("./data/screenshots", exist_ok=True)
        ts = task_id or "unknown"
        filename = f"screenshot_{account_id}_{ts}_{int(time.time())}.png"
        filepath = os.path.join("./data/screenshots", filename)
        await page.screenshot(path=filepath, full_page=True)
        return filepath


browser_engine = BrowserEngine()
