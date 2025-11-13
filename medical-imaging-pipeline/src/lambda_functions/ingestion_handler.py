"""
Lambda handler for DICOM file ingestion.
Triggered by S3 upload events.
"""

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.dicom_parser import DICOMParser
from ingestion.deidentifier import DICOMDeidentifier
from storage.s3_handler import S3Handler
from utils.logger import get_logger

logger = get_logger(__name__)


def lambda_handler(event, context):
    """
    Handle S3 upload event - complete DICOM processing pipeline.
    1. Download DICOM from raw bucket
    2. Parse and extract metadata
    3. De-identify PHI
    4. Upload to processed bucket

    Args:
        event: S3 event notification
        context: Lambda context

    Returns:
        dict: Processing result
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract S3 information from event
        if 'Records' not in event:
            raise ValueError("No Records in event")

        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        processed_bucket = os.environ.get('PROCESSED_BUCKET',
                                         'medical-imaging-pipeline-dev-processed-dicom')

        logger.info(f"Processing file: s3://{bucket}/{key}")

        # Initialize handlers
        s3_handler = S3Handler(bucket_name=bucket)
        parser = DICOMParser()
        deidentifier = DICOMDeidentifier()

        # Download file
        local_path = f"/tmp/{os.path.basename(key)}"
        s3_handler.download_file(key, local_path)
        logger.info(f"Downloaded to {local_path}")

        # Parse DICOM and extract metadata
        dcm = parser.read_dicom_file(local_path)
        metadata = parser.extract_metadata(dcm)
        logger.info(f"Extracted metadata: {metadata.get('patient_id')}")

        # De-identify
        deidentified_dcm = deidentifier.deidentify_dataset(dcm)
        logger.info("De-identification complete")

        # Save de-identified file
        output_path = f"/tmp/deidentified_{os.path.basename(key)}"
        deidentified_dcm.save_as(output_path, write_like_original=False)

        # Upload to processed bucket
        s3_processed = S3Handler(bucket_name=processed_bucket)
        output_key = f"processed/{os.path.basename(key)}"
        s3_processed.upload_file(output_path, output_key)
        logger.info(f"Uploaded to s3://{processed_bucket}/{output_key}")

        # Clean up
        os.remove(local_path)
        os.remove(output_path)

        result = {
            "status": "success",
            "input_bucket": bucket,
            "input_key": key,
            "output_bucket": processed_bucket,
            "output_key": output_key,
            "metadata": metadata
        }

        logger.info(f"Processing complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in processing: {str(e)}", exc_info=True)
        raise
