"""Minimal RAG retrieval slice — semantic top-k over vec_chunks.

Usage: python scripts/rag_query.py "your question" [--k 10] [--db data/db/archive.db]

Deliberately minimal: semantic only (no FTS5 hybrid, no rerank, no LLM
answer generation). Point is to eyeball whether the embeddings are
load-bearing for real queries, before committing to PRD Phase 5 or
Phase 2 wiki compilation on top of them.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

import sqlite_vec
from mychatarchive.embeddings import embed_single

DEFAULT_DB = Path("data/db/archive.db")
VAULT_THREADS_DIR = Path("vault/threads")


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    con.row_factory = sqlite3.Row
    return con


def search(con: sqlite3.Connection, query: str, k: int) -> list[sqlite3.Row]:
    q_emb = embed_single(query)
    q_blob = sqlite_vec.serialize_float32(q_emb)

    return con.execute(
        """
        WITH hits AS (
            SELECT chunk_id, distance
            FROM vec_chunks
            WHERE embedding MATCH ?
              AND k = ?
        )
        SELECT
            h.distance,
            c.chunk_id,
            c.canonical_thread_id AS thread_id,
            c.chunk_index,
            c.text AS chunk_text,
            c.ts_start,
            m.title,
            m.role
        FROM hits h
        JOIN chunks c ON c.chunk_id = h.chunk_id
        JOIN messages m ON m.message_id = c.message_id
        ORDER BY h.distance
        """,
        (q_blob, k),
    ).fetchall()


def iso_date(ts: str | None) -> str:
    if not ts:
        return "?"
    return ts[:10]


def find_vault_note(thread_id: str) -> Path | None:
    if not VAULT_THREADS_DIR.exists():
        return None
    prefix = thread_id[:12]
    matches = list(VAULT_THREADS_DIR.glob(f"{prefix}__*.md"))
    return matches[0] if matches else None


def print_results(query: str, rows: list[sqlite3.Row]) -> None:
    print(f"\nQuery: {query!r}")
    print(f"Top {len(rows)} chunks by cosine distance\n")
    print("=" * 78)

    for rank, r in enumerate(rows, 1):
        snippet = " ".join(r["chunk_text"].split())[:200]
        note = find_vault_note(r["thread_id"])
        note_str = f"  vault: {note}" if note else ""
        print(
            f"[{rank:2d}] dist={r['distance']:.4f}  {iso_date(r['ts_start'])}  "
            f"{r['role']:<9}  {r['thread_id'][:12]}"
        )
        print(f"     title: {(r['title'] or '(untitled)')[:80]}")
        print(f"     chunk: {snippet}")
        if note_str:
            print(note_str)
        print("-" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Natural-language query")
    parser.add_argument("--k", type=int, default=10, help="Top-k chunks (default 10)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite path (default {DEFAULT_DB})")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"DB not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    con = connect(args.db)
    try:
        rows = search(con, args.query, args.k)
    finally:
        con.close()

    if not rows:
        print("No results.")
        return

    print_results(args.query, rows)


if __name__ == "__main__":
    main()
