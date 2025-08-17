#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from PIL import Image
import argparse
from fpdf import FPDF
import logging
import time
import shutil
import itertools
import traceback
import img2pdf
import re
    
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s - %(name)s %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
)
# Import the file card generator
from file_card_generator import create_file_info_card, determine_file_type, save_card_as_tiff

def parse_page_size(size_name):
    # Returns (width, height) in pixels at 300dpi
    size_name = size_name.upper()
    dpi = 300
    sizes = {
        'A5': (5.83, 8.27),
        'A4': (8.27, 11.69),
        'A3': (11.69, 16.54),
        'A2': (16.54, 23.39),
        'A1': (23.39, 33.11),
        'A0': (33.11, 46.81),
        'TRADE_LARGE': (7, 9),
        'LETTER': (8.5, 11),
        'LEGAL': (8.5, 14),
        'TABLOID': (11, 17),
        'DIGEST': (5.5, 8.5),         # Digest size
        'POCKETBOOK': (4.25, 6.87),   # PocketBook size
        # Playing card sizes (in inches, rounded to 2 decimals)
        'POKER': (2.48, 3.46),        # 63x88mm
        'BRIDGE': (2.24, 3.46),       # 57x88mm
        'MINI': (1.73, 2.68),         # 44x68mm
        'LARGE_TAROT': (2.76, 4.72),  # 70x120mm
        'SMALL_TAROT': (2.76, 4.25),  # 70x108mm
        'LARGE_SQUARE': (2.76, 2.76), # 70x70mm
        'SMALL_SQUARE': (2.48, 2.48), # 63x63mm
    }
    logging.debug(f"Parsing page size: {size_name}")
    if size_name in sizes:
        w_in, h_in = sizes[size_name]
        logging.info(f"Using predefined size: {size_name} -> {w_in}x{h_in} inches")
        logging.info(f"Converted to pixels at {dpi} dpi: {int(w_in * dpi)}x{int(h_in * dpi)}")
        return int(w_in * dpi), int(h_in * dpi)
    # fallback: try WxH format in inches
    if 'X' in size_name:
        try:
            w_in, h_in = map(float, size_name.split('X'))
            return int(w_in * dpi), int(h_in * dpi)
        except Exception:
            pass
    # Default to A4
    logging.warning(f"Unknown page size '{size_name}', defaulting to A5")
    w_in, h_in = sizes['A5']
    logging.warning(f"A5 size: {w_in}x{h_in} inches")
    return int(w_in * dpi), int(h_in * dpi)

def build_file_cards_from_directory(
    input_dir,
    output_dir='file_card_tests',
    cmyk_mode=False,
    page_size='LARGE_TAROT',
    exclude_file_path=False,
    border_color=(250, 250, 250),
    border_inch_width=0.125,
    include_video_frames=False,
    max_depth=0,  # 0 = no recursion; negative => unlimited
    metadata_text=None
):
    """
    Test the file card generation by creating cards for all files in a directory.
    
    Args:
        input_dir: Directory containing files to process
        output_dir: Directory to save the generated card images
        cmyk_mode: Whether to use CMYK mode for the cards
        page_size: Page size for the cards (default is LARGE_TAROT)
        exclude_file_path: Exclude the vertical file path label
        border_color: RGB tuple for border color
        border_inch_width: Border width in inches
        include_video_frames: Also output individual video frames as cards
        max_depth: Maximum folder recursion depth; 0 = no recursion, negative = unlimited
        metadata_text: Custom metadata text to include on the card
    """
    logging.info(f"Starting file card with size {page_size}")
    input_path = Path(input_dir)
    # Normalize max_depth
    if isinstance(max_depth, int) and max_depth < 0:
        max_depth = None
    logging.info(f"Input directory: {input_path}")
    logging.info(f"Output directory: {output_dir}")
    output_path = Path(output_dir)
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(exist_ok=True, parents=True)
    width, height = parse_page_size(page_size)
    logging.debug(f"page_size: {page_size} width: {width} height: {height}")

    logging.debug(f"Parsed page size: {page_size} -> {width}x{height} pixels")

    if not input_path.is_dir():
        print(f"Error: {input_dir} is not a directory")
        return
    
    logging.debug(f"width: {width}, height: {height}, cmyk_mode: {cmyk_mode}")
    # Helper to find files with depth limit
    def find_files(root_dir, max_depth=None):
        result = []
        root_depth = str(root_dir).rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root_dir):
            current_depth = str(dirpath).rstrip(os.sep).count(os.sep) - root_depth
            # Prune when we are at or beyond the max_depth to prevent descending
            if max_depth is not None and current_depth >= max_depth:
                dirnames[:] = []
            for filename in filenames:
                if filename != '.DS_Store':
                    result.append(Path(dirpath) / filename)
        return result

    # Use provided max_depth (no sys.argv parsing)
    file_count = 0
    for file_path in sorted(find_files(input_path, max_depth=max_depth)):
        if file_path.is_file():
            try:
                file_type = determine_file_type(file_path)
                logging.debug(f"Processing {file_path.name} - Type: {file_type}")

                # Log width and height before calling create_file_info_card
                logging.debug(f"Before create_file_info_card: width={width}, height={height}")

                # Generate the card
                card = create_file_info_card(
                    file_path,
                    width=width,
                    height=height,
                    cmyk_mode=cmyk_mode,
                    exclude_file_path=exclude_file_path,
                    border_color=border_color,
                    border_inch_width=border_inch_width,
                    include_video_frames=include_video_frames,
                    metadata_text="HELLO!"
                )

                # Handle single card or multiple cards (for video files)
                if isinstance(card, list):
                    for idx, card_img in enumerate(card):
                        card_size = card_img.size
                        output_file = output_path / f"{file_path.stem}_card_{idx+1}.tiff"
                        save_card_as_tiff(card_img, output_file, cmyk_mode=cmyk_mode)
                        logging.debug(f"Saved card to {output_file} with size: {card_size}")
                        if not cmyk_mode:
                            png_file = output_path / f"{file_path.stem}_card_{idx+1}.png"
                            card_img.save(png_file)
                            logging.debug(f"Saved card to {png_file} with size: {card_size}")
                    file_count += len(card)
                else:
                    card_size = card.size
                    output_file = output_path / f"{file_path.stem}_card.tiff"
                    save_card_as_tiff(card, output_file, cmyk_mode=cmyk_mode)
                    logging.debug(f"Saved card to {output_file} with size: {card_size}")
                    if not cmyk_mode:
                        png_file = output_path / f"{file_path.stem}_card.png"
                        card.save(png_file)
                        logging.debug(f"Saved card to {png_file} with size: {card_size}")
                    file_count += 1
            except Exception as e:
                logging.error(f"Error processing {file_path.name}: {e}")
                logging.error("Traceback:\n" + traceback.format_exc())
    
    logging.info(f"\nProcessing complete. Generated {file_count} file cards in {output_path}")

def assemble_cards_to_pdf(output_dir, pdf_file, page_size):
    """
    Assemble all generated file cards into a single PDF.

    Args:
        output_dir: Directory containing the generated card images
        pdf_file: Path to save the combined PDF
        page_size: Page size for the PDF (width, height in pixels at 300 dpi)
    """
    # Check if we can use img2pdf which has better TIFF support
    try:
        use_img2pdf = True
        logging.debug("Using img2pdf for PDF generation (better TIFF support)")
    except ImportError:
        use_img2pdf = False
        logging.info("img2pdf not available, using FPDF")
    
    output_path = Path(output_dir)
    
    # Get list of all card files, including multi-page video frames
    card_files = sorted(list(output_path.glob("*_card.*")) + list(output_path.glob("*_card_*.*")))

    # Convert webp images to PNG for img2pdf compatibility
    converted_files = []
    for f in card_files:
        if f.suffix.lower() == '.webp':
            png_path = f.with_suffix('.png')
            try:
                from PIL import Image
                im = Image.open(f)
                im.save(png_path)
                logging.info(f"Converted {f} to {png_path} for PDF assembly.")
                converted_files.append(str(png_path))
            except Exception as e:
                logging.error(f"Error converting {f} to PNG: {e}")
        else:
            converted_files.append(str(f))

    # If using img2pdf and we have TIFF files, use it directly
    if use_img2pdf and any(Path(f).suffix.lower() == '.tiff' or Path(f).suffix.lower() == '.tif' for f in converted_files):
        try:
            # Filter to only include image files that img2pdf supports
            valid_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp']
            image_files = [str(f) for f in converted_files if Path(f).suffix.lower() in valid_extensions]

            if image_files:
                logging.debug(f"Creating PDF with img2pdf using {len(image_files)} images")
                with open(pdf_file, "wb") as f:
                    # img2pdf works with points (1/72 inch)
                    # Convert our 300dpi measurements to points
                    width_pt = page_size[0] / 300 * 72  # Convert from pixels at 300dpi to points
                    height_pt = page_size[1] / 300 * 72
                    
                    # Set PDF page size in points
                    # layout = img2pdf.get_layout_fun({
                    #     "pagesize": (width_pt, height_pt)
                    # })
                    f.write(img2pdf.convert(image_files, pagesize=(width_pt, height_pt)))
                logging.info(f"Combined PDF saved to {pdf_file}")
                return
        except Exception as e:
            logging.error(f"Error using img2pdf: {e} (type: {type(e)})")
            logging.error("Traceback:\n" + traceback.format_exc())
            logging.error(f"Image files passed to img2pdf: {image_files}")
            logging.error("Bust.")

def _decode_metadata_text(s: str) -> str:
    # Minimal, safe escape handling for CLI input
    return (
        s.replace('\\n', '\n')
         .replace('\\r', '\r')
         .replace('\\t', '\t')
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test file card generation and PDF assembly for various file types')
    parser.add_argument('--input-dir', help='Directory containing files to create cards for')
    parser.add_argument('--output-dir', help='Directory to save card images')
    parser.add_argument('--cmyk-mode', action='store_true', help='Generate cards in CMYK mode')
    parser.add_argument('--cmyk', dest='cmyk_mode', action='store_true', help='Alias for --cmyk-mode')
    parser.add_argument('--page-size', default='LARGE_TAROT', help='Page size (A4, LETTER, TABLOID, WxH in inches)')
    parser.add_argument('--pdf-output-name', help='Path to save the combined PDF')
    parser.add_argument('--slack', action='store_true', help='Look for a "files" subdirectory in input-dir (for Slack data dumps)')
    parser.add_argument('--max-depth', type=int, default=0, help='Maximum folder recursion depth (default: 0, no recursion)')
    parser.add_argument('--exclude-file-path', default=False, action='store_true', help='Exclude the vertical file path from the card (default: shown)')
    parser.add_argument('--delete-cards-after-pdf', action='store_true', help='Delete individual card files after PDF is created')
    parser.add_argument('--border-color', default='250,250,250', help='Border color for the cards in RGB format (default: 250,250,250)')
    parser.add_argument('--border-inch-width', type=float, default=0.125, help='Border width in inches (default: 0.125)')
    parser.add_argument('--include-video-frames', action='store_true', help='Also output individual video frames as cards (default: overview only)')
    parser.add_argument('--metadata-text', default=None, help='Custom metadata text to include on the card')

    args = parser.parse_args()
    logging.info(f"Arguments: {args}")
    # Validate and adjust input_dir
    input_path = Path(args.input_dir)
    if not input_path.is_dir():
        print(f"Error: {args.input_dir} is not a directory.")
        sys.exit(1)
    if args.slack:
        files_subdir = input_path / "files"
        if files_subdir.is_dir():
            args.input_dir = str(files_subdir)
            print(f"Using 'files' subdirectory: {args.input_dir}")
        else:
            print(f"Error: No 'files' subdirectory found in {args.input_dir}.")
            sys.exit(1)
    
    input_dir_name = os.path.basename(os.path.normpath(args.input_dir))
    # Set default output_dir if not specified
    if not args.output_dir:
        # Use the base name of the input directory for the default output directory
        args.output_dir = f"{input_dir_name}_{args.page_size}"
        logging.info(f"Using default output directory: {args.output_dir}")
    else:
        args.output_dir = f"{args.output_dir}/{args.page_size}"

    # Determine the PDF path (in both cases above)
    output_path_obj = Path(args.output_dir)
    output_dir_name = output_path_obj.name
    # Compute pdf_name consistently
    if not args.pdf_output_name:
        pdf_name = f"{input_dir_name}_combined_{args.page_size}.pdf"
        logging.info(f"No PDF output name provided, using default: {pdf_name}")
    elif args.pdf_output_name.endswith('.pdf'):
        tmp_name = args.pdf_output_name.rsplit('.', 1)[0]
        pdf_name = f"{tmp_name}_combined_{args.page_size}.pdf"
    else:
        pdf_name = f"{args.pdf_output_name}_combined_{args.page_size}.pdf"

    pdf_path = str(output_path_obj / pdf_name)
    logging.info(f"PDF Name will be {pdf_name}")
    logging.info(f"PDF will be saved at: {pdf_path}")

    logging.info(f"Will generate file cards in: {args.output_dir}")
    logging.info(f"Output PDF name: {pdf_name}")
    
    # pick the border color from the command line
    border_color_parts = re.split(r'[,\s]+', args.border_color.strip())
    t_border_color = tuple(map(int, border_color_parts))

    if args.metadata_text:
        args.metadata_text = _decode_metadata_text(args.metadata_text)

    # Generate file cards
    build_file_cards_from_directory(
        args.input_dir,
        args.output_dir,
        args.cmyk_mode,
        args.page_size,
        exclude_file_path=args.exclude_file_path,
        border_color=t_border_color,
        border_inch_width=args.border_inch_width,
        include_video_frames=args.include_video_frames,
        max_depth=args.max_depth,
        metadata_text=args.metadata_text
    )

    # Report summary
    output_path = Path(args.output_dir)
    card_files = sorted(output_path.glob("*_card.*"))
    logging.info(f"Summary +++++++++++++++++++++++++++++")
    logging.info(f"Output directory: {os.path.abspath(args.output_dir)}")
    logging.info(f"Number of card files generated: {len(card_files)}")
    if card_files:
        #logging.info(f"Generated {len(card_files)} card files")
        # Print in 3 columns
        col_count = 3
        names = [f.name for f in card_files]
        max_len = max((len(name) for name in names), default=0)
        term_width = shutil.get_terminal_size((120, 20)).columns
        col_width = max_len + 2
        cols = min(col_count, max(1, term_width // col_width))
        rows = (len(names) + cols - 1) // cols
        for row in range(rows):
            line = "".join(names[row + rows * col].ljust(col_width) for col in range(cols) if row + rows * col < len(names))
            #logging.info(line)

    # Assemble cards into a PDF if requested
    if pdf_name:
        logging.info(f"Assembling cards into PDF: {pdf_name}")
        width, height = parse_page_size(args.page_size)
        

        assemble_cards_to_pdf(args.output_dir, pdf_path, (width, height))
        
        # Delete individual card files if requested
        if args.delete_cards_after_pdf:
            logging.info("Deleting individual card files after PDF creation...")
            output_dir_path = Path(args.output_dir)
            # Collect both single-card and per-frame card outputs
            delete_patterns = ["*_card.*", "*_card_*.*"]
            deleted = 0
            for pattern in delete_patterns:
                for card_file in output_dir_path.glob(pattern):
                    # Skip the combined PDF if it ever matched (it shouldn't with these patterns)
                    if Path(card_file).resolve() == Path(pdf_path).resolve():
                        continue
                    try:
                        card_file.unlink()
                        deleted += 1
                        logging.debug(f"Deleted: {card_file}")
                    except Exception as e:
                        logging.error(f"Error deleting {card_file}: {e}")
            logging.info(f"Card files cleanup complete. Deleted {deleted} files.")
