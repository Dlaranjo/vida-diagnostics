"""
Integration tests for validated DICOM parser.

Tests the integration between DICOM parsing and Pydantic validation.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydicom.dataset import Dataset
from pydantic import ValidationError

from src.ingestion.validated_parser import ValidatedDICOMParser
from src.validation.schemas import DICOMMetadataSchema


@pytest.fixture
def validated_parser() -> ValidatedDICOMParser:
    """Create ValidatedDICOMParser instance."""
    return ValidatedDICOMParser()


@pytest.fixture
def sample_ct_dataset() -> Dataset:
    """Create a sample CT DICOM dataset for testing."""
    ds = Dataset()

    # Patient information
    ds.PatientID = "TEST123"
    ds.PatientName = "Test^Patient"
    ds.PatientSex = "M"
    ds.PatientAge = "045Y"

    # Study information
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9"
    ds.StudyDate = "20250115"
    ds.StudyTime = "120000"
    ds.StudyDescription = "Test CT Study"
    ds.AccessionNumber = "ACC123"

    # Series information
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.10"
    ds.SeriesNumber = "1"
    ds.SeriesDescription = "Chest CT"
    ds.Modality = "CT"

    # Instance information
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.11"
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    ds.InstanceNumber = "1"

    # Image information
    ds.Rows = 512
    ds.Columns = 512
    ds.BitsAllocated = 16
    ds.BitsStored = 12

    # CT-specific
    ds.KVP = 120
    ds.SliceThickness = 5.0

    return ds


@pytest.fixture
def sample_mr_dataset() -> Dataset:
    """Create a sample MR DICOM dataset for testing."""
    ds = Dataset()

    # Patient information
    ds.PatientID = "TEST456"
    ds.PatientSex = "F"

    # Study information
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.20"
    ds.StudyDate = "20250116"

    # Series information
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.21"
    ds.Modality = "MR"

    # Instance information
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.22"
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.4"

    # Image information
    ds.Rows = 256
    ds.Columns = 256
    ds.BitsAllocated = 16
    ds.BitsStored = 16

    # MR-specific
    ds.RepetitionTime = 500
    ds.EchoTime = 20
    ds.MagneticFieldStrength = 1.5

    return ds


class TestValidatedDICOMParser:
    """Integration tests for ValidatedDICOMParser."""

    def test_initialization(self, validated_parser: ValidatedDICOMParser) -> None:
        """Test parser initialization."""
        assert validated_parser is not None
        assert validated_parser.parser is not None

    @patch("pydicom.dcmread")
    def test_parse_and_validate_ct_success(
        self,
        mock_dcmread: Mock,
        validated_parser: ValidatedDICOMParser,
        sample_ct_dataset: Dataset,
        tmp_path: Path,
    ) -> None:
        """Test successfully parsing and validating CT DICOM."""
        # Setup
        test_file = tmp_path / "test_ct.dcm"
        test_file.touch()
        mock_dcmread.return_value = sample_ct_dataset

        # Execute
        result = validated_parser.parse_and_validate(test_file)

        # Verify
        assert isinstance(result, DICOMMetadataSchema)
        assert result.patient.patient_id == "TEST123"
        assert result.patient.patient_sex == "M"
        assert result.study.study_instance_uid == "1.2.3.4.5.6.7.8.9"
        assert result.series.modality == "CT"
        assert result.ct_metadata is not None
        assert result.ct_metadata.kvp == 120
        assert result.mr_metadata is None

    @patch("pydicom.dcmread")
    def test_parse_and_validate_mr_success(
        self,
        mock_dcmread: Mock,
        validated_parser: ValidatedDICOMParser,
        sample_mr_dataset: Dataset,
        tmp_path: Path,
    ) -> None:
        """Test successfully parsing and validating MR DICOM."""
        # Setup
        test_file = tmp_path / "test_mr.dcm"
        test_file.touch()
        mock_dcmread.return_value = sample_mr_dataset

        # Execute
        result = validated_parser.parse_and_validate(test_file)

        # Verify
        assert isinstance(result, DICOMMetadataSchema)
        assert result.series.modality == "MR"
        assert result.mr_metadata is not None
        assert result.mr_metadata.repetition_time == 500
        assert result.mr_metadata.magnetic_field_strength == 1.5
        assert result.ct_metadata is None

    def test_validate_dataset_ct(
        self, validated_parser: ValidatedDICOMParser, sample_ct_dataset: Dataset
    ) -> None:
        """Test validating CT dataset directly."""
        result = validated_parser.validate_dataset(sample_ct_dataset)

        assert result.patient.patient_id == "TEST123"
        assert result.series.modality == "CT"
        assert result.image is not None
        assert result.image.rows == 512
        assert result.ct_metadata is not None

    def test_validate_dataset_mr(
        self, validated_parser: ValidatedDICOMParser, sample_mr_dataset: Dataset
    ) -> None:
        """Test validating MR dataset directly."""
        result = validated_parser.validate_dataset(sample_mr_dataset)

        assert result.patient.patient_id == "TEST456"
        assert result.series.modality == "MR"
        assert result.mr_metadata is not None

    def test_validate_dataset_invalid_uid_fails(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test validation fails with invalid UID."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.StudyInstanceUID = "invalid.uid.with.letters.abc"  # Invalid
        ds.SeriesInstanceUID = "1.2.3.4"
        ds.SOPInstanceUID = "1.2.3.4.5"
        ds.SOPClassUID = "1.2.840"
        ds.Modality = "CT"

        with pytest.raises(ValidationError) as exc_info:
            validated_parser.validate_dataset(ds)

        assert "must contain only digits and dots" in str(exc_info.value)

    def test_validate_dataset_missing_required_fields_fails(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test validation fails with missing required fields."""
        ds = Dataset()
        ds.PatientID = "TEST"
        # Missing StudyInstanceUID, SeriesInstanceUID, etc.

        with pytest.raises(ValidationError):
            validated_parser.validate_dataset(ds)

    def test_validate_dataset_invalid_patient_age_fails(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test validation fails with invalid patient age."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.PatientAge = "999Y"  # Exceeds max age
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.Modality = "CT"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7"
        ds.SOPClassUID = "1.2.840"

        with pytest.raises(ValidationError) as exc_info:
            validated_parser.validate_dataset(ds)

        assert "Age in years cannot exceed 150" in str(exc_info.value)

    def test_validate_metadata_dict_success(self, validated_parser: ValidatedDICOMParser) -> None:
        """Test validating metadata dictionary."""
        metadata = {
            "patient_id": "P001",
            "patient_sex": "M",
            "study_instance_uid": "1.2.3.4.5",
            "series_instance_uid": "1.2.3.4.5.6",
            "modality": "CT",
            "sop_instance_uid": "1.2.3.4.5.6.7",
            "sop_class_uid": "1.2.840",
        }

        result = validated_parser.validate_metadata_dict(metadata)

        assert result.patient.patient_id == "P001"
        assert result.series.modality == "CT"

    def test_validate_metadata_dict_invalid_fails(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test validation fails with invalid metadata dict."""
        metadata = {
            "patient_id": "P001",
            "study_instance_uid": "1.2.3.4.5",
            "series_instance_uid": "invalid-uid",  # Invalid
            "modality": "CT",
            "sop_instance_uid": "1.2.3.4.5.6.7",
            "sop_class_uid": "1.2.840",
        }

        with pytest.raises(ValidationError):
            validated_parser.validate_metadata_dict(metadata)

    def test_parse_nonexistent_file_fails(self, validated_parser: ValidatedDICOMParser) -> None:
        """Test parsing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            validated_parser.parse_and_validate("/nonexistent/file.dcm")

    def test_validate_dataset_without_image_data(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test validating dataset without image metadata."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.Modality = "CT"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7"
        ds.SOPClassUID = "1.2.840"
        # No Rows, Columns, etc.

        result = validated_parser.validate_dataset(ds)

        assert result.image is None

    def test_validate_dataset_ct_without_specific_metadata(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test CT dataset without CT-specific metadata."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.Modality = "CT"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7"
        ds.SOPClassUID = "1.2.840"
        # No KVP, SliceThickness, etc.

        result = validated_parser.validate_dataset(ds)

        assert result.ct_metadata is None

    def test_image_metadata_with_bits_validation(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test image metadata validates bits relationship."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.Modality = "CT"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7"
        ds.SOPClassUID = "1.2.840"
        ds.Rows = 512
        ds.Columns = 512
        ds.BitsAllocated = 16
        ds.BitsStored = 12  # Valid: <= BitsAllocated

        result = validated_parser.validate_dataset(ds)

        assert result.image.bits_allocated == 16
        assert result.image.bits_stored == 12

    def test_image_metadata_bits_invalid_relationship_fails(
        self, validated_parser: ValidatedDICOMParser
    ) -> None:
        """Test validation fails when bits_stored > bits_allocated."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.5.6"
        ds.Modality = "CT"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7"
        ds.SOPClassUID = "1.2.840"
        ds.Rows = 512
        ds.Columns = 512
        ds.BitsAllocated = 12
        ds.BitsStored = 16  # Invalid: > BitsAllocated

        with pytest.raises(ValidationError) as exc_info:
            validated_parser.validate_dataset(ds)

        assert "bits_stored cannot exceed bits_allocated" in str(exc_info.value)
