# File Card Generator

This tool creates visual information cards for files. It's designed to generate cards that display file metadata, previews, and type indicators, making it useful for cataloging files, creating visual indices, or preparing file information for print.

## Overview

`create_file_cards.py` processes files from a directory and creates visual information cards for each file. These cards include:

- File name and file extension
- File type indicator and color coding
- File size and metadata (creation/modification dates)
- Content preview (when applicable)
- Visual thumbnails for images, PDFs, and videos
- GPS track visualization for GPS data files
- Code/text preview for text-based files
- Hex preview for binary files

## Usage

Basic usage:
```bash
python create_file_cards.py --input-dir /path/to/files --output-dir ./output --page-size LARGE_TAROT --cmyk-mode
```

### Command Line Arguments

- `--input-dir`: Directory containing files to process (required)
- `--output-dir`: Directory to save the generated card images (default: parent directory of input-dir + `_cards_output`)
- `--cmyk-mode`: Generate cards in CMYK color mode for professional printing (default: RGB mode)
- `--page-size`: Card size (default: LARGE_TAROT)
  - Predefined sizes: A0-A5, LETTER, LEGAL, TABLOID
  - Card sizes: POKER, BRIDGE, MINI, LARGE_TAROT, SMALL_TAROT, LARGE_SQUARE, SMALL_SQUARE
  - Custom sizes: Specify as WxH in inches (e.g., "3.5X5.0")
- `--pdf-output-name`: Name for the combined PDF (default: parent directory of input-dir + `_combined_pdf.pdf`, saved in output-dir)

### Defaults

If `--output-dir` is not specified, it will default to the parent directory name of the input directory with `_cards_output` appended. For example, if your input directory is `/path/to/my_files/files`, the output directory will be `my_files_cards_output`.

If `--pdf-output-name` is not specified, it will default to the parent directory name of the input directory with `_combined_pdf.pdf` appended, and the PDF will be saved inside the output directory. For example, if your input directory is `/path/to/my_files/files`, the PDF will be saved as `my_files_cards_output/my_files_combined_pdf.pdf`.

## Examples

Create Large Tarot-sized cards (2.76×4.72 inches) in CMYK mode with PDF output (using defaults):
```bash
python create_file_cards.py --input-dir ./my_files/files --cmyk-mode
```
This will create cards in `my_files_cards_output` and the combined PDF in `my_files_cards_output/my_files_combined_pdf.pdf`.

Create custom sized cards (3.5×5.0 inches) and specify output locations:
```bash
python create_file_cards.py --input-dir ./my_files/files --output-dir ./cards_output --page-size 3.5X5.0 --pdf-output-name custom_cards.pdf
```

## Card Features

### File Type Detection

The tool automatically detects and color-codes these file types:
- Code files (`.py`, `.js`, `.html`, etc.)
- Data files (`.json`, `.csv`, `.xml`, etc.)
- Documents (`.doc`, `.pdf`, `.txt`, etc.)
- Images (`.jpg`, `.png`, `.tiff`, etc.)
- Videos (`.mp4`, `.mov`, etc.)
- GPS data (`.gpx`, `.fit`, `.tcx`)
- Archives (`.zip`, `.tar`, `.gz`, etc.)
- Binary files (`.bin`, `.hex`, `.dat`, etc.)

### Special Handling

The tool provides rich previews for special file types:
- **Images**: Thumbnail previews
- **PDFs**: Multi-page grid preview
- **Videos**: Frame grid preview
- **GPS files**: Track visualization with optional map integration
- **Archives**: File listing preview
- **Text/Code**: Content preview with syntax formatting
- **Binary**: Hex dump preview

### Slack Integration

If files come from a Slack export (with accompanying metadata files), the cards will also display:
- Channel name
- Shared by (username)
- Original sharing date
- Message ID
- User avatar (if available)

## Output Format

Each card is saved as:
- PNG file in RGB mode
- TIFF file in CMYK mode (for professional printing)

## PDF Assembly

For better quality PDF assembly with precise control over page size, DPI, and sorting, use the included Node.js script:

```bash
node combine_images_to_pdf.js -i ./cards_output -o combined_cards.pdf --cmyk-mode --page-size A4 --sort-order name
```

The Node.js script offers these options:
- `-i, --input-dir`: Input directory with card images
- `-o, --output-file`: Output PDF file path
- `-c, --cmyk-mode`: Use CMYK color mode
- `-p, --page-size`: Page size (default: A4)
- `-d, --dpi`: DPI for page size calculation (default: 300)
- `-s, --sort-order`: Sort order (name, name-desc, date, date-desc)
- `-f, --filter`: Filter files by pattern (regex)
- `-q, --quiet`: Suppress non-essential output

## Requirements

- Python 3.7+
- Pillow (PIL Fork)
- pdf2image (requires poppler)
- OpenCV (for video processing)
- gpxpy (for GPS data)
- Additional optional dependencies for special file types

To install requirements:
```bash
pip install pillow pdf2image opencv-python gpxpy requests polyline
```

For PDF assembly script:
```bash
npm install sharp pdfkit commander
```

## Batch Processing

For batch processing of multiple Slack channels or directories, use the included Node.js script:

`batch_create_file_cards.js` automates running `create_file_cards.py` for every channel directory (with a `files` subdirectory) under a root directory. This is useful for Slack exports or other bulk file sets.

See `README_batch_create_file_cards.md` for details.