# directory_to_flipbooks.py

## Overview
`directory_to_flipbooks.py` is a Python script designed to create flipbooks from movie/video files in a specified input directory. It does **not** generate standard image grids or pages for other file types. The output consists of flipbook pages and optional PDFs, organized by channel (parent directory name) and video file name.

## Features
- Processes only movie/video files (`.mp4`, `.mov`, `.avi`, `.mkv`) in the input directory.
- Extracts frames at a user-defined rate (frames per second) for flipbook creation.
- Generates flipbook pages as images (TIFF for CMYK, PNG for RGB).
- Optionally combines flipbook pages into a PDF per video.
- Customizable page size, orientation, hairline border, and background color (RGB or CMYK).
- Output directory structure includes channel name and video name for easy organization.

## Command Line Arguments
```
python directory_to_flipbooks.py <input_dir> [options]
```

### Required Argument
- `input_dir`: Path to the input directory containing movie/video files.

### Optional Arguments
- `--page-size`: Page size. Supported options:
    - `8.5x11`
    - `A0`
    - `A1`
    - `A2`
    - `A3`
    - `A4`
    - `A5`
    - `A6`
    - `A7`
    - `A8`
    - `ANSI A`
    - `ANSI B`
    - `ANSI C`
  You can also specify a custom size in the format `<width>x<height>` (in inches), which will be converted to pixels at 300 DPI. Default: `8.5x11`.
- `--page-orientation`: Page orientation (`portrait` or `landscape`). Default: `portrait`.
- `--hairline-width`: Width of hairline border in inches. Default: `0.0033` (approx 1 pixel).
- `--hairline-color`: Color of hairline border. Default: `black`.
- `--video-fps`: Frames per second to extract from videos. Default: `1`.
- `--output-pdf`: If set, generates a PDF of the flipbook pages for each video.
- `--output-dir`: Directory to save output flipbook pages. Default: `<parent_of_parent>_flipbook_pages` in the script directory.
- `--cmyk-mode`: If set, outputs images in CMYK color mode (TIFF format).
- `--cmyk-background`: CMYK background color for content pages as `C,M,Y,K` values (0-255, comma-separated). Default: `0,0,0,0` (white).
- `--cmyk-flipbook-background`: CMYK background color for blank flipbook pages as `C,M,Y,K` values (0-255, comma-separated). Default: `22,0,93,0` (Omata acid color).

### Example Usage
```
python directory_to_flipbooks.py /path/to/channel_dir --video-fps 2 --output-pdf --cmyk-mode --page-size A4 --hairline-color "#FF00FF"
```

```
python3 ./directory_to_flipbooks.py /Users/julian/Code/SlackExporterForOmata/id-explorations/files/ --page-size A5 --p
age-orientation portrait --video-fps 1 --cmyk-mode --cmyk-flipbook-background '61,53
,42,14' --output-dir '/Users/julian/Dropbox (Personal)/Projects By Year/@2025/OMATA Process Diary/OMATA-SlackBooks/slack-channel-cards/'
```

## Output Structure
- Output directory: `<parent_of_parent>_flipbook_pages` (or as specified by `--output-dir`)
- For each video file:
  - Subdirectory: `<channel_name>/<channel_name>_flipbook_<video_name>`
  - Flipbook pages: Sequentially numbered TIFF or PNG files
  - Optional PDF: `<video_name>_flipbook.pdf`

## Mapbox API_TOKEN Note
This script does **not** require a Mapbox API_TOKEN. If you use related scripts (e.g., for map visualizations or geospatial features), you may need to set your Mapbox API_TOKEN as an environment variable:
```
export MAPBOX_API_TOKEN=your_token_here
```
For `directory_to_flipbooks.py`, this is **not required**.

## Related Information
- Only movie/video files are processed for flipbook creation. Other file types (images, PDFs, non-visual files) are ignored.
- For grid/masonry layouts or batch processing of all file types, use `directory_to_images.py` or `generate_flipbook_pages.py`.
- Output images are scaled to fit 70% of the page width and positioned on the right side of each page, with blank verso pages in flipbooks.
- CMYK mode is recommended for print-ready output (TIFF format).

## Troubleshooting
- Ensure all dependencies are installed: `Pillow`, `opencv-python`, `pdf2image`, `pillow-heif` (for HEIC), etc.
- If you encounter errors with video processing, check that `ffmpeg` is installed and accessible.
- For CMYK output, TIFF format is used; for RGB, PNG format is used.

## License & Credits
- Developed for Omata by Julian Bleecker and contributors.
- See repository for license and additional documentation.
