use anyhow::Result;
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{Read, Write};
use std::path::PathBuf;
use flate2::Compression;
use flate2::write::GzEncoder;
use flate2::read::GzDecoder;

#[derive(Debug, Serialize, Deserialize)]
pub struct RequestHistory {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub request_type: String,
    pub message: String,
    pub model: Option<String>,
    pub provider: Option<String>,
    pub tokens: Option<TokenUsage>,
    pub estimated_cost: Option<f64>,
    pub execution_time: f64,
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct TokenUsage {
    pub input: u32,
    pub output: u32,
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct Statistics {
    pub total_requests: u32,
    pub total_tokens: TokenUsage,
    pub total_cost: f64,
    pub most_used_model: String,
    pub most_used_provider: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct History {
    pub requests: Vec<RequestHistory>,
    pub statistics: Statistics,
}

impl Default for History {
    fn default() -> Self {
        Self {
            requests: Vec::new(),
            statistics: Statistics {
                total_requests: 0,
                total_tokens: TokenUsage::default(),
                total_cost: 0.0,
                most_used_model: String::from("gpt-3.5-turbo"),
                most_used_provider: String::from("openai"),
            },
        }
    }
}

pub struct HistoryManager {
    current_file: PathBuf,
    archive_dir: PathBuf,
    max_items: u32,
    retention_days: u32,
}

impl HistoryManager {
    pub fn new(max_items: u32, retention_days: u32) -> Result<Self> {
        let config_dir = if cfg!(target_os = "windows") {
            dirs::config_dir()
                .unwrap_or_else(|| PathBuf::from("%APPDATA%"))
                .join("codai")
        } else {
            dirs::config_dir()
                .unwrap_or_else(|| PathBuf::from("~/.config"))
                .join("codai")
        };

        let archive_dir = config_dir.join("history_archives");
        fs::create_dir_all(&archive_dir)?;

        Ok(Self {
            current_file: config_dir.join("history.json"),
            archive_dir,
            max_items,
            retention_days,
        })
    }

    pub fn add_request(&mut self, request: RequestHistory) -> Result<()> {
        let mut history = self.load_current_history()?;
        history.requests.push(request);
        
        if history.requests.len() > self.max_items as usize {
            self.archive_old_records(&mut history)?;
        }
        
        self.update_statistics(&mut history);
        self.save_current_history(&history)?;
        self.cleanup_old_archives()?;
        
        Ok(())
    }

    fn load_current_history(&self) -> Result<History> {
        if !self.current_file.exists() {
            return Ok(History::default());
        }
        
        let content = fs::read_to_string(&self.current_file)?;
        Ok(serde_json::from_str(&content)?)
    }

    fn save_current_history(&self, history: &History) -> Result<()> {
        let content = serde_json::to_string_pretty(history)?;
        fs::write(&self.current_file, content)?;
        Ok(())
    }

    fn archive_old_records(&self, history: &mut History) -> Result<()> {
        let cutoff_index = history.requests.len() - self.max_items as usize;
        if cutoff_index == 0 {
            return Ok(());
        }

        let records_to_archive: Vec<RequestHistory> = history.requests.drain(..cutoff_index).collect();
        if records_to_archive.is_empty() {
            return Ok(());
        }

        let archive_content = serde_json::to_string(&records_to_archive)?;
        let archive_filename = format!(
            "history_archive_{}.json.gz",
            Utc::now().format("%Y%m%d_%H%M%S")
        );
        let archive_path = self.archive_dir.join(archive_filename);

        let file = File::create(&archive_path)?;
        let mut encoder = GzEncoder::new(file, Compression::default());
        encoder.write_all(archive_content.as_bytes())?;
        encoder.finish()?;

        Ok(())
    }

    fn cleanup_old_archives(&self) -> Result<()> {
        let cutoff_date = Utc::now() - Duration::days(self.retention_days as i64);
        
        for entry in fs::read_dir(&self.archive_dir)? {
            let entry = entry?;
            let metadata = entry.metadata()?;
            
            if let Ok(modified) = metadata.modified() {
                let modified_time = DateTime::<Utc>::from(modified);
                if modified_time < cutoff_date {
                    fs::remove_file(entry.path())?;
                }
            }
        }
        
        Ok(())
    }

    fn update_statistics(&self, history: &mut History) {
        let mut model_counts: HashMap<String, u32> = HashMap::new();
        let mut provider_counts: HashMap<String, u32> = HashMap::new();
        
        history.statistics.total_requests = history.requests.len() as u32;
        history.statistics.total_tokens = TokenUsage::default();
        history.statistics.total_cost = 0.0;

        for request in &history.requests {
            if let Some(model) = &request.model {
                *model_counts.entry(model.clone()).or_default() += 1;
            }
            if let Some(provider) = &request.provider {
                *provider_counts.entry(provider.clone()).or_default() += 1;
            }
            if let Some(tokens) = &request.tokens {
                history.statistics.total_tokens.input += tokens.input;
                history.statistics.total_tokens.output += tokens.output;
            }
            if let Some(cost) = request.estimated_cost {
                history.statistics.total_cost += cost;
            }
        }

        // Update most used model and provider
        if let Some((model, _)) = model_counts.iter().max_by_key(|&(_, count)| count) {
            history.statistics.most_used_model = model.clone();
        }
        if let Some((provider, _)) = provider_counts.iter().max_by_key(|&(_, count)| count) {
            history.statistics.most_used_provider = provider.clone();
        }
    }

    pub fn get_statistics(&self) -> Result<Statistics> {
        Ok(self.load_current_history()?.statistics)
    }

    pub fn search_history(&self, query: &str, days: u32) -> Result<Vec<RequestHistory>> {
        let mut results = Vec::new();
        let cutoff_date = Utc::now() - Duration::days(days as i64);
        
        // 현재 히스토리 검색
        let current_history = self.load_current_history()?;
        for request in current_history.requests {
            if request.timestamp >= cutoff_date && 
               (request.message.contains(query) || 
                request.request_type.contains(query)) {
                results.push(request);
            }
        }

        // 아카이브 검색
        for entry in fs::read_dir(&self.archive_dir)? {
            let entry = entry?;
            let file = File::open(entry.path())?;
            let mut decoder = GzDecoder::new(file);
            let mut content = String::new();
            decoder.read_to_string(&mut content)?;
            
            let archived_requests: Vec<RequestHistory> = serde_json::from_str(&content)?;
            for request in archived_requests {
                if request.timestamp >= cutoff_date && 
                   (request.message.contains(query) || 
                    request.request_type.contains(query)) {
                    results.push(request);
                }
            }
        }

        results.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        Ok(results)
    }

    pub fn clear(&self) -> Result<()> {
        if self.current_file.exists() {
            fs::remove_file(&self.current_file)?;
        }
        if self.archive_dir.exists() {
            fs::remove_dir_all(&self.archive_dir)?;
            fs::create_dir(&self.archive_dir)?;
        }
        Ok(())
    }
} 