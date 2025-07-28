import sys
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
import math
import argparse
import os

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


def fit_image(img, max_w, max_h, fit_mode, is_flipbook=False):
    if is_flipbook:
        # For flipbook images, try to scale up to 3x but ensure they fit within bounds
        # Never rotate flipbook images
        original_width, original_height = img.width, img.height
        
        # Calculate 3x dimensions
        scaled_width = original_width * 3
        scaled_height = original_height * 3
        
        # If scaled dimensions exceed max dimensions, scale down proportionally
        if scaled_width > max_w or scaled_height > max_h:
            # Calculate scale factors
            scale_w = max_w / scaled_width if scaled_width > max_w else 1
            scale_h = max_h / scaled_height if scaled_height > max_h else 1
            
            # Use the smaller scale factor to ensure it fits
            scale = min(scale_w, scale_h)
            
            # Calculate final dimensions
            final_width = int(scaled_width * scale)
            final_height = int(scaled_height * scale)
            
            # Resize with these dimensions
            img = img.resize((final_width, final_height), Image.Resampling.LANCZOS)
        else:
            # Can scale up to full 3x
            img = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    else:
        # Original behavior for non-flipbook images
        if fit_mode == 'rotate':
            # Rotate image if it better fits the max dimensions
            if (img.width > img.height and max_w < max_h) or (img.width < img.height and max_w > max_h):
                img = img.rotate(90, expand=True)
        if fit_mode in ['scale', 'rotate']:
            img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        else:  # uniform
            img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    
    return img


def arrange_grid(images, page_size, n, gap, hairline_width, hairline_color, padding, 
                image_fit_mode, grid_rows=None, grid_cols=None, page_margin=0, 
                side='recto', is_flipbook=False, image_paths=None):
    page_w, page_h = page_size
    
    # Important: For proper recto/verso layout, we need different content widths for each page type
    # For recto pages: leave wide left margin, narrow right margin
    # For verso pages: leave narrow left margin, wide right margin
    
    # For flipbooks, use only 70% of the page width
    if is_flipbook:
        usable_width = int((page_w - 2 * page_margin) * 0.7)  # 70% of usable width for flipbook
    else:
        usable_width = page_w - 2 * page_margin  # Use full page width minus margins for regular content
    
    if grid_rows and grid_cols:
        rows = grid_rows
        cols = grid_cols
    else:
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)

    total_gap_w = gap * (cols - 1)
    total_gap_h = gap * (rows - 1)
    
    # Calculate cell width based on the usable width
    cell_w = (usable_width - total_gap_w) // cols
    
    # For vertical layout, still use the standard content height
    content_h = page_h - 2 * page_margin
    cell_h = (content_h - 2 * (padding + hairline_width) - total_gap_h) // rows

    page_img = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(page_img)

    # For book-style layout: 
    # - For verso (left) pages: left edge of content is exactly page_margin from left edge
    # - For recto (right) pages: right edge of content is exactly page_margin from right edge
    
    # Calculate the total width needed for the grid
    grid_width = cols * cell_w + (cols - 1) * gap
    
    # CRITICAL DEBUG CHECK - verify our calculations work as expected
    #print(f"[CRITICAL DEBUG] grid_width={grid_width}, cols={cols}, cell_w={cell_w}, gap={gap}")
    
    if side == 'recto':
        # For recto (right) pages, right edge of content is page_margin from right edge
        recto_offset_x = page_w - page_margin - grid_width
        #print(f"[CRITICAL DEBUG] RECTO page: page_w={page_w}, page_margin={page_margin}, calc: {page_w} - {page_margin} - {grid_width} = {recto_offset_x}")
        offset_x = recto_offset_x
    else:
        # For verso (left) pages, left edge of content is page_margin from left edge
        verso_offset_x = page_margin
        #print(f"[CRITICAL DEBUG] VERSO page: page_margin={page_margin}, offset_x={verso_offset_x}")
        offset_x = verso_offset_x
    
    #print(f"[CRITICAL DEBUG] FINAL offset_x = {offset_x}")
    
    offset_y = page_margin
    
    #print(f"[DEBUG] arrange_grid: side={side}, page_w={page_w}, page_margin={page_margin}, usable_width={usable_width}, grid_width={grid_width}, offset_x={offset_x}, offset_y={offset_y}, cols={cols}, rows={rows}, n={n}")
    for idx in range(n):
        if idx >= len(images):
            break
        img = images[idx]
        max_w = cell_w - 2 * (padding + hairline_width)
        max_h = cell_h - 2 * (padding + hairline_width) - 20  # Reserve space for filename
        
        img = fit_image(img, max_w, max_h, image_fit_mode, is_flipbook=is_flipbook)

        col = idx % cols
        row = idx // cols
        x = offset_x + col * (cell_w + gap)
        y = offset_y + row * (cell_h + gap)

        img_x = x + padding + hairline_width
        img_y = y + padding + hairline_width

        page_img.paste(img, (img_x, img_y))

        border_xy = (img_x, img_y, img_x + img.width - 1, img_y + img.height - 1)
        draw_hairline_border(draw, border_xy, hairline_width, hairline_color)
        
        # Add filename caption if image_paths is provided
        if image_paths and idx < len(image_paths):
            # Get just the filename from the path
            filename = os.path.basename(image_paths[idx])
            
            # Create a font for the caption
            try:
                font = ImageFont.truetype("Input Sans Compressed", 9)
            except IOError:
                font = ImageFont.load_default()
                
            # Calculate text position (centered below image)
            text_y = img_y + img.height + 5
            text_x = img_x + img.width // 2
            
            # Draw the text with a drop shadow for better visibility
            draw.text((text_x+1, text_y+1), filename, fill='gray', font=font, anchor="mt")
            draw.text((text_x, text_y), filename, fill='black', font=font, anchor="mt")
            
    return page_img


def arrange_masonry(images, page_size, n, gap, hairline_width, hairline_color, padding, 
                   image_fit_mode, page_margin=0, side='recto', is_flipbook=False):
    page_w, page_h = page_size
    
    # For flipbooks, use only 70% of the page width
    if is_flipbook:
        usable_width = int((page_w - 2 * page_margin) * 0.7)  # 70% of usable width for flipbook
    else:
        usable_width = page_w - 2 * page_margin  # Use full page width minus margins for regular content
    
    # Rest of the function remains the same...

    # For vertical layout, still use the standard content height
    content_h = page_h - 2 * page_margin

    cols = math.ceil(math.sqrt(n))
    col_w = (usable_width - gap * (cols - 1)) // cols

    page_img = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(page_img)

    col_y_offsets = [0] * cols

    # For book-style layout: 
    # - For verso (left) pages: left edge of content is exactly page_margin from left edge
    # - For recto (right) pages: right edge of content is exactly page_margin from right edge
    
    # Calculate the total width needed for the masonry grid
    grid_width = cols * col_w + (cols - 1) * gap
    
    # CRITICAL DEBUG CHECK - verify our calculations work as expected
    #print(f"[CRITICAL DEBUG MASONRY] grid_width={grid_width}, cols={cols}, col_w={col_w}, gap={gap}")
    
    if side == 'recto':
        # For recto (right) pages, right edge of content is page_margin from right edge
        recto_offset_x = page_w - page_margin - grid_width
        #print(f"[CRITICAL DEBUG MASONRY] RECTO page: page_w={page_w}, page_margin={page_margin}, calc: {page_w} - {page_margin} - {grid_width} = {recto_offset_x}")
        offset_x = recto_offset_x
    else:
        # For verso (left) pages, left edge of content is page_margin from left edge
        verso_offset_x = page_margin
        #print(f"[CRITICAL DEBUG MASONRY] VERSO page: page_margin={page_margin}, offset_x={verso_offset_x}")
        offset_x = verso_offset_x
    
    #print(f"[CRITICAL DEBUG MASONRY] FINAL offset_x = {offset_x}")
    
    offset_y = page_margin
    
    #print(f"[DEBUG] arrange_masonry: side={side}, page_w={page_w}, page_margin={page_margin}, usable_width={usable_width}, grid_width={grid_width}, offset_x={offset_x}, offset_y={offset_y}, cols={cols}, n={n}")
    for idx in range(n):
        if idx >= len(images):
            break
        img = images[idx]
        max_w = col_w - 2 * (padding + hairline_width)

        img = fit_image(img, max_w, content_h, image_fit_mode, is_flipbook=is_flipbook)

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


def pdf_to_images(pdf_path, layout, page_size, gap, hairline_width, hairline_color, 
                 padding, page_orientation, image_fit_mode, grid_rows=None, 
                 grid_cols=None, page_margin=0, output_pdf=False, flipbook_mode=False):
    images = convert_from_path(pdf_path)
    output_dir = Path(pdf_path).stem + '_output_pages'
    Path(output_dir).mkdir(exist_ok=True)

    output_images = []

    # Process images in chunks based on grid size or automatic
    chunk_size = None
    if grid_rows and grid_cols:
        chunk_size = grid_rows * grid_cols

    side = 'recto'  # Default to recto; you can modify this logic if needed

    for i in range(0, len(images), chunk_size or len(images)):
        chunk = images[i:i+(chunk_size or len(images))]
        page_num = (i // (chunk_size or len(images))) + 1
        side = 'recto' if page_num % 2 == 1 else 'verso'
        
        #print(f"[CRITICAL DEBUG PDF] Processing page {page_num}, side={side}, i={i}, chunk_size={chunk_size or len(images)}")

        if layout == 'grid':
            page_img = arrange_grid(chunk, page_size, len(chunk), gap, hairline_width, 
                               hairline_color, padding, image_fit_mode, grid_rows, 
                               grid_cols, page_margin, side=side, is_flipbook=flipbook_mode)
        else:
            page_img = arrange_masonry(chunk, page_size, len(chunk), gap, hairline_width, 
                                  hairline_color, padding, image_fit_mode, page_margin, 
                                  side=side, is_flipbook=flipbook_mode)

        output_images.append(page_img)

        output_path = Path(output_dir) / f'output_page_{page_num}.png'
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
    parser.add_argument('--flipbook-mode', action='store_true', 
                       help='Enable flipbook mode - scales images up to 3x without rotation')

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

    pdf_to_images(args.input_pdf, args.layout, page_size, args.gap, args.hairline_width, args.hairline_color, args.padding, args.page_orientation, args.image_fit_mode, grid_rows, grid_cols, page_margin_px, args.output_pdf, args.flipbook_mode)


if __name__ == '__main__':
    main()
