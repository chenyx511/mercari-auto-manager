import asyncio
import csv
import json
import random
from datetime import datetime
from src.automation.browser_manager import BrowserManager
from src.automation.mercari_operations import MercariOperations
from src.core.template_engine import TemplateEngine
from src.data.database import ProductRepository, OperationLogRepository
from src.utils.config import get
from src.utils.logger import setup_logger

logger = setup_logger("listing")


class ListingEngine:
    """批量上架引擎：CSV导入、模板优化、队列发布"""

    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.mercari = MercariOperations(browser)
        self.template = TemplateEngine()
        self._is_running = False
        self._progress_callback = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_progress_callback(self, callback):
        """设置进度回调：callback(current, total, product_title, status)"""
        self._progress_callback = callback

    def _notify_progress(self, current: int, total: int, title: str, status: str):
        if self._progress_callback:
            self._progress_callback(current, total, title, status)

    @staticmethod
    def import_from_csv(csv_path: str, optimize: bool = True) -> list[dict]:
        """
        从 CSV 文件导入商品列表
        CSV 格式: title, description, category, price, condition, images
        images 列为分号分隔的图片路径
        """
        products = []
        template = TemplateEngine()

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                product = {
                    'title': row.get('title', '').strip(),
                    'description': row.get('description', '').strip(),
                    'category': row.get('category', '').strip(),
                    'price': int(row.get('price', 0)),
                    'condition': row.get('condition', '目立った傷や汚れなし').strip(),
                    'shipping_payer': row.get('shipping_payer', '送料込み(出品者負担)').strip(),
                    'shipping_method': row.get('shipping_method', '').strip(),
                    'shipping_area': row.get('shipping_area', '').strip(),
                    'shipping_days': row.get('shipping_days', '1~2日で発送').strip(),
                    'notes': row.get('notes', '').strip(),
                }

                images_str = row.get('images', '')
                if images_str:
                    image_list = [p.strip() for p in images_str.split(';') if p.strip()]
                    product['images'] = json.dumps(image_list)
                else:
                    product['images'] = '[]'

                if optimize:
                    product = template.process_product(product)

                products.append(product)

        logger.info(f"从CSV导入 {len(products)} 件商品")
        return products

    @staticmethod
    def add_products_to_queue(products: list[dict]) -> list[int]:
        """将商品添加到发布队列（数据库）"""
        product_ids = []
        for product in products:
            pid = ProductRepository.add(product)
            product_ids.append(pid)
            logger.info(f"商品已加入队列: [{pid}] {product.get('title', '')}")
        return product_ids

    async def publish_queue(self, product_ids: list[int] = None):
        """发布队列中的待发布商品"""
        if self._is_running:
            logger.warning("发布任务已在运行中")
            return

        self._is_running = True

        try:
            if product_ids:
                products = [ProductRepository.get_by_id(pid) for pid in product_ids]
                products = [p for p in products if p and p['status'] == 'pending']
            else:
                products = ProductRepository.get_all(status='pending')

            total = len(products)
            logger.info(f"开始发布 {total} 件商品")

            delay_base = get('listing.delay_between_items_seconds', 30)
            delay_range = get('listing.random_delay_range', 10)

            for i, product in enumerate(products):
                if not self._is_running:
                    logger.info("发布任务已停止")
                    break

                self._notify_progress(i + 1, total, product['title'], "发布中...")

                try:
                    mercari_id = await self.mercari.publish_product(product)

                    if mercari_id:
                        ProductRepository.update_status(product['id'], 'listed', mercari_id)
                        OperationLogRepository.add(
                            'listing', product['id'],
                            f"发布成功: {mercari_id}"
                        )
                        self._notify_progress(i + 1, total, product['title'], "发布成功")
                        logger.info(f"[{i+1}/{total}] 发布成功: {product['title']}")
                    else:
                        ProductRepository.update_status(product['id'], 'pending')
                        OperationLogRepository.add(
                            'listing', product['id'],
                            "发布结果未确认", 'failed'
                        )
                        self._notify_progress(i + 1, total, product['title'], "发布失败")
                        logger.warning(f"[{i+1}/{total}] 发布未确认: {product['title']}")

                except Exception as e:
                    OperationLogRepository.add(
                        'listing', product['id'],
                        str(e), 'failed', str(e)
                    )
                    self._notify_progress(i + 1, total, product['title'], f"出错: {e}")
                    logger.error(f"[{i+1}/{total}] 发布出错: {e}")

                if i < total - 1 and self._is_running:
                    delay = delay_base + random.randint(-delay_range, delay_range)
                    delay = max(10, delay)
                    logger.info(f"等待 {delay} 秒后发布下一件...")
                    self._notify_progress(i + 1, total, product['title'], f"等待 {delay}s...")
                    await asyncio.sleep(delay)

        finally:
            self._is_running = False
            logger.info("发布任务结束")

    def stop(self):
        """停止正在运行的发布任务"""
        self._is_running = False
        logger.info("收到停止信号")
