# Atom 4: Control/Feedback Loop Integration

**AOT Session:** 2026-01-23
**Agent:** general-purpose
**Agent ID:** a0a6ff4
**Complexity:** Complex
**Delegation:** Automatic (per AOT rules)

---

## Task Description

Design how to integrate the mcp-feedback-enhanced concepts into the Ralph Inferno monitoring dashboard.

**Based on the research findings:**
1. Persistent Session Model - Single active session across spec executions
2. Real-Time Bidirectional Communication - WebSocket events for updates
3. Intelligent Environment Detection - Auto-detect VM vs local
4. Multi-Modal State Management - Session history, logging, audio alerts
5. Hierarchical Timeout Management - Per-spec → Session → Cleanup

**Your task:**
For EACH of the 5 concepts identified:
1. **Explain how it applies to Ralph Inferno** - Specific use case
2. **Define the integration approach** - How to implement (high-level)
3. **Prioritize** - Must-have (MVP) vs Nice-to-have (V2)

**Deliverable:** Integration plan document with:
- Table of 5 concepts with priority and complexity ratings
- MVP feature list (what to build first)
- Architecture diagram (text-based is fine)
- Technical considerations (WebSocket vs polling, state management, etc.)

**Constraints:**
- Be practical - we're building this
- Focus on VALUE to the user (you monitoring overnight builds)
- Consider effort vs impact for prioritization

---

## Independence Analysis

This atom is **dependent** on Atom 1 (mcp-feedback research) but the **integration design is independent** - can be done regardless of port architecture or query interface decisions.

---

## Execution

**Delegated to:** general-purpose agent (Agent ID: a0a6ff4)

---

## Result

### Concepts Integration Table

| # | Concept | Ralph Inferno Use Case | Priority | Complexity |
|---|---------|------------------------|----------|------------|
| 1 | **Persistent Session Model** | Single monitoring session across all spec executions | **Must Have (MVP)** | Medium |
| 2 | **Real-Time Bidirectional Communication** | WebSocket events for spec status, errors, and intervention requests | **Must Have (MVP)** | High |
| 3 | **Intelligent Environment Detection** | Auto-detect VM (192.168.206.128) vs local, auto-launch web UI | Nice-to-Have (V2) | Low |
| 4 | **Multi-Modal State Management** | Session history, audio alerts, configurable logging levels | Nice-to-Have (V2) | Medium |
| 5 | **Hierarchical Timeout Management** | Per-spec (3hr) → Session (24hr) → Cleanup | **Must Have (MVP)** | Low |

### MVP Feature List (What to Build First)

**Phase 1: Core Monitoring (Week 1)**
- Persistent Session - Single session across all spec executions
- Basic WebSocket - One-way: Ralph → Dashboard status updates
- Hierarchical Timeouts - Per-spec + session timeout handling
- Simple Dashboard UI - Progress bar, current spec, status list

**Phase 2: Enhanced Monitoring (Week 2)**
- Bidirectional WebSocket - Dashboard can send pause/resume/abort
- Error Notifications - Alert on test failures, parse errors
- Session History - Browse past sessions (localStorage)
- Logs View - View live logs from tmux pane

**Phase 3: Polish & V2 Features (Week 3)**
- Environment Detection - Auto VM vs local detection
- Audio Alerts - Sound on spec completion/failure
- Privacy Levels - Configurable logging verbosity
- Tunnel Setup - SSH tunnel instructions for remote

### Architecture Diagram

```
VM (192.168.206.128):
  Ralph Loop (existing)
    ↓ Instrumentation Points
  Monitoring Layer (NEW)
    ├── SessionManager (progress tracking)
    ├── TimeoutManager (resource management)
    └── WebSocketManager (event broadcasting)
    ↓ WebSocket (ws://192.168.206.128:8001)
Windows Machine:
  Dashboard (Next.js)
    ├── Session Progress
    ├── Spec Timeline
    ├── Live Logs
    └── Controls (Pause/Resume)
```

### Technical Considerations

**WebSocket vs. Polling:**
- **Decision:** WebSocket (MVP)
- **Why:** Real-time updates are core value; VM is on local network (no firewall issues)

**State Management:**
- **Active session:** In-memory (SessionManager singleton)
- **Session history:** JSON files (StateManager)
- **Future:** PostgreSQL for analytics

**Deployment:**
- VM hosts: Ralph sessions + Monitoring API + Dashboard UI
- Windows accesses via: `http://192.168.206.128:8003`

### Prioritized Implementation Order

1. **Session Manager** (Days 1-3) - Core to multi-spec monitoring
2. **Timeout Manager** (Days 4-6) - Prevents hung builds
3. **WebSocket Server + Basic Dashboard** (Days 7-10) - Real-time visibility
4. **Bidirectional Communication** (Days 11-13) - Intervention capabilities
5. **Error Handling** (Days 14-16) - Alert system
6. **Session History** (Days 17-18) - Past session browsing
7. **Environment Detection** (Days 19-20) - Auto-configuration
8. **Audio + Privacy** (Days 21-22) - Enhanced UX

---

## Success Criteria

✅ 5 concepts analyzed with priority ratings
✅ MVP feature list defined
✅ Architecture diagram provided
✅ Technical considerations documented
✅ Implementation order prioritized
✅ Output saved to `.taskmaster/docs/research/ralph-monitoring-integration-plan.md`

---

## Output Files

- Integration plan: `.taskmaster/docs/research/ralph-monitoring-integration-plan.md`
