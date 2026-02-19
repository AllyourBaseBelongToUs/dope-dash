# Phase 6: Rate Limit & Quota Management

**Status:** Design Complete - Ready for Implementation
**Date:** 2026-01-30
**Phase:** 6 of 6 (Advanced Automation)
**Dependencies:** Phases 1-5 must be complete
**Timeline:** 1 week

---

## Executive Summary

**Rate Limit & Quota Management** provides intelligent API rate limit protection, real-time quota monitoring, and automated safeguards for the Dope-Dash. It prevents 429 errors, manages request throttling, and ensures projects don't exhaust their API quotas unexpectedly.

**Key Philosophy:** "Set and forget" quota protection - monitor, alert, throttle, and auto-pause automatically based on configurable thresholds.

**Why a Separate Phase:**
- Builds on Phase 5's Mission Control (agent pool management)
- Adds advanced automation layer
- Includes CLI tools for power users
- Can be implemented independently if needed

---

## Table of Contents

1. [Problem & Solution](#problem--solution)
2. [Quota Monitor Dashboard](#quota-monitor-dashboard)
3. [Rate Limit Detection](#rate-limit-detection)
4. [Request Queue & Throttling](#request-queue--throttling)
5. [Auto-Pause & Quota Management](#auto-pause--quota-management)
6. [/quota CLI Command](#quota-cli-command)
7. [Alert Configuration](#alert-configuration)
8. [Database Schema](#database-schema)
9. [API Endpoints](#api-endpoints)
10. [Integration with Agent Pool](#integration-with-agent-pool)
11. [Implementation Roadmap](#implementation-roadmap)

---

## 1. Problem & Solution

### 1.1 The Problem

API providers enforce rate limits and quotas:
- **Claude API**: 50 requests/minute, 1M tokens/day
- **Gemini API**: 60 requests/minute, 1.5M tokens/day
- **OpenAI API**: 100 requests/minute, 3M tokens/day
- **Cursor API**: 30 requests/minute, 50K tokens/hour

Without proper handling:
- Agents hit 429 errors (Too Many Requests)
- Requests fail and waste quota
- Projects get stuck mid-build
- Quotas exhausted unexpectedly
- No visibility into usage until too late

### 1.2 The Solution

Comprehensive rate limit management with:

| Feature | Description |
|---------|-------------|
| **Real-time Monitoring** | Dashboard shows all quotas at a glance |
| **429 Detection** | Catch rate limits from any provider |
| **Auto-Retry** | Exponential backoff when rate limited |
| **Request Queue** | Throttle requests when approaching limits |
| **Auto-Pause** | Pause low-priority projects at 95% quota |
| **Smart Alerts** | Multi-channel notifications at thresholds |
| **CLI Tools** | `/quota` command for terminal users |

---

## 2. Quota Monitor Dashboard

### 2.1 Main Dashboard View

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 API Quota Monitor                                              [Refresh]     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Global Status: ⚠️  Moderate Usage (78% of total quota)                          │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Provider          │ Quota Type    │ Used    │ Limit    │ Reset        │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ Claude API        │ Tokens/day    │ 847K    │ 1M      │ 4h 23m       │  │
│  │                   │ ━━━━━━━━━━━━━━━━━━━━━━ 84%                            │  │
│  │                   │ Requests/min  │ 45      │ 50      │ 12s           │  │
│  │                   │ ━━━━━━━━━━━━━━━━━━━━━━ 90% ⚠️                         │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ Gemini API        │ Tokens/day    │ 1.2M    │ 1.5M    │ 2h 47m        │  │
│  │                   │ ━━━━━━━━━━━━━━━━━━━━━━ 83% ⚠️                         │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ OpenAI API        │ Tokens/day    │ 2.3M    │ 3M      │ 8h 15m        │  │
│  │                   │ ━━━━━━━━━━━━━━━━━━━━━━ 76%                            │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ Cursor Agent API  │ Tokens/hr     │ 45K     │ 50K     │ 23m           │  │
│  │                   │ ━━━━━━━━━━━━━━━━━━━━━━ 90% ⚠️                         │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Alerts                                                                    │  │
│  │ ⚠️  [4x] Claude API: 90% requests/min limit - throttling active           │  │
│  │ ⚠️  [1x] Gemini API: 83% daily quota - consider pausing non-critical      │  │
│  │ ⚠️  [1x] Cursor API: 90% hourly quota - auto-pause in 5 min                │  │
│  │                   [Dismiss All] [View All Alerts]                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Per-Agent Usage                                                            │  │
│  │ ┌────────────────────────────────────────────────────────────────────┐   │  │
│  │ │ Agent         │ Provider  │ Tokens Used │ Hourly Rate │ Status     │   │  │
│  │ │ ─────────────────────────────────────────────────────────────────── │   │  │
│  │ │ ralph-main    │ Gemini   │ 452K        │ 52K/hr     │ 🟢 Normal  │   │  │
│  │ │ ralph-sec     │ Gemini   │ 389K        │ 48K/hr     │ 🟢 Normal  │   │  │
│  │ │ claude-1      │ Claude   │ 847K        │ 105K/hr    │ 🟡 Throttled│   │  │
│  │ │ cursor-dev    │ Cursor   │ 45K         │ 58K/hr     │ 🟡 Throttled│   │  │
│  │ └────────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Auto-Pause Policy                                                          │  │
│  │ ☑ Enable auto-pause at 95% quota                                          │  │
│  │ ☑ Pause lowest priority projects first                                    │  │
│  │ ☑ Send notification before pausing                                        │  │
│  │ Alert threshold: [80%━━●━━95%]                                             │  │
│  │                                           [Save Policy]                   │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  [/quota] [Export CSV] [Configure Alerts] [View Historical Data]               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Per-Project Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 Project Quota Breakdown                                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Filter: [All Projects] [Running] [High Priority]                              │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Project              │ Agent      │ Provider │ Tokens    │ Cost    │ %  │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ nonprofit-matcher   │ ralph-main │ Gemini  │ 452,000   │ $0.45   │ 30%│  │
│  │   Priority: High    │            │          │ 52K/hr    │         │    │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ twitter-archive     │ ralph-sec  │ Gemini  │ 389,000   │ $0.39   │ 26%│  │
│  │   Priority: Medium  │            │          │ 48K/hr    │         │    │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ project-alpha       │ claude-1   │ Claude  │ 523,000   │ $1.57   │ 52%│  │
│  │   Priority: Critical│           │          │ 105K/hr   │         │    │  │
│  │ ─────────────────────────────────────────────────────────────────────── │  │
│  │ api-gateway         │ cursor-dev │ Cursor  │ 28,000    │ $0.14   │ 56%│  │
│  │   Priority: Low     │            │          │ 58K/hr    │         │    │  │
│  │ └──────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  Total: 1,392,000 tokens | $2.55 | Projected: $3.50 today                       │
│                                                                                │
│  Recommendations:                                                               │
│  ⚠️  Pause api-gateway (low priority) to save Cursor quota                     │
│  ✓ All other projects within acceptable range                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Rate Limit Detection

### 3.1 Detection Methods

```typescript
interface RateLimitDetector {
  // Detect 429 errors
  detect429(response: any): boolean;

  // Detect rate limit headers
  detectRateLimitHeaders(response: any): RateLimitInfo;

  // Detect approaching limits
  detectApproachingLimit(usage: QuotaUsage): boolean;

  // Parse provider-specific rate limit headers
  parseRateLimitHeaders(provider: Provider, headers: Headers): RateLimitInfo;
}

interface RateLimitInfo {
  provider: Provider;
  limitType: 'requests' | 'tokens' | 'cost';
  current: number;
  limit: number;
  remaining: number;
  resetAt: Date;
  retryAfter?: number; // seconds
}
```

### 3.2 Provider-Specific Implementations

#### Claude API

```typescript
class ClaudeRateLimitDetector implements RateLimitDetector {
  detect429(response: any): boolean {
    return response.status === 429 ||
           response.error?.type === 'rate_limit_error';
  }

  parseRateLimitHeaders(headers: Headers): RateLimitInfo {
    return {
      provider: 'claude',
      limitType: 'tokens',
      current: parseInt(headers.get('anthropic-ratelimit-tokens-used') || '0'),
      limit: parseInt(headers.get('anthropic-ratelimit-tokens-limit') || '0'),
      remaining: parseInt(headers.get('anthropic-ratelimit-tokens-remaining') || '0'),
      resetAt: new Date(headers.get('anthropic-ratelimit-reset') || ''),
    };
  }
}
```

#### Gemini API

```typescript
class GeminiRateLimitDetector implements RateLimitDetector {
  detect429(response: any): boolean {
    return response.status === 429 ||
           response.error?.code === 429;
  }

  parseRateLimitHeaders(headers: Headers): RateLimitInfo {
    // Gemini doesn't provide rate limit headers
    // Must track manually via request counting
    return this.getManualRateLimitInfo();
  }

  private getManualRateLimitInfo(): RateLimitInfo {
    // Query internal tracking database
    const usage = this.getCurrentUsage('gemini');
    return {
      provider: 'gemini',
      limitType: 'tokens',
      current: usage.used,
      limit: usage.limit,
      remaining: usage.limit - usage.used,
      resetAt: this.getNextResetTime(),
    };
  }
}
```

### 3.3 429 Error Handling

```typescript
class RateLimitHandler {
  async handleRequest(
    request: APIRequest,
    maxRetries: number = 5
  ): Promise<APIResponse> {
    let attempt = 0;

    while (attempt < maxRetries) {
      try {
        const response = await this.executeRequest(request);

        // Check for 429
        if (this.isRateLimited(response)) {
          attempt++;
          const retryAfter = this.getRetryAfter(response);

          // Exponential backoff
          const backoffDelay = this.calculateBackoff(attempt, retryAfter);

          console.log(`Rate limited, retrying in ${backoffDelay}ms (attempt ${attempt}/${maxRetries})`);

          await this.sleep(backoffDelay);
          continue;
        }

        // Update quota tracking
        await this.updateQuotaTracking(request, response);

        return response;
      } catch (error) {
        if (this.isRateLimitError(error)) {
          attempt++;
          const backoffDelay = this.calculateBackoff(attempt);
          await this.sleep(backoffDelay);
          continue;
        }
        throw error;
      }
    }

    throw new Error('Max retries exceeded for rate-limited request');
  }

  calculateBackoff(attempt: number, retryAfter?: number): number {
    if (retryAfter) {
      // Respect server's retry-after hint
      return retryAfter * 1000;
    }

    // Exponential backoff: 2^attempt seconds, with jitter
    const baseDelay = Math.pow(2, attempt) * 1000;
    const jitter = Math.random() * 1000;
    return baseDelay + jitter;
  }

  sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

---

## 4. Request Queue & Throttling

### 4.1 Request Queue Architecture

```typescript
interface RequestQueue {
  enqueue(request: QueuedRequest): void;
  dequeue(): QueuedRequest | null;
  peek(): QueuedRequest | null;
  size(): number;
  clear(): void;
}

interface QueuedRequest extends APIRequest {
  id: string;
  priority: number; // Higher = more important
  queuedAt: Date;
  project: string;
  agent: string;
  timeout: number;
}

class PriorityRequestQueue implements RequestQueue {
  private queue: QueuedRequest[] = [];

  enqueue(request: QueuedRequest): void {
    this.queue.push(request);
    this.queue.sort((a, b) => b.priority - a.priority);
  }

  dequeue(): QueuedRequest | null {
    return this.queue.shift() || null;
  }

  peek(): QueuedRequest | null {
    return this.queue[0] || null;
  }

  size(): number {
    return this.queue.length;
  }

  clear(): void {
    this.queue = [];
  }
}
```

### 4.2 Throttling Strategy

```typescript
class Throttler {
  private requestCounts: Map<string, number[]> = new Map(); // provider -> timestamps
  private readonly windowMs: number = 60000; // 1 minute window
  private readonly limits: Map<string, number> = new Map();

  constructor() {
    // Configure limits per provider
    this.limits.set('claude', 50); // 50 requests/minute
    this.limits.set('gemini', 60);
    this.limits.set('openai', 100);
    this.limits.set('cursor', 30);
  }

  async throttleRequest(
    provider: string,
    request: () => Promise<any>
  ): Promise<any> {
    // Clean old requests outside the window
    this.cleanOldRequests(provider);

    // Check if we're at the limit
    const count = this.getRequestCount(provider);
    const limit = this.limits.get(provider) || 50;

    if (count >= limit) {
      // Wait until we can make the request
      const oldestRequest = this.getOldestRequest(provider);
      const waitTime = this.windowMs - (Date.now() - oldestRequest);

      console.log(`Throttling ${provider}: waiting ${waitTime}ms`);

      await this.sleep(waitTime);

      // Clean again after waiting
      this.cleanOldRequests(provider);
    }

    // Make the request
    const response = await request();

    // Track the request
    this.trackRequest(provider);

    return response;
  }

  private cleanOldRequests(provider: string): void {
    const now = Date.now();
    const requests = this.requestCounts.get(provider) || [];
    const validRequests = requests.filter(ts => now - ts < this.windowMs);
    this.requestCounts.set(provider, validRequests);
  }

  private getRequestCount(provider: string): number {
    return (this.requestCounts.get(provider) || []).length;
  }

  private trackRequest(provider: string): void {
    const requests = this.requestCounts.get(provider) || [];
    requests.push(Date.now());
    this.requestCounts.set(provider, requests);
  }

  private getOldestRequest(provider: string): number {
    const requests = this.requestCounts.get(provider) || [];
    return requests[0] || 0;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

---

## 5. Auto-Pause & Quota Management

### 5.1 Quota Thresholds

```typescript
interface QuotaThresholds {
  warning: number;    // 80% - Send alert
  critical: number;   // 90% - Throttle non-critical
  emergency: number;  // 95% - Auto-pause lowest priority
  maximum: number;    // 100% - Hard stop all
}

class QuotaManager {
  private thresholds: QuotaThresholds = {
    warning: 80,
    critical: 90,
    emergency: 95,
    maximum: 100
  };

  async checkQuotaAndAct(provider: string): Promise<void> {
    const usage = await this.getCurrentUsage(provider);
    const percentage = (usage.used / usage.limit) * 100;

    // Check thresholds
    if (percentage >= this.thresholds.maximum) {
      await this.handleMaximum(provider);
    } else if (percentage >= this.thresholds.emergency) {
      await this.handleEmergency(provider);
    } else if (percentage >= this.thresholds.critical) {
      await this.handleCritical(provider);
    } else if (percentage >= this.thresholds.warning) {
      await this.handleWarning(provider);
    }
  }
}
```

### 5.2 Threshold Actions

| Threshold | Actions |
|-----------|---------|
| **80% (Warning)** | • Dashboard notification<br>• Log to alert history |
| **90% (Critical)** | • Urgent alert<br>• Throttle non-critical projects<br>• Reduce request frequency |
| **95% (Emergency)** | • Emergency alert<br>• Auto-pause low-priority projects<br>• Desktop notification<br>• Optional email/webhook |
| **100% (Maximum)** | • Hard stop ALL projects<br>• Emergency notification<br>• Log to event history |

### 5.3 Priority-Based Pause Strategy

```typescript
interface ProjectPriority {
  projectId: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  quotaUsage: number; // tokens/hour
  canPause: boolean;
}

class PriorityBasedPause {
  async pauseLowPriorityProjects(provider: string): Promise<string[]> {
    // Get all projects using this provider
    const projects = await this.getProjectsByProvider(provider);

    // Sort by priority (lowest first) then by quota usage
    const sorted = projects.sort((a, b) => {
      const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      if (priorityOrder[a.priority] !== priorityOrder[b.priority]) {
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      }
      return b.quotaUsage - a.quotaUsage; // Higher usage paused first
    });

    // Pause projects until we're back under the threshold
    const pausedProjects: string[] = [];
    let quotaSaved = 0;
    const targetQuotaSave = await this.getQuotaSaveTarget(provider);

    for (const project of sorted) {
      if (quotaSaved >= targetQuotaSave) break;
      if (!project.canPause) continue;

      await this.pauseProject(project.projectId);
      pausedProjects.push(project.projectId);
      quotaSaved += project.quotaUsage;
    }

    return pausedProjects;
  }
}
```

---

## 6. /quota CLI Command

### 6.1 Command Overview

The `/quota` command provides terminal-based quota monitoring for power users who prefer CLI over dashboard, or for scripting/automation purposes.

### 6.2 Basic Usage

```bash
# Show all quotas
/quota

# Show specific provider
/quota --provider claude

# Show per-project breakdown
/quota --by-project

# Show projected usage
/quota --projected

# Show only critical alerts
/quota --critical-only

# Export to CSV
/quota --export csv

# Show historical trends (last N days)
/quota --history 7

# Compact mode (for scripts)
/quota --compact
```

### 6.3 Command Output

#### Basic Output

```bash
$ /quota

╔══════════════════════════════════════════════════════════════════════════════╗
║                              API Quota Status                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

Global Status: ⚠️  Moderate Usage (78% of total quota)

┌──────────────┬─────────────┬──────────┬──────────┬──────────┬─────────┐
│ Provider     │ Type        │ Used     │ Limit    │ %        │ Reset   │
├──────────────┼─────────────┼──────────┼──────────┼──────────┼─────────┤
│ Claude       │ Tokens/day  │ 847,321  │ 1,000,000 │ 85%     │ 4h 23m  │
│ Claude       │ Req/min     │ 47       │ 50       │ 94% ⚠️  │ 12s     │
├──────────────┼─────────────┼──────────┼──────────┼──────────┼─────────┤
│ Gemini       │ Tokens/day  │ 1,245,000 │ 1,500,000 │ 83% ⚠️  │ 2h 47m  │
├──────────────┼─────────────┼──────────┼──────────┼──────────┼─────────┤
│ OpenAI       │ Tokens/day  │ 2,340,000 │ 3,000,000 │ 78%     │ 8h 15m  │
├──────────────┼─────────────┼──────────┼──────────┼──────────┼─────────┤
│ Cursor       │ Tokens/hr   │ 47,500   │ 50,000   │ 95% ⚠️  │ 23m     │
└──────────────┴─────────────┴──────────┴──────────┴──────────┴─────────┘

Active Alerts:
  ⚠️  Claude API: 94% requests/min - throttling active
  ⚠️  Gemini API: 83% daily quota - monitor closely
  ⚠️  Cursor API: 95% hourly quota - auto-pause imminent

Recommendations:
  ⚠️  Pause non-critical Cursor projects
  ✓ Claude within acceptable range
  ✓ OpenAI well within limits

For more details, visit: http://192.168.206.128:8003/quota
```

#### Per-Project Output

```bash
$ /quota --by-project

╔══════════════════════════════════════════════════════════════════════════════╗
║                           Project Quota Breakdown                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────┬──────────┬──────────┬──────────┬────────┬──────────┐
│ Project              │ Agent    │ Provider │ Tokens   │ Cost   │ %        │
├──────────────────────┼──────────┼──────────┼──────────┼────────┼──────────┤
│ nonprofit-matcher    │ ralph-mn │ Gemini  │ 452,000  │ $0.45  │ 30%      │
│   Priority: High     │          │          │ 52K/hr   │        │          │
├──────────────────────┼──────────┼──────────┼──────────┼────────┼──────────┤
│ twitter-archive      │ ralph-sc │ Gemini  │ 389,000  │ $0.39  │ 26%      │
│   Priority: Medium   │          │          │ 48K/hr   │        │          │
├──────────────────────┼──────────┼──────────┼──────────┼────────┼──────────┤
│ project-alpha        │ claude-1 │ Claude  │ 523,000  │ $1.57  │ 52%      │
│   Priority: Critical │          │          │ 105K/hr  │        │          │
├──────────────────────┼──────────┼──────────┼──────────┼────────┼──────────┤
│ api-gateway          │ cursor-d │ Cursor  │ 28,000   │ $0.14  │ 56%      │
│   Priority: Low      │          │          │ 58K/hr   │        │          │
└──────────────────────┴──────────┴──────────┴──────────┴────────┴──────────┘

Total: 1,392,000 tokens | $2.55
Projected: $3.50 today

Actions:
  /quota pause-project api-gateway
  /quota throttle-provider cursor
```

#### Compact Output (for scripts)

```bash
$ /quota --compact
claude_tokens=847321/1000000,85%;claude_req=47/50,94%;gemini=1245000/1500000,83%;cursor=47500/50000,95%
```

### 6.4 Command Implementation

```typescript
class QuotaCommand {
  async execute(args: QuotaCommandArgs): Promise<void> {
    if (args.compact) {
      return this.printCompact();
    }

    if (args.provider) {
      return this.printProvider(args.provider);
    }

    if (args.byProject) {
      return this.printByProject();
    }

    if (args.projected) {
      return this.printProjected();
    }

    if (args.history) {
      return this.printHistory(args.history);
    }

    if (args.export) {
      return this.exportData(args.export);
    }

    // Default: print all
    return this.printAll();
  }

  private async printAll(): Promise<void> {
    const quotas = await this.getAllQuotas();

    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log('║                         API Quota Status                          ║');
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    // Print table...
  }
}
```

---

## 7. Alert Configuration

### 7.1 Alert Configuration UI

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚙️ Quota Alert Configuration                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  Provider: [Claude ▼]                                                          │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Thresholds                                                                │  │
│  │ ┌────────────────────────────────────────────────────────────────────┐   │  │
│  │ │ Warning Level    : [80%──●────] Trigger: Send alert                │   │  │
│  │ │ Critical Level   : [90%────●───] Trigger: Throttle + alert         │   │  │
│  │ │ Emergency Level  : [95%──────●─] Trigger: Auto-pause + notify      │   │  │
│  │ └────────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Actions                                                                    │  │
│  │ ☑ Enable auto-throttle at critical level                                  │  │
│  │ ☑ Enable auto-pause at emergency level                                    │  │
│  │ ☑ Pause priorities: [☑ Low] [☑ Medium] [☐ High] [☐ Critical]            │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ Notification Channels                                                      │  │
│  │ ☑ Dashboard notifications                                                 │  │
│  │ ☑ Desktop notifications (Browser API)                                     │  │
│  │ ☐ Email notifications                 [Email: ━━━━━━━━━━━━━━━]            │  │
│  │ ☐ Webhook                          [URL: ━━━━━━━━━━━━━━━━━━━]             │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  [Test Alert] [Reset to Defaults] [Save Configuration]                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Alert Manager

```typescript
interface QuotaAlertConfig {
  enabled: boolean;
  thresholds: {
    warning: number;   // Default: 80%
    critical: number;  // Default: 90%
    emergency: number; // Default: 95%
  };
  actions: {
    notify: boolean;           // Send notifications
    throttle: boolean;         // Throttle at critical
    autoPause: boolean;        // Auto-pause at emergency
    pausePriorities: string[]; // Which priorities to pause
  };
  channels: {
    dashboard: boolean;
    desktop: boolean;
    email?: string;
    webhook?: string;
  };
}

class QuotaAlertManager {
  async sendAlert(alert: QuotaAlert): Promise<void> {
    const config = await this.getConfig(alert.provider);

    if (!config?.enabled) return;

    const { percentage, provider } = alert;

    // Determine alert level
    let level: AlertLevel = 'warning';
    if (percentage >= config.thresholds.emergency) level = 'emergency';
    else if (percentage >= config.thresholds.critical) level = 'critical';

    // Send to configured channels
    if (config.channels.dashboard) {
      await this.sendToDashboard(alert, level);
    }

    if (config.channels.desktop) {
      await this.sendDesktopNotification(alert, level);
    }

    if (config.channels.email && level !== 'warning') {
      await this.sendEmailAlert(alert, level, config.channels.email);
    }

    if (config.channels.webhook && level === 'emergency') {
      await this.sendWebhookAlert(alert, config.channels.webhook);
    }

    // Execute actions
    if (config.actions.throttle && level === 'critical') {
      await this.throttleProvider(provider);
    }

    if (config.actions.autoPause && level === 'emergency') {
      await this.autoPauseProjects(provider, config.actions.pausePriorities);
    }
  }
}
```

---

## 8. Database Schema

```sql
-- Quota tracking table
CREATE TABLE quota_usage (
  id BIGSERIAL PRIMARY KEY,
  provider VARCHAR(50) NOT NULL, -- claude, gemini, openai, cursor
  quota_type VARCHAR(50) NOT NULL, -- tokens/day, requests/min, cost/month
  current_usage BIGINT NOT NULL DEFAULT 0,
  limit_value BIGINT NOT NULL,
  percentage DECIMAL(5,2) GENERATED ALWAYS AS ((current_usage::DECIMAL / limit_value) * 100) STORED,
  reset_at TIMESTAMPTZ NOT NULL,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (provider, quota_type),
  INDEX idx_quota_provider (provider),
  INDEX idx_quota_reset (reset_at)
);

-- Quota history
CREATE TABLE quota_history (
  id BIGSERIAL PRIMARY KEY,
  provider VARCHAR(50) NOT NULL,
  quota_type VARCHAR(50) NOT NULL,
  usage_value BIGINT NOT NULL,
  limit_value BIGINT NOT NULL,
  percentage DECIMAL(5,2),
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  INDEX idx_quota_history_provider (provider, recorded_at DESC)
);

-- Rate limit events (429s, throttles, pauses)
CREATE TABLE rate_limit_events (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  provider VARCHAR(50) NOT NULL,
  project_id UUID REFERENCES projects(id),
  agent_type VARCHAR(50),
  event_type VARCHAR(50) NOT NULL, -- 429_error, throttled, auto_paused, resumed
  details JSONB DEFAULT '{}',
  resolved_at TIMESTAMPTZ,
  INDEX idx_rate_limit_events_provider (provider, timestamp DESC),
  INDEX idx_rate_limit_events_project (project_id, timestamp DESC)
);

-- Alert history
CREATE TABLE quota_alerts (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  provider VARCHAR(50) NOT NULL,
  alert_level VARCHAR(20) NOT NULL, -- warning, critical, emergency
  percentage DECIMAL(5,2) NOT NULL,
  message TEXT NOT NULL,
  actions_taken JSONB DEFAULT '{}',
  sent_to_dashboard BOOLEAN DEFAULT false,
  sent_to_email BOOLEAN DEFAULT false,
  sent_to_webhook BOOLEAN DEFAULT false,
  INDEX idx_quota_alerts_provider (provider, timestamp DESC),
  INDEX idx_quota_alerts_level (alert_level, timestamp DESC)
);

-- Request queue
CREATE TABLE request_queue (
  id UUID PRIMARY KEY,
  queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  provider VARCHAR(50) NOT NULL,
  project_id UUID REFERENCES projects(id),
  agent_type VARCHAR(50),
  priority INTEGER DEFAULT 0, -- Higher = more important
  request_data JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
  processed_at TIMESTAMPTZ,
  result JSONB,
  error_message TEXT,
  INDEX idx_queue_provider_status (provider, status, priority DESC),
  INDEX idx_queue_project (project_id, queued_at)
);
```

---

## 9. API Endpoints

```typescript
// Base URL: http://192.168.206.128:8002/api/quota

// Quota Monitoring
GET    /quota                             // Get all quota statuses
GET    /quota/:provider                   // Get specific provider quota
GET    /quota/:provider/history           // Get quota history (last N days)
POST   /quota/configure                   // Configure quota alerts

// Rate Limit Events
GET    /quota/events                      // Get rate limit events
GET    /quota/events/:id                  // Get specific event
POST   /quota/events/:id/resolve          // Mark event as resolved

// Alerts
GET    /quota/alerts                      // Get alert history
POST   /quota/alerts/test                 // Send test alert
POST   /quota/alerts/:id/acknowledge      // Acknowledge alert

// Actions
POST   /quota/pause-provider              // Pause all projects using provider
POST   /quota/throttle-provider            // Throttle provider requests
POST   /quota/pause-low-priority          // Pause low priority projects

// Request Queue
GET    /request-queue                     // Get queued requests
POST   /request-queue/:id/cancel          // Cancel queued request
POST   /request-queue/priority            // Adjust request priority
```

---

## 10. Integration with Agent Pool

```typescript
class AgentPoolRateLimitManager {
  private agentPool: AgentPool;
  private quotaManager: QuotaManager;
  private requestQueue: PriorityRequestQueue;

  async assignProjectWithQuotaAwareness(
    project: Project,
    requirements: AgentRequirements
  ): Promise<AgentAssignment> {
    // Get available agents
    const availableAgents = await this.agentPool.getAvailableAgents();

    // Check quota status for each agent's provider
    const agentsWithQuota = await Promise.all(
      availableAgents.map(async (agent) => ({
        agent,
        quota: await this.quotaManager.getCurrentUsage(agent.provider)
      }))
    );

    // Filter out agents with critical quota issues
    const healthyAgents = agentsWithQuota.filter(
      ({ quota }) => quota.percentage < 90
    );

    if (healthyAgents.length === 0) {
      throw new Error('No agents with available quota');
    }

    // Sort by quota availability (most quota first)
    healthyAgents.sort((a, b) => a.quota.percentage - b.quota.percentage);

    // Assign to agent with most quota
    const selectedAgent = healthyAgents[0].agent;

    return await this.agentPool.assignProject(project.id, selectedAgent.id);
  }
}
```

---

## 11. Implementation Roadmap

### Week 1: Rate Limit & Quota Management

**Days 1-2: Rate Limit Detection**
- [ ] Rate limit detector implementations (Claude, Gemini, OpenAI, Cursor)
- [ ] 429 error detection and handling
- [ ] Provider-specific header parsing
- [ ] Manual tracking for providers without headers

**Days 3-4: Request Queue & Throttling**
- [ ] Priority request queue implementation
- [ ] Throttling strategy (token bucket, sliding window)
- [ ] Queue management API (pause, cancel, re-prioritize)
- [ ] Queue visualization in dashboard

**Day 5: Quota Monitoring Dashboard**
- [ ] Real-time quota tracking per provider
- [ ] Quota monitor dashboard UI
- [ ] Per-project quota breakdown
- [ ] Usage projections and recommendations

**Day 6: Auto-Pause & Alerts**
- [ ] Quota threshold configuration (80/90/95/100%)
- [ ] Auto-pause logic for low-priority projects
- [ ] Alert system (dashboard, desktop, email, webhook)
- [ ] Priority-based pause strategy

**Day 7: /quota CLI Command**
- [ ] `/quota` command implementation
- [ ] Per-provider quota display
- [ ] Per-project breakdown
- [ ] Historical trends and projections
- [ ] Compact mode for scripting

**Deliverable:** Complete rate limit and quota management system

### Success Criteria

| Criteria | How to Verify |
|----------|---------------|
| **Rate Limit Detection** | 429 errors detected and handled with exponential backoff |
| **Quota Monitoring** | Real-time quota tracking per provider visible in dashboard |
| **Auto-Pause** | Projects auto-pause at 95% quota, lowest priority first |
| **Request Queue** | Requests queued and throttled when approaching limits |
| **Alert System** | Alerts sent at 80%/90%/95% thresholds (dashboard, desktop, email) |
| **/quota Command** | `/quota` command works with all options |
| **API Endpoints** | All quota API endpoints functional |
| **Integration** | Seamless integration with Phase 5 Mission Control |

---

## Conclusion

**Rate Limit & Quota Management** adds intelligent API protection to the Dope-Dash. By automatically detecting rate limits, retrying with backoff, throttling requests, and pausing projects at critical thresholds, it ensures your autonomous agents never exhaust their quotas unexpectedly.

**Key Benefits:**
- **Set and Forget:** Configure thresholds once, protection runs automatically
- **Multi-Provider:** Works with Claude, Gemini, OpenAI, Cursor, and more
- **Smart Throttling:** Priority-based queuing ensures critical work continues
- **CLI Tools:** `/quota` command for terminal users and scripting
- **Full Visibility:** Dashboard + CLI provide complete quota transparency

**Production Ready:** This design is comprehensive and ready for implementation as Phase 6 of the Dope-Dash.

---

**Document Status:** ✅ Complete
**Last Updated:** 2026-01-30
**Version:** 1.0
**Phase:** 6 of 6 (Advanced Automation)
