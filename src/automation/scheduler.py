import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.automation.browser_manager import BrowserManager
from src.core.pricing_engine import PricingEngine
from src.core.reply_engine import ReplyEngine
from src.utils.config import get
from src.utils.logger import setup_logger

logger = setup_logger("scheduler")


class TaskScheduler:
    """定时任务调度器，管理自动调价和自动回复的定时运行"""

    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.scheduler = AsyncIOScheduler()
        self.pricing_engine = PricingEngine(browser)
        self.reply_engine = ReplyEngine(browser)
        self._pricing_job = None
        self._reply_job = None

    def start_pricing_schedule(self):
        interval = get('pricing.check_interval_minutes', 60)
        if self._pricing_job:
            self._pricing_job.remove()

        self._pricing_job = self.scheduler.add_job(
            self._run_pricing,
            IntervalTrigger(minutes=interval),
            id='auto_pricing',
            replace_existing=True,
        )
        logger.info(f"自动调价定时任务已启动 (间隔: {interval}分钟)")

        if not self.scheduler.running:
            self.scheduler.start()

    def stop_pricing_schedule(self):
        if self._pricing_job:
            self._pricing_job.remove()
            self._pricing_job = None
            logger.info("自动调价定时任务已停止")

    def start_reply_schedule(self):
        interval = get('auto_reply.check_interval_seconds', 120)
        if self._reply_job:
            self._reply_job.remove()

        self._reply_job = self.scheduler.add_job(
            self._run_reply,
            IntervalTrigger(seconds=interval),
            id='auto_reply',
            replace_existing=True,
        )
        logger.info(f"自动回复定时任务已启动 (间隔: {interval}秒)")

        if not self.scheduler.running:
            self.scheduler.start()

    def stop_reply_schedule(self):
        if self._reply_job:
            self._reply_job.remove()
            self._reply_job = None
            logger.info("自动回复定时任务已停止")

    def stop_all(self):
        self.stop_pricing_schedule()
        self.stop_reply_schedule()
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("所有定时任务已停止")

    async def _run_pricing(self):
        if not self.browser.is_running:
            logger.warning("浏览器未运行，跳过自动调价")
            return
        try:
            await self.pricing_engine.execute_price_adjustments()
        except Exception as e:
            logger.error(f"定时调价出错: {e}")

    async def _run_reply(self):
        if not self.browser.is_running:
            logger.warning("浏览器未运行，跳过自动回复")
            return
        try:
            await self.reply_engine.check_and_reply_once()
        except Exception as e:
            logger.error(f"定时回复出错: {e}")
