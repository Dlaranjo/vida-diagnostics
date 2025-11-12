"""
Validated DICOM parser with Pydantic schema validation.

Combines DICOM parsing with data validation for type-safe metadata handling.
"""

from pathlib import Path
from typing import Union

from pydicom.dataset import FileDataset
from pydantic import ValidationError

from src.ingestion.dicom_parser import DICOMParser
from src.utils.logger import get_logger, log_execution
from src.validation.schemas import (
    CTMetadataSchema,
    DICOMInstanceSchema,
    DICOMMetadataSchema,
    ImageMetadataSchema,
    MRMetadataSchema,
    PatientSchema,
    SeriesSchema,
    StudySchema,
)

logger = get_logger(__name__)


class ValidatedDICOMParser:
    """
    DICOM parser with automatic Pydantic validation.

    Extends DICOMParser to provide type-safe validated metadata objects.
    """

    def __init__(self) -> None:
        """Initialize validated parser."""
        self.parser = DICOMParser()

    def parse_and_validate(self, file_path: Union[str, Path]) -> DICOMMetadataSchema:
        """
        Parse DICOM file and validate metadata with Pydantic schemas.

        Args:
            file_path: Path to DICOM file

        Returns:
            Validated DICOMMetadataSchema object

        Raises:
            FileNotFoundError: If file doesn't exist
            pydicom.errors.InvalidDicomError: If file is not valid DICOM
            ValidationError: If metadata validation fails
        """
        log_execution(
            logger,
            operation="parse_and_validate",
            status="started",
            details={"file_path": str(file_path)},
        )

        try:
            # Parse DICOM file
            dataset = self.parser.read_dicom_file(file_path)

            # Extract and validate metadata
            validated_metadata = self.validate_dataset(dataset)

            log_execution(
                logger,
                operation="parse_and_validate",
                status="completed",
                details={
                    "file_path": str(file_path),
                    "patient_id": validated_metadata.patient.patient_id,
                    "modality": validated_metadata.series.modality,
                },
            )

            return validated_metadata

        except ValidationError as e:
            log_execution(
                logger,
                operation="parse_and_validate",
                status="failed",
                details={"file_path": str(file_path), "validation_errors": str(e)},
                error=e,
            )
            raise

        except Exception as e:
            log_execution(
                logger,
                operation="parse_and_validate",
                status="failed",
                details={"file_path": str(file_path)},
                error=e,
            )
            raise

    def validate_dataset(self, dataset: FileDataset) -> DICOMMetadataSchema:
        """
        Validate DICOM dataset with Pydantic schemas.

        Args:
            dataset: Parsed DICOM dataset

        Returns:
            Validated DICOMMetadataSchema object

        Raises:
            ValidationError: If validation fails
        """
        # Extract raw metadata
        metadata = self.parser.extract_metadata(dataset)

        # Build validated schemas
        patient = PatientSchema(
            patient_id=metadata.get("patient_id", ""),
            patient_sex=metadata.get("patient_sex"),
            patient_age=metadata.get("patient_age"),
        )

        study = StudySchema(
            study_instance_uid=metadata.get("study_instance_uid", ""),
            study_date=metadata.get("study_date"),
            study_time=metadata.get("study_time"),
            study_description=metadata.get("study_description"),
            accession_number=metadata.get("accession_number"),
        )

        series = SeriesSchema(
            series_instance_uid=metadata.get("series_instance_uid", ""),
            series_number=metadata.get("series_number"),
            series_description=metadata.get("series_description"),
            modality=metadata.get("modality", ""),
        )

        instance = DICOMInstanceSchema(
            sop_instance_uid=metadata.get("sop_instance_uid", ""),
            sop_class_uid=metadata.get("sop_class_uid", ""),
            instance_number=metadata.get("instance_number"),
        )

        # Build image metadata if present
        image = None
        if metadata.get("rows") is not None or metadata.get("columns") is not None:
            image = ImageMetadataSchema(
                rows=metadata.get("rows"),
                columns=metadata.get("columns"),
                bits_allocated=metadata.get("bits_allocated"),
                bits_stored=metadata.get("bits_stored"),
                pixel_spacing=metadata.get("pixel_spacing"),
            )

        # Build modality-specific metadata
        ct_metadata = None
        mr_metadata = None

        if metadata.get("modality") == "CT":
            # Only create CT metadata if at least one CT-specific field has a value
            if any(
                metadata.get(k) is not None
                for k in ["kvp", "slice_thickness", "reconstruction_diameter"]
            ):
                ct_metadata = CTMetadataSchema(
                    kvp=metadata.get("kvp"),
                    slice_thickness=metadata.get("slice_thickness"),
                    reconstruction_diameter=metadata.get("reconstruction_diameter"),
                )

        elif metadata.get("modality") == "MR":
            # Only create MR metadata if at least one MR-specific field has a value
            if any(
                metadata.get(k) is not None
                for k in ["repetition_time", "echo_time", "magnetic_field_strength"]
            ):
                mr_metadata = MRMetadataSchema(
                    repetition_time=metadata.get("repetition_time"),
                    echo_time=metadata.get("echo_time"),
                    magnetic_field_strength=metadata.get("magnetic_field_strength"),
                )

        # Combine into complete schema
        validated_metadata = DICOMMetadataSchema(
            patient=patient,
            study=study,
            series=series,
            instance=instance,
            image=image,
            ct_metadata=ct_metadata,
            mr_metadata=mr_metadata,
        )

        return validated_metadata

    def validate_metadata_dict(self, metadata: dict) -> DICOMMetadataSchema:
        """
        Validate metadata dictionary directly.

        Useful for validating metadata from other sources (CSV, JSON, etc.)

        Args:
            metadata: Dictionary with DICOM metadata

        Returns:
            Validated DICOMMetadataSchema object

        Raises:
            ValidationError: If validation fails
        """
        # Build schemas from dict
        patient = PatientSchema(
            patient_id=metadata.get("patient_id", ""),
            patient_sex=metadata.get("patient_sex"),
            patient_age=metadata.get("patient_age"),
        )

        study = StudySchema(
            study_instance_uid=metadata.get("study_instance_uid", ""),
            study_date=metadata.get("study_date"),
            study_time=metadata.get("study_time"),
            study_description=metadata.get("study_description"),
            accession_number=metadata.get("accession_number"),
        )

        series = SeriesSchema(
            series_instance_uid=metadata.get("series_instance_uid", ""),
            series_number=metadata.get("series_number"),
            series_description=metadata.get("series_description"),
            modality=metadata.get("modality", ""),
        )

        instance = DICOMInstanceSchema(
            sop_instance_uid=metadata.get("sop_instance_uid", ""),
            sop_class_uid=metadata.get("sop_class_uid", ""),
            instance_number=metadata.get("instance_number"),
        )

        # Build complete schema
        validated = DICOMMetadataSchema(
            patient=patient,
            study=study,
            series=series,
            instance=instance,
        )

        return validated
