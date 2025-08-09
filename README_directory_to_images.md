# directory_to_images.py

A Python utility for converting directories of images, videos, PDFs, and other files into printable grid or masonry layouts, with advanced support for non-visual files and professional print features.

## Features

- **Grid and Masonry Layouts:** Arrange images, video frames, and file cards in customizable grid or masonry layouts for print-ready pages. Note: Masonry is experimental and still a work in progress.
- **Flipbook Mode:** Extract frames from videos and generate flipbook pages, ensuring all flipbook frames appear on recto (right) pages with blank verso pages as needed.
- **Non-Visual File Support:** Automatically generates visual information cards for non-image files (code, data, spreadsheets, archives, etc.), including file metadata and content previews.
- **HEIC Image Support:** Optionally loads HEIC images if `pillow-heif` is installed.
- **CMYK Color Mode:** Outputs images in CMYK color space for professional printing, with configurable background colors for both regular and flipbook pages.
- **PDF Output:** Combines generated pages into a single PDF for easy printing or archiving.
- **Customizable Appearance:** Control page size, orientation, grid size, gaps, margins, borders, and more via command-line arguments.
- **Robust Error Handling:** Logs errors and provides detailed tracebacks for troubleshooting.

## How It Works

1. **File Discovery:** Scans the input directory for images, videos, PDFs, and other files.
2. **Image & Video Processing:** Loads images and extracts frames from videos (with options for flipbook mode and frame rate).
3. **Non-Visual File Cards:** For non-image files, generates a visual card with file type, name, size, dates, and a preview of text content if available.
4. **Page Layout:** Arranges all visual assets (images, video frames, file cards) into grid or masonry layouts, with options for recto/verso alignment and flipbook handling.
5. **Output Generation:** Saves each page as PNG or TIFF (CMYK), and optionally combines all pages into a PDF.

## Usage

### Basic Command

```bash
python3 directory_to_images.py <input_dir> [options]
```

### Common Options

- `--layout [grid|masonry]` : Choose layout style (default: grid)
- `--grid-rows N` : Number of rows in grid
- `--grid-cols N` : Number of columns in grid
- `--masonry-cols N` : Number of columns in masonry (override auto-detected columns)
- `--page-size SIZE` : Page size (e.g. A5, 8.5x11)
- `--page-orientation [portrait|landscape]`
- `--image-fit-mode [uniform|rotate|scale]`
- `--gap INCHES` : Gap between images (default: 0.0333)
- `--hairline-width INCHES` : Border width (default: 0.0033)
- `--hairline-color COLOR` : Border color (default: black)
- `--padding INCHES` : Padding between image and border (default: 0.0167)
- `--page-margin INCHES` : Page margin (default: 0.25)
- `--output-pdf` : Generate a PDF of all output pages
- `--output-dir DIR` : Custom output directory
- `--flipbook-mode` : Enable flipbook layout for videos
- `--video-fps N` : Frames per second for video extraction (default: 1)
- `--exclude-video-stills` : Exclude video frames from main grid pages
- `--handle-non-visual` : Create info cards for non-visual files (default: true)
- `--no-handle-non-visual` : Skip non-visual files
- `--cmyk-mode` : Output images in CMYK color mode
- `--cmyk-background C,M,Y,K` : CMYK background for regular pages (default: 0,0,0,0)
- `--cmyk-flipbook-background C,M,Y,K` : CMYK background for flipbook blank pages (default: 22,0,93,0)

### Example

```bash
python3 directory_to_images.py ./my_files --layout grid --grid-rows 2 --grid-cols 2 --output-pdf --handle-non-visual
```

### Masonry (Experimental / WIP)

The masonry layout attempts to place items in columns of varying heights while ensuring that every image or card appears without cropping or truncation. It uses:

- A global vertical scaling so the tallest column fits within the page height (including padding, borders, gaps, and caption space).
- A per-column width constraint so columns never overlap horizontally; images are scaled to fit inside the column’s inner width.
- Optional column override via `--masonry-cols` to explicitly choose the number of columns instead of the auto-detected value.

Because this is still a work in progress, results may not always match expectations (for example, items might be smaller than desired on dense pages). If the output isn’t satisfactory:

- Try changing `--masonry-cols` (fewer columns = larger items; more columns = smaller items).
- Adjust `--gap` and `--padding` to change spacing density.
- Consider using `--layout grid` for predictable sizing.

Example:

```bash
python3 directory_to_images.py ./my_files --layout masonry --masonry-cols 3 --output-pdf
```

## Output

- Images and file cards are arranged into pages and saved as PNG (RGB) or TIFF (CMYK).
- If `--output-pdf` is specified, all pages are combined into a single PDF.
- Flipbook pages are saved in a separate directory if flipbook mode is enabled.

## Requirements

- Python 3.8+
- Pillow
- pdf2image
- opencv-python
- numpy
- (Optional) pillow-heif for HEIC support

Install dependencies:

```bash
pip install pillow pdf2image opencv-python numpy pillow-heif
```

## Advanced Features

- **HEIC Support:** If you have HEIC images, install `pillow-heif` to enable loading.
- **CMYK Printing:** Use `--cmyk-mode` for print-ready TIFFs and PDFs.
- **Non-Visual File Cards:** Enable `--handle-non-visual` to include code, data, and other files as visual cards in your archive.
- **Error Logging:** All errors are logged and tracebacks are printed for debugging.

## Troubleshooting

- If you see errors about missing packages, install them with `pip install ...` as above.
- For HEIC images, ensure `pillow-heif` is installed.
- For PDF conversion, ensure `poppler` is installed on your system (e.g. `brew install poppler` on macOS).
- Masonry layout is experimental. If items look too small or placement isn’t desirable, tweak `--masonry-cols`, `--gap`, and `--padding`, or switch to the grid layout.

## License

MIT License
