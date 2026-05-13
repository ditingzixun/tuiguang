"""AI文案生成引擎 -- 关键词驱动 + 大模型API + 模板降级 + 伪原创"""
import re
import random
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader
from utils.text_filter import SensitiveWordFilter
from core.ai_provider import ai_provider_manager


# ====== 提示词模板 ======

SYSTEM_PROMPTS = {
    "soft_article": (
        '你是一位资深的企业服务推广文案专家，擅长撰写自然、有说服力的软文。'
        '写作风格：口语化、有温度，像朋友聊天一样推荐服务。'
        '避免AI感强的表达，避免过度营销。'
        '文章结构：痛点引入 -> 解决方案 -> 服务优势 -> 行动号召。'
        '直接返回Markdown格式的完整文章，不要额外说明。'
    ),
    "science_article": (
        '你是一位专业的资质办理顾问，擅长用通俗语言解释复杂的政策法规。'
        '写作风格：条理清晰、逻辑严密、数据详实，像一个资深顾问在解答客户疑问。'
        '文章结构：定义说明 -> 适用对象 -> 办理条件 -> 办理流程 -> 注意事项 -> FAQ。'
        '直接返回Markdown格式的完整文章，不要额外说明。'
    ),
    "comparison_article": (
        '你是一位客观中立的行业分析师，擅长用对比和数据分析帮企业做出决策。'
        '写作风格：客观理性、数据说话，用表格和清单对比不同方案。'
        '文章结构：问题引入 -> 方案A分析 -> 方案B分析 -> 对比表格 -> 结论建议。'
        '直接返回Markdown格式的完整文章，不要额外说明。'
    ),
    "policy_article": (
        '你是一位政策研究专家，擅长解读最新的行政许可和政策变化。'
        '写作风格：专业严谨但非学术化，让企业老板能看懂政策影响。'
        '文章结构：政策背景 -> 核心变化 -> 对企业的影响 -> 应对建议 -> 未来趋势。'
        '直接返回Markdown格式的完整文章，不要额外说明。'
    ),
    "case_study": (
        '你是一位商业案例作者，擅长通过讲故事的方式展示服务价值。'
        '写作风格：叙事性强、生动具体，像是分享一个真实的成功故事。'
        '文章结构：客户背景 -> 遇到的困难 -> 解决方案 -> 办理过程 -> 最终成果 -> 客户评价。'
        '直接返回Markdown格式的完整文章，不要额外说明。'
    ),
}

USER_PROMPT_TEMPLATES = {
    "soft_article": (
        '请围绕关键词 [{keyword}] 撰写一篇软文推广文章。\n'
        '要求：\n'
        '- 标题吸引人，包含关键词\n'
        '- 正文 {min_words}-{max_words} 字\n'
        '- 自然地融入以下要点：办理条件、流程、周期、费用优势\n'
        '{company_section}'
        '- 使用小标题分段，方便阅读\n'
        '- 结尾引导用户咨询或留言'
    ),
    "science_article": (
        '请围绕关键词 [{keyword}] 撰写一篇科普解读文章。\n'
        '要求：\n'
        '- 标题以"什么是""解读""详解"等开头\n'
        '- 正文 {min_words}-{max_words} 字\n'
        '- 解释清楚这个资质的定义、谁需要办理、不办的后果\n'
        '- 列出具体的办理条件和材料清单\n'
        '- 说明办理流程和周期\n'
        '{company_section}'
        '- 使用小标题分段，条理清晰'
    ),
    "comparison_article": (
        '请围绕关键词 [{keyword}] 撰写一篇对比分析文章。\n'
        '要求：\n'
        '- 标题突出"对比""哪个好""怎么选"\n'
        '- 正文 {min_words}-{max_words} 字\n'
        '- 对比"自己办理"和"找代办机构"两种方式\n'
        '- 从时间、费用、通过率、省心程度等维度对比\n'
        '- 使用对比表格\n'
        '{company_section}'
        '- 给出明确的选择建议'
    ),
    "policy_article": (
        '请围绕关键词 [{keyword}] 撰写一篇政策解读文章。\n'
        '要求：\n'
        '- 标题包含"政策""新规""最新"等关键词\n'
        '- 正文 {min_words}-{max_words} 字\n'
        '- 介绍最新的政策动态和监管趋势\n'
        '- 分析政策变化对企业的影响\n'
        '- 给出企业的应对建议和时间窗口\n'
        '{company_section}'
        '- 使用小标题分段'
    ),
    "case_study": (
        '请围绕关键词 [{keyword}] 撰写一篇成功案例文章。\n'
        '要求：\n'
        '- 标题包含"案例""成功""经验"等关键词\n'
        '- 正文 {min_words}-{max_words} 字\n'
        '- 以一个虚拟但真实的客户故事为主线\n'
        '- 描述客户办理前的困境和担忧\n'
        '- 展示办理的过程和关键节点\n'
        '- 分享最终的成果和数据\n'
        '{company_section}'
        '- 结尾提炼可复制的经验'
    ),
}

REWRITE_SYSTEM_PROMPT = (
    '你是一位专业的内容编辑，擅长在不改变原意的前提下进行深度改写。'
    '改写原则：保留核心信息和关键词，但更换表达方式。'
    '具体技巧：调整段落顺序、换用同义词、改变句式结构、合并或拆分句子。'
    '直接返回改写后的完整内容，不要额外说明。'
)

REWRITE_USER_PROMPT = (
    '请对以下内容进行伪原创改写（改写强度：{intensity}）。\n'
    '{extra_instruction}'
    '原文如下：\n\n{content}'
)

TITLE_SYSTEM_PROMPT = (
    '你是一位擅长标题创作的营销文案专家。'
    '为给定的关键词生成多样化的文章标题，覆盖不同类型。'
    '每个标题不超过30字，要吸引眼球但不标题党。'
    '直接返回标题列表，每行一个，用换行分隔，不要编号。'
)

TITLE_USER_PROMPT = (
    '请围绕关键词 [{keyword}] 生成 {count} 个不同类型的文章标题。\n'
    '类型分布:\n'
    '- 30% 疑问型 (如: 办理XX需要什么条件?)\n'
    '- 25% 数字型 (如: 办理XX的3个关键步骤)\n'
    '- 20% 对比型 (如: 自己办还是找代办? XX办理方式对比)\n'
    '- 15% 故事型 (如: 从零到拿证的XX办理之路)\n'
    '- 10% 紧迫型 (如: XX新规已实施, 你的企业合规了吗?)\n'
)


# ====== 资质信息库（模板降级后备） ======

QUALIFICATION_INFO = {
    "网络文化经营许可证": {
        "short": "文网文", "desc": "网络文化经营许可证是从事互联网文化活动的企业必须具备的资质证书",
        "apply_dept": "文化和旅游部门", "validity": "3年",
        "key_points": ["注册资金100万以上", "有确定的互联网文化活动范围", "有相应的专业人员"],
    },
    "ICP经营许可证": {
        "short": "ICP", "desc": "ICP经营许可证是经营性网站必须办理的增值电信业务经营许可证",
        "apply_dept": "通信管理局", "validity": "5年",
        "key_points": ["注册资金100万以上", "公司为内资企业", "有相应的网站"],
    },
    "EDI经营许可证": {
        "short": "EDI", "desc": "EDI经营许可证是在线数据处理与交易处理业务许可证",
        "apply_dept": "通信管理局", "validity": "5年",
        "key_points": ["注册资金100万以上", "有交易处理平台", "具备安全保障措施"],
    },
    "广播电视节目制作经营许可证": {
        "short": "广电证", "desc": "从事广播电视节目制作业务必须取得的许可证",
        "apply_dept": "广播电视局", "validity": "2年",
        "key_points": ["有专业人员", "有必要的设备", "注册资金300万以上"],
    },
    "增值电信业务经营许可证": {
        "short": "增值电信证", "desc": "经营增值电信业务的企业必须取得的资质证书",
        "apply_dept": "通信管理局", "validity": "5年",
        "key_points": ["公司注册资金满足要求", "无外资成分", "有社保人员"],
    },
}


# ====== 伪原创同义词库 ======

SYNONYM_DICT = {
    "办理": ["申办", "申请", "代办", "拿下", "搞定"],
    "企业": ["公司", "机构", "企业单位", "经营主体"],
    "需要": ["须要", "要求", "必须", "必须满足", "应当"],
    "条件": ["门槛", "要求", "标准", "硬性条件"],
    "流程": ["步骤", "环节", "程序", "阶段"],
    "费用": ["成本", "花费", "支出", "价格"],
    "时间": ["周期", "期限", "时长", "时限"],
    "优势": ["好处", "优点", "利好", "价值"],
    "专业": ["资深", "靠谱", "经验丰富", "老牌"],
    "帮助": ["协助", "辅助", "支持", "帮忙"],
    "通过率": ["成功率", "下证率", "获批率"],
    "重要的": ["关键的", "核心的", "必不可少的", "至关重要的"],
    "提高": ["提升", "增强", "加强", "优化"],
    "减少": ["降低", "缩短", "削减", "压缩"],
    "确保": ["保证", "保障", "确认", "核实"],
    "问题": ["难题", "痛点", "难点", "困难"],
    "解决": ["处理", "应对", "搞定", "化解"],
    "选择": ["挑选", "甄选", "抉择", "选定"],
    "服务": ["代办服务", "专业服务", "一条龙服务"],
    "快速": ["高效", "快捷", "省时", "加急"],
    "推荐": ["建议", "倾情推荐", "首选"],
    "全面": ["全方位", "一站式", "系统化", "全流程"],
    "安全": ["可靠", "稳妥", "有保障", "安心"],
    "经验": ["案例", "实操经验", "行业积淀"],
}

TITLE_TEMPLATES = {
    "soft_article": [
        "办理{keyword}需要什么条件？资深顾问一文讲透",
        "{year}年{keyword}办理全攻略，少走弯路看这篇就够了",
        "为什么企业都要办{keyword}？这些好处你可能不知道",
        "{keyword}代办哪家好？选择专业服务的3大标准",
        "别再自己跑{keyword}了，专业代办帮你省时又省心",
    ],
    "science_article": [
        "什么是{keyword}？一文读懂全解析",
        "{keyword}办理流程详解：从准备到拿证的完整指南",
        "企业需要办理{keyword}吗？自测清单来了",
        "{keyword}办理条件逐条解读，企业老板必读",
    ],
    "comparison_article": [
        "自己办还是找代办？{keyword}办理方式对比分析",
        "为什么越来越多的企业选择代办{keyword}？深度对比",
        "{keyword}代办费用解析：代办比自己办贵在哪？",
        "3分钟看懂：{keyword}代办 vs 自己办，哪个更划算",
    ],
    "policy_article": [
        "{year}年{keyword}最新政策解读，企业必看",
        "新规来了！{keyword}办理条件有哪些变化？",
        "深入解读：{keyword}新规办理门槛是升是降？",
    ],
    "case_study": [
        "成功案例：某科技公司{keyword}办理经验分享",
        "从零到一：{keyword}办理真实案例全记录",
        "一个月拿下{keyword}，这家公司做对了什么？",
    ],
}

CONTENT_WORD_RANGES = {
    "soft_article": (800, 1500),
    "science_article": (1000, 2000),
    "comparison_article": (800, 1500),
    "policy_article": (800, 1500),
    "case_study": (600, 1200),
}


class AIContentEngine:
    """AI文案生成引擎 -- API优先 + 模板降级"""

    def __init__(self):
        cfg = config_loader
        self.max_tokens = cfg.get_int("AI_MAX_TOKENS", 2048)
        self.temperature = cfg.get_float("AI_TEMPERATURE", 0.8)
        self.filter = SensitiveWordFilter()

    @property
    def ai_enabled(self):
        return config_loader.get_bool("AI_ENABLED", False)

    @property
    def fallback_template(self):
        return config_loader.get_bool("AI_FALLBACK_TEMPLATE", True)



    def generate_by_keyword(self, keyword: str, content_type: str,
                            company_name: str = "", min_words: int = None,
                            max_words: int = None) -> Optional[dict]:
        """关键词驱动生成文案"""
        if content_type not in USER_PROMPT_TEMPLATES:
            logger.error(f"不支持的文章类型: {content_type}")
            return None

        if min_words is None or max_words is None:
            min_words, max_words = CONTENT_WORD_RANGES.get(
                content_type, (800, 1500)
            )

        if self.ai_enabled:
            result = self._generate_via_api(keyword, content_type, company_name, min_words, max_words)
            if result:
                logger.info(f"API生成成功 [{content_type}]: {keyword}")
                return result

        if self.fallback_template:
            logger.info(f"降级到模板生成 [{content_type}]: {keyword}")
            return self._generate_via_template(keyword, content_type, company_name)

        return None



    def _generate_via_api(self, keyword: str, content_type: str,
                           company_name: str, min_words: int, max_words: int) -> Optional[dict]:
        """通过AI提供商生成文案"""
        provider = ai_provider_manager.active_provider
        if not provider.is_available():
            return None

        system_prompt = SYSTEM_PROMPTS.get(content_type, SYSTEM_PROMPTS["soft_article"])
        company_section = ""
        if company_name:
            company_section = (
                f'- 在文中自然地提到 [{company_name}] 作为专业代办机构\n'
                f'- 结尾可加上 -- {company_name}，专注资质代办服务\n'
            )
        user_prompt = USER_PROMPT_TEMPLATES[content_type].format(
            keyword=keyword,
            min_words=min_words,
            max_words=max_words,
            company_section=company_section,
        )

        full_text = provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        if not full_text:
            return None

        title, content = self._parse_markdown(full_text, keyword, content_type)
        filtered = self.filter.filter(content)
        return {
            "title": title,
            "content": filtered,
            "content_type": content_type,
            "qualification_type": keyword,
            "keywords": keyword,
            "source": f"ai({provider.name})",
            "generated_at": datetime.now().isoformat(),
        }

    def _parse_markdown(self, text: str, keyword: str, content_type: str) -> tuple:
        """从AI生成的Markdown中解析标题和正文"""
        lines = text.strip().split("\n")
        title = ""
        body_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# ") and not title:
                title = stripped[2:].strip()
                body_start = i + 1
            elif stripped and not title:
                title = stripped.lstrip("#").strip()
                body_start = i + 1
                break

        if not title:
            title_tmpl = random.choice(TITLE_TEMPLATES.get(content_type, TITLE_TEMPLATES["soft_article"]))
            title = title_tmpl.format(keyword=keyword, year=datetime.now().year)

        content = "\n".join(lines[body_start:]).strip()
        if not content or len(content) < 100:
            content = text.strip()

        return title, content



    def _generate_via_template(self, keyword: str, content_type: str,
                                company_name: str = "") -> Optional[dict]:
        """模板方式生成文案"""
        qual_info = QUALIFICATION_INFO.get(keyword)
        if not qual_info:
            qual_info = {
                "short": keyword,
                "desc": f"{keyword}是企业在经营过程中需要办理的重要资质证书",
                "apply_dept": "相关主管部门",
                "validity": "3-5年",
                "key_points": ["具备合法的经营主体资格", "符合行业准入条件", "有相应的专业人员和设备"],
            }

        year = datetime.now().year
        titles = TITLE_TEMPLATES.get(content_type, TITLE_TEMPLATES["soft_article"])
        title = random.choice(titles).format(keyword=keyword, year=year)
        content = self._build_template_content(keyword, qual_info, content_type, company_name)
        filtered = self.filter.filter(content)

        return {
            "title": title,
            "content": filtered,
            "content_type": content_type,
            "qualification_type": keyword,
            "keywords": keyword,
            "source": "local_template",
            "generated_at": datetime.now().isoformat(),
        }

    def _build_template_content(self, qual_type: str, info: dict,
                                  content_type: str, company_name: str) -> str:
        """构建模板文章内容"""
        desc = info["desc"]
        dept = info["apply_dept"]
        validity = info["validity"]
        points = info["key_points"]

        section_map = {
            "soft_article": [
                f"## 什么是{qual_type}？",
                f"{desc}。该证书由{dept}颁发，有效期{validity}。",
                f"## 为什么需要办理{qual_type}？",
                f"在当前监管环境下，{qual_type}已成为企业合法经营的必备资质。"
                f"没有该证书，企业将面临罚款、停业整顿等处罚风险。",
                f"## 办理条件",
                "\n".join(f"- {p}" for p in points),
                f"## 办理流程",
                f"1. 准备申请材料\n2. 向{dept}提交申请\n"
                f"3. 材料审核（约20-30个工作日）\n4. 现场核查\n5. 领取证书",
                f"## 选择专业代办的优势",
                f"- 熟悉流程，大幅缩短办理周期\n- 材料准备专业，提高通过率\n"
                f"- 全程跟踪，省心省力\n- 处理各种疑难问题",
            ],
            "science_article": [
                f"## {qual_type}的定义", f"{desc}",
                f"## 适用企业类型",
                f"凡是在中国境内从事相关经营活动的企业，均需依法办理{qual_type}。",
                f"## 办理条件详解",
                "\n".join(f"### {i+1}. {p}" for i, p in enumerate(points)),
                f"## 办理流程",
                f"1. 准备阶段：收集企业资质文件\n2. 申请阶段：向{dept}提交材料\n"
                f"3. 审核阶段：等待{dept}审核\n4. 获证阶段：领取证书",
                f"## 注意事项",
                f"- 证书有效期{validity}，到期前需续期\n- 企业信息变更需及时更新",
            ],
            "comparison_article": [
                f"## 自主办理 vs 代办服务",
                f"### 自主办理",
                f"- 优点：费用低\n- 缺点：耗时长（3-6个月）、通过率低、材料反复修改",
                f"### 专业代办",
                f"- 优点：周期短（1-2个月）、通过率高（95%+）、全程服务\n- 缺点：需要服务费用",
                f"## 成本对比",
                f"| 项目 | 自主办理 | 专业代办 |\n|------|---------|----------|\n"
                f"| 时间成本 | 3-6个月 | 1-2个月 |\n"
                f"| 人员成本 | 2-3人 | 无需专人 |\n"
                f"| 通过率 | 60-70% | 95%+ |\n"
                f"| 补交材料 | 3-5次 | 0-1次 |",
                f"## 结论",
                f"对于大多数企业来说，专业代办服务能大幅节省时间成本，降低办理风险。",
            ],
            "policy_article": [
                f"## {qual_type}最新政策动态",
                f"近年来，{dept}对{qual_type}的监管力度持续加强。",
                f"## 主要政策变化",
                f"1. 审批流程优化：推行一网通办，缩短审批时限\n"
                f"2. 监管力度加强：无证经营处罚力度加大\n"
                f"3. 续期要求明确：证书到期前3个月需启动续期流程",
                f"## 对企业的影响",
                f"- 合规成本短期上升\n- 长期来看有利于行业规范发展\n- 建议企业提前布局",
            ],
            "case_study": [
                f"## 案例背景",
                f"某互联网科技公司，主营在线业务，需办理{qual_type}。",
                f"## 办理过程",
                f"1. 第1周：准备材料，发现并解决企业资质问题\n"
                f"2. 第2-3周：提交申请，材料一次性通过\n"
                f"3. 第4-6周：等待审批\n4. 第7周：顺利通过核查，领取证书",
                f"## 经验总结",
                f"- 提前准备是成功的关键\n- 专业团队指导可避免大量弯路\n- 选择有经验的代办机构至关重要",
            ],
        }

        parts = section_map.get(content_type, section_map["soft_article"])
        content = f"# {qual_type}办理指南\n\n" + "\n\n".join(parts)

        if company_name:
            content += f"\n\n---\n**{company_name}** -- 专注资质代办服务，已成功服务1000+企业。"

        return content



    def pseudo_rewrite(self, original: str, intensity: str = "medium",
                       title: str = None) -> Optional[dict]:
        """伪原创改写

        Args:
            original: 原文内容
            intensity: 改写强度 (light/medium/heavy)
            title: 原标题（可选）
        """
        intensity_map = {
            "light": "轻度改写：只更换约30%的表达，保持句子结构和段落顺序基本不变",
            "medium": "中度改写：更换约50%的表达，适当调整句式和段落顺序",
            "heavy": "深度改写：更换70%以上的表达，大幅调整结构，融入新的叙述视角",
        }
        extra = intensity_map.get(intensity, intensity_map["medium"])

        if self.ai_enabled:
            provider = ai_provider_manager.active_provider
            if provider.is_available():
                extra_instruction = f'原标题为 [{title}]，请生成一个新的标题。' if title else '请保留原标题。'
                prompt = REWRITE_USER_PROMPT.format(
                    intensity=extra, content=original, extra_instruction=extra_instruction
                )
                result = provider.generate(
                    prompt=prompt,
                    system_prompt=REWRITE_SYSTEM_PROMPT,
                    max_tokens=self.max_tokens,
                    temperature=0.9,
                )
                if result:
                    new_title, new_content = self._parse_markdown(result, "", "soft_article")
                    return {
                        "title": new_title or title or "",
                        "content": self.filter.filter(new_content),
                        "source": f"rewrite_ai({provider.name})",
                    }

        content = self._spin_content(original, intensity)
        return {
            "title": title or "",
            "content": self.filter.filter(content),
            "source": "rewrite_local",
        }

    def _spin_content(self, text: str, intensity: str) -> str:
        """本地同义词替换"""
        intensity_ratio = {"light": 0.15, "medium": 0.40, "heavy": 0.65}.get(intensity, 0.40)

        paragraphs = text.split("\n")
        result = []
        for para in paragraphs:
            if para.startswith("#") or para.startswith("|") or (para.startswith("- ") and len(para) < 20):
                result.append(para)
                continue
            for word, synonyms in SYNONYM_DICT.items():
                if word in para and random.random() < intensity_ratio:
                    para = para.replace(word, random.choice(synonyms), 1)
            result.append(para)

        return "\n".join(result)



    def batch_generate_titles(self, keyword: str, count: int = 20) -> list:
        """批量生成标题库

        Returns: [{"title": str, "type": str, "source": str}, ...]
        """
        titles = []

        if self.ai_enabled:
            provider = ai_provider_manager.active_provider
            if provider.is_available():
                prompt = TITLE_USER_PROMPT.format(keyword=keyword, count=count)
                result = provider.generate(
                    prompt=prompt,
                    system_prompt=TITLE_SYSTEM_PROMPT,
                    max_tokens=500,
                    temperature=0.95,
                )
                if result:
                    for line in result.strip().split("\n"):
                        line = line.strip().lstrip("0123456789.、- )").strip()
                        if line and len(line) >= 8:
                            titles.append({
                                "title": line,
                                "type": self._classify_title_type(line),
                                "source": "ai",
                            })
                    if len(titles) >= count:
                        return titles[:count]

        all_templates = []
        for ct, tmpls in TITLE_TEMPLATES.items():
            for tmpl in tmpls:
                t = tmpl.format(keyword=keyword, year=datetime.now().year)
                all_templates.append({"title": t, "type": ct, "source": "template"})

        while len(all_templates) < count:
            base = random.choice(all_templates)["title"]
            spun = self._spin_content(base, "light")
            all_templates.append({"title": spun, "type": "soft_article", "source": "spin"})

        return all_templates[:count]

    def _classify_title_type(self, title: str) -> str:
        """根据标题特征判断类型"""
        if any(w in title for w in ["？", "什么", "怎么", "如何", "吗"]):
            return "疑问型"
        if any(w in title for w in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
            if any(w in title for w in ["步", "个", "条", "大", "招"]):
                return "数字型"
        if any(w in title for w in ["对比", "区别", "哪个", "还是", "选择"]):
            return "对比型"
        if any(w in title for w in ["案例", "经验", "故事", "记录"]):
            return "故事型"
        if any(w in title for w in ["政策", "新规", "最新", "变化"]):
            return "政策型"
        return "综合型"



    def batch_generate(self, keywords: list, content_types: list,
                       count_per_type: int = 3, company_name: str = "") -> list:
        """批量生成文案，返回结果列表"""
        results = []
        for kw in keywords:
            for ct in content_types:
                for i in range(count_per_type):
                    result = self.generate_by_keyword(
                        keyword=kw, content_type=ct,
                        company_name=company_name
                    )
                    if result:
                        result["batch_index"] = i + 1
                        result["batch_keyword"] = kw
                        results.append(result)
        logger.info(f"批量生成完成: {len(keywords)}关键词 x {len(content_types)}类型 = {len(results)}篇")
        return results



    def generate(self, qualification_type: str, content_type: str,
                 company_name: str = "") -> Optional[dict]:
        """兼容旧API"""
        return self.generate_by_keyword(qualification_type, content_type, company_name)


ai_engine = AIContentEngine()
