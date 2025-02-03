use anyhow::Result;
use crate::Config;
use crate::prompts::{get_code_generation_prompt, get_code_review_prompt};
use crate::types::{CodeRequest, CodeResponse};

pub async fn generate_code(request: CodeRequest, config: &Config) -> Result<CodeResponse> {
    let provider_type = request.provider
        .clone()
        .unwrap_or_else(|| config.default_provider.clone().unwrap_or_else(|| "openai".to_string()));
    
    let api_key = match provider_type.as_str() {
        "openai" => config.openai_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("OpenAI API key is not set"))?,
        "anthropic" => config.anthropic_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Anthropic API key is not set"))?,
        "gemini" => config.google_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Google API key is not set"))?,
        "groq" => config.groq_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Groq API key is not set"))?,
        "ollama" => "",
        _ => return Err(anyhow::anyhow!("Unsupported provider type: {}", provider_type)),
    };

    let provider = crate::providers::create_provider(&provider_type, api_key)?;
    let language = request.language.as_deref().unwrap_or("python");

    let prompt = if let Some(result) = &request.execution_result {
        // Code execution result review
        let review_prompt = get_code_review_prompt();
        format!(
            "{}\n\nCode:\n{}\n\nExecution Result:\n{}\n\nError:\n{}\n\nExecution Success: {}",
            review_prompt,
            request.message,
            result.stdout,
            result.stderr,
            result.success
        )
    } else {
        // General code generation
        let system_prompt = get_code_generation_prompt(language);
        if let Some(ref error) = request.error_message {
            format!(
                "{}\nThe following error occurred during previous code execution:\n{}\nPlease generate code that fixes this error.",
                system_prompt, error
            )
        } else if let Some(ref feedback) = request.feedback {
            format!(
                "{}\nPlease modify the code reflecting the following feedback:\n{}",
                system_prompt, feedback
            )
        } else {
            format!("{}\n{}", system_prompt, request.message)
        }
    };

    let provider_request = crate::providers::CodeRequest {
        message: prompt,
        language: request.language,
        model: request.model,
        feedback: request.feedback,
        error_message: request.error_message,
    };

    let provider_response = provider.generate_code(&provider_request).await?;
    
    // Remove markdown format and process review
    let (code, review) = if request.execution_result.is_some() {
        (
            request.message.clone(),      // 원본 코드 유지
            Some(provider_response.code)  // AI가 생성한 리뷰
        )
    } else {
        let extracted_code = provider_response.code
            .lines()
            .skip_while(|line| !line.contains("```"))
            .skip(1)
            .take_while(|line| !line.contains("```"))
            .collect::<Vec<_>>()
            .join("\n");
        (
            if extracted_code.is_empty() { 
                provider_response.code.clone() 
            } else { 
                extracted_code 
            },
            None  // 코드 생성 시에는 리뷰 없음
        )
    };

    Ok(CodeResponse {
        code: if request.execution_result.is_some() { request.message } else { code },  // 리뷰 시에는 원본 코드 유지
        explanation: provider_response.explanation,
        packages: Some(provider_response.packages),
        review,
        output: None,
        task_status: None,
        input_tokens: provider_response.input_tokens,
        output_tokens: provider_response.output_tokens,
    })
} 