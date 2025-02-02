use anyhow::Result;
use serde::{Deserialize, Serialize};
use crate::providers::create_provider;
use crate::Config;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Provider {
    OpenAI,
    Anthropic,
    Gemini,
    Groq,
    Ollama,
}

impl Provider {
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "openai" => Some(Provider::OpenAI),
            "anthropic" => Some(Provider::Anthropic),
            "gemini" => Some(Provider::Gemini),
            "groq" => Some(Provider::Groq),
            "ollama" => Some(Provider::Ollama),
            _ => None,
        }
    }

    pub fn to_string(&self) -> String {
        match self {
            Provider::OpenAI => "openai",
            Provider::Anthropic => "anthropic",
            Provider::Gemini => "gemini",
            Provider::Groq => "groq",
            Provider::Ollama => "ollama",
        }.to_string()
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequest {
    pub message: String,
    pub model: Option<String>,
    pub provider: Option<Provider>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponse {
    pub message: String,
    pub token_usage: Option<(u32, u32)>,  // (input_tokens, output_tokens)
    pub estimated_cost: Option<f64>,
}

pub async fn chat(request: ChatRequest, config: &Config) -> Result<ChatResponse> {
    let provider_type = request.provider
        .clone()
        .map(|p| p.to_string())
        .unwrap_or_else(|| config.default_provider.clone().unwrap_or_else(|| "openai".to_string()));
    
    let api_key = match provider_type.as_str() {
        "openai" => config.openai_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("OpenAI API key is not set"))?,
        "anthropic" => config.anthropic_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Anthropic API key is not set"))?,
        "gemini" => config.google_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Google API key is not set"))?,
        "groq" => config.groq_api_key.as_deref().ok_or_else(|| anyhow::anyhow!("Groq API key is not set"))?,
        "ollama" => "",
        _ => return Err(anyhow::anyhow!("Unsupported provider type: {}", provider_type)),
    };

    let provider = create_provider(&provider_type, api_key)?;
    let response = provider.chat(&request.message, request.model).await?;

    // 임시로 토큰 사용량과 비용을 추정
    let input_tokens = request.message.len() as u32 / 4;  // 대략적인 추정
    let output_tokens = response.len() as u32 / 4;  // 대략적인 추정
    
    let cost_per_1k_tokens = match provider_type.as_str() {
        "openai" => 0.002,  // gpt-3.5-turbo 기준
        "anthropic" => 0.015,  // claude-3-sonnet 기준
        "gemini" => 0.00025,  // gemini-pro 기준
        "groq" => 0.0007,  // mixtral-8x7b 기준
        _ => 0.0,
    };
    
    let estimated_cost = ((input_tokens + output_tokens) as f64 * cost_per_1k_tokens) / 1000.0;

    Ok(ChatResponse {
        message: response,
        token_usage: Some((input_tokens, output_tokens)),
        estimated_cost: Some(estimated_cost),
    })
} 