# Medical Imaging Pipeline - Terraform Infrastructure

This directory contains Terraform Infrastructure as Code (IaC) for deploying the Medical Imaging DICOM processing pipeline to AWS.

## Architecture Overview

The infrastructure includes:

- **S3 Buckets**: Raw DICOM input, processed output, and access logs
- **Lambda Functions**: Ingestion, validation, and de-identification
- **Step Functions**: State machine orchestrating the processing workflow
- **IAM Roles**: Least-privilege access policies
- **CloudWatch**: Logging and monitoring with alarms
- **S3 Event Triggers**: Automatic pipeline invocation on file upload

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
   ```bash
   aws configure
   ```

2. **Terraform** >= 1.0
   ```bash
   # Install Terraform
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

3. **Python 3.12** for building Lambda layer
   ```bash
   python3 --version
   ```

4. **jq** for JSON processing (optional, for pretty output)
   ```bash
   brew install jq  # macOS
   ```

## Directory Structure

```
terraform/
├── main.tf                  # Main configuration
├── variables.tf             # Input variables
├── outputs.tf               # Output values
├── provider.tf              # AWS provider configuration
├── backend.tf               # Remote state configuration
├── terraform.tfvars.example # Example variables file
├── modules/                 # Terraform modules
│   ├── s3/                  # S3 buckets module
│   ├── lambda/              # Lambda functions module
│   ├── iam/                 # IAM roles module
│   ├── step_functions/      # Step Functions module
│   └── cloudwatch/          # CloudWatch module
├── environments/            # Environment-specific configs
│   ├── dev/
│   │   └── terraform.tfvars
│   └── prod/
│       └── terraform.tfvars
└── scripts/
    ├── build_lambda_layer.sh  # Build Lambda dependencies
    └── deploy.sh              # Automated deployment script
```

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Deploy to dev environment
cd terraform
./scripts/deploy.sh dev

# Deploy to prod environment
./scripts/deploy.sh prod
```

The deployment script will:
1. Build Lambda layer with dependencies
2. Initialize Terraform
3. Create/select workspace
4. Validate configuration
5. Create and show plan
6. Ask for confirmation
7. Apply configuration
8. Display outputs

### Option 2: Manual Deployment

#### Step 1: Configure Backend (Optional but Recommended)

Set up S3 backend for remote state:

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://medical-imaging-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket medical-imaging-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket medical-imaging-terraform-state \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name medical-imaging-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Update `backend.tf` with your bucket name:

```hcl
terraform {
  backend "s3" {
    bucket         = "medical-imaging-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "medical-imaging-terraform-locks"
    encrypt        = true
  }
}
```

#### Step 2: Build Lambda Layer

```bash
cd terraform
./scripts/build_lambda_layer.sh
```

This creates `lambda_layer.zip` with all Python dependencies.

#### Step 3: Configure Variables

```bash
# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your configuration
vim terraform.tfvars
```

Or use environment-specific configs:

```bash
# For dev
cp environments/dev/terraform.tfvars .

# For prod
cp environments/prod/terraform.tfvars .
```

#### Step 4: Initialize Terraform

```bash
terraform init
```

#### Step 5: Plan Deployment

```bash
# Using default terraform.tfvars
terraform plan -out=tfplan

# Or using environment-specific file
terraform plan -var-file="environments/dev/terraform.tfvars" -out=tfplan
```

#### Step 6: Apply Configuration

```bash
terraform apply tfplan
```

#### Step 7: Verify Deployment

```bash
# View outputs
terraform output

# View deployment summary
terraform output deployment_summary
```

## Configuration Variables

### Core Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_name` | Project name for resource naming | `medical-imaging-pipeline` | No |
| `environment` | Environment (dev/prod) | `dev` | No |
| `aws_region` | AWS region | `us-east-1` | No |

### S3 Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `raw_bucket_name` | Raw DICOM files bucket | Auto-generated |
| `processed_bucket_name` | Processed files bucket | Auto-generated |
| `logs_bucket_name` | Logs bucket | Auto-generated |
| `s3_bucket_lifecycle_days` | Days before transitioning to IA | `90` |
| `enable_s3_encryption` | Enable S3 encryption | `true` |

### Lambda Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `lambda_runtime` | Python runtime version | `python3.12` |
| `lambda_timeout` | Function timeout (seconds) | `300` |
| `lambda_memory_size` | Function memory (MB) | `512` |

### CloudWatch Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `log_retention_days` | Log retention period | `30` |

## Testing the Deployment

### 1. Upload a Test DICOM File

```bash
# Get bucket name
RAW_BUCKET=$(terraform output -raw raw_bucket_name)

# Upload test file
aws s3 cp test.dcm s3://$RAW_BUCKET/
```

### 2. Monitor Step Functions Execution

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(terraform output -raw state_machine_arn)

# List executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN

# Describe specific execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

### 3. View Lambda Logs

```bash
# Get function name
INGESTION_FUNCTION=$(terraform output -raw ingestion_function_name)

# Tail logs
aws logs tail /aws/lambda/$INGESTION_FUNCTION --follow
```

### 4. Check Processed Files

```bash
# Get processed bucket name
PROCESSED_BUCKET=$(terraform output -raw processed_bucket_name)

# List processed files
aws s3 ls s3://$PROCESSED_BUCKET/ --recursive
```

### 5. Generate Presigned URL for Download

```python
import boto3
from src.delivery.presigned_url_handler import PresignedUrlHandler

# Initialize handler
handler = PresignedUrlHandler(
    bucket_name="<processed-bucket-name>",
    region_name="us-east-1"
)

# Generate secure download URL
url_info = handler.generate_secure_download_url(
    object_key="path/to/processed/file.dcm",
    expiration_seconds=3600,
    validate_exists=True
)

print(f"Download URL: {url_info['url']}")
```

## Outputs

After deployment, Terraform provides these outputs:

- `raw_bucket_name`: Name of the raw DICOM files bucket
- `processed_bucket_name`: Name of the processed files bucket
- `logs_bucket_name`: Name of the logs bucket
- `ingestion_function_name`: Ingestion Lambda function name
- `validation_function_name`: Validation Lambda function name
- `deidentification_function_name`: Deidentification Lambda function name
- `state_machine_name`: Step Functions state machine name
- `state_machine_arn`: Step Functions state machine ARN
- `lambda_execution_role_arn`: Lambda execution role ARN
- `step_functions_execution_role_arn`: Step Functions execution role ARN
- `deployment_summary`: Complete deployment summary

## Environment Management

### Workspaces

Use Terraform workspaces for environment isolation:

```bash
# Create new workspace
terraform workspace new prod

# List workspaces
terraform workspace list

# Switch workspace
terraform workspace select dev

# Show current workspace
terraform workspace show
```

### Multi-Environment Deployment

```bash
# Deploy dev
terraform workspace select dev
terraform apply -var-file="environments/dev/terraform.tfvars"

# Deploy prod
terraform workspace select prod
terraform apply -var-file="environments/prod/terraform.tfvars"
```

## Security Best Practices

1. **Enable S3 Encryption**: All buckets use AES-256 encryption by default
2. **Block Public Access**: All S3 buckets block public access
3. **Least Privilege IAM**: Roles have minimal required permissions
4. **VPC Configuration**: Lambda functions can be deployed in VPC (set `enable_lambda_vpc = true`)
5. **CloudWatch Logging**: All services log to CloudWatch with configurable retention
6. **Versioning**: S3 buckets have versioning enabled
7. **Lifecycle Policies**: Automatic transition to cheaper storage classes

## Cost Optimization

### Development Environment

- Smaller Lambda memory (`256 MB`)
- Shorter log retention (`7 days`)
- Faster lifecycle transitions (`30 days`)

### Production Environment

- Adequate Lambda memory (`512 MB`)
- Longer log retention (`30+ days`)
- Standard lifecycle transitions (`90 days`)

### Estimated Monthly Costs (Dev)

- Lambda: ~$5-10 (low usage)
- S3: ~$5-20 (depends on storage)
- Step Functions: ~$1-5
- CloudWatch: ~$1-5
- **Total**: ~$15-40/month

## Troubleshooting

### Issue: Lambda Layer Too Large

**Error**: `InvalidParameterValueException: Unzipped size must be smaller than 262144000 bytes`

**Solution**: Optimize layer by removing unnecessary files

```bash
# Manually rebuild layer with optimization
cd terraform/scripts
./build_lambda_layer.sh
```

### Issue: State Lock Timeout

**Error**: `Error acquiring the state lock`

**Solution**: Force unlock (use with caution)

```bash
terraform force-unlock <lock-id>
```

### Issue: Permission Denied

**Error**: `AccessDenied` when creating resources

**Solution**: Ensure AWS credentials have sufficient permissions

```bash
# Check current identity
aws sts get-caller-identity

# Required IAM permissions:
# - s3:*
# - lambda:*
# - states:*
# - iam:*
# - logs:*
# - cloudwatch:*
```

## Cleanup

### Destroy Infrastructure

```bash
# Destroy specific environment
terraform workspace select dev
terraform destroy

# Or use automated script
./scripts/destroy.sh dev  # (if created)
```

### Manual Cleanup

```bash
# Empty S3 buckets first
aws s3 rm s3://<bucket-name> --recursive

# Then destroy
terraform destroy
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ['terraform/**']

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Terraform Init
        run: terraform init
        working-directory: terraform

      - name: Terraform Plan
        run: terraform plan -var-file="environments/dev/terraform.tfvars"
        working-directory: terraform

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve -var-file="environments/dev/terraform.tfvars"
        working-directory: terraform
```

## Support

For issues or questions:
- Check the main project README
- Review CloudWatch logs
- Check Step Functions execution history
- Review IAM permissions

## References

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [Project Vision Document](../PROJECT_VISION.md)
