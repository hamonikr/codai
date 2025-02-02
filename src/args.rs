use clap::Parser;

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Commands>,

    #[arg(short, long)]
    pub setup: bool,
}

#[derive(clap::Subcommand, Debug)]
pub enum Commands {
    /// Chat with AI
    Chat {
        /// Message to send
        message: Option<String>,
        /// AI provider to use
        #[arg(long)]
        provider: Option<String>,
        /// Model to use
        #[arg(long)]
        model: Option<String>,
    },
    /// Generate and execute code
    Code {
        /// Code generation prompt
        message: Option<String>,
        /// Programming language
        #[arg(short, long, default_value = "python")]
        language: String,
        /// Execute the generated code
        #[arg(short, long)]
        run: bool,
        /// AI provider to use
        #[arg(long)]
        provider: Option<String>,
        /// Model to use
        #[arg(long)]
        model: Option<String>,
    },
    /// Execute complex task
    Task {
        /// Task description
        message: Option<String>,
        /// AI provider to use
        #[arg(long)]
        provider: Option<String>,
        /// Model to use
        #[arg(long)]
        model: Option<String>,
    },
    /// Configure settings
    Config {
        /// Configuration key
        key: String,
        /// Configuration value
        value: Option<String>,
        /// History subcommand
        #[command(subcommand)]
        history_command: Option<HistoryCommands>,
    },
    /// History management
    History {
        /// History subcommand
        #[command(subcommand)]
        command: HistoryCommands,
    },
}

#[derive(clap::Subcommand, Debug)]
pub enum HistoryCommands {
    /// Show history statistics
    Stats,
    /// Search history
    Search {
        /// Search query
        query: String,
        /// Number of days to search back (default: 30)
        #[arg(short, long, default_value = "30")]
        days: u32,
    },
    /// Clear history
    Clear,
} 