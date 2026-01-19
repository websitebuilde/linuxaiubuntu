#!/bin/bash
#
# Build script for AI System Assistant Debian package
#
# Usage: ./build-deb.sh
#
# This script creates a .deb package from the source files.
#

set -e

PACKAGE_NAME="ai-system-assistant"
VERSION="1.0.0"
ARCH="amd64"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"  # Go up one level from scripts/

# Build directory
BUILD_DIR="/tmp/${PACKAGE_NAME}_${VERSION}_${ARCH}"
OUTPUT_DIR="${PROJECT_DIR}/dist"

echo "=== Building ${PACKAGE_NAME} v${VERSION} ==="
echo "Project directory: ${PROJECT_DIR}"
echo "Build directory: ${BUILD_DIR}"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Create directory structure
echo "Creating directory structure..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/opt/ai-system-assistant/src"
mkdir -p "${BUILD_DIR}/opt/ai-system-assistant/systemd"
mkdir -p "${BUILD_DIR}/opt/ai-system-assistant/bin"
mkdir -p "${BUILD_DIR}/var/log"

# Copy DEBIAN files
echo "Copying DEBIAN files..."
cp "${PROJECT_DIR}/debian/DEBIAN/control" "${BUILD_DIR}/DEBIAN/"
cp "${PROJECT_DIR}/debian/DEBIAN/postinst" "${BUILD_DIR}/DEBIAN/"
cp "${PROJECT_DIR}/debian/DEBIAN/prerm" "${BUILD_DIR}/DEBIAN/"

# Set permissions for DEBIAN scripts
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

# Copy application files
echo "Copying application files..."
cp -r "${PROJECT_DIR}/src/"* "${BUILD_DIR}/opt/ai-system-assistant/src/"
cp "${PROJECT_DIR}/requirements.txt" "${BUILD_DIR}/opt/ai-system-assistant/"
cp "${PROJECT_DIR}/README.md" "${BUILD_DIR}/opt/ai-system-assistant/"
cp "${PROJECT_DIR}/systemd/ai-assistant.service" "${BUILD_DIR}/opt/ai-system-assistant/systemd/"
cp "${PROJECT_DIR}/bin/ai-assistant" "${BUILD_DIR}/opt/ai-system-assistant/bin/"

# Set permissions
chmod 755 "${BUILD_DIR}/opt/ai-system-assistant/bin/ai-assistant"

# Create empty log file placeholder
touch "${BUILD_DIR}/var/log/.ai-assistant-placeholder"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build the package
echo "Building Debian package..."
DEB_FILE="${OUTPUT_DIR}/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$BUILD_DIR" "$DEB_FILE"

# Clean up
rm -rf "$BUILD_DIR"

echo ""
echo "=== Build complete ==="
echo "Package: ${DEB_FILE}"
echo ""
echo "To install:"
echo "  sudo dpkg -i ${DEB_FILE}"
echo "  sudo apt-get install -f  # Install dependencies if needed"
echo ""

# Verify package
echo "Package info:"
dpkg-deb --info "$DEB_FILE"
