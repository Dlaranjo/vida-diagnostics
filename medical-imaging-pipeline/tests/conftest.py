"""
Pytest configuration and shared fixtures for medical imaging pipeline tests.
"""

import os
from pathlib import Path
from typing import Generator

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_dicom_dir(test_data_dir: Path) -> Path:
    """Return path to sample DICOM files directory."""
    dicom_dir = test_data_dir / "sample_dicom"
    dicom_dir.mkdir(parents=True, exist_ok=True)
    return dicom_dir


@pytest.fixture(scope="session")
def sample_csv_dir(test_data_dir: Path) -> Path:
    """Return path to sample CSV files directory."""
    csv_dir = test_data_dir / "sample_csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    return csv_dir


@pytest.fixture(scope="session")
def sample_json_dir(test_data_dir: Path) -> Path:
    """Return path to sample JSON files directory."""
    json_dir = test_data_dir / "sample_json"
    json_dir.mkdir(parents=True, exist_ok=True)
    return json_dir


@pytest.fixture
def aws_credentials() -> None:
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_client(aws_credentials: None) -> Generator:
    """Create mock S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def s3_bucket(s3_client) -> str:
    """Create a mock S3 bucket for testing."""
    bucket_name = "test-medical-imaging-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    return bucket_name


@pytest.fixture
def lambda_client(aws_credentials: None) -> Generator:
    """Create mock Lambda client."""
    with mock_aws():
        yield boto3.client("lambda", region_name="us-east-1")


@pytest.fixture
def stepfunctions_client(aws_credentials: None) -> Generator:
    """Create mock Step Functions client."""
    with mock_aws():
        yield boto3.client("stepfunctions", region_name="us-east-1")


@pytest.fixture
def cloudwatch_client(aws_credentials: None) -> Generator:
    """Create mock CloudWatch client."""
    with mock_aws():
        yield boto3.client("cloudwatch", region_name="us-east-1")
