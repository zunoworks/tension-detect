# tension-detect

Your CLAUDE.md says "Ship fast" AND "Plan before coding." Which one wins?

**tension-detect finds the contradictions and tells you when each rule applies.**

## The Problem

Every team's AI rules contradict each other:

- "Write readable code" vs "Keep it DRY"
- "Review carefully" vs "Ship fast"
- "Keep PRs small" vs "Think big picture"

AI doesn't know which one to follow. It guesses. Sometimes it guesses wrong.

## The Solution

tension-detect turns contradictions into **judgment boundaries**:

```
Rule A: "Ship fast"
Rule B: "Plan before coding"
  -> Boundary: Production incident -> ship fast. Normal work -> plan first.
  -> Signal: Is there an open incident ticket?
```

Two rules become one decision. Your AI stops guessing.

## Install

```bash
pip install tension-detect
```

## Usage

### MCP Server (recommended)

Register once:

```bash
claude mcp add tension-detect -- python -m tension_detect.server
```

Then just ask:

```
You: Find contradictions in my CLAUDE.md and generate judgment boundaries
```

The AI will:
1. Read your rules file
2. Detect contradictions (server-side, no LLM needed)
3. Generate boundary conditions (using its own reasoning, zero cost)
4. Write the results back to your CLAUDE.md

#### What gets added to your CLAUDE.md

```markdown
<!-- tension-detect:start -->
## Judgment Boundaries

- **Ship fast** vs **Plan before coding**
  - Boundary: Production incident -> ship fast. Normal work -> plan first.
  - Signal: Is there an open incident ticket?

- **Keep PRs small** vs **Think big picture**
  - Boundary: Implementation -> small PRs. Design discussion -> big picture.
  - Signal: Are you writing code or discussing architecture?

- **Maintain backward compat** vs **Refactor aggressively**
  - Boundary: External API -> maintain compat. Internal code -> refactor.
  - Signal: Do external users depend on this?
<!-- tension-detect:end -->
```

Next session, your AI follows these boundaries instead of guessing.

### CLI (detection only)

```bash
tension-detect .claude/CLAUDE.md
```

Output:

```
Rules parsed: 12
Contradictions found: 3

  Tension 1/3:
    A: Ship fast, bias for action
    B: Plan before you start coding
    Directions: wait <-> act
```

CLI detects contradictions but doesn't generate boundaries. For that, use the MCP server.

## MCP Tools

| Tool | What it does | LLM needed? |
|------|-------------|-------------|
| `detect_tensions` | Find contradictions in rule text | No (server) |
| `analyze_file` | Read a file and detect contradictions | No (server) |
| `save_tension` | Save a boundary condition | No (server) |
| `get_tensions` | List saved boundaries | No (server) |
| `inject_tensions` | Write boundaries into a file | No (server) |

The server does detection and storage. Your AI does the thinking. Zero additional API cost.

## Supported Languages

English and Japanese. Detects 4 opposing direction pairs:

- **confirm vs execute** — verify first vs ship immediately
- **preserve vs change** — don't break it vs improve it
- **wait vs act** — plan first vs move fast
- **part vs whole** — small scope vs big picture

## Why Not Just Resolve Contradictions?

Because both rules are right.

A chef who only knows "add salt" is bad. A chef who only knows "less salt" is also bad. A chef who knows **when** to do which is a professional.

tension-detect teaches your AI when to do which.

## License

MIT
