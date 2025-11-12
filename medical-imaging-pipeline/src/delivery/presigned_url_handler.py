"""
Presigned URL handler for secure DICOM file delivery.

Provides methods for generating secure, time-limited URLs for downloading
de-identified DICOM files from S3.
"""

from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

from src.utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class PresignedUrlHandler:
    """Handler for generating presigned URLs for S3 file access."""

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        """
        Initialize PresignedUrlHandler.

        Args:
            bucket_name: S3 bucket name for file storage
            region_name: AWS region name
            aws_access_key_id: Optional AWS access key ID
            aws_secret_access_key: Optional AWS secret access key
        """
        self.bucket_name = bucket_name
        self.region_name = region_name

        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.s3_client = boto3.client("s3", **session_kwargs)

        log_execution(
            logger,
            operation="presigned_url_handler_init",
            status="initialized",
            details={"bucket": bucket_name, "region": region_name},
        )

    def generate_download_url(
        self,
        object_key: str,
        expiration_seconds: int = 3600,
        response_content_type: Optional[str] = None,
        response_content_disposition: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate presigned URL for downloading a file from S3.

        Args:
            object_key: S3 object key (file path)
            expiration_seconds: URL expiration time in seconds (default: 1 hour)
            response_content_type: Optional Content-Type header for response
            response_content_disposition: Optional Content-Disposition header

        Returns:
            Dict containing:
                - url: Presigned URL string
                - expires_in: Expiration time in seconds
                - object_key: S3 object key
                - bucket: S3 bucket name

        Raises:
            ClientError: If URL generation fails
        """
        log_execution(
            logger,
            operation="generate_download_url",
            status="started",
            details={"object_key": object_key, "expiration": expiration_seconds},
        )

        try:
            # Build parameters for presigned URL
            params = {"Bucket": self.bucket_name, "Key": object_key}

            # Add optional response headers
            if response_content_type:
                params["ResponseContentType"] = response_content_type

            if response_content_disposition:
                params["ResponseContentDisposition"] = response_content_disposition

            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expiration_seconds,
            )

            result = {
                "url": url,
                "expires_in": expiration_seconds,
                "object_key": object_key,
                "bucket": self.bucket_name,
            }

            log_execution(
                logger,
                operation="generate_download_url",
                status="completed",
                details={"object_key": object_key},
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="generate_download_url",
                status="failed",
                details={"object_key": object_key},
                error=e,
            )
            raise

    def generate_upload_url(
        self,
        object_key: str,
        expiration_seconds: int = 3600,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Generate presigned URL for uploading a file to S3.

        Args:
            object_key: S3 object key (file path)
            expiration_seconds: URL expiration time in seconds (default: 1 hour)
            content_type: Optional Content-Type for the upload
            metadata: Optional metadata dict to attach to the object

        Returns:
            Dict containing:
                - url: Presigned URL string
                - expires_in: Expiration time in seconds
                - object_key: S3 object key
                - bucket: S3 bucket name

        Raises:
            ClientError: If URL generation fails
        """
        log_execution(
            logger,
            operation="generate_upload_url",
            status="started",
            details={"object_key": object_key, "expiration": expiration_seconds},
        )

        try:
            # Build parameters for presigned URL
            params = {"Bucket": self.bucket_name, "Key": object_key}

            if content_type:
                params["ContentType"] = content_type

            if metadata:
                params["Metadata"] = metadata

            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=expiration_seconds,
            )

            result = {
                "url": url,
                "expires_in": expiration_seconds,
                "object_key": object_key,
                "bucket": self.bucket_name,
            }

            log_execution(
                logger,
                operation="generate_upload_url",
                status="completed",
                details={"object_key": object_key},
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="generate_upload_url",
                status="failed",
                details={"object_key": object_key},
                error=e,
            )
            raise

    def generate_batch_download_urls(
        self,
        object_keys: list[str],
        expiration_seconds: int = 3600,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate presigned URLs for multiple files.

        Args:
            object_keys: List of S3 object keys
            expiration_seconds: URL expiration time in seconds

        Returns:
            Dict mapping object_key to presigned URL info dict
        """
        log_execution(
            logger,
            operation="generate_batch_download_urls",
            status="started",
            details={"count": len(object_keys), "expiration": expiration_seconds},
        )

        results = {}
        failed_keys = []

        for object_key in object_keys:
            try:
                url_info = self.generate_download_url(
                    object_key=object_key, expiration_seconds=expiration_seconds
                )
                results[object_key] = url_info
            except ClientError as e:
                logger.warning(
                    f"Failed to generate URL for {object_key}: {str(e)}",
                    extra={"object_key": object_key, "error": str(e)},
                )
                failed_keys.append(object_key)

        log_execution(
            logger,
            operation="generate_batch_download_urls",
            status="completed",
            details={
                "successful": len(results),
                "failed": len(failed_keys),
                "failed_keys": failed_keys,
            },
        )

        return results

    def validate_object_exists(self, object_key: str) -> bool:
        """
        Validate that an object exists in S3 before generating URL.

        Args:
            object_key: S3 object key to validate

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.warning(
                    f"Object not found: {object_key}",
                    extra={"object_key": object_key, "bucket": self.bucket_name},
                )
                return False
            raise

    def generate_secure_download_url(
        self,
        object_key: str,
        expiration_seconds: int = 3600,
        validate_exists: bool = True,
    ) -> Optional[Dict[str, str]]:
        """
        Generate presigned URL with validation and security checks.

        Args:
            object_key: S3 object key
            expiration_seconds: URL expiration time
            validate_exists: Whether to validate object existence first

        Returns:
            Presigned URL info dict or None if validation fails
        """
        log_execution(
            logger,
            operation="generate_secure_download_url",
            status="started",
            details={"object_key": object_key, "validate": validate_exists},
        )

        # Validate object exists if requested
        if validate_exists:
            if not self.validate_object_exists(object_key):
                log_execution(
                    logger,
                    operation="generate_secure_download_url",
                    status="failed",
                    details={"object_key": object_key, "reason": "object_not_found"},
                )
                return None

        # Generate URL with appropriate headers for DICOM files
        return self.generate_download_url(
            object_key=object_key,
            expiration_seconds=expiration_seconds,
            response_content_type="application/dicom",
            response_content_disposition=f'attachment; filename="{object_key.split("/")[-1]}"',
        )
