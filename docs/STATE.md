# Current Phase

Phase 0 — Foundation: Ingest & Store

# Objective (thin slice)

Get one end-to-end slice working: raw ChatGPT export → MyChatArchive ingest → inspect the resulting SQLite DB → chunk a small sample of conversations.

# Definition of done for this phase

- Local SQLite DB created from a sample export
- At least 10 conversations verified as correctly imported
- Chunking works on a sample of 5–10 conversations
- All findings recorded in `PROGRESS.md`

# Tasks

## Now
- [x] verify mychatarchive import on a sample export — 540 threads / 24,240 messages imported from 56 MB conversations.json
- [x] inspect output SQLite schema — see PROGRESS.md 2026-04-12 Session 02
- [x] run chunking on 5–10 conversations — done 2026-04-11 Session 03 via `mychatarchive embed` on a 10-thread tiny DB; 241 messages → 430 chunks + 430 vec_chunks; nearest-neighbour sanity query works
- [x] design custom table for **classifications** only — `scripts/migrations/0001_classifications.sql` applied to `data/db/archive-tiny.db` (see PROGRESS 2026-04-12 Session 04)

## Next
- [x] classification prompt test on 10 conversations — done 2026-04-12 Session 05; 10/10 classified via real-time API, results stored in `classifications` table (5470 rows after fan-out to chunks)
- [x] report on tag distribution — done 2026-04-12 Session 06; conversation-level dedup report via `scripts/tag_distribution.py`
- [x] fix classification prompt/taxonomy issues before scaling to full corpus — done 2026-04-12 Session 06; tightened prompt (outcome enum, snake_case topics, on-taxonomy categories, emotion vocabulary), fixed JSON parser for preamble text; re-validated 10/10 on archive-tiny.db
- [ ] ingest Batch API results and run tag distribution on full corpus — batch ID: `msgbatch_01V4QaM15kUoCU23oWnLSU4j`

## Later
- [ ] BERTopic exploration
- [ ] Obsidian dashboards
- [ ] Phase 3 tiered emotion analysis (NRCLex → GoEmotions → Opus pass)

# Open questions

- ~~Exact folder layout for scripts and migrations~~ **Resolved 2026-04-12 Session 04:** migrations live in `scripts/migrations/NNNN_name.sql`, numbered sequentially.
- ~~SQLite migrations: raw SQL files vs Python (Alembic-style)?~~ **Resolved 2026-04-12 Session 04:** raw `.sql` files applied ad-hoc via `sqlite3` / `executescript`. Revisit if we accumulate >3 migrations or need a tracking table.
- ~~Where to keep the sample export for repeatable local testing?~~ **Resolved 2026-04-12:** `data/sample/` gitignored; publishable repos document the path in README rather than committing user data.
- ~~How does mychatarchive populate the `chunks` table?~~ **Resolved 2026-04-11 Session 03:** `chunker.chunk_text` is called only from `embeddings.run()` — chunks are a side effect of `embed`, inserted together with their vector. There is no chunk-only code path; `db.insert_chunk` requires an embedding arg.
- Whether to trim the torch/CUDA dependency stack pulled in by sentence-transformers (not needed for Phase 0 ingest, adds ~few GB)

# Risks

- Export format mismatch between user's actual export and MyChatArchive's expected shape
- Assumptions about MyChatArchive schema may be wrong until we inspect it
- Chunking boundary quality on a small sample may not generalize

# Decisions (load-bearing choices, newest on top)

- 2026-04-12 Session 07 — Embedded full 24,240-message archive (31,007 chunks across 523 threads). Wrote `scripts/classify_batch.py` (submit/poll/ingest). Submitted Batch API classification for all 540 conversations. Batch ID: `msgbatch_01V4QaM15kUoCU23oWnLSU4j`. Applied `0001_classifications.sql` migration to full DB.
- 2026-04-12 Session 06 — Classification prompt tightened: outcome must be exact enum (`success` not `successful`), topics must be `snake_case`, categories must come from the taxonomy (no invented ones), emotions must be genuine feelings (blocklist for mental states like `strategic`, `focused`, `determined`). JSON parser now handles preamble text before JSON. Re-validated 10/10.
- 2026-04-12 Session 05 — Classification prompt test uses real-time Messages API (not Batch) for small tests. Conversation-level classification is fanned out to all chunks in the thread. JSON fencing stripping added to handle model wrapping responses in markdown.
- 2026-04-12 Session 04 — `classifications` table stores one row per (chunk_id, scheme, label, model). Multi-label is native (multiple rows), confidence is optional, `raw` TEXT holds the Batch-API JSON payload for audit, `batch_id` ties rows back to a specific Batch-API submission. UNIQUE(chunk_id, scheme, label, model) makes re-runs idempotent.
- 2026-04-12 Session 04 — migrations: raw SQL files in `scripts/migrations/`, applied via `executescript`. No tracking table yet — add one if migration count grows.
- 2026-04-11 Session 03 — chunking + embedding is one coupled step in mychatarchive; rather than fight it, we use `mychatarchive embed` on a sliced tiny DB (10 threads) as the Phase 0 end-to-end slice. Keeps us on the real pipeline and gives us vectors for free.
- 2026-04-12 — install mychatarchive via `pip install -r requirements.txt` pinned to commit `46ac45e08b664960a7bc9befa0257faf2d50d78a` — reproducible, publishable, pip-idiomatic (repo is pip-installable via `pyproject.toml`)
- 2026-04-12 — `data/` (sample + db) is gitignored; never commit user exports or generated DBs
- 2026-04-12 — override mychatarchive's default `~/.mychatarchive/archive.db` location with `--db data/db/archive.db` so all project state lives under the repo
- 2026-04-11 — adopt minimal 3-file scaffolding (CLAUDE.md + STATE.md + PROGRESS.md) instead of 6-file generic LLM-handoff pattern — leverages Claude Code's `CLAUDE.md` auto-load, reduces maintenance surface
- 2026-04-11 — `AGENTS.md` is a symlink to `CLAUDE.md` — single source of truth for both Claude Code and Codex, zero drift risk
