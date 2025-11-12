"""
DICOM de-identification module for removing PHI (Protected Health Information).

Implements HIPAA Safe Harbor method for de-identifying medical imaging data.
"""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Union

import pydicom
from pydicom.dataset import FileDataset

from utils.logger import get_logger, log_audit_event, log_execution

logger = get_logger(__name__)


class DICOMDeidentifier:
    """
    De-identifier for removing PHI from DICOM files per HIPAA requirements.

    Implements Safe Harbor de-identification method with option to maintain
    temporal relationships and unique identifiers through hashing.
    """

    # DICOM tags to remove completely (HIPAA Safe Harbor)
    REMOVE_TAGS = [
        "PatientName",
        "PatientBirthDate",
        "PatientAddress",
        "PatientTelephoneNumbers",
        "PatientMotherBirthName",
        "MilitaryRank",
        "BranchOfService",
        "MedicalRecordLocator",
        "InstitutionName",
        "InstitutionAddress",
        "InstitutionalDepartmentName",
        "ReferringPhysicianName",
        "ReferringPhysicianAddress",
        "ReferringPhysicianTelephoneNumbers",
        "PerformingPhysicianName",
        "NameOfPhysiciansReadingStudy",
        "OperatorsName",
        "RequestingPhysician",
        "StudyIDIssuer",
        "IssuerOfPatientID",
        "DeviceSerialNumber",
        "PlateID",
        "ProtocolName",
        "StationName",
        "OtherPatientIDs",
        "OtherPatientNames",
        "RegionOfResidence",
        "CurrentPatientLocation",
        "PatientInstitutionResidence",
    ]

    # Tags to hash (preserve uniqueness while removing identifying info)
    HASH_TAGS = [
        "PatientID",
        "AccessionNumber",
    ]

    # Tags to shift dates (preserve temporal relationships)
    DATE_TAGS = [
        "StudyDate",
        "SeriesDate",
        "AcquisitionDate",
        "ContentDate",
        "InstanceCreationDate",
    ]

    TIME_TAGS = [
        "StudyTime",
        "SeriesTime",
        "AcquisitionTime",
        "ContentTime",
        "InstanceCreationTime",
    ]

    def __init__(self, salt: Optional[str] = None, date_shift_days: Optional[int] = None) -> None:
        """
        Initialize de-identifier.

        Args:
            salt: Salt for hashing patient IDs (maintains consistency across studies)
            date_shift_days: Number of days to shift dates (negative or positive)
                           If None, a random shift is generated per patient
        """
        self.salt = salt or "medical-imaging-pipeline-default-salt"
        self.date_shift_days = date_shift_days
        self._patient_date_shifts: Dict[str, int] = {}

    def deidentify_dataset(
        self,
        dataset: FileDataset,
        remove_private_tags: bool = True,
        remove_pixel_data: bool = False,
    ) -> FileDataset:
        """
        De-identify a DICOM dataset by removing or anonymizing PHI.

        Args:
            dataset: DICOM dataset to de-identify
            remove_private_tags: Whether to remove private tags
            remove_pixel_data: Whether to remove pixel data (useful for metadata-only processing)

        Returns:
            De-identified DICOM dataset
        """
        log_execution(
            logger,
            operation="deidentify_dataset",
            status="started",
            details={
                "sop_instance_uid": str(dataset.get("SOPInstanceUID", "unknown")),
                "remove_private_tags": remove_private_tags,
                "remove_pixel_data": remove_pixel_data,
            },
        )

        try:
            # Get original patient ID for consistent hashing
            original_patient_id = str(dataset.get("PatientID", "unknown"))

            # Remove tags containing PHI
            for tag in self.REMOVE_TAGS:
                if tag in dataset:
                    delattr(dataset, tag)

            # Hash identifying tags
            for tag in self.HASH_TAGS:
                if tag in dataset:
                    original_value = str(dataset.get(tag))
                    hashed_value = self._hash_value(original_value)
                    setattr(dataset, tag, hashed_value)

            # Shift dates to preserve temporal relationships
            date_shift = self._get_date_shift(original_patient_id)
            for tag in self.DATE_TAGS:
                if tag in dataset:
                    original_date = str(dataset.get(tag))
                    shifted_date = self._shift_date(original_date, date_shift)
                    if shifted_date:
                        setattr(dataset, tag, shifted_date)

            # Age handling: if patient is >89, set to 90+ per HIPAA
            if "PatientAge" in dataset:
                age_str = str(dataset.PatientAge)
                if age_str.endswith("Y"):  # Format like "065Y"
                    age = int(age_str[:-1])
                    if age > 89:
                        dataset.PatientAge = "090Y"

            # Remove patient sex if required for higher privacy
            # (keeping it by default as it's often needed for analysis)

            # Remove private tags (vendor-specific)
            if remove_private_tags:
                dataset.remove_private_tags()

            # Remove pixel data if requested
            if remove_pixel_data and "PixelData" in dataset:
                delattr(dataset, "PixelData")

            # Add de-identification marker
            dataset.PatientIdentityRemoved = "YES"
            dataset.DeidentificationMethod = "HIPAA Safe Harbor with date shifting and ID hashing"

            log_audit_event(
                logger,
                event_type="phi_deidentification",
                user="deidentification-service",
                resource=f"DICOM:{dataset.get('SOPInstanceUID', 'unknown')}",
                action="deidentify",
                result="success",
                details={
                    "original_patient_id": original_patient_id,
                    "hashed_patient_id": dataset.get("PatientID", ""),
                    "date_shift_days": date_shift,
                    "private_tags_removed": remove_private_tags,
                },
            )

            log_execution(
                logger,
                operation="deidentify_dataset",
                status="completed",
                details={"sop_instance_uid": str(dataset.get("SOPInstanceUID", "unknown"))},
            )

            return dataset

        except Exception as e:
            log_execution(logger, operation="deidentify_dataset", status="failed", error=e)
            raise

    def deidentify_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        remove_private_tags: bool = True,
        remove_pixel_data: bool = False,
    ) -> None:
        """
        De-identify a DICOM file and save to new location.

        Args:
            input_path: Path to input DICOM file
            output_path: Path to save de-identified file
            remove_private_tags: Whether to remove private tags
            remove_pixel_data: Whether to remove pixel data
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Read DICOM file
        dataset = pydicom.dcmread(str(input_path))

        # De-identify
        deidentified_dataset = self.deidentify_dataset(
            dataset, remove_private_tags=remove_private_tags, remove_pixel_data=remove_pixel_data
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save de-identified file
        deidentified_dataset.save_as(str(output_path))

        logger.info(
            "De-identified DICOM saved",
            extra={
                "extra_fields": {
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                }
            },
        )

    def _hash_value(self, value: str) -> str:
        """
        Hash a value with salt for consistent anonymization.

        Args:
            value: Value to hash

        Returns:
            Hashed value as hex string
        """
        salted_value = f"{value}{self.salt}"
        hash_object = hashlib.sha256(salted_value.encode())
        return hash_object.hexdigest()[:16]  # Use first 16 chars for readability

    def _get_date_shift(self, patient_id: str) -> int:
        """
        Get consistent date shift for a patient.

        Args:
            patient_id: Original patient ID

        Returns:
            Number of days to shift (can be negative)
        """
        if self.date_shift_days is not None:
            return self.date_shift_days

        # Generate consistent shift per patient (but random across patients)
        if patient_id not in self._patient_date_shifts:
            # Use hash to generate consistent but pseudo-random shift (-365 to +365 days)
            hash_value = int(hashlib.md5(f"{patient_id}{self.salt}".encode()).hexdigest(), 16)
            shift = (hash_value % 730) - 365  # Range: -365 to +365
            self._patient_date_shifts[patient_id] = shift

        return self._patient_date_shifts[patient_id]

    def _shift_date(self, date_str: str, days: int) -> Optional[str]:
        """
        Shift a DICOM date string by specified number of days.

        Args:
            date_str: Date string in DICOM format (YYYYMMDD)
            days: Number of days to shift

        Returns:
            Shifted date string in same format, or None if parsing fails
        """
        try:
            if not date_str or len(date_str) != 8:
                return None

            # Parse DICOM date (YYYYMMDD)
            original_date = datetime.strptime(date_str, "%Y%m%d")

            # Shift date
            shifted_date = original_date + timedelta(days=days)

            # Return in DICOM format
            return shifted_date.strftime("%Y%m%d")

        except (ValueError, TypeError):
            return None

    def get_deidentification_report(self, dataset: FileDataset) -> Dict[str, any]:
        """
        Generate report of de-identification actions.

        Args:
            dataset: Original DICOM dataset (before de-identification)

        Returns:
            Dictionary with de-identification report
        """
        report = {
            "phi_tags_present": [],
            "tags_to_remove": [],
            "tags_to_hash": [],
            "tags_to_shift": [],
            "private_tags_count": 0,
        }

        # Check which PHI tags are present
        for tag in self.REMOVE_TAGS:
            if tag in dataset:
                report["phi_tags_present"].append(tag)
                report["tags_to_remove"].append(tag)

        for tag in self.HASH_TAGS:
            if tag in dataset:
                report["phi_tags_present"].append(tag)
                report["tags_to_hash"].append(tag)

        for tag in self.DATE_TAGS:
            if tag in dataset:
                report["phi_tags_present"].append(tag)
                report["tags_to_shift"].append(tag)

        # Count private tags
        for elem in dataset:
            if elem.tag.is_private:
                report["private_tags_count"] += 1

        report["total_phi_elements"] = len(report["phi_tags_present"])

        return report
