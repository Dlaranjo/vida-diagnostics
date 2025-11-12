"""
CloudWatch monitoring handler for logs and metrics.

Provides integration with AWS CloudWatch for centralized logging and metrics.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError

from utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class CloudWatchHandler:
    """
    Handler for AWS CloudWatch Logs and Metrics.

    Provides methods for sending logs and publishing custom metrics to CloudWatch.
    """

    def __init__(
        self,
        log_group_name: Optional[str] = None,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        """
        Initialize CloudWatch handler.

        Args:
            log_group_name: CloudWatch log group name
            region_name: AWS region (default: us-east-1)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.log_group_name = log_group_name
        self.region_name = region_name

        # Initialize CloudWatch clients
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.logs_client = boto3.client("logs", **session_kwargs)
        self.cloudwatch_client = boto3.client("cloudwatch", **session_kwargs)

        # Cache for sequence tokens
        self._sequence_tokens: Dict[str, Optional[str]] = {}

    def create_log_group(self, log_group_name: Optional[str] = None) -> bool:
        """
        Create CloudWatch log group.

        Args:
            log_group_name: Log group name (uses default if None)

        Returns:
            True if created or already exists

        Raises:
            ClientError: If creation fails
        """
        group_name = log_group_name or self.log_group_name
        if not group_name:
            raise ValueError("log_group_name must be provided")

        log_execution(
            logger,
            operation="create_log_group",
            status="started",
            details={"log_group": group_name},
        )

        try:
            self.logs_client.create_log_group(logGroupName=group_name)

            log_execution(
                logger,
                operation="create_log_group",
                status="completed",
                details={"log_group": group_name},
            )

            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                log_execution(
                    logger,
                    operation="create_log_group",
                    status="completed",
                    details={"log_group": group_name, "note": "already_exists"},
                )
                return True

            log_execution(
                logger,
                operation="create_log_group",
                status="failed",
                details={"log_group": group_name},
                error=e,
            )
            raise

    def create_log_stream(
        self,
        log_stream_name: str,
        log_group_name: Optional[str] = None,
    ) -> bool:
        """
        Create CloudWatch log stream.

        Args:
            log_stream_name: Log stream name
            log_group_name: Log group name (uses default if None)

        Returns:
            True if created or already exists

        Raises:
            ClientError: If creation fails
        """
        group_name = log_group_name or self.log_group_name
        if not group_name:
            raise ValueError("log_group_name must be provided")

        log_execution(
            logger,
            operation="create_log_stream",
            status="started",
            details={"log_group": group_name, "log_stream": log_stream_name},
        )

        try:
            self.logs_client.create_log_stream(
                logGroupName=group_name, logStreamName=log_stream_name
            )

            log_execution(
                logger,
                operation="create_log_stream",
                status="completed",
                details={"log_group": group_name, "log_stream": log_stream_name},
            )

            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                log_execution(
                    logger,
                    operation="create_log_stream",
                    status="completed",
                    details={
                        "log_group": group_name,
                        "log_stream": log_stream_name,
                        "note": "already_exists",
                    },
                )
                return True

            log_execution(
                logger,
                operation="create_log_stream",
                status="failed",
                details={"log_group": group_name, "log_stream": log_stream_name},
                error=e,
            )
            raise

    def put_log_events(
        self,
        log_stream_name: str,
        messages: Union[str, List[str]],
        log_group_name: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send log events to CloudWatch.

        Args:
            log_stream_name: Log stream name
            messages: Single message or list of messages
            log_group_name: Log group name (uses default if None)
            timestamp: Unix timestamp in milliseconds (uses current time if None)

        Returns:
            Dictionary with result including next sequence token

        Raises:
            ClientError: If put operation fails
        """
        group_name = log_group_name or self.log_group_name
        if not group_name:
            raise ValueError("log_group_name must be provided")

        # Normalize messages to list
        if isinstance(messages, str):
            messages = [messages]

        # Use current timestamp if not provided
        if timestamp is None:
            timestamp = int(time.time() * 1000)

        # Prepare log events
        log_events = [{"message": msg, "timestamp": timestamp} for msg in messages]

        log_execution(
            logger,
            operation="put_log_events",
            status="started",
            details={
                "log_group": group_name,
                "log_stream": log_stream_name,
                "event_count": len(log_events),
            },
        )

        try:
            # Get sequence token for stream
            stream_key = f"{group_name}/{log_stream_name}"
            sequence_token = self._sequence_tokens.get(stream_key)

            # Prepare put request
            put_kwargs = {
                "logGroupName": group_name,
                "logStreamName": log_stream_name,
                "logEvents": log_events,
            }

            if sequence_token:
                put_kwargs["sequenceToken"] = sequence_token

            # Put log events
            response = self.logs_client.put_log_events(**put_kwargs)

            # Update sequence token
            if "nextSequenceToken" in response:
                self._sequence_tokens[stream_key] = response["nextSequenceToken"]

            result = {
                "log_group": group_name,
                "log_stream": log_stream_name,
                "events_sent": len(log_events),
                "next_sequence_token": response.get("nextSequenceToken"),
            }

            log_execution(
                logger,
                operation="put_log_events",
                status="completed",
                details=result,
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="put_log_events",
                status="failed",
                details={"log_group": group_name, "log_stream": log_stream_name},
                error=e,
            )
            raise

    def put_metric_data(
        self,
        namespace: str,
        metric_name: str,
        value: float,
        unit: str = "None",
        dimensions: Optional[List[Dict[str, str]]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Publish custom metric to CloudWatch.

        Args:
            namespace: Metric namespace
            metric_name: Metric name
            value: Metric value
            unit: Metric unit (default: None)
            dimensions: List of dimension dicts with Name and Value
            timestamp: Metric timestamp (uses current time if None)

        Returns:
            Dictionary with result

        Raises:
            ClientError: If put operation fails
        """
        log_execution(
            logger,
            operation="put_metric_data",
            status="started",
            details={
                "namespace": namespace,
                "metric": metric_name,
                "value": value,
            },
        )

        try:
            # Prepare metric data
            metric_data = {
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
            }

            if timestamp:
                metric_data["Timestamp"] = timestamp
            else:
                metric_data["Timestamp"] = datetime.utcnow()

            if dimensions:
                metric_data["Dimensions"] = dimensions

            # Put metric
            self.cloudwatch_client.put_metric_data(Namespace=namespace, MetricData=[metric_data])

            result = {
                "namespace": namespace,
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
            }

            log_execution(
                logger,
                operation="put_metric_data",
                status="completed",
                details=result,
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="put_metric_data",
                status="failed",
                details={"namespace": namespace, "metric": metric_name},
                error=e,
            )
            raise

    def put_metric_data_batch(
        self,
        namespace: str,
        metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Publish multiple metrics in batch.

        Args:
            namespace: Metric namespace
            metrics: List of metric dictionaries with keys:
                - metric_name: str
                - value: float
                - unit: str (optional, default: None)
                - dimensions: List[Dict] (optional)
                - timestamp: datetime (optional)

        Returns:
            Dictionary with result

        Raises:
            ClientError: If put operation fails
        """
        log_execution(
            logger,
            operation="put_metric_data_batch",
            status="started",
            details={"namespace": namespace, "metric_count": len(metrics)},
        )

        try:
            # Prepare metric data
            metric_data = []
            for metric in metrics:
                data = {
                    "MetricName": metric["metric_name"],
                    "Value": metric["value"],
                    "Unit": metric.get("unit", "None"),
                }

                if "timestamp" in metric:
                    data["Timestamp"] = metric["timestamp"]
                else:
                    data["Timestamp"] = datetime.utcnow()

                if "dimensions" in metric:
                    data["Dimensions"] = metric["dimensions"]

                metric_data.append(data)

            # Put metrics (CloudWatch supports up to 20 metrics per request)
            # Split into batches if needed
            batch_size = 20
            for i in range(0, len(metric_data), batch_size):
                batch = metric_data[i : i + batch_size]
                self.cloudwatch_client.put_metric_data(Namespace=namespace, MetricData=batch)

            result = {
                "namespace": namespace,
                "metrics_sent": len(metrics),
            }

            log_execution(
                logger,
                operation="put_metric_data_batch",
                status="completed",
                details=result,
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="put_metric_data_batch",
                status="failed",
                details={"namespace": namespace},
                error=e,
            )
            raise

    def delete_log_group(self, log_group_name: Optional[str] = None) -> bool:
        """
        Delete CloudWatch log group.

        Args:
            log_group_name: Log group name (uses default if None)

        Returns:
            True if deleted

        Raises:
            ClientError: If deletion fails
        """
        group_name = log_group_name or self.log_group_name
        if not group_name:
            raise ValueError("log_group_name must be provided")

        log_execution(
            logger,
            operation="delete_log_group",
            status="started",
            details={"log_group": group_name},
        )

        try:
            self.logs_client.delete_log_group(logGroupName=group_name)

            # Clear cached sequence tokens for this group
            keys_to_remove = [
                key for key in self._sequence_tokens.keys() if key.startswith(group_name)
            ]
            for key in keys_to_remove:
                del self._sequence_tokens[key]

            log_execution(
                logger,
                operation="delete_log_group",
                status="completed",
                details={"log_group": group_name},
            )

            return True

        except ClientError as e:
            log_execution(
                logger,
                operation="delete_log_group",
                status="failed",
                details={"log_group": group_name},
                error=e,
            )
            raise

    def log_group_exists(self, log_group_name: Optional[str] = None) -> bool:
        """
        Check if log group exists.

        Args:
            log_group_name: Log group name (uses default if None)

        Returns:
            True if exists, False otherwise
        """
        group_name = log_group_name or self.log_group_name
        if not group_name:
            raise ValueError("log_group_name must be provided")

        try:
            response = self.logs_client.describe_log_groups(logGroupNamePrefix=group_name, limit=1)

            # Check if exact match exists
            for log_group in response.get("logGroups", []):
                if log_group["logGroupName"] == group_name:
                    return True

            return False

        except ClientError:
            return False

    def get_log_events(
        self,
        log_stream_name: str,
        log_group_name: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve log events from CloudWatch.

        Args:
            log_stream_name: Log stream name
            log_group_name: Log group name (uses default if None)
            limit: Maximum number of events to retrieve
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of log event dictionaries

        Raises:
            ClientError: If retrieval fails
        """
        group_name = log_group_name or self.log_group_name
        if not group_name:
            raise ValueError("log_group_name must be provided")

        try:
            kwargs = {
                "logGroupName": group_name,
                "logStreamName": log_stream_name,
                "limit": limit,
            }

            if start_time:
                kwargs["startTime"] = start_time
            if end_time:
                kwargs["endTime"] = end_time

            response = self.logs_client.get_log_events(**kwargs)

            events = []
            for event in response.get("events", []):
                events.append(
                    {
                        "timestamp": event["timestamp"],
                        "message": event["message"],
                        "ingestion_time": event.get("ingestionTime"),
                    }
                )

            return events

        except ClientError as e:
            log_execution(
                logger,
                operation="get_log_events",
                status="failed",
                details={"log_group": group_name, "log_stream": log_stream_name},
                error=e,
            )
            raise
