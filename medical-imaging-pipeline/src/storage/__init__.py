"""
AWS storage integration for DICOM files.

Handles S3 operations including upload, download, and presigned URL generation.
"""

from src.storage.s3_handler import S3Handler

__all__ = ["S3Handler"]
