#!/bin/bash

# Create release directory
mkdir -p release

# Build for Linux
echo "Building for Linux..."
cargo build --release --target x86_64-unknown-linux-gnu
cp target/x86_64-unknown-linux-gnu/release/codai release/codai-linux

# Build for Windows
echo "Building for Windows..."
cargo build --release --target x86_64-pc-windows-gnu
cp target/x86_64-pc-windows-gnu/release/codai.exe release/codai-windows.exe

# Build for macOS
echo "Building for macOS..."
cargo build --release --target x86_64-apple-darwin
cp target/x86_64-apple-darwin/release/codai release/codai-macos

echo "Build complete! Binaries are in the release directory:"
ls -lh release/ 