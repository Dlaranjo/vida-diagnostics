"""
Unit tests for DICOM de-identification module.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydicom.dataset import Dataset

from src.ingestion.deidentifier import DICOMDeidentifier


@pytest.fixture
def sample_dicom_with_phi() -> Dataset:
    """Create a sample DICOM dataset with PHI for testing."""
    ds = Dataset()

    # PHI tags
    ds.PatientID = "PATIENT123"
    ds.PatientName = "Doe^John"
    ds.PatientBirthDate = "19750315"
    ds.PatientSex = "M"
    ds.PatientAge = "048Y"
    ds.PatientAddress = "123 Main St, City, State"
    ds.InstitutionName = "Test Hospital"
    ds.ReferringPhysicianName = "Dr. Smith"

    # Non-PHI but important
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9"
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.10"
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.11"
    ds.Modality = "CT"
    ds.StudyDate = "20230615"
    ds.StudyTime = "143000"
    ds.AccessionNumber = "ACC456"

    return ds


@pytest.fixture
def deidentifier() -> DICOMDeidentifier:
    """Create DICOMDeidentifier instance."""
    return DICOMDeidentifier(salt="test-salt", date_shift_days=100)


class TestDICOMDeidentifier:
    """Test cases for DICOMDeidentifier class."""

    def test_initialization(self) -> None:
        """Test deidentifier initialization."""
        deidentifier = DICOMDeidentifier()
        assert deidentifier is not None
        assert deidentifier.salt is not None

    def test_initialization_with_params(self) -> None:
        """Test deidentifier initialization with custom parameters."""
        deidentifier = DICOMDeidentifier(salt="custom-salt", date_shift_days=50)
        assert deidentifier.salt == "custom-salt"
        assert deidentifier.date_shift_days == 50

    def test_deidentify_dataset_removes_phi(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test that de-identification removes PHI tags."""
        result = deidentifier.deidentify_dataset(sample_dicom_with_phi)

        # PHI tags should be removed
        assert not hasattr(result, "PatientName")
        assert not hasattr(result, "PatientAddress")
        assert not hasattr(result, "InstitutionName")
        assert not hasattr(result, "ReferringPhysicianName")

    def test_deidentify_dataset_hashes_patient_id(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test that patient ID is hashed consistently."""
        original_id = sample_dicom_with_phi.PatientID
        result = deidentifier.deidentify_dataset(sample_dicom_with_phi)

        # Patient ID should exist but be different
        assert hasattr(result, "PatientID")
        assert result.PatientID != original_id
        assert len(result.PatientID) == 16  # Hash truncated to 16 chars

    def test_deidentify_dataset_patient_id_consistency(
        self, deidentifier: DICOMDeidentifier
    ) -> None:
        """Test that same patient ID always produces same hash."""
        ds1 = Dataset()
        ds1.PatientID = "PATIENT123"
        ds1.SOPInstanceUID = "1.2.3.4.5.6.7.8.1"
        ds1.StudyInstanceUID = "1.2.3.4.5"
        ds1.SeriesInstanceUID = "1.2.3.4.6"
        ds1.Modality = "CT"

        ds2 = Dataset()
        ds2.PatientID = "PATIENT123"
        ds2.SOPInstanceUID = "1.2.3.4.5.6.7.8.2"
        ds2.StudyInstanceUID = "1.2.3.4.5"
        ds2.SeriesInstanceUID = "1.2.3.4.6"
        ds2.Modality = "CT"

        result1 = deidentifier.deidentify_dataset(ds1)
        result2 = deidentifier.deidentify_dataset(ds2)

        # Same patient ID should hash to same value
        assert result1.PatientID == result2.PatientID

    def test_deidentify_dataset_shifts_dates(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test that dates are shifted consistently."""
        original_date = sample_dicom_with_phi.StudyDate
        result = deidentifier.deidentify_dataset(sample_dicom_with_phi)

        # Date should exist but be different
        assert hasattr(result, "StudyDate")
        assert result.StudyDate != original_date
        assert len(result.StudyDate) == 8  # YYYYMMDD format maintained

    def test_deidentify_dataset_handles_old_age(self, deidentifier: DICOMDeidentifier) -> None:
        """Test that ages >89 are set to 90+ per HIPAA."""
        ds = Dataset()
        ds.PatientID = "OLD_PATIENT"
        ds.PatientAge = "092Y"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.11"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.6"
        ds.Modality = "CT"

        result = deidentifier.deidentify_dataset(ds)

        assert result.PatientAge == "090Y"

    def test_deidentify_dataset_preserves_young_age(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test that ages <=89 are preserved."""
        result = deidentifier.deidentify_dataset(sample_dicom_with_phi)

        assert result.PatientAge == "048Y"  # Should remain unchanged

    def test_deidentify_dataset_preserves_non_phi(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test that non-PHI data is preserved."""
        result = deidentifier.deidentify_dataset(sample_dicom_with_phi)

        # Non-PHI should be preserved
        assert result.StudyInstanceUID == sample_dicom_with_phi.StudyInstanceUID
        assert result.SeriesInstanceUID == sample_dicom_with_phi.SeriesInstanceUID
        assert result.SOPInstanceUID == sample_dicom_with_phi.SOPInstanceUID
        assert result.Modality == sample_dicom_with_phi.Modality

    def test_deidentify_dataset_adds_marker(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test that de-identification marker is added."""
        result = deidentifier.deidentify_dataset(sample_dicom_with_phi)

        assert hasattr(result, "PatientIdentityRemoved")
        assert result.PatientIdentityRemoved == "YES"
        assert hasattr(result, "DeidentificationMethod")

    def test_deidentify_dataset_removes_private_tags(self, deidentifier: DICOMDeidentifier) -> None:
        """Test that private tags are removed when requested."""
        ds = Dataset()
        ds.PatientID = "TEST"
        ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.11"
        ds.StudyInstanceUID = "1.2.3.4.5"
        ds.SeriesInstanceUID = "1.2.3.4.6"
        ds.Modality = "CT"
        # Add a private tag
        ds.add_new((0x0009, 0x0010), "LO", "PRIVATE_CREATOR")
        ds.add_new((0x0009, 0x1001), "LO", "Private Data")

        result = deidentifier.deidentify_dataset(ds, remove_private_tags=True)

        # Private tags should be removed
        private_tags = [elem for elem in result if elem.tag.is_private]
        assert len(private_tags) == 0

    @patch("pydicom.dcmread")
    @patch.object(Dataset, "save_as")
    def test_deidentify_file(
        self,
        mock_save_as: Mock,
        mock_dcmread: Mock,
        deidentifier: DICOMDeidentifier,
        sample_dicom_with_phi: Dataset,
        tmp_path: Path,
    ) -> None:
        """Test de-identifying and saving a file."""
        input_path = tmp_path / "input.dcm"
        output_path = tmp_path / "output.dcm"
        input_path.touch()

        mock_dcmread.return_value = sample_dicom_with_phi

        deidentifier.deidentify_file(input_path, output_path)

        mock_dcmread.assert_called_once()
        mock_save_as.assert_called_once_with(str(output_path))

    def test_hash_value_consistency(self, deidentifier: DICOMDeidentifier) -> None:
        """Test that hashing produces consistent results."""
        value = "TEST_VALUE"

        hash1 = deidentifier._hash_value(value)
        hash2 = deidentifier._hash_value(value)

        assert hash1 == hash2

    def test_hash_value_different_for_different_inputs(
        self, deidentifier: DICOMDeidentifier
    ) -> None:
        """Test that different values produce different hashes."""
        hash1 = deidentifier._hash_value("VALUE1")
        hash2 = deidentifier._hash_value("VALUE2")

        assert hash1 != hash2

    def test_shift_date_valid(self, deidentifier: DICOMDeidentifier) -> None:
        """Test date shifting with valid date."""
        original = "20230615"  # June 15, 2023
        shifted = deidentifier._shift_date(original, 100)

        assert shifted is not None
        assert len(shifted) == 8
        assert shifted == "20230923"  # September 23, 2023

    def test_shift_date_invalid(self, deidentifier: DICOMDeidentifier) -> None:
        """Test date shifting with invalid date returns None."""
        result = deidentifier._shift_date("INVALID", 100)
        assert result is None

        result = deidentifier._shift_date("", 100)
        assert result is None

    def test_get_deidentification_report(
        self, deidentifier: DICOMDeidentifier, sample_dicom_with_phi: Dataset
    ) -> None:
        """Test generating de-identification report."""
        report = deidentifier.get_deidentification_report(sample_dicom_with_phi)

        assert "phi_tags_present" in report
        assert "tags_to_remove" in report
        assert "tags_to_hash" in report
        assert "tags_to_shift" in report

        # Should find PHI tags
        assert len(report["phi_tags_present"]) > 0
        assert "PatientName" in report["tags_to_remove"]
        assert "PatientID" in report["tags_to_hash"]
        assert "StudyDate" in report["tags_to_shift"]
