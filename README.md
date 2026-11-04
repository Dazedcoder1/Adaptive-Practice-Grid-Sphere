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
| 2a — AI tutor + RAG | Five-mode tutor, document ingestion, pgvector hybrid retrieval with citations, guardrails, prompts, limits, usage | ✅ Done |
| 2b — AI content | AI question generation (draft → validation → review → approval), misconception detection | Planned |

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
- **AI tutor (Phase 2a)**: Teach me · Give a hint · Solve with me · Test me · Find my mistake, on its own
  page and beside every practice question. Answers are grounded in approved study material and cite it.
  Before a student answers, the tutor never receives the answer key, and a reply that gives the answer
  away is caught and replaced; tutor help counts like a hint for mastery. Prompt-injection fencing, a
  wellbeing check, per-student and platform limits. **Without an API key it still works**: answers come
  from approved study notes, authored hints and worked solutions, clearly labelled.
- **AI admin**: provider status and live test, model / limits / prices / retrieval / retention settings,
  document upload (PDF, DOCX, Markdown, text) → review passages and concept mapping → approve, a
  retrieval playground with score breakdowns, retrieval evaluation (hit rate, MRR), versioned prompts,
  and usage, cost and guardrail reports.

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
It also loads approved study notes for the two sample chapters, which the AI tutor retrieves and cites.

### AI tutor (optional)

The tutor works without any AI provider (notes mode). To switch the AI on, add to `.env` and restart
the API:

```bash
LLM_PROVIDER=openai          # or gemini, anthropic, openai_compatible
LLM_API_KEY=...
EMBEDDING_PROVIDER=openai    # optional: semantic search (openai or gemini); blank = keyword search
```

Then check **Admin → AI & RAG**: the provider shows *Ready*, and *Test chat* makes a tiny live call.
Set your provider's prices there to see cost estimates, and press **Embed** on each document once
embeddings are switched on. Retrieval needs the `vector` extension — Neon has it; the migration
enables it.

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

The test Postgres needs pgvector (`pgvector/pgvector:pg16` in Docker, or `postgresql-16-pgvector`).
AI tests use an offline stand-in provider, so they never call a real API or need a key.

CI (GitHub Actions) runs lint, format, type-check, migrations (up/down/check), backend tests,
frontend tests, build, and the Playwright suite.

## API

Versioned REST under `/api/v1` — browse `/api/v1/docs`. Errors are always
`{"error": {"code", "message", "fields"?}}`.
