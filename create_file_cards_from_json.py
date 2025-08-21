#!/usr/bin/env python3

import os
import sys
import re
import json
import logging
import shutil
import time
import hashlib
from pathlib import Path
from datetime import datetime
import argparse
from file_card_generator import create_file_info_card, determine_file_type, save_card_as_tiff
from create_file_cards import parse_page_size, _decode_metadata_text, assemble_cards_to_pdf

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s - %(name)s %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
)

logging.getLogger("file_card_generator").setLevel(logging.INFO)


def short_hash(s, length=8):
    return hashlib.md5(s.encode('utf-8')).hexdigest()[:length]

def build_file_cards_from_json(
    json_path,
    image_base_dir,
    output_dir='file_card_tests',
    cmyk_mode=False,
    page_size='LARGE_TAROT',
    exclude_file_path=False,
    border_color=(250, 250, 250),
    border_inch_width=0.125,
    include_video_frames=False,
    metadata_text=None,
    cards_per_chunk=0
):
    logging.info(f"Starting file card generation from JSON: {json_path}")
    is_stories = False
    is_other_media = False
    output_path = Path(output_dir)
    if output_path.exists():
        shutil.rmtree(output_path)
        time.sleep(5)
    output_path.mkdir(exist_ok=True, parents=True)
    width, height = parse_page_size(page_size)
    logging.info(f"Parsed page size: {page_size} -> {width}x{height} pixels")
    # if the filename is like 'stories.json' or similar, then just note that
    json_path_obj = Path(json_path)
    if "stories" in json_path_obj.stem:
        is_stories = True
        logging.info("Detected 'stories' in JSON filename.")
    if "posts" in json_path_obj.stem:
        is_stories = False
        logging.info("Detected 'posts' in JSON filename.")
    if "ig_other_media" in json_path_obj.stem:
        is_stories = False
        is_other_media = True
        logging.info("Detected 'ig_other_media' in JSON filename.")

    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "ig_stories" in data:
        posts = data["ig_stories"]
        logging.info(f"Loaded {len(posts)} stories from {json_path}")
    elif isinstance(data, dict) and "ig_other_media" in data:
        posts = data["ig_other_media"]
        logging.info(f"Loaded {len(posts)} ig other media from {json_path}")
    else:
        posts = data
        logging.info(f"Loaded {len(posts)} posts from {json_path}")

    # Sort posts by creation_timestamp (earliest to most recent)
    posts = sorted(posts, key=lambda post: post.get("creation_timestamp", 0))

    file_count = 0
    media_idx = 0
    chunk_idx = 0
    chunk_dir = output_path
    for post in posts:
        # Regular Stories JSON
        media_idx = 0
        if is_stories:
            uri = post.get("uri")
            title = post.get("title", "")
            creation_ts = post.get("creation_timestamp")
            if not uri:
                logging.warning("Skipping media with missing 'uri'")
                continue
            if uri.startswith('http://') or uri.startswith('https://'):
                logging.warning(f"Skipping URI that looks like a URL, not a file: {uri}")
                continue
            # Construct absolute image path
            abs_file_path = str(Path(image_base_dir) / uri)
            if not Path(abs_file_path).is_file():
                logging.warning(f"Image file does not exist: {abs_file_path}")
                continue
            # Format metadata_text
            metadata_text = concat_timestamp_title(creation_ts, title)
            human_readable_date = datetime.fromtimestamp(creation_ts).strftime('%Y-%m-%d %H:%M:%S') if creation_ts else None
            try:
                card = create_file_info_card(
                    abs_file_path,
                    width=width,
                    height=height,
                    cmyk_mode=cmyk_mode,
                    exclude_file_path=exclude_file_path,
                    border_color=border_color,
                    border_inch_width=border_inch_width,
                    include_video_frames=include_video_frames,
                    metadata_text=metadata_text,
                    title=human_readable_date
                )
                if isinstance(card, list):
                    for idx, img in enumerate(card):
                        short_path = short_hash(abs_file_path)
                        # Chunking logic
                        if cards_per_chunk and cards_per_chunk > 0:
                            if file_count % cards_per_chunk == 0:
                                chunk_idx = file_count // cards_per_chunk
                                chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                                chunk_dir.mkdir(exist_ok=True, parents=True)
                            output_file = chunk_dir / f"{creation_ts}_{media_idx:04d}_{short_path}_card_{idx+1}.tiff"
                        else:
                            output_file = output_path / f"{creation_ts}_{media_idx:04d}_{short_path}_card_{idx+1}.tiff"
                        save_card_as_tiff(img, output_file, cmyk_mode=cmyk_mode)
                        media_idx += 1
                        file_count += 1
                else:
                    short_path = short_hash(abs_file_path)
                    if cards_per_chunk and cards_per_chunk > 0:
                        if file_count % cards_per_chunk == 0:
                            chunk_idx = file_count // cards_per_chunk
                            chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                            chunk_dir.mkdir(exist_ok=True, parents=True)
                        output_file = chunk_dir / f"{creation_ts}_{short_path}_card.tiff"
                    else:
                        output_file = output_path / f"{creation_ts}_{short_path}_card.tiff"
                    save_card_as_tiff(card, output_file, cmyk_mode=cmyk_mode)
                    logging.debug(f"Saved card to {output_file}")
                    file_count += 1
                # After saving each card, check if chunk is full
                if cards_per_chunk and cards_per_chunk > 0 and file_count % cards_per_chunk == 0:
                    pdf_name_chunk = f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                    pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                    logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                    assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height))
                    logging.info(f"Saved chunk PDF: {pdf_path_chunk}")
                    # Delete images in chunk_dir
                    for card_file in chunk_dir.glob("*_card.*"):
                        try:
                            card_file.unlink()
                        except Exception as e:
                            logging.error(f"Error deleting {card_file}: {e}")
                    logging.info(f"Deleted images in {chunk_dir}")
                    chunk_idx += 1
            except Exception as e:
                logging.error(f"Error processing {abs_file_path}: {e}")
        
        # Regular Post JSON        
        else:
            media_list = post.get("media", [])
            for media in media_list:
                uri = media.get("uri")
                
                title = media.get("title", "")
                if not title:
                    title = post.get("title", "")            
                
                creation_ts = media.get("creation_timestamp")
                if not uri:
                    logging.warning("Skipping media with missing 'uri'")
                    continue
                
                if uri.startswith('http://') or uri.startswith('https://'):
                    logging.warning(f"Skipping URI that looks like a URL, not a file: {uri}")
                    continue

                # Construct absolute image path
                abs_file_path = str(Path(image_base_dir) / uri)
                if not Path(abs_file_path).is_file():
                    logging.warning(f"Image file does not exist: {abs_file_path}")
                    continue

                # Format metadata_text
                metadata_text = concat_timestamp_title(creation_ts, title)
                human_readable_date = datetime.fromtimestamp(creation_ts).strftime('%Y-%m-%d %H:%M:%S') if creation_ts else None
                try:
                    card = create_file_info_card(
                        abs_file_path,
                        width=width,
                        height=height,
                        cmyk_mode=cmyk_mode,
                        exclude_file_path=exclude_file_path,
                        border_color=border_color,
                        border_inch_width=border_inch_width,
                        include_video_frames=include_video_frames,
                        metadata_text=metadata_text,
                        title=human_readable_date
                    )
                    short_path = short_hash(abs_file_path)
                    if cards_per_chunk and cards_per_chunk > 0:
                        if file_count % cards_per_chunk == 0:
                            chunk_idx = file_count // cards_per_chunk
                            chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                            chunk_dir.mkdir(exist_ok=True, parents=True)
                        output_file = chunk_dir / f"{creation_ts}_{media_idx:04d}_{short_path}_card.tiff"
                    else:
                        output_file = output_path / f"{creation_ts}_{media_idx:04d}_{short_path}_card.tiff"
                    save_card_as_tiff(card, output_file, cmyk_mode=cmyk_mode)
                    logging.debug(f"Saved card to {output_file}")
                    file_count += 1
                    media_idx += 1
                except Exception as e:
                    logging.error(f"Error processing {abs_file_path}: {e}")
            if cards_per_chunk and cards_per_chunk > 0 and file_count % cards_per_chunk == 0:
                pdf_name_chunk = f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height))
                logging.info(f"Saved chunk PDF: {pdf_path_chunk}")
                for card_file in chunk_dir.glob("*_card.*"):
                    try:
                        card_file.unlink()
                    except Exception as e:
                        logging.error(f"Error deleting {card_file}: {e}")
                logging.info(f"Deleted images in {chunk_dir}")
                chunk_idx += 1

    logging.info(f"Processing complete. Generated {file_count} file cards in {output_path}")

def concat_timestamp_title(creation_timestamp, title):
    if creation_timestamp:
        # Convert to human-readable date string
        try:
            readable_date = datetime.fromtimestamp(creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            readable_date = str(creation_timestamp)
        if title is not None and title != '':
            return f"{readable_date}\n{title}"
        return f"{readable_date}"
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate file cards from a JSON file and assemble into a PDF')
    parser.add_argument('--input-json', required=True, help='Path to the input JSON file')
    parser.add_argument('--image-base-dir', required=True, help='Base directory for image files referenced in the JSON')
    parser.add_argument('--output-dir', help='Directory to save card images')
    parser.add_argument('--cmyk-mode', action='store_true', help='Generate cards in CMYK mode')
    parser.add_argument('--page-size', default='LARGE_TAROT', help='Page size (A4, LETTER, TABLOID, WxH in inches)')
    parser.add_argument('--pdf-output-name', help='Path to save the combined PDF')
    parser.add_argument('--delete-cards-after-pdf', action='store_true', help='Delete individual card files after PDF is created')
    parser.add_argument('--border-color', default='250,250,250', help='Border color for the cards in RGB format (default: 250,250,250)')
    parser.add_argument('--border-inch-width', type=float, default=0.125, help='Border width in inches (default: 0.125)')
    parser.add_argument('--include-video-frames', action='store_true', help='Also output individual video frames as cards (default: overview only)')
    parser.add_argument('--exclude-file-path', default=False, action='store_true', help='Exclude the vertical file path from the card (default: shown)')  # <-- Add this back
    parser.add_argument('--cards-per-chunk', type=int, default=0, help='If >0, split card images into chunked folders of this many cards and produce one PDF per chunk')

    args = parser.parse_args()
    logging.info(f"Arguments: {args}")

    # Set up output directory
    input_json_name = os.path.basename(os.path.normpath(args.input_json)).replace('.json', '')
    if not args.output_dir:
        args.output_dir = f"{input_json_name}_{args.page_size}"
        logging.info(f"Using default output directory: {args.output_dir}")
    else:
        args.output_dir = f"{args.output_dir}/{args.page_size}"

    output_path_obj = Path(args.output_dir)
    output_dir_name = output_path_obj.name

    # Determine the PDF path
    if not args.pdf_output_name:
        pdf_name = f"{input_json_name}_combined_{args.page_size}.pdf"
        logging.info(f"No PDF output name provided, using default: {pdf_name}")
    elif args.pdf_output_name.endswith('.pdf'):
        tmp_name = args.pdf_output_name.rsplit('.', 1)[0]
        pdf_name = f"{tmp_name}_combined_{args.page_size}.pdf"
    else:
        pdf_name = f"{args.pdf_output_name}_combined_{args.page_size}.pdf"

    pdf_path = str(output_path_obj / pdf_name)
    logging.info(f"PDF Name will be {pdf_name}")
    logging.info(f"PDF will be saved at: {pdf_path}")

    # pick the border color from the command line
    border_color_parts = re.split(r'[,\s]+', args.border_color.strip())
    t_border_color = tuple(map(int, border_color_parts))

    # Generate file cards from JSON (assume function exists: build_file_cards_from_json)
    build_file_cards_from_json(
        args.input_json,
        args.image_base_dir,
        args.output_dir,
        args.cmyk_mode,
        args.page_size,
        exclude_file_path=args.exclude_file_path,
        border_color=t_border_color,
        border_inch_width=args.border_inch_width,
        include_video_frames=args.include_video_frames,
        cards_per_chunk=args.cards_per_chunk
    )

    # Assemble cards into a PDF
    logging.info(f"Assembling cards into PDF: {pdf_name}")
    width, height = parse_page_size(args.page_size)
    assemble_cards_to_pdf(args.output_dir, pdf_path, (width, height))

    # Delete individual card files if requested
    if args.delete_cards_after_pdf:
        logging.info("Deleting individual card files after PDF creation...")
        output_dir_path = Path(args.output_dir)
        delete_patterns = ["*_card.*", "*_card_*.*"]
        deleted = 0
        for pattern in delete_patterns:
            for card_file in output_dir_path.glob(pattern):
                if Path(card_file).resolve() == Path(pdf_path).resolve():
                    continue
                try:
                    card_file.unlink()
                    deleted += 1
                    logging.debug(f"Deleted: {card_file}")
                except Exception as e:
                    logging.error(f"Error deleting {card_file}: {e}")
        logging.info(f"Card files cleanup complete. Deleted {deleted} files.")

