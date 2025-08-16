# File Card Generator

This tool creates visual information cards for files. It's designed to generate cards that display file metadata, previews, and type indicators, making it useful for cataloging files, creating visual indices, or preparing file information for print.

## Overview

`generate_flipbook_pages.py` processes files from a directory and creates visual information cards for each file. These cards include:

- File name and file extension
- File type indicator and color coding
- File size and metadata (creation/modification dates)
- Content preview (when applicable)
- Visual thumbnails for images, PDFs, and videos
- GPS track visualization for GPS data files
- Code/text preview for text-based files
- Hex preview for binary files

## Usage
## `create_file_cards.py`

This script generates visual information cards for files in a specified directory. Each card displays metadata (file name, extension, size, dates), a preview (image, PDF, video frame, text/code snippet, or hex dump), and type indicators. It is suitable for cataloging files, creating visual indices, or preparing file information for print.

### Usage


Basic usage (no recursion, only files in the specified folder):
```bash
python create_file_cards.py --input-dir /path/to/files --output-dir ./output --page-size LARGE_TAROT --cmyk-mode
```


#### Command Line Arguments


- `--input-dir`: Directory containing files to process (required)
- `--output-dir`: Directory to save the generated card images (default: parent directory of input-dir + `_cards_output`)
- `--cmyk-mode`: Generate cards in CMYK color mode for professional printing (default: RGB mode)
- `--cmyk`: Alias for `--cmyk-mode`
- `--page-size`: Card size (default: LARGE_TAROT)
  - Predefined sizes: A0-A5, LETTER, LEGAL, TABLOID, DIGEST
  - Card sizes: POKER, BRIDGE, MINI, LARGE_TAROT, SMALL_TAROT, LARGE_SQUARE, SMALL_SQUARE
  - Custom sizes: Specify as WxH in inches (e.g., "3.5X5.0")

**Supported Page Sizes and Their Dimensions (in inches):**

| Name         | Width (in) | Height (in) |
|--------------|------------|-------------|
| A0           | 33.11      | 46.81       |
| A1           | 23.39      | 33.11       |
| A2           | 16.54      | 23.39       |
| A3           | 11.69      | 16.54       |
| A4           | 8.27       | 11.69       |
| A5           | 5.83       | 8.27        |
| LETTER       | 8.5        | 11          |
| LEGAL        | 8.5        | 14          |
| TABLOID      | 11         | 17          |
| DIGEST       | 5.5        | 8.5         |
| POCKETBOOK   | 4.25       | 6.87        |
| POKER        | 2.48       | 3.46        |
| BRIDGE       | 2.24       | 3.46        |
| MINI         | 1.73       | 2.68        |
| LARGE_TAROT  | 2.76       | 4.72        |
| SMALL_TAROT  | 2.76       | 4.25        |
| LARGE_SQUARE | 2.76       | 2.76        |
| SMALL_SQUARE | 2.48       | 2.48        |
-------------------------------------------
- `--pdf-output-name`: Name for the combined PDF (default: parent directory of input-dir + `_combined_pdf.pdf`, saved in output-dir)
- `--exclude-file-path`: Exclude the vertical file path from the card (default: shown)
- `--card-background-color`: Set the background color for the card (default: 'white'). Accepts any valid Pillow color string or RGB tuple, eg `--card-background-color "(251,238,104)"`
- `--include-video-frames`: Also output individual video frames as cards. By default, videos produce a single “overview” card with a grid of frames; with this flag, additional per-frame cards are generated and included in the combined PDF.
- `--delete-cards-after-pdf`: After assembling the combined PDF, delete the generated card images. This removes both overview cards (`*_card.*`) and per-frame cards (`*_card_*.*`).

#### Output

- Cards are saved as PNG (RGB) or TIFF (CMYK) files in the output directory.
- Optionally, a combined PDF of all cards can be generated.

Basic usage:
```bash
python generate_flipbook_pages.py --input-dir /path/to/files --output-dir ./output --page-size LARGE_TAROT --cmyk-mode
```

### Command Line Arguments

- `--input-dir`: Directory containing files to process (required)
- `--output-dir`: Directory to save the generated card images (default: parent directory of input-dir + `_cards_output`)
- `--cmyk-mode`: Generate cards in CMYK color mode for professional printing (default: RGB mode)
- `--cmyk`: Alias for `--cmyk-mode`
- `--page-size`: Card size (default: LARGE_TAROT)
  - Predefined sizes: A0-A5, LETTER, LEGAL, TABLOID
  - Card sizes: POKER, BRIDGE, MINI, LARGE_TAROT, SMALL_TAROT, LARGE_SQUARE, SMALL_SQUARE
  - Custom sizes: Specify as WxH in inches (e.g., "3.5X5.0")
- `--pdf-output-name`: Name for the combined PDF (default: parent directory of input-dir + `_combined_pdf.pdf`, saved in output-dir)
- `--compact`: Enable compact mode for reduced text size, minimal spacing, and maximized preview area
- `--include-video-frames`: Generate per-frame video cards alongside the overview card
- `--delete-cards-after-pdf`: Delete generated card images after the PDF is created

### Defaults


If `--max-depth` is not specified, only files in the specified folder are processed (no recursion). To include files in subfolders, set `--max-depth` to a higher value.

If `--output-dir` is not specified, it will default to the parent directory name of the input directory with `_cards_output` appended. For example, if your input directory is `/path/to/my_files/files`, the output directory will be `my_files_cards_output`.

If `--pdf-output-name` is not specified, it will default to the parent directory name of the input directory with `_combined_pdf.pdf` appended, and the PDF will be saved inside the output directory. For example, if your input directory is `/path/to/my_files/files`, the PDF will be saved as `my_files_cards_output/my_files_combined_pdf.pdf`.

## Examples



Create Large Tarot-sized cards (2.76×4.72 inches) in CMYK mode and compact mode with PDF output (using defaults, no recursion):
```bash
python create_file_cards.py --input-dir ./my_files/files --cmyk-mode --compact
```

`--input-dir`: Directory containing files to process (required)
`--output-dir`: Directory to save the generated card images (default: parent directory of input-dir + `_cards_output`)
`--cmyk-mode`: Generate cards in CMYK color mode for professional printing (default: RGB mode)
`--page-size`: Card size (default: LARGE_TAROT)

**Supported page sizes:**
- A5, A4, A3, A2, A1, A0
- LETTER, LEGAL, TABLOID
- POKER, BRIDGE, MINI, LARGE_TAROT, SMALL_TAROT, LARGE_SQUARE, SMALL_SQUARE
- Or custom WxH in inches (e.g. 8.5x11)

`--pdf-output-name`: Name for the combined PDF (default: parent directory of input-dir + `_combined_pdf.pdf`, saved in output-dir)
`--max-depth`: Maximum folder recursion depth (default: 0, no recursion; set higher for deeper traversal)
Example including individual video frame cards and cleaning up images after PDF assembly:
```bash
python create_file_cards.py \
  --input-dir ./videos_and_images \
  --output-dir ./cards_out \
  --page-size LARGE_TAROT \
  --cmyk \
  --include-video-frames \
  --pdf-output-name my_collection \
  --delete-cards-after-pdf
```

### Compact Mode

When `--compact` is specified, cards are generated with:
- Smaller font sizes
- Minimal vertical spacing
- No file type icon text below the header
- Maximized preview/image area
This is ideal for print layouts or when you want the preview to take priority over metadata.

### File Type Detection

The tool automatically detects and color-codes these file types:
- Code files (`.py`, `.js`, `.html`, etc.)
- Data files (`.json`, `.csv`, `.xml`, etc.)
- Documents (`.doc`, `.pdf`, `.txt`, etc.)
- Images (`.jpg`, `.png`,`.tif`, `.tiff`, etc.)
- Videos (`.mp4`, `.mov`, etc.)
- GPS data (`.gpx`, `.fit`, `.tcx`)
- Archives (`.zip`, `.tar`, `.gz`, `.rar`, etc.)
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

`batch_create_file_cards.js` automates running `generate_flipbook_pages.py` for every channel directory (with a `files` subdirectory) under a root directory. This is useful for Slack exports or other bulk file sets.

See `README_batch_create_file_cards.md` for details.