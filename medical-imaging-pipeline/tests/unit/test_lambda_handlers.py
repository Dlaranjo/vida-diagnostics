"""
Unit tests for Lambda handlers.

Tests Lambda function handlers with mocked AWS services.
"""

import json
from unittest.mock import Mock, patch

import pytest
from moto import mock_aws
from pydantic import ValidationError

from src.orchestration.lambda_handlers import (
    DeidentificationHandler,
    IngestionHandler,
    ValidationHandler,
    lambda_handler_wrapper,
)


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def lambda_context():
    """Create mock Lambda context."""
    context = Mock()
    context.aws_request_id = "test-request-id-12345"
    context.function_name = "test-function"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    return context


@pytest.fixture
def s3_event():
    """Create mock S3 event."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test-file.dcm", "size": 1024},
                },
            }
        ]
    }


class TestLambdaHandlerWrapper:
    """Test lambda_handler_wrapper decorator."""

    def test_wrapper_success_without_cloudwatch(self, lambda_context):
        """Test wrapper with successful handler execution."""

        @lambda_handler_wrapper(handler_name="test-handler", enable_cloudwatch=False)
        def test_handler(event, context):
            return {"result": "success", "data": event.get("data")}

        event = {"data": "test-data"}
        response = test_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["result"] == "success"
        assert body["data"] == "test-data"

    def test_wrapper_with_exception(self, lambda_context):
        """Test wrapper handles exceptions."""

        @lambda_handler_wrapper(handler_name="test-handler", enable_cloudwatch=False)
        def failing_handler(event, context):
            raise ValueError("Test error")

        event = {}
        response = failing_handler(event, lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert body["error"] == "Test error"
        assert body["error_type"] == "ValueError"

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_wrapper_with_cloudwatch_success(self, mock_cloudwatch_class, lambda_context):
        """Test wrapper with CloudWatch enabled."""
        mock_cloudwatch = Mock()
        mock_cloudwatch_class.return_value = mock_cloudwatch

        @lambda_handler_wrapper(
            handler_name="test-handler",
            enable_cloudwatch=True,
            log_group_name="/aws/lambda/test",
            metric_namespace="TestMetrics",
        )
        def test_handler(event, context):
            return {"result": "success"}

        event = {}
        response = test_handler(event, lambda_context)

        assert response["statusCode"] == 200
        mock_cloudwatch.create_log_group.assert_called_once()
        mock_cloudwatch.put_metric_data.assert_called_once()

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_wrapper_with_cloudwatch_logging_failure(self, mock_cloudwatch_class, lambda_context):
        """Test wrapper continues when CloudWatch logging fails."""
        mock_cloudwatch = Mock()
        mock_cloudwatch.create_log_group.side_effect = Exception("CloudWatch error")
        mock_cloudwatch_class.return_value = mock_cloudwatch

        @lambda_handler_wrapper(
            handler_name="test-handler",
            enable_cloudwatch=True,
            log_group_name="/aws/lambda/test",
        )
        def test_handler(event, context):
            return {"result": "success"}

        event = {}
        response = test_handler(event, lambda_context)

        # Should still succeed despite CloudWatch error
        assert response["statusCode"] == 200

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_wrapper_with_cloudwatch_metric_failure(self, mock_cloudwatch_class, lambda_context):
        """Test wrapper continues when CloudWatch metric fails."""
        mock_cloudwatch = Mock()
        mock_cloudwatch.put_metric_data.side_effect = Exception("Metric error")
        mock_cloudwatch_class.return_value = mock_cloudwatch

        @lambda_handler_wrapper(
            handler_name="test-handler",
            enable_cloudwatch=True,
            metric_namespace="TestMetrics",
        )
        def test_handler(event, context):
            return {"result": "success"}

        event = {}
        response = test_handler(event, lambda_context)

        # Should still succeed despite metric error
        assert response["statusCode"] == 200

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_wrapper_publishes_failure_metric(self, mock_cloudwatch_class, lambda_context):
        """Test wrapper publishes failure metric on exception."""
        mock_cloudwatch = Mock()
        mock_cloudwatch_class.return_value = mock_cloudwatch

        @lambda_handler_wrapper(
            handler_name="test-handler",
            enable_cloudwatch=True,
            metric_namespace="TestMetrics",
        )
        def failing_handler(event, context):
            raise ValueError("Test error")

        event = {}
        response = failing_handler(event, lambda_context)

        assert response["statusCode"] == 500
        # Should call put_metric_data for failure
        mock_cloudwatch.put_metric_data.assert_called()

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_wrapper_handles_metric_failure_on_exception(
        self, mock_cloudwatch_class, lambda_context
    ):
        """Test wrapper continues when failure metric publishing fails."""
        mock_cloudwatch = Mock()
        mock_cloudwatch.put_metric_data.side_effect = Exception("Metric failed")
        mock_cloudwatch_class.return_value = mock_cloudwatch

        @lambda_handler_wrapper(
            handler_name="test-handler",
            enable_cloudwatch=True,
            metric_namespace="TestMetrics",
        )
        def failing_handler(event, context):
            raise ValueError("Test error")

        event = {}
        response = failing_handler(event, lambda_context)

        # Should still return error response despite metric failure
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["error"] == "Test error"


class TestIngestionHandler:
    """Test IngestionHandler."""

    @pytest.fixture
    def ingestion_handler(self, aws_credentials):
        """Create IngestionHandler instance."""
        with mock_aws():
            handler = IngestionHandler(
                output_bucket="test-output-bucket",
                region_name="us-east-1",
                enable_cloudwatch=False,
            )
            yield handler

    def test_initialization(self, ingestion_handler):
        """Test handler initialization."""
        assert ingestion_handler.output_bucket == "test-output-bucket"
        assert ingestion_handler.s3_handler is not None
        assert ingestion_handler.parser is not None

    @patch("src.orchestration.lambda_handlers.S3Handler")
    @patch("src.orchestration.lambda_handlers.ValidatedDICOMParser")
    def test_handle_success(
        self,
        mock_parser_class,
        mock_s3_class,
        s3_event,
        lambda_context,
        tmp_path,
    ):
        """Test successful ingestion handling."""
        # Setup mocks
        mock_s3 = Mock()
        mock_s3_class.return_value = mock_s3
        mock_s3.download_file.return_value = {"status": "success"}
        mock_s3.upload_file.return_value = {"status": "success"}

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        # Create mock validated metadata
        from src.validation.schemas import (
            DICOMMetadataSchema,
            DICOMInstanceSchema,
            PatientSchema,
            SeriesSchema,
            StudySchema,
        )

        mock_metadata = DICOMMetadataSchema(
            patient=PatientSchema(patient_id="P123", patient_sex="M"),
            study=StudySchema(study_instance_uid="1.2.3.4.5"),
            series=SeriesSchema(series_instance_uid="1.2.3.4.5.6", modality="CT"),
            instance=DICOMInstanceSchema(sop_instance_uid="1.2.3.4.5.6.7", sop_class_uid="1.2.840"),
        )
        mock_parser.parse_and_validate.return_value = mock_metadata

        handler = IngestionHandler(output_bucket="test-bucket", enable_cloudwatch=False)

        # Execute
        result = handler.handle(s3_event, lambda_context)

        # Verify
        assert result["processed"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "success"
        assert "validated_key" in result["results"][0]

    @patch("src.orchestration.lambda_handlers.S3Handler")
    @patch("src.orchestration.lambda_handlers.ValidatedDICOMParser")
    def test_handle_validation_failure(
        self, mock_parser_class, mock_s3_class, s3_event, lambda_context
    ):
        """Test handling validation failure."""
        # Setup mocks
        mock_s3 = Mock()
        mock_s3_class.return_value = mock_s3
        mock_s3.download_file.return_value = {"status": "success"}

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse_and_validate.side_effect = ValidationError.from_exception_data(
            "test",
            [
                {
                    "type": "value_error",
                    "loc": ("field",),
                    "msg": "Invalid",
                    "input": None,
                    "ctx": {"error": "test"},
                }
            ],
        )

        handler = IngestionHandler(output_bucket="test-bucket", enable_cloudwatch=False)

        # Execute
        result = handler.handle(s3_event, lambda_context)

        # Verify
        assert result["processed"] == 1

class TestValidationHandler:
    """Test ValidationHandler."""

    @pytest.fixture
    def validation_handler(self, aws_credentials):
        """Create ValidationHandler instance."""
        with mock_aws():
            handler = ValidationHandler(region_name="us-east-1", enable_cloudwatch=False)
            yield handler

    def test_initialization(self, validation_handler):
        """Test handler initialization."""
        assert validation_handler.parser is not None

    def test_handle_valid_metadata(self, validation_handler, lambda_context):
        """Test handling valid metadata."""
        event = {
            "metadata": {
                "patient_id": "P123",
                "patient_sex": "M",
                "study_instance_uid": "1.2.3.4.5",
                "series_instance_uid": "1.2.3.4.5.6",
                "modality": "CT",
                "sop_instance_uid": "1.2.3.4.5.6.7",
                "sop_class_uid": "1.2.840",
            }
        }

        result = validation_handler.handle(event, lambda_context)

        assert result["status"] == "valid"
        assert result["patient_id"] == "P123"
        assert result["modality"] == "CT"

    def test_handle_invalid_metadata(self, validation_handler, lambda_context):
        """Test handling invalid metadata."""
        event = {
            "metadata": {
                "patient_id": "P123",
                "study_instance_uid": "invalid-uid",  # Invalid UID
                "series_instance_uid": "1.2.3.4.5.6",
                "modality": "CT",
                "sop_instance_uid": "1.2.3.4.5.6.7",
                "sop_class_uid": "1.2.840",
            }
        }

        result = validation_handler.handle(event, lambda_context)

        assert result["status"] == "invalid"
        assert "error" in result

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_handle_publishes_success_metric(self, mock_cw_class, lambda_context):
        """Test handler publishes success metric."""
        mock_cw = Mock()
        mock_cw_class.return_value = mock_cw

        handler = ValidationHandler(enable_cloudwatch=True)

        event = {
            "metadata": {
                "patient_id": "P123",
                "patient_sex": "M",
                "study_instance_uid": "1.2.3.4.5",
                "series_instance_uid": "1.2.3.4.5.6",
                "modality": "CT",
                "sop_instance_uid": "1.2.3.4.5.6.7",
                "sop_class_uid": "1.2.840",
            }
        }

        result = handler.handle(event, lambda_context)

        assert result["status"] == "valid"
        mock_cw.put_metric_data.assert_called()

    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_handle_publishes_failure_metric(self, mock_cw_class, lambda_context):
        """Test handler publishes failure metric."""
        mock_cw = Mock()
        mock_cw_class.return_value = mock_cw

        handler = ValidationHandler(enable_cloudwatch=True)

        event = {"metadata": {"patient_id": "P123"}}  # Missing required fields

        result = handler.handle(event, lambda_context)

        assert result["status"] == "invalid"
        mock_cw.put_metric_data.assert_called()


class TestDeidentificationHandler:
    """Test DeidentificationHandler."""

    @pytest.fixture
    def deidentification_handler(self, aws_credentials):
        """Create DeidentificationHandler instance."""
        with mock_aws():
            handler = DeidentificationHandler(
                output_bucket="test-deidentified-bucket",
                region_name="us-east-1",
                enable_cloudwatch=False,
            )
            yield handler

    def test_initialization(self, deidentification_handler):
        """Test handler initialization."""
        assert deidentification_handler.output_bucket == "test-deidentified-bucket"
        assert deidentification_handler.s3_handler is not None
        assert deidentification_handler.deidentifier is not None

    @patch("src.orchestration.lambda_handlers.S3Handler")
    @patch("src.orchestration.lambda_handlers.DICOMDeidentifier")
    def test_handle_success(self, mock_deidentifier_class, mock_s3_class, s3_event, lambda_context):
        """Test successful de-identification handling."""
        # Setup mocks
        mock_s3 = Mock()
        mock_s3_class.return_value = mock_s3
        mock_s3.download_file.return_value = {"status": "success"}
        mock_s3.upload_file.return_value = {"status": "success"}

        mock_deidentifier = Mock()
        mock_deidentifier_class.return_value = mock_deidentifier
        mock_deidentifier.deidentify_file.return_value = {
            "PatientID": "ANON123",
            "PatientName": "ANONYMIZED",
        }

        handler = DeidentificationHandler(output_bucket="test-bucket", enable_cloudwatch=False)

        # Execute
        result = handler.handle(s3_event, lambda_context)

        # Verify
        assert result["processed"] == 1
        assert result["results"][0]["status"] == "success"
        assert "deidentified_key" in result["results"][0]
        assert result["results"][0]["anonymized_patient_id"] == "ANON123"

    @patch("src.orchestration.lambda_handlers.S3Handler")
    @patch("src.orchestration.lambda_handlers.DICOMDeidentifier")
    def test_handle_deidentification_failure(
        self, mock_deidentifier_class, mock_s3_class, s3_event, lambda_context
    ):
        """Test handling de-identification failure."""
        # Setup mocks
        mock_s3 = Mock()
        mock_s3_class.return_value = mock_s3
        mock_s3.download_file.return_value = {"status": "success"}

        mock_deidentifier = Mock()
        mock_deidentifier_class.return_value = mock_deidentifier
        mock_deidentifier.deidentify_file.side_effect = Exception("Deidentification failed")

        handler = DeidentificationHandler(output_bucket="test-bucket", enable_cloudwatch=False)

        # Execute
        result = handler.handle(s3_event, lambda_context)

        # Verify
        assert result["processed"] == 1
        assert result["results"][0]["status"] == "failed"
        assert "error" in result["results"][0]

    @patch("src.orchestration.lambda_handlers.S3Handler")
    @patch("src.orchestration.lambda_handlers.DICOMDeidentifier")
    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_handle_publishes_metrics(
        self,
        mock_cw_class,
        mock_deidentifier_class,
        mock_s3_class,
        s3_event,
        lambda_context,
    ):
        """Test handler publishes CloudWatch metrics."""
        # Setup mocks
        mock_s3 = Mock()
        mock_s3_class.return_value = mock_s3
        mock_s3.download_file.return_value = {"status": "success"}
        mock_s3.upload_file.return_value = {"status": "success"}

        mock_deidentifier = Mock()
        mock_deidentifier_class.return_value = mock_deidentifier
        mock_deidentifier.deidentify_file.return_value = {"PatientID": "ANON123"}

        mock_cw = Mock()
        mock_cw_class.return_value = mock_cw

        handler = DeidentificationHandler(output_bucket="test-bucket", enable_cloudwatch=True)

        # Execute
        _ = handler.handle(s3_event, lambda_context)

        # Verify metric was published
        mock_cw.put_metric_data.assert_called()

    @patch("src.orchestration.lambda_handlers.S3Handler")
    @patch("src.orchestration.lambda_handlers.DICOMDeidentifier")
    @patch("src.orchestration.lambda_handlers.CloudWatchHandler")
    def test_handle_publishes_failure_metric(
        self,
        mock_cw_class,
        mock_deidentifier_class,
        mock_s3_class,
        s3_event,
        lambda_context,
    ):
        """Test handler publishes failure metric."""
        # Setup mocks
        mock_s3 = Mock()
        mock_s3_class.return_value = mock_s3
        mock_s3.download_file.return_value = {"status": "success"}

        mock_deidentifier = Mock()
        mock_deidentifier_class.return_value = mock_deidentifier
        mock_deidentifier.deidentify_file.side_effect = Exception("Failed")

        mock_cw = Mock()
        mock_cw_class.return_value = mock_cw

        handler = DeidentificationHandler(output_bucket="test-bucket", enable_cloudwatch=True)

        # Execute
        _ = handler.handle(s3_event, lambda_context)

        # Verify failure metric was published
        calls = mock_cw.put_metric_data.call_args_list
        # Should have at least one call for failure metric
        assert len(calls) > 0
