use anyhow::Result;
use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;
use std::sync::Mutex;

use super::{AIProvider, CodeRequest, CodeResponse, ContextWindow};
use crate::prompts;

pub struct AnthropicProvider {
    api_key: String,
    client: Client,
    context: Mutex<ContextWindow>,
}

impl AnthropicProvider {
    pub fn new(api_key: &str) -> Self {
        Self {
            api_key: api_key.to_string(),
            client: Client::new(),
            context: Mutex::new(ContextWindow::new(200000)), // Claude-3의 기본 컨텍스트 길이
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
impl AIProvider for AnthropicProvider {
    async fn chat(&self, message: &str, model: Option<String>) -> Result<String> {
        let model = model.unwrap_or_else(|| "claude-3-opus-20240229".to_string());
        self.update_context_window(&model);

        let messages = {
            let mut context = self.context.lock().unwrap();
            let estimated_tokens = self.estimate_tokens(message);
            context.add_message("user", message, estimated_tokens);
            context.get_context()
        };

        let response = self.client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&json!({
                "model": model,
                "messages": messages,
                "max_tokens": 1024,
                "system": "당신은 친절하고 도움이 되는 AI 어시스턴트입니다."
            }))
            .send()
            .await?
            .error_for_status()?;

        let response_data: serde_json::Value = response.json().await?;
        let content = response_data["content"][0]["text"]
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
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&json!({
                "model": request.model.clone().unwrap_or_else(|| "claude-3-opus-20240229".to_string()),
                "messages": [{
                    "role": "user",
                    "content": format!("{}\n{}", system_message, request.message)
                }],
                "temperature": 0.7
            }))
            .send()
            .await?
            .error_for_status()?;

        let response_data: serde_json::Value = response.json().await?;
        let content = response_data["content"][0]["text"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Invalid response format"))?;

        // Get token counts from response
        let input_tokens = response_data["usage"]["input_tokens"]
            .as_u64()
            .map(|t| t as u32);
        let output_tokens = response_data["usage"]["output_tokens"]
            .as_u64()
            .map(|t| t as u32);

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