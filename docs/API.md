# API Documentation

## Overview

This document describes the Python APIs and handler interfaces for the Medical Imaging Pipeline.

## Table of Contents

1. [Storage Handlers](#storage-handlers)
2. [Monitoring Handlers](#monitoring-handlers)
3. [Orchestration Handlers](#orchestration-handlers)
4. [Delivery Handlers](#delivery-handlers)
5. [Ingestion Modules](#ingestion-modules)
6. [Validation Schemas](#validation-schemas)

---

## Storage Handlers

### S3Handler

Location: `src/storage/s3_handler.py`

Handles all S3 operations including upload, download, and file management.

#### Class: `S3Handler`

```python
class S3Handler:
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None
```

**Parameters**:
- `bucket_name` (str): S3 bucket name
- `region_name` (str): AWS region (default: "us-east-1")
- `aws_access_key_id` (Optional[str]): AWS access key
- `aws_secret_access_key` (Optional[str]): AWS secret key

#### Methods

##### upload_file()

```python
def upload_file(
    self,
    file_path: str,
    object_key: str,
    metadata: Optional[Dict[str, str]] = None,
    content_type: str = "application/dicom",
) -> Dict[str, str]
```

Upload file to S3 bucket.

**Parameters**:
- `file_path` (str): Local file path
- `object_key` (str): S3 object key
- `metadata` (Optional[Dict]): Metadata tags
- `content_type` (str): MIME type

**Returns**: `Dict[str, str]` - Upload result with bucket, key, etag

**Example**:
```python
handler = S3Handler(bucket_name="my-bucket")
result = handler.upload_file(
    file_path="/path/to/file.dcm",
    object_key="patient123/study456/image.dcm",
    metadata={"patient_id": "anon123"},
    content_type="application/dicom"
)
print(result)
# {'bucket': 'my-bucket', 'key': '...', 'etag': '...'}
```

##### download_file()

```python
def download_file(
    self,
    object_key: str,
    file_path: str,
) -> Dict[str, str]
```

Download file from S3 bucket.

**Parameters**:
- `object_key` (str): S3 object key
- `file_path` (str): Local destination path

**Returns**: `Dict[str, str]` - Download result

**Example**:
```python
result = handler.download_file(
    object_key="patient123/study456/image.dcm",
    file_path="/tmp/downloaded.dcm"
)
```

##### list_objects()

```python
def list_objects(
    self,
    prefix: str = "",
    max_keys: int = 1000,
) -> List[Dict[str, Any]]
```

List objects in bucket with optional prefix.

**Parameters**:
- `prefix` (str): Key prefix filter
- `max_keys` (int): Maximum results

**Returns**: `List[Dict]` - List of object metadata

**Example**:
```python
objects = handler.list_objects(prefix="patient123/")
for obj in objects:
    print(f"Key: {obj['Key']}, Size: {obj['Size']}")
```

##### delete_object()

```python
def delete_object(self, object_key: str) -> bool
```

Delete object from bucket.

**Parameters**:
- `object_key` (str): S3 object key

**Returns**: `bool` - Success status

##### get_object_metadata()

```python
def get_object_metadata(
    self,
    object_key: str,
) -> Dict[str, Any]
```

Get object metadata without downloading.

**Returns**: `Dict` with ContentLength, ContentType, Metadata, etc.

---

## Monitoring Handlers

### CloudWatchHandler

Location: `src/monitoring/cloudwatch_handler.py`

Handles CloudWatch logging and metrics.

#### Class: `CloudWatchHandler`

```python
class CloudWatchHandler:
    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None
```

#### Methods

##### put_metric_data()

```python
def put_metric_data(
    self,
    namespace: str,
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: Optional[List[Dict[str, str]]] = None,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]
```

Publish custom metric to CloudWatch.

**Parameters**:
- `namespace` (str): Metric namespace
- `metric_name` (str): Metric name
- `value` (float): Metric value
- `unit` (str): Unit (Count, Seconds, etc.)
- `dimensions` (Optional[List[Dict]]): Metric dimensions
- `timestamp` (Optional[datetime]): Timestamp

**Example**:
```python
handler = CloudWatchHandler()
handler.put_metric_data(
    namespace="MedicalImaging/Pipeline",
    metric_name="FilesProcessed",
    value=1,
    unit="Count",
    dimensions=[
        {"Name": "Environment", "Value": "Production"}
    ]
)
```

##### create_log_group()

```python
def create_log_group(
    self,
    log_group_name: str,
    retention_days: int = 7,
) -> Dict[str, str]
```

Create CloudWatch log group.

##### create_log_stream()

```python
def create_log_stream(
    self,
    log_group_name: str,
    log_stream_name: str,
) -> Dict[str, str]
```

Create log stream in log group.

##### put_log_events()

```python
def put_log_events(
    self,
    log_group_name: str,
    log_stream_name: str,
    log_events: List[Dict[str, Any]],
) -> Dict[str, Any]
```

Write log events to stream.

**Example**:
```python
events = [
    {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "message": json.dumps({"level": "INFO", "msg": "Processing started"})
    }
]
handler.put_log_events(
    log_group_name="/aws/lambda/my-function",
    log_stream_name="2024/01/01/stream",
    log_events=events
)
```

---

## Orchestration Handlers

### Step Functions Handler

Location: `src/orchestration/step_functions.py`

Manages Step Functions state machines and executions.

#### Class: `StepFunctionsHandler`

```python
class StepFunctionsHandler:
    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None
```

#### Methods

##### create_state_machine()

```python
def create_state_machine(
    self,
    name: str,
    definition: Dict[str, Any],
    role_arn: str,
    logging_config: Optional[Dict[str, Any]] = None,
    tags: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]
```

Create Step Functions state machine.

**Example**:
```python
handler = StepFunctionsHandler()
result = handler.create_state_machine(
    name="my-workflow",
    definition={"Comment": "...", "StartAt": "...", "States": {...}},
    role_arn="arn:aws:iam::123456789012:role/StepFunctionsRole"
)
print(result["state_machine_arn"])
```

##### start_execution()

```python
def start_execution(
    self,
    state_machine_arn: str,
    execution_input: Dict[str, Any],
    execution_name: Optional[str] = None,
) -> Dict[str, Any]
```

Start state machine execution.

**Example**:
```python
result = handler.start_execution(
    state_machine_arn="arn:aws:states:...",
    execution_input={
        "Records": [{"s3": {"bucket": {"name": "..."}, "object": {"key": "..."}}}]
    }
)
execution_arn = result["execution_arn"]
```

##### describe_execution()

```python
def describe_execution(self, execution_arn: str) -> Dict[str, Any]
```

Get execution details and status.

**Returns**: Dict with status, input, output, error, cause

**Example**:
```python
details = handler.describe_execution(execution_arn="arn:aws:states:...")
print(f"Status: {details['status']}")
if details['status'] == 'FAILED':
    print(f"Error: {details['error']}")
    print(f"Cause: {details['cause']}")
```

##### list_executions()

```python
def list_executions(
    self,
    state_machine_arn: str,
    status_filter: Optional[str] = None,
    max_results: int = 100,
) -> List[Dict[str, Any]]
```

List executions for state machine.

**Parameters**:
- `status_filter` (Optional[str]): RUNNING, SUCCEEDED, FAILED, etc.

##### load_state_machine_definition()

```python
@staticmethod
def load_state_machine_definition(file_path: str) -> Dict[str, Any]
```

Load state machine definition from JSON file.

##### substitute_variables()

```python
def substitute_variables(
    self,
    definition: Dict[str, Any],
    variables: Dict[str, str]
) -> Dict[str, Any]
```

Substitute ${VarName} placeholders in definition.

**Example**:
```python
definition = handler.load_state_machine_definition("workflow.json")
substituted = handler.substitute_variables(
    definition,
    {
        "LambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:my-func",
        "S3Bucket": "my-bucket"
    }
)
```

### Lambda Handlers

Location: `src/orchestration/lambda_handlers.py`

#### Decorator: `lambda_handler_wrapper`

```python
def lambda_handler_wrapper(handler_class):
    """Decorator for standardized Lambda handler error handling."""
```

Provides:
- Automatic error catching
- Structured error responses
- CloudWatch logging
- Consistent return format

**Usage**:
```python
@lambda_handler_wrapper
class MyHandler:
    def handle(self, event, context):
        # Your logic here
        return {"statusCode": 200, "body": {...}}
```

#### Class: `IngestionHandler`

```python
class IngestionHandler:
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]
```

Handles DICOM file ingestion from S3 events.

**Event Format**:
```json
{
  "Records": [
    {
      "s3": {
        "bucket": {"name": "my-bucket"},
        "object": {"key": "path/to/file.dcm"}
      }
    }
  ]
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "bucket": "my-bucket",
    "key": "path/to/file.dcm",
    "metadata": {...}
  }
}
```

#### Class: `ValidationHandler`

```python
class ValidationHandler:
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]
```

Validates DICOM metadata against Pydantic schemas.

**Input**:
```json
{
  "metadata": {
    "patient": {...},
    "study": {...},
    "series": {...}
  }
}
```

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "valid": true,
    "metadata": {...}
  }
}
```

#### Class: `DeidentificationHandler`

```python
class DeidentificationHandler:
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]
```

De-identifies DICOM files by removing PHI.

**Input**: S3 event with file location

**Response**:
```json
{
  "statusCode": 200,
  "body": {
    "input_key": "raw/file.dcm",
    "output_key": "processed/file.dcm",
    "removed_tags": [...]
  }
}
```

---

## Delivery Handlers

### PresignedUrlHandler

Location: `src/delivery/presigned_url_handler.py`

Generates secure, time-limited URLs for file downloads.

#### Class: `PresignedUrlHandler`

```python
class PresignedUrlHandler:
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None
```

#### Methods

##### generate_download_url()

```python
def generate_download_url(
    self,
    object_key: str,
    expiration_seconds: int = 3600,
    response_content_type: Optional[str] = None,
    response_content_disposition: Optional[str] = None,
) -> Dict[str, str]
```

Generate presigned URL for downloading file.

**Example**:
```python
handler = PresignedUrlHandler(bucket_name="processed-bucket")
url_info = handler.generate_download_url(
    object_key="patient/study/image.dcm",
    expiration_seconds=3600,
    response_content_type="application/dicom",
    response_content_disposition='attachment; filename="image.dcm"'
)
print(url_info["url"])  # https://...
print(url_info["expires_in"])  # 3600
```

##### generate_upload_url()

```python
def generate_upload_url(
    self,
    object_key: str,
    expiration_seconds: int = 3600,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, str]
```

Generate presigned URL for uploading file.

##### generate_batch_download_urls()

```python
def generate_batch_download_urls(
    self,
    object_keys: list[str],
    expiration_seconds: int = 3600,
) -> Dict[str, Dict[str, str]]
```

Generate multiple presigned URLs at once.

**Example**:
```python
keys = ["file1.dcm", "file2.dcm", "file3.dcm"]
results = handler.generate_batch_download_urls(keys, expiration_seconds=1800)
for key, url_info in results.items():
    print(f"{key}: {url_info['url']}")
```

##### validate_object_exists()

```python
def validate_object_exists(self, object_key: str) -> bool
```

Check if object exists before generating URL.

##### generate_secure_download_url()

```python
def generate_secure_download_url(
    self,
    object_key: str,
    expiration_seconds: int = 3600,
    validate_exists: bool = True,
) -> Optional[Dict[str, str]]
```

Generate URL with validation and DICOM headers.

**Example**:
```python
url_info = handler.generate_secure_download_url(
    object_key="patient/study/image.dcm",
    expiration_seconds=3600,
    validate_exists=True
)

if url_info:
    print(f"Download: {url_info['url']}")
else:
    print("File not found")
```

---

## Ingestion Modules

### DICOMParser

Location: `src/ingestion/dicom_parser.py`

Parses DICOM files using pydicom.

#### Class: `DICOMParser`

```python
class DICOMParser:
    def __init__(self) -> None
```

#### Methods

##### parse_file()

```python
def parse_file(self, file_path: str) -> pydicom.Dataset
```

Parse DICOM file from path.

**Example**:
```python
parser = DICOMParser()
dataset = parser.parse_file("/path/to/file.dcm")
print(dataset.PatientName)
print(dataset.StudyInstanceUID)
```

##### parse_bytes()

```python
def parse_bytes(self, dicom_bytes: bytes) -> pydicom.Dataset
```

Parse DICOM from bytes (e.g., from S3).

##### get_transfer_syntax()

```python
def get_transfer_syntax(self, dataset: pydicom.Dataset) -> str
```

Get DICOM transfer syntax UID.

### Deidentifier

Location: `src/ingestion/deidentifier.py`

Removes PHI from DICOM files.

#### Class: `Deidentifier`

```python
class Deidentifier:
    def __init__(self, preserve_tags: Optional[List[str]] = None) -> None
```

**Parameters**:
- `preserve_tags` (Optional[List[str]]): Tags to preserve (default: diagnostic tags)

#### Methods

##### deidentify_dataset()

```python
def deidentify_dataset(
    self,
    dataset: pydicom.Dataset,
    patient_id: Optional[str] = None,
) -> Tuple[pydicom.Dataset, List[str]]
```

Remove PHI from dataset.

**Returns**: (deidentified_dataset, removed_tags)

**Example**:
```python
deidentifier = Deidentifier()
clean_dataset, removed = deidentifier.deidentify_dataset(
    dataset,
    patient_id="ANON12345"
)
print(f"Removed {len(removed)} tags")
print(f"New Patient ID: {clean_dataset.PatientID}")
```

##### deidentify_file()

```python
def deidentify_file(
    self,
    input_path: str,
    output_path: str,
    patient_id: Optional[str] = None,
) -> List[str]
```

Deidentify DICOM file and save.

### MetadataExtractor

Location: `src/ingestion/metadata_extractor.py`

Extracts structured metadata from DICOM files.

#### Class: `MetadataExtractor`

```python
class MetadataExtractor:
    def __init__(self) -> None
```

#### Methods

##### extract_metadata()

```python
def extract_metadata(self, dataset: pydicom.Dataset) -> Dict[str, Any]
```

Extract comprehensive metadata.

**Returns**:
```python
{
    "patient": {...},
    "study": {...},
    "series": {...},
    "image": {...},
    "acquisition": {...}
}
```

**Example**:
```python
extractor = MetadataExtractor()
metadata = extractor.extract_metadata(dataset)
print(f"Patient: {metadata['patient']['patient_name']}")
print(f"Study Date: {metadata['study']['study_date']}")
print(f"Modality: {metadata['series']['modality']}")
```

---

## Validation Schemas

### Pydantic Models

Location: `src/validation/schemas.py`

#### PatientModel

```python
class PatientModel(BaseModel):
    patient_id: str = Field(..., description="Patient identifier")
    patient_name: Optional[str] = Field(None, description="Patient name")
    patient_birth_date: Optional[str] = Field(None, description="YYYYMMDD")
    patient_sex: Optional[str] = Field(None, description="M, F, O")
    patient_age: Optional[str] = Field(None, description="Age string")
```

#### StudyModel

```python
class StudyModel(BaseModel):
    study_instance_uid: str = Field(..., description="Study UID")
    study_date: Optional[str] = Field(None, description="YYYYMMDD")
    study_time: Optional[str] = Field(None, description="HHMMSS")
    study_description: Optional[str] = None
    accession_number: Optional[str] = None
```

#### SeriesModel

```python
class SeriesModel(BaseModel):
    series_instance_uid: str = Field(..., description="Series UID")
    series_number: Optional[int] = None
    modality: Optional[str] = Field(None, description="CT, MR, etc.")
    series_description: Optional[str] = None
    body_part_examined: Optional[str] = None
```

#### ImageModel

```python
class ImageModel(BaseModel):
    sop_instance_uid: str = Field(..., description="Image UID")
    instance_number: Optional[int] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    bits_allocated: Optional[int] = None
    pixel_spacing: Optional[List[float]] = None
```

#### DICOMMetadataModel

```python
class DICOMMetadataModel(BaseModel):
    patient: PatientModel
    study: StudyModel
    series: SeriesModel
    image: ImageModel
    acquisition: Optional[AcquisitionModel] = None
```

**Usage**:
```python
from src.validation.schemas import DICOMMetadataModel

# Validate metadata
try:
    validated = DICOMMetadataModel(**metadata_dict)
    print("Valid metadata!")
except ValidationError as e:
    print(f"Validation errors: {e}")
```

---

## Error Handling

All handlers follow consistent error handling patterns:

```python
{
    "statusCode": 500,
    "error": "ErrorType",
    "message": "Human-readable error message",
    "details": {...}  # Optional additional context
}
```

### Common Error Codes

- `200`: Success
- `400`: Bad request / invalid input
- `404`: Resource not found
- `500`: Internal server error
- `503`: Service unavailable

---

## Logging Format

All handlers use structured JSON logging:

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "logger": "src.storage.s3_handler",
  "module": "s3_handler",
  "function": "upload_file",
  "line": 123,
  "message": "File uploaded successfully",
  "operation": "upload_file",
  "status": "completed",
  "details": {...}
}
```

Access via CloudWatch Logs Insights:
```
fields @timestamp, level, operation, status, details
| filter level = "ERROR"
| sort @timestamp desc
```

---

## Testing

All handlers have comprehensive test coverage. See `tests/unit/` for examples.

**Example test**:
```python
import pytest
from moto import mock_aws
from src.storage.s3_handler import S3Handler

@mock_aws
def test_upload_file():
    handler = S3Handler(bucket_name="test-bucket")
    handler.s3_client.create_bucket(Bucket="test-bucket")

    result = handler.upload_file(
        file_path="/tmp/test.dcm",
        object_key="test.dcm"
    )

    assert result["bucket"] == "test-bucket"
    assert result["key"] == "test.dcm"
```
