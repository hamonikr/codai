Language: [English](README.md) | [한국어](README.ko.md)

[![Release](https://img.shields.io/github/v/release/hamonikr/codai)](https://github.com/hamonikr/codai/releases)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black)](https://github.com/hamonikr/codai)
[![macOS](https://img.shields.io/badge/macOS-000000?style=flat&logo=apple&logoColor=white)](https://github.com/hamonikr/codai)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white)](https://github.com/hamonikr/codai)
[![ARM](https://img.shields.io/badge/ARM-02569B?style=flat&logo=arm&logoColor=white)](https://github.com/hamonikr/codai)

The easiest way to bring powerful AI capabilities to your local machine. Built with Rust for maximum performance and reliability, codai lets you harness the power of various AI models directly from your terminal - no complex setup required.

## 🌟 Key Features

- **🚀 Powerful AI Integration**
  - Multiple AI providers support (OpenAI, Anthropic, Google, Groq, Ollama)
  - Smart context handling and token optimization
  - Real-time cost monitoring and analytics

- **💻 Developer-Centric Tools**
  - Intelligent code generation with context awareness
  - Automated code review and analysis
  - Direct code execution capabilities
  - Multi-language support
  - Built-in cost tracking for each AI provider

- **⚡ Performance & Reliability**
  - Built with Rust for maximum speed and stability
  - Efficient memory management
  - Optimized token usage
  - Automatic context summarization

- **🔧 Easy Setup & Use**
  - One-command installation
  - Zero configuration to start
  - Intuitive CLI interface
  - Cross-platform support

## 🔬 Core Technologies

- **🛠️ Built with Rust**
  - High-performance, memory-safe systems programming
  - Zero-cost abstractions
  - Thread safety and concurrent processing
  - Cross-platform compatibility

- **🧠 AI Integration**
  - Multiple model support (GPT-4, Claude-3, Gemini, Mixtral)
  - Efficient token management and context handling
  - Streaming responses with real-time processing
  - Custom prompt engineering and optimization

- **🤖 Agentic System Pattern**
  - Autonomous task planning and execution
  - Context-aware decision making
  - Self-improving prompt optimization
  - Dynamic tool selection and utilization
  - Adaptive error handling and recovery

- **⚡ Performance Optimization**
  - Asynchronous operations with Tokio
  - Efficient memory management
  - Smart caching system
  - Parallel processing capabilities

## Features

- 🤖 Multiple AI providers support (OpenAI, Anthropic, Google, Groq, Ollama)
- 💻 Code generation with multiple programming languages
- 🔄 Interactive code execution and feedback
- 📝 Code review and suggestions
- 🎯 Task analysis and step-by-step execution
- 🔍 Context-aware responses
- 📊 Usage tracking and cost estimation
- 📜 Command history management with advanced features
  - Automatic request logging with detailed information
  - Compressed archiving of old records
  - Search functionality across current and archived history
  - Usage statistics and cost tracking
  - Configurable retention policies

## Why codai?

- **Simple to Install**: One command to install, zero configuration needed to start
- **Multiple AI Providers**: Ready-to-use integrations with leading AI models
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude-3)
  - Google (Gemini)
  - Groq (Mixtral)
  - Ollama (Local models)

- **Developer-Focused Features**
  - Instant code generation with context awareness
  - Automated code review and analysis
  - Direct code execution support
  - Multi-language compatibility
  - Cost tracking and usage analytics for each AI provider

- **Smart Resource Management**
  - Optimized context handling for each AI provider
  - Efficient token usage
  - Dynamic conversation management
  - Automatic context summarization
  - Real-time token usage and cost monitoring

## 🚀 Quick Start

### One-Line Installation
```bash
# Linux/macOS
curl -sSL https://raw.githubusercontent.com/hamonikr/codai/main/install.sh | bash
```

### Basic Usage
```bash
# Generate code with AI
codai code "create a web scraper for news headlines" -r

# Get instant programming help
codai chat "explain async/await in Rust"

# Execute complex task from file
echo "1. Create a REST API server
2. Add user authentication
3. Implement CRUD operations for posts
4. Add API documentation" > task.txt && codai task < task.txt
```

## 📦 Installation Methods

### Package Managers
```bash
# Homebrew (macOS/Linux)
brew install codai

# Cargo (Rust package manager)
cargo install codai

# Windows (PowerShell)
winget install codai
```

### Manual Installation
1. Download the latest release for your platform from the [releases page](https://github.com/hamonikr/codai/releases)
2. Extract the archive
3. Add the binary to your system PATH

## ⚙️ Configuration

### Using Setup Wizard
The easiest way to configure codai is to use the setup wizard:
```bash
codai --setup
```
This command will start an interactive setup wizard that guides you through all necessary configurations.

### Manual Configuration
Create a configuration file at `~/.config/codai/config.toml` (Linux/macOS) or `%APPDATA%\codai\config.toml` (Windows):

```toml
[api]
openai_api_key = "your-openai-key"
anthropic_api_key = "your-anthropic-key"
google_api_key = "your-google-key"
groq_api_key = "your-groq-key"

[defaults]
model = "gpt-4"
temperature = 0.7
max_tokens = 2000

[advanced]
context_window = 8000
cache_dir = "~/.cache/codai"
```

### Command-line Configuration

You can also configure settings using the `codai config` command:

```bash
# Set API keys
codai config openai_api_key "your-api-key"

# Set default model
codai config default_model "gpt-4"

# Set default provider
codai config default_provider "openai"

# Check current settings
codai config openai_api_key
codai config default_model
codai config default_provider
```

Additionally, you can specify the provider and model for one-time use with each command:
```bash
codai chat --provider openai --model gpt-4 "your question"
codai code --provider anthropic --model claude-3 "code generation request"
codai task --provider google --model gemini-pro "task request"
```

### History Management

Codai now includes a comprehensive history management system that helps you track and analyze your AI interactions:

```bash
# View history statistics
codai config history_stats

# Search through history
codai config history_search "your search query"

# Configure history settings
codai config history_enabled true/false        # Enable/disable history feature
codai config history_max_items 1000            # Set maximum number of recent items to keep
codai config history_retention_days 30         # Set archive retention period in days
```

#### History Features

- **Automatic Logging**: Every interaction is automatically logged with:
  - Timestamp and unique ID
  - Request type and message
  - Used model and provider
  - Token usage and estimated costs
  - Execution time

- **Smart Archiving**:
  - Old records are automatically compressed and archived
  - Archives are stored in `~/.config/codai/history_archives/` (Linux/macOS) or `%APPDATA%\codai\history_archives\` (Windows)
  - Configurable retention period for archived records

- **Statistics and Analysis**:
  - Total requests and token usage
  - Cumulative cost tracking
  - Most used models and providers
  - Detailed usage patterns

- **Search Capabilities**:
  - Search through both current and archived history
  - Filter by date range
  - Search in message content and request types
  - Results sorted by date

#### History File Structure

The history is stored in the following locations:
- Current history: `~/.config/codai/history.json`
- Archives: `~/.config/codai/history_archives/*.json.gz`

Each history entry contains:
```json
{
    "id": "unique-uuid",
    "timestamp": "2024-03-21T12:34:56Z",
    "request_type": "chat|code|task",
    "message": "user request message",
    "model": "used-model-name",
    "provider": "ai-provider-name",
    "tokens": {
        "input": 123,
        "output": 456
    },
    "estimated_cost": 0.123,
    "execution_time": 1.23
}
```