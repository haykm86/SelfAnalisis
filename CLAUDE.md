# selfanalisis — Agent Operating Context

Personal self-analysis engine: build a personal knowledge base and behavioral analysis system from ~2GB of ChatGPT conversation exports. Evidence-first — every answer must trace back to source chunks.

**Owner:** Hayk
**Stack:** Python, Claude Batch API, SQLite, Obsidian, MCP servers, WSL

## Handoff protocol (read at session start)

1. Read `docs/STATE.md` — current phase, tasks, decisions, open questions.
2. Read the last 2 entries of `docs/PROGRESS.md` — what the previous session did.
3. The full architectural spec is `docs/personal-kb-final.md` (~1800 lines). **Read sections on demand, never the whole file.** Use the Table of Contents to jump.
4. Before changing code, list the files you plan to touch and wait for confirmation if scope is unclear.

## Guardrails (load-bearing, don't violate without discussion)

- **Use mychatarchive** (`1ch1n/mychatarchive`) for ingestion. Don't reimplement ChatGPT export parsing — it already handles tree-structured JSON, dedup, FTS5, and vector storage.
- **Python everywhere, no Go.** See ADR-1 in the PRD.
- **Claude Batch API for bulk classification; subscription for wiki compilation below plan limits.** See ADR-3 and STATE.md Session 16/21 decisions for rationale.
- **SQLite + Markdown, not Postgres.** See ADR-1.
- **Evidence-first.** Answers must trace to source chunks, not wiki summaries.
- See ADR-1..ADR-4 in `docs/personal-kb-final.md` section 1 for full rationale before overriding any of the above.

## Session discipline

- **One task per session.** Pick one item from `STATE.md` → Now, do it end-to-end, log it, stop. Chaining tasks burns context on Pro plan.
- **Plan mode liberally** for anything non-trivial. It costs nothing and catches mistakes early.
- **At session end**, propose updates for `docs/STATE.md` (task checkboxes, new decisions, new open questions) and append an entry to `docs/PROGRESS.md` before closing.

## When using Codex

Codex drifts more than Claude Code when under-constrained. Give it:

1. One task copied verbatim from `STATE.md` → Now.
2. The exact files it may touch.
3. An explicit instruction not to modify anything outside that scope.

Both Codex and Claude Code read this file (`AGENTS.md` is a symlink to `CLAUDE.md`), so the handoff protocol above applies to both.
