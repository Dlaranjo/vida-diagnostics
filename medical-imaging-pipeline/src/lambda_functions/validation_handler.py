"""
Lambda handler for DICOM validation.
"""
import os
from orchestration.lambda_handlers import ValidationHandler

# Initialize handler with environment variables
handler = ValidationHandler(
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    enable_cloudwatch=True
)


def lambda_handler(event, context):
    """
    AWS Lambda entry point for DICOM validation.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Validation result
    """
    return handler.handle(event, context)

