import os
import json
from pathlib import Path
import argparse

def rename_files_from_json(json_path, directory):
    """
    Rename files in a directory based on a JSON file.

    Args:
        json_path (str): Path to the JSON file.
        directory (str): Path to the directory containing the files to rename.
    """
    # Load the JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ensure the directory exists
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: {directory} is not a valid directory.")
        return

    # Iterate through the JSON elements
    for element in data:
        if "files" in element:
            for file_info in element["files"]:
                file_name = file_info.get("name")
                timestamp = file_info.get("timestamp")

                # Ensure both name and timestamp exist
                if file_name and timestamp:
                    # Find the file in the directory
                    file_path = dir_path / file_name
                    if file_path.exists() and file_path.is_file():
                        # Construct the new filename (change root only, keep extension)
                        new_name = f"ts_{timestamp}_ts__{file_name}"
                        new_path = dir_path / new_name

                        # Rename the file
                        file_path.rename(new_path)
                        print(f"Renamed: {file_path} -> {new_path}")
                    else:
                        print(f"File not found: {file_name}")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Rename files in a directory based on a JSON file.")
    parser.add_argument("--json-file", type=str, required=True, help="Path to the JSON file.")
    parser.add_argument("--target-directory", type=str, required=True, help="Path to the target directory.")
    args = parser.parse_args()

    # Call the function with parsed arguments
    rename_files_from_json(args.json_file, args.target_directory)