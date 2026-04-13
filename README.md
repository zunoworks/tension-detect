# tension-detect

Detect contradictions in your AI rules and generate judgment boundaries.

Your CLAUDE.md says "Write readable code" AND "Keep it DRY." Which one wins?

**tension-detect finds the contradictions and helps you define when each rule applies.**

## Install

```bash
pip install tension-detect
```

## Usage

### MCP Server (recommended)

```bash
claude mcp add tension-detect -- python -m tension_detect.server
```

Then ask your AI: "Analyze my CLAUDE.md for contradictions and generate judgment boundaries"

### CLI (detection only)

```bash
tension-detect .claude/CLAUDE.md
```

## How it works

Most tools detect contradictions and try to **resolve** them.
tension-detect turns them into **judgment boundaries**:

```
Rule A: "Write readable code"
Rule B: "Keep it DRY"
  -> Boundary: 3 lines or less -> readability. More -> DRY.
  -> Signal: Count the duplicated lines.
```

## Architecture

Zero-LLM server. The MCP server does detection. The client LLM generates boundaries at zero cost.

## License

MIT
