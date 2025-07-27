import sys
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import math
import argparse


STANDARD_SIZES = {
    '8.5x11': (2550, 3300),  # 300 DPI
    'A0': (9933, 14043),
    'A1': (7016, 9933),
    'A2': (4961, 7016),
    'A3': (3508, 4961),
    'A4': (2480, 3508),
    'A5': (1748, 2480),
    'A6': (1240, 1748),
    'A7': (874, 1240),
    'A8': (614, 874),
    'ANSI A': (2550, 3300),
    'ANSI B': (3300, 5100),
    'ANSI C': (5100, 6600),
}


def parse_page_size(size_str, orientation='portrait'):
    if size_str in STANDARD_SIZES:
        w, h = STANDARD_SIZES[size_str]
    else:
        try:
            w, h = size_str.lower().split('x')
            w, h = float(w), float(h)
            w, h = int(w * 300), int(h * 300)
        except Exception:
            raise ValueError(f'Invalid page size: {size_str}')
    if orientation == 'landscape':
        w, h = h, w
    return w, h


def draw_hairline_border(draw, xy, width, color):
    x0, y0, x1, y1 = xy
    # Draw rectangle tightly around the image bounds
    for i in range(width):
        draw.rectangle([x0+i, y0+i, x1-i, y1-i], outline=color)


def fit_image(img, max_w, max_h, fit_mode):
    if fit_mode == 'rotate':
        # Rotate image if it better fits the max dimensions
        if (img.width > img.height and max_w < max_h) or (img.width < img.height and max_w > max_h):
            img = img.rotate(90, expand=True)
    if fit_mode in ['scale', 'rotate']:
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    else:  # uniform
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img


def arrange_grid(images, page_size, gap, hairline_width, hairline_color, padding, image_fit_mode, grid_rows=None, grid_cols=None, page_margin=0):
    page_w, page_h = page_size
    content_w = page_w - 2 * page_margin
    content_h = page_h - 2 * page_margin

    if grid_rows and grid_cols:
        rows = grid_rows
        cols = grid_cols
    else:
        cols = math.ceil(math.sqrt(len(images)))
        rows = math.ceil(len(images) / cols)

    total_gap_w = gap * (cols - 1)
    total_gap_h = gap * (rows - 1)
    cell_w = (content_w - total_gap_w) // cols
    cell_h = (content_h - total_gap_h) // rows

    page_img = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(page_img)

    offset_x = page_margin
    offset_y = page_margin

    for idx, img in enumerate(images):
        max_w = cell_w - 2 * (padding + hairline_width)
        max_h = cell_h - 2 * (padding + hairline_width)

        img = fit_image(img, max_w, max_h, image_fit_mode)

        col = idx % cols
        row = idx // cols
        x = offset_x + col * (cell_w + gap)
        y = offset_y + row * (cell_h + gap)

        img_x = x + padding + hairline_width
        img_y = y + padding + hairline_width

        page_img.paste(img, (img_x, img_y))

        border_xy = (img_x, img_y, img_x + img.width - 1, img_y + img.height - 1)
        draw_hairline_border(draw, border_xy, hairline_width, hairline_color)

    return page_img


def arrange_masonry(images, page_size, gap, hairline_width, hairline_color, padding, image_fit_mode, page_margin=0):
    page_w, page_h = page_size
    content_w = page_w - 2 * page_margin
    content_h = page_h - 2 * page_margin

    cols = math.ceil(math.sqrt(len(images)))
    col_w = (content_w - gap * (cols - 1)) // cols

    page_img = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(page_img)

    col_y_offsets = [0] * cols

    offset_x = page_margin
    offset_y = page_margin

    for idx, img in enumerate(images):
        max_w = col_w - 2 * (padding + hairline_width)

        img = fit_image(img, max_w, content_h, image_fit_mode)

        col = col_y_offsets.index(min(col_y_offsets))
        x = offset_x + col * (col_w + gap)
        y = offset_y + col_y_offsets[col]

        img_x = x + padding + hairline_width
        img_y = y + padding + hairline_width

        page_img.paste(img, (img_x, img_y))

        border_xy = (img_x, img_y, img_x + img.width - 1, img_y + img.height - 1)
        draw_hairline_border(draw, border_xy, hairline_width, hairline_color)

        col_y_offsets[col] += img.height + gap

        if col_y_offsets[col] > content_h:
            break

    return page_img


def pdf_to_images(pdf_path, layout, page_size, gap, hairline_width, hairline_color, padding, page_orientation, image_fit_mode, grid_rows=None, grid_cols=None, page_margin=0, output_pdf=False):
    images = convert_from_path(pdf_path)
    output_dir = Path(pdf_path).stem + '_output_pages'
    Path(output_dir).mkdir(exist_ok=True)

    output_images = []

    # Process images in chunks based on grid size or automatic
    chunk_size = None
    if grid_rows and grid_cols:
        chunk_size = grid_rows * grid_cols

    for i in range(0, len(images), chunk_size or len(images)):
        chunk = images[i:i+(chunk_size or len(images))]

        if layout == 'grid':
            page_img = arrange_grid(chunk, page_size, gap, hairline_width, hairline_color, padding, image_fit_mode, grid_rows, grid_cols, page_margin)
        else:
            page_img = arrange_masonry(chunk, page_size, gap, hairline_width, hairline_color, padding, image_fit_mode, page_margin)

        output_images.append(page_img)

        output_path = Path(output_dir) / f'output_page_{i//(chunk_size or len(images)) + 1}.png'
        page_img.save(output_path)
        print(f'Saved {output_path}')

    if output_pdf:
        pdf_path_out = Path(output_dir) / (Path(pdf_path).stem + '_output.pdf')
        output_images[0].save(pdf_path_out, save_all=True, append_images=output_images[1:])
        print(f'Saved PDF {pdf_path_out}')


def main():
    parser = argparse.ArgumentParser(description='Convert PDF to pages of images arranged in grid or masonry layout.')
    parser.add_argument('input_pdf', help='Path to input PDF file')
    parser.add_argument('--layout', choices=['grid', 'masonry'], default='grid', help='Layout style')
    parser.add_argument('--page-size', default='8.5x11', help='Page size (e.g. 8.5x11, A4, ANSI A)')
    parser.add_argument('--page-orientation', choices=['portrait', 'landscape'], default='portrait', help='Page orientation')
    parser.add_argument('--image-fit-mode', choices=['uniform', 'rotate', 'scale'], default='uniform', help='Image fit mode')
    parser.add_argument('--gap', type=int, default=10, help='Gap between images in pixels')
    parser.add_argument('--hairline-width', type=int, default=1, help='Width of hairline border in pixels')
    parser.add_argument('--hairline-color', default='black', help='Color of hairline border')
    parser.add_argument('--padding', type=int, default=5, help='Padding between image and hairline border in pixels')
    parser.add_argument('--grid-rows', type=int, help='Number of rows in grid layout')
    parser.add_argument('--grid-cols', type=int, help='Number of columns in grid layout')
    parser.add_argument('--grid', type=str, help='Grid size shorthand as ROWSxCOLS, e.g. 2x3')
    parser.add_argument('--page-margin', type=float, default=0.25, help='Page margin in inches')
    parser.add_argument('--output-pdf', action='store_true', help='Generate a PDF of the output pages')

    args = parser.parse_args()

    # Parse grid shorthand if provided
    grid_rows = args.grid_rows
    grid_cols = args.grid_cols
    if args.grid:
        try:
            parts = args.grid.lower().split('x')
            if len(parts) == 2:
                grid_rows = int(parts[0])
                grid_cols = int(parts[1])
            else:
                raise ValueError('Invalid grid format')
        except Exception as e:
            print(f'Error parsing --grid: {e}')
            sys.exit(1)

    try:
        page_size = parse_page_size(args.page_size, args.page_orientation)
    except ValueError as e:
        print(e)
        sys.exit(1)

    page_margin_px = int(args.page_margin * 300)  # Convert inches to pixels

    pdf_to_images(args.input_pdf, args.layout, page_size, args.gap, args.hairline_width, args.hairline_color, args.padding, args.page_orientation, args.image_fit_mode, grid_rows, grid_cols, page_margin_px, args.output_pdf)


if __name__ == '__main__':
    main()
