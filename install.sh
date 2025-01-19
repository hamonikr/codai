#!/bin/bash

set -e

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

# Detect OS and architecture
detect_os() {
    local os
    local arch
    
    case "$(uname -s)" in
        Linux*)     os="linux";;
        Darwin*)    os="macos";;
        MINGW*|MSYS*|CYGWIN*) 
            print_error "Windows installation via script is not supported. Please download airun-cli-windows.exe from: https://github.com/chaeya/airun-cli/releases"
            exit 1
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

# Check for required tools
check_requirements() {
    local missing_tools=()
    local missing_packages=()

    # Check for curl
    if ! command -v curl >/dev/null 2>&1; then
        missing_tools+=("curl")
    fi

    # Check for Python
    local python_cmd=""
    if command -v python3 >/dev/null 2>&1; then
        python_cmd="python3"
    elif command -v python >/dev/null 2>&1; then
        if [[ $(python --version 2>&1) == Python\ 3* ]]; then
            python_cmd="python"
        fi
    fi

    if [ -z "$python_cmd" ]; then
        missing_tools+=("python3")
    else
        # Check Python version
        local python_version
        python_version=$($python_cmd -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")')
        major_version=$(echo "$python_version" | cut -d. -f1)
        minor_version=$(echo "$python_version" | cut -d. -f2)
        
        if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 7 ]); then
            print_error "Python 3.7 or higher is required (found version $python_version)"
            exit 1
        fi

        # Check for venv module
        if ! $python_cmd -c "import venv" 2>/dev/null; then
            case "$(uname -s)" in
                Linux*)
                    missing_packages+=("python3-venv")
                    ;;
                Darwin*)
                    # venv is included with Python on macOS
                    print_error "Python venv module not found. Please reinstall Python"
                    exit 1
                    ;;
            esac
        fi
    fi

    # Install missing tools
    if [ ${#missing_tools[@]} -ne 0 ] || [ ${#missing_packages[@]} -ne 0 ]; then
        if [ "$(uname -s)" = "Linux" ]; then
            if command -v apt-get >/dev/null 2>&1; then
                print_status "Installing missing dependencies..."
                sudo apt-get update
                [ ${#missing_tools[@]} -ne 0 ] && sudo apt-get install -y "${missing_tools[@]}"
                [ ${#missing_packages[@]} -ne 0 ] && sudo apt-get install -y "${missing_packages[@]}"
            elif command -v dnf >/dev/null 2>&1; then
                [ ${#missing_tools[@]} -ne 0 ] && sudo dnf install -y "${missing_tools[@]}"
                [ ${#missing_packages[@]} -ne 0 ] && sudo dnf install -y "${missing_packages[@]}"
            elif command -v yum >/dev/null 2>&1; then
                [ ${#missing_tools[@]} -ne 0 ] && sudo yum install -y "${missing_tools[@]}"
                [ ${#missing_packages[@]} -ne 0 ] && sudo yum install -y "${missing_packages[@]}"
            elif command -v pacman >/dev/null 2>&1; then
                [ ${#missing_tools[@]} -ne 0 ] && sudo pacman -Sy --noconfirm "${missing_tools[@]}"
                [ ${#missing_packages[@]} -ne 0 ] && sudo pacman -Sy --noconfirm "${missing_packages[@]}"
            else
                print_error "Please install the following tools manually: ${missing_tools[*]} ${missing_packages[*]}"
                exit 1
            fi
        elif [ "$(uname -s)" = "Darwin" ]; then
            if command -v brew >/dev/null 2>&1; then
                [ ${#missing_tools[@]} -ne 0 ] && brew install "${missing_tools[@]}"
            else
                print_error "Please install Homebrew first: https://brew.sh/"
                exit 1
            fi
        fi
    fi

    print_status "All required dependencies are installed"
}

# Create necessary directories
create_directories() {
    local config_dir

    if [ "$(uname -s)" = "Darwin" ]; then
        config_dir="$HOME/Library/Application Support/airun-cli"
    else
        config_dir="$HOME/.config/airun-cli"
    fi

    mkdir -p "$config_dir"
    print_status "Created configuration directory: $config_dir"
}

# Download and install binary
install_binary() {
    local os_arch=$1
    local tmp_dir
    local install_dir
    local binary_name="airun-cli"
    
    # Determine installation directory
    if [ "$(id -u)" -eq 0 ]; then
        install_dir="/usr/local/bin"
    else
        install_dir="$HOME/.local/bin"
        mkdir -p "$install_dir"
    fi

    # Add ~/.local/bin to PATH if it's not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    fi

    # Create temporary directory
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "$tmp_dir"' EXIT

    print_status "Downloading airun-cli for ${os_arch}..."
    
    # Get the latest release URL
    local latest_release_url="https://github.com/chaeya/airun-cli/releases/latest/download/airun-cli-${os_arch}"
    
    # Download binary
    if ! curl -sSL "$latest_release_url" -o "$tmp_dir/$binary_name"; then
        print_error "Failed to download airun-cli"
        exit 1
    fi

    # Install binary
    chmod +x "$tmp_dir/$binary_name"
    if [ "$(id -u)" -eq 0 ]; then
        mv "$tmp_dir/$binary_name" "$install_dir/"
    else
        mv "$tmp_dir/$binary_name" "$install_dir/"
    fi

    print_status "Successfully installed airun-cli to $install_dir/$binary_name"
}

# Main installation process
main() {
    print_status "Starting airun-cli installation..."
    
    # Check for required tools
    check_requirements
    
    # Detect OS and architecture
    local os_arch
    os_arch=$(detect_os)
    print_status "Detected system: $os_arch"
    
    # Create necessary directories
    create_directories
    
    # Install binary
    install_binary "$os_arch"
    
    # Final setup
    print_status "Installation completed successfully!"
    print_status "To get started, run: airun-cli --help"
    
    # Notify about shell restart
    print_warning "Please restart your shell or run 'source ~/.bashrc' (or ~/.zshrc) to update your PATH"
}

# Run main installation
main 