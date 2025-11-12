"""
Lambda handler for DICOM validation.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validation.schemas import DICOMMetadata
from utils.logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event, context):
    """
    Validate DICOM metadata.

    Args:
        event: Contains metadata from ingestion
        context: Lambda context

    Returns:
        dict: Validation result
    """
    try:
        logger.info(f"Validating metadata: {json.dumps(event)}")

        metadata = event.get('metadata', {})

        # Validate using Pydantic schema
        validated = DICOMMetadata(**metadata)

        result = {
            "status": "valid",
            "metadata": validated.dict(),
            "bucket": event.get('bucket'),
            "key": event.get('key')
        }

        logger.info(f"Validation complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return {
            "status": "invalid",
            "error": str(e),
            "bucket": event.get('bucket'),
            "key": event.get('key')
        }
