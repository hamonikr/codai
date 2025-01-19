use std::collections::HashMap;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use crate::types::{CodeRequest, ExecutionResult};
use crate::Config;
use colored::*;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TaskStatus {
    NotStarted,
    InProgress,
    Completed,
    Failed(String),
    Blocked(String),
}

impl Default for TaskStatus {
    fn default() -> Self {
        Self::NotStarted
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStep {
    pub id: String,
    pub description: String,
    pub status: TaskStatus,
    pub dependencies: Vec<String>,
    pub request: CodeRequest,
    pub result: Option<ExecutionResult>,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Default)]
pub struct TaskManager {
    pub steps: HashMap<String, TaskStep>,
    pub overall_status: TaskStatus,
    pub started_at: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub api_calls: HashMap<String, u32>,
    pub model_costs: HashMap<String, f64>,
    pub token_counts: HashMap<String, (u32, u32)>, // (input_tokens, output_tokens)
}

impl TaskManager {
    pub fn new() -> Self {
        Self {
            steps: HashMap::new(),
            overall_status: TaskStatus::NotStarted,
            started_at: None,
            completed_at: None,
            api_calls: HashMap::new(),
            model_costs: HashMap::new(),
            token_counts: HashMap::new(),
        }
    }

    pub fn add_step(&mut self, step: TaskStep) -> anyhow::Result<()> {
        self.steps.insert(step.id.clone(), step);
        Ok(())
    }

    pub fn update_step_status(&mut self, step_id: &str, status: TaskStatus) -> anyhow::Result<()> {
        if let Some(step) = self.steps.get_mut(step_id) {
            step.status = status.clone();
            
            // Update overall status
            let mut has_failed = false;
            let mut all_completed = true;
            
            for step in self.steps.values() {
                match &step.status {
                    TaskStatus::Failed(_) => {
                        has_failed = true;
                        break;
                    }
                    TaskStatus::Completed => continue,
                    _ => {
                        all_completed = false;
                    }
                }
            }
            
            self.overall_status = if has_failed {
                TaskStatus::Failed("One or more steps have failed.".to_string())
            } else if all_completed {
                TaskStatus::Completed
            } else {
                TaskStatus::InProgress
            };
        }
        Ok(())
    }

    pub fn get_progress_report(&self) -> String {
        let overall_status_icon = match self.overall_status {
            TaskStatus::NotStarted => "🔵",
            TaskStatus::InProgress => "⏳",
            TaskStatus::Completed => "✅",
            TaskStatus::Failed(_) => "❌",
            TaskStatus::Blocked(_) => "⛔",
        };

        let mut report = format!("Overall Status: {} {:?}\n", overall_status_icon, self.overall_status);
        report.push_str("Step Status:\n");
        
        let mut steps: Vec<_> = self.steps.values().collect();
        steps.sort_by_key(|step| step.id.parse::<i32>().unwrap_or(0));
        
        let total_steps = steps.len();
        let completed_steps = steps.iter()
            .filter(|step| matches!(step.status, TaskStatus::Completed))
            .count();
        
        for (i, step) in steps.iter().enumerate() {
            let status_icon = match &step.status {
                TaskStatus::NotStarted => "⭕",   // Waiting
                TaskStatus::InProgress => "▶️",   // In Progress
                TaskStatus::Completed => "✅",    // Completed
                TaskStatus::Failed(_) => "❌",    // Failed
                TaskStatus::Blocked(_) => "⛔",   // Blocked
            };
            
            report.push_str(&format!("{} [{}/{}] {}: {:?}\n", 
                status_icon,
                i + 1,
                total_steps,
                step.description,
                step.status
            ));
        }

        // 전체 진행 상황을 마지막에 추가
        report.push_str(&format!("\nTotal Progress: {}/{} steps completed", completed_steps, total_steps));
        
        report
    }

    pub fn start_execution(&mut self) {
        self.started_at = Some(Utc::now());
    }

    pub fn complete_execution(&mut self) {
        self.completed_at = Some(Utc::now());
    }

    pub fn record_api_call(&mut self, model: &str, input_tokens: u32, output_tokens: u32) {
        *self.api_calls.entry(model.to_string()).or_insert(0) += 1;
        
        // Update token counts
        let (total_input, total_output) = self.token_counts
            .entry(model.to_string())
            .or_insert((0, 0));
        *total_input += input_tokens;
        *total_output += output_tokens;
        
        // Cost per 1K tokens
        let (input_cost, output_cost) = match model {
            // OpenAI Models
            "gpt-4" => (0.03, 0.06),            // $0.03 input, $0.06 output
            "gpt-4-turbo" => (0.01, 0.03),      // $0.01 input, $0.03 output
            "gpt-3.5-turbo" => (0.0005, 0.0015),// $0.0005 input, $0.0015 output
            
            // Anthropic Models
            "claude-3-opus" => (0.015, 0.075),   // $0.015 input, $0.075 output
            "claude-3-sonnet" => (0.003, 0.015), // $0.003 input, $0.015 output
            "claude-3-haiku" => (0.0025, 0.0125),// $0.0025 input, $0.0125 output
            "claude-2.1" => (0.008, 0.024),      // $0.008 input, $0.024 output
            "claude-2.0" => (0.008, 0.024),      // $0.008 input, $0.024 output
            "claude-instant-1.2" => (0.0025, 0.0075), // $0.0025 input, $0.0075 output
            
            // Google Models
            "gemini-pro" => (0.00025, 0.0005),   // $0.00025 input, $0.0005 output
            "gemini-ultra" => (0.00075, 0.00125), // $0.00075 input, $0.00125 output
            
            // Groq Models (flat rate for both input and output)
            "mixtral-8x7b" => (0.0007, 0.0007),  // $0.0007 per 1K tokens
            "llama2-70b" => (0.0007, 0.0007),    // $0.0007 per 1K tokens
            
            // Ollama Models (free/local)
            "llama2" | "mistral" | "codellama" | "dolphin-mixtral" | "neural-chat" => (0.0, 0.0),
            
            // Default for unknown models
            _ => (0.0, 0.0),
        };

        let cost = (input_tokens as f64 * input_cost + output_tokens as f64 * output_cost) / 1000.0;
        *self.model_costs.entry(model.to_string()).or_insert(0.0) += cost;
    }

    pub fn get_execution_stats(&self) -> String {
        let mut stats = String::new();
        
        // 실행 시간 계산
        if let (Some(start), Some(end)) = (self.started_at, self.completed_at) {
            let duration = end.signed_duration_since(start);
            stats.push_str(&format!("\n⏱️  Total Execution Time: {}{}\n",
                format!("{:.2}", duration.num_milliseconds() as f64 / 1000.0).cyan(),
                " seconds".cyan()
            ));
        }

        // API 호출 및 토큰 통계
        stats.push_str("\n🤖 API Calls and Token Usage:\n");
        for (model, count) in &self.api_calls {
            let (input_tokens, output_tokens) = self.token_counts.get(model).unwrap_or(&(0, 0));
            stats.push_str(&format!("  • {}: {} {} ({} input tokens, {} output tokens)\n",
                model.yellow(),
                count.to_string().cyan(),
                "calls".cyan(),
                input_tokens.to_string().cyan(),
                output_tokens.to_string().cyan()
            ));
        }

        // 비용 통계
        stats.push_str("\n💰 Estimated Costs:\n");
        let mut total_cost = 0.0;
        for (model, cost) in &self.model_costs {
            let (input_tokens, output_tokens) = self.token_counts.get(model).unwrap_or(&(0, 0));
            stats.push_str(&format!("  • {}: {}{} ({:.1}K tokens)\n",
                model.yellow(),
                "$".green(),
                format!("{:.4}", cost).green(),
                (input_tokens + output_tokens) as f64 / 1000.0
            ));
            total_cost += cost;
        }
        stats.push_str(&format!("\n💵 Total Estimated Cost: {}{}\n",
            "$".bright_green(),
            format!("{:.4}", total_cost).bright_green()
        ));

        stats
    }

    pub async fn get_next_executable_step<'a>(&'a mut self, _config: &'a Config) -> Option<&'a TaskStep> {
        let mut steps: Vec<_> = self.steps.values().collect();
        steps.sort_by_key(|step| step.id.parse::<i32>().unwrap_or(0));

        // 실행 가능한 작업 찾기
        for step in &steps {
            if matches!(step.status, TaskStatus::NotStarted) {
                let mut can_execute = true;
                
                // 의존성 체크
                for dep_id in &step.dependencies {
                    if let Some(dep_step) = self.steps.get(dep_id) {
                        if !matches!(dep_step.status, TaskStatus::Completed) {
                            can_execute = false;
                            break;
                        }
                    }
                }
                
                if can_execute {
                    // 작업 ID로 실제 작업 반환
                    return self.steps.get(&step.id);
                }
            }
        }
        None
    }
} 