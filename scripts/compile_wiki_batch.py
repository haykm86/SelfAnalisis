"""Compile one wiki topic via Claude Batch API without touching the control article.

Workflow:
  prepare — build the exact topic bundle locally, no network call
  submit  — submit one topic as a Batch API request
  poll    — check batch status
  ingest  — write the batch result to a separate experiment file

Usage:
  python scripts/compile_wiki_batch.py prepare --topic clickhouse
  python scripts/compile_wiki_batch.py submit  --topic clickhouse
  python scripts/compile_wiki_batch.py poll    --batch-id msgbatch_...
  python scripts/compile_wiki_batch.py ingest  --topic clickhouse --batch-id msgbatch_...

The existing vault/wiki/<topic>.md file is treated as the control and is never
overwritten unless the caller explicitly points --out there and passes --overwrite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from compile_wiki_input import DEFAULT_DB, DEFAULT_THREAD_CHARS, build_bundle, connect

load_dotenv()

MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 4000
DEFAULT_OUT_DIR = Path("vault/wiki/_batch_experiments")
PROMPT_PATH = Path("prompts/wiki_compile.md")


def get_client():
    import anthropic

    return anthropic.Anthropic()


def load_system_prompt(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def build_user_message(bundle_text: str) -> str:
    return (
        "Compile exactly one L2 wiki article from the source bundle below.\n"
        "Return only the final markdown article body.\n"
        "Do not wrap the article in code fences.\n"
        "Do not add YAML frontmatter; it will be added after ingest.\n\n"
        f"{bundle_text}"
    )


def default_out_path(topic: str) -> Path:
    return DEFAULT_OUT_DIR / f"{topic}.batch.md"


def default_bundle_path(topic: str) -> Path:
    return DEFAULT_OUT_DIR / f"{topic}.bundle.txt"


def print_batch_status(batch) -> None:
    print(f"Batch: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Counts: {batch.request_counts}")

    for field in (
        "created_at",
        "ended_at",
        "expires_at",
        "cancel_initiated_at",
        "archived_at",
    ):
        value = getattr(batch, field, None)
        if value is not None:
            print(f"{field}: {value}")


def strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    fence_match = re.fullmatch(r"```(?:markdown|md)?\s*\n?(.*?)```", stripped, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return stripped


def build_frontmatter(metadata: dict[str, object], batch_id: str, model: str) -> str:
    topic = metadata["topic"]
    source_thread_ids = metadata["source_thread_ids"]
    baseline = Path("vault/wiki") / f"{topic}.md"
    return (
        "---\n"
        "type: wiki\n"
        "layer: L2\n"
        f"topic: {topic}\n"
        f"source_thread_ids: {json.dumps(source_thread_ids)}\n"
        f'time_span: "{metadata["time_span"]}"\n'
        f"last_compiled: {date.today().isoformat()}\n"
        f"thread_count: {metadata['thread_count']}\n"
        "compilation_method: batch_api_experiment\n"
        f"batch_id: {batch_id}\n"
        f"model: {model}\n"
        f"comparison_baseline: {baseline.as_posix()}\n"
        "---\n\n"
    )


def prepare_bundle(
    db_path: Path, topic: str, thread_chars: int, bundle_out: Path | None
) -> tuple[str, dict[str, object]]:
    con = connect(db_path)
    try:
        bundle_text, metadata = build_bundle(con, topic, thread_chars)
    finally:
        con.close()

    if bundle_out is not None:
        bundle_out.parent.mkdir(parents=True, exist_ok=True)
        bundle_out.write_text(bundle_text, encoding="utf-8")

    return bundle_text, metadata


def cmd_prepare(args: argparse.Namespace) -> None:
    try:
        bundle_text, metadata = prepare_bundle(
            args.db, args.topic, args.thread_chars, args.bundle_out
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Topic:            {metadata['topic']}")
    print(f"Threads included: {metadata['thread_count']}/{metadata['total_threads']}")
    print(f"Time span:        {metadata['time_span']}")
    print(f"Bundle chars:     {metadata['char_count']:,}")
    print(f"Control article:  vault/wiki/{args.topic}.md")
    print(f"Experiment out:   {args.out or default_out_path(args.topic)}")
    if args.bundle_out is not None:
        print(f"Bundle saved:     {args.bundle_out}")
    dropped = metadata["dropped_thread_ids"]
    if dropped:
        print(f"Dropped threads:  {len(dropped)}")
        print("  " + ", ".join(thread_id[:12] for thread_id in dropped))

    if args.preview:
        preview = bundle_text[: args.preview]
        print("\n--- bundle preview ---\n")
        print(preview)
        if len(bundle_text) > args.preview:
            print("\n...[truncated]")


def cmd_submit(args: argparse.Namespace) -> None:
    try:
        bundle_text, metadata = prepare_bundle(
            args.db, args.topic, args.thread_chars, args.bundle_out
        )
        system_prompt = load_system_prompt(args.prompt)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    request = {
        "custom_id": args.topic,
        "params": {
            "model": args.model,
            "max_tokens": args.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": build_user_message(bundle_text)}],
        },
    }

    print(
        f"Submitting topic {args.topic} "
        f"({metadata['thread_count']} threads, {metadata['char_count']:,} chars)..."
    )
    client = get_client()
    batch = client.messages.batches.create(requests=[request])
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Control article:  vault/wiki/{args.topic}.md")
    print(f"Experiment out:   {args.out or default_out_path(args.topic)}")
    print(
        f"\nTo poll:   python scripts/compile_wiki_batch.py poll --batch-id {batch.id}"
    )
    print(
        "To ingest: "
        "python scripts/compile_wiki_batch.py ingest "
        f"--topic {args.topic} --batch-id {batch.id}"
    )


def cmd_poll(args: argparse.Namespace) -> None:
    client = get_client()
    batch = client.messages.batches.retrieve(args.batch_id)
    print_batch_status(batch)

    if args.wait:
        print("\nWaiting for completion...")
        while batch.processing_status != "ended":
            time.sleep(30)
            batch = client.messages.batches.retrieve(args.batch_id)
            print_batch_status(batch)
        print("Batch complete.")


def cmd_ingest(args: argparse.Namespace) -> None:
    out_path = args.out or default_out_path(args.topic)
    if out_path.exists() and not args.overwrite:
        print(
            f"ERROR: output exists: {out_path} "
            "(pass --overwrite to replace the experiment file)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        _, metadata = prepare_bundle(args.db, args.topic, args.thread_chars, None)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    client = get_client()
    batch = client.messages.batches.retrieve(args.batch_id)
    if batch.processing_status != "ended":
        print(f"Batch not done yet. Status: {batch.processing_status}")
        print(f"Counts: {batch.request_counts}")
        return

    selected = None
    for result in client.messages.batches.results(args.batch_id):
        if result.custom_id == args.topic:
            selected = result
            break

    if selected is None:
        print(
            f"ERROR: no result for topic {args.topic!r} found in batch {args.batch_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    if selected.result.type != "succeeded":
        print(
            f"ERROR: batch result for {args.topic!r} failed: {selected.result.type}",
            file=sys.stderr,
        )
        sys.exit(1)

    body = strip_markdown_fences(selected.result.message.content[0].text)
    frontmatter = build_frontmatter(metadata, args.batch_id, args.model)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(frontmatter + body.strip() + "\n", encoding="utf-8")

    print(f"Wrote experiment article: {out_path}")
    print(f"Control article:         vault/wiki/{args.topic}.md")
    print(
        "Next step: diff the two files and compare evidence markers, chronology, "
        "and cleanup burden."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=DEFAULT_DB)
    common.add_argument("--topic", required=True)
    common.add_argument("--thread-chars", type=int, default=DEFAULT_THREAD_CHARS)
    common.add_argument("--out", type=Path)

    p_prepare = sub.add_parser("prepare", parents=[common], help="Build bundle locally")
    p_prepare.add_argument(
        "--bundle-out",
        type=Path,
        help="Optional path to save the exact bundle text for audit/review",
    )
    p_prepare.add_argument(
        "--preview",
        type=int,
        default=0,
        help="Print the first N chars of the bundle for a quick local preview",
    )

    p_submit = sub.add_parser("submit", parents=[common], help="Submit one-topic batch")
    p_submit.add_argument("--prompt", type=Path, default=PROMPT_PATH)
    p_submit.add_argument("--bundle-out", type=Path, default=None)
    p_submit.add_argument("--model", default=MODEL)
    p_submit.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)

    p_poll = sub.add_parser("poll", help="Check batch status")
    p_poll.add_argument("--batch-id", required=True)
    p_poll.add_argument("--wait", action="store_true", help="Poll until complete")

    p_ingest = sub.add_parser("ingest", parents=[common], help="Write experiment markdown")
    p_ingest.add_argument("--batch-id", required=True)
    p_ingest.add_argument("--model", default=MODEL)
    p_ingest.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the experiment output if it already exists",
    )

    args = parser.parse_args()

    if args.command == "prepare":
        cmd_prepare(args)
    elif args.command == "submit":
        cmd_submit(args)
    elif args.command == "poll":
        cmd_poll(args)
    elif args.command == "ingest":
        cmd_ingest(args)


if __name__ == "__main__":
    main()
