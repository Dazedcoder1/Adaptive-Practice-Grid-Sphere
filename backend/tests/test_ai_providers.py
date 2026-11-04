"""Provider adapters: request shapes, error mapping, retries and fallback — no network."""

import json

import httpx
import pytest

from app.config.settings import settings
from app.integrations import embeddings, llm


@pytest.fixture
def mock(monkeypatch):
    """Route provider HTTP to a handler; returns the list of captured requests."""
    seen: list[httpx.Request] = []
    handlers: list = []

    def handler(request: httpx.Request):
        seen.append(request)
        return handlers.pop(0)(request) if len(handlers) > 1 else handlers[0](request)

    monkeypatch.setattr(llm, "transport", httpx.MockTransport(handler))

    def use(*fns):
        handlers[:] = list(fns)
        return seen

    return use


def _openai_ok(text="Hi", pt=11, ct=3):
    return lambda r: httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": pt, "completion_tokens": ct},
        },
    )


def _configure(monkeypatch, provider, key="sk-test", model="", fb=None):
    monkeypatch.setattr(settings, "llm_provider", provider)
    monkeypatch.setattr(settings, "llm_api_key", key)
    monkeypatch.setattr(settings, "llm_model", model)
    monkeypatch.setattr(settings, "llm_fallback_provider", fb[0] if fb else "")
    monkeypatch.setattr(settings, "llm_fallback_api_key", fb[1] if fb else "")
    monkeypatch.setattr(settings, "llm_fallback_model", "")


def test_openai_request_shape(monkeypatch, mock):
    _configure(monkeypatch, "openai")
    seen = mock(_openai_ok("Hello", 20, 5))
    out = llm.complete("SYSTEM", [llm.ChatMessage("user", "hey")], max_tokens=50)
    req = seen[0]
    body = json.loads(req.content)
    assert str(req.url) == "https://api.openai.com/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer sk-test"
    assert body["model"] == "gpt-4.1-mini"
    assert body["max_completion_tokens"] == 50 and "max_tokens" not in body
    assert body["messages"][0] == {"role": "system", "content": "SYSTEM"}
    assert (out.text, out.input_tokens, out.output_tokens) == ("Hello", 20, 5)


def test_gemini_uses_openai_compatible_endpoint(monkeypatch, mock):
    _configure(monkeypatch, "gemini", model="gemini-x")
    seen = mock(_openai_ok())
    llm.complete("S", [llm.ChatMessage("user", "q")], max_tokens=40)
    body = json.loads(seen[0].content)
    assert seen[0].url.path.endswith("/v1beta/openai/chat/completions")
    assert body["model"] == "gemini-x" and body["max_tokens"] == 40


def test_anthropic_request_shape(monkeypatch, mock):
    _configure(monkeypatch, "anthropic", key="ak")
    seen = mock(
        lambda r: httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "Hi "}, {"type": "text", "text": "there"}],
                "usage": {"input_tokens": 9, "output_tokens": 2},
            },
        )
    )
    out = llm.complete("SYS", [llm.ChatMessage("user", "q")], max_tokens=30, temperature=0.2)
    req, body = seen[0], json.loads(seen[0].content)
    assert str(req.url) == "https://api.anthropic.com/v1/messages"
    assert req.headers["x-api-key"] == "ak" and req.headers["anthropic-version"] == "2023-06-01"
    assert body["system"] == "SYS" and body["messages"] == [{"role": "user", "content": "q"}]
    assert out.text == "Hi there" and out.input_tokens == 9


def test_temperature_is_dropped_when_the_model_refuses_it(monkeypatch, mock):
    _configure(monkeypatch, "openai")
    seen = mock(
        lambda r: httpx.Response(
            400, json={"error": {"message": "Unsupported value: 'temperature'"}}
        ),
        _openai_ok("ok"),
    )
    assert llm.complete("S", [llm.ChatMessage("user", "q")], temperature=0.3).text == "ok"
    assert "temperature" in json.loads(seen[0].content)
    assert "temperature" not in json.loads(seen[1].content)


def test_bad_key_is_not_retried(monkeypatch, mock):
    _configure(monkeypatch, "openai")
    seen = mock(lambda r: httpx.Response(401, json={}))
    with pytest.raises(llm.LLMError) as e:
        llm.complete("S", [llm.ChatMessage("user", "q")])
    assert e.value.code == "auth_failed" and len(seen) == 1


def test_server_error_is_retried_once(monkeypatch, mock):
    _configure(monkeypatch, "openai")
    seen = mock(lambda r: httpx.Response(503), _openai_ok("second time"))
    assert llm.complete("S", [llm.ChatMessage("user", "q")]).text == "second time"
    assert len(seen) == 2


def test_fallback_provider_takes_over(monkeypatch, mock):
    _configure(monkeypatch, "openai", fb=("anthropic", "ak"))
    seen = mock(
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(
            200, json={"content": [{"type": "text", "text": "from fallback"}], "usage": {}}
        ),
    )
    out = llm.complete("S", [llm.ChatMessage("user", "q")])
    assert out.text == "from fallback" and out.fallback_used and out.provider == "anthropic"
    assert seen[1].url.host == "api.anthropic.com"


def test_unconfigured_and_fake_outside_tests(monkeypatch):
    _configure(monkeypatch, "")
    assert not llm.is_configured()
    _configure(monkeypatch, "openai", key="")  # provider named but no key
    assert not llm.is_configured()
    _configure(monkeypatch, "fake")
    assert llm.is_configured()
    monkeypatch.setattr(settings, "environment", "development")
    assert not llm.is_configured()  # the stand-in never runs outside tests


def test_status_never_exposes_keys(monkeypatch):
    _configure(monkeypatch, "openai", key="sk-secret-value")
    assert "sk-secret-value" not in json.dumps(llm.status())


# ── embeddings ───────────────────────────────────────────────────────────────


def _vec(n=embeddings.DIMENSIONS):
    return [0.1] * n


def test_openai_embeddings_ask_for_fixed_dimensions(monkeypatch, mock):
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    monkeypatch.setattr(settings, "embedding_api_key", "ek")
    seen = mock(
        lambda r: httpx.Response(
            200,
            json={
                "data": [{"index": 1, "embedding": _vec()}, {"index": 0, "embedding": _vec()}],
                "usage": {"prompt_tokens": 7},
            },
        )
    )
    res = embeddings.get_embedder().embed(["a", "b"])
    body = json.loads(seen[0].content)
    assert body["dimensions"] == 768 and body["model"] == "text-embedding-3-small"
    assert len(res.vectors) == 2 and res.input_tokens == 7
    assert abs(sum(x * x for x in res.vectors[0]) - 1) < 1e-9  # normalised


def test_gemini_embeddings_use_batch_endpoint(monkeypatch, mock):
    monkeypatch.setattr(settings, "embedding_provider", "gemini")
    monkeypatch.setattr(settings, "embedding_api_key", "gk")
    seen = mock(lambda r: httpx.Response(200, json={"embeddings": [{"values": _vec()}]}))
    embeddings.get_embedder().embed(["q"], kind="query")
    body = json.loads(seen[0].content)
    assert seen[0].url.path.endswith("/models/gemini-embedding-001:batchEmbedContents")
    assert seen[0].headers["x-goog-api-key"] == "gk"
    req = body["requests"][0]
    assert req["taskType"] == "RETRIEVAL_QUERY" and req["outputDimensionality"] == 768


def test_wrong_dimensions_are_rejected(monkeypatch, mock):
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    monkeypatch.setattr(settings, "embedding_api_key", "ek")
    mock(lambda r: httpx.Response(200, json={"data": [{"index": 0, "embedding": _vec(1536)}]}))
    with pytest.raises(llm.LLMError) as e:
        embeddings.get_embedder().embed(["a"])
    assert e.value.code == "bad_dimensions"


def test_embedding_key_reuses_llm_key_for_same_provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_api_key", "shared")
    monkeypatch.setattr(settings, "embedding_provider", "gemini")
    monkeypatch.setattr(settings, "embedding_api_key", "")
    assert embeddings.get_embedder().key == "shared"
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    assert embeddings.get_embedder() is None  # different provider, no key of its own
