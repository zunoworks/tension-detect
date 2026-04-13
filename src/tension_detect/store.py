"""Lightweight JSON store for resolved tensions."""

from __future__ import annotations

import fcntl
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

STORE_DIR = Path.home() / ".tension-detect"
TENSIONS_FILE = STORE_DIR / "tensions.json"


@dataclass(slots=True)
class Tension:
    """A resolved tension with boundary condition."""

    id: str
    rule_a_text: str
    rule_b_text: str
    boundary: str
    signal: str
    scope: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")


_TENSION_FIELDS = {f.name for f in __import__("dataclasses").fields(Tension)}


def load_tensions() -> list[Tension]:
    if not TENSIONS_FILE.exists():
        return []
    try:
        data = json.loads(TENSIONS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        tensions: list[Tension] = []
        for t in data:
            if not isinstance(t, dict):
                continue
            safe = {k: v for k, v in t.items() if k in _TENSION_FIELDS}
            if "id" in safe and "rule_a_text" in safe and "rule_b_text" in safe:
                tensions.append(Tension(**safe))
        return tensions
    except (json.JSONDecodeError, TypeError):
        return []


def save_tension(tension: Tension) -> str:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = STORE_DIR / ".lock"
    with open(lock_file, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            tensions = load_tensions()
            tensions.append(tension)
            TENSIONS_FILE.write_text(
                json.dumps([asdict(t) for t in tensions], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
    return tension.id
