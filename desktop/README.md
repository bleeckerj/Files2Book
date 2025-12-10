# File2Book Desktop Layer

This directory will house the Tauri-powered desktop wrapper for `File2Book`. It is intentionally small, modular, and documented so the UI layer stays separate from the Rust backend.

## Goals

- Provide a minimal, drag-and-drop UI (under `src/`)
- Keep frontend logic clean (no giant inline scripts)
- Expose a single Rust command (`run_file2book`) in `src-tauri/src/commands.rs`
- Shell out to the bundled Python runtime that ships with the installer

## Development Notes

- Frontend tooling (React/Vite/etc.) should live entirely under `src/`.
- `src-tauri/` contains the Rust command/CLI glue and the `Cargo.toml`/`tauri.conf.json` definitions.
- Environment variables such as `FILE2BOOK_PYTHON_PATH` can be used to locate the bundled interpreter for both dev and production.
- Follow the modularity guideline: split larger helpers into small Rust modules and keep UI components focused.

Next steps:

1. Flesh out the frontend entry point (`src/App.tsx`) with drag/drop + option form + status display.
2. Implement the Rust command that builds CLI args, runs Python, and returns a success path or error message.
3. Wire the Tauri builder to expose that command and connect the JS frontend to it.

## Dev workflow

- Run `npm run tauri:dev` from `desktop/` to launch the dynamic dev flow: the helper script picks an open port, starts Vite on that port, and runs `tauri dev` with a temporary config that points to the same URL so the frontend/backend stay coordinated even if port 3000 is busy.

### Visual guidance

- This UI is built with a neo-brutalist aesthetic—strong borders, high-contrast color blocks, fixed-card layout—in a compact 520×560 shell so it feels like a purposeful tool.
- Typography now loads the bundled **3270 Nerd Font** and **ShareTech Mono Nerd Font** from `desktop/src/assets/fonts/`, so no separate install is required. The CSS still prefers `3270 Nerd Font` for the main UI and falls back to `Space Grotesk` if the files are unavailable.

- Run `npm run tauri:dev` from `desktop/` to launch the dynamic dev flow: the helper script picks an open port, starts Vite on that port, and runs `tauri dev` with a temporary config that points to the same URL so the frontend/backend stay coordinated even if port 3000 is busy.
