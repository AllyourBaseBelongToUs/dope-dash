# LSP and Agent Detection Research

## Executive Summary

This comprehensive research covers multiple methods for detecting AI agents in IDEs and development environments:

1. **LSP (Language Server Protocol)** - Can be traced/monitored to detect language server activity, including AI-enhanced servers
2. **Process-based Detection** - Windows provides robust APIs (WMI, Win32_Process) for process tree analysis
3. **Port/WebSocket Monitoring** - IDE AI agents use specific ports and WebSocket connections
4. **Named Pipes** - Windows IPC mechanism that can be enumerated and monitored
5. **File Lock/Handle Monitoring** - Sysinternals tools provide real-time handle tracking
6. **ETW (Event Tracing for Windows)** - High-performance kernel-level event monitoring

---

## 1. Language Server Protocol (LSP) Trace

### What is LSP?

The Language Server Protocol (LSP) is a JSON-RPC 2.0 based protocol developed by Microsoft that defines communication between editors/IDEs and language servers. Key characteristics:

- **Transport Layer**: stdio, TCP sockets, or named pipes
- **Message Format**: JSON-RPC 2.0
- **Communication Pattern**: Request-Response and Notifications (bidirectional)

### LSP Architecture

```
+-------------------+     LSP/JSON-RPC     +------------------+
|  IDE/Editor       | <-----------------> | Language Server  |
|  (Client)         |    stdio/TCP/pipe   |  (Server)        |
+-------------------+                      +------------------+
```

### How LSP Works

1. **Initialization**: Client sends `initialize` request with capabilities
2. **Ready State**: Server responds with its capabilities
3. **Document Sync**: Client sends `textDocument/didOpen`, `textDocument/didChange`
4. **Features**: Server provides completion, diagnostics, hover, etc.

### LSP Trace Methods

#### VS Code Built-in Trace

In VS Code, enable LSP trace output:
```json
// settings.json
{
  "lsp.trace.server": "verbose"
}
```

Command palette: `Developer: Open Language Server Trace Output`

#### LSP Inspector Tool

Microsoft provides the **Language Server Protocol Inspector**:
- Repository: https://gitcode.com/microsoft/language-server-protocol-inspector
- Features:
  - Visualize LSP communication logs
  - Real-time filtering by query or language feature
  - Supports text and JSON log formats
  - Timeline view of interactions

### LSP Detection for Agent Discovery

**Can LSP trace detect AI agents?** Indirectly, yes:

1. **AI-enhanced language servers** (like Pyright with Copilot integration) show specific capabilities
2. **Custom AI language servers** can be detected by their registered name/GUID
3. **Port monitoring** can catch TCP-based LSP connections
4. **Process analysis** reveals language server subprocesses spawned by AI agents

**Limitations**: LSP itself doesn't expose AI agent identity directly. Detection requires combining with process/network analysis.

---

## 2. Process-Based Detection (Windows)

### Windows Process Tree Analysis

Windows maintains parent-child process relationships accessible via multiple APIs:

#### Method 1: WMI (Windows Management Instrumentation)

```powershell
# Get process with parent PID
Get-WmiObject Win32_Process | Select-Object Name, ProcessId, ParentProcessId

# Query specific process parent
Get-WmiObject -Query "SELECT ParentProcessId FROM Win32_Process WHERE ProcessId = 1234"

# Find children of a process
Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq 1234 }
```

#### Method 2: WMIC Command

```cmd
# Get parent process ID
wmic process where ProcessId=1234 get ParentProcessId

# Get process tree
wmic process get name,parentprocessid,processid

# Get command line
wmic process where ProcessId=1234 get CommandLine
```

#### Method 3: PowerShell Recursive Tree

```powershell
function Show-ProcessTree {
    param([int]$pid, [string]$indent = "")
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "$indent$($process.Name) (PID: $($process.Id))"
        $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $pid }
        foreach ($child in $children) {
            Show-ProcessTree -pid $child.ProcessId -indent "$indent  "
        }
    }
}
```

#### Method 4: Process Explorer (Sysinternals)

- GUI tool showing full process tree
- Displays parent PID in Properties > Image tab
- Can search by PID, name, or handle
- Download: `winget install Microsoft.Sysinternals.ProcessExplorer`

### Detecting Claude Code Processes

Claude Code on Windows typically runs as:
- `node.exe` with command line containing `claude` or specific paths
- May spawn subagents as child processes
- Check command line arguments via:
```cmd
wmic process where "name='node.exe'" get CommandLine,ProcessId
```

### Detecting Multiple Claude Code Sessions

Each Claude Code session runs in separate process tree:
1. Get all `node.exe` processes with Claude-related command lines
2. Group by parent process or working directory
3. Use timestamp and memory usage to distinguish sessions

---

## 3. Port and WebSocket Detection

### Common Ports for IDE AI Agents

| Agent/Service | Typical Port(s) | Protocol |
|---------------|-----------------|----------|
| GitHub Copilot | 443 (HTTPS), various ephemeral | HTTPS/WSS |
| VS Code Remote | Random ephemeral (e.g., 63574) | WebSocket |
| Claude Code | MCP server dependent | stdio/WebSocket |
| MCP Servers | Custom (e.g., 5555, 8080) | WebSocket/SSE |

### Port Discovery Commands

```cmd
# List all listening ports with PIDs
netstat -ano | findstr LISTENING

# Find process using specific port
netstat -ano | findstr :443

# PowerShell alternative
Get-NetTCPConnection -State Listen | Select-Object LocalPort,OwningProcess
```

### WebSocket Connection Detection

1. **Resource Monitor**:
   - Open `resmon.exe`
   - CPU tab > Associated Handles
   - Search for "WebSocket" or process name

2. **Process Explorer**:
   - Ctrl+F > Find Handle or DLL
   - Search for "WebSocket" or port number

3. **Network monitoring**:
   - Wireshark: Filter by `websocket` protocol
   - TCPView (Sysinternals): Real-time connection view

### MCP Server Detection

Model Context Protocol (MCP) servers can use:
- **stdio**: Communication via stdin/stdout (harder to detect)
- **SSE (Server-Sent Events)**: HTTP-based, check for persistent connections
- **WebSocket**: Check for WSS connections

MCP Inspector tool: `npx @modelcontextprotocol/inspector`
- Default UI: http://127.0.0.1:6274
- Proxy: http://127.0.0.1:6277

---

## 4. Named Pipes Detection (Windows)

### What are Named Pipes?

Named pipes are Windows IPC (Inter-Process Communication) mechanism:
- Path format: `\\.\pipe\PipeName`
- Local access: `\\.\pipe\name`
- Remote access: `\\ServerName\pipe\name`
- Implemented by NPFS.SYS (Named Pipe File System driver)

### Listing Named Pipes

#### PowerShell (v3+)
```powershell
# List all named pipes
Get-ChildItem \\.\pipe\

# Alternative method
[System.IO.Directory]::GetFiles("\\.\pipe\")
```

#### PipeList (Sysinternals)
```cmd
pipelist.exe
```
Shows:
- Pipe name
- Maximum instances
- Active instances

#### Chrome Browser
Address bar: `file://.//pipe//`

#### Process Explorer
Find > Handle or DLL > Search `\Device\NamedPipe`

### Named Pipe Monitoring

For monitoring pipe activity:
1. **PipeViewer**: https://gitcode.com/gh_mirrors/pi/PipeViewer
   - Real-time data stream monitoring
   - Multiple data format views
   - Filtering capabilities

2. **ETW tracing**: Enable `Microsoft-Windows-Kernel-NamedPipe` provider

### Common Named Pipes for AI/Development

```
VSCode-specific pipes:
\\.\pipe\vscode-ipc-*
\\.\pipe\vscode-language-*

Language servers:
\\.\pipe\*-language-server

General development:
\\.\pipe\eslint-server
\\.\pipe\typescript-server
```

### Programmatic Named Pipe Detection

```python
# Python example
import win32pipe
import win32file

PIPE_NAME = r'\\.\pipe\test_pipe'

# Create named pipe
named_pipe = win32pipe.CreateNamedPipe(
    PIPE_NAME,
    win32pipe.PIPE_ACCESS_DUPLEX,
    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_WAIT,
    win32pipe.PIPE_UNLIMITED_INSTANCES,
    65535, 65535, 500, None
)
```

---

## 5. File Lock and Handle Monitoring

### Windows Handle Basics

A **handle** is a reference to a system resource:
- Files
- Registry keys
- Mutexes
- Events
- Ports

When a file is "locked," a process holds an open handle to it.

### Detecting File Locks

#### Method 1: Resource Monitor (Built-in)

1. Open `resmon.exe` (Win+R > resmon)
2. CPU tab > Associated Handles
3. Search by filename
4. Shows process name, PID, handle name

#### Method 2: Handle.exe (Sysinternals)

```cmd
# Find who has a file open
handle.exe "path\to\file.log"

# Find all handles containing string
handle.exe "partial_name"

# List handles for specific process
handle.exe -p 1234
handle.exe -p processname.exe

# Close handle (DANGEROUS!)
handle.exe -c <HandleID> -p <PID>
```

#### Method 3: Process Explorer

1. Open `procexp.exe` (run as admin)
2. Ctrl+F > Find Handle or DLL
3. Enter filename or pattern
4. Results show process and handle details

#### Method 4: openfiles (Built-in, requires setup)

```cmd
# Enable (requires restart)
openfiles /local on

# Query open files
openfiles /query
```

### Common Lock Scenarios for AI Agents

1. **Log files**: Agent writes to session logs
2. **Config files**: `.claude/` directory files
3. **Project files**: IDE workspace files
4. **MCP state**: IPC files for MCP servers

### File Monitor Tools

**Process Monitor (Sysinternals)**:
- Real-time file system activity
- Filter by path, process, operation
- Capture stack traces

```cmd
# Download via winget
winget install Microsoft.Sysinternals.ProcessMonitor
```

---

## 6. ETW (Event Tracing for Windows)

### What is ETW?

ETW is Windows' high-performance event tracing infrastructure:
- Kernel-level buffering
- Minimal performance impact
- Real-time or file-based logging
- .etl file format for traces

### ETW Components

```
+-------------+     +----------+     +------------+
|  Provider   | --> |  Session | --> |  Consumer  |
| (Event src) |     | (Buffer) |     | (Analysis) |
+-------------+     +----------+     +------------+
```

1. **Provider**: Generates events (app, driver, kernel)
2. **Session**: Buffers events in kernel, writes to file
3. **Controller**: Manages sessions (start/stop/configure)
4. **Consumer**: Reads and processes events

### ETW Tools

#### logman (Built-in)

```cmd
# List all providers
logman query providers

# List active sessions
logman query -ets

# Create trace session
logman create trace MyTrace -o output.etl -p "ProviderName" 0xffffffff 0xff

# Start/stop trace
logman start MyTrace
logman stop MyTrace

# Delete session
logman delete MyTrace
```

#### Performance Monitor (perfmon)

GUI for ETW session management:
- Run `perfmon`
- Data Collector Sets > User Defined

#### Windows Performance Recorder/Analyzer (WPR/WPA)

```cmd
# Install via Windows ADK
# Record performance
wpr -start GeneralProfile

# Stop and save
wpr -stop output.etl

# Analyze
wpa output.etl
```

### Process Monitoring with ETW

#### Key Providers for Process Events

```
Microsoft-Windows-Kernel-Process
Microsoft-Windows-Kernel-ProcessIds
Microsoft-Windows-Diagnostics-LoggingChannel
```

#### ETW Process Events

- Process start/stop
- Thread creation/deletion
- Image (DLL) load
- Handle creation

### ETW for Agent Detection

```cmd
# Trace process events
logman create trace AgentTrace -o agent.etl -p "Microsoft-Windows-Kernel-Process" 0xffffffff 0xff -nb 16 16 -bs 1024 -max 2048
logman start AgentTrace

# ... reproduce activity ...

logman stop AgentTrace

# Convert to readable format
tracerpt agent.etl -o agent.evtx -of EVTX
```

### Process Monitor X v2

Modern ETW-based process monitor:
- Repository: https://gitcode.com/gh_mirrors/pr/ProcMonXv2
- Features:
  - File operation monitoring
  - Registry access
  - Network activity
  - No kernel driver required

---

## 7. IDE AI Agent Specifics

### VS Code + Copilot Architecture

```
+-------------------+     HTTPS/443     +------------------+
|  VS Code          | ----------------> | Copilot API      |
|  (Extension Host) | <---------------- | (GitHub Cloud)   |
+-------------------+     WSS Stream    +------------------+
         |
         v (LSP/stdio)
+-------------------+
| Language Servers  |
| (TypeScript, etc) |
+-------------------+
```

### Communication Protocols

| Use Case | Protocol | Notes |
|----------|----------|-------|
| Code completion | HTTPS POST | Request-response |
| Chat streaming | WSS | Real-time token stream |
| Language features | LSP/stdio | Local IPC |
| MCP tools | stdio/SSE/WSS | Configurable |

### VS Code Ports

- **Copilot**: api.enterprise.githubcopilot.com:443
- **Remote SSH/WSL**: Ephemeral WebSocket ports
- **Debug**: Node.js inspector on localhost:9229

### Detection Strategy for AI Agents

1. **Process Detection**:
   ```powershell
   # Find VS Code with Copilot
   Get-Process | Where-Object {$_.ProcessName -like "*code*"} | ForEach-Object {
       $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
       if ($cmd -match "copilot|github") { Write-Host "$($_.Name) [$($_.Id)]: $cmd" }
   }
   ```

2. **Network Detection**:
   ```powershell
   # Find connections to Copilot endpoints
   Get-NetTCPConnection | Where-Object { $_.RemoteAddress -match "githubcopilot" }
   ```

3. **Handle Detection**:
   ```cmd
   handle.exe -p code.exe | findstr /i "copilot"
   ```

---

## 8. Practical Detection Implementation

### Combined Detection Script (PowerShell)

```powershell
function Detect-AIAgents {
    $results = @()

    # 1. Process-based detection
    $nodeProcesses = Get-Process node -ErrorAction SilentlyContinue
    foreach ($proc in $nodeProcesses) {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)").CommandLine
        if ($cmd -match "claude|copilot|cursor|agent") {
            $results += [PSCustomObject]@{
                Type = "Process"
                Name = $proc.ProcessName
                PID = $proc.Id
                Detail = $cmd.Substring(0, [Math]::Min(200, $cmd.Length))
            }
        }
    }

    # 2. Named pipe detection
    $pipes = Get-ChildItem \\.\pipe\ -ErrorAction SilentlyContinue
    foreach ($pipe in $pipes) {
        if ($pipe.Name -match "vscode|language|lsp|mcp|claude") {
            $results += [PSCustomObject]@{
                Type = "NamedPipe"
                Name = $pipe.Name
                PID = "N/A"
                Detail = $pipe.FullName
            }
        }
    }

    # 3. Network connection detection
    $connections = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc.ProcessName -match "code|node|Code") {
            if ($conn.RemotePort -in @(443, 8080, 3000) -or $conn.RemoteAddress -match "github|anthropic|openai") {
                $results += [PSCustomObject]@{
                    Type = "Network"
                    Name = $proc.ProcessName
                    PID = $conn.OwningProcess
                    Detail = "$($conn.LocalAddress):$($conn.LocalPort) -> $($conn.RemoteAddress):$($conn.RemotePort)"
                }
            }
        }
    }

    return $results | Format-Table -AutoSize
}

Detect-AIAgents
```

### Handle Monitoring Script

```powershell
# Requires handle.exe from Sysinternals
function Get-FileLocks {
    param([string]$Path)

    $handleOutput = & handle.exe $Path 2>&1
    $handleOutput | ForEach-Object {
        if ($_ -match "^(\S+)\s+pid:(\d+)\s+type:(\S+)\s+([A-F0-9]+):\s+(.+)$") {
            [PSCustomObject]@{
                Process = $Matches[1]
                PID = $Matches[2]
                Type = $Matches[3]
                Handle = $Matches[4]
                Resource = $Matches[5]
            }
        }
    }
}
```

---

## 9. Comparison of Detection Methods

| Method | Reliability | Performance | Complexity | Use Case |
|--------|-------------|-------------|------------|----------|
| Process Tree | High | Excellent | Low | Basic agent detection |
| Named Pipes | Medium | Good | Medium | IPC monitoring |
| Port Monitoring | High | Good | Low | Network agents |
| Handle Monitoring | High | Fair | Medium | File locks |
| ETW Tracing | Very High | Excellent | High | Detailed analysis |
| LSP Trace | Low | Good | Medium | Language servers |

---

## 10. Recommendations

### For Basic Detection
1. Use **Process Tree** analysis via WMI/PowerShell
2. Combine with **command line inspection** for node.exe processes
3. Check for **parent-child relationships** to identify sessions

### For Comprehensive Monitoring
1. Deploy **ETW tracing** for kernel-level visibility
2. Use **Process Monitor** for real-time file/registry activity
3. Monitor **named pipes** for IPC communication
4. Track **network connections** to known AI API endpoints

### For Windows Development
1. Install **Sysinternals Suite**: `winget install Microsoft.Sysinternals.SysinternalsSuite`
2. Key tools: Process Explorer, Handle, PipeList, Process Monitor
3. Use **Resource Monitor** for quick file lock checks

---

## 11. Sources and References

### LSP Documentation
- [Language Server Protocol Specification](https://microsoft.github.io/language-server-protocol/)
- [LSP Inspector](https://gitcode.com/microsoft/language-server-protocol-inspector)
- [VS Code LSP Extension Guide](https://learn.microsoft.com/en-us/visualstudio/extensibility/adding-an-lsp-extension)

### Windows Process Management
- [Windows WMI Documentation](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process)
- [Process Explorer](https://learn.microsoft.com/en-us/sysinternals/downloads/process-explorer)
- [Tasklist Command Reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tasklist)

### Named Pipes
- [Named Pipe Functions](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/)
- [PipeList Tool](https://learn.microsoft.com/en-us/sysinternals/downloads/pipelist)
- [PipeViewer](https://gitcode.com/gh_mirrors/pi/PipeViewer)

### ETW Documentation
- [Event Tracing for Windows](https://learn.microsoft.com/en-us/windows/win32/etw/event-tracing-portal)
- [ETW Managed Reference](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.tracing)
- [Process Monitor X v2](https://gitcode.com/gh_mirrors/pr/ProcMonXv2)

### Handle and File Lock
- [Handle.exe](https://learn.microsoft.com/en-us/sysinternals/downloads/handle)
- [Process Monitor](https://learn.microsoft.com/en-us/sysinternals/downloads/procmon)
- [File Lock Detection Guide](https://techcommunity.microsoft.com/blog/itopstalkblog/identify-which-process-is-blocking-a-file-in-windows/4432635)

### MCP and AI Agents
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Chrome MCP Server](https://www.npmjs.com/package/@railsblueprint/chrome-mcp)

---

*Research completed: 2026-02-22*
*Focus: Windows-specific detection methods for IDE AI agents*
