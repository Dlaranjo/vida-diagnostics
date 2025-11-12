# Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Medical Imaging Pipeline to AWS, including AWS credentials setup, infrastructure deployment, and verification procedures.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [AWS Credentials Configuration](#aws-credentials-configuration)
4. [Infrastructure Deployment](#infrastructure-deployment)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Cleanup](#cleanup)

---

## Prerequisites

### Required Software

1. **AWS CLI** (v2.x or higher)
   ```bash
   # Install AWS CLI
   # macOS
   brew install awscli

   # Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # Windows
   # Download installer from https://aws.amazon.com/cli/

   # Verify installation
   aws --version
   # Expected: aws-cli/2.x.x
   ```

2. **Terraform** (>= 1.0)
   ```bash
   # macOS
   brew install terraform

   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/

   # Windows
   choco install terraform

   # Verify installation
   terraform --version
   # Expected: Terraform v1.x.x
   ```

3. **Python 3.12+**
   ```bash
   python3 --version
   # Expected: Python 3.12.x
   ```

4. **jq** (Optional, for JSON processing)
   ```bash
   # macOS
   brew install jq

   # Linux
   sudo apt-get install jq

   # Windows
   choco install jq
   ```

---

## AWS Account Setup

### Step 1: Create AWS Account

If you don't have an AWS account:

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Follow the registration process
4. Provide payment information (required even for free tier)

### Step 2: Sign AWS BAA (HIPAA Compliance)

**IMPORTANT**: For HIPAA compliance, you must sign AWS Business Associate Agreement.

1. Sign in to AWS Console
2. Navigate to AWS Artifact
   - https://console.aws.amazon.com/artifact/
3. Go to "Agreements"
4. Find "AWS Business Associate Addendum (BAA)"
5. Click "Accept Agreement"
6. Review and accept terms

**Note**: This is required before processing any PHI/DICOM files.

### Step 3: Create IAM User for Deployment

**Why**: Never use root account credentials. Create a dedicated IAM user for deployment.

1. Go to IAM Console: https://console.aws.amazon.com/iam/
2. Click "Users" → "Create user"
3. User name: `medical-imaging-deployer`
4. Click "Next"

### Step 4: Attach Permissions

The deployment user needs these permissions:

**Option A: AWS Managed Policies** (Easier, broader permissions)
- `AdministratorAccess` (for initial deployment)

**Option B: Custom Policy** (More secure, least privilege)

Create a custom policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "lambda:*",
        "states:*",
        "iam:*",
        "logs:*",
        "cloudwatch:*",
        "events:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Recommended for production**: Start with AdministratorAccess for initial deployment, then create a least-privilege policy based on actual resources created.

### Step 5: Create Access Keys

1. Go to user details: `medical-imaging-deployer`
2. Click "Security credentials" tab
3. Scroll to "Access keys"
4. Click "Create access key"
5. Choose "Command Line Interface (CLI)"
6. Check "I understand..." checkbox
7. Click "Next" → "Create access key"
8. **Important**: Copy both values:
   - **Access Key ID**: `AKIAIOSFODNN7EXAMPLE`
   - **Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

**Security Note**:
- Never commit these credentials to Git
- Store them securely (password manager)
- You won't be able to see the secret key again

---

## AWS Credentials Configuration

You need to provide your AWS credentials to the deployment tools. There are three methods:

### Method 1: AWS CLI Configuration (Recommended)

This is the easiest and most secure method.

```bash
# Run AWS configure command
aws configure

# You'll be prompted for:
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

**What this does**:
- Creates `~/.aws/credentials` file with your keys
- Creates `~/.aws/config` file with settings
- Both Terraform and AWS CLI will automatically use these credentials

**Verify configuration**:
```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/medical-imaging-deployer"
}
```

### Method 2: Environment Variables

Set credentials as environment variables (temporary, for single session):

```bash
# Linux/macOS
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"

# Windows PowerShell
$env:AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
$env:AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
$env:AWS_DEFAULT_REGION="us-east-1"

# Windows CMD
set AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
set AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
set AWS_DEFAULT_REGION=us-east-1
```

**Verify**:
```bash
aws sts get-caller-identity
```

### Method 3: AWS Named Profiles

For multiple AWS accounts/users:

```bash
# Configure named profile
aws configure --profile medical-imaging

# Use profile in commands
aws s3 ls --profile medical-imaging
terraform apply -var="aws_profile=medical-imaging"
```

---

## Infrastructure Deployment

### Option 1: Automated Deployment (Recommended)

The easiest way to deploy:

```bash
# Navigate to terraform directory
cd terraform

# Deploy to dev environment
./scripts/deploy.sh dev

# Or deploy to prod environment
./scripts/deploy.sh prod
```

The script will:
1. ✅ Build Lambda dependencies layer
2. ✅ Initialize Terraform
3. ✅ Select/create workspace
4. ✅ Validate configuration
5. ✅ Create deployment plan
6. ✅ Show plan for review
7. ❓ Ask for confirmation
8. ✅ Apply infrastructure
9. ✅ Display outputs

**Example output**:
```
[INFO] Deploying Medical Imaging Pipeline to dev environment...
[INFO] Step 1: Building Lambda layer...
Lambda layer built successfully!
Location: /path/to/lambda_layer.zip
Size: 25M

[INFO] Step 2: Initializing Terraform...
Terraform has been successfully initialized!

[INFO] Step 3: Selecting workspace: dev...
Switched to workspace "dev".

[INFO] Step 4: Validating Terraform configuration...
Success! The configuration is valid.

[INFO] Step 5: Checking Terraform formatting...
Terraform files are properly formatted.

[INFO] Step 6: Creating Terraform plan...
Plan: 24 to add, 0 to change, 0 to destroy.

[WARNING] Review the plan above. Do you want to apply these changes? (yes/no)
yes

[INFO] Step 7: Applying Terraform configuration...
Apply complete! Resources: 24 added, 0 changed, 0 destroyed.

[INFO] Step 8: Deployment completed! Here are the outputs:
{
  "raw_bucket_name": "medical-imaging-pipeline-dev-raw-dicom",
  "processed_bucket_name": "medical-imaging-pipeline-dev-processed-dicom",
  "state_machine_arn": "arn:aws:states:us-east-1:...",
  ...
}

[INFO] Done!
```

### Option 2: Manual Deployment

For more control over the deployment process:

#### Step 1: Build Lambda Layer

```bash
cd terraform
./scripts/build_lambda_layer.sh
```

This creates `lambda_layer.zip` with all Python dependencies (~25-50 MB).

#### Step 2: Configure Variables

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your settings
vim terraform.tfvars
```

**Or** use environment-specific config:
```bash
# For dev
cp environments/dev/terraform.tfvars .

# For prod
cp environments/prod/terraform.tfvars .
```

**Key variables to review**:
```hcl
project_name = "medical-imaging-pipeline"
environment  = "dev"
aws_region   = "us-east-1"

# Lambda configuration
lambda_memory_size = 512  # MB
lambda_timeout     = 300  # seconds

# Log retention
log_retention_days = 30  # days

# Security
enable_s3_encryption = true
```

#### Step 3: Initialize Terraform

```bash
terraform init
```

Expected output:
```
Initializing the backend...
Initializing modules...
Initializing provider plugins...

Terraform has been successfully initialized!
```

#### Step 4: Plan Deployment

```bash
# Create execution plan
terraform plan -out=tfplan

# Review the plan
# Look for:
# - Resources to be created
# - Any unexpected changes
# - Estimated costs (if using cost estimation)
```

Expected output:
```
Plan: 24 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + raw_bucket_name        = "medical-imaging-pipeline-dev-raw-dicom"
  + processed_bucket_name  = "medical-imaging-pipeline-dev-processed-dicom"
  + state_machine_arn      = (known after apply)
  ...
```

#### Step 5: Apply Configuration

```bash
# Apply the plan
terraform apply tfplan

# This will create:
# - 3 S3 buckets
# - 3 Lambda functions
# - 1 Lambda layer
# - 1 Step Functions state machine
# - IAM roles and policies
# - CloudWatch log groups
# - CloudWatch alarms
```

**Deployment time**: ~5-10 minutes

#### Step 6: Verify Outputs

```bash
# View all outputs
terraform output

# View specific output
terraform output raw_bucket_name
terraform output state_machine_arn

# View as JSON
terraform output -json > outputs.json
```

---

## Verification

### 1. Verify AWS Resources Created

#### Check S3 Buckets

```bash
# List buckets
aws s3 ls | grep medical-imaging

# Expected:
# medical-imaging-pipeline-dev-raw-dicom
# medical-imaging-pipeline-dev-processed-dicom
# medical-imaging-pipeline-dev-logs
```

#### Check Lambda Functions

```bash
# List functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `medical-imaging`)].FunctionName'

# Expected:
# [
#   "medical-imaging-pipeline-ingestion",
#   "medical-imaging-pipeline-validation",
#   "medical-imaging-pipeline-deidentification"
# ]
```

#### Check Step Functions

```bash
# Get state machine ARN
STATE_MACHINE=$(terraform output -raw state_machine_arn)

# Describe state machine
aws stepfunctions describe-state-machine --state-machine-arn $STATE_MACHINE

# Check status
aws stepfunctions list-state-machines --query 'stateMachines[?name==`dicom-processing-workflow-dev`]'
```

### 2. Test Pipeline

#### Upload Test DICOM File

```bash
# Get bucket name
RAW_BUCKET=$(terraform output -raw raw_bucket_name)

# Create test DICOM file (if you have one)
# Or download sample: https://barre.dev/medical/samples/

# Upload
aws s3 cp sample.dcm s3://$RAW_BUCKET/test/sample.dcm

# Expected: Upload successful
```

#### Monitor Step Functions Execution

```bash
# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE \
  --max-results 10

# Get execution ARN from output
EXECUTION_ARN="arn:aws:states:us-east-1:..."

# Describe execution
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN

# Check status
# Status should be: RUNNING → SUCCEEDED
```

#### Check Lambda Logs

```bash
# Get function name
INGESTION_FUNCTION=$(terraform output -raw ingestion_function_name)

# Tail logs
aws logs tail /aws/lambda/$INGESTION_FUNCTION --follow

# Or view recent logs
aws logs tail /aws/lambda/$INGESTION_FUNCTION --since 10m
```

#### Verify Processed File

```bash
# Get processed bucket
PROCESSED_BUCKET=$(terraform output -raw processed_bucket_name)

# List processed files
aws s3 ls s3://$PROCESSED_BUCKET/ --recursive

# Download and verify
aws s3 cp s3://$PROCESSED_BUCKET/test/sample.dcm /tmp/processed.dcm

# Check de-identification (using Python)
python3 << EOF
import pydicom
ds = pydicom.dcmread('/tmp/processed.dcm')
print(f"Patient ID: {ds.get('PatientID', 'REMOVED')}")
print(f"Patient Name: {ds.get('PatientName', 'REMOVED')}")
# Should show anonymous values
EOF
```

### 3. Test Presigned URL Generation

```python
from src.delivery.presigned_url_handler import PresignedUrlHandler

# Initialize handler
handler = PresignedUrlHandler(
    bucket_name="YOUR-PROCESSED-BUCKET-NAME",
    region_name="us-east-1"
)

# Generate URL
url_info = handler.generate_secure_download_url(
    object_key="test/sample.dcm",
    expiration_seconds=3600,
    validate_exists=True
)

if url_info:
    print(f"Download URL: {url_info['url']}")
    print(f"Expires in: {url_info['expires_in']} seconds")
else:
    print("File not found")

# Test download
import requests
response = requests.get(url_info['url'])
if response.status_code == 200:
    print(f"Successfully downloaded {len(response.content)} bytes")
```

---

## Troubleshooting

### Issue: AWS Credentials Not Found

**Error**:
```
Error: No valid credential sources found for AWS Provider.
```

**Solutions**:
1. Run `aws configure` to set up credentials
2. Verify with `aws sts get-caller-identity`
3. Check environment variables are set
4. Ensure credentials file exists: `~/.aws/credentials`

### Issue: Insufficient Permissions

**Error**:
```
Error: Error creating S3 bucket: AccessDenied: Access Denied
```

**Solutions**:
1. Check IAM user has necessary permissions
2. Verify AWS BAA is signed (for HIPAA)
3. Add required policies to IAM user
4. Use `AdministratorAccess` for testing (not recommended for production)

### Issue: Lambda Layer Too Large

**Error**:
```
Error: InvalidParameterValueException: Unzipped size must be smaller than 262144000 bytes
```

**Solutions**:
1. Rebuild layer with optimization:
   ```bash
   ./scripts/build_lambda_layer.sh
   ```
2. Check layer size: `ls -lh lambda_layer.zip`
3. Remove unnecessary dependencies from `requirements.txt`
4. Use Lambda container images for very large dependencies

### Issue: Terraform State Lock

**Error**:
```
Error: Error acquiring the state lock
```

**Solutions**:
1. Wait for other operations to complete
2. Force unlock (use with caution):
   ```bash
   terraform force-unlock <LOCK_ID>
   ```
3. Check DynamoDB lock table (if using remote backend)

### Issue: Resource Already Exists

**Error**:
```
Error: Error creating S3 bucket: BucketAlreadyExists
```

**Solutions**:
1. Bucket names must be globally unique
2. Change `raw_bucket_name` in `terraform.tfvars`
3. Or let Terraform auto-generate names (leave empty)

### Issue: Lambda Timeout

**Error**: Lambda execution times out after 300 seconds

**Solutions**:
1. Increase timeout in `terraform/variables.tf`:
   ```hcl
   variable "lambda_timeout" {
     default = 600  # 10 minutes
   }
   ```
2. Optimize code for performance
3. Check if file size is too large (>250MB)

### Issue: Step Functions Execution Failed

**Solutions**:
1. Check execution details:
   ```bash
   aws stepfunctions describe-execution --execution-arn $EXECUTION_ARN
   ```
2. Review CloudWatch logs for specific Lambda function
3. Check error message in Step Functions console
4. Verify input data format matches expected schema

---

## Cleanup

### Destroy Infrastructure

When you're done testing or want to remove all resources:

```bash
cd terraform

# Using automated script (recommended)
./scripts/destroy.sh dev

# Or manual destruction
terraform destroy

# Confirm by typing: yes
```

**What gets deleted**:
- All Lambda functions
- Lambda layer
- Step Functions state machine
- IAM roles and policies
- CloudWatch log groups
- CloudWatch alarms
- S3 buckets (must be empty first)

**Important**:
- S3 buckets must be empty before Terraform can delete them
- The destroy script automatically empties buckets
- If manual, empty buckets first:
  ```bash
  aws s3 rm s3://bucket-name --recursive
  ```

### Complete Cleanup

To remove all traces:

```bash
# 1. Delete Terraform state bucket (if using remote backend)
aws s3 rb s3://medical-imaging-terraform-state --force

# 2. Delete DynamoDB lock table
aws dynamodb delete-table --table-name medical-imaging-terraform-locks

# 3. Delete CloudWatch log groups (if retained)
aws logs delete-log-group --log-group-name /aws/lambda/medical-imaging-pipeline-ingestion
aws logs delete-log-group --log-group-name /aws/lambda/medical-imaging-pipeline-validation
aws logs delete-log-group --log-group-name /aws/lambda/medical-imaging-pipeline-deidentification
aws logs delete-log-group --log-group-name /aws/stepfunctions/dicom-processing-workflow-dev

# 4. Delete IAM user (if no longer needed)
# Go to IAM Console and delete medical-imaging-deployer user
```

---

## Production Deployment Checklist

Before deploying to production:

### Security
- [ ] AWS BAA signed and active
- [ ] IAM user has least-privilege permissions
- [ ] MFA enabled for console access
- [ ] S3 encryption enabled
- [ ] S3 public access blocked
- [ ] VPC configuration (if required)
- [ ] CloudTrail logging enabled

### Configuration
- [ ] Use `prod` environment variables
- [ ] Increase Lambda memory/timeout if needed
- [ ] Set appropriate log retention (30+ days)
- [ ] Configure longer S3 lifecycle (180+ days)
- [ ] Enable S3 versioning
- [ ] Set up backup strategy

### Monitoring
- [ ] CloudWatch alarms configured
- [ ] SNS notifications set up
- [ ] Log aggregation configured
- [ ] Cost monitoring enabled
- [ ] Performance baselines established

### Compliance
- [ ] HIPAA compliance reviewed
- [ ] Security controls documented
- [ ] Incident response plan ready
- [ ] Staff trained on HIPAA
- [ ] Audit logging verified

### Testing
- [ ] End-to-end test completed
- [ ] Load testing performed
- [ ] Disaster recovery tested
- [ ] Backup/restore verified
- [ ] Rollback plan ready

---

## Next Steps

After successful deployment:

1. **Configure Monitoring**:
   - Set up CloudWatch dashboards
   - Configure SNS alerts
   - Integrate with monitoring tools

2. **Set Up CI/CD**:
   - GitHub Actions for automated deployments
   - Automated testing pipeline
   - Infrastructure drift detection

3. **Implement Additional Features**:
   - API Gateway for REST API
   - SQS for buffering
   - DynamoDB for metadata index
   - SNS for notifications

4. **Optimize Costs**:
   - Review Lambda memory allocation
   - Adjust S3 lifecycle policies
   - Use Reserved Concurrency if needed
   - Enable S3 Intelligent-Tiering

5. **Enhance Security**:
   - Implement KMS encryption
   - Add WAF rules (if using API Gateway)
   - Set up GuardDuty
   - Enable Security Hub

---

## Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/
- **Project Documentation**: See `docs/` directory
- **AWS Support**: https://console.aws.amazon.com/support/

For issues or questions specific to this project, refer to:
- [Architecture Documentation](ARCHITECTURE.md)
- [API Documentation](API.md)
- [Compliance Documentation](COMPLIANCE.md)
- [User Guide](USER_GUIDE.md)
