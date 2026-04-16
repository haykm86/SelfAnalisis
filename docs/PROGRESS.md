# Progress Log

Append-only session log. Newest entries at the top. Each entry follows the template below.

---

## 2026-04-16 Session 22 — claude-code

**Goal:** Status review, full-pass scaling decision, and housekeeping (commit all untracked work from Sessions 10-21).

**Done:**
- Reviewed project status end-to-end. Phase 0-1 complete, Phase 2 first-pass complete (5/5 articles).
- Made the full-pass scaling decision: compile 22 remaining topics at ≥10 threads on subscription. Rejected ≥5 threshold (57 extra thin buckets) and Batch API (slow, unproven quality).
- Committed all untracked work from Sessions 10-21 (8 scripts, 1 prompt, 1 migration, 4 modified files).
- Softened CLAUDE.md ADR-3 guardrail to reflect subscription-based wiki compilation reality.
- Updated STATE.md with the scaling decision and refreshed task queue.

**Note — Sessions gap:** Sessions between 20 and 21 (articles daily_routines, english_grammar, interview_preparation) were compiled to disk but never logged to PROGRESS.md. Article files exist with correct frontmatter; session-level decisions and bundle stats are not recoverable. Accepting the gap rather than fabricating entries.

**Decisions:**
- Full-pass scope: 27 topics at ≥10 threads (22 remaining after 5 first-pass). 3 oversized buckets (interview_preparation, english_learning, data_structures_algorithms) need `--thread-chars 1500`.
- Subscription over Batch API for all wiki compilation. Batch was 4.5h on one article; subscription is faster, iterative, zero marginal cost.
- After wiki full-pass: Phase 5 (Retrieval with FTS5 hybrid) before Phase 3 (Emotion). Retrieval makes the knowledge base queryable; emotion analysis doesn't unblock anything.

**Files touched:**
- `CLAUDE.md` — softened ADR-3 guardrail
- `docs/STATE.md` — scaling decision recorded, task queue refreshed
- `docs/PROGRESS.md` — this entry + gap acknowledgment
- All previously untracked files staged and committed

**Next:**
- Begin wiki full-pass: compile ~4 articles per session from the remaining 22 topics.

---

## 2026-04-14 Session 21 — claude-code

**Goal:** Compile the 5th first-pass wiki article: `microservices`. This is the architectural-axis pick from the first-pass shortlist in STATE.md → Now (microservices vs system_design), and closes out the 5-article first pass.

**Done:**
- Rebuilt the source bundle with `python scripts/compile_wiki_input.py --topic microservices --out /tmp/microservices.bundle.txt`. 26/26 threads included, 68,280 chars, well under the 150k cap at the default 2,500-char per-thread budget.
- Read the bundle in full and the compile prompt in [prompts/wiki_compile.md](prompts/wiki_compile.md).
- Wrote [vault/wiki/microservices.md](vault/wiki/microservices.md) — ~2,700 words, five-phase chronological arc (2023 inherited mess → 2024 Hayyert co-founder era → setback overlay → 2025 Go pivot → `ggwpbet` saga/outbox implementation). Frontmatter lists all 26 `source_thread_ids`. Cross-refs to [[clickhouse]], [[interview_preparation]], [[daily_routines]], [[english_grammar]], [[data_structures_algorithms]].

**Decisions:**
- Picked `microservices` over `system_design` when prompted — user's choice.
- Treated the 2024-08-12 Hayyert setback thread and the 2024-10-07 self-doubt thread as load-bearing *context* for the microservices arc (not a detour), because they explain why Hayyert progress stalled in Aug-Sep 2024 while the architectural learning kept accumulating. Same for the 2025-10-10 Go-internals reflection.
- Framed the 2025-11-02 "mini-monolith" thread as the narrative closure — the same diagnosis as the 2023 inherited-mess thread, but self-applied early on a green-field project. This is the emergent pattern for the article.

**Files touched:**
- `vault/wiki/microservices.md` — new article (article #5 of first pass)
- `docs/PROGRESS.md` — this entry
- `docs/STATE.md` — check off article #5, note first-pass complete, pending a go/no-go on full-pass scaling

**Mistakes / wrong assumptions:**
- Sessions 21–24 (articles #2 daily_routines, #3 english_grammar, #4 interview_preparation) were compiled and written to disk but **never logged to PROGRESS.md**. The log jumps straight from Session 20 to this Session 21. The article files exist (`vault/wiki/daily_routines.md`, `english_grammar.md`, `interview_preparation.md`) with mtimes Apr 13–14, but the session-level decisions, bundle sizes, and open questions for those compiles are not captured anywhere in this log. This is a session-discipline gap worth backfilling if we want the PROGRESS trail to stay reconstructable.

**Open questions:**
- Backfill question: do we reconstruct Sessions 21a/21b/21c entries for daily_routines / english_grammar / interview_preparation from the article frontmatter + git mtimes, or accept the gap and continue forward?
- First-pass is now 5/5. Time to decide the full-pass scaling path (STATE.md → Now → 2nd bullet): stay on subscription for ~190 remaining buckets, switch to Batch API, or narrow scope to ≥ 20 threads. We now have 5 articles of quality evidence, not just 1 — the decision was explicitly gated on this.
- Guardrail revisit: CLAUDE.md / ADR-3 currently still says "Batch API for bulk LLM work". With 5 subscription-compiled articles user-validated at article time, is now the moment to soften that wording to something like "Batch API for bulk classification, subscription for bulk compilation below plan limits"?

**Next:**
- User review of `microservices.md`.
- Then either (a) backfill the 3 missing session entries, or (b) move directly to the full-pass scaling decision, or (c) start article #6 if we're extending the first pass past 5.

---

## 2026-04-14 Session 20 — codex

**Goal:** Create a genuinely blind Codex ClickHouse wiki from the source bundle only, so the Codex-vs-Opus comparison is not contaminated by prior exposure to the existing wiki outputs.

**Done:**
- Re-used the preserved ClickHouse source bundle at `/tmp/clickhouse.bundle.txt`, which contains the 22-thread bundled input for the topic.
- Wrote a new blind comparison file at [vault/wiki/_batch_experiments/clickhouse.codex-blind.md](vault/wiki/_batch_experiments/clickhouse.codex-blind.md).
- Kept the earlier artifacts untouched:
  - subscription baseline: [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md)
  - Batch result: [vault/wiki/_batch_experiments/clickhouse.batch.md](vault/wiki/_batch_experiments/clickhouse.batch.md)
  - earlier informed Codex variant: [vault/wiki/_batch_experiments/clickhouse.codex.md](vault/wiki/_batch_experiments/clickhouse.codex.md)

**Decisions:**
- Treat `clickhouse.codex-blind.md` as the cleaner Codex benchmark, because it was written from the bundled evidence only.
- Keep `clickhouse.codex.md` rather than deleting it; it still has value as an informed editorial variant, just not as the fairest benchmark.

**Files touched:**
- `vault/wiki/_batch_experiments/clickhouse.codex-blind.md` — new blind Codex comparison article
- `docs/STATE.md` — noted that the blind artifact is now the more valid benchmark
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- The earlier Codex article was useful but not truly independent because I had already seen the subscription and Batch outputs. This session corrects that experimental weakness rather than pretending it did not exist.

**Open questions:**
- How does the blind Codex version compare to the Opus/Batch version on factual accuracy, chronology, and synthesis quality?
- Is the remaining gap, if any, mostly about writing style or about missed evidence?

**Next:**
- Compare at least these three files side by side:
  1. [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md)
  2. [vault/wiki/_batch_experiments/clickhouse.batch.md](vault/wiki/_batch_experiments/clickhouse.batch.md)
  3. [vault/wiki/_batch_experiments/clickhouse.codex-blind.md](vault/wiki/_batch_experiments/clickhouse.codex-blind.md)

---

## 2026-04-14 Session 19 — codex

**Goal:** Produce a Codex-authored ClickHouse wiki so the project has a third comparison artifact beside the user-validated subscription version and the Opus/Batch result.

**Done:**
- Read the current baseline [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md), the Batch result [vault/wiki/_batch_experiments/clickhouse.batch.md](vault/wiki/_batch_experiments/clickhouse.batch.md), and the preserved source bundle in `/tmp/clickhouse.bundle.txt`.
- Wrote a separate Codex-authored article at [vault/wiki/_batch_experiments/clickhouse.codex.md](vault/wiki/_batch_experiments/clickhouse.codex.md). It uses the same 22-thread source set, keeps evidence markers in the body, and explicitly positions itself as a comparison artifact rather than a replacement.
- Kept both existing articles untouched:
  - baseline: [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md)
  - Batch API result: [vault/wiki/_batch_experiments/clickhouse.batch.md](vault/wiki/_batch_experiments/clickhouse.batch.md)

**Decisions:**
- Use a third file rather than rewriting either existing article. This keeps the comparison clean and reversible.
- Put the Codex-authored article under `_batch_experiments/` with the Batch version because the folder is now functioning as the comparison workspace, not just the Batch-output workspace.

**Files touched:**
- `vault/wiki/_batch_experiments/clickhouse.codex.md` — new Codex-written comparison article
- `docs/STATE.md` — recorded that the third artifact now exists
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- None significant this session. This was a straightforward artifact-creation pass with no pipeline or API work.

**Open questions:**
- Which of the three versions is actually best on accuracy and usefulness: the subscription baseline, the Batch API result, or the Codex synthesis?
- Should future comparisons also get a `*.codex.md` sibling, or was this only worth doing because `clickhouse` became the first calibration topic?

**Next:**
- Compare the three ClickHouse files side by side and decide what quality dimensions matter most for the eventual full-pass strategy: factual faithfulness, chronology, writing clarity, cleanup burden, or runtime/cost.

---

## 2026-04-14 Session 18 — codex

**Goal:** Complete the first real Batch API wiki comparison run for `clickhouse`, ingest the result into the separate experiment path, and capture the operational outcome for future full-pass planning.

**Done:**
- Submitted the ClickHouse wiki compile via [scripts/compile_wiki_batch.py](scripts/compile_wiki_batch.py) using the already-verified single-topic bundle. Batch ID: `msgbatch_0139GhgeUv1D6Q9H6RPRa35B`.
- Confirmed the submission shape was what we intended: **one** Batch API request containing a bundled source document built from **22 ClickHouse threads**. This resolved the user's concern about why Anthropic status showed `processing=1` rather than `processing=22` — the 22 threads are source material inside one compile request, not 22 separate batch items.
- Hit the expected sandbox network restriction on the first submit attempt (`anthropic.APIConnectionError` / DNS resolution failure), then re-ran with escalation and submitted successfully. No code bug here; just network permissions.
- While the batch was running, improved [scripts/compile_wiki_batch.py](scripts/compile_wiki_batch.py) so `poll` prints timestamp metadata (`created_at`, `ended_at`, `expires_at`, and related fields when present). This turned out to be useful because the run was much slower than expected and we needed stronger visibility than just `in_progress`.
- Confirmed final status:
  - `created_at: 2026-04-13 15:18:21.741127+00:00`
  - `ended_at: 2026-04-13 19:51:33.313035+00:00`
  - `succeeded=1, errored=0, expired=0`
  - Total runtime: about **4 hours 33 minutes**
- Ingested the finished result to [vault/wiki/_batch_experiments/clickhouse.batch.md](vault/wiki/_batch_experiments/clickhouse.batch.md). The control article [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md) was left untouched.

**Findings:**
- The Batch helper worked end-to-end on the first real run: submit → poll → ingest all behaved correctly.
- Anthropic treated the wiki compile as one batch item, which matches the code and the intended design.
- The operational profile was slower than expected for a one-request wiki compile. Not a failure, but it weakens the simple assumption that Batch will reliably come back in ~1 hour for this workload.

**Decisions:**
- Keep the first Batch artifact as a comparison target only. No replacement of the subscription baseline happens automatically.
- Treat runtime as a real planning signal. The next full-pass decision should use observed batch duration, not just the PRD's coarse estimate.
- Defer quality judgment to a separate comparison step. This session's job was completion + ingestion + logging, not editorial scoring.

**Files touched:**
- `scripts/compile_wiki_batch.py` — richer batch-status output in `poll`
- `docs/STATE.md` — recorded successful completion of the first wiki Batch experiment and its runtime
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- Initial user concern that `processing=1` implied a bad submission turned out to be a mental-model mismatch, not an implementation bug. The script correctly submits one bundled request.
- The Batch turnaround estimate was too optimistic. Nothing broke, but the actual elapsed time was materially longer than I expected.

**Open questions:**
- How does the Batch-written article actually compare to the subscription baseline on accuracy, chronology, and cleanup burden?
- Was the 4 h 33 m turnaround an outlier queue condition, or should we expect similar latency for future wiki compiles?

**Next:**
- Diff [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md) against [vault/wiki/_batch_experiments/clickhouse.batch.md](vault/wiki/_batch_experiments/clickhouse.batch.md) and judge whether Batch quality is better, worse, or similar enough to justify scale.

---

## 2026-04-13 Session 17 — codex

**Goal:** Set up a safe A/B experiment for wiki compilation so the existing subscription-written [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md) can stay the control while a Batch API version is generated separately and compared later.

**Done:**
- Read [docs/STATE.md](docs/STATE.md), the latest progress entries, [vault/wiki/clickhouse.md](vault/wiki/clickhouse.md), [scripts/compile_wiki_input.py](scripts/compile_wiki_input.py), [prompts/wiki_compile.md](prompts/wiki_compile.md), and the Phase 2 PRD section in [docs/personal-kb-final.md](docs/personal-kb-final.md) before changing anything. Confirmed the repo already had a subscription-side bundler, but no wiki Batch helper.
- Refactored [scripts/compile_wiki_input.py](scripts/compile_wiki_input.py) so the topic-bundling logic lives in a reusable `build_bundle()` helper instead of only inside the CLI path. Behavior is still the same from the caller's perspective: same 150k global char cap, same per-thread truncation, same user+assistant-only message filtering. One useful cleanup: time span and thread counts are now derived from the actually included threads after cap enforcement, not the pre-drop candidate list.
- Added [scripts/compile_wiki_batch.py](scripts/compile_wiki_batch.py) with four subcommands:
  - `prepare` — local dry run, builds the exact bundle with no network call
  - `submit` — submits one topic as a one-request Claude Batch
  - `poll` — checks Batch API status
  - `ingest` — writes the result as markdown with generated frontmatter
- The new script deliberately treats `vault/wiki/<topic>.md` as the control article and defaults Batch output to `vault/wiki/_batch_experiments/<topic>.batch.md`. `ingest` refuses to overwrite an existing experiment file unless `--overwrite` is passed. Nothing in the script points at `vault/wiki/clickhouse.md` for writing.
- Verified locally with the project venv:
  - `.venv/bin/python -m py_compile scripts/compile_wiki_input.py scripts/compile_wiki_batch.py`
  - `.venv/bin/python scripts/compile_wiki_batch.py prepare --topic clickhouse --bundle-out /tmp/clickhouse.bundle.txt --preview 400`
  - Dry-run result: **22/22 threads included, 56,270 chars**, experiment output path `vault/wiki/_batch_experiments/clickhouse.batch.md`, control path preserved as `vault/wiki/clickhouse.md`.

**Decisions:**
- Keep the experiment artifact separate from the validated control article. This is now encoded in the script defaults rather than depending on operator discipline.
- Reuse the exact same bundle builder and the exact same compile prompt for the Batch path. That keeps the comparison honest: execution mode changes, not source selection or prompt wording.
- Add a local `prepare` mode before any network call. This makes it easy to inspect the bundle and confirm the output target before spending Batch API money or risking confusion.

**Files touched:**
- `scripts/compile_wiki_input.py` — extracted shared `build_bundle()` helper
- `scripts/compile_wiki_batch.py` — new safe Batch experiment helper
- `docs/STATE.md` — noted the new harness and the default no-overwrite rule
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- First verification attempt used `python`, but this shell only exposes `python3`. Switched to `.venv/bin/python` for all checks.
- First version of `compile_wiki_batch.py` imported `anthropic` at module import time, which meant even local `prepare` mode depended on the Batch SDK import path. Tightened that to a lazy `get_client()` helper so only `submit/poll/ingest` need the API client.

**Open questions:**
- The rebuilt ClickHouse bundle reports a `2024-09-28` upper bound while the existing control article frontmatter says `2024-09-26`. Likely a timestamp-boundary/detail issue rather than a substantive mismatch, but worth checking once we do the actual diff so we know whether the control article metadata should be normalized.
- When we run the real Batch compile, do we want to preserve the exact input bundle used for the run under `/tmp` only, or save it somewhere durable for auditability? For now the helper supports optional `--bundle-out`; no permanent storage policy was chosen.

**Next:**
- If/when we want the actual A/B comparison, run:
  1. `.venv/bin/python scripts/compile_wiki_batch.py submit --topic clickhouse`
  2. `.venv/bin/python scripts/compile_wiki_batch.py poll --batch-id <id> --wait`
  3. `.venv/bin/python scripts/compile_wiki_batch.py ingest --topic clickhouse --batch-id <id>`
  4. Diff `vault/wiki/clickhouse.md` against `vault/wiki/_batch_experiments/clickhouse.batch.md`

---

## 2026-04-13 Session 16 — claude-code

**Goal:** Design and begin execution of the Phase 2 wiki compilation slice. Resolve the upstream architectural question the user raised mid-planning: **why pay Batch API money when Claude Code runs on a subscription where tokens are sunk cost?** Validate the §12.3 compile prompt on a first real article before committing to the full ~200-article pass.

**Done:**
- Engaged the user's architectural challenge to ADR-3 head-on. Read [docs/personal-kb-final.md §6.2.3](docs/personal-kb-final.md) and §13 cost table. Concluded: ADR-3's rationale (50% vs real-time API, prompt caching, async) was written without accounting for a subscription model — for a **first-pass** (3–5 articles) subscription-based compilation is strictly better (zero marginal cost, live iteration, human-in-loop per article); for a **full pass** (~200 articles, ~2M input + 600K output tokens) Pro-plan weekly caps may force a switch to Batch API, but that decision should wait until we've seen first-pass quality. Guardrail isn't rewritten yet — deferred until we have quality evidence.
- User decisions logged in the approved plan: cluster by existing `canonical_label` buckets (zero new work), compile 3–5 L2 articles before attempting the L1 identity doc.
- Plan written to `~/.claude/plans/shimmering-meandering-rivest.md` and approved.
- Wrote [scripts/compile_wiki_input.py](scripts/compile_wiki_input.py) — pure Python data bundler, no LLM calls. Two modes: `--list` (topics with ≥ N threads, thread/msg/raw-char counts, estimated budget, fit flag) and `--topic NAME --out PATH` (assembles a compile-ready bundle with per-thread char budget, user+assistant roles only, truncation with `…[truncated]` marker, and a 150k global char cap with drop-list reporting).
- Copied §12.3 prompt verbatim to [prompts/wiki_compile.md](prompts/wiki_compile.md) so iterations are version-controlled separately from the PRD.
- Ran `--list --min-threads 10` → 27 meaningful canonical buckets surfaced. Top 3 (interview_preparation 81, english_learning 69, data_structures_algorithms 62) exceed 150k cap at default 2500 chars/thread; everything else fits.
- Compiled first wiki article: **`vault/wiki/clickhouse.md`** (22 threads, 2023-07-21 → 2024-09-26, ~1,900 words). Bundle was 56,212 chars with all 22 threads included (no drops). Article follows PRD §12.3 structure: Overview / Timeline / Decisions & Outcomes / Lessons & Patterns / People / Connections. Includes explicit "unresolved in source material" subsection for claims the source material raised but didn't answer.
- User read the article and judged it **"mostly correct"** on first pass. No prompt tweaks requested this session. Prompt and data-assembly pipeline are provisionally validated.

**Findings — what the corpus actually clusters into:**
- 27 canonical topics have ≥ 10 threads. Most fit under 150k chars at 2500 chars/thread budget.
- 3 huge buckets (`interview_preparation`, `english_learning`, `data_structures_algorithms`) need a smaller per-thread budget (~1500 chars) to fit — deferred as a small follow-up.
- `COALESCE(canonical_label, label)` returns 3461 distinct topics once the long tail of singleton unaliased raw labels is included. The 22 real canonicals from [scripts/topic_aliases.py](scripts/topic_aliases.py) aren't a closed set in the DB — they coexist with ~3400 singleton topics. For wiki compilation the `--min-threads 10` filter is what actually matters, not the alias status.

**Findings — what emerged from the clickhouse article:**
- A real 14-month narrative arc exists in the ClickHouse conversations (July 2023 "can I use EF?" → ADO.NET pivot → operational schema/syntax battles → late-2024 architectural reflection on microservices reporting). This is exactly the kind of synthesis the wiki layer is supposed to produce.
- Project context leaked out naturally: "Hayyert" taxi/payment platform, Yandex.Taxi integration, Armenia-based dev env (`DEV-CRM-DB02.toto.am`). The wiki article captured it without hallucinating.
- Recurring patterns the article surfaced: ORM-over-OLAP impedance mismatch, "sync is harder than the engine," ClickHouse dialect surprises (`SET GLOBAL`, UNION column order, DateTime64 precision corruption), background-job observability gaps. These are exactly the kinds of cross-conversation patterns only a synthesis pass can surface — they're invisible from any single thread.

**Decisions:**
- **Subscription-based first-pass of Phase 2 wiki compilation** instead of Batch API. Load-bearing — future sessions need to know why we diverged from ADR-3. Rationale: ADR-3 assumed pay-per-token; under a subscription, marginal cost is zero, iteration speed is much higher, and first-pass scope (3–5 articles, ~40k input tokens each) is trivially within plan limits. Full-pass scale decision deferred until we've seen more first-pass quality.
- **Per-thread char budget with truncation** is the representative-sampling strategy ([PRD §6.2.3](docs/personal-kb-final.md) punted on this). For first pass, default 2500 chars/thread × N threads, global cap 150k. Drop only when a thread would push past the global cap. Works empirically: 22/22 clickhouse threads fit without drops.
- **Drop `tool` and `system` roles** from the compile bundles — they're mostly noise (tool-call JSON from older ChatGPT versions, system wrappers). User+assistant only. Applied at both SQL-query and `--list` stats level so numbers are consistent.
- **No subagents for first-pass compilation.** Subagents cold-start without conversation context, can't see prompt-tuning feedback across articles, make iteration harder. Main-thread compilation is slower but gives live feedback. Subagents become the right choice at scale (200 articles), not prototype (5).
- **Defer `evidence_links` table writes** ([PRD §2.4](docs/personal-kb-final.md)). Table doesn't exist yet in schema; first-pass records `source_thread_ids` in YAML frontmatter only. Migrate the table when we know wiki output is worth keeping long-term.

**Files touched:**
- `scripts/compile_wiki_input.py` (new, ~180 lines)
- `prompts/wiki_compile.md` (new, verbatim PRD §12.3)
- `vault/wiki/clickhouse.md` (new, first compiled article; vault is gitignored)
- `docs/STATE.md` (this session's updates — see below)
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- First version of the `list_topics` query assumed `COALESCE(canonical_label, label)` would return ~22 canonicals. It returned 3461 — because only the 69 raw labels in the alias map get folded; everything else keeps its original (often singleton) label. Fixed by adding `--min-threads` filter rather than trying to enumerate a "canonical-only" set.
- First version included full message bodies without per-thread truncation; everything blew past the 150k cap because real conversations average ~20k chars. Fixed by introducing a per-thread budget with ellipsis truncation — simple, preserves chronological order, no representative-sample logic needed yet.

**Open questions:**
- Is the §12.3 prompt final, or will later topics (especially the personal/behavioral ones like `daily_routines`, `time_management`, `habit_formation`) need prompt adjustments? Can't answer without trying at least one non-technical compile.
- Should the wiki directory be pushed through `generate_vault.py` so it's browseable in the same Obsidian vault as the thread dashboards, or kept as a separate manually-maintained folder? Session 14's script writes `threads/` and `dashboards/`; adding `wiki/` to that pipeline would unify the vault but bloats the script's responsibilities.
- How much of the "unresolved in source material" content in the clickhouse article points at things that actually *are* answered in *other* topics (e.g. the CQRS/materialized-view question is probably answered in `microservices` or `event_driven_architecture` conversations)? The PRD's cross-reference pass ([§2.5](docs/personal-kb-final.md)) is supposed to catch this but it runs after all wikis are compiled.

**Next:**
- Compile articles #2–#5 from the first-pass shortlist: likely `daily_routines` (personal/behavioral axis), one of `microservices`/`system_design` (architectural axis), `interview_preparation` (career axis, needs `--thread-chars 1500`), and `english_grammar` or similar learning-oriented topic. Review each individually before continuing to the next. User wants pacing, not batching.
- After the first 3–5 articles, make the full-pass decision: (a) continue on subscription for the remaining ~190 buckets with ≥ 10 threads, (b) switch to Batch API for the scaled pass, or (c) narrow the full-pass scope (e.g. only buckets with ≥ 20 threads to cut ~150 articles). Decision depends on subscription headroom and article quality stability.
- Separately: revisit CLAUDE.md/ADR-3 guardrail wording once we have evidence from ≥ 3 articles that subscription-based compilation is reliable.

---

## 2026-04-13 Session 15 — claude-code

**Goal:** Answer the half of the user's Session 14 question that the vault left open: *"does our rag work ok or it completely mess"*. Build a minimal retrieval slice over `vec_chunks` that is small enough to ship in one afternoon and strong enough to give a clear pass/fail signal on whether the embeddings are load-bearing. Unblock the Phase 2 decision either way.

**Done:**
- Re-grounded mental model with the user in plan mode. Walked through Sessions 13–14 which they had missed, validated their mental model of the pipeline against the PRD (mostly right, with two clarifications: topic normalization is fold-not-cluster, and classification is per-thread fanned out to per-chunk rows).
- Wrote [scripts/rag_query.py](scripts/rag_query.py) (~110 lines). Three design choices worth noting: (a) imports `embed_single` directly from `mychatarchive.embeddings` so the query-side embedder is literally the same Python object as the index-side — no config drift, no model-mismatch class of bugs possible; (b) uses a CTE `WITH hits AS (SELECT chunk_id, distance FROM vec_chunks WHERE embedding MATCH ? AND k = ?)` because sqlite-vec's MATCH clause doesn't compose with JOINs in the same WHERE; (c) resolves vault note paths via `glob(<12char_tid>__*.md)` to match the slug convention from Session 14's `generate_vault.py`.
- Verified mychatarchive's actual embedding config: `sentence-transformers/all-MiniLM-L6-v2`, 384-dim. Not assumed — read from `mychatarchive.config.get_embedding_model()` / `get_embedding_dim()`.
- Ran four probe queries end-to-end against `data/db/archive.db`:
  1. `"concurrency control in payment transactions"` → 5/5 bullseye, distances 0.25–0.28. Top hits: CompletableFuture thread (`17d119b622be`), Concurrency Risks (`0cd59011fd0e`), the famous Concurrency Control in Payments (`7eb1db0f1296` — known from Sessions 09/13), plus a "Hayert" thread I didn't know about (`4c9f6a35df92`, 2024-07-10) which is legitimately about concurrent payment dedup. The 408-chunk ReserveConsumer thread did NOT show up in the top 5 — different vocabulary (reserve / consumer vs payment / concurrency).
  2. `"deciding to leave my job and write resignation letter"` → 4/5 bullseye, distances 0.41–0.56. Top hit is `768f6e83f83d` "CEO Informed About Resignation" (exactly the outlier note we hand-verified in Session 14). Also surfaces the `35c51c36cd02` "Exit Interview: Firm Decision" thread and a `fdc9d9e8f0ff` "Farewell Party Invitation" — all clustered around March 2024, which matches the real timeline.
  3. `"english grammar past perfect tense"` → ~1/5. Returns grammar-adjacent threads ("Prepositions with Dates", "Will do vs will be doing", "English Speaking Test") but no direct past-perfect thread. Two interpretations: no such thread in corpus, or MiniLM is fuzzy on fine-grained grammar subtopic disambiguation. Likely both. This is the PRD's motivating case for FTS5 hybrid search.
  4. `"how do I prepare for a software engineering interview"` → 4/5, distances 0.27–0.38. Ranks 2–5 are all interview-prep threads across different stacks ("Programming Interview Prep", "Payment Gateway Interview Prep", ".NET C# Interview Prep", "Learning Plan and Prioritization"). Rank 1 is "Thank you Response" which is a miss — probably a post-interview thank-you note thread that the embedding couldn't distinguish.
- Updated `docs/STATE.md`: current phase header updated to reflect the Session 15 result, Now queue rewritten to point at Phase 2 wiki compilation design, RAG slice moved to Later as completed, added a Next entry for the FTS5 hybrid follow-up.

**Findings:**
- **Retrieval is load-bearing for concrete-noun queries.** On concurrency/payments, resignation/career, and interview-prep, top-5 hit rates were 4–5/5 and the clusters were tight (distance spread under 0.15 across the top 5). That's more than good enough to justify building Phase 2 wiki compilation on top.
- **Weakness is structural / abstract / category-subtopic queries.** "Past perfect tense" is a 3-word query inside a broader grammar domain. The embedding collapses it toward "english grammar in general" rather than the specific tense. This is textbook MiniLM — dense semantic search is strong on topic, weak on syntactic/categorical precision. It's also exactly the case for which PRD §5 (Phase 5 hybrid) was designed: combine semantic top-k with FTS5 BM25 so that keyword-specific queries ("past perfect") pick up keyword-matching chunks that pure semantic search misses.
- **Date clustering is a free bonus.** For the resignation probe, all 5 hits fell inside a 9-day window in March 2024. We didn't ask for temporal coherence — it emerged because the underlying conversations were contiguous in time. This strongly suggests Phase 5's "timeline" query mode will work without much extra engineering.
- **Model loading dominates wall-clock.** Each `rag_query.py` invocation pays ~4 s loading MiniLM. For a real interactive session we'd want a REPL or a long-lived process. Not worth fixing today.
- Unexpected-key warning from `BertModel LOAD REPORT` (`embeddings.position_ids`) is cosmetic — transformers library version mismatch with the checkpoint. Same warning appears at index time, so query and index see consistent behavior. Ignorable.

**Decisions:**
- See STATE.md Decisions 2026-04-13 Session 15. The headline: shipping retrieval validation *before* Phase 2 wiki compilation is a deliberate reordering of PRD phase numbering, justified by ADR-8's framing of evidence-first retrieval as foundational rather than terminal. The minimal slice is scoped *just* to the "does the semantic layer return real results" question — everything else in PRD Phase 5 (FTS5 hybrid, reranking, context expansion, LLM answer generation, CLI modes, query_log) is a later session.
- Reuse `mychatarchive.embeddings.embed_single` instead of re-instantiating `SentenceTransformer` in the script. One embedder, zero drift. The 3-line import is cheaper and safer than any amount of config discipline.
- Probe queries were chosen across four intentionally different modes (technical-concrete, personal-concrete, structural-abstract, aspirational-abstract) rather than picking only easy queries. Got a pass/fail-per-mode signal out of four runs instead of a single homogeneous "looks fine" impression.
- Did NOT add a `query_log` table or persistent probe-battery script yet. The four probes are reproducible from this log if we need to re-run; making them a first-class regression suite is premature until Phase 5 is actually being built.

**Files touched:**
- `scripts/rag_query.py` (new, ~110 lines)
- `docs/STATE.md` — phase header, Now/Next/Later reshuffled, Session 15 decision added
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- First draft of the SQL joined `vec_chunks` to `chunks` in one WHERE clause with both a `MATCH` predicate and a normal join predicate. sqlite-vec rejects this — its virtual-table MATCH must be isolated. Rewrote as a CTE, worked on first try. Lesson for next time: treat `vec_chunks` like an FTS virtual table — query it alone, JOIN onto it from an outer query.
- Initially considered loading `SentenceTransformer` directly in `rag_query.py` to avoid importing the whole mychatarchive package at query time. Decided against it — the drift risk (someone changes the default model in `mychatarchive.config` and we don't notice) vastly outweighs the ~200 ms import cost.
- Almost forgot to verify the embedding model name before writing the script. If I'd guessed wrong (e.g., `multi-qa-MiniLM` vs `all-MiniLM`) every distance would have been nonsense and the probe results would have looked randomly mediocre instead of clearly working. Lesson: *always* read the config for load-bearing assumptions, never guess.

**Open questions:**
- Should we extend `rag_query.py` with an FTS5 path now (one more afternoon) or bundle it into the eventual Phase 5 work? Argument for now: the past-perfect probe exposed the weakness, fix it while the context is hot. Argument for later: Phase 5 will do it properly with rerank + merge, and a half-hybrid is easy to get wrong. Leaning later, but will let the user decide.
- The ReserveConsumer thread (`135ef7cce3f0`, 408 chunks, recovered in Session 13) did not surface on the concurrency probe. Worth a targeted probe with a more specific query to check whether it's retrievable at all, or whether long code-heavy threads get diluted across too many chunks to rank. If the latter, it's a structural issue we'll need to address in Phase 5 rerank.
- Do we need a real probe battery (a CSV of query → expected-thread-IDs with a top-k recall metric) before Phase 2, or is eyeball-on-demand enough? Probably enough for now; formalize if we re-run this test after changing the embedding stack.

**Next:**
- Phase 2 wiki compilation design session. PRD §6 is the reference. Open questions to resolve before writing code: (a) clustering strategy — reuse `canonical_label` buckets directly, run BERTopic on chunk embeddings, or hand-seed starter clusters for the top 10 `canonical_label` values; (b) L1 identity compile (one document, cheap) vs L2 domain articles first (many documents, expensive but higher-value); (c) Batch API cost ceiling for the first pass — probably cap at the 10 largest canonical buckets so we can iterate on prompts before paying the full-corpus bill.

---

## 2026-04-13 Session 14 — claude-code

**Goal:** Ship the first user-facing artifact — a lightweight Obsidian vault derived from `classifications` + `messages` — so the user can finally *see* what the classification pipeline produced. User explicitly said: "I don't even see what we have done until now, does our rag work ok or it completely mess". Answering the second question is out of scope (retrieval = PRD Phase 5, not started); the first is exactly what a dashboard solves.

**Done:**
- Wrote [scripts/generate_vault.py](scripts/generate_vault.py) (~350 lines). Two-query data load: one GROUP BY over `messages` for per-thread `title`/`first_ts`/`last_ts`/`msg_count`, plus a `ROW_NUMBER() OVER (PARTITION BY canonical_thread_id ORDER BY ts ASC)` window query for the first user message; one GROUP BY over `classifications JOIN chunks` for per-thread labels with `CASE WHEN scheme='key_topic' THEN COALESCE(canonical_label, label) ELSE label END` (per Session 10's design — canonical_label is NULL for non-topic schemes). Python groups into a `{tid: {..., labels: {scheme: [label, ...]}}}` map. No sqlite-vec (no vector queries), no shared DB module extracted (premature abstraction for 2 call sites).
- Generated vault structure: `vault/README.md`, `vault/dashboards/overview-static.md` (pre-rendered Markdown tables, no plugin required), `vault/dashboards/overview-dataview.md` (Dataview queries, requires plugin), `vault/threads/<12char_tid>__<slug>.md` × 934. Thread note bodies are deliberately thin: YAML frontmatter (title, thread_id, date, last_date, message_count, categories, topics, emotions, outcome) + 220-char first-user-message snippet + a ready-to-paste SQL query to pull the full conversation from `archive.db`.
- Added `vault/` to `.gitignore`. Confirmed `git status` shows no vault files.
- Ran on `data/db/archive.db`: **934 thread notes written, ~5 s wall-clock, 3.8 MB total**.
- Spot-checked three notes by hand:
  - `7eb1db0f1296__concurrency-control-in-payments.md` — Session 09's known-loss thread. It's now classified (per Session 11 re-ingest). Frontmatter: 2 categories, 9 topics, 3 emotions, outcome=ongoing. Snippet is the `@Transactional` Java method the user was debugging — matches the title.
  - `768f6e83f83d__ceo-informed-about-resignation.md` — personal/career outlier. 2 categories including `personal/struggles` + `work/career`, 6 topics including `resignation_letter` + `work_burnout`, emotions `anxious, ashamed, exhausted, grateful`, outcome=success. Classification looks coherent.
  - Grammar and concurrency threads appear in expected slug buckets.
- Cross-checked `overview-static.md` against [tag_distribution.py](scripts/tag_distribution.py): top topics `interview_preparation 81 / english_learning 69 / data_structures_algorithms 62 / english_grammar 56` — direction consistent with Session 10's pre-re-import baseline (`english_learning 46 / english_grammar 34`) scaled by the Session 11 +459-thread re-ingest. Dedup SQL pattern is a byte-for-byte copy of tag_distribution's `COUNT(DISTINCT c.canonical_thread_id)`.
- Updated `CLAUDE.md`-visible docs: promoted a "decide next direction" item to `STATE.md → Now` (queue was empty — Session 13's closeout flagged this), updated the stale "Phase 0 — Foundation" header to reflect that ingest/classification are done and we're bridging toward Phase 2, added two Next tasks (BERTopic, RAG minimal slice), moved Obsidian dashboards from Later → completed in Later.

**Findings:**
- Full corpus distribution confirms the picture from Session 08's narrower report: work/technical 40.8%, learning (successful+ongoing) 53.0%, curious 61.6% / frustrated 33.7% / confused 30.5%, success 47.0% / ongoing 42.8%. Outcomes reveal 3 off-taxonomy strays that slipped through prompt-tightening: `successful` (1), `trivial` (77), `unclear` (10), `abandoned` (2). Not worth a re-classification pass — merge at reporting time if ever.
- The forward-slash category format (`work/technical`, `personal/struggles`) survives plain-scalar YAML emission without quoting because `/` is not a YAML indicator — confirmed by reading back a thread note.
- Category `learning/trivial`, `learning/abandoned`, `personal/learning`, `personal/life` etc. are also off-taxonomy strays. Same triage: fold at query time.
- Data shape insight from overview: 400 threads are `outcome=ongoing`. That's 43% — a lot of in-progress work. If we later build a "what's unresolved" dashboard it'll be the biggest surface area.

**Decisions:**
- See STATE.md Session 14 decision (two-query data load, static + dataview dashboards side-by-side, no shared DB helper module, no conversation bodies, vault gitignored, idempotent regenerate).

**Files touched:**
- `scripts/generate_vault.py` (new, ~350 lines)
- `.gitignore` — added `vault/`
- `vault/` — fully generated, gitignored
- `docs/STATE.md` — current phase header rewritten, Now queue repopulated, Session 14 decision added, Obsidian task marked done in Later
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- Initially assumed `7eb1db0f1296` was still the known-loss from Session 09 and mentally prepared to flag it in the vault as an unclassified outlier. It's actually classified (Session 11 re-ingest + Session 13 recipe). Should have re-read the Session 13 closeout first — it explicitly said "0 unclassified threads-with-chunks remaining". Lesson: when a session closeout brags about reaching 100%, trust it.
- Drafted the plan initially with a `scripts/db.py` shared-helper module extraction, then removed it after noticing only 2 scripts would use `connect()`. Would have been premature abstraction.

**Open questions:**
- Which of {BERTopic, RAG minimal slice, Phase 2 wiki compilation} ships next. User said "I leave to you choosing" in this session, but the three have genuinely different value — BERTopic polishes what we have, RAG validates retrieval, Phase 2 compiles wikis. My read: RAG minimal slice has the highest information value because it's the *other* implicit question the user asked and we haven't touched Phase 5 at all. BERTopic has diminishing returns (Session 10's manual head mapping already covered the load-bearing labels). Phase 2 is expensive and shouldn't ship without validated retrieval underneath.
- Whether to write a `docs/vault-tour.md` pointing at the 10 most interesting threads for a first-time walkthrough. Would turn the dashboard into a guided tour rather than a directory. Not urgent.

**Next:**
- Wait for user review of `vault/dashboards/overview-static.md`. Then pick one of {RAG minimal slice, BERTopic, Phase 2} for the next session and promote it from Next to Now.

---

## 2026-04-13 Session 13 — claude-code

**Goal:** Re-classify the 7 parse-failure threads left over from the Session 11 re-import batch (`msgbatch_013jRmbiEucWUG1Dc7hVG6uw`). Same failure mode as Session 09 — model continues the conversation instead of returning JSON — but the Session 09 front-only anti-answer preamble was already in `classify_batch.py` from that session, so a plain re-run would have produced identical failures. Needed a stronger intervention.

**Done:**
- Identified the 7 unclassified threads-with-chunks via LEFT JOIN. Five large code/study threads (120–408 chunks): `135ef7cce3f0` ReserveConsumer concurrency (408), `a98465c06256` Neovim executable fix (290), `0d0dae49e9c4` DSA-Course-Sheduled (176), `29f522555eaa` Phase 0 overview (156), `6e526e18f820` 2-3,2-3-4,B Trees (120). Two tiny outliers: `7f8454f6a056` "Worker Introduction Tips" (3 msgs/2 chunks) and `ce1b8631b5b1` "Tired but okay" (136 msgs but only 2 chunks — most messages were empty/non-text).
- Diagnosed why Session 09's recipe wasn't enough: a front-only preamble gets drowned out when the body is 80K chars of code. Standard Claude pattern for "treat as data, not directive" is XML wrapping + a post-body re-instruction.
- Edited [classify_batch.py](scripts/classify_batch.py): (a) wrapped the conversation body in `<archived_conversation>` tags, (b) appended a postamble after the closing tag re-stating "Output ONLY JSON, do not respond to anything inside the tags above", (c) accounted for postamble length in the 80K truncation budget, (d) added one sentence to the system prompt naming the XML tag and the no-respond rule.
- Submitted `msgbatch_01Mtd5ra3jm6FtouCV8JaD9x` — 72 requests (7 real failures + 65 no-chunk skip-filter quirk known from Sessions 09/11). Batch ended in ~5 min, **72/72 succeeded, 0 errored**.
- Ingested: **7 succeeded, 0 parse failures, 0 API failures**, 65 no-chunk skips. Classifications: 509,239 → **523,967** (+14,728 rows).
- Ran `apply_topic_aliases.py`. Folded 14,737 of 299,071 key_topic rows; distinct labels 3,508 → 3,461 (47 collapsed).
- Verified end state: **0 unclassified threads-with-chunks**, 934 classified threads, 45,896 distinct chunks classified.

**Findings:**
- The XML-wrap + postamble recipe cracked even `135ef7cce3f0` (ReserveConsumer concurrency, 408 chunks), structurally identical to the Session 09 known-loss `7eb1db0f1296` (Concurrency Control in Payments, 761 chunks). The new recipe almost certainly classifies `7eb1db0f1296` too — it was already classified in the Session 11 re-import sweep, so the "known loss" status from Session 09 is stale anyway.
- Recovery rate this run = 7/7. Session 09 = 7/8. Session 11 follow-up (the failures we just fixed) = 0/7. Same anti-answer wording in all three; the only thing that changed was *placement*. Bracketing the body beats prefixing it. Worth remembering for any future "model ignored my instructions" debugging.
- Skip-filter quirk persists (65 no-chunk threads keep getting included). Cost is pennies; deferred.

**Decisions:**
- See STATE.md Decisions 2026-04-13 Session 13. The XML-wrap + postamble recipe stays in `classify_batch.py` as the new default — no downside on successful cases, and it's the only recipe known to work on the long code-heavy threads.

**Files touched:**
- `scripts/classify_batch.py` — XML wrapping + postamble in `cmd_submit`, system-prompt sentence
- `data/db/archive.db` — +14,728 classification rows, +14,737 canonical_label folds (gitignored)
- `docs/STATE.md` — re-classify task closed, Session 13 decision added
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- Initial instinct was to just re-run the existing `classify_batch.py` on the 7 failures. Caught it before submitting — the Session 09 preamble was already in the script, so a re-run would have reproduced identical failures. Lesson: when a "fix from last time" is already in the code and the bug recurs, don't re-apply it, design the next escalation.

**Open questions:**
- Skip-filter quirk: still costing ~65 redundant batch requests on every re-run. Fix if we expect more re-runs; leave otherwise.

**Next:**
- All Phase 0/1 follow-up tasks are now closed. The queue jumps to STATE.md → Later: BERTopic exploration, Obsidian dashboards, or Phase 3 tiered emotion analysis. No strong opinion on ordering yet — depends on what the user wants to see first. BERTopic would clean up the long-tail topic clustering that Session 10 explicitly punted on; Obsidian dashboards would be the first user-facing artifact from the corpus; emotion analysis is the next phase boundary.

---

## 2026-04-13 Session 11 — claude-code

**Goal:** Re-ingest a fresh full ChatGPT export (received from OpenAI, April 2026) on top of existing `archive.db` without losing chunks or classifications. User was worried about duplicates; wanted confirmation that IDs would let us skip previously-ingested content.

**Done:**
- Verified mychatarchive re-import mechanics via Explore subagent reading installed source. Confirmed: `message_id` is SHA1(`platform, account_id, canonical_thread_id, role, rounded_ts, normalized_content`) written via `INSERT OR IGNORE` against a PRIMARY KEY ([ingest.py:110-113](.venv/lib/python3.12/site-packages/mychatarchive/ingest.py#L110-L113), [sqlite.py:204-211](.venv/lib/python3.12/site-packages/mychatarchive/sqlite.py#L204-L211)). `canonical_thread_id` is SHA1(`platform, account, normalized_title, first_msg_ts, first_role, first_msg_snippet`) ([ingest.py:99-106](.venv/lib/python3.12/site-packages/mychatarchive/ingest.py#L99-L106)). `embeddings.run()` skips messages already in `db.embedded_message_ids(con)` ([embeddings.py:57, 81-83](.venv/lib/python3.12/site-packages/mychatarchive/embeddings.py#L57)). Re-import is safe by construction — no custom dedup needed.
- Snapshotted `data/db/archive.db` → `data/db/archive.db.bak-preimport-2026-04-13` (853 MB).
- Recorded pre-import baseline to `/tmp/preimport_baseline.json`: messages=24,240 / threads=540 / chunks=31,007 / chunk-messages=15,844 / classifications=335,322 / classified threads=522 / canonical_label=192,906.
- Inspected new export: 10 shards `conversations-00{0..9}.json` (~130 MB total, 100 convos each, last one 99 = **999 total conversations**). Same JSON shape as old monolithic export (list of conversation dicts). `export_manifest.json` is an index of 6,596 binary attachments (audio/images) — ignored for text ingest.
- Imported all 10 shards via bash loop of `mychatarchive import --format chatgpt --db data/db/archive.db`. Dedup per-shard:
  - 000: 0 inserted / 3,293 dup · 001: 0 / 4,196 · 002: 93 / 8,334 · 003: 1,093 / 2,668 · 004: 4,284 / 189 · 005: 4,343 / 44 · 006: 2,894 / 128 · 007: 2,877 / 179 · 008: 683 / 2,528 · 009: 4 / 3,980
  - Total inserted: **+16,271 messages**
- Ran `mychatarchive embed --db data/db/archive.db` — 50 s wall-clock on CPU. Skipped 32,824 already-embedded; embedded 7,687 new messages → 15,152 new chunks.
- Submitted classify batch `msgbatch_013jRmbiEucWUG1Dc7hVG6uw` with **477 requests** (459 new threads + 17 old no-chunk sweep + 1 known-loss `7eb1db0f1296`). `cmd_submit` skip-filter correctly identified 522 already classified. Batch status at session end: `in_progress`, 0/477 succeeded (submitted ~1 minute before session wind-down).

**Findings:**
- messages: 24,240 → **40,511** (+16,271)
- threads: 540 → **999** (+459 new, **zero ghost threads** from title renames — `canonical_thread_id` was stable for all 540 prior threads)
- chunks: 31,007 → **46,159** (+15,152)
- threads with chunks: 523 → **934** (65 threads have no chunks = short/empty; consistent with prior ~3% no-chunk ratio)
- Shard-level delta pattern was non-uniform: 000/001/009 were almost entirely duplicates; 004/005 were almost entirely new. Suggests the export is sorted by something stable (likely `create_time`) and growth is concentrated in mid-2025 → early-2026.

**Decisions:**
- See STATE.md Decisions 2026-04-13 Session 11 (re-import is safe by mychatarchive's construction; loop over shards; `export_manifest.json` ignored).
- Kept old `conversations.json` (56 MB, Mar 2025) alongside the new shards as provenance — not deleted.
- Did NOT process `export_manifest.json` or any attachments — audio/image analysis is an explicit future phase, out of scope here.

**Files touched:**
- `data/db/archive.db` — +16,271 messages, +15,152 chunks (gitignored)
- `data/db/archive.db.bak-preimport-2026-04-13` — rollback snapshot (gitignored)
- `data/sample/conversations-00{0..9}.json` — new sharded export (gitignored)
- `data/sample/export_manifest.json` — attachment index (gitignored, unused)
- `docs/STATE.md` — Later task added for ingest resume, Session 11 decision added
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- Briefly thought the background poll `--wait` process had silently completed (output file was empty). It hadn't — `poll --wait` has no stdout until the batch ends. Direct API call `messages.batches.retrieve` is the reliable status source, not the poll log.

**Open questions:**
- Whether to fix the `cmd_submit` skip-filter quirk that sweeps no-chunk threads into the "remaining" set — hit it twice now (Sessions 09 + 11). Cost is still pennies per re-run, so low priority.
- Whether to update `tag_distribution.py` to read `canonical_label` instead of `label` before the post-import report (1-line change, deferred since Session 10).

**Next:**
- When batch `msgbatch_013jRmbiEucWUG1Dc7hVG6uw` reaches `ended`:
  1. `python scripts/classify_batch.py ingest --batch-id msgbatch_013jRmbiEucWUG1Dc7hVG6uw`
  2. `python scripts/apply_topic_aliases.py --db data/db/archive.db`
  3. Re-run the baseline count query and diff against `/tmp/preimport_baseline.json`
  4. Close Session 11 Later task, append delta numbers to this entry (or open Session 12 for clarity)

---

## 2026-04-13 Session 10 — claude-code

**Goal:** Topic normalization pass — collapse near-duplicate `key_topic` labels so the top of the distribution is readable for reporting.

**Done:**
- Added migration `scripts/migrations/0002_canonical_label.sql` introducing `canonical_label TEXT` on `classifications` (+ index on `(scheme, canonical_label)`). Applied to `data/db/archive.db`.
- Wrote `scripts/topic_inspect.py` — conversation-level frequency report for a given scheme. Confirmed scale: 2,076 distinct `key_topic` labels, 1,772 singletons (85%), 2,743 total conv-hits. Long tail is huge and dominated by unique labels that edit distance can't help with.
- Drafted `scripts/topic_aliases.py` as a plain Python dict of `canonical_label -> [raw variants]`. Hand-reviewed the top ~250 labels and built 22 clusters covering 69 raw labels. Deliberately conservative: grammar subtopics (tenses, modals, conditionals) stay distinct from `english_grammar`; `burnout_recovery` vs `burnout_prevention` stay split; `memory_*` left alone because `memory_techniques` is a different domain than `memory_management`.
- User reviewed the draft and approved as-is.
- Wrote `scripts/apply_topic_aliases.py` — dry-run + apply modes, idempotent, writes `canonical_label = reverse.get(label, label)` for every `scheme='key_topic'` row. Ran dry-run first, then applied.

**Findings:**
- 12,558 of 192,906 key_topic rows got folded (6.5%); 180,348 passed through unchanged.
- Distinct canonical labels: 2,029 (was 2,076) — 47 labels collapsed. 0 NULL canonical_label rows for key_topic.
- Top distribution after normalization:
  - `english_learning` 12 → 46
  - `english_grammar` 21 → 34
  - `data_structures_algorithms` 10 → 30
  - `entity_framework_core` 10 → 25
  - `clickhouse` 11 → 22
  - `microservices` 9 → 18
  - `interview_preparation` 13 → 17
- The English/grammar/data-structures signal was badly fragmented in the raw labels; the normalized head now tells a much clearer story about what Hayk actually talks about at volume.
- 1,772 singletons unchanged — that's expected. BERTopic on chunk text is the right tool for the tail, not label-string clustering.

**Decisions:**
- `canonical_label` column (not in-place rewrite). Keeps raw model output as source of truth; mapping is reversible without re-classification.
- Mapping lives as a Python dict, not YAML — avoids a dependency, supports inline comments, trivial to edit.
- Only `scheme='key_topic'` gets `canonical_label` populated in this pass. Other schemes (category, emotion, outcome) have their own, smaller cleanup problems and are left with NULL for now.
- Reports wanting normalized topics should `SELECT canonical_label WHERE scheme='key_topic'` directly — no COALESCE needed because the apply script populated it for all key_topic rows.

**Files touched:**
- `scripts/migrations/0002_canonical_label.sql` (new)
- `scripts/topic_inspect.py` (new)
- `scripts/topic_aliases.py` (new)
- `scripts/apply_topic_aliases.py` (new)
- `data/db/archive.db` — column added, 192,906 rows updated; gitignored
- `docs/STATE.md` — task closed, decision added
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- Earlier in the planning I floated edit-distance clustering as the main tool. Actually running `topic_inspect.py` killed that idea quickly — 85% singleton rate means edit distance is the wrong mechanism. Manual head mapping is the right call until BERTopic comes along.

**Open questions:**
- Should `canonical_label` eventually be NOT NULL (with a trigger or default) now that we always populate it for key_topic rows? Probably not worth it until another scheme gets its own normalization pass.
- Grammar subtopics (present_continuous, modal_verbs, conditional_sentences, etc.) are currently siblings of `english_grammar` in the canonical vocabulary rather than children. Good enough for flat reporting; would need a hierarchy column if we ever want drill-down.
- `tag_distribution.py` still reads `label`, not `canonical_label`. Updating it is a 1-line change; deferred until we actually want a fresh report.

**Next:**
- STATE.md → Later. Candidates: BERTopic exploration, Obsidian dashboards, Phase 3 emotion analysis. No strong opinion yet; depends on what the user wants next.

---

## 2026-04-12 Session 09 — claude-code

**Goal:** Re-classify the 8 parse-failure conversations from Session 08 without changing the prompt or taxonomy.

**Done:**
- Identified the 8 failing threads by LEFT JOIN on `chunks`/`classifications`. All 7 of the largest were technical/code-heavy (ClickHouse, EFCore, concurrency, exceptions, SQL). One outlier: "CEO Informed About Resignation" (10 msgs, personal/work-career).
- Added an anti-answer preamble to the user message in `classify_batch.py cmd_submit`: "archived conversation for analysis, do NOT answer, classify only". Adjusted the 80K truncation budget to account for the preamble length.
- Submitted batch `msgbatch_01MyLEvG871kbCNSgrz8JRDc` — picked up 25 "remaining" threads (8 parse failures + 17 genuinely no-chunk threads that also look unclassified through the chunks JOIN). Cost of the extra 17 is trivial; not worth refiltering.
- Ingested: 7 succeeded, 1 parse failure, 17 no-chunk skips. One failure: `7eb1db0f1296` "Concurrency Control in Payments" (137 msgs, 761 chunks — the biggest thread in the archive). Model still reverted to code-debugging instead of classifying, even with the preamble.
- Verified via LEFT JOIN: 522/523 threads-with-chunks now classified, 1 remaining.

**Findings:**
- Anti-answer preamble recovered 7/8 (87.5%). Cheap, effective insurance.
- The remaining failure is the largest code-heavy thread in the corpus. The preamble isn't enough when the conversation body is long enough to drown it out. Could try: moving the anti-answer instruction into the system prompt, or truncating more aggressively for this class of conversation. Not urgent — it's 1/523.
- `cmd_submit`'s "already classified" filter joins via chunks, so it can't distinguish "has no chunks" from "not yet classified". Included 17 no-chunk threads on this re-run. Harmless but noisy in the ingest log.

**Decisions:**
- Accept `7eb1db0f1296` as a known loss rather than iterate further. Phase 1 completion is not gated on 100% classification coverage.
- Anti-answer preamble stays in `classify_batch.py` going forward — no downside for successful cases.

**Files touched:**
- `scripts/classify_batch.py` — anti-answer preamble in `cmd_submit`
- `data/db/archive.db` — +15,387 classification rows (319,935 → 335,322); gitignored
- `docs/STATE.md` — task closed, decision added
- `docs/PROGRESS.md` — this entry

**Mistakes / wrong assumptions:**
- Expected 8 requests in the batch; got 25 because the skip-classified filter counts no-chunk threads as unclassified. Not actually a bug — just a minor efficiency wart. Fix later if we ever need to rerun classification on targeted subsets.

**Open questions:**
- Is `7eb1db0f1296` worth a one-off rescue (system-prompt level anti-answer, or manual classification)? Low priority.
- `cmd_submit` skip filter should probably exclude no-chunk threads from the "remaining" set so reruns stay tight. Minor cleanup.

**Next:**
- Topic normalization pass (STATE.md → Later). That was the recommended next step before this session; nothing has changed.

---

## 2026-04-12 Session 08 — claude-code

**Goal:** Ingest Batch API classification results and run full-corpus tag distribution report.

**Done:**
- Polled batch `msgbatch_01V4QaM15kUoCU23oWnLSU4j` — status `ended`, 540/540 succeeded at the API level.
- Ran `python scripts/classify_batch.py ingest --batch-id msgbatch_01V4QaM15kUoCU23oWnLSU4j`: 515 ingested, 8 parse failures, 17 skipped (no chunks). 319,935 rows written to `classifications` table.
- Ran `python scripts/tag_distribution.py --db data/db/archive.db` — full-corpus distribution report.

**Findings — full-corpus tag distribution (515 conversations):**
- **Categories:** `work/technical` 45.2%, `learning/ongoing` 22.7%, `learning/successful` 18.6%, `work/crm` 10.9%, `personal/struggles` 7.6%, `meta/planning` 6.8%, `personal/philosophy` 6.2%. Some off-taxonomy categories leaked (7 singletons like `personal/curiosity`, `personal/tech_preferences`).
- **Emotions:** `curious` 53.6%, `frustrated` 36.1%, `confused` 26.8%, `hopeful` 10.5%, `anxious` 8.2%. Blocklisted terms still leak: `focused` (24), `engaged` (10), `determined` (7), `analytical` (2).
- **Topics:** 500+ distinct topics, heavy long-tail fragmentation. Top: `english_grammar` (21), `data_structures` (20), `time_management` (14), `entity_framework` (13), `interview_preparation` (13). Many near-duplicates (e.g., `english_grammar`/`english_learning`/`english_practice`/`english_fluency`/`english_language_learning`).
- **Outcomes:** `ongoing` 43.7%, `success` 42.7%, `trivial` 11.3%, `unclear` 1.2%, `failure` 0.8%, `abandoned` 0.4%.
- **Parse failures (8):** Model returned conversation content (code snippets, explanations) instead of JSON classification. Affected conversations had heavy code content that confused the model into "answering" rather than classifying.

**Decisions:**
- Added "re-classify 8 parse-failure conversations" and "topic normalization pass" to Later queue — not blocking for Phase 1 completion.
- 17 no-chunk conversations are genuinely empty/very short — confirmed from Session 07 embedding step, not a bug.

**Files touched:**
- `data/db/archive.db` (319,935 rows inserted into `classifications`; gitignored)
- `docs/STATE.md` (task checked off, decision added, Later queue updated)
- `docs/PROGRESS.md` (this entry)

**Mistakes / wrong assumptions:**
- None this session. Ingest and report ran cleanly.

**Open questions:**
- Topic normalization: manual mapping table vs automated clustering (BERTopic on topic strings, or simple edit-distance dedup)? BERTopic is already in the Later queue for chunk-level topic discovery — could fold topic-string dedup into that step.
- Off-taxonomy categories (7 singletons): post-process to remap, or re-prompt? Low impact at 0.2% each.

**Next:**
- Pick next item from Later queue. Candidates: topic normalization, BERTopic exploration, Obsidian dashboards, Phase 3 emotion analysis.

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
