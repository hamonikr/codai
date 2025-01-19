use anyhow::Result;
use colored::*;
use crossterm::{
    event::{self, Event, KeyCode, KeyEvent, KeyModifiers},
    terminal::{disable_raw_mode, enable_raw_mode},
};
use crate::types::CodeResponse;
use std::io::Write;

pub struct Menu {
    options: Vec<String>,
    selected: usize,
}

impl Menu {
    pub fn new(options: Vec<String>) -> Self {
        Self {
            options,
            selected: 0,
        }
    }

    pub fn display(&self, response: &CodeResponse) {
        println!("\n{}", "=".repeat(80).yellow());
        println!("{}", "Generated code:".cyan());
        if response.code.is_empty() {
            println!("No code was generated.");
        } else {
            println!("{}", response.code);
            println!();
        }
        
        if let Some(packages) = &response.packages {
            if !packages.is_empty() {
                println!("Required packages:");
                for package in packages {
                    println!("- {}", package);
                }
                println!();
            }
        }

        if let Some(explanation) = &response.explanation {
            if !explanation.is_empty() {
                println!("\n{}", "Explanation:".cyan());
                println!("{}", explanation);
            }
        }

        println!("\n{}", "Please select an option:".yellow());
        self.display_menu_options();
        std::io::stdout().flush().unwrap();
    }

    fn display_menu_options(&self) {
        // Display menu options with left alignment
        for (i, option) in self.options.iter().enumerate() {
            if i == self.selected {
                println!("{} {}", "→".yellow(), option.cyan().bold());
            } else {
                println!("  {}", option);
            }
        }
        std::io::stdout().flush().unwrap();
    }

    fn update_menu(&mut self) {
        // Move cursor to menu start position
        print!("\x1B[{}A", self.options.len());
        std::io::stdout().flush().unwrap();
        
        // Redraw menu with left alignment
        for (i, option) in self.options.iter().enumerate() {
            print!("\r\x1B[K"); // Clear current line
            if i == self.selected {
                println!("{} {}", "→".yellow(), option.cyan().bold());
            } else {
                println!("  {}", option);
            }
        }
        std::io::stdout().flush().unwrap();
    }

    pub fn handle_input(&mut self) -> Result<Option<usize>> {
        enable_raw_mode()?;
        let result = match event::read()? {
            Event::Key(KeyEvent { code, modifiers, .. }) => {
                match code {
                    KeyCode::Char('c') if modifiers.contains(KeyModifiers::CONTROL) => {
                        disable_raw_mode()?;
                        println!("\n{}", "Exiting...".yellow());
                        std::process::exit(0);
                    }
                    KeyCode::Up => {
                        if self.selected > 0 {
                            self.selected -= 1;
                            self.update_menu();
                        }
                        None
                    }
                    KeyCode::Down => {
                        if self.selected < self.options.len() - 1 {
                            self.selected += 1;
                            self.update_menu();
                        }
                        None
                    }
                    KeyCode::Enter => {
                        disable_raw_mode()?;
                        println!();
                        Some(self.selected)
                    }
                    KeyCode::Esc => {
                        disable_raw_mode()?;
                        println!("\n{}", "Exiting...".yellow());
                        std::process::exit(0);
                    }
                    _ => None
                }
            }
            _ => None
        };
        disable_raw_mode()?;
        Ok(result)
    }

    pub fn run(&mut self) -> Result<String> {
        enable_raw_mode()?;
        
        // Initial display with clear line
        for (i, option) in self.options.iter().enumerate() {
            print!("\r\x1B[K"); // Clear current line
            if i == self.selected {
                println!("{} {}", "→".yellow(), option.cyan().bold());
            } else {
                println!("  {}", option);
            }
        }
        std::io::stdout().flush().unwrap();

        loop {
            if let Event::Key(KeyEvent { code, modifiers, .. }) = event::read()? {
                match code {
                    KeyCode::Up => {
                        if self.selected > 0 {
                            self.selected -= 1;
                            self.update_menu();
                        }
                    }
                    KeyCode::Down => {
                        if self.selected < self.options.len() - 1 {
                            self.selected += 1;
                            self.update_menu();
                        }
                    }
                    KeyCode::Enter => {
                        disable_raw_mode()?;
                        println!("\nSelected: {}", self.options[self.selected].cyan());
                        return Ok(self.options[self.selected].clone());
                    }
                    KeyCode::Char('c') if modifiers.contains(KeyModifiers::CONTROL) => {
                        disable_raw_mode()?;
                        return Err(anyhow::anyhow!("Setup cancelled by user."));
                    }
                    _ => {}
                }
            }
        }
    }

    pub fn reset_selection(&mut self) {
        self.selected = 0;
    }
}

pub fn display_logo(version: &str) {
    println!("\n{}", "=".repeat(50).yellow());
    println!("{}", format!("AI.RUN CLI v{}", version).yellow());
    println!("{}", "Empowering Your AI Journey (https://invesume.com)".white());
    println!("{}", "=".repeat(50).yellow());
}