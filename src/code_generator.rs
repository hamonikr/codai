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
        if let Some(context) = &request.code_context {
            format!(
                "{}\n\nOriginal Request:\n{}\n\nPrevious Code:\n{}\n\nError:\n{}\n\n\
                This is attempt {} to fix the code. The previous code failed with the above error.\n\n\
                CRITICAL INSTRUCTIONS:\n\
                1. Analyze the error message carefully - identify the EXACT line and reason for failure\n\
                2. The error shows: {}\n\
                3. To fix this, you MUST:\n\
                   - Ensure all imports are correctly handled\n\
                   - Check if required modules exist before using\n\
                   - Maintain proper error handling\n\
                4. Keep working parts of the code unchanged\n\
                5. The code must still accomplish the original request\n\n\
                ERROR HANDLING RULES:\n\
                1. ALL errors MUST propagate up using raise\n\
                2. NEVER catch errors silently\n\
                3. NEVER use print() for error handling\n\
                4. Test code MUST also propagate errors\n\
                5. DO NOT catch errors in the final test code\n\n\
                BEFORE GENERATING CODE:\n\
                1. Review the original request carefully\n\
                2. Analyze the previous code and error\n\
                3. Make ONLY the necessary changes to fix the error\n\
                4. Test the changes before proceeding",
                system_prompt,
                context.original_request,
                context.previous_code,
                context.error_message,
                context.attempt_count,
                context.error_message
            )
        } else if let Some(ref error) = request.error_message {
            // 오류 수정을 위한 프롬프트
            format!(
                "{}\n\nOriginal Request:\n{}\n\nError:\n{}\n\n\
                Please fix the error while maintaining the original functionality.\n\n\
                IMPORTANT:\n\
                1. The code should still accomplish the original request\n\
                2. Focus on fixing the specific error\n\
                3. Keep the same overall structure\n\
                4. Maintain all error handling rules",
                system_prompt,
                request.message,
                error
            )
        } else if let Some(ref feedback) = request.feedback {
            format!(
                "{}\n\nOriginal Request:\n{}\n\nFeedback:\n{}\n\n\
                Please modify the code reflecting this feedback while maintaining the original functionality.",
                system_prompt,
                request.message,
                feedback
            )
        } else {
            format!("{}\n\n{}", system_prompt, request.message)
        }
    };

    // 프롬프트 내용은 디버그 모드에서만 출력
    #[cfg(debug_assertions)]
    log::debug!("Generated prompt:\n{}", prompt);

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