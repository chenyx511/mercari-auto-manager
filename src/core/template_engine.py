import re
from src.utils.logger import setup_logger

logger = setup_logger("template")

CATEGORY_MAPPING = {
    "服": "レディース > トップス",
    "シャツ": "メンズ > トップス > シャツ",
    "Tシャツ": "メンズ > トップス > Tシャツ/カットソー",
    "パンツ": "メンズ > パンツ",
    "ジャケット": "メンズ > ジャケット/アウター",
    "コート": "メンズ > ジャケット/アウター > コート",
    "スニーカー": "メンズ > 靴 > スニーカー",
    "バッグ": "メンズ > バッグ",
    "時計": "メンズ > 小物 > 時計",
    "ワンピース": "レディース > ワンピース",
    "スカート": "レディース > スカート",
    "化粧品": "コスメ・香水・美容 > ベースメイク",
    "香水": "コスメ・香水・美容 > 香水",
    "本": "本・音楽・ゲーム > 本",
    "漫画": "本・音楽・ゲーム > 本 > 漫画",
    "ゲーム": "本・音楽・ゲーム > テレビゲーム",
    "CD": "本・音楽・ゲーム > CD",
    "DVD": "本・音楽・ゲーム > DVD/ブルーレイ",
    "スマホ": "家電・スマホ・カメラ > スマートフォン/携帯電話",
    "iPhone": "家電・スマホ・カメラ > スマートフォン/携帯電話 > スマートフォン本体",
    "カメラ": "家電・スマホ・カメラ > カメラ",
    "パソコン": "家電・スマホ・カメラ > PC/タブレット",
    "イヤホン": "家電・スマホ・カメラ > オーディオ機器 > イヤフォン",
    "フィギュア": "おもちゃ・ホビー・グッズ > フィギュア",
    "ぬいぐるみ": "おもちゃ・ホビー・グッズ > ぬいぐるみ",
    "食器": "インテリア・住まい・小物 > キッチン/食器",
    "インテリア": "インテリア・住まい・小物 > インテリア小物",
    "スポーツ": "スポーツ・レジャー",
    "ゴルフ": "スポーツ・レジャー > ゴルフ",
    "自転車": "スポーツ・レジャー > 自転車",
    "ベビー": "ベビー・キッズ",
    "ペット": "その他 > ペット用品",
}

BRAND_KEYWORDS = [
    "NIKE", "ナイキ", "Adidas", "アディダス",
    "UNIQLO", "ユニクロ", "GU", "ジーユー",
    "ZARA", "ザラ", "H&M",
    "GUCCI", "グッチ", "Louis Vuitton", "ルイヴィトン",
    "CHANEL", "シャネル", "Hermès", "エルメス",
    "Supreme", "シュプリーム",
    "Apple", "アップル", "Sony", "ソニー",
    "Nintendo", "任天堂",
    "MUJI", "無印良品",
]

TITLE_SEO_KEYWORDS = {
    "服": ["新品", "美品", "送料無料", "即購入OK"],
    "電子": ["動作確認済み", "美品", "付属品あり", "送料無料"],
    "本": ["美品", "初版", "帯付き", "送料無料"],
    "ゲーム": ["動作確認済み", "ソフト", "送料無料", "即購入OK"],
    "一般": ["美品", "送料無料", "即購入OK", "お値下げ"],
}


class TemplateEngine:
    """基于规则和模板的商品信息优化引擎"""

    def optimize_title(self, title: str, category: str = "") -> str:
        """优化商品标题以提升搜索排名"""
        if not title:
            return title

        optimized = title.strip()

        # 限制 Mercari 标题长度 40 字
        max_len = 40

        brand = self._detect_brand(optimized)

        seo_category = self._detect_seo_category(optimized, category)
        seo_words = TITLE_SEO_KEYWORDS.get(seo_category, TITLE_SEO_KEYWORDS["一般"])

        parts = []
        if brand and brand not in optimized:
            parts.append(brand)
        parts.append(optimized)

        for word in seo_words:
            candidate = " ".join(parts + [word])
            if len(candidate) <= max_len and word not in optimized:
                parts.append(word)

        result = " ".join(parts)
        if len(result) > max_len:
            result = result[:max_len]

        logger.info(f"标题优化: '{title}' → '{result}'")
        return result

    def generate_description(self, product: dict) -> str:
        """基于商品信息生成描述模板"""
        title = product.get('title', '')
        condition = product.get('condition', '目立った傷や汚れなし')
        category = product.get('category', '')
        notes = product.get('notes', '')

        brand = self._detect_brand(title)

        lines = []
        lines.append(f"【{title}】")
        lines.append("")

        if brand:
            lines.append(f"▪ ブランド: {brand}")

        lines.append(f"▪ 商品の状態: {condition}")

        if category:
            lines.append(f"▪ カテゴリ: {category}")

        lines.append("")
        lines.append("【商品説明】")
        if notes:
            lines.append(notes)
        else:
            lines.append(f"{title}です。")
            lines.append(f"状態は「{condition}」です。")

        lines.append("")
        lines.append("【発送について】")
        lines.append("▪ 送料込み（出品者負担）")
        lines.append("▪ 1〜2日で発送いたします")
        lines.append("▪ 匿名配送対応")
        lines.append("")
        lines.append("【注意事項】")
        lines.append("▪ 即購入OKです")
        lines.append("▪ コメントなしで購入いただけます")
        lines.append("▪ 商品の状態は写真をご確認ください")
        lines.append("")
        lines.append("#メルカリ #送料無料 #即購入OK")

        if brand:
            brand_tag = brand.replace(" ", "")
            lines[-1] += f" #{brand_tag}"

        description = "\n".join(lines)
        logger.info(f"描述已生成 ({len(description)} 字)")
        return description

    def suggest_category(self, title: str) -> str:
        """根据标题关键词推荐分类"""
        if not title:
            return ""

        best_match = ""
        best_len = 0

        for keyword, category in CATEGORY_MAPPING.items():
            if keyword in title and len(keyword) > best_len:
                best_match = category
                best_len = len(keyword)

        if best_match:
            logger.info(f"分类推荐: '{title}' → '{best_match}'")
        return best_match

    def _detect_brand(self, text: str) -> str:
        """从文本中检测品牌名"""
        text_upper = text.upper()
        for brand in BRAND_KEYWORDS:
            if brand.upper() in text_upper:
                return brand
        return ""

    def _detect_seo_category(self, title: str, category: str) -> str:
        """判断商品的 SEO 类别"""
        combined = f"{title} {category}"
        clothing_words = ["服", "シャツ", "パンツ", "ジャケット", "ワンピース", "コート"]
        if any(w in combined for w in clothing_words):
            return "服"

        electronic_words = ["スマホ", "パソコン", "カメラ", "iPhone", "イヤホン", "電子"]
        if any(w in combined for w in electronic_words):
            return "電子"

        book_words = ["本", "漫画", "雑誌", "書籍"]
        if any(w in combined for w in book_words):
            return "本"

        game_words = ["ゲーム", "Nintendo", "PS5", "Switch"]
        if any(w in combined for w in game_words):
            return "ゲーム"

        return "一般"

    def process_product(self, product: dict) -> dict:
        """一键优化商品信息"""
        title = product.get('title', '')
        category = product.get('category', '')

        if not category:
            category = self.suggest_category(title)
            product['category'] = category

        product['title'] = self.optimize_title(title, category)
        product['description'] = self.generate_description(product)

        return product
