"""Tests for contradiction detector."""

from tension_detect.parser import Rule
from tension_detect.detector import classify_directions, extract_keywords, detect_tensions


def test_ja_confirm():
    assert "confirm" in classify_directions("ユーザーに確認を取れ")


def test_ja_execute():
    assert "execute" in classify_directions("即座に実行しろ")


def test_ja_preserve():
    assert "preserve" in classify_directions("既存のコードを壊すな")


def test_ja_change():
    assert "change" in classify_directions("段階的に改善しろ")


def test_en_confirm():
    assert "confirm" in classify_directions("Always verify before making changes")


def test_en_execute():
    assert "execute" in classify_directions("Ship it immediately, don't wait")


def test_en_preserve():
    assert "preserve" in classify_directions("Don't break backward compatibility")


def test_en_change():
    assert "change" in classify_directions("Refactor legacy code when possible")


def test_en_wait_act():
    assert "wait" in classify_directions("Think before you code. Plan first.")
    assert "act" in classify_directions("Bias for action, ship fast, stop planning")


def test_en_part_whole():
    assert "part" in classify_directions("Keep PRs small and incremental")
    assert "whole" in classify_directions("Consider the big picture, think end-to-end")


def test_en_keywords():
    kw = extract_keywords("Write readable code with good tests")
    assert "readable" in kw
    assert "good" in kw
    assert "with" not in kw


def test_ja_keywords():
    kw = extract_keywords("コードは読みやすく書け")
    assert len(kw) > 0


def test_detect_english_contradiction():
    rules = [
        Rule(id="r1", text="Always verify before making changes", scope="Process"),
        Rule(id="r2", text="Ship it immediately, don't wait for approval", scope="Process"),
    ]
    candidates = detect_tensions(rules)
    assert len(candidates) >= 1
    assert len(candidates[0].opposing_directions) > 0


def test_detect_japanese_contradiction():
    rules = [
        Rule(id="r1", text="ユーザーに確認を取ってから作業を開始しろ"),
        Rule(id="r2", text="即座に結果を出せ、走れ"),
    ]
    candidates = detect_tensions(rules)
    assert len(candidates) >= 1


def test_no_contradiction():
    rules = [
        Rule(id="r1", text="Write tests for all new code"),
        Rule(id="r2", text="Use TypeScript instead of JavaScript"),
    ]
    candidates = detect_tensions(rules)
    assert len(candidates) == 0


def test_keyword_overlap_detection():
    rules = [
        Rule(id="r1", text="Write readable code, prioritize clarity and simplicity", scope="Quality"),
        Rule(id="r2", text="Keep code DRY, eliminate readable duplication for clarity", scope="Quality"),
    ]
    candidates = detect_tensions(rules)
    assert len(candidates) >= 1


def test_markdown_noise_excluded_from_keywords():
    kw = extract_keywords("**Always** write `tests` before shipping")
    assert "shipping" in kw


def test_path_fragments_excluded():
    kw = extract_keywords("Run npm install in the src/bin directory")
    assert "npm" not in kw
    assert "bin" not in kw
    assert "install" in kw
    assert "directory" in kw


def test_max_50_candidates():
    rules = [Rule(id=f"r{i}", text=f"Rule about topic {i % 3} and aspect {i % 5}") for i in range(30)]
    candidates = detect_tensions(rules)
    assert len(candidates) <= 50
