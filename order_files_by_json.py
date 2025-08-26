import os
import json
from pathlib import Path
import argparse


def generate_ordered_csv_from_json(json_path, directory, output_csv=None, dedupe=False):
    """
    Parse the JSON file and produce a CSV listing files in timestamp order.

    The CSV will have columns: path,timestamp_raw,timestamp_epoch
    Files with missing or unparsable timestamps are placed at the end of the list.
    """
    # Load the JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ensure the directory exists
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: {directory} is not a valid directory.")
        return

    items = []  # list of tuples (resolved_path_str, raw_timestamp, parsed_epoch_or_None)

    # Iterate through the JSON elements and collect file entries
    for element in data:
        files = element.get("files") if isinstance(element, dict) else None
        if not files:
            continue
        for file_info in files:
            file_name = file_info.get("name") if isinstance(file_info, dict) else None
            timestamp_raw = file_info.get("timestamp") if isinstance(file_info, dict) else None

            if not file_name:
                continue

            file_path = dir_path / file_name
            # Represent path as absolute if file exists, otherwise keep the joined path
            try:
                resolved_str = str(file_path.resolve()) if file_path.exists() else str(file_path)
            except Exception:
                resolved_str = str(file_path)

            # Normalize timestamp: try numeric epoch first, then ISO datetime
            parsed_epoch = None
            if timestamp_raw is not None and str(timestamp_raw).strip() != "":
                # Try numeric
                try:
                    parsed_epoch = float(timestamp_raw)
                except Exception:
                    # Try ISO format
                    try:
                        from datetime import datetime
                        # datetime.fromisoformat supports many ISO variants
                        parsed_epoch = datetime.fromisoformat(str(timestamp_raw)).timestamp()
                    except Exception:
                        parsed_epoch = None

            items.append((resolved_str, str(timestamp_raw) if timestamp_raw is not None else "", parsed_epoch))

    # Sort items by parsed_epoch, placing None (missing/unparsable) at the end
    items_sorted = sorted(items, key=lambda x: (x[2] is None, x[2] if x[2] is not None else float('inf')))

    # Optional deduplication: keep earliest (first) occurrence per resolved path
    if dedupe:
        seen = set()
        deduped = []
        for p, raw, epoch in items_sorted:
            key = (p, raw)
            if key in seen:
                continue
            seen.add(key)
            deduped.append((p, raw, epoch))
        removed = len(items_sorted) - len(deduped)
        items_sorted = deduped
        print(f"Deduplication enabled: removed {removed} duplicate entries; {len(items_sorted)} remain.")

    # Determine output CSV path
    if not output_csv:
        output_csv = str(dir_path / "ordered_files.csv")

    import csv
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["path", "timestamp_raw", "timestamp_epoch"])
        for path_str, raw_ts, epoch in items_sorted:
            epoch_val = "" if epoch is None else ("{:.6f}".format(epoch) if isinstance(epoch, float) else str(epoch))
            writer.writerow([path_str, raw_ts, epoch_val])

    print(f"Wrote {len(items_sorted)} entries to {output_csv}")


def generate_ordered_output_from_json(json_path, directory, output_csv=None, output_json=None, dedupe=False):
    """
    Parse the JSON file and produce an ordered CSV and/or JSON listing files in timestamp order.

    If output_json is provided, write a JSON array of objects with keys:
        filepath, raw_ts, actual_ts
    If output_csv is provided (or neither provided), write a CSV with columns:
        path,timestamp_raw,timestamp_epoch

    Files with missing or unparsable timestamps are placed at the end of the list.
    """
    # Load the JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ensure the directory exists
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: {directory} is not a valid directory.")
        return

    items = []  # list of tuples (resolved_path_str, raw_timestamp, parsed_epoch_or_None)

    # Iterate through the JSON elements and collect file entries
    for element in data:
        # Support flat objects as well as the previous 'files' array structure
        if isinstance(element, dict) and ('filepath' in element or 'path' in element or 'file' in element):
            # New flattened format
            fp = element.get('filepath') or element.get('path') or element.get('file')
            raw_ts = element.get('raw_ts') or element.get('timestamp_raw') or element.get('timestamp')
            actual_ts = element.get('actual_ts') or element.get('timestamp_epoch') or element.get('timestamp_epoch')

            # Normalize filepath value: it might be a dict or other structure
            fp_val = fp
            if isinstance(fp_val, dict):
                # Try common nested keys
                for k in ('name', 'filename', 'path', 'file'):
                    try:
                        v = fp_val.get(k)
                    except Exception:
                        v = None
                    if isinstance(v, (str, bytes, os.PathLike)):
                        fp_val = v
                        break
                else:
                    # Fallback: try to find any string-like value inside the dict
                    found = False
                    for v in fp_val.values():
                        if isinstance(v, (str, bytes, os.PathLike)):
                            fp_val = v
                            found = True
                            break
                    if not found:
                        # Last resort: stringify the dict
                        fp_val = str(fp_val)

            # Ensure we have a string/Path-like for os.path.isabs
            if not isinstance(fp_val, (str, bytes, os.PathLike)):
                fp_str = str(fp_val)
            else:
                fp_str = fp_val

            if not fp_str:
                continue

            # Normalize timestamp fields if they are dicts
            if isinstance(raw_ts, dict):
                raw_ts = raw_ts.get('raw_ts') or raw_ts.get('timestamp') or raw_ts.get('value') or str(raw_ts)
            if isinstance(actual_ts, dict):
                actual_ts = actual_ts.get('actual_ts') or actual_ts.get('timestamp_epoch') or actual_ts.get('value') or str(actual_ts)

            # Build file_path correctly depending on whether fp is absolute
            try:
                if os.path.isabs(fp_str):
                    file_path = Path(fp_str)
                else:
                    file_path = dir_path / fp_str
            except Exception:
                file_path = dir_path / str(fp_str)

            # Represent path as absolute if file exists, otherwise keep the joined path
            try:
                resolved_str = str(file_path.resolve()) if file_path.exists() else str(file_path)
            except Exception:
                resolved_str = str(file_path)

            parsed_epoch = None
            if actual_ts is not None and str(actual_ts).strip() != "":
                try:
                    parsed_epoch = float(actual_ts)
                except Exception:
                    try:
                        from datetime import datetime
                        parsed_epoch = datetime.fromisoformat(str(actual_ts)).timestamp()
                    except Exception:
                        parsed_epoch = None

            items.append((resolved_str, str(raw_ts) if raw_ts is not None else "", parsed_epoch))

        else:
            # Legacy structure: element may contain a 'files' list
            files = element.get("files") if isinstance(element, dict) else None
            if not files:
                continue
            for file_info in files:
                file_name = file_info.get("name") if isinstance(file_info, dict) else None
                timestamp_raw = file_info.get("timestamp") if isinstance(file_info, dict) else None

                if not file_name:
                    continue

                file_path = dir_path / file_name
                # Represent path as absolute if file exists, otherwise keep the joined path
                try:
                    resolved_str = str(file_path.resolve()) if file_path.exists() else str(file_path)
                except Exception:
                    resolved_str = str(file_path)

                # Normalize timestamp: try numeric epoch first, then ISO datetime
                parsed_epoch = None
                if timestamp_raw is not None and str(timestamp_raw).strip() != "":
                    # Try numeric
                    try:
                        parsed_epoch = float(timestamp_raw)
                    except Exception:
                        # Try ISO format
                        try:
                            from datetime import datetime
                            # datetime.fromisoformat supports many ISO variants
                            parsed_epoch = datetime.fromisoformat(str(timestamp_raw)).timestamp()
                        except Exception:
                            parsed_epoch = None

                items.append((resolved_str, str(timestamp_raw) if timestamp_raw is not None else "", parsed_epoch))

    # Sort items by parsed_epoch, placing None (missing/unparsable) at the end
    items_sorted = sorted(items, key=lambda x: (x[2] is None, x[2] if x[2] is not None else float('inf')))

    # Optional deduplication: keep earliest (first) occurrence per resolved path
    if dedupe:
        seen = set()
        deduped = []
        for p, raw, epoch in items_sorted:
            key = (p, raw)
            if key in seen:
                continue
            seen.add(key)
            deduped.append((p, raw, epoch))
        removed = len(items_sorted) - len(deduped)
        items_sorted = deduped
        print(f"Deduplication enabled: removed {removed} duplicate entries; {len(items_sorted)} remain.")

    # Default CSV path if none and JSON not requested
    if not output_csv and not output_json:
        output_csv = str(dir_path / "ordered_files.csv")

    # Write CSV if requested
    if output_csv:
        import csv as _csv
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = _csv.writer(csvfile)
            writer.writerow(["path", "timestamp_raw", "timestamp_epoch"])
            for path_str, raw_ts, epoch in items_sorted:
                epoch_val = "" if epoch is None else ("{:.6f}".format(epoch) if isinstance(epoch, float) else str(epoch))
                writer.writerow([path_str, raw_ts, epoch_val])
        print(f"Wrote {len(items_sorted)} entries to {output_csv}")

    # Write JSON if requested
    if output_json:
        out_list = []
        for path_str, raw_ts, epoch in items_sorted:
            actual_ts = "" if epoch is None else ("{:.6f}".format(epoch) if isinstance(epoch, float) else str(epoch))
            out_list.append({
                "filepath": path_str,
                "raw_ts": raw_ts,
                "actual_ts": actual_ts
            })
        with open(output_json, 'w', encoding='utf-8') as jf:
            json.dump(out_list, jf, ensure_ascii=False, indent=2)
        print(f"Wrote {len(out_list)} entries to {output_json}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Create a CSV or JSON of files ordered by timestamp from a JSON file.")
    parser.add_argument("--json-file", type=str, required=True, help="Path to the JSON file.")
    parser.add_argument("--target-directory", type=str, required=True, help="Path to the target directory.")
    parser.add_argument("--output-csv", type=str, required=False, help="Path to write the ordered CSV (default: <target-directory>/ordered_files.csv)")
    parser.add_argument("--output-json", type=str, required=False, help="Path to write the ordered JSON (optional)")
    parser.add_argument("--dedupe", action='store_true', help="Remove duplicate file paths, keeping the earliest timestamp")
    args = parser.parse_args()

    generate_ordered_output_from_json(args.json_file, args.target_directory, args.output_csv, args.output_json, dedupe=getattr(args, 'dedupe', False))