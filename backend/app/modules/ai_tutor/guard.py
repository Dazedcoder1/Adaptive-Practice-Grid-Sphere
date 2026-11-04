"""Independent checks on what goes into and comes out of the LLM.

None of these trust the model to police itself:
- input: wrap untrusted text so it can't close our tags; flag likely prompt injection;
  route messages about self-harm to a fixed, caring reply (no LLM involved).
- output: drop citations to sources that weren't provided; catch a reply that gives away
  the answer to a question the student hasn't answered yet; catch a reply that echoes the
  hidden rules (canary); cap length.
"""

import re
from dataclasses import dataclass, field

from app.modules.ai_tutor.prompts import CANARY

MAX_REPLY_CHARS = 6000

_INJECTION = re.compile(
    r"ignore (all |any |the )?(previous|prior|above) (instructions|rules|prompts?)"
    r"|disregard (your|the) (rules|instructions)"
    r"|(reveal|show|print|repeat) (me )?(your|the) (system )?(prompt|instructions|rules)"
    r"|you are now\b|developer mode|jailbreak|\bDAN\b"
    r"|(give|tell|show) me the answer key",
    re.I,
)
_WELLBEING = re.compile(
    r"\b(kill(ing)? myself|end(ing)? my life|suicid\w*|want to die|wanna die|self[- ]?harm"
    r"|hurt(ing)? myself|cut(ting)? myself|no reason to live|better off dead)\b",
    re.I,
)

WELLBEING_REPLY = (
    "It sounds like you're going through something really hard, and I'm glad you said it. "
    "I'm a study tutor, so I'm not the right help for this — but you deserve support from a "
    "real person.\n\n"
    "Please talk to someone you trust today, like a parent, a teacher or your school "
    "counsellor. In India you can call **Tele-MANAS on 14416** (free, any time of day) to talk "
    "with a trained counsellor. If you are in immediate danger, call **112**.\n\n"
    "Your studies can wait. I'm here whenever you want to come back to them."
)


def needs_wellbeing_reply(message: str) -> bool:
    return bool(_WELLBEING.search(message))


def looks_like_injection(message: str) -> bool:
    return bool(_INJECTION.search(message))


def fence(text: str, tag: str) -> str:
    """Neutralise anything that could close or open our own tags."""
    return re.sub(rf"</?\s*{tag}\b", lambda m: m.group(0).replace("<", "&lt;"), text, flags=re.I)


# ── citations ────────────────────────────────────────────────────────────────

_CITE = re.compile(r"\[(S\d{1,2}(?:\s*[,;]\s*S\d{1,2})*)\]")


def clean_citations(text: str, valid: set[str]) -> tuple[str, list[str], bool]:
    """Returns (text, cited ids in order, whether any invalid citation was removed)."""
    cited: list[str] = []
    removed = False

    def sub(m):
        nonlocal removed
        ids = [i.strip() for i in re.split(r"[,;]", m.group(1))]
        keep = [i for i in ids if i in valid]
        removed |= len(keep) != len(ids)
        for i in keep:
            if i not in cited:
                cited.append(i)
        return f"[{', '.join(keep)}]" if keep else ""

    out = _CITE.sub(sub, text)
    out = re.sub(r"[ \t]+([.,;:!?])", r"\1", out)
    return re.sub(r"(?<=\S)[ \t]{2,}", " ", out), cited, removed


# ── answer disclosure ────────────────────────────────────────────────────────

_NUM = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:\s*[x×]\s*10\^?\{?[-+]?\d+\}?)?")
_ANSWERISH = re.compile(r"\b(answer|correct|right|result|equals|therefore)\b", re.I)


def _numbers(text: str) -> list[float]:
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    out = []
    for m in _NUM.finditer(text):
        s = m.group(0).replace(" ", "")
        try:
            if "10" in s and ("x" in s or "×" in s):
                base, exp = re.split(r"[x×]10\^?", s)
                out.append(float(base) * 10 ** float(exp.strip("{}")))
            else:
                out.append(float(s))
        except ValueError:
            continue
    return out


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?\n])\s+", text) if s.strip()]


def reveals_answer(reply: str, ctx: dict) -> bool:
    """True if the reply gives away the answer to an unanswered question.

    Deliberately conservative: it looks for the answer stated as the answer (an option
    named as correct, the final value, every blank's word next to "answer"), and ignores
    numbers that already appear in the question itself.
    """
    if ctx.get("answered"):
        return False
    key = ctx.get("_answer_key") or {}
    qtype = ctx.get("type")
    stem = ctx.get("stem", "")
    content = ctx.get("content") or {}
    text = reply.replace("**", "")

    if qtype in ("mcq_single", "assertion_reason", "diagram", "mcq_multi"):
        correct = key.get("correct")
        ids = [correct] if isinstance(correct, str) else list(correct or [])
        if not ids:
            return False
        opts = {o["id"]: o.get("text", "") for o in content.get("options") or []}
        for s in _sentences(text):
            if not _ANSWERISH.search(s):
                continue
            named = {
                i
                for i in ids
                if re.search(
                    rf"(option|choice|answer|\()\s*[:=]?\s*\(?\s*{re.escape(i)}\s*\)?(?![\w])"
                    rf"|(option|choice|answer)\s+(is|=|:|would be|will be)\s*\(?\s*{re.escape(i)}\b"
                    rf"|(?<![\w]){re.escape(i)}\s*\)\s|\b{re.escape(i)}\b\s+is\s+(the\s+)?(correct|right)",
                    s,
                    re.I,
                )
            }
            if named == set(ids):
                return True
            if len(ids) == 1:
                t = re.sub(r"\s+", " ", opts.get(ids[0], "")).strip().lower()
                if (
                    len(t) >= 4
                    and t in s.lower()
                    and re.search(r"\b(correct|right|answer)\b", s, re.I)
                ):
                    return True
        return False

    if qtype in ("numerical", "integer"):
        if "value" not in key:
            return False
        target = float(key["value"])
        tol = float(key.get("tolerance") or max(abs(target) * 0.01, 1e-9))
        given = set(_numbers(stem + " " + str(content)))
        for n in _numbers(text):
            if abs(n - target) <= tol and not any(abs(n - g) <= tol for g in given):
                return True
        return False

    if qtype == "fill_blank":
        accepted = key.get("accepted") or []
        words = [a[0].lower() for a in accepted if a]
        if not words:
            return False
        lowered = text.lower()
        if all(re.search(rf"\b{re.escape(w)}\b", lowered) for w in words) and not all(
            re.search(rf"\b{re.escape(w)}\b", stem.lower()) for w in words
        ):
            return any(
                re.search(r"\b(answer|blank|missing word|fill)\b", s, re.I)
                and all(w in s.lower() for w in words)
                for s in _sentences(text)
            )
    return False


@dataclass
class Checked:
    text: str
    cited: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    leaked: bool = False


def check_reply(raw: str, *, valid_sources: set[str], question: dict | None) -> Checked:
    text = (raw or "").strip()
    flags: list[str] = []
    if CANARY in text:
        return Checked(
            "I can't share my instructions, but I'm happy to help with your studies. "
            "What would you like to work on?",
            flags=["instructions_withheld"],
        )
    text = re.sub(r"<\s*/?\s*(script|iframe|style)[^>]*>", "", text, flags=re.I)
    if len(text) > MAX_REPLY_CHARS:
        text = text[:MAX_REPLY_CHARS].rsplit(" ", 1)[0] + "…"
        flags.append("truncated")
    text, cited, removed = clean_citations(text, valid_sources)
    if removed:
        flags.append("citation_removed")
    leaked = bool(question) and reveals_answer(text, question)
    return Checked(text, cited, flags, leaked)
