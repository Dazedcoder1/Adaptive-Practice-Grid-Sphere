"""/api/v1/admin/ai — AI provider status, settings, limits, prompts and usage (brief §7.7).

API keys are managed as environment secrets; this API only reports whether a provider is
ready and never accepts or returns a key.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request

from app.config.database import DbSession, transaction
from app.integrations import embeddings, llm
from app.modules.ai_tutor import config, prompts, service
from app.modules.ai_tutor.schemas import AiSettingsIn, PromptIn, TestIn
from app.modules.audit import service as audit
from app.modules.rag import service as rag
from app.shared.permissions import Principal, require_permission
from app.shared.request import client_ip

router = APIRouter(prefix="/admin/ai", tags=["admin: ai"])
Manager = Annotated[Principal, Depends(require_permission("ai.manage"))]

_FIELDS = list(AiSettingsIn.model_fields)


def _settings_dict(s) -> dict:
    out = {f: getattr(s, f) for f in _FIELDS}
    for k in (
        "platform_daily_cost_usd",
        "input_price_per_mtok",
        "output_price_per_mtok",
        "embedding_price_per_mtok",
    ):  # noqa: E501
        out[k] = float(out[k])
    return {**out, "updated_at": s.updated_at}


def _log(db, p, request, action, details=None):
    audit.record(
        db,
        action,
        actor_user_id=p.user_id,
        target_type="ai",
        target_id=None,
        details=details or {},
        ip=client_ip(request),
    )


@router.get("/overview")
def overview(_: Manager, db: DbSession):
    with transaction(db):
        s = config.get_settings(db)
        return {
            "llm": llm.status(),
            "embeddings": embeddings.status(),
            "providers": [{"id": k, "label": v["label"]} for k, v in llm.PROVIDERS.items()],
            "effective_model": (llm.primary_config(s.chat_model) or llm.primary_config()).model
            if llm.is_configured()
            else None,
            "settings": _settings_dict(s),
            "documents": rag.stats(db),
            "today": {
                "cost_usd": float(config.cost_today(db)),
                "limit_usd": float(s.platform_daily_cost_usd),
            },
        }


@router.put("/settings")
def update_settings(body: AiSettingsIn, p: Manager, db: DbSession, request: Request):
    with transaction(db):
        s = config.get_settings(db)
        before = _settings_dict(s)
        for k, v in body.model_dump().items():
            setattr(s, k, v.strip() if isinstance(v, str) else v)
        s.updated_by = p.user_id
        db.flush()
        after = _settings_dict(s)
        changed = {k: [before[k], after[k]] for k in _FIELDS if before[k] != after[k]}
        _log(db, p, request, "ai.settings_updated", {"changed": changed})
    return after


@router.post("/test")
def test_provider(body: TestIn, p: Manager, db: DbSession):
    """A tiny live call to check the key and model work. Recorded as usage."""
    with transaction(db):
        s = config.get_settings(db)
        try:
            if body.kind == "embedding":
                e = embeddings.get_embedder()
                if e is None:
                    return {"ok": False, "message": "No embedding provider is configured."}
                r = e.embed(["Newton's second law relates force and acceleration."], kind="query")
                config.record_usage(
                    db, feature="test", provider=e.name, model=e.model, user_id=p.user_id,
                    input_tokens=r.input_tokens, latency_ms=r.latency_ms,
                )  # fmt: skip
                return {
                    "ok": True,
                    "message": f"{e.model}: {len(r.vectors[0])} dimensions in {r.latency_ms} ms.",
                }  # noqa: E501
            out = llm.complete(
                "Reply with the single word OK.",
                [llm.ChatMessage("user", "Say OK.")],
                max_tokens=20,
                temperature=None,
                model=s.chat_model,
                fallback_model=s.fallback_model,
            )
            config.record_usage(
                db, feature="test", provider=out.provider, model=out.model, user_id=p.user_id,
                input_tokens=out.input_tokens, output_tokens=out.output_tokens,
                latency_ms=out.latency_ms, fallback_used=out.fallback_used,
            )  # fmt: skip
            via = " (via fallback)" if out.fallback_used else ""
            return {"ok": True, "message": f"{out.model}{via} replied in {out.latency_ms} ms."}
        except llm.LLMError as e:
            return {"ok": False, "message": str(e), "code": e.code}


@router.get("/usage")
def usage(_: Manager, db: DbSession, days: Annotated[int, Query(ge=1, le=90)] = 14):
    with transaction(db):
        return service.usage_report(db, days)


@router.get("/prompts")
def list_prompts(_: Manager, db: DbSession):
    return prompts.overview(db)


@router.post("/prompts/{key}")
def new_prompt_version(key: str, body: PromptIn, p: Manager, db: DbSession, request: Request):
    """Saves a new version (not yet active)."""
    with transaction(db):
        v = prompts.create_version(db, key, body.body, body.note, p.user_id)
        _log(db, p, request, "ai.prompt_version_created", {"key": key, "version": v.version})
    return prompts.overview(db)


@router.post("/prompts/{key}/activate")
def activate_prompt(
    key: str,
    p: Manager,
    db: DbSession,
    request: Request,
    version: Annotated[int, Body(embed=True, ge=0)],
):
    """Make a version live (0 = back to the built-in default)."""
    with transaction(db):
        prompts.activate(db, key, version)
        _log(db, p, request, "ai.prompt_activated", {"key": key, "version": version})
    return prompts.overview(db)
