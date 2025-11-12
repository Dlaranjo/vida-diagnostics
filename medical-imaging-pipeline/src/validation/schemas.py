"""
Pydantic schemas for data validation.

Provides type-safe data models for DICOM metadata, study information,
and delivery packages with comprehensive validation rules.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from utils.logger import get_logger

logger = get_logger(__name__)


class PatientSchema(BaseModel):
    """Schema for patient information (de-identified)."""

    patient_id: str = Field(..., min_length=1, max_length=64, description="Hashed patient ID")
    patient_sex: Optional[str] = Field(None, pattern="^[MFO]$", description="Patient sex")
    patient_age: Optional[str] = Field(
        None, pattern="^\\d{3}[DWMY]$", description="Patient age in DICOM format"
    )

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, v: str) -> str:
        """Validate patient ID is not empty or whitespace."""
        if not v or v.isspace():
            raise ValueError("Patient ID cannot be empty or whitespace")
        return v.strip()

    @field_validator("patient_age")
    @classmethod
    def validate_age_range(cls, v: Optional[str]) -> Optional[str]:
        """Validate age is within reasonable range."""
        if v is None:
            return v

        # Extract numeric part
        age_num = int(v[:3])
        age_unit = v[3]

        # Validate ranges based on unit
        if age_unit == "Y" and age_num > 150:
            raise ValueError("Age in years cannot exceed 150")
        elif age_unit == "M" and age_num > 1800:  # ~150 years
            raise ValueError("Age in months cannot exceed 1800")
        elif age_unit == "W" and age_num > 7800:  # ~150 years
            raise ValueError("Age in weeks cannot exceed 7800")
        elif age_unit == "D" and age_num > 54750:  # ~150 years
            raise ValueError("Age in days cannot exceed 54750")

        return v


class StudySchema(BaseModel):
    """Schema for DICOM study information."""

    study_instance_uid: str = Field(..., min_length=1, description="Unique study identifier")
    study_date: Optional[str] = Field(None, pattern="^\\d{8}$", description="Study date YYYYMMDD")
    study_time: Optional[str] = Field(
        None, pattern="^\\d{6}(\\.\\d{1,6})?$", description="Study time HHMMSS"
    )
    study_description: Optional[str] = Field(None, max_length=64)
    accession_number: Optional[str] = Field(None, max_length=16)

    @field_validator("study_instance_uid")
    @classmethod
    def validate_uid_format(cls, v: str) -> str:
        """Validate UID follows DICOM format (numeric components separated by dots)."""
        if not re.match(r"^[\d\.]+$", v):
            raise ValueError("Study UID must contain only digits and dots")
        if v.startswith(".") or v.endswith(".") or ".." in v:
            raise ValueError("Study UID has invalid dot placement")
        return v

    @field_validator("study_date")
    @classmethod
    def validate_study_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate study date is a valid date."""
        if v is None:
            return v

        try:
            datetime.strptime(v, "%Y%m%d")
        except ValueError:
            raise ValueError(f"Invalid study date format: {v}")

        return v


class SeriesSchema(BaseModel):
    """Schema for DICOM series information."""

    series_instance_uid: str = Field(..., min_length=1, description="Unique series identifier")
    series_number: Optional[int] = Field(None, ge=0, le=99999, description="Series number")
    series_description: Optional[str] = Field(None, max_length=64)
    modality: str = Field(..., min_length=2, max_length=16, description="Imaging modality")

    @field_validator("series_instance_uid")
    @classmethod
    def validate_uid_format(cls, v: str) -> str:
        """Validate UID follows DICOM format."""
        if not re.match(r"^[\d\.]+$", v):
            raise ValueError("Series UID must contain only digits and dots")
        if v.startswith(".") or v.endswith(".") or ".." in v:
            raise ValueError("Series UID has invalid dot placement")
        return v

    @field_validator("modality")
    @classmethod
    def validate_modality(cls, v: str) -> str:
        """Validate modality is uppercase."""
        return v.upper()


class ImageMetadataSchema(BaseModel):
    """Schema for image-specific metadata."""

    rows: Optional[int] = Field(None, ge=1, le=65535, description="Image height in pixels")
    columns: Optional[int] = Field(None, ge=1, le=65535, description="Image width in pixels")
    bits_allocated: Optional[int] = Field(None, ge=1, le=64, description="Bits allocated per pixel")
    bits_stored: Optional[int] = Field(None, ge=1, le=64, description="Bits stored per pixel")
    pixel_spacing: Optional[List[float]] = Field(None, description="Pixel spacing [row, column]")

    @field_validator("pixel_spacing")
    @classmethod
    def validate_pixel_spacing(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate pixel spacing has exactly 2 elements."""
        if v is not None and len(v) != 2:
            raise ValueError("Pixel spacing must have exactly 2 elements [row, column]")
        return v

    @model_validator(mode="after")
    def validate_bits_relationship(self) -> "ImageMetadataSchema":
        """Validate bits_stored <= bits_allocated."""
        if (
            self.bits_allocated is not None
            and self.bits_stored is not None
            and self.bits_stored > self.bits_allocated
        ):
            raise ValueError("bits_stored cannot exceed bits_allocated")
        return self


class CTMetadataSchema(BaseModel):
    """Schema for CT-specific metadata."""

    kvp: Optional[float] = Field(None, ge=0, le=200, description="kVp (kilovoltage peak)")
    slice_thickness: Optional[float] = Field(None, ge=0, description="Slice thickness in mm")
    reconstruction_diameter: Optional[float] = Field(None, ge=0, description="Reconstruction FOV")


class MRMetadataSchema(BaseModel):
    """Schema for MR-specific metadata."""

    repetition_time: Optional[float] = Field(None, ge=0, description="TR in ms")
    echo_time: Optional[float] = Field(None, ge=0, description="TE in ms")
    magnetic_field_strength: Optional[float] = Field(
        None, ge=0, le=20, description="Field strength in Tesla"
    )


class DICOMInstanceSchema(BaseModel):
    """Schema for complete DICOM instance metadata."""

    sop_instance_uid: str = Field(..., min_length=1, description="SOP Instance UID")
    sop_class_uid: str = Field(..., min_length=1, description="SOP Class UID")
    instance_number: Optional[int] = Field(None, ge=0, description="Instance number")

    @field_validator("sop_instance_uid", "sop_class_uid")
    @classmethod
    def validate_uid_format(cls, v: str) -> str:
        """Validate UID follows DICOM format."""
        if not re.match(r"^[\d\.]+$", v):
            raise ValueError("UID must contain only digits and dots")
        if v.startswith(".") or v.endswith(".") or ".." in v:
            raise ValueError("UID has invalid dot placement")
        return v


class DICOMMetadataSchema(BaseModel):
    """Complete DICOM metadata schema combining all components."""

    patient: PatientSchema
    study: StudySchema
    series: SeriesSchema
    instance: DICOMInstanceSchema
    image: Optional[ImageMetadataSchema] = None
    ct_metadata: Optional[CTMetadataSchema] = None
    mr_metadata: Optional[MRMetadataSchema] = None

    @model_validator(mode="after")
    def validate_modality_specific_metadata(self) -> "DICOMMetadataSchema":
        """Ensure modality-specific metadata matches the modality."""
        modality = self.series.modality

        if modality == "CT" and self.mr_metadata is not None:
            raise ValueError("CT modality should not have MR metadata")
        if modality == "MR" and self.ct_metadata is not None:
            raise ValueError("MR modality should not have CT metadata")

        return self


class CSVRecordSchema(BaseModel):
    """Schema for validating CSV metadata records."""

    patient_id: str = Field(..., min_length=1)
    study_date: str = Field(..., pattern="^\\d{4}-\\d{2}-\\d{2}$")
    modality: str = Field(..., min_length=2)
    accession_number: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|completed|failed)$")

    @field_validator("study_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is valid."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {v}")
        return v


class DeliveryFileSchema(BaseModel):
    """Schema for a file in delivery package."""

    file_path: str = Field(..., min_length=1)
    file_size: int = Field(..., ge=0, description="File size in bytes")
    checksum: str = Field(..., min_length=32, max_length=64, description="File checksum")
    presigned_url: Optional[str] = Field(None, description="S3 presigned URL")
    url_expiration: Optional[str] = Field(None, description="URL expiration timestamp")


class DeliveryManifestSchema(BaseModel):
    """Schema for delivery manifest containing multiple files."""

    manifest_id: str = Field(..., min_length=1)
    created_at: str = Field(..., description="ISO 8601 timestamp")
    patient_id: str = Field(..., min_length=1)
    study_instance_uid: str = Field(..., min_length=1)
    total_files: int = Field(..., ge=0)
    total_size_bytes: int = Field(..., ge=0)
    files: List[DeliveryFileSchema] = Field(..., min_length=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO 8601 timestamp."""
        # Check for ISO 8601 format with regex first
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
        if not re.match(iso_pattern, v):
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")
        return v

    @model_validator(mode="after")
    def validate_file_count(self) -> "DeliveryManifestSchema":
        """Ensure total_files matches actual file count."""
        if len(self.files) != self.total_files:
            raise ValueError(
                f"total_files ({self.total_files}) does not match "
                f"actual file count ({len(self.files)})"
            )
        return self
