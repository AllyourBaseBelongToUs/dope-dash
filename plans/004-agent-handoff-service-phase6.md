# Plan: Agent Handoff Service (Phase 6)

**Status:** Deferred (Optional)
**Parent Plan:** 001-ui-navigation-issue-fix.md (Enhanced Session Reassignment)

## Context

This phase was part of the enhanced session reassignment plan but is marked as optional. It implements context handoff patterns from `cli-continues` research to provide seamless session transfers between agents.

---

## Phase 6: Context Handoff Service

### 6.1 Create Handoff Service

**File:** `backend/app/services/agent_handoff.py` (NEW)

```python
"""Agent handoff context service based on cli-continues patterns."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import json
from pathlib import Path

@dataclass
class ToolSummary:
    category: str
    count: int
    samples: list[str] = field(default_factory=list)

@dataclass
class HandoffContext:
    session_id: str
    source_agent_type: str
    source_agent_id: str
    target_agent_type: str
    target_agent_id: str
    summary: str
    tool_summaries: list[ToolSummary]
    files_modified: list[str]
    pending_tasks: list[str]
    decisions: list[str]
    recent_messages: list[dict]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class SummaryCollector:
    """Tracks agent actions during task execution."""

    def __init__(self, max_samples: int = 3):
        self._data: dict[str, dict] = {}
        self._files: set[str] = set()
        self._max_samples = max_samples

    def add(self, category: str, summary: str, file_path: str | None = None):
        if category not in self._data:
            self._data[category] = {"count": 0, "samples": []}

        self._data[category]["count"] += 1

        if len(self._data[category]["samples"]) < self._max_samples:
            self._data[category]["samples"].append(summary)

        if file_path:
            self._files.add(file_path)

    def get_summaries(self) -> list[ToolSummary]:
        return [
            ToolSummary(cat, data["count"], data["samples"])
            for cat, data in self._data.items()
        ]

    def get_files_modified(self) -> list[str]:
        return list(self._files)

def generate_handoff_markdown(context: HandoffContext) -> str:
    """Generate handoff document in cli-continues format."""
    lines = [
        "# Session Handoff Context",
        "",
        "## Session Overview",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Source** | {context.source_agent_type} ({context.source_agent_id}) |",
        f"| **Target** | {context.target_agent_type} ({context.target_agent_id}) |",
        f"| **Session ID** | {context.session_id} |",
        f"| **Created** | {context.created_at.isoformat()} |",
        "",
        "## Summary",
        f"> {context.summary}",
        "",
        "## Tool Activity",
    ]

    for ts in context.tool_summaries:
        samples = " · ".join(ts.samples[:3])
        lines.append(f"- **{ts.category}** (×{ts.count}): {samples}")

    if context.files_modified:
        lines.extend(["", "## Files Modified"])
        for f in context.files_modified:
            lines.append(f"- `{f}`")

    if context.pending_tasks:
        lines.extend(["", "## Pending Tasks"])
        for task in context.pending_tasks:
            lines.append(f"- [ ] {task}")

    if context.decisions:
        lines.extend(["", "## Key Decisions"])
        for decision in context.decisions:
            lines.append(f"- 💭 {decision}")

    lines.extend([
        "",
        "---",
        f"**You are continuing this session from {context.source_agent_type}. Pick up exactly where it left off.**"
    ])

    return "\n".join(lines)
```

### 6.2 Integration Points

1. **Session Reassign Endpoint** - Call handoff service when reassigning sessions
2. **Agent Wrapper** - Collect tool summaries during execution
3. **Session Storage** - Store handoff documents with session metadata

### 6.3 API Endpoint (Optional)

```python
# Add to session_control.py

@router.get("/{session_id}/handoff", response_model=dict[str, Any])
async def get_handoff_context(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get handoff context for a session transfer."""
    # Generate handoff document for the session
    pass
```

---

## Future Considerations

- **JSONL Storage** - Append-only session logs for streaming/parsing
- **Handoff UI** - Display handoff context in the assignment dialog
- **Automatic Context** - Auto-generate handoff on reassignment

---

## References

- `cli-continues` patterns: SummaryCollector, Handoff Markdown, Unified Session Interface
- DirectorsConsole CPE patterns (deferred to separate phase)
