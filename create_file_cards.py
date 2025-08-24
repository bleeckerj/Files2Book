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
IMAGE_EXTS = frozenset({'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp'})

def is_valid_card_file(p: Path) -> bool:
    """
    Return True if p is a regular file (not a dotfile) and has a supported image extension.
    """
    if not isinstance(p, Path):
        return False
    name = p.name
    if name.startswith(".") or name.startswith("._"):
        return False
    return p.is_file() and p.suffix.lower() in IMAGE_EXTS

from file_card_generator import create_file_info_card, get_original_timestamp, determine_file_type, save_card_as_tiff

global_glob_pattern = ["*_card.*", "*_card_*.*", "* card.*", "* card_*.*"]

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
    metadata_text=None,
    cards_per_chunk=0,
    pdf_name=None
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
        cards_per_chunk: If >0, split card images into chunked folders of this many cards and produce one PDF per chunk
        pdf_name: Name of the output PDF file (default: assembled)
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
    chunk_idx = 0
    files_handled_count = 0  # Count of number of files handled
    total_files_count = 0
    chunk_dir = output_path
    
    # Initialize a list to store cards and their timestamps
    card_ordering_list = []
    
    # count the number of files total and create an ordered list
    for file_path in find_files(input_path, max_depth=max_depth):
        if file_path.is_file():
            total_files_count += 1
            original_timestamp = get_original_timestamp(file_path)

            # Add the card and its timestamp to the list
            card_ordering_list.append((file_path, original_timestamp))

    card_ordering_list.sort(key=lambda x: x[1])
    logging.info(f"Total files to process: {total_files_count} {len(card_ordering_list)}")


    for file_path, _ in card_ordering_list:
        if file_path.is_file():
            try:
                #file_type = determine_file_type(file_path)
                #logging.debug(f"Processing {file_path.name} - Type: {file_type}")
                file_stem = file_path.stem
                # Kludgy way to get the files in order. There's a better way.
                # Must be..
                # if file_stem.startswith("ts_") and "_ts__" in file_stem:
                #     file_stem = file_stem.split("_ts__")[-1]
                card = create_file_info_card(
                    file_path,
                    width=width,
                    height=height,
                    cmyk_mode=cmyk_mode,
                    exclude_file_path=exclude_file_path,
                    border_color=border_color,
                    border_inch_width=border_inch_width,
                    include_video_frames=include_video_frames,
                    metadata_text=None,
                    title=file_stem
                )

                if isinstance(card, list):
                    for idx, card_img in enumerate(card):
                        card_size = card_img.size
                        # Chunking logic
                        if cards_per_chunk and cards_per_chunk > 0:
                            if file_count % cards_per_chunk == 0:
                                #### where did this come from? chunk_idx = file_count // cards_per_chunk
                                chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                                chunk_dir.mkdir(exist_ok=True, parents=True)
                            output_file = chunk_dir / f"{file_path.stem}_card_{idx+1}.tiff"
                        else:
                            output_file = output_path / f"{file_path.stem}_card_{idx+1}.tiff"
                        
                        
                        save_card_as_tiff(card_img, output_file, cmyk_mode=cmyk_mode)
                        
                        logging.debug(f"Saved card to {output_file} with size: {card_size}")

                        file_count += 1
                        chunk_file_count = sum(
                            len(list(chunk_dir.glob(pattern)))
                            for pattern in global_glob_pattern
                        )
                        if (chunk_file_count != file_count):
                            file_count = chunk_file_count
                        #logging.info(f"Chunk {chunk_idx} contains {chunk_file_count} card files.")
                        # After saving each card, check if chunk is full
                        if cards_per_chunk and cards_per_chunk > 0 and chunk_file_count % cards_per_chunk == 0:
                            pdf_name_chunk = f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                            pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                            logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                            
                            assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height), card_ordering_list)
                            logging.info(f"Saved chunk PDF: {pdf_path_chunk}")
                            card_ordering_list = []
                            
                            ## DO NOT DELETE THIS LINE
                            ## Optionally delete images in the last chunk

                            if args.delete_cards_after_pdf:
                                delete_cards_in_directory(chunk_dir)
                                
                            ## DO NOT DELETE THIS LINE
                            chunk_idx += 1
                else:
                    card_size = card.size
                    if cards_per_chunk and cards_per_chunk > 0:
                        if file_count % cards_per_chunk == 0:
                            chunk_idx = file_count // cards_per_chunk
                            chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                            chunk_dir.mkdir(exist_ok=True, parents=True)
                        output_file = chunk_dir / f"{file_path.stem}_card.tiff"
                    else:
                        output_file = output_path / f"{file_path.stem}_card.tiff"
                        
                    save_card_as_tiff(card, output_file, cmyk_mode=cmyk_mode)
                    logging.debug(f"Saved card to {output_file} with size: {card_size}")
                    
                    original_timestamp = get_original_timestamp(file_path)

                    # Add the card and its timestamp to the list
                    card_ordering_list.append((output_file, original_timestamp))
                        
    

                    file_count += 1
                    
                    ## double check how many files we are at..in some cases for some reason
                    ## I have noticed that file_count is not reflective of the numbers of files
                    ## in the directory, typically less than the number of files, presumably
                    ## because some files do not get saved for some reason that escapes me (wrong type, e.g.? system file?)
                    chunk_file_count = sum(
                        len(list(chunk_dir.glob(pattern)))
                        for pattern in global_glob_pattern
                    )
                    if (chunk_file_count != file_count):
                        file_count = chunk_file_count
                    # After saving each card, check if chunk is full
                    if cards_per_chunk and cards_per_chunk > 0 and chunk_file_count % cards_per_chunk == 0:
                        pdf_name_chunk = f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                        pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                        logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")

                        assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height), card_ordering_list)
                        
                        
                        card_ordering_list = []
                        
                        logging.info(f"Saved chunk PDF: {pdf_path_chunk}")
                        
                        ## DO NOT DELETE THIS LINE
                        ## Optionally delete images in the last chunk

                        if args.delete_cards_after_pdf:
                            delete_cards_in_directory(chunk_dir)
                            
                        ## DO NOT DELETE THIS LINE
                                    
                        chunk_idx += 1
            except Exception as e:
                logging.error(f"Error processing {file_path.name}: {e}")
                logging.error("Traceback:\n" + traceback.format_exc())
    
    
                
                
    # After the loop: Handle the last chunk (if any cards remain)
    if cards_per_chunk and cards_per_chunk > 0 and (chunk_file_count % cards_per_chunk != 0 or files_handled_count >= total_files_count):
        pdf_name_chunk = f"{pdf_name}_chunk_{chunk_idx:04d}.pdf"
        pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
        logging.info(f"Assembling final PDF for chunk {chunk_idx}: {pdf_path_chunk}")

        assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height), card_ordering_list)
        
        card_ordering_list = []
        
        logging.info(f"Saved final chunk PDF: {pdf_path_chunk}")
        
        ## DO NOT DELETE THIS LINE
        ## Optionally delete images in the last chunk

        if args.delete_cards_after_pdf:
            delete_cards_in_directory(chunk_dir)
            
        ## DO NOT DELETE THIS LINE
        
        logging.info(f"Processing complete. Generated {file_count} file cards in {output_path}")    
    
    logging.info(f"\nProcessing complete. Generated {file_count} file cards in {output_path}")

def assemble_cards_to_pdf(output_dir, pdf_file, page_size, cards=None):
    """
    Assemble all generated file cards into a single PDF.

    Args:
        output_dir: Directory containing the generated card images (ignored if `cards` is provided)
        pdf_file: Path to save the combined PDF
        page_size: Page size for the PDF (width, height in pixels at 300 dpi)
        cards: Optional list of card file paths to include in the PDF
    """
    # Check if we can use img2pdf which has better TIFF support
    try:
        use_img2pdf = True
        logging.debug("Using img2pdf for PDF generation (better TIFF support)")
    except ImportError:
        use_img2pdf = False
        logging.info("img2pdf not available, using FPDF")
    
    # If no cards are provided, use files from the output directory
    if cards is None:
        output_path = Path(output_dir)
        try:
            # Only include files whose name does not start with "." or "._"
            # and whose extension is a supported image type
            valid_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp']
            card_files = []
            for pattern in global_glob_pattern:
                card_files.extend(
                    f for f in output_path.glob(pattern)
                    if f.is_file()
                    and f.suffix.lower() in valid_exts
                    and not (f.name.startswith(".") or f.name.startswith("._"))
                )
            card_files = sorted(card_files)
        except Exception as e:
            logging.error(f"Error while processing card files: {e}")
            return
    else:
        # Use the provided list of cards
        try:
            card_files = [Path(card[0]) for card in cards]
        except Exception as e:
            logging.error(f"Error while processing provided card files: {e}")
            return
        logging.info(f"Using provided card files: {card_files}")
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
    if use_img2pdf and any(Path(f).suffix.lower() in ['.tiff', '.tif'] for f in card_files):
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

def delete_cards_in_directory(chunk_dir: Path):
    # Delete card files in the specified directory
    delete_patterns = global_glob_pattern
    for pattern in delete_patterns:
        for card_file in chunk_dir.glob(pattern):
            if card_file.name.startswith("._"):
                continue  # Skip macOS metadata files
            if card_file.suffix.lower() not in {".tiff", ".tif", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue  # Skip non-image files
            try:
                card_file.unlink()
                time.sleep(0.01)
            except Exception as e:
                logging.error(f"Error deleting {card_file}: {e}")
                logging.error("Traceback:\n" + traceback.format_exc())
    logging.info(f"Deleted images in {chunk_dir}")


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
    parser.add_argument('--include-video-frames', default=False, action='store_true', help='Also output individual video frames as cards (default: overview only)')
    parser.add_argument('--metadata-text', default=None, help='Custom metadata text to include on the card')
    parser.add_argument('--cards-per-chunk', type=int, default=0, help='If >0, split card images into chunked folders of this many cards and produce one PDF per chunk')

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
        pdf_name = f"{input_dir_name}_combined_{args.page_size}"
        logging.info(f"No PDF output name provided, using default: {pdf_name}")
    elif args.pdf_output_name.endswith('.pdf'):
        tmp_name = args.pdf_output_name.rsplit('.', 1)[0]
        pdf_name = f"{tmp_name}_combined_{args.page_size}"
    else:
        pdf_name = f"{args.pdf_output_name}_combined_{args.page_size}"

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
        metadata_text=args.metadata_text,
        cards_per_chunk=args.cards_per_chunk,  # <--- Pass chunk size
        pdf_name=pdf_name
    )

    # Report summary
    output_path = Path(args.output_dir)
    card_files = []
    for pattern in global_glob_pattern:
        card_files.extend(output_path.glob(pattern))
    card_files = sorted(card_files)

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
        

        assemble_cards_to_pdf(args.output_dir, pdf_path, (width, height), None)

        # Delete individual card files if requested
        if args.delete_cards_after_pdf:
            logging.info("Deleting individual card files after PDF creation...")
            output_dir_path = Path(args.output_dir)
            # Collect both single-card and per-frame card outputs
            delete_patterns = global_glob_pattern
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
    
        # Chunked PDF assembly
        cards_per_chunk = getattr(args, "cards_per_chunk", 0) or 0
        output_dir_path = Path(args.output_dir)
        if cards_per_chunk and cards_per_chunk > 0:
            chunk_dirs = sorted([d for d in output_dir_path.iterdir() if d.is_dir() and d.name.startswith("chunk_")])
            for chunk_dir in chunk_dirs:
                try:
                    chunk_idx = int(chunk_dir.name.split("_")[1])
                except Exception:
                    chunk_idx = 0
                base_name = output_dir_path.name
                pdf_name_chunk = f"{base_name}_chunk_{chunk_idx:04d}.pdf"
                pdf_path_chunk = str(output_dir_path / pdf_name_chunk)
                logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height))
                logging.info(f"Saved chunk PDF: {pdf_path_chunk}")
        else:
            assemble_cards_to_pdf(args.output_dir, pdf_path, (width, height))
