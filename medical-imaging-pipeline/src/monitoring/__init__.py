"""
AWS CloudWatch monitoring integration.

Handles log streaming and metrics publishing to CloudWatch.
"""

from monitoring.cloudwatch_handler import CloudWatchHandler

__all__ = ["CloudWatchHandler"]
