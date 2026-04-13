"""MCP server for tension-detect. Zero-LLM architecture.

The server detects contradiction candidates (no LLM needed).
The client LLM generates boundary conditions (zero additional cost).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .parser import parse_rules
from .detector import detect_tensions
from .store import Tension, save_tension as _store_save, load_tensions
from .formatter import format_tensions_for_injection, inject_into_text

# Security: allowed file extensions for read/write operations
_ALLOWED_EXTENSIONS = {".md", ".txt", ".cursorrules", ".rules", ".yaml", ".yml"}


def _validate_file_path(file_path: str) -> tuple[Path | None, str | None]:
    """Validate a file path for security.

    Returns (resolved_path, None) on success, (None, error_msg) on failure.
    """
    path = Path(file_path).expanduser().resolve()

    if path.is_symlink():
        return None, "Symlinks are not allowed for security reasons."

    if path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(_ALLOWED_EXTENSIONS))
        return None, f"File type '{path.suffix}' not allowed. Allowed: {allowed}"

    return path, None


mcp = FastMCP(
    "tension-detect",
    version="0.1.0",
    instructions=(
        "Detect contradictions in AI rules (CLAUDE.md, Cursor Rules, etc.) "
        "and help the user define judgment boundaries. "
        "Use detect_tensions to find candidates, then generate boundaries "
        "with your own reasoning, and save them with save_tension. "
        "Finally, inject_tensions writes the results back to the rules file."
    ),
)


@mcp.tool()
def detect_tensions_tool(rules_text: str) -> dict:
    """Detect contradiction candidates in a set of rules.

    Pass the full text of a rules file (CLAUDE.md, .cursorrules, etc.).
    Returns candidates ranked by confidence score.

    You (the client LLM) should then:
    1. Review each candidate
    2. For genuine contradictions, think about the boundary condition
    3. Call save_tension with your boundary and signal
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
    tension_id = f"tension-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
