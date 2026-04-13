"""MCP server for tension-detect. Zero-LLM architecture.

The server detects contradiction candidates (no LLM needed).
The client LLM generates boundary conditions (zero additional cost).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from mcp.server.fastmcp import FastMCP

from .parser import parse_rules
from .detector import detect_tensions
from .store import Tension, save_tension as _store_save, load_tensions
from .formatter import format_tensions_for_injection, inject_into_text

# Security: allowed file extensions for read/write operations
_ALLOWED_EXTENSIONS = {".md", ".txt", ".cursorrules", ".rules", ".yaml", ".yml"}
_ALLOWED_FILENAMES = {".cursorrules", "RULES", "rules"}


def _validate_file_path(file_path: str) -> tuple[Path | None, str | None]:
    """Validate a file path for security.

    Returns (resolved_path, None) on success, (None, error_msg) on failure.
    """
    try:
        raw = Path(file_path).expanduser()
    except (ValueError, OSError):
        return None, f"Invalid file path: {file_path!r}"

    # Check symlink BEFORE resolve (resolve follows symlinks)
    try:
        if raw.is_symlink():
            return None, "Symlinks are not allowed for security reasons."
        path = raw.resolve()
    except (ValueError, OSError):
        return None, f"Cannot resolve path: {file_path!r}"

    if path.name not in _ALLOWED_FILENAMES and path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(_ALLOWED_EXTENSIONS | _ALLOWED_FILENAMES))
        return None, f"File '{path.name}' not allowed. Allowed extensions/names: {allowed}"

    return path, None


mcp = FastMCP(
    "tension-detect",
    instructions=(
        "You are a Contradiction Montage engine. "
        "Your job is to turn contradicting rules into judgment boundaries.\n\n"
        "WORKFLOW:\n"
        "1. Call detect_tensions or analyze_file to find contradictions.\n"
        "2. For EACH contradiction found, generate a judgment boundary:\n"
        "   a. Imagine a concrete situation where Rule A is correct.\n"
        "   b. Imagine a concrete situation where Rule B is correct.\n"
        "   c. Identify the SIGNAL: what observable fact distinguishes the two situations?\n"
        "   d. Write the boundary: 'When [signal], apply A. Otherwise, apply B.'\n"
        "3. Call save_tension for each boundary you generated.\n"
        "4. Call inject_tensions to write all boundaries back to the user's rules file.\n\n"
        "EXAMPLE:\n"
        "  Rule A: 'Review code thoroughly before merging'\n"
        "  Rule B: 'Ship features fast, iterate quickly'\n"
        "  Boundary: 'Production hotfix -> ship fast. Normal feature work -> review thoroughly.'\n"
        "  Signal: 'Is there an open production incident?'\n\n"
        "IMPORTANT: Both rules are always correct. Never delete either rule. "
        "Your job is to find WHEN each one applies, not WHICH one is better."
    ),
)


@mcp.tool()
def detect_tensions_tool(rules_text: str) -> dict:
    """Detect contradiction candidates in a set of rules.

    Pass the full text of a rules file (CLAUDE.md, .cursorrules, etc.).
    Returns candidates ranked by confidence score.

    For EACH candidate, you MUST generate a judgment boundary:
    1. Imagine when Rule A is the right call (concrete situation)
    2. Imagine when Rule B is the right call (concrete situation)
    3. Find the SIGNAL: what observable fact tells you which situation you're in?
    4. Write: "When [signal], apply A. Otherwise, apply B."
    5. Call save_tension_tool with your boundary and signal
    After all boundaries are saved, call inject_tensions_tool to write them to the file.
    """
    rules = parse_rules(rules_text)
    candidates = detect_tensions(rules)

    return {
        "rules_parsed": len(rules),
        "candidates_found": len(candidates),
        "candidates": [
            {
                "rule_a_text": c.rule_a.text,
                "rule_b_text": c.rule_b.text,
                "shared_keywords": c.shared_keywords,
                "opposing_directions": c.opposing_directions,
            }
            for c in candidates
        ],
    }


@mcp.tool()
def analyze_file(file_path: str) -> dict:
    """Analyze a rules file and report rule count and contradiction candidates."""
    path, err = _validate_file_path(file_path)
    if err:
        return {"error": err}
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    text = path.read_text(encoding="utf-8")
    rules = parse_rules(text)
    candidates = detect_tensions(rules)

    return {
        "file": str(path),
        "rules_parsed": len(rules),
        "candidates_found": len(candidates),
        "candidates": [
            {
                "rule_a_text": c.rule_a.text,
                "rule_b_text": c.rule_b.text,
                "shared_keywords": c.shared_keywords,
                "opposing_directions": c.opposing_directions,
            }
            for c in candidates
        ],
    }


@mcp.tool()
def save_tension_tool(
    rule_a_text: str,
    rule_b_text: str,
    boundary: str,
    signal: str,
    scope: str = "",
) -> dict:
    """Save a resolved tension with its boundary condition.

    Call this after you (the client LLM) have determined:
    - boundary: When to apply rule A vs rule B
    - signal: What observable cue triggers the switch
    """
    tension_id = f"tension-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
    t = Tension(
        id=tension_id,
        rule_a_text=rule_a_text,
        rule_b_text=rule_b_text,
        boundary=boundary,
        signal=signal,
        scope=scope,
    )
    saved_id = _store_save(t)
    return {"id": saved_id, "status": "saved"}


@mcp.tool()
def get_tensions_tool() -> dict:
    """Get all saved tensions with their boundary conditions."""
    tensions = load_tensions()
    return {
        "count": len(tensions),
        "tensions": [
            {
                "id": t.id,
                "rule_a_text": t.rule_a_text,
                "rule_b_text": t.rule_b_text,
                "boundary": t.boundary,
                "signal": t.signal,
                "created_at": t.created_at,
            }
            for t in tensions
        ],
    }


@mcp.tool()
def inject_tensions_tool(file_path: str) -> dict:
    """Inject saved tensions as a Judgment Boundaries section into a file.

    Uses <!-- tension-detect:start/end --> markers for idempotent updates.
    """
    path, err = _validate_file_path(file_path)
    if err:
        return {"error": err}
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    tensions = load_tensions()
    if not tensions:
        return {"error": "No saved tensions. Run detect + save first."}

    section = format_tensions_for_injection(tensions)
    original = path.read_text(encoding="utf-8")
    updated = inject_into_text(original, section)
    path.write_text(updated, encoding="utf-8")

    return {"file": str(path), "tensions_injected": len(tensions), "status": "written"}
