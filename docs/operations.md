# Operations

## Creating the first Super Admin

There is no public admin sign-up. From `backend/` (venv active, `.env` pointing at the target DB):

```bash
python -m scripts.create_superadmin --email you@example.com
```

With Docker: `docker compose run --rm backend python -m scripts.create_superadmin --email you@example.com`

## Migrations

```bash
cd backend
alembic upgrade head                                   # apply
alembic revision --autogenerate -m "describe change"   # after changing models
alembic check                                          # CI fails if models and migrations disagree
```

Migrations run against `DATABASE_DIRECT_URL` (Neon's non-pooled endpoint). The app uses the pooled
`DATABASE_URL`. Deploy migrations before the code that needs them, and keep them backward compatible
so the previous release keeps working during a rollout.

## Backups and restore (Neon)

- Neon keeps point-in-time restore history for the project (retention depends on the plan).
- **Restore drill** (do this before launch and periodically): in the Neon console create a branch
  from a past timestamp, point a staging `.env` at that branch, run `python -m scripts.check_db`
  and the API smoke test (`/api/v1/health`), then delete the branch.
- For an independent copy: `pg_dump "$DATABASE_DIRECT_URL" -Fc -f backup.dump`, store it
  encrypted (e.g. `age`/`gpg`) in a separate account, and test `pg_restore` into a scratch DB.
- R2 objects: enable bucket versioning or replicate to a second bucket.

## Background jobs

- Events are written to `outbox_events` in the same transaction as the change that caused them.
  `scheduler` (Celery beat) runs the relay every 2 s; workers consume them idempotently.
- If publishing fails 10 times an event is dead-lettered (`outbox_events.dead_lettered_at`).
  A consumer that exhausts its retries writes a row to `dead_letters`.
- Both are counted on the admin dashboard ("Failed background jobs") and listed under
  System Settings. After fixing the cause, replay by clearing `dead_lettered_at` (outbox) or
  re-sending the task with the stored args.

## AI tutor and study material

- **Keys**: `LLM_API_KEY`, `LLM_FALLBACK_API_KEY` and `EMBEDDING_API_KEY` live only in the
  environment (use your host's secret store in production). They are never written to the database,
  logs or API responses. Rotate a key by changing the variable and restarting the API.
- **No key = notes mode**: the tutor answers from approved study passages, authored hints and worked
  solutions, and says so. Turning the tutor off in Admin → AI does the same.
- **Fallback**: set `LLM_FALLBACK_PROVIDER` (+ key) to fail over on errors or timeouts; otherwise a
  failed call is retried once, then the student gets a notes-mode answer.
- **Limits**: per-student daily AI messages and tokens, and a platform-wide daily cost cap (needs prices
  entered in Admin → AI). Hitting a limit falls back to notes mode — students never see an error.
- **Documents**: uploads are type-checked from their content (PDF, DOCX, Markdown, UTF-8 text, 15 MB),
  extracted, split into passages and mapped to concepts. Nothing is retrieved until an admin approves
  it, and a document with an unknown licence can't be approved. Uploading a new version and approving it
  archives the old one. Originals go to R2 when it's configured.
- **Embeddings**: 768-dimension vectors in pgvector (HNSW index). Each passage records the model that
  embedded it; after changing `EMBEDDING_PROVIDER`/`EMBEDDING_MODEL`, press *Embed* on each document.
  Embedding runs on the `ai` queue (`worker-ai`), or in the API process when `PROCESS_EVENTS_INLINE=true`.
- **Retrieval quality**: add test queries in Admin → AI → Retrieval testing and re-run the evaluation
  after changing content, chunk sizes or the embedding model.
- **Privacy**: prompts contain no names, emails or other personal details. Students can delete their
  conversations; older ones are purged daily after the retention period (default 365 days) by the
  `ai.purge_conversations` beat task.

## Security notes

- Refresh tokens: httpOnly cookie, path `/api/v1/auth`, rotated on every use; a reused token
  revokes the whole login family. Access tokens are 15-minute JWTs held in memory only.
- Every authenticated request re-checks the user and session in the DB, so suspension and
  sign-out take effect immediately.
- Set `ENVIRONMENT=production` in production: refresh cookies get the `Secure` flag.
  Never set `ENVIRONMENT=test` outside automated tests — it mounts the `/__test__` helpers.
- Set `TRUST_PROXY_HEADERS=true` only behind `infra/nginx` (or a proxy that overwrites
  `X-Forwarded-For`), otherwise clients could spoof their IP to dodge rate limits.
- Legal: the minor/guardian-consent flow is designed for the DPDP Act 2023 but needs legal
  review before launch (verifiable consent method, retention periods, notices).
