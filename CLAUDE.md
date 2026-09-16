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
npx vitest run <file>    # single test file (e.g. npx vitest run app/__tests__/creditPanel.test.tsx)
npm run test:e2e         # playwright e2e (needs backend on :8001)

# Backend
python start_backend.py --reload   # starts uvicorn on port 8000 (the script default)
# In this env the live backend runs on :8001 instead — start uvicorn with --port 8001,
# or point the dev proxy elsewhere via NEXT_PUBLIC_BACKEND_URL.

pytest                       # all backend tests (testpaths set in pytest.ini at repo root)
pytest backend/tests/test_quota_m2.py              # single test module
pytest backend/tests/test_presence_b3.py -k presence  # single test by keyword
```

`pytest.ini` (repo root) sets `asyncio_mode = auto` and `testpaths = backend/tests backend/test_api.py`. The 4 async tests in `backend/test_api.py` are a smoke script that hits the live backend on :8001 — they fail with `httpx.ConnectError` when the backend isn't running; that is an environment block, not a code regression. `backend/tests/conftest.py` adds `backend/` to `sys.path` so the `app` package imports without installation.

Backend unit tests use a temp-file DB pattern: create a scratch SQLite DB with the full schema (`SCHEMA_SQL` from `backend/app/db.py`), seed it, then `patch.object(settings, "database_url", f"sqlite+aiosqlite:///{tmp_path}")` so `quota.py` functions hit the temp DB, never the authoritative `backend/yunzhang.db`. Follow this pattern for any new quota/credit test.

## Architecture that requires reading multiple files

- **Generation + SSE**: `backend/app/api/routes/generation.py` holds the three pipelines. The same router is registered twice in `main.py` — under `/api/generation` **and** `/api/collab` — so the SSE endpoint (`/api/collab/stream?session_id=...`) and the `collab_publish()` in-memory broadcast bus (per-session last-100 events + `asyncio.Queue` fan-out + 30s `ping` heartbeat + replay on join) live on the generation module. SSE event protocol (locked, front/back aligned): `snapshot`, `generation_progress` (stage enum: `intent`/`outline`/`content`/`numbering`/`style`/`keep_original` + extension `keep_original_progress`), `collab_status`, `ping`; `slide_update`/`generation_complete` are reserved types with no producer yet. Frontend hook: `app/components/collab/useCollabStream.ts` + `CollabStatusPanel.tsx`.
- **Quota / credits** (`backend/app/core/quota.py`): daily free-quota counter (`usage_log`, `FREE_DAILY_LIMIT=10`) + Phase 4 credit system (`user_credits` + `credit_ledger`, optimistic-lock deduction in `debit_credits`, retry 3× with 50ms backoff). `/create` checks quota then credits; 429 = free-quota exhausted with balance 0, 402 = insufficient credits — separate paths. `GET /api/quota/status` resolves `user_id` the same three-tier way as `/create` (`X-User-Id` header → `anon-{IP}` → `anon-unknown`); cross-user_id requests 404, never enumerate. `reserve_credit()` (M5-A `901dfa2`) is wired into `/create` at `generation.py:790` — only when free quota is exhausted (`if required > 0 and not allowed`); free-quota-priority means it is NOT called while the daily quota remains. collaborative/full_control modes no longer early-return 0 (M5-B `a525605` removed the two `return 0` lines in `estimate_required`); all three modes price off the same input_len tiers (≤500→1, ≤4000→3, ≤8000→5, >8000→8), multimodal→6, **M6-C final form**: `estimate_required` applies a Chinese-content ×1.2 ceiling coefficient INSIDE the tier formula (M6-B `e62709d`): 1→2, 3→4, 5→6, 8→10, multimodal stays 6 (early-return). `debit_credits` writes `credit_ledger` with `delta=-required`, `reason=f"gen_{mode}"` (M5-A); session_id is backfilled via `update_credit_ledger_session_id` after successful generation. The 402 paths: `generation.py:777` pre-check (`not allowed and 0 < balance < required`, balance > 0 but insufficient) and `:793` debit_fail fallback (`debit_credits` returns -1 = no account row → 402, or -2 = 3 version conflicts → 503). M6-C verification: M6-A `test_m6a_credit_ledger.py` (3 scenarios, commit `18ea893`) locks the ledger assertion baseline — interception paths assert zero increment; pass path uses located assertion `WHERE user_id=? AND delta=-required AND reason LIKE 'gen_%' AND created_at >= ?` → `count==1`.
- **Model fallback chain**: Agnes (primary, `agnes_client.py`) → GLM (zhipu, `zhipu_client.py`) → built-in static defaults; `model_router.py` picks the channel. `/create` is not wired to Ollama despite `ollama_client.py` existing.
- **Long-text pagination**: `_paginate_keep_original()` in generation.py groups title+content lines, splits long paragraphs at sentence boundaries (no boundary → 300-char hard cut), promotes first line to page title when missing — no empty-title pages allowed. Each page emits a `keep_original_progress` SSE event.
- **Frontend state**: `app/generationStore.ts` (Zustand) drives the generation flow; all API calls go through `app/api.ts` returning `ApiResult<T>`.
- **DB schema** is defined in `backend/app/db.py` `SCHEMA_SQL` (seed + idempotent `init_db()` at startup): `usage_log` composite PK `(user_id, generated_at)` + index on the same (no autoincrement id, no separate date column); `record_usage` uses `INSERT OR REPLACE` which under the composite PK is an UPSERT — same-day over-limit short-circuits to 429, this is not request-level dedup. `credit_ledger` schema is 6 columns (`seq` AUTOINCREMENT PK, `user_id`, `delta`, `reason`, `session_id`, `created_at`) + index `idx_credit_ledger_user_time(user_id, created_at)` — it has NO `input_len` or `required` columns; when writing ledger assertions, match on `delta = -required`, `reason LIKE 'gen_%'` (actual value is `f"gen_{mode}"`, e.g. `gen_quick`/`gen_collaborative`/`gen_full_control`, NOT the literal `'reserved'`), and `created_at >= ?` to bound stale rows. `reserve_credit`/`debit_credits` have NO built-in idempotent dedup — every call writes a new ledger row, so tests must use a fresh `user_id` per scenario.

## Docs & process

This repo is driven by a multi-agent workflow (JARVIS decides scope, Hermes 组长 gives final acceptance rulings, Claude/Codex execute). `STATUS.md` is the live status tracker — it is the authoritative record of milestones (M1–M5), locked line-number baselines, and pending items. When working in milestone areas, read the top of `STATUS.md` first; it records hard constraints (e.g. which lines in `quota.py`/`generation.py` must not change) and line-number baselines that have been three-way locked. `docs/phase4-plan.md` and `docs/m3-a-b-engineering-schedule-risk.md` hold the credit-system and M3/M4 engineering design. `BLOCKERS.md`, `TODOLIST.md`, `TEAM-CHARTER.md` round out the tracking docs.

## Testing notes

- Frontend unit: Vitest + Testing Library (jsdom, `@` alias → `./app`), coverage threshold 60% in `vitest.config.ts`; CI (`npm run test:ci`) fails below it.
- E2E: Playwright in `e2e/` against a live backend (`API_BASE` env, default :8001). The 429 path is verified by the E2E baseline (11 rapid calls = 10×200 + 1×429), not by unit tests.
- Backend: pytest; quota regression lives in `backend/tests/test_quota_m2.py` — M6-B anchors at lines 101–102 (post-`e62709d` baseline): `estimate_required("collaborative", 5000, "auto") == 6` and `estimate_required("full_control", 5000, "auto") == 6` (ceiling of `5 × 1.2` under the M6-B ×1.2 coefficient; M5 anchors at lines 100–101 with `== 5` are superseded).
- `backend/tests/test_m6a_credit_ledger.py` (M6-A, commit `18ea893`) locks the ledger assertion baseline: 3 scenarios, each with a **fresh, scenario-specific `user_id`** (single request, no replay), no `reserve_credit` mock on the 402 paths — interception happens at `generation.py:777` before the debit gate, so zero ledger increment is asserted. On the pass path the located-assertion must be `count==1` against `WHERE user_id=? AND delta=-required AND reason LIKE 'gen_%' AND created_at >= ?`.
