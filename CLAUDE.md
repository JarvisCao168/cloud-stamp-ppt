# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Project overview

云章PPT智能体系统 — an AI-driven PPT generation platform. Monorepo of two apps:

- **Frontend**: Next.js (App Router) + React 19 + TypeScript + TailwindCSS 4, in `app/`.
- **Backend**: FastAPI + Python 3.12 (async, aiosqlite), in `backend/app/`. SQLite DB at `backend/yunzhang.db` — single authoritative DB, path anchored to an absolute path in `backend/app/core/config.py` so uvicorn CWD drift can never recreate a root-level DB.

Three generation modes: 极速 (`quick`), 协作 (`collaborative`), 掌控 (`full_control`). Export formats: HTML / PPTX / PDF / PNG.

## Commands

```bash
# Frontend
npm run dev              # dev server :3000; proxies /api/* → http://localhost:8001 (next.config.ts rewrites)
npm run build:verify     # next build + tsc --noEmit + eslint
npm run test:run         # vitest, all unit tests
npx vitest run <file>    # single test file (e.g. npx vitest run __tests__/creditPanel.test.ts)
npm run test:e2e         # playwright e2e (needs backend on :8001)

# Backend (FastAPI on :8001 in this env — 8000 has a legacy residual process)
python start_backend.py --reload
pytest                   # all backend tests (testpaths set in pytest.ini)
pytest backend/tests/test_quota_m2.py            # single test module
pytest backend/tests/test_presence_b3.py -k presence  # single test by keyword
```

`pytest.ini` sets `asyncio_mode = auto` and `testpaths = backend/tests backend/test_api.py`. The 4 async tests in `backend/test_api.py` are a smoke script that hits the live backend on :8001 — they fail with `httpx.ConnectError` when the backend isn't running; that is an environment block, not a code regression.

## Architecture that requires reading multiple files

- **Generation + SSE**: `backend/app/api/routes/generation.py` holds the three pipelines. The same router is registered twice in `main.py` — under `/api/generation` **and** `/api/collab` — so the SSE endpoint (`/api/collab/stream?session_id=...`) and the `collab_publish()` in-memory broadcast bus (per-session last-100 events + `asyncio.Queue` fan-out + 30s `ping` heartbeat + replay on join) live on the generation module. SSE event protocol (locked, front/back aligned): `snapshot`, `generation_progress` (stage enum: `intent`/`outline`/`content`/`numbering`/`style`/`keep_original` + extension `keep_original_progress`), `collab_status`, `ping`; `slide_update`/`generation_complete` are reserved types with no producer yet. Frontend hook: `app/components/collab/useCollabStream.ts` + `CollabStatusPanel.tsx`.
- **Quota / credits** (`backend/app/core/quota.py`): daily free-quota counter (`usage_log`, `FREE_DAILY_LIMIT=10`) + Phase 4 credit system (`user_credits` + `credit_ledger`, optimistic-lock deduction in `debit_credits`, retry 3× with 50ms backoff). `/create` checks quota then credits; 429 = free-quota exhausted with balance 0, 402 = insufficient credits — separate paths. `GET /api/quota/status` resolves `user_id` the same three-tier way as `/create` (`X-User-Id` header → `anon-{IP}` → `anon-unknown`); cross-user_id requests 404, never enumerate.
- **Model fallback chain**: Agnes (primary, `agnes_client.py`) → GLM (zhipu, `zhipu_client.py`) → built-in static defaults; `model_router.py` picks the channel. `/create` is not wired to Ollama despite `ollama_client.py` existing.
- **Long-text pagination**: `_paginate_keep_original()` in generation.py groups title+content lines, splits long paragraphs at sentence boundaries (no boundary → 300-char hard cut), promotes first line to page title when missing — no empty-title pages allowed. Each page emits a `keep_original_progress` SSE event.
- **Frontend state**: `app/generationStore.ts` (Zustand) drives the generation flow; all API calls go through `app/api.ts` returning `ApiResult<T>`.
- **DB schema** is defined in `backend/app/db.py` `SCHEMA_SQL` (seed + idempotent `init_db()` at startup): `usage_log` composite PK `(user_id, generated_at)` + index on the same (no autoincrement id, no separate date column); `record_usage` uses `INSERT OR REPLACE` which under the composite PK is an UPSERT — same-day over-limit short-circuits to 429, this is not request-level dedup.

## Docs & process

This repo is driven by a multi-agent workflow (JARVIS decides scope, Hermes 组长 gives final acceptance rulings, Claude/Codex execute). `STATUS.md` is the live status tracker — it is the authoritative record of milestones (M1–M4), locked line-number baselines, and pending items. When working in milestone areas, read the top of `STATUS.md` first; it records hard constraints (e.g. which lines in `quota.py`/`generation.py` must not change) and line-number baselines that have been three-way locked. `docs/phase4-plan.md` and `docs/m3-a-b-engineering-schedule-risk.md` hold the credit-system and M3/M4 engineering design. `BLOCKERS.md`, `TODOLIST.md`, `TEAM-CHARTER.md` round out the tracking docs.

## Testing notes

- Frontend unit: Vitest + Testing Library (jsdom, `@` alias → `./app`), coverage threshold 60% in `vitest.config.ts`; CI (`npm run test:ci`) fails below it.
- E2E: Playwright in `e2e/` against a live backend (`API_BASE` env, default :8001). The 429 path is verified by the E2E baseline (11 rapid calls = 10×200 + 1×429), not by unit tests.
- Backend: pytest; quota regression lives in `backend/tests/test_quota_m2.py` (collaborative/full_control single-test anchors at lines 99–100).
