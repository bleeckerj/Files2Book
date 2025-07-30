# Combine Images to PDF

A Node.js tool to combine images from a directory into a single PDF, with support for both RGB and CMYK color modes.

## Features

- Combine multiple image files into a single PDF
- Support for CMYK or RGB color mode
- Custom page sizes (standard sizes or custom dimensions)
- Sorting options (by name or date)
- Filtering by filename pattern
- Cross-platform compatibility

## Installation

1. Make sure you have [Node.js](https://nodejs.org/) installed (version 14 or higher recommended).

2. Install dependencies:

```bash
npm install
```

3. Make the script executable:

```bash
chmod +x combine_images_to_pdf.js
```

## Usage

```bash
./combine_images_to_pdf.js -i <input_directory> -o <output_pdf_file> [options]
```

### Options

- `-i, --input-dir <dir>`: Directory containing the images (required)
- `-o, --output-file <file>`: Output PDF file path (required)
- `-c, --cmyk-mode`: Use CMYK color mode (default: false)
- `-p, --page-size <size>`: Page size (A4, LETTER, TABLOID, WxH in inches) (default: "A4")
- `-d, --dpi <number>`: DPI for page size calculations (default: 300)
- `-s, --sort-order <order>`: Sort order (name, name-desc, date, date-desc) (default: "name")
- `-f, --filter <pattern>`: Filter files by name pattern (regex)
- `-q, --quiet`: Suppress all non-essential output
- `-h, --help`: Display help
- `-V, --version`: Output the version number

### Examples

1. Convert a folder of images to a PDF in RGB mode:

```bash
./combine_images_to_pdf.js -i ./my_images -o output.pdf
```

2. Convert a folder of images to a PDF in CMYK mode:

```bash
./combine_images_to_pdf.js -i ./my_images -o output_cmyk.pdf --cmyk-mode
```

3. Use a custom page size (5x7 inches) and sort by date:

```bash
./combine_images_to_pdf.js -i ./my_images -o output.pdf -p 5x7 -s date
```

4. Process only TIFF files:

```bash
./combine_images_to_pdf.js -i ./my_images -o output.pdf -f "\.tiff?$"
```

5. Run in quiet mode (suppress all non-essential output):

```bash
./combine_images_to_pdf.js -i ./my_images -o output.pdf --quiet
```

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- TIFF (.tif, .tiff)
- WebP (.webp)
- GIF (.gif)
- SVG (.svg)
- AVIF (.avif)

## Global Installation (Optional)

To install the tool globally on your system:

```bash
npm install -g .
```

After installing globally, you can use the command from anywhere:

```bash
combine-images-to-pdf -i ./my_images -o output.pdf
```
