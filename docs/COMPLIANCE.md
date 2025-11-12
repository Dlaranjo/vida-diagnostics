# HIPAA Compliance Documentation

## Overview

This document outlines how the Medical Imaging Pipeline implements HIPAA (Health Insurance Portability and Accountability Act) compliance requirements for handling Protected Health Information (PHI) in DICOM medical imaging files.

## HIPAA Requirements

### Security Rule

The HIPAA Security Rule establishes national standards to protect electronic personal health information (ePHI). It requires:

1. **Administrative Safeguards**
2. **Physical Safeguards**
3. **Technical Safeguards**

## Implementation Summary

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Encryption at Rest | AES-256 for all S3 buckets | ✅ Implemented |
| Encryption in Transit | HTTPS/TLS for all communications | ✅ Implemented |
| Access Control | IAM roles with least privilege | ✅ Implemented |
| Audit Logging | CloudWatch Logs for all operations | ✅ Implemented |
| PHI De-identification | Automated removal of 30+ PHI tags | ✅ Implemented |
| Data Backup | S3 versioning enabled | ✅ Implemented |
| Disaster Recovery | Infrastructure as Code (Terraform) | ✅ Implemented |
| Access Monitoring | CloudWatch metrics and alarms | ✅ Implemented |
| Data Retention | Configurable lifecycle policies | ✅ Implemented |

## Technical Safeguards

### 1. Encryption

#### Encryption at Rest

**Implementation**:
```terraform
# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

**Details**:
- All S3 buckets use AES-256 encryption
- Encryption is enforced at the bucket level
- Keys are managed by AWS (can upgrade to KMS for additional control)

**Compliance**: HIPAA §164.312(a)(2)(iv) - Encryption and Decryption

#### Encryption in Transit

**Implementation**:
- All AWS API calls use HTTPS/TLS
- S3 presigned URLs use HTTPS
- Lambda functions communicate over AWS internal network (encrypted)

**Enforcement**:
```python
# S3 client automatically uses HTTPS
s3_client = boto3.client('s3', region_name='us-east-1')
```

**Compliance**: HIPAA §164.312(e)(1) - Transmission Security

### 2. Access Control

#### IAM Role-Based Access

**Lambda Execution Role** (Least Privilege):
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": [
    "arn:aws:s3:::raw-bucket/*",
    "arn:aws:s3:::processed-bucket/*"
  ]
}
```

**Key Principles**:
- No hardcoded credentials
- Role-based access only
- Minimal permissions per function
- No public access to buckets

**Compliance**: HIPAA §164.312(a)(1) - Access Control

#### S3 Bucket Policies

**Public Access Block**:
```terraform
resource "aws_s3_bucket_public_access_block" "raw" {
  bucket = aws_s3_bucket.raw.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**Compliance**: HIPAA §164.308(a)(3) - Workforce Security

### 3. Audit Controls

#### CloudWatch Logging

**All operations are logged**:
- Lambda function invocations
- Step Functions executions
- S3 access events
- API calls (via CloudTrail, can be enabled)

**Log Format** (Structured JSON):
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "operation": "upload_file",
  "user": "arn:aws:sts::123456789012:assumed-role/...",
  "status": "success",
  "resource": "s3://bucket/key",
  "details": {...}
}
```

**Log Retention**:
- CloudWatch Logs: 30 days (configurable)
- S3 Access Logs: 90 days
- Can be extended for compliance requirements

**Compliance**: HIPAA §164.312(b) - Audit Controls

#### S3 Access Logging

**Implementation**:
```terraform
resource "aws_s3_bucket_logging" "raw" {
  bucket = aws_s3_bucket.raw.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "raw-bucket-logs/"
}
```

**Log Content**:
- Requester identity
- Access time
- Operation performed
- Response status

**Compliance**: HIPAA §164.308(a)(1)(ii)(D) - Information System Activity Review

### 4. PHI De-identification

#### Protected Health Information Removed

The deidentifier removes all PHI tags per HIPAA Safe Harbor method:

**Patient Identifiers**:
```python
PATIENT_PHI_TAGS = [
    (0x0010, 0x0010),  # Patient Name
    (0x0010, 0x0020),  # Patient ID
    (0x0010, 0x0030),  # Patient Birth Date
    (0x0010, 0x0040),  # Patient Sex
    (0x0010, 0x1000),  # Other Patient IDs
    (0x0010, 0x1001),  # Other Patient Names
    (0x0010, 0x1040),  # Patient Address
    (0x0010, 0x2154),  # Patient Telephone
    # ... 30+ tags total
]
```

**Study/Series Identifiers**:
```python
STUDY_PHI_TAGS = [
    (0x0008, 0x0080),  # Institution Name
    (0x0008, 0x0081),  # Institution Address
    (0x0008, 0x0090),  # Referring Physician Name
    (0x0008, 0x1048),  # Physician Reading Study
    (0x0008, 0x1050),  # Performing Physician Name
    # ...
]
```

**Anonymization Process**:
1. Load DICOM file
2. Remove all PHI tags
3. Generate anonymous Patient ID (UUID)
4. Preserve diagnostic metadata
5. Save de-identified file

**Compliance**: HIPAA §164.514(b) - De-identification of Protected Health Information

#### Safe Harbor Method

The deidentifier implements HIPAA Safe Harbor method by removing:
1. Names
2. Geographic subdivisions smaller than state
3. Dates (except year)
4. Telephone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers
13. Device identifiers and serial numbers
14. URLs
15. IP addresses
16. Biometric identifiers
17. Full-face photographs
18. Any other unique identifying number, characteristic, or code

**Reference**: 45 CFR §164.514(b)(2)

### 5. Integrity Controls

#### Data Integrity

**S3 Versioning**:
```terraform
resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id

  versioning_configuration {
    status = "Enabled"
  }
}
```

**Benefits**:
- Protects against accidental deletion
- Maintains version history
- Enables recovery from corruption
- Audit trail of changes

**ETags for Validation**:
```python
# S3 provides ETag (MD5) for integrity checking
result = s3_client.upload_file(...)
etag = result['ETag']
```

**Compliance**: HIPAA §164.312(c)(1) - Integrity

### 6. Person or Entity Authentication

#### AWS IAM Authentication

**Multi-Factor Authentication (MFA)**:
- Recommended for all users with console access
- Can be enforced via IAM policies
- Required for sensitive operations

**Role Assumption**:
```python
# Lambda functions assume IAM roles
# No credentials in code or environment variables
session = boto3.Session()
s3_client = session.client('s3')
```

**Compliance**: HIPAA §164.312(d) - Person or Entity Authentication

## Administrative Safeguards

### 1. Security Management Process

#### Risk Analysis

**Identified Risks**:
1. Unauthorized access to PHI
2. Data breach during transmission
3. Accidental PHI exposure
4. Data loss from deletion/corruption
5. Insufficient audit trails

**Mitigations**:
1. IAM role-based access control
2. End-to-end encryption (TLS/HTTPS)
3. Automated de-identification
4. S3 versioning and backups
5. Comprehensive CloudWatch logging

**Compliance**: HIPAA §164.308(a)(1)(ii)(A) - Risk Analysis

#### Security Incident Procedures

**Monitoring**:
- CloudWatch Alarms for failures
- Automatic notifications (can be configured with SNS)
- Log aggregation and analysis

**Incident Response Plan**:
1. **Detection**: CloudWatch Alarms
2. **Analysis**: Review logs in CloudWatch Insights
3. **Containment**: Disable compromised IAM roles
4. **Eradication**: Remove malicious code/access
5. **Recovery**: Restore from S3 versions
6. **Post-Incident**: Review and update security

**Compliance**: HIPAA §164.308(a)(6) - Security Incident Procedures

### 2. Assigned Security Responsibility

**Designated Security Official**:
- AWS account owner is responsible for compliance
- IAM users should be mapped to real individuals
- Principle of individual accountability

**Compliance**: HIPAA §164.308(a)(2) - Assigned Security Responsibility

### 3. Workforce Training

**Required Training**:
- HIPAA Privacy and Security Rules
- Proper handling of PHI
- Incident reporting procedures
- System-specific training for this pipeline

**Documentation**:
- Maintain training records
- Update training materials annually
- New employee orientation

**Compliance**: HIPAA §164.308(a)(5) - Security Awareness and Training

### 4. Contingency Plan

#### Data Backup

**S3 Versioning**:
- Automatic versioning of all objects
- Retrieve previous versions anytime
- Protection against accidental deletion

**Cross-Region Replication** (Optional):
```terraform
# Can be added for disaster recovery
resource "aws_s3_bucket_replication_configuration" "replication" {
  # Replicate to secondary region
}
```

**Compliance**: HIPAA §164.308(a)(7)(ii)(A) - Data Backup Plan

#### Disaster Recovery

**Infrastructure as Code**:
- Complete Terraform configuration
- Reproducible infrastructure
- Version controlled

**Recovery Procedure**:
1. Clone Terraform repository
2. Run `terraform apply` in new region
3. Restore data from S3 versions or backups
4. Update DNS/endpoints

**RTO/RPO Targets**:
- Recovery Time Objective (RTO): < 4 hours
- Recovery Point Objective (RPO): < 1 hour (S3 versioning)

**Compliance**: HIPAA §164.308(a)(7)(ii)(B) - Disaster Recovery Plan

## Physical Safeguards

### AWS Shared Responsibility Model

**AWS Responsibilities** (Physical):
- Data center physical security
- Hardware security
- Network infrastructure
- Environmental controls

**Customer Responsibilities** (Logical):
- Data encryption
- Access control (IAM)
- Network configuration
- Application security

**Compliance**: HIPAA §164.310 - Physical Safeguards

## Data Retention and Disposal

### Retention Policy

**Configurable Lifecycle**:
```terraform
resource "aws_s3_bucket_lifecycle_configuration" "processed" {
  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555  # 7 years (typical medical record retention)
    }
  }
}
```

**Retention Periods**:
- Active Storage: 90 days (STANDARD)
- Warm Archive: 90-180 days (STANDARD_IA)
- Cold Archive: 180+ days (GLACIER)
- Automatic Deletion: After 7 years (configurable)

**Compliance**: HIPAA §164.316(b)(2)(i) - Retention of Documentation

### Secure Disposal

**S3 Deletion**:
- S3 handles secure deletion automatically
- Multi-phase deletion process
- Cryptographic erasure of encryption keys

**Version Cleanup**:
```python
# Delete all versions of an object
s3_client.delete_objects(
    Bucket=bucket,
    Delete={'Objects': [...]}
)
```

**Compliance**: HIPAA §164.310(d)(2)(i) - Disposal

## Business Associate Agreements (BAA)

### AWS BAA

**AWS BAA Coverage**:
AWS offers a Business Associate Agreement covering:
- Amazon S3
- AWS Lambda
- AWS Step Functions
- Amazon CloudWatch
- AWS IAM

**Activation**:
1. Sign into AWS Organizations
2. Navigate to Artifact
3. Download and sign AWS BAA
4. AWS becomes a Business Associate

**Important**: Ensure AWS BAA is in place before processing PHI.

### Third-Party Services

**Current Services**:
- All processing happens within AWS
- No third-party PHI processors
- pydicom is a client library (no external calls)

**Future Integrations**:
- Ensure BAA with any third-party service
- Evaluate HIPAA compliance claims
- Review data handling practices

## Compliance Monitoring

### Regular Audits

**Quarterly Reviews**:
- Review IAM permissions
- Analyze CloudWatch logs
- Check encryption status
- Verify backup procedures
- Test disaster recovery

**Annual Reviews**:
- Full security risk assessment
- Penetration testing
- Compliance audit
- Update policies and procedures

### Continuous Monitoring

**CloudWatch Alarms**:
```terraform
resource "aws_cloudwatch_metric_alarm" "unauthorized_access" {
  alarm_name          = "UnauthorizedS3Access"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "4xxErrors"
  namespace           = "AWS/S3"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
}
```

**Log Analysis**:
```
# CloudWatch Logs Insights query
fields @timestamp, operation, status, details.error
| filter status = "failed" or status = "error"
| sort @timestamp desc
| limit 100
```

## Incident Response

### Security Incident Types

1. **Unauthorized Access Attempt**
   - Alert: CloudWatch Alarm
   - Response: Disable IAM role, review logs
   - Reporting: Document in incident log

2. **Data Breach**
   - Alert: Manual detection or automated
   - Response: Immediate containment, investigation
   - Reporting: Notify affected individuals (if required)

3. **System Compromise**
   - Alert: Unusual activity patterns
   - Response: Isolate system, forensic analysis
   - Reporting: Full incident report

### Breach Notification

**HIPAA Breach Notification Rule**:
- Notify affected individuals within 60 days
- Notify HHS if breach affects 500+ individuals
- Maintain breach log for all incidents

**Breach Threshold**:
- Low probability of PHI compromise (4-factor test)
- If threshold exceeded = breach notification required

## Compliance Checklist

### Pre-Deployment

- [ ] AWS BAA signed and active
- [ ] IAM roles follow least privilege
- [ ] S3 encryption enabled
- [ ] S3 public access blocked
- [ ] CloudWatch logging configured
- [ ] Log retention periods set
- [ ] Versioning enabled
- [ ] Lifecycle policies configured
- [ ] Terraform state encrypted

### Post-Deployment

- [ ] Verify encryption is active
- [ ] Test de-identification process
- [ ] Validate audit logging
- [ ] Test disaster recovery procedure
- [ ] Configure CloudWatch alarms
- [ ] Document security controls
- [ ] Train staff on HIPAA compliance
- [ ] Establish incident response plan

### Ongoing

- [ ] Quarterly security reviews
- [ ] Annual risk assessment
- [ ] Penetration testing (as needed)
- [ ] Update documentation
- [ ] Review and update training
- [ ] Monitor compliance alerts
- [ ] Maintain audit trail

## References

### HIPAA Regulations

- **45 CFR Part 160** - General Administrative Requirements
- **45 CFR Part 164, Subpart A** - General Provisions
- **45 CFR Part 164, Subpart C** - Security Rule
- **45 CFR Part 164, Subpart D** - Notification in Case of Breach
- **45 CFR Part 164, Subpart E** - Privacy of Individually Identifiable Health Information

### AWS Resources

- [AWS HIPAA Compliance](https://aws.amazon.com/compliance/hipaa-compliance/)
- [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/)
- [AWS BAA](https://aws.amazon.com/artifact/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)

### DICOM Standards

- [DICOM PS3.15](https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html) - Security and System Management Profiles
- [DICOM PS3.18](https://dicom.nema.org/medical/dicom/current/output/chtml/part18/chapter_B.html) - Web Services

## Disclaimer

This documentation provides guidance on HIPAA compliance implementation. It is not legal advice. Organizations should:

1. Consult with legal counsel
2. Conduct thorough risk assessments
3. Implement additional controls as needed
4. Maintain current with regulatory changes
5. Document all compliance efforts

HIPAA compliance is an ongoing process requiring continuous monitoring, assessment, and improvement.

---

**Last Updated**: 2024-01-01
**Next Review**: 2024-04-01
**Document Owner**: Security Team
