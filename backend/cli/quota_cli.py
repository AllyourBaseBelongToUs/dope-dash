#!/usr/bin/env python3
"""Quota CLI command for terminal users.

This CLI provides quota management and monitoring capabilities:
- View current quota usage across all providers
- List all configured providers
- Show usage history and trends
- Display next quota reset times
- Watch mode with auto-refresh

Usage:
    python -m cli.quota_cli
    python -m cli.quota_cli --providers
    python -m cli.quota_cli --history
    python -m cli.quota_cli --reset
    python -m cli.quota_cli --json
    python -m cli.quota_cli --watch
    python -m cli.quota_cli --help
"""
from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import db_manager
from app.services.quota import QuotaService
from app.models.quota import (
    ProviderType,
    QuotaAlertStatus,
    QuotaAlertType,
    QuotaResetType,
)


# ANSI Color codes
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"

    @classmethod
    def disable(cls) -> None:
        """Disable all colors (for non-TTY output)."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.MAGENTA = ""
        cls.CYAN = ""
        cls.WHITE = ""
        cls.BG_RED = ""
        cls.BG_GREEN = ""
        cls.BG_YELLOW = ""


def get_usage_color(usage_percent: float) -> str:
    """Get color based on usage percentage.

    Args:
        usage_percent: Usage percentage (0-100+)

    Returns:
        ANSI color code
    """
    if usage_percent >= 95:
        return Colors.RED
    elif usage_percent >= 80:
        return Colors.YELLOW
    else:
        return Colors.GREEN


def get_status_indicator(usage_percent: float) -> str:
    """Get status indicator symbol based on usage.

    Args:
        usage_percent: Usage percentage (0-100+)

    Returns:
        Status indicator string
    """
    if usage_percent >= 95:
        return f"{Colors.BG_RED}!!{Colors.RESET}"
    elif usage_percent >= 80:
        return f"{Colors.YELLOW}!{Colors.RESET}"
    else:
        return f"{Colors.GREEN}OK{Colors.RESET}"


def format_bytes(tokens: int) -> str:
    """Format token count with K/M suffix.

    Args:
        tokens: Number of tokens

    Returns:
        Formatted string
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def format_time_remaining(seconds: int | None) -> str:
    """Format time remaining in human-readable format.

    Args:
        seconds: Seconds until reset

    Returns:
        Formatted time string
    """
    if seconds is None:
        return "N/A"

    if seconds <= 0:
        return "Now"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_datetime(dt: datetime | None) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format

    Returns:
        Formatted string
    """
    if dt is None:
        return "N/A"

    # Convert to local timezone for display
    if dt.tzinfo is not None:
        dt = dt.astimezone()

    return dt.strftime("%Y-%m-%d %H:%M:%S")


class QuotaCLI:
    """Quota CLI for terminal users."""

    def __init__(self, json_output: bool = False, no_color: bool = False) -> None:
        """Initialize the quota CLI.

        Args:
            json_output: If True, output in JSON format
            no_color: If True, disable colored output
        """
        self.json_output = json_output

        if no_color or not sys.stdout.isatty():
            Colors.disable()

    async def show_usage(self) -> None:
        """Display current quota usage summary."""
        async with db_manager.get_session() as session:
            service = QuotaService(session)

            # Get summary
            summary = await service.get_summary()

            # Get detailed usage
            usage_list = await service.get_quota_usage()
            providers = await service.get_providers(active_only=False)

            if self.json_output:
                self._output_json({
                    "summary": summary.model_dump(),
                    "usage": [u.model_dump() for u in usage_list.items],
                    "providers": [p.model_dump() for p in providers.items],
                })
                return

            # Print header
            self._print_header("Quota Usage Summary")

            # Print summary stats
            print()
            print(f"  {Colors.BOLD}Total Providers:{Colors.RESET}   {summary.active_providers}/{summary.total_providers} active")
            print(f"  {Colors.BOLD}Total Requests:{Colors.RESET}   {summary.total_requests:,}")
            print(f"  {Colors.BOLD}Total Tokens:{Colors.RESET}     {format_bytes(summary.total_tokens)}")
            print(f"  {Colors.BOLD}Avg Usage:{Colors.RESET}       {self._colorize_percent(summary.total_usage_percent)}")
            print(f"  {Colors.BOLD}Over Limit:{Colors.RESET}      {Colors.RED if summary.providers_over_limit > 0 else Colors.GREEN}{summary.providers_over_limit}{Colors.RESET} providers")
            print(f"  {Colors.BOLD}Active Alerts:{Colors.RESET}   {Colors.RED if summary.alerts_critical > 0 else Colors.YELLOW if summary.alerts_count > 0 else Colors.GREEN}{summary.alerts_count}{Colors.RESET} ({summary.alerts_critical} critical)")
            print(f"  {Colors.BOLD}Last Updated:{Colors.RESET}    {format_datetime(summary.last_updated)}")

            # Print usage table
            if usage_list.items:
                print()
                self._print_usage_table(usage_list.items)
            else:
                print()
                print(f"  {Colors.DIM}No quota usage records found.{Colors.RESET}")

    async def show_providers(self) -> None:
        """Display all configured providers."""
        async with db_manager.get_session() as session:
            service = QuotaService(session)
            providers = await service.get_providers(active_only=False)

            if self.json_output:
                self._output_json({
                    "providers": [p.model_dump() for p in providers.items],
                    "total": providers.total,
                })
                return

            self._print_header("Provider Configuration")

            if not providers.items:
                print(f"\n  {Colors.DIM}No providers configured.{Colors.RESET}")
                return

            print()
            # Table header
            print(f"  {'Provider':<18} {'Status':<8} {'Quota Limit':>12} {'Reset Type':<10} {'Reset Hour':<12}")
            print(f"  {'-'*18} {'-'*8} {'-'*12} {'-'*10} {'-'*12}")

            for provider in providers.items:
                status = f"{Colors.GREEN}active{Colors.RESET}" if provider.is_active else f"{Colors.DIM}inactive{Colors.RESET}"
                reset_type = provider.quota_reset_type.value
                reset_hour = f"{provider.quota_reset_hour:02d}:00 UTC"

                print(f"  {Colors.BOLD}{provider.display_name:<18}{Colors.RESET} {status:<17} {provider.default_quota_limit:>12,} {reset_type:<10} {reset_hour:<12}")

            print()
            print(f"  {Colors.DIM}Total: {providers.total} providers{Colors.RESET}")

    async def show_history(self, limit: int = 10) -> None:
        """Display usage history (recent alerts and events).

        Args:
            limit: Maximum number of history items to show
        """
        async with db_manager.get_session() as session:
            service = QuotaService(session)

            # Get recent alerts as history
            alerts = await service.get_alerts(limit=limit)

            # Get current usage for context
            usage_list = await service.get_quota_usage()

            if self.json_output:
                self._output_json({
                    "alerts": [a.model_dump() for a in alerts.items],
                    "current_usage": [u.model_dump() for u in usage_list.items],
                })
                return

            self._print_header("Quota History")

            # Show recent alerts
            print()
            print(f"  {Colors.BOLD}Recent Alerts:{Colors.RESET}")
            print()

            if not alerts.items:
                print(f"  {Colors.DIM}No recent alerts.{Colors.RESET}")
            else:
                for alert in alerts.items:
                    alert_color = Colors.RED if alert.alert_type in (QuotaAlertType.CRITICAL, QuotaAlertType.OVERAGE) else Colors.YELLOW
                    status_color = Colors.GREEN if alert.status == QuotaAlertStatus.RESOLVED else Colors.YELLOW if alert.status == QuotaAlertStatus.ACKNOWLEDGED else Colors.RED

                    print(f"  {alert_color}[{alert.alert_type.value.upper():<8}]{Colors.RESET} {alert.provider_name or 'Unknown':<12} "
                          f"{alert.current_usage}/{alert.quota_limit} ({alert.threshold_percent}%) "
                          f"{status_color}[{alert.status.value}]{Colors.RESET}")
                    print(f"  {Colors.DIM}  {format_datetime(alert.created_at)}{Colors.RESET}")
                    if alert.message:
                        print(f"  {Colors.DIM}  {alert.message[:60]}{'...' if len(alert.message) > 60 else ''}{Colors.RESET}")
                    print()

            # Show usage trends
            print()
            print(f"  {Colors.BOLD}Current Usage by Provider:{Colors.RESET}")
            print()

            if not usage_list.items:
                print(f"  {Colors.DIM}No usage data available.{Colors.RESET}")
            else:
                for usage in usage_list.items:
                    color = get_usage_color(usage.usage_percent)
                    bar = self._progress_bar(usage.usage_percent, width=20)
                    print(f"  {usage.provider_name or 'Unknown':<12} {color}{bar}{Colors.RESET} {usage.usage_percent:.1f}%")
                    print(f"  {Colors.DIM}  {usage.current_requests}/{usage.quota_limit} requests, {format_bytes(usage.current_tokens)} tokens{Colors.RESET}")
                    print()

    async def show_reset_times(self) -> None:
        """Display quota reset times for all providers."""
        async with db_manager.get_session() as session:
            service = QuotaService(session)

            # Get all usage records
            usage_list = await service.get_quota_usage()
            providers = await service.get_providers(active_only=True)

            if self.json_output:
                self._output_json({
                    "usage": [{
                        "provider_name": u.provider_name,
                        "period_end": u.period_end.isoformat() if u.period_end else None,
                        "time_until_reset_seconds": u.time_until_reset_seconds,
                        "last_reset_at": u.last_reset_at.isoformat() if u.last_reset_at else None,
                    } for u in usage_list.items],
                    "providers": [{
                        "name": p.name.value,
                        "display_name": p.display_name,
                        "reset_type": p.quota_reset_type.value,
                        "reset_hour": p.quota_reset_hour,
                        "reset_timezone": p.quota_reset_timezone,
                    } for p in providers.items],
                })
                return

            self._print_header("Quota Reset Schedule")

            print()

            # Group by reset type
            daily_resets = []
            monthly_resets = []

            for provider in providers.items:
                if provider.quota_reset_type == QuotaResetType.DAILY:
                    daily_resets.append(provider)
                elif provider.quota_reset_type == QuotaResetType.MONTHLY:
                    monthly_resets.append(provider)

            # Show daily resets
            if daily_resets:
                print(f"  {Colors.BOLD}Daily Reset Schedule:{Colors.RESET}")
                print()
                for provider in daily_resets:
                    reset_time = f"{provider.quota_reset_hour:02d}:00 {provider.quota_reset_timezone}"
                    print(f"    {provider.display_name:<20} resets at {Colors.CYAN}{reset_time}{Colors.RESET}")
                print()

            # Show monthly resets
            if monthly_resets:
                print(f"  {Colors.BOLD}Monthly Reset Schedule:{Colors.RESET}")
                print()
                for provider in monthly_resets:
                    day = provider.quota_reset_day_of_month or 1
                    reset_time = f"{provider.quota_reset_hour:02d}:00 {provider.quota_reset_timezone}"
                    print(f"    {provider.display_name:<20} resets on day {day} at {Colors.CYAN}{reset_time}{Colors.RESET}")
                print()

            # Show next reset for active usage
            if usage_list.items:
                print(f"  {Colors.BOLD}Next Quota Resets:{Colors.RESET}")
                print()

                # Sort by time until reset
                sorted_usage = sorted(
                    [u for u in usage_list.items if u.time_until_reset_seconds is not None],
                    key=lambda x: x.time_until_reset_seconds or 0
                )

                for usage in sorted_usage[:5]:  # Show top 5
                    time_remaining = format_time_remaining(usage.time_until_reset_seconds)
                    reset_color = Colors.RED if usage.time_until_reset_seconds and usage.time_until_reset_seconds < 3600 else Colors.WHITE

                    print(f"    {usage.provider_name or 'Unknown':<15} {reset_color}{time_remaining:>10}{Colors.RESET} "
                          f"{Colors.DIM}({format_datetime(usage.period_end)}){Colors.RESET}")

            print()

    async def watch_mode(self, interval: int = 5) -> None:
        """Run in watch mode with auto-refresh.

        Args:
            interval: Refresh interval in seconds
        """
        print(f"{Colors.CYAN}Starting quota watch mode (refresh every {interval}s, Ctrl+C to exit)...{Colors.RESET}")
        print()

        running = True

        def signal_handler() -> None:
            nonlocal running
            running = False

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        try:
            while running:
                # Clear screen
                print("\033[2J\033[H", end="")

                # Show current usage
                await self.show_usage()

                # Show next reset times
                print()
                print(f"  {Colors.DIM}{'─' * 50}{Colors.RESET}")
                print()
                await self.show_reset_times()

                # Show timestamp
                print()
                print(f"  {Colors.DIM}Last updated: {format_datetime(datetime.now(timezone.utc))}{Colors.RESET}")
                print(f"  {Colors.DIM}Next refresh in {interval}s...{Colors.RESET}")

                # Wait for next refresh
                try:
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break

        finally:
            # Remove signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(sig)

            print()
            print(f"{Colors.CYAN}Watch mode ended.{Colors.RESET}")

    def _print_header(self, title: str) -> None:
        """Print a section header.

        Args:
            title: Header title
        """
        print()
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    def _print_usage_table(self, items: list[Any]) -> None:
        """Print usage table.

        Args:
            items: List of usage items
        """
        # Table header
        print(f"  {'Provider':<12} {'Status':<4} {'Usage':>15} {'Limit':>10} {'%':>8} {'Tokens':>10} {'Reset In':>10}")
        print(f"  {'-'*12} {'-'*4} {'-'*15} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")

        for usage in items:
            color = get_usage_color(usage.usage_percent)
            status = get_status_indicator(usage.usage_percent)

            usage_str = f"{usage.current_requests:,}"
            limit_str = f"{usage.quota_limit:,}"
            percent_str = f"{usage.usage_percent:.1f}%"
            tokens_str = format_bytes(usage.current_tokens)
            reset_str = format_time_remaining(usage.time_until_reset_seconds)

            print(f"  {usage.provider_name or 'Unknown':<12} {status:<6} {usage_str:>15} {limit_str:>10} {color}{percent_str:>8}{Colors.RESET} {tokens_str:>10} {reset_str:>10}")

    def _colorize_percent(self, percent: float) -> str:
        """Colorize a percentage value.

        Args:
            percent: Percentage value

        Returns:
            Colorized string
        """
        color = get_usage_color(percent)
        return f"{color}{percent:.1f}%{Colors.RESET}"

    def _progress_bar(self, percent: float, width: int = 20) -> str:
        """Create a text progress bar.

        Args:
            percent: Percentage value
            width: Bar width in characters

        Returns:
            Progress bar string
        """
        filled = int(min(percent, 100) / 100 * width)
        empty = width - filled
        return "[" + "=" * filled + " " * empty + "]"

    def _output_json(self, data: dict[str, Any]) -> None:
        """Output data as JSON.

        Args:
            data: Data to output
        """
        print(json.dumps(data, indent=2, default=str))


async def main_async(args: argparse.Namespace) -> int:
    """Main async entry point.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    cli = QuotaCLI(json_output=args.json, no_color=args.no_color)

    # Initialize database
    db_manager.init_db()

    try:
        if args.watch:
            await cli.watch_mode(interval=args.interval)
        elif args.providers:
            await cli.show_providers()
        elif args.history:
            await cli.show_history(limit=args.limit)
        elif args.reset:
            await cli.show_reset_times()
        else:
            # Default: show usage summary
            await cli.show_usage()

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}", file=sys.stderr)
        return 1

    finally:
        await db_manager.close_db()


def main() -> None:
    """Main entry point for the quota CLI."""
    parser = argparse.ArgumentParser(
        prog="quota",
        description="Quota CLI for monitoring API provider usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quota                          Show current quota usage
  quota --providers              List all configured providers
  quota --history                Show usage history and recent alerts
  quota --reset                  Show quota reset times
  quota --json                   Output in JSON format (for scripting)
  quota --watch                  Watch mode with auto-refresh
  quota --watch --interval 10    Watch mode with 10s refresh interval

Color Codes:
  GREEN   = Usage below 80%
  YELLOW  = Usage between 80-95%
  RED     = Usage at or above 95%

Exit Codes:
  0 = Success
  1 = Error
        """,
    )

    # Command options
    parser.add_argument(
        "--providers",
        action="store_true",
        help="List all configured providers",
    )

    parser.add_argument(
        "--history",
        action="store_true",
        help="Show usage history and recent alerts",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Show quota reset times",
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode with auto-refresh",
    )

    # Output options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval for watch mode (default: 5 seconds)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of history items (default: 10)",
    )

    args = parser.parse_args()

    # Run async main
    try:
        exit_code = asyncio.run(main_async(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
