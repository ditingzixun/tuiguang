"""AI提供商抽象层 — 统一接口，支持 OpenAI/Claude/本地模型/模板降级"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)
from utils.config_loader import config_loader


class AIProvider(ABC):
    """AI提供商基类"""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 2048, temperature: float = 0.8) -> Optional[str]:
        """生成文本，失败返回None"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查是否可用"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class OpenAIProvider(AIProvider):
    """OpenAI 兼容接口 — 支持 OpenAI / 国内代理 / 兼容API"""

    def __init__(self):
        cfg = config_loader
        self.api_key = cfg.get("AI_API_KEY", "")
        self.api_base = cfg.get("AI_API_BASE", "https://api.openai.com/v1")
        self.model = cfg.get("AI_MODEL", "gpt-4o-mini")
        self._client = None

    @property
    def name(self):
        return f"OpenAI({self.model})"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _ensure_client(self):
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            except ImportError:
                logger.warning("openai 库未安装，无法使用 OpenAI 提供商")

    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 2048, temperature: float = 0.8) -> Optional[str]:
        if not self.is_available():
            return None
        self._ensure_client()
        if not self._client:
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            return None


class ClaudeProvider(AIProvider):
    """Anthropic Claude 接口"""

    def __init__(self):
        cfg = config_loader
        self.api_key = cfg.get("CLAUDE_API_KEY", "")
        self.model = cfg.get("CLAUDE_MODEL", "claude-sonnet-4-6")
        self._client = None

    @property
    def name(self):
        return f"Claude({self.model})"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _ensure_client(self):
        if self._client is None and self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic 库未安装，无法使用 Claude 提供商")

    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 2048, temperature: float = 0.8) -> Optional[str]:
        if not self.is_available():
            return None
        self._ensure_client()
        if not self._client:
            return None

        try:
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            logger.error(f"Claude API 调用失败: {e}")
            return None


class TemplateProvider(AIProvider):
    """模板降级提供商 — 无需API，始终可用"""

    @property
    def name(self):
        return "模板引擎(本地)"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 2048, temperature: float = 0.8) -> Optional[str]:
        # 模板引擎不通过 generate() 接口工作，由 AIContentEngine 直接调用模板方法
        return None


class AIProviderManager:
    """AI提供商管理器 — 按优先级自动选择可用提供商"""

    def __init__(self):
        self._providers = []
        self._register_providers()

    def _register_providers(self):
        """按优先级注册提供商"""
        self._providers = [
            ClaudeProvider(),
            OpenAIProvider(),
            TemplateProvider(),
        ]

    @property
    def active_provider(self) -> AIProvider:
        """获取当前可用的最佳提供商"""
        for p in self._providers:
            if p.is_available():
                return p
        return self._providers[-1]  # TemplateProvider 始终可用

    def get_provider(self, name: str) -> Optional[AIProvider]:
        for p in self._providers:
            if name.lower() in p.name.lower():
                return p
        return None

    def get_all_available(self) -> list:
        return [p for p in self._providers if p.is_available()]


ai_provider_manager = AIProviderManager()
