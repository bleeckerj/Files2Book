# File2Book Desktop (Tauri + Python)

## Project Brief

**File2Book Desktop** is a cross-platform desktop application that wraps the existing `File2Book` Python command-line tool with a minimal, focused graphical interface.

The purpose of this project is **not** to rewrite File2Book’s core logic, but to:
- Preserve the existing Python CLI as the authoritative conversion engine
- Provide a simple drag-and-drop desktop UI
- Package the system as a macOS / Windows / Linux desktop app using **Tauri**

This repository already contains the **CLI version of File2Book**.  
This README defines a new desktop application layer (Path A) that shells out to Python.

This document is written to be consumed by **GitHub Copilot / agentic coding assistants** to scaffold and implement the desktop application correctly.

---

## Goals

- Drag-and-drop a **file or directory** onto the app
- Configure a small set of File2Book parameters (page size, aspect ratio, recursion depth, etc.)
- Invoke the existing Python CLI with those parameters
- Generate a final PDF “book”
- Display success, failure, and basic progress feedback
- Remain cross-platform and simple

**Non-goals**
- Rewriting the File2Book conversion pipeline
- Reimplementing PDF logic in Rust
- Over-designing the UI or adding document editing features

---

## High-Level Architecture

```
┌──────────────────────────┐
│  Desktop UI (Webview)    │
│  HTML / CSS / JS         │
│  Drag & Drop + Form      │
└───────────┬──────────────┘
            │ Tauri invoke()
┌───────────▼──────────────┐
│  Tauri Backend (Rust)    │
│  - Receives input paths  │
│  - Builds CLI arguments  │
│  - Spawns Python process │
│  - Captures output       │
└───────────┬──────────────┘
            │ shell out
┌───────────▼──────────────┐
│  Python CLI (existing)   │
│  File2Book               │
│  - Traverses directories│
│  - Converts files to PDF│
│  - Assembles final book │
└──────────────────────────┘
```

**Key principle:**  
Tauri is a thin shell. Python does the work.

---

## Existing Assumptions (Important)

- The File2Book CLI already exists in this repo
- It can be invoked as:

```bash
python -m file2book <INPUT_PATH> [OPTIONS...]
```

- The CLI:
  - Accepts file or directory paths
  - Recursively traverses directories (with depth control)
  - Outputs a final PDF
  - Prints the final output path to `stdout`

If any of these assumptions are not yet true, **fix the CLI first** before building the GUI.

---

## Desktop App Responsibilities

### UI Responsibilities
- Accept drag-and-drop of **folders or files**
- Store the absolute filesystem path
- Provide simple controls:
  - Page size (A4, A5, Letter, etc.)
  - Aspect ratio (e.g. 3:2, 4:3)
  - Recursion depth (optional)
- Show:
  - Current status (idle, running, done, error)
  - Final output path on success

### Rust Backend Responsibilities
- Expose a Tauri command like:
  ```rust
  run_file2book(input_path, options)
  ```
- Convert UI options to CLI flags
- Spawn the Python process via `std::process::Command`
- Capture stdout / stderr
- Return:
  - Success → final PDF path
  - Failure → error message

### Python Responsibilities
- None beyond the existing CLI
- No GUI code
- No Rust bindings

---

## Suggested Repository Layout

```
file2book/
├─ file2book/               # existing Python package
│  ├─ core.py
│  ├─ __main__.py
│  └─ ...
│
├─ desktop/                 # NEW: Tauri application
│  ├─ src/                  # frontend (JS / TS)
│  │  └─ App.(tsx|js)
│  ├─ src-tauri/
│  │  ├─ src/
│  │  │  └─ main.rs
│  │  └─ tauri.conf.json
│  ├─ package.json
│  └─ README.md
│
├─ README.md                # main repo README
└─ README_desktop.md        # THIS FILE
```

---

## Tauri Command Contract (Important)

The Tauri backend should expose **one primary command**:

```rust
#[tauri::command]
fn run_file2book(
    input_path: String,
    options: File2BookOptions
) -> Result<String, String>
```

Where:

```rust
struct File2BookOptions {
    page_size: String,
    aspect_ratio: String,
    depth: Option<i32>,
}
```

Returned string = final PDF path.

---

## CLI Argument Mapping

The Rust backend should map options exactly to CLI flags:

| UI Option        | CLI Flag            |
|------------------|---------------------|
| input_path       | positional argument |
| page_size        | --page-size         |
| aspect_ratio     | --aspect-ratio      |
| depth            | --depth             |

Example invocation constructed in Rust:

```bash
python -m file2book /path/to/folder \
  --page-size=A5 \
  --aspect-ratio=3:2 \
  --depth=3
```

---

## Progress Handling (Optional, Phase 2)

If implemented later:

- Python emits lines like:
  ```
  PROGRESS:0.35
  ```
- Rust reads stdout line-by-line
- Rust emits Tauri events to frontend
- Frontend updates a progress bar

This is **optional** for v1.

---

## Python Environment Strategy

Initial implementation assumes:
- A bundled Python runtime with all CLI dependencies is shipped with the app
- The Tauri installer handles installing/extracting that runtime so `python -m file2book` is always runnable from Rust

Later enhancements may:
- Streamline the bundled runtime size
- Improve how the Rust backend locates the shipped interpreter

Do **not** block v1 on packaging the installer, but do bundle Python.

---

## Design Constraints

- Minimal UI
- No wizard flows
- No previews
- One job at a time
- “Drop folder → configure → make book”

---

## Development Order (Recommended)

1. Ensure File2Book CLI is stable
2. Scaffold Tauri app
3. Implement drag-and-drop path capture
4. Implement Rust → Python shell-out
5. Display success / failure
6. Add polish only after core path works

---

## Project Intent

This desktop app exists to:
- Make File2Book usable without a terminal
- Preserve the author’s Python investment
- Provide a foundation for future refinement

This is a **tool**, not a platform.

---

## License

Same license as File2Book.
