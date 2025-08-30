import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime

def extract_prompt(content):
    # Extract everything between the first pair of **'s
    match = re.search(r"\*\*(.*?)\*\*", content)
    return match.group(1).strip() if match else ""

def process_json_file(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    created_raw = data.get("created_at")
    created_fmt = None
    if created_raw:
        try:
            # Always parse as ISO format with timezone
            created_dt = datetime.fromisoformat(created_raw)
            created_fmt = created_dt.strftime("%B %d, %Y %H:%M:%S")
        except Exception:
            created_fmt = created_raw  # fallback to raw if parsing fails
    return {
        "filepath": data.get("image_path"),
        "metadata": {
            "_prompt": extract_prompt(data.get("content", "")),
            "_created": created_fmt,
            "_title": created_fmt,
            "_filename": data.get("downloaded_filename"),
            "qr_data": data.get("full_path")
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Combine JSON files into a single JSON array with transformed structure.")
    parser.add_argument("--json-folder-path", required=True, help="Path to folder containing JSON files.")
    parser.add_argument("--output-folder-path", default=".", help="Path to folder to save the output JSON file.")
    parser.add_argument("--output-json-name", required=True, help="Name of the output JSON file.")
    parser.add_argument("--max-depth", type=int, default=1, help="Maximum directory depth to process recursively (default: 1, only top-level).")
    args = parser.parse_args()

    json_folder = Path(args.json_folder_path)
    output_folder = Path(args.output_folder_path)
    output_folder.mkdir(parents=True, exist_ok=True)
    output_json_path = output_folder / args.output_json_name

    all_entries = []
    def process_dir(folder, current_depth, max_depth):
        if current_depth > max_depth:
            return
        for item in folder.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                process_dir(item, current_depth + 1, max_depth)
            elif item.is_file() and item.suffix == ".json":
                try:
                    entry = process_json_file(item)
                    all_entries.append(entry)
                except Exception as e:
                    print(f"Error processing {item}: {e}")

    process_dir(json_folder, 1, args.max_depth)

    with open(output_json_path, "w", encoding="utf-8") as out_f:
        json.dump(all_entries, out_f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()