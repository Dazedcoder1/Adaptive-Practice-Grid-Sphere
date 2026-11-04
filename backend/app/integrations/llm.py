"""LLM provider boundary (design §8).

Everything AI goes through here, so the provider or model can change without touching
learning logic. The LLM never decides scores, exam timing or mastery.

Providers (LLM_PROVIDER): openai · gemini · anthropic · openai_compatible. Gemini is
called through Google's OpenAI-compatible endpoint. An optional fallback provider is tried
when the first one times out or errors. Keys come only from the environment — they are
never stored in the database or returned by the API.

`fake` is a deterministic stand-in that only works when ENVIRONMENT=test.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config.settings import settings

log = logging.getLogger(__name__)

PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini",
        "style": "openai",
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-3.5-flash-lite",
        "style": "openai",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-haiku-5-5",
        "style": "anthropic",
    },
    "openai_compatible": {
        "label": "OpenAI-compatible",
        "base_url": "",
        "model": "",
        "style": "openai",
    },
}
FAKE = "fake"

# Tests swap this for an httpx.MockTransport to check request shapes without a network.
transport: httpx.BaseTransport | None = None


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    fallback_used: bool = False


class LLMError(Exception):
    def __init__(self, code: str, message: str, *, retriable: bool = False):
        super().__init__(message)
        self.code = code
        self.retriable = retriable


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key: str
    model: str
    base_url: str

    @property
    def label(self) -> str:
        return PROVIDERS.get(self.name, {}).get("label", self.name)


def _fake_allowed() -> bool:
    return settings.environment == "test"


def _config(name: str, key: str, model: str, base_url: str) -> ProviderConfig | None:
    name = (name or "").strip().lower()
    if not name:
        return None
    if name == FAKE:
        return ProviderConfig(FAKE, "", model or "fake-tutor", "") if _fake_allowed() else None
    preset = PROVIDERS.get(name)
    if preset is None:
        log.warning("Unknown LLM provider %r — ignoring", name)
        return None
    base = (base_url or preset["base_url"]).rstrip("/")
    model = model or preset["model"]
    if not key or not base or not model:
        return None
    return ProviderConfig(name, key, model, base)


def primary_config(model_override: str = "") -> ProviderConfig | None:
    return _config(
        settings.llm_provider,
        settings.llm_api_key,
        model_override or settings.llm_model,
        settings.llm_base_url,
    )


def fallback_config(model_override: str = "") -> ProviderConfig | None:
    return _config(
        settings.llm_fallback_provider,
        settings.llm_fallback_api_key,
        model_override or settings.llm_fallback_model,
        settings.llm_fallback_base_url,
    )


def is_configured() -> bool:
    return primary_config() is not None


# ── HTTP ─────────────────────────────────────────────────────────────────────


def http_json(url: str, *, headers: dict, body: dict, timeout: float) -> dict[str, Any]:
    """POST JSON and map failures to LLMError codes. Never logs keys or prompt text."""
    try:
        with httpx.Client(timeout=timeout, transport=transport) as c:
            r = c.post(url, headers=headers, json=body)
    except httpx.TimeoutException as e:
        raise LLMError(
            "timeout", "The AI provider took too long to respond.", retriable=True
        ) from e
    except httpx.HTTPError as e:
        raise LLMError("network_error", "Couldn't reach the AI provider.", retriable=True) from e
    if r.status_code == 429:
        raise LLMError("rate_limited", "The AI provider is rate limiting us.", retriable=True)
    if r.status_code in (401, 403):
        raise LLMError("auth_failed", "The AI provider rejected the API key.")
    if r.status_code >= 500:
        raise LLMError("provider_error", f"AI provider error ({r.status_code}).", retriable=True)
    if r.status_code >= 400:
        raise LLMError("bad_request", f"AI provider refused the request: {r.text[:300]}")
    try:
        return r.json()
    except ValueError as e:
        raise LLMError("bad_response", "The AI provider sent an unreadable response.") from e


class HttpProvider:
    def __init__(self, cfg: ProviderConfig, timeout: float | None = None):
        self.cfg = cfg
        self.timeout = timeout or settings.llm_timeout_seconds

    def complete(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int,
        temperature: float | None,
    ) -> Completion:
        started = time.perf_counter()
        if PROVIDERS[self.cfg.name]["style"] == "anthropic":
            text, tin, tout = self._anthropic(system, messages, max_tokens, temperature)
        else:
            text, tin, tout = self._openai(system, messages, max_tokens, temperature)
        return Completion(
            text=text,
            provider=self.cfg.name,
            model=self.cfg.model,
            input_tokens=tin,
            output_tokens=tout,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _openai(self, system, messages, max_tokens, temperature):
        body: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m.role, "content": m.content} for m in messages],
        }
        # OpenAI's own API uses max_completion_tokens; compatible APIs still use max_tokens.
        body["max_completion_tokens" if self.cfg.name == "openai" else "max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature
        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        url = f"{self.cfg.base_url}/chat/completions"
        try:
            data = http_json(url, headers=headers, body=body, timeout=self.timeout)
        except LLMError as e:
            # Some models only accept their default temperature — retry once without it.
            if e.code != "bad_request" or "temperature" not in str(e) or "temperature" not in body:
                raise
            body.pop("temperature")
            data = http_json(url, headers=headers, body=body, timeout=self.timeout)
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError("bad_response", "The AI provider sent an unexpected response.") from e
        usage = data.get("usage") or {}
        return text, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)

    def _anthropic(self, system, messages, max_tokens, temperature):
        body: dict[str, Any] = {
            "model": self.cfg.model,
            "system": system,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if temperature is not None:
            body["temperature"] = temperature
        data = http_json(
            f"{self.cfg.base_url}/messages",
            headers={"x-api-key": self.cfg.api_key, "anthropic-version": "2023-06-01"},
            body=body,
            timeout=self.timeout,
        )
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError) as e:
            raise LLMError("bad_response", "The AI provider sent an unexpected response.") from e
        usage = data.get("usage") or {}
        return text, int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0)


class FakeProvider:
    """Deterministic stand-in for tests and E2E (ENVIRONMENT=test only).

    Push strings onto `replies` to script responses; set `fail_with` to an error code to
    make every call fail. By default it gives a short guiding reply citing source S1.
    """

    replies: list[str] = []
    fail_with: str | None = None
    calls: list[dict] = []

    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg

    @classmethod
    def reset(cls) -> None:
        cls.replies, cls.fail_with, cls.calls = [], None, []

    def complete(self, system, messages, *, max_tokens, temperature) -> Completion:
        FakeProvider.calls.append({"system": system, "messages": messages})
        if FakeProvider.fail_with:
            raise LLMError(FakeProvider.fail_with, "fake failure", retriable=True)
        if FakeProvider.replies:
            text = FakeProvider.replies.pop(0)
        else:
            cite = " [S1]" if '<source id="S1"' in system else ""
            text = (
                "Let's reason it through together. Start from what the question gives you "
                f"and ask which law connects force, mass and acceleration.{cite}"
            )
        return Completion(text, FAKE, self.cfg.model, len(system) // 4, len(text) // 4, 5)


def _provider(cfg: ProviderConfig):
    return FakeProvider(cfg) if cfg.name == FAKE else HttpProvider(cfg)


def complete(
    system: str,
    messages: list[ChatMessage],
    *,
    max_tokens: int = 900,
    temperature: float | None = 0.3,
    model: str = "",
    fallback_model: str = "",
) -> Completion:
    """Primary provider, then the fallback on any failure. Without a fallback, one retry
    of the primary on a retriable failure (timeout, rate limit, 5xx)."""
    primary = primary_config(model)
    if primary is None:
        raise LLMError("not_configured", "No AI provider is configured.")
    fb = fallback_config(fallback_model)
    chain = [primary, fb if fb is not None else primary]
    for i, cfg in enumerate(chain):
        try:
            out = _provider(cfg).complete(
                system, messages, max_tokens=max_tokens, temperature=temperature
            )
            out.fallback_used = i > 0 and fb is not None
            return out
        except LLMError as e:
            log.warning("LLM call failed provider=%s code=%s", cfg.name, e.code)
            if i == len(chain) - 1 or (fb is None and not e.retriable):
                raise
            if fb is None:
                time.sleep(0.5)
    raise AssertionError("unreachable")


def status() -> dict:
    """What the admin sees: which providers are set up — never the keys themselves."""

    def describe(cfg: ProviderConfig | None, name: str) -> dict | None:
        name = (name or "").strip().lower()
        if not name:
            return None
        return {
            "provider": name,
            "label": PROVIDERS.get(name, {}).get("label", name),
            "model": cfg.model if cfg else None,
            "ready": cfg is not None,
        }

    return {
        "primary": describe(primary_config(), settings.llm_provider),
        "fallback": describe(fallback_config(), settings.llm_fallback_provider),
    }
