# README_file_card_generator

## Overview

`file_card_generator.py` is a robust Python script for generating visual info cards for a wide variety of file types. It creates beautiful, informative images summarizing file metadata, previews, and even GPS tracks with dynamic Mapbox map thumbnails. Whether you're working with images, PDFs, videos, archives, or GPS files, this tool helps you visualize and organize your files with style.

## Features

- **Supports Many File Types:**
  - Images (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tif`, `.tiff`, `.heic`)
  - Videos (`.mp4`, `.mov`, `.avi`, `.mkv`)
  - Documents (`.pdf`, `.docx`, `.key`, `.txt`, `.md`, etc.)
    - **Keynote (.key):** Lists contents and shows embedded images in a grid
    - **DOCX (.docx):** Extracts and previews text
    - **PPTX (.pptx):** Not yet supported for preview (only metadata)
  - Archives (`.zip`, `.gz`, `.bz2`, etc.)
  - GPS Tracks (`.gpx`, `.fit`, `.tcx`) with Mapbox map thumbnails
  - Binary, code, spreadsheet, and more
- **File Metadata:**
  - Name, type, size, hash, timestamps (created, modified, original)
- **Content Preview:**
  - Text preview for text/code/data/log files
  - Hex preview for binary files
  - Archive contents preview
  - PDF grid thumbnails
  - Video frame grids
  - Keynote: grid of embedded images
  - DOCX: extracted text
  - PPTX: metadata only
- **Mapbox Integration:**
  - Automatically generates map thumbnails for GPS tracks
  - Polyline overlays for routes
  - Dynamic zoom calculation for best fit
- **Customizable Appearance:**
  - Uses custom fonts (3270 Nerd Font recommended)
  - CMYK mode for print
- **Error Handling:**
  - Graceful fallback for missing dependencies or unsupported files

## Requirements

- Python 3.7+
- [Pillow](https://pypi.org/project/Pillow/) (PIL)
- [requests](https://pypi.org/project/requests/)
- [gpxpy](https://pypi.org/project/gpxpy/)
- [fitparse](https://pypi.org/project/fitparse/) (optional, for `.fit` files)
- [polyline](https://pypi.org/project/polyline/)
- [pdf2image](https://pypi.org/project/pdf2image/)
- [opencv-python](https://pypi.org/project/opencv-python/) (for video previews)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [pyheif](https://pypi.org/project/pyheif/) (optional, for `.heic` images)
- Node.js 14+ (for PDF assembly with `combine_images_to_pdf.js`)
- sharp (for Node.js, image processing)
- pdfkit (for Node.js, PDF generation)
- commander (for Node.js, command-line interface)

Install requirements:
```bash
pip install Pillow requests gpxpy fitparse polyline pdf2image opencv-python python-dotenv pyheif
npm install
```

## Mapbox Access Token

To use Mapbox map thumbnails, you **must** set your Mapbox access token as an environment variable:

```bash
export MAPBOX_TOKEN=your_mapbox_access_token_here
```
Or create a `.env` file in the same directory:
```
MAPBOX_TOKEN=your_mapbox_access_token_here
```
You can get a token from https://account.mapbox.com/

## Usage


### As a Script

You can run the script directly to generate a file info card:
```bash
python file_card_generator.py /path/to/your/file.ext [--compact]
```

### Command Line Arguments

`file_path` (required): Path to the file you want to generate a card for.
`--width WIDTH`: Output card width (default: 800)
`--height HEIGHT`: Output card height (default: 1000)
`--cmyk`: Enable CMYK mode for print
`--output OUTPUT_PATH`: Path to save the generated image (default: `file_card.png`)
`--compact`: Enable compact mode for reduced text size, tighter spacing, and maximized preview area
`--exclude-file-path`: Exclude the vertical file path from the card (by default, the file path is shown vertically along the preview area)
`--card-background-color`: Set the background color for the card (default: 'white'). Accepts any valid Pillow color string or RGB tuple, eg `--card-background-color "(251,238,104)"`
`--border-inch-width`: Specify the border width in inches, eg `--border-inch-width 0.124`

**Supported page sizes:**
- A5, A4, A3, A2, A1, A0
- LETTER, LEGAL, TABLOID
- POKER, BRIDGE, MINI, LARGE_TAROT, SMALL_TAROT, LARGE_SQUARE, SMALL_SQUARE
- Or custom WxH in inches (e.g. 8.5x11)

Example:
```bash
python file_card_generator.py myfile.gpx --width 1200 --height 1500 --output my_card.png --compact
```

To hide the vertical file path on the card:
```bash
python file_card_generator.py myfile.jpg --exclude-file-path
```

### As a Module
You can import and use `create_file_info_card` in your own Python code:
```python
from file_card_generator import create_file_info_card
img = create_file_info_card('myfile.pdf', width=1200, height=1500)
img.save('my_card.png')
```

## New Features and Enhancements

### Compact Mode
- Use the `--compact` flag to generate cards with reduced font size, minimal spacing, and a maximized preview area.
- Useful for print layouts or when you want the image/preview to take priority over metadata.


### HEIC Image Support
- Added support for `.heic` and `.heif` image formats using the `pillow-heif` library.
- Automatically processes HEIC images and generates thumbnails for preview.

### Slack Metadata Integration
- Extracts metadata from Slack `messages.json` and `users.json` files.
- Displays the following Slack-specific metadata:
  - **Slack Channel**: The channel where the file was shared.
  - **Shared By**: The real name of the user who shared the file.
  - **Shared Date**: The timestamp when the file was shared.

### Avatar Handling
- Resolves and displays user avatars from Slack's `avatars` directory.
- Avatars are resized, rounded, and placed next to the "Shared By" metadata for a polished look.
- Graceful fallback for missing or invalid avatar images.

### Improved Error Logging
- Added detailed logging for debugging issues with Slack metadata and avatar processing.
- Logs include paths checked for avatars and errors encountered during processing.

### Enhanced Metadata Display
- Metadata font size and spacing have been adjusted for better readability.
- Metadata now includes both created and modified timestamps if the original timestamp is unavailable.

### Other Improvements
- Optimized scaling for image previews to fit within the preview box while maintaining aspect ratio.
- Improved handling of large files and unsupported formats with clear error messages.

---

## Notes & Tips
- For best results, use the recommended font. If not available, the script will fall back to the default font.
- Large files (>50MB) may skip hash calculation for performance.
- Mapbox requests may fail if the token is missing, invalid, or the polyline is too long. The script will print helpful error messages.
- Fractional zoom levels are supported for Mapbox maps for optimal fit.
- If you see a 401 error from Mapbox, check your token and make sure the polyline is URL-encoded (the script does this for you).

## Troubleshooting
- **Mapbox 401 Error:**
  - Check your token, and make sure it's set in your environment or `.env` file.
  - If your polyline contains weird characters, don't worry—the script URL-encodes it for you.
- **Missing Dependencies:**
  - Install all required packages with `pip install ...` as above.
- **Font Issues:**
  - Download and install [3270 Nerd Font](https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/3270) for best appearance.

## Contributing
Pull requests, bug reports, and feature suggestions are welcome! Just don't ask the AI to write your README for you, or you might get a joke instead of documentation.

## License
MIT License

## A Joke (or a Warning)
> Working with my co-pilot AI was like herding cats, only the cats are made of code, and they keep suggesting you pip install things you already have. If you ever feel lost, just remember: the AI is probably lost too, but at least it's lost with you!

---

Enjoy your file cards!

# File Card Generator

This tool generates visual information cards for files in a directory, showing metadata, content previews, and other information in a standardized card format. The cards can be output as individual images or combined into a PDF.

## Features

- Creates visually appealing file information cards with previews
- Supports many file types with specialized previews:
  - Images (PNG, JPG, TIFF, HEIC, etc.)
  - PDF (shows thumbnails of first few pages)
  - Videos (shows frame samples)
  - Code & Text (shows formatted content preview)
  - Archive files (ZIP, GZ, BZ2 - shows file listings)
  - GPS files (GPX, FIT, TCX - shows track maps)
- Mapbox integration for GPS tracks with beautiful maps
- Slack integration for files exported from Slack
- CMYK color mode support for print-ready output
- Customizable page sizes and scaling
- Avatar display for Slack-shared files
- User-friendly command line interface

## Requirements

- Python 3.7+
- Node.js 14+ (for PDF assembly with `combine_images_to_pdf.js`)
- Pillow
- pdf2image (requires poppler)
- fitparse (optional, for FIT file support)
- pillow-heif (optional, for HEIC file support)
- gpxpy
- polyline
- cv2
- requests
- dotenv
- For Node.js script:
  - sharp
  - pdfkit
  - commander

## Installation

```bash
# Install Python dependencies
pip install pillow pdf2image fitparse gpxpy polyline opencv-python requests python-dotenv pillow-heif

# Install Node.js dependencies
npm install
```

## Processing Order

The file card generation and PDF assembly workflow follows these steps:

1. **Card Generation** (`file_card_generator.py`)
   - Processes individual files and creates information cards
   - Extracts metadata, generates previews, and creates visual cards
   - Outputs individual TIFF or JPEG files

2. **Card Assembly** (Choose one option)
   - **Python Method** (`test_file_cards.py`):
     - Processes a directory of files, generating cards for each
     - Optionally combines cards into a PDF using img2pdf or FPDF
     - Good for simple assemblies but has limitations with TIFF files
   
   - **Node.js Method** (`combine_images_to_pdf.js`):
     - Takes generated card images and combines them into a single PDF
     - Handles both RGB and CMYK color modes
     - Better color fidelity and TIFF support
     - More customization options (sorting, filtering, etc.)

## Usage

### Basic Card Generation

```bash
python test_file_cards.py --input-dir /path/to/files --output-dir /path/for/cards --cmyk-mode --page-size A4
```

### Combining Images to PDF (Node.js Method)

After generating individual cards, use the Node.js script for better PDF output:

```bash
# RGB mode
./combine_images_to_pdf.js -i ./file_card_tests -o combined_cards.pdf

# CMYK mode (print-ready)
./combine_images_to_pdf.js -i ./file_card_tests -o combined_cards_cmyk.pdf --cmyk-mode

# Customize sorting order (by name, date, etc.)
./combine_images_to_pdf.js -i ./file_card_tests -o combined_cards.pdf --sort-by name --sort-order desc

# Suppress verbose output
./combine_images_to_pdf.js -i ./file_card_tests -o combined_cards.pdf --quiet
```

The Node.js script offers several advantages:
- Better handling of TIFF files with CMYK color profiles
- High-quality image processing with Sharp library
- Flexible page size options
- Sorting and filtering capabilities
- Can handle large collections of images efficiently

## Mapbox Integration

For GPS files (GPX, FIT, TCX), the cards can display beautiful maps using Mapbox:

1. Create a free Mapbox account at https://www.mapbox.com/
2. Get your API key (access token)
3. Create a `.env` file with: `MAPBOX_TOKEN=your_token_here`
4. Run the script and enjoy beautiful map previews!

## Slack Integration

The tool can display additional metadata for files from a Slack export:

- Channel name
- User who shared the file
- User's avatar
- Date shared
- Message ID

Ensure your Slack export contains the following files:
- `messages.json` (in each channel directory)
- `users.json` (in the export root)
- User avatars in an `avatars` directory

## Troubleshooting

- If HEIC files are not displaying, ensure you have the `pillow-heif` package installed
- For PDF issues, ensure you have poppler installed
- For CMYK output, use the Node.js method to combine files into a PDF
- If Mapbox maps are not showing, check your token and internet connection
