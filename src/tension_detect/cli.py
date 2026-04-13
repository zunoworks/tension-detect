"""CLI entry point for tension-detect (detection only, no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

from .parser import parse_rules
from .detector import detect_tensions
from .formatter import format_candidates


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: tension-detect <file>")
        print("       tension-detect -          (read from stdin)")
        print()
        print("Detect contradictions in AI rule files (CLAUDE.md, .cursorrules, etc.)")
        print()
        print("For full boundary generation, use the MCP server instead:")
        print("  claude mcp add tension-detect -- python -m tension_detect.server")
        sys.exit(0)

    if sys.argv[1] == "--version":
        from . import __version__
        print(f"tension-detect {__version__}")
        sys.exit(0)

    if sys.argv[1] == "-":
        text = sys.stdin.read()
        filename = "<stdin>"
    else:
        path = Path(sys.argv[1]).expanduser()
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
        filename = str(path)

    rules = parse_rules(text)
    candidates = detect_tensions(rules)

    print(f"File: {filename}")
    print(f"Rules parsed: {len(rules)}")
    print(f"Contradictions found: {len(candidates)}")
    print()

    if candidates:
        print(format_candidates(candidates))
        print("To generate judgment boundaries, use the MCP server:")
        print("  claude mcp add tension-detect -- python -m tension_detect.server")
    else:
        print("No contradictions detected.")


if __name__ == "__main__":
    main()
