"""Generate a read-only Obsidian vault from classifications + messages.

Writes:
    vault/
        README.md
        dashboards/
            overview-static.md       # pre-rendered tables, no plugin needed
            overview-dataview.md     # Dataview queries
        threads/
            <12char_tid>__<slug>.md  # one per classified thread

This is a visibility-only dashboard. Bodies are deliberately thin — the source
of truth is archive.db. For the first-user-message snippet only.

Usage:
    python scripts/generate_vault.py [--db data/db/archive.db] [--vault vault/]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

DEFAULT_DB = Path("data/db/archive.db")
DEFAULT_VAULT = Path("vault")

SNIPPET_LEN = 220
SLUG_LEN = 60
TOP_TOPICS = 30
TOP_EMOTIONS = 20
RECENT_THREADS = 20


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def slugify(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:SLUG_LEN] or "untitled"


def short_tid(tid: str) -> str:
    return tid[:12]


def yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    escaped = [f'"{s}"' if any(c in s for c in ' :,[]#"\'') else s for s in items]
    return "[" + ", ".join(escaped) + "]"


def yaml_str(text: str) -> str:
    if text is None:
        return '""'
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def truncate_utf8(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    return text[:n].rstrip() + "…"


# ---------------- data loading ----------------


def load_threads(con: sqlite3.Connection) -> dict[str, dict]:
    """One row per classified thread, keyed by canonical_thread_id."""
    rows = con.execute(
        """
        SELECT
            m.canonical_thread_id AS tid,
            MAX(m.title)          AS title,
            MIN(m.ts)             AS first_ts,
            MAX(m.ts)             AS last_ts,
            COUNT(*)              AS msg_count
        FROM messages m
        WHERE m.canonical_thread_id IN (
            SELECT DISTINCT c.canonical_thread_id
            FROM chunks c
            JOIN classifications cl ON cl.chunk_id = c.chunk_id
        )
        GROUP BY m.canonical_thread_id
        """
    ).fetchall()

    threads: dict[str, dict] = {}
    for r in rows:
        threads[r["tid"]] = {
            "tid": r["tid"],
            "title": r["title"] or r["tid"][:12],
            "first_ts": r["first_ts"],
            "last_ts": r["last_ts"],
            "msg_count": r["msg_count"],
            "first_user_text": "",
            "labels": defaultdict(list),  # scheme -> [label, ...]
        }

    # first user message per thread via window function
    first_user = con.execute(
        """
        SELECT tid, text FROM (
            SELECT
                canonical_thread_id AS tid,
                text,
                ROW_NUMBER() OVER (PARTITION BY canonical_thread_id ORDER BY ts ASC) AS rn
            FROM messages
            WHERE role = 'user' AND text IS NOT NULL AND text != ''
        )
        WHERE rn = 1
        """
    ).fetchall()
    for r in first_user:
        if r["tid"] in threads:
            threads[r["tid"]]["first_user_text"] = r["text"] or ""

    # all labels, already deduped per (thread, scheme, label_resolved)
    labels = con.execute(
        """
        SELECT
            c.canonical_thread_id AS tid,
            cl.scheme,
            CASE WHEN cl.scheme = 'key_topic'
                 THEN COALESCE(cl.canonical_label, cl.label)
                 ELSE cl.label
            END AS label,
            MAX(cl.confidence) AS confidence
        FROM classifications cl
        JOIN chunks c ON c.chunk_id = cl.chunk_id
        GROUP BY c.canonical_thread_id, cl.scheme,
                 CASE WHEN cl.scheme = 'key_topic'
                      THEN COALESCE(cl.canonical_label, cl.label)
                      ELSE cl.label
                 END
        """
    ).fetchall()
    for r in labels:
        t = threads.get(r["tid"])
        if t:
            t["labels"][r["scheme"]].append(r["label"])

    for t in threads.values():
        for scheme in t["labels"]:
            t["labels"][scheme].sort()

    return threads


def load_stats(con: sqlite3.Connection) -> dict:
    total_threads = con.execute(
        """
        SELECT COUNT(DISTINCT c.canonical_thread_id)
        FROM chunks c JOIN classifications cl ON cl.chunk_id = c.chunk_id
        """
    ).fetchone()[0]

    def dist(scheme: str, use_canonical: bool) -> list[sqlite3.Row]:
        label_expr = (
            "COALESCE(cl.canonical_label, cl.label)" if use_canonical else "cl.label"
        )
        return con.execute(
            f"""
            SELECT {label_expr} AS label,
                   COUNT(DISTINCT c.canonical_thread_id) AS n
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
            WHERE cl.scheme = ?
            GROUP BY {label_expr}
            ORDER BY n DESC, label
            """,
            (scheme,),
        ).fetchall()

    topics = dist("key_topic", use_canonical=True)
    categories = dist("category", use_canonical=False)
    outcomes = dist("outcome", use_canonical=False)

    emotions = con.execute(
        """
        SELECT cl.label AS label,
               COUNT(DISTINCT c.canonical_thread_id) AS n,
               ROUND(AVG(cl.confidence), 2) AS avg_intensity
        FROM classifications cl
        JOIN chunks c ON c.chunk_id = cl.chunk_id
        WHERE cl.scheme = 'emotion'
        GROUP BY cl.label
        ORDER BY n DESC, label
        """
    ).fetchall()

    corpus = con.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM messages)                              AS messages,
            (SELECT COUNT(DISTINCT canonical_thread_id) FROM messages)   AS threads,
            (SELECT COUNT(*) FROM chunks)                                AS chunks,
            (SELECT COUNT(*) FROM classifications)                       AS classifications
        """
    ).fetchone()

    return {
        "total_threads": total_threads,
        "topics": topics,
        "categories": categories,
        "outcomes": outcomes,
        "emotions": emotions,
        "corpus": corpus,
    }


# ---------------- writers ----------------


def thread_filename(t: dict) -> str:
    return f"{short_tid(t['tid'])}__{slugify(t['title'])}.md"


def thread_relpath(t: dict) -> str:
    return f"threads/{thread_filename(t)}"


def write_thread_note(path: Path, t: dict) -> None:
    first_date = (t["first_ts"] or "")[:10]
    last_date = (t["last_ts"] or "")[:10]
    categories = t["labels"].get("category", [])
    topics = t["labels"].get("key_topic", [])
    emotions = t["labels"].get("emotion", [])
    outcomes = t["labels"].get("outcome", [])
    outcome = outcomes[0] if outcomes else ""

    snippet = truncate_utf8(t["first_user_text"].strip(), SNIPPET_LEN) if t["first_user_text"] else ""
    snippet_quoted = "\n".join(f"> {line}" for line in snippet.splitlines()) if snippet else "> *(no user message)*"

    body = f"""---
title: {yaml_str(t['title'])}
thread_id: {t['tid']}
date: {first_date}
last_date: {last_date}
message_count: {t['msg_count']}
categories: {yaml_list(categories)}
topics: {yaml_list(topics)}
emotions: {yaml_list(emotions)}
outcome: {yaml_str(outcome)}
---

# {t['title']}

**Thread:** `{t['tid']}`
**Dates:** {first_date} → {last_date}
**Messages:** {t['msg_count']}

## First user message

{snippet_quoted}

---

*Full conversation is stored in `data/db/archive.db`. Query with:*

```sql
SELECT role, ts, text
FROM messages
WHERE canonical_thread_id = '{t['tid']}'
ORDER BY ts ASC;
```
"""
    path.write_text(body, encoding="utf-8")


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{n / total * 100:.1f}%"


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        lines.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(lines)


def write_static_overview(path: Path, stats: dict, threads: dict[str, dict]) -> None:
    total = stats["total_threads"]
    corpus = stats["corpus"]

    lines: list[str] = []
    lines.append("# Overview (static)\n")
    lines.append(
        "Pre-rendered classification dashboard. Works in any Markdown viewer — "
        "no plugins required. Regenerate with `python scripts/generate_vault.py`.\n"
    )

    lines.append("## Corpus\n")
    lines.append(
        md_table(
            ["metric", "value"],
            [
                ["messages", corpus["messages"]],
                ["threads (all)", corpus["threads"]],
                ["threads classified", total],
                ["chunks", corpus["chunks"]],
                ["classification rows", corpus["classifications"]],
            ],
        )
        + "\n"
    )

    lines.append(f"## Top {TOP_TOPICS} canonical topics\n")
    topic_rows = [
        [r["label"], r["n"], pct(r["n"], total)] for r in stats["topics"][:TOP_TOPICS]
    ]
    lines.append(md_table(["topic", "threads", "share"], topic_rows) + "\n")

    lines.append("## Categories\n")
    cat_rows = [[r["label"], r["n"], pct(r["n"], total)] for r in stats["categories"]]
    lines.append(md_table(["category", "threads", "share"], cat_rows) + "\n")

    lines.append(f"## Top {TOP_EMOTIONS} emotions\n")
    emo_rows = [
        [
            r["label"],
            r["n"],
            pct(r["n"], total),
            r["avg_intensity"] if r["avg_intensity"] is not None else "—",
        ]
        for r in stats["emotions"][:TOP_EMOTIONS]
    ]
    lines.append(
        md_table(["emotion", "threads", "share", "avg intensity"], emo_rows) + "\n"
    )

    lines.append("## Outcomes\n")
    out_rows = [[r["label"], r["n"], pct(r["n"], total)] for r in stats["outcomes"]]
    lines.append(md_table(["outcome", "threads", "share"], out_rows) + "\n")

    lines.append(f"## {RECENT_THREADS} most recent threads\n")
    recent = sorted(
        threads.values(), key=lambda t: t["last_ts"] or "", reverse=True
    )[:RECENT_THREADS]
    recent_rows = []
    for t in recent:
        link = f"[[{thread_filename(t).removesuffix('.md')}]]"
        recent_rows.append([(t["last_ts"] or "")[:10], link, t["msg_count"]])
    lines.append(md_table(["date", "thread", "msgs"], recent_rows) + "\n")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_dataview_overview(path: Path) -> None:
    body = """# Overview (Dataview)

Requires the [Dataview](https://github.com/blacksmithgu/obsidian-dataview) plugin.
If you see raw code blocks instead of tables, install Dataview and reload.

## Threads by category

```dataview
TABLE length(rows) AS threads
FROM "threads"
FLATTEN categories AS category
GROUP BY category
SORT length(rows) DESC
```

## Active / unresolved threads

```dataview
TABLE date, message_count, topics
FROM "threads"
WHERE outcome != "success" AND outcome != "trivial"
SORT date DESC
LIMIT 40
```

## Top topics (flattened)

```dataview
TABLE length(rows) AS threads
FROM "threads"
FLATTEN topics AS topic
GROUP BY topic
SORT length(rows) DESC
LIMIT 40
```

## Most recent threads

```dataview
TABLE date, categories, outcome, message_count
FROM "threads"
SORT date DESC
LIMIT 30
```

## Long conversations (50+ messages)

```dataview
TABLE date, message_count, topics
FROM "threads"
WHERE message_count >= 50
SORT message_count DESC
LIMIT 30
```
"""
    path.write_text(body, encoding="utf-8")


def write_readme(path: Path, thread_count: int) -> None:
    body = f"""# selfanalisis vault

Generated read-only Obsidian vault for classification visibility. **Do not edit by hand** — regenerate with:

```bash
python scripts/generate_vault.py --db data/db/archive.db --vault vault/
```

## Contents

- `dashboards/overview-static.md` — pre-rendered tables, works without plugins.
- `dashboards/overview-dataview.md` — richer queries, requires the Dataview plugin.
- `threads/` — {thread_count} per-thread notes with YAML frontmatter (title, date, categories, topics, emotions, outcome, message_count). Bodies contain only the first user-message snippet; the full conversation lives in `data/db/archive.db`.

## Opening in Obsidian

1. Obsidian → *Open folder as vault* → select this `vault/` directory.
2. Optional (for the Dataview dashboard): Settings → Community plugins → Browse → search **Dataview** → install + enable.
3. Open `dashboards/overview-static.md` first — it works immediately.

## Why this vault is thin

This is a read-only view of what the classification pipeline produced. It
deliberately does **not** contain full conversation bodies, wiki articles,
change-points, or entity notes — those belong to later PRD phases. The goal is
one thing only: let you see whether the classifications look sensible.

## Regenerating

Re-running the script fully overwrites existing files. Safe and idempotent.
"""
    path.write_text(body, encoding="utf-8")


# ---------------- main ----------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"ERROR: DB not found at {args.db}")

    args.vault.mkdir(parents=True, exist_ok=True)
    (args.vault / "threads").mkdir(exist_ok=True)
    (args.vault / "dashboards").mkdir(exist_ok=True)

    con = connect(args.db)
    try:
        print(f"Loading threads from {args.db}…")
        threads = load_threads(con)
        print(f"  {len(threads)} classified threads")

        print("Computing distributions…")
        stats = load_stats(con)

        print(f"Writing {len(threads)} thread notes…")
        for t in threads.values():
            write_thread_note(args.vault / "threads" / thread_filename(t), t)

        print("Writing dashboards…")
        write_static_overview(args.vault / "dashboards" / "overview-static.md", stats, threads)
        write_dataview_overview(args.vault / "dashboards" / "overview-dataview.md")
        write_readme(args.vault / "README.md", len(threads))
    finally:
        con.close()

    print(f"Done. Vault at {args.vault.resolve()}")


if __name__ == "__main__":
    main()
