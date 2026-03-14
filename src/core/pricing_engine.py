import asyncio
import math
from datetime import datetime, timedelta
from src.automation.browser_manager import BrowserManager
from src.automation.mercari_operations import MercariOperations
from src.data.database import ProductRepository, OperationLogRepository
from src.utils.config import get
from src.utils.logger import setup_logger

logger = setup_logger("pricing")


class PricingStrategy:
    """调价策略"""

    def __init__(self):
        self.strategies = get('pricing.strategies', [
            {'days_unsold': 1, 'discount_percent': 3},
            {'days_unsold': 3, 'discount_percent': 5},
            {'days_unsold': 7, 'discount_percent': 10},
        ])
        self.strategies.sort(key=lambda s: s['days_unsold'], reverse=True)
        self.min_price = get('pricing.min_price', 300)

    def calculate_new_price(self, product: dict) -> tuple[int, str] | None:
        """
        根据策略计算新价格
        返回 (new_price, reason) 或 None（无需调价）
        """
        listed_at = product.get('listed_at')
        last_update = product.get('last_price_update')
        current_price = product.get('price', 0)
        original_price = product.get('original_price', current_price)

        reference_time = last_update or listed_at
        if not reference_time:
            return None

        if isinstance(reference_time, str):
            reference_time = datetime.fromisoformat(reference_time)

        days_since = (datetime.now() - reference_time).days

        for strategy in self.strategies:
            if days_since >= strategy['days_unsold']:
                discount = strategy['discount_percent']
                new_price = math.ceil(current_price * (1 - discount / 100))
                new_price = max(new_price, self.min_price)

                if new_price >= current_price:
                    return None

                reason = f"{days_since}日未售出 → 降价{discount}% (¥{current_price} → ¥{new_price})"
                return (new_price, reason)

        return None


class PricingEngine:
    """自动调价引擎"""

    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.mercari = MercariOperations(browser)
        self.strategy = PricingStrategy()
        self._is_running = False
        self._progress_callback = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_progress_callback(self, callback):
        """callback(product_title, old_price, new_price, status)"""
        self._progress_callback = callback

    def _notify(self, title: str, old_price: int, new_price: int, status: str):
        if self._progress_callback:
            self._progress_callback(title, old_price, new_price, status)

    def check_prices(self) -> list[dict]:
        """检查所有在售商品，返回需要调价的列表"""
        listed = ProductRepository.get_listed_products()
        adjustments = []

        for product in listed:
            result = self.strategy.calculate_new_price(product)
            if result:
                new_price, reason = result
                adjustments.append({
                    'product': product,
                    'new_price': new_price,
                    'reason': reason,
                })

        logger.info(f"检查 {len(listed)} 件商品，{len(adjustments)} 件需要调价")
        return adjustments

    async def execute_price_adjustments(self, adjustments: list[dict] = None):
        """执行调价操作"""
        if self._is_running:
            logger.warning("调价任务已在运行中")
            return

        self._is_running = True

        try:
            if adjustments is None:
                adjustments = self.check_prices()

            if not adjustments:
                logger.info("没有需要调价的商品")
                return

            logger.info(f"开始调价: {len(adjustments)} 件商品")

            for adj in adjustments:
                if not self._is_running:
                    break

                product = adj['product']
                new_price = adj['new_price']
                reason = adj['reason']
                mercari_id = product.get('mercari_id')

                if not mercari_id:
                    logger.warning(f"商品 [{product['id']}] 没有 Mercari ID，跳过")
                    continue

                try:
                    self._notify(product['title'], product['price'], new_price, "调价中...")

                    success = await self.mercari.update_price(mercari_id, new_price)

                    if success:
                        ProductRepository.update_price(product['id'], new_price, reason)
                        OperationLogRepository.add(
                            'pricing', product['id'], reason
                        )
                        self._notify(product['title'], product['price'], new_price, "调价成功")
                        logger.info(f"调价成功: {product['title']} - {reason}")
                    else:
                        OperationLogRepository.add(
                            'pricing', product['id'], reason, 'failed'
                        )
                        self._notify(product['title'], product['price'], new_price, "调价失败")

                except Exception as e:
                    OperationLogRepository.add(
                        'pricing', product['id'], str(e), 'failed', str(e)
                    )
                    self._notify(product['title'], product['price'], new_price, f"出错: {e}")
                    logger.error(f"调价出错: {e}")

                await asyncio.sleep(5)

        finally:
            self._is_running = False
            logger.info("调价任务结束")

    def stop(self):
        self._is_running = False
        logger.info("调价引擎收到停止信号")
