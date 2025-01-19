#!/bin/bash

# Create release directory
mkdir -p release

# Build for Linux
echo "Building for Linux..."
cargo build --release --target x86_64-unknown-linux-gnu
cp target/x86_64-unknown-linux-gnu/release/airun-cli release/airun-cli-linux

# Build for Windows
echo "Building for Windows..."
cargo build --release --target x86_64-pc-windows-gnu
cp target/x86_64-pc-windows-gnu/release/airun-cli.exe release/airun-cli-windows.exe

# Build for macOS
echo "Building for macOS..."
cargo build --release --target x86_64-apple-darwin
cp target/x86_64-apple-darwin/release/airun-cli release/airun-cli-macos

echo "Build complete! Binaries are in the release directory:"
ls -lh release/ 