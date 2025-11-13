"""
Lambda handler for DICOM de-identification.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.dicom_parser import DICOMParser
from ingestion.deidentifier import Deidentifier
from storage.s3_handler import S3Handler
from utils.logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event, context):
    """
    De-identify DICOM file and save to processed bucket.

    Args:
        event: Contains bucket and key from validation
        context: Lambda context

    Returns:
        dict: Processing result
    """
    try:
        logger.info(f"De-identifying file: {json.dumps(event)}")

        bucket = event.get('bucket')
        key = event.get('key')
        processed_bucket = os.environ.get('PROCESSED_BUCKET')

        # Initialize handlers
        s3_handler = S3Handler(bucket_name=bucket)
        parser = DICOMParser()
        deidentifier = Deidentifier()

        # Download file
        local_path = f"/tmp/{os.path.basename(key)}"
        s3_handler.download_file(key, local_path)

        # Parse and de-identify
        dcm = parser.parse(local_path)
        deidentified_dcm = deidentifier.deidentify(dcm)

        # Save de-identified file
        output_path = f"/tmp/deidentified_{os.path.basename(key)}"
        deidentified_dcm.save_as(output_path, write_like_original=False)

        # Upload to processed bucket
        s3_processed = S3Handler(bucket_name=processed_bucket)
        output_key = f"processed/{os.path.basename(key)}"
        s3_processed.upload_file(output_path, output_key)

        # Clean up
        os.remove(local_path)
        os.remove(output_path)

        result = {
            "status": "success",
            "input_bucket": bucket,
            "input_key": key,
            "output_bucket": processed_bucket,
            "output_key": output_key
        }

        logger.info(f"De-identification complete: {result}")
        return result

    except Exception as e:
        logger.error(f"De-identification error: {str(e)}", exc_info=True)
        raise
