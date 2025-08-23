# order_files_by_json.py

## Purpose
The `order_files_by_json.py` script is designed to rename files in a specified directory based on metadata provided in a JSON file. This is particularly useful for organizing files systematically, such as appending timestamps or other metadata to filenames for better sorting and identification.

## Functionality
The script reads a JSON file containing metadata about files and renames the files in the target directory according to the specified rules. It ensures that only the root of the filename is modified, while preserving the original file extension.

### Key Features
- Reads metadata from a JSON file.
- Renames files in a directory based on the metadata.
- Modifies only the root of the filename, keeping the original extension intact.
- Provides error handling for missing files or invalid directories.

## Usage

### Command-Line Arguments
The script accepts the following arguments:

- `--json-file`: Path to the JSON file containing metadata.
- `--target-directory`: Path to the directory containing the files to rename.

### Example Command
```bash
python order_files_by_json.py --json-file /path/to/messages.json --target-directory /path/to/directory
```

### JSON File Format
The JSON file should be structured as follows:
```json
[
    {
        "files": [
            {
                "name": "example_file.txt",
                "timestamp": "20250823"
            },
            {
                "name": "another_file.doc",
                "timestamp": "20250822"
            }
        ]
    }
]
```

### Output
For each file, the script renames it to include the timestamp in the root of the filename. For example:
- `example_file.txt` becomes `ts_20250823_example_file_ts.txt`
- `another_file.doc` becomes `ts_20250822_another_file_ts.doc`

## Error Handling
- If the specified directory does not exist, the script will print an error message and exit.
- If a file listed in the JSON file is not found in the directory, the script will print a warning message.

## Requirements
- Python 3.6 or higher
- `argparse` and `json` modules (both included in the Python standard library)

## Notes
- Ensure that the JSON file and the target directory paths are correct.
- The script does not create backups of the original filenames, so use it cautiously.

## Author
This script was developed as part of the Files2Book project.
