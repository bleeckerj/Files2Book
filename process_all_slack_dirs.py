#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import sys

def main():
    # Base directory containing all the Slack export directories
    base_dir = Path("/Users/julian/Code/SlackExporterForOmata")
    
    # Script to run
    script_path = Path("/Users/julian/Code/pdf-to-grid-of-images/directory_to_images.py")
    
    # Check if script exists
    if not script_path.exists():
        print(f"Error: Script not found at {script_path}")
        sys.exit(1)
    
    # Check if base directory exists
    if not base_dir.exists() or not base_dir.is_dir():
        print(f"Error: Base directory not found at {base_dir}")
        sys.exit(1)
    
    # Count to keep track of processed directories
    processed_count = 0
    
    # Common command arguments
    common_args = [
        "--layout", "grid",
        "--grid-rows", "2",
        "--grid-cols", "1",
        "--page-size", "A5",
        "--page-orientation", "portrait",
        "--image-fit-mode", "scale",
        "--gap", "0.125",
        "--hairline-width", "0.008",
        "--hairline-color", "gray",
        "--padding", "0.125",
        "--page-margin", "0.25",
        "--output-pdf",
        "--exclude-video-stills",
        "--flipbook-mode",
        "--video-fps", "1"
    ]
    
    # Iterate through all directories in the base directory
    for item in base_dir.iterdir():
        if item.is_dir():
            files_dir = item / "files"
            
            # Check if this directory has a "files" subdirectory
            if files_dir.exists() and files_dir.is_dir():
                channel_name = item.name
                print(f"\n{'='*80}")
                print(f"Processing channel: {channel_name}")
                print(f"{'='*80}")
                
                # Construct the command
                cmd = [
                    "python3",
                    str(script_path),
                    str(files_dir),
                ] + common_args
                
                # Print the command being run
                print("Running command:")
                print(" ".join(cmd))
                print()
                
                try:
                    # Run the command
                    result = subprocess.run(cmd, check=True, text=True)
                    print(f"Successfully processed {channel_name}")
                    processed_count += 1
                except subprocess.CalledProcessError as e:
                    print(f"Error processing {channel_name}: {e}")
                    print(f"Return code: {e.returncode}")
                    if e.output:
                        print(f"Output: {e.output}")
                    if e.stderr:
                        print(f"Stderr: {e.stderr}")
    
    print(f"\nProcessing complete. {processed_count} directories were processed.")

if __name__ == "__main__":
    main()
