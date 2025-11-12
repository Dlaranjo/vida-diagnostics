"""
S3 storage handler for DICOM files.

Provides high-level interface for S3 operations including upload, download,
listing, and presigned URL generation.
"""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class S3Handler:
    """
    Handler for AWS S3 storage operations.

    Provides methods for uploading, downloading, listing, and managing
    DICOM files in S3 buckets with support for presigned URLs.
    """

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        """
        Initialize S3 handler.

        Args:
            bucket_name: S3 bucket name
            region_name: AWS region (default: us-east-1)
            aws_access_key_id: AWS access key (optional, uses default credentials if None)
            aws_secret_access_key: AWS secret key (optional, uses default credentials if None)
        """
        self.bucket_name = bucket_name
        self.region_name = region_name

        # Initialize S3 client
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.s3_client = boto3.client("s3", **session_kwargs)
        self.s3_resource = boto3.resource("s3", **session_kwargs)

    def upload_file(
        self,
        local_path: Union[str, Path],
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: str = "application/dicom",
    ) -> Dict[str, Any]:
        """
        Upload file to S3.

        Args:
            local_path: Path to local file
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach
            content_type: MIME type (default: application/dicom)

        Returns:
            Dictionary with upload results including ETag and size

        Raises:
            FileNotFoundError: If local file doesn't exist
            NoCredentialsError: If AWS credentials not found
            ClientError: If S3 upload fails
        """
        log_execution(
            logger,
            operation="upload_file",
            status="started",
            details={"s3_key": s3_key, "local_path": str(local_path)},
        )

        try:
            local_path = Path(local_path)
            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")

            # Calculate file checksum
            file_hash = self._calculate_file_hash(local_path)
            file_size = local_path.stat().st_size

            # Prepare extra args
            extra_args = {"ContentType": content_type}
            if metadata:
                extra_args["Metadata"] = metadata

            # Upload file
            self.s3_client.upload_file(
                str(local_path), self.bucket_name, s3_key, ExtraArgs=extra_args
            )

            # Get object metadata
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)

            result = {
                "bucket": self.bucket_name,
                "key": s3_key,
                "size": file_size,
                "etag": response["ETag"].strip('"'),
                "checksum": file_hash,
                "content_type": content_type,
            }

            log_execution(
                logger,
                operation="upload_file",
                status="completed",
                details={
                    "s3_key": s3_key,
                    "size": file_size,
                    "etag": result["etag"],
                },
            )

            return result

        except (FileNotFoundError, NoCredentialsError, ClientError) as e:
            log_execution(
                logger,
                operation="upload_file",
                status="failed",
                details={"s3_key": s3_key},
                error=e,
            )
            raise

    def download_file(
        self, s3_key: str, local_path: Union[str, Path], verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """
        Download file from S3.

        Args:
            s3_key: S3 object key
            local_path: Path to save file locally
            verify_checksum: Whether to verify ETag after download

        Returns:
            Dictionary with download results

        Raises:
            ClientError: If S3 download fails
        """
        log_execution(
            logger,
            operation="download_file",
            status="started",
            details={"s3_key": s3_key, "local_path": str(local_path)},
        )

        try:
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))

            # Get object metadata
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            s3_etag = response["ETag"].strip('"')

            result = {
                "bucket": self.bucket_name,
                "key": s3_key,
                "local_path": str(local_path),
                "size": local_path.stat().st_size,
                "etag": s3_etag,
            }

            # Verify checksum if requested
            if verify_checksum:
                local_hash = self._calculate_file_hash(local_path)
                result["checksum"] = local_hash
                result["checksum_verified"] = local_hash == s3_etag

            log_execution(
                logger,
                operation="download_file",
                status="completed",
                details={"s3_key": s3_key, "size": result["size"]},
            )

            return result

        except ClientError as e:
            log_execution(
                logger,
                operation="download_file",
                status="failed",
                details={"s3_key": s3_key},
                error=e,
            )
            raise

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        List objects in S3 bucket with optional prefix filter.

        Args:
            prefix: Key prefix to filter (e.g., "patient-123/")
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata dictionaries

        Raises:
            ClientError: If S3 list operation fails
        """
        log_execution(
            logger,
            operation="list_objects",
            status="started",
            details={"prefix": prefix, "max_keys": max_keys},
        )

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix, MaxKeys=max_keys
            )

            objects = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    objects.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "etag": obj["ETag"].strip('"'),
                        }
                    )

            log_execution(
                logger,
                operation="list_objects",
                status="completed",
                details={"prefix": prefix, "count": len(objects)},
            )

            return objects

        except ClientError as e:
            log_execution(
                logger,
                operation="list_objects",
                status="failed",
                details={"prefix": prefix},
                error=e,
            )
            raise

    def delete_object(self, s3_key: str) -> bool:
        """
        Delete object from S3.

        Args:
            s3_key: S3 object key to delete

        Returns:
            True if successful

        Raises:
            ClientError: If S3 delete operation fails
        """
        log_execution(
            logger,
            operation="delete_object",
            status="started",
            details={"s3_key": s3_key},
        )

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

            log_execution(
                logger,
                operation="delete_object",
                status="completed",
                details={"s3_key": s3_key},
            )

            return True

        except ClientError as e:
            log_execution(
                logger,
                operation="delete_object",
                status="failed",
                details={"s3_key": s3_key},
                error=e,
            )
            raise

    def generate_presigned_url(
        self, s3_key: str, expiration: int = 3600, http_method: str = "GET"
    ) -> str:
        """
        Generate presigned URL for temporary access to S3 object.

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            http_method: HTTP method (GET or PUT)

        Returns:
            Presigned URL string

        Raises:
            ClientError: If presigned URL generation fails
        """
        log_execution(
            logger,
            operation="generate_presigned_url",
            status="started",
            details={"s3_key": s3_key, "expiration": expiration},
        )

        try:
            client_method = "get_object" if http_method.upper() == "GET" else "put_object"

            url = self.s3_client.generate_presigned_url(
                client_method,
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )

            log_execution(
                logger,
                operation="generate_presigned_url",
                status="completed",
                details={"s3_key": s3_key, "expiration": expiration},
            )

            return url

        except ClientError as e:
            log_execution(
                logger,
                operation="generate_presigned_url",
                status="failed",
                details={"s3_key": s3_key},
                error=e,
            )
            raise

    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_object_metadata(self, s3_key: str) -> Dict[str, Any]:
        """
        Get metadata for S3 object.

        Args:
            s3_key: S3 object key

        Returns:
            Dictionary with object metadata

        Raises:
            ClientError: If object doesn't exist or operation fails
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)

            metadata = {
                "key": s3_key,
                "size": response["ContentLength"],
                "last_modified": response["LastModified"].isoformat(),
                "etag": response["ETag"].strip('"'),
                "content_type": response.get("ContentType", "unknown"),
            }

            if "Metadata" in response:
                metadata["custom_metadata"] = response["Metadata"]

            return metadata

        except ClientError as e:
            log_execution(
                logger,
                operation="get_object_metadata",
                status="failed",
                details={"s3_key": s3_key},
                error=e,
            )
            raise

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of file.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash as hex string
        """
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
