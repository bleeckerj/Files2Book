# README_file_card_generator

## Overview

`file_card_generator.py` is a robust Python script for generating visual info cards for a wide variety of file types. It creates beautiful, informative images summarizing file metadata, previews, and even GPS tracks with dynamic Mapbox map thumbnails. Whether you're working with images, PDFs, videos, archives, or GPS files, this tool helps you visualize and organize your files with style.

## Features

- **Supports Many File Types:**
  - Images (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.tiff`, `.heic`)
  - Videos (`.mp4`, `.mov`, `.avi`, `.mkv`)
  - Documents (`.pdf`, `.docx`, `.txt`, `.md`, etc.)
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

Install requirements:
```bash
pip install Pillow requests gpxpy fitparse polyline pdf2image opencv-python python-dotenv pyheif
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
python file_card_generator.py /path/to/your/file.ext
```

### Command Line Arguments
- `file_path` (required): Path to the file you want to generate a card for.
- `--width WIDTH`: Output card width (default: 800)
- `--height HEIGHT`: Output card height (default: 1000)
- `--cmyk`: Enable CMYK mode for print
- `--output OUTPUT_PATH`: Path to save the generated image (default: `file_card.png`)

Example:
```bash
python file_card_generator.py myfile.gpx --width 1200 --height 1500 --output my_card.png
```

### As a Module
You can import and use `create_file_info_card` in your own Python code:
```python
from file_card_generator import create_file_info_card
img = create_file_info_card('myfile.pdf', width=1200, height=1500)
img.save('my_card.png')
```

## New Features and Enhancements

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
