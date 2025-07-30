# PPTX Grid Preview Script

## Description
This script recursively finds all .pptx files in a directory, converts each to PDF using LibreOffice, generates preview images of the first few slides, and creates a grid image as a visual summary. The grid image is saved next to the original .pptx file.

## Requirements
- Python 3
- Pillow (`pip install pillow`)
- pdf2image (`pip install pdf2image`)
- LibreOffice (soffice) installed and available in your PATH

## LibreOffice Installation
- **macOS**: Download from https://www.libreoffice.org/download/download/ and install. The `soffice` binary is usually in `/Applications/LibreOffice.app/Contents/MacOS/soffice`.
- **Linux**: Install via your package manager, e.g. `sudo apt install libreoffice`.
- **Windows**: Download and install from https://www.libreoffice.org/download/download/. Add the LibreOffice program folder to your PATH.

## Usage
```bash
python pptx_grid_preview.py --root-dir /path/to/search --slides 4
```
- `--root-dir`: Directory to search for .pptx files
- `--slides`: Number of slides to show in the grid (default: 4)

## Output
For each .pptx file, a grid image named `<pptx_name>_preview.png` will be created in the same directory.

## Notes
- The script deletes the temporary PDF after creating the preview.
- If you have issues with `soffice` not being found, specify the full path in the script or add it to your PATH.
