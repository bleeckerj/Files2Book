import sys
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont, ImageCms
import math
import argparse
import os
import io

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

def create_cmyk_image(width, height, color=(0, 0, 0, 0)):
    """
    Create a new CMYK image with the specified dimensions and color.
    
    Args:
        width (int): Image width in pixels
        height (int): Image height in pixels
        color (tuple): CMYK color values as a tuple (C, M, Y, K) where each value is in range 0-255
                       0 means no color (white), 255 means full color
        
    Returns:
        PIL.Image: A CMYK mode image
    """
    # Create a CMYK image
    cmyk_image = Image.new('CMYK', (width, height), color)
    return cmyk_image

def rgb_to_cmyk_image(rgb_image):
    """
    Convert an RGB image to CMYK mode.
    
    Args:
        rgb_image (PIL.Image): RGB mode image
        
    Returns:
        PIL.Image: A CMYK mode image
    """
    # Make sure the image is in RGB mode first
    if rgb_image.mode != 'RGB':
        rgb_image = rgb_image.convert('RGB')
        
    # Convert to CMYK
    cmyk_image = rgb_image.convert('CMYK')
    return cmyk_image

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
    for i in range(width):
        draw.rectangle([x0+i, y0+i, x1-i, y1-i], outline=color)

def fit_image(img, max_w, max_h, fit_mode, is_flipbook=False):
    if is_flipbook:
        original_width, original_height = img.width, img.height
        scaled_width = original_width * 3
        scaled_height = original_height * 3
        if scaled_width > max_w or scaled_height > max_h:
            scale = min(max_w / scaled_width, max_h / scaled_height)
            img = img.resize((int(scaled_width * scale), int(scaled_height * scale)), Image.Resampling.LANCZOS)
        else:
            img = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    else:
        if fit_mode == 'rotate':
            if (img.width > img.height and max_w < max_h) or (img.width < img.height and max_w > max_h):
                img = img.rotate(90, expand=True)
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img

def arrange_grid(images, page_size, n, gap, hairline_width, hairline_color, padding, 
                 image_fit_mode, grid_rows=None, grid_cols=None,
                 inner_margin_px=0, outer_margin_px=0, side='recto',
                 is_flipbook=False, image_paths=None, cmyk_mode=False, cmyk_background=(0,0,0,0)):
    page_w, page_h = page_size
    if cmyk_mode:
        page_img = create_cmyk_image(page_w, page_h, cmyk_background)
    else:
        page_img = Image.new('RGB', page_size, 'white')
    draw = ImageDraw.Draw(page_img)

    cols = grid_cols if grid_cols else math.ceil(math.sqrt(n))
    rows = grid_rows if grid_rows else math.ceil(n / cols)

    total_gap_w = gap * (cols - 1)
    total_gap_h = gap * (rows - 1)

    left_margin = inner_margin_px if side == 'recto' else outer_margin_px
    right_margin = outer_margin_px if side == 'recto' else inner_margin_px

    usable_width = page_w - left_margin - right_margin
    usable_width = int(usable_width * 0.7) if is_flipbook else usable_width

    # Calculate column width based on image dimensions for all layouts
    max_image_width = 0
    for img in images:
        if img.width > max_image_width:
            max_image_width = img.width
    
    # Add minimal padding and hairlines
    cell_w = max_image_width + 2 * (padding + hairline_width)
    
    # If flipbook mode, scale up the cell width
    if is_flipbook:
        cell_w = int(cell_w * 3)
        
    # Ensure cell doesn't exceed usable width
    max_allowed_width = page_w - left_margin - right_margin
    if is_flipbook:
        max_allowed_width = int(max_allowed_width * 0.7)
    
    # For multi-column layouts, ensure all columns fit
    if cols > 1:
        total_width_needed = (cell_w * cols) + (gap * (cols - 1))
        if total_width_needed > max_allowed_width:
            # Scale down cell width to fit if needed
            available_width = max_allowed_width - (gap * (cols - 1))
            cell_w = available_width // cols

    # Update grid width calculation
    grid_width = cols * cell_w + (cols - 1) * gap
    
    # Calculate offset based on side
    if side == 'recto':
        offset_x = page_w - right_margin - grid_width
    else:
        offset_x = left_margin

    # Add bottom margin for captions
    bottom_margin_px = int(0.14 * 300)  # 0.14 inch in pixels
    content_h = page_h - inner_margin_px - outer_margin_px - bottom_margin_px
    cell_h = (content_h - total_gap_h) // rows
    offset_y = inner_margin_px

    # # Draw debug rectangles for column boundaries
    # for col in range(cols):
    #     x = offset_x + col * (cell_w + gap)
    #     # Draw a red rectangle outline for each column's boundaries
    #     draw.rectangle([x, offset_y, x + cell_w, offset_y + content_h], 
    #                   outline='red', fill=(255, 0, 0, 25))  # Very light red fill
    #     # Print column positions
    #     print(f"[DEBUG] Column {col}: x={x}, width={cell_w}, right edge={x + cell_w}")
    
    # # Draw page margins for debugging
    # draw.line([(left_margin, 0), (left_margin, page_h)], fill='blue', width=2)  # Left margin
    # draw.line([(page_w - right_margin, 0), (page_w - right_margin, page_h)], fill='blue', width=2)  # Right margin

    # # Draw a vertical line at offset_x to show where grid starts
    # draw.line([(offset_x, 0), (offset_x, page_h)], fill='green', width=2)  # Grid start position

    # Position images within columns with proper alignment
    for idx in range(n):
        if idx >= len(images):
            break
        img = images[idx]
        max_w = cell_w - 2 * (padding + hairline_width)
        filename_space = 40  # Allow more space for filename text
        max_h = cell_h - 2 * (padding + hairline_width) - filename_space
        img = fit_image(img, max_w, max_h, image_fit_mode, is_flipbook)

        col = idx % cols
        row = idx // cols
        x = offset_x + col * (cell_w + gap)
        y = offset_y + row * (cell_h + gap)

        # Align image within column based on page side
        if side == 'recto':
            # Right-align image within column
            img_x = x + (cell_w - img.width - 2 * (padding + hairline_width))
        else:
            # Left-align image within column
            img_x = x + padding + hairline_width
        
        img_y = y + padding + hairline_width

        page_img.paste(img, (img_x, img_y))
        draw_hairline_border(draw, (img_x, img_y, img_x + img.width - 1, img_y + img.height - 1), 
                           hairline_width, hairline_color)

        if image_paths and idx < len(image_paths):
            filename = os.path.basename(image_paths[idx])
            # Calculate text position first
            text_y = img_y + img.height + 5
            text_x = img_x + img.width // 2
            
            #print(f"Drawing filename: {filename} at position ({text_x}, {text_y})")
            try:
                font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 30)
            except IOError:
                print("Using default font due to IOError")
                font = ImageFont.load_default()
                
            # Draw text shadow and then text
            draw.text((text_x+1, text_y+1), filename, fill='gray', font=font, anchor="mt")
            draw.text((text_x, text_y), filename, fill='black', font=font, anchor="mt")

    return page_img

def arrange_masonry(images, page_size, n, gap, hairline_width, hairline_color, padding, 
                    image_fit_mode, inner_margin_px=0, outer_margin_px=0, 
                    side='recto', is_flipbook=False, image_paths=None, 
                    cmyk_mode=False, cmyk_background=(0,0,0,0)):
    page_w, page_h = page_size
    left_margin = inner_margin_px if side == 'recto' else outer_margin_px
    right_margin = outer_margin_px if side == 'recto' else inner_margin_px
    
    # Create page and drawing context - either RGB or CMYK
    if cmyk_mode:
        page_img = create_cmyk_image(page_w, page_h, cmyk_background)
    else:
        page_img = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(page_img)

    # Calculate usable dimensions
    usable_width = page_w - left_margin - right_margin
    if is_flipbook:
        usable_width = int(usable_width * 0.7)

    # Add bottom margin for captions
    bottom_margin_px = int(0.14 * 300)  # 0.14 inch in pixels
    content_h = page_h - inner_margin_px - outer_margin_px - bottom_margin_px
    cols = math.ceil(math.sqrt(n))
    
    # Calculate max image width for column sizing
    max_image_width = 0
    for img in images:
        if img.width > max_image_width:
            max_image_width = img.width
    
    # Base column width on actual image dimensions plus padding
    col_w = max_image_width + 2 * (padding + hairline_width)
    if is_flipbook:
        col_w = int(col_w * 3)
    
    # Ensure columns fit within usable width
    total_width_needed = (col_w * cols) + (gap * (cols - 1))
    if total_width_needed > usable_width:
        available_width = usable_width - (gap * (cols - 1))
        col_w = available_width // cols

    # Initialize column tracking
    col_y_offsets = [0] * cols
    
    # Calculate starting x position based on side
    if side == 'recto':
        offset_x = page_w - right_margin - (cols * col_w + (cols - 1) * gap)
    else:
        offset_x = left_margin
    
    offset_y = inner_margin_px

    # Position images within columns
    for idx in range(n):
        if idx >= len(images):
            break
            
        img = images[idx]
        max_w = col_w - 2 * (padding + hairline_width)
        img = fit_image(img, max_w, content_h, image_fit_mode, is_flipbook)

        # Find shortest column
        col = col_y_offsets.index(min(col_y_offsets))
        x = offset_x + col * (col_w + gap)
        y = offset_y + col_y_offsets[col]

        # Align image within column based on page side
        if side == 'recto':
            img_x = x + (col_w - img.width - 2 * (padding + hairline_width))
        else:
            img_x = x + padding + hairline_width
            
        img_y = y + padding + hairline_width

        # Place image and draw border
        page_img.paste(img, (img_x, img_y))
        draw_hairline_border(draw, (img_x, img_y, img_x + img.width - 1, img_y + img.height - 1), 
                           hairline_width, hairline_color)

        # Add filename caption if paths provided
        if image_paths and idx < len(image_paths):
            filename = os.path.basename(image_paths[idx])
            text_y = img_y + img.height + 5
            text_x = img_x + img.width // 2
            
            try:
                font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 30)
            except IOError:
                print("Using default font due to IOError")
                font = ImageFont.load_default()
            
            # Draw text shadow and then text
            draw.text((text_x+1, text_y+1), filename, fill='gray', font=font, anchor="mt")
            draw.text((text_x, text_y), filename, fill='black', font=font, anchor="mt")

        # Update column height
        filename_space = 40  # Allow more space for filename text
        col_y_offsets[col] += img.height + gap + filename_space
        if col_y_offsets[col] > content_h:
            break

    return page_img

def pdf_to_images(pdf_path, layout, page_size, gap, hairline_width, hairline_color, 
                 padding, page_orientation, image_fit_mode, grid_rows=None, 
                 grid_cols=None, inner_margin_px=0, outer_margin_px=0, 
                 output_pdf=False, flipbook_mode=False, cmyk_mode=False, cmyk_background=(0,0,0,0)):
    images = convert_from_path(pdf_path)
    output_dir = Path(pdf_path).stem + '_output_pages'
    Path(output_dir).mkdir(exist_ok=True)

    output_images = []
    chunk_size = grid_rows * grid_cols if grid_rows and grid_cols else None

    page_counter = 1
    for i in range(0, len(images), chunk_size or len(images)):
        chunk = images[i:i+(chunk_size or len(images))]
        
        side = 'recto' if page_counter % 2 == 1 else 'verso'

        if layout == 'grid':
            page_img = arrange_grid(chunk, page_size, len(chunk), gap, hairline_width, 
                                     hairline_color, padding, image_fit_mode, grid_rows, 
                                     grid_cols, inner_margin_px, outer_margin_px, side, 
                                     is_flipbook=flipbook_mode, cmyk_mode=cmyk_mode, 
                                     cmyk_background=cmyk_background)
        else:
            page_img = arrange_masonry(chunk, page_size, len(chunk), gap, hairline_width, 
                                       hairline_color, padding, image_fit_mode, 
                                       inner_margin_px, outer_margin_px, side, 
                                       is_flipbook=flipbook_mode, cmyk_mode=cmyk_mode, 
                                       cmyk_background=cmyk_background)

        output_images.append(page_img)
        # Save image - use TIFF for CMYK mode
        if cmyk_mode:
            output_path = Path(output_dir) / f'output_page_{page_counter}.tiff'
            page_img.save(output_path, compression='tiff_lzw')
        else:
            output_path = Path(output_dir) / f'output_page_{page_counter}.png'
            page_img.save(output_path)
        print(f'Saved {output_path}')
        page_counter += 1

    if output_pdf:
        pdf_path_out = Path(output_dir) / (Path(pdf_path).stem + '_output.pdf')
        # For CMYK mode, we need to save with special options
        if cmyk_mode:
            output_images[0].save(
                pdf_path_out, 
                save_all=True, 
                append_images=output_images[1:],
                resolution=300.0,
                quality=100,
                compression='tiff_lzw'
            )
        else:
            output_images[0].save(pdf_path_out, save_all=True, append_images=output_images[1:])
        print(f'Saved PDF {pdf_path_out}')

def main():
    parser = argparse.ArgumentParser(description='Convert PDF to image pages laid out in grid or masonry format.')
    parser.add_argument('input_pdf', help='Input PDF path')
    parser.add_argument('--layout', choices=['grid', 'masonry'], default='grid')
    parser.add_argument('--page-size', default='8.5x11')
    parser.add_argument('--page-orientation', choices=['portrait', 'landscape'], default='portrait')
    parser.add_argument('--image-fit-mode', choices=['uniform', 'rotate', 'scale'], default='uniform')
    parser.add_argument('--gap', type=int, default=10)
    parser.add_argument('--hairline-width', type=int, default=1)
    parser.add_argument('--hairline-color', default='black')
    parser.add_argument('--padding', type=int, default=5)
    parser.add_argument('--grid-rows', type=int)
    parser.add_argument('--grid-cols', type=int)
    parser.add_argument('--grid', type=str)
    parser.add_argument('--inner-margin', type=float, default=0.25)
    parser.add_argument('--outer-margin', type=float, default=0.5)
    parser.add_argument('--output-pdf', action='store_true')
    parser.add_argument('--flipbook-mode', action='store_true')
    parser.add_argument('--cmyk-mode', action='store_true', help='Output images in CMYK color mode')
    parser.add_argument('--cmyk-background', type=str, default='0,0,0,0', 
                      help='CMYK background color as C,M,Y,K values (0-255, comma-separated)')
    args = parser.parse_args()

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

    inner_margin_px = int(args.inner_margin * 300)
    outer_margin_px = int(args.outer_margin * 300)
    
    # Parse CMYK background color if provided
    cmyk_background = (0, 0, 0, 0)  # Default: no color (white)
    if args.cmyk_background:
        try:
            cmyk_values = [int(x.strip()) for x in args.cmyk_background.split(',')]
            if len(cmyk_values) == 4:
                cmyk_background = tuple(max(0, min(255, v)) for v in cmyk_values)  # Clamp to 0-255
            else:
                print("Warning: CMYK background must have 4 values. Using default.")
        except ValueError:
            print("Warning: Invalid CMYK values. Using default.")

    pdf_to_images(
        args.input_pdf, args.layout, page_size, args.gap, args.hairline_width,
        args.hairline_color, args.padding, args.page_orientation, args.image_fit_mode,
        grid_rows, grid_cols, inner_margin_px, outer_margin_px,
        args.output_pdf, args.flipbook_mode, args.cmyk_mode, cmyk_background
    )

if __name__ == '__main__':
    main()
