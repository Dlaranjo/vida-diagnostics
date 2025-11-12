# Medical Imaging Data Pipeline

A production-ready, HIPAA-compliant data delivery pipeline for processing and delivering medical imaging data packages using AWS services.

## Project Overview

This pipeline demonstrates end-to-end capabilities for:
- Processing DICOM medical imaging files
- De-identifying Protected Health Information (PHI)
- Validating data quality and schema compliance
- Securely delivering data packages to partners
- Maintaining comprehensive audit logs

Built for the **Data Delivery Engineer** role at VIDA Diagnostics.

## Key Features

- **DICOM Processing**: Parse and extract metadata from medical imaging files
- **PHI De-identification**: HIPAA-compliant removal of patient information
- **Multi-format ETL**: Process DICOM, CSV, and JSON data
- **Data Validation**: Pydantic schemas with quality checks
- **AWS Integration**: S3, Lambda, Step Functions, CloudWatch
- **Secure Delivery**: Time-limited presigned URLs with encryption
- **Comprehensive Testing**: 80%+ code coverage with pytest
- **Infrastructure as Code**: Terraform for reproducible deployments

## Architecture

```
Data Ingestion → Processing & Validation → Delivery → Monitoring
     (S3)              (Lambda/Step Functions)        (S3 + URLs)    (CloudWatch)
```

See [PROJECT_VISION.md](../PROJECT_VISION.md) for detailed architecture and design decisions.

## Technology Stack

- **Python 3.11+** with type hints
- **pydicom** for DICOM file processing
- **pandas** for data transformation
- **pydantic** for schema validation
- **boto3** for AWS SDK
- **pytest** for testing
- **Terraform** for infrastructure

## Project Structure

```
medical-imaging-pipeline/
├── src/                      # Source code
│   ├── ingestion/           # DICOM parsing, de-identification
│   ├── validation/          # Pydantic schemas, quality checks
│   ├── transformation/      # Data standardization
│   ├── delivery/            # Secure delivery mechanisms
│   ├── orchestration/       # Step Functions handlers
│   └── utils/               # Logging, encryption, audit
├── lambda_functions/        # AWS Lambda handlers
├── infrastructure/          # Terraform IaC
├── tests/                   # Test suite
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/           # Sample test data
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
└── config/                  # Environment configurations
```

## Quick Start

### Prerequisites

- Python 3.11+
- AWS Account with appropriate permissions
- Terraform 1.5+
- Docker (optional, for local testing)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd medical-imaging-pipeline

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Check code quality
black --check src tests
flake8 src tests
mypy src
```

### Local Development

```bash
# Run tests with coverage
pytest --cov=src --cov-report=html

# Format code
black src tests
isort src tests

# View coverage report
open htmlcov/index.html
```

### AWS Deployment

```bash
# Configure AWS credentials
aws configure

# Initialize Terraform
cd infrastructure/terraform
terraform init

# Plan deployment
terraform plan

# Deploy to AWS
terraform apply

# Run end-to-end tests
pytest tests/e2e/
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions (coming soon).

## Testing

The project includes comprehensive testing:

- **Unit Tests**: Individual component testing
- **Integration Tests**: AWS service interaction testing (using moto)
- **End-to-End Tests**: Full pipeline validation
- **Coverage Target**: 80%+ code coverage

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage report
pytest --cov=src --cov-report=term-missing
```

## Compliance & Security

This pipeline implements HIPAA technical safeguards:

- **Access Control**: IAM roles, presigned URL expiration
- **Audit Controls**: CloudTrail logging, execution history
- **Integrity**: Checksum verification, S3 versioning
- **Transmission Security**: TLS encryption, KMS at-rest encryption

See [docs/COMPLIANCE.md](docs/COMPLIANCE.md) for detailed compliance documentation (coming soon).

## Documentation

- [PROJECT_VISION.md](../PROJECT_VISION.md) - High-level project vision and architecture
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detailed system design (coming soon)
- [docs/COMPLIANCE.md](docs/COMPLIANCE.md) - HIPAA/SOC2/GxP documentation (coming soon)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide (coming soon)

## Development Roadmap

### Current Status: Week 1 - Foundation
- [x] Project setup and structure
- [ ] DICOM processing implementation
- [ ] Data validation framework
- [ ] Basic AWS integration

### Week 2 - Deployment
- [ ] Step Functions orchestration
- [ ] Secure delivery mechanisms
- [ ] Comprehensive testing
- [ ] AWS deployment
- [ ] Documentation completion

## Contributing

This is a demonstration project for a job application. However, if you'd like to provide feedback or suggestions:

1. Ensure all tests pass
2. Follow code style (black, flake8, mypy)
3. Maintain 80%+ test coverage
4. Update documentation

## License

MIT License - See LICENSE file for details

## Contact

For questions about this project, please contact daniel.laranjo@iebtinnovation.com.

---

**Built for**: Data Delivery Engineer position at VIDA Diagnostics
**Timeline**: 1-2 weeks MVP
**Status**: In Development
