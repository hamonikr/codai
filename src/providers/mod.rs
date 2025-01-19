use anyhow::Result;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};

pub mod openai;
pub mod anthropic;
pub mod gemini;
pub mod groq;
pub mod ollama;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextWindow {
    pub messages: Vec<Message>,
    pub total_tokens: usize,
    pub max_tokens: usize,
    pub summary: Option<String>,  // 대화 요약
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
    pub tokens: usize,
}

impl ContextWindow {
    pub fn new(max_tokens: usize) -> Self {
        Self {
            messages: Vec::new(),
            total_tokens: 0,
            max_tokens,
            summary: None,
        }
    }

    pub fn add_message(&mut self, role: &str, content: &str, tokens: usize) {
        let message = Message {
            role: role.to_string(),
            content: content.to_string(),
            tokens,
        };

        // 새 메시지를 추가했을 때 최대 토큰 수를 초과하는 경우
        // 가장 오래된 메시지부터 제거하고 요약 생성
        while self.total_tokens + tokens > self.max_tokens && !self.messages.is_empty() {
            let removed = self.messages.remove(0);
            self.total_tokens -= removed.tokens;
            
            // 메시지가 제거될 때 요약 업데이트
            if self.messages.len() > 0 {
                self.update_summary(&removed);
            }
        }

        self.messages.push(message);
        self.total_tokens += tokens;
    }

    fn update_summary(&mut self, removed_message: &Message) {
        let current_summary = self.summary.take().unwrap_or_default();
        let new_content = format!(
            "{}\n\n{}: {}",
            current_summary,
            removed_message.role,
            removed_message.content
        );
        self.summary = Some(new_content.trim().to_string());
    }

    pub fn clear(&mut self) {
        self.messages.clear();
        self.total_tokens = 0;
        self.summary = None;
    }

    pub fn get_context(&self) -> Vec<serde_json::Value> {
        let mut context = Vec::new();
        
        // 요약이 있으면 시스템 메시지로 추가
        if let Some(summary) = &self.summary {
            context.push(serde_json::json!({
                "role": "system",
                "content": format!("Previous conversation summary:\n{}", summary)
            }));
        }

        // 현재 메시지들 추가
        context.extend(self.messages.iter().map(|msg| {
            serde_json::json!({
                "role": msg.role,
                "content": msg.content
            })
        }));

        context
    }
}

#[async_trait]
pub trait AIProvider {
    async fn chat(&self, message: &str, model: Option<String>) -> Result<String>;
    async fn generate_code(&self, request: &CodeRequest) -> Result<CodeResponse>;
    
    // 컨텍스트 관리를 위한 메서드들
    fn get_max_context_length(&self, model: &str) -> usize {
        match model {
            // OpenAI 모델들
            "gpt-3.5-turbo" => 4096,
            "gpt-4" => 8192,
            "gpt-4-turbo" => 128000,
            
            // Anthropic 모델들
            "claude-3-opus-20240229" => 200000,
            "claude-3-sonnet-20240229" => 200000,
            "claude-3-haiku-20240307" => 200000,
            
            // Gemini 모델들
            "gemini-pro" => 32768,
            "gemini-1.5-pro" => 32768,
            
            // Groq 모델들
            "mixtral-8x7b-32768" => 32768,
            "llama2-70b-4096" => 4096,
            
            // 기본값
            _ => 4096,
        }
    }
    
    fn estimate_tokens(&self, text: &str) -> usize {
        // 간단한 토큰 수 추정 (실제로는 더 정교한 구현이 필요)
        text.split_whitespace().count() * 2
    }
}

#[derive(Debug)]
pub struct CodeRequest {
    pub message: String,
    pub language: Option<String>,
    pub model: Option<String>,
    pub feedback: Option<String>,
    pub error_message: Option<String>,
}

#[derive(Debug)]
pub struct CodeResponse {
    pub code: String,
    pub explanation: Option<String>,
    pub packages: Vec<String>,
    pub input_tokens: Option<u32>,
    pub output_tokens: Option<u32>,
}

pub fn create_provider(provider_type: &str, api_key: &str) -> Result<Box<dyn AIProvider>> {
    match provider_type {
        "openai" => Ok(Box::new(openai::OpenAIProvider::new(api_key))),
        "anthropic" => Ok(Box::new(anthropic::AnthropicProvider::new(api_key))),
        "gemini" => Ok(Box::new(gemini::GeminiProvider::new(api_key))),
        "groq" => Ok(Box::new(groq::GroqProvider::new(api_key))),
        "ollama" => Ok(Box::new(ollama::OllamaProvider::new())),
        _ => Err(anyhow::anyhow!("Unsupported provider type: {}", provider_type))
    }
} 