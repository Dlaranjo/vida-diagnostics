"""
Unit tests for Pydantic validation schemas.
"""

import pytest
from pydantic import ValidationError

from src.validation.schemas import (
    CTMetadataSchema,
    CSVRecordSchema,
    DICOMInstanceSchema,
    DICOMMetadataSchema,
    DeliveryFileSchema,
    DeliveryManifestSchema,
    ImageMetadataSchema,
    MRMetadataSchema,
    PatientSchema,
    SeriesSchema,
    StudySchema,
)


class TestPatientSchema:
    """Test cases for PatientSchema."""

    def test_valid_patient(self) -> None:
        """Test creating valid patient schema."""
        patient = PatientSchema(patient_id="abc123", patient_sex="M", patient_age="045Y")

        assert patient.patient_id == "abc123"
        assert patient.patient_sex == "M"
        assert patient.patient_age == "045Y"

    def test_patient_id_strip_whitespace(self) -> None:
        """Test patient ID whitespace is stripped."""
        patient = PatientSchema(patient_id="  abc123  ")
        assert patient.patient_id == "abc123"

    def test_patient_id_empty_fails(self) -> None:
        """Test empty patient ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PatientSchema(patient_id="")

        assert "patient_id" in str(exc_info.value)

    def test_patient_id_whitespace_only_fails(self) -> None:
        """Test whitespace-only patient ID raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PatientSchema(patient_id="   ")

        assert "Patient ID cannot be empty or whitespace" in str(exc_info.value)

    def test_patient_sex_valid_values(self) -> None:
        """Test patient sex accepts valid values."""
        for sex in ["M", "F", "O"]:
            patient = PatientSchema(patient_id="test", patient_sex=sex)
            assert patient.patient_sex == sex

    def test_patient_sex_invalid_fails(self) -> None:
        """Test invalid patient sex raises error."""
        with pytest.raises(ValidationError):
            PatientSchema(patient_id="test", patient_sex="X")

    def test_patient_age_format(self) -> None:
        """Test patient age format validation."""
        valid_ages = ["045Y", "006M", "012W", "090D"]

        for age in valid_ages:
            patient = PatientSchema(patient_id="test", patient_age=age)
            assert patient.patient_age == age

    def test_patient_age_invalid_format_fails(self) -> None:
        """Test invalid age format raises error."""
        with pytest.raises(ValidationError):
            PatientSchema(patient_id="test", patient_age="45Y")  # Missing leading zero

    def test_patient_age_exceeds_max_fails(self) -> None:
        """Test age exceeding maximum raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PatientSchema(patient_id="test", patient_age="200Y")

        assert "Age in years cannot exceed 150" in str(exc_info.value)

    def test_patient_optional_fields(self) -> None:
        """Test patient with only required fields."""
        patient = PatientSchema(patient_id="test")

        assert patient.patient_id == "test"
        assert patient.patient_sex is None
        assert patient.patient_age is None


class TestStudySchema:
    """Test cases for StudySchema."""

    def test_valid_study(self) -> None:
        """Test creating valid study schema."""
        study = StudySchema(
            study_instance_uid="1.2.3.4.5",
            study_date="20250115",
            study_time="143000",
            study_description="Test Study",
            accession_number="ACC123",
        )

        assert study.study_instance_uid == "1.2.3.4.5"
        assert study.study_date == "20250115"

    def test_study_uid_format_valid(self) -> None:
        """Test valid UID formats."""
        valid_uids = ["1.2.3", "1.2.840.10008.5.1.4.1.1.2", "123.456.789.012345"]

        for uid in valid_uids:
            study = StudySchema(study_instance_uid=uid)
            assert study.study_instance_uid == uid

    def test_study_uid_invalid_characters_fails(self) -> None:
        """Test UID with invalid characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            StudySchema(study_instance_uid="1.2.abc.4")

        assert "must contain only digits and dots" in str(exc_info.value)

    def test_study_uid_invalid_dots_fails(self) -> None:
        """Test UID with invalid dot placement raises error."""
        invalid_uids = [".1.2.3", "1.2.3.", "1..2.3"]

        for uid in invalid_uids:
            with pytest.raises(ValidationError) as exc_info:
                StudySchema(study_instance_uid=uid)

            assert "invalid dot placement" in str(exc_info.value)

    def test_study_date_format(self) -> None:
        """Test study date format validation."""
        study = StudySchema(study_instance_uid="1.2.3", study_date="20250115")
        assert study.study_date == "20250115"

    def test_study_date_invalid_format_fails(self) -> None:
        """Test invalid study date format raises error."""
        with pytest.raises(ValidationError):
            StudySchema(study_instance_uid="1.2.3", study_date="2025-01-15")

    def test_study_date_invalid_date_fails(self) -> None:
        """Test invalid date raises error."""
        with pytest.raises(ValidationError) as exc_info:
            StudySchema(study_instance_uid="1.2.3", study_date="20251332")

        assert "Invalid study date format" in str(exc_info.value)

    def test_study_time_format(self) -> None:
        """Test study time format validation."""
        valid_times = ["143000", "120000.123456"]

        for time in valid_times:
            study = StudySchema(study_instance_uid="1.2.3", study_time=time)
            assert study.study_time == time

    def test_study_optional_fields(self) -> None:
        """Test study with only required fields."""
        study = StudySchema(study_instance_uid="1.2.3")

        assert study.study_date is None
        assert study.study_time is None


class TestSeriesSchema:
    """Test cases for SeriesSchema."""

    def test_valid_series(self) -> None:
        """Test creating valid series schema."""
        series = SeriesSchema(
            series_instance_uid="1.2.3.4.5.6",
            series_number=1,
            series_description="Test Series",
            modality="CT",
        )

        assert series.series_instance_uid == "1.2.3.4.5.6"
        assert series.modality == "CT"

    def test_series_number_range(self) -> None:
        """Test series number range validation."""
        series = SeriesSchema(series_instance_uid="1.2.3", series_number=99999, modality="CT")
        assert series.series_number == 99999

    def test_series_number_negative_fails(self) -> None:
        """Test negative series number raises error."""
        with pytest.raises(ValidationError):
            SeriesSchema(series_instance_uid="1.2.3", series_number=-1, modality="CT")

    def test_series_number_exceeds_max_fails(self) -> None:
        """Test series number exceeding max raises error."""
        with pytest.raises(ValidationError):
            SeriesSchema(series_instance_uid="1.2.3", series_number=100000, modality="CT")

    def test_modality_uppercase_conversion(self) -> None:
        """Test modality is converted to uppercase."""
        series = SeriesSchema(series_instance_uid="1.2.3", modality="ct")
        assert series.modality == "CT"

    def test_modality_required(self) -> None:
        """Test modality is required."""
        with pytest.raises(ValidationError):
            SeriesSchema(series_instance_uid="1.2.3")


class TestImageMetadataSchema:
    """Test cases for ImageMetadataSchema."""

    def test_valid_image_metadata(self) -> None:
        """Test creating valid image metadata."""
        image = ImageMetadataSchema(
            rows=512,
            columns=512,
            bits_allocated=16,
            bits_stored=12,
            pixel_spacing=[0.5, 0.5],
        )

        assert image.rows == 512
        assert image.bits_allocated == 16

    def test_dimensions_range(self) -> None:
        """Test image dimensions range validation."""
        image = ImageMetadataSchema(rows=1, columns=65535)
        assert image.rows == 1
        assert image.columns == 65535

    def test_dimensions_zero_fails(self) -> None:
        """Test zero dimensions raise error."""
        with pytest.raises(ValidationError):
            ImageMetadataSchema(rows=0, columns=512)

    def test_dimensions_exceeds_max_fails(self) -> None:
        """Test dimensions exceeding max raise error."""
        with pytest.raises(ValidationError):
            ImageMetadataSchema(rows=65536, columns=512)

    def test_pixel_spacing_length(self) -> None:
        """Test pixel spacing must have 2 elements."""
        with pytest.raises(ValidationError) as exc_info:
            ImageMetadataSchema(pixel_spacing=[0.5, 0.5, 0.5])

        assert "must have exactly 2 elements" in str(exc_info.value)

    def test_bits_relationship_valid(self) -> None:
        """Test bits_stored <= bits_allocated is valid."""
        image = ImageMetadataSchema(bits_allocated=16, bits_stored=12)
        assert image.bits_stored == 12

    def test_bits_relationship_invalid_fails(self) -> None:
        """Test bits_stored > bits_allocated raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ImageMetadataSchema(bits_allocated=12, bits_stored=16)

        assert "bits_stored cannot exceed bits_allocated" in str(exc_info.value)

    def test_all_fields_optional(self) -> None:
        """Test all fields are optional."""
        image = ImageMetadataSchema()
        assert image.rows is None


class TestCTMetadataSchema:
    """Test cases for CTMetadataSchema."""

    def test_valid_ct_metadata(self) -> None:
        """Test creating valid CT metadata."""
        ct = CTMetadataSchema(kvp=120, slice_thickness=5.0, reconstruction_diameter=350)

        assert ct.kvp == 120
        assert ct.slice_thickness == 5.0

    def test_kvp_range(self) -> None:
        """Test kVp range validation."""
        ct = CTMetadataSchema(kvp=0)
        assert ct.kvp == 0

        ct = CTMetadataSchema(kvp=200)
        assert ct.kvp == 200

    def test_kvp_exceeds_max_fails(self) -> None:
        """Test kVp exceeding max raises error."""
        with pytest.raises(ValidationError):
            CTMetadataSchema(kvp=250)

    def test_kvp_negative_fails(self) -> None:
        """Test negative kVp raises error."""
        with pytest.raises(ValidationError):
            CTMetadataSchema(kvp=-10)


class TestMRMetadataSchema:
    """Test cases for MRMetadataSchema."""

    def test_valid_mr_metadata(self) -> None:
        """Test creating valid MR metadata."""
        mr = MRMetadataSchema(repetition_time=500, echo_time=20, magnetic_field_strength=1.5)

        assert mr.repetition_time == 500
        assert mr.magnetic_field_strength == 1.5

    def test_field_strength_range(self) -> None:
        """Test field strength range validation."""
        mr = MRMetadataSchema(magnetic_field_strength=0)
        assert mr.magnetic_field_strength == 0

        mr = MRMetadataSchema(magnetic_field_strength=20)
        assert mr.magnetic_field_strength == 20

    def test_field_strength_exceeds_max_fails(self) -> None:
        """Test field strength exceeding max raises error."""
        with pytest.raises(ValidationError):
            MRMetadataSchema(magnetic_field_strength=25)


class TestDICOMInstanceSchema:
    """Test cases for DICOMInstanceSchema."""

    def test_valid_instance(self) -> None:
        """Test creating valid instance schema."""
        instance = DICOMInstanceSchema(
            sop_instance_uid="1.2.3.4.5.6.7", sop_class_uid="1.2.840.10008.5.1.4.1.1.2"
        )

        assert instance.sop_instance_uid == "1.2.3.4.5.6.7"


class TestDICOMMetadataSchema:
    """Test cases for complete DICOMMetadataSchema."""

    def test_valid_dicom_metadata(self) -> None:
        """Test creating valid complete DICOM metadata."""
        metadata = DICOMMetadataSchema(
            patient=PatientSchema(patient_id="test123"),
            study=StudySchema(study_instance_uid="1.2.3"),
            series=SeriesSchema(series_instance_uid="1.2.3.4", modality="CT"),
            instance=DICOMInstanceSchema(sop_instance_uid="1.2.3.4.5", sop_class_uid="1.2.840"),
        )

        assert metadata.patient.patient_id == "test123"
        assert metadata.series.modality == "CT"

    def test_dicom_with_ct_metadata(self) -> None:
        """Test DICOM with CT-specific metadata."""
        metadata = DICOMMetadataSchema(
            patient=PatientSchema(patient_id="test"),
            study=StudySchema(study_instance_uid="1.2.3"),
            series=SeriesSchema(series_instance_uid="1.2.3.4", modality="CT"),
            instance=DICOMInstanceSchema(sop_instance_uid="1.2.3.4.5", sop_class_uid="1.2.840"),
            ct_metadata=CTMetadataSchema(kvp=120),
        )

        assert metadata.ct_metadata.kvp == 120

    def test_ct_with_mr_metadata_fails(self) -> None:
        """Test CT modality with MR metadata raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DICOMMetadataSchema(
                patient=PatientSchema(patient_id="test"),
                study=StudySchema(study_instance_uid="1.2.3"),
                series=SeriesSchema(series_instance_uid="1.2.3.4", modality="CT"),
                instance=DICOMInstanceSchema(sop_instance_uid="1.2.3.4.5", sop_class_uid="1.2.840"),
                mr_metadata=MRMetadataSchema(repetition_time=500),
            )

        assert "CT modality should not have MR metadata" in str(exc_info.value)

    def test_mr_with_ct_metadata_fails(self) -> None:
        """Test MR modality with CT metadata raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DICOMMetadataSchema(
                patient=PatientSchema(patient_id="test"),
                study=StudySchema(study_instance_uid="1.2.3"),
                series=SeriesSchema(series_instance_uid="1.2.3.4", modality="MR"),
                instance=DICOMInstanceSchema(sop_instance_uid="1.2.3.4.5", sop_class_uid="1.2.840"),
                ct_metadata=CTMetadataSchema(kvp=120),
            )

        assert "MR modality should not have CT metadata" in str(exc_info.value)


class TestCSVRecordSchema:
    """Test cases for CSVRecordSchema."""

    def test_valid_csv_record(self) -> None:
        """Test creating valid CSV record."""
        record = CSVRecordSchema(
            patient_id="P001",
            study_date="2025-01-15",
            modality="CT",
            accession_number="ACC123",
            status="completed",
        )

        assert record.patient_id == "P001"
        assert record.status == "completed"

    def test_date_format_validation(self) -> None:
        """Test date format validation."""
        record = CSVRecordSchema(patient_id="P001", study_date="2025-01-15", modality="CT")
        assert record.study_date == "2025-01-15"

    def test_invalid_date_format_fails(self) -> None:
        """Test invalid date format raises error."""
        with pytest.raises(ValidationError):
            CSVRecordSchema(patient_id="P001", study_date="20250115", modality="CT")

    def test_invalid_date_fails(self) -> None:
        """Test invalid date raises error."""
        with pytest.raises(ValidationError) as exc_info:
            CSVRecordSchema(patient_id="P001", study_date="2025-13-45", modality="CT")

        assert "Invalid date format" in str(exc_info.value)

    def test_status_validation(self) -> None:
        """Test status validation."""
        for status in ["pending", "completed", "failed"]:
            record = CSVRecordSchema(
                patient_id="P001", study_date="2025-01-15", modality="CT", status=status
            )
            assert record.status == status

    def test_invalid_status_fails(self) -> None:
        """Test invalid status raises error."""
        with pytest.raises(ValidationError):
            CSVRecordSchema(
                patient_id="P001", study_date="2025-01-15", modality="CT", status="unknown"
            )


class TestDeliveryFileSchema:
    """Test cases for DeliveryFileSchema."""

    def test_valid_delivery_file(self) -> None:
        """Test creating valid delivery file."""
        file = DeliveryFileSchema(
            file_path="s3://bucket/file.dcm",
            file_size=1024,
            checksum="abc123def456" * 3,
            presigned_url="https://s3.amazonaws.com/...",
            url_expiration="2025-01-15T12:00:00Z",
        )

        assert file.file_size == 1024

    def test_file_size_zero_valid(self) -> None:
        """Test zero file size is valid."""
        file = DeliveryFileSchema(file_path="test.txt", file_size=0, checksum="a" * 32)
        assert file.file_size == 0

    def test_file_size_negative_fails(self) -> None:
        """Test negative file size raises error."""
        with pytest.raises(ValidationError):
            DeliveryFileSchema(file_path="test.txt", file_size=-1, checksum="a" * 32)

    def test_checksum_length(self) -> None:
        """Test checksum length validation."""
        # MD5 (32 chars)
        file = DeliveryFileSchema(file_path="test.txt", file_size=100, checksum="a" * 32)
        assert len(file.checksum) == 32

        # SHA256 (64 chars)
        file = DeliveryFileSchema(file_path="test.txt", file_size=100, checksum="a" * 64)
        assert len(file.checksum) == 64

    def test_checksum_too_short_fails(self) -> None:
        """Test checksum too short raises error."""
        with pytest.raises(ValidationError):
            DeliveryFileSchema(file_path="test.txt", file_size=100, checksum="abc123")


class TestDeliveryManifestSchema:
    """Test cases for DeliveryManifestSchema."""

    def test_valid_delivery_manifest(self) -> None:
        """Test creating valid delivery manifest."""
        manifest = DeliveryManifestSchema(
            manifest_id="MAN123",
            created_at="2025-01-15T12:00:00Z",
            patient_id="P001",
            study_instance_uid="1.2.3",
            total_files=2,
            total_size_bytes=2048,
            files=[
                DeliveryFileSchema(file_path="file1.dcm", file_size=1024, checksum="a" * 32),
                DeliveryFileSchema(file_path="file2.dcm", file_size=1024, checksum="b" * 32),
            ],
        )

        assert manifest.total_files == 2
        assert len(manifest.files) == 2

    def test_timestamp_validation(self) -> None:
        """Test ISO 8601 timestamp validation."""
        timestamps = [
            "2025-01-15T12:00:00Z",
            "2025-01-15T12:00:00+00:00",
            "2025-01-15T12:00:00.123456Z",
        ]

        for ts in timestamps:
            manifest = DeliveryManifestSchema(
                manifest_id="MAN123",
                created_at=ts,
                patient_id="P001",
                study_instance_uid="1.2.3",
                total_files=0,
                total_size_bytes=0,
                files=[],
            )
            assert manifest.created_at == ts

    def test_invalid_timestamp_fails(self) -> None:
        """Test invalid timestamp raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DeliveryManifestSchema(
                manifest_id="MAN123",
                created_at="2025-01-15 12:00:00",
                patient_id="P001",
                study_instance_uid="1.2.3",
                total_files=0,
                total_size_bytes=0,
                files=[],
            )

        assert "Invalid ISO 8601 timestamp" in str(exc_info.value)

    def test_file_count_mismatch_fails(self) -> None:
        """Test file count mismatch raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DeliveryManifestSchema(
                manifest_id="MAN123",
                created_at="2025-01-15T12:00:00Z",
                patient_id="P001",
                study_instance_uid="1.2.3",
                total_files=3,  # Says 3
                total_size_bytes=1024,
                files=[
                    DeliveryFileSchema(file_path="file1.dcm", file_size=1024, checksum="a" * 32)
                ],  # But only 1
            )

        assert "does not match actual file count" in str(exc_info.value)

    def test_empty_files_list_valid(self) -> None:
        """Test empty files list is valid."""
        manifest = DeliveryManifestSchema(
            manifest_id="MAN123",
            created_at="2025-01-15T12:00:00Z",
            patient_id="P001",
            study_instance_uid="1.2.3",
            total_files=0,
            total_size_bytes=0,
            files=[],
        )

        assert len(manifest.files) == 0

    def test_metadata_optional(self) -> None:
        """Test metadata field is optional."""
        manifest = DeliveryManifestSchema(
            manifest_id="MAN123",
            created_at="2025-01-15T12:00:00Z",
            patient_id="P001",
            study_instance_uid="1.2.3",
            total_files=0,
            total_size_bytes=0,
            files=[],
        )

        assert manifest.metadata == {}
