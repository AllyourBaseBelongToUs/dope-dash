# IDE AI Agent Session Storage Research

**Research Date:** 2026-02-22
**Purpose:** Investigate how IDE AI agents store session data for detection and monitoring

---

## Executive Summary

- **Cursor IDE** uses SQLite databases (`state.vscdb`) with well-documented key structures (`cursorDiskKV`, `composerData`, `bubbleId`) that can be parsed to extract session info
- **VS Code + Copilot** uses similar SQLite storage with `interactive.sessions` keys; Copilot Chat was open-sourced in June 2025
- **Trae IDE** (ByteDance) stores data locally at `%APPDATA%\Trae\` but specific database structure is not publicly documented
- **Zed Editor** uses a Sled binary database (not JSON/SQLite) at `~/.local/share/zed/`, making direct parsing more difficult
- **Detection method:** Process enumeration (`tasklist`/`ps`) combined with SQLite parsing can identify running sessions and their workspaces

---

## 1. Cursor IDE

### Storage Locations

| Platform | Path |
|----------|------|
| **Windows** | `%APPDATA%\Cursor\User\` |
| **macOS** | `~/Library/Application Support/Cursor/User/` |
| **Linux** | `~/.config/Cursor/User/` |

### Database Structure

#### Global Storage
- **Path:** `globalStorage/state.vscdb`
- **Contains:** AI full responses, individual messages (bubbles), session metadata
- **Key Table:** `cursorDiskKV`

#### Workspace Storage
- **Path:** `workspaceStorage/<hash>/state.vscdb`
- **Additional file:** `workspace.json` (records the actual project path)
- **Contains:** Chat lists and user messages specific to each project

### SQLite Key Structure

```sql
-- Get all composer/chat sessions
SELECT value FROM ItemTable WHERE key = 'composer.composerData';

-- Get individual messages for a session
SELECT key, value FROM cursorDiskKV
WHERE key LIKE 'bubbleId:<composerId>:%'
ORDER BY rowid ASC;
```

**Key Formats:**
- `composerData:<composerId>` - Session/conversation metadata
- `bubbleId:<composerId>:<bubbleId>` - Individual messages

### Data Schema

```
WORKSPACE DB (per-project):          GLOBAL DB (shared):
+-------------------------+         +-------------------------+
| composer.composerData   |         | cursorDiskKV            |
| - composerId            |   --->  | - bubbleId:chat1:msg1   |
| - name                  |   LINK  | - bubbleId:chat1:msg2   |
| - lastUpdatedAt         |         | - bubbleId:chat2:msg1   |
| - filesChangedCount     |         | ...                     |
+-------------------------+         +-------------------------+
```

### Python Parsing Example

```python
import sqlite3
import json

def parse_cursor_vscdb(file_path):
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()

    # Get composer sessions
    cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
    sessions = cursor.fetchone()

    # Get messages
    cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")
    messages = cursor.fetchall()

    conn.close()
    return sessions, messages
```

### Tools for Export

| Tool | Description | Link |
|------|-------------|------|
| **cursor-chat-export** | Python CLI to export chats to Markdown | [GitHub](https://github.com/somogyijanos/cursor-chat-export) |
| **cursor-history** | Structured extraction to knowledge base | Community tool |
| **SpecStory** | Cursor extension for auto-export | VS Code Marketplace |
| **WayLog** | Free extension for chat backup | VS Code Marketplace |

### Commands

```bash
# Discover all chats from all workspaces
./chat.py discover

# Export chats as Markdown
./chat.py export --output-dir "/path/to/output"

# Find which hash folder belongs to which project (macOS/Linux)
grep -R "project-name" ~/Library/Application\ Support/Cursor/User/workspaceStorage/*/workspace.json

# Find project (Windows PowerShell)
Get-ChildItem -Path "$env:APPDATA\Cursor\User\workspaceStorage" -Recurse -Filter "workspace.json" | Select-String "project-name"
```

---

## 2. VS Code + Copilot Chat

### Storage Locations

| Platform | Path |
|----------|------|
| **Windows** | `%APPDATA%\Code\User\` |
| **macOS** | `~/Library/Application Support/Code/User/` |
| **Linux** | `~/.config/Code/User/` |

### Copilot Chat Specific

- **Chat storage:** `%APPDATA%\Code\User\globalStorage\github.copilot-chat`
- **Database key:** `interactive.sessions` in `state.vscdb`

### Export Chat History

1. **Command Palette** -> `Chat: Export Chat...`
2. Right-click in Chat view -> `Copy All`
3. Use third-party tools like `copilot-chat-to-markdown`

### SQLite Query

```sql
SELECT value FROM ItemTable WHERE key = 'interactive.sessions';
```

### JSON Structure (Exported)

```json
{
  "session_id": "sess_abc123",
  "timestamp": 1717000000,
  "messages": [
    {
      "role": "user",
      "content": "Your question here"
    },
    {
      "role": "assistant",
      "content": "Copilot's response..."
    }
  ]
}
```

### VS Code Extension Storage APIs

```typescript
// Global storage (cross-workspace)
await context.globalState.update('lastUsedSetting', 'value');

// Workspace storage (project-specific)
await context.workspaceState.update('currentSessionId', 'abc123');

// File-based storage
const dataFile = vscode.Uri.joinPath(context.globalStorageUri, 'data.json');
await vscode.workspace.fs.writeFile(dataFile, writeData);
```

---

## 3. Trae IDE (ByteDance)

### Overview

Trae is an AI-native IDE developed by ByteDance with deep Chinese development scenario integration.

### Storage Locations

| Platform | Path |
|----------|------|
| **Windows** | `%APPDATA%\Trae\` |
| **macOS** | `~/.trae` or `~/Library/Application Support/Trae/` |
| **Linux** | `~/.trae` |

### Process Information

- **Process name:** "Trae" or "Trae Helper"
- **Binary paths (macOS):** `/Applications/Trae.app/Contents/MacOS/Trae`

### Data Collection Notes

- **Local-first** and **minimized data collection** principle
- Code files stored locally by default
- For indexing: files may be temporarily uploaded for embeddings, then deleted

### Unknowns

The search results **did not reveal**:
- Specific database file location on disk
- Session storage path details
- SQLite or other database file names used for agent sessions

### Investigation Approach

1. Check common locations:
   ```
   %APPDATA%\Trae\
   ~/Library/Application Support/Trae/
   ~/.trae/
   ```

2. Search for SQLite databases: `.sqlite` or `.db` files

3. Use filesystem monitoring:
   - **Windows:** Process Monitor
   - **macOS:** `fs_usage`
   - **Linux:** `inotifywait`

---

## 4. Zed Editor

### Storage Locations

| Platform | Config Path | Data Path |
|----------|-------------|-----------|
| **Linux** | `~/.config/zed/settings.json` | `~/.local/share/zed/` |
| **Linux (Flatpak)** | Container-specific | `~/.var/app/dev.zed.Zed/data/zed/` |
| **macOS** | `~/Library/Application Support/Zed/settings.json` | `~/Library/Application Support/Zed/` |
| **Windows** | `C:\Users\[Username]\AppData\Local\Zed` | Same |

### Database Technology

- Uses **Sled** database (high-performance embedded Rust database)
- **Binary format** (not JSON or SQLite)
- Historically used JSON, but migrated to binary format

### Key Limitations

- Binary format makes direct programmatic analysis difficult
- No public documentation on internal schema
- Must use "Open as Markdown" export feature for individual threads

### Export Method

Zed provides a small button at the right end of a thread to export as Markdown.

---

## 5. Process Detection Methods

### Windows (tasklist)

```batch
:: Check if VS Code is running
tasklist /FI "IMAGENAME eq Code.exe" /FO CSV

:: Check if Cursor is running
tasklist /FI "IMAGENAME eq Cursor.exe" /FO CSV

:: Check if Trae is running
tasklist /FI "IMAGENAME eq Trae.exe" /FO CSV

:: Combined check
tasklist | findstr "Code.exe Cursor.exe Trae.exe"
```

### Linux/macOS (ps)

```bash
# Check for running IDEs
ps aux | grep -E "code|cursor|trae|zed"

# Get full process info
ps -ef | grep -i cursor
```

### Process Names

| IDE | Process Name |
|-----|-------------|
| **VS Code** | `Code.exe` / `code` |
| **Cursor** | `Cursor.exe` / `cursor` |
| **Trae** | `Trae.exe` / `trae` |
| **Zed** | `zed` / `Zed` |
| **Windsurf** | `Windsurf.exe` / `windsurf` |

---

## 6. Detection Strategy Summary

### What We CAN Detect

| Information | Cursor | VS Code/Copilot | Trae | Zed |
|-------------|--------|-----------------|------|-----|
| **Process running** | Yes | Yes | Yes | Yes |
| **Number of windows** | Yes (process count) | Yes | Yes | Yes |
| **Project/workspace path** | Yes (workspace.json) | Yes (workspace.json) | Unknown | Unknown |
| **Session count** | Yes (SQLite) | Yes (SQLite) | Unknown | No (binary) |
| **Active session** | Maybe (timestamps) | Maybe | Unknown | Unknown |

### Detection Approach

1. **Process Enumeration**
   ```bash
   # Get all IDE processes
   tasklist /FI "IMAGENAME eq Code.exe" /FO CSV
   tasklist /FI "IMAGENAME eq Cursor.exe" /FO CSV
   ```

2. **Workspace Resolution**
   - Parse `workspaceStorage/*/workspace.json` to map hash folders to project paths
   - Cross-reference with running processes

3. **Session Extraction**
   - For Cursor/VS Code: Query `state.vscdb` SQLite databases
   - Use `composer.composerData` and `interactive.sessions` keys

4. **State Determination**
   - Check timestamps in session data
   - Compare with process start time
   - Look for "active" flags or recent activity

### Limitations

- **Zed**: Binary Sled database format prevents direct parsing
- **Trae**: Undocumented storage structure
- **Multi-window**: Each IDE window is a separate process but shares storage
- **Permissions**: May require elevated access to read application data

---

## 7. Implementation Recommendations

### For Cursor/VS Code Detection

```python
import sqlite3
import os
import json
from pathlib import Path

def detect_cursor_sessions():
    """Detect Cursor sessions on the system."""
    app_data = os.environ.get('APPDATA', '')
    workspace_storage = Path(app_data) / 'Cursor' / 'User' / 'workspaceStorage'

    sessions = []

    for workspace_dir in workspace_storage.iterdir():
        if not workspace_dir.is_dir():
            continue

        workspace_json = workspace_dir / 'workspace.json'
        state_db = workspace_dir / 'state.vscdb'

        if workspace_json.exists():
            with open(workspace_json) as f:
                workspace_info = json.load(f)

        if state_db.exists():
            conn = sqlite3.connect(str(state_db))
            cursor = conn.cursor()

            # Get session count
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
            result = cursor.fetchone()

            if result:
                sessions.append({
                    'workspace': workspace_info.get('folder'),
                    'session_data': result[0]
                })

            conn.close()

    return sessions
```

### For Cross-Platform Process Detection

```python
import subprocess
import platform

def get_running_ides():
    """Get list of running IDE processes."""
    system = platform.system()
    ides = ['Code', 'Cursor', 'Trae', 'zed', 'Windsurf']
    running = []

    if system == 'Windows':
        for ide in ides:
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {ide}.exe', '/FO', 'CSV'],
                capture_output=True, text=True
            )
            if ide in result.stdout:
                running.append(ide)
    else:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        for ide in ides:
            if ide.lower() in result.stdout.lower():
                running.append(ide)

    return running
```

---

## Sources

### Cursor IDE
- [Cursor Chat Export GitHub](https://github.com/somogyijanos/cursor-chat-export)
- [Cursor Forum - Chat History](https://forum.cursor.com/t/chat-history-folder/7653/2)
- [CSDN - Cursor History Export Guide](https://www.cnblogs.com/borui-coding-diary/p/19474492/cursor-history-exploration-tips)

### VS Code / Copilot
- [GitHub Community - Export Chat History](https://github.com/orgs/community/discussions/57190)
- [VS Code v1.102 Update - Copilot Open Source](https://code.visualstudio.com/updates/v1_102)
- [VS Code Chat Extensions Guide](https://code.visualstudio.com/api/extension-guides/chat)
- [CSDN - Copilot Chat to Markdown](https://blog.csdn.net/i042416/article/details/152003866)

### Trae IDE
- [Trae IDE Official](https://traeide.com/)
- [CSDN - Trae Configuration Path](https://blog.csdn.net/qq_37380802/article/details/149149913)
- [Unit221B Blog - Trae Data Collection](https://blog.unit221b.com/dont-read-this-blog/unveiling-trae-bytedances-ai-ide-and-its-extensive-data-collection-system)

### Zed Editor
- [GitHub Discussion #32335 - Conversation History](https://github.com/zed-industries/zed/discussions/32335)
- [GitHub Discussion #32293 - Config Layering](https://github.com/zed-industries/zed/discussions/32293)
- [CSDN - Zed Editor Configuration Guide](https://blog.csdn.net/gitblog_01179/article/details/152348233)

### Process Detection
- [CSDN - VS Code Process Detection](https://wenku.csdn.net/answer/6f160fda553d4f428b270952f6d54972)
- [GitHub Issue #64997 - Multi-Window Bug](https://github.com/Microsoft/vscode/issues/64997)

---

## Further Investigation Needed

1. **Trae IDE Database Structure**: Need filesystem exploration on actual Trae installation
2. **Zed Sled Database**: Check if there are any tools or libraries for reading Sled databases
3. **Real-time Monitoring**: Investigate file system watchers for live session detection
4. **Cross-IDE Session Correlation**: Methods to identify if multiple IDEs are working on same project
