# File Card Generator

This tool creates visual preview / information cards for files. It's designed to generate cards that display file metadata, previews, and type indicators, making it useful for cataloging files, creating visual indices, or preparing file information for print.

## Overview

`create_file_cards.py` is a Python script designed to generate visual information cards for files in a specified directory. These cards provide a detailed overview of each file, including metadata, previews, and type indicators. The script is particularly useful for cataloging files, creating visual indices, or preparing file information for print or digital archives.

### Key Features:

- **Metadata Display**: Includes file name, extension, size, creation/modification dates, and more.
- **Content Previews**: Generates visual thumbnails for images, PDFs, and videos, as well as previews for text/code, GPS tracks, and binary files.
- **Customizable Output**: Supports various card sizes, color modes (RGB/CMYK), and background colors.
- **PDF Assembly**: Combines generated cards into a single PDF for easy sharing or printing.
- **Specialized Handling**: Provides enhanced previews for specific file types, such as multi-page PDFs, video frame grids, and GPS visualizations.
- **Slack Integration**: Displays additional metadata for files originating from Slack exports, including channel name, user details, and timestamps.

## Usage

### Command Line Arguments

All command line arguments supported by `create_file_cards.py`:

- `--input-dir`: Directory containing files to create cards for.
- `--output-dir`: Directory to save card images.
- `--file-list`: Path to a CSV file containing comma-separated file paths (items may be quoted). If provided, `--input-dir` is not required and the ordered file list will be processed.
- `--cmyk-mode`: Generate cards in CMYK mode.
- `--cmyk`: Alias for `--cmyk-mode`.
- `--page-size`: Page size (default: LARGE_TAROT). Accepts predefined sizes (A0-A5, LETTER, LEGAL, TABLOID, DIGEST, POKER, BRIDGE, MINI, LARGE_TAROT, SMALL_TAROT, LARGE_SQUARE, SMALL_SQUARE) or custom WxH in inches (e.g., "3.5x5.0").
- `--pdf-output-name`: Path to save the combined PDF.
- `--max-depth`: Maximum folder recursion depth (default: 0, no recursion).
- `--exclude-file-path`: Exclude the vertical file path from the card (default: shown).
- `--delete-cards-after-pdf`: Delete individual card files after PDF is created.
- `--border-color`: Border color for the cards in RGB format (default: "250,250,250").
- `--border-inch-width`: Border width in inches (default: 0.125).
- `--include-video-frames`: Also output individual video frames as cards (default: overview only).
- `--max-video-frames`: Minimum number of video frames to include (default: 30).
- `--exclude-exts`: Comma-separated list of file extensions to exclude (e.g. "dng,oci").
- `--metadata-text`: Custom metadata text to include on the card.
- `--cards-per-chunk`: If >0, split card images into chunked folders of this many cards and produce one PDF per chunk.
- `--slack-data-root`: Path to Slack export root (directory containing messages.json and files/). If provided, the script will treat input as Slack data and resolve relative filepaths accordingly.

## Examples

Create Large Tarot-sized cards (2.76×4.72 inches) in CMYK mode and compact mode with PDF output (using defaults, no recursion):

```bash
python create_file_cards.py --input-dir ./my_files/files --cmyk-mode --compact
```

Example with custom page size, Slack integration, file list, border color, and chunked output:

```bash
python3 ./create_file_cards.py \
  --page-size "5.75x8.75" \
  --slack-data-root "/Volumes/OMATA/SlackExporterForOmata/omata-brand/" \
  --file-list "/Volumes/OMATA/SlackExporterForOmata/omata-brand/downloaded_files.json" \
  --output-dir "/Volumes/OMATA/SlackExporterForOmata/slack-channels-file-cards/omata-brand_file_cards_output" \
  --cmyk-mode \
  --max-depth 3 \
  --border-color "161 216 26" \
  --border-inch-width 0.2 \
  --delete-cards-after-pdf --cards-per-chunk 500 \
  --input-dir "/Volumes/OMATA/SlackExporterForOmata/"
```

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

## Supported Page Sizes

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

Or specify custom size as WxH in inches (e.g. "8.5x11").

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