"""Report on classification tag distribution at the conversation level.

Deduplicates the chunk fan-out by grouping on (canonical_thread_id, scheme, label).

Usage:
    python scripts/tag_distribution.py [--db DB_PATH]
"""

import argparse
import sqlite3
from pathlib import Path

DEFAULT_DB = Path("data/db/archive-tiny.db")


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def report(con: sqlite3.Connection) -> None:
    # Total conversations and chunks with classifications
    stats = con.execute("""
        SELECT
            COUNT(DISTINCT c.canonical_thread_id) AS threads,
            COUNT(DISTINCT cl.chunk_id) AS chunks,
            COUNT(*) AS total_rows
        FROM classifications cl
        JOIN chunks c ON c.chunk_id = cl.chunk_id
    """).fetchone()
    print(f"Classified conversations: {stats['threads']}")
    print(f"Classified chunks:        {stats['chunks']}")
    print(f"Total classification rows: {stats['total_rows']}")

    # Conversation-level label distribution per scheme
    schemes = con.execute("""
        SELECT DISTINCT scheme FROM classifications ORDER BY scheme
    """).fetchall()

    for s in schemes:
        scheme = s["scheme"]
        print(f"\n{'=' * 50}")
        print(f"  [{scheme}]")
        print(f"{'=' * 50}")

        rows = con.execute("""
            SELECT
                cl.label,
                COUNT(DISTINCT c.canonical_thread_id) AS conv_count
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
            WHERE cl.scheme = ?
            GROUP BY cl.label
            ORDER BY conv_count DESC, cl.label
        """, (scheme,)).fetchall()

        total_convs = stats["threads"]
        for r in rows:
            pct = r["conv_count"] / total_convs * 100
            bar = "#" * int(pct / 5)
            print(f"    {r['label']:40s}  {r['conv_count']:2d}/{total_convs}  ({pct:5.1f}%)  {bar}")

    # Co-occurrence: how many conversations have >1 category?
    print(f"\n{'=' * 50}")
    print("  [category co-occurrence]")
    print(f"{'=' * 50}")
    cooccur = con.execute("""
        SELECT
            n_cats,
            COUNT(*) AS conv_count
        FROM (
            SELECT
                c.canonical_thread_id,
                COUNT(DISTINCT cl.label) AS n_cats
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
            WHERE cl.scheme = 'category'
            GROUP BY c.canonical_thread_id
        )
        GROUP BY n_cats
        ORDER BY n_cats
    """).fetchall()
    for r in cooccur:
        print(f"    {r['n_cats']} categories: {r['conv_count']} conversations")

    # Emotion intensity summary (conversation-level: avg intensity per emotion)
    print(f"\n{'=' * 50}")
    print("  [emotion intensity — conversation-level avg]")
    print(f"{'=' * 50}")
    emotions = con.execute("""
        SELECT
            cl.label AS emotion,
            COUNT(DISTINCT c.canonical_thread_id) AS conv_count,
            ROUND(AVG(cl.confidence), 2) AS avg_intensity
        FROM classifications cl
        JOIN chunks c ON c.chunk_id = cl.chunk_id
        WHERE cl.scheme = 'emotion'
        GROUP BY cl.label
        ORDER BY avg_intensity DESC, cl.label
    """).fetchall()
    for r in emotions:
        intensity = r["avg_intensity"] if r["avg_intensity"] is not None else "N/A"
        print(f"    {r['emotion']:30s}  convs: {r['conv_count']:2d}  avg_intensity: {intensity}")

    # Outcome distribution
    print(f"\n{'=' * 50}")
    print("  [outcome distribution]")
    print(f"{'=' * 50}")
    outcomes = con.execute("""
        SELECT
            cl.label,
            COUNT(DISTINCT c.canonical_thread_id) AS conv_count
        FROM classifications cl
        JOIN chunks c ON c.chunk_id = cl.chunk_id
        WHERE cl.scheme = 'outcome'
        GROUP BY cl.label
        ORDER BY conv_count DESC
    """).fetchall()
    total_convs = stats["threads"]
    for r in outcomes:
        pct = r["conv_count"] / total_convs * 100
        print(f"    {r['label']:20s}  {r['conv_count']:2d}/{total_convs}  ({pct:5.1f}%)")

    # Per-conversation summary table
    print(f"\n{'=' * 50}")
    print("  [per-conversation breakdown]")
    print(f"{'=' * 50}")
    convs = con.execute("""
        SELECT DISTINCT c.canonical_thread_id,
               (SELECT m.title FROM messages m
                WHERE m.canonical_thread_id = c.canonical_thread_id
                  AND m.title IS NOT NULL LIMIT 1) AS title
        FROM chunks c
        JOIN classifications cl ON cl.chunk_id = c.chunk_id
        ORDER BY c.canonical_thread_id
    """).fetchall()
    for cv in convs:
        tid = cv["canonical_thread_id"]
        title = cv["title"] or tid[:12]
        labels = con.execute("""
            SELECT DISTINCT cl.scheme, cl.label
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
            WHERE c.canonical_thread_id = ?
            ORDER BY cl.scheme, cl.label
        """, (tid,)).fetchall()

        print(f"\n  {title}")
        current_scheme = None
        for lb in labels:
            if lb["scheme"] != current_scheme:
                current_scheme = lb["scheme"]
                print(f"    [{current_scheme}]", end="")
            print(f" {lb['label']}", end=",")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    if not args.db.exists():
        print(f"ERROR: DB not found at {args.db}")
        return

    con = connect(args.db)
    report(con)
    con.close()


if __name__ == "__main__":
    main()
