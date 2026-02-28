# MCP Feedback Integration Guide

## What This Is

An MCP (Model Context Protocol) server that lets AI agents request feedback from users via the dope-dash dashboard instead of opening a separate UI window.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          YOUR MACHINE                                     │
│                                                                           │
│  ┌─────────────────┐      stdio       ┌────────────────────────────┐     │
│  │  Claude Code    │ ←──────────────→ │ dope_dash_mcp.py           │     │
│  │  (CLI/IDE)      │                  │ (MCP Server)               │     │
│  │                 │                  │                            │     │
│  │  Calls:         │                  │  Tool: interactive_feedback│     │
│  │  interactive_   │                  │                            │     │
│  │  feedback()     │                  └────────────┬───────────────┘     │
│  └─────────────────┘                               │                      │
│                                                    │ WebSocket            │
│                                                    ▼                      │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                    DOPE-DASH BACKEND (:8001)                     │     │
│  │                                                                   │     │
│  │  /feedback/ws/mcp     ← MCP server connects here                 │     │
│  │  /feedback/ws         ← Dashboard connects here                  │     │
│  │  /feedback/{id}/submit ← User submits feedback here              │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                    │                      │
│                                                    │ WebSocket broadcast  │
│                                                    ▼                      │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                    DOPE-DASH FRONTEND                            │     │
│  │                                                                   │     │
│  │  FeedbackPanel.tsx  ← Popup appears when AI requests input      │     │
│  │                                                                   │     │
│  │  ┌────────────────────────────────────────┐                      │     │
│  │  │  🤖 AI Needs Your Input                │                      │     │
│  │  │                                        │                      │     │
│  │  │  "Should I continue with the           │                      │     │
│  │  │   refactoring or wait for tests?"      │                      │     │
│  │  │                                        │                      │     │
│  │  │  [Continue] [Wait] [Cancel]            │                      │     │
│  │  │                                        │                      │     │
│  │  │  ⏱️ 4:32 remaining                     │                      │     │
│  │  └────────────────────────────────────────┘                      │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install mcp websockets
```

### 2. Add to Claude Code Settings

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "dope-dash-feedback": {
      "command": "python",
      "args": ["C:\\Users\\EddyE\\Desktop\\Web Projects\\dope-dash\\backend\\mcp\\dope_dash_mcp.py"],
      "env": {
        "DOPE_DASH_WS_URL": "ws://localhost:8001/feedback/ws/mcp",
        "DOPE_DASH_FEEDBACK_TIMEOUT": "300"
      }
    }
  }
}
```

### 3. Start dope-dash Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

### 4. Start dope-dash Frontend

```bash
cd frontend
npm run dev
```

### 5. Restart Claude Code

The MCP server will be loaded on next startup.

## Usage

Once configured, AI agents (including Claude Code) can use the `interactive_feedback` tool:

```python
# The AI agent calls this when it needs user input:
result = interactive_feedback(
    message="I found 3 potential solutions. Which should I implement?",
    options=["Solution A (fastest)", "Solution B (most robust)", "Solution C (best tested)"],
    timeout=300,  # 5 minutes
    project_directory="/path/to/project"
)
```

The request appears in dope-dash dashboard as a popup. User responds, and the AI receives the feedback.

## CLI vs IDE Support

| Environment | Works? | Notes |
|-------------|--------|-------|
| **Claude Code CLI** | ✅ Yes | Full support via MCP |
| **Cursor IDE** | ✅ Yes | If MCP is configured in Cursor |
| **VS Code + Cline** | ✅ Yes | If MCP is configured |
| **Windsurf** | ✅ Yes | If MCP is configured |
| **Any MCP client** | ✅ Yes | Standard MCP protocol |

**Key difference from original**: The feedback appears in dope-dash dashboard, NOT in the IDE/CLI itself. This is a feature - you get a consistent UI regardless of which tool the AI is running in.

## Comparison to interactive-feedback-mcp

| Aspect | interactive-feedback-mcp | dope-dash-mcp |
|--------|-------------------------|---------------|
| **UI** | Opens separate browser window | Integrated in dashboard |
| **Context** | User loses current context | Stays in dashboard |
| **State** | Separate session | Unified with agent monitoring |
| **Multi-tool** | Different UI per tool | Same dashboard for all |
| **Setup** | Install separately | Already part of dope-dash |

## Configuration Options

Environment variables for the MCP server:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOPE_DASH_WS_URL` | `ws://localhost:8001/feedback/ws/mcp` | WebSocket endpoint |
| `DOPE_DASH_FEEDBACK_TIMEOUT` | `300` | Default timeout (seconds) |

Dashboard settings (in Settings → AI Feedback):

- **Enable/Disable**: Toggle MCP feedback integration
- **Desktop Notifications**: Alert when AI requests feedback
- **Fallback to Local**: Use local UI if dashboard unavailable
- **Timeout**: Default time to wait for user response

## Troubleshooting

### MCP Server Not Loading

1. Check Python path in settings.json
2. Verify `mcp` package installed: `pip show mcp`
3. Check Claude Code logs

### Dashboard Not Receiving Requests

1. Verify backend is running on port 8001
2. Check WebSocket connection in browser DevTools
3. Ensure FeedbackPanel is mounted (check layout.tsx)

### Timeout Issues

1. Increase `DOPE_DASH_FEEDBACK_TIMEOUT` env var
2. Check dashboard settings for timeout value
3. Verify network connectivity between MCP server and backend

## Files

```
backend/
├── mcp/
│   ├── __init__.py
│   └── dope_dash_mcp.py      # MCP server implementation
├── app/
│   └── api/
│       └── feedback.py        # WebSocket endpoints

frontend/
├── src/
│   ├── components/
│   │   └── feedback/
│   │       ├── FeedbackPanel.tsx  # Popup component
│   │       └── index.ts
│   ├── store/
│   │   └── feedbackSettingsStore.ts
│   └── app/
│       └── settings/
│           └── page.tsx      # AI Feedback tab
```

## Future Enhancements

- [ ] Image attachment support in feedback
- [ ] Feedback history log
- [ ] Multiple simultaneous requests queue
- [ ] Sound notifications per request
- [ ] Request priority levels
