use std::path::PathBuf;
use std::process::Command;
use anyhow::Result;
use std::collections::HashSet;
use dirs;
use regex::Regex;
use std::fs;
use colored::*;
use indicatif::{ProgressBar, ProgressStyle};
use std::time::Duration;
use spinners::{Spinner, Spinners};
use std::collections::HashMap;
use lazy_static::lazy_static;
use serde_json::Value;
use crate::config::Config;
use crate::code_generator::generate_code;
use crate::types::{CodeRequest, ExecutionResult, UTILS_PY, TOOLS_CONF};
use std::sync::Mutex;
use crate::history::{HistoryManager, RequestHistory, TokenUsage};
use uuid::Uuid;
use chrono::Utc;
use std::time::Instant;

lazy_static! {
    static ref PACKAGE_MAPPINGS: HashMap<String, String> = {
        let mut map = HashMap::new();
        // 기본 매핑
        map.insert("PIL".to_string(), "pillow".to_string());
        map.insert("sklearn".to_string(), "scikit-learn".to_string());
        
        // 외부 매핑 파일 로드 시도
        if let Ok(content) = fs::read_to_string(
            dirs::config_dir()
                .unwrap_or_else(|| PathBuf::from("~/.config"))
                .join("codai")
                .join("package_mappings.json")
        ) {
            if let Ok(json) = serde_json::from_str::<Value>(&content) {
                if let Some(obj) = json.as_object() {
                    for (k, v) in obj {
                        if let Some(v) = v.as_str() {
                            map.insert(k.clone(), v.to_string());
                        }
                    }
                }
            }
        }
        map
    };

    static ref CODE_REVIEW_STATE: Mutex<bool> = Mutex::new(true);
}

pub fn set_code_review_enabled(enabled: bool) {
    if let Ok(mut state) = CODE_REVIEW_STATE.lock() {
        *state = enabled;
    }
}

fn create_spinner(msg: &'static str) -> ProgressBar {
    let pb = ProgressBar::new_spinner();
    pb.enable_steady_tick(Duration::from_millis(120));
    pb.set_style(
        ProgressStyle::default_spinner()
            .tick_strings(&[
                "⠋",
                "⠙",
                "⠹",
                "⠸",
                "⠼",
                "⠴",
                "⠦",
                "⠧",
                "⠇",
                "⠏",
            ])
            .template("{spinner:.yellow} {msg}")
            .unwrap()
    );
    pb.set_message(msg);
    pb
}

pub struct CodeExecutor {
    venv_path: PathBuf,
    python_path: PathBuf,
    installed_packages: HashSet<String>,
}

impl CodeExecutor {
    pub fn new(venv_path: PathBuf, python_path: PathBuf) -> Self {
        Self {
            venv_path,
            python_path,
            installed_packages: HashSet::new(),
        }
    }

    pub fn execute_code(&mut self, code: &str) -> Result<ExecutionResult> {
        let sp = create_spinner("Preparing code execution...");
        
        // 가상 환경 내부에 임시 디렉토리 생성
        let temp_dir = self.venv_path.join("temp");
        fs::create_dir_all(&temp_dir)?;

        let file_path = temp_dir.join("temp_code.py");
        fs::write(&file_path, code)?;

        sp.set_message("Executing code...");
        
        let mut command = Command::new(&self.python_path);
        command.arg(&file_path);
        
        // 가상 환경의 site-packages 경로 설정
        let site_packages = if cfg!(windows) {
            self.venv_path.join("Lib").join("site-packages")
        } else {
            let output = Command::new(&self.python_path)
                .args(&["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"])
                .output()?;
            let python_version = String::from_utf8_lossy(&output.stdout).trim().to_string();
            self.venv_path.join("lib")
                .join(format!("python{}", python_version))
                .join("site-packages")
        };

        // PYTHONPATH 환경 변수 설정
        if let Some(site_packages_str) = site_packages.to_str() {
            command.env("PYTHONPATH", site_packages_str);
        }

        let output = command.output()?;

        let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        let success = output.status.success();

        // 임시 파일 및 디렉토리 정리
        if let Err(e) = fs::remove_file(&file_path) {
            eprintln!("Warning: Failed to remove temporary file: {}", e);
        }
        if let Err(e) = fs::remove_dir(&temp_dir) {
            eprintln!("Warning: Failed to remove temporary directory: {}", e);
        }

        sp.finish_and_clear();

        Ok(ExecutionResult {
            stdout,
            stderr,
            success,
        })
    }

    pub fn setup_venv(&mut self) -> Result<()> {
        if !self.venv_path.exists() {
            let sp = create_spinner("Setting up Python virtual environment...");
            let python = if cfg!(windows) { "python" } else { "python3" };
            
            let status = Command::new(python)
                .args(&["-m", "venv", self.venv_path.to_str().unwrap()])
                .status()?;

            if !status.success() {
                sp.finish_and_clear();
                return Err(anyhow::anyhow!("Failed to create virtual environment"));
            }

            let pip_path = if cfg!(windows) {
                self.venv_path.join("Scripts").join("pip.exe")
            } else {
                self.venv_path.join("bin").join("pip")
            };

            sp.set_message("Upgrading pip...");
            let status = Command::new(&pip_path)
                .args(&["install", "--upgrade", "pip"])
                .status()?;

            if !status.success() {
                sp.finish_and_clear();
                return Err(anyhow::anyhow!("Failed to upgrade pip"));
            }

            // 필수 패키지 설치
            sp.set_message("Installing required packages...");
            let required_packages = ["setuptools", "wheel", "requests", "beautifulsoup4"];
            for package in required_packages.iter() {
                let status = Command::new(&pip_path)
                    .args(&["install", package])
                    .status()?;
                
                if !status.success() {
                    sp.finish_and_clear();
                    return Err(anyhow::anyhow!("Failed to install {}", package));
                }
            }

            sp.finish_and_clear();
        }

        // Get Python version
        let output = Command::new(&self.python_path)
            .args(&["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"])
            .output()?;
        
        let python_version = String::from_utf8_lossy(&output.stdout).trim().to_string();
        
        // utils.py 파일을 임베디드 리소스에서 생성
        let target_dir = if cfg!(windows) {
            self.venv_path.join("Lib").join("site-packages")
        } else {
            self.venv_path.join("lib")
                .join(format!("python{}", python_version))
                .join("site-packages")
        };
        let target_path = target_dir.join("utils.py");

        // 대상 디렉토리가 없으면 생성
        if !target_dir.exists() {
            fs::create_dir_all(&target_dir)?;
        }

        // utils.py 파일이 없을 때만 생성
        if !target_path.exists() {
            fs::write(&target_path, UTILS_PY)?;
            println!("{}", "Created utils.py in virtual environment.".green());
        }

        // tools.conf 파일을 임베디드 리소스에서 생성
        let config_dir = dirs::config_dir()
            .ok_or_else(|| anyhow::anyhow!("Could not find config directory"))?
            .join("codai");

        if !config_dir.exists() {
            fs::create_dir_all(&config_dir)?;
        }

        let tools_conf_path = config_dir.join("tools.conf");
        // tools.conf 파일이 없을 때만 생성
        if !tools_conf_path.exists() {
            fs::write(&tools_conf_path, TOOLS_CONF)?;
            println!("{}", "Created tools.conf in config directory.".green());
        }

        Ok(())
    }

    pub fn install_package(&mut self, package: &str) -> Result<()> {
        if self.installed_packages.contains(package) {
            return Ok(());
        }

        let mut sp = Spinner::new(Spinners::Dots9, format!("Installing {}...", package));

        let install_package = match PACKAGE_MAPPINGS.get(package) {
            Some(mapped) => mapped.to_string(),
            None => package.to_string()
        };

        // pip search를 통한 패키지 검색 시도 (pip 21.0 이후 비활성화됨)
        let output = Command::new(&self.python_path)
            .arg("-m")
            .arg("pip")
            .arg("install")
            .arg(&install_package)
            .output()?;

        if !output.status.success() {
            // 설치 실패 시 PyPI API를 통한 패키지 검색 시도
            if let Ok(similar_package) = self.find_similar_package(package) {
                println!("  {} Trying alternative package name: {}", "ℹ".blue(), similar_package);
                let output = Command::new(&self.python_path)
                    .arg("-m")
                    .arg("pip")
                    .arg("install")
                    .arg(&similar_package)
                    .output()?;

                if output.status.success() {
                    // 성공한 매핑 정보 저장
                    if let Err(e) = self.save_package_mapping(package, &similar_package) {
                        eprintln!("Warning: Failed to save package mapping: {}", e);
                    }
                    self.installed_packages.insert(package.to_string());
                    sp.stop();
                    println!("  {} {}", "✓".green(), format!("{} installed", similar_package).green());
                    return Ok(());
                }
            }
            
            sp.stop();
            println!("  {} {}", "✗".red(), format!("Failed to install {}", package).red());
            return Err(anyhow::anyhow!(
                "Failed to install package {}: {}",
                package,
                String::from_utf8_lossy(&output.stderr)
            ));
        }

        self.installed_packages.insert(package.to_string());
        sp.stop();
        println!("  {} {}", "✓".green(), format!("{} installed", install_package).green());
        Ok(())
    }

    fn find_similar_package(&self, package: &str) -> Result<String> {
        // PyPI JSON API를 사용하여 패키지 검색
        let url = format!("https://pypi.org/pypi/{}/json", package);
        let response = ureq::get(&url).call();

        match response {
            Ok(_) => Ok(package.to_string()),
            Err(_) => {
                // 검색 API를 사용하여 유사한 패키지 찾기
                let search_url = format!(
                    "https://pypi.org/search/?q={}&o=",
                    urlencoding::encode(package)
                );
                let response = ureq::get(&search_url).call()?;
                let text = response.into_string()?;

                // 간단한 휴리스틱: 첫 번째 검색 결과 사용
                let re = Regex::new(r#"class="package-snippet__name">([^<]+)</span>"#)?;
                if let Some(captures) = re.captures(&text) {
                    if let Some(name) = captures.get(1) {
                        return Ok(name.as_str().to_string());
                    }
                }
                
                Ok(package.to_string())
            }
        }
    }

    fn save_package_mapping(&self, original: &str, mapped: &str) -> Result<()> {
        let config_dir = dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("~/.config"))
            .join("codai");
        
        fs::create_dir_all(&config_dir)?;
        let mapping_file = config_dir.join("package_mappings.json");

        let mut mappings = if mapping_file.exists() {
            let content = fs::read_to_string(&mapping_file)?;
            serde_json::from_str(&content)?
        } else {
            serde_json::Map::new()
        };

        mappings.insert(original.to_string(), Value::String(mapped.to_string()));
        
        let content = serde_json::to_string_pretty(&mappings)?;
        fs::write(mapping_file, content)?;
        
        Ok(())
    }

    pub fn extract_import_errors(&self, error_message: &str) -> HashSet<String> {
        let mut missing_packages = HashSet::new();
        let mut package_replacements = HashMap::new();
        
        // ModuleNotFoundError: No module named 'package_name'
        let module_regex = Regex::new(r"No module named '([^']+)'").unwrap();
        
        // ImportError: cannot import name 'name' from 'package'
        let import_regex = Regex::new(r"cannot import name '[^']+' from '([^']+)'").unwrap();
        
        // Package deprecation/replacement messages
        let deprecated_regex = Regex::new(r"[Tt]he '([^']+)' PyPI package is deprecated, use '([^']+)'").unwrap();
        let use_instead_regex = Regex::new(r"[Uu]se '([^']+)' instead of '([^']+)'").unwrap();
        let replace_with_regex = Regex::new(r"[Rr]eplace '([^']+)' with '([^']+)'").unwrap();

        // 패키지 이름 변경 정보 수집
        for line in error_message.lines() {
            if let Some(captures) = deprecated_regex.captures(line) {
                if let (Some(old), Some(new)) = (captures.get(1), captures.get(2)) {
                    package_replacements.insert(old.as_str().to_string(), new.as_str().to_string());
                }
            }
            if let Some(captures) = use_instead_regex.captures(line) {
                if let (Some(new), Some(old)) = (captures.get(1), captures.get(2)) {
                    package_replacements.insert(old.as_str().to_string(), new.as_str().to_string());
                }
            }
            if let Some(captures) = replace_with_regex.captures(line) {
                if let (Some(old), Some(new)) = (captures.get(1), captures.get(2)) {
                    package_replacements.insert(old.as_str().to_string(), new.as_str().to_string());
                }
            }
        }

        // 누락된 패키지 수집 및 이름 변경 적용
        for line in error_message.lines() {
            if let Some(captures) = module_regex.captures(line) {
                if let Some(package) = captures.get(1) {
                    let package_name = package.as_str().to_string();
                    if !package_name.contains('.') {  // 상대 경로 import는 제외
                        if let Some(replacement) = package_replacements.get(&package_name) {
                            println!("  {} Package '{}' is deprecated, using '{}' instead", 
                                "ℹ".blue(), package_name, replacement);
                            missing_packages.insert(replacement.clone());
                        } else {
                            missing_packages.insert(package_name);
                        }
                    }
                }
            }
            
            if let Some(captures) = import_regex.captures(line) {
                if let Some(package) = captures.get(1) {
                    let package_name = package.as_str().to_string();
                    if !package_name.contains('.') {  // 상대 경로 import는 제외
                        if let Some(replacement) = package_replacements.get(&package_name) {
                            println!("  {} Package '{}' is deprecated, using '{}' instead", 
                                "ℹ".blue(), package_name, replacement);
                            missing_packages.insert(replacement.clone());
                        } else {
                            missing_packages.insert(package_name);
                        }
                    }
                }
            }
        }
        
        missing_packages
    }
}

pub async fn execute_code_with_retry(
    message: &str,
    language: &str,
    config: &Config,
    provider: Option<String>,
    initial_code: Option<String>,
) -> Result<ExecutionResult> {
    let start_time = Instant::now();
    let home_dir = dirs::home_dir()
        .ok_or_else(|| anyhow::anyhow!("Can't find home directory."))?;
    let venv_path = home_dir.join(".codai-venv");
    let python_path = if cfg!(windows) {
        venv_path.join("Scripts").join("python.exe")
    } else {
        venv_path.join("bin").join("python")
    };

    let mut executor = CodeExecutor::new(venv_path, python_path);
    executor.setup_venv()?;

    let mut retry_count = 0;
    let max_retries = 3;
    let mut current_code: String;
    let mut response_tokens = None;

    // 초기 코드 사용 또는 생성
    if let Some(code) = initial_code {
        current_code = code;
    } else {
        let request = CodeRequest {
            message: message.to_string(),
            language: Some(language.to_string()),
            model: config.default_model.clone(),
            feedback: None,
            error_message: None,
            execution_result: None,
            provider: provider.clone(),
            task_id: None,
        };

        let response = generate_code(request, config).await?;
        current_code = response.code.clone();
        response_tokens = Some(TokenUsage {
            input: response.input_tokens.unwrap_or(0),
            output: response.output_tokens.unwrap_or(0),
        });
        
        println!("\n{}", "Generated code:".cyan());
        println!("{}", current_code);
    }

    while retry_count < max_retries {
        match executor.execute_code(&current_code) {
            Ok(output) => {
                if output.success {
                    // 히스토리 저장
                    if let Some(true) = config.history_enabled {
                        let mut history_manager = HistoryManager::new(
                            config.history_max_items.unwrap_or(1000),
                            config.history_retention_days.unwrap_or(30),
                        )?;

                        let request_history = RequestHistory {
                            id: Uuid::new_v4().to_string(),
                            timestamp: Utc::now(),
                            request_type: "code".to_string(),
                            message: message.to_string(),
                            model: config.default_model.clone(),
                            provider: provider.clone(),
                            tokens: response_tokens,
                            estimated_cost: None,
                            execution_time: start_time.elapsed().as_secs_f64(),
                        };

                        history_manager.add_request(request_history)?;
                    }

                    return Ok(output);
                } else {
                    // 누락된 패키지 확인
                    let missing_packages = executor.extract_import_errors(&output.stderr);
                    if !missing_packages.is_empty() {
                        println!("\n{}", "Installing missing packages:".yellow());
                        let mut all_packages_installed = true;
                        for package in missing_packages {
                            if let Err(e) = executor.install_package(&package) {
                                println!("Failed to install package {}: {}", package, e);
                                all_packages_installed = false;
                                break;
                            }
                        }
                        if all_packages_installed {
                            continue;  // 패키지 설치 후 같은 코드로 재시도
                        }
                    }
                    
                    if retry_count < max_retries - 1 {
                        println!("\n{}", format!("Regenerating code... (attempt {}/{})", retry_count + 2, max_retries).yellow());
                        
                        let regenerate_request = CodeRequest {
                            message: message.to_string(),
                            language: Some(language.to_string()),
                            model: config.default_model.clone(),
                            feedback: None,
                            error_message: Some(output.stderr),
                            execution_result: None,
                            provider: provider.clone(),
                            task_id: None,
                        };

                        let new_response = generate_code(regenerate_request, config).await?;
                        current_code = new_response.code.clone();
                        println!("\n{}", "Newly generated code:".cyan());
                        println!("{}", current_code);
                    }
                }
            }
            Err(e) => {
                println!("\n{}", "Code execution error:".red());
                println!("{}", e);
                
                if retry_count < max_retries - 1 {
                    println!("\n{}", format!("Regenerating code... (attempt {}/{})", retry_count + 2, max_retries).yellow());
                    
                    let error_request = CodeRequest {
                        message: message.to_string(),
                        language: Some(language.to_string()),
                        model: config.default_model.clone(),
                        feedback: None,
                        error_message: Some(e.to_string()),
                        execution_result: None,
                        provider: provider.clone(),
                        task_id: None,
                    };

                    let new_response = generate_code(error_request, config).await?;
                    current_code = new_response.code.clone();
                    println!("\n{}", "Newly generated code:".cyan());
                    println!("{}", current_code);
                }
            }
        }
        retry_count += 1;
    }

    println!("\n{}", "Maximum retry count reached.".red());
    Err(anyhow::anyhow!("Failed to execute code after {} retries", max_retries))
} 