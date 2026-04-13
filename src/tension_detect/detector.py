"""Contradiction detection engine. Bilingual (English + Japanese)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .parser import Rule

# ---------------------------------------------------------------------------
# Direction classification
# ---------------------------------------------------------------------------

OPPOSITE_DIRECTIONS: list[tuple[str, str]] = [
    ("confirm", "execute"),
    ("preserve", "change"),
    ("wait", "act"),
    ("part", "whole"),
]

_JA_PATTERNS: dict[str, re.Pattern[str]] = {
    "confirm": re.compile(r"確認|聞[けい]|方針.*取[れる]|承認|ユーザーに.*求め|仰[ぐげ]"),
    "execute": re.compile(r"即[座実]|即.*[せしや]|結果を出|走[れる]|完遂|一気に|即座"),
    "preserve": re.compile(r"壊すな|変更するな|守[れる]|既存.*[を壊変]|維持|退行させるな|上書きするな"),
    "change": re.compile(r"改善|段階的|動くもの|磨き|リファクタ"),
    "wait": re.compile(r"待[てつ]|先[にに]|してから|完了.*から|前に"),
    "act": re.compile(r"宣言するな|やれ$|動け$|出せ$|止めるな|走らせろ|止まるな"),
    "part": re.compile(r"段階|一つ.*完了|単体|指定された範囲"),
    "whole": re.compile(r"全体.*[を見再]|全指摘|部分.*するな|全件"),
}

_EN_PATTERNS: dict[str, re.Pattern[str]] = {
    "confirm": re.compile(r"verify|check first|confirm|ask before|review before|get approval", re.I),
    "execute": re.compile(r"immediately|ship it|act fast|just do|move quickly|don.t wait", re.I),
    "preserve": re.compile(r"don.t break|maintain|keep existing|preserve|backward.?compat|stable", re.I),
    "change": re.compile(r"improve|refactor|modernize|upgrade|simplify|clean up", re.I),
    "wait": re.compile(r"before you|first,?\s|plan before|think before|don.t rush|step back", re.I),
    "act": re.compile(r"bias for action|move fast|ship|don.t overthink|just start|stop planning", re.I),
    "part": re.compile(r"small pr|incremental|one thing|focused|atomic|narrow scope", re.I),
    "whole": re.compile(r"big picture|holistic|end.to.end|full context|consider everything", re.I),
}


def classify_directions(text: str) -> set[str]:
    """Classify a rule text into action direction tags."""
    directions: set[str] = set()
    for tag, pat in _JA_PATTERNS.items():
        if pat.search(text):
            directions.add(tag)
    for tag, pat in _EN_PATTERNS.items():
        if pat.search(text):
            directions.add(tag)
    return directions


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

_JA_PARTICLE_RE = re.compile(
    r'[、。・\s\u3000（）「」/,.\-:;!?]|'
    r'(?<=[^\u3040-\u309F])[をにはがでとのもへから]{1,2}(?=[^\u3040-\u309F])|'
    r'(?<=.)[をにはがでとのもへ](?=.)'
)

_JA_STOP = {
    "しろ", "せよ", "やれ", "するな", "やるな", "出せ", "直せ",
    "動け", "避けよ", "控え", "走るな", "行け", "超えるな",
    "変えるな", "実行しろ", "確認しろ", "記録しろ",
    "ユーザー", "タスク", "作業", "実行", "確認", "提案",
    "コード", "修正", "バグ", "テスト", "セッション",
    "ファイル", "データ", "結果", "報告", "指示",
    "必ず", "即座", "自発", "自動", "最優先", "禁止",
    "場合", "状態", "問題", "対応", "処理", "機能",
    "ルール", "メモリ", "記録", "保存", "設定",
}

_EN_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "and", "but", "or", "nor", "not", "no", "so", "if", "then", "than",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
    "into", "about", "between", "through", "after", "before",
    "all", "any", "each", "every", "both", "few", "more", "most", "some",
    "such", "only", "very", "just", "also", "still",
    "code", "file", "use", "make", "keep", "don't", "always", "never",
    "when", "how", "why", "where",
    # Path/command/tool fragments (cause false positives)
    "bin", "src", "usr", "etc", "var", "tmp", "opt",
    "run", "dev", "npm", "pip", "git", "node", "python",
    "desktop", "users", "home", "documents",
    "cd", "mkdir", "echo", "cat", "grep", "sed",
}

# Markdown/formatting noise to strip before keyword extraction
_MD_NOISE_RE = re.compile(r"\*{1,3}|_{1,3}|`[^`]*`|#{1,4}\s")


def _is_english(text: str) -> bool:
    if not text:
        return False
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    return (ascii_chars / len(text)) > 0.7


def extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from rule text. Bilingual."""
    # Strip markdown noise first
    cleaned = _MD_NOISE_RE.sub(" ", text)
    if _is_english(cleaned):
        tokens = re.split(r'[\s,.:;!?\-/()"\[\]{}]+', cleaned.lower())
        return {t for t in tokens if len(t) >= 3 and t not in _EN_STOP}
    else:
        tokens = _JA_PARTICLE_RE.split(cleaned)
        result: set[str] = set()
        for t in tokens:
            t = t.strip()
            if len(t) >= 2:
                result.add(t)
                for sub in re.split(r'[をにはがでとのもへ]', t):
                    sub = sub.strip()
                    if len(sub) >= 2:
                        result.add(sub)
        return result - _JA_STOP


# ---------------------------------------------------------------------------
# Tension candidate detection
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TensionCandidate:
    """A detected contradiction between two rules."""

    rule_a: Rule
    rule_b: Rule
    shared_keywords: list[str]
    opposing_directions: list[str]
    score: float


def detect_tensions(rules: list[Rule]) -> list[TensionCandidate]:
    """Detect contradiction candidates between rules.

    Two strategies:
    1. Keyword overlap - rules about the same topic
    2. Direction opposition - rules pointing in opposite directions

    Returns candidates sorted by score (highest first), capped at 50.
    """
    kw_cache = {r.id: extract_keywords(r.text) for r in rules}
    dir_cache = {r.id: classify_directions(r.text) for r in rules}

    candidates: list[TensionCandidate] = []

    for i, a in enumerate(rules):
        for j, b in enumerate(rules):
            if j <= i:
                continue

            kw_a, kw_b = kw_cache[a.id], kw_cache[b.id]
            dirs_a, dirs_b = dir_cache[a.id], dir_cache[b.id]

            overlap = sorted(kw_a & kw_b) if kw_a and kw_b else []
            scope_match = bool(a.scope and b.scope and a.scope == b.scope)

            keyword_score = 0
            if scope_match and len(overlap) >= 2:
                keyword_score = len(overlap) + 5
            elif len(overlap) >= 3:
                keyword_score = len(overlap)

            direction_score = 0
            opposing: list[str] = []
            if dirs_a and dirs_b:
                for da, db in OPPOSITE_DIRECTIONS:
                    if (da in dirs_a and db in dirs_b) or (db in dirs_a and da in dirs_b):
                        direction_score += 8
                        opposing.append(f"{da} \u2194 {db}")

            score = max(keyword_score, direction_score)
            if keyword_score > 0 and direction_score > 0:
                score = keyword_score + direction_score

            if score < 2:
                continue

            candidates.append(TensionCandidate(
                rule_a=a, rule_b=b,
                shared_keywords=overlap,
                opposing_directions=opposing,
                score=score,
            ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:50]
