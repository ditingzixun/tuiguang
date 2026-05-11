"""AI文案生成引擎 - 对接大模型API批量生成资质代办文案"""
import json
import random
from datetime import datetime
from typing import Optional
from openai import OpenAI
from loguru import logger
from utils.config_loader import config_loader
from utils.text_filter import SensitiveWordFilter, ContentSpinner


class AIContentEngine:
    """AI文案生成引擎"""

    QUALIFICATION_INFO = {
        "网络文化经营许可证": {
            "short": "文网文",
            "desc": "网络文化经营许可证是从事互联网文化活动的企业必须具备的资质证书",
            "apply_dept": "文化和旅游部门",
            "validity": "3年",
            "key_points": ["注册资金100万以上", "有确定的互联网文化活动范围", "有相应的专业人员"],
        },
        "ICP经营许可证": {
            "short": "ICP",
            "desc": "ICP经营许可证是经营性网站必须办理的增值电信业务经营许可证",
            "apply_dept": "通信管理局",
            "validity": "5年",
            "key_points": ["注册资金100万以上", "公司为内资企业", "有相应的网站"],
        },
        "EDI经营许可证": {
            "short": "EDI",
            "desc": "EDI经营许可证是在线数据处理与交易处理业务许可证",
            "apply_dept": "通信管理局",
            "validity": "5年",
            "key_points": ["注册资金100万以上", "有交易处理平台", "具备安全保障措施"],
        },
        "广播电视节目制作经营许可证": {
            "short": "广电证",
            "desc": "从事广播电视节目制作业务必须取得的许可证",
            "apply_dept": "广播电视局",
            "validity": "2年",
            "key_points": ["有专业人员", "有必要的设备", "注册资金300万以上"],
        },
        "增值电信业务经营许可证": {
            "short": "增值电信证",
            "desc": "经营增值电信业务的企业必须取得的资质证书",
            "apply_dept": "通信管理局",
            "validity": "5年",
            "key_points": ["公司注册资金满足要求", "无外资成分", "有社保人员"],
        },
    }

    CONTENT_TEMPLATES = {
        "soft_article": "以{qualification}办理为主题，写一篇推广软文，重点突出办理{qualification}的必要性和选择专业代办的优势，语气专业可信",
        "science_article": "以{qualification}为主题，写一篇科普文章，详细介绍{qualification}的定义、办理流程、所需材料、注意事项等，客观专业，带有教育性质",
        "comparison_article": "以{qualification}为主题，写一篇对比分析文章，对比自主办理vs代办服务的优劣势，用数据和案例说明代办服务的价值",
        "policy_article": "以{qualification}为主题，写一篇政策解读文章，解读最新的{qualification}相关政策和法规变化，分析对企业的影响",
        "case_study": "以{qualification}为主题，写一篇案例分享文章，以成功办理{qualification}的企业为例，展示办理过程和效果",
    }

    def __init__(self):
        cfg = config_loader.config.get("ai_content", {})
        self.provider = cfg.get("provider", "openai")
        self.api_url = cfg.get("api_url", "https://api.openai.com/v1")
        self.api_key = cfg.get("api_key", "")
        self.model = cfg.get("model", "gpt-4")
        self.max_tokens = cfg.get("max_tokens", 2000)
        self.temperature = cfg.get("temperature", 0.8)
        self.client = None
        self.filter = SensitiveWordFilter()
        self.spinner = ContentSpinner()
        if self.api_key:
            self._init_client()

    def _init_client(self):
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url)

    def set_api_key(self, key: str, url: str = None):
        self.api_key = key
        if url:
            self.api_url = url
        self._init_client()

    def generate(self, qualification_type: str, content_type: str,
                 keywords: list = None, company_name: str = "",
                 extra_requirements: str = "") -> Optional[dict]:
        """生成文案"""
        if qualification_type not in self.QUALIFICATION_INFO:
            logger.error(f"不支持的资质类型: {qualification_type}")
            return None

        qual_info = self.QUALIFICATION_INFO[qualification_type]
        template = self.CONTENT_TEMPLATES.get(content_type, self.CONTENT_TEMPLATES["soft_article"])

        prompt = template.format(qualification=qualification_type)
        if keywords:
            prompt += f"\n\n请在文章中自然融入以下关键词：{', '.join(keywords)}"
        if company_name:
            prompt += f"\n\n服务公司名称为：{company_name}"
        if extra_requirements:
            prompt += f"\n\n额外要求：{extra_requirements}"
        prompt += f"\n\n{qualification_type}的关键信息：{json.dumps(qual_info, ensure_ascii=False)}"
        prompt += "\n\n请生成一篇800-1500字的文章，包含适当的小标题，层次分明。"

        system_prompt = ("你是一位专业的资质代办行业内容营销专家，擅长撰写各类资质办理相关的推广文案、"
                         "科普文章和政策解读。你的文风专业、可信、有说服力，同时通俗易懂。")

        try:
            if self.client:
                return self._generate_with_openai(system_prompt, prompt, qualification_type, content_type)
            else:
                return self._generate_local(qualification_type, content_type, qual_info, company_name, prompt)
        except Exception as e:
            logger.error(f"AI文案生成失败: {e}")
            return self._generate_local(qualification_type, content_type, qual_info, company_name, prompt)

    def _generate_with_openai(self, system_prompt: str, prompt: str,
                              qualification_type: str, content_type: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        content = resp.choices[0].message.content
        title = self._extract_title(content, qualification_type)
        filtered_content = self.filter.filter(content)
        return {
            "title": title,
            "content": filtered_content,
            "content_type": content_type,
            "qualification_type": qualification_type,
            "source": "ai",
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_local(self, qualification_type: str, content_type: str,
                        qual_info: dict, company_name: str, prompt: str) -> dict:
        """本地模板生成（无需API）"""
        short = qual_info["short"]
        title_templates = {
            "soft_article": [
                f"办理{qualification_type}需要什么条件？资深顾问一文讲透",
                f"2024年{qualification_type}办理全攻略，少走弯路看这篇就够了",
                f"为什么企业都要办{qualification_type}？这些好处你可能不知道",
                f"{qualification_type}代办哪家好？选择专业服务的3大标准",
            ],
            "science_article": [
                f"什么是{qualification_type}？一文读懂{short}证书全解析",
                f"{qualification_type}办理流程详解：从准备到拿证的完整指南",
                f"{qualification_type}与{short}证书的区别与联系，别再混淆了",
                f"企业需要办理{qualification_type}吗？自测清单来了",
            ],
            "comparison_article": [
                f"自己办还是找代办？{qualification_type}办理方式对比分析",
                f"{qualification_type}自主办理vs代办服务，哪个更划算？",
                f"为什么越来越多的企业选择代办{qualification_type}？深度对比",
                f"{qualification_type}代办费用解析：代办比自己办贵在哪？",
            ],
            "policy_article": [
                f"2024年{qualification_type}最新政策解读，企业必看",
                f"新规来了！{qualification_type}办理条件有哪些变化？",
                f"{qualification_type}政策变动对企业的影响分析",
                f"深入解读{short}新规：办理门槛是升是降？",
            ],
            "case_study": [
                f"成功案例：某科技公司{qualification_type}办理经验分享",
                f"从零到一：{qualification_type}办理真实案例全记录",
                f"这些企业都是这样拿到{qualification_type}的，经验分享",
                f"一个月拿下{qualification_type}，这家公司做对了什么？",
            ],
        }

        titles = title_templates.get(content_type, title_templates["soft_article"])
        title = random.choice(titles)

        content = f"""# {title}

## 什么是{qualification_type}？
{qual_info['desc']}。该证书由{qual_info['apply_dept']}颁发，有效期为{qual_info['validity']}。

## 办理{qualification_type}的必要性
在当前的互联网监管环境下，{qualification_type}已经成为企业合法经营的必备资质。没有该证书，企业将面临罚款、停业整顿等处罚风险。

## 办理条件
"""
        for point in qual_info["key_points"]:
            content += f"- {point}\n"

        content += f"""
## 办理流程
1. 准备申请材料
2. 向{qual_info['apply_dept']}提交申请
3. 材料审核（约20-30个工作日）
4. 现场核查
5. 领取证书

## 为什么选择专业代办？
- 熟悉流程，大幅缩短办理周期
- 材料准备专业，提高通过率
- 全程跟踪，省心省力
- 处理各种疑难问题

## 联系我们
如需办理{qualification_type}，欢迎咨询我们的专业顾问团队。
"""
        if company_name:
            content += f"\n**{company_name}** - 专注资质代办服务，已成功服务1000+企业。\n"

        filtered = self.filter.filter(content)
        return {
            "title": title,
            "content": filtered,
            "content_type": content_type,
            "qualification_type": qualification_type,
            "source": "local_template",
            "generated_at": datetime.now().isoformat(),
        }

    def batch_generate(self, qualification_types: list, content_types: list,
                       count_per_type: int = 3, company_name: str = "",
                       keywords_map: dict = None) -> list:
        """批量生成文案"""
        results = []
        for qt in qualification_types:
            for ct in content_types:
                for i in range(count_per_type):
                    keywords = None
                    if keywords_map and qt in keywords_map:
                        keywords = keywords_map[qt]
                    result = self.generate(qt, ct, keywords=keywords, company_name=company_name)
                    if result:
                        result["batch_index"] = i + 1
                        results.append(result)
                    import time
                    time.sleep(1)  # API限速
        logger.info(f"批量生成完成，共 {len(results)} 篇文案")
        return results

    def spin_content(self, text: str, rate: float = 0.3) -> str:
        """伪原创处理"""
        return self.spinner.spin(text, rate)

    def _extract_title(self, content: str, fallback_type: str) -> str:
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line and len(line) <= 60:
                return line
        return f"{fallback_type}办理指南 - 资质代办"


ai_engine = AIContentEngine()
