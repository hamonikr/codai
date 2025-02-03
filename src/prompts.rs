use crate::types::{SYSTEM_PROMPT, CODE_REVIEW_PROMPT};
use std::fs;
use std::path::PathBuf;
use anyhow::Result;

fn get_config_dir() -> Option<PathBuf> {
    if let Some(config_dir) = dirs::config_dir() {
        let codai_config_dir = config_dir.join("codai");
        if !codai_config_dir.exists() {
            if let Err(_) = fs::create_dir_all(&codai_config_dir) {
                return None;
            }
        }
        Some(codai_config_dir)
    } else {
        None
    }
}

fn ensure_prompt_file(filename: &str, default_content: &str) -> Result<PathBuf> {
    if let Some(config_dir) = get_config_dir() {
        let prompt_path = config_dir.join(filename);
        if !prompt_path.exists() {
            fs::write(&prompt_path, default_content)?;
            println!("Created default prompt file: {}", prompt_path.display());
        }
        Ok(prompt_path)
    } else {
        Err(anyhow::anyhow!("Could not create config directory"))
    }
}

fn read_prompt_file(path: PathBuf) -> Result<String> {
    Ok(fs::read_to_string(path)?)
}

pub fn init_default_prompts() -> Result<()> {
    ensure_prompt_file("system_prompt.txt", SYSTEM_PROMPT)?;
    ensure_prompt_file("code_review.txt", CODE_REVIEW_PROMPT)?;
    Ok(())
}

pub fn get_code_generation_prompt(language: &str) -> String {
    let result = ensure_prompt_file("system_prompt.txt", SYSTEM_PROMPT)
        .and_then(read_prompt_file);
    
    match result {
        Ok(content) => content.replace("{language}", language),
        Err(_) => SYSTEM_PROMPT.replace("{language}", language)
    }
}

pub fn get_code_review_prompt() -> String {
    let result = ensure_prompt_file("code_review.txt", CODE_REVIEW_PROMPT)
        .and_then(read_prompt_file);
    
    match result {
        Ok(content) => content,
        Err(_) => CODE_REVIEW_PROMPT.to_string()
    }
} 