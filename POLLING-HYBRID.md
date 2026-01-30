# Polling + WebSocket Hybrid Design

**Decision:** Both modes coexist, user toggles between them

---

## User's Insight

> "Polling can be done with websocket, if we toggle the option, else yeah while in the dashboard websocket is dope with a button click (which it works and we want just sometimes know whats going on or sleeping its on demand web socket or when major changes happening then it sends an event to our dashboard and it gets updated. ANd since we anyway have a database where stuff is stored or state.json we can read anytime and wont lose progress right?"

**Key points:**
1. Both WebSocket and polling are valuable
2. Toggle between them based on context/use case
3. Database is primary storage (not just in-memory)
4. Won't lose progress even if disconnected

---

## Design

### Two Communication Modes

#### Mode 1: WebSocket (Real-Time Push)
- **When to use:** Actively monitoring, overnight builds with screen on
- **Behavior:** Server pushes updates immediately when events occur
- **Pros:** Real-time, low latency, efficient
- **Cons:** Requires persistent connection, breaks if network hiccups

#### Mode 2: Polling (On-Demand)
- **When to use:** Checking progress sporadically, connection unstable
- **Behavior:** Dashboard queries database every N seconds
- **Pros:** Works even if connection drops, simple, reliable
- **Cons:** Delayed updates (up to N seconds old), more server load

### Toggle UI

```
┌─────────────────────────────────────────────────────────────┐
│  Connection Mode                                    ●    │
│  ◉ Real-time (WebSocket)                                    │
│  ○ On-demand (Polling)                                    │
├─────────────────────────────────────────────────────────────┤
│  Current mode: Real-time                                    │
│  Update frequency: Push on event                           │
│  Last update: 2 seconds ago                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        PostgreSQL                             │
│  (Source of Truth - All Events Stored)                      │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ events table:                                            │   │
│  │  - spec_started                                         │   │
│  │  - spec_completed                                       │   │
│  │  - spec_failed                                         │   │
│  │  - intervention_request                                 │   │
│  │  - timeout_triggered                                    │   │
│  │  - session_heartbeat                                   │   │
│  │  All with timestamps                                     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ WebSocket Server (pushes events)                     │   │
│  │  → When: Event occurs                                  │   │
│  │  → To: Connected clients                                 │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ REST API (polling endpoint)                             │   │
│  │  GET /api/status?since=last-check                      │   │
│  │  → Returns: Events since timestamp                   │   │
│  │  → Polling interval: 5-30s (configurable)             │   │
│  │  → When: User switches to polling mode                  │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Dashboard                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  WebSocket Client:                                        │  │
│  │    - Auto-connects on page load                        │  │
│  │    - Receives push updates when in WebSocket mode      │  │
│  │    - Auto-reconnects on disconnect                    │  │
│  │    - Shows "Live" indicator when connected             │  │
│  │                                                           │  │
│  │  Polling Client:                                          │  │
│  │    - Runs interval query every 5s when in Polling mode  │  │
│  │    - Shows "Last update: X seconds ago" indicator     │  │
│  │                                                           │  │
│  │  UI State:                                                │  │  │
│  │    - Displays latest data from either client              │  │
│  │    - Shows connection status (Live/Delayed/Offline)        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Toggle Button:                                           │  │
│  │    [🔄 WebSocket] ← current mode (click to switch)    │  │
│  │    Shows "Live" indicator when receiving updates          │  │
│  │                                                           │  │
│  │ Connection Status Badge:                                   │  │
│ │    ● Live (green, pulsing)                               │  │
│ │    ● Delayed (yellow, shows delay in seconds)         │  │
│  │    ● Offline (gray, shows last update time)          │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Use Cases

### Use Case 1: Overnight Monitoring (WebSocket Mode)
```
Scenario: You start Ralph at 10pm, keep dashboard open on tablet

Mode: WebSocket (toggle ON)
Behavior:
  - Dashboard receives push updates all night
  - "Live" indicator (green, pulsing)
  - Zero delay when events occur
  - If network hiccups, auto-reconnects
User wakes up: Sees exactly what happened when it happened
```

### Use Case 2: Sporadic Checking (Polling Mode)
```
Scenario: At work, check Ralph progress occasionally during coffee breaks

Mode: Polling (toggle ON)
Behavior:
  - Dashboard queries database every 10s
  - "Last update: 15 seconds ago" indicator
  - Saves battery (no persistent connection)
  - Works even if you close/reopen browser
User checks: Sees data from last query, might be 10s stale
```

### Use Case 3: Unreliable Network (Automatic Fallback)
```
Scenario: Internet connection drops periodically

Mode: WebSocket initially
Behavior:
  - Dashboard detects connection dropped
  - Automatically switches to polling mode
  - Shows yellow badge: "Delayed mode (polling every 10s)"
  - When connection restored, asks user: "Switch back to real-time?"
```

### Use Case 4: On-Demand Sync (Button Click)
```
Scenario: Dashboard open but not actively monitoring

Mode: WebSocket (toggle ON)
Behavior:
  - No auto-updates, waits for events
  - User clicks [Refresh] button
  - Dashboard queries database for latest state
  - "Last update: Just now"
```

---

## Technical Implementation

### Frontend (TypeScript)

```typescript
// Connection Mode Type
type ConnectionMode = 'websocket' | 'polling';

interface ConnectionState {
  mode: ConnectionMode;
  isLive: boolean;           // WebSocket connected and receiving
  lastUpdate: Date;         // Last successful data fetch
  pollingInterval?: number; // Only in polling mode
}

class RalphDataClient {
  private mode: ConnectionMode = 'websocket';
  private wsClient: WebSocket | null = null;
  private pollingTimer: NodeJS.Timeout | null = null;
  pollingInterval: number = 10000; // 10s default

  // Toggle between modes
  setMode(mode: ConnectionMode) {
    this.mode = mode;
    if (mode === 'websocket') {
      this.connectWebSocket();
    } else {
      this.startPolling();
    }
  }

  // WebSocket mode
  private connectWebSocket() {
    this.wsClient = new WebSocket('ws://192.168.206.128:8001/ws');

    this.wsClient.onopen = () => {
      console.log('[WebSocket] Connected');
    };

    this.wsClient.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.updateUI(data);
      this.lastUpdate = new Date();
    };

    this.wsClient.onclose = () => {
      console.log('[WebSocket] Disconnected');
      // Auto-fallback to polling if configured
      if (this.autoFallback) {
        this.setMode('polling');
      }
    };
  }

  // Polling mode
  private startPolling() {
    this.pollingTimer = setInterval(async () => {
      const data = await fetch('/api/status?since=' + this.lastUpdate.toISOString())
        .then(r => r.json());

      this.updateUI(data);
      this.lastUpdate = new Date();
    }, this.pollingInterval);
  }

  // Manual refresh button
  async refresh() {
    const data = await fetch('/api/status').then(r => r.json());
    this.updateUI(data);
    this.lastUpdate = new Date();
    this.lastUpdate = new Date(); // "Just now"
  }

  // Update UI with received data
  private updateUI(data: any) {
    // React state update
    this.setState({ ralphData: data });
  }
}
```

### Backend (FastAPI)

```python
from fastapi import FastAPI
from fastapi.websockets import WebSocket
from datetime import datetime, timedelta

app = FastAPI()

# Database events table (source of truth)
# All events stored with timestamp, regardless of connection status

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Send initial state
    await websocket.send_json({
        "type": "connection_established",
        "data": await get_current_state()
    })

    # Subscribe to PostgreSQL notifications (LISTEN/NOTIFY)
    # This connection receives push updates
    try:
        while True:
            # Wait for database notification or timeout
            event = await wait_for_event_or_timeout(timeout=5)
            await websocket.send_json({
                "type": "event_update",
                "data": event
            })
    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/api/status")
async def get_status(since: str | None = None):
    """Polling endpoint - returns events since timestamp"""
    if since:
        since_dt = datetime.fromisoformat(since)
    else:
        since_dt = datetime.now() - timedelta(minutes=5)  # Default: last 5 min

    events = await get_events_since(since_dt)
    return {
        "events": events,
        "timestamp": datetime.now().isoformat(),
        "mode": "polling"
    }

# Database listener (background task)
async def event_listener():
    """Listens for new events and notifies WebSocket clients"""
    async for new_event in listen_for_events():
        await broadcast_to_websocket_clients(new_event)
```

---

## Toggle Behavior

### Switching WebSocket → Polling
```
User clicks: [Switch to Polling]

Dashboard:
  1. Closes WebSocket connection
  2. Shows yellow badge: "Delayed mode"
  3. Starts polling every 10s
  4. Shows "Last update: X seconds ago"

Backend:
  - WebSocket client disconnected
  - No action needed (polling endpoint always available)
```

### Switching Polling → WebSocket
```
User clicks: [Switch to Real-time]

Dashboard:
  1. Shows loading spinner
  2. Opens WebSocket connection
  3. Shows green badge: "Live" when connected
  4. Stops polling timer

Backend:
  - WebSocket client connects
  - Sends current state immediately
  - Begins push updates
```

---

## Benefits

### Why Both Modes?

**WebSocket strengths:**
- Real-time updates (critical for overnight monitoring)
- Lower server load (event-driven vs repeated queries)
- Better for "always-on" dashboard

**Polling strengths:**
- Works with unreliable connections
- Better battery life (no persistent connection)
- Simpler (no reconnection logic needed)
- On-demand sync (click refresh button)

### Database as Source of Truth

User's key insight: > "since we anyway have a database where stuff is stored or state.json we can read anytime and wont lose progress right?"

**Exactly right.** This is the key:

1. **All events stored in PostgreSQL** - Nothing is lost
2. **WebSocket pushes events** - For real-time updates
3. **Polling queries database** - For on-demand catch-up
4. **Either mode shows same data** - Just different delivery mechanism

**No progress lost** - Database persists everything regardless of connection mode.

---

## Configuration

### User Settings

```typescript
interface ConnectionSettings {
  preferredMode: 'websocket' | 'polling' | 'auto';
  pollingInterval: number;  // seconds (5-60)
  autoFallback: boolean;    // Auto-switch to polling on disconnect
  manualRefreshOnly: boolean;  // WebSocket for notifications only, manual refresh for data
}

// Default config
const defaultSettings: ConnectionSettings = {
  preferredMode: 'websocket',
  pollingInterval: 10,      // 10 seconds
  autoFallback: true,
  manualRefreshOnly: false
};
```

### UI Configuration

```
┌─────────────────────────────────────────────────────────────┐
│  Connection Settings                                      │
├─────────────────────────────────────────────────────────────┤
│  Preferred mode:                                           │
│  ◉ Auto (best mode for current conditions)               │
│  ○ WebSocket (real-time, requires stable connection)       │
│  ○ Polling (on-demand, works on any network)            │
│                                                              │
│  Polling interval: [5──●──] seconds                        │
│                                                              │
│  ☑ Auto-fallback to polling on WebSocket disconnect         │
│                                                              │
│  ☑ Manual refresh button in WebSocket mode (data on event)   │
│                                                              │
│           [Save]  [Cancel]                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Decision: Toggles vs Auto-Detection

### Option A: Auto-Detect Best Mode

```typescript
function detectOptimalMode(): ConnectionMode {
  // If WebSocket connected and stable → use WebSocket
  if (websocketConnected && connectionStable()) {
    return 'websocket';
  }

  // If on unstable network → use polling
  if (unstableNetwork()) {
    return 'polling';
  }

  // If dashboard not visible → use polling (save battery)
  if (!document.hasFocus()) {
    return 'polling';
  }

  return 'websocket'; // Default
}
```

### Option B: User Toggle (Recommended)

```typescript
// User explicitly chooses mode
// Dashboard respects user preference
// Shows indicator if current mode is suboptimal

function showModeRecommendation() {
  const optimal = detectOptimalMode();

  if (currentMode !== optimal) {
    showNotification(`Consider switching to ${optimal} mode for better performance`);
  }
}
```

**Decision:** User toggle (Option B)

**Why:**
- User control > automation for this use case
- User knows their context better than auto-detection
- Explicit toggle builds mental model
- Notification if suboptimal mode is active (but doesn't auto-switch)

---

## Summary

**Answer to user:** "both is best" - You nailed it.

- **WebSocket** for real-time when actively monitoring (overnight builds)
- **Polling** for on-demand checks or unreliable networks
- **Toggle between them** (no auto-switching, but shows recommendation)
- **Database is source of truth** (no progress lost either way)
- **Refresh button** always available for on-demand sync

**Key insight:** Database decouples event delivery from event storage. WebSocket/Polling just choose HOW to get events, not WHETHER events exist.

---

## Success Criteria

✅ Both modes coexist
✅ User toggles between modes
✅ WebSocket: Real-time push on events
✅ Polling: Database queries every N seconds
✅ Both show identical data
✅ Database is source of truth (no data loss)
✅ Refresh button always available
