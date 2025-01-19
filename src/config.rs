use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::path::Path;
use std::fs;
use crate::ui::Menu;
use std::io::Write;
use colored::*;

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct Config {
    pub openai_api_key: Option<String>,
    pub anthropic_api_key: Option<String>,
    pub google_api_key: Option<String>,
    pub groq_api_key: Option<String>,
    pub ollama_host: Option<String>,
    pub default_model: Option<String>,
    pub default_provider: Option<String>,
    pub history_size: Option<u32>,
    pub max_context_length: Option<u32>,  // 최대 컨텍스트 길이 (토큰 수)
    pub context_window_ratio: Option<f32>, // 컨텍스트 윈도우 비율 (0.0 ~ 1.0)
    pub code_review_enabled: Option<bool>, // 코드 리뷰 기능 활성화 여부
}

#[allow(dead_code)]
impl Config {
    pub fn new() -> Self {
        Self {
            default_provider: Some("openai".to_string()),
            default_model: Some("gpt-3.5-turbo".to_string()),
            history_size: Some(10),
            max_context_length: Some(4000),  // 기본 최대 컨텍스트 길이
            context_window_ratio: Some(0.8),  // 기본 컨텍스트 윈도우 비율
            code_review_enabled: Some(true),  // 코드 리뷰 기능 기본 활성화
            ..Default::default()
        }
    }

    pub fn save_to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let content = toml::to_string(self)?;
        fs::write(path, content)?;
        Ok(())
    }

    pub fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = fs::read_to_string(path)?;
        let config: Config = toml::from_str(&content)?;
        Ok(config)
    }

    pub fn update(&mut self, key: &str, value: Option<String>) -> Result<()> {
        match key {
            "openai_api_key" => self.openai_api_key = value,
            "default_provider" => self.default_provider = value,
            "default_model" => self.default_model = value,
            "history_size" => self.history_size = value.map(|v| v.parse().unwrap_or(10)),
            _ => return Err(anyhow::anyhow!("Invalid config key: {}", key)),
        }
        Ok(())
    }

    pub fn load() -> Result<Self> {
        let config_dir = if cfg!(target_os = "windows") {
            dirs::config_dir().unwrap_or_else(|| PathBuf::from("%APPDATA%"))
                .join("codai")
        } else if cfg!(target_os = "macos") {
            dirs::home_dir().unwrap_or_else(|| PathBuf::from("~"))
                .join("Library")
                .join("Application Support")
                .join("codai")
        } else {
            dirs::config_dir().unwrap_or_else(|| PathBuf::from("~/.config"))
                .join("codai")
        };

        std::fs::create_dir_all(&config_dir)?;
        let config_path = config_dir.join("config.toml");

        if config_path.exists() {
            let contents = std::fs::read_to_string(&config_path)?;
            Ok(toml::from_str(&contents)?)
        } else {
            Ok(Config::default())
        }
    }

    pub fn save(&self) -> Result<()> {
        let config_dir = if cfg!(target_os = "windows") {
            dirs::config_dir().unwrap_or_else(|| PathBuf::from("%APPDATA%"))
                .join("codai")
        } else if cfg!(target_os = "macos") {
            dirs::home_dir().unwrap_or_else(|| PathBuf::from("~"))
                .join("Library")
                .join("Application Support")
                .join("codai")
        } else {
            dirs::config_dir().unwrap_or_else(|| PathBuf::from("~/.config"))
                .join("codai")
        };

        std::fs::create_dir_all(&config_dir)?;
        let config_path = config_dir.join("config.toml");
        let contents = toml::to_string_pretty(self)?;
        std::fs::write(&config_path, contents)?;
        Ok(())
    }

    pub fn validate(&self) -> Result<(), ConfigValidationError> {
        // 기본 제공자 확인
        let provider = self.default_provider
            .as_ref()
            .ok_or(ConfigValidationError::MissingProvider)?;

        // 기본 모델 확인
        if self.default_model.is_none() {
            return Err(ConfigValidationError::MissingModel);
        }

        // 제공자별 필수 설정 확인
        match provider.as_str() {
            "openai" => {
                if self.openai_api_key.as_ref().map_or(true, |key| key.is_empty()) {
                    return Err(ConfigValidationError::MissingApiKey("OpenAI".to_string()));
                }
            }
            "anthropic" => {
                if self.anthropic_api_key.as_ref().map_or(true, |key| key.is_empty()) {
                    return Err(ConfigValidationError::MissingApiKey("Anthropic".to_string()));
                }
            }
            "gemini" => {
                if self.google_api_key.as_ref().map_or(true, |key| key.is_empty()) {
                    return Err(ConfigValidationError::MissingApiKey("Google".to_string()));
                }
            }
            "groq" => {
                if self.groq_api_key.as_ref().map_or(true, |key| key.is_empty()) {
                    return Err(ConfigValidationError::MissingApiKey("Groq".to_string()));
                }
            }
            "ollama" => {
                if self.ollama_host.as_ref().map_or(true, |host| host.is_empty()) {
                    return Err(ConfigValidationError::InvalidOllamaHost);
                }
            }
            _ => return Err(ConfigValidationError::MissingProvider)
        }

        Ok(())
    }

    fn check_python_installation() -> Result<(), SystemRequirementError> {
        if cfg!(target_os = "windows") {
            match std::process::Command::new("python")
                .arg("--version")
                .output() {
                    Ok(output) if output.status.success() => Ok(()),
                    _ => match std::process::Command::new("py")
                        .arg("--version")
                        .output() {
                            Ok(output) if output.status.success() => Ok(()),
                            _ => Err(SystemRequirementError::PythonNotFound)
                        }
                }
        } else {
            match std::process::Command::new("python3")
                .arg("--version")
                .output() {
                    Ok(output) if output.status.success() => Ok(()),
                    _ => match std::process::Command::new("python")
                        .arg("--version")
                        .output() {
                            Ok(output) if output.status.success() => Ok(()),
                            _ => Err(SystemRequirementError::PythonNotFound)
                        }
                }
        }
    }

    fn check_venv_capability() -> Result<(), SystemRequirementError> {
        if cfg!(target_os = "windows") {
            match std::process::Command::new("python")
                .arg("-m")
                .arg("venv")
                .arg("--help")
                .output() {
                    Ok(output) if output.status.success() => Ok(()),
                    _ => match std::process::Command::new("py")
                        .arg("-m")
                        .arg("venv")
                        .arg("--help")
                        .output() {
                            Ok(output) if output.status.success() => Ok(()),
                            Ok(_) => Err(SystemRequirementError::VenvCreationFailed(
                                "Unable to use venv module".to_string()
                            )),
                            Err(e) => Err(SystemRequirementError::VenvCreationFailed(
                                format!("Failed to test venv creation: {}", e)
                            ))
                        }
                }
        } else {
            match std::process::Command::new("python3")
                .arg("-m")
                .arg("venv")
                .arg("--help")
                .output() {
                    Ok(output) if output.status.success() => Ok(()),
                    Ok(_) => Err(SystemRequirementError::VenvCreationFailed(
                        "Unable to use venv module".to_string()
                    )),
                    Err(e) => Err(SystemRequirementError::VenvCreationFailed(
                        format!("Failed to test venv creation: {}", e)
                    ))
                }
        }
    }

    pub fn check_system_requirements(&self) -> Result<(), SystemRequirementError> {
        // Python 설치 확인
        Self::check_python_installation()?;

        // venv 생성 가능 여부 확인
        Self::check_venv_capability()?;

        // 운영체제별 추가 요구사항 확인
        if cfg!(target_os = "windows") {
            // Windows 특정 요구사항 체크
            // TODO: Add Windows-specific checks if needed
        } else if cfg!(target_os = "macos") {
            // macOS 특정 요구사항 체크
            // TODO: Add macOS-specific checks if needed
        } else {
            // Linux 특정 요구사항 체크
            // TODO: Add Linux-specific checks if needed
        }

        Ok(())
    }

    pub fn get_system_requirements_message(error: &SystemRequirementError) -> String {
        match error {
            SystemRequirementError::PythonNotFound => 
                "Python is not installed. Please install Python from: https://www.python.org/downloads/".to_string(),
            SystemRequirementError::VenvCreationFailed(msg) => 
                format!("Failed to use Python venv module: {}. Try reinstalling Python or running with administrator privileges.", msg),
        }
    }
}

#[allow(dead_code)]
pub fn is_config_exists() -> bool {
    get_config_path().exists()
}

pub fn get_config_path() -> PathBuf {
    let mut config_dir = dirs::config_dir().expect("Could not find configuration directory");
    config_dir.push("codai");
    std::fs::create_dir_all(&config_dir).expect("Could not create configuration directory");
    config_dir.push("config.toml");
    config_dir
}

#[derive(Debug)]
pub enum ConfigValidationError {
    MissingProvider,
    MissingModel,
    MissingApiKey(String),
    InvalidOllamaHost,
}

#[derive(Debug)]
pub enum SystemRequirementError {
    PythonNotFound,
    VenvCreationFailed(String),
}

pub fn setup_config() -> Result<()> {
    let mut config = Config::load()?;
    
    println!("\nWelcome to Codai CLI Setup Wizard!");
    println!("Use arrow keys to navigate and Enter to select.\n");

    // Select AI service provider
    let providers = vec![
        "OpenAI".to_string(),
        "Anthropic".to_string(), 
        "Gemini".to_string(),
        "Groq".to_string(),
        "Ollama".to_string()
    ];
    
    println!("{}", "Please select an AI service provider:".cyan());
    let mut menu = Menu::new(providers);
    let provider = menu.run()?;
    
    // Enter API key (except for Ollama) only if not already set
    let needs_api_key = match provider.as_str() {
        "OpenAI" => config.openai_api_key.as_ref().map_or(true, |key| key.is_empty()),
        "Anthropic" => config.anthropic_api_key.as_ref().map_or(true, |key| key.is_empty()),
        "Gemini" => config.google_api_key.as_ref().map_or(true, |key| key.is_empty()),
        "Groq" => config.groq_api_key.as_ref().map_or(true, |key| key.is_empty()),
        "Ollama" => false,
        _ => false
    };

    if needs_api_key {
        print!("\nPlease enter your {} API key: ", provider);
        std::io::stdout().flush()?;
        let mut api_key = String::new();
        std::io::stdin().read_line(&mut api_key)?;
        let api_key = api_key.trim().to_string();
        
        match provider.as_str() {
            "OpenAI" => config.openai_api_key = Some(api_key),
            "Anthropic" => config.anthropic_api_key = Some(api_key),
            "Gemini" => config.google_api_key = Some(api_key),
            "Groq" => config.groq_api_key = Some(api_key),
            _ => {}
        }
    }
    
    // Select model
    let models = match provider.as_str() {
        "OpenAI" => vec![
            "gpt-3.5-turbo".to_string(),
            "gpt-4o-mini".to_string(),
            "gpt-4o".to_string(),            
            "gpt-4-turbo".to_string(),
            "gpt-4".to_string()
        ],
        "Anthropic" => vec![
            "claude-3-5-sonnet-20241022".to_string(),
            "claude-3-opus-20240229".to_string(),            
            "claude-3-haiku-20240307".to_string()
        ],
        "Gemini" => vec![
            "gemini-2.0-flash-exp".to_string(),
            "gemini-1.5-pro".to_string(),
            "gemini-1.5-flash".to_string()
        ],
        "Groq" => vec![
            "mixtral-8x7b-32768".to_string(),
            "llama-3.3-70b-versatile".to_string(),
            "llama3-70b-8192".to_string(),
            "gemma2-9b-it".to_string(),
            "gemma-7b-it".to_string()
        ],
        "Ollama" => vec![
            "llama2".to_string(),
            "mistral".to_string(),
            "codellama".to_string(),
            "dolphin-mixtral".to_string()
        ],
        _ => vec![]
    };
    
    println!("\n{}", "Please select a model to use:".cyan());
    let mut menu = Menu::new(models);
    let model = menu.run()?;
    
    // 코드 리뷰 기능 활성화 여부 설정
    println!("\n{}", "Enable code review feature?".cyan());
    let review_options = vec!["Yes".to_string(), "No".to_string()];
    let mut menu = Menu::new(review_options);
    let review_choice = menu.run()?;
    config.code_review_enabled = Some(review_choice == "Yes");
    
    // Save configuration
    config.default_provider = Some(provider.to_lowercase());
    config.default_model = Some(model);
    config.save()?;
    
    if cfg!(target_os = "windows") {
        println!("\n{}", "Configuration saved successfully!".green());
        println!("\nConfiguration file location:");
        println!("%APPDATA%\\codai\\config.toml");
        println!("(Usually at C:\\Users\\username\\AppData\\Roaming\\codai\\config.toml)");
        println!("\nTo manually modify settings, open the above file with Notepad or another text editor and edit in this format:");
        println!("default_provider = \"{}\"  # AI provider (openai, anthropic, gemini, groq, ollama)", config.default_provider.as_ref().unwrap_or(&"openai".to_string()));
        println!("default_model = \"{}\"     # Model to use", config.default_model.as_ref().unwrap_or(&"gpt-3.5-turbo".to_string()));
        println!("code_review_enabled = {}   # Enable/disable code review feature", config.code_review_enabled.unwrap_or(true));
        if let Some(key) = &config.openai_api_key {
            println!("openai_api_key = \"{}...\"  # API key", &key[..6]);
        }
        println!("\nOr install Windows Terminal to use the interactive configuration menu.");
    } else {
        println!("\n{}", "Configuration saved successfully!".green());
        println!("Current settings:");
        println!("- AI Service: {}", config.default_provider.unwrap_or_default());
        println!("- Model: {}", config.default_model.unwrap_or_default());
        println!("- Code Review: {}", if config.code_review_enabled.unwrap_or(true) { "Enabled" } else { "Disabled" });
    }
    
    // API 키 정보 출력 (Windows가 아닌 경우에만)
    if !cfg!(target_os = "windows") {
        if let Some(key) = &config.openai_api_key {
            if !key.is_empty() {
                println!("- OpenAI API Key: {}...", &key[..6]);
            }
        }
        if let Some(key) = &config.anthropic_api_key {
            if !key.is_empty() {
                println!("- Anthropic API Key: {}...", &key[..6]);
            }
        }
        if let Some(key) = &config.google_api_key {
            if !key.is_empty() {
                println!("- Google API Key: {}...", &key[..6]);
            }
        }
        if let Some(key) = &config.groq_api_key {
            if !key.is_empty() {
                println!("- Groq API Key: {}...", &key[..6]);
            }
        }
    }
    
    Ok(())
} 