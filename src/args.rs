use clap::Parser;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Commands>,

    #[arg(short, long)]
    pub setup: bool,
}

#[derive(clap::Subcommand)]
pub enum Commands {
    Chat {
        message: Option<String>,
        #[arg(short, long)]
        provider: Option<String>,
        #[arg(short, long)]
        model: Option<String>,
    },
    Code {
        message: Option<String>,
        #[arg(short, long, default_value = "python")]
        language: String,
        #[arg(short, long)]
        run: bool,
        #[arg(short, long)]
        provider: Option<String>,
        #[arg(short, long)]
        model: Option<String>,
    },
    Task {
        message: Option<String>,
        #[arg(short, long)]
        provider: Option<String>,
        #[arg(short, long)]
        model: Option<String>,
    },
    Config {
        #[arg(help = "Configuration key to get/set. Available keys:\n  \
               openai_api_key     - OpenAI API key\n  \
               anthropic_api_key  - Anthropic API key\n  \
               google_api_key     - Google API key for Gemini\n  \
               groq_api_key      - Groq API key\n  \
               default_model     - Default AI model to use\n  \
               default_provider  - Default AI provider (openai/anthropic/gemini/groq/ollama)\n  \
               history_size     - Number of messages to keep in chat history")]
        key: String,
        #[arg(help = "Value to set for the configuration key. If not provided, shows current value")]
        value: Option<String>,
    },
} 