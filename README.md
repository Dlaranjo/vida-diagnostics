# Medical Imaging Pipeline

> HIPAA-compliant serverless DICOM processing pipeline for medical imaging workflows

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-95.5%25-brightgreen.svg)](medical-imaging-pipeline/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Terraform](https://img.shields.io/badge/terraform-%3E%3D1.0-purple.svg)](https://www.terraform.io/)

## Overview

A production-ready, serverless medical imaging pipeline built on AWS that automates DICOM file ingestion, validation, de-identification, and secure delivery. Designed with HIPAA compliance, scalability, and cost optimization in mind.

### Key Features

- **Automated DICOM Processing**: Seamless ingestion, validation, and de-identification
- **HIPAA Compliant**: Encryption, audit logging, and PHI removal
- **Serverless Architecture**: AWS Lambda + Step Functions for scalability
- **High Test Coverage**: 95.5% code coverage with 284 comprehensive tests
- **Infrastructure as Code**: Complete Terraform configuration for reproducible deployments
- **Secure File Delivery**: Time-limited presigned URLs for downloads
- **Comprehensive Monitoring**: CloudWatch logging, metrics, and alarms

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DICOM Processing Pipeline                    │
│                                                                   │
│  S3 Raw Bucket                                                   │
│       │                                                           │
│       ├─► Lambda Trigger (.dcm files)                            │
│       │                                                           │
│       ▼                                                           │
│  ┌──────────────────────────────────────┐                        │
│  │   Step Functions State Machine       │                        │
│  │                                      │                        │
│  │  ┌────────────┐   ┌──────────────┐  │                        │
│  │  │ Ingestion  │──►│ Validation   │  │                        │
│  │  │  Lambda    │   │   Lambda     │  │                        │
│  │  └────────────┘   └──────────────┘  │                        │
│  │                          │           │                        │
│  │                          ▼           │                        │
│  │                  ┌────────────────┐  │                        │
│  │                  │ Deidentify     │  │                        │
│  │                  │   Lambda       │  │                        │
│  │                  └────────────────┘  │                        │
│  │                          │           │                        │
│  └──────────────────────────┼───────────┘                        │
│                             ▼                                    │
│                    S3 Processed Bucket                           │
│                             │                                    │
│                             ▼                                    │
│                    Presigned URL Handler                         │
│                             │                                    │
│                             ▼                                    │
│                    Secure Download Links                         │
│                                                                   │
│  CloudWatch: Logging, Metrics, Alarms                           │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12+
- AWS CLI configured
- Terraform >= 1.0
- pytest for testing

### Installation

```bash
# Clone repository
git clone <repository-url>
cd medical-imaging-pipeline

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run with markers
pytest -m unit
pytest -m integration
```

### Local Development

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/ --max-line-length=100

# Type checking (if mypy installed)
mypy src/
```

## Project Structure

```
medical-imaging-pipeline/
├── src/                          # Source code
│   ├── ingestion/                # DICOM ingestion & parsing
│   │   ├── dicom_parser.py       # DICOM file parsing
│   │   ├── deidentifier.py       # PHI removal
│   │   ├── metadata_extractor.py # Metadata extraction
│   │   └── validated_parser.py   # Validated parsing
│   ├── validation/               # Data validation
│   │   └── schemas.py            # Pydantic schemas
│   ├── storage/                  # Storage handlers
│   │   └── s3_handler.py         # S3 operations
│   ├── monitoring/               # Monitoring & logging
│   │   └── cloudwatch_handler.py # CloudWatch integration
│   ├── orchestration/            # Workflow orchestration
│   │   ├── lambda_handlers.py    # Lambda function handlers
│   │   └── step_functions.py     # Step Functions handler
│   ├── delivery/                 # File delivery
│   │   └── presigned_url_handler.py # Presigned URL generation
│   └── utils/                    # Utilities
│       └── logger.py             # Structured logging
│
├── tests/                        # Test suite (95.5% coverage)
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
│
├── terraform/                    # Infrastructure as Code
│   ├── modules/                  # Reusable modules
│   │   ├── s3/                   # S3 buckets
│   │   ├── lambda/               # Lambda functions
│   │   ├── iam/                  # IAM roles & policies
│   │   └── step_functions/       # Step Functions
│   ├── environments/             # Environment configs
│   │   ├── dev/
│   │   └── prod/
│   └── scripts/                  # Automation scripts
│       ├── build_lambda_layer.sh
│       ├── deploy.sh
│       └── destroy.sh
│
├── state_machines/               # Step Functions definitions
│   └── dicom_processing_workflow.json
│
├── lambda_functions/             # Lambda entry points
│   ├── ingestion_handler.py
│   ├── validation_handler.py
│   └── deidentification_handler.py
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # Architecture details
│   ├── API.md                    # API documentation
│   ├── COMPLIANCE.md             # HIPAA compliance
│   ├── DEPLOYMENT.md             # Deployment guide
│   └── USER_GUIDE.md             # User guide
│
├── PROJECT_VISION.md             # High-level vision
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── requirements-dev.txt          # Development dependencies
├── pytest.ini                    # Pytest configuration
├── pyproject.toml                # Project metadata
└── setup.cfg                     # Tool configurations
```

## Core Components

### 1. DICOM Processing

**Ingestion** (`src/ingestion/`)
- Parse DICOM files with pydicom
- Extract comprehensive metadata
- Validate DICOM structure
- Handle various DICOM formats

**De-identification** (`src/ingestion/deidentifier.py`)
- Remove PHI (Protected Health Information)
- Anonymize patient data
- Preserve diagnostic value
- HIPAA-compliant processing

### 2. Validation

**Pydantic Schemas** (`src/validation/schemas.py`)
- Strict type validation
- DICOM metadata schemas
- Patient, Study, Series models
- Comprehensive validation rules

### 3. Storage

**S3 Handler** (`src/storage/s3_handler.py`)
- Upload/download operations
- Multipart upload support
- Lifecycle management
- Encryption at rest

### 4. Monitoring

**CloudWatch Integration** (`src/monitoring/cloudwatch_handler.py`)
- Structured logging
- Custom metrics
- Log groups management
- Alarm configuration

### 5. Orchestration

**Step Functions** (`src/orchestration/step_functions.py`)
- Workflow state machine
- Error handling & retries
- Execution management
- Variable substitution

**Lambda Handlers** (`src/orchestration/lambda_handlers.py`)
- Ingestion handler
- Validation handler
- Deidentification handler
- Standardized error handling

### 6. Delivery

**Presigned URLs** (`src/delivery/presigned_url_handler.py`)
- Secure download links
- Time-limited access
- Batch URL generation
- DICOM-specific headers

## Testing

### Test Statistics

- **Total Tests**: 284
- **Coverage**: 95.5%
- **Test Types**: Unit, Integration, End-to-End

### Test Organization

```bash
tests/
├── unit/                         # Unit tests (22 test classes)
│   ├── test_dicom_parser.py
│   ├── test_deidentifier.py
│   ├── test_metadata_extractor.py
│   ├── test_validated_parser.py
│   ├── test_schemas.py
│   ├── test_s3_handler.py
│   ├── test_cloudwatch_handler.py
│   ├── test_lambda_handlers.py
│   ├── test_step_functions.py
│   └── test_presigned_url_handler.py
│
└── integration/                  # Integration tests
    └── test_validated_parser.py
```

### Running Specific Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific module
pytest tests/unit/test_dicom_parser.py -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Deployment

### Infrastructure Deployment

Complete infrastructure deployment with Terraform:

```bash
cd terraform

# Automated deployment
./scripts/deploy.sh dev

# Or manual deployment
terraform init
terraform plan -var-file="environments/dev/terraform.tfvars"
terraform apply
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions and AWS credentials setup.

### AWS Resources Created

- **3 S3 Buckets**: Raw, processed, logs
- **3 Lambda Functions**: Ingestion, validation, deidentification
- **1 Lambda Layer**: Python dependencies
- **1 Step Functions State Machine**: Processing workflow
- **IAM Roles**: Lambda and Step Functions execution
- **CloudWatch Log Groups**: Logging for all services
- **CloudWatch Alarms**: Failure and timeout monitoring

## Usage

### Uploading DICOM Files

```bash
# Get raw bucket name from Terraform
RAW_BUCKET=$(cd terraform && terraform output -raw raw_bucket_name)

# Upload DICOM file
aws s3 cp patient_scan.dcm s3://$RAW_BUCKET/
```

### Monitoring Processing

```bash
# Get state machine ARN
STATE_MACHINE=$(cd terraform && terraform output -raw state_machine_arn)

# List executions
aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE

# Describe specific execution
aws stepfunctions describe-execution --execution-arn <arn>
```

### Generating Download URLs

```python
from src.delivery.presigned_url_handler import PresignedUrlHandler

# Initialize handler
handler = PresignedUrlHandler(
    bucket_name="processed-bucket-name",
    region_name="us-east-1"
)

# Generate secure download URL
url_info = handler.generate_secure_download_url(
    object_key="patient/study/series/image.dcm",
    expiration_seconds=3600,  # 1 hour
    validate_exists=True
)

print(f"Download URL: {url_info['url']}")
print(f"Expires in: {url_info['expires_in']} seconds")
```

## Security & Compliance

### HIPAA Compliance

- ✅ **Encryption at Rest**: AES-256 for all S3 buckets
- ✅ **Encryption in Transit**: HTTPS for all communications
- ✅ **PHI Removal**: Comprehensive de-identification
- ✅ **Access Logging**: Complete audit trail
- ✅ **Least Privilege**: Minimal IAM permissions
- ✅ **Data Retention**: Configurable lifecycle policies

See [docs/COMPLIANCE.md](docs/COMPLIANCE.md) for detailed compliance documentation.

### Security Best Practices

1. **Authentication**: AWS IAM for all access
2. **Authorization**: Role-based access control
3. **Encryption**: End-to-end encryption
4. **Monitoring**: CloudWatch logs and alarms
5. **Versioning**: S3 versioning enabled
6. **Backup**: Lifecycle policies for data retention

## Performance

### Benchmarks

- **DICOM Parsing**: ~100ms per file (typical)
- **De-identification**: ~200ms per file
- **S3 Upload**: Depends on file size (multipart for large files)
- **Lambda Cold Start**: ~2-3s (with layer)
- **Lambda Warm Start**: ~100-200ms

### Scalability

- **Concurrent Executions**: Unlimited (configurable Lambda limits)
- **File Size**: Up to 250MB per file (Lambda limit)
- **Throughput**: 1000s of files per hour
- **Storage**: Unlimited S3 storage

### Cost Optimization

- **S3 Lifecycle Policies**: Automatic transition to cheaper storage
- **Lambda Memory**: Optimized per function
- **CloudWatch Logs**: Configurable retention
- **Step Functions**: Express workflows for high-volume

## Monitoring & Observability

### CloudWatch Dashboards

Access CloudWatch console to view:
- Lambda invocation metrics
- Step Functions execution metrics
- S3 bucket metrics
- Custom application metrics

### Logging

All services log to CloudWatch:
```bash
# View Lambda logs
aws logs tail /aws/lambda/medical-imaging-pipeline-ingestion --follow

# View Step Functions logs
aws logs tail /aws/stepfunctions/dicom-processing-workflow --follow
```

### Alarms

Pre-configured alarms for:
- Step Functions execution failures
- Step Functions timeouts
- Lambda errors (can be added)
- S3 access patterns (can be added)

## Contributing

### Development Setup

```bash
# Install pre-commit hooks (if using)
pre-commit install

# Run tests before committing
pytest tests/ --cov=src

# Format code
black src/ tests/

# Lint
flake8 src/ tests/ --max-line-length=100
```

### Code Standards

- **Python**: PEP 8 with Black formatting
- **Line Length**: 100 characters
- **Type Hints**: Encouraged
- **Docstrings**: Required for public functions
- **Test Coverage**: Maintain >90%

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)**: Detailed technical architecture
- **[API Documentation](docs/API.md)**: Handler APIs and interfaces
- **[Compliance](docs/COMPLIANCE.md)**: HIPAA and security compliance
- **[Deployment](docs/DEPLOYMENT.md)**: Step-by-step deployment guide
- **[User Guide](docs/USER_GUIDE.md)**: End-user documentation

## Troubleshooting

### Common Issues

**Issue**: Lambda timeout
- **Solution**: Increase timeout in `terraform/variables.tf`

**Issue**: Out of memory
- **Solution**: Increase memory_size in Lambda configuration

**Issue**: S3 access denied
- **Solution**: Check IAM role permissions

**Issue**: DICOM parsing errors
- **Solution**: Verify DICOM file format and transfer syntax

See full troubleshooting guide in [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [pydicom](https://github.com/pydicom/pydicom) for DICOM processing
- Powered by AWS serverless services
- Infrastructure managed with Terraform
- Tested with pytest and moto

## Support

For issues, questions, or contributions:
- Review documentation in `docs/`
- Check existing issues
- Submit new issues with detailed description

---

**Note**: This is a demonstration project for VIDA Diagnostics job application. For production use, ensure proper AWS account setup, security review, and compliance validation.
