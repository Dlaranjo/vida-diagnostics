#!/bin/bash
# Script to build Lambda layer with Python dependencies

set -e

echo "Building Lambda layer with Python dependencies..."

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
MEDICAL_IMAGING_DIR="$PROJECT_ROOT/medical-imaging-pipeline"
LAYER_DIR="$SCRIPT_DIR/lambda_layer"
OUTPUT_ZIP="$PROJECT_ROOT/terraform/lambda_layer.zip"

# Clean previous build
echo "Cleaning previous build..."
rm -rf "$LAYER_DIR"
rm -f "$OUTPUT_ZIP"

# Create layer directory structure
echo "Creating layer directory structure..."
mkdir -p "$LAYER_DIR/python"

# Install dependencies
echo "Installing dependencies..."
if [ -f "$MEDICAL_IMAGING_DIR/requirements.txt" ]; then
    pip install -r "$MEDICAL_IMAGING_DIR/requirements.txt" \
        --target "$LAYER_DIR/python" \
        --platform manylinux2014_x86_64 \
        --only-binary=:all: \
        --upgrade
else
    echo "Error: requirements.txt not found at $MEDICAL_IMAGING_DIR/requirements.txt"
    exit 1
fi

# Remove unnecessary files to reduce layer size
echo "Optimizing layer size..."
cd "$LAYER_DIR/python"
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
# Keep .dist-info and .egg-info for package metadata (needed for imports)
# find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
# find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "Creating layer zip file..."
python3 "$SCRIPT_DIR/create_zip.py" "$LAYER_DIR/python" "$OUTPUT_ZIP"

echo ""
echo "Lambda layer built successfully!"
echo "Location: $OUTPUT_ZIP"
echo ""
echo "Note: AWS Lambda layer size limit is 50MB (zipped) / 250MB (unzipped)"

# Cleanup
echo "Cleaning up temporary files..."
rm -rf "$LAYER_DIR"

echo "Done!"
