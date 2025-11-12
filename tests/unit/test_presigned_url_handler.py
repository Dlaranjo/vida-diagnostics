"""Tests for PresignedUrlHandler."""

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.delivery.presigned_url_handler import PresignedUrlHandler


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def bucket_name():
    """Test bucket name."""
    return "test-dicom-bucket"


@pytest.fixture
def presigned_url_handler(aws_credentials, bucket_name):
    """Create PresignedUrlHandler with mocked AWS."""
    with mock_aws():
        handler = PresignedUrlHandler(bucket_name=bucket_name, region_name="us-east-1")

        # Create the bucket and add test objects
        handler.s3_client.create_bucket(Bucket=bucket_name)
        handler.s3_client.put_object(
            Bucket=bucket_name, Key="test/file.dcm", Body=b"test content"
        )
        handler.s3_client.put_object(
            Bucket=bucket_name, Key="test/file2.dcm", Body=b"test content 2"
        )

        yield handler


class TestPresignedUrlHandlerInitialization:
    """Tests for PresignedUrlHandler initialization."""

    def test_init_with_default_credentials(self, aws_credentials, bucket_name):
        """Test initialization with default credentials."""
        with mock_aws():
            handler = PresignedUrlHandler(
                bucket_name=bucket_name, region_name="us-east-1"
            )

            assert handler.bucket_name == bucket_name
            assert handler.region_name == "us-east-1"
            assert handler.s3_client is not None

    def test_init_with_custom_credentials(self, aws_credentials, bucket_name):
        """Test initialization with custom credentials."""
        with mock_aws():
            handler = PresignedUrlHandler(
                bucket_name=bucket_name,
                region_name="us-west-2",
                aws_access_key_id="custom_key",
                aws_secret_access_key="custom_secret",
            )

            assert handler.bucket_name == bucket_name
            assert handler.region_name == "us-west-2"
            assert handler.s3_client is not None


class TestDownloadUrlGeneration:
    """Tests for download URL generation."""

    def test_generate_download_url_success(self, presigned_url_handler):
        """Test successful download URL generation."""
        result = presigned_url_handler.generate_download_url(
            object_key="test/file.dcm", expiration_seconds=3600
        )

        assert "url" in result
        assert "expires_in" in result
        assert "object_key" in result
        assert "bucket" in result
        assert result["expires_in"] == 3600
        assert result["object_key"] == "test/file.dcm"
        assert result["bucket"] == "test-dicom-bucket"
        assert "test/file.dcm" in result["url"]

    def test_generate_download_url_with_custom_expiration(self, presigned_url_handler):
        """Test download URL generation with custom expiration."""
        result = presigned_url_handler.generate_download_url(
            object_key="test/file.dcm", expiration_seconds=1800
        )

        assert result["expires_in"] == 1800
        assert "url" in result

    def test_generate_download_url_with_response_headers(self, presigned_url_handler):
        """Test download URL generation with custom response headers."""
        result = presigned_url_handler.generate_download_url(
            object_key="test/file.dcm",
            expiration_seconds=3600,
            response_content_type="application/dicom",
            response_content_disposition='attachment; filename="file.dcm"',
        )

        assert "url" in result
        assert "ResponseContentType" in result["url"]
        assert "ResponseContentDisposition" in result["url"]

    def test_generate_download_url_nonexistent_object(self, presigned_url_handler):
        """Test download URL generation for nonexistent object still succeeds."""
        # Presigned URLs are generated without checking object existence by default
        result = presigned_url_handler.generate_download_url(
            object_key="nonexistent/file.dcm", expiration_seconds=3600
        )

        assert "url" in result
        assert result["object_key"] == "nonexistent/file.dcm"


class TestUploadUrlGeneration:
    """Tests for upload URL generation."""

    def test_generate_upload_url_success(self, presigned_url_handler):
        """Test successful upload URL generation."""
        result = presigned_url_handler.generate_upload_url(
            object_key="test/new_file.dcm", expiration_seconds=3600
        )

        assert "url" in result
        assert "expires_in" in result
        assert "object_key" in result
        assert "bucket" in result
        assert result["expires_in"] == 3600
        assert result["object_key"] == "test/new_file.dcm"
        assert result["bucket"] == "test-dicom-bucket"

    def test_generate_upload_url_with_content_type(self, presigned_url_handler):
        """Test upload URL generation with content type."""
        result = presigned_url_handler.generate_upload_url(
            object_key="test/new_file.dcm",
            expiration_seconds=3600,
            content_type="application/dicom",
        )

        assert "url" in result
        # URL should contain content type parameter
        assert "ContentType" in result["url"] or "content-type" in result["url"].lower()

    def test_generate_upload_url_with_metadata(self, presigned_url_handler):
        """Test upload URL generation with metadata."""
        metadata = {"patient-id": "anonymous", "study-date": "2024-01-01"}

        result = presigned_url_handler.generate_upload_url(
            object_key="test/new_file.dcm",
            expiration_seconds=3600,
            metadata=metadata,
        )

        assert "url" in result
        assert result["object_key"] == "test/new_file.dcm"


class TestBatchUrlGeneration:
    """Tests for batch URL generation."""

    def test_generate_batch_download_urls_success(self, presigned_url_handler):
        """Test successful batch URL generation."""
        object_keys = ["test/file.dcm", "test/file2.dcm"]

        results = presigned_url_handler.generate_batch_download_urls(
            object_keys=object_keys, expiration_seconds=3600
        )

        assert len(results) == 2
        assert "test/file.dcm" in results
        assert "test/file2.dcm" in results

        for key in object_keys:
            assert "url" in results[key]
            assert results[key]["object_key"] == key
            assert results[key]["expires_in"] == 3600

    def test_generate_batch_download_urls_empty_list(self, presigned_url_handler):
        """Test batch URL generation with empty list."""
        results = presigned_url_handler.generate_batch_download_urls(
            object_keys=[], expiration_seconds=3600
        )

        assert len(results) == 0

    def test_generate_batch_download_urls_with_failures(
        self, presigned_url_handler, monkeypatch
    ):
        """Test batch URL generation with some failures."""
        object_keys = ["test/file.dcm", "test/file2.dcm", "test/file3.dcm"]

        # Mock generate_download_url to fail for one key
        original_generate = presigned_url_handler.generate_download_url
        call_count = [0]

        def mock_generate(object_key, expiration_seconds):
            call_count[0] += 1
            if object_key == "test/file2.dcm":
                raise ClientError(
                    {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                    "generate_presigned_url",
                )
            return original_generate(object_key, expiration_seconds)

        monkeypatch.setattr(
            presigned_url_handler, "generate_download_url", mock_generate
        )

        results = presigned_url_handler.generate_batch_download_urls(
            object_keys=object_keys, expiration_seconds=3600
        )

        # Should have results for 2 out of 3 keys
        assert len(results) == 2
        assert "test/file.dcm" in results
        assert "test/file3.dcm" in results
        assert "test/file2.dcm" not in results


class TestObjectValidation:
    """Tests for object existence validation."""

    def test_validate_object_exists_true(self, presigned_url_handler):
        """Test validation for existing object."""
        exists = presigned_url_handler.validate_object_exists("test/file.dcm")
        assert exists is True

    def test_validate_object_exists_false(self, presigned_url_handler):
        """Test validation for nonexistent object."""
        exists = presigned_url_handler.validate_object_exists("nonexistent/file.dcm")
        assert exists is False

    def test_validate_object_exists_handles_errors(
        self, presigned_url_handler, monkeypatch
    ):
        """Test validation handles non-404 errors."""

        def mock_head_object(*args, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "head_object",
            )

        monkeypatch.setattr(presigned_url_handler.s3_client, "head_object", mock_head_object)

        with pytest.raises(ClientError):
            presigned_url_handler.validate_object_exists("test/file.dcm")


class TestSecureDownloadUrl:
    """Tests for secure download URL generation."""

    def test_generate_secure_download_url_success(self, presigned_url_handler):
        """Test secure download URL generation for existing object."""
        result = presigned_url_handler.generate_secure_download_url(
            object_key="test/file.dcm", expiration_seconds=3600, validate_exists=True
        )

        assert result is not None
        assert "url" in result
        assert "application/dicom" in result["url"]
        assert "attachment" in result["url"]

    def test_generate_secure_download_url_nonexistent(self, presigned_url_handler):
        """Test secure download URL for nonexistent object returns None."""
        result = presigned_url_handler.generate_secure_download_url(
            object_key="nonexistent/file.dcm",
            expiration_seconds=3600,
            validate_exists=True,
        )

        assert result is None

    def test_generate_secure_download_url_skip_validation(self, presigned_url_handler):
        """Test secure download URL without validation."""
        result = presigned_url_handler.generate_secure_download_url(
            object_key="nonexistent/file.dcm",
            expiration_seconds=3600,
            validate_exists=False,
        )

        assert result is not None
        assert "url" in result

    def test_generate_secure_download_url_with_dicom_headers(
        self, presigned_url_handler
    ):
        """Test secure download URL includes DICOM-specific headers."""
        result = presigned_url_handler.generate_secure_download_url(
            object_key="test/file.dcm", expiration_seconds=1800, validate_exists=False
        )

        assert result is not None
        url = result["url"]

        # Check for DICOM content type
        assert "application%2Fdicom" in url or "application/dicom" in url

        # Check for attachment disposition
        assert "attachment" in url


class TestIntegration:
    """Integration tests for PresignedUrlHandler."""

    def test_full_download_workflow(self, presigned_url_handler):
        """Test complete download workflow."""
        # Validate object exists
        exists = presigned_url_handler.validate_object_exists("test/file.dcm")
        assert exists is True

        # Generate download URL
        result = presigned_url_handler.generate_download_url(
            object_key="test/file.dcm", expiration_seconds=3600
        )

        assert "url" in result
        assert result["object_key"] == "test/file.dcm"

    def test_full_secure_workflow(self, presigned_url_handler):
        """Test complete secure download workflow."""
        # Generate secure URL (includes validation)
        result = presigned_url_handler.generate_secure_download_url(
            object_key="test/file.dcm", expiration_seconds=3600, validate_exists=True
        )

        assert result is not None
        assert "url" in result
        assert result["object_key"] == "test/file.dcm"

    def test_batch_workflow_with_mixed_results(self, presigned_url_handler):
        """Test batch workflow with existing and nonexistent objects."""
        # Generate batch URLs (doesn't validate by default)
        object_keys = ["test/file.dcm", "test/file2.dcm", "nonexistent/file.dcm"]

        results = presigned_url_handler.generate_batch_download_urls(
            object_keys=object_keys, expiration_seconds=3600
        )

        # All URLs should be generated (presigned URLs don't check existence)
        assert len(results) == 3
        for key in object_keys:
            assert key in results
