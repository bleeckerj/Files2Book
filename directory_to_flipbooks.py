import logging
import sys
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import argparse
import math
import cv2
import numpy as np
import os
import traceback

from pdf_to_images import (
    parse_page_size,
    draw_hairline_border,
    create_cmyk_image,
)
from file_card_generator import (
    create_file_info_card,
    determine_file_type
)

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.heic'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}

try:
    import pillow_heif
    PILLOW_HEIF_AVAILABLE = True
except ImportError:
    PILLOW_HEIF_AVAILABLE = False

def get_parent_of_parent_name(input_dir):
    input_path = Path(input_dir).resolve()
    return input_path.parent.name.replace(' ', '_')

def load_images_from_dir(input_dir, flipbook_mode=False, video_fps=1, exclude_video_stills=False, 
                        handle_non_visual=True, cmyk_mode=False):
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise ValueError(f'Input path {input_dir} is not a directory')
    images = []
    image_paths = []
    video_frames_map = {}
    for file_path in sorted(input_path.iterdir()):
        file_type = determine_file_type(file_path)
        ext = file_path.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            if ext == '.heic':
                if PILLOW_HEIF_AVAILABLE:
                    try:
                        heif_file = pillow_heif.open_heif(str(file_path))
                        img = Image.frombytes(
                            heif_file.mode,
                            heif_file.size,
                            heif_file.data,
                            "raw"
                        ).convert('RGB')
                        images.append(img)
                        image_paths.append(str(file_path))
                    except Exception as e:
                        print(f"Error loading HEIC image {file_path}: {e}")
                else:
                    print(f"pillow-heif not available, skipping HEIC image: {file_path}")
            else:
                img = Image.open(file_path).convert('RGB')
                images.append(img)
                image_paths.append(str(file_path))
        elif ext == '.pdf':
            pdf_images = convert_from_path(str(file_path))
            images.extend(pdf_images)
            image_paths.extend([f"{file_path} (Page {i+1})" for i in range(len(pdf_images))])
        elif ext in VIDEO_EXTENSIONS:
            video_name = file_path.stem.replace(' ', '_')
            if flipbook_mode:
                frames = extract_frames_from_video_fps(file_path, video_fps)
                video_frames_map[video_name] = frames
    return images, video_frames_map, image_paths

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

def create_blank_page(page_size, color='white', cmyk_mode=False, cmyk_color=(0, 0, 0, 0)):
    if cmyk_mode:
        return create_cmyk_image(page_size[0], page_size[1], cmyk_color)
    else:
        return Image.new('RGB', page_size, color)

def create_flipbooks_only(video_frames_map, page_size, hairline_width, hairline_color, cmyk_mode, cmyk_background, cmyk_flipbook_background, output_pdf, output_dir, parent_prefix):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    for video_name, frames in video_frames_map.items():
        flipbook_dir = output_dir / f'{parent_prefix}' / f'{parent_prefix}_flipbook_{video_name}'
        flipbook_dir.mkdir(parents=True, exist_ok=True)
        video_output_images = []
        page_counter = 1
        for idx, img in enumerate(frames):
            if page_counter % 2 == 0:
                blank_page = create_cmyk_image(page_size[0], page_size[1], cmyk_flipbook_background)
                video_output_images.append(blank_page)
                if cmyk_mode:
                    output_path = flipbook_dir / f'{video_name}_flipbook_frame_{page_counter:03d}_blank.tiff'
                    blank_page.save(output_path, compression='tiff_lzw')
                else:
                    output_path = flipbook_dir / f'{video_name}_flipbook_frame_{page_counter:03d}_blank.png'
                    blank_page.save(output_path)
                page_counter += 1
            if cmyk_mode:
                page_img = create_cmyk_image(page_size[0], page_size[1], cmyk_background)
            else:
                page_img = Image.new('RGB', page_size, 'white')
            img = img.copy()
            max_width = int(page_size[0] * 0.7)
            max_height = page_size[1]
            original_width, original_height = img.width, img.height
            scale_factor = min(max_width / original_width, max_height / original_height)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            margin_flip = int(0.1 * 300.0)
            x = page_size[0] - img.width - margin_flip
            y = (page_size[1] - img.height) // 2
            page_img.paste(img, (x, y))
            border_xy = (x, y, x + img.width - 1, y + img.height - 1)
            draw = ImageDraw.Draw(page_img)
            draw_hairline_border(draw, border_xy, hairline_width, hairline_color)
            video_output_images.append(page_img)
            if cmyk_mode:
                output_path = flipbook_dir / f'{video_name}_flipbook_frame_{page_counter:03d}.tiff'
                page_img.save(output_path, compression='tiff_lzw')
            else:
                output_path = flipbook_dir / f'{video_name}_flipbook_frame_{page_counter:03d}.png'
                page_img.save(output_path)
            page_counter += 1
        if output_pdf and video_output_images:
            pdf_path_out = flipbook_dir / f'{video_name}_flipbook.pdf'
            if cmyk_mode:
                video_output_images[0].save(
                    pdf_path_out, 
                    save_all=True, 
                    append_images=video_output_images[1:],
                    resolution=300.0,
                    quality=100,
                    compression='tiff_lzw'
                )
            else:
                video_output_images[0].save(
                    pdf_path_out, 
                    save_all=True, 
                    append_images=video_output_images[1:]
                )
            logging.info(f'Saved PDF {pdf_path_out}')

def parse_inches_to_pixels(value_in_inches):
    return int(value_in_inches * 300)

def main():
    parser = argparse.ArgumentParser(description='Create flipbooks from videos in a directory.')
    parser.add_argument('input_dir', help='Path to input directory containing images and videos')
    parser.add_argument('--page-size', default='8.5x11', help='Page size (e.g. 8.5x11, A4, ANSI A)')
    parser.add_argument('--page-orientation', choices=['portrait', 'landscape'], default='portrait', help='Page orientation')
    parser.add_argument('--hairline-width', type=float, default=0.0033, help='Width of hairline border in inches (default: 0.0033 inches, approx 1 pixel)')
    parser.add_argument('--hairline-color', default='black', help='Color of hairline border')
    parser.add_argument('--video-fps', type=int, default=1, help='Frames per second to extract from videos in flipbook mode')
    parser.add_argument('--output-pdf', action='store_true', default=True,help='Generate a PDF of the flipbook pages. Default is True.')
    parser.add_argument('--output-dir', default=None, help='Directory to save output flipbook pages (default: <parent_of_parent>_flipbook_pages)')
    parser.add_argument('--cmyk-mode', action='store_true', help='Output images in CMYK color mode')
    parser.add_argument('--cmyk-background', type=str, default='0,0,0,0', 
                   help='CMYK background color as C,M,Y,K values (0-255, comma-separated)')
    parser.add_argument('--cmyk-flipbook-background', type=str, default='22,0,93,0', 
                   help='CMYK background color for flipbook pages as C,M,Y,K values (0-255, comma-separated) default is 22,0,93,0 which is Omata acid color')
    args = parser.parse_args()
    try:
        page_size = parse_page_size(args.page_size, args.page_orientation)
    except ValueError as e:
        print(e)
        sys.exit(1)
    hairline_width_px = parse_inches_to_pixels(args.hairline_width)
    parent_dir_name = get_parent_of_parent_name(args.input_dir)
    script_dir = Path(__file__).parent.resolve()
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = str(script_dir / f'{parent_dir_name}_flipbook_pages')
    logging.info(f'Output directory: {output_dir}')
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    cmyk_background = (0, 0, 0, 0)
    if args.cmyk_mode and args.cmyk_background:
        try:
            cmyk_values = [int(x.strip()) for x in args.cmyk_background.split(',')]
            if len(cmyk_values) == 4:
                cmyk_background = tuple(max(0, min(255, v)) for v in cmyk_values)
            else:
                print("Warning: CMYK background must have 4 values. Using default.")
        except ValueError:
            print("Warning: Invalid CMYK values. Using default.")
    cmyk_flipbook_background = (22, 0, 93, 0)
    if args.cmyk_flipbook_background:
        try:
            cmyk_flipbook_values = [int(x.strip()) for x in args.cmyk_flipbook_background.split(',')]
            if len(cmyk_flipbook_values) == 4:
                cmyk_flipbook_background = tuple(max(0, min(255, v)) for v in cmyk_flipbook_values)
            else:
                print("Warning: CMYK flipbook background must have 4 values. Using default.")
        except ValueError:
            print("Warning: Invalid CMYK flipbook background values. Using default.")
    try:
        images, video_frames_map, image_paths = load_images_from_dir(
            args.input_dir, 
            flipbook_mode=True, 
            video_fps=args.video_fps,
            exclude_video_stills=True,
            handle_non_visual=False,
            cmyk_mode=args.cmyk_mode
        )
        if not video_frames_map:
            print('No videos found for flipbook creation in the input directory.')
            sys.exit(1)
        create_flipbooks_only(
            video_frames_map, page_size, hairline_width_px, args.hairline_color, args.cmyk_mode, cmyk_background, cmyk_flipbook_background, args.output_pdf, output_dir, parent_dir_name
        )
    except Exception as e:
        logging.error(f'Error processing flipbooks: {e}', exc_info=True)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
