# Architecture Documentation

## System Overview

The Medical Imaging Pipeline is a serverless, event-driven architecture built on AWS that automates DICOM file processing from ingestion through de-identification and delivery.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Medical Imaging Pipeline                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          Data Ingestion Layer                           │ │
│  │                                                                          │ │
│  │  [Client] ──► S3 Raw Bucket ──► S3 Event Notification                   │ │
│  │                    │                       │                             │ │
│  │                    │                       ▼                             │ │
│  │                    │              Ingestion Lambda ◄─── IAM Role        │ │
│  │                    │                       │                             │ │
│  │                    └───────────────────────┘                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                   │                                          │
│                                   ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Processing Orchestration Layer                     │ │
│  │                                                                          │ │
│  │                     Step Functions State Machine                         │ │
│  │                                                                          │ │
│  │   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐        │ │
│  │   │  Ingestion   │─────►│  Validation  │─────►│ Deidentify   │        │ │
│  │   │    State     │      │    State     │      │    State     │        │ │
│  │   └──────────────┘      └──────────────┘      └──────────────┘        │ │
│  │         │                     │                      │                  │ │
│  │         │                     │                      │                  │ │
│  │         ▼                     ▼                      ▼                  │ │
│  │   Lambda Invoke         Lambda Invoke          Lambda Invoke           │ │
│  │                                                                          │ │
│  │   Error Handling: Retry Logic + CloudWatch Metrics                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                   │                                          │
│                                   ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          Storage & Delivery Layer                       │ │
│  │                                                                          │ │
│  │  S3 Processed Bucket ◄─── Deidentification Lambda                       │ │
│  │         │                                                                │ │
│  │         ▼                                                                │ │
│  │  Presigned URL Handler ──► Time-Limited Download URLs                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                   │                                          │
│                                   ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Monitoring & Logging Layer                         │ │
│  │                                                                          │ │
│  │  CloudWatch Logs  │  CloudWatch Metrics  │  CloudWatch Alarms           │ │
│  │  ─────────────────┴──────────────────────┴─────────────────            │ │
│  │  • Lambda Logs          • Execution Count      • Failures               │ │
│  │  • Step Functions       • Duration             • Timeouts               │ │
│  │  • Custom App Logs      • Error Rate           • Custom Alarms          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Ingestion Layer

#### S3 Raw Bucket
- **Purpose**: Store uploaded DICOM files
- **Configuration**:
  - Versioning: Enabled
  - Encryption: AES-256
  - Lifecycle: Transition to IA after 90 days
  - Event notifications: Trigger Lambda on `.dcm` upload

#### Ingestion Lambda
- **Runtime**: Python 3.12
- **Memory**: 512 MB (configurable)
- **Timeout**: 300 seconds
- **Trigger**: S3 ObjectCreated event
- **Responsibilities**:
  - Parse DICOM file from S3
  - Extract metadata (Patient, Study, Series, Image)
  - Validate DICOM structure
  - Prepare data for validation step

### 2. Processing Layer

#### Step Functions State Machine

**State Flow**:
```
IngestionStep
    ↓
CheckIngestionStatus (Choice)
    ↓
ParseIngestionResult (Pass)
    ↓
ValidationStep
    ↓
CheckValidationStatus (Choice)
    ↓
ParseValidationResult (Pass)
    ↓
DeidentificationStep
    ↓
CheckDeidentificationStatus (Choice)
    ↓
ParseDeidentificationResult (Pass)
    ↓
PublishSuccessMetric (CloudWatch PutMetricData)
    ↓
SuccessState (Succeed)

[Any Error] ──► ErrorHandler ──► FailureState (Fail)
```

**Retry Configuration**:
- Max Attempts: 3
- Backoff Rate: 2x
- Initial Interval: 2 seconds
- Error Types: Lambda.ServiceException, Lambda.AWSLambdaException

**Error Handling**:
- Catch-all error handler
- CloudWatch metrics on failure
- Detailed error logging

#### Validation Lambda
- **Runtime**: Python 3.12
- **Memory**: 512 MB
- **Timeout**: 300 seconds
- **Responsibilities**:
  - Validate metadata against Pydantic schemas
  - Check DICOM compliance (UIDs, dates, required fields)
  - Return validation results

#### Deidentification Lambda
- **Runtime**: Python 3.12
- **Memory**: 512 MB
- **Timeout**: 300 seconds
- **Responsibilities**:
  - Remove PHI (Protected Health Information)
  - Anonymize patient identifiers
  - Preserve diagnostic metadata
  - Upload de-identified file to processed bucket

### 3. Storage Layer

#### S3 Processed Bucket
- **Purpose**: Store de-identified DICOM files
- **Configuration**:
  - Versioning: Enabled
  - Encryption: AES-256
  - Lifecycle: Transition to IA after 90 days, Glacier after 180 days
  - Public access: Blocked

#### S3 Logs Bucket
- **Purpose**: Store S3 access logs
- **Configuration**:
  - Server-side encryption
  - Lifecycle: Expire after 90 days

### 4. Delivery Layer

#### Presigned URL Handler
- **Purpose**: Generate secure, time-limited download URLs
- **Features**:
  - Configurable expiration (default: 1 hour)
  - Object existence validation
  - DICOM-specific content headers
  - Batch URL generation
  - Structured logging

### 5. Security Layer

#### IAM Roles

**Lambda Execution Role**:
```json
{
  "Permissions": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket",
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "cloudwatch:PutMetricData"
  ]
}
```

**Step Functions Execution Role**:
```json
{
  "Permissions": [
    "lambda:InvokeFunction",
    "cloudwatch:PutMetricData",
    "logs:CreateLogDelivery",
    "logs:PutResourcePolicy"
  ]
}
```

### 6. Monitoring Layer

#### CloudWatch Logs
- **Log Groups**:
  - `/aws/lambda/medical-imaging-pipeline-ingestion`
  - `/aws/lambda/medical-imaging-pipeline-validation`
  - `/aws/lambda/medical-imaging-pipeline-deidentification`
  - `/aws/stepfunctions/dicom-processing-workflow`

- **Retention**: 30 days (configurable)
- **Format**: JSON structured logging

#### CloudWatch Metrics
- **Custom Metrics**:
  - `MedicalImaging/Pipeline/PipelineSuccess`
  - `MedicalImaging/Pipeline/PipelineFailure`

- **AWS Metrics**:
  - Lambda invocations, errors, duration
  - Step Functions executions, failures, timeouts
  - S3 bucket metrics

#### CloudWatch Alarms
- Step Functions execution failures
- Step Functions timeouts
- (Extensible for Lambda errors, S3 events)

## Data Flow

### 1. Upload Flow

```
Client
  │
  ├─► aws s3 cp file.dcm s3://raw-bucket/
  │
  ▼
S3 Raw Bucket
  │
  ├─► S3 Event Notification
  │
  ▼
Ingestion Lambda
  │
  ├─► Parse DICOM
  ├─► Extract metadata
  ├─► Log to CloudWatch
  │
  ▼
Return metadata JSON
```

### 2. Processing Flow

```
Step Functions Execution Start
  │
  ├─► IngestionStep
  │     ├─► Invoke Lambda with S3 event
  │     ├─► Parse DICOM file
  │     └─► Return: { statusCode: 200, metadata: {...} }
  │
  ├─► ValidationStep
  │     ├─► Validate metadata with Pydantic
  │     ├─► Check DICOM compliance
  │     └─► Return: { statusCode: 200, valid: true }
  │
  ├─► DeidentificationStep
  │     ├─► Load DICOM from S3
  │     ├─► Remove PHI tags
  │     ├─► Upload to processed bucket
  │     └─► Return: { statusCode: 200, output_key: "..." }
  │
  ├─► PublishSuccessMetric
  │     └─► CloudWatch PutMetricData
  │
  └─► SuccessState
```

### 3. Download Flow

```
Client Application
  │
  ├─► from src.delivery import PresignedUrlHandler
  ├─► handler = PresignedUrlHandler(bucket, region)
  ├─► url_info = handler.generate_secure_download_url(key)
  │
  ▼
Presigned URL Generated
  │
  ├─► Time-limited (1 hour default)
  ├─► DICOM content-type
  ├─► Attachment disposition
  │
  ▼
Client downloads file via URL
```

## Technology Stack

### Core Technologies
- **Python**: 3.12
- **AWS Lambda**: Serverless compute
- **AWS Step Functions**: Workflow orchestration
- **AWS S3**: Object storage
- **AWS CloudWatch**: Monitoring & logging
- **AWS IAM**: Access control

### Python Libraries
- **pydicom**: DICOM file processing (2.4.4)
- **pydantic**: Data validation (2.9.2)
- **boto3**: AWS SDK (1.35.77)
- **pytest**: Testing framework (9.0.0)
- **moto**: AWS mocking (5.0.22)
- **black**: Code formatting (24.10.0)
- **flake8**: Linting (7.1.1)

### Infrastructure
- **Terraform**: >= 1.0
- **Terraform AWS Provider**: ~> 5.0

## Design Patterns

### 1. Event-Driven Architecture
- S3 events trigger Lambda functions
- Asynchronous, decoupled components
- Scalable and resilient

### 2. Orchestration Pattern
- Step Functions coordinate complex workflows
- Retry logic and error handling
- State management

### 3. Handler Pattern
- Standardized Lambda handlers
- Decorator-based wrapper
- Consistent error handling

### 4. Repository Pattern
- S3Handler abstracts storage operations
- CloudWatchHandler abstracts monitoring
- Testable and mockable

### 5. Validation Pattern
- Pydantic schemas for type safety
- Early validation in pipeline
- Clear error messages

## Scalability Considerations

### Horizontal Scaling
- **Lambda**: Automatic scaling to handle concurrent requests
- **S3**: Unlimited storage and throughput
- **Step Functions**: 1000s of concurrent executions

### Performance Optimization
- **Lambda Layers**: Shared dependencies reduce cold start
- **Memory Tuning**: Optimized per function
- **S3 Transfer**: Multipart upload for large files
- **Caching**: Presigned URLs reduce S3 calls

### Cost Optimization
- **S3 Lifecycle**: Automatic tier transitions
- **Lambda Memory**: Right-sized allocations
- **CloudWatch Logs**: Configurable retention
- **Step Functions**: Express workflows for high-volume (future)

## Security Architecture

### Encryption
- **At Rest**: AES-256 for all S3 buckets
- **In Transit**: HTTPS/TLS for all communications
- **Key Management**: AWS-managed keys (can upgrade to KMS)

### Access Control
- **IAM Roles**: Least privilege principle
- **S3 Bucket Policies**: Deny public access
- **VPC**: Optional Lambda VPC deployment
- **Presigned URLs**: Time-limited access

### Compliance
- **HIPAA**: PHI removal, encryption, audit logs
- **Audit Trail**: CloudWatch logs all operations
- **Data Retention**: Configurable lifecycle policies
- **Versioning**: S3 versioning for data protection

## Disaster Recovery

### Backup Strategy
- **S3 Versioning**: Previous file versions available
- **Cross-Region Replication**: Can be enabled (future)
- **Terraform State**: Stored in S3 with versioning
- **Infrastructure**: Reproducible with Terraform

### Recovery Procedures
1. **Data Loss**: Restore from S3 version history
2. **Infrastructure Failure**: Re-deploy with Terraform
3. **Corruption**: Replay from raw bucket to processed
4. **Regional Outage**: Deploy to alternate region (future)

## Monitoring & Alerting

### Key Metrics
- **Throughput**: Files processed per hour
- **Latency**: End-to-end processing time
- **Error Rate**: Failed executions percentage
- **Cost**: Daily/monthly AWS costs

### Alert Thresholds
- Step Functions failures: > 0
- Step Functions timeouts: > 0
- Lambda errors: > 5% error rate (can add)
- S3 access denied: > 0 (can add)

## Future Enhancements

### Planned Features
1. **Express Workflows**: For high-throughput scenarios
2. **SQS Integration**: Buffering for burst traffic
3. **DynamoDB**: Metadata index for fast queries
4. **API Gateway**: REST API for uploads/downloads
5. **SNS Notifications**: Email alerts on completion
6. **Cross-Region Replication**: Disaster recovery
7. **Data Lake**: Athena queries on metadata
8. **ML Integration**: Automated image analysis

### Optimization Opportunities
1. **Lambda Performance**: Profile and optimize hot paths
2. **Cost Analysis**: Detailed cost attribution
3. **Advanced Monitoring**: Custom dashboards
4. **Testing**: Load testing and chaos engineering
5. **Documentation**: OpenAPI specs for APIs

## Integration Points

### External Systems
- **PACS Systems**: Can integrate via DICOM C-STORE
- **EMR Systems**: API integration for metadata
- **Viewing Applications**: Download via presigned URLs
- **Analytics Platforms**: S3 data lake integration

### APIs
- **S3 API**: Upload/download files
- **Step Functions API**: Start executions, check status
- **CloudWatch API**: Query logs and metrics
- **Presigned URL Handler**: Generate download URLs

## Performance Benchmarks

### Typical Performance
- **DICOM Parsing**: 100-200ms per file
- **Validation**: 50-100ms
- **De-identification**: 150-300ms per file
- **S3 Upload**: ~1s per 10MB (depends on network)
- **Total Processing**: 2-5 seconds per file (warm Lambda)

### Capacity
- **Concurrent Files**: 1000+ (Lambda concurrency limit)
- **File Size**: Up to 250MB (Lambda limit)
- **Daily Throughput**: Millions of files (theoretically unlimited)
- **Storage**: Unlimited (S3)

## Glossary

- **DICOM**: Digital Imaging and Communications in Medicine
- **PHI**: Protected Health Information
- **IAM**: Identity and Access Management
- **VPC**: Virtual Private Cloud
- **HIPAA**: Health Insurance Portability and Accountability Act
- **IA**: Infrequent Access (S3 storage class)
- **ASL**: Amazon States Language (Step Functions definition)
- **UID**: Unique Identifier (DICOM)
- **SOP**: Service-Object Pair (DICOM)
