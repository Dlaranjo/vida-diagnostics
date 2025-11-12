"""
Lambda handler for DICOM deidentification.
"""
import os
from orchestration.lambda_handlers import DeidentificationHandler

# Initialize handler with environment variables
handler = DeidentificationHandler(
    output_bucket=os.environ.get('PROCESSED_BUCKET', ''),
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    enable_cloudwatch=True
)


def lambda_handler(event, context):
    """
    AWS Lambda entry point for DICOM deidentification.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Deidentification result
    """
    return handler.handle(event, context)

