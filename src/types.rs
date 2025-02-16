use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeContext {
    pub original_request: String,
    pub previous_code: String,
    pub error_message: String,
    pub attempt_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeRequest {
    pub message: String,
    pub language: Option<String>,
    pub model: Option<String>,
    pub feedback: Option<String>,
    pub error_message: Option<String>,
    pub execution_result: Option<ExecutionResult>,
    pub provider: Option<String>,
    pub task_id: Option<String>,
    pub code_context: Option<CodeContext>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeResponse {
    pub code: String,
    pub explanation: Option<String>,
    pub packages: Option<Vec<String>>,
    pub review: Option<String>,
    pub output: Option<String>,
    pub task_status: Option<String>,
    pub input_tokens: Option<u32>,
    pub output_tokens: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub stdout: String,
    pub stderr: String,
    pub success: bool,
}

// Embedded resources
pub const UTILS_PY: &str = include_str!("tools/utils.py");
pub const SYSTEM_PROMPT: &str = include_str!("prompts/system_prompt.txt");
pub const CODE_REVIEW_PROMPT: &str = include_str!("prompts/code_review.txt");
pub const TOOLS_CONF: &str = include_str!("tools/tools.conf");
