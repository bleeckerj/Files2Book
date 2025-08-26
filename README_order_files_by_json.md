# order_files_by_json.py — README

## Purpose

This utility parses a JSON export that contains file entries and timestamps, sorts the files by their timestamp, and writes an ordered list in CSV and/or JSON formats. It is intended to prepare an ordered file list for downstream processing (for example, feeding into create_file_cards.py using the --file-list flag).

## Key features

- Accepts JSON input in two common structures:
  - Legacy format where each top-level element contains a "files" array with objects containing "name" and "timestamp" fields.
  - Flattened format where each element is an object with keys like "filepath", "raw_ts" and "actual_ts".
- Sorts entries by actual timestamp (numeric epoch). Items with missing or unparsable timestamps are placed at the end of the list.
- Produces CSV output (path,timestamp_raw,timestamp_epoch) and/or JSON output (array of objects with filepath, raw_ts, actual_ts).
- Resolves relative paths against a provided target directory; absolute file paths are preserved.

## Requirements

- Python 3.x
- Standard library only (json, csv, argparse, pathlib, os)

## Files

- order_files_by_json.py — script that generates ordered CSV/JSON output.
- README_order_files_by_json.md — this README.

## Input formats

1) Legacy structure (example):

```json
[
  {
    "files": [
      {"name": "image1.png", "timestamp": "1441122360"},
      {"name": "document.pdf", "timestamp": "1441125000"}
    ]
  }
]
```

Here, names are resolved relative to the provided target directory.

2) Flattened structure (example):

```json
[
  {
    "filepath": "/full/path/to/image1.png",
    "raw_ts": "1441122360",
    "actual_ts": "1441122360.000000"
  },
  {
    "filepath": "relative/path/document.pdf",
    "raw_ts": "1441125000",
    "actual_ts": "1441125000.000000"
  }
]
```

Relative filepaths are resolved against the --target-directory argument.

## Timestamp parsing rules

- The script prefers an explicit numeric timestamp (epoch seconds) when available.
- If the timestamp is a string representing a float (e.g. "1441122360.000000"), it is converted to float and used for sorting.
- If numeric conversion fails, the script attempts to parse ISO date/time strings using datetime.fromisoformat and converts to epoch seconds.
- If parsing fails or the timestamp is missing, that item is kept but sorted after all valid timestamps (i.e., at the end).

## Output

- CSV (default if no output option is provided): columns are path,timestamp_raw,timestamp_epoch. The path column contains the absolute path when resolvable.
- JSON (optional): array of objects, each with keys: filepath, raw_ts, actual_ts.

## Usage examples

Write default CSV in target directory:

```bash
python3 order_files_by_json.py --json-file export.json --target-directory /path/to/files
```

Write a specific CSV:

```bash
python3 order_files_by_json.py --json-file export.json --target-directory /path/to/files --output-csv ordered.csv
```

Write JSON output instead (or in addition):

```bash
python3 order_files_by_json.py --json-file export.json --target-directory /path/to/files --output-json ordered.json
```

Write both CSV and JSON:

```bash
python3 order_files_by_json.py --json-file export.json --target-directory /path/to/files --output-csv ordered.csv --output-json ordered.json
```

## Notes and edge cases

- Non-existent files: the script will include the supplied filepath (resolved) even if the file does not exist, but it resolves paths to absolute where possible. Consumers should handle missing files.
- Duplicate file entries: preserved in the output in the same order relative to matching timestamps.
- Large JSON files: reading is done in-memory; for extremely large exports, consider pre-filtering or streaming approaches.

## Integration tip

The generated CSV or JSON can be used as the --file-list input to create_file_cards.py (the script supports JSON arrays or CSVs with a path/filepath column). Using an ordered file list ensures the card generation follows the desired chronological order.

## License and attribution

This utility is a small tool for file ordering and is provided as-is. Modify and integrate into workflows as needed.
