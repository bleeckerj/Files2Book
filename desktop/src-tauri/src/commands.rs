use serde::Deserialize;
use std::{
    fmt,
    path::{Path, PathBuf},
    process::Command,
};

/// Options received from the frontend.
#[derive(Debug, Deserialize)]
pub struct File2BookOptions {
    pub page_size: String,
    pub aspect_ratio: String,
    pub depth: Option<i32>,
}

/// Friendly wrapper around command errors so we can attach stderr info.
#[derive(Debug)]
struct CommandError {
    message: String,
}

impl fmt::Display for CommandError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for CommandError {}

/// Tauri command exposed to the frontend.
#[tauri::command]
pub fn run_file2book(input_path: String, options: File2BookOptions) -> Result<String, String> {
    let python_path = match locate_python_path() {
        Ok(path) => path,
        Err(err) => return Err(err.to_string()),
    };

    let args = build_cli_arguments(&input_path, &options);
    let output = Command::new(python_path)
        .args(&args)
        .output()
        .map_err(|e| e.to_string())?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        let final_path = stdout
            .lines()
            .rev()
            .find(|line| !line.trim().is_empty())
            .map(str::trim)
            .unwrap_or("")
            .to_string();

        if final_path.is_empty() {
            Err("File2Book succeeded but did not report an output path.".to_string())
        } else {
            Ok(final_path)
        }
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(CommandError {
            message: format!("File2Book failed: {}", stderr.trim()),
        }
        .to_string())
    }
}

fn build_cli_arguments(input_path: &str, options: &File2BookOptions) -> Vec<String> {
    let mut args = vec![
        "-m".to_string(),
        "file2book".to_string(),
        input_path.to_string(),
        format!("--page-size={}", options.page_size),
        format!("--aspect-ratio={}", options.aspect_ratio),
    ];

    if let Some(depth) = options.depth {
        args.push(format!("--depth={}", depth));
    }

    args
}

fn locate_python_path() -> Result<String, CommandError> {
    if let Ok(explicit) = std::env::var("FILE2BOOK_PYTHON_PATH") {
        return Ok(explicit);
    }

    let exe_dir = std::env::current_exe()
        .map_err(|e| CommandError { message: e.to_string() })?
        .parent()
        .ok_or_else(|| CommandError {
            message: "Failed to determine executable directory".into(),
        })?
        .to_path_buf();

    if let Some(candidate) = discover_bundled_python(&exe_dir) {
        return Ok(candidate.to_string_lossy().to_string());
    }

    // Fallback to system python so developers can run in dev environments.
    let fallback = if cfg!(windows) { "python.exe" } else { "python3" };
    Ok(fallback.to_string())
}

fn discover_bundled_python(exe_dir: &Path) -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if cfg!(windows) {
        candidates.push(exe_dir.join("python").join("python.exe"));
        candidates.push(exe_dir.join("resources").join("python").join("python.exe"));
    } else {
        candidates.push(exe_dir.join("python").join("bin").join("python3"));
        candidates.push(exe_dir.join("python").join("bin").join("python"));
        candidates.push(
            exe_dir
                .join("resources")
                .join("python")
                .join("bin")
                .join("python3"),
        );
    }

    candidates.into_iter().find(|path| path.exists())
}
