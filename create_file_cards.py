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
        'LETTER': (8.5, 11),
        'LEGAL': (8.5, 14),
        'TABLOID': (11, 17),
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
    logging.warning(f"Unknown page size '{size_name}', defaulting to A4")
    return int(8.3 * dpi), int(11.7 * dpi)

def build_file_cards_from_directory(input_dir, output_dir='file_card_tests', cmyk_mode=False, page_size='LARGE_TAROT', compact_mode=False):
    """
    Test the file card generation by creating cards for all files in a directory.
    
    Args:
        input_dir: Directory containing files to process
        output_dir: Directory to save the generated card images
        cmyk_mode: Whether to use CMYK mode for the cards
        page_size: Page size for the cards (default is A4)
    """
    logging.basicConfig(level=logging.INFO)
    logging.debug(f"Starting file card with size {page_size}")
    input_path = Path(input_dir)
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
            if max_depth is not None and current_depth > max_depth:
                dirnames[:] = []
                continue
            for filename in filenames:
                if filename != '.DS_Store':
                    result.append(Path(dirpath) / filename)
        return result

    # Get max_depth from global args if present
    import sys
    max_depth = None
    for arg in sys.argv:
        if arg.startswith('--max-depth='):
            try:
                max_depth = int(arg.split('=')[1])
            except Exception:
                pass
    file_count = 0
    for file_path in sorted(find_files(input_path, max_depth=max_depth)):
        if file_path.is_file():
            try:
                file_type = determine_file_type(file_path)
                logging.debug(f"Processing {file_path.name} - Type: {file_type}")

                # Log width and height before calling create_file_info_card
                logging.debug(f"Before create_file_info_card: width={width}, height={height}")

                # Generate the card
                card = create_file_info_card(file_path, width=width, height=height, cmyk_mode=cmyk_mode, compact_mode=compact_mode)
                
                # Save the card using specialized TIFF save function
                card_file_name = f"{file_path.stem}_card.tiff"
                card_path = output_path / card_file_name
                
                # Use dedicated function for TIFF saving to preserve borders
                save_card_as_tiff(card, card_path, cmyk_mode=cmyk_mode)
                logging.debug(f"Saved card: {card_path}")
                
                # Log the size of the saved card
                card_size = card.size
                logging.debug(f"Card size: {card_size}")

                logging.debug(f"Created card for {file_path.name} with size: {card.size} width: {card.width}, height: {card.height}")
                # Save the card as PNG only if not CMYK
                if not cmyk_mode:
                    output_file = output_path / f"{file_path.stem}_card.png"
                    card.save(output_file)
                    logging.debug(f"Saved card to {output_file} with size: {card.size}")
                file_count += 1
            except Exception as e:
                logging.error(f"Error processing {file_path.name}: {e}")
    
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
    
    # Get list of all card files
    card_files = sorted(output_path.glob("*_card.*"))
    
    # If using img2pdf and we have TIFF files, use it directly
    if use_img2pdf and any(f.suffix.lower() == '.tiff' for f in card_files):
        try:
            # Filter to only include image files that img2pdf supports
            valid_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
            image_files = [str(f) for f in card_files if f.suffix.lower() in valid_extensions]
            
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
            logging.warning(f"Error using img2pdf: {e} (type: {type(e)})")
            logging.warning("Traceback:\n" + traceback.format_exc())
            logging.warning(f"Image files passed to img2pdf: {image_files}")
            logging.warning("Falling back to FPDF")
    
                # Only include TIFFs for CMYK, PNGs otherwise
                # Detect CMYK mode by presence of TIFFs (since only CMYK saves TIFFs)
            tiff_files = sorted(output_path.glob("*_card.tiff"))
            png_files = sorted(output_path.glob("*_card.png"))
            if tiff_files:
                image_files = [str(f) for f in tiff_files]
            else:
                image_files = [str(f) for f in png_files]
            if image_files:
                try:
                    logging.debug(f"Creating PDF with img2pdf using {len(image_files)} images")
                    with open(pdf_file, "wb") as f:
                        width_pt = page_size[0] / 300 * 72
                        height_pt = page_size[1] / 300 * 72
                        f.write(img2pdf.convert(image_files, pagesize=(width_pt, height_pt)))
                    logging.info(f"Combined PDF saved to {pdf_file}")
                    return
                except Exception as e:
                    logging.warning(f"Error using img2pdf: {e} (type: {type(e)})")
                    logging.warning("Traceback:\n" + traceback.format_exc())
            # Direct inclusion for other formats
            pdf.image(str(card_file), x=0, y=0, w=page_size[0], h=page_size[1])
        except Exception as e:
            logging.error(f"Error adding {card_file} to PDF: {e}")

    pdf.output(pdf_file)
    logging.info(f"Combined PDF saved to {pdf_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test file card generation and PDF assembly for various file types')
    parser.add_argument('--input-dir', help='Directory containing files to create cards for')
    parser.add_argument('--output-dir', help='Directory to save card images')
    parser.add_argument('--cmyk-mode', action='store_true', help='Generate cards in CMYK mode')
    parser.add_argument('--page-size', default='LARGE_TAROT', help='Page size (A4, LETTER, TABLOID, WxH in inches)')
    parser.add_argument('--pdf-output-name', help='Path to save the combined PDF')
    parser.add_argument('--compact', action='store_true', help='Enable compact mode for file card generation')
    parser.add_argument('--slack', action='store_true', help='Look for a "files" subdirectory in input-dir (for Slack data dumps)')
    parser.add_argument('--max-depth', type=int, default=0, help='Maximum folder recursion depth (default: 0, no recursion)')

    args = parser.parse_args()
    logging.debug(f"Arguments: {args}")
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

    # Set default output_dir if not specified
    if not args.output_dir:
        parent_dir_name = os.path.basename(os.path.dirname(os.path.normpath(args.input_dir)))
        args.output_dir = f"{parent_dir_name}_cards_output"
        logging.info(f"Using default output directory: {args.output_dir}")

    # Set default pdf_output_name if not specified
    if not args.pdf_output_name:
        parent_dir_name = os.path.basename(os.path.dirname(os.path.normpath(args.input_dir)))
        args.pdf_output_name = f"{parent_dir_name}_combined_pdf.pdf"
        logging.info(f"Using default PDF output name: {args.pdf_output_name}")

    # Generate file cards
    build_file_cards_from_directory(
        args.input_dir,
        args.output_dir,
        args.cmyk_mode,
        args.page_size,
        compact_mode=args.compact
    )

    # Report summary
    output_path = Path(args.output_dir)
    card_files = sorted(output_path.glob("*_card.*"))
    print(f"\nSummary:")
    print(f"Output directory: {os.path.abspath(args.output_dir)}")
    print(f"Number of card files generated: {len(card_files)}")
    if card_files:
        print("Generated card files:")
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
            print(line)

    # Assemble cards into a PDF if requested
    if args.pdf_output_name:
        width, height = parse_page_size(args.page_size)
        pdf_path = str(Path(args.output_dir) / args.pdf_output_name)
        assemble_cards_to_pdf(args.output_dir, pdf_path, (width, height))
