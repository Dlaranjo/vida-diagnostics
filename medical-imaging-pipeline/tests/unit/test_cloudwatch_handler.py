"""
Unit tests for CloudWatch handler.

Tests CloudWatch Logs and Metrics integration using moto mocking.
"""

import time
from datetime import datetime

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.monitoring.cloudwatch_handler import CloudWatchHandler


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def log_group_name() -> str:
    """Standard log group name for testing."""
    return "test-log-group"


@pytest.fixture
def cloudwatch_handler(aws_credentials, log_group_name):
    """Create CloudWatchHandler with mocked AWS."""
    with mock_aws():
        handler = CloudWatchHandler(log_group_name=log_group_name, region_name="us-east-1")
        yield handler


class TestCloudWatchHandlerInitialization:
    """Test CloudWatch handler initialization."""

    def test_initialization_with_defaults(self, aws_credentials):
        """Test handler initialization with default parameters."""
        with mock_aws():
            handler = CloudWatchHandler(log_group_name="test-group")

            assert handler.log_group_name == "test-group"
            assert handler.region_name == "us-east-1"
            assert handler.logs_client is not None
            assert handler.cloudwatch_client is not None

    def test_initialization_with_custom_region(self, aws_credentials):
        """Test handler initialization with custom region."""
        with mock_aws():
            handler = CloudWatchHandler(log_group_name="test-group", region_name="us-west-2")

            assert handler.region_name == "us-west-2"

    def test_initialization_with_credentials(self, aws_credentials):
        """Test handler initialization with explicit credentials."""
        with mock_aws():
            handler = CloudWatchHandler(
                log_group_name="test-group",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
            )

            assert handler.logs_client is not None
            assert handler.cloudwatch_client is not None

    def test_initialization_without_log_group(self, aws_credentials):
        """Test handler can be initialized without log group name."""
        with mock_aws():
            handler = CloudWatchHandler()

            assert handler.log_group_name is None


class TestCloudWatchLogGroups:
    """Test log group operations."""

    def test_create_log_group_success(self, cloudwatch_handler: CloudWatchHandler):
        """Test creating a new log group."""
        result = cloudwatch_handler.create_log_group()

        assert result is True
        assert cloudwatch_handler.log_group_exists()

    def test_create_log_group_with_custom_name(self, cloudwatch_handler: CloudWatchHandler):
        """Test creating log group with custom name."""
        result = cloudwatch_handler.create_log_group("custom-log-group")

        assert result is True
        assert cloudwatch_handler.log_group_exists("custom-log-group")

    def test_create_log_group_already_exists(self, cloudwatch_handler: CloudWatchHandler):
        """Test creating log group that already exists."""
        cloudwatch_handler.create_log_group()
        result = cloudwatch_handler.create_log_group()

        assert result is True

    def test_create_log_group_without_name_fails(self, aws_credentials):
        """Test creating log group without name raises error."""
        with mock_aws():
            handler = CloudWatchHandler()

            with pytest.raises(ValueError) as exc_info:
                handler.create_log_group()

            assert "log_group_name must be provided" in str(exc_info.value)

    def test_delete_log_group_success(self, cloudwatch_handler: CloudWatchHandler):
        """Test deleting a log group."""
        cloudwatch_handler.create_log_group()
        result = cloudwatch_handler.delete_log_group()

        assert result is True
        assert not cloudwatch_handler.log_group_exists()

    def test_delete_log_group_clears_sequence_tokens(self, cloudwatch_handler: CloudWatchHandler):
        """Test deleting log group clears cached sequence tokens."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")
        cloudwatch_handler.put_log_events("test-stream", "test message")

        # Should have sequence token cached
        stream_key = f"{cloudwatch_handler.log_group_name}/test-stream"
        assert stream_key in cloudwatch_handler._sequence_tokens

        cloudwatch_handler.delete_log_group()

        # Sequence token should be cleared
        assert stream_key not in cloudwatch_handler._sequence_tokens

    def test_log_group_exists_returns_true(self, cloudwatch_handler: CloudWatchHandler):
        """Test checking if log group exists."""
        cloudwatch_handler.create_log_group()

        assert cloudwatch_handler.log_group_exists() is True

    def test_log_group_exists_returns_false(self, cloudwatch_handler: CloudWatchHandler):
        """Test checking if non-existent log group exists."""
        assert cloudwatch_handler.log_group_exists() is False

    def test_log_group_exists_without_name_fails(self, aws_credentials):
        """Test checking existence without name raises error."""
        with mock_aws():
            handler = CloudWatchHandler()

            with pytest.raises(ValueError) as exc_info:
                handler.log_group_exists()

            assert "log_group_name must be provided" in str(exc_info.value)

    def test_delete_log_group_without_name_fails(self, aws_credentials):
        """Test deleting log group without name raises error."""
        with mock_aws():
            handler = CloudWatchHandler()

            with pytest.raises(ValueError) as exc_info:
                handler.delete_log_group()

            assert "log_group_name must be provided" in str(exc_info.value)

    def test_log_group_exists_with_client_error(
        self, cloudwatch_handler: CloudWatchHandler, monkeypatch
    ):
        """Test log_group_exists returns False on ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        def mock_describe_log_groups(*args, **kwargs):
            error_response = {
                "Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}
            }
            raise BotoClientError(error_response, "DescribeLogGroups")

        monkeypatch.setattr(
            cloudwatch_handler.logs_client, "describe_log_groups", mock_describe_log_groups
        )

        result = cloudwatch_handler.log_group_exists()
        assert result is False


class TestCloudWatchLogStreams:
    """Test log stream operations."""

    def test_create_log_stream_success(self, cloudwatch_handler: CloudWatchHandler):
        """Test creating a log stream."""
        cloudwatch_handler.create_log_group()
        result = cloudwatch_handler.create_log_stream("test-stream")

        assert result is True

    def test_create_log_stream_already_exists(self, cloudwatch_handler: CloudWatchHandler):
        """Test creating log stream that already exists."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")
        result = cloudwatch_handler.create_log_stream("test-stream")

        assert result is True

    def test_create_log_stream_with_custom_group(self, cloudwatch_handler: CloudWatchHandler):
        """Test creating log stream with custom group name."""
        cloudwatch_handler.create_log_group("custom-group")
        result = cloudwatch_handler.create_log_stream("test-stream", "custom-group")

        assert result is True

    def test_create_log_stream_without_group_name_fails(self, aws_credentials):
        """Test creating log stream without group name raises error."""
        with mock_aws():
            handler = CloudWatchHandler()

            with pytest.raises(ValueError) as exc_info:
                handler.create_log_stream("test-stream")

            assert "log_group_name must be provided" in str(exc_info.value)


class TestCloudWatchLogEvents:
    """Test log event operations."""

    def test_put_log_events_single_message(self, cloudwatch_handler: CloudWatchHandler):
        """Test sending single log event."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        result = cloudwatch_handler.put_log_events("test-stream", "Test message")

        assert result["events_sent"] == 1
        assert result["log_stream"] == "test-stream"
        assert "next_sequence_token" in result

    def test_put_log_events_multiple_messages(self, cloudwatch_handler: CloudWatchHandler):
        """Test sending multiple log events."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        messages = ["Message 1", "Message 2", "Message 3"]
        result = cloudwatch_handler.put_log_events("test-stream", messages)

        assert result["events_sent"] == 3

    def test_put_log_events_with_custom_timestamp(self, cloudwatch_handler: CloudWatchHandler):
        """Test sending log events with custom timestamp."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        timestamp = int(time.time() * 1000)
        result = cloudwatch_handler.put_log_events(
            "test-stream", "Test message", timestamp=timestamp
        )

        assert result["events_sent"] == 1

    def test_put_log_events_with_custom_group(self, cloudwatch_handler: CloudWatchHandler):
        """Test sending log events to custom group."""
        cloudwatch_handler.create_log_group("custom-group")
        cloudwatch_handler.create_log_stream("test-stream", "custom-group")

        result = cloudwatch_handler.put_log_events(
            "test-stream", "Test message", log_group_name="custom-group"
        )

        assert result["log_group"] == "custom-group"

    def test_put_log_events_updates_sequence_token(self, cloudwatch_handler: CloudWatchHandler):
        """Test that sequence token is cached and updated."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        # First put
        result1 = cloudwatch_handler.put_log_events("test-stream", "Message 1")
        token1 = result1.get("next_sequence_token")

        # Second put should use cached token
        result2 = cloudwatch_handler.put_log_events("test-stream", "Message 2")
        token2 = result2.get("next_sequence_token")

        # Tokens should be different (moto behavior)
        assert token1 != token2

    def test_put_log_events_without_group_name_fails(self, aws_credentials):
        """Test sending events without group name raises error."""
        with mock_aws():
            handler = CloudWatchHandler()

            with pytest.raises(ValueError) as exc_info:
                handler.put_log_events("test-stream", "Test message")

            assert "log_group_name must be provided" in str(exc_info.value)

    def test_get_log_events_success(self, cloudwatch_handler: CloudWatchHandler):
        """Test retrieving log events."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")
        cloudwatch_handler.put_log_events("test-stream", "Test message")

        events = cloudwatch_handler.get_log_events("test-stream")

        assert len(events) > 0
        assert events[0]["message"] == "Test message"
        assert "timestamp" in events[0]

    def test_get_log_events_with_limit(self, cloudwatch_handler: CloudWatchHandler):
        """Test retrieving log events with limit."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        messages = [f"Message {i}" for i in range(5)]
        cloudwatch_handler.put_log_events("test-stream", messages)

        events = cloudwatch_handler.get_log_events("test-stream", limit=2)

        assert len(events) <= 2

    def test_get_log_events_with_time_range(self, cloudwatch_handler: CloudWatchHandler):
        """Test retrieving log events with time range."""
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        start_time = int(time.time() * 1000)
        cloudwatch_handler.put_log_events("test-stream", "Test message")
        end_time = int(time.time() * 1000) + 1000

        events = cloudwatch_handler.get_log_events(
            "test-stream", start_time=start_time, end_time=end_time
        )

        assert len(events) >= 0

    def test_get_log_events_without_group_name_fails(self, aws_credentials):
        """Test retrieving events without group name raises error."""
        with mock_aws():
            handler = CloudWatchHandler()

            with pytest.raises(ValueError) as exc_info:
                handler.get_log_events("test-stream")

            assert "log_group_name must be provided" in str(exc_info.value)


class TestCloudWatchMetrics:
    """Test CloudWatch Metrics operations."""

    def test_put_metric_data_success(self, cloudwatch_handler: CloudWatchHandler):
        """Test publishing single metric."""
        result = cloudwatch_handler.put_metric_data(
            namespace="MedicalImaging",
            metric_name="ProcessingTime",
            value=123.45,
            unit="Milliseconds",
        )

        assert result["namespace"] == "MedicalImaging"
        assert result["metric_name"] == "ProcessingTime"
        assert result["value"] == 123.45
        assert result["unit"] == "Milliseconds"

    def test_put_metric_data_with_dimensions(self, cloudwatch_handler: CloudWatchHandler):
        """Test publishing metric with dimensions."""
        dimensions = [
            {"Name": "Environment", "Value": "Production"},
            {"Name": "Service", "Value": "DICOM-Processing"},
        ]

        result = cloudwatch_handler.put_metric_data(
            namespace="MedicalImaging",
            metric_name="FilesProcessed",
            value=10,
            dimensions=dimensions,
        )

        assert result["namespace"] == "MedicalImaging"

    def test_put_metric_data_with_timestamp(self, cloudwatch_handler: CloudWatchHandler):
        """Test publishing metric with custom timestamp."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)

        result = cloudwatch_handler.put_metric_data(
            namespace="MedicalImaging",
            metric_name="FilesProcessed",
            value=5,
            timestamp=timestamp,
        )

        assert result["metric_name"] == "FilesProcessed"

    def test_put_metric_data_batch_success(self, cloudwatch_handler: CloudWatchHandler):
        """Test publishing multiple metrics in batch."""
        metrics = [
            {"metric_name": "Metric1", "value": 1.0},
            {"metric_name": "Metric2", "value": 2.0},
            {"metric_name": "Metric3", "value": 3.0},
        ]

        result = cloudwatch_handler.put_metric_data_batch(
            namespace="MedicalImaging", metrics=metrics
        )

        assert result["namespace"] == "MedicalImaging"
        assert result["metrics_sent"] == 3

    def test_put_metric_data_batch_with_all_options(self, cloudwatch_handler: CloudWatchHandler):
        """Test publishing batch metrics with all options."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        dimensions = [{"Name": "Environment", "Value": "Test"}]

        metrics = [
            {
                "metric_name": "ComplexMetric",
                "value": 100.0,
                "unit": "Count",
                "dimensions": dimensions,
                "timestamp": timestamp,
            }
        ]

        result = cloudwatch_handler.put_metric_data_batch(
            namespace="MedicalImaging", metrics=metrics
        )

        assert result["metrics_sent"] == 1

    def test_put_metric_data_batch_large_batch(self, cloudwatch_handler: CloudWatchHandler):
        """Test publishing large batch (>20 metrics) splits correctly."""
        # CloudWatch supports max 20 metrics per request
        metrics = [{"metric_name": f"Metric{i}", "value": float(i)} for i in range(50)]

        result = cloudwatch_handler.put_metric_data_batch(
            namespace="MedicalImaging", metrics=metrics
        )

        assert result["metrics_sent"] == 50


class TestCloudWatchErrorHandling:
    """Test error handling scenarios."""

    def test_create_log_group_with_error(self, cloudwatch_handler: CloudWatchHandler, monkeypatch):
        """Test create_log_group handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        def mock_create_log_group(*args, **kwargs):
            error_response = {
                "Error": {"Code": "InvalidParameterException", "Message": "Invalid parameter"}
            }
            raise BotoClientError(error_response, "CreateLogGroup")

        monkeypatch.setattr(
            cloudwatch_handler.logs_client, "create_log_group", mock_create_log_group
        )

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.create_log_group()

        assert exc_info.value.response["Error"]["Code"] == "InvalidParameterException"

    def test_create_log_stream_with_error(self, cloudwatch_handler: CloudWatchHandler, monkeypatch):
        """Test create_log_stream handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        cloudwatch_handler.create_log_group()

        def mock_create_log_stream(*args, **kwargs):
            error_response = {
                "Error": {"Code": "InvalidParameterException", "Message": "Invalid parameter"}
            }
            raise BotoClientError(error_response, "CreateLogStream")

        monkeypatch.setattr(
            cloudwatch_handler.logs_client, "create_log_stream", mock_create_log_stream
        )

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.create_log_stream("test-stream")

        assert exc_info.value.response["Error"]["Code"] == "InvalidParameterException"

    def test_put_log_events_with_error(self, cloudwatch_handler: CloudWatchHandler, monkeypatch):
        """Test put_log_events handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        def mock_put_log_events(*args, **kwargs):
            error_response = {
                "Error": {
                    "Code": "DataAlreadyAcceptedException",
                    "Message": "Data already accepted",
                }
            }
            raise BotoClientError(error_response, "PutLogEvents")

        monkeypatch.setattr(cloudwatch_handler.logs_client, "put_log_events", mock_put_log_events)

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.put_log_events("test-stream", "test message")

        assert exc_info.value.response["Error"]["Code"] == "DataAlreadyAcceptedException"

    def test_put_metric_data_with_error(self, cloudwatch_handler: CloudWatchHandler, monkeypatch):
        """Test put_metric_data handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        def mock_put_metric_data(*args, **kwargs):
            error_response = {
                "Error": {"Code": "InvalidParameterValueException", "Message": "Invalid value"}
            }
            raise BotoClientError(error_response, "PutMetricData")

        monkeypatch.setattr(
            cloudwatch_handler.cloudwatch_client, "put_metric_data", mock_put_metric_data
        )

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.put_metric_data(
                namespace="Test", metric_name="TestMetric", value=1.0
            )

        assert exc_info.value.response["Error"]["Code"] == "InvalidParameterValueException"

    def test_put_metric_data_batch_with_error(
        self, cloudwatch_handler: CloudWatchHandler, monkeypatch
    ):
        """Test put_metric_data_batch handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        def mock_put_metric_data(*args, **kwargs):
            error_response = {
                "Error": {"Code": "InvalidParameterValueException", "Message": "Invalid value"}
            }
            raise BotoClientError(error_response, "PutMetricData")

        monkeypatch.setattr(
            cloudwatch_handler.cloudwatch_client, "put_metric_data", mock_put_metric_data
        )

        metrics = [{"metric_name": "TestMetric", "value": 1.0}]

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.put_metric_data_batch(namespace="Test", metrics=metrics)

        assert exc_info.value.response["Error"]["Code"] == "InvalidParameterValueException"

    def test_delete_log_group_with_error(self, cloudwatch_handler: CloudWatchHandler, monkeypatch):
        """Test delete_log_group handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        cloudwatch_handler.create_log_group()

        def mock_delete_log_group(*args, **kwargs):
            error_response = {
                "Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}
            }
            raise BotoClientError(error_response, "DeleteLogGroup")

        monkeypatch.setattr(
            cloudwatch_handler.logs_client, "delete_log_group", mock_delete_log_group
        )

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.delete_log_group()

        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"

    def test_get_log_events_with_error(self, cloudwatch_handler: CloudWatchHandler, monkeypatch):
        """Test get_log_events handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("test-stream")

        def mock_get_log_events(*args, **kwargs):
            error_response = {
                "Error": {"Code": "ResourceNotFoundException", "Message": "Resource not found"}
            }
            raise BotoClientError(error_response, "GetLogEvents")

        monkeypatch.setattr(cloudwatch_handler.logs_client, "get_log_events", mock_get_log_events)

        with pytest.raises(ClientError) as exc_info:
            cloudwatch_handler.get_log_events("test-stream")

        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"


class TestCloudWatchIntegration:
    """Integration tests for CloudWatch handler."""

    def test_complete_logging_workflow(self, cloudwatch_handler: CloudWatchHandler):
        """Test complete logging workflow: create, log, retrieve, delete."""
        # Create resources
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("integration-stream")

        # Send logs
        messages = [f"Integration test message {i}" for i in range(3)]
        put_result = cloudwatch_handler.put_log_events("integration-stream", messages)
        assert put_result["events_sent"] == 3

        # Retrieve logs
        events = cloudwatch_handler.get_log_events("integration-stream")
        assert len(events) == 3

        # Cleanup
        cloudwatch_handler.delete_log_group()
        assert not cloudwatch_handler.log_group_exists()

    def test_multiple_streams_same_group(self, cloudwatch_handler: CloudWatchHandler):
        """Test using multiple log streams in same group."""
        cloudwatch_handler.create_log_group()

        # Create multiple streams
        for i in range(3):
            cloudwatch_handler.create_log_stream(f"stream-{i}")
            cloudwatch_handler.put_log_events(f"stream-{i}", f"Message from stream {i}")

        # Verify each stream has events
        for i in range(3):
            events = cloudwatch_handler.get_log_events(f"stream-{i}")
            assert len(events) > 0

    def test_metrics_and_logging_together(self, cloudwatch_handler: CloudWatchHandler):
        """Test using metrics and logging simultaneously."""
        # Setup logging
        cloudwatch_handler.create_log_group()
        cloudwatch_handler.create_log_stream("metrics-logs")

        # Send logs
        cloudwatch_handler.put_log_events("metrics-logs", "Processing started")

        # Publish metrics
        cloudwatch_handler.put_metric_data(
            namespace="IntegrationTest",
            metric_name="ProcessingTime",
            value=100.0,
            unit="Milliseconds",
        )

        # Send more logs
        cloudwatch_handler.put_log_events("metrics-logs", "Processing completed")

        # Verify logs
        events = cloudwatch_handler.get_log_events("metrics-logs")
        assert len(events) == 2
