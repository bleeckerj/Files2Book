import sys
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import argparse
import math
import cv2
import numpy as np
import os

from pdf_to_images import (
    parse_page_size,
    arrange_grid,
    arrange_masonry,
    fit_image,
    draw_hairline_border,
)

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}


def get_parent_of_parent_name(input_dir):
    input_path = Path(input_dir).resolve()
    return input_path.parent.name.replace(' ', '_')


def load_images_from_dir(input_dir, flipbook_mode=False, video_fps=1, exclude_video_stills=False):
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise ValueError(f'Input path {input_dir} is not a directory')

    images = []
    video_frames_map = {}  # video_name -> list of frames
    frame_index = 0

    for file_path in sorted(input_path.iterdir()):
        ext = file_path.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            img = Image.open(file_path).convert('RGB')
            images.append(img)
        elif ext == '.pdf':
            pdf_images = convert_from_path(str(file_path))
            images.extend(pdf_images)
        elif ext in VIDEO_EXTENSIONS:
            video_name = file_path.stem.replace(' ', '_')
            if flipbook_mode:
                frames = extract_frames_from_video_fps(file_path, video_fps)
                # Only add frames to main images list if not excluding video stills
                if not exclude_video_stills:
                    images.extend(frames)
                # Always add to video_frames_map for flipbook generation
                video_frames_map[video_name] = frames
            elif not exclude_video_stills:
                # Only add video frames if not excluding them
                frames = extract_frames_from_video(file_path, num_frames=12)
                images.extend(frames)
    
    return images, video_frames_map


def extract_frames_from_video(video_path, num_frames=12):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Warning: Cannot open video file {video_path}")
        return []
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count == 0:
        cap.release()
        return []
    interval = max(frame_count // num_frames, 1)
    frames = []
    for i in range(num_frames):
        frame_no = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        frames.append(pil_img)
    cap.release()
    return frames


def extract_frames_from_video_fps(video_path, fps=1):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Warning: Cannot open video file {video_path}")
        return []
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / video_fps if video_fps > 0 else 0
    if duration == 0:
        cap.release()
        return []
    total_frames_to_extract = int(duration * fps)
    if total_frames_to_extract == 0:
        total_frames_to_extract = 1
    interval = max(frame_count // total_frames_to_extract, 1)
    frames = []
    for i in range(total_frames_to_extract):
        frame_no = i * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        frames.append(pil_img)
    cap.release()
    return frames


def create_blank_page(page_size, color='white'):
    return Image.new('RGB', page_size, color)


def images_to_pages(images, layout, page_size, gap, hairline_width, hairline_color, padding,
                    image_fit_mode, grid_rows=None, grid_cols=None, page_margin=0, output_pdf=False,
                    output_dir='output_pages', flipbook_mode=False, video_frames_map=None, parent_prefix='output',
                    image_paths=None):
    
    # Convert output_dir to a Path object if it's a string
    output_dir = Path(output_dir)
    
    # Create the output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # If image_paths isn't provided, create dummy paths
    if image_paths is None:
        image_paths = []
        for idx, img in enumerate(images):
            if hasattr(img, 'filename') and img.filename:
                image_paths.append(img.filename)
            else:
                image_paths.append(f"image_{idx+1}")
    
    # Flipbook pages per video
    if flipbook_mode and video_frames_map:
        for video_name, frames in video_frames_map.items():
            flipbook_dir = output_dir / f'flipbook_{video_name}'
            flipbook_dir.mkdir(exist_ok=True)
            video_output_images = []
            for idx, img in enumerate(frames):
                page_img = Image.new('RGB', page_size, 'white')
                img = img.copy()
                
                # Calculate 70% of page width
                max_width = int(page_size[0] * 0.7)
                max_height = page_size[1]
                
                # Scale the image to fit within 70% of page width
                original_width, original_height = img.width, img.height
                scale_factor = min(max_width / original_width, max_height / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Position image at right side
                margin_flip = int(0.1 * 300.0)  # Convert inches to pixels
                x = page_size[0] - img.width - margin_flip
                y = (page_size[1] - img.height) // 2
                
                page_img.paste(img, (x, y))
                border_xy = (x, y, x + img.width - 1, y + img.height - 1)
                draw = ImageDraw.Draw(page_img)
                draw_hairline_border(draw, border_xy, hairline_width, hairline_color)
                video_output_images.append(page_img)
                output_path = flipbook_dir / f'{video_name}_flipbook_frame_{idx + 1:03d}.png'
                page_img.save(output_path)
                print(f'Saved flipbook page {output_path}')
            if output_pdf and video_output_images:
                pdf_path_out = flipbook_dir / f'{video_name}_flipbook.pdf'
                video_output_images[0].save(pdf_path_out, save_all=True, append_images=video_output_images[1:])
                print(f'Saved PDF {pdf_path_out}')

    # Generate standard pages for all images
    chunk_size = (grid_rows or 2) * (grid_cols or 2)
    output_images = []  # Collect page images for PDF output
    for i in range(0, len(images), chunk_size):
        chunk = images[i:i + (chunk_size or len(images))]
        page_num = i // (chunk_size or len(images)) + 1
        side = 'recto' if page_num % 2 == 1 else 'verso'
        if layout == 'grid':
            page_img = arrange_grid(chunk, page_size, len(chunk), gap, hairline_width, hairline_color,
                                    padding, image_fit_mode, grid_rows, grid_cols, page_margin, 
                                    side=side, is_flipbook=flipbook_mode, image_paths=image_paths[i:i+chunk_size])
        else:
            page_img = arrange_masonry(chunk, page_size, len(chunk), gap, hairline_width, hairline_color,
                                       padding, image_fit_mode, page_margin, side=side)
        filename = f'{parent_prefix}_output_page_{page_num:03d}.png'
        output_path = output_dir / filename
        page_img.save(output_path)
        output_images.append(page_img)
        print(f'Saved {output_path}')
    if output_pdf and output_images:
        pdf_path_out = output_dir / f'{parent_prefix}_output_combined.pdf'
        output_images[0].save(pdf_path_out, save_all=True, append_images=output_images[1:])
        print(f'Saved PDF {pdf_path_out}')


def parse_inches_to_pixels(value_in_inches):
    return int(value_in_inches * 300)


def main():
    parser = argparse.ArgumentParser(description='Convert directory of images and PDFs into pages of images arranged in grid or masonry layout.')
    parser.add_argument('input_dir', help='Path to input directory containing images and PDFs')
    parser.add_argument('--layout', choices=['grid', 'masonry'], default='grid', help='Layout style')
    parser.add_argument('--page-size', default='8.5x11', help='Page size (e.g. 8.5x11, A4, ANSI A)')
    parser.add_argument('--page-orientation', choices=['portrait', 'landscape'], default='portrait', help='Page orientation')
    parser.add_argument('--image-fit-mode', choices=['uniform', 'rotate', 'scale'], default='uniform', help='Image fit mode')
    parser.add_argument('--gap', type=float, default=0.0333, help='Gap between images in inches (default: 0.0333 inches, approx 10 pixels)')
    parser.add_argument('--hairline-width', type=float, default=0.0033, help='Width of hairline border in inches (default: 0.0033 inches, approx 1 pixel)')
    parser.add_argument('--hairline-color', default='black', help='Color of hairline border')
    parser.add_argument('--padding', type=float, default=0.0167, help='Padding between image and hairline border in inches (default: 0.0167 inches, approx 5 pixels)')
    parser.add_argument('--grid-rows', type=int, help='Number of rows in grid layout')
    parser.add_argument('--grid-cols', type=int, help='Number of columns in grid layout')
    parser.add_argument('--grid', type=str, help='Grid size shorthand as ROWSxCOLS, e.g. 2x3')
    parser.add_argument('--page-margin', type=float, default=0.25, help='Page margin in inches')
    parser.add_argument('--output-pdf', action='store_true', help='Generate a PDF of the output pages')
    parser.add_argument('--output-dir', default=None, help='Directory to save output pages (default: <parent_of_parent>_output_pages)')
    parser.add_argument('--flipbook-mode', action='store_true', help='Enable flipbook layout for videos')
    parser.add_argument('--video-fps', type=int, default=1, help='Frames per second to extract from videos in flipbook mode')
    parser.add_argument('--exclude-video-stills', action='store_true',
                   help='Exclude video frames from standard grid pages (but keep flipbook pages if enabled)')
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
    page_margin_px = int(args.page_margin * 300)  # Convert inches to pixels

    # Convert inches to pixels for padding, gap, hairline_width
    padding_px = parse_inches_to_pixels(args.padding)
    gap_px = parse_inches_to_pixels(args.gap)
    hairline_width_px = parse_inches_to_pixels(args.hairline_width)

    # Set output directory based on parent of parent directory
    parent_dir_name = get_parent_of_parent_name(args.input_dir)
    script_dir = Path(__file__).parent.resolve()
    output_dir = args.output_dir or str(script_dir / f'{parent_dir_name}_output_pages')

    try:
        # Get images and video frames from the main loader function
        images, video_frames_map = load_images_from_dir(
            args.input_dir, 
            flipbook_mode=args.flipbook_mode, 
            video_fps=args.video_fps,
            exclude_video_stills=args.exclude_video_stills
        )

        # Create image_paths list matching ONLY the images that were actually loaded
        image_paths = []
        for file_path in sorted(Path(args.input_dir).glob('*')):
            ext = file_path.suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                image_paths.append(str(file_path))
            elif ext == '.pdf':
                pdf_images = convert_from_path(str(file_path))
                image_paths.extend([f"{file_path} (Page {i+1})" for i in range(len(pdf_images))])

        if not images:
            print('No images or PDFs found in the input directory.')
            sys.exit(1)

        # Process the images
        images_to_pages(
            images, args.layout, page_size, gap_px, hairline_width_px,
            args.hairline_color, padding_px, args.image_fit_mode,
            grid_rows, grid_cols, page_margin_px, args.output_pdf,
            output_dir, args.flipbook_mode, video_frames_map, parent_dir_name,
            image_paths=image_paths
        )

    except Exception as e:
        print(f'Error processing images: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
