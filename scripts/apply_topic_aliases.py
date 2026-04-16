"""Populate classifications.canonical_label for scheme='key_topic' rows.

For every row with scheme='key_topic':
  - if its label is in the alias map, canonical_label = mapped canonical
  - otherwise, canonical_label = label (unchanged)

Other schemes (category, emotion, outcome) are left with NULL canonical_label
for now — they have their own, much smaller cleanup problem that we're not
tackling in this pass.

Safe to re-run: the UPDATE is idempotent.

Usage:
    python scripts/apply_topic_aliases.py [--db DB_PATH] [--dry-run]
"""

import argparse
import sqlite3
from pathlib import Path

from topic_aliases import ALIASES, build_reverse_map

DEFAULT_DB = Path("data/db/archive.db")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true",
                    help="compute the changes but don't write them")
    args = ap.parse_args()

    reverse = build_reverse_map()
    print(f"Loaded {len(ALIASES)} canonical labels covering {len(reverse)} raw labels")

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row

    total = con.execute(
        "SELECT COUNT(*) FROM classifications WHERE scheme = 'key_topic'"
    ).fetchone()[0]
    print(f"Total key_topic rows: {total:,}")

    # Count rows that will be folded (label in the reverse map, and the
    # canonical differs from the raw label).
    folded_rows = 0
    passthrough_rows = 0
    distinct_before = con.execute(
        "SELECT COUNT(DISTINCT label) FROM classifications WHERE scheme = 'key_topic'"
    ).fetchone()[0]

    # Compute planned assignments per distinct label so we can report cleanly.
    planned: dict[str, str] = {}
    rows = con.execute(
        "SELECT DISTINCT label FROM classifications WHERE scheme = 'key_topic'"
    ).fetchall()
    for r in rows:
        raw = r["label"]
        planned[raw] = reverse.get(raw, raw)

    # Count rows per planned assignment (for reporting).
    for raw, canonical in planned.items():
        cnt = con.execute(
            "SELECT COUNT(*) FROM classifications WHERE scheme='key_topic' AND label=?",
            (raw,),
        ).fetchone()[0]
        if canonical != raw:
            folded_rows += cnt
        else:
            passthrough_rows += cnt

    print(f"Distinct labels before: {distinct_before:,}")
    print(f"Rows to fold:           {folded_rows:,}")
    print(f"Rows to pass through:   {passthrough_rows:,}")

    if args.dry_run:
        print("\n--dry-run set, no writes performed.")
        con.close()
        return

    # Apply. Two UPDATEs: one for aliased labels, one bulk for passthrough.
    for raw, canonical in planned.items():
        con.execute(
            """UPDATE classifications
               SET canonical_label = ?
               WHERE scheme = 'key_topic' AND label = ?""",
            (canonical, raw),
        )
    con.commit()

    # Verify: distinct canonical_label count should be smaller.
    distinct_after = con.execute(
        """SELECT COUNT(DISTINCT canonical_label)
           FROM classifications
           WHERE scheme = 'key_topic'"""
    ).fetchone()[0]
    null_after = con.execute(
        """SELECT COUNT(*) FROM classifications
           WHERE scheme = 'key_topic' AND canonical_label IS NULL"""
    ).fetchone()[0]

    print()
    print(f"Distinct canonical labels: {distinct_after:,} (was {distinct_before:,})")
    print(f"Rows with NULL canonical:  {null_after:,}")
    print(f"Reduction:                 {distinct_before - distinct_after} labels collapsed")

    con.close()


if __name__ == "__main__":
    main()
