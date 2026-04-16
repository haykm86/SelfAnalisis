"""Prepare compile-ready input bundles for Phase 2 wiki articles.

Does NOT call any LLM. Pure data assembly:
    --list             inspect canonical topics (thread/msg/char counts)
    --topic NAME --out assemble one bundle file for in-session compilation

The companion compile step happens in Claude Code reading the bundle +
prompts/wiki_compile.md, per /home/haykm/.claude/plans/shimmering-meandering-rivest.md.

Usage:
    python scripts/compile_wiki_input.py --list
    python scripts/compile_wiki_input.py --topic interview_preparation --out /tmp/wiki_interview.txt
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path("data/db/archive.db")
CHAR_CAP = 150_000
DEFAULT_THREAD_CHARS = 2500
DEFAULT_MIN_THREADS = 5
KEEP_ROLES = ("user", "assistant")


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def list_topics(con: sqlite3.Connection, min_threads: int) -> list[sqlite3.Row]:
    return con.execute(
        """
        WITH topic_threads AS (
            SELECT DISTINCT
                COALESCE(cl.canonical_label, cl.label) AS topic,
                c.canonical_thread_id AS tid
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
            WHERE cl.scheme = 'key_topic'
        ),
        topic_stats AS (
            SELECT
                tt.topic,
                COUNT(DISTINCT tt.tid) AS threads,
                SUM((SELECT COUNT(*) FROM messages m
                      WHERE m.canonical_thread_id = tt.tid
                        AND m.role IN ('user', 'assistant'))) AS messages,
                SUM((SELECT SUM(LENGTH(COALESCE(m.text, ''))) FROM messages m
                      WHERE m.canonical_thread_id = tt.tid
                        AND m.role IN ('user', 'assistant'))) AS chars
            FROM topic_threads tt
            GROUP BY tt.topic
        )
        SELECT topic, threads, messages, chars
        FROM topic_stats
        WHERE threads >= ?
        ORDER BY threads DESC, chars DESC
        """,
        (min_threads,),
    ).fetchall()


def threads_for_topic(con: sqlite3.Connection, topic: str) -> list[sqlite3.Row]:
    return con.execute(
        """
        WITH topic_threads AS (
            SELECT DISTINCT c.canonical_thread_id AS tid
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
            WHERE cl.scheme = 'key_topic'
              AND COALESCE(cl.canonical_label, cl.label) = ?
        )
        SELECT
            tt.tid,
            MAX(m.title) AS title,
            MIN(m.ts)    AS first_ts,
            MAX(m.ts)    AS last_ts,
            COUNT(*)     AS msg_count
        FROM topic_threads tt
        JOIN messages m ON m.canonical_thread_id = tt.tid
        GROUP BY tt.tid
        ORDER BY first_ts ASC
        """,
        (topic,),
    ).fetchall()


def messages_for_thread(con: sqlite3.Connection, tid: str) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT role, ts, text
        FROM messages
        WHERE canonical_thread_id = ?
          AND text IS NOT NULL AND text != ''
          AND role IN ('user', 'assistant')
        ORDER BY ts ASC
        """,
        (tid,),
    ).fetchall()


def cmd_list(con: sqlite3.Connection, min_threads: int, thread_chars: int) -> None:
    rows = list_topics(con, min_threads)
    total = len(rows)
    print(f"{total} topics with ≥ {min_threads} threads (ordered by thread count, desc)\n")
    print(
        f"{'topic':<40} {'threads':>8} {'msgs':>8} {'raw_chars':>12} "
        f"{'est_budget':>11} {'fits?':>6}"
    )
    print("-" * 92)
    for r in rows:
        est = r["threads"] * thread_chars
        fits = "yes" if est <= CHAR_CAP else "NO"
        print(
            f"{r['topic']:<40} {r['threads']:>8} {r['messages']:>8} "
            f"{r['chars'] or 0:>12,} {est:>11,} {fits:>6}"
        )
    print(
        f"\nCHAR_CAP = {CHAR_CAP:,} | per-thread budget = {thread_chars:,} chars "
        f"(user+assistant only)"
    )
    print("est_budget = threads × per-thread budget; raw_chars is full body before truncation")


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …[truncated]"


def build_bundle(
    con: sqlite3.Connection, topic: str, thread_chars: int
) -> tuple[str, dict[str, object]]:
    threads = threads_for_topic(con, topic)
    if not threads:
        raise ValueError(f"no threads for topic {topic!r}")

    blocks: list[str] = []
    included_threads: list[sqlite3.Row] = []
    included_thread_ids: list[str] = []
    dropped_thread_ids: list[str] = []

    for t in threads:
        short_tid = t["tid"][:12]
        header = f"### [{short_tid}] {t['title'] or '(untitled)'} ({(t['first_ts'] or '')[:10]})"

        msgs = messages_for_thread(con, t["tid"])
        per_thread_body: list[str] = [header]
        budget = thread_chars
        for m in msgs:
            if budget <= 0:
                break
            snippet = truncate(m["text"], budget)
            per_thread_body.append(f"**{m['role']}:** {snippet}")
            budget -= len(snippet)
        per_thread_body.append("---")
        block = "\n\n".join(per_thread_body) + "\n\n"

        blocks.append(block)
        included_threads.append(t)
        included_thread_ids.append(t["tid"])

    header_parts: list[str] = []
    while True:
        if not included_threads:
            raise ValueError(
                f"topic {topic!r} does not fit under the {CHAR_CAP:,} char cap "
                f"with {thread_chars:,} chars per thread"
            )

        time_span = (
            f"{(included_threads[0]['first_ts'] or '')[:10]} → "
            f"{(included_threads[-1]['last_ts'] or '')[:10]}"
        )
        header_parts = [
            f"# Wiki compile input: {topic}",
            f"Threads in topic: {len(threads)}",
            f"Threads included: {len(included_threads)}",
            f"Time span: {time_span}",
            f"Per-thread char budget: {thread_chars:,} (user+assistant only, truncated)",
            "",
            "---",
            "",
        ]
        body = "\n".join(header_parts + blocks[: len(included_threads)])
        if len(body) <= CHAR_CAP:
            metadata = {
                "topic": topic,
                "thread_count": len(included_threads),
                "total_threads": len(threads),
                "time_span": time_span,
                "thread_chars": thread_chars,
                "source_thread_ids": included_thread_ids.copy(),
                "dropped_thread_ids": dropped_thread_ids.copy(),
                "char_count": len(body),
            }
            return body, metadata

        dropped = included_threads.pop()
        included_thread_ids.pop()
        dropped_thread_ids.insert(0, dropped["tid"])


def cmd_bundle(
    con: sqlite3.Connection, topic: str, out_path: Path, thread_chars: int
) -> None:
    try:
        bundle_text, metadata = build_bundle(con, topic, thread_chars)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(bundle_text, encoding="utf-8")

    print(f"Wrote {out_path} ({metadata['char_count']:,} chars)")
    print(f"Included: {metadata['thread_count']}/{metadata['total_threads']} threads")
    dropped = metadata["dropped_thread_ids"]
    if dropped:
        print(f"Dropped (over {CHAR_CAP:,} char cap): {len(dropped)} threads")
        print(
            "  " + ", ".join(thread_id[:12] for thread_id in dropped)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--list", action="store_true", help="List canonical topics with counts")
    parser.add_argument("--topic", type=str, help="Canonical topic to bundle")
    parser.add_argument("--out", type=Path, help="Output path for --topic bundle")
    parser.add_argument(
        "--min-threads",
        type=int,
        default=DEFAULT_MIN_THREADS,
        help=f"Min threads per topic for --list (default {DEFAULT_MIN_THREADS})",
    )
    parser.add_argument(
        "--thread-chars",
        type=int,
        default=DEFAULT_THREAD_CHARS,
        help=f"Per-thread char budget (default {DEFAULT_THREAD_CHARS})",
    )
    args = parser.parse_args()

    if not args.db.exists():
        print(f"DB not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    if not args.list and not args.topic:
        parser.error("one of --list or --topic is required")
    if args.topic and not args.out:
        parser.error("--topic requires --out")

    con = connect(args.db)
    try:
        if args.list:
            cmd_list(con, args.min_threads, args.thread_chars)
        else:
            cmd_bundle(con, args.topic, args.out, args.thread_chars)
    finally:
        con.close()


if __name__ == "__main__":
    main()
