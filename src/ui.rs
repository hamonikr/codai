use anyhow::Result;
use colored::*;
use crossterm::{
    event::{self, Event, KeyCode, KeyEvent, KeyModifiers},
    terminal::{disable_raw_mode, enable_raw_mode},
    queue,
    cursor,
    terminal::Clear as TerminalClear,
    terminal::ClearType,
};
use crate::types::CodeResponse;
use std::io::{Write, stdout};

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

    fn display_menu_options(&self) {
        let mut stdout = stdout();
        
        // 현재 커서 위치에서 메뉴 옵션만큼만 위로 이동
        if cfg!(windows) {
            queue!(
                stdout,
                cursor::MoveUp(self.options.len() as u16),
                TerminalClear(ClearType::FromCursorDown)
            ).unwrap();
        } else {
            // Unix 계열에서는 ANSI 이스케이프 시퀀스 사용
            for _ in 0..self.options.len() {
                print!("\x1B[A");  // 한 줄 위로
                print!("\r\x1B[K"); // 현재 줄 지우기
            }
        }
        
        // 메뉴 옵션 출력
        for (i, option) in self.options.iter().enumerate() {
            if i == self.selected {
                println!("\r→ {}", option.cyan().bold());
            } else {
                println!("\r  {}", option);
            }
        }
        stdout.flush().unwrap();
    }

    pub fn run(&mut self) -> Result<String> {
        enable_raw_mode()?;
        
        // 초기 메뉴 표시
        self.display_menu_options();

        loop {
            if let Event::Key(KeyEvent { code, modifiers, .. }) = event::read()? {
                match code {
                    KeyCode::Up => {
                        if self.selected > 0 {
                            self.selected -= 1;
                            self.display_menu_options();
                        }
                    }
                    KeyCode::Down => {
                        if self.selected < self.options.len() - 1 {
                            self.selected += 1;
                            self.display_menu_options();
                        }
                    }
                    KeyCode::Enter => {
                        disable_raw_mode()?;
                        // 메뉴 옵션만 지우기
                        if cfg!(windows) {
                            queue!(
                                stdout(),
                                cursor::MoveUp(self.options.len() as u16),
                                TerminalClear(ClearType::FromCursorDown)
                            ).unwrap();
                        } else {
                            for _ in 0..self.options.len() {
                                print!("\x1B[A");  // 한 줄 위로
                                print!("\r\x1B[K"); // 현재 줄 지우기
                            }
                        }
                        println!("\rSelected: {}", self.options[self.selected].cyan());
                        return Ok(self.options[self.selected].clone());
                    }
                    KeyCode::Char('c') if modifiers.contains(KeyModifiers::CONTROL) => {
                        disable_raw_mode()?;
                        println!("\nSetup cancelled by user.");
                        return Err(anyhow::anyhow!("Setup cancelled by user."));
                    }
                    _ => {}
                }
            }
        }
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
                            self.display_menu_options();
                        }
                        None
                    }
                    KeyCode::Down => {
                        if self.selected < self.options.len() - 1 {
                            self.selected += 1;
                            self.display_menu_options();
                        }
                        None
                    }
                    KeyCode::Enter => {
                        disable_raw_mode()?;
                        // 메뉴 옵션만 지우기
                        if cfg!(windows) {
                            queue!(
                                stdout(),
                                cursor::MoveUp(self.options.len() as u16),
                                TerminalClear(ClearType::FromCursorDown)
                            ).unwrap();
                        } else {
                            for _ in 0..self.options.len() {
                                print!("\x1B[A");  // 한 줄 위로
                                print!("\r\x1B[K"); // 현재 줄 지우기
                            }
                        }
                        println!("\rSelected: {}", self.options[self.selected].cyan());
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
    }

    pub fn reset_selection(&mut self) {
        self.selected = 0;
    }
}

pub fn display_logo(version: &str) {
    println!("\n{}", "=".repeat(50).yellow());
    println!("{}", format!("Codai v{}", version).yellow());
    println!("{}", "The easiest way to bring AI to your computer".white());
    println!("{}", "=".repeat(50).yellow());
    println!();  // 빈 줄 추가
}