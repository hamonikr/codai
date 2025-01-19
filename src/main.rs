mod config;
mod ui;
mod code_executor;
mod code_generator;
mod chat;
mod prompts;
mod args;
pub mod providers;
mod task_executor;
mod task;
mod types;
#[cfg(test)]
mod tests;

use colored::*;
use anyhow::Result;
use std::io::Write;
use crate::config::{Config, ConfigValidationError};
use crate::ui::display_logo;
use crate::code_executor::execute_python_code;
use crate::code_generator::generate_code;
use crate::types::CodeRequest;
use crate::chat::ChatRequest;
use crate::args::{Cli, Commands};
use clap::Parser;
use crate::ui::Menu;
use spinners::{Spinner, Spinners};
use crate::task_executor::TaskManager;

async fn handle_chat_command(
    message: Option<String>,
    provider: Option<String>,
    model: Option<String>,
    config: &Config,
) -> Result<()> {
    println!("{}", "Starting chat with AI...".green());
    
    let input = if let Some(msg) = message {
        msg
    } else {
        let mut buffer = String::new();
        std::io::stdin().read_line(&mut buffer)?;
        buffer.trim().to_string()
    };

    let request = ChatRequest {
        message: input,
        model,
        provider: provider.as_ref().and_then(|p| chat::Provider::from_str(p)),
    };

    let response = chat::chat(request, config).await?;
    println!("\n{}", "AI:".cyan());
    println!("{}", response.message);
    Ok(())
}

async fn handle_code_command(
    message: Option<String>,
    language: String,
    run: bool,
    feedback: Option<String>,
    provider: Option<String>,
    model: Option<String>,
    config: &Config,
) -> Result<()> {
    let current_message = if let Some(msg) = message {
        msg
    } else {
        let mut buffer = String::new();
        std::io::stdin().read_line(&mut buffer)?;
        buffer.trim().to_string()
    };

    let mut sp = Spinner::new(Spinners::Dots9, "Generating code...".cyan().to_string());

    let request = CodeRequest {
        message: current_message.clone(),
        language: Some(language.clone()),
        model: model.clone(),
        feedback,
        error_message: None,
        execution_result: None,
        provider: provider.clone(),
        task_id: None,
    };

    let start_time = std::time::Instant::now();
    let mut api_calls = std::collections::HashMap::new();
    let mut token_counts = std::collections::HashMap::new();

    let mut response = match code_generator::generate_code(request, config).await {
        Ok(response) => {
            sp.stop();
            // API 호출 및 토큰 수 기록
            let model_name = model.clone().unwrap_or_else(|| config.default_model.clone().unwrap_or_else(|| "gpt-3.5-turbo".to_string()));
            *api_calls.entry(model_name.clone()).or_insert(0) += 1;
            if let (Some(input), Some(output)) = (response.input_tokens, response.output_tokens) {
                token_counts.insert(model_name, (input, output));
            }
            response
        }
        Err(e) => {
            sp.stop();
            println!("\n{} {}", "✗".red(), "Code generation failed".red());
            match e.to_string() {
                s if s.contains("API key") => {
                    println!("\n{}", "Error: Invalid or missing API key. Please check your configuration.".red());
                }
                s if s.contains("rate limit") => {
                    println!("\n{}", "Error: Rate limit exceeded. Please try again later.".red());
                }
                s if s.contains("timeout") => {
                    println!("\n{}", "Error: Request timed out. Please check your internet connection.".red());
                }
                _ => {
                    println!("\n{}", format!("Error generating code: {}", e).red());
                }
            }
            return Ok(());
        }
    };

    if run {
        if language == "python" {
            println!("\n{}", "=".repeat(80).yellow());
            println!("{}", "Generated code:".cyan());
            println!("{}", response.code);
            println!();

            execute_python_code(
                &response.code,
                &current_message,
                &language,
                config,
                &provider,
            ).await?;

            // 실행 통계 출력
            let elapsed = start_time.elapsed();
            println!("\n{}\n", "===== Execution Statistics =====".cyan());
            println!("⏱️  Total Execution Time: {:.2} seconds\n", elapsed.as_secs_f64());

            println!("🤖 API Calls and Token Usage:");
            for (model, count) in &api_calls {
                if let Some((input, output)) = token_counts.get(model) {
                    println!("  • {}: {} calls ({} input tokens, {} output tokens)", 
                        model, count, input, output);
                } else {
                    println!("  • {}: {} calls", model, count);
                }
            }

            println!("\n💰 Estimated Costs:");
            let mut total_cost = 0.0;
            for (model, (input, output)) in &token_counts {
                let cost = match model.as_str() {
                    // OpenAI 모델
                    "gpt-4" => ((*input as f64 * 0.03) + (*output as f64 * 0.06)) / 1000.0,
                    "gpt-3.5-turbo" => ((*input as f64 * 0.001) + (*output as f64 * 0.002)) / 1000.0,
                    // Anthropic 모델
                    "claude-3-opus-20240229" => ((*input as f64 * 0.015) + (*output as f64 * 0.075)) / 1000.0,
                    "claude-3-sonnet-20240229" => ((*input as f64 * 0.003) + (*output as f64 * 0.015)) / 1000.0,
                    // Google 모델
                    "gemini-pro" => ((*input as f64 + *output as f64) * 0.00025) / 1000.0,
                    // Groq 모델
                    "mixtral-8x7b-32768" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
                    "llama2-70b-4096" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
                    // 기본값
                    _ => 0.0,
                };
                total_cost += cost;
                println!("  • {}: ${:.4} ({:.1}K tokens)", 
                    model, cost, (*input + *output) as f64 / 1000.0);
            }

            println!("\n💵 Total Estimated Cost: ${:.4}", total_cost);

            display_logo(env!("CARGO_PKG_VERSION"));
            return Ok(());
        } else {
            println!("Running code in {} is not supported yet.", language);
        }
    }

    // 메뉴는 run 옵션이 false일 때만 표시
    let menu_options = vec![
        "Execute code".to_string(),
        "Regenerate code".to_string(),
        "Modify prompt".to_string(),
        "Exit program".to_string()
    ];
    
    let mut menu = Menu::new(menu_options);
    menu.display(&response);
    
    loop {
        if let Some(selected) = menu.handle_input()? {
            match selected {
                0 => {
                    if language == "python" {
                        execute_python_code(
                            &response.code,
                            &current_message,
                            &language,
                            config,
                            &provider,
                        ).await?;

                        display_logo(env!("CARGO_PKG_VERSION"));
                        return Ok(());
                    } else {
                        println!("Currently only Python code execution is supported.");
                    }
                    println!("\nPress Enter to continue...");
                    let mut input = String::new();
                    std::io::stdin().read_line(&mut input)?;
                    menu.display(&response);
                }
                1 => {
                    println!("\n{}", "Regenerating code...".yellow());
                    let request = CodeRequest {
                        message: current_message.clone(),
                        language: Some(language.clone()),
                        model: model.clone(),
                        feedback: None,
                        error_message: None,
                        execution_result: None,
                        provider: provider.clone(),
                        task_id: None,
                    };

                    let new_response = generate_code(request, config).await?;
                    response = new_response;
                    menu.display(&response);
                }
                2 => {
                    loop {
                        println!("\n{}", "Please enter new prompt:".yellow());
                        print!("New prompt: ");
                        std::io::stdout().flush()?;

                        let mut new_prompt = String::new();
                        std::io::stdin().read_line(&mut new_prompt)?;
                        let new_message = new_prompt.trim().to_string();

                        // 빈 입력이면 이전 메뉴로 돌아갑니다
                        if new_message.is_empty() {
                            menu.display(&response);
                            break;
                        }

                        let mut sp = Spinner::new(Spinners::Dots9, "Generating code...".cyan().to_string());

                        let request = CodeRequest {
                            message: new_message.clone(),
                            language: Some(language.clone()),
                            model: model.clone(),
                            feedback: None,
                            error_message: None,
                            execution_result: None,
                            provider: provider.clone(),
                            task_id: None,
                        };

                        let new_response = match generate_code(request, config).await {
                            Ok(response) => {
                                sp.stop();
                                response
                            }
                            Err(e) => {
                                sp.stop();
                                println!("\n{} {}", "✗".red(), "Code generation failed".red());
                                println!("\n{}", format!("Error generating code: {}", e).red());
                                continue;
                            }
                        };
                        
                        response = new_response;
                        menu.reset_selection();  // 선택된 항목을 Execute code로 재설정
                        menu.display(&response);
                        break;  // 새 코드가 생성된 후 loop를 종료하고 메인 메뉴로 돌아갑니다
                    }
                }
                3 => break,
                _ => {}
            }
        }
    }

    // 실행 통계 출력
    let elapsed = start_time.elapsed();
    println!("\n{}\n", "===== Execution Statistics =====".cyan());
    println!("⏱️  Total Execution Time: {:.2} seconds\n", elapsed.as_secs_f64());

    println!("🤖 API Calls and Token Usage:");
    for (model, count) in &api_calls {
        if let Some((input, output)) = token_counts.get(model) {
            println!("  • {}: {} calls ({} input tokens, {} output tokens)", 
                model, count, input, output);
        } else {
            println!("  • {}: {} calls", model, count);
        }
    }

    println!("\n💰 Estimated Costs:");
    let mut total_cost = 0.0;
    for (model, (input, output)) in &token_counts {
        let cost = match model.as_str() {
            // OpenAI 모델
            "gpt-4" => ((*input as f64 * 0.03) + (*output as f64 * 0.06)) / 1000.0,
            "gpt-3.5-turbo" => ((*input as f64 * 0.001) + (*output as f64 * 0.002)) / 1000.0,
            // Anthropic 모델
            "claude-3-opus-20240229" => ((*input as f64 * 0.015) + (*output as f64 * 0.075)) / 1000.0,
            "claude-3-sonnet-20240229" => ((*input as f64 * 0.003) + (*output as f64 * 0.015)) / 1000.0,
            // Google 모델
            "gemini-pro" => ((*input as f64 + *output as f64) * 0.00025) / 1000.0,
            // Groq 모델
            "mixtral-8x7b-32768" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
            "llama2-70b-4096" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
            // 기본값
            _ => 0.0,
        };
        total_cost += cost;
        println!("  • {}: ${:.4} ({:.1}K tokens)", 
            model, cost, (*input + *output) as f64 / 1000.0);
    }

    println!("\n💵 Total Estimated Cost: ${:.4}", total_cost);

    Ok(())
}

async fn handle_task_command(
    message: Option<String>,
    provider: Option<String>,
    model: Option<String>,
    config: &Config,
) -> Result<()> {
    println!("{}", "Starting task analysis...".green());
    
    let input = if let Some(msg) = message {
        msg
    } else {
        let mut buffer = String::new();
        std::io::stdin().read_line(&mut buffer)?;
        buffer.trim().to_string()
    };

    let request = CodeRequest {
        message: input,
        language: Some("python".to_string()),
        model,
        feedback: None,
        error_message: None,
        execution_result: None,
        provider,
        task_id: None,
    };

    let mut task_manager = TaskManager::new();
    
    // 작업 분석 및 단계 생성
    let steps = task_executor::analyze_task(&request, config).await?;
    
    // 분석된 단계들을 TaskManager에 추가
    for step in steps {
        task_manager.add_step(step)?;
    }
    
    // 작업 실행
    task_executor::execute_task(&mut task_manager, config, &request).await?;
    
    Ok(())
}

fn handle_config_command(key: String, value: Option<String>) -> Result<()> {
    let mut config = Config::load()?;
    match (key.as_str(), value) {
        ("openai_api_key", Some(val)) => {
            config.openai_api_key = Some(val);
        }
        ("default_model", Some(val)) => {
            config.default_model = Some(val);
        }
        ("default_provider", Some(val)) => {
            config.default_provider = Some(val);
        }
        ("history_size", Some(val)) => {
            if let Ok(size) = val.parse::<u32>() {
                config.history_size = Some(size);
            } else {
                println!("Invalid value. Please enter a number.");
                return Ok(());
            }
        }
        ("code_review_enabled", Some(val)) => {
            match val.to_lowercase().as_str() {
                "true" | "yes" | "1" | "on" => config.code_review_enabled = Some(true),
                "false" | "no" | "0" | "off" => config.code_review_enabled = Some(false),
                _ => {
                    println!("Invalid value. Please use true/false, yes/no, 1/0, or on/off.");
                    return Ok(());
                }
            }
        }
        (key, None) => {
            match key {
                "openai_api_key" => println!("OpenAI API key: {}", config.openai_api_key.as_deref().unwrap_or("")),
                "default_model" => println!("Default model: {}", config.default_model.as_deref().unwrap_or("")),
                "default_provider" => println!("Default provider: {}", config.default_provider.as_deref().unwrap_or("")),
                "history_size" => println!("Chat history size: {}", config.history_size.unwrap_or(0)),
                "code_review_enabled" => println!("Code review feature: {}", if config.code_review_enabled.unwrap_or(true) { "enabled" } else { "disabled" }),
                _ => println!("Unknown configuration key: {}", key),
            }
            return Ok(());
        }
        _ => {
            println!("Unknown configuration key: {}", key);
            return Ok(());
        }
    }
    config.save()?;
    println!("Configuration updated successfully.");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize default prompts
    if let Err(e) = prompts::init_default_prompts() {
        eprintln!("Warning: Failed to initialize default prompts: {}", e);
    }

    let cli = Cli::parse();

    if cli.setup {
        display_logo(env!("CARGO_PKG_VERSION"));
        return config::setup_config();
    }

    match cli.command {
        None => {
            let config = Config::load()?;
            
            // 시스템 요구사항 체크
            if let Err(e) = config.check_system_requirements() {
                let message = Config::get_system_requirements_message(&e);
                println!("{}", message);
                return Ok(());
            }

            // 설정 유효성 검사
            if let Err(e) = config.validate() {
                match e {
                    ConfigValidationError::MissingProvider => 
                        println!("AI provider is not configured."),
                    ConfigValidationError::MissingModel => 
                        println!("AI model is not configured."),
                    ConfigValidationError::MissingApiKey(provider) => 
                        println!("{} API key is not configured.", provider),
                    ConfigValidationError::InvalidOllamaHost => 
                        println!("Invalid Ollama host configuration."),
                }
                println!("\nRunning setup wizard...\n");
                display_logo(env!("CARGO_PKG_VERSION"));
                return config::setup_config();
            }

            // 설정이 올바른 경우 도움말 표시
            display_logo(env!("CARGO_PKG_VERSION"));
            Cli::try_parse_from(&["airun", "--help"])?;
            Ok(())
        }
        Some(Commands::Chat { message, provider, model }) => {
            handle_chat_command(message, provider, model, &Config::load()?).await
        }
        Some(Commands::Code { message, language, run, feedback, provider, model }) => {
            handle_code_command(
                message,
                language,
                run,
                feedback,
                provider,
                model,
                &Config::load()?,
            ).await
        }
        Some(Commands::Task { message, provider, model }) => {
            handle_task_command(message, provider, model, &Config::load()?).await
        }
        Some(Commands::Config { key, value }) => {
            handle_config_command(key, value)
        }
    }
}
