# Atom 3: Query Interface for Ralph and Claude Code

**AOT Session:** 2026-01-23
**Agent:** deep-researcher
**Agent ID:** a8a3c52
**Complexity:** Medium
**Delegation:** Automatic (per AOT rules)

---

## Task Description

Design a text-based query interface for the Ralph Inferno monitoring dashboard.

**Requirements:**
1. **Query Ralph sessions** - Send natural language commands to active Ralph sessions
2. **Query Claude Code** - Integrate with Claude Code CLI for context-aware questions
3. **Command syntax** - Simple, intuitive commands (not full chat interface)
4. **Response format** - Structured JSON responses + human-readable display

**Examples of what users should be able to do:**
- "What is Ralph working on now?" → Status: "CR-02-typography, 67% complete"
- "Why did the last spec fail?" → Error: "Test failed because..."
- "Skip to next spec" → Action: "CR-02 marked as failed, starting CR-03"
- "Show me the logs for CR-01" → Display: Last 50 lines from CR-01 execution
- "How much time remaining?" → Estimate: "2 specs left, ~15 minutes"
- "What's the token usage?" → Cost: "73,914 tokens used, $0.78 spent"

**Deliverable:** A specification document covering:
- Command syntax (simple, not complex)
- API endpoints (if using REST) or WebSocket message types
- Response formats (JSON schema)
- Integration points with Ralph and Claude Code CLI

**Constraints:**
- Keep it practical - we're building this, not just theorizing
- Consider both implementation difficulty AND user value
- Reference the monitoring research doc we have

---

## Independence Analysis

This atom is **independent** because:
- Standalone API design exercise
- Doesn't depend on other atoms' output
- Can be implemented regardless of port architecture decisions

---

## Execution

**Delegated to:** deep-researcher agent (Agent ID: a8a3c52)

---

## Result

### Command Syntax (Simple, Not Complex)

```bash
# Core commands
ralph-query status              # Current status
ralph-query error CR-02         # Why did CR-02 fail?
ralph-query logs CR-01          # Show logs for CR-01
ralph-query tokens              # Token usage
ralph-query eta                 # Time remaining

# Control commands
ralph-query skip                # Skip to next spec
ralph-query stop                # Stop Ralph
ralph-query pause               # Pause after current spec
ralph-query resume              # Resume paused session
```

### Natural Language Aliases

```bash
ralph-query "what is Ralph working on"
ralph-query "why did the last spec fail"
ralph-query "how much time left"
```

### API Endpoints (REST)

- `POST /api/query` - Main query endpoint
- `GET /api/query/status` - Status
- `GET /api/query/error` - Errors
- `GET /api/query/logs` - Logs
- `GET /api/query/tokens` - Token usage
- `POST /api/query/skip` - Skip action
- `POST /api/query/stop` - Stop action

### Response Format (JSON)

```json
{
  "success": true,
  "data": { /* query-specific data */ },
  "meta": {
    "timestamp": "2026-01-23T10:30:00Z",
    "query": "status"
  }
}
```

### Integration Points

1. **Reads Ralph state files** - `.spec-checksums/`, `.ralph/logs/`, token tracking
2. **Control via tmux** - `tmux send-keys -t ralph` for actions
3. **Extends existing monitoring API** - Builds on the PostgreSQL/Express architecture

### Implementation Phases

1. **Phase 1 (MVP):** Read-only queries (status, logs, errors, tokens)
2. **Phase 2:** Control actions (skip, stop, retry)
3. **Phase 3:** Natural language processing and fuzzy matching

---

## How It Addresses User Requirements

✅ Query Ralph sessions - YES via status/logs/errors commands
✅ Query Claude Code - YES via integration wrapper
✅ Simple command syntax - YES (ralph-query <command>)
✅ Structured responses - YES (JSON with metadata)

---

## Success Criteria

✅ Command syntax defined (simple + natural language)
✅ API endpoints specified
✅ Response format (JSON schema) documented
✅ Integration points identified
✅ Implementation phases outlined
✅ Output saved to `.taskmaster/docs/research/ralph-query-interface-spec.md`

---

## Output Files

- Specification: `.taskmaster/docs/research/ralph-query-interface-spec.md`
