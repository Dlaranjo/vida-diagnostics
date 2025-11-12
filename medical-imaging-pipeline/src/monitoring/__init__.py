"""
AWS CloudWatch monitoring integration.

Handles log streaming and metrics publishing to CloudWatch.
"""

from src.monitoring.cloudwatch_handler import CloudWatchHandler

__all__ = ["CloudWatchHandler"]
