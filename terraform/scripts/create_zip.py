#!/usr/bin/env python3
"""Create Lambda layer zip file using Python's zipfile module."""

import os
import sys
import zipfile
from pathlib import Path


def create_zip(source_dir: str, output_file: str) -> None:
    """Create a zip file from a directory.

    Args:
        source_dir: Source directory to zip
        output_file: Output zip file path
    """
    source_path = Path(source_dir)
    output_path = Path(output_file)

    # Remove existing zip file
    if output_path.exists():
        output_path.unlink()

    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create zip file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_path.parent)
                zipf.write(file_path, arcname)

    # Get file size
    size_bytes = output_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    print(f"Created: {output_path}")
    print(f"Size: {size_mb:.2f} MB")

    if size_mb > 50:
        print(f"WARNING: Layer size ({size_mb:.2f} MB) exceeds AWS limit (50 MB)")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: create_zip.py <source_dir> <output_file>")
        sys.exit(1)

    source_dir = sys.argv[1]
    output_file = sys.argv[2]

    create_zip(source_dir, output_file)
