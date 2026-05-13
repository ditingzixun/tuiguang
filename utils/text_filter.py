"""敏感词过滤模块"""
import re
import logging

logger = logging.getLogger(__name__)


class SensitiveWordFilter:
    """敏感词检测与过滤"""

    DEFAULT_SENSITIVE = [
        "赌博", "博彩", "色情", "违禁", "枪支",
        "贩卖", "走私", "毒品",
    ]

    def __init__(self):
        self.words = set(self.DEFAULT_SENSITIVE)
        self.replace_char = "*"
        self.enabled = True

    def load_words(self, words: list):
        self.words.update(words)
        logger.info(f"已加载 {len(self.words)} 个敏感词")

    def add_word(self, word: str):
        self.words.add(word)

    def remove_word(self, word: str):
        self.words.discard(word)

    def detect(self, text: str) -> list:
        """检测文本中的敏感词，返回命中的敏感词列表"""
        if not self.enabled:
            return []
        text_lower = text.lower()
        return [w for w in self.words if w.lower() in text_lower]

    def filter(self, text: str) -> str:
        """过滤敏感词并替换"""
        if not self.enabled:
            return text
        hit_words = self.detect(text)
        if not hit_words:
            return text
        result = text
        for word in hit_words:
            result = result.replace(word, self.replace_char * len(word))
        if hit_words:
            logger.warning(f"检测到敏感词: {hit_words}")
        return result

    def is_safe(self, text: str) -> bool:
        """检查文本是否安全（不含敏感词）"""
        return len(self.detect(text)) == 0
