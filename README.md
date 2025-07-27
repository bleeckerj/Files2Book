# PDF to Pages of Images Converter

This Python CLI tool converts an input PDF document into output pages consisting of multiple images of the original PDF pages. Each output page contains images arranged either in a grid layout or a masonry style layout.

## Features

- Convert each page of a PDF into an image.
- Arrange multiple images per output page.
- Support grid layout with configurable rows, columns, gaps, hairline borders, and padding.
- Support masonry layout with variable image heights stacked in columns.
- Specify output page size with standard sizes (A0-A8, ANSI A-C) or custom dimensions.
- Specify page orientation (portrait or landscape).
- Specify image fit mode to control rotation and scaling of images.
- Specify page margin to add whitespace around the content area.
- Optionally generate a PDF file of the output pages.

## Requirements

### System Requirements

- macOS, Linux, or Windows
- Python 3.7 or higher
- [Poppler](https://poppler.freedesktop.org/) utilities installed and in system PATH (required by `pdf2image`)

  - On macOS, install via Homebrew:
    ```bash
    brew install poppler
    ```

### Python Environment Requirements

- `pdf2image` library
- `Pillow` (PIL) library

Install Python dependencies using pip:

```bash
pip install pdf2image Pillow
```

## Usage

```bash
python pdf_to_images.py <input_pdf_path> [options]
```

### Options

- `--layout`: Layout style, either `grid` or `masonry` (default: `grid`)
- `--page-size`: Output page size, standard sizes like `8.5x11`, `A4`, `ANSI A` or custom size in inches (e.g., `8x10`) (default: `8.5x11`)
- `--page-orientation`: Page orientation, `portrait` or `landscape` (default: `portrait`)
- `--image-fit-mode`: How images fit in their cells:
  - `uniform`: fit images uniformly without rotation
  - `rotate`: rotate images to better fit cell orientation
  - `scale`: scale images to maximize space usage (default: `uniform`)
- `--gap`: Gap between images in pixels (default: 10)
- `--hairline-width`: Width of hairline border around images in pixels (default: 1)
- `--hairline-color`: Color of hairline border (default: `black`)
- `--padding`: Padding between image and hairline border in pixels (default: 5)
- `--grid-rows`: Number of rows in grid layout (optional)
- `--grid-cols`: Number of columns in grid layout (optional)
- `--grid`: Grid size shorthand as ROWSxCOLS, e.g. 2x3 (optional)
- `--page-margin`: Margin around page edges in inches (default: 0.25)
- `--output-pdf`: Generate a PDF of the output pages (optional)

### Example

```bash
python pdf_to_images.py "/path/to/input.pdf" --layout grid --grid-rows 2 --grid-cols 3 --page-size A4 --page-orientation landscape --image-fit-mode scale --gap 8 --hairline-width 1 --hairline-color gray --padding 4 --page-margin 0.5 --output-pdf
```

This command converts the input PDF into output pages arranged in a 2x3 grid layout on A4 sized landscape pages, scaling images to maximize space, with specified gap, hairline border, padding, page margin, and generates a PDF of the output pages.

## Layout and Arrangement Details

- The program arranges images on output pages according to the selected layout style (`grid` or `masonry`).
- In grid layout, the number of rows and columns can be specified explicitly or calculated automatically.
- In masonry layout, images are stacked in columns with variable heights.
- The page margin defines whitespace around the content area, ensuring images do not touch page edges.
- Images are centered within the content area defined by the page size minus margins.
- The image fit mode controls whether images are rotated or scaled to better fit their allocated space.
- Hairline borders are drawn tightly around each image with configurable width, color, and padding.

## Notes

- Ensure Poppler is installed and accessible in your system PATH for `pdf2image` to work.
- Output images are saved in a folder named `<input_pdf_filename>_output_pages` in the current directory.
- If `--output-pdf` is specified, a PDF file containing all output pages is saved in the output directory.

## License

MIT License
