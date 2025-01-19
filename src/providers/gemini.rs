use anyhow::Result;
use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;
use std::sync::Mutex;

use super::{AIProvider, CodeRequest, CodeResponse, ContextWindow};
use crate::prompts;

pub struct GeminiProvider {
    api_key: String,
    client: Client,
    context: Mutex<ContextWindow>,
}

impl GeminiProvider {
    pub fn new(api_key: &str) -> Self {
        Self {
            api_key: api_key.to_string(),
            client: Client::new(),
            context: Mutex::new(ContextWindow::new(32768)), // Gemini의 기본 컨텍스트 길이
        }
    }

    fn update_context_window(&self, model: &str) {
        let max_tokens = self.get_max_context_length(model);
        let mut context = self.context.lock().unwrap();
        if context.max_tokens != max_tokens {
            context.max_tokens = max_tokens;
        }
    }
}

#[async_trait]
impl AIProvider for GeminiProvider {
    async fn chat(&self, message: &str, model: Option<String>) -> Result<String> {
        let model = model.unwrap_or_else(|| "gemini-1.5-pro".to_string());
        self.update_context_window(&model);

        let contents = {
            let mut context = self.context.lock().unwrap();
            let estimated_tokens = self.estimate_tokens(message);
            context.add_message("user", message, estimated_tokens);
            
            // Gemini API는 다른 형식을 사용하므로 변환이 필요
            context.get_context().into_iter().map(|msg| {
                json!({
                    "parts": [{
                        "text": msg["content"].as_str().unwrap_or_default()
                    }]
                })
            }).collect::<Vec<serde_json::Value>>()
        };

        let response = self.client
            .post(format!(
                "https://generativelanguage.googleapis.com/v1/models/{}:generateContent?key={}",
                model, self.api_key
            ))
            .json(&json!({
                "contents": contents
            }))
            .send()
            .await?
            .error_for_status()?;

        let response_data: serde_json::Value = response.json().await?;
        let content = response_data["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Invalid response format"))?;

        // 응답도 컨텍스트에 추가
        {
            let mut context = self.context.lock().unwrap();
            let response_tokens = self.estimate_tokens(content);
            context.add_message("assistant", content, response_tokens);
        }

        Ok(content.to_string())
    }

    async fn generate_code(&self, request: &CodeRequest) -> Result<CodeResponse> {
        let language = request.language.as_deref().unwrap_or("python");
        let system_message = prompts::get_code_generation_prompt(language);

        let response = self.client
            .post(format!(
                "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={}",
                self.api_key
            ))
            .json(&json!({
                "contents": [{
                    "parts": [{
                        "text": format!("{}\n{}", system_message, request.message)
                    }]
                }]
            }))
            .send()
            .await?
            .error_for_status()?;

        let response_data: serde_json::Value = response.json().await?;
        let content = response_data["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Invalid response format"))?;

        // Get token counts from response
        let prompt = format!("{}\n{}", system_message, request.message);
        let input_tokens = Some(self.estimate_tokens(&prompt) as u32);
        let output_tokens = Some(self.estimate_tokens(content) as u32);

        // Parse the response content to extract code
        let code = content.to_string();
        let explanation = String::new();
        let packages = Vec::new();
        
        Ok(CodeResponse {
            code,
            explanation: Some(explanation),
            packages,
            input_tokens,
            output_tokens,
        })
    }
} 