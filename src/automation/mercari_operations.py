import asyncio
import json
import os
import re
from datetime import datetime
from src.automation.browser_manager import BrowserManager
from src.utils.config import get
from src.utils.logger import setup_logger

logger = setup_logger("mercari_ops")

BASE_URL = "https://jp.mercari.com"


class MercariOperations:
    """封装所有 Mercari 页面操作"""

    def __init__(self, browser: BrowserManager):
        self.browser = browser

    async def login(self) -> bool:
        try:
            login_url = get('mercari.login_url', f'{BASE_URL}/signin')
            await self.browser.navigate(login_url)
            logger.info("请在浏览器中手动登录 Mercari...")

            try:
                await self.browser.page.wait_for_url(
                    f"{BASE_URL}/**",
                    timeout=300000
                )
                await self.browser.random_sleep(2000, 3000)
                logger.info("登录成功!")
                return True
            except Exception:
                logger.warning("登录超时")
                return False
        except Exception as e:
            logger.error(f"登录出错: {e}")
            return False

    async def check_login_status(self) -> bool:
        try:
            await self.browser.navigate(BASE_URL)
            await self.browser.random_sleep(2000, 3000)
            page = self.browser.page

            logged_in = await page.query_selector(
                'a[href="/mypage"], '
                'a[data-testid="mypage-link"], '
                '[data-testid="header-mypage-button"], '
                'a[href*="/mypage"]'
            )
            if logged_in:
                logger.info("已检测到登录状态")
                return True

            page_text = await page.text_content('body')
            if 'マイページ' in (page_text or '') or 'ログアウト' in (page_text or ''):
                logger.info("已检测到登录状态 (通过文本)")
                return True

            logger.info("未检测到登录状态")
            return False
        except Exception as e:
            logger.error(f"检查登录状态出错: {e}")
            return False

    async def fetch_my_listings(self) -> list[dict]:
        """
        抓取已登录 Mercari 账户中的在售商品信息
        返回包含标题、价格、ID、图片等的字典列表
        """
        try:
            await self.browser.navigate(f"{BASE_URL}/mypage/listings")
            await self.browser.random_sleep(3000, 5000)
            page = self.browser.page

            for _ in range(10):
                prev_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.browser.random_sleep(1000, 2000)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == prev_height:
                    break

            await page.evaluate("window.scrollTo(0, 0)")
            await self.browser.random_sleep(500, 1000)

            listings = await page.evaluate("""
                () => {
                    const items = [];
                    // Try multiple selector strategies for Mercari's layout
                    const links = document.querySelectorAll('a[href*="/item/"]');
                    const seen = new Set();

                    for (const link of links) {
                        const href = link.getAttribute('href') || '';
                        const match = href.match(/\\/item\\/([a-zA-Z0-9]+)/);
                        if (!match) continue;
                        const itemId = match[1];
                        if (seen.has(itemId)) continue;
                        seen.add(itemId);

                        // Find container (parent elements)
                        let container = link;
                        for (let i = 0; i < 5; i++) {
                            if (container.parentElement) container = container.parentElement;
                        }

                        // Extract title
                        const titleEl = container.querySelector(
                            '[data-testid="item-name"], '
                            + 'span[class*="itemName"], '
                            + 'div[class*="itemName"], '
                            + 'p[class*="itemName"]'
                        );
                        let title = '';
                        if (titleEl) {
                            title = titleEl.textContent.trim();
                        } else {
                            // Fallback: get alt text from image or aria-label
                            const img = link.querySelector('img');
                            if (img) title = img.alt || '';
                            if (!title) title = link.getAttribute('aria-label') || '';
                        }

                        // Extract price
                        const priceEl = container.querySelector(
                            '[data-testid="item-price"], '
                            + 'span[class*="price" i], '
                            + 'div[class*="price" i]'
                        );
                        let price = 0;
                        if (priceEl) {
                            const priceText = priceEl.textContent || '';
                            const digits = priceText.replace(/[^0-9]/g, '');
                            price = parseInt(digits) || 0;
                        }

                        // Extract image
                        const imgEl = link.querySelector('img') || container.querySelector('img');
                        const imgSrc = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';

                        if (title || price > 0) {
                            items.push({
                                mercari_id: itemId,
                                title: title,
                                price: price,
                                image_url: imgSrc,
                                url: href.startsWith('http') ? href : 'https://jp.mercari.com' + href,
                            });
                        }
                    }
                    return items;
                }
            """)

            logger.info(f"从 Mercari 抓取到 {len(listings)} 件在售商品")
            return listings

        except Exception as e:
            logger.error(f"抓取在售商品出错: {e}")
            return []

    async def fetch_product_detail(self, mercari_id: str) -> dict:
        """抓取单个商品的详细信息"""
        try:
            url = f"{BASE_URL}/item/{mercari_id}"
            await self.browser.navigate(url)
            await self.browser.random_sleep(2000, 4000)
            page = self.browser.page

            detail = await page.evaluate("""
                () => {
                    const getText = (selectors) => {
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el && el.textContent.trim()) return el.textContent.trim();
                        }
                        return '';
                    };

                    const title = getText([
                        'h1[data-testid="product-name"]',
                        'h1[class*="itemName"]',
                        'h1'
                    ]);

                    const priceText = getText([
                        '[data-testid="product-price"]',
                        'span[class*="price" i]',
                    ]);
                    const price = parseInt((priceText || '0').replace(/[^0-9]/g, '')) || 0;

                    const description = getText([
                        '[data-testid="product-description"]',
                        'pre[class*="description" i]',
                        'div[class*="description" i]',
                    ]);

                    const condition = getText([
                        '[data-testid="商品の状態"]',
                        'span[class*="condition" i]',
                    ]);

                    const category = getText([
                        '[data-testid="category"]',
                        'span[class*="category" i]',
                    ]);

                    const images = [];
                    const imgEls = document.querySelectorAll(
                        '[data-testid="product-image"] img, '
                        + 'div[class*="itemImage"] img, '
                        + 'div[class*="slick"] img'
                    );
                    for (const img of imgEls) {
                        const src = img.src || img.getAttribute('data-src');
                        if (src && !images.includes(src)) images.push(src);
                    }

                    return { title, price, description, condition, category, images };
                }
            """)

            detail['mercari_id'] = mercari_id
            logger.info(f"获取商品详情: {detail.get('title', '')[:30]}")
            return detail

        except Exception as e:
            logger.error(f"获取商品详情出错: {e}")
            return {}

    async def publish_product(self, product: dict) -> str | None:
        try:
            sell_url = get('mercari.sell_url', f'{BASE_URL}/sell')
            await self.browser.navigate(sell_url)
            await self.browser.random_sleep(2000, 4000)
            page = self.browser.page

            images = product.get('images', '')
            if images:
                image_list = json.loads(images) if isinstance(images, str) else images
                for img_path in image_list:
                    if os.path.exists(img_path):
                        file_input = await page.query_selector('input[type="file"]')
                        if file_input:
                            await file_input.set_input_files(img_path)
                            await self.browser.random_sleep(1500, 3000)
                            logger.info(f"已上传图片: {img_path}")

            await self.browser.random_sleep(1000, 2000)

            title = product.get('title', '')
            if title:
                title_input = await page.query_selector(
                    'input[name="name"], input[data-testid="product-name"]'
                )
                if title_input:
                    await title_input.click()
                    await title_input.fill('')
                    await page.keyboard.type(title, delay=30)
                    logger.info(f"已填写标题: {title}")

            await self.browser.random_sleep(800, 1500)

            description = product.get('description', '')
            if description:
                desc_input = await page.query_selector(
                    'textarea[name="description"], textarea[data-testid="product-description"]'
                )
                if desc_input:
                    await desc_input.click()
                    await desc_input.fill('')
                    await page.keyboard.type(description, delay=20)
                    logger.info("已填写描述")

            await self.browser.random_sleep(800, 1500)

            category = product.get('category', '')
            if category:
                category_btn = await page.query_selector(
                    '[data-testid="category-selector"], .category-select'
                )
                if category_btn:
                    await category_btn.click()
                    await self.browser.random_sleep(500, 1000)
                    categories = category.split('>')
                    for cat in categories:
                        cat = cat.strip()
                        cat_option = await page.query_selector(f'text="{cat}"')
                        if cat_option:
                            await cat_option.click()
                            await self.browser.random_sleep(300, 800)

            await self.browser.random_sleep(800, 1500)

            condition = product.get('condition', '目立った傷や汚れなし')
            condition_btn = await page.query_selector(
                '[data-testid="condition-selector"], .condition-select'
            )
            if condition_btn:
                await condition_btn.click()
                await self.browser.random_sleep(500, 1000)
                cond_option = await page.query_selector(f'text="{condition}"')
                if cond_option:
                    await cond_option.click()

            await self.browser.random_sleep(800, 1500)

            shipping_payer = product.get('shipping_payer', '送料込み(出品者負担)')
            ship_btn = await page.query_selector(
                '[data-testid="shipping-payer-selector"]'
            )
            if ship_btn:
                await ship_btn.click()
                await self.browser.random_sleep(500, 1000)
                ship_option = await page.query_selector(f'text="{shipping_payer}"')
                if ship_option:
                    await ship_option.click()

            await self.browser.random_sleep(800, 1500)

            price = product.get('price', 0)
            if price:
                price_input = await page.query_selector(
                    'input[name="price"], input[data-testid="product-price"]'
                )
                if price_input:
                    await price_input.click()
                    await price_input.fill('')
                    await page.keyboard.type(str(price), delay=50)
                    logger.info(f"已填写价格: ¥{price}")

            await self.browser.random_sleep(1000, 2000)

            submit_btn = await page.query_selector(
                'button[data-testid="sell-button"], button:has-text("出品する")'
            )
            if submit_btn:
                await submit_btn.click()
                logger.info("已点击发布按钮")
                await self.browser.random_sleep(3000, 5000)

                current_url = page.url
                if '/item/' in current_url:
                    mercari_id = current_url.split('/item/')[-1].split('?')[0]
                    logger.info(f"商品发布成功! ID: {mercari_id}")
                    return mercari_id

            logger.warning("无法确认发布结果，可能需要手动检查")
            return None

        except Exception as e:
            logger.error(f"发布商品出错: {e}")
            return None

    async def update_price(self, mercari_id: str, new_price: int) -> bool:
        try:
            edit_url = f"{BASE_URL}/sell/edit/{mercari_id}"
            await self.browser.navigate(edit_url)
            await self.browser.random_sleep(2000, 4000)
            page = self.browser.page

            price_input = await page.query_selector(
                'input[name="price"], input[data-testid="product-price"]'
            )
            if price_input:
                await price_input.click()
                await price_input.fill('')
                await page.keyboard.type(str(new_price), delay=50)
                await self.browser.random_sleep(500, 1000)

                save_btn = await page.query_selector(
                    'button[data-testid="update-button"], button:has-text("変更する")'
                )
                if save_btn:
                    await save_btn.click()
                    await self.browser.random_sleep(2000, 4000)
                    logger.info(f"价格更新成功: {mercari_id} → ¥{new_price}")
                    return True

            logger.warning(f"无法更新价格: {mercari_id}")
            return False
        except Exception as e:
            logger.error(f"更新价格出错: {e}")
            return False

    async def check_messages(self) -> list[dict]:
        try:
            await self.browser.navigate(f"{BASE_URL}/mypage/notifications")
            await self.browser.random_sleep(2000, 3000)
            page = self.browser.page

            messages = []
            notification_items = await page.query_selector_all(
                '[data-testid="notification-item"], .notification-item'
            )

            for item in notification_items[:10]:
                text = await item.text_content()
                link = await item.query_selector('a')
                href = await link.get_attribute('href') if link else ''
                messages.append({
                    'text': text.strip() if text else '',
                    'link': href,
                    'product_id': href.split('/item/')[-1].split('/')[0] if '/item/' in href else ''
                })

            logger.info(f"获取到 {len(messages)} 条通知")
            return messages
        except Exception as e:
            logger.error(f"检查消息出错: {e}")
            return []

    async def reply_to_comment(self, product_url: str, reply_text: str) -> bool:
        try:
            await self.browser.navigate(product_url)
            await self.browser.random_sleep(2000, 3000)
            page = self.browser.page

            comment_input = await page.query_selector(
                'textarea[name="comment"], textarea[data-testid="comment-input"]'
            )
            if comment_input:
                await comment_input.click()
                await page.keyboard.type(reply_text, delay=30)
                await self.browser.random_sleep(500, 1000)

                send_btn = await page.query_selector(
                    'button[data-testid="comment-submit"], button:has-text("コメントする")'
                )
                if send_btn:
                    await send_btn.click()
                    await self.browser.random_sleep(2000, 3000)
                    logger.info(f"回复成功: {product_url}")
                    return True

            logger.warning(f"无法回复: {product_url}")
            return False
        except Exception as e:
            logger.error(f"回复出错: {e}")
            return False

    async def get_product_comments(self, product_url: str) -> list[dict]:
        try:
            await self.browser.navigate(product_url)
            await self.browser.random_sleep(2000, 3000)
            page = self.browser.page

            comments = []
            comment_items = await page.query_selector_all(
                '[data-testid="comment-item"], .comment-item'
            )

            for item in comment_items:
                username_el = await item.query_selector('.comment-username, [data-testid="comment-user"]')
                body_el = await item.query_selector('.comment-body, [data-testid="comment-body"]')
                username = await username_el.text_content() if username_el else ''
                body = await body_el.text_content() if body_el else ''
                comments.append({
                    'username': username.strip(),
                    'body': body.strip()
                })

            return comments
        except Exception as e:
            logger.error(f"获取评论出错: {e}")
            return []

    async def get_my_listings(self) -> list[dict]:
        return await self.fetch_my_listings()
