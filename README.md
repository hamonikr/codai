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

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/hamonikr/codai.git
cd codai

# Install development dependencies
cargo install --path .

# Run tests
cargo test

# Build in release mode
cargo build --release
```

## 📚 Technical Documentation

- [Technical Architecture](docs/architecture.md) - System design and component details
- [Feature Details](docs/features.md) - In-depth explanation of each feature
- [Core Technologies](docs/core-technologies.md) - Technical deep-dive into the core technologies

## 📄 License

This project is available under dual licensing:

### Community License (Apache License 2.0)
- Free for personal use, non-commercial organizations, and open source projects
- See [LICENSE.community](LICENSE.community) for details

### Commercial License
- Required for commercial use by companies and business organizations
- Includes additional features, support, and customization options
- See [LICENSE.commercial](LICENSE.commercial) for detailed terms and conditions
- Contact Information:
  - Email: sales@invesume.com
  - Tel: +82-2-2039-3977
  - Address: Suite 201, 17, Saimdang-ro 8-gil, Seocho-gu, Seoul, 06640 KOREA

For commercial licensing inquiries, please visit [Contact Us](https://invesume.com/contactus.html).
