"""Endpoints for automated end-to-end tests ONLY.

Mounted solely when ENVIRONMENT=test (see app/main.py). They expose emails captured by
the console backend and create admins without the CLI — never available in dev/prod.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config.database import DbSession, transaction
from app.integrations import email
from app.modules.identity.service import create_super_admin

router = APIRouter(prefix="/__test__", tags=["test-only"], include_in_schema=False)


@router.get("/emails")
def emails(to: str):
    return [
        {"to": m.to, "subject": m.subject, "body": m.body}
        for m in email.outbox
        if m.to == to.strip().lower()
    ]


class AdminIn(BaseModel):
    email: str
    password: str


@router.post("/admins", status_code=201)
def make_admin(body: AdminIn, db: DbSession):
    with transaction(db):
        user = create_super_admin(db, body.email, body.password)
    return {"id": str(user.id)}
