# preprocess_mj_json.py — README

Purpose
-------
`preprocess_mj_json.py` scans a folder of JSON files produced by my Midjourney downloader (or similar) and produces a single JSON array suitable for ingestion by `create_file_cards.py`. For each input JSON file the script:

- extracts the `image_path` as `filepath`
- extracts a simplified `metadata` object containing:
  - `_prompt` — everything between the first pair of `**` in `content` (if any)
  - `_created` and `_title` — a human readable ISO-parsed `created_at` timestamp (falls back to raw string if parsing fails)
  - `_filename` — `downloaded_filename` (if present)
  - `qr_data` — `full_path` (if present)

It skips hidden files and can recurse into subdirectories up to a configurable depth.

Requirements
------------
- Python 3.7+ (uses `datetime.fromisoformat`)
- Standard library only (no extra pip installs required)

Quick example
-------------
Run on a folder of `.json` files and write the combined output:

```bash
python3 preprocess_mj_json.py \
  --json-folder-path /path/to/mj_json_folder \
  --output-folder-path /path/to/output \
  --output-json-name combined.json \
  --max-depth 2
```

Command line arguments
----------------------
- `--json-folder-path` (required)  
  Path to the folder containing JSON files to process.

- `--output-folder-path` (optional, default `.`)  
  Directory where the output JSON file will be saved. The directory will be created if needed.

- `--output-json-name` (required)  
  Filename to write (e.g. `mj_prepared.json`).

- `--max-depth` (optional, default `1`)  
  Maximum recursion depth for directories. `1` means only the top-level folder; increase to process nested subfolders.

Behavior and notes
------------------
- Hidden files and directories (names beginning with `.`) are skipped.
- The script tries to parse `created_at` with `datetime.fromisoformat`. If parsing fails it leaves the raw value in `_created` and `_title`.
- The `_prompt` field is extracted with a simple regex that finds the first `**...**` pair in the `content` string. If none are found `_prompt` will be an empty string.
- On errors while processing an individual JSON file the script prints an error message and continues processing other files.
- The resulting JSON file is an array of entries like:

```json
[
  {
    "filepath": "path/to/image.jpg",
    "metadata": {
      "_prompt": "the extracted prompt text",
      "_created": "April 15, 2025 19:32:21",
      "_title": "April 15, 2025 19:32:21",
      "_filename": "downloaded_name.jpg",
      "qr_data": "/full/path/to/image.jpg"
    }
  }
]
```

Integration
-----------
The output can be passed to your existing `create_file_cards.py` as a file list so previews/cards are generated using the normalized fields.

Troubleshooting
---------------
- If timestamps remain unparsed, inspect `created_at` values — the script expects ISO-like strings for `datetime.fromisoformat`. Non-ISO formats will be preserved as-is.
- If `_prompt` extraction misses content, check that prompts are enclosed in `**...**`. The regex extracts only the first matching pair.

License / Attribution
---------------------
Provided as-is for local use. Modify to suit your data and pipeline.

```// filepath: /Users/julian/Code/Files2Book/README_preprocess_mj.md
# preprocess_mj_json.py — README

Purpose
-------
`preprocess_mj_json.py` scans a folder of JSON files produced by Midjourney (or similar) and produces a single JSON array suitable for ingestion by `create_file_cards.py`. For each input JSON file the script:

- extracts the `image_path` as `filepath`
- extracts a simplified `metadata` object containing:
  - `_prompt` — everything between the first pair of `**` in `content` (if any)
  - `_created` and `_title` — a human readable ISO-parsed `created_at` timestamp (falls back to raw string if parsing fails)
  - `_filename` — `downloaded_filename` (if present)
  - `qr_data` — `full_path` (if present)

It skips hidden files and can recurse into subdirectories up to a configurable depth.

Requirements
------------
- Python 3.7+ (uses `datetime.fromisoformat`)
- Standard library only (no extra pip installs required)

Quick example
-------------
Run on a folder of `.json` files and write the combined output:

```bash
python3 preprocess_mj_json.py \
  --json-folder-path /path/to/mj_json_folder \
  --output-folder-path /path/to/output \
  --output-json-name combined.json \
  --max-depth 2
```

Command line arguments
----------------------
- `--json-folder-path` (required)  
  Path to the folder containing JSON files to process.

- `--output-folder-path` (optional, default `.`)  
  Directory where the output JSON file will be saved. The directory will be created if needed.

- `--output-json-name` (required)  
  Filename to write (e.g. `mj_prepared.json`).

- `--max-depth` (optional, default `1`)  
  Maximum recursion depth for directories. `1` means only the top-level folder; increase to process nested subfolders.

Behavior and notes
------------------
- Hidden files and directories (names beginning with `.`) are skipped.
- The script tries to parse `created_at` with `datetime.fromisoformat`. If parsing fails it leaves the raw value in `_created` and `_title`.
- The `_prompt` field is extracted with a simple regex that finds the first `**...**` pair in the `content` string. If none are found `_prompt` will be an empty string.
- On errors while processing an individual JSON file the script prints an error message and continues processing other files.
- The resulting JSON file is an array of entries like:

```json
[
  {
    "filepath": "path/to/image.jpg",
    "metadata": {
      "_prompt": "the extracted prompt text",
      "_created": "April 15, 2025 19:32:21",
      "_title": "April 15, 2025 19:32:21",
      "_filename": "downloaded_name.jpg",
      "qr_data": "/full/path/to/image.jpg"
    }
  }
]
```

Integration
-----------
The output can be passed to your existing `create_file_cards.py` as a file list so previews/cards are generated using the normalized fields.

Troubleshooting
---------------
- If timestamps remain unparsed, inspect `created_at` values — the script expects ISO-like strings for `datetime.fromisoformat`. Non-ISO formats will be preserved as-is.
- If `_prompt` extraction misses content, check that prompts are enclosed in `**...**`. The regex extracts only the first matching pair.

License / Attribution
---------------------
Provided as-is for local use. Modify to suit your data and pipeline.
