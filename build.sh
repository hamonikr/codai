#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print with color
print_status() {
    echo -e "${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

# Create release directory
mkdir -p release

# Detect OS and architecture
detect_os() {
    local os
    local arch
    
    case "$(uname -s)" in
        Linux*)     os="linux";;
        Darwin*)    os="macos";;
        MINGW*|MSYS*|CYGWIN*) 
            os="windows"
            ;;
        *)
            print_error "Unsupported operating system"
            exit 1
            ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64)
            arch="x86_64"
            ;;
        aarch64|arm64)
            arch="arm64"
            ;;
        armv7l|armv6l)
            arch="arm32"
            ;;
        *)
            print_error "Unsupported architecture: $(uname -m)"
            exit 1
            ;;
    esac

    echo "${os}-${arch}"
}

# Main build process
main() {
    local os_arch
    os_arch=$(detect_os)
    print_status "Detected system: $os_arch"

    case "$os_arch" in
        "linux-x86_64")
            print_status "Building for Linux..."
            cargo build --release --target x86_64-unknown-linux-gnu
            cp target/x86_64-unknown-linux-gnu/release/codai release/codai-linux
            ./install.sh
            ;;
        "macos-x86_64")
            print_status "Building for macOS..."
            cargo build --release --target x86_64-apple-darwin
            cp target/x86_64-apple-darwin/release/codai release/codai-macos
            ;;
        "windows-x86_64")
            print_status "Building for Windows..."
            cargo build --release --target x86_64-pc-windows-gnu
            cp target/x86_64-pc-windows-gnu/release/codai.exe release/codai-windows.exe
            ;;
        *)
            print_error "Unsupported platform: $os_arch"
            exit 1
            ;;
    esac

    print_status "Build complete! Binary is in the release directory:"
    ls -lh release/
}

# Run main build process
main 