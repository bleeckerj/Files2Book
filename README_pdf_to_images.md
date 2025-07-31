# pdf_to_images.py

## Overview
`pdf_to_images.py` is a Python script that converts PDF files into image pages, arranging them in either grid or masonry layouts. It supports advanced options for page size, orientation, image fit mode, margins, and color mode (RGB or CMYK). The script can also generate a combined PDF of the output images and supports flipbook-style layouts.

## Features
- Converts each page of a PDF into an image file (PNG for RGB, TIFF for CMYK).
- Arranges images in grid or masonry layouts with customizable rows, columns, gaps, and padding.
- Supports custom and standard page sizes (e.g., 8.5x11, A4, ANSI A, etc.).
- Allows portrait or landscape orientation.
- Optional hairline borders and captions for each image.
- Supports CMYK color mode for print-ready output.
- Can generate a combined PDF of all output images.
- Flipbook mode for special layouts.

## Command Line Arguments
```
python pdf_to_images.py <input_pdf> [options]
```

### Required Argument
- `input_pdf`: Path to the input PDF file.

### Optional Arguments
- `--layout`: Layout style (`grid` or `masonry`). Default: `grid`.
- `--page-size`: Page size. Supported options:
    - `8.5x11`
    - `A0`, `A1`, `A2`, `A3`, `A4`, `A5`, `A6`, `A7`, `A8`
    - `ANSI A`, `ANSI B`, `ANSI C`
  You can also specify a custom size in the format `<width>x<height>` (in inches), which will be converted to pixels at 300 DPI. Default: `8.5x11`.
- `--page-orientation`: Page orientation (`portrait` or `landscape`). Default: `portrait`.
- `--image-fit-mode`: How images are fit (`uniform`, `rotate`, `scale`). Default: `uniform`.
- `--gap`: Gap between images in pixels. Default: `10`.
- `--hairline-width`: Width of hairline border in pixels. Default: `1`.
- `--hairline-color`: Color of hairline border. Default: `black`.
- `--padding`: Padding between image and border in pixels. Default: `5`.
- `--grid-rows`: Number of rows in grid layout.
- `--grid-cols`: Number of columns in grid layout.
- `--grid`: Grid size shorthand as `ROWSxCOLS`, e.g. `2x3`.
- `--inner-margin`: Inner margin in inches. Default: `0.25`.
- `--outer-margin`: Outer margin in inches. Default: `0.5`.
- `--output-pdf`: If set, generates a PDF of the output images.
- `--flipbook-mode`: If set, enables flipbook layout.
- `--cmyk-mode`: If set, outputs images in CMYK color mode (TIFF format).
- `--cmyk-background`: CMYK background color as `C,M,Y,K` values (0-255, comma-separated). Default: `0,0,0,0` (white).

### Example Usage
```
python pdf_to_images.py mydoc.pdf --layout grid --page-size A4 --grid 2x3 --output-pdf --cmyk-mode
```

## Output Structure
- Output images are saved in a directory named `<input_pdf_stem>_output_pages`.
- Images are sequentially numbered (e.g., `output_page_1.png`, `output_page_2.tiff`).
- If `--output-pdf` is set, a combined PDF is saved in the same directory.

## Dependencies
- Python 3.x
- [Pillow](https://python-pillow.org/) (PIL)
- [pdf2image](https://github.com/Belval/pdf2image)
- [PyPDF2](https://github.com/py-pdf/PyPDF2) (if required by pdf2image)
- [opencv-python](https://github.com/opencv/opencv-python) (for advanced image handling)

Install dependencies with:
```
pip install pillow pdf2image opencv-python
```
You may also need to install poppler for `pdf2image`:
- macOS: `brew install poppler`
- Ubuntu: `sudo apt-get install poppler-utils`

## Troubleshooting
- Ensure all dependencies are installed and available in your Python environment.
- For CMYK output, TIFF format is used; for RGB, PNG format is used.
- If you encounter errors with PDF conversion, check that poppler is installed and accessible.

## License & Credits
- Developed for Omata by Julian Bleecker and contributors.
- See repository for license and additional documentation.
