"""Classification prompt test on 10 conversations (Phase 1, Step 1.1).

Classifies each conversation in archive-tiny.db using the PRD Section 12.1
system prompt via the real-time Messages API, then stores results in the
classifications table.

Usage:
    python scripts/classify_test.py [--db DB_PATH] [--dry-run]

Requires ANTHROPIC_API_KEY env var.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB = Path("data/db/archive-tiny.db")
MODEL = "claude-sonnet-4-20250514"
MAX_CONTENT_CHARS = 80_000

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
  "key_topics": ["specific_topic_1", "specific_topic_2"],  // always snake_case
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
# Classification
# ---------------------------------------------------------------------------

def classify_conversation(client: anthropic.Anthropic, conv: dict) -> dict | None:
    """Send one conversation to the API and return parsed JSON."""
    content = f"Conversation title: {conv['title']}\n\n{conv['text']}"
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS]

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text

    # Extract JSON from the response, handling:
    # 1. Markdown fencing (```json ... ```)
    # 2. Preamble text before the JSON object
    stripped = raw_text.strip()

    # Strip markdown fencing
    if "```" in stripped:
        import re
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
        print(f"  WARNING: Failed to parse JSON for '{conv['title']}'")
        print(f"  Raw response (first 500 chars):\n  {raw_text[:500]}")
        return None


def store_classifications(
    con: sqlite3.Connection,
    thread_id: str,
    result: dict,
    raw_json: str,
) -> int:
    """Fan out conversation-level labels to all chunks in the thread.

    Returns the number of rows inserted.
    """
    chunk_ids = get_chunk_ids_for_thread(con, thread_id)
    if not chunk_ids:
        print(f"  WARNING: No chunks found for thread {thread_id[:12]}")
        return 0

    rows_inserted = 0

    # Build list of (scheme, label, confidence) tuples from the result
    labels: list[tuple[str, str, float | None]] = []

    for cat in result.get("categories", []):
        labels.append(("category", cat, None))

    for emo in result.get("emotions", []):
        labels.append(("emotion", emo["emotion"], emo.get("intensity")))

    for topic in result.get("key_topics", []):
        labels.append(("key_topic", topic, None))

    if result.get("outcome"):
        labels.append(("outcome", result["outcome"], None))

    for chunk_id in chunk_ids:
        for scheme, label, confidence in labels:
            try:
                con.execute(
                    """INSERT OR IGNORE INTO classifications
                       (chunk_id, scheme, label, confidence, model, batch_id, raw)
                       VALUES (?, ?, ?, ?, ?, NULL, ?)""",
                    (chunk_id, scheme, label, confidence, MODEL, raw_json),
                )
                rows_inserted += con.total_changes  # approximate; OR IGNORE skips
            except sqlite3.IntegrityError:
                pass  # duplicate — idempotent

    con.commit()
    # Accurate count via total_changes isn't per-statement; count directly
    count = con.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify but don't write to DB")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"ERROR: DB not found at {args.db}")
        sys.exit(1)

    con = connect(args.db)
    conversations = load_conversations(con)
    print(f"Loaded {len(conversations)} conversations from {args.db}\n")

    client = anthropic.Anthropic()
    results: list[tuple[dict, dict]] = []  # (conv, parsed_result)

    for i, conv in enumerate(conversations, 1):
        print(f"[{i}/{len(conversations)}] Classifying: {conv['title']}")
        print(f"  Messages: {conv['message_count']}  Chars: {len(conv['text'])}")

        result = classify_conversation(client, conv)
        if result is None:
            continue

        results.append((conv, result))

        # Pretty-print for human review
        print(f"  Categories: {result.get('categories')}")
        print(f"  Emotions:   {[e['emotion'] for e in result.get('emotions', [])]}")
        print(f"  Outcome:    {result.get('outcome')}")
        print(f"  Topics:     {result.get('key_topics')}")
        print(f"  Summary:    {result.get('summary', '')[:120]}")
        print(f"  Confidence: {result.get('confidence')}")
        print()

    # Store results
    if args.dry_run:
        print("-- DRY RUN: skipping DB writes --")
    else:
        print("--- Storing classifications ---")
        for conv, result in results:
            raw_json = json.dumps(result)
            store_classifications(con, conv["thread_id"], result, raw_json)
            print(f"  Stored: {conv['title']}")

        # Summary stats
        print("\n--- Classification Summary ---")
        rows = con.execute(
            "SELECT scheme, label, COUNT(*) AS n FROM classifications GROUP BY scheme, label ORDER BY scheme, n DESC"
        ).fetchall()
        current_scheme = None
        for r in rows:
            if r["scheme"] != current_scheme:
                current_scheme = r["scheme"]
                print(f"\n  [{current_scheme}]")
            print(f"    {r['label']}: {r['n']}")

        total = con.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
        print(f"\n  Total rows: {total}")

    con.close()


if __name__ == "__main__":
    main()
