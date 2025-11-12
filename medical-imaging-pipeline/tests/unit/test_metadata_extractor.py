"""
Unit tests for metadata extractor module.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.metadata_extractor import MetadataExtractor


@pytest.fixture
def metadata_extractor() -> MetadataExtractor:
    """Create MetadataExtractor instance."""
    return MetadataExtractor()


@pytest.fixture
def fixtures_dir() -> Path:
    """Get path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_csv_path(fixtures_dir: Path) -> Path:
    """Get path to sample CSV file."""
    return fixtures_dir / "sample_metadata.csv"


@pytest.fixture
def sample_json_path(fixtures_dir: Path) -> Path:
    """Get path to sample JSON file."""
    return fixtures_dir / "sample_study.json"


@pytest.fixture
def sample_xml_path(fixtures_dir: Path) -> Path:
    """Get path to sample XML file."""
    return fixtures_dir / "sample_imaging.xml"


class TestMetadataExtractor:
    """Test cases for MetadataExtractor class."""

    def test_initialization(self, metadata_extractor: MetadataExtractor) -> None:
        """Test extractor initialization."""
        assert metadata_extractor is not None

    # CSV Tests
    def test_read_csv_success(
        self, metadata_extractor: MetadataExtractor, sample_csv_path: Path
    ) -> None:
        """Test successfully reading a CSV file."""
        df = metadata_extractor.read_csv(sample_csv_path)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert len(df.columns) == 5
        assert "patient_id" in df.columns
        assert "study_date" in df.columns
        assert df.iloc[0]["patient_id"] == "P001"

    def test_read_csv_not_found(self, metadata_extractor: MetadataExtractor) -> None:
        """Test reading non-existent CSV file raises error."""
        with pytest.raises(FileNotFoundError):
            metadata_extractor.read_csv("/nonexistent/file.csv")

    def test_read_csv_custom_delimiter(
        self, metadata_extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test reading CSV with custom delimiter."""
        # Create semicolon-delimited CSV
        csv_file = tmp_path / "test_semicolon.csv"
        csv_file.write_text("col1;col2;col3\nval1;val2;val3\nval4;val5;val6")

        df = metadata_extractor.read_csv(csv_file, delimiter=";")

        assert len(df) == 2
        assert len(df.columns) == 3
        assert df.iloc[0]["col1"] == "val1"

    def test_read_csv_with_path_string(
        self, metadata_extractor: MetadataExtractor, sample_csv_path: Path
    ) -> None:
        """Test reading CSV with string path instead of Path object."""
        df = metadata_extractor.read_csv(str(sample_csv_path))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    # JSON Tests
    def test_read_json_success(
        self, metadata_extractor: MetadataExtractor, sample_json_path: Path
    ) -> None:
        """Test successfully reading a JSON file."""
        data = metadata_extractor.read_json(sample_json_path)

        assert isinstance(data, dict)
        assert data["study_instance_uid"] == "1.2.3.4.5.6.7.8.9"
        assert data["patient_id"] == "P001"
        assert "series" in data
        assert len(data["series"]) == 2

    def test_read_json_not_found(self, metadata_extractor: MetadataExtractor) -> None:
        """Test reading non-existent JSON file raises error."""
        with pytest.raises(FileNotFoundError):
            metadata_extractor.read_json("/nonexistent/file.json")

    def test_read_json_invalid(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        """Test reading invalid JSON raises error."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json content")

        with pytest.raises(json.JSONDecodeError):
            metadata_extractor.read_json(json_file)

    def test_read_json_array(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        """Test reading JSON array."""
        json_file = tmp_path / "array.json"
        json_file.write_text('[{"id": 1}, {"id": 2}]')

        data = metadata_extractor.read_json(json_file)

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == 1

    def test_read_json_with_path_string(
        self, metadata_extractor: MetadataExtractor, sample_json_path: Path
    ) -> None:
        """Test reading JSON with string path."""
        data = metadata_extractor.read_json(str(sample_json_path))

        assert isinstance(data, dict)
        assert data["patient_id"] == "P001"

    # XML Tests
    def test_read_xml_success(
        self, metadata_extractor: MetadataExtractor, sample_xml_path: Path
    ) -> None:
        """Test successfully reading an XML file."""
        root = metadata_extractor.read_xml(sample_xml_path)

        assert isinstance(root, ET.Element)
        assert root.tag == "imaging_study"
        assert len(root) > 0

    def test_read_xml_not_found(self, metadata_extractor: MetadataExtractor) -> None:
        """Test reading non-existent XML file raises error."""
        with pytest.raises(FileNotFoundError):
            metadata_extractor.read_xml("/nonexistent/file.xml")

    def test_read_xml_invalid(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        """Test reading invalid XML raises error."""
        xml_file = tmp_path / "invalid.xml"
        xml_file.write_text("<invalid><unclosed>")

        with pytest.raises(ET.ParseError):
            metadata_extractor.read_xml(xml_file)

    def test_read_xml_with_path_string(
        self, metadata_extractor: MetadataExtractor, sample_xml_path: Path
    ) -> None:
        """Test reading XML with string path."""
        root = metadata_extractor.read_xml(str(sample_xml_path))

        assert isinstance(root, ET.Element)
        assert root.tag == "imaging_study"

    # XML to Dict Tests
    def test_xml_to_dict_simple_element(self, metadata_extractor: MetadataExtractor) -> None:
        """Test converting simple XML element to dict."""
        xml_string = "<name>John Doe</name>"
        element = ET.fromstring(xml_string)

        result = metadata_extractor.xml_to_dict(element)

        assert result == {"name": "John Doe"}

    def test_xml_to_dict_with_attributes(self, metadata_extractor: MetadataExtractor) -> None:
        """Test converting XML element with attributes."""
        xml_string = '<patient id="P001" status="active"><name>John</name></patient>'
        element = ET.fromstring(xml_string)

        result = metadata_extractor.xml_to_dict(element)

        assert "@attributes" in result["patient"]
        assert result["patient"]["@attributes"]["id"] == "P001"
        assert result["patient"]["name"] == "John"

    def test_xml_to_dict_nested(self, metadata_extractor: MetadataExtractor) -> None:
        """Test converting nested XML to dict."""
        xml_string = """
        <study>
            <patient>
                <name>John</name>
                <age>45</age>
            </patient>
            <modality>CT</modality>
        </study>
        """
        element = ET.fromstring(xml_string)

        result = metadata_extractor.xml_to_dict(element)

        assert "study" in result
        assert "patient" in result["study"]
        assert result["study"]["patient"]["name"] == "John"
        assert result["study"]["modality"] == "CT"

    def test_xml_to_dict_multiple_children_same_tag(
        self, metadata_extractor: MetadataExtractor
    ) -> None:
        """Test XML with multiple children of same tag becomes list."""
        xml_string = """
        <series>
            <item>Series 1</item>
            <item>Series 2</item>
            <item>Series 3</item>
        </series>
        """
        element = ET.fromstring(xml_string)

        result = metadata_extractor.xml_to_dict(element)

        assert "series" in result
        assert "item" in result["series"]
        assert isinstance(result["series"]["item"], list)
        assert len(result["series"]["item"]) == 3
        assert result["series"]["item"][0] == "Series 1"

    def test_xml_to_dict_empty_element(self, metadata_extractor: MetadataExtractor) -> None:
        """Test converting empty XML element."""
        xml_string = "<empty></empty>"
        element = ET.fromstring(xml_string)

        result = metadata_extractor.xml_to_dict(element)

        assert result == {"empty": None}

    # CSV to Dict Tests
    def test_csv_to_dict_records(self, metadata_extractor: MetadataExtractor) -> None:
        """Test converting DataFrame to list of dictionaries."""
        df = pd.DataFrame(
            {
                "patient_id": ["P001", "P002"],
                "study_date": ["2025-01-15", "2025-01-16"],
                "modality": ["CT", "MR"],
            }
        )

        records = metadata_extractor.csv_to_dict_records(df)

        assert isinstance(records, list)
        assert len(records) == 2
        assert records[0]["patient_id"] == "P001"
        assert records[1]["modality"] == "MR"

    def test_csv_to_dict_records_empty_df(self, metadata_extractor: MetadataExtractor) -> None:
        """Test converting empty DataFrame."""
        df = pd.DataFrame()

        records = metadata_extractor.csv_to_dict_records(df)

        assert isinstance(records, list)
        assert len(records) == 0

    # Merge Metadata Tests
    def test_merge_metadata_simple(self, metadata_extractor: MetadataExtractor) -> None:
        """Test merging two metadata dictionaries."""
        primary = {"patient_id": "P001", "study_date": "2025-01-15"}
        additional = {"modality": "CT", "accession": "ACC001"}

        merged = metadata_extractor.merge_metadata(primary, additional)

        assert merged["patient_id"] == "P001"
        assert merged["study_date"] == "2025-01-15"
        assert merged["modality"] == "CT"
        assert merged["accession"] == "ACC001"

    def test_merge_metadata_override(self, metadata_extractor: MetadataExtractor) -> None:
        """Test that later metadata overrides earlier values."""
        primary = {"patient_id": "P001", "status": "pending"}
        additional = {"status": "completed", "modality": "CT"}

        merged = metadata_extractor.merge_metadata(primary, additional)

        assert merged["status"] == "completed"  # Should be overridden
        assert merged["patient_id"] == "P001"
        assert merged["modality"] == "CT"

    def test_merge_metadata_multiple(self, metadata_extractor: MetadataExtractor) -> None:
        """Test merging multiple metadata dictionaries."""
        primary = {"patient_id": "P001"}
        meta2 = {"study_date": "2025-01-15"}
        meta3 = {"modality": "CT"}
        meta4 = {"accession": "ACC001"}

        merged = metadata_extractor.merge_metadata(primary, meta2, meta3, meta4)

        assert len(merged) == 4
        assert merged["patient_id"] == "P001"
        assert merged["accession"] == "ACC001"

    def test_merge_metadata_empty_additional(self, metadata_extractor: MetadataExtractor) -> None:
        """Test merging with empty additional dict."""
        primary = {"patient_id": "P001", "modality": "CT"}

        merged = metadata_extractor.merge_metadata(primary, {})

        assert merged == primary

    # Validate Required Fields Tests
    def test_validate_required_fields_all_present(
        self, metadata_extractor: MetadataExtractor
    ) -> None:
        """Test validation when all required fields are present."""
        data = {
            "patient_id": "P001",
            "study_date": "2025-01-15",
            "modality": "CT",
        }
        required = ["patient_id", "study_date", "modality"]

        result = metadata_extractor.validate_required_fields(data, required)

        assert result["is_valid"] is True
        assert len(result["missing_fields"]) == 0
        assert len(result["present_fields"]) == 3
        assert "patient_id" in result["present_fields"]

    def test_validate_required_fields_some_missing(
        self, metadata_extractor: MetadataExtractor
    ) -> None:
        """Test validation when some required fields are missing."""
        data = {"patient_id": "P001", "study_date": "2025-01-15"}
        required = ["patient_id", "study_date", "modality", "accession"]

        result = metadata_extractor.validate_required_fields(data, required)

        assert result["is_valid"] is False
        assert len(result["missing_fields"]) == 2
        assert "modality" in result["missing_fields"]
        assert "accession" in result["missing_fields"]
        assert len(result["present_fields"]) == 2

    def test_validate_required_fields_empty_values(
        self, metadata_extractor: MetadataExtractor
    ) -> None:
        """Test validation treats empty values as missing."""
        data = {
            "patient_id": "P001",
            "study_date": "",
            "modality": None,
            "accession": [],
        }
        required = ["patient_id", "study_date", "modality", "accession"]

        result = metadata_extractor.validate_required_fields(data, required)

        assert result["is_valid"] is False
        assert len(result["missing_fields"]) == 3
        assert "study_date" in result["missing_fields"]
        assert "modality" in result["missing_fields"]
        assert "accession" in result["missing_fields"]
        assert len(result["present_fields"]) == 1

    def test_validate_required_fields_no_requirements(
        self, metadata_extractor: MetadataExtractor
    ) -> None:
        """Test validation with no required fields."""
        data = {"patient_id": "P001"}
        required = []

        result = metadata_extractor.validate_required_fields(data, required)

        assert result["is_valid"] is True
        assert len(result["missing_fields"]) == 0
        assert len(result["present_fields"]) == 0

    def test_validate_required_fields_empty_data(
        self, metadata_extractor: MetadataExtractor
    ) -> None:
        """Test validation with empty data dict."""
        data = {}
        required = ["patient_id", "study_date"]

        result = metadata_extractor.validate_required_fields(data, required)

        assert result["is_valid"] is False
        assert len(result["missing_fields"]) == 2
        assert len(result["present_fields"]) == 0
