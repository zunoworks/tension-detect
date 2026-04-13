"""Parse text files (CLAUDE.md, Cursor Rules, etc.) into individual rules."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class Rule:
    """A single rule extracted from a rules file."""

    id: str
    text: str
    scope: str = ""


# Inline code / backtick content stripper
_BACKTICK_RE = re.compile(r"`[^`]+`")
# Bold/italic markers
_MD_EMPHASIS_RE = re.compile(r"\*{1,3}|_{1,3}")
# HTML comments (e.g. <!-- CORREX:NARRATIVE:END -->)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Max rule length — longer text is a description, not a rule
_MAX_RULE_LEN = 200
# Lines that are commands, paths, config, or code — not rules
_NON_RULE_RE = re.compile(
    r"^`|"                      # starts with backtick
    r"^\$\s|"                   # shell prompt
    r"^[A-Za-z]:\\|"            # Windows path
    r"^/[A-Za-z]|"              # Unix absolute path
    r"^https?://|"              # URL
    r"^[a-z_]+\(|"              # function call
    r"^\{|"                     # JSON/dict literal
    r"^[A-Z_]{2,}\s*=|"        # ENV_VAR = ...
    r"^[a-z]+:\s*`"             # key: `value` (config line)
)


def _clean_rule_text(text: str) -> str:
    """Strip markdown formatting and HTML comments from rule text."""
    text = _HTML_COMMENT_RE.sub("", text)
    text = _BACKTICK_RE.sub("", text)
    text = _MD_EMPHASIS_RE.sub("", text)
    return text.strip()


def _is_non_rule(text: str) -> bool:
    """Check if a line is a command, path, or config rather than a rule."""
    return bool(_NON_RULE_RE.match(text.strip()))


def _has_cjk(text: str) -> bool:
    """Check if text contains CJK characters (Japanese/Chinese/Korean)."""
    return any(0x3000 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF for c in text)


# CJK text packs more meaning per character; use lower threshold
_MIN_LEN_CJK = 5
_MIN_LEN_DEFAULT = 10


def parse_rules(text: str) -> list[Rule]:
    """Extract individual rules from markdown-formatted text.

    Recognises:
      - Bullet points (- or *)
      - Numbered lists (1. 2. etc.)
      - Headings as scope markers (## Section)
      - Plain paragraphs separated by blank lines

    Skips: code blocks, inline code, shell commands, paths, URLs.
    Minimum rule length: 10 chars (after cleaning).
    """
    lines = text.splitlines()
    rules: list[Rule] = []
    current_scope = ""
    in_code_block = False
    paragraph_buf: list[str] = []
    rule_idx = 0

    def _add_rule(raw: str) -> None:
        nonlocal rule_idx
        cleaned = _clean_rule_text(raw)
        min_len = _MIN_LEN_CJK if _has_cjk(cleaned) else _MIN_LEN_DEFAULT
        if min_len <= len(cleaned) <= _MAX_RULE_LEN and not _is_non_rule(cleaned):
            rules.append(Rule(id=f"rule-{rule_idx}", text=cleaned, scope=current_scope))
            rule_idx += 1

    def _flush_paragraph() -> None:
        joined = " ".join(paragraph_buf).strip()
        if joined:
            _add_rule(joined)
        paragraph_buf.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            _flush_paragraph()
            continue
        if in_code_block:
            continue

        heading_m = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_m:
            _flush_paragraph()
            current_scope = heading_m.group(2).strip()
            continue

        bullet_m = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet_m:
            _flush_paragraph()
            _add_rule(bullet_m.group(1).strip())
            continue

        numbered_m = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if numbered_m:
            _flush_paragraph()
            _add_rule(numbered_m.group(1).strip())
            continue

        if not stripped:
            _flush_paragraph()
            continue

        paragraph_buf.append(stripped)

    _flush_paragraph()
    return rules
