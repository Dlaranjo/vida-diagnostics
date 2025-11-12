"""
Unit tests for DICOM parser module.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydicom.dataset import Dataset

from src.ingestion.dicom_parser import DICOMParser


@pytest.fixture
def sample_dicom_dataset() -> Dataset:
    """Create a sample DICOM dataset for testing."""
    ds = Dataset()

    # Patient information
    ds.PatientID = "TEST123"
    ds.PatientName = "Test^Patient"
    ds.PatientBirthDate = "19800101"
    ds.PatientSex = "M"

    # Study information
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9"
    ds.StudyDate = "20250101"
    ds.StudyTime = "120000"
    ds.StudyDescription = "Test Study"
    ds.AccessionNumber = "ACC123"

    # Series information
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.10"
    ds.SeriesNumber = "1"
    ds.SeriesDescription = "Test Series"
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
def dicom_parser() -> DICOMParser:
    """Create DICOMParser instance."""
    return DICOMParser()


class TestDICOMParser:
    """Test cases for DICOMParser class."""

    def test_initialization(self, dicom_parser: DICOMParser) -> None:
        """Test parser initialization."""
        assert dicom_parser is not None
        assert "CT" in dicom_parser.supported_modalities
        assert "MR" in dicom_parser.supported_modalities

    @patch("pydicom.dcmread")
    def test_read_dicom_file_success(
        self,
        mock_dcmread: Mock,
        dicom_parser: DICOMParser,
        sample_dicom_dataset: Dataset,
        tmp_path: Path,
    ) -> None:
        """Test successfully reading a DICOM file."""
        # Create temp file
        test_file = tmp_path / "test.dcm"
        test_file.touch()

        # Mock pydicom.dcmread
        mock_dcmread.return_value = sample_dicom_dataset

        # Read file
        result = dicom_parser.read_dicom_file(test_file)

        assert result == sample_dicom_dataset
        mock_dcmread.assert_called_once_with(str(test_file))

    def test_read_dicom_file_not_found(self, dicom_parser: DICOMParser) -> None:
        """Test reading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            dicom_parser.read_dicom_file("/nonexistent/file.dcm")

    def test_extract_metadata(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test metadata extraction from DICOM dataset."""
        metadata = dicom_parser.extract_metadata(sample_dicom_dataset)

        # Check patient info
        assert metadata["patient_id"] == "TEST123"
        assert metadata["patient_name"] == "Test^Patient"
        assert metadata["patient_sex"] == "M"

        # Check study info
        assert metadata["study_instance_uid"] == "1.2.3.4.5.6.7.8.9"
        assert metadata["study_date"] == "20250101"
        assert metadata["accession_number"] == "ACC123"

        # Check series info
        assert metadata["modality"] == "CT"
        assert metadata["series_number"] == "1"

        # Check image info
        assert metadata["rows"] == 512
        assert metadata["columns"] == 512

        # Check CT-specific
        assert metadata["kvp"] == 120
        assert metadata["slice_thickness"] == 5.0

    def test_validate_dicom_valid(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test validation of valid DICOM."""
        validation = dicom_parser.validate_dicom(sample_dicom_dataset)

        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0

    def test_validate_dicom_missing_required_tag(self, dicom_parser: DICOMParser) -> None:
        """Test validation fails with missing required tags."""
        ds = Dataset()
        ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9"
        # Missing SOPInstanceUID, SeriesInstanceUID, Modality

        validation = dicom_parser.validate_dicom(ds)

        assert validation["is_valid"] is False
        assert len(validation["errors"]) > 0
        assert any("SOPInstanceUID" in error for error in validation["errors"])

    def test_validate_dicom_unsupported_modality(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test validation warning for unsupported modality."""
        sample_dicom_dataset.Modality = "UNKNOWN"

        validation = dicom_parser.validate_dicom(sample_dicom_dataset)

        assert validation["is_valid"] is True  # Just a warning, not invalid
        assert len(validation["warnings"]) > 0
        assert any("not be fully supported" in warning for warning in validation["warnings"])

    def test_validate_dicom_small_dimensions(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test validation warning for small image dimensions."""
        sample_dicom_dataset.Rows = 32
        sample_dicom_dataset.Columns = 32

        validation = dicom_parser.validate_dicom(sample_dicom_dataset)

        assert validation["is_valid"] is True
        assert len(validation["warnings"]) > 0
        assert any("unusually small" in warning for warning in validation["warnings"])

    def test_extract_patient_identifiers(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test extraction of PHI tags."""
        phi_tags = dicom_parser.extract_patient_identifiers(sample_dicom_dataset)

        assert "PatientName" in phi_tags
        assert "PatientID" in phi_tags
        assert "PatientBirthDate" in phi_tags
        assert "StudyDate" in phi_tags

    def test_get_tag_value_existing(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test getting existing tag value."""
        value = dicom_parser._get_tag_value(sample_dicom_dataset, "PatientID")
        assert value == "TEST123"

    def test_get_tag_value_missing_with_default(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test getting missing tag returns default."""
        value = dicom_parser._get_tag_value(
            sample_dicom_dataset, "NonExistentTag", default="DEFAULT"
        )
        assert value == "DEFAULT"

    def test_get_dicom_summary(
        self, dicom_parser: DICOMParser, sample_dicom_dataset: Dataset
    ) -> None:
        """Test generating DICOM summary."""
        summary = dicom_parser.get_dicom_summary(sample_dicom_dataset)

        assert "DICOM File Summary" in summary
        assert "CT" in summary
        assert "1.2.3.4.5.6.7.8.9" in summary  # Study UID
        assert "512x512" in summary  # Dimensions
