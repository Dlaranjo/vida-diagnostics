"""
Metadata extraction from CSV, JSON, and XML files.

Handles parsing and validation of non-DICOM metadata files.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd

from utils.logger import get_logger, log_execution

logger = get_logger(__name__)


class MetadataExtractor:
    """
    Extractor for metadata from various file formats (CSV, JSON, XML).

    Provides unified interface for reading and parsing metadata files.
    """

    def __init__(self) -> None:
        """Initialize metadata extractor."""
        pass

    def read_csv(
        self, file_path: Union[str, Path], delimiter: str = ",", encoding: str = "utf-8"
    ) -> pd.DataFrame:
        """
        Read CSV file into pandas DataFrame.

        Args:
            file_path: Path to CSV file
            delimiter: CSV delimiter character
            encoding: File encoding

        Returns:
            DataFrame containing CSV data

        Raises:
            FileNotFoundError: If file doesn't exist
            pd.errors.ParserError: If CSV parsing fails
        """
        log_execution(
            logger, operation="read_csv", status="started", details={"file_path": str(file_path)}
        )

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"CSV file not found: {file_path}")

            # Read CSV with pandas
            df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding)

            log_execution(
                logger,
                operation="read_csv",
                status="completed",
                details={
                    "file_path": str(file_path),
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns),
                },
            )

            return df

        except Exception as e:
            log_execution(
                logger,
                operation="read_csv",
                status="failed",
                details={"file_path": str(file_path)},
                error=e,
            )
            raise

    def read_json(self, file_path: Union[str, Path], encoding: str = "utf-8") -> Union[Dict, List]:
        """
        Read JSON file.

        Args:
            file_path: Path to JSON file
            encoding: File encoding

        Returns:
            Parsed JSON as dictionary or list

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON parsing fails
        """
        log_execution(
            logger, operation="read_json", status="started", details={"file_path": str(file_path)}
        )

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"JSON file not found: {file_path}")

            # Read JSON
            with open(file_path, "r", encoding=encoding) as f:
                data = json.load(f)

            log_execution(
                logger,
                operation="read_json",
                status="completed",
                details={
                    "file_path": str(file_path),
                    "data_type": type(data).__name__,
                    "size_bytes": file_path.stat().st_size,
                },
            )

            return data

        except Exception as e:
            log_execution(
                logger,
                operation="read_json",
                status="failed",
                details={"file_path": str(file_path)},
                error=e,
            )
            raise

    def read_xml(self, file_path: Union[str, Path], encoding: str = "utf-8") -> ET.Element:
        """
        Read XML file.

        Args:
            file_path: Path to XML file
            encoding: File encoding

        Returns:
            Parsed XML root element

        Raises:
            FileNotFoundError: If file doesn't exist
            ET.ParseError: If XML parsing fails
        """
        log_execution(
            logger, operation="read_xml", status="started", details={"file_path": str(file_path)}
        )

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"XML file not found: {file_path}")

            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()

            log_execution(
                logger,
                operation="read_xml",
                status="completed",
                details={
                    "file_path": str(file_path),
                    "root_tag": root.tag,
                    "children_count": len(root),
                },
            )

            return root

        except Exception as e:
            log_execution(
                logger,
                operation="read_xml",
                status="failed",
                details={"file_path": str(file_path)},
                error=e,
            )
            raise

    def xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """
        Convert XML element to dictionary.

        Args:
            element: XML element to convert

        Returns:
            Dictionary representation of XML
        """
        result: Dict[str, Any] = {}

        # Add attributes
        if element.attrib:
            result["@attributes"] = element.attrib

        # Add text content
        if element.text and element.text.strip():
            if len(element) == 0:  # No children, just return text
                return {element.tag: element.text.strip()}
            result["text"] = element.text.strip()

        # Add children
        for child in element:
            child_data = self.xml_to_dict(child)

            if child.tag in result:
                # Tag already exists, convert to list
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data[child.tag])
            else:
                result[child.tag] = child_data[child.tag]

        return {element.tag: result if result else element.text}

    def csv_to_dict_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Convert DataFrame to list of dictionaries (one per row).

        Args:
            df: DataFrame to convert

        Returns:
            List of row dictionaries
        """
        return df.to_dict(orient="records")

    def merge_metadata(
        self, primary: Dict[str, Any], *additional: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge multiple metadata dictionaries.

        Args:
            primary: Primary metadata dictionary
            *additional: Additional metadata dictionaries to merge

        Returns:
            Merged metadata dictionary (later values override earlier ones)
        """
        merged = primary.copy()

        for metadata in additional:
            merged.update(metadata)

        return merged

    def validate_required_fields(
        self, data: Dict[str, Any], required_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Validate that required fields are present in metadata.

        Args:
            data: Metadata dictionary
            required_fields: List of required field names

        Returns:
            Validation results
        """
        results = {
            "is_valid": True,
            "missing_fields": [],
            "present_fields": [],
        }

        for field in required_fields:
            if field in data and data[field] not in [None, "", []]:
                results["present_fields"].append(field)
            else:
                results["is_valid"] = False
                results["missing_fields"].append(field)

        return results
