"""
Unit tests for S3 storage handler.

Tests S3 operations using moto mocking library.
"""

import hashlib
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.storage.s3_handler import S3Handler


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def s3_bucket_name():
    """Test bucket name."""
    return "test-dicom-bucket"


@pytest.fixture
def s3_handler(aws_credentials, s3_bucket_name):
    """Create S3Handler with mocked AWS."""
    with mock_aws():
        # Create bucket
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket=s3_bucket_name)

        # Create handler
        handler = S3Handler(bucket_name=s3_bucket_name, region_name="us-east-1")

        yield handler


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create sample test file."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("Sample DICOM content for testing")
    return test_file


@pytest.fixture
def sample_dicom_file(tmp_path: Path) -> Path:
    """Create sample DICOM-like file."""
    test_file = tmp_path / "test.dcm"
    test_file.write_bytes(b"DICM" + b"\x00" * 100)
    return test_file


class TestS3HandlerInitialization:
    """Tests for S3Handler initialization."""

    def test_initialization_with_defaults(self, aws_credentials, s3_bucket_name):
        """Test handler initialization with default parameters."""
        with mock_aws():
            handler = S3Handler(bucket_name=s3_bucket_name)
            assert handler.bucket_name == s3_bucket_name
            assert handler.region_name == "us-east-1"
            assert handler.s3_client is not None
            assert handler.s3_resource is not None

    def test_initialization_with_custom_region(self, aws_credentials, s3_bucket_name):
        """Test handler initialization with custom region."""
        with mock_aws():
            handler = S3Handler(bucket_name=s3_bucket_name, region_name="us-west-2")
            assert handler.region_name == "us-west-2"

    def test_initialization_with_credentials(self, s3_bucket_name):
        """Test handler initialization with explicit credentials."""
        with mock_aws():
            handler = S3Handler(
                bucket_name=s3_bucket_name,
                aws_access_key_id="test_key",
                aws_secret_access_key="test_secret",
            )
            assert handler.bucket_name == s3_bucket_name


class TestS3HandlerUpload:
    """Tests for file upload operations."""

    def test_upload_file_success(self, s3_handler: S3Handler, sample_file: Path):
        """Test successful file upload."""
        result = s3_handler.upload_file(local_path=sample_file, s3_key="test/sample.txt")

        assert result["bucket"] == s3_handler.bucket_name
        assert result["key"] == "test/sample.txt"
        assert result["size"] == sample_file.stat().st_size
        assert "etag" in result
        assert "checksum" in result
        assert result["content_type"] == "application/dicom"

    def test_upload_file_with_metadata(self, s3_handler: S3Handler, sample_file: Path):
        """Test file upload with custom metadata."""
        metadata = {"patient-id": "P001", "study-uid": "1.2.3.4.5"}

        result = s3_handler.upload_file(
            local_path=sample_file, s3_key="test/with_metadata.txt", metadata=metadata
        )

        assert result["key"] == "test/with_metadata.txt"

        # Verify metadata was stored
        obj_metadata = s3_handler.get_object_metadata("test/with_metadata.txt")
        assert "custom_metadata" in obj_metadata
        assert obj_metadata["custom_metadata"]["patient-id"] == "P001"

    def test_upload_file_with_custom_content_type(self, s3_handler: S3Handler, sample_file: Path):
        """Test file upload with custom content type."""
        result = s3_handler.upload_file(
            local_path=sample_file,
            s3_key="test/custom_type.txt",
            content_type="text/plain",
        )

        assert result["content_type"] == "text/plain"

    def test_upload_file_not_found(self, s3_handler: S3Handler):
        """Test upload with non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            s3_handler.upload_file(local_path="/nonexistent/file.txt", s3_key="test/fail.txt")

        assert "not found" in str(exc_info.value).lower()

    def test_upload_file_with_string_path(self, s3_handler: S3Handler, sample_file: Path):
        """Test upload with string path instead of Path object."""
        result = s3_handler.upload_file(local_path=str(sample_file), s3_key="test/string_path.txt")

        assert result["key"] == "test/string_path.txt"


class TestS3HandlerDownload:
    """Tests for file download operations."""

    def test_download_file_success(self, s3_handler: S3Handler, sample_file: Path, tmp_path: Path):
        """Test successful file download."""
        # Upload first
        s3_handler.upload_file(local_path=sample_file, s3_key="test/download.txt")

        # Download
        download_path = tmp_path / "downloaded.txt"
        result = s3_handler.download_file(s3_key="test/download.txt", local_path=download_path)

        assert result["key"] == "test/download.txt"
        assert result["local_path"] == str(download_path)
        assert download_path.exists()
        assert download_path.read_text() == sample_file.read_text()

    def test_download_file_with_checksum_verification(
        self, s3_handler: S3Handler, sample_file: Path, tmp_path: Path
    ):
        """Test download with checksum verification."""
        # Upload
        upload_result = s3_handler.upload_file(local_path=sample_file, s3_key="test/verify.txt")

        # Download with verification
        download_path = tmp_path / "verified.txt"
        result = s3_handler.download_file(
            s3_key="test/verify.txt", local_path=download_path, verify_checksum=True
        )

        assert "checksum" in result
        assert "checksum_verified" in result
        assert result["checksum_verified"] is True
        assert result["checksum"] == upload_result["checksum"]

    def test_download_file_creates_parent_directories(
        self, s3_handler: S3Handler, sample_file: Path, tmp_path: Path
    ):
        """Test download creates parent directories if they don't exist."""
        # Upload
        s3_handler.upload_file(local_path=sample_file, s3_key="test/nested.txt")

        # Download to nested path
        download_path = tmp_path / "nested" / "dir" / "file.txt"
        s3_handler.download_file(s3_key="test/nested.txt", local_path=download_path)

        assert download_path.exists()
        assert download_path.parent.exists()

    def test_download_file_nonexistent_key(self, s3_handler: S3Handler, tmp_path: Path):
        """Test download with non-existent S3 key."""
        download_path = tmp_path / "fail.txt"

        with pytest.raises(ClientError) as exc_info:
            s3_handler.download_file(s3_key="nonexistent/key.txt", local_path=download_path)

        assert exc_info.value.response["Error"]["Code"] in ["404", "NoSuchKey"]


class TestS3HandlerList:
    """Tests for list operations."""

    def test_list_objects_empty_bucket(self, s3_handler: S3Handler):
        """Test listing objects in empty bucket."""
        objects = s3_handler.list_objects()

        assert isinstance(objects, list)
        assert len(objects) == 0

    def test_list_objects_with_files(self, s3_handler: S3Handler, sample_file: Path):
        """Test listing objects with files present."""
        # Upload multiple files
        s3_handler.upload_file(local_path=sample_file, s3_key="file1.txt")
        s3_handler.upload_file(local_path=sample_file, s3_key="file2.txt")
        s3_handler.upload_file(local_path=sample_file, s3_key="dir/file3.txt")

        objects = s3_handler.list_objects()

        assert len(objects) == 3
        keys = [obj["key"] for obj in objects]
        assert "file1.txt" in keys
        assert "file2.txt" in keys
        assert "dir/file3.txt" in keys

    def test_list_objects_with_prefix(self, s3_handler: S3Handler, sample_file: Path):
        """Test listing objects with prefix filter."""
        # Upload files with different prefixes
        s3_handler.upload_file(local_path=sample_file, s3_key="patient-001/study1.dcm")
        s3_handler.upload_file(local_path=sample_file, s3_key="patient-001/study2.dcm")
        s3_handler.upload_file(local_path=sample_file, s3_key="patient-002/study1.dcm")

        # List with prefix
        objects = s3_handler.list_objects(prefix="patient-001/")

        assert len(objects) == 2
        keys = [obj["key"] for obj in objects]
        assert all(key.startswith("patient-001/") for key in keys)

    def test_list_objects_max_keys(self, s3_handler: S3Handler, sample_file: Path):
        """Test listing objects with max_keys limit."""
        # Upload 5 files
        for i in range(5):
            s3_handler.upload_file(local_path=sample_file, s3_key=f"file{i}.txt")

        # List with max_keys=3
        objects = s3_handler.list_objects(max_keys=3)

        assert len(objects) == 3

    def test_list_objects_metadata_structure(self, s3_handler: S3Handler, sample_file: Path):
        """Test that list_objects returns correct metadata structure."""
        s3_handler.upload_file(local_path=sample_file, s3_key="test.txt")

        objects = s3_handler.list_objects()

        assert len(objects) == 1
        obj = objects[0]
        assert "key" in obj
        assert "size" in obj
        assert "last_modified" in obj
        assert "etag" in obj
        assert isinstance(obj["size"], int)


class TestS3HandlerDelete:
    """Tests for delete operations."""

    def test_delete_object_success(self, s3_handler: S3Handler, sample_file: Path):
        """Test successful object deletion."""
        # Upload first
        s3_handler.upload_file(local_path=sample_file, s3_key="to_delete.txt")

        # Verify exists
        assert s3_handler.object_exists("to_delete.txt") is True

        # Delete
        result = s3_handler.delete_object("to_delete.txt")

        assert result is True
        assert s3_handler.object_exists("to_delete.txt") is False

    def test_delete_nonexistent_object(self, s3_handler: S3Handler):
        """Test deleting non-existent object (should succeed without error)."""
        # S3 delete is idempotent - deleting non-existent object succeeds
        result = s3_handler.delete_object("nonexistent.txt")

        assert result is True


class TestS3HandlerPresignedURL:
    """Tests for presigned URL generation."""

    def test_generate_presigned_url_get(self, s3_handler: S3Handler, sample_file: Path):
        """Test generating presigned URL for GET."""
        # Upload file
        s3_handler.upload_file(local_path=sample_file, s3_key="presigned.txt")

        # Generate URL
        url = s3_handler.generate_presigned_url("presigned.txt", expiration=3600)

        assert isinstance(url, str)
        assert "presigned.txt" in url
        assert s3_handler.bucket_name in url
        assert "X-Amz-Expires=3600" in url or "Expires=" in url

    def test_generate_presigned_url_put(self, s3_handler: S3Handler):
        """Test generating presigned URL for PUT."""
        url = s3_handler.generate_presigned_url("new_file.txt", expiration=1800, http_method="PUT")

        assert isinstance(url, str)
        assert "new_file.txt" in url

    def test_generate_presigned_url_custom_expiration(
        self, s3_handler: S3Handler, sample_file: Path
    ):
        """Test presigned URL with custom expiration."""
        s3_handler.upload_file(local_path=sample_file, s3_key="expiring.txt")

        url = s3_handler.generate_presigned_url("expiring.txt", expiration=7200)

        assert isinstance(url, str)
        assert "expiring.txt" in url


class TestS3HandlerUtilities:
    """Tests for utility methods."""

    def test_object_exists_true(self, s3_handler: S3Handler, sample_file: Path):
        """Test object_exists returns True for existing object."""
        s3_handler.upload_file(local_path=sample_file, s3_key="exists.txt")

        assert s3_handler.object_exists("exists.txt") is True

    def test_object_exists_false(self, s3_handler: S3Handler):
        """Test object_exists returns False for non-existent object."""
        assert s3_handler.object_exists("does_not_exist.txt") is False

    def test_get_object_metadata_success(self, s3_handler: S3Handler, sample_file: Path):
        """Test getting object metadata."""
        s3_handler.upload_file(
            local_path=sample_file,
            s3_key="metadata.txt",
            metadata={"key1": "value1"},
        )

        metadata = s3_handler.get_object_metadata("metadata.txt")

        assert metadata["key"] == "metadata.txt"
        assert "size" in metadata
        assert "last_modified" in metadata
        assert "etag" in metadata
        assert "content_type" in metadata
        assert "custom_metadata" in metadata
        assert metadata["custom_metadata"]["key1"] == "value1"

    def test_get_object_metadata_nonexistent(self, s3_handler: S3Handler):
        """Test getting metadata for non-existent object."""
        with pytest.raises(ClientError) as exc_info:
            s3_handler.get_object_metadata("nonexistent.txt")

        assert exc_info.value.response["Error"]["Code"] in ["404", "NoSuchKey"]

    def test_calculate_file_hash(self, s3_handler: S3Handler, sample_file: Path):
        """Test MD5 hash calculation."""
        calculated_hash = s3_handler._calculate_file_hash(sample_file)

        # Verify against manual calculation
        md5_hash = hashlib.md5()
        with open(sample_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)
        expected_hash = md5_hash.hexdigest()

        assert calculated_hash == expected_hash


class TestS3HandlerErrorHandling:
    """Tests for error handling and edge cases."""

    def test_list_objects_with_client_error(self, s3_handler: S3Handler):
        """Test list_objects handles ClientError gracefully."""
        # Use invalid bucket to trigger error
        invalid_handler = S3Handler(bucket_name="nonexistent-bucket-12345")

        with pytest.raises(ClientError):
            invalid_handler.list_objects()

    def test_delete_object_with_invalid_bucket(self, aws_credentials):
        """Test delete_object with invalid bucket raises error."""
        with mock_aws():
            # Create handler with non-existent bucket
            handler = S3Handler(bucket_name="nonexistent-bucket-xyz")

            # Delete should fail with ClientError
            with pytest.raises(ClientError):
                handler.delete_object("some-file.txt")

    def test_object_exists_with_non_404_error(self, s3_handler: S3Handler, monkeypatch):
        """Test object_exists raises non-404 ClientErrors."""
        from botocore.exceptions import ClientError as BotoClientError

        def mock_head_object(*args, **kwargs):
            # Simulate a non-404 error (e.g., permission denied)
            error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
            raise BotoClientError(error_response, "HeadObject")

        # Monkeypatch the head_object method
        monkeypatch.setattr(s3_handler.s3_client, "head_object", mock_head_object)

        with pytest.raises(ClientError) as exc_info:
            s3_handler.object_exists("test.txt")

        assert exc_info.value.response["Error"]["Code"] == "AccessDenied"

    def test_generate_presigned_url_with_error(self, s3_handler: S3Handler, monkeypatch):
        """Test generate_presigned_url handles ClientError."""
        from botocore.exceptions import ClientError as BotoClientError

        def mock_generate_presigned_url(*args, **kwargs):
            # Simulate an error during presigned URL generation
            error_response = {"Error": {"Code": "InvalidRequest", "Message": "Invalid request"}}
            raise BotoClientError(error_response, "GeneratePresignedUrl")

        # Monkeypatch the generate_presigned_url method
        monkeypatch.setattr(
            s3_handler.s3_client, "generate_presigned_url", mock_generate_presigned_url
        )

        with pytest.raises(ClientError) as exc_info:
            s3_handler.generate_presigned_url("test-file.txt")

        assert exc_info.value.response["Error"]["Code"] == "InvalidRequest"


class TestS3HandlerIntegration:
    """Integration tests combining multiple operations."""

    def test_upload_download_roundtrip(
        self, s3_handler: S3Handler, sample_dicom_file: Path, tmp_path: Path
    ):
        """Test complete upload-download roundtrip preserves content."""
        # Upload
        upload_result = s3_handler.upload_file(local_path=sample_dicom_file, s3_key="roundtrip.dcm")

        # Download
        download_path = tmp_path / "roundtrip_download.dcm"
        download_result = s3_handler.download_file(
            s3_key="roundtrip.dcm", local_path=download_path, verify_checksum=True
        )

        # Verify content matches
        assert download_path.read_bytes() == sample_dicom_file.read_bytes()
        assert download_result["checksum_verified"] is True
        assert upload_result["checksum"] == download_result["checksum"]

    def test_upload_list_delete_workflow(self, s3_handler: S3Handler, sample_file: Path):
        """Test typical workflow of upload, list, and delete."""
        # Upload multiple files
        keys = ["workflow1.txt", "workflow2.txt", "workflow3.txt"]
        for key in keys:
            s3_handler.upload_file(local_path=sample_file, s3_key=key)

        # List and verify all present
        objects = s3_handler.list_objects()
        listed_keys = [obj["key"] for obj in objects]
        assert all(key in listed_keys for key in keys)

        # Delete one
        s3_handler.delete_object("workflow2.txt")

        # List again and verify deletion
        objects = s3_handler.list_objects()
        listed_keys = [obj["key"] for obj in objects]
        assert "workflow1.txt" in listed_keys
        assert "workflow2.txt" not in listed_keys
        assert "workflow3.txt" in listed_keys

    def test_presigned_url_generation_for_existing_file(
        self, s3_handler: S3Handler, sample_file: Path
    ):
        """Test presigned URL workflow for existing file."""
        # Upload
        s3_handler.upload_file(local_path=sample_file, s3_key="presigned_flow.txt")

        # Verify exists
        assert s3_handler.object_exists("presigned_flow.txt") is True

        # Generate presigned URL
        url = s3_handler.generate_presigned_url("presigned_flow.txt")

        assert isinstance(url, str)
        assert len(url) > 0
