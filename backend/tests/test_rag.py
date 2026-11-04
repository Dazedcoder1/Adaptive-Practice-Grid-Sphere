"""Study-material ingestion and retrieval (design §8.2)."""

import io

import pytest
from sqlalchemy import select

from app.config.database import SessionLocal, transaction
from app.config.settings import settings
from app.modules.rag import service as rag
from app.modules.rag.chunking import chunk
from app.modules.rag.extraction import ExtractionError, extract
from app.modules.rag.models import DocumentStatus, RagChunk, RagDocument
from tests.conftest import bearer
from tests.learning_helpers import onboarded_student, seed

NOTES = b"""# Practice notes

## Sledges on an icy hill
<!-- concepts: FRIC -->

A sledge on a toboggan hill has normal force $N = mg\\cos\\theta$. The sledge starts to
slip when $\\tan\\theta = \\mu_s$. Kinetic friction is usually smaller than static friction.

## Kabaddi tackles

A kabaddi raider who is tackled feels a smaller force if the stop is spread over a longer
time. The push on the raider equals the change in the raider's momentum.
"""


def _pdf(text: str) -> bytes:
    """A minimal one-page PDF with a line of text (no extra libraries needed)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def _docx() -> bytes:
    import docx

    d = docx.Document()
    d.add_heading("Circular motion", level=1)
    d.add_paragraph("The centripetal force on a body moving in a circle is m v squared over r.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ── extraction & chunking ────────────────────────────────────────────────────


def test_extracts_pdf_with_page_markers():
    ex = extract(
        "notes.pdf", _pdf("Inertia is the tendency of a body to keep its state of motion.")
    )
    assert ex.page_count == 1 and ex.mime_type == "application/pdf"
    assert "[[page 1]]" in ex.text and "Inertia is the tendency" in ex.text
    assert chunk(ex.text)[0].page == 1


def test_extracts_docx_headings():
    ex = extract("notes.docx", _docx())
    assert ex.text.startswith("# Circular motion")
    assert chunk(ex.text)[0].heading == "Circular motion"


@pytest.mark.parametrize(
    "name,data,msg",
    [
        ("virus.exe", b"MZ....", "Upload a PDF"),
        ("fake.pdf", b"not really a pdf at all, just text pretending", "valid PDF"),
        ("fake.docx", b"plain text", "valid Word"),
        ("empty.md", b"", "empty"),
        ("short.txt", b"hi", "No readable text"),
        ("bin.txt", b"\x00\x01\x02" * 50, "text file"),
    ],
)
def test_rejects_bad_files(name, data, msg):
    with pytest.raises(ExtractionError, match=msg):
        extract(name, data)


def test_chunks_keep_sections_maths_and_overlap():
    body = " ".join(f"Sentence number {i} explains a step of the method." for i in range(40))
    text = f"# A\n\n{body}\n\n$$F = ma$$\n\n# B\n\nShort section about impulse and momentum here."
    out = chunk(text, target=120, overlap=30)
    assert {c.heading for c in out} == {"A", "B"}  # never spans two sections
    assert all(c.text.count("$$") % 2 == 0 for c in out)  # display maths never cut
    a = [c for c in out if c.heading == "A"]
    assert len(a) > 1
    last_sentence = a[0].text.rsplit(". ", 1)[-1]
    assert last_sentence in a[1].text[:200]  # overlap carries the tail forward


# ── through the API ──────────────────────────────────────────────────────────


@pytest.fixture
def content():
    seed()
    with SessionLocal() as db:
        from app.modules.curriculum.models import Chapter, Curriculum, Subject

        cur = db.scalar(select(Curriculum).where(Curriculum.is_sample))
        sub = db.scalar(select(Subject).where(Subject.curriculum_id == cur.id))
        ch = db.scalar(select(Chapter).where(Chapter.name == "Laws of Motion"))
        return {"curriculum_id": cur.id, "subject_id": sub.id, "chapter_id": ch.id}


def _upload(client, token, content, data=NOTES, name="ramp.md", **over):
    form = {
        "title": "Ramp notes",
        "curriculum_id": content["curriculum_id"],
        "subject_id": content["subject_id"],
        "chapter_id": content["chapter_id"],
        "source_type": "notes",
        "licence": "owned",
        **over,
    }
    return client.post(
        "/api/v1/admin/rag/documents",
        headers=bearer(token),
        data={k: str(v) for k, v in form.items() if v is not None},
        files={"file": (name, data, "text/markdown")},
    )


def _search(client, token, content, query, **kw):
    r = client.post(
        "/api/v1/admin/rag/search",
        headers=bearer(token),
        json={"query": query, "curriculum_id": content["curriculum_id"], **kw},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_sample_notes_are_seeded_and_approved(content):
    with SessionLocal() as db:
        docs = list(db.scalars(select(RagDocument)))
    assert {d.status for d in docs} == {DocumentStatus.APPROVED}
    assert sum(d.chunk_count for d in docs) >= 12
    seed()  # idempotent
    with SessionLocal() as db:
        assert len(list(db.scalars(select(RagDocument)))) == len(docs)


def test_upload_review_approve_and_retrieve(client, admin_token, content):
    r = _upload(client, admin_token, content)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["status"] == "review" and doc["chunk_count"] == 2
    ramp = next(c for c in doc["chunks"] if "sledge" in c["heading"].lower())
    assert [c["name"] for c in ramp["concepts"]] == ["Friction"]  # exact tag

    def titles(**kw):
        hits = _search(client, admin_token, content, "sledge toboggan hill", **kw)["hits"]
        return [h["title"] for h in hits]

    assert "Ramp notes" not in titles()  # not approved yet → never retrieved
    assert "Ramp notes" in titles(include_unapproved=True)
    r = client.post(f"/api/v1/admin/rag/documents/{doc['id']}/approve", headers=bearer(admin_token))
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert titles()[0] == "Ramp notes"
    assert _search(client, admin_token, content, "sledge")["mode"] == "keyword"


def test_duplicates_unknown_licence_and_bad_scope(client, admin_token, content):
    assert _upload(client, admin_token, content).status_code == 201
    r = _upload(client, admin_token, content)
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicate"

    r = _upload(client, admin_token, content, data=NOTES + b"\nMore.", licence="unknown")
    r = client.post(
        f"/api/v1/admin/rag/documents/{r.json()['id']}/approve", headers=bearer(admin_token)
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "licence_required"

    r = _upload(client, admin_token, content, data=NOTES + b"\nX.", subject_id=999999)
    assert r.json()["error"]["code"] == "bad_scope"

    r = _upload(client, admin_token, content, data=b"MZ\x00", name="x.exe")
    assert r.json()["error"]["code"] == "unreadable_file"


def test_new_version_replaces_the_old_one_on_approval(client, admin_token, content):
    v1 = _upload(client, admin_token, content).json()
    client.post(f"/api/v1/admin/rag/documents/{v1['id']}/approve", headers=bearer(admin_token))
    v2 = _upload(
        client, admin_token, content, data=NOTES + b"\nUpdated.", replaces_id=v1["id"]
    ).json()
    assert v2["version"] == 2
    client.post(f"/api/v1/admin/rag/documents/{v2['id']}/approve", headers=bearer(admin_token))
    old = client.get(f"/api/v1/admin/rag/documents/{v1['id']}", headers=bearer(admin_token)).json()
    assert old["status"] == "archived"


def test_admin_can_correct_passage_concepts(client, admin_token, content):
    doc = _upload(client, admin_token, content).json()
    sport = next(c for c in doc["chunks"] if "kabaddi" in c["heading"].lower())
    by_name = {c["name"]: c["id"] for c in doc["concepts"]}
    r = client.patch(
        f"/api/v1/admin/rag/chunks/{sport['id']}",
        headers=bearer(admin_token),
        json={"concept_ids": [by_name["Impulse"]]},
    )
    assert r.status_code == 200 and r.json()["concept_ids"] == [by_name["Impulse"]]
    r = client.patch(
        f"/api/v1/admin/rag/chunks/{sport['id']}",
        headers=bearer(admin_token),
        json={"concept_ids": [987654]},
    )
    assert r.json()["error"]["code"] == "bad_concepts"


def test_students_cannot_use_admin_rag_endpoints(client, content):
    s = onboarded_student(client)
    assert client.get("/api/v1/admin/rag/documents", headers=s["h"]).status_code == 403


def test_retrieval_respects_curriculum_and_subject_filters(content):
    with SessionLocal() as db:
        hits = rag.retrieve(db, "inertia first law", curriculum_id=content["curriculum_id"]).hits
        assert hits and "Inertia" in hits[0].heading
        assert not rag.retrieve(
            db, "inertia", curriculum_id=content["curriculum_id"], subject_ids=[]
        ).hits  # noqa: E501
        assert not rag.retrieve(db, "inertia", curriculum_id=987654).hits


def test_concept_passages_fill_in_when_words_dont_match(content):
    from app.modules.curriculum.models import Concept

    with SessionLocal() as db:
        n3 = db.scalar(select(Concept.id).where(Concept.code == "N3"))
        hits = rag.retrieve(
            db, "teach me", curriculum_id=content["curriculum_id"], concept_ids=[n3]
        ).hits
    assert hits and "third law" in hits[0].heading.lower() and hits[0].concept_match


def test_hybrid_retrieval_with_embeddings(client, admin_token, content, monkeypatch):
    monkeypatch.setattr(settings, "embedding_provider", "fake")
    doc = _upload(client, admin_token, content).json()  # embedding runs after the response
    detail = client.get(
        f"/api/v1/admin/rag/documents/{doc['id']}", headers=bearer(admin_token)
    ).json()
    assert detail["embedded_count"] == detail["chunk_count"] == 2
    client.post(f"/api/v1/admin/rag/documents/{doc['id']}/approve", headers=bearer(admin_token))
    res = _search(client, admin_token, content, "kabaddi raider tackled")
    assert res["mode"] == "hybrid"
    top = res["hits"][0]
    assert top["title"] == "Ramp notes" and top["similarity"] is not None
    with SessionLocal() as db:
        models = set(
            db.scalars(select(RagChunk.embedding_model).where(RagChunk.document_id == doc["id"]))
        )
    assert models == {"fake:hash-bow:768"}


def test_reprocess_uses_current_chunk_settings(client, admin_token, content):
    from app.modules.ai_tutor import config

    doc = _upload(client, admin_token, content).json()
    with SessionLocal() as db, transaction(db):
        s = config.get_settings(db)
        s.chunk_target_tokens, s.chunk_overlap_tokens = 80, 10
    r = client.post(
        f"/api/v1/admin/rag/documents/{doc['id']}/reprocess", headers=bearer(admin_token)
    )
    assert r.status_code == 200 and r.json()["status"] == "review"


def test_retrieval_evaluation(client, admin_token, content):
    with SessionLocal() as db:
        notes = db.scalar(select(RagDocument).where(RagDocument.title.like("Laws of Motion%")))
    for q, phrase in [("what is impulse", "impulse"), ("centripetal force on a turning car", "")]:
        r = client.post(
            "/api/v1/admin/rag/eval-cases",
            headers=bearer(admin_token),
            json={
                "query": q,
                "curriculum_id": content["curriculum_id"],
                "expected_document_id": str(notes.id),
                "expected_phrase": phrase,
            },
        )
        assert r.status_code == 201, r.text
    run = client.post("/api/v1/admin/rag/eval-runs?k=3", headers=bearer(admin_token)).json()
    assert run["cases"] == 2 and run["hit_rate"] == 1.0 and run["mrr"] > 0.5
    assert (
        client.get("/api/v1/admin/rag/eval-runs", headers=bearer(admin_token)).json()[0]["id"]
        == run["id"]
    )
