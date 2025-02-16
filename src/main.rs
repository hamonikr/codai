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
mod history;
#[cfg(test)]
mod tests;

use colored::*;
use anyhow::Result;
use std::io::Write;
use crate::config::{Config, ConfigValidationError};
use crate::ui::display_logo;
use crate::code_executor::execute_code_with_retry;
use crate::code_generator::generate_code;
use crate::types::{CodeRequest, ExecutionResult};
use crate::chat::ChatRequest;
use crate::args::{Cli, Commands};
use clap::Parser;
use crate::ui::Menu;
use spinners::{Spinner, Spinners};
use crate::task_executor::TaskManager;
use crate::history::{HistoryManager, RequestHistory};
use env_logger;

async fn handle_chat_command(
    message: Option<String>,
    provider: Option<String>,
    model: Option<String>,
    config: &Config,
) -> Result<()> {
    let start_time = std::time::Instant::now();
    println!("{}", "Starting chat with AI...".green());
    
    let input = if let Some(msg) = message {
        msg
    } else {
        let mut buffer = String::new();
        std::io::stdin().read_line(&mut buffer)?;
        buffer.trim().to_string()
    };

    let request = ChatRequest {
        message: input.clone(),
        model: model.clone(),
        provider: provider.as_ref().and_then(|p| chat::Provider::from_str(p)),
    };

    let response = chat::chat(request, config).await?;
    println!("\n{}", "AI:".cyan());
    println!("{}", response.message);

    if config.history_enabled.unwrap_or(true) {
        let mut history_manager = HistoryManager::new(
            config.history_max_items.unwrap_or(1000),
            config.history_retention_days.unwrap_or(30),
        )?;

        history_manager.add_request(RequestHistory {
            id: uuid::Uuid::new_v4().to_string(),
            timestamp: chrono::Utc::now(),
            request_type: "chat".to_string(),
            message: input,
            model,
            provider: provider.clone(),
            tokens: response.token_usage.map(|usage| history::TokenUsage {
                input: usage.0,
                output: usage.1,
            }),
            estimated_cost: response.estimated_cost,
            execution_time: start_time.elapsed().as_secs_f64(),
        })?;
    }

    Ok(())
}

async fn handle_code_command(
    message: Option<String>,
    language: String,
    run: bool,
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

    let spinner_text = if cfg!(windows) {
        "Generating code...".to_string()
    } else {
        "Generating code...".cyan().to_string()
    };
    let mut sp = Spinner::new(Spinners::Dots9, spinner_text);

    let request = CodeRequest {
        message: current_message.clone(),
        language: Some(language.clone()),
        model: model.clone(),
        feedback: None,
        error_message: None,
        execution_result: None,
        provider: provider.clone(),
        task_id: None,
        code_context: None,
    };

    let start_time = std::time::Instant::now();
    let mut api_calls = std::collections::HashMap::new();
    let mut token_counts = std::collections::HashMap::new();

    let mut response = match code_generator::generate_code(request, config).await {
        Ok(response) => {
            sp.stop();
            // API calls and token count recording
            let model_name = model.clone().unwrap_or_else(|| config.default_model.clone().unwrap_or_else(|| "gpt-3.5-turbo".to_string()));
            *api_calls.entry(model_name.clone()).or_insert(0) += 1;
            if let (Some(input), Some(output)) = (response.input_tokens, response.output_tokens) {
                token_counts.insert(model_name, (input, output));
            }
            response
        }
        Err(e) => {
            sp.stop();
            if cfg!(windows) {
                println!("\nX Code generation failed");
                match e.to_string() {
                    s if s.contains("API key") => {
                        println!("\nError: Invalid or missing API key. Please check your configuration.");
                    }
                    s if s.contains("rate limit") => {
                        println!("\nError: Rate limit exceeded. Please try again later.");
                    }
                    s if s.contains("timeout") => {
                        println!("\nError: Request timed out. Please check your internet connection.");
                    }
                    _ => {
                        println!("\nError generating code: {}", e);
                    }
                }
            } else {
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

            let result = execute_code_with_retry(
                &current_message,
                &language,
                config,
                provider.clone(),
                Some(response.code.clone())
            ).await?;

            // 실행 결과 출력
            if result.success {
                if !result.stdout.trim().is_empty() {
                    println!("\n{}", "Execution output:".cyan());
                    println!("{}", result.stdout);
                }
                if !result.stderr.trim().is_empty() {
                    println!("\n{}", "Execution warnings:".yellow());
                    println!("{}", result.stderr);
                }
                println!("\n{}", "✓ Code executed successfully".green());

                // 실행이 성공한 경우에만 리뷰 수행
                if config.code_review_enabled.unwrap_or(true) {
                    let review_request = CodeRequest {
                        message: response.code.clone(),
                        language: None,
                        model: model.clone(),
                        feedback: None,
                        error_message: None,
                        execution_result: Some(ExecutionResult {
                            stdout: result.stdout.clone(),
                            stderr: result.stderr.clone(),
                            success: result.success,
                        }),
                        provider,
                        task_id: None,
                        code_context: None,
                    };

                    if let Ok(review_response) = code_generator::generate_code(review_request, config).await {
                        if let Some(review) = review_response.review {
                            println!("\n{}", "Code Review:".cyan());
                            println!("{}", review);
                            
                            // API 호출 및 토큰 카운트 기록 업데이트
                            let model_name = model.clone().unwrap_or_else(|| config.default_model.clone().unwrap_or_else(|| "gpt-3.5-turbo".to_string()));
                            *api_calls.entry(model_name.clone()).or_insert(0) += 1;
                            if let (Some(input), Some(output)) = (review_response.input_tokens, review_response.output_tokens) {
                                if let Some((prev_input, prev_output)) = token_counts.get_mut(&model_name) {
                                    *prev_input += input;
                                    *prev_output += output;
                                } else {
                                    token_counts.insert(model_name, (input, output));
                                }
                            }
                        }
                    }
                }

                // Print execution statistics
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
                        // OpenAI models
                        "gpt-4" => ((*input as f64 * 0.03) + (*output as f64 * 0.06)) / 1000.0,
                        "gpt-3.5-turbo" => ((*input as f64 * 0.001) + (*output as f64 * 0.002)) / 1000.0,
                        // Anthropic models
                        "claude-3-opus-20240229" => ((*input as f64 * 0.015) + (*output as f64 * 0.075)) / 1000.0,
                        "claude-3-sonnet-20240229" => ((*input as f64 * 0.003) + (*output as f64 * 0.015)) / 1000.0,
                        // Google models
                        "gemini-pro" => ((*input as f64 + *output as f64) * 0.00025) / 1000.0,
                        // Groq models
                        "mixtral-8x7b-32768" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
                        "llama2-70b-4096" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
                        // Default value
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
                println!("\n{}", "Code execution failed:".red());
                println!("{}", result.stderr);
            }

            display_logo(env!("CARGO_PKG_VERSION"));
            return Ok(());
        } else {
            println!("Running code in {} is not supported yet.", language);
        }
    }

    // Menu is only displayed when run option is false
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
                        let result = execute_code_with_retry(
                            &current_message,
                            &language,
                            config,
                            provider,
                            Some(response.code.clone())
                        ).await?;

                        // 실행 결과 출력
                        if result.success {
                            if !result.stdout.trim().is_empty() {
                                println!("\n{}", "Execution output:".cyan());
                                println!("{}", result.stdout);
                            }
                            if !result.stderr.trim().is_empty() {
                                println!("\n{}", "Execution warnings:".yellow());
                                println!("{}", result.stderr);
                            }
                            println!("\n{}", "✓ Code executed successfully".green());
                        } else {
                            println!("\n{}", "Code execution failed:".red());
                            println!("{}", result.stderr);
                        }

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
                        code_context: None,
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

                        // Return to previous menu on empty input
                        if new_message.is_empty() {
                            menu.display(&response);
                            break;
                        }

                        let spinner_text = if cfg!(windows) {
                            "Generating code...".to_string()
                        } else {
                            "Generating code...".cyan().to_string()
                        };
                        let mut sp = Spinner::new(Spinners::Dots9, spinner_text);

                        let request = CodeRequest {
                            message: new_message.clone(),
                            language: Some(language.clone()),
                            model: model.clone(),
                            feedback: None,
                            error_message: None,
                            execution_result: None,
                            provider: provider.clone(),
                            task_id: None,
                            code_context: None,
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
                        menu.reset_selection();  // Reset selected item to Execute code
                        menu.display(&response);
                        break;  // Return to main menu after new code is generated
                    }
                }
                3 => break,
                _ => {}
            }
        }
    }

    // Print execution statistics
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
            // OpenAI models
            "gpt-4" => ((*input as f64 * 0.03) + (*output as f64 * 0.06)) / 1000.0,
            "gpt-3.5-turbo" => ((*input as f64 * 0.001) + (*output as f64 * 0.002)) / 1000.0,
            // Anthropic models
            "claude-3-opus-20240229" => ((*input as f64 * 0.015) + (*output as f64 * 0.075)) / 1000.0,
            "claude-3-sonnet-20240229" => ((*input as f64 * 0.003) + (*output as f64 * 0.015)) / 1000.0,
            // Google models
            "gemini-pro" => ((*input as f64 + *output as f64) * 0.00025) / 1000.0,
            // Groq models
            "mixtral-8x7b-32768" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
            "llama2-70b-4096" => ((*input as f64 + *output as f64) * 0.0007) / 1000.0,
            // Default value
            _ => 0.0,
        };
        total_cost += cost;
        println!("  • {}: ${:.4} ({:.1}K tokens)", 
            model, cost, (*input + *output) as f64 / 1000.0);
    }

    println!("\n💵 Total Estimated Cost: ${:.4}", total_cost);

    display_logo(env!("CARGO_PKG_VERSION"));
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
        code_context: None,
    };

    let mut task_manager = TaskManager::new();
    
    // Task analysis and step generation
    let steps = task_executor::analyze_task(&request, config).await?;
    
    // Add analyzed steps to TaskManager
    for step in steps {
        task_manager.add_step(step)?;
    }
    
    // Execute tasks
    task_executor::execute_task(&mut task_manager, config, &request).await?;
    
    Ok(())
}

async fn handle_config_command(key: String, value: Option<String>, history_command: Option<args::HistoryCommands>) -> Result<()> {
    let mut config = Config::load()?;

    // 히스토리 서브커맨드가 있는 경우 처리
    if let Some(history_cmd) = history_command {
        return handle_history_command(history_cmd, &config).await;
    }

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
        ("history_enabled", Some(val)) => {
            match val.to_lowercase().as_str() {
                "true" | "yes" | "1" | "on" => config.history_enabled = Some(true),
                "false" | "no" | "0" | "off" => config.history_enabled = Some(false),
                _ => {
                    println!("Invalid value. Please use true/false, yes/no, 1/0, or on/off.");
                    return Ok(());
                }
            }
        }
        ("history_max_items", Some(val)) => {
            if let Ok(size) = val.parse::<u32>() {
                config.history_max_items = Some(size);
            } else {
                println!("Invalid value. Please enter a number.");
                return Ok(());
            }
        }
        ("history_retention_days", Some(val)) => {
            if let Ok(days) = val.parse::<u32>() {
                config.history_retention_days = Some(days);
            } else {
                println!("Invalid value. Please enter a number.");
                return Ok(());
            }
        }
        ("history_stats", None) => {
            if let Some(true) = config.history_enabled {
                let history_manager = HistoryManager::new(
                    config.history_max_items.unwrap_or(1000),
                    config.history_retention_days.unwrap_or(30),
                )?;
                
                if let Ok(stats) = history_manager.get_statistics() {
                    println!("\n=== History Statistics ===");
                    println!("Total Requests: {}", stats.total_requests);
                    println!("Total Tokens: {} (input: {}, output: {})",
                        stats.total_tokens.input + stats.total_tokens.output,
                        stats.total_tokens.input,
                        stats.total_tokens.output);
                    println!("Total Estimated Cost: ${:.4}", stats.total_cost);
                    println!("Most Used Model: {}", stats.most_used_model);
                    println!("Most Used Provider: {}", stats.most_used_provider);
                }
            } else {
                println!("History feature is disabled.");
            }
            return Ok(());
        }
        ("history_search", Some(query)) => {
            if let Some(true) = config.history_enabled {
                let history_manager = HistoryManager::new(
                    config.history_max_items.unwrap_or(1000),
                    config.history_retention_days.unwrap_or(30),
                )?;
                
                if let Ok(results) = history_manager.search_history(&query, 30) {
                    println!("\n=== Search Results ===");
                    for (i, request) in results.iter().enumerate() {
                        println!("\n{}. [{}] {}", 
                            i + 1,
                            request.timestamp.format("%Y-%m-%d %H:%M:%S"),
                            request.message);
                        if let Some(model) = &request.model {
                            println!("   Model: {}", model);
                        }
                        if let Some(tokens) = &request.tokens {
                            println!("   Tokens: {} (in: {}, out: {})",
                                tokens.input + tokens.output,
                                tokens.input,
                                tokens.output);
                        }
                    }
                }
            } else {
                println!("History feature is disabled.");
            }
            return Ok(());
        }
        (key, None) => {
            match key {
                "openai_api_key" => println!("OpenAI API key: {}", config.openai_api_key.as_deref().unwrap_or("")),
                "default_model" => println!("Default model: {}", config.default_model.as_deref().unwrap_or("")),
                "default_provider" => println!("Default provider: {}", config.default_provider.as_deref().unwrap_or("")),
                "history_size" => println!("Chat history size: {}", config.history_size.unwrap_or(0)),
                "code_review_enabled" => println!("Code review feature: {}", if config.code_review_enabled.unwrap_or(true) { "enabled" } else { "disabled" }),
                "history_enabled" => println!("History feature: {}", if config.history_enabled.unwrap_or(true) { "enabled" } else { "disabled" }),
                "history_max_items" => println!("Maximum history items: {}", config.history_max_items.unwrap_or(1000)),
                "history_retention_days" => println!("History retention days: {}", config.history_retention_days.unwrap_or(30)),
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

async fn handle_history_command(command: args::HistoryCommands, config: &Config) -> Result<()> {
    let history_manager = HistoryManager::new(
        config.history_max_items.unwrap_or(1000),
        config.history_retention_days.unwrap_or(30),
    )?;

    match command {
        args::HistoryCommands::Stats => {
            let stats = history_manager.get_statistics()?;
            println!("\n=== History Statistics ===");
            println!("Total Requests: {}", stats.total_requests);
            println!("Total Tokens: {} (input: {}, output: {})",
                stats.total_tokens.input + stats.total_tokens.output,
                stats.total_tokens.input,
                stats.total_tokens.output);
            println!("Total Estimated Cost: ${:.4}", stats.total_cost);
            println!("Most Used Model: {}", stats.most_used_model);
            println!("Most Used Provider: {}", stats.most_used_provider);
        },
        args::HistoryCommands::Search { query, days } => {
            let results = history_manager.search_history(&query, days)?;
            if results.is_empty() {
                println!("No matching records found.");
                return Ok(());
            }

            println!("\n=== Search Results ===");
            for (i, request) in results.iter().enumerate() {
                println!("\n{}. [{}] {}", 
                    i + 1,
                    request.timestamp.format("%Y-%m-%d %H:%M:%S"),
                    request.message);
                if let Some(model) = &request.model {
                    println!("   Model: {}", model);
                }
                if let Some(tokens) = &request.tokens {
                    println!("   Tokens: {} (in: {}, out: {})",
                        tokens.input + tokens.output,
                        tokens.input,
                        tokens.output);
                }
                if let Some(cost) = request.estimated_cost {
                    println!("   Cost: ${:.4}", cost);
                }
            }
        },
        args::HistoryCommands::Clear => {
            println!("Are you sure you want to clear all history? (y/N)");
            let mut input = String::new();
            std::io::stdin().read_line(&mut input)?;
            if input.trim().to_lowercase() == "y" {
                history_manager.clear()?;
                println!("History cleared successfully.");
            } else {
                println!("Operation cancelled.");
            }
        },
    }
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    env_logger::init();
    
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
            
            // Check system requirements
            if let Err(e) = config.check_system_requirements() {
                let message = Config::get_system_requirements_message(&e);
                println!("{}", message);
                return Ok(());
            }

            // Validate configuration
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

            // Display help if configuration is valid
            display_logo(env!("CARGO_PKG_VERSION"));
            Cli::try_parse_from(&["codai", "--help"])?;
            Ok(())
        }
        Some(Commands::Chat { message, provider, model }) => {
            handle_chat_command(message, provider, model, &Config::load()?).await
        }
        Some(Commands::Code { message, language, run, provider, model }) => {
            handle_code_command(
                message,
                language,
                run,
                provider,
                model,
                &Config::load()?,
            ).await
        }
        Some(Commands::Task { message, provider, model }) => {
            handle_task_command(message, provider, model, &Config::load()?).await
        }
        Some(Commands::Config { key, value, history_command }) => {
            handle_config_command(key, value, history_command).await
        }
        Some(Commands::History { command }) => {
            handle_history_command(command, &Config::load()?).await
        },
    }
}
