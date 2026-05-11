"""敏感词过滤模块"""
import re
import random
import jieba
from loguru import logger


class SensitiveWordFilter:
    """敏感词检测与过滤"""

    DEFAULT_SENSITIVE = [
        "代办", "代考", "代写", "办证", "刻章",
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

    def jieba_detect(self, text: str) -> list:
        """使用jieba分词进行更精确的敏感词检测"""
        if not self.enabled:
            return []
        words = set(jieba.lcut(text))
        return list(words & self.words)


class ContentSpinner:
    """伪原创/同义词替换"""

    SYNONYMS = {
        "办理": ["代办", "申办", "代理办理", "协助办理"],
        "资质": ["许可证", "资格证", "经营资质", "准入资质"],
        "企业": ["公司", "单位", "机构", "组织"],
        "需要": ["需", "须", "要求", "必须"],
        "流程": ["步骤", "程序", "过程", "环节"],
        "材料": ["资料", "文件", "证件", "手续"],
        "时间": ["周期", "期限", "时长", "时限"],
        "费用": ["成本", "价格", "收费", "开支"],
        "重要": ["关键", "核心", "首要", "根本"],
        "服务": ["协助", "支持", "帮助", "代办"],
    }

    @classmethod
    def spin(cls, text: str, rate: float = 0.3) -> str:
        """对文本进行伪原创处理"""
        words = list(jieba.cut(text))
        result = []
        for word in words:
            if word in cls.SYNONYMS and random.random() < rate:
                result.append(random.choice(cls.SYNONYMS[word]))
            else:
                result.append(word)
        return "".join(result)
