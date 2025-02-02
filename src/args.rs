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
        #[arg(value_parser = parse_shell_string)]
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
        #[arg(value_parser = parse_shell_string)]
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
        #[arg(value_parser = parse_shell_string)]
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
        #[arg(value_parser = parse_shell_string)]
        query: String,
        /// Number of days to search back (default: 30)
        #[arg(short, long, default_value = "30")]
        days: u32,
    },
    /// Clear history
    Clear,
}

fn parse_shell_string(s: &str) -> Result<String, String> {
    let mut result = String::with_capacity(s.len());
    let mut chars = s.chars().peekable();
    let mut in_quotes = false;
    let mut escaped = false;

    while let Some(c) = chars.next() {
        match c {
            '\\' if !escaped => {
                escaped = true;
                continue;
            }
            '"' if !escaped => {
                in_quotes = !in_quotes;
                continue;
            }
            '!' if !escaped && !in_quotes => {
                // 히스토리 확장 문자를 일반 문자로 처리
                result.push('!');
            }
            _ => {
                if escaped {
                    match c {
                        'n' => result.push('\n'),
                        't' => result.push('\t'),
                        'r' => result.push('\r'),
                        _ => result.push(c),
                    }
                    escaped = false;
                } else {
                    result.push(c);
                }
            }
        }
    }

    if escaped {
        result.push('\\');
    }

    Ok(result)
} 