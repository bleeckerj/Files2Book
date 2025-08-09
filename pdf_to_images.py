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
                 is_flipbook=False, image_paths=None, cmyk_mode=False, cmyk_background=(0,0,0,0), rotate_to_aspect_ratio=False):
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

    # Position images within cells
    for idx in range(n):
        if idx >= len(images):
            break
        img = images[idx]
        max_w = cell_w - 2 * (padding + hairline_width)
        filename_space = 40
        max_h = cell_h - 2 * (padding + hairline_width) - filename_space
        if rotate_to_aspect_ratio:
            img_aspect = img.width / img.height
            cell_aspect = max_w / max_h if max_h > 0 else 1
            if (img_aspect > 1 and cell_aspect < 1) or (img_aspect < 1 and cell_aspect > 1):
                img = img.rotate(90, expand=True)
        img = fit_image(img, max_w, max_h, image_fit_mode, is_flipbook)

        col = idx % cols
        row = idx // cols
        x = offset_x + col * (cell_w + gap)
        y = offset_y + row * (cell_h + gap)

        if side == 'recto':
            img_x = x + (cell_w - img.width - 2 * (padding + hairline_width))
        else:
            img_x = x + padding + hairline_width
        img_y = y + padding + hairline_width

        page_img.paste(img, (img_x, img_y))
        draw_hairline_border(draw, (img_x, img_y, img_x + img.width - 1, img_y + img.height - 1), 
                           hairline_width, hairline_color)

        if image_paths and idx < len(image_paths):
            filename = os.path.basename(image_paths[idx])
            text_y = img_y + img.height + 5
            text_x = img_x + img.width // 2
            try:
                font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 30)
            except IOError:
                print("Using default font due to IOError")
                font = ImageFont.load_default()
            draw.text((text_x+1, text_y+1), filename, fill='gray', font=font, anchor="mt")
            draw.text((text_x, text_y), filename, fill='black', font=font, anchor="mt")

    return page_img

def arrange_masonry(images, page_size, n, gap, hairline_width, hairline_color, padding, 
                    image_fit_mode, inner_margin_px=0, outer_margin_px=0, 
                    side='recto', is_flipbook=False, image_paths=None, 
                    cmyk_mode=False, cmyk_background=(0,0,0,0), rotate_to_aspect_ratio=False,
                    masonry_cols=None):
    page_w, page_h = page_size
    left_margin = inner_margin_px if side == 'recto' else outer_margin_px
    right_margin = outer_margin_px if side == 'recto' else inner_margin_px

    # Create page and drawing context
    if cmyk_mode:
        page_img = create_cmyk_image(page_w, page_h, cmyk_background)
    else:
        page_img = Image.new('RGB', (page_w, page_h), 'white')
    draw = ImageDraw.Draw(page_img)

    # Usable dimensions
    usable_width = page_w - left_margin - right_margin
    if is_flipbook:
        usable_width = int(usable_width * 0.7)
    bottom_margin_px = int(0.14 * 300)
    content_h = page_h - inner_margin_px - outer_margin_px - bottom_margin_px

    # Columns
    cols = max(1, masonry_cols if masonry_cols else math.ceil(math.sqrt(n)))

    # Assign images to columns (round-robin) with original indices
    column_images = [[] for _ in range(cols)]
    for idx, img in enumerate(images[:n]):
        column_images[idx % cols].append((idx, img))

    # Vertical parameters
    filename_space_base = 40
    padline = padding + hairline_width

    # Compute global scale to fit tallest column
    s_candidates = []
    for col_imgs in column_images:
        m = len(col_imgs)
        if m == 0:
            continue
        sum_img_heights = sum(img.height for _, img in col_imgs)
        denom = sum_img_heights + (m - 1) * gap + m * filename_space_base
        numer = content_h - m * 2 * padline
        if denom <= 0:
            s_candidates.append(1.0)
        else:
            s_candidates.append(max(0.05, min(1.0, numer / denom)))
    global_scale = min(s_candidates) if s_candidates else 1.0

    # Column width to avoid horizontal overlap
    total_col_gaps = (cols - 1) * gap
    col_w = max(1, (usable_width - total_col_gaps) // cols)

    # Offsets
    grid_width = cols * col_w + (cols - 1) * gap
    if side == 'recto':
        offset_x = page_w - right_margin - grid_width
    else:
        offset_x = left_margin
    offset_y = inner_margin_px

    # Scaled spacing
    scaled_gap = max(0, int(round(gap * global_scale)))
    scaled_caption = max(0, int(round(filename_space_base * global_scale)))

    # Place images
    for col_idx, col_imgs in enumerate(column_images):
        y_offset = 0
        for img_idx, (orig_idx, img) in enumerate(col_imgs):
            # Width constraint inside the column
            inner_w_limit = max(1, col_w - 2 * padline)

            # Optionally rotate to better fit aspect
            if rotate_to_aspect_ratio and img.height > 0:
                img_aspect = img.width / img.height
                col_aspect = inner_w_limit / max(1, content_h)
                if (img_aspect > 1 and col_aspect < 1) or (img_aspect < 1 and col_aspect > 1):
                    img = img.rotate(90, expand=True)

            width_scale = min(1.0, inner_w_limit / max(1, img.width))
            final_scale = min(global_scale, width_scale)

            new_w = max(1, int(round(img.width * final_scale)))
            new_h = max(1, int(round(img.height * final_scale)))
            img_scaled = img if (new_w == img.width and new_h == img.height) else img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            x = offset_x + col_idx * (col_w + gap)
            y = offset_y + y_offset

            if side == 'recto':
                img_x = x + (col_w - img_scaled.width - 2 * padline)
            else:
                img_x = x + padline
            img_y = y + padline

            page_img.paste(img_scaled, (img_x, img_y))
            draw_hairline_border(draw, (img_x, img_y, img_x + img_scaled.width - 1, img_y + img_scaled.height - 1),
                                 hairline_width, hairline_color)

            if image_paths and 0 <= orig_idx < len(image_paths):
                filename = os.path.basename(image_paths[orig_idx])
                text_y = img_y + img_scaled.height + 5
                text_x = img_x + img_scaled.width // 2
                try:
                    font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 30)
                except IOError:
                    print("Using default font due to IOError")
                    font = ImageFont.load_default()
                draw.text((text_x+1, text_y+1), filename, fill='gray', font=font, anchor="mt")
                draw.text((text_x, text_y), filename, fill='black', font=font, anchor="mt")

            y_offset += img_scaled.height + 2 * padline + scaled_caption
            if img_idx < len(col_imgs) - 1:
                y_offset += scaled_gap

    return page_img

def pdf_to_images(pdf_path, layout, page_size, gap, hairline_width, hairline_color, 
                 padding, page_orientation, image_fit_mode, grid_rows=None, 
                 grid_cols=None, inner_margin_px=0, outer_margin_px=0, 
                 output_pdf=False, flipbook_mode=False, cmyk_mode=False, cmyk_background=(0,0,0,0),
                 rotate_to_aspect_ratio=False, masonry_cols=None):
    images = convert_from_path(pdf_path)
    # Rotate extracted PDF page images to match target page orientation if flag is set
    if rotate_to_aspect_ratio:
        page_w, page_h = page_size
        page_is_portrait = page_h >= page_w
        for i in range(len(images)):
            img = images[i]
            img_is_portrait = img.height >= img.width
            if page_is_portrait != img_is_portrait:
                images[i] = img.rotate(90, expand=True)
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
                                     is_flipbook=flipbook_mode, image_paths=None, cmyk_mode=cmyk_mode, 
                                     cmyk_background=cmyk_background, rotate_to_aspect_ratio=rotate_to_aspect_ratio)
        else:
            page_img = arrange_masonry(chunk, page_size, len(chunk), gap, hairline_width, 
                                       hairline_color, padding, image_fit_mode, 
                                       inner_margin_px, outer_margin_px, side, 
                                       is_flipbook=flipbook_mode, image_paths=None, cmyk_mode=cmyk_mode, 
                                       cmyk_background=cmyk_background, rotate_to_aspect_ratio=rotate_to_aspect_ratio,
                                       masonry_cols=masonry_cols)

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
    parser = argparse.ArgumentParser(description='Convert PDF to image pages laid out in grid or masonry format.')
    parser.add_argument('--rotate-to-aspect-ratio', action='store_true', help='Rotate images to match cell/page aspect ratio')
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
    parser.add_argument('--masonry-cols', type=int, help='Number of columns in masonry layout')
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

    rotate_to_aspect_ratio = args.rotate_to_aspect_ratio

    pdf_to_images(
        args.input_pdf, args.layout, page_size, args.gap, args.hairline_width,
        args.hairline_color, args.padding, args.page_orientation, args.image_fit_mode,
        grid_rows, grid_cols, inner_margin_px, outer_margin_px,
        args.output_pdf, args.flipbook_mode, args.cmyk_mode, cmyk_background,
        rotate_to_aspect_ratio=rotate_to_aspect_ratio, masonry_cols=args.masonry_cols
    )

if __name__ == '__main__':
    main()
