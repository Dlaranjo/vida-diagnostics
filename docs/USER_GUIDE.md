# User Guide

## Overview

This guide provides end-to-end instructions for using the Medical Imaging Pipeline to process DICOM files, from upload through de-identification to secure download.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Uploading DICOM Files](#uploading-dicom-files)
3. [Monitoring Processing](#monitoring-processing)
4. [Downloading Processed Files](#downloading-processed-files)
5. [Understanding Results](#understanding-results)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Getting Started

### Prerequisites

Before using the pipeline, ensure:

1. **AWS Account Access**: You have valid AWS credentials
2. **Pipeline Deployed**: Infrastructure is deployed to AWS
3. **Bucket Names**: You know the S3 bucket names (from Terraform outputs)
4. **AWS CLI**: Installed and configured (for command-line access)

### Getting Bucket Names

From Terraform outputs:

```bash
cd terraform
terraform output raw_bucket_name
terraform output processed_bucket_name
```

Example output:
```
raw_bucket_name = "medical-imaging-pipeline-dev-raw-dicom"
processed_bucket_name = "medical-imaging-pipeline-dev-processed-dicom"
```

---

## Uploading DICOM Files

### Method 1: AWS CLI (Recommended)

```bash
# Set your bucket name
RAW_BUCKET="medical-imaging-pipeline-dev-raw-dicom"

# Upload single file
aws s3 cp /path/to/file.dcm s3://$RAW_BUCKET/patient123/study456/

# Upload entire directory
aws s3 cp /path/to/dicom/directory/ s3://$RAW_BUCKET/patient123/study456/ --recursive

# Upload with specific naming
aws s3 cp /path/to/file.dcm s3://$RAW_BUCKET/patient123/study456/image001.dcm
```

**Best Practices**:
- Organize files by patient/study/series hierarchy
- Use meaningful naming conventions
- Only upload `.dcm` files (other files are ignored)

### Method 2: AWS Console

1. Go to S3 Console: https://s3.console.aws.amazon.com/
2. Find your raw bucket: `medical-imaging-pipeline-dev-raw-dicom`
3. Click "Upload"
4. Drag and drop DICOM files or click "Add files"
5. Click "Upload"

**Note**: Processing starts automatically when upload completes.

### Method 3: Programmatic Upload (Python)

```python
import boto3

# Initialize S3 client
s3_client = boto3.client('s3', region_name='us-east-1')

# Upload file
with open('/path/to/file.dcm', 'rb') as f:
    s3_client.upload_fileobj(
        f,
        'medical-imaging-pipeline-dev-raw-dicom',
        'patient123/study456/image001.dcm',
        ExtraArgs={
            'ContentType': 'application/dicom',
            'Metadata': {
                'study-id': 'study456',
                'patient-id': 'patient123'
            }
        }
    )

print("Upload complete!")
```

### Supported File Types

- ✅ DICOM files (`.dcm`, `.DCM`, `.dicom`)
- ✅ Standard DICOM transfer syntaxes
- ✅ Compressed DICOM (JPEG, JPEG 2000, RLE)
- ❌ Non-DICOM files (ignored)
- ❌ Corrupted/invalid DICOM files (processing will fail)

### File Size Limits

- **Maximum file size**: 250 MB (AWS Lambda limit)
- **Recommended**: Under 100 MB for optimal performance
- **Large files**: Consider splitting or using alternative processing

---

## Monitoring Processing

### Checking Step Functions Execution

#### AWS CLI

```bash
# Get state machine ARN
STATE_MACHINE=$(cd terraform && terraform output -raw state_machine_arn)

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE \
  --max-results 10

# Get execution details
EXECUTION_ARN="<arn-from-list>"
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN
```

#### AWS Console

1. Go to Step Functions Console: https://console.aws.amazon.com/states/
2. Click on `dicom-processing-workflow-dev`
3. View list of executions
4. Click on specific execution to see details:
   - Visual workflow diagram
   - Input/output for each step
   - Execution history
   - Error messages (if any)

### Checking Lambda Logs

#### AWS CLI

```bash
# Get function name
INGESTION_FUNCTION=$(cd terraform && terraform output -raw ingestion_function_name)

# View recent logs
aws logs tail /aws/lambda/$INGESTION_FUNCTION --since 30m

# Follow logs in real-time
aws logs tail /aws/lambda/$INGESTION_FUNCTION --follow

# Filter for errors
aws logs tail /aws/lambda/$INGESTION_FUNCTION --filter-pattern "ERROR"
```

#### AWS Console

1. Go to CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/
2. Click "Log groups"
3. Find your Lambda function log group:
   - `/aws/lambda/medical-imaging-pipeline-ingestion`
   - `/aws/lambda/medical-imaging-pipeline-validation`
   - `/aws/lambda/medical-imaging-pipeline-deidentification`
4. Click on log stream to view details

### Understanding Execution Status

**RUNNING**: Processing in progress
- Normal for files taking time to process
- Check which Lambda function is currently executing

**SUCCEEDED**: Processing completed successfully
- File has been de-identified
- Available in processed bucket
- Ready for download

**FAILED**: Processing encountered an error
- Check error message in execution details
- Review Lambda logs for stack trace
- See [Troubleshooting](#troubleshooting) section

**TIMED_OUT**: Execution exceeded timeout limit
- Default timeout: 5 minutes (configurable)
- May indicate very large file or performance issue
- Consider increasing timeout or optimizing

### Processing Time

Typical processing times:
- **Small files (<10 MB)**: 2-5 seconds
- **Medium files (10-50 MB)**: 5-15 seconds
- **Large files (50-250 MB)**: 15-60 seconds

Factors affecting processing time:
- File size
- DICOM compression
- Lambda cold start (first invocation)
- Number of DICOM tags
- Metadata complexity

---

## Downloading Processed Files

### Method 1: Generate Presigned URL (Recommended)

Presigned URLs provide secure, time-limited access without requiring AWS credentials.

#### Python Script

```python
from src.delivery.presigned_url_handler import PresignedUrlHandler

# Initialize handler with processed bucket
handler = PresignedUrlHandler(
    bucket_name="medical-imaging-pipeline-dev-processed-dicom",
    region_name="us-east-1"
)

# Generate URL
url_info = handler.generate_secure_download_url(
    object_key="patient123/study456/image001.dcm",
    expiration_seconds=3600,  # 1 hour
    validate_exists=True
)

if url_info:
    print(f"Download URL: {url_info['url']}")
    print(f"Expires in: {url_info['expires_in']} seconds")
    print(f"Object: {url_info['object_key']}")
else:
    print("File not found")
```

#### Download with URL

```bash
# Using curl
curl -o downloaded.dcm "<presigned-url>"

# Using wget
wget -O downloaded.dcm "<presigned-url>"

# Using Python
import requests
response = requests.get("<presigned-url>")
with open('downloaded.dcm', 'wb') as f:
    f.write(response.content)
```

### Method 2: AWS CLI Direct Download

```bash
PROCESSED_BUCKET="medical-imaging-pipeline-dev-processed-dicom"

# Download single file
aws s3 cp s3://$PROCESSED_BUCKET/patient123/study456/image001.dcm ./downloaded.dcm

# Download entire directory
aws s3 cp s3://$PROCESSED_BUCKET/patient123/study456/ ./downloads/ --recursive

# List files before downloading
aws s3 ls s3://$PROCESSED_BUCKET/patient123/study456/ --recursive
```

### Method 3: AWS Console

1. Go to S3 Console
2. Navigate to processed bucket
3. Browse to file location
4. Click file → "Download" button

**Note**: Console download requires AWS credentials and browser access.

### Batch Download

Generate multiple URLs at once:

```python
from src.delivery.presigned_url_handler import PresignedUrlHandler

handler = PresignedUrlHandler(
    bucket_name="medical-imaging-pipeline-dev-processed-dicom",
    region_name="us-east-1"
)

# List of files to download
file_keys = [
    "patient123/study456/image001.dcm",
    "patient123/study456/image002.dcm",
    "patient123/study456/image003.dcm",
]

# Generate URLs
results = handler.generate_batch_download_urls(
    object_keys=file_keys,
    expiration_seconds=3600
)

# Download all files
import requests
for key, url_info in results.items():
    filename = key.split('/')[-1]
    print(f"Downloading {filename}...")
    response = requests.get(url_info['url'])
    with open(f"downloads/{filename}", 'wb') as f:
        f.write(response.content)
    print(f"  ✓ Downloaded {len(response.content)} bytes")
```

---

## Understanding Results

### De-identified DICOM Files

Processed files have PHI removed while preserving diagnostic information.

#### Removed Tags

The following DICOM tags are removed during de-identification:

**Patient Information**:
- Patient Name
- Patient ID (replaced with anonymous ID)
- Patient Birth Date
- Patient Sex
- Patient Address
- Patient Telephone Numbers
- Other Patient IDs/Names

**Study/Institution Information**:
- Institution Name
- Institution Address
- Referring Physician Name
- Performing Physician Name
- Operators' Name
- Station Name

**Dates/Times** (replaced with shifted/removed dates):
- Content Date/Time (except year)
- Acquisition Date/Time
- Study Date/Time (year preserved)

**See Full List**: `src/ingestion/deidentifier.py` for complete tag list

#### Preserved Information

Diagnostic metadata is preserved:
- Study Instance UID (anonymized)
- Series Instance UID (anonymized)
- SOP Instance UID (anonymized)
- Image dimensions (Rows, Columns)
- Pixel spacing
- Modality
- Body part examined
- Study description (if not PHI)
- Acquisition parameters
- Image pixel data

### Verifying De-identification

```python
import pydicom

# Load original file
original = pydicom.dcmread('original.dcm')
print(f"Original Patient Name: {original.PatientName}")
print(f"Original Patient ID: {original.PatientID}")

# Load de-identified file
processed = pydicom.dcmread('processed.dcm')
print(f"Processed Patient Name: {processed.get('PatientName', 'REMOVED')}")
print(f"Processed Patient ID: {processed.get('PatientID', 'ANONYMOUS')}")

# Should show:
# Original Patient Name: John Doe
# Original Patient ID: 12345
# Processed Patient Name: REMOVED
# Processed Patient ID: ANON-abc123def456
```

### File Naming

Processed files maintain the same key structure:
- Input: `s3://raw-bucket/patient123/study456/image001.dcm`
- Output: `s3://processed-bucket/patient123/study456/image001.dcm`

The patient/study IDs in the path are preserved for organizational purposes, but the DICOM tags inside the file are anonymized.

---

## Troubleshooting

### Issue: File Not Processing

**Symptoms**: File uploaded but no execution started

**Possible Causes**:
1. File extension not `.dcm`
2. S3 event notification not configured
3. Lambda function not triggered

**Solutions**:
```bash
# Check file extension
aws s3 ls s3://raw-bucket/ --recursive

# Verify S3 event notification
aws s3api get-bucket-notification-configuration \
  --bucket medical-imaging-pipeline-dev-raw-dicom

# Manually trigger processing (if needed)
aws lambda invoke \
  --function-name medical-imaging-pipeline-ingestion \
  --payload file://event.json \
  response.json
```

### Issue: Processing Failed

**Symptoms**: Execution status shows "FAILED"

**Diagnosis**:
```bash
# Get execution details
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query '{status:status, error:error, cause:cause}'
```

**Common Errors**:

1. **"Invalid DICOM file"**
   - Cause: File is not valid DICOM format
   - Solution: Verify file with DICOM viewer before uploading

2. **"Validation failed"**
   - Cause: Missing required DICOM tags
   - Solution: Check error details for specific missing tags

3. **"Lambda timeout"**
   - Cause: File too large or processing taking too long
   - Solution: Increase Lambda timeout or split large files

4. **"Access Denied"**
   - Cause: IAM permissions issue
   - Solution: Verify Lambda execution role has S3 access

### Issue: Downloaded File Corrupted

**Symptoms**: Downloaded DICOM file won't open in viewer

**Solutions**:
1. Verify download completed:
   ```bash
   # Check file size matches
   aws s3 ls s3://processed-bucket/path/to/file.dcm
   ls -lh downloaded.dcm
   ```

2. Re-download file:
   ```bash
   aws s3 cp s3://processed-bucket/path/to/file.dcm ./file.dcm
   ```

3. Verify DICOM validity:
   ```python
   import pydicom
   try:
       ds = pydicom.dcmread('downloaded.dcm')
       print("Valid DICOM file")
   except Exception as e:
       print(f"Invalid DICOM: {e}")
   ```

### Issue: Presigned URL Expired

**Symptoms**: URL returns "AccessDenied" or 403 error

**Cause**: URL has exceeded expiration time (default 1 hour)

**Solution**: Generate new URL:
```python
handler = PresignedUrlHandler(bucket_name="...", region_name="us-east-1")
new_url = handler.generate_download_url(
    object_key="path/to/file.dcm",
    expiration_seconds=7200  # 2 hours
)
```

### Issue: Slow Processing

**Symptoms**: Files taking longer than expected to process

**Diagnosis**:
```bash
# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=medical-imaging-pipeline-deidentification \
  --statistics Average,Maximum \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600
```

**Solutions**:
1. Increase Lambda memory (more memory = more CPU)
2. Optimize DICOM file size before upload
3. Use compressed transfer syntax
4. Check for Lambda cold starts

### Issue: Cannot Find Processed File

**Symptoms**: File in raw bucket but not in processed bucket

**Diagnosis**:
1. Check Step Functions execution status
2. Review Lambda logs for errors
3. Verify file path structure

**Solutions**:
```bash
# List all files in processed bucket
aws s3 ls s3://processed-bucket/ --recursive

# Search for specific file
aws s3 ls s3://processed-bucket/ --recursive | grep "filename"

# Check if processing is still running
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE \
  --status-filter RUNNING
```

---

## FAQ

### General Questions

**Q: How long are files stored?**

A: Storage lifecycle is configurable:
- Raw bucket: 90 days (Standard) → 180 days (IA) → Glacier
- Processed bucket: Same lifecycle
- Can be customized in Terraform variables

**Q: What happens to PHI?**

A: PHI is completely removed from DICOM files. Only anonymous IDs and diagnostic metadata remain.

**Q: Can I recover original files?**

A: Yes, original files are stored in the raw bucket with versioning enabled. They can be recovered if needed (subject to retention policies).

**Q: How do I delete files?**

A:
```bash
# Delete from raw bucket
aws s3 rm s3://raw-bucket/path/to/file.dcm

# Delete from processed bucket
aws s3 rm s3://processed-bucket/path/to/file.dcm

# Delete recursively
aws s3 rm s3://bucket-name/folder/ --recursive
```

### Technical Questions

**Q: What DICOM formats are supported?**

A: All standard DICOM formats are supported including:
- Uncompressed
- JPEG Baseline
- JPEG 2000
- RLE
- All standard transfer syntaxes

**Q: Can I process non-DICOM medical images?**

A: Currently only DICOM format is supported. Other formats (JPEG, PNG, etc.) will be ignored.

**Q: What's the maximum file size?**

A: 250 MB due to AWS Lambda limits. For larger files, consider alternative processing methods.

**Q: How do I process files programmatically?**

A: Upload files to S3 using AWS SDK (boto3, AWS SDK for Java, etc.). Processing starts automatically.

**Q: Can I customize de-identification rules?**

A: Yes, modify `src/ingestion/deidentifier.py` and redeploy:
```python
# Add tags to preserve
deidentifier = Deidentifier(preserve_tags=[
    (0x0008, 0x0070),  # Manufacturer
    (0x0008, 0x1090),  # Model Name
])
```

**Q: How do I monitor costs?**

A:
```bash
# AWS Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://cost-filter.json
```

Or use AWS Cost Explorer in console: https://console.aws.amazon.com/cost-management/

### Security Questions

**Q: Is this HIPAA compliant?**

A: Yes, when properly configured:
- Sign AWS BAA
- Enable encryption
- Configure audit logging
- Follow security best practices
- See [COMPLIANCE.md](COMPLIANCE.md) for details

**Q: Who can access the files?**

A: Only IAM users/roles with explicit permissions. All buckets block public access by default.

**Q: Are files encrypted?**

A: Yes:
- At rest: AES-256 encryption
- In transit: HTTPS/TLS
- Keys managed by AWS

**Q: How long do presigned URLs last?**

A: Default 1 hour, configurable up to 7 days:
```python
url_info = handler.generate_download_url(
    object_key="file.dcm",
    expiration_seconds=604800  # 7 days
)
```

**Q: Can I audit who accessed files?**

A: Yes, enable:
- S3 access logging (enabled by default)
- CloudTrail (for API calls)
- CloudWatch Logs (application logs)

### Performance Questions

**Q: How fast is processing?**

A: Typical performance:
- 100 MB file: ~10-15 seconds
- 50 MB file: ~5-10 seconds
- 10 MB file: ~2-5 seconds

**Q: How many files can I process concurrently?**

A: Default AWS Lambda concurrency limits apply (1000 concurrent executions). Can be increased by requesting AWS limit increase.

**Q: Can I speed up processing?**

A: Yes:
1. Increase Lambda memory allocation
2. Use smaller file sizes
3. Optimize DICOM compression
4. Pre-warm Lambda functions

**Q: What about very large studies (1000+ images)?**

A: Consider:
1. Upload in batches
2. Use Step Functions Express workflows
3. Implement queuing with SQS
4. Scale Lambda concurrency

---

## Best Practices

### File Organization

```
s3://raw-bucket/
  ├── patient001/
  │   ├── study001/
  │   │   ├── series001/
  │   │   │   ├── image001.dcm
  │   │   │   ├── image002.dcm
  │   │   │   └── ...
  │   │   └── series002/
  │   └── study002/
  └── patient002/
```

### Naming Conventions

- Use consistent naming
- Include study/series identifiers
- Use `.dcm` extension
- Avoid spaces and special characters

### Security

- Never commit AWS credentials
- Use IAM roles instead of access keys
- Enable MFA for console access
- Regularly rotate credentials
- Monitor CloudWatch logs for suspicious activity

### Cost Optimization

- Delete raw files after processing (if no longer needed)
- Use S3 lifecycle policies
- Right-size Lambda memory
- Monitor and optimize cold starts
- Use S3 Intelligent-Tiering for long-term storage

---

## Getting Help

### Documentation

- [Architecture](ARCHITECTURE.md) - Technical architecture details
- [API Documentation](API.md) - Handler APIs and interfaces
- [Compliance](COMPLIANCE.md) - HIPAA compliance documentation
- [Deployment](DEPLOYMENT.md) - Deployment and AWS setup

### AWS Resources

- AWS Support: https://console.aws.amazon.com/support/
- AWS Documentation: https://docs.aws.amazon.com/
- DICOM Standard: https://www.dicomstandard.org/

### Common Commands Reference

```bash
# Upload file
aws s3 cp file.dcm s3://raw-bucket/path/

# Check processing status
aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE

# View logs
aws logs tail /aws/lambda/function-name --follow

# Download file
aws s3 cp s3://processed-bucket/path/file.dcm ./

# List files
aws s3 ls s3://bucket-name/ --recursive

# Delete file
aws s3 rm s3://bucket-name/path/file.dcm
```

---

**Need more help?** Review the documentation in `docs/` directory or check AWS CloudWatch logs for detailed error messages.
