"""Port error logging utility for tracking port binding failures.

This module provides a centralized logging system for recording port binding
errors with service name, port number, error details, and timestamps.

Log file format: JSON lines (one JSON object per line)
Log file location: backend/logs/port_errors.log
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class PortErrorLogger:
    """Logs port binding errors to a file for debugging and monitoring.

    Features:
    - JSON lines format for easy parsing
    - Automatic log directory creation
    - Timestamp tracking
    - Service identification
    """

    # Default log directory relative to backend root
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_LOG_FILE = "port_errors.log"

    def __init__(self, log_dir: str | None = None, log_file: str | None = None):
        """Initialize the port error logger.

        Args:
            log_dir: Directory for log files. Defaults to backend/logs/.
            log_file: Log file name. Defaults to port_errors.log.
        """
        # Determine log directory
        if log_dir is None:
            # Find backend directory (parent of app/utils)
            backend_dir = Path(__file__).parent.parent.parent
            log_dir = backend_dir / self.DEFAULT_LOG_DIR
        else:
            log_dir = Path(log_dir)

        # Ensure log directory exists
        log_dir.mkdir(parents=True, exist_ok=True)

        # Full log file path
        self.log_path = log_dir / (log_file or self.DEFAULT_LOG_FILE)

    def log_port_error(
        self,
        service_name: str,
        port: int,
        error: str | Exception,
        additional_info: dict[str, Any] | None = None,
    ) -> None:
        """Log a port binding error to the log file.

        Args:
            service_name: Name of the service (e.g., "websocket", "control", "analytics")
            port: Port number that failed to bind
            error: Error message or exception
            additional_info: Optional additional context
        """
        # Build error record
        error_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service_name": service_name,
            "port": port,
            "error": str(error),
            "error_type": type(error).__name__ if isinstance(error, Exception) else "str",
        }

        # Add additional info if provided
        if additional_info:
            error_record["additional_info"] = additional_info

        # Append to log file (JSON lines format)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_record) + "\n")
        except Exception as e:
            # Fallback to stderr if file write fails
            import sys
            print(f"[PORT ERROR LOGGING FAILED] {e}", file=sys.stderr)
            print(f"[ORIGINAL ERROR] {json.dumps(error_record)}", file=sys.stderr)

    def get_recent_errors(self, count: int = 10) -> list[dict[str, Any]]:
        """Get recent port errors from the log file.

        Args:
            count: Maximum number of errors to retrieve.

        Returns:
            List of error records, most recent first.
        """
        errors = []
        try:
            if self.log_path.exists():
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                errors.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                # Return most recent first
                errors = errors[-count:][::-1]
        except Exception:
            pass
        return errors

    def clear_logs(self) -> int:
        """Clear all port error logs.

        Returns:
            Number of log entries removed.
        """
        count = 0
        try:
            if self.log_path.exists():
                with open(self.log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            count += 1
                self.log_path.unlink()
        except Exception:
            pass
        return count


# Global instance for convenience
_global_logger: PortErrorLogger | None = None


def get_port_error_logger() -> PortErrorLogger:
    """Get the global port error logger instance.

    Returns:
        PortErrorLogger instance.
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = PortErrorLogger()
    return _global_logger


def log_port_error(
    service_name: str,
    port: int,
    error: str | Exception,
    additional_info: dict[str, Any] | None = None,
) -> None:
    """Convenience function to log a port error using the global logger.

    Args:
        service_name: Name of the service.
        port: Port number that failed.
        error: Error message or exception.
        additional_info: Optional additional context.
    """
    logger = get_port_error_logger()
    logger.log_port_error(service_name, port, error, additional_info)


# Service port mapping for reference
SERVICE_PORTS = {
    "core_api": 8000,
    "websocket": 8005,
    "control_api": 8010,
    "dashboard": 8015,
    "analytics": 8020,
}
