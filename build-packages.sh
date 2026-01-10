#!/bin/bash
set -e

VERSION=$(grep -oP "version: '\K[^']+" meson.build | head -1)
PKG_NAME="bottles-deflatpak-${VERSION}"
BUILD_DIR="build"
INSTALL_DIR="install_root"

echo "Building ${PKG_NAME}..."

# Clean up
rm -rf "${BUILD_DIR}" "${INSTALL_DIR}" "${PKG_NAME}.tar.gz"

MESON_ARGS="--prefix=/usr"
if [[ "$*" == *"--development"* ]]; then
    MESON_ARGS="${MESON_ARGS} -Dprofile=development"
fi

# Build
meson setup "${BUILD_DIR}" ${MESON_ARGS}
ninja -C "${BUILD_DIR}"

# Install to temp root
DESTDIR="$(pwd)/${INSTALL_DIR}" ninja -C "${BUILD_DIR}" install

# Create tarball
cd "${INSTALL_DIR}"
tar -czf "../${PKG_NAME}.tar.gz" .
cd ..

echo "Created ${PKG_NAME}.tar.gz"

# Cleanup
rm -rf "${INSTALL_DIR}"
