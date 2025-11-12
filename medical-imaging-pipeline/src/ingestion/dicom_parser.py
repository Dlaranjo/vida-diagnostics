"""
DICOM file parsing and metadata extraction.

Handles reading and parsing medical imaging DICOM files using pydicom library.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

import pydicom
from pydicom.dataset import FileDataset

from utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class DICOMParser:
    """
    Parser for DICOM medical imaging files.

    Handles reading DICOM files, extracting metadata, and validating format.
    """

    def __init__(self) -> None:
        """Initialize DICOM parser."""
        self.supported_modalities = {"CT", "MR", "CR", "DX", "XA", "PT", "NM", "US"}

    def read_dicom_file(self, file_path: Union[str, Path]) -> FileDataset:
        """
        Read a DICOM file from disk.

        Args:
            file_path: Path to DICOM file

        Returns:
            Parsed DICOM dataset

        Raises:
            FileNotFoundError: If file doesn't exist
            pydicom.errors.InvalidDicomError: If file is not valid DICOM
        """
        log_execution(
            logger,
            operation="read_dicom_file",
            status="started",
            details={"file_path": str(file_path)},
        )

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"DICOM file not found: {file_path}")

            # Read DICOM file
            dataset = pydicom.dcmread(str(file_path))

            log_execution(
                logger,
                operation="read_dicom_file",
                status="completed",
                details={
                    "file_path": str(file_path),
                    "sop_instance_uid": str(dataset.SOPInstanceUID),
                },
            )

            return dataset

        except Exception as e:
            log_execution(
                logger,
                operation="read_dicom_file",
                status="failed",
                details={"file_path": str(file_path)},
                error=e,
            )
            raise

    def extract_metadata(self, dataset: FileDataset) -> Dict[str, Any]:
        """
        Extract key metadata from DICOM dataset.

        Args:
            dataset: Parsed DICOM dataset

        Returns:
            Dictionary of extracted metadata
        """
        metadata: Dict[str, Any] = {}

        # Patient information (will be de-identified later)
        metadata["patient_id"] = self._get_tag_value(dataset, "PatientID")
        metadata["patient_name"] = str(self._get_tag_value(dataset, "PatientName", ""))
        metadata["patient_birth_date"] = self._get_tag_value(dataset, "PatientBirthDate")
        metadata["patient_sex"] = self._get_tag_value(dataset, "PatientSex")
        metadata["patient_age"] = self._get_tag_value(dataset, "PatientAge")

        # Study information
        metadata["study_instance_uid"] = str(self._get_tag_value(dataset, "StudyInstanceUID"))
        metadata["study_date"] = self._get_tag_value(dataset, "StudyDate")
        metadata["study_time"] = self._get_tag_value(dataset, "StudyTime")
        metadata["study_description"] = self._get_tag_value(dataset, "StudyDescription")
        metadata["accession_number"] = self._get_tag_value(dataset, "AccessionNumber")

        # Series information
        metadata["series_instance_uid"] = str(self._get_tag_value(dataset, "SeriesInstanceUID"))
        metadata["series_number"] = self._get_tag_value(dataset, "SeriesNumber")
        metadata["series_description"] = self._get_tag_value(dataset, "SeriesDescription")
        metadata["modality"] = self._get_tag_value(dataset, "Modality")

        # Instance information
        metadata["sop_instance_uid"] = str(self._get_tag_value(dataset, "SOPInstanceUID"))
        metadata["sop_class_uid"] = str(self._get_tag_value(dataset, "SOPClassUID"))
        metadata["instance_number"] = self._get_tag_value(dataset, "InstanceNumber")

        # Image information
        metadata["rows"] = self._get_tag_value(dataset, "Rows")
        metadata["columns"] = self._get_tag_value(dataset, "Columns")
        metadata["bits_allocated"] = self._get_tag_value(dataset, "BitsAllocated")
        metadata["bits_stored"] = self._get_tag_value(dataset, "BitsStored")
        metadata["pixel_spacing"] = self._get_tag_value(dataset, "PixelSpacing")

        # Imaging parameters (modality-specific)
        if metadata["modality"] == "CT":
            metadata["kvp"] = self._get_tag_value(dataset, "KVP")
            metadata["slice_thickness"] = self._get_tag_value(dataset, "SliceThickness")
            metadata["reconstruction_diameter"] = self._get_tag_value(
                dataset, "ReconstructionDiameter"
            )

        elif metadata["modality"] == "MR":
            metadata["repetition_time"] = self._get_tag_value(dataset, "RepetitionTime")
            metadata["echo_time"] = self._get_tag_value(dataset, "EchoTime")
            metadata["magnetic_field_strength"] = self._get_tag_value(
                dataset, "MagneticFieldStrength"
            )

        return metadata

    def validate_dicom(self, dataset: FileDataset) -> Dict[str, Any]:
        """
        Validate DICOM dataset for completeness and quality.

        Args:
            dataset: Parsed DICOM dataset

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        }

        # Check required tags
        required_tags = [
            "SOPInstanceUID",
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "Modality",
        ]

        for tag in required_tags:
            if not hasattr(dataset, tag):
                validation_results["is_valid"] = False
                validation_results["errors"].append(f"Missing required tag: {tag}")

        # Check modality support
        modality = self._get_tag_value(dataset, "Modality")
        if modality and modality not in self.supported_modalities:
            validation_results["warnings"].append(
                f"Modality '{modality}' may not be fully supported"
            )

        # Check image dimensions
        rows = self._get_tag_value(dataset, "Rows")
        columns = self._get_tag_value(dataset, "Columns")

        if rows and columns:
            if rows < 64 or columns < 64:
                validation_results["warnings"].append(
                    f"Image dimensions ({rows}x{columns}) are unusually small"
                )
        else:
            validation_results["warnings"].append("Image dimensions not found")

        # Check pixel data presence
        if not hasattr(dataset, "PixelData"):
            validation_results["warnings"].append("No pixel data found")

        return validation_results

    def extract_patient_identifiers(self, dataset: FileDataset) -> List[str]:
        """
        Extract all DICOM tags that contain PHI (Protected Health Information).

        Args:
            dataset: Parsed DICOM dataset

        Returns:
            List of tag names containing PHI
        """
        # DICOM tags that typically contain PHI
        phi_tags = [
            "PatientName",
            "PatientID",
            "PatientBirthDate",
            "PatientSex",
            "PatientAge",
            "PatientAddress",
            "PatientTelephoneNumbers",
            "InstitutionName",
            "InstitutionAddress",
            "ReferringPhysicianName",
            "PerformingPhysicianName",
            "OperatorName",
            "StudyDate",
            "StudyTime",
            "SeriesDate",
            "SeriesTime",
            "AcquisitionDate",
            "AcquisitionTime",
            "ContentDate",
            "ContentTime",
        ]

        present_phi_tags = []
        for tag in phi_tags:
            if hasattr(dataset, tag):
                value = getattr(dataset, tag)
                if value not in [None, "", []]:
                    present_phi_tags.append(tag)

        return present_phi_tags

    def _get_tag_value(self, dataset: FileDataset, tag_name: str, default: Any = None) -> Any:
        """
        Safely get DICOM tag value with default fallback.

        Args:
            dataset: DICOM dataset
            tag_name: Name of DICOM tag
            default: Default value if tag not found

        Returns:
            Tag value or default
        """
        try:
            if hasattr(dataset, tag_name):
                value = getattr(dataset, tag_name)
                # Convert to Python types
                if hasattr(value, "value"):
                    return value.value
                return value
            return default
        except Exception:
            return default

    def get_dicom_summary(self, dataset: FileDataset) -> str:
        """
        Get human-readable summary of DICOM file.

        Args:
            dataset: Parsed DICOM dataset

        Returns:
            Summary string
        """
        metadata = self.extract_metadata(dataset)
        validation = self.validate_dicom(dataset)

        summary_lines = [
            "DICOM File Summary",
            "=" * 50,
            f"Modality: {metadata.get('modality', 'Unknown')}",
            f"Study UID: {metadata.get('study_instance_uid', 'Unknown')}",
            f"Series UID: {metadata.get('series_instance_uid', 'Unknown')}",
            f"SOP Instance UID: {metadata.get('sop_instance_uid', 'Unknown')}",
            f"Dimensions: {metadata.get('rows', '?')}x{metadata.get('columns', '?')}",
            f"Valid: {'Yes' if validation['is_valid'] else 'No'}",
        ]

        if validation["errors"]:
            summary_lines.append("\nErrors:")
            for error in validation["errors"]:
                summary_lines.append(f"  - {error}")

        if validation["warnings"]:
            summary_lines.append("\nWarnings:")
            for warning in validation["warnings"]:
                summary_lines.append(f"  - {warning}")

        return "\n".join(summary_lines)
