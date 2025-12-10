#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use commands::run_file2book;

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![run_file2book])
        .run(tauri::generate_context!())
        .expect("failed to run Tauri application");
}
