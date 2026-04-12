"""vec0-aware SQLite inspector for the mychatarchive schema.

Usage: python scripts/inspect_db.py [DB_PATH]
    Defaults to data/db/archive-tiny.db.
"""

import sqlite3
import sys
from pathlib import Path

import sqlite_vec

DEFAULT_DB = Path("data/db/archive-tiny.db")


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    con.row_factory = sqlite3.Row
    return con


def main() -> None:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    print(f"db: {db_path}")
    con = connect(db_path)

    tables = [
        "messages",
        "chunks",
        "vec_chunks",
        "thoughts",
        "thread_summaries",
        "thread_groups",
    ]
    print("\n-- row counts --")
    for t in tables:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n}")
        except sqlite3.OperationalError as e:
            print(f"  {t}: ERR {e}")

    print("\n-- distinct threads in chunks --")
    n = con.execute("SELECT COUNT(DISTINCT canonical_thread_id) FROM chunks").fetchone()[0]
    print(f"  {n}")

    print("\n-- chunks per message (top 5) --")
    rows = con.execute(
        """
        SELECT message_id, COUNT(*) AS c
        FROM chunks
        GROUP BY message_id
        ORDER BY c DESC
        LIMIT 5
        """
    ).fetchall()
    for r in rows:
        print(f"  {r['message_id'][:12]}…  {r['c']} chunks")

    print("\n-- chunk length distribution --")
    rows = con.execute(
        """
        SELECT MIN(LENGTH(text)), AVG(LENGTH(text)), MAX(LENGTH(text)), COUNT(*)
        FROM chunks
        """
    ).fetchone()
    print(f"  min={rows[0]}  avg={rows[1]:.0f}  max={rows[2]}  n={rows[3]}")

    print("\n-- sample chunk (longest message, first 3 chunks) --")
    longest = con.execute(
        """
        SELECT message_id FROM chunks
        GROUP BY message_id ORDER BY COUNT(*) DESC LIMIT 1
        """
    ).fetchone()
    if longest:
        rows = con.execute(
            "SELECT chunk_index, LENGTH(text) AS n, SUBSTR(text, 1, 80) AS head "
            "FROM chunks WHERE message_id = ? ORDER BY chunk_index LIMIT 3",
            (longest["message_id"],),
        ).fetchall()
        for r in rows:
            print(f"  [{r['chunk_index']}] len={r['n']}  {r['head']!r}")

    print("\n-- vec_chunks sanity: one nearest-neighbour query --")
    probe = con.execute("SELECT chunk_id FROM vec_chunks LIMIT 1").fetchone()
    if probe:
        rows = con.execute(
            """
            SELECT v.chunk_id, v.distance, SUBSTR(c.text, 1, 60) AS head
            FROM vec_chunks v
            JOIN chunks c ON c.chunk_id = v.chunk_id
            WHERE v.embedding MATCH (SELECT embedding FROM vec_chunks WHERE chunk_id = ?)
              AND k = 3
            ORDER BY v.distance
            """,
            (probe["chunk_id"],),
        ).fetchall()
        for r in rows:
            print(f"  dist={r['distance']:.4f}  {r['head']!r}")

    con.close()


if __name__ == "__main__":
    main()
