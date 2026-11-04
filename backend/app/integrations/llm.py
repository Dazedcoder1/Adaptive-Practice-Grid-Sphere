"""LLM provider boundary (design §8).

Everything AI goes through this interface so the provider/model can change without
touching learning logic. The LLM never decides scores, exam timing or mastery.
Provider choice is an open design item (Appendix B) — implement one when selected.
"""

from dataclasses import dataclass
from typing import Protocol

from app.config.settings import settings


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(Protocol):
    def complete(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str: ...


class NotConfiguredLLM:
    def complete(self, messages: list[ChatMessage], *, max_tokens: int = 1024) -> str:
        raise RuntimeError("No LLM provider configured — set LLM_PROVIDER / LLM_API_KEY in .env")


def get_llm() -> LLMClient:
    match settings.llm_provider.lower():
        # case "anthropic": return AnthropicLLM(...)
        # case "openai":    return OpenAILLM(...)
        case _:
            return NotConfiguredLLM()
