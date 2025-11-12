"""
Lambda function handlers for DICOM processing pipeline.

Provides wrapper functions and handlers for AWS Lambda integration.
"""

import json
import traceback
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import unquote_plus

from src.ingestion.deidentifier import DICOMDeidentifier
from src.ingestion.validated_parser import ValidatedDICOMParser
from src.monitoring.cloudwatch_handler import CloudWatchHandler
from src.storage.s3_handler import S3Handler
from src.utils.logger import get_logger

logger = get_logger(__name__)


def lambda_handler_wrapper(
    handler_name: str,
    enable_cloudwatch: bool = True,
    log_group_name: Optional[str] = None,
    metric_namespace: Optional[str] = None,
) -> Callable:
    """
    Decorator for Lambda handler functions with monitoring and error handling.

    Args:
        handler_name: Name of the handler for logging
        enable_cloudwatch: Enable CloudWatch integration
        log_group_name: CloudWatch log group name
        metric_namespace: CloudWatch metric namespace

    Returns:
        Decorated handler function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            """
            Lambda handler wrapper with error handling and monitoring.

            Args:
                event: Lambda event
                context: Lambda context

            Returns:
                Response dictionary
            """
            cloudwatch = None
            if enable_cloudwatch:
                cloudwatch = CloudWatchHandler(log_group_name=log_group_name)

            try:
                # Log invocation
                logger.info(
                    f"Lambda handler '{handler_name}' invoked",
                    extra={
                        "handler": handler_name,
                        "request_id": getattr(context, "aws_request_id", None),
                    },
                )

                if cloudwatch and log_group_name:
                    try:
                        cloudwatch.create_log_group()
                        cloudwatch.create_log_stream(getattr(context, "aws_request_id", "default"))
                        cloudwatch.put_log_events(
                            getattr(context, "aws_request_id", "default"),
                            f"Handler {handler_name} started",
                        )
                    except Exception as cw_error:
                        logger.warning(f"CloudWatch logging failed: {cw_error}")

                # Execute handler
                result = func(event, context)

                # Log success
                logger.info(f"Lambda handler '{handler_name}' completed successfully")

                if cloudwatch and metric_namespace:
                    try:
                        cloudwatch.put_metric_data(
                            namespace=metric_namespace,
                            metric_name=f"{handler_name}Success",
                            value=1.0,
                            unit="Count",
                        )
                    except Exception as metric_error:
                        logger.warning(f"CloudWatch metric failed: {metric_error}")

                return {
                    "statusCode": 200,
                    "body": json.dumps(result),
                }

            except Exception as e:
                # Log error
                error_msg = f"Lambda handler '{handler_name}' failed: {str(e)}"
                logger.error(error_msg, exc_info=True)

                if cloudwatch and metric_namespace:
                    try:
                        cloudwatch.put_metric_data(
                            namespace=metric_namespace,
                            metric_name=f"{handler_name}Failure",
                            value=1.0,
                            unit="Count",
                        )
                    except Exception:
                        pass

                return {
                    "statusCode": 500,
                    "body": json.dumps(
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc(),
                        }
                    ),
                }

        return wrapper

    return decorator


class IngestionHandler:
    """
    Lambda handler for DICOM file ingestion and validation.

    Processes S3 upload events and validates DICOM files.
    """

    def __init__(
        self,
        output_bucket: str,
        region_name: str = "us-east-1",
        enable_cloudwatch: bool = True,
    ) -> None:
        """
        Initialize ingestion handler.

        Args:
            output_bucket: S3 bucket for validated files
            region_name: AWS region
            enable_cloudwatch: Enable CloudWatch monitoring
        """
        self.output_bucket = output_bucket
        self.region_name = region_name
        self.enable_cloudwatch = enable_cloudwatch

        self.s3_handler = S3Handler(bucket_name=output_bucket, region_name=region_name)
        self.parser = ValidatedDICOMParser()

        if enable_cloudwatch:
            self.cloudwatch = CloudWatchHandler(
                log_group_name="/aws/lambda/dicom-ingestion", region_name=region_name
            )

    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Handle S3 upload event for DICOM ingestion.

        Args:
            event: S3 event
            context: Lambda context

        Returns:
            Processing result
        """
        results = []

        # Parse S3 event
        records = event.get("Records", [])

        for record in records:
            try:
                # Extract S3 information
                s3_info = record.get("s3", {})
                bucket = s3_info.get("bucket", {}).get("name")
                key = unquote_plus(s3_info.get("object", {}).get("key", ""))

                logger.info(f"Processing DICOM file: s3://{bucket}/{key}")

                # Download file to temp
                temp_path = Path(f"/tmp/{Path(key).name}")
                self.s3_handler.download_file(s3_key=key, local_path=temp_path)

                # Validate DICOM
                validated_metadata = self.parser.parse_and_validate(temp_path)

                # Upload to validated bucket
                validated_key = f"validated/{key}"
                self.s3_handler.upload_file(
                    local_path=temp_path,
                    s3_key=validated_key,
                    metadata={
                        "patient_id": validated_metadata.patient.patient_id,
                        "study_uid": validated_metadata.study.study_instance_uid,
                        "modality": validated_metadata.series.modality,
                    },
                )

                result = {
                    "status": "success",
                    "source_key": key,
                    "validated_key": validated_key,
                    "metadata": {
                        "patient_id": validated_metadata.patient.patient_id,
                        "modality": validated_metadata.series.modality,
                    },
                }

                results.append(result)

                # Publish metric
                if self.enable_cloudwatch:
                    try:
                        self.cloudwatch.put_metric_data(
                            namespace="MedicalImaging/Ingestion",
                            metric_name="FilesProcessed",
                            value=1.0,
                            unit="Count",
                            dimensions=[
                                {"Name": "Modality", "Value": validated_metadata.series.modality}
                            ],
                        )
                    except Exception as metric_error:
                        logger.warning(f"Metric publishing failed: {metric_error}")

                # Cleanup
                temp_path.unlink(missing_ok=True)

            except Exception as e:
                logger.error(f"Failed to process {key}: {str(e)}", exc_info=True)
                results.append({"status": "failed", "source_key": key, "error": str(e)})

        return {
            "processed": len(results),
            "results": results,
        }


class ValidationHandler:
    """
    Lambda handler for DICOM validation.

    Validates DICOM metadata against schemas.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        enable_cloudwatch: bool = True,
    ) -> None:
        """
        Initialize validation handler.

        Args:
            region_name: AWS region
            enable_cloudwatch: Enable CloudWatch monitoring
        """
        self.region_name = region_name
        self.enable_cloudwatch = enable_cloudwatch
        self.parser = ValidatedDICOMParser()

        if enable_cloudwatch:
            self.cloudwatch = CloudWatchHandler(
                log_group_name="/aws/lambda/dicom-validation", region_name=region_name
            )

    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Handle validation request.

        Args:
            event: Validation event with metadata
            context: Lambda context

        Returns:
            Validation result
        """
        try:
            # Extract metadata from event
            metadata_dict = event.get("metadata", {})

            # Validate metadata
            validated = self.parser.validate_metadata_dict(metadata_dict)

            result = {
                "status": "valid",
                "patient_id": validated.patient.patient_id,
                "study_uid": validated.study.study_instance_uid,
                "modality": validated.series.modality,
            }

            # Publish metric
            if self.enable_cloudwatch:
                try:
                    self.cloudwatch.put_metric_data(
                        namespace="MedicalImaging/Validation",
                        metric_name="ValidationSuccess",
                        value=1.0,
                        unit="Count",
                    )
                except Exception:
                    pass

            return result

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}", exc_info=True)

            if self.enable_cloudwatch:
                try:
                    self.cloudwatch.put_metric_data(
                        namespace="MedicalImaging/Validation",
                        metric_name="ValidationFailure",
                        value=1.0,
                        unit="Count",
                    )
                except Exception:
                    pass

            return {
                "status": "invalid",
                "error": str(e),
                "error_type": type(e).__name__,
            }


class DeidentificationHandler:
    """
    Lambda handler for DICOM de-identification.

    Removes PHI from DICOM files.
    """

    def __init__(
        self,
        output_bucket: str,
        region_name: str = "us-east-1",
        enable_cloudwatch: bool = True,
    ) -> None:
        """
        Initialize de-identification handler.

        Args:
            output_bucket: S3 bucket for de-identified files
            region_name: AWS region
            enable_cloudwatch: Enable CloudWatch monitoring
        """
        self.output_bucket = output_bucket
        self.region_name = region_name
        self.enable_cloudwatch = enable_cloudwatch

        self.s3_handler = S3Handler(bucket_name=output_bucket, region_name=region_name)
        self.deidentifier = DICOMDeidentifier()

        if enable_cloudwatch:
            self.cloudwatch = CloudWatchHandler(
                log_group_name="/aws/lambda/dicom-deidentification",
                region_name=region_name,
            )

    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Handle de-identification request.

        Args:
            event: S3 event with DICOM file location
            context: Lambda context

        Returns:
            De-identification result
        """
        results = []

        # Parse S3 event
        records = event.get("Records", [])

        for record in records:
            try:
                # Extract S3 information
                s3_info = record.get("s3", {})
                bucket = s3_info.get("bucket", {}).get("name")
                key = unquote_plus(s3_info.get("object", {}).get("key", ""))

                logger.info(f"De-identifying DICOM file: s3://{bucket}/{key}")

                # Download file
                temp_input = Path(f"/tmp/input_{Path(key).name}")
                self.s3_handler.download_file(s3_key=key, local_path=temp_input)

                # De-identify
                temp_output = Path(f"/tmp/deidentified_{Path(key).name}")
                mapping = self.deidentifier.deidentify_file(
                    input_path=temp_input, output_path=temp_output
                )

                # Upload de-identified file
                deidentified_key = f"deidentified/{key}"
                self.s3_handler.upload_file(
                    local_path=temp_output,
                    s3_key=deidentified_key,
                    metadata={"deidentified": "true"},
                )

                result = {
                    "status": "success",
                    "source_key": key,
                    "deidentified_key": deidentified_key,
                    "anonymized_patient_id": mapping.get("PatientID"),
                }

                results.append(result)

                # Publish metric
                if self.enable_cloudwatch:
                    try:
                        self.cloudwatch.put_metric_data(
                            namespace="MedicalImaging/Deidentification",
                            metric_name="FilesDeidentified",
                            value=1.0,
                            unit="Count",
                        )
                    except Exception:
                        pass

                # Cleanup
                temp_input.unlink(missing_ok=True)
                temp_output.unlink(missing_ok=True)

            except Exception as e:
                logger.error(f"Failed to de-identify {key}: {str(e)}", exc_info=True)
                results.append({"status": "failed", "source_key": key, "error": str(e)})

                if self.enable_cloudwatch:
                    try:
                        self.cloudwatch.put_metric_data(
                            namespace="MedicalImaging/Deidentification",
                            metric_name="DeidentificationFailure",
                            value=1.0,
                            unit="Count",
                        )
                    except Exception:
                        pass

        return {
            "processed": len(results),
            "results": results,
        }
