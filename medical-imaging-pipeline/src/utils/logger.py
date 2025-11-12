"""
Structured logging utilities for medical imaging pipeline.

Provides JSON-formatted logging for audit trails and monitoring.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class CustomJsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get or create a structured logger.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance with JSON formatting
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(level)

        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # Set JSON formatter
        formatter = CustomJsonFormatter()
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def log_execution(
    logger: logging.Logger,
    operation: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None,
) -> None:
    """
    Log pipeline execution event in structured format.

    Args:
        logger: Logger instance
        operation: Operation name (e.g., "dicom_processing")
        status: Status (e.g., "started", "completed", "failed")
        details: Additional context details
        error: Exception if operation failed
    """
    log_data = {
        "operation": operation,
        "status": status,
    }

    if details:
        log_data["details"] = details

    if error:
        log_data["error"] = {
            "type": type(error).__name__,
            "message": str(error),
        }

    if status == "failed":
        logger.error(f"Operation {operation} failed", extra={"extra_fields": log_data})
    elif status == "started":
        logger.info(f"Operation {operation} started", extra={"extra_fields": log_data})
    else:
        logger.info(f"Operation {operation} {status}", extra={"extra_fields": log_data})


def log_audit_event(
    logger: logging.Logger,
    event_type: str,
    user: str,
    resource: str,
    action: str,
    result: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log audit event for compliance tracking.

    Args:
        logger: Logger instance
        event_type: Type of audit event (e.g., "data_access", "phi_deidentification")
        user: User or service performing action
        resource: Resource being accessed (e.g., file path, S3 key)
        action: Action performed (e.g., "read", "write", "delete")
        result: Result of action (e.g., "success", "denied")
        details: Additional context
    """
    audit_data = {
        "audit_event": True,
        "event_type": event_type,
        "user": user,
        "resource": resource,
        "action": action,
        "result": result,
    }

    if details:
        audit_data["details"] = details

    logger.info(
        f"Audit: {event_type} - {action} on {resource} by {user}",
        extra={"extra_fields": audit_data},
    )


# Example usage
if __name__ == "__main__":
    # Create logger
    test_logger = get_logger(__name__)

    # Log execution event
    log_execution(
        test_logger, operation="dicom_processing", status="started", details={"file_count": 10}
    )

    # Log audit event
    log_audit_event(
        test_logger,
        event_type="data_access",
        user="pipeline-service",
        resource="s3://bucket/patient-123/scan.dcm",
        action="read",
        result="success",
    )
