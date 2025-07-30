# DOCX Grid Preview Script

## Description
This script recursively finds all .docx files in a directory, extracts the first few paragraphs of text, renders them as images, and creates a grid image as a visual summary. The grid image is saved next to the original .docx file.

## Requirements
- Python 3
- Pillow (`pip install pillow`)
- python-docx (`pip install python-docx`)

## Usage
```bash
python docx_grid_preview.py --root-dir /path/to/search --paragraphs 4
```
- `--root-dir`: Directory to search for .docx files
- `--paragraphs`: Number of paragraphs to show in the grid (default: 4)

## Output
For each .docx file, a grid image named `<docx_name>_preview.png` will be created in the same directory.

## Notes
- The script uses the default system font if Arial is not available.
- Only non-empty paragraphs are shown.
