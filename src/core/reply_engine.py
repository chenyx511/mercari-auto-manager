import asyncio
from datetime import datetime
from src.automation.browser_manager import BrowserManager
from src.automation.mercari_operations import MercariOperations
from src.data.database import MessageRepository, OperationLogRepository
from src.utils.config import get
from src.utils.logger import setup_logger

logger = setup_logger("reply")


class KeywordMatcher:
    """关键词匹配规则引擎"""

    def __init__(self):
        self.rules = get('auto_reply.rules', [])

    def reload_rules(self):
        from src.utils.config import reload_config
        reload_config()
        self.rules = get('auto_reply.rules', [])

    def find_reply(self, message: str) -> str | None:
        """根据买家消息匹配自动回复"""
        if not message:
            return None

        message_lower = message.lower()

        for rule in self.rules:
            keywords = rule.get('keywords', [])
            reply = rule.get('reply', '')
            if any(kw.lower() in message_lower for kw in keywords):
                logger.info(f"匹配到关键词规则, 消息: '{message[:30]}...'")
                return reply

        return None

    def add_rule(self, keywords: list[str], reply: str):
        self.rules.append({'keywords': keywords, 'reply': reply})

    def remove_rule(self, index: int):
        if 0 <= index < len(self.rules):
            self.rules.pop(index)

    def get_rules(self) -> list[dict]:
        return self.rules


class ReplyEngine:
    """自动回复引擎"""

    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self.mercari = MercariOperations(browser)
        self.matcher = KeywordMatcher()
        self._is_running = False
        self._replied_messages: set[str] = set()
        self._log_callback = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_log_callback(self, callback):
        """callback(buyer_msg, reply_msg, product_id, status)"""
        self._log_callback = callback

    def _notify(self, buyer_msg: str, reply_msg: str, product_id: str, status: str):
        if self._log_callback:
            self._log_callback(buyer_msg, reply_msg, product_id, status)

    async def check_and_reply_once(self) -> int:
        """检查一次消息并自动回复，返回回复数"""
        replied_count = 0

        try:
            listings = await self.mercari.get_my_listings()

            for listing in listings:
                if not self._is_running:
                    break

                product_url = listing.get('url', '')
                if not product_url:
                    continue

                if not product_url.startswith('http'):
                    product_url = f"https://jp.mercari.com{product_url}"

                comments = await self.mercari.get_product_comments(product_url)

                if not comments:
                    continue

                last_comment = comments[-1]
                msg_key = f"{product_url}:{last_comment['body'][:50]}"

                if msg_key in self._replied_messages:
                    continue

                reply = self.matcher.find_reply(last_comment['body'])

                if reply:
                    self._notify(
                        last_comment['body'], reply,
                        listing.get('mercari_id', ''), "回复中..."
                    )

                    success = await self.mercari.reply_to_comment(product_url, reply)

                    if success:
                        self._replied_messages.add(msg_key)
                        replied_count += 1

                        MessageRepository.add({
                            'mercari_product_id': listing.get('mercari_id', ''),
                            'buyer_message': last_comment['body'],
                            'reply_message': reply,
                            'replied_at': datetime.now().isoformat(),
                        })
                        OperationLogRepository.add(
                            'reply', None,
                            f"自动回复: {last_comment['body'][:30]}..."
                        )
                        self._notify(
                            last_comment['body'], reply,
                            listing.get('mercari_id', ''), "回复成功"
                        )
                        logger.info(f"自动回复成功: {last_comment['body'][:30]}...")
                    else:
                        self._notify(
                            last_comment['body'], reply,
                            listing.get('mercari_id', ''), "回复失败"
                        )

                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"检查消息出错: {e}")

        return replied_count

    async def start_monitoring(self):
        """启动自动回复监控循环"""
        if self._is_running:
            logger.warning("自动回复已在运行中")
            return

        self._is_running = True
        interval = get('auto_reply.check_interval_seconds', 120)

        logger.info(f"自动回复监控已启动 (间隔: {interval}秒)")

        while self._is_running:
            try:
                count = await self.check_and_reply_once()
                if count > 0:
                    logger.info(f"本轮自动回复 {count} 条")
            except Exception as e:
                logger.error(f"自动回复循环出错: {e}")

            for _ in range(interval):
                if not self._is_running:
                    break
                await asyncio.sleep(1)

        logger.info("自动回复监控已停止")

    def stop(self):
        self._is_running = False
        logger.info("自动回复引擎收到停止信号")
