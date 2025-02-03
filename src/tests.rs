use crate::config::Config;
use crate::chat::{ChatRequest, Provider};
use crate::types::ExecutionResult;
use crate::Cli;
use clap::Parser;

#[cfg(test)]
mod tests {
    use super::*;

    // CLI 명령어 테스트
    #[test]
    fn test_cli_commands() {
        // --setup 명령어 테스트
        let args = vec!["codai", "--setup"];
        let cli = Cli::try_parse_from(args).expect("Failed to parse setup command");
        assert!(cli.setup == true);
        assert!(cli.command.is_none());

        // chat 명령어 테스트
        let args = vec!["codai", "chat", "Hello", "--provider", "openai", "--model", "gpt-3.5-turbo"];
        let cli = Cli::try_parse_from(args).expect("Failed to parse chat command with options");
        if let Some(cmd) = cli.command {
            match cmd {
                crate::Commands::Chat { message, provider, model } => {
                    assert_eq!(message, Some("Hello".to_string()));
                    assert_eq!(provider, Some("openai".to_string()));
                    assert_eq!(model, Some("gpt-3.5-turbo".to_string()));
                }
                _ => panic!("Expected Chat command"),
            }
        }

        // code 명령어 테스트
        let args = vec![
            "codai", "code", "print hello",
            "--language", "python",
            "--run",
            "--provider", "openai",
            "--model", "gpt-3.5-turbo"
        ];
        let cli = Cli::try_parse_from(args).expect("Failed to parse code command with options");
        if let Some(cmd) = cli.command {
            match cmd {
                crate::Commands::Code { message, language, run, provider, model } => {
                    assert_eq!(message, Some("print hello".to_string()));
                    assert_eq!(language, "python");
                    assert_eq!(run, true);
                    assert_eq!(provider, Some("openai".to_string()));
                    assert_eq!(model, Some("gpt-3.5-turbo".to_string()));
                }
                _ => panic!("Expected Code command"),
            }
        }

        // config 명령어 테스트
        let args = vec!["codai", "config", "openai_api_key", "test_key"];
        let cli = Cli::try_parse_from(args).expect("Failed to parse config command");
        if let Some(cmd) = cli.command {
            match cmd {
                crate::Commands::Config { key, value, history_command } => {
                    assert_eq!(key, "openai_api_key");
                    assert_eq!(value, Some("test_key".to_string()));
                    assert!(history_command.is_none());
                }
                _ => panic!("Expected Config command"),
            }
        }
    }

    // 설정 구조체 테스트
    #[test]
    fn test_config_struct() {
        let config = Config {
            default_provider: Some("openai".to_string()),
            default_model: Some("gpt-3.5-turbo".to_string()),
            history_size: Some(10),
            ..Default::default()
        };

        assert_eq!(config.default_provider, Some("openai".to_string()));
        assert_eq!(config.default_model, Some("gpt-3.5-turbo".to_string()));
        assert_eq!(config.history_size, Some(10));
        assert_eq!(config.openai_api_key, None);
    }

    // 채팅 요청 테스트
    #[test]
    fn test_chat_request() {
        let request = ChatRequest {
            message: "Hello".to_string(),
            model: Some("gpt-3.5-turbo".to_string()),
            provider: Some(Provider::OpenAI),
        };
        
        assert_eq!(request.message, "Hello");
        assert_eq!(request.model, Some("gpt-3.5-turbo".to_string()));
        assert!(matches!(request.provider, Some(Provider::OpenAI)));
    }

    // 실행 결과 테스트
    #[test]
    fn test_execution_result() {
        let result = ExecutionResult {
            stdout: "Hello, World!".to_string(),
            stderr: String::new(),
            success: true,
        };
        
        assert!(result.success);
        assert_eq!(result.stdout, "Hello, World!");
        assert!(result.stderr.is_empty());
    }
} 