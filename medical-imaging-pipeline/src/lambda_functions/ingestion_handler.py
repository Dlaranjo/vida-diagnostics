"""
Lambda handler for DICOM ingestion.
"""
import os
from orchestration.lambda_handlers import IngestionHandler

# Initialize handler with environment variables
handler = IngestionHandler(
    output_bucket=os.environ.get('PROCESSED_BUCKET', ''),
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    enable_cloudwatch=True
)


def lambda_handler(event, context):
    """
    AWS Lambda entry point for DICOM ingestion.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Processing result
    """
    return handler.handle(event, context)

