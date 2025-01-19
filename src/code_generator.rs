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
        // 코드 실행 결과 리뷰
        let review_prompt = get_code_review_prompt();
        format!(
            "{}\n\n코드:\n{}\n\n실행 결과:\n{}\n\n오류:\n{}\n\n실행 성공: {}",
            review_prompt,
            request.message,
            result.stdout,
            result.stderr,
            result.success
        )
    } else {
        // 일반 코드 생성
        let system_prompt = get_code_generation_prompt(language);
        if let Some(ref error) = request.error_message {
            format!(
                "{}\n이전 코드 실행 중 다음 오류가 발생했습니다:\n{}\n오류를 수정한 코드를 생성해주세요.",
                system_prompt, error
            )
        } else if let Some(ref feedback) = request.feedback {
            format!(
                "{}\n다음 피드백을 반영하여 코드를 수정해주세요:\n{}",
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
    
    // 마크다운 포맷 제거 및 리뷰 처리
    let (code, review) = if request.execution_result.is_some() {
        (
            provider_response.code.clone(),
            Some(provider_response.code)
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
            None
        )
    };

    Ok(CodeResponse {
        code,
        explanation: provider_response.explanation,
        packages: Some(provider_response.packages),
        review,
        output: None,
        task_status: None,
        input_tokens: provider_response.input_tokens,  // provider에서 제공한 실제 토큰 수 사용
        output_tokens: provider_response.output_tokens, // provider에서 제공한 실제 토큰 수 사용
    })
} 