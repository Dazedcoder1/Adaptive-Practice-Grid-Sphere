# AdaptiveLearn AI

Self-paced, adaptive learning platform for Classes 6–12, JEE and NEET aspirants.
Modular monolith: **FastAPI** backend, **Next.js 16** frontend, **PostgreSQL (Neon)**, **Redis**,
**Celery**, **Cloudflare R2**, Docker, Nginx.

Two portals only: the **Student Portal** and the **Super Admin Portal** (no teacher portal).

## Status

| Phase | Scope | State |
|---|---|---|
| 0 — Foundation | Structure, Docker, DB + migrations, auth, RBAC, audit, CI | ✅ Done |
| 1a — First milestone | Curriculum, question bank + approval, onboarding, diagnostic + adaptive practice, BKT knowledge model, session reports, revision, error notebook, real dashboard | ✅ Done |
| 1b — Rest of MVP | Mock exams (timers, negative marking), analytics page, achievements/XP, learning-content editor, curriculum editor UI | Planned |
| 2 — AI | AI Tutor, RAG (pgvector), AI question generation | Planned |

Planned modules appear in both portals' navigation marked **Soon**, with a page describing exactly
what will ship. Nothing shows fabricated data.

### What works now

- **Learning loop (Phase 1a)**: onboarding (School / JEE / NEET → syllabus → subjects → goals →
  study rhythm), My Curriculum with per-concept mastery, concept pages with prerequisites, diagnostic
  and adaptive practice for all 9 question types (KaTeX maths, hints, server-side marking, solutions,
  "why this question"), pause/resume, session reports, spaced-repetition revision, weak topics and an
  error notebook with re-attempts. Mastery uses versioned Bayesian Knowledge Tracing (`bkt-v1`);
  question selection is foundations-first with controlled exploration, and every choice is stored.
- **Admin content**: question bank with filters, an editor for every type with live preview, versioning
  (edits never change past attempts) and draft → review → publish; curriculum tree with export.

- **Student**: register (with guardian-consent flow for under-18s), email verification, sign in,
  silent session restore, profile & timezone, change/reset password, signed-in devices (revoke
  one / sign out everywhere), account-deletion request.
- **Super Admin**: separate sign-in, live platform stats, system health, user search/filter/paging,
  user detail, suspend/activate (takes effect instantly), audit log, login activity, roles &
  permissions, failed background jobs.
- **Platform**: Argon2id, rotating refresh tokens with reuse detection, per-request session checks,
  rate limiting, append-only audit log, transactional outbox with idempotent consumers, retries
  and dead-lettering.

## Layout

```
backend/              FastAPI app
  app/config/         settings, database, redis, security
  app/modules/        20 domain modules (identity, users, administration, security, audit, … )
  app/shared/         exceptions, middleware, permissions, events (outbox)
  app/workers/        Celery app, outbox relay, consumers
  app/integrations/   email, storage (R2), llm, embeddings
  migrations/         Alembic
  tests/              pytest (real Postgres + Redis)
  scripts/            check_db, check_r2, create_superadmin
frontend/             Next.js app (App Router, Tailwind, shadcn-style UI, TanStack Query, Zustand,
                      React Hook Form + Zod, Framer Motion)
  src/app/            (auth)/ · (student)/ · admin/(portal)/ · admin/login
  e2e/                Playwright
infra/nginx/          reverse proxy config
docs/operations.md    admins, migrations, backups/restore, background jobs, security notes
```

## Setup

`.env` at the repo root is read by the backend and Docker Compose (copy `.env.example`).
`frontend/.env.local` sets `API_PROXY_TARGET` — the browser calls `/api/v1` on the web app's own origin and Next.js forwards it to the backend (Nginx does this in production).

### Docker (everything)

```bash
docker compose up --build
docker compose run --rm backend python -m scripts.create_superadmin --email you@example.com
```

Web http://localhost:3000 · API docs http://localhost:8000/api/v1/docs ·
Admin http://localhost:3000/admin/login

### Sample content

Practice needs published questions. Load the sample (CBSE Class 11 Physics — Laws of Motion, 11
concepts, 38 questions, every answer checked) once:

```bash
cd backend && python -m scripts.seed_sample_content
```

It's flagged as sample content and safe to run twice. Edit or archive it from the admin question bank.

### Native (Windows PowerShell shown)

```powershell
docker compose up -d redis

cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed_sample_content
python -m scripts.create_superadmin --email you@example.com
uvicorn app.main:app --reload

# workers (optional until features emit events)
celery -A app.workers.celery_app worker -Q default,ai,analytics -l info --pool=solo
celery -A app.workers.celery_app beat -l info

cd ..\frontend
npm install
npm run dev
```

With `EMAIL_BACKEND=console` (default), verification / reset / consent emails are printed in the
**backend terminal** — copy the link from there.

## Tests

```bash
# backend — needs a throwaway local Postgres + Redis (never your real DB; conftest refuses)
cd backend
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ap_test"   # PowerShell
pytest

# frontend unit/component
cd frontend
npm test

# end-to-end: run the API with ENVIRONMENT=test against a throwaway DB, the web app on :3000, then
npx playwright install chromium
npm run test:e2e
```

CI (GitHub Actions) runs lint, format, type-check, migrations (up/down/check), backend tests,
frontend tests, build, and the Playwright suite.

## API

Versioned REST under `/api/v1` — browse `/api/v1/docs`. Errors are always
`{"error": {"code", "message", "fields"?}}`.
