"""Tests for rule parser."""

from tension_detect.parser import parse_rules


def test_bullet_points():
    text = "- Write readable code always\n- Keep it DRY everywhere\n- Test everything thoroughly"
    rules = parse_rules(text)
    assert len(rules) == 3
    assert rules[0].text == "Write readable code always"


def test_numbered_list():
    text = "1. First rule is important\n2. Second rule is important\n3. Third rule is important"
    rules = parse_rules(text)
    assert len(rules) == 3


def test_headings_as_scope():
    text = "## Code Quality\n- Write tests for everything\n## Performance\n- Optimize all hot paths"
    rules = parse_rules(text)
    assert len(rules) == 2
    assert rules[0].scope == "Code Quality"
    assert rules[1].scope == "Performance"


def test_code_blocks_skipped():
    text = "- This is a real rule\n```\n- Not a rule inside code\n```\n- Another real rule here"
    rules = parse_rules(text)
    assert len(rules) == 2


def test_japanese_rules():
    text = "- コードは読みやすく書け\n- DRYにしろ（繰り返すな）\n- テストは必ず書け"
    rules = parse_rules(text)
    assert len(rules) == 3


def test_paragraph_rules():
    text = "Write code that is easy to read and maintain.\n\nAlways prefer simplicity over cleverness in design."
    rules = parse_rules(text)
    assert len(rules) == 2


def test_short_lines_ignored():
    text = "- Too short\n- This is a real rule with enough text to pass"
    rules = parse_rules(text)
    assert len(rules) == 1


def test_empty_input():
    assert parse_rules("") == []


def test_mixed_format():
    text = "## Guidelines\n- Write readable code always\n- Keep it DRY everywhere\n\n## Process\n1. Plan before you start coding\n2. Ship small PRs regularly"
    rules = parse_rules(text)
    assert len(rules) == 4
    assert rules[0].scope == "Guidelines"
    assert rules[2].scope == "Process"


def test_markdown_bold_stripped():
    text = "- **Always** write tests before shipping code"
    rules = parse_rules(text)
    assert len(rules) == 1
    assert "**" not in rules[0].text


def test_inline_code_stripped():
    text = "- Use `pytest` for running all test suites"
    rules = parse_rules(text)
    assert len(rules) == 1
    assert "`" not in rules[0].text


def test_command_lines_skipped():
    text = "- Write clean code always\n- `cd /usr/bin && run test`\n- /Users/foo/bar/baz"
    rules = parse_rules(text)
    assert len(rules) == 1


def test_url_lines_skipped():
    text = "- Always review pull requests\n- https://example.com/docs"
    rules = parse_rules(text)
    assert len(rules) == 1
