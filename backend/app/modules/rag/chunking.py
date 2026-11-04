"""Semantic chunking and concept mapping.

Text is split at headings first (a passage never spans two sections), then packed
paragraph by paragraph up to a token budget. A paragraph is only split if it is larger than
the budget on its own, and then at sentence boundaries. Display maths ($$ … $$) is never cut.
When a section has to be split for size, the next passage repeats the last sentence or two
(the overlap), so an idea that straddles the cut is still retrievable.

Concept mapping: authored notes can tag a section exactly with a line
`<!-- concepts: N2, MOM -->`; otherwise concepts are matched from their names in the
heading and text. Admins can correct the mapping per passage.
"""

import re
from dataclasses import dataclass, field

from app.modules.rag.extraction import PAGE_MARK

HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*#*$")
TAG = re.compile(r"<!--\s*concepts?\s*:\s*([^>]*?)\s*-->", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[$])")


def tokens(text: str) -> int:
    return max(1, round(len(text) / 4))


@dataclass
class Chunk:
    heading: str
    text: str
    page: int | None
    tagged_codes: list[str] = field(default_factory=list)

    @property
    def token_count(self) -> int:
        return tokens(self.heading + " " + self.text)


@dataclass
class _Section:
    heading: str
    page: int | None
    codes: list[str]
    paras: list[tuple[str, int | None]]  # (paragraph, page it starts on)


def _sections(text: str) -> list[_Section]:
    path: list[str] = []
    page: int | None = None
    cur = _Section("", None, [], [])
    out = [cur]
    buf: list[str] = []
    buf_page: int | None = None
    in_math = False

    def flush():
        nonlocal buf, buf_page
        para = "\n".join(buf).strip()
        if para:
            cur.paras.append((para, buf_page))
        buf, buf_page = [], None

    for line in text.split("\n"):
        pm = PAGE_MARK.match(line.strip())
        if pm:
            page = int(pm.group(1))
            continue
        tag = TAG.search(line)
        if tag:
            cur.codes += [c.strip().upper() for c in tag.group(1).split(",") if c.strip()]
            line = TAG.sub("", line)
            if not line.strip():
                continue
        h = HEADING.match(line.strip()) if not in_math else None
        if h:
            flush()
            level = len(h.group(1))
            path = path[: level - 1] + [h.group(2).strip()]
            cur = _Section(" › ".join(path), page, [], [])
            out.append(cur)
            continue
        if not line.strip() and not in_math:
            flush()
            continue
        if not buf:
            buf_page = page
        buf.append(line)
        if line.count("$$") % 2:
            in_math = not in_math
    flush()
    return [s for s in out if s.paras]


def _split_long(para: str, budget: int) -> list[str]:
    if tokens(para) <= budget or "$$" in para:
        return [para]
    parts, cur = [], ""
    for sentence in SENTENCE.split(para):
        if cur and tokens(cur + " " + sentence) > budget:
            parts.append(cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}".strip()
    if cur:
        parts.append(cur)
    return parts


def _tail(text: str, overlap: int) -> str:
    """The last sentence(s) of a passage, up to `overlap` tokens."""
    if overlap <= 0:
        return ""
    picked: list[str] = []
    for sentence in reversed(SENTENCE.split(text)):
        if picked and tokens(" ".join([sentence, *picked])) > overlap:
            break
        picked.insert(0, sentence)
        if tokens(" ".join(picked)) > overlap:
            return ""  # a single sentence bigger than the overlap — skip it
    return " ".join(picked)


def chunk(text: str, *, target: int = 350, overlap: int = 50) -> list[Chunk]:
    target = max(80, target)
    overlap = max(0, min(overlap, target // 3))
    out: list[Chunk] = []
    for sec in _sections(text):
        pieces: list[tuple[str, int | None]] = []
        for para, page in sec.paras:
            pieces += [(p, page) for p in _split_long(para, target)]
        cur: list[str] = []
        cur_page = pieces[0][1] if pieces else sec.page
        for piece, page in pieces:
            if cur and tokens("\n\n".join([*cur, piece])) > target:
                body = "\n\n".join(cur)
                out.append(Chunk(sec.heading, body, cur_page, sec.codes))
                carry = _tail(body, overlap)
                cur, cur_page = ([carry] if carry else []), page
            cur.append(piece)
        if cur:
            body = "\n\n".join(cur)
            prev = out[-1] if out else None
            # Fold a tiny remainder into the previous passage of the same section.
            if prev and prev.heading == sec.heading and tokens(body) < 40 and len(cur) == 1:
                prev.text += "\n\n" + body
            else:
                out.append(Chunk(sec.heading, body, cur_page, sec.codes))
    return out


# ── concept mapping ──────────────────────────────────────────────────────────

_STOP = {
    "and", "the", "of", "for", "with", "law", "laws", "its", "from", "into", "a", "an", "in",
    "on", "to", "by", "is", "are", "as",
}  # fmt: skip


def _words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z]+", text.lower().replace("'s", "")):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _key_terms(name: str) -> set[str]:
    return {w for w in _words(name) if len(w) >= 3 and w not in _STOP}


def map_concepts(c: Chunk, concepts: list[dict], *, limit: int = 3) -> list[int]:
    """`concepts`: [{"id", "code", "name"}]. Exact tags win; otherwise name matching."""
    if c.tagged_codes:
        by_code = {x["code"].upper(): x["id"] for x in concepts}
        return [by_code[code] for code in c.tagged_codes if code in by_code][:limit]
    head = set(_words(c.heading))
    body_words = _words(c.text)
    body = set(body_words)
    scored = []
    for x in concepts:
        terms = _key_terms(x["name"])
        if not terms:
            continue
        head_cov = len(terms & head) / len(terms)
        body_cov = len(terms & body) / len(terms)
        hits = sum(1 for w in body_words if w in terms)
        if head_cov >= 0.6 or (body_cov == 1 and hits >= 2 * len(terms)):
            scored.append((head_cov * 2 + body_cov + min(hits, 10) / 10, x["id"]))
    scored.sort(reverse=True)
    return [cid for _, cid in scored[:limit]]
