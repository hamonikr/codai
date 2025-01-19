use anyhow::Result;
use crate::Config;
use crate::types::CodeRequest;
pub use crate::task::TaskManager;
use crate::task::{TaskStep, TaskStatus};
use chrono::Utc;
use colored::Colorize;
use std::collections::HashMap;
use crate::code_generator::generate_code;
use std::path::PathBuf;
use crate::code_executor::CodeExecutor;

#[derive(Debug, Clone, PartialEq)]
enum DetectedLanguage {
    Korean,
    English,
    Other(String),
}

fn detect_language(text: &str) -> DetectedLanguage {
    // Check for Korean (Hangul)
    if text.chars().any(|c| matches!(c as u32, 0xAC00..=0xD7A3)) {
        return DetectedLanguage::Korean;
    }
    // Default to English if mostly ASCII
    if text.chars().all(|c| c.is_ascii()) {
        return DetectedLanguage::English;
    }
    // For other languages
    DetectedLanguage::Other("unknown".to_string())
}

fn get_task_analysis_prompt(lang: &DetectedLanguage, task: &str) -> String {
    match lang {
        DetectedLanguage::Korean => format!(
            "다음 작업을 분석하여 수행해야 할 주요 단계들을 나열해주세요.\n\
            각 단계는 구체적이고 독립적으로 실행 가능한 기능 단위여야 합니다.\n\
            라이브러리 임포트나 기본 설정과 같은 구현 세부사항은 제외하고,\n\
            실제로 수행해야 할 핵심 기능들을 중심으로 작성해주세요.\n\n\
            작업: {}\n\n\
            다음 형식으로 응답해주세요:\n\n\
            작업 단계:\n\
            1. [구체적인 기능 단위 작업]\n\
            2. [구체적인 기능 단위 작업]\n\
            ...\n\n\
            의존성:\n\
            - 작업 2는 작업 1에 의존합니다\n\
            - 작업 4는 작업 2, 작업 3에 의존합니다\n\
            ...\n\n\
            주의사항:\n\
            - 각 단계는 실제 기능을 수행하는 독립적인 단위여야 합니다\n\
            - 라이브러리 임포트, 변수 설정 등은 제외합니다\n\
            - 데이터 처리, 분석, 시각화 등 실제 작업을 중심으로 작성합니다",
            task
        ),
        _ => format!(
            "Please analyze the following task and list the main steps that need to be performed.\n\
            Each step should be a concrete and independently executable functional unit.\n\
            Exclude implementation details like library imports and basic setup,\n\
            and focus on the core functionalities that need to be performed.\n\n\
            Task: {}\n\n\
            Please respond in the following format:\n\n\
            Task Breakdown:\n\
            1. [Specific functional unit task]\n\
            2. [Specific functional unit task]\n\
            ...\n\n\
            Dependencies:\n\
            - Task 2 depends on Task 1\n\
            - Task 4 depends on Task 2, Task 3\n\
            ...\n\n\
            Important Notes:\n\
            - Each step should be an independent unit performing actual functionality\n\
            - Exclude library imports, variable setup, etc.\n\
            - Focus on actual tasks like data processing, analysis, visualization",
            task
        ),
    }
}

pub async fn analyze_task(request: &CodeRequest, config: &Config) -> Result<Vec<TaskStep>> {
    let provider_type = config.default_provider.clone().unwrap_or_else(|| "openai".to_string());
    let api_key = match provider_type.as_str() {
        "openai" => config.openai_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("OpenAI API key is not set"))?,
        "anthropic" => config.anthropic_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Anthropic API key is not set"))?,
        "gemini" => config.google_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Google API key is not set"))?,
        "groq" => config.groq_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Groq API key is not set"))?,
        "ollama" => "",
        _ => return Err(anyhow::anyhow!("Unsupported provider type: {}", provider_type)),
    };

    let provider = crate::providers::create_provider(&provider_type, api_key)?;
    
    // Detect language of the request
    let detected_lang = detect_language(&request.message);
    
    // Task analysis request with appropriate language
    let analysis_request = crate::providers::CodeRequest {
        message: get_task_analysis_prompt(&detected_lang, &request.message),
        language: request.language.clone(),
        model: request.model.clone(),
        feedback: None,
        error_message: None,
    };

    // Wait for AI response
    let analysis_response = provider.generate_code(&analysis_request).await?;
    
    // Parse the response into steps
    let steps = parse_task_breakdown(&analysis_response.code, request)?;
    
    // Only display results after we have the steps
    if !steps.is_empty() {
        // Display results in the detected language
        let (header, task_list, status_label, deps_label) = match detected_lang {
            DetectedLanguage::Korean => (
                "=== 작업 분석 결과 ===",
                "실행할 작업 목록:",
                "상태",
                "의존성"
            ),
            _ => (
                "=== Task Analysis Result ===",
                "Task list to be executed:",
                "Status",
                "Dependencies"
            ),
        };

        println!("\n{}", header.cyan());
        println!("\n{}", task_list.yellow());

        // Display each task with its status and dependencies
        for (i, step) in steps.iter().enumerate() {
            let status_str = match &step.status {
                TaskStatus::NotStarted => match detected_lang {
                    DetectedLanguage::Korean => "대기 중".yellow(),
                    _ => "Waiting".yellow(),
                },
                TaskStatus::InProgress => match detected_lang {
                    DetectedLanguage::Korean => "진행 중".blue(),
                    _ => "In Progress".blue(),
                },
                TaskStatus::Completed => match detected_lang {
                    DetectedLanguage::Korean => "완료".green(),
                    _ => "Completed".green(),
                },
                TaskStatus::Failed(err) => format!("{}: {}", 
                    match detected_lang {
                        DetectedLanguage::Korean => "실패",
                        _ => "Failed",
                    },
                    err
                ).red(),
                TaskStatus::Blocked(reason) => format!("{}: {}", 
                    match detected_lang {
                        DetectedLanguage::Korean => "차단됨",
                        _ => "Blocked",
                    },
                    reason
                ).red(),
            };

            let deps_str = if step.dependencies.is_empty() {
                match detected_lang {
                    DetectedLanguage::Korean => "없음",
                    _ => "None",
                }.to_string()
            } else {
                match detected_lang {
                    DetectedLanguage::Korean => format!("작업 {}", step.dependencies.join(", 작업 ")),
                    _ => format!("Task {}", step.dependencies.join(", Task ")),
                }
            };

            println!("{}. {} ({}: {}, {}: {})", 
                i + 1,
                step.description,
                status_label,
                status_str,
                deps_label,
                deps_str
            );
        }
        
        println!("\n{}", "=====================".to_string().cyan());
    }
    
    Ok(steps)
}

pub async fn execute_task(
    task_manager: &mut TaskManager,
    config: &Config,
    request: &CodeRequest,
) -> anyhow::Result<()> {
    println!("Task list has been generated. Starting execution of each step...\n");
    
    // Write the start time of the task
    task_manager.start_execution();

    let mut context = String::new();
    let mut final_output = None;

    // Execute each step in sequence
    while let Some(step) = task_manager.get_next_executable_step(config).await {
        let step_id = step.id.clone();
        let step = step.clone();
        println!("\n{}", format!("Executing step: {}", step.description).yellow());
        
        let mut retry_count = 0;
        let max_retries = 10;
        let mut last_error = None;
        
        while retry_count < max_retries {
            let step_request = CodeRequest {
                message: format!(
                    "Previous code and its execution result:\n{}\n\nCurrent task: {}",
                    if context.is_empty() {
                        "No previous code".to_string()
                    } else {
                        format!("```\n{}\n```\nOutput: {}", 
                            context,
                            final_output.as_ref().unwrap_or(&"No output".to_string())
                        )
                    },
                    step.description
                ),
                language: request.language.clone(),
                model: step.request.model.clone(),
                feedback: None,
                error_message: last_error.clone(),
                execution_result: None,
                provider: step.request.provider.clone(),
                task_id: None,
            };

            task_manager.update_step_status(&step_id, TaskStatus::InProgress)?;
            
            // Generate code and record API call
            let model = step_request.model.clone()
                .or_else(|| config.default_model.clone())
                .unwrap_or_else(|| "gpt-3.5-turbo".to_string());
            
            match generate_code(step_request, config).await {
                Ok(response) => {
                    // Record API call with token counts
                    task_manager.record_api_call(
                        &model,
                        response.input_tokens.unwrap_or(0),
                        response.output_tokens.unwrap_or(0)
                    );
                    
                    println!("\n=== Generated Code ===");
                    println!("{}", response.code);
                    println!("\n✓ Code generated successfully. Executing...");
                    
                    let mut executor = CodeExecutor::new(
                        PathBuf::from(format!("{}/.codai-venv", std::env::var("HOME").unwrap_or_else(|_| "~".to_string()))),
                        if cfg!(windows) {
                            PathBuf::from(format!("{}/.codai-venv/Scripts/python.exe", std::env::var("HOME").unwrap_or_else(|_| "~".to_string())))
                        } else {
                            PathBuf::from(format!("{}/.codai-venv/bin/python", std::env::var("HOME").unwrap_or_else(|_| "~".to_string())))
                        }
                    );
                    
                    // Setup virtual environment
                    if let Err(e) = executor.setup_venv() {
                        last_error = Some(format!("Failed to setup virtual environment: {}", e));
                        println!("\n=== Error ===\n{}", last_error.as_ref().unwrap());
                        continue;
                    }
                    
                    let code = response.code.clone();
                    match executor.execute_code(&code) {
                        Ok(result) => {
                            if result.success {
                                println!("\n=== Execution Result ===");
                                println!("Output:\n{}", result.stdout);
                                if !result.stderr.is_empty() {
                                    println!("\nWarnings/Debug Info:\n{}", result.stderr);
                                }
                                
                                // Update context and output
                                context = code;
                                final_output = Some(result.stdout);
                                
                                // Update task status
                                task_manager.update_step_status(&step_id, TaskStatus::Completed)?;
                                break;
                            } else {
                                last_error = Some(format!("Execution failed:\n{}", result.stderr));
                                println!("\n=== Error ===\n{}", last_error.as_ref().unwrap());
                            }
                        }
                        Err(e) => {
                            last_error = Some(format!("Error: {}", e));
                            println!("\n=== Error ===\n{}", last_error.as_ref().unwrap());
                        }
                    }
                }
                Err(e) => {
                    last_error = Some(format!("Code generation failed: {}", e));
                    println!("\n=== Error ===\n{}", last_error.as_ref().unwrap());
                }
            }
            
            retry_count += 1;
            if retry_count >= max_retries {
                task_manager.update_step_status(&step_id, TaskStatus::Failed(last_error.unwrap_or_else(|| "Unknown error".to_string())))?;
                return Err(anyhow::anyhow!("Failed to execute step after {} retries", max_retries));
            }
            
            if retry_count < max_retries {
                println!("\nRetrying... ({}/{})", retry_count + 1, max_retries);
            }
        }
        
        println!("\n=== Current Progress ===\n{}", task_manager.get_progress_report());
    }
    
    // 작업 완료 시간 기록
    task_manager.complete_execution();
    
    // 코드 리뷰 다시 활성화
    crate::code_executor::set_code_review_enabled(true);
    
    // 최종 상태 및 통계 출력
    println!("\n=== Final Task Status ===\n{}", task_manager.get_progress_report());
    println!("\n{}", "===== Execution Statistics =====".cyan());
    println!("{}", task_manager.get_execution_stats());
    
    Ok(())
}

fn parse_task_breakdown(analysis: &str, request: &CodeRequest) -> Result<Vec<TaskStep>> {
    let mut steps = Vec::new();
    let mut tasks = Vec::new();
    let mut dependencies = HashMap::new();
    let mut in_task_section = false;
    let mut in_deps_section = false;

    // Detect language
    let is_korean = analysis.contains("작업 단계:") || analysis.contains("의존성:");

    // Parse tasks and dependencies from each line
    for line in analysis.lines() {
        let trimmed = line.trim();
        
        if trimmed == "Task Breakdown:" || trimmed == "작업 단계:" {
            in_task_section = true;
            in_deps_section = false;
            continue;
        } else if trimmed == "Dependencies:" || trimmed == "의존성:" {
            in_task_section = false;
            in_deps_section = true;
            continue;
        }

        if in_task_section && !trimmed.is_empty() {
            // Parse task description starting with a number
            if let Some(pos) = trimmed.find(|c: char| !c.is_digit(10) && c != '.') {
                let task = trimmed[pos..].trim().to_string();
                if !task.is_empty() {
                    tasks.push(task);
                }
            }
        } else if in_deps_section && !trimmed.is_empty() {
            // Parse dependencies for both English and Korean formats
            if is_korean && trimmed.contains("는") && trimmed.contains("의존") {
                // Korean format: "작업 2는 작업 1에 의존합니다"
                let parts: Vec<&str> = trimmed.split("는").collect();
                if parts.len() == 2 {
                    let task_str = parts[0].trim().replace("작업 ", "");
                    let dep_str = parts[1]
                        .trim()
                        .replace("작업 ", "")
                        .replace("에 의존합니다", "")
                        .replace("을 의존합니다", "")
                        .replace("를 의존합니다", "")
                        .replace("에 의존", "")
                        .replace("을 의존", "")
                        .replace("를 의존", "")
                        .trim()
                        .to_string();

                    if let (Ok(task_num), Ok(dep_num)) = (task_str.parse::<usize>(), dep_str.parse::<usize>()) {
                        let task_idx = task_num - 1;
                        let dep_idx = dep_num - 1;
                        dependencies.entry(task_idx)
                            .or_insert_with(Vec::new)
                            .push(dep_idx.to_string());
                    }
                }
            } else if trimmed.contains("depends on") {
                // English format: "Task 2 depends on Task 1"
                let parts: Vec<&str> = trimmed.split("depends on").collect();
                if parts.len() == 2 {
                    let task_str = parts[0].trim().replace("Task ", "");
                    let dep_str = parts[1].trim().replace("Task ", "");
                    
                    if let (Ok(task_num), Ok(dep_num)) = (task_str.parse::<usize>(), dep_str.parse::<usize>()) {
                        let task_idx = task_num - 1;
                        let dep_idx = dep_num - 1;
                        dependencies.entry(task_idx)
                            .or_insert_with(Vec::new)
                            .push(dep_idx.to_string());
                    }
                }
            }
        }
    }

    // Create task steps
    if tasks.is_empty() {
        return Err(anyhow::anyhow!("Failed to analyze task: No tasks were identified"));
    }

    // Create task steps from analyzed tasks
    for (i, task) in tasks.into_iter().enumerate() {
        let deps = dependencies.get(&i).cloned().unwrap_or_default();
        steps.push(TaskStep {
            id: i.to_string(),
            description: task.trim().to_string(),
            status: TaskStatus::NotStarted,
            dependencies: deps,
            request: CodeRequest {
                message: task.trim().to_string(),
                language: request.language.clone(),
                model: None,
                feedback: None,
                error_message: None,
                execution_result: None,
                provider: None,
                task_id: Some(i.to_string()),
            },
            result: None,
            created_at: Utc::now(),
            completed_at: None,
        });
    }

    Ok(steps)
} 