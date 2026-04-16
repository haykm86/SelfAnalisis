"""Inspect key_topic labels for normalization planning.

Produces a conversation-level frequency report (deduplicated via
canonical_thread_id so the chunk fan-out doesn't inflate counts).

Usage:
    python scripts/topic_inspect.py [--db DB_PATH] [--top N]
"""

import argparse
import sqlite3
from pathlib import Path

DEFAULT_DB = Path("data/db/archive.db")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--top", type=int, default=150,
                    help="how many top topics to print in detail")
    ap.add_argument("--scheme", default="key_topic")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        """
        SELECT cl.label AS label,
               COUNT(DISTINCT c.canonical_thread_id) AS convs
        FROM classifications cl
        JOIN chunks c ON c.chunk_id = cl.chunk_id
        WHERE cl.scheme = ?
        GROUP BY cl.label
        ORDER BY convs DESC, cl.label ASC
        """,
        (args.scheme,),
    ).fetchall()

    total_distinct = len(rows)
    total_conv_hits = sum(r["convs"] for r in rows)
    singletons = sum(1 for r in rows if r["convs"] == 1)

    print(f"scheme:            {args.scheme}")
    print(f"distinct labels:   {total_distinct}")
    print(f"total conv hits:   {total_conv_hits}")
    print(f"singletons:        {singletons} ({singletons / total_distinct:.0%})")
    print(f"top {args.top}:")
    print()
    print(f"{'convs':>6}  label")
    print("-" * 60)
    for r in rows[: args.top]:
        print(f"{r['convs']:>6}  {r['label']}")

    con.close()


if __name__ == "__main__":
    main()
