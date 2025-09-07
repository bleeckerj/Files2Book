#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from PIL import Image
import argparse
#from fpdf import FPDF
import logging
import time
import shutil
import itertools
import traceback
import img2pdf
import re
import csv
import json
import tempfile
import zipfile


os.environ["PYDEVD_WARN_EVALUATION_TIMEOUT"] = "120000" # that's 2 minutes!

logging.basicConfig(
    level=logging.INFO,
    # format='%(asctime)s:%(levelname)s - %(name)s %(filename)s:%(funcName)s:%(lineno)d - %(message)s'
    format='%(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s'

)

total_files_handled_count = 0
exclude_exts = None
#IMAGE_EXTS = frozenset({'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp'})
# def is_valid_card_file(p: Path) -> bool:
#     """
#     Return True if p is a regular file (not a dotfile) and has a supported image extension.
#     """
#     if not isinstance(p, Path):
#         return False
#     name = p.name
#     if name.startswith(".") or name.startswith("._"):
#         return False
#     return p.is_file() and p.suffix.lower() in IMAGE_EXTS

from file_card_generator import create_file_info_card, determine_file_type, save_card_as_tiff
import file_card_generator

global_glob_pattern = ["*_card.*", "*_card_*.*", "* card.*", "* card_*.*"]

def parse_page_size(size_name):
    # Returns (width, height) in pixels at 300dpi
    size_name = size_name.upper()
    dpi = 300
    sizes = {
        'A5': (5.83, 8.27),
        'A5_FULLBLEED': (5.955, 8.395),
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
        'DIGEST_FULLBLEED': (5.625, 8.625),
        'POCKETBOOK': (4.25, 6.87),   # PocketBook size
        'POCKETBOOK_FULLBLEED': (4.375, 6.995),
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

def _process_file_iterable(
    file_iterable,
    output_path: Path,
    width: int,
    height: int,
    cmyk_mode: bool = False,
    exclude_file_path: bool = False,
    exclude_exts: list = None,
    border_color=(250, 250, 250),
    border_inch_width: float = 0.125,
    include_video_frames: bool = False,
    max_video_frames: int = 30,
    metadata_text=None,
    cards_per_chunk: int = 0,
    pdf_name=None,
    delete_cards_after_pdf: bool = False
):
    """
    Shared processing loop for an iterable of file paths. Handles card creation,
    saving, chunking, PDF assembly per-chunk, and optional deletion of chunk
    images after PDF creation.
    """
    current_chunk_file_count = 0
    chunk_idx = 0
    global total_files_handled_count
    total_files_handled_count = 0
    total_files_to_process_count = 0
    # Initialize chunk_dir correctly
    if cards_per_chunk and cards_per_chunk > 0:
        chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
        chunk_dir.mkdir(exist_ok=True, parents=True)
    else:
        chunk_dir = output_path

    if exclude_exts is None:
        exclude_exts = []
        
    files_to_process = []
    # Pre-count valid files
    for p in file_iterable:
        # its either filepath, or file  or uti in the thing or we end up skipping
        pth = Path(
            p['filepath'] if isinstance(p, dict) and 'filepath' in p
            else p['uri'] if isinstance(p, dict) and 'uri' in p
            else p['file'] if isinstance(p, dict) and 'file' in p
            else p
        )

        if pth.suffix.lower() in exclude_exts:
            logging.info(f"Excluded by extension: {pth.name}")
            continue

        try:
            is_file = pth.is_file()
        except OSError as e:
            logging.error(f"OSError while checking file '{pth}': {e}")
            continue
        except Exception as e:
            logging.error(f"Error while checking file '{pth}': {e}")
            continue

        if is_file:
            total_files_to_process_count += 1
            files_to_process.append(p)
        else:
            logging.debug(f"Skipping non-file entry: {pth}")

    logging.info(f"Total files to process: {total_files_to_process_count}")

    # Iterate again for actual processing
    for p in files_to_process:
        file_path = Path(
            p['filepath'] if isinstance(p, dict) and 'filepath' in p
            else p['uri'] if isinstance(p, dict) and 'uri' in p
            else p['file'] if isinstance(p, dict) and 'file' in p
            else p
        )

        try:
            file_type = determine_file_type(file_path)
            logging.debug(f"Processing {file_path.name} - Type: {file_type}")

            metadata = p.get('metadata') if isinstance(p, dict) and 'metadata' in p else None
            title = metadata['title'] if metadata and 'title' in metadata else file_path.stem
            card = create_file_info_card(
                file_path,
                width=width,
                height=height,
                cmyk_mode=cmyk_mode,
                exclude_file_path=exclude_file_path,
                border_color=border_color,
                border_inch_width=border_inch_width,
                include_video_frames=include_video_frames,
                max_video_frames=args.max_video_frames,
                metadata_text=metadata_text,
                metadata=metadata,
                title=title
            )
            
            if card is None:
                logging.warning(f"No card generated for {file_path}. Skipping.")
                continue

            if isinstance(card, list):
                for idx, card_img in enumerate(card):
                    card_size = card_img.size
                    if cards_per_chunk and cards_per_chunk > 0:
                        if total_files_handled_count % cards_per_chunk == 0:
                            chunk_idx = total_files_handled_count // cards_per_chunk
                            chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                            chunk_dir.mkdir(exist_ok=True, parents=True)
                        output_file = chunk_dir / f"{current_chunk_file_count:04d}_{file_path.stem}_card_{idx+1}.tiff"
                    else:
                        output_file = output_path / f"{total_files_handled_count:04d}_{file_path.stem}_card_{idx+1}.tiff"
                    save_card_as_tiff(card_img, output_file, cmyk_mode=cmyk_mode)
                    total_files_handled_count += 1
                    logging.info(f"Saved card to {output_file}")
                    current_chunk_file_count = get_count_of_non_dot_card_files(chunk_dir)
                    # Count unique files in the chunk directory to avoid double-counting overlapping glob patterns

                    if cards_per_chunk and cards_per_chunk > 0 and current_chunk_file_count % cards_per_chunk == 0:
                        pdf_name_chunk = f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                        pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                        logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                        assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height))
                        logging.info(f"Saved chunk PDF: {pdf_path_chunk}")

                        if delete_cards_after_pdf:
                            delete_cards_in_directory(chunk_dir)

                        # chunk_idx += 1
                        # chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
            else:
                card_size = card.size
                if cards_per_chunk and cards_per_chunk > 0:
                    if total_files_handled_count % cards_per_chunk == 0:
                        chunk_idx = total_files_handled_count // cards_per_chunk
                        chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
                        chunk_dir.mkdir(exist_ok=True, parents=True)
                    output_file = chunk_dir / f"{current_chunk_file_count:04d}_{file_path.stem}_card.tiff"
                else:
                    output_file = output_path / f"{current_chunk_file_count:04d}_{file_path.stem}_card.tiff"
                save_card_as_tiff(card, output_file, cmyk_mode=cmyk_mode)
                logging.debug(f"Saved card to {output_file} with size: {card_size}")
                total_files_handled_count += 1
                current_chunk_file_count = get_count_of_non_dot_card_files(chunk_dir)
                # Count unique files in the chunk directory to avoid double-counting overlapping glob patterns

                # Do NOT overwrite the global file_count with the per-chunk count.
                # file_count is the absolute index across all cards; chunk_file_count
                # is only used to decide when a chunk is complete.

                if cards_per_chunk and cards_per_chunk > 0 and current_chunk_file_count % cards_per_chunk == 0:
                    pdf_name_chunk = f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                    pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                    logging.info(f"Assembling PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                    assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height))
                    logging.info(f"Saved chunk PDF: {pdf_path_chunk}")

                    if delete_cards_after_pdf:
                        delete_cards_in_directory(chunk_dir)

                    # chunk_idx += 1
                    # chunk_dir = output_path / f"chunk_{chunk_idx:04d}"
        except Exception as e:
            logging.error(f"Error processing {file_path.name}: {e}")
            logging.error("Traceback:\n" + traceback.format_exc())

    # After the loop: Handle the last chunk (if any cards remain)
    if cards_per_chunk and cards_per_chunk > 0:
        try:
            if 'current_chunk_file_count' in locals() and (current_chunk_file_count % cards_per_chunk != 0 or total_files_handled_count >= total_files_to_process_count):
                pdf_name_chunk = f"{pdf_name}_chunk_{chunk_idx:04d}.pdf" if pdf_name else f"{output_path.name}_chunk_{chunk_idx:04d}.pdf"
                pdf_path_chunk = str(chunk_dir / pdf_name_chunk)
                logging.info(f"Assembling final PDF for chunk {chunk_idx}: {pdf_path_chunk}")
                assemble_cards_to_pdf(str(chunk_dir), pdf_path_chunk, (width, height))
                logging.info(f"Saved final chunk PDF: {pdf_path_chunk}")

                if delete_cards_after_pdf:
                    delete_cards_in_directory(chunk_dir)
        except Exception as e:
            logging.error(f"Error assembling final chunk PDF: {e}")

    try:
        # Count recursively to include cards saved in chunk subdirectories
        n_cards = sum(1 for _ in output_path.rglob('*.tiff'))
    except Exception:
        n_cards = ''
    logging.info(f"\nProcessing complete. Generated {n_cards} file cards in {output_path}")

def find_files(root_dir, max_depth=None):
    """
    Find all files under root_dir respecting a max_depth. Returns a list of Path objects.
    This is the same logic previously embedded in build_file_cards_from_directory but
    exposed as a top-level helper so both directory- and list-based flows can reuse it.
    """
    result = []
    root_depth = str(root_dir).rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        current_depth = str(dirpath).rstrip(os.sep).count(os.sep) - root_depth
        # Prune when we are at or beyond the max_depth to prevent descending
        if max_depth is not None and current_depth >= max_depth:
            dirnames[:] = []
        for filename in filenames:
            pth = Path(dirpath) / filename
            if not filename.startswith('.') and pth.suffix.lower() not in exclude_exts:
                result.append(pth)
    return result

def build_file_cards_from_list(
    file_list,
    output_dir='file_card_tests',
    cmyk_mode=False,
    page_size='LARGE_TAROT',
    exclude_exts=None,
    exclude_file_path=None,
    border_color=(250, 250, 250),
    border_inch_width=0.125,
    include_video_frames=False,
    max_video_frames=30,
    metadata_text=None,
    cards_per_chunk=0,
    pdf_name=None,
    delete_cards_after_pdf: bool = False
):
    """
    Wrapper that prepares output directory and delegates to _process_file_iterable
    for ordered list processing. Supports file_list as a flat list of paths or a list of dicts
    with 'filepath' and optional 'metadata' keys.
    """
    logging.info(f"Output directory: {output_dir}")

    output_path = Path(output_dir)
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(exist_ok=True, parents=True)

    width, height = parse_page_size(page_size)

    ########
    # This seems to already have been done by the time we get here
    ########
    # Normalize file_list to a list of file paths and optional metadata
    # normalized_filepaths_and_metadata = []
    # if file_list and isinstance(file_list[0], dict):
    #     logging.info("Detected list of dicts with 'filepath' and optional 'metadata' and optional 'timestamp'")
    #     # List of dicts: extract 'filepath'
    #     for entry in file_list:
    #         fp = entry.get('filepath') or entry.get('path') or entry.get('file')
    #         if fp:
    #             normalized_filepaths_and_metadata.append({'filepath': fp, 'metadata': entry.get('metadata') if 'metadata' in entry else None})
    # else:
    #     # Flat list: just file paths
    #     for fp in file_list:
    #         normalized_filepaths_and_metadata.append({'filepath': fp})

    # Expand zip files
    zip_expanded_files_list = []
    temp_dirs = []
    for entry in file_list:
        fp = entry['filepath']
        if str(fp).lower().endswith('.zip'):
            temp_dir = tempfile.TemporaryDirectory()
            temp_dirs.append(temp_dir)
            zip_base = Path(fp).stem
            with zipfile.ZipFile(fp, 'r') as z:
                for name in z.namelist():
                    if name.startswith("._") or name.startswith("__MACOSX") or name.startswith(".DS"):
                        continue
                    new_name = f"{zip_base}__{Path(name).name}"
                    target_path = Path(temp_dir.name) / new_name
                    try:
                        with z.open(name) as src, open(target_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                    except Exception as e:
                        logging.error(f"Error extracting {name} from zip {fp}: {e}")
                    zip_expanded_files_list.append({'filepath': target_path, 'metadata': {'Zip File':zip_base}})
            zip_expanded_files_list.append({'filepath': fp})
        else:
            zip_expanded_files_list.append(entry)

    # Prepare iterable of file paths for _process_file_iterable
    final_file_list = [entry for entry in zip_expanded_files_list]
    
    
    _process_file_iterable(
        final_file_list,
        output_path=output_path,
        width=width,
        height=height,
        cmyk_mode=cmyk_mode,
        exclude_file_path=exclude_file_path,
        exclude_exts=exclude_exts,
        border_color=border_color,
        border_inch_width=border_inch_width,
        include_video_frames=include_video_frames,
        max_video_frames=max_video_frames,
        metadata_text=metadata_text,
        cards_per_chunk=cards_per_chunk,
        pdf_name=pdf_name,
        delete_cards_after_pdf=delete_cards_after_pdf
    )



def build_file_cards_from_directory(
    input_dir,
    output_dir='file_card_tests',
    cmyk_mode=False,
    page_size='LARGE_TAROT',
    exclude_file_path=False,
    border_color=(250, 250, 250),
    border_inch_width=0.125,
    include_video_frames=False,
    exclude_exts=None,
    max_video_frames=30,
    max_depth=0,  # 0 = no recursion; negative => unlimited
    metadata_text=None,
    cards_per_chunk=0,
    pdf_name=None,
    delete_cards_after_pdf: bool = False
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
        logging.error(f"Error: {input_dir} is not a directory")
        return

    # Reuse the shared processing implementation by passing the find_files iterable
    files_iter = find_files(input_path, max_depth=max_depth)
    expanded_files, temp_dirs = expand_zip_files(files_iter)
    _process_file_iterable(
        expanded_files,
        output_path=output_path,
        width=width,
        height=height,
        cmyk_mode=cmyk_mode,
        exclude_exts=exclude_exts,
        exclude_file_path=exclude_file_path,
        border_color=border_color,
        border_inch_width=border_inch_width,
        include_video_frames=include_video_frames,
        max_video_frames=args.max_video_frames,
        metadata_text=metadata_text,
        cards_per_chunk=cards_per_chunk,
        pdf_name=pdf_name,
        delete_cards_after_pdf=delete_cards_after_pdf
    )

    try:
        # Count recursively to include cards in chunk folders
        n_cards = sum(1 for _ in output_path.rglob('*.tiff'))
    except Exception:
        n_cards = ''
    logging.info(f"\nProcessing complete. Generated {n_cards} file cards in {output_path}")

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
    try:
        # Only include files whose name does not start with "." or "._"
        # and whose extension is a supported image type
        # valid_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp']
        card_files = []
        # for pattern in global_glob_pattern:
        #     card_files.extend(
        #     f for f in output_path.glob(pattern)
        #     if f.is_file()
        #     and f.suffix.lower() in valid_exts
        #     and not (f.name.startswith(".") or f.name.startswith("._"))
        #     )
        card_files = get_non_dot_card_files(output_path)
        card_files = sorted(card_files)
    except Exception as e:
        logging.error(f"Error while processing card files: {e}")
    
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





def get_non_dot_card_files(directory: Path):
    """
    Return a set of card files recursively starting in 'directory' matching any of the glob_patterns,
    excluding files whose name starts with '.' or '._'.
    """
    matched_files = set()
    for pattern in global_glob_pattern:
        for f in directory.rglob(pattern):
            if f.is_file() and not (f.name.startswith(".") or f.name.startswith("._")):
                try:
                    matched_files.add(f.resolve())
                except Exception:
                    matched_files.add(f)
    return matched_files


def get_count_of_non_dot_card_files(directory: Path):

   return len(get_non_dot_card_files(directory))


def expand_zip_files(file_list):
    expanded_files = []
    temp_dirs = []
    for file_path in file_list:
        if str(file_path).lower().endswith('.zip'):
            temp_dir = tempfile.TemporaryDirectory()
            temp_dirs.append(temp_dir)  # Keep reference to avoid premature cleanup
            zip_base = Path(file_path).stem
            with zipfile.ZipFile(file_path, 'r') as z:
                for name in z.namelist():
                    # Ignore macOS "._*" files and metadata
                    if name.startswith("._") or name.startswith("__MACOSX") or name.startswith(".DS"):
                        continue
                    # Add zip file name as prefix to extracted file
                    new_name = f"{zip_base}__{Path(name).name}"
                    target_path = Path(temp_dir.name) / new_name
                    with z.open(name) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    expanded_files.append(target_path)
            expanded_files.append(file_path)
        else:
            expanded_files.append(file_path)
    return expanded_files, temp_dirs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test file card generation and PDF assembly for various file types')
    parser.add_argument('--input-dir', help='Directory containing files to create cards for')
    parser.add_argument('--output-dir', help='Directory to save card images')
    parser.add_argument('--file-list', help='Path to a CSV file containing comma-separated file paths (items may be quoted). If provided, input-dir is not required and the ordered file list will be processed.')
    parser.add_argument('--cmyk-mode', action='store_true', help='Generate cards in CMYK mode')
    parser.add_argument('--cmyk', dest='cmyk_mode', action='store_true', help='Alias for --cmyk-mode')
    parser.add_argument('--page-size', default='LARGE_TAROT', help='Page size (A4, LETTER, TABLOID, WxH in inches)')
    parser.add_argument('--pdf-output-name', help='Path to save the combined PDF')
    # parser.add_argument('--slack', action='store_true', help='Look for a "files" subdirectory in input-dir (for Slack data dumps)')
    parser.add_argument('--max-depth', type=int, default=0, help='Maximum folder recursion depth (default: 0, no recursion)')
    parser.add_argument('--exclude-file-path', default=False, action='store_true', help='Exclude the vertical file path from the card (default: shown)')
    parser.add_argument('--delete-cards-after-pdf', action='store_true', help='Delete individual card files after PDF is created')
    parser.add_argument('--border-color', default='250,250,250', help='Border color for the cards in RGB format (default: 250,250,250)')
    parser.add_argument('--border-inch-width', type=float, default=0.125, help='Border width in inches (default: 0.125)')
    parser.add_argument('--include-video-frames', default=False, action='store_true', help='Also output individual video frames as cards (default: overview only)')
    parser.add_argument('--max-video-frames', type=int, default=30, help='Minimum number of video frames to include')
    parser.add_argument('--exclude-exts', default=None, help='Comma-separated list of file extensions to exclude (e.g. "dng, oci")')
    parser.add_argument('--metadata-text', default=None, help='Custom metadata text to include on the card')
    parser.add_argument('--cards-per-chunk', type=int, default=0, help='If >0, split card images into chunked folders of this many cards and produce one PDF per chunk')
    parser.add_argument('--slack-data-root', help='Path to Slack export root (directory containing messages.json and files/). If provided, the script will treat input as Slack data and resolve relative filepaths accordingly.')
    args = parser.parse_args()
    logging.info(f"Arguments: {args}")
    if args.exclude_exts is not None:
        exclude_exts = [ext.strip().lower() for ext in args.exclude_exts.split(',') if ext.strip()]
    else:
        exclude_exts = []    # If a file list CSV is provided, parse it and process that list in order.

    exclude_file_path = args.exclude_file_path
    
    files_from_list = None
    if args.file_list:
        if not os.path.isfile(args.file_list):
            logging.error(f"Error: {args.file_list} is not a file.")
            sys.exit(1)
        files_from_list = []
        try:
            # Support JSON or CSV input. If the file extension ends with .json, parse JSON.
            # The JSON structure is expected to be an array of objects, each with a 'filepath' key.
            # It can also contain a 'timestamp' key for each file and a 'metadata' key that will be used
            # For the metatext for the corresponding card
            if args.file_list.lower().endswith('.json'):
                try:
                    with open(args.file_list, 'r', encoding='utf-8') as jf:
                        data = json.load(jf)
                        # The array is either at the root or under a 'file' or 'filelist' key
                        if isinstance(data, list):
                            array = data
                        elif isinstance(data, dict):
                            # Try common keys
                            array = data.get('file') or data.get('filelist')
                            if array is None:
                                logging.error("JSON file does not contain a root array or a 'file'/'filelist' key.")
                                sys.exit(1)
                        else:
                            logging.error("JSON file is not a list or dict.")
                            sys.exit(1)
                        for elem in array:
                            fp = None
                            metadata = None
                            if isinstance(elem, dict):
                                fp = elem.get('filepath') or elem.get('uri') or elem.get('path') or elem.get('file')
                                metadata = elem.get('metadata')
                            elif isinstance(elem, str):
                                fp = elem
                            if not fp:
                                continue
                            # Normalize: expand user, strip whitespace
                            fp_str = os.path.expanduser(str(fp).strip())
                            # If the filepath is relative, resolve it against --input-dir if provided,
                            # otherwise against the current working directory.
                            if not os.path.isabs(fp_str):
                                base_dir = args.input_dir if getattr(args, 'input_dir', None) else os.getcwd()
                                fp_str = os.path.join(base_dir, fp_str)
                            entry = {"filepath": fp_str, "metadata": metadata}
                            files_from_list.append(entry)
                except Exception as e:
                     logging.error(f"Error reading JSON file list {args.file_list}: {e}")
                     sys.exit(1)
            else:
                 # Fall back to CSV parsing for backward compatibility
                 # Support CSVs with header 'path' or 'filepath' plus other columns (timestamp_raw,timestamp_epoch)
                 with open(args.file_list, newline='', encoding='utf-8') as csvfile:
                     sample = csvfile.read(2048)
                     csvfile.seek(0)
                     try:
                         has_header = csv.Sniffer().has_header(sample)
                     except Exception:
                         has_header = False
                     if has_header:
                         reader = csv.DictReader(csvfile)
                         for row in reader:
                             # Prefer 'path' or 'filepath' column
                             fp = None
                             if isinstance(row, dict):
                                 fp = row.get('path') or row.get('filepath') or row.get('file')
                             if not fp:
                                 continue
                             fp_str = os.path.expanduser(str(fp).strip())
                             if not os.path.isabs(fp_str):
                                 base_dir = args.input_dir if getattr(args, 'input_dir', None) else os.getcwd()
                                 fp_str = os.path.join(base_dir, fp_str)
                             entry = os.path.abspath(fp_str)
                             files_from_list.append(entry)
                     else:
                         reader = csv.reader(csvfile)
                         for row in reader:
                             for item in row:
                                 entry = item.strip()
                                 if not entry:
                                     continue
                                 entry = os.path.expanduser(entry)
                                 if not os.path.isabs(entry):
                                     base_dir = args.input_dir if getattr(args, 'input_dir', None) else os.getcwd()
                                     entry = os.path.join(base_dir, entry)
                                 entry = os.path.abspath(entry)
                                 files_from_list.append(entry)
        except Exception as e:
            logging.error(f"Error reading file list {args.file_list}: {e}")
            sys.exit(1)

        if not files_from_list:
            logging.error(f"Error: {args.file_list} contains no valid file paths.")
            sys.exit(1)

    # Validate and adjust input_dir when no file-list was provided
    input_dir_provided = bool(args.input_dir)
    if files_from_list is None:
        if not input_dir_provided:
            logging.error("Error: --input-dir is required unless --file-list is provided.")
            sys.exit(1)
        input_path = Path(args.input_dir)
        if args.slack_data_root:
            files_subdir = input_path / "files"
            if files_subdir.is_dir():
                args.input_dir = str(files_subdir)
                logging.info(f"Using 'files' subdirectory: {args.input_dir}")
            else:
                logging.error(f"Error: No 'files' subdirectory found in {args.input_dir}.")
                sys.exit(1)
        else:
            input_path = Path(args.input_dir)
    if getattr(args, "slack_data_root", None):
        slack_data_root = Path(args.slack_data_root)
        if not slack_data_root.exists() or not slack_data_root.is_dir():
            logging.error(f"Error: Slack data directory {args.slack_data_root} not found or not a directory.")
            sys.exit(1)
        # Prefer the standard 'files' subdirectory if present
        files_subdir = slack_data_root / "files"
        if files_subdir.is_dir():
            args.input_dir = str(files_subdir)
            logging.info(f"Using Slack 'files' subdirectory: {args.input_dir}")
        else:
            # Fall back to the provided slack root itself (useful if user points at a channel dir)
            args.input_dir = str(slack_data_root)
            logging.info(f"Using Slack data directory: {args.input_dir}")

        # Propagate into file_card_generator so file_card_generator.get_original_timestamp()
        # can resolve messages.json / users.json relative to the same slack export root.
        try:
            file_card_generator.slack_data_root = Path(args.slack_data_root).expanduser().resolve()
        except Exception:
            logging.warning("Failed to set file_card_generator.slack_data_root; continuing without it.")

    # Determine base name used for default output dir / pdf name
    if files_from_list is not None:
        input_dir_name = os.path.splitext(os.path.basename(args.file_list))[0]
    else:
        input_dir_name = os.path.basename(os.path.normpath(args.input_dir))

    # Set default output_dir if not specified
    if not args.output_dir:
        # Use the base name of the input directory or file-list for the default output directory
        args.output_dir = f"{input_dir_name}_{args.page_size}"
        logging.info(f"Using default output directory: {args.output_dir}")
    else:
        args.output_dir = f"{args.output_dir}/{args.page_size}"

    output_path_obj = Path(args.output_dir)
    output_dir_name = output_path_obj.name
    logging.info(f"Output directory will be: {output_dir_name}")
    # Compute pdf_name consistently
    if getattr(args, "cards_per_chunk", 0) and args.cards_per_chunk > 0:
        pdf_name = None
        logging.info("cards_per_chunk specified; skipping creation of a top-level combined PDF (chunk-level PDFs will be created).")
    else:
        if not args.pdf_output_name:
            # if no PDF output name is provided, use a default name
            # the default name is based on the input directory name and page size
            # but we want to make sure pdf_name has the extension ".pdf"
            # and we want input_dir_name as used here to have whitespace replaced by _
            pdf_name = f"{input_dir_name.replace(' ', '_')}_combined_{args.page_size}.pdf"
            logging.info(f"No PDF output name provided, using default: {pdf_name}")
        elif args.pdf_output_name.endswith('.pdf'):
            tmp_name = args.pdf_output_name.rsplit('.', 1)[0]
            pdf_name = f"{tmp_name}_combined_{args.page_size}.pdf"
        else:
            pdf_name = f"{args.pdf_output_name}_combined_{args.page_size}.pdf"

    if pdf_name:
        pdf_path = str(output_path_obj / pdf_name)
        logging.info(f"PDF Name will be {pdf_name}")
        logging.info(f"PDF will be saved at: {pdf_path}")
    else:
        pdf_path = None
        logging.info("No top-level combined PDF will be generated due to chunked output.")

    logging.info(f"Will generate file cards in: {args.output_dir}")
    logging.info(f"Output PDF name: {pdf_name}")
    
    # pick the border color from the command line
    border_color_parts = re.split(r'[,\s]+', args.border_color.strip())
    t_border_color = tuple(map(int, border_color_parts))

    if args.metadata_text:
        args.metadata_text = _decode_metadata_text(args.metadata_text)

    # Generate file cards either from the provided list or from a directory
    if files_from_list is not None:
        build_file_cards_from_list(
            files_from_list,
            args.output_dir,
            args.cmyk_mode,
            args.page_size,
            exclude_file_path=exclude_file_path,
            exclude_exts=exclude_exts,
            border_color=t_border_color,
            border_inch_width=args.border_inch_width,
            include_video_frames=args.include_video_frames,
            metadata_text=args.metadata_text,
            cards_per_chunk=args.cards_per_chunk,
            pdf_name=pdf_name,
            delete_cards_after_pdf=args.delete_cards_after_pdf
        )
    else:
        build_file_cards_from_directory(
            args.input_dir,
            args.output_dir,
            args.cmyk_mode,
            args.page_size,
            exclude_file_path=exclude_file_path,
            exclude_exts=exclude_exts,
            border_color=t_border_color,
            border_inch_width=args.border_inch_width,
            include_video_frames=args.include_video_frames,
            max_depth=args.max_depth,
            metadata_text=args.metadata_text,
            cards_per_chunk=args.cards_per_chunk,  # <--- Pass chunk size
            pdf_name=pdf_name,
            delete_cards_after_pdf=args.delete_cards_after_pdf
        )

    # Report summary
    output_path = Path(args.output_dir)
    # Include chunk subdirectories when counting card files using the canonical glob patterns
    # matched = set()
    # for pattern in global_glob_pattern:
    #     for p in output_path.rglob(pattern):
    #         if p.is_file():
    #             try:
    #                 matched.add(p.resolve())
    #             except Exception:
    #                 matched.add(p)
    #card_files = get_non_dot_card_files(output_path)
    logging.info(f"Summary +++++++++++++++++++++++++++++")
    logging.info(f"Output directory: {os.path.abspath(args.output_dir)}")
    logging.info(f"Number of card files generated: {total_files_handled_count}")
    # if card_files:
    #     #logging.info(f"Generated {len(card_files)} card files")
    #     # Print in 3 columns
    #     col_count = 3
    #     names = [f.name for f in card_files]
    #     max_len = max((len(name) for name in names), default=0)
    #     term_width = shutil.get_terminal_size((120, 20)).columns
    #     col_width = max_len + 2
    #     cols = min(col_count, max(1, term_width // col_width))
    #     rows = (len(names) + cols - 1) // cols
    #     for row in range(rows):
    #         line = "".join(names[row + rows * col].ljust(col_width) for col in range(cols) if row + rows * col < len(names))
    #         #logging.info(line)

    # Assemble cards into a PDF if requested
    if pdf_name:
        logging.info(f"Assembling cards into PDF: {pdf_name}")
        width, height = parse_page_size(args.page_size)
        
        # For chunked output we assemble chunk PDFs below; skip assembling a top-level PDF here to avoid empty PDFs.
        
        # Determine chunking
        cards_per_chunk = getattr(args, "cards_per_chunk", 0) or 0
        output_dir_path = Path(args.output_dir)

        # If chunked, skip top-level assembly (chunks were assembled during processing)
        if cards_per_chunk and cards_per_chunk > 0:
            logging.info("cards_per_chunk specified; chunk PDFs were assembled during processing; skipping top-level combined PDF.")
        else:
            # First assemble the combined PDF from the generated cards
            try:
                assemble_cards_to_pdf(args.output_dir, pdf_path, (width, height))
                logging.info(f"Assembled top-level PDF: {pdf_path}")
            except Exception as e:
                logging.error(f"Error assembling top-level PDF: {e}")
                logging.error("Traceback:\n" + traceback.format_exc())

            # Then, if requested, delete the individual card image files
            if args.delete_cards_after_pdf and cards_per_chunk == 0:
                logging.info("Deleting individual card files after PDF creation...")
                output_dir_path = Path(args.output_dir)
                # Collect both single-card and per-frame card outputs
                delete_patterns = global_glob_pattern
                deleted = 0
                for pattern in delete_patterns:
                    for card_file in output_dir_path.glob(pattern):
                        # Skip the combined PDF if it ever matched (it shouldn't with these patterns)
                        if pdf_path and Path(card_file).resolve() == Path(pdf_path).resolve():
                            continue
                        try:
                            card_file.unlink()
                            deleted += 1
                            logging.debug(f"Deleted: {card_file}")
                        except Exception as e:
                            logging.error(f"Error deleting {card_file}: {e}")
                logging.info(f"Card files cleanup complete. Deleted {deleted} files.")

