# Spec 13: Agent Communication Bus

**Status:** Proposed
**Priority:** ⭐⭐⭐
**Complexity:** MEDIUM
**Duration:** 1 week
**Parent:** Phase 3 (Multi-Agent Support)
**Dependencies:** Spec 1 (Handoff Integration)

---

## Overview

### Objective

Enable real-time communication between agents working on related tasks. Create a publish/subscribe messaging system where agents can broadcast status, request assistance, share discoveries, and coordinate on shared files.

### Problem Statement

Currently:
- Agents work in isolation
- No inter-agent communication
- No way to request specialist help
- Coordination must be manual

After implementation:
- Agents can send messages to each other
- Message history persists
- Frontend shows message log
- Project-based channels

### Success Criteria

- [ ] Agents can send messages via WebSocket
- [ ] Message history persists to database
- [ ] Frontend displays message log
- [ ] Unavailable agents receive queued messages
- [ ] Project-based message channels

---

## Approach: WebSocket Relay

**Decision:** Use existing WebSocket infrastructure instead of Redis. Simpler, no new dependencies, sufficient for single-user deployment.

### Architecture

```
Agent A ──→ WebSocket Server ──→ Agent B
              ↓
         Message Log (DB)
              ↓
          Frontend Display
```

---

## Database Schema

### New Table: `agent_messages`

```sql
CREATE TABLE agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Sender
    sender_agent_id VARCHAR(255) NOT NULL,
    sender_agent_type VARCHAR(50) NOT NULL,
    sender_session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,

    -- Content
    message_type VARCHAR(50) NOT NULL, -- status, request, discovery, coordination
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Delivery
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agent_messages_project ON agent_messages(project_id, created_at DESC);
CREATE INDEX idx_agent_messages_type ON agent_messages(message_type);
```

---

## Message Types

| Type | Purpose | Example |
|------|---------|---------|
| `status` | Broadcast state updates | "Agent X now running session Y" |
| `request` | Request assistance | "Need frontend specialist for component Z" |
| `discovery` | Share findings | "Found bug in API endpoint" |
| `coordination` | Coordinate work | "About to modify config.yaml, any objections?" |

---

## API Changes

### WebSocket Handler

```python
# backend/app/websocket/agent_messages.py

@router.websocket("/ws/agent/messages/{project_id}")
async def agent_message_ws(
    websocket: WebSocket,
    project_id: uuid.UUID,
    agent_id: str,
):
    """WebSocket endpoint for agent messages."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            # Store message
            message = AgentMessage(
                project_id=project_id,
                sender_agent_id=agent_id,
                sender_agent_type=data.get("agent_type"),
                message_type=data.get("type", "status"),
                content=data.get("content"),
                metadata=data.get("metadata", {}),
            )
            db.add(message)
            await db.commit()

            # Broadcast to other agents in project
            await manager.broadcast_to_project(project_id, message, exclude=agent_id)

    except WebSocketDisconnect:
        manager.disconnect(agent_id, project_id)
```

---

## Frontend: Message Log

```typescript
// frontend/src/components/communication/AgentMessageLog.tsx

export function AgentMessageLog({ projectId }: { projectId: string }) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8001/ws/agent/messages/${projectId}`);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };

    return () => ws.close();
  }, [projectId]);

  return (
    <Card>
      <h2>Agent Messages</h2>
      <div className="space-y-2">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
      </div>
    </Card>
  );
}
```

---

## Testing Checklist

- [ ] Agent sends message, other agent receives
- [ ] Message persisted to database
- [ ] Frontend displays messages
- [ ] WebSocket reconnection works
- [ ] Message queue for offline agents

---

**Document Version:** 1.0
**Created:** 2026-02-28
**Status:** Ready for Implementation
