"""Slice the first N conversations out of a ChatGPT export.

Usage: python scripts/make_tiny_sample.py [N]
    Defaults to 10. Writes data/sample/conversations-tiny.json.
"""

import json
import sys
from pathlib import Path

SRC = Path("data/sample/conversations.json")
DST = Path("data/sample/conversations-tiny.json")


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    convs = json.loads(SRC.read_text())
    tiny = convs[:n]
    DST.write_text(json.dumps(tiny))
    msgs = sum(len(c.get("mapping", {})) for c in tiny)
    print(f"wrote {DST} — {len(tiny)} conversations, ~{msgs} mapping nodes")


if __name__ == "__main__":
    main()
