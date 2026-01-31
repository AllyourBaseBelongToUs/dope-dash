"""Report generation library for creating PDF and Markdown reports.

This module provides functions to generate reports with real analytics data,
including chart generation and PDF export capabilities.
"""
import base64
import json
import os
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import qrcode
from markdown2 import markdown
from weasyprint import HTML, CSS
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import ReportType, ReportFormat, ReportConfig
from app.models.session import Session
from app.models.event import Event
from sqlalchemy import and_, func, select, case, literal_column


REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
REPORTS_DIR.mkdir(exist_ok=True)


def calculate_duration_seconds(started_at: datetime | None, ended_at: datetime | None) -> int:
    """Calculate duration in seconds between two timestamps."""
    if started_at is None:
        return 0
    end = ended_at if ended_at else datetime.now(started_at.tzinfo)
    return int((end - started_at).total_seconds())


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_date(iso_date: str) -> str:
    """Format ISO date string to readable format."""
    try:
        dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return iso_date


async def fetch_session_summary(session_id: str, db_session: AsyncSession) -> dict[str, Any]:
    """Fetch session summary data."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise ValueError(f"Invalid session_id format: {session_id}")

    # Get session data
    session_query = select(Session).where(Session.id == session_uuid)
    session_result = await db_session.execute(session_query)
    session_obj = session_result.scalar_one_or_none()

    if not session_obj:
        raise ValueError(f"Session not found: {session_id}")

    # Get event counts by type
    event_counts_query = select(
        Event.event_type,
        func.count().label("count")
    ).where(
        Event.session_id == session_uuid
    ).group_by(Event.event_type)

    event_counts_result = await db_session.execute(event_counts_query)
    event_type_counts = {row.event_type: row.count for row in event_counts_result.all()}

    # Get total events
    total_events_query = select(func.count()).where(Event.session_id == session_uuid)
    total_events_result = await db_session.execute(total_events_query)
    total_events = total_events_result.scalar() or 0

    # Get error count
    error_count_query = select(func.count()).where(
        and_(
            Event.session_id == session_uuid,
            Event.event_type.in_(["error", "spec_fail"])
        )
    )
    error_count_result = await db_session.execute(error_count_query)
    error_count = error_count_result.scalar() or 0

    # Get warning count
    warning_count_query = select(func.count()).where(
        and_(
            Event.session_id == session_uuid,
            Event.data["warning"].astext != None
        )
    )
    warning_count_result = await db_session.execute(warning_count_query)
    warning_count = warning_count_result.scalar() or 0

    # Get spec info
    spec_info = session_obj.meta_data.get("specs", {})
    total_specs = spec_info.get("total", 0)
    completed_specs = spec_info.get("completed", 0)
    failed_specs = spec_info.get("failed", 0)

    if total_specs == 0:
        spec_start_query = select(func.count()).where(
            and_(
                Event.session_id == session_uuid,
                Event.event_type == "spec_start"
            )
        )
        spec_start_result = await db_session.execute(spec_start_query)
        total_specs = spec_start_result.scalar() or 0

    if completed_specs == 0:
        spec_complete_query = select(func.count()).where(
            and_(
                Event.session_id == session_uuid,
                Event.event_type == "spec_complete"
            )
        )
        spec_complete_result = await db_session.execute(spec_complete_query)
        completed_specs = spec_complete_result.scalar() or 0

    if failed_specs == 0:
        spec_fail_query = select(func.count()).where(
            and_(
                Event.session_id == session_uuid,
                Event.event_type == "spec_fail"
            )
        )
        spec_fail_result = await db_session.execute(spec_fail_query)
        failed_specs = spec_fail_result.scalar() or 0

    spec_success_rate = (completed_specs / total_specs) if total_specs > 0 else 0
    duration_seconds = calculate_duration_seconds(session_obj.started_at, session_obj.ended_at)

    return {
        "sessionId": str(session_obj.id),
        "agentType": session_obj.agent_type.value,
        "projectName": session_obj.project_name,
        "status": session_obj.status.value,
        "startedAt": session_obj.started_at.isoformat() if session_obj.started_at else None,
        "endedAt": session_obj.ended_at.isoformat() if session_obj.ended_at else None,
        "duration": duration_seconds,
        "totalSpecs": total_specs,
        "completedSpecs": completed_specs,
        "failedSpecs": failed_specs,
        "specSuccessRate": spec_success_rate,
        "totalEvents": total_events,
        "errorCount": error_count,
        "warningCount": warning_count,
        "eventBreakdown": event_type_counts,
    }


async def fetch_trends_data(period_days: int, db_session: AsyncSession) -> dict[str, Any]:
    """Fetch trends analysis data."""
    from datetime import timedelta
    from_date = datetime.now() - timedelta(days=period_days)

    # Get total sessions
    total_sessions_query = select(func.count()).where(
        Session.started_at >= from_date
    )
    total_sessions_result = await db_session.execute(total_sessions_query)
    total_sessions = total_sessions_result.scalar() or 0

    # Get sessions by status
    sessions_by_status_query = select(
        Session.status,
        func.count().label("count")
    ).where(
        Session.started_at >= from_date
    ).group_by(Session.status)

    sessions_by_status_result = await db_session.execute(sessions_by_status_query)
    sessions_by_status = {row.status.value: row.count for row in sessions_by_status_result.all()}

    # Get sessions by agent type
    sessions_by_agent_query = select(
        Session.agent_type,
        func.count().label("count")
    ).where(
        Session.started_at >= from_date
    ).group_by(Session.agent_type)

    sessions_by_agent_result = await db_session.execute(sessions_by_agent_query)
    sessions_by_agent = {row.agent_type.value: row.count for row in sessions_by_agent_result.all()}

    # Get session trend
    session_trend_query = select(
        func.date_trunc('day', Session.started_at).label("timestamp"),
        func.count().label("count")
    ).where(
        Session.started_at >= from_date
    ).group_by(
        func.date_trunc('day', Session.started_at)
    ).order_by(
        func.date_trunc('day', Session.started_at)
    )

    session_trend_result = await db_session.execute(session_trend_query)
    session_trend = [
        {"timestamp": row.timestamp.isoformat(), "count": row.count}
        for row in session_trend_result.all()
    ]

    # Get spec trend
    spec_complete_trend = select(
        func.date_trunc('day', Event.created_at).label("timestamp"),
        func.count().label("count")
    ).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_complete"
        )
    ).group_by(
        func.date_trunc('day', Event.created_at)
    ).subquery()

    spec_fail_trend = select(
        func.date_trunc('day', Event.created_at).label("timestamp"),
        func.count().label("count")
    ).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_fail"
        )
    ).group_by(
        func.date_trunc('day', Event.created_at)
    ).subquery()

    spec_trend_query = select(
        func.coalesce(spec_complete_trend.c.timestamp, spec_fail_trend.c.timestamp).label("timestamp"),
        func.coalesce(spec_complete_trend.c.count, 0).label("completed"),
        func.coalesce(spec_fail_trend.c.count, 0).label("failed"),
    ).outerjoin(
        spec_fail_trend,
        spec_complete_trend.c.timestamp == spec_fail_trend.c.timestamp
    ).order_by(
        func.coalesce(spec_complete_trend.c.timestamp, spec_fail_trend.c.timestamp)
    )

    spec_trend_result = await db_session.execute(spec_trend_query)
    spec_trend = [
        {
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "total": row.completed + row.failed,
            "completed": row.completed,
            "failed": row.failed,
        }
        for row in spec_trend_result.all()
    ]

    # Get error trend
    error_trend_query = select(
        func.date_trunc('day', Event.created_at).label("timestamp"),
        func.count().label("count")
    ).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type.in_(["error", "spec_fail"])
        )
    ).group_by(
        func.date_trunc('day', Event.created_at)
    ).order_by(
        func.date_trunc('day', Event.created_at)
    )

    error_trend_result = await db_session.execute(error_trend_query)
    error_trend = [
        {"timestamp": row.timestamp.isoformat(), "count": row.count}
        for row in error_trend_result.all()
    ]

    # Calculate average session duration
    avg_duration_query = select(
        func.avg(
            func.extract("epoch", Session.ended_at) -
            func.extract("epoch", Session.started_at)
        )
    ).where(
        and_(
            Session.started_at >= from_date,
            Session.ended_at.isnot(None)
        )
    )

    avg_duration_result = await db_session.execute(avg_duration_query)
    avg_session_duration = avg_duration_result.scalar() or 0

    # Get spec success rate
    total_complete = select(func.count()).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_complete"
        )
    )
    total_complete_result = await db_session.execute(total_complete)
    completed_count = total_complete_result.scalar() or 0

    total_fail = select(func.count()).where(
        and_(
            Event.created_at >= from_date,
            Event.event_type == "spec_fail"
        )
    )
    total_fail_result = await db_session.execute(total_fail)
    failed_count = total_fail_result.scalar() or 0

    total_spec_runs = completed_count + failed_count
    spec_success_rate = (completed_count / total_spec_runs) if total_spec_runs > 0 else 0

    return {
        "period": str(period_days),
        "bucketSize": "day",
        "fromDate": from_date.isoformat(),
        "toDate": datetime.now().isoformat(),
        "totalSessions": total_sessions,
        "sessionsByStatus": sessions_by_status,
        "sessionsByAgent": sessions_by_agent,
        "sessionTrend": session_trend,
        "specTrend": spec_trend,
        "errorTrend": error_trend,
        "avgSessionDuration": avg_session_duration,
        "totalSpecRuns": total_spec_runs,
        "specSuccessRate": spec_success_rate,
    }


def generate_chart_svg(
    chart_type: str,
    title: str,
    data: list[dict[str, Any]],
    color: str = "#3b82f6"
) -> str:
    """Generate an SVG chart from data."""
    width = 500
    height = 200
    margin_top = 40
    margin_left = 50
    margin_bottom = 30
    margin_right = 20

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        '.title { font: bold 14px sans-serif; fill: #1e293b; }',
        '.label { font: 10px sans-serif; fill: #64748b; }',
        '.value { font: 10px sans-serif; fill: #3b82f6; }',
        '.grid { stroke: #e2e8f0; stroke-width: 1; }',
        '.axis { stroke: #cbd5e1; stroke-width: 1; }',
        '.bar { fill: ' + color + '; }',
        '.line { fill: none; stroke: ' + color + '; stroke-width: 2; }',
        '.dot { fill: ' + color + '; }',
        '</style>',
        f'<text x="{width // 2}" y="20" text-anchor="middle" class="title">{title}</text>',
    ]

    if chart_type == "bar" and data:
        # Bar chart
        max_value = max(item.get("value", 0) for item in data) if data else 1
        if max_value == 0:
            max_value = 1

        bar_width = min(40, chart_width / len(data) - 10)

        for i, item in enumerate(data):
            value = item.get("value", 0)
            label = item.get("label", str(i))
            bar_height = (value / max_value) * chart_height if max_value > 0 else 0
            x = margin_left + i * (bar_width + 10)
            y = margin_top + chart_height - bar_height

            svg_parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" class="bar" rx="2"/>')
            svg_parts.append(f'<text x="{x + bar_width // 2}" y="{y - 5}" text-anchor="middle" class="value">{value}</text>')
            svg_parts.append(f'<text x="{x + bar_width // 2}" y="{height - 10}" text-anchor="middle" class="label">{label[:8]}</text>')

    elif chart_type == "line" and data:
        # Line chart
        values = [item.get("value", 0) for item in data]
        max_value = max(values) if values else 1
        min_value = min(values) if values else 0
        value_range = max_value - min_value if max_value != min_value else 1

        points = []
        for i, item in enumerate(data):
            value = item.get("value", 0)
            normalized_value = (value - min_value) / value_range
            x = margin_left + (i / max(len(data) - 1, 1)) * chart_width
            y = margin_top + chart_height - (normalized_value * chart_height)
            points.append((x, y))

        # Grid lines
        for i in range(5):
            y = margin_top + (i * chart_height / 4)
            svg_parts.append(f'<line x1="{margin_left}" y1="{y}" x2="{width - margin_right}" y2="{y}" class="grid" stroke-dasharray="3,3"/>')

        # Line path
        if len(points) > 1:
            path_data = " ".join([f"{'M' if i == 0 else 'L'} {x} {y}" for i, (x, y) in enumerate(points)])
            svg_parts.append(f'<path d="{path_data}" class="line"/>')

            # Dots
            for x, y in points:
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="3" class="dot"/>')

    # Axes
    svg_parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" class="axis"/>')
    svg_parts.append(f'<line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{width - margin_right}" y2="{margin_top + chart_height}" class="axis"/>')

    svg_parts.append('</svg>')

    return "\n".join(svg_parts)


def generate_markdown_report(
    title: str,
    report_type: str,
    data: dict[str, Any],
    generated_at: str
) -> str:
    """Generate a markdown report."""
    md = f"# {title}\n\n"
    md += f"**Generated At:** {format_date(generated_at)}\n"
    md += f"**Report Type:** {report_type}\n\n"
    md += "---\n\n"

    sessions = data.get("sessions", [])
    trends = data.get("trends")
    comparison = data.get("comparison")

    # Session summary section
    if sessions:
        md += "## Session Summary\n\n"
        for session in sessions:
            md += f"### Session: {session.get('projectName', 'Unknown')}\n\n"
            md += "| Property | Value |\n"
            md += "|----------|-------|\n"
            md += f"| **Session ID** | `{session.get('sessionId', '')}` |\n"
            md += f"| **Agent Type** | {session.get('agentType', '')} |\n"
            md += f"| **Status** | {session.get('status', '')} |\n"
            md += f"| **Started At** | {format_date(session.get('startedAt', ''))} |\n"
            md += f"| **Ended At** | {format_date(session.get('endedAt', '')) if session.get('endedAt') else 'N/A'} |\n"
            md += f"| **Duration** | {format_duration(session.get('duration', 0))} |\n\n"

            # Spec execution
            md += "#### Spec Execution\n\n"
            md += "| Metric | Count |\n"
            md += "|--------|-------|\n"
            md += f"| **Total Specs** | {session.get('totalSpecs', 0)} |\n"
            md += f"| **Completed Specs** | {session.get('completedSpecs', 0)} |\n"
            md += f"| **Failed Specs** | {session.get('failedSpecs', 0)} |\n"
            md += f"| **Success Rate** | {(session.get('specSuccessRate', 0) * 100):.1f}% |\n\n"

            # Events
            md += "#### Events\n\n"
            md += "| Type | Count |\n"
            md += "|------|-------|\n"
            for event_type, count in session.get('eventBreakdown', {}).items():
                md += f"| **{event_type}** | {count} |\n"
            md += "\n"

            # Errors & Warnings
            md += "#### Errors & Warnings\n\n"
            md += "| Type | Count |\n"
            md += "|------|-------|\n"
            md += f"| **Errors** | {session.get('errorCount', 0)} |\n"
            md += f"| **Warnings** | {session.get('warningCount', 0)} |\n\n"
            md += "---\n\n"

    # Trends section
    if trends:
        md += "## Trends Analysis\n\n"
        md += f"**Period:** {trends.get('period', 'N/A')} days\n"
        md += f"**From:** {format_date(trends.get('fromDate', ''))}\n"
        md += f"**To:** {format_date(trends.get('toDate', ''))}\n\n"

        md += "### Overview\n\n"
        md += "| Metric | Value |\n"
        md += "|--------|-------|\n"
        md += f"| **Total Sessions** | {trends.get('totalSessions', 0)} |\n"
        md += f"| **Total Spec Runs** | {trends.get('totalSpecRuns', 0)} |\n"
        md += f"| **Avg Session Duration** | {format_duration(int(trends.get('avgSessionDuration', 0)))} |\n"
        md += f"| **Spec Success Rate** | {(trends.get('specSuccessRate', 0) * 100):.1f}% |\n\n"

        # Sessions by status
        md += "### Sessions by Status\n\n"
        md += "| Status | Count |\n"
        md += "|--------|-------|\n"
        for status, count in trends.get('sessionsByStatus', {}).items():
            md += f"| **{status}** | {count} |\n"
        md += "\n"

        # Sessions by agent
        md += "### Sessions by Agent Type\n\n"
        md += "| Agent Type | Count |\n"
        md += "|------------|-------|\n"
        for agent, count in trends.get('sessionsByAgent', {}).items():
            md += f"| **{agent}** | {count} |\n"
        md += "\n"

        md += "---\n\n"

    # Comparison section
    if comparison:
        md += "## Session Comparison\n\n"
        md += "### Overview Metrics\n\n"
        md += "| Metric | Value |\n"
        md += "|--------|-------|\n"

        metrics = comparison.get('metrics', {})
        md += f"| **Total Sessions Compared** | {metrics.get('totalSessions', 0)} |\n"
        md += f"| **Average Duration** | {format_duration(int(metrics.get('avgDuration', 0)))} |\n"
        md += f"| **Average Spec Success Rate** | {(metrics.get('avgSpecSuccessRate', 0) * 100):.1f}% |\n"
        md += f"| **Total Specs Run** | {metrics.get('totalSpecs', 0)} |\n"
        md += f"| **Total Errors** | {metrics.get('totalErrors', 0)} |\n\n"

        for session in comparison.get('sessions', []):
            md += f"### Session: {session.get('projectName', 'Unknown')}\n\n"
            md += "| Property | Value |\n"
            md += "|----------|-------|\n"
            md += f"| **Status** | {session.get('status', '')} |\n"
            md += f"| **Duration** | {format_duration(session.get('duration', 0))} |\n"
            md += f"| **Specs** | {session.get('completedSpecs', 0)}/{session.get('totalSpecs', 0)} |\n"
            md += f"| **Success Rate** | {(session.get('specSuccessRate', 0) * 100):.1f}% |\n\n"

        md += "---\n\n"

    # Footer
    md += "\n---\n\n"
    md += "*This report was automatically generated by Dope Dash Report Generation System*\n"

    return md


def generate_html_from_markdown(markdown_content: str, title: str) -> str:
    """Convert markdown to HTML with styling for PDF generation."""
    html_body = markdown(markdown_content)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-center {{
                content: "Generated by Dope Dash | Page " counter(page) " of " counter(pages);
                font-size: 10px;
                color: #94a3b8;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #1e293b;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #1e293b;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #3b82f6;
            margin-top: 30px;
        }}
        h3 {{
            color: #475569;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #e2e8f0;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #3b82f6;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        code {{
            background-color: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 30px 0;
        }}
        .footer {{
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>"""

    return html_template


async def generate_pdf_report(
    title: str,
    report_type: str,
    data: dict[str, Any],
    generated_at: str,
    include_charts: bool = True
) -> bytes:
    """Generate a PDF report with optional charts."""
    # First generate markdown
    markdown_content = generate_markdown_report(title, report_type, data, generated_at)

    # Convert to HTML
    html_content = generate_html_from_markdown(markdown_content, title)

    # Add charts if requested
    if include_charts:
        # Generate chart SVGs
        charts_html = "\n<div class='charts'>\n<h2>Charts & Visualizations</h2>\n"

        # Session duration chart
        sessions = data.get("sessions", [])
        if sessions:
            sorted_sessions = sorted(sessions, key=lambda s: s.get("duration", 0), reverse=True)[:10]
            chart_data = [
                {"label": s.get("projectName", "")[:10], "value": s.get("duration", 0) // 60}
                for s in sorted_sessions
            ]
            chart_svg = generate_chart_svg("bar", "Session Duration (minutes)", chart_data, "#3b82f6")
            charts_html += f'<div class="chart">{chart_svg}</div>\n'

        # Trends charts
        trends = data.get("trends")
        if trends:
            # Error trend
            error_trend = trends.get("errorTrend", [])[-10:]
            if error_trend:
                error_data = [
                    {"label": format_date(p.get("timestamp", ""))[:10], "value": p.get("count", 0)}
                    for p in error_trend
                ]
                chart_svg = generate_chart_svg("line", "Error Trend", error_data, "#ef4444")
                charts_html += f'<div class="chart">{chart_svg}</div>\n'

            # Spec completion trend
            spec_trend = trends.get("specTrend", [])[-10:]
            if spec_trend:
                spec_data = [
                    {"label": format_date(p.get("timestamp", ""))[:10], "value": p.get("completed", 0)}
                    for p in spec_trend
                ]
                chart_svg = generate_chart_svg("bar", "Spec Completions", spec_data, "#22c55e")
                charts_html += f'<div class="chart">{chart_svg}</div>\n'

        charts_html += "</div>\n"

        # Insert charts before the footer
        html_content = html_content.replace(
            "<hr>",
            charts_html + "<hr>"
        )

    # Add CSS for charts
    chart_css = """
    <style>
        .charts {
            margin-top: 30px;
        }
        .chart {
            margin: 20px 0;
            text-align: center;
        }
        .chart svg {
            max-width: 100%;
            height: auto;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
    """
    html_content = html_content.replace("</style>", chart_css + "</style>")

    # Generate PDF using weasyprint
    html_doc = HTML(string=html_content, base_url=".")
    pdf_bytes = html_doc.write_pdf()

    return pdf_bytes


async def generate_report(
    config: ReportConfig,
    report_id: str,
    db_session: AsyncSession
) -> tuple[str, str | bytes, str]:
    """Generate a report based on configuration.

    Returns:
        Tuple of (file_extension, content, content_type)
    """
    generated_at = datetime.now().isoformat()
    data: dict[str, Any] = {}

    # Fetch data based on report type
    if config.type == ReportType.SESSION:
        session_ids = config.session_ids or []
        sessions = []
        for session_id in session_ids:
            try:
                session_data = await fetch_session_summary(session_id, db_session)
                sessions.append(session_data)
            except Exception as e:
                print(f"Error fetching session {session_id}: {e}")
        data["sessions"] = sessions

    elif config.type == ReportType.TRENDS:
        period_days = 30  # Default period
        trends = await fetch_trends_data(period_days, db_session)
        data["trends"] = trends

    elif config.type == ReportType.COMPARISON:
        session_ids = config.compare_session_ids or []
        sessions = []
        for session_id in session_ids:
            try:
                session_data = await fetch_session_summary(session_id, db_session)
                sessions.append(session_data)
            except Exception as e:
                print(f"Error fetching session {session_id}: {e}")

        # Calculate comparison metrics
        if sessions:
            durations = [s.get("duration", 0) for s in sessions]
            success_rates = [s.get("specSuccessRate", 0) for s in sessions]

            metrics = {
                "totalSessions": len(sessions),
                "avgDuration": sum(durations) / len(durations) if durations else 0,
                "avgSpecSuccessRate": sum(success_rates) / len(success_rates) if success_rates else 0,
                "totalSpecs": sum(s.get("totalSpecs", 0) for s in sessions),
                "totalErrors": sum(s.get("errorCount", 0) for s in sessions),
            }
            data["comparison"] = {"sessions": sessions, "metrics": metrics}

    elif config.type == ReportType.ERROR_ANALYSIS:
        # For error analysis, we include sessions data
        session_ids = config.session_ids or []
        sessions = []
        for session_id in session_ids:
            try:
                session_data = await fetch_session_summary(session_id, db_session)
                sessions.append(session_data)
            except Exception as e:
                print(f"Error fetching session {session_id}: {e}")
        data["sessions"] = sessions
        data["errorAnalysis"] = {"totalErrors": sum(s.get("errorCount", 0) for s in sessions)}

    # Generate output based on format
    if config.format == ReportFormat.MARKDOWN:
        markdown_content = generate_markdown_report(
            config.title,
            config.type.value,
            data,
            generated_at
        )
        return (".md", markdown_content, "text/markdown")

    elif config.format == ReportFormat.PDF:
        pdf_content = await generate_pdf_report(
            config.title,
            config.type.value,
            data,
            generated_at,
            config.include_charts
        )
        return (".pdf", pdf_content, "application/pdf")

    elif config.format == ReportFormat.JSON:
        json_content = json.dumps({
            "title": config.title,
            "generatedAt": generated_at,
            "type": config.type.value,
            "data": data,
        }, indent=2)
        return (".json", json_content, "application/json")

    elif config.format == ReportFormat.HTML:
        markdown_content = generate_markdown_report(
            config.title,
            config.type.value,
            data,
            generated_at
        )
        html_content = generate_html_from_markdown(markdown_content, config.title)
        return (".html", html_content, "text/html")

    else:
        raise ValueError(f"Unsupported format: {config.format}")
