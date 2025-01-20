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