import asyncio
import os
import platform
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.utils.config import get
from src.utils.logger import setup_logger

logger = setup_logger("browser")


def _find_chrome_path() -> str | None:
    """自动查找系统已安装的 Chrome / Chromium 路径"""
    system = platform.system()

    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        prog = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        prog86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        candidates = [
            os.path.join(local, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(prog, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(prog86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(prog, r"Microsoft\Edge\Application\msedge.exe"),
            os.path.join(local, r"BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
    else:
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class BrowserManager:
    """管理 Playwright 浏览器实例，支持持久化登录状态"""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._launch_error: str | None = None

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def is_running(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    @property
    def last_error(self) -> str | None:
        return self._launch_error

    async def start(self):
        if self.is_running:
            logger.info("浏览器已在运行中")
            return

        self._launch_error = None
        logger.info("正在启动浏览器...")

        self._playwright = await async_playwright().start()

        user_data_dir = os.path.abspath(
            get('browser.user_data_dir', './data/browser_profile')
        )
        os.makedirs(user_data_dir, exist_ok=True)

        chrome_path = _find_chrome_path()

        launch_kwargs = dict(
            user_data_dir=user_data_dir,
            headless=get('browser.headless', False),
            slow_mo=get('browser.slow_mo', 500),
            viewport={
                'width': get('browser.viewport_width', 1280),
                'height': get('browser.viewport_height', 800)
            },
            locale='ja-JP',
            timezone_id='Asia/Tokyo',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
            ],
        )

        if chrome_path:
            launch_kwargs['executable_path'] = chrome_path
            logger.info(f"使用系统浏览器: {chrome_path}")
        else:
            logger.info("使用 Playwright 内置 Chromium")

        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                **launch_kwargs
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"持久化上下文启动失败: {error_msg}")
            logger.info("尝试使用普通模式启动...")

            try:
                self._browser = await self._playwright.chromium.launch(
                    headless=get('browser.headless', False),
                    slow_mo=get('browser.slow_mo', 500),
                    executable_path=chrome_path if chrome_path else None,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                    ],
                )
                self._context = await self._browser.new_context(
                    viewport={
                        'width': get('browser.viewport_width', 1280),
                        'height': get('browser.viewport_height', 800)
                    },
                    locale='ja-JP',
                    timezone_id='Asia/Tokyo',
                )
            except Exception as e2:
                self._launch_error = str(e2)
                logger.error(f"普通模式也启动失败: {e2}")
                await self._cleanup()
                raise RuntimeError(f"浏览器启动失败: {e2}") from e2

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        logger.info("浏览器启动成功")

    async def _cleanup(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    async def close(self):
        logger.info("正在关闭浏览器...")
        await self._cleanup()
        logger.info("浏览器已关闭")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded"):
        if not self.is_running:
            raise RuntimeError("浏览器未启动")
        logger.info(f"导航至: {url}")
        await self._page.goto(url, wait_until=wait_until, timeout=30000)

    async def wait_for_selector(self, selector: str, timeout: int = 30000):
        return await self._page.wait_for_selector(selector, timeout=timeout)

    async def human_type(self, selector: str, text: str, delay: int = 50):
        element = await self._page.wait_for_selector(selector)
        await element.click()
        await element.fill('')
        await self._page.type(selector, text, delay=delay)

    async def random_sleep(self, min_ms: int = 500, max_ms: int = 2000):
        import random
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)

    async def screenshot(self, path: str = None) -> bytes:
        if path:
            return await self._page.screenshot(path=path)
        return await self._page.screenshot()
