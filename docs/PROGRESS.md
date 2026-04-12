# Progress Log

Append-only session log. Newest entries at the top. Each entry follows the template below.

---

## 2026-04-12 Session 07 — claude-code

**Goal:** Run classification on full 540-conversation corpus via Batch API.

**Done:**
- Applied `scripts/migrations/0001_classifications.sql` to `data/db/archive.db`.
- Ran `mychatarchive embed --db data/db/archive.db` — 24,240 messages → 31,007 chunks across 523 threads (~1:20 on CPU). 17 threads produced no chunks (empty/very short messages).
- Wrote `scripts/classify_batch.py` with three subcommands: `submit` (builds and sends batch), `poll` (checks status, optional `--wait`), `ingest` (downloads results, parses JSON, fans out to chunks, stores in `classifications` table).
- Submitted batch: `msgbatch_01V4QaM15kUoCU23oWnLSU4j` — 540 requests, status `in_progress` at session end.

**Decisions:**
- Prompt shared between `classify_test.py` and `classify_batch.py` (duplicated, not extracted to a shared module — only 2 consumers, not worth the abstraction yet).
- `classify_batch.py` skips already-classified threads (checks via `classifications` JOIN `chunks`) — safe for re-runs.
- Embedding the full DB was a prerequisite for chunk fan-out storage. Running `mychatarchive embed` on the full archive is a one-time cost.

**Files touched:**
- `scripts/classify_batch.py` (new)
- `data/db/archive.db` (migration applied, chunks embedded; gitignored)
- `docs/STATE.md` (task updated, decision added)
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- First `mychatarchive embed` run in background exited without producing chunks (output truncated, no error). Re-ran in foreground-background mode and it completed successfully. Likely a shell buffering or early-exit issue with the first invocation.

**Open questions:**
- 17 threads have no chunks — are these genuinely empty conversations or a parsing issue? Check after ingest.

**Next:**
- Ingest batch results: `python scripts/classify_batch.py ingest --batch-id msgbatch_01V4QaM15kUoCU23oWnLSU4j`
- Run `python scripts/tag_distribution.py --db data/db/archive.db` for the full-corpus distribution report.

---

## 2026-04-12 Session 06 — claude-code

**Goal:** Generate a tag distribution report, then fix the classification prompt/taxonomy issues surfaced by the report before scaling to full corpus.

**Done:**
- Wrote `scripts/tag_distribution.py`: queries `classifications` joined through `chunks.canonical_thread_id` to produce conversation-level label counts per scheme, co-occurrence stats, emotion intensity averages, outcome distribution, and a per-conversation breakdown.
- Ran initial report on `archive-tiny.db` (10 conversations, 430 chunks, 5,470 classification rows). Surfaced 5 issues.
- Fixed all issues in the classification prompt in `classify_test.py`:
  1. **Outcome enum:** added explicit instruction to use exact values (`success` not `successful`).
  2. **Topic naming:** enforced `snake_case` in instructions and example.
  3. **Off-taxonomy categories:** added instruction to only use listed categories; no invented ones.
  4. **Emotion vocabulary:** added explicit valid/invalid emotion lists. Blocklisted mental states: `strategic`, `focused`, `engaged`, `analytical`, `determined`, `motivated`, `cautious`, `contemplative`.
  5. **JSON parsing:** replaced simple fencing stripper with robust parser that handles preamble text before JSON and markdown fencing via regex. Fixed the 2/10 parse failures from Session 05.
- Re-ran classification with fixed prompt: **10/10 parsed successfully**. All outcomes correct enum values, all topics snake_case, no off-taxonomy categories. One `engaged` slipped through (1/10 — acceptable model noise).
- Re-ran tag distribution report to verify clean data.

**Findings (post-fix, conversation-level):**
- **Categories:** `learning/ongoing` 6/10, `work/career` 3/10, `learning/successful` and `meta/planning` 2/10 each. All on-taxonomy.
- **Emotions:** More evenly distributed. `anxious`, `curious`, `frustrated`, `hopeful` each 3/10. No non-emotion labels except one `engaged`.
- **Topics:** All snake_case. 49 distinct topics, long-tail as expected. `interview_preparation` appears in 3/10 (highest reuse).
- **Outcomes:** `ongoing` 8, `success` 1, `unclear` 1. Correct enum values.
- **Confidence:** Still uniformly 0.9 — would need calibration examples in the prompt to improve discrimination. Not worth addressing before scaling.

**Decisions:**
- Report script deduplicates at conversation level via `COUNT(DISTINCT canonical_thread_id)` — correct denominator for frequency stats.
- Emotion blocklist enforced in the prompt rather than post-processing — cheaper to prevent than to clean up, especially at 540-conversation scale.
- JSON preamble stripping at parse time (find first `{`) — pragmatic; the prompt already says "no preamble" but models sometimes ignore it.

**Files touched:**
- `scripts/tag_distribution.py` (new)
- `scripts/classify_test.py` (prompt tightened, JSON parser improved)
- `docs/STATE.md` (tasks checked off, decision added)
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- Initial prompt fix run still had 2/10 JSON parse failures — the old fencing stripper didn't handle preamble text. Fixed by finding first `{` in the response.

**Open questions:**
- Overall `confidence` score (0.9+ uniformly) is not being stored — add a `confidence` column to a conversation-level table, or drop it?
- `engaged` still slips through occasionally despite blocklist — acceptable noise or add post-processing filter?

**Next:**
- STATE.md → Next → "run classification on full 540-conversation corpus via Batch API".

---

## 2026-04-12 Session 05 — claude-code

**Goal:** Run the classification prompt test (Phase 1, Step 1.1) on the 10 conversations in `archive-tiny.db` using the PRD Section 12.1 system prompt.

**Done:**
- Added `anthropic>=0.45.0` to `requirements.txt`, installed SDK (v0.94.0).
- Created `.env` for `ANTHROPIC_API_KEY` (gitignored).
- Wrote `scripts/classify_test.py`: loads conversations from the DB, classifies each via real-time Messages API (`claude-sonnet-4-20250514`), pretty-prints results for human review, then fans out conversation-level labels to all chunks in each thread and stores them in the `classifications` table.
- First run: 8/10 succeeded, 2 failed JSON parsing. Conv #4 returned a mind-map drawing (wrong format entirely), conv #5 wrapped JSON in markdown fencing despite the prompt saying not to.
- Fix: added markdown fencing stripping before `json.loads`. Warnings still print loudly for genuinely unparseable responses — no silent failures.
- Second run: 10/10 classified successfully. 5,470 rows in `classifications` (labels fanned out across 430 chunks).

**Findings — Human Checkpoint 1A:**
- Categories mostly accurate. Model invented `learning/planning` (not in taxonomy — should be `meta/planning`). Minor drift.
- Emotions are nuanced and contextual (e.g., `self-doubt`, `overwhelmed`, `strategic`). Some (`strategic`) are arguably not emotions — the taxonomy doesn't constrain this.
- Outcome values inconsistent: model returned `successful` vs the prompt's `success`. Needs tighter enum enforcement.
- Topics are appropriately specific. Naming inconsistency: some use underscores, some use spaces.
- Fan-out inflation: the 143-chunk "Bitwise Operations" conversation dominates all per-label counts. Summary stats should be read at conversation level, not chunk level.
- Confidence scores uniformly 0.9-0.95 — not much discrimination.

**Decisions:**
- Real-time API for tests (<20 conversations), Batch API for production runs. Confirmed ADR-3 approach.
- Conversation-level classification fanned out to chunks. Redundant storage but makes joins from chunk to labels trivial.
- Markdown fencing stripping is a parse-time fix, not a prompt fix. The prompt already says "no markdown fencing" — models sometimes ignore it.

**Files touched:**
- `scripts/classify_test.py` (new)
- `requirements.txt` (added `anthropic>=0.45.0`)
- `.env` (new, gitignored)
- `.gitignore` (added `.env`)
- `docs/STATE.md` (task checked off, decision added)
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- First paste of API key was truncated — caused a 401. Fixed by using the full key from the user's curl test.

**Open questions:**
- Should the prompt enforce stricter enum values for `outcome` (`successful` vs `success`)?
- Should we normalize topic naming (spaces vs underscores) at insert time or leave it to post-processing?
- `learning/planning` is not in the taxonomy — add it, or instruct the model more firmly to stay on-taxonomy?
- Confidence scores are uniformly high (0.9+). Add calibration examples to the prompt?

**Next:**
- STATE.md → Next → "report on tag distribution" — query `classifications` for label frequencies at the conversation level (deduplicate the chunk fan-out).

---

## 2026-04-12 Session 04 — claude-code

**Goal:** Close out Phase 0 Now list by designing the custom `classifications` table that Phase 1 Batch-API passes will write into.

**Done:**
- Inspected `chunks` schema on `data/db/archive-tiny.db`: `chunk_id TEXT PRIMARY KEY` — FK target confirmed.
- Wrote `scripts/migrations/0001_classifications.sql`: `classifications(classification_id PK AUTOINCREMENT, chunk_id FK→chunks, scheme, label, confidence REAL, model, batch_id, raw TEXT, created_at DEFAULT now)`.
- Indexes: `(chunk_id)`, `(scheme, label)`, `(batch_id)`, plus `UNIQUE(chunk_id, scheme, label, model)` for idempotent re-runs.
- Applied to `archive-tiny.db` via `executescript`. Verified: schema reads back correct, insert works, duplicate hits the unique index, bad `chunk_id` hits the FK (with `PRAGMA foreign_keys=ON`).
- Cleaned the test row; final `classifications` row count = 0.

**Decisions:**
- One row per (chunk, scheme, label, model). Multi-label is modelled as multiple rows, not a JSON blob — keeps SQL queries on label distribution straightforward. `raw` column still stores the Batch payload for audit.
- `model` is part of the uniqueness key so re-classifying with a newer model doesn't collide with old rows.
- Migrations live in `scripts/migrations/NNNN_name.sql`, applied ad-hoc via Python `executescript`. No tracking table until we have a reason.
- FK to `chunks` uses a plain `FOREIGN KEY` without `ON DELETE CASCADE` — classifications are derived data but not worth auto-dropping if a chunk is re-ingested; surface the error instead.

**Files touched:**
- `scripts/migrations/0001_classifications.sql` (new)
- `data/db/archive-tiny.db` (migrated; gitignored)
- `docs/STATE.md` (task checked off, 2 open questions resolved, 2 decisions added)
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- None this session. Initial instinct was to add a migration-tracking table up front; talked myself down per the "don't add abstractions beyond what the task requires" guardrail.

**Open questions:**
- Do we also want a `classification_runs` table (one row per Batch submission with prompt version, submission time, chunk count, cost)? Would make experiment bookkeeping cleaner but is not needed to run the first prompt test. Defer until the classification prompt test actually ships.
- Should `confidence` be NOT NULL? Left nullable because some prompting strategies won't return one. Revisit after the prompt test to see what we actually get back.

**Next:**
- STATE.md → Next → "classification prompt test on 10 conversations" against `data/db/archive-tiny.db`. That means: pick ~10 chunks, draft a classification prompt, run a small Batch-API submission, write results into `classifications`, verify the rows look sane.

---

## 2026-04-11 Session 03 — claude-code

**Goal:** Close the Phase 0 end-to-end slice by running chunking on 5–10 conversations. Open question from Session 02: find out how mychatarchive actually populates the `chunks` table.

**Done:**
- Traced the chunking path in installed mychatarchive 0.2.0: `chunker.chunk_text` is only called from `embeddings.run()` → `_flush_batch` → `db.insert_chunk`, which writes into both `chunks` and `vec_chunks` in one go. There is no chunk-only entry point.
- Wrote `scripts/make_tiny_sample.py` — slices the first N conversations out of `data/sample/conversations.json` (top-level is a plain list of 540 conversation objects, each with `title`/`mapping`/`conversation_id`/…).
- Generated `data/sample/conversations-tiny.json` with 10 conversations (~330 mapping nodes).
- `mychatarchive import … --db data/db/archive-tiny.db` → 303 parsed messages, 302 inserted (1 duplicate), 10 threads. ~0.05 s.
- `mychatarchive embed --db data/db/archive-tiny.db` → loaded `sentence-transformers/all-MiniLM-L6-v2`, processed 302 messages in ~20 s on CPU. Result: **241 messages embedded, 430 chunks, 61 skipped** (empty or <10 chars).
- Wrote `scripts/inspect_db.py` — vec0-aware SQLite inspector. Mirrors mychatarchive's own sqlite-vec load sequence (`enable_load_extension` → `sqlite_vec.load` → disable).

**Findings — tiny DB state after `embed`:**
- `messages`: 302 · `chunks`: 430 · `vec_chunks`: 430 · `thoughts`/`thread_summaries`/`thread_groups`: 0 (those are later pipeline steps, not side effects of `embed`).
- Chunks span all 10 threads.
- Chunk-length distribution: min 10, avg 693, max 1348 chars. Max exceeds the 1200-char target because `_apply_overlap` prepends ~150 chars from the previous chunk (documented behavior in [chunker.py:148](.venv/lib/python3.12/site-packages/mychatarchive/chunker.py#L148)).
- One outlier message produced 43 chunks — an unusually long assistant response (DSA course-material dump). Second-worst: 14. Suggests most user/assistant messages fit in 1–2 chunks.
- vec_chunks sanity query: `MATCH` with a probe embedding returns the chunk itself at distance 0, a near-duplicate at 0.055 (same course-material message, different chunk), and an unrelated chunk at 0.30. Cosine metric is working.

**Decisions:**
- Adopt `mychatarchive embed` on a sliced tiny DB as the Phase 0 end-to-end slice. Coupling chunking and embedding is a constraint of the upstream tool; working around it (raw-SQL chunker bypassing `vec_chunks`) would diverge from the real pipeline for no real gain.
- Keep `data/db/archive-tiny.db` as the canonical Phase 0 playground — next tasks (classification prompt test, tag-distribution report) should target it rather than re-embedding the full 24k-message DB.
- `scripts/inspect_db.py` stays as the default way to peek at a mychatarchive DB from this project — removes the per-session boilerplate of loading `sqlite_vec`.

**Files touched:**
- `scripts/make_tiny_sample.py` (new)
- `scripts/inspect_db.py` (new)
- `data/sample/conversations-tiny.json` (new, gitignored)
- `data/db/archive-tiny.db` (new, gitignored)
- `docs/STATE.md` — marked chunking task done, resolved the open question about the `chunks` population path, added a decision about the tiny-DB slice
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- Session 02 carried the assumption that a "chunk-only" entry point might exist somewhere in mychatarchive. It does not — `chunk_text` is strictly an internal helper of `embeddings.run()`. Resolved by reading the source instead of guessing.

**Open questions:**
- One message produced 43 chunks — do we want a hard per-message cap, or is unrestricted splitting fine for Phase 1 classification? Probably fine for now; flag it if Opus-pass costs balloon later.
- Still unresolved from Session 02: whether to split requirements into `requirements.txt` (ingest-only) + `requirements-embed.txt`. Not urgent; only matters if we publish or containerize.

**Next:**
- STATE.md → Now → "design custom table for classifications only". Sketch a schema that references `chunks.chunk_id` and stores tags/categories/confidence from the Batch API. Then pick up STATE.md → Next → classification prompt test on 10 conversations against `archive-tiny.db`.

---

## 2026-04-12 Session 02 — claude-code

**Goal:** Phase 0 first slice — get a ChatGPT export ingested via mychatarchive into a local SQLite DB and inspect the resulting schema.

**Done:**
- Moved `conversations.json` (56 MB, Mar 2025 export) → `data/sample/conversations.json`
- Added `.gitignore` (ignores `data/`, `.venv/`, pycache, Zone.Identifier)
- Added `requirements.txt` pinning `mychatarchive @ git+https://github.com/1ch1n/mychatarchive.git@46ac45e08b664960a7bc9befa0257faf2d50d78a`
- Created `.venv` (after installing `python3.12-venv` via apt), upgraded pip to 26.0.1
- `pip install -r requirements.txt` — succeeded; pulled torch + full NVIDIA CUDA stack via sentence-transformers (heavier than Phase 0 needs)
- `mychatarchive import data/sample/conversations.json --format chatgpt --db data/db/archive.db` — succeeded: parsed 24,966 messages across 540 threads; inserted 24,240 (726 duplicates); runtime ~3 seconds
- Inspected schema, row counts, thread count, role distribution, date range (see Findings)

**Findings — schema (mychatarchive 0.2.0):**
- Core tables: `messages`, `chunks`, `thoughts`, `thread_summaries`, `thread_groups`, `thread_group_members`
- **No dedicated `threads` table** — thread identity is denormalized as `canonical_thread_id` on every message row. Cheaper but means any thread metadata (title) lives on messages.
- `messages` columns: `message_id`, `canonical_thread_id`, `platform`, `account_id`, `ts`, `role`, `text`, `title`, `source_id`
- `chunks` columns: `chunk_id`, `message_id`, `canonical_thread_id`, `chunk_index`, `text`, `ts_start`, `ts_end`, `meta` — **already defined by mychatarchive, we don't need to design our own**
- FTS5 full-text search on `messages.text` via `messages_fts` + satellite tables — populated on import (24,240 docs)
- Vector tables: `vec_chunks`, `vec_thoughts`, `vec_thread_summaries` via sqlite-vec `vec0` virtual tables, 384-dim cosine. Require loading the sqlite-vec extension at connect time — plain `sqlite3.connect` cannot query them (hit `no such module: vec0` during inspection).

**Findings — data shape from this export:**
- Threads: 540 | Messages: 24,240
- Role distribution: user 10,725 · assistant 12,121 · tool 942 · system 452
- Date range: 2023-03-12 → 2025-03-30 (~2 years of history)
- `chunks`, `thoughts`, `thread_summaries`, `thread_groups` all empty after import — populated by later pipeline steps (`summarize`, `embed`, `groups`), not `import`

**Decisions:**
- Install mychatarchive via pinned git commit in `requirements.txt` (not submodule, not vendored) — it's pip-installable, so this is the idiomatic path and publishes cleanly
- `data/` (sample + generated DB) is gitignored — don't commit user data or derived state
- Override mychatarchive's default `~/.mychatarchive/archive.db` with `--db data/db/archive.db` so project state stays under the repo

**Files touched:**
- `CLAUDE.md` — fixed repo name (`chat-export-structurer` → `mychatarchive`)
- `.gitignore` (new)
- `requirements.txt` (new)
- `docs/STATE.md` — checked off first 2 Now tasks, added new open questions, logged decisions
- `docs/PROGRESS.md` (this entry)
- Moved `conversations.json` → `data/sample/conversations.json`
- Created `.venv/` (gitignored)

**Mistakes / wrong assumptions:**
- CLAUDE.md named the repo `1ch1n/chat-export-structurer` — the actual repo is `1ch1n/mychatarchive`. Fixed.
- Assumed we'd need to design our own `chunks` table — mychatarchive already defines it. Updated STATE.md to narrow the custom-table task to classifications only.
- Row-count inspection script consumed the sqlite_master cursor mid-iteration; had to re-run with a materialized list. Minor.

**Open questions:**
- How does mychatarchive populate the `chunks` table? No `chunk` subcommand exists; chunks likely come from `embed` or `summarize` as a side effect. Needs investigation before next session's chunking task.
- Whether to keep torch/CUDA in the dependency tree for Phase 0 (not needed for ingest, adds ~few GB). Could split deps into `requirements.txt` (ingest-only) + `requirements-embed.txt` later.
- SQLite inspection tooling: a helper script in `scripts/inspect_db.py` would be nice so we don't rewrite the vec0-aware connect boilerplate each session.

**Next:**
- Investigate how mychatarchive populates `chunks` (read `src/mychatarchive/` for the relevant module). Then either run the built-in pipeline step on 5–10 threads, or write a small stopgap chunker that writes directly into the existing `chunks` table. Pick up from STATE.md → Now → third bullet.

---

## 2026-04-11 Session 01 — claude-code

**Goal:** Decide and set up a lightweight workflow for cross-session, cross-model (Claude Code + Codex) continuity without building an agentic framework.

**Done:**
- Reviewed ChatGPT's proposed 6-file scaffolding (PROJECT / CONTEXT / PLAN / TASKS / PROGRESS / BOOTSTRAP)
- Rejected it in favor of a minimal 3-file approach that leverages Claude Code's native `CLAUDE.md` auto-load
- Created `CLAUDE.md` at repo root with handoff protocol, guardrails, session discipline, and Codex usage notes
- Created `docs/STATE.md` seeded from Phase 0 of the PRD
- Created this file (`docs/PROGRESS.md`)
- Pending: symlink `AGENTS.md` → `CLAUDE.md`

**Decisions:**
- Minimal 3-file scaffolding over 6-file — rationale logged in `STATE.md`
- `AGENTS.md` = symlink to `CLAUDE.md` — single source of truth, no drift
- PRD (`docs/personal-kb-final.md`) stays untouched as architectural source of truth; live working memory lives in `STATE.md` + `PROGRESS.md`
- No multi-agent framework, no orchestrator, no automation hooks for now

**Files touched:**
- `CLAUDE.md` (new)
- `docs/STATE.md` (new)
- `docs/PROGRESS.md` (new)
- `AGENTS.md` (symlink, pending)

**Mistakes / wrong assumptions:**
- Initial plan had 6 files; had to be talked down to 3 after realizing it ignored Claude Code's native `CLAUDE.md` auto-load. Lesson: check whether the tool already solves the problem before designing scaffolding.

**Open questions:**
- Whether to keep a committed sample export in the repo or in a gitignored local folder
- SQLite migration tooling choice (raw SQL vs Alembic)

**Next:**
- First real task from `STATE.md` → Now: verify MyChatArchive import on a sample export.

---

<!--
Template for future entries:

## YYYY-MM-DD Session NN — <claude-code | codex>

**Goal:**
**Done:**
**Decisions:**
**Files touched:**
**Mistakes / wrong assumptions:**
**Open questions:**
**Next:**
-->
