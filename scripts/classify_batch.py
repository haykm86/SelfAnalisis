"""Classify all conversations in the full archive via Claude Batch API.

Three modes:
  submit  — build batch requests and submit to the API
  poll    — check batch status
  ingest  — download results and store in the classifications table

Usage:
    python scripts/classify_batch.py submit [--db DB_PATH]
    python scripts/classify_batch.py poll   --batch-id BATCH_ID
    python scripts/classify_batch.py ingest --batch-id BATCH_ID [--db DB_PATH]

Requires ANTHROPIC_API_KEY env var.
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB = Path("data/db/archive.db")
MODEL = "claude-sonnet-4-20250514"
MAX_CONTENT_CHARS = 80_000

# Same prompt as classify_test.py (tightened in Session 06)
SYSTEM_PROMPT = """\
You are analyzing a personal conversation from a 4-year ChatGPT archive belonging to a software developer named Hayk. Your job is to extract structured metadata about THIS conversation.

Focus on HAYK's side — his questions, concerns, decisions, emotional state. The AI assistant's responses are context but not the subject of analysis.

Respond with ONLY valid JSON (no markdown fencing, no preamble):

{
  "categories": ["primary/sub", "secondary/sub"],
  "emotions": [
    {"emotion": "frustrated", "intensity": 0.7, "context": "deadline pressure"},
    {"emotion": "curious", "intensity": 0.9, "context": "exploring new framework"}
  ],
  "decisions_made": ["Chose X over Y because Z"],
  "lessons_learned": ["Learned that A leads to B"],
  "people_mentioned": ["person_name or role"],
  "outcome": "success | failure | ongoing | unclear | trivial",
  "time_period": "YYYY-QN",
  "key_topics": ["specific_topic_1", "specific_topic_2"],
  "summary": "2-3 sentences: what was this conversation about, what was Hayk trying to accomplish, what was the result?",
  "confidence": 0.85
}

Category taxonomy:
- work/crm — CRM project: features, bugs, architecture, migrations
- work/technical — general technical work, non-CRM coding
- work/team — colleague dynamics, management, workplace relationships
- work/career — career decisions, job concerns, professional growth
- learning/successful — learning that produced lasting skill/knowledge
- learning/abandoned — started learning something, stopped
- learning/ongoing — still actively learning
- personal/struggles — depression, anxiety, life difficulties, emotional processing
- personal/philosophy — philosophical discussions, meaning, values, worldview
- personal/relationships — family, friends, romantic, social dynamics
- personal/health — physical or mental health discussions
- meta/planning — goal setting, life planning, project planning
- meta/reflection — looking back, self-analysis, pattern recognition
- meta/dreams — aspirations, future visions, what-ifs

Rules:
- A conversation can have multiple categories — but ONLY from the taxonomy above. Do not invent new categories. If a conversation doesn't fit neatly, pick the closest match.
- For emotions, use ONLY genuine emotions (feelings a person experiences), not cognitive states, strategies, or attitudes. Examples of valid emotions: frustrated, curious, anxious, proud, relieved, hopeful, discouraged, confused, nervous, guilty, grateful, excited, sad, angry, ashamed, envious, nostalgic. NEVER use these (they are mental states, not emotions): strategic, focused, engaged, analytical, determined, motivated, cautious, contemplative.
- For emotions, score intensity 0.0-1.0 where 0.5 is neutral/mild, 0.8+ is strong
- For outcome, use EXACTLY one of: success, failure, ongoing, unclear, trivial. No variations (not "successful", not "incomplete").
- If the conversation is trivial (small talk, single question), set outcome to "trivial"
- For key_topics, always use snake_case (e.g., "leetcode_practice" not "leetcode practice", "data_structures" not "data structures")
- Be specific in key_topics — "postgresql_connection_pooling" not just "database"
- For people, use their name if mentioned, otherwise their role ("team lead", "friend")
- Set confidence 0.0-1.0 for how sure you are about the overall classification
- All metadata is INFERRED, not ground truth — mark appropriately"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con


def load_conversations(con: sqlite3.Connection) -> list[dict]:
    """Return one dict per thread with title and formatted messages."""
    threads = con.execute(
        "SELECT DISTINCT canonical_thread_id FROM messages ORDER BY canonical_thread_id"
    ).fetchall()

    conversations = []
    for row in threads:
        tid = row["canonical_thread_id"]
        msgs = con.execute(
            """SELECT role, text, title
               FROM messages
               WHERE canonical_thread_id = ?
               ORDER BY ts""",
            (tid,),
        ).fetchall()

        title = next((m["title"] for m in msgs if m["title"]), tid[:12])
        formatted = "\n---\n".join(
            f"[{m['role']}]: {m['text']}" for m in msgs if m["text"]
        )
        conversations.append({
            "thread_id": tid,
            "title": title,
            "text": formatted,
            "message_count": len(msgs),
        })
    return conversations


def get_chunk_ids_for_thread(con: sqlite3.Connection, thread_id: str) -> list[str]:
    rows = con.execute(
        "SELECT chunk_id FROM chunks WHERE canonical_thread_id = ?",
        (thread_id,),
    ).fetchall()
    return [r["chunk_id"] for r in rows]


# ---------------------------------------------------------------------------
# JSON parsing (same logic as classify_test.py)
# ---------------------------------------------------------------------------

def parse_json_response(raw_text: str) -> dict | None:
    """Extract JSON from model response, handling fencing and preamble."""
    stripped = raw_text.strip()

    # Strip markdown fencing
    if "```" in stripped:
        fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", stripped, re.DOTALL)
        if fence_match:
            stripped = fence_match.group(1).strip()

    # If it doesn't start with {, try to find the first {
    if not stripped.startswith("{"):
        brace_pos = stripped.find("{")
        if brace_pos != -1:
            stripped = stripped[brace_pos:]

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

def cmd_submit(args: argparse.Namespace) -> None:
    con = connect(args.db)
    conversations = load_conversations(con)
    print(f"Loaded {len(conversations)} conversations from {args.db}")

    # Skip already-classified threads
    classified = set()
    try:
        rows = con.execute("""
            SELECT DISTINCT c.canonical_thread_id
            FROM classifications cl
            JOIN chunks c ON c.chunk_id = cl.chunk_id
        """).fetchall()
        classified = {r["canonical_thread_id"] for r in rows}
    except sqlite3.OperationalError:
        pass  # no classifications yet

    remaining = [c for c in conversations if c["thread_id"] not in classified]
    print(f"Already classified: {len(classified)}, remaining: {len(remaining)}")

    if not remaining:
        print("Nothing to classify.")
        return

    # Build batch requests
    requests = []
    for conv in remaining:
        content = f"Conversation title: {conv['title']}\n\n{conv['text']}"
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS]

        requests.append({
            "custom_id": conv["thread_id"],
            "params": {
                "model": MODEL,
                "max_tokens": 2000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": content}],
            },
        })

    print(f"Submitting batch with {len(requests)} requests...")
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"\nTo poll:   python scripts/classify_batch.py poll --batch-id {batch.id}")
    print(f"To ingest: python scripts/classify_batch.py ingest --batch-id {batch.id}")

    con.close()


# ---------------------------------------------------------------------------
# Poll
# ---------------------------------------------------------------------------

def cmd_poll(args: argparse.Namespace) -> None:
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(args.batch_id)
    print(f"Batch: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Counts: {batch.request_counts}")

    if args.wait:
        print("\nWaiting for completion...")
        while batch.processing_status != "ended":
            time.sleep(30)
            batch = client.messages.batches.retrieve(args.batch_id)
            print(f"  Status: {batch.processing_status} | Counts: {batch.request_counts}")
        print("Batch complete.")


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def cmd_ingest(args: argparse.Namespace) -> None:
    client = anthropic.Anthropic()

    # Check batch status
    batch = client.messages.batches.retrieve(args.batch_id)
    if batch.processing_status != "ended":
        print(f"Batch not done yet. Status: {batch.processing_status}")
        print(f"Counts: {batch.request_counts}")
        return

    print(f"Batch {args.batch_id} complete. Downloading results...")

    con = connect(args.db)

    succeeded = 0
    failed_parse = 0
    failed_api = 0
    skipped_no_chunks = 0
    total = 0

    for result in client.messages.batches.results(args.batch_id):
        total += 1
        thread_id = result.custom_id

        if result.result.type != "succeeded":
            failed_api += 1
            print(f"  FAIL (API): {thread_id[:12]} — {result.result.type}")
            continue

        raw_text = result.result.message.content[0].text
        parsed = parse_json_response(raw_text)
        if parsed is None:
            failed_parse += 1
            print(f"  FAIL (parse): {thread_id[:12]} — {raw_text[:200]}")
            continue

        # Fan out to chunks
        chunk_ids = get_chunk_ids_for_thread(con, thread_id)
        if not chunk_ids:
            skipped_no_chunks += 1
            if total <= 5 or skipped_no_chunks <= 3:
                print(f"  SKIP (no chunks): {thread_id[:12]}")
            continue

        raw_json = json.dumps(parsed)

        # Build labels
        labels: list[tuple[str, str, float | None]] = []
        for cat in parsed.get("categories", []):
            labels.append(("category", cat, None))
        for emo in parsed.get("emotions", []):
            labels.append(("emotion", emo["emotion"], emo.get("intensity")))
        for topic in parsed.get("key_topics", []):
            labels.append(("key_topic", topic, None))
        if parsed.get("outcome"):
            labels.append(("outcome", parsed["outcome"], None))

        for chunk_id in chunk_ids:
            for scheme, label, confidence in labels:
                con.execute(
                    """INSERT OR IGNORE INTO classifications
                       (chunk_id, scheme, label, confidence, model, batch_id, raw)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (chunk_id, scheme, label, confidence, MODEL, args.batch_id, raw_json),
                )

        succeeded += 1

    con.commit()

    total_rows = con.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
    print(f"\n--- Ingest Summary ---")
    print(f"Total results:      {total}")
    print(f"Succeeded:          {succeeded}")
    print(f"Failed (API):       {failed_api}")
    print(f"Failed (parse):     {failed_parse}")
    print(f"Skipped (no chunks):{skipped_no_chunks}")
    print(f"Total DB rows:      {total_rows}")

    con.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_submit = sub.add_parser("submit", help="Submit batch to API")
    p_submit.add_argument("--db", type=Path, default=DEFAULT_DB)

    p_poll = sub.add_parser("poll", help="Check batch status")
    p_poll.add_argument("--batch-id", required=True)
    p_poll.add_argument("--wait", action="store_true", help="Poll until complete")

    p_ingest = sub.add_parser("ingest", help="Download and store results")
    p_ingest.add_argument("--batch-id", required=True)
    p_ingest.add_argument("--db", type=Path, default=DEFAULT_DB)

    args = parser.parse_args()

    if args.command == "submit":
        cmd_submit(args)
    elif args.command == "poll":
        cmd_poll(args)
    elif args.command == "ingest":
        cmd_ingest(args)


if __name__ == "__main__":
    main()
