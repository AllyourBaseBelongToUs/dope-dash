import type { ReportData, SessionSummary, TrendData, ComparisonData, ErrorAnalysisData } from '@/types/reports';
import { format } from 'date-fns';

/**
 * Markdown Report Generator
 * Generates formatted markdown reports from analytics data
 */

/**
 * Format a date string for display
 */
function formatDate(dateString: string): string {
  try {
    return format(new Date(dateString), 'yyyy-MM-dd HH:mm:ss');
  } catch {
    return dateString;
  }
}

/**
 * Format a duration in seconds to human-readable format
 */
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

/**
 * Generate a session summary section
 */
function generateSessionSummary(session: SessionSummary): string {
  return `
### Session: ${session.projectName}

| Property | Value |
|----------|-------|
| **Session ID** | \`${session.sessionId}\` |
| **Agent Type** | ${session.agentType} |
| **Status** | ${session.status} |
| **Started At** | ${formatDate(session.startedAt)} |
| **Ended At** | ${session.endedAt ? formatDate(session.endedAt) : 'N/A'} |
| **Duration** | ${formatDuration(session.duration)} |

#### Spec Execution

| Metric | Count |
|--------|-------|
| **Total Specs** | ${session.totalSpecs} |
| **Completed Specs** | ${session.completedSpecs} |
| **Failed Specs** | ${session.failedSpecs} |
| **Success Rate** | ${(session.specSuccessRate * 100).toFixed(1)}% |

#### Events

| Type | Count |
|------|-------|
${Object.entries(session.eventBreakdown)
  .map(([type, count]) => `| **${type}** | ${count} |`)
  .join('\n')}

#### Errors & Warnings

| Type | Count |
|------|-------|
| **Errors** | ${session.errorCount} |
| **Warnings** | ${session.warningCount} |

---
`;
}

/**
 * Generate a trends section
 */
function generateTrendsSection(trends: TrendData): string {
  return `
## Trends Analysis

**Period:** ${trends.period} days (${formatDate(trends.fromDate)} - ${formatDate(trends.toDate)})
**Bucket Size:** ${trends.bucketSize}

### Overview

| Metric | Value |
|--------|-------|
| **Total Sessions** | ${trends.totalSessions} |
| **Total Spec Runs** | ${trends.totalSpecRuns} |
| **Avg Session Duration** | ${formatDuration(Math.round(trends.avgSessionDuration))} |
| **Spec Success Rate** | ${(trends.specSuccessRate * 100).toFixed(1)}% |

### Sessions by Status

| Status | Count |
|--------|-------|
${Object.entries(trends.sessionsByStatus)
  .map(([status, count]) => `| **${status}** | ${count} |`)
  .join('\n')}

### Sessions by Agent Type

| Agent Type | Count |
|------------|-------|
${Object.entries(trends.sessionsByAgent)
  .map(([agent, count]) => `| **${agent}** | ${count} |`)
  .join('\n')}

### Session Trend

${trends.sessionTrend
  .slice(-10)
  .map((point) => `- ${formatDate(point.timestamp)}: ${point.count} sessions`)
  .join('\n')}

### Spec Trend

${trends.specTrend
  .slice(-10)
  .map((point) => `- ${formatDate(point.timestamp)}: ${point.completed}/${point.total} completed (${point.failed} failed)`)
  .join('\n')}

### Error Trend

${trends.errorTrend
  .slice(-10)
  .map((point) => `- ${formatDate(point.timestamp)}: ${point.count} errors`)
  .join('\n')}

---
`;
}

/**
 * Generate a comparison section
 */
function generateComparisonSection(comparison: ComparisonData): string {
  const { sessions, metrics } = comparison;

  return `
## Session Comparison

### Overview Metrics

| Metric | Value |
|--------|-------|
| **Total Sessions Compared** | ${metrics.totalSessions} |
| **Average Duration** | ${formatDuration(Math.round(metrics.avgDuration))} |
| **Average Spec Success Rate** | ${(metrics.avgSpecSuccessRate * 100).toFixed(1)}% |
| **Total Specs Run** | ${metrics.totalSpecs} |
| **Total Errors** | ${metrics.totalErrors} |

### Performance Highlights

| Category | Session ID | Value |
|----------|------------|-------|
| **Fastest Session** | \`${metrics.fastestSession?.sessionId || 'N/A'}\` | ${formatDuration(Math.round(metrics.fastestSession?.duration || 0))} |
| **Slowest Session** | \`${metrics.slowestSession?.sessionId || 'N/A'}\` | ${formatDuration(Math.round(metrics.slowestSession?.duration || 0))} |
| **Highest Success Rate** | \`${metrics.highestSuccessRate?.sessionId || 'N/A'}\` | ${(metrics.highestSuccessRate?.rate || 0).toFixed(1)}% |
| **Lowest Success Rate** | \`${metrics.lowestSuccessRate?.sessionId || 'N/A'}\` | ${(metrics.lowestSuccessRate?.rate || 0).toFixed(1)}% |

### Session Details

${sessions.map((s) => generateSessionSummary(s)).join('')}

---
`;
}

/**
 * Generate an error analysis section
 */
function generateErrorAnalysisSection(errorAnalysis: ErrorAnalysisData): string {
  return `
## Error Analysis

### Overview

| Metric | Value |
|--------|-------|
| **Total Errors** | ${errorAnalysis.totalErrors} |
| **Unique Error Types** | ${Object.keys(errorAnalysis.errorFrequency).length} |

### Top Errors

| # | Error Message | Count | Affected Sessions |
|---|---------------|-------|-------------------|
${errorAnalysis.topErrors
  .map((e, i) => `| ${i + 1} | ${e.message.slice(0, 80)}${e.message.length > 80 ? '...' : ''} | ${e.count} | ${e.sessions.length} |`)
  .join('\n')}

### Errors by Session

| Session | Project | Error Count | Most Recent Error |
|---------|---------|-------------|-------------------|
${errorAnalysis.errorsBySession
  .slice(0, 20)
  .map((s) => `| \`${s.sessionId.slice(0, 8)}\` | ${s.projectName} | ${s.errorCount} | ${s.mostRecentError.slice(0, 60)}${s.mostRecentError.length > 60 ? '...' : ''} |`)
  .join('\n')}

### Error Trend

${errorAnalysis.errorTrend.length > 0
  ? errorAnalysis.errorTrend
      .slice(-10)
      .map((point) => `- ${formatDate(point.timestamp)}: ${point.count} errors`)
      .join('\n')
  : '_No trend data available_'}

---
`;
}

/**
 * Main function to generate markdown report
 */
export function generateMarkdownReport(data: ReportData): string {
  let markdown = `# ${data.title}

**Generated At:** ${formatDate(data.generatedAt)}
**Report Type:** ${data.type}
**Format:** ${data.format}

---

`;

  // Add content based on report type
  if (data.sessions && data.sessions.length > 0) {
    markdown += `## Session Summary

`;
    if (data.sessions.length === 1) {
      markdown += generateSessionSummary(data.sessions[0]);
    } else {
      data.sessions.forEach((session) => {
        markdown += generateSessionSummary(session);
      });
    }
  }

  if (data.trends) {
    markdown += generateTrendsSection(data.trends);
  }

  if (data.comparison) {
    markdown += generateComparisonSection(data.comparison);
  }

  if (data.errorAnalysis) {
    markdown += generateErrorAnalysisSection(data.errorAnalysis);
  }

  // Add footer
  markdown += `
---

*This report was automatically generated by Dope Dash Report Generation System*
*For more information, visit the Dope Dash dashboard*
`;

  return markdown;
}
