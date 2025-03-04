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
            print_error "Windows installation via script is not supported. Please download codai-windows.exe from: https://github.com/hamonikr/codai/releases"
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
        config_dir="$HOME/Library/Application Support/codai"
    else
        config_dir="$HOME/.config/codai"
    fi

    mkdir -p "$config_dir"
    print_status "Created configuration directory: $config_dir"
}

# Download and install binary
install_binary() {
    local os_arch=$1
    local tmp_dir
    local install_dir
    local binary_name="codai"
    local local_binary="target/x86_64-unknown-linux-gnu/release/codai"
    
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

    # Check if local binary exists
    if [ -f "$local_binary" ]; then
        print_status "Using locally built binary from $local_binary"
        cp "$local_binary" "$tmp_dir/$binary_name"
    else
        print_status "Downloading codai for ${os_arch}..."
        
        # Get the latest release URL
        local latest_release_url="https://github.com/hamonikr/codai/releases/latest/download/codai-${os_arch}"
        
        # Download binary
        if ! curl -sSL "$latest_release_url" -o "$tmp_dir/$binary_name"; then
            print_error "Failed to download codai"
            exit 1
        fi
    fi

    # Verify downloaded file
    if [ ! -s "$tmp_dir/$binary_name" ]; then
        print_error "Binary file is empty"
        exit 1
    fi

    # Check if file is a valid binary
    if ! file "$tmp_dir/$binary_name" | grep -q "ELF"; then
        print_error "File is not a valid binary"
        cat "$tmp_dir/$binary_name"
        exit 1
    fi

    # Install binary
    chmod +x "$tmp_dir/$binary_name"
    if [ "$(id -u)" -eq 0 ]; then
        mv "$tmp_dir/$binary_name" "$install_dir/"
    else
        mv "$tmp_dir/$binary_name" "$install_dir/"
    fi

    print_status "Successfully installed codai to $install_dir/$binary_name"
}

# Install completion scripts
install_completion() {
    local completion_dir
    local zsh_completion_dir
    
    # Bash completion
    if [ "$(id -u)" -eq 0 ]; then
        completion_dir="/usr/share/bash-completion/completions"
    else
        completion_dir="$HOME/.local/share/bash-completion/completions"
        mkdir -p "$completion_dir"
    fi
    
    # Zsh completion
    if [ "$(id -u)" -eq 0 ]; then
        zsh_completion_dir="/usr/share/zsh/site-functions"
    else
        zsh_completion_dir="$HOME/.local/share/zsh/site-functions"
        mkdir -p "$zsh_completion_dir"
    fi
    
    # Create bash completion script
    cat > "$completion_dir/codai" << 'EOF'
#!/bin/bash

_codai_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="chat code task config history help --setup --help --version"

    case "${prev}" in
        codai)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
        chat|code|task|config|history|help)
            COMPREPLY=( $(compgen -W "--help" -- ${cur}) )
            return 0
            ;;
        *)
            COMPREPLY=()
            return 0
            ;;
    esac
}

complete -F _codai_completion codai
EOF

    # Create zsh completion script
    cat > "$zsh_completion_dir/_codai" << 'EOF'
#compdef codai

_codai() {
    local -a commands
    commands=(
        'chat:Chat with AI'
        'code:Generate and execute code'
        'task:Execute complex task'
        'config:Configure settings'
        'history:History management'
        'help:Print help information'
    )

    _arguments -C \
        '(-h --help)'{-h,--help}'[Print help information]' \
        '(-V --version)'{-V,--version}'[Print version]' \
        '(-s --setup)'{-s,--setup}'[Setup configuration]' \
        '*:: :->subcmds' && return 0

    if (( CURRENT == 1 )); then
        _describe -t commands "codai subcommands" commands
        return
    fi

    case "$words[1]" in
        chat|code|task|config|history|help)
            _arguments \
                '(-h --help)'{-h,--help}'[Print help information]'
            ;;
    esac
}

_codai "$@"
EOF

    # Set permissions
    chmod +x "$completion_dir/codai" "$zsh_completion_dir/_codai"

    # Add completion to shell config if not already present
    local bash_completion_config="# Codai completion\nif [ -f $completion_dir/codai ]; then\n    . $completion_dir/codai\nfi"
    local zsh_completion_config="# Codai completion\nfpath=($zsh_completion_dir \$fpath)\nautoload -Uz compinit\ncompinit"
    
    # Add to .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "Codai completion" "$HOME/.bashrc"; then
            echo -e "\n$bash_completion_config" >> "$HOME/.bashrc"
        fi
    fi
    
    # Add to .zshrc if it exists
    if [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "Codai completion" "$HOME/.zshrc"; then
            echo -e "\n$zsh_completion_config" >> "$HOME/.zshrc"
        fi
    fi

    print_status "Installed shell completion scripts"
}

# Main installation process
main() {
    print_status "Starting codai installation..."
    
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
    
    # Install completion scripts
    install_completion
    
    # Final setup
    print_status "Installation completed successfully!"
    print_status "To get started, run: codai --help"
    
    # Notify about shell restart
    print_warning "Please restart your shell or run 'source ~/.bashrc' (or ~/.zshrc) to update your PATH and enable completions"
}

# Run main installation
main 