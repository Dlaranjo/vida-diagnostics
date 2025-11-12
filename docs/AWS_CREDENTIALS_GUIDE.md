# AWS Credentials Setup Guide

## Quick Reference

This guide explains **exactly** what AWS credentials you need to deploy the Medical Imaging Pipeline and how to obtain them.

---

## What You Need

To deploy this project to AWS, you need:

1. ✅ **AWS Account** (free to create, credit card required)
2. ✅ **IAM User** with deployment permissions
3. ✅ **Access Key ID** and **Secret Access Key**
4. ✅ **AWS CLI** configured with these credentials

---

## Step-by-Step Setup

### Step 1: Create AWS Account (if you don't have one)

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the registration steps:
   - Enter email address
   - Create password
   - Provide contact information
   - Enter payment information (required for verification, even for free tier)
4. Verify your identity (phone verification)
5. Select support plan (choose "Basic Support - Free")
6. Wait for account activation (usually instant, can take up to 24 hours)

**Cost**: Account creation is free. You only pay for resources you use (see cost estimates below).

### Step 2: Sign AWS Business Associate Agreement (HIPAA)

**REQUIRED for HIPAA compliance**:

1. Sign in to AWS Console: https://console.aws.amazon.com
2. Go to AWS Artifact: https://console.aws.amazon.com/artifact/
3. Click "Agreements" in left sidebar
4. Find "AWS Business Associate Addendum (BAA)"
5. Click "Review and Accept"
6. Read the agreement
7. Check the box to accept
8. Click "Accept Agreement"

**Note**: This is legally required before processing any PHI (Protected Health Information).

### Step 3: Create IAM User for Deployment

**Why**: Best practice - never use root account credentials.

1. Go to IAM Console: https://console.aws.amazon.com/iam/
2. Click "Users" in left sidebar
3. Click "Create user" button
4. Enter user details:
   - **User name**: `medical-imaging-deployer` (or any name you prefer)
   - **Provide user access to the AWS Management Console**: ❌ Uncheck (not needed)
5. Click "Next"

### Step 4: Attach Permissions

**Option A: Use AdministratorAccess** (Easiest for initial deployment)

1. Select "Attach policies directly"
2. Search for "AdministratorAccess"
3. Check the box next to "AdministratorAccess"
4. Click "Next"
5. Review and click "Create user"

**Option B: Use Minimum Required Permissions** (More secure)

1. Select "Attach policies directly"
2. Search and select these AWS managed policies:
   - `AmazonS3FullAccess`
   - `AWSLambda_FullAccess`
   - `AWSStepFunctionsFullAccess`
   - `IAMFullAccess`
   - `CloudWatchFullAccess`
3. Click "Next"
4. Click "Create user"

**Recommendation**: Use Option A for initial deployment, then create a custom least-privilege policy after understanding resource requirements.

### Step 5: Create Access Keys

This is the most important step - these are the credentials you'll use.

1. Click on the user you just created (`medical-imaging-deployer`)
2. Click the "Security credentials" tab
3. Scroll down to "Access keys" section
4. Click "Create access key"
5. Select use case: **"Command Line Interface (CLI)"**
6. Check the box: "I understand the above recommendation..."
7. Click "Next"
8. (Optional) Add description tag: "Medical Imaging Pipeline Deployment"
9. Click "Create access key"

**IMPORTANT**: You'll see two values:

```
Access key ID: AKIAIOSFODNN7EXAMPLE
Secret access key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**⚠️ CRITICAL**:
- Copy BOTH values immediately
- Store them securely (password manager recommended)
- You CANNOT see the secret key again after closing this window
- If you lose it, you'll need to create new keys

10. Click "Download .csv file" (RECOMMENDED)
11. Store the CSV file securely
12. Click "Done"

---

## Configuring Credentials

Now that you have your credentials, configure them for use:

### Option 1: AWS CLI Configuration (Recommended)

```bash
# Run this command
aws configure

# You'll be prompted for:
AWS Access Key ID [None]: PASTE_YOUR_ACCESS_KEY_ID_HERE
AWS Secret Access Key [None]: PASTE_YOUR_SECRET_KEY_HERE
Default region name [None]: us-east-1
Default output format [None]: json
```

**Example**:
```bash
aws configure

AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

**What this does**:
- Creates `~/.aws/credentials` file (Linux/macOS) or `C:\Users\USERNAME\.aws\credentials` (Windows)
- Stores your credentials securely
- Both AWS CLI and Terraform automatically use these credentials

**Verify it worked**:
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

If you see your account number and user ARN, **you're good to go!**

### Option 2: Environment Variables (Alternative)

Set credentials as environment variables:

**Linux/macOS**:
```bash
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="us-east-1"
```

**Windows PowerShell**:
```powershell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION="us-east-1"
```

**Windows CMD**:
```cmd
set AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
set AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
set AWS_DEFAULT_REGION=us-east-1
```

**Note**: Environment variables only last for the current terminal session.

---

## Verification

Before deploying, verify everything is set up correctly:

### 1. Check AWS CLI

```bash
aws --version
# Expected: aws-cli/2.x.x ...
```

### 2. Verify Credentials

```bash
aws sts get-caller-identity
```

Should show:
- Your account ID
- Your IAM user ARN
- User ID

### 3. Test S3 Access

```bash
aws s3 ls
```

Should list S3 buckets (may be empty if new account).

### 4. Test IAM Permissions

```bash
aws iam list-users
```

Should list IAM users (including the one you just created).

### 5. Check Region

```bash
aws configure get region
# Expected: us-east-1
```

If all commands work, **you're ready to deploy!**

---

## Deployment Command

Now you can deploy the infrastructure:

```bash
# Navigate to project
cd /path/to/medical-imaging-pipeline

# Go to terraform directory
cd terraform

# Deploy to dev environment
./scripts/deploy.sh dev
```

The deployment script will:
1. Build Lambda dependencies
2. Initialize Terraform
3. Create AWS resources
4. Display resource outputs

---

## Security Best Practices

### DO:

✅ **Store credentials securely**
- Use password manager
- Use AWS CLI credentials file
- Enable MFA on IAM user (recommended)

✅ **Rotate credentials regularly**
- Create new keys every 90 days
- Delete old keys

✅ **Use least privilege**
- Start with AdministratorAccess for testing
- Move to minimal permissions for production

✅ **Never commit to Git**
- Add `.aws/` to `.gitignore`
- Never put credentials in code

### DON'T:

❌ **Don't use root account**
- Always use IAM users

❌ **Don't share credentials**
- Each person should have own IAM user

❌ **Don't store in plaintext**
- Don't put in scripts or config files
- Don't send via email/chat

❌ **Don't hardcode in code**
```python
# ❌ NEVER DO THIS
aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"  # BAD!
aws_secret_access_key = "wJalr..."  # VERY BAD!

# ✅ DO THIS INSTEAD
session = boto3.Session()  # Automatically uses credentials file
s3_client = session.client('s3')
```

---

## Cost Estimates

### Free Tier (First 12 Months)

New AWS accounts get free tier:
- **Lambda**: 1 million requests/month
- **S3**: 5 GB storage, 20,000 GET requests, 2,000 PUT requests
- **CloudWatch**: 10 custom metrics, 1 million API requests
- **Step Functions**: 4,000 state transitions

### Expected Monthly Costs (Dev Environment)

After free tier or for production:

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 10,000 invocations | $0.20 |
| S3 | 10 GB storage | $0.23 |
| S3 | 10,000 requests | $0.05 |
| Step Functions | 1,000 executions | $0.03 |
| CloudWatch Logs | 5 GB | $2.50 |
| Data Transfer | 5 GB out | $0.45 |
| **Total** | | **~$3.50/month** |

### Expected Monthly Costs (Production)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 100,000 invocations | $2.00 |
| S3 | 100 GB storage | $2.30 |
| S3 | 100,000 requests | $0.50 |
| Step Functions | 10,000 executions | $0.25 |
| CloudWatch Logs | 20 GB | $10.00 |
| Data Transfer | 50 GB out | $4.50 |
| **Total** | | **~$20/month** |

**Note**: Actual costs depend on usage. Monitor with AWS Cost Explorer.

---

## Troubleshooting

### Issue: "Unable to locate credentials"

**Error**:
```
Error: No valid credential sources found for AWS Provider.
```

**Solution**:
```bash
# Run aws configure
aws configure

# Enter your credentials when prompted
```

### Issue: "Access Denied"

**Error**:
```
Error creating S3 bucket: AccessDenied
```

**Solution**:
- Verify IAM user has required permissions
- Check if MFA is required
- Try using AdministratorAccess policy temporarily

### Issue: "Invalid security token"

**Error**:
```
Error: ExpiredToken: The security token included in the request is expired
```

**Solution**:
- Credentials may be expired (if using temporary credentials)
- Run `aws configure` again with fresh keys
- Verify system clock is correct

### Issue: "Region not specified"

**Error**:
```
Error: region not specified
```

**Solution**:
```bash
# Set default region
aws configure set region us-east-1

# Or use environment variable
export AWS_DEFAULT_REGION=us-east-1
```

---

## Getting New Credentials

If you lost your secret access key or need to rotate:

1. Go to IAM Console: https://console.aws.amazon.com/iam/
2. Click "Users" → your user
3. "Security credentials" tab
4. Under "Access keys":
   - Click "Create access key"
   - Follow same process as before
5. After creating new key:
   - Run `aws configure` with new credentials
   - Delete old access key

---

## Summary Checklist

Before deploying, ensure you have:

- [ ] AWS account created
- [ ] AWS BAA signed (for HIPAA)
- [ ] IAM user created (`medical-imaging-deployer`)
- [ ] Permissions attached (AdministratorAccess or custom)
- [ ] Access keys created and saved
- [ ] AWS CLI installed
- [ ] Credentials configured (`aws configure`)
- [ ] Credentials verified (`aws sts get-caller-identity`)
- [ ] Ready to deploy (`./scripts/deploy.sh dev`)

---

## Quick Start Commands

```bash
# 1. Install AWS CLI (if not installed)
# macOS: brew install awscli
# Linux: See deployment guide
# Windows: Download installer

# 2. Configure credentials
aws configure
# Enter: Access Key ID, Secret Key, Region (us-east-1), Format (json)

# 3. Verify
aws sts get-caller-identity

# 4. Navigate to project
cd /path/to/medical-imaging-pipeline/terraform

# 5. Deploy
./scripts/deploy.sh dev

# 6. Done! Resources created in AWS
```

---

## Support

If you encounter issues:

1. **Check AWS Console**: https://console.aws.amazon.com
2. **Review IAM policies**: Ensure sufficient permissions
3. **Check CloudWatch logs**: For detailed error messages
4. **AWS Support**: https://console.aws.amazon.com/support/

---

**Ready to deploy?** Follow the [Deployment Guide](DEPLOYMENT.md) for detailed deployment instructions.
