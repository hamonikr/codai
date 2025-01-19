use anyhow::Result;
use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;
use std::sync::Mutex;

use super::{AIProvider, CodeRequest, CodeResponse, ContextWindow};
use crate::prompts;

pub struct OllamaProvider {
    host: String,
    client: Client,
    context: Mutex<ContextWindow>,
}

impl OllamaProvider {
    pub fn new() -> Self {
        Self {
            host: "http://localhost:11434".to_string(),
            client: Client::new(),
            context: Mutex::new(ContextWindow::new(4096)), // Default context length
        }
    }

    pub fn with_host(host: &str) -> Self {
        Self {
            host: host.to_string(),
            client: Client::new(),
            context: Mutex::new(ContextWindow::new(4096)), // Default context length
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
impl AIProvider for OllamaProvider {
    async fn chat(&self, message: &str, model: Option<String>) -> Result<String> {
        let model = model.unwrap_or_else(|| "llama2".to_string());
        self.update_context_window(&model);

        let messages = {
            let mut context = self.context.lock().unwrap();
            let estimated_tokens = self.estimate_tokens(message);
            context.add_message("user", message, estimated_tokens);
            context.get_context()
        };

        let response = self.client
            .post(format!("{}/api/chat", self.host))
            .json(&json!({
                "model": model,
                "messages": messages,
                "stream": false
            }))
            .send()
            .await?
            .error_for_status()?;

        let response_data: serde_json::Value = response.json().await?;
        let content = response_data["message"]["content"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Invalid response format"))?;

        // Add response to context
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
            .post("http://localhost:11434/api/generate")
            .json(&json!({
                "model": request.model.clone().unwrap_or_else(|| "llama2".to_string()),
                "prompt": format!("{}\n{}", system_message, request.message),
                "stream": false
            }))
            .send()
            .await?
            .error_for_status()?;

        let response_data: serde_json::Value = response.json().await?;
        let content = response_data["response"]
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