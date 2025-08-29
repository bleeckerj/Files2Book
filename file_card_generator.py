import os
import time
import re
import bs4
import numpy as np
from datetime import datetime
import hashlib
import mimetypes
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pillow_heif import register_heif_opener
import io
import math
import textwrap
import zipfile
import bz2
import gzip
import textwrap
from bs4 import BeautifulSoup

try:
    from fitparse import FitFile
    FITPARSE_AVAILABLE = True
except ImportError:
    FITPARSE_AVAILABLE = False
import binascii
import json
from pdf2image import convert_from_path
import gpxpy
import cv2

# Patch for Python 3.13 compatibility
import collections
if not hasattr(collections, 'MutableMapping'):
    import collections.abc
    collections.MutableMapping = collections.abc.MutableMapping

import requests
import dotenv
import polyline
import logging
import traceback
import random
from pillow_textbox import draw_text_box

Image.MAX_IMAGE_PIXELS = 500_000_000  # or any large number
#Image.MAX_IMAGE_PIXELS = None  # disables the limit (use with caution)

register_heif_opener()


# Initialize mimetypes
mimetypes.init()

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s - %(name)s %(filename)s@%(lineno)d - %(message)s'
)

# Allow optional global Slack export root (can be set by create_file_cards.py or via env SLACK_DATA_DIR)
slack_data_root = None
# _env_slack = os.getenv("SLACK_DATA_DIR") or os.getenv("SLACK_ROOT")
# if _env_slack:
#     try:
#         SLACK_DATA_ROOT = Path(_env_slack).expanduser().resolve()
#     except Exception:
#         SLACK_DATA_ROOT = None

logging.getLogger("pdf2image").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("img2pdf").setLevel(logging.WARNING)

# Try to import fontTools for font metadata
try:
    from fontTools import ttLib
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False
    logging.warning("fontTools not available. Font metadata will be limited.")


def wrap_text_by_pixel(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def round_image_corners(img, radius):
    # Ensure img is RGBA
    img = img.convert("RGBA")
    w, h = img.size
    # Create mask
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    # Apply mask
    img.putalpha(mask)
    return img

def scale_image(image, scale_factor):
    """Scale a PIL image by a given scale factor (e.g., 0.95 for 95%)."""
    if image is None or scale_factor <= 0:
        return None
    w, h = image.size
    new_w = max(1, int(w * scale_factor))
    new_h = max(1, int(h * scale_factor))
    return image.resize((new_w, new_h), Image.LANCZOS)

# Define file type groups with recognizable icons
FILE_TYPE_GROUPS = {
    'code': {
        'extensions': {'.patch', '.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.sh', '.rb', '.swift', '.php', '.go'},
        'icon': "< / >",
        'color': (251, 64, 55)  # HEX: fb4037
    },
    'data': {
        'extensions': {'.json', '.csv', '.xml', '.yaml', '.yml', '.toml', '.ini'},
        'icon': "{ }",
        'color': (210, 255, 66)  # HEX: d2ff42
    },
    'spreadsheet': {
        'extensions': {'.xlsx', '.xls', '.numbers'},
        'icon': "SPREADSHEET",
        'color': (255, 93, 153)  # HEX: 686974
    },
    'document': {
        'extensions': {'.doc', '.docx','.odt','.tex'},
        'icon': "DOC",
        'color': (123, 17, 116)  # HEX: 6b6d67
    },
    'pdf': {
        'extensions': {'.pdf'},
        'icon': "PDF",
        'color': (69, 137, 119)  # HEX: 458977
    },
    'presentation': {
        'extensions': {'.ppt', '.pptx', '.odp', '.key'},
        'icon': "DECK OF SLIDES",
        'color': (166, 0, 245)  # HEX: #a600f5
    },
    'text': {
        'extensions': {'.txt', '.md', '.rtf', '.mdx'},
        'icon': "TEXT",
        'color': (101, 0, 237)  # HEX: 6500ed
    },
    'archive': {
        'extensions': {'.zip', '.tar', '.gz', '.bz2', '.rar', '.7z'},
        'icon': "ZIP",
        'color': (128, 128, 38)  # HEX: 808026
    },
    'executable': {
        'extensions': {'.exe', '.bin', '.app', '.sh', '.bat', '.dll', '.so', '.dylib'},
        'icon': "EXE",
        'color': (0, 0, 0)  # HEX: 000000
    },
    'binary': {
        'extensions': {'.hex', '.bin', '.dat', '.dfu', '.oci'},
        'icon': "BIN",
        'color': (252, 252, 75)  # HEX: fcfc4a
    },
    'font': {
        'extensions': {'.ttf', '.otf', '.woff', '.woff2', '.eot'},
        'icon': "FONT",
        'color': (34, 153, 84)  # HEX: #229954
    },
    'gps': {
        'extensions': {'.gpx', '.fit', '.tcx'},
        'icon': "GPS",
        'color': (123, 156, 116)  # HEX: 33A1FD
    },
    'log': {
        'extensions': {'.log', '.txt', '.out'},
        'icon': "LOG",
        'color': (0, 0, 0)  # HEX: 000000
    },
    'movie': {
        'extensions': {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm'},
        'icon': "MOVIE",
        'color': (42, 219, 61)  # HEX: 2adb3d
    },
    'image': {
        'extensions': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp'},
        'icon': "IMAGE",
        'color': (0, 244, 240)  # HEX: 00f4f0
    },
    'cad': {
        'extensions': {'.stp', '.step', '.igs', '.iges', '.stl', '.dxf', '.obj'},
        'icon': "CAD",
        'color': (45, 150, 230)  # HEX: 2D96E6
    }
}

def scale_image_by_percent(image, percent):
    """Scale a PIL image by a given percentage (e.g., percent=0.95 for 95%)."""
    if image is None or percent <= 0:
        return None
    w, h = image.size
    new_w = max(1, int(w * percent))
    new_h = max(1, int(h * percent))
    return image.resize((new_w, new_h), Image.LANCZOS)

def get_file_type_info(file_path):
    """Determine file type group and icon information."""
    ext = file_path.suffix.lower()
    #logging.debug(f"ext={ext}")
    # Check if the extension is in any of our groups
    for group, info in FILE_TYPE_GROUPS.items():
        if ext in info['extensions']:
            #logging.debug(f"Found group {group} for extension {ext} for file {file_path}")
            return {
                'group': group,
                'icon': info['icon'],
                'color': info['color']
            }
    # If not found, try to use mimetype to determine a general type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        if mime_type.startswith('text/'):
            return {
                'group': 'text',
                'icon': "TXT",
                'color': (216, 71, 151)  #  
            }
        elif mime_type.startswith('application/'):
            return {
                'group': 'application',
                'icon': "APP",
                'color': (238, 97, 35)  # Darker red
            }
    # Default for unknown types
    return {
        'group': 'unknown',
        'icon': "FILE",
        'color': (250, 0, 63)  # Medium gray
    }

def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_file_hash(file_path, algorithm='md5', block_size=65536):
    """Calculate hash of file contents."""
    hash_obj = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            hash_obj.update(block)
    return hash_obj.hexdigest()[:10]  # First 10 chars for brevity


def preview_html_content(file_path, max_lines=5, max_line_length=40):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        lines = []
        for i, line in enumerate(text.splitlines()):
            if i >= max_lines:
                break
            wrapped = textwrap.wrap(line.strip(), width=max_line_length)
            if not wrapped:
                lines.append('')
            else:
                lines.extend(wrapped)
        return lines
    except Exception:
        return None

def preview_text_content(file_path, max_lines=5, max_line_length=40):
    """Get a preview of text content if the file is text-based, wrapping long lines."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                wrapped = textwrap.wrap(line.rstrip('\n'), width=max_line_length)
                if not wrapped:
                    lines.append('')
                else:
                    lines.extend(wrapped)
            return lines
    except Exception:
        return None

def get_original_timestamp(file_path):
    """Try to find the original timestamp for a file from messages.json in the parent directory."""
    parent = file_path.parent
    messages_json = slack_data_root / "messages.json"
    if not messages_json.exists():
        return None
    try:
        with open(messages_json, 'r', encoding='utf-8', errors='ignore') as f:
            messages = json.load(f)
        for msg in messages:
            if 'files' in msg:
                for fobj in msg['files']:
                    # Match by filename
                    if fobj.get('name') == file_path.name:
                        # Prefer human-readable timestamp if available
                        ts_human = msg.get('ts_human') or fobj.get('ts_human')
                        if ts_human:
                            try:
                                # Try to parse as datetime
                                return datetime.strptime(ts_human, "%Y-%m-%d %H:%M:%S")
                            except Exception:
                                return ts_human  # Return as string if parsing fails
                        ts = fobj.get('timestamp') or fobj.get('created') or msg.get('ts')
                        if ts:
                            try:
                                return datetime.fromtimestamp(float(ts))
                            except Exception:
                                pass
        return None
    except Exception:
        return None

def get_zip_preview(file_path, max_files=40):
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            names = z.namelist()
            if len(names) == 1:
                # If only one file, extract and show hex preview
                with z.open(names[0]) as f:
                    data = f.read(1024)
                hex_lines = []
                for i in range(0, len(data), 16):
                    chunk = data[i:i+16]
                    hexstr = ' '.join(f"{b:02X}" for b in chunk)
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                    hex_lines.append(f"{i:08X}: {hexstr:<48} {ascii_str}")
                return [f"ZIP: 1 file ({names[0]})"] + hex_lines
            # More than one file: list all, then hex dump largest
            file_infos = [(name, z.getinfo(name).file_size) for name in names]
            file_infos.sort(key=lambda x: x[1], reverse=True)
            largest_name, largest_size = file_infos[0]
            with z.open(largest_name) as f:
                data = f.read(1024)
            hex_lines = []
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hexstr = ' '.join(f"{b:02X}" for b in chunk)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                hex_lines.append(f"{i:08X}: {hexstr:<48} {ascii_str}")
            listing = [f"ZIP: {len(names)} files"] + [f"  {name} ({size} bytes)" for name, size in file_infos[:max_files]]
            listing.append(f"\nLargest file: {largest_name} ({largest_size} bytes) hex preview:")
            return listing + hex_lines
    except Exception as e:
        return [f"ZIP error: {e}"]

def get_bz2_preview(file_path, max_bytes=1024):
    try:
        with bz2.open(file_path, 'rb') as f:
            data = f.read(max_bytes)
        hex_lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hexstr = ' '.join(f"{b:02X}" for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            hex_lines.append(f"{i:08X}: {hexstr:<48} {ascii_str}")
        return ["BZ2 (hex preview):"] + hex_lines
    except Exception as e:
        return [f"BZ2 error: {e}"]

def get_gz_preview(file_path, max_bytes=1024, preview_box=None):
    import mimetypes
    try:
        with gzip.open(file_path, 'rb') as f:
            data = f.read(max_bytes * 10)  # Read more for image/text detection
        # Guess file type from original filename if possible
        orig_name = Path(file_path).stem
        ext = Path(orig_name).suffix.lower()
        # Try image preview
        if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.heic', '.heif','.webp'} and preview_box:
            try:
                img = Image.open(io.BytesIO(data))
                img.thumbnail(preview_box)
                return None, img, None
            except Exception:
                pass
        # Try text preview
        mime, _ = mimetypes.guess_type(orig_name)
        if mime and mime.startswith('text'):
            try:
                text = data.decode(errors='ignore')
                lines = text.splitlines()[:40]
                return lines, None, None
            except Exception:
                pass
        # Fallback: hex preview
        hex_lines = []
        for i in range(0, min(len(data), max_bytes), 16):
            chunk = data[i:i+16]
            hexstr = ' '.join(f"{b:02X}" for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            hex_lines.append(f"{i:08X}: {hexstr:<48} {ascii_str}")
        return hex_lines, None, None
    except Exception as e:
        return [f"GZ error: {e}"], None, None

def is_mostly_text_or_html(file_path, chunk_size=4096):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
        try:
            text = chunk.decode('utf-8')
        except UnicodeDecodeError:
            text = chunk.decode('latin-1')
        printable = sum(c.isprintable() or c.isspace() for c in text)
        ratio = printable / max(1, len(text))
        html_like = any(tag in text.lower() for tag in ['<html', '<body', '<div', '<span', '<head', '<title', '<p>'])
        # Consider as text if >90% printable or contains HTML tags
        return ratio > 0.9 or html_like
    except Exception:
        return False


def get_hex_preview(file_path, max_bytes=1024):
    try:
        with open(file_path, 'rb') as f:
            data = f.read(max_bytes)
        hex_lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hexstr = ' '.join(f"{b:02X}" for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            hex_lines.append(f"{i:08X}: {hexstr:<48} {ascii_str}")
        return hex_lines
    except Exception as e:
        return [f"Hex error: {e}"]

def get_fit_preview(file_path, max_records=40):
    if not FITPARSE_AVAILABLE:
        return ["fitparse not installed"]
    try:
        fitfile = FitFile(str(file_path))
        lines = []
        for i, record in enumerate(fitfile.get_messages()):
            if i >= max_records:
                break
            lines.append(f"{record.get('name', 'Record')}: {record}")
        if not lines:
            lines = ["No records found"]
        return lines
    except Exception as e:
        return [f"FIT error: {e}"]

def get_fit_summary_preview(file_path):
    if not FITPARSE_AVAILABLE:
        return ["fitparse not installed"], {}
    try:
        fitfile = FitFile(str(file_path))
        summary = []
        meta = {}
        # Try to extract session/activity summary
        for msg in fitfile.get_messages('session'):
            fields = {d.name: d.value for d in msg}
            summary.append(f"Session: {fields.get('sport', 'N/A')} {fields.get('sub_sport', '')}")
            if 'start_time' in fields:
                summary.append(f"Start: {fields['start_time']}")
                meta['start_time'] = fields['start_time']
            if 'total_timer_time' in fields:
                summary.append(f"Duration: {fields['total_timer_time']:.1f} sec")
            if 'total_distance' in fields:
                summary.append(f"Distance: {fields['total_distance']/1000:.2f} km")
            if 'total_ascent' in fields:
                summary.append(f"Ascent: {fields['total_ascent']} m")
            if 'avg_speed' in fields:
                summary.append(f"Avg Speed: {fields['avg_speed']*3.6:.2f} km/h")
            if 'max_speed' in fields:
                summary.append(f"Max Speed: {fields['max_speed']*3.6:.2f} km/h")
            if 'total_calories' in fields:
                summary.append(f"Calories: {fields['total_calories']}")
            summary.append("")
        # If no session, try activity
        if not summary:
            for msg in fitfile.get_messages('activity'):
                fields = {d.name: d.value for d in msg}
                summary.append(f"Activity: {fields.get('type', 'N/A')}")
                if 'timestamp' in fields:
                    summary.append(f"Timestamp: {fields['timestamp']}")
                    meta['timestamp'] = fields['timestamp']
                summary.append("")
        # GPS points summary
        gps_points = []
        for record in fitfile.get_messages('record'):
            lat = None
            lon = None
            for d in record:
                if d.name == 'position_lat':
                    lat = d.value
                elif d.name == 'position_long':
                    lon = d.value
            if lat is not None and lon is not None:
                lat = lat * (180.0 / 2**31)
                lon = lon * (180.0 / 2**31)
                gps_points.append((lat, lon))
        if gps_points:
            summary.append(f"GPS Points: {len(gps_points)}")
            summary.append(f"Start: ({gps_points[0][0]:.5f}, {gps_points[0][1]:.5f})")
            summary.append(f"End:   ({gps_points[-1][0]:.5f}, {gps_points[-1][1]:.5f})")
            # Optionally show a few sample points
            if len(gps_points) > 2:
                summary.append(f"Sample: ({gps_points[len(gps_points)//2][0]:.5f}, {gps_points[len(gps_points)//2][1]:.5f})")
        # Fallback: show number of records
        n_records = sum(1 for _ in fitfile.get_messages('record'))
        summary.append(f"Records: {n_records}")
        meta['records'] = n_records
        # Add all metadata fields from file header
        if hasattr(fitfile, 'file_id'):
            for k, v in fitfile.file_id.items():
                summary.append(f"{k}: {v}")
                meta[k] = v
        return summary[:40], meta
    except Exception as e:
        return [f"FIT error: {e}"], {}

def get_pdf_preview(file_path, box_w, box_h):
    try:
        # First, get the total number of pages
        from pdf2image import convert_from_path
        import numpy as np
        #logging.debug(f"Attempting to extract PDF preview: {file_path}")
        all_pages = convert_from_path(str(file_path))
        n_total = len(all_pages)
        logging.info(f"PDF {file_path} page count is {n_total} pages")

        if n_total == 0:
            logging.warning(f"No pages found in PDF: {file_path}")
            return None

        # Cap how many pages we consider for previews to avoid extreme CPU and tiny thumbs
        max_preview_cap = min(n_total, 42)

        best_score = -1
        best_config = None

        # Try all candidate preview counts (1..max_preview_cap)
        for total_count in range(1, max_preview_cap + 1):
            # Choose evenly distributed page indices for this total_count (always include first page)
            indices = [0]
            if total_count > 1 and n_total > 1:
                remaining = np.linspace(1, n_total - 1, total_count - 1)
                indices += [int(round(i)) for i in remaining]
            indices = sorted(set(indices))
            selected_pages = [all_pages[i] for i in indices]
            n_pages = len(selected_pages)

            # Evaluate every possible rows partition for this selection
            for rows in range(1, n_pages + 1):
                cols = int(math.ceil(n_pages / rows))
                cell_w = box_w // cols
                cell_h = box_h // rows

                # Ignore impossible cells
                if cell_w <= 0 or cell_h <= 0:
                    continue

                total_used_area = 0
                orientations = []  # True if rotated for best fit, False otherwise

                # For each page, try both orientations and pick the one that uses more area in the cell
                for page in selected_pages:
                    w, h = page.width, page.height

                    # No-rotate fit
                    scale_no = min(cell_w / w, cell_h / h) if w and h else 0
                    used_w_no = int(max(0, int(w * scale_no)))
                    used_h_no = int(max(0, int(h * scale_no)))
                    area_no = used_w_no * used_h_no

                    # Rotated fit (90 degrees)
                    scale_rot = min(cell_w / h, cell_h / w) if w and h else 0
                    used_w_rot = int(max(0, int(h * scale_rot)))
                    used_h_rot = int(max(0, int(w * scale_rot)))
                    area_rot = used_w_rot * used_h_rot

                    if area_rot > area_no:
                        total_used_area += area_rot
                        orientations.append(True)
                    else:
                        total_used_area += area_no
                        orientations.append(False)

                # Keep the configuration with the highest total used thumbnail area
                score = total_used_area + n_pages * 10000  # Bonus: 10,000 per page shown

                if score > best_score:
                    best_score = score
                    best_config = {
                        'indices': indices,
                        'rows': rows,
                        'cols': cols,
                        'cell_w': cell_w,
                        'cell_h': cell_h,
                        'selected_pages': selected_pages,
                        'orientations': orientations
                    }

        if not best_config:
            logging.warning(f"Could not determine a layout for PDF: {file_path}")
            return None

        # Build thumbnails using the chosen layout and orientations
        selected_pages = best_config['selected_pages']
        best_rows = best_config['rows']
        best_cols = best_config['cols']
        best_thumb_w = best_config['cell_w']
        best_thumb_h = best_config['cell_h']
        orientations = best_config['orientations']

        thumbs = []
        for page, rotate_choice in zip(selected_pages, orientations):
            page = page.copy()
            if rotate_choice:
                page = page.rotate(90, expand=True)
            # Scale the page to fit the cell while preserving aspect ratio
            try:
                thumb = ImageOps.contain(page, (best_thumb_w, best_thumb_h), Image.LANCZOS)
            except Exception:
                # Fallback to thumbnail if ImageOps is not available for some reason
                thumb = page.copy()
                thumb.thumbnail((best_thumb_w, best_thumb_h))
            thumbs.append(thumb)
        grid_img = Image.new('RGB', (box_w, box_h), (255, 255, 255))
        for idx, page in enumerate(thumbs):
            # Default row-major placement: left-to-right, top-to-bottom
            if not orientations[idx]:
                col = idx % best_cols
                row = idx // best_cols
            else:
                # For rotated pages, fill columns left-to-right, each column bottom-to-top
                # This preserves the natural reading order when pages are rotated 90 degrees.
                col = idx // best_rows
                row_in_col = idx % best_rows
                row = best_rows - 1 - row_in_col
            x = col * best_thumb_w + (best_thumb_w - page.width) // 2
            y = row * best_thumb_h + (best_thumb_h - page.height) // 2
            grid_img.paste(page, (x, y))

        return grid_img
    except Exception as e:
        logging.error(f"PDF preview error for {file_path}: {e}")
        return None

def get_image_thumbnail(file_path, box_size=(320, 320), cmyk_mode=False):
    try:
        img = Image.open(file_path)
        # Composite transparent images onto white/light background BEFORE any CMYK conversion
        if img.mode in ("RGBA", "LA"):
            #logging.debug(f"Compositing transparent image onto white background: {file_path.name}")
            background = Image.new("RGBA", img.size, (250, 250, 250))
            background.paste(img, mask=img.split()[-1])
            img = background

        img_w, img_h = img.size
        box_w, box_h = box_size
        # Rotate image if box is portrait and image is landscape
        if box_h > box_w and img_w > img_h:
            img = img.rotate(90, expand=True)
            img_w, img_h = img.size
        # Scale to fit box, maximizing coverage
        scale_factor = min(box_w / img_w, box_h / img_h)
        new_w = int(img_w * scale_factor)
        new_h = int(img_h * scale_factor)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Center in box

        # Set the background color behind the image thumbnail
        if cmyk_mode:
            # Use CMYK equivalent of light gray
            thumb_bg_color = rgb_to_cmyk(250, 250, 250)
            thumb = Image.new('CMYK', (box_w, box_h), thumb_bg_color)
        else:
            thumb = Image.new('RGB', (box_w, box_h), (250, 250, 250))

        x = (box_w - new_w) // 2
        y = (box_h - new_h) // 2
        thumb.paste(img, (x, y))
        return thumb
    except Exception:
        return None

def get_font_preview(file_path, box_w, box_h):
    """
    Generate a preview image for a font file (TTF, OTF).
    
    Args:
        file_path: Path to the font file
        box_w: Width of the preview box
        box_h: Height of the preview box
        
    Returns:
        A PIL Image containing a preview of the font with sample text
    """
    try:
        # Create a white background image
        preview = Image.new('RGB', (box_w, box_h), (255, 255, 255))
        draw = ImageDraw.Draw(preview)
        
        # Try to load the font
        font_path = str(file_path)
        
        # Sample text to display
        sample_text = "The OMATA One. As useful as art."
        pangram = "The quick brown fox jumps over the lazy dog"
        numbers = "0123456789"
        special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>/?"
        
        # Font sizes to display
        sizes = [36, 48, 64, 72]
        
        # Get font metadata if possible
        font_metadata = []
        if FONTTOOLS_AVAILABLE:
            try:
                font = ttLib.TTFont(font_path)
                
                # Try to get font family name
                if 'name' in font:
                    for record in font['name'].names:
                        if record.nameID == 1 and record.isUnicode():  # Font Family name
                            family_name = record.toUnicode()
                            font_metadata.append(f"Family: {family_name}")
                            break
                    
                    for record in font['name'].names:
                        if record.nameID == 2 and record.isUnicode():  # Font Subfamily name
                            style = record.toUnicode()
                            font_metadata.append(f"Style: {style}")
                            break
                            
                    for record in font['name'].names:
                        if record.nameID == 5 and record.isUnicode():  # Version
                            version = record.toUnicode()
                            font_metadata.append(f"Version: {version}")
                            break
            except Exception as e:
                logging.error(f"Could not read font metadata: {e}")
        
        if not font_metadata:
            font_metadata = ["Font: " + os.path.basename(font_path)]
        
        # Draw font metadata
        # Use a much larger font for metadata
        big_metadata_font_size = max(24, int(box_h * 0.02))
        try:
            metadata_font = ImageFont.truetype(font_path, big_metadata_font_size)
        except Exception:
            metadata_font = ImageFont.load_default()
        y_pos = 10
        for line in font_metadata:
            draw.text((10, y_pos), line, fill=(0, 0, 0), font=metadata_font)
            # Increase spacing for big font
            y_pos += big_metadata_font_size + 10
        
        y_pos += 20  # Extra space after metadata
        
        # Draw sample text in different sizes
        for size in sizes:
            try:
                font = ImageFont.truetype(font_path, size)
                text = f"{size}pt: {sample_text}"
                draw.text((10, y_pos), text, fill=(0, 0, 0), font=font)
                y_pos += size + 60
            except Exception as e:
                logging.warning(f"Error loading font at size {size}: {e}")
                # Use default font as fallback
                fallback_font = ImageFont.load_default()
                draw.text((10, y_pos), f"Size {size}pt not available", fill=(255, 0, 0), font=fallback_font)
                y_pos += 80
        
        # Draw numbers and special characters
        try:
            size = 124
            font = ImageFont.truetype(font_path, size)
            draw.text((10, y_pos), numbers, fill=(0, 0, 0), font=font)
            y_pos += size + 60
            
            size=72
            font = ImageFont.truetype(font_path, size)
            draw.text((10, y_pos), special_chars, fill=(0, 0, 0), font=font)
            y_pos += size + 60
        except Exception as e:
            logging.warning(f"Error drawing numbers/special chars: {e}")
        
        # Draw pangram
        try:
            pangram_size = 42
            font = ImageFont.truetype(font_path, pangram_size)
            
            # Wrap text to fit width
            wrapped_text = textwrap.fill(pangram, width=int(box_w / (pangram_size * 0.6)))
            draw.text((10, y_pos), wrapped_text, fill=(0, 0, 0), font=font)
            
            # Move position down based on number of lines
            lines = wrapped_text.count('\n') + 1
            y_pos += (pangram_size + 20) * lines
        except Exception as e:
            logging.warning(f"Error drawing pangram: {e}")


        return preview
    except Exception as e:
        logging.error(f"Error creating font preview: {e}")
        logging.error(traceback.format_exc())
        # Create a fallback image
        fallback = Image.new('RGB', (box_w, box_h), (240, 240, 240))
        draw = ImageDraw.Draw(fallback)
        fallback_font = ImageFont.load_default()
        draw.text((10, 10), f"Font preview not available", fill=(255, 0, 0), font=fallback_font)
        draw.text((10, 30), f"Error: {str(e)}", fill=(255, 0, 0), font=fallback_font)
        return fallback

def get_gpx_preview(file_path, box_w, box_h):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            gpx = gpxpy.parse(f)
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for p in segment.points:
                    points.append((p.longitude, p.latitude))
        if not points:
            return None
        lons, lats = zip(*points)
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        # Normalize and scale
        def scale(val, minv, maxv, size):
            if maxv == minv:
                return size // 2
            return int((val - minv) / (maxv - minv) * (size - 20) + 10)
        img = Image.new('RGB', (box_w, box_h), (245, 245, 245))
        draw = ImageDraw.Draw(img)
        prev = None
        for lon, lat in points:
            x = scale(lon, min_lon, max_lon, box_w)
            y = box_h - scale(lat, min_lat, max_lat, box_h)
            if prev:
                draw.line([prev, (x, y)], fill=(0, 120, 160), width=3)
            prev = (x, y)
        return img
    except Exception:
        return None

def get_video_preview(file_path, box_w, box_h, grid_cols=3, grid_rows=3, rotate_frames_if_portrait=True):
    try:
        cap = cv2.VideoCapture(str(file_path))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            cap.release()
            return None
        # Select frames using a normal distribution (bell curve) centered in the video
        import numpy as np
        num_frames = grid_cols * grid_rows
        mean = frame_count / 2
        stddev = frame_count / 4
        idxs = np.random.normal(loc=mean, scale=stddev, size=num_frames)
        idxs = np.clip(idxs, 0, frame_count - 1)
        idxs = np.round(idxs).astype(int)
        # Ensure unique and sorted indices for visual consistency
        idxs = sorted(set(idxs))
        # If not enough unique frames, fill in with evenly spaced frames
        while len(idxs) < num_frames:
            extra = np.linspace(0, frame_count - 1, num_frames)
            idxs = sorted(set(list(idxs) + list(np.round(extra).astype(int))))
            if len(idxs) > num_frames:
                idxs = idxs[:num_frames]
        thumbs = []
        thumb_w = box_w // grid_cols
        thumb_h = box_h // grid_rows
        portrait_mode = box_h > box_w
        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame)
            # Rotate individual frame if preview box is portrait
            if rotate_frames_if_portrait and portrait_mode and pil_img.width > pil_img.height:
                pil_img = pil_img.rotate(90, expand=True)
            pil_img.thumbnail((thumb_w, thumb_h))
            thumbs.append(pil_img)
        cap.release()
        grid_img = Image.new('RGB', (box_w, box_h), (245, 245, 245))
        for i, thumb in enumerate(thumbs):
            x = (i % grid_cols) * thumb_w + (thumb_w - thumb.width)//2
            y = (i // grid_cols) * thumb_h + (thumb_h - thumb.height)//2
            grid_img.paste(thumb, (x, y))
        #logging.debug(f"Grid size: {grid_img.size} for file {file_path}")
        return grid_img
    except Exception:
        return None

def get_video_frames(file_path, max_frames=9, rotate_frames_if_portrait=True):
    """
    Extracts up to max_frames from the video file and returns them as PIL Images.
    """
    try:
        cap = cv2.VideoCapture(str(file_path))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            cap.release()
            return []
        # Evenly spaced frame indices
        indices = [int(i) for i in np.linspace(0, frame_count - 1, max_frames)]
        frames = []
        portrait_mode = False
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame)
            # Rotate individual frame if preview box is portrait
            if rotate_frames_if_portrait and pil_img.width > pil_img.height:
                pil_img = pil_img.rotate(90, expand=True)
            frames.append(pil_img)
        cap.release()
        return frames
    except Exception:
        logging.warning("Error extracting video frames", exc_info=True)
        return []

# Check for pillow-heif availability
try:
    import pillow_heif
    PILLOW_HEIF_AVAILABLE = True
except ImportError:
    PILLOW_HEIF_AVAILABLE = False

def get_heif_image(file_path):
    if not PILLOW_HEIF_AVAILABLE:
        logging.warning("pillow-heif library is not available. Cannot process HEIC files.")
        return None
    try:
        img = Image.open(file_path)
        logging.info(f"Successfully processed HEIC file using Pillow: {file_path}")
        return img
    except Exception as e:
        logging.error(f"Error processing HEIC file {file_path} with Pillow: {e}")
        return None

def get_fit_gps_preview(file_path, box_w, box_h):
    if not FITPARSE_AVAILABLE:
        return None
    try:
        fitfile = FitFile(str(file_path))
        points = []
        for record in fitfile.get_messages('record'):
            lat = None
            lon = None
            for d in record:
                if d.name == 'position_lat':
                    lat = d.value
                elif d.name == 'position_long':
                    lon = d.value
            if lat is not None and lon is not None:
                # Convert semicircles to degrees
                lat = lat * (180.0 / 2**31)
                lon = lon * (180.0 / 2**31)
                points.append((lon, lat))
        if not points:
            return None
        lons, lats = zip(*points)
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        def scale(val, minv, maxv, size):
            if maxv == minv:
                return size // 2
            return int((val - minv) / (maxv - minv) * (size - 20) + 10)
        img = Image.new('RGB', (box_w, box_h), (245, 245, 245))
        draw = ImageDraw.Draw(img)
        prev = None
        for lon, lat in points:
            x = scale(lon, min_lon, max_lon, box_w)
            y = box_h - scale(lat, min_lat, max_lat, box_h)
            if prev:
                draw.line([prev, (x, y)], fill=(0, 120, 160), width=3)
            prev = (x, y)
        return img
    except Exception:
        return None

MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN', '').strip()
logging.info("Using Mapbox token: %s", MAPBOX_TOKEN if MAPBOX_TOKEN else "Not set")
def downsample_points(points, max_points=100):
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    return points[::step]

def get_mapbox_tile_for_bounds(min_lat, max_lat, min_lon, max_lon, width, height, api_key=None, path_points=None):
    # Ensure the API key is resolved at runtime (avoid referencing MAPBOX_TOKEN at function-definition time)
    if api_key is None:
        api_key = os.getenv('MAPBOX_TOKEN', '').strip()

    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    # Calculate zoom level based on bounding box and image size
    # Reference: https://docs.mapbox.com/help/glossary/zoom-level/
    def lat_rad(lat):
        from math import radians, log, tan, pi
        sin = math.sin(radians(lat))
        return log((1 + sin) / (1 - sin)) / 2
    WORLD_DIM = 256  # Mapbox tile size in pixels
    def zoom_for_bounds(min_lat, max_lat, min_lon, max_lon, width, height):
        # Clamp latitude to avoid math domain errors
        min_lat = max(min_lat, -85.05112878)
        max_lat = min(max_lat, 85.05112878)
        lat_fraction = (lat_rad(max_lat) - lat_rad(min_lat)) / math.pi
        lon_fraction = (max_lon - min_lon) / 360.0
        lat_zoom = math.log2(height / WORLD_DIM / lat_fraction) if lat_fraction > 0 else 20
        lon_zoom = math.log2(width / WORLD_DIM / lon_fraction) if lon_fraction > 0 else 20
        zoom = min(lat_zoom, lon_zoom, 22)
        zoom = max(0, zoom)
        calculated_zoom = float(zoom)
        adjusted_zoom = max(0.0, calculated_zoom - 0.3)  # Adjust zoom to avoid too high resolution
        return adjusted_zoom
    zoom = zoom_for_bounds(min_lat, max_lat, min_lon, max_lon, min(width, 1280), min(height, 1280))

    import urllib.parse
    path_str = ""
    if path_points and len(path_points) > 1:
        path_points = downsample_points(path_points, max_points=100)
        # Mapbox expects [lon,lat] pairs for polyline encoding
        poly_points = [(lat, lon) for lon, lat in path_points]
        encoded = polyline.encode(poly_points)
        encoded_url = urllib.parse.quote(encoded, safe='')
        path_str = f"/path-5+f44-0.7({encoded_url})"
    # Log style info from Mapbox Styles API
    style_username = "darthjulian"
    style_id = "ciwqpkc0s00882qnxuuscegmn"
    style_api_url = f"https://api.mapbox.com/styles/v1/{style_username}/{style_id}?access_token={api_key}"
    try:
        style_resp = requests.get(style_api_url)
        if style_resp.status_code == 200:
            style_json = style_resp.json()
            logging.info(f"Mapbox style name: {style_json.get('name')}")
            logging.info(f"Mapbox style owner: {style_json.get('owner')}")
            logging.info(f"Mapbox style visibility: {style_json.get('visibility')}")
        else:
            logging.warning(f"Could not fetch Mapbox style info: {style_resp.status_code} {style_resp.text}")
    except Exception as e:
        logging.warning(f"Exception fetching Mapbox style info: {e}")
    url = (
       # f"https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/static"
        f"https://api.mapbox.com/styles/v1/darthjulian/ciwqpkc0s00882qnxuuscegmn/static"
        f"{path_str}/{center_lon},{center_lat},{zoom},0,50/{width}x{height}"
        f"?access_token={api_key}"
    )
    resp = requests.get(url)
    logging.info("Mapbox URL: %s", url)
    logging.info("Mapbox zoom: %s", zoom)
    logging.info("Mapbox status: %s", resp.status_code)
    if resp.status_code == 200:
        return Image.open(io.BytesIO(resp.content))
    else:
        logging.error("Mapbox error: %s %s", resp.status_code, resp.text)
        logging.error("Bounds are (%f, %f, %f, %f)", min_lat, max_lat, min_lon, max_lon)
        logging.error("Width: %d, Height: %d", width, height)
        logging.error("Zoom level: %f", zoom)
        exit(-1)  # Exit with error code if Mapbox request fails
    return None


def create_file_info_card(file_path, width=800, height=800, cmyk_mode=False, exclude_file_path=False, border_color=(245, 245, 245), border_inch_width=0.125, include_video_frames=False, metadata_text=None, title=None, metadata=None):
    #logging.debug(f"Creating file info card for {file_path} with size {width}x{height}, cmyk_mode={cmyk_mode}")
    #logging.debug(f"File path: {file_path}, exclude_file_path={exclude_file_path}, border_color={border_color}, border_inch_width={border_inch_width}, include_video_frames={include_video_frames}, metadata_text={metadata_text}")
    original_dt = None
    
    file_info = {}
    ###
    ### Metadata extraction
    ### Push metadata to file_info to get it to render out for the card
    ###
    if metadata is not None and isinstance(metadata, dict):
        file_info.update(metadata)
        
    file_path = Path(file_path)
    # ignore "._*" ".DS_Store" files
    if file_path.name.startswith("._") or file_path.name == ".DS_Store":
        logging.info(f"Ignoring file: {file_path.name}")
        return None
    # Proportional scaling
    base_width = 800
    base_height = 1000
    scale = min(width / base_width, height / base_height)
    #logging.debug(f"Scaling card to {width}x{height} with scale factor {scale:.2f}")
    # Proportional paddings
    border_width = max(2, int(1 * scale))  # Using a more reasonable but still very visible border width
    outer_padding = max(80, int(50 * scale))  # Padding between border and outer edges of content

    # Create the full-sized background image that is the canvas for the preview
    # Use non-alpha modes so downstream PDF assembly doesn't hit alpha issues
    if cmyk_mode:
        # Light background in CMYK
        img = Image.new('CMYK', (width, height), rgb_to_cmyk(250, 250, 250))
    else:
        # Light background in RGB
        img = Image.new('RGB', (width, height), (250, 250, 250))
    draw = ImageDraw.Draw(img)

    # Draw the border around the content area
    # Determine the color mode first to avoid variable reference issues
    rgb_mode = not cmyk_mode
    preview_background_color = (250, 250, 250) if rgb_mode else rgb_to_cmyk(250, 250, 250)
    # Define a reliable black text color for the current mode
    text_black = (0, 0, 0) if rgb_mode else (0, 0, 0, 255)
    if rgb_mode:
        # For RGB mode, use standard black border
        draw.rectangle(
            [outer_padding, outer_padding, width - outer_padding - 1, height - outer_padding - 1],
            outline=(0, 0, 0), 
            width=border_width
        )
    else:
        # For CMYK mode, use solid black (K channel only at 100%) for maximum visibility
        # Draw multiple concentric borders to ensure visibility
        for i in range(0, min(10, border_width), 2):  # Draw up to 5 concentric borders
            draw.rectangle(
                [
                    outer_padding + i,
                    outer_padding + i,
                    width - outer_padding - 1 - i,
                    height - outer_padding - 1 - i
                ],
                outline=(0, 0, 0, 5),  # 100% black in CMYK
                width=max(5, border_width // 5)  # Make each border line thick
            )

    # Proportional font sizes
    title_font_size = int(20 * scale)
    info_font_size = int(15 * scale)  # Smaller font size for metadata
    preview_font_size = int(12 * scale)
    fit_font_size = int(15 * scale)
    # Proportional paddings (keeping the original border_width value)
    icon_space = int((100 + 40) * scale)
    metadata_line_height = int(info_font_size * 1.02)  # Tighter line spacing for metadata
    spacing_between_metadata_and_content_preview = int(20 * scale)
    preview_box_padding = int(2 * scale)
    header_height = int(20 * scale)

    # Add a margin between the header/title and the metadata box
    metadata_top_margin = int(12 * scale)

    # Load fonts
    try:
        title_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", title_font_size)
        info_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", info_font_size)
        preview_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", preview_font_size)
        fit_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", fit_font_size)
    except:
        title_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        preview_font = ImageFont.load_default()
        fit_font = ImageFont.load_default()

    file_type_info = get_file_type_info(file_path)
    logging.info(f"Processing {file_path.name} - Type: {file_type_info['group']}")
    icon = file_type_info['icon']
    ext = file_path.suffix.lower()


    try:
        size = os.path.getsize(file_path)
        modified_time = os.path.getmtime(file_path)
        created_time = os.path.getctime(file_path)
    except (FileNotFoundError, PermissionError):
        size = 0
        modified_time = 0
        created_time = 0

    ##
    ##
    ## START OF SLACK METADATA EXTRACTION
    ## FOR THE CASE WHERE metadata IS NONE
    ##
    ##
    # if metadata is not None, then skip all of this slack stuff..
    # Eventually, it's going to get torn out..
    if metadata is None:

        ##
        ## VERY SLACK SPECIFIC..
        ##
        slack_channel = None
        slack_message_id = None
        slack_user_id = None
        slack_user_name = None
        slack_avatar = None
        slack_shared_date = None
        if slack_data_root:
            # Try to get original timestamp and Slack metadata
            original_dt = get_original_timestamp(file_path)

            parent = slack_data_root.parent if slack_data_root else file_path.parent.parent

            # Determine channel_dir/messages.json:
            # - If SLACK_DATA_ROOT is set and the file_path is inside it, resolve the channel
            #   directory relative to the slack root (expected layout: <slack_root>/<channel>/files/...)
            # - Otherwise, fall back to the previous heuristic (parent.parent)
            try:
                if slack_data_root:
                    p_resolved = Path(file_path).resolve()
                    slack_root_resolved = slack_data_root
                    if str(p_resolved).startswith(str(slack_root_resolved)):
                        rel = p_resolved.relative_to(slack_root_resolved)
                        # Expect at least: <channel>/files/...
                        if len(rel.parts) >= 2 and rel.parts[1] == "files":
                            channel_dir = slack_root_resolved / rel.parts[0]
                        else:
                            # Not the expected layout — fall back to parent.parent
                            channel_dir = parent
                    else:
                        # File not inside configured slack root — fall back
                        channel_dir = slack_data_root
                else:
                    channel_dir = slack_data_root
            except Exception:
                channel_dir = slack_data_root

            messages_json = slack_data_root / "messages.json"
            users_json = parent / "users.json"
            avatars_dir = slack_data_root.parent / "avatars_40x40"
            #user_profile = None
            if messages_json.exists():
                try:
                    with open(messages_json, 'r', encoding='utf-8', errors='ignore') as f:
                        messages = json.load(f)
                    for msg in messages:
                        if 'files' in msg:
                            for fobj in msg['files']:
                                if fobj.get('name') == file_path.name:
                                    slack_channel = channel_dir.name
                                    slack_message_id = msg.get('client_msg_id') or msg.get('ts')
                                    slack_user_id = msg.get('user') or msg.get('username') or fobj.get('user')
                                    slack_shared_date = None
                                    ts = fobj.get('timestamp') or fobj.get('created') or msg.get('ts')
                                    if ts:
                                        try:
                                            slack_shared_date = datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')
                                        except Exception:
                                            slack_shared_date = str(ts)
                                    # Resolve avatar from local 'avatars' directory
                                    avatars_dir = slack_data_root.parent / "avatars"
                                    #logging.debug(f"Looking for avatars in: {avatars_dir}")
                                    if slack_user_id and avatars_dir.exists():
                                        avatar_path = avatars_dir / f"{slack_user_id}.jpg"
                                        #logging.debug(f"Checking avatar path: {avatar_path}")
                                        if avatar_path.exists():
                                            slack_avatar = str(avatar_path)
                                    #logging.debug(f"Found avatar for {slack_user_id}: {slack_avatar}")
                                    # Resolve user name from users.json
                                    if users_json.exists() and slack_user_id:
                                        try:
                                            with open(users_json, 'r', encoding='utf-8', errors='ignore') as uf:
                                                users = json.load(uf)
                                            for user in users:
                                                if user.get('id') == slack_user_id or user.get('name') == slack_user_id:
                                                    slack_user_name = user.get('real_name') or user.get('profile', {}).get('real_name') or user.get('name')
                                                    break
                                        except Exception as e:
                                            logging.error(f"Error reading users.json: {e}")
                                    break
                        if slack_channel:
                            break
                except Exception:
                    pass
                
                
                
        # Step 2: If EXIF-capable, try to read EXIF data
        exif_data = None
        exif_candidate = False
        ext = Path(file_path).suffix.lower()


        # Step 1: Check if file is an EXIF-capable image type
        exif_candidate = ext in {'.jpg', '.jpeg', '.tif', '.tiff'}
        if exif_candidate:
            logging.debug(f"File {file_path} is an EXIF-capable image type: {ext}")
            try:
                exif_img = Image.open(file_path)
                if hasattr(exif_img, '_getexif'):
                    exif_data = exif_img._getexif()
                elif hasattr(exif_img, 'getexif'):
                    exif_data = exif_img.getexif()
                try:
                    exif_img.close()
                except Exception:
                    pass
            except Exception:
                exif_data = None
        if exif_data is not None:
            logging.debug(f"EXIF data found: {exif_data is not None}")
            logging.debug(f"EXIF data : {exif_data.get(36867)}")

        if exif_data is not None:
            date_time_original = exif_data.get(36867)
            logging.info(f"EXIF DateTimeOriginal: {date_time_original}")
            if date_time_original:
                file_info['DateTimeOriginal'] = date_time_original
                logging.debug(f"NOW EXIF DateTimeOriginal: {date_time_original}")
                logging.debug(f"File info before DateTimeOriginal check: {file_info}")
        # If DateTimeOriginal is present, skip other date fields
        logging.debug(f"File info before DateTimeOriginal check: {file_info}")
        if 'DateTimeOriginal' in file_info and file_info['DateTimeOriginal']:
            logging.debug(f"DateTimeOriginal found: {file_info['DateTimeOriginal']}")
            pass
        elif original_dt is not None:
            file_info['Original Date'] = original_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            file_info['Modified'] = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
            file_info['Created'] = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build metadata with Slack Channel at the top if present
        if slack_channel:
            file_info['Slack Channel'] = slack_channel
        file_info['Type'] = f"{file_path.suffix[1:].upper()} ({file_type_info['group']})"
        file_info['Size'] = format_file_size(size)
        if slack_message_id:
            file_info['Message ID'] = slack_message_id
        if slack_user_name:
            file_info['Shared By'] = slack_user_name
        if slack_shared_date:
            file_info['Shared Date'] = slack_shared_date

        
        # Move Name to the end
        if not exclude_file_path:
            file_info['Filepath'] = "/".join(Path(file_path).parts[-3:])

    ##
    ##
    ## END IF NO METADATA
    ##
    ##
    
    # --- Custom metadata_text support (multiline, wrapped) ---
    # If metadata_text is provided, use it instead of the default metadata lines.
    custom_metadata_text = None
    if metadata_text is not None:
        if isinstance(metadata_text, str):
            custom_metadata_text = metadata_text
        elif isinstance(metadata_text, (list, tuple)):
            custom_metadata_text = "\n".join(str(x) for x in metadata_text)
        else:
            custom_metadata_text = str(metadata_text)
        # if exclude_file_path is False:
        #     custom_metadata_text = f"{custom_metadata_text}\n\n{str(file_path.parent)}"
    # Compute metadata block height
    # Default: number of key/value pairs * line height
    content_area_width_for_wrap = width - 2 * outer_padding
    if custom_metadata_text:
        # Measure single-line height and derive spacing to match metadata_line_height advance
        tmp_img = Image.new("RGBA", (width, height))
        tmp_draw = ImageDraw.Draw(tmp_img)
        l, t, r, b = tmp_draw.textbbox((0, 0), "Ag", font=info_font)
        single_h = b - t
        custom_line_spacing_px = max(0, int(metadata_line_height - single_h))

        # Use the SAME padding for measure and draw
        meta_pad = int(30 * scale)

        # Choose background colors matching the target image mode
        bg_rgb = (245, 245, 245)
        bg_outline_rgb = (200, 200, 200)
        if cmyk_mode:
            bg_fill = rgb_to_cmyk(*bg_rgb)
            bg_outline = rgb_to_cmyk(*bg_outline_rgb)
        else:
            bg_fill = bg_rgb
            bg_outline = bg_outline_rgb

        # Measure wrapped text height (text only), then add vertical padding
        measure = draw_text_box(
            tmp_draw,
            custom_metadata_text,
            info_font,
            box=(outer_padding, outer_padding + header_height, content_area_width_for_wrap, height - (outer_padding + header_height)),
            padding=meta_pad,
            line_spacing=custom_line_spacing_px,
            align="center",
            v_align="top",
            fill=bg_fill,
            stroke_fill=bg_outline,
            stroke_width=1
        )
        metadata_height = measure["used_size"][1] + (meta_pad * 2)
    else:
        metadata_lines = len(file_info)
        metadata_height = metadata_lines * metadata_line_height
    logging.debug(f"Metadata height: {metadata_height}")
    # Content area dimensions, accounting for outer padding
    content_area_left = outer_padding
    content_area_right = width - outer_padding
    content_area_width = content_area_right - content_area_left
    
    # Preview box within the content area
    preview_box_left = content_area_left + int(content_area_width * 0.005)
    preview_box_right = content_area_right - int(content_area_width * 0.005)
    preview_box_top = outer_padding + header_height + metadata_top_margin + metadata_height + spacing_between_metadata_and_content_preview
    logging.debug(f"Preview box top: {preview_box_top}, icon space: {icon_space}, metadata height: {metadata_height}")
    preview_box_bottom = height - outer_padding - int(30 * scale)
    preview_box_height = preview_box_bottom - preview_box_top - preview_box_padding * 2
    max_line_width_pixels = preview_box_right - preview_box_left - preview_box_padding * 2
    temp_img = Image.new('RGBA', (width, height))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), 'A', font=preview_font)
    line_height = bbox[3] - bbox[1] + int(3 * scale)
    char_bbox = temp_draw.textbbox((0, 0), 'A', font=preview_font)
    char_width = char_bbox[2] - char_bbox[0]
    max_line_length = max(10, max_line_width_pixels // char_width)
    max_preview_lines = max(1, preview_box_height // line_height)

    # --- Preview logic by file type ---
    preview_lines = []
    fit_meta = {}
    image_thumb = None
    pdf_grid_thumb = None
    gpx_thumb = None
    video_thumb = None
    fit_gps_thumb = None
    zip_file_list = None
    zip_file_preview_img = None
    zip_file_preview_lines = None
    video_frames = []
    video_frame_thumbs = []

    # --- Preview logic by file type ---
    preview_lines = []
    fit_meta = {}
    image_thumb = None
    pdf_grid_thumb = None
    gpx_thumb = None
    video_thumb = None
    fit_gps_thumb = None
    zip_file_list = None
    zip_file_preview_img = None
    zip_file_preview_lines = None
    video_frames = []
    video_frame_thumbs = []

    if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp'}:
        image = get_image_thumbnail(
            file_path,
            box_size=(max_line_width_pixels, preview_box_height),
            cmyk_mode=cmyk_mode
        )
        if image is not None:
            img_w, img_h = image.size
            logging.debug(f"Original image size: {img_w}x{img_h} for {file_path.name}")
            logging.debug(f"width: {width}, height: {height}, img_w: {img_w}, img_h: {img_h}")
            # Rotate image if card is portrait and image is landscape
            if width < height and img_w > img_h:
                logging.debug(f"Rotating image for portrait card: {file_path.name}")
                image = image.rotate(90, expand=True)
                img_w, img_h = image.size
                logging.debug(f"Image size after rotation: {img_w}x{img_h} for {file_path.name}")

            # Scale to fit preview area
            scale_factor = min(
                (max_line_width_pixels) / img_w,
                (preview_box_height) / img_h
            ) * 0.95
            logging.debug(f"Scaling image by factor {scale_factor:.3f} for {file_path.name}")
            new_w = int(img_w * scale_factor)
            new_h = int(img_h * scale_factor)
            image_thumb = image.resize((new_w, new_h), Image.LANCZOS)
            logging.debug(f"Final image_thumb size: {new_w}x{new_h} for {file_path.name}")
    elif ext in {'.heic', '.heif'}:
        image = get_heif_image(file_path)
        if image is not None:
            img_w, img_h = image.size
            if width < height and img_w > img_h:
                image = image.rotate(90, expand=True)
                img_w, img_h = image.size
            scale_factor = min(
                (max_line_width_pixels) / img_w,
                (preview_box_height) / img_h
            ) * 0.95
            new_w = int(img_w * scale_factor)
            new_h = int(img_h * scale_factor)
            image_thumb = image.resize((new_w, new_h), Image.LANCZOS)
    elif ext == '.numbers':
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                names = z.namelist()
                preview_lines = [f"NUMBERS file: {len(names)} items"]
                preview_lines += [f"  {name}" for name in names[:max_preview_lines]]
                # Try to find a preview image
                image_files = [name for name in names if name.lower().endswith(('.jpg', '.jpeg', '.png'))]
                image_thumb = None
                if image_files:
                    with z.open(image_files[0]) as img_file:
                        img_data = img_file.read()
                        try:
                            img = Image.open(io.BytesIO(img_data))
                            img.thumbnail((max_line_width_pixels, preview_box_height))
                            image_thumb = img
                        except Exception:
                            pass
        except Exception as e:
            preview_lines = [f"NUMBERS error: {e}"]
    elif ext == '.pdf':
        try:
            #pages = convert_from_path(str(file_path), first_page=1, last_page=1)
            #if pages:
                #image_thumb = process_pdf_or_ai_page(pages[0], max_line_width_pixels, preview_box_height)
            image_thumb = get_pdf_preview(str(file_path), max_line_width_pixels, preview_box_height)
            #else:
            #    preview_lines = ["PDF preview not available."]
        except Exception as e:
            preview_lines = [f"PDF error: {e}"]
    elif ext in {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.webm'}:
        # Dynamically determine grid size based on video length
        def get_video_grid_size(file_path):
            try:
                import cv2
                cap = cv2.VideoCapture(str(file_path))
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                # Use a matrix/function to scale grid size with video length
                # Short videos: 3x3, Medium: 4x3, Long: 4x4, Very long: 5x4, etc.
                if frame_count < 30:
                    return 3, 3
                elif frame_count < 900:
                    return 4, 4
                elif frame_count < 1800:
                    return 4, 5
                elif frame_count < 3600:
                    return 4, 5
                else:
                    # For very long videos, cap at 4x6
                    return 4, 5
            except Exception:
                return 3, 3
        grid_cols, grid_rows = get_video_grid_size(file_path)
        video_thumb = get_video_preview(file_path, max_line_width_pixels, preview_box_height, grid_cols=grid_cols, grid_rows=grid_rows)
        video_frames = get_video_frames(file_path, max_frames=grid_cols * grid_rows)
        video_frame_thumbs = []
        for frame in video_frames:
            scale_factor = min(
                (max_line_width_pixels) / frame.width,
                (preview_box_height) / frame.height
            ) * 0.98
            new_w = int(frame.width * scale_factor)
            new_h = int(frame.height * scale_factor)
            thumb = frame.resize((new_w, new_h), Image.LANCZOS)
            video_frame_thumbs.append(thumb)

    # Defer drawing to later section after header/metadata are drawn.
    elif ext == '.gpx':
        gpx_thumb = get_gpx_preview(file_path, max_line_width_pixels, preview_box_height)
        # Mapbox integration for GPX with polyline
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                gpx = gpxpy.parse(f)
            points = []
            for track in gpx.tracks:
                for segment in track.segments:
                    for p in segment.points:
                        points.append((p.longitude, p.latitude))
            if points:
                lons, lats = zip(*points)
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                mapbox_img = get_mapbox_tile_for_bounds(min_lat, max_lat, min_lon, max_lon, min(max_line_width_pixels, 1280), min(preview_box_height, 1280), path_points=points)
                if mapbox_img:
                    gpx_thumb = mapbox_img
        except Exception:
            pass
    elif ext in {'.xlsx', '.xls'}:
        preview_lines = get_excel_preview(file_path, max_rows=max_preview_lines, max_cols=8)

    elif ext in {'.fit', '.tcx'}:
        preview_lines, fit_meta = get_fit_summary_preview(file_path)
        fit_gps_thumb = get_fit_gps_preview(file_path, max_line_width_pixels, preview_box_height)
        # Mapbox integration for FIT/TCX with polyline
        try:
            fitfile = FitFile(str(file_path))
            points = []
            for record in fitfile.get_messages('record'):
                lat = None
                lon = None
                for d in record:
                    if d.name == 'position_lat':
                        lat = d.value * (180.0 / 2**31)
                    elif d.name == 'position_long':
                        lon = d.value * (180.0 / 2**31)
                if lat is not None and lon is not None:
                    points.append((lon, lat))
            if points:
                lons, lats = zip(*points)
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                mapbox_img = get_mapbox_tile_for_bounds(min_lat, max_lat, min_lon, max_lon, min(max_line_width_pixels, 1280), min(preview_box_height, 1280), path_points=points)
                if mapbox_img:
                    fit_gps_thumb = mapbox_img
        except Exception:
            pass
    elif ext == '.docx':
        try:
            from docx import Document
            doc = Document(file_path)
            doc_lines = [p.text for p in doc.paragraphs if p.text.strip()]
            logging.info(f"Extracted {len(doc_lines)} lines from DOCX file: {file_path}")
            txt_path = file_path.with_suffix('.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(doc_lines))
            preview_lines = []
            for raw_line in doc_lines:
                wrapped = textwrap.wrap(raw_line, width=max_line_length)
                if not wrapped:
                    preview_lines.append('')
                else:
                    preview_lines.extend(wrapped)
            preview_lines = preview_lines[:max_preview_lines]
        except Exception as e:
            preview_lines = [f"DOCX error: {e}"]
    elif file_type_info['group'] == 'font':
        # For font files, generate a visual preview
        try:
            image_thumb = get_font_preview(file_path, max_line_width_pixels, preview_box_height)
            if image_thumb:
                preview_text_replaced_with_image = True
                preview_lines = []  # No text preview needed
            else:
                preview_lines = [f"Font preview not available for {os.path.basename(file_path)}"]
        except Exception as e:
            preview_lines = [f"Font preview error: {str(e)}"]
    elif file_type_info['group'] == 'binary' or ext == '.dfu':
        preview_lines = get_hex_preview(file_path, max_preview_lines * 16)
    elif file_type_info['group'] in ['code', 'data', 'document', 'log']:
        # Read a large chunk and wrap
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_lines = []
                for i in enumerate(f):
                    if i > 1000:
                        break
                    raw_lines.append(line.rstrip('\n'))
        except Exception:
            raw_lines = []
        for raw_line in raw_lines:
            wrapped = textwrap.wrap(raw_line, width=max_line_length)
            if not wrapped:
                preview_lines.append('')
            else:
                preview_lines.extend(wrapped)
        preview_lines = preview_lines[:max_preview_lines]
    elif file_type_info['group'] == 'text':
        preview_lines = preview_text_content(file_path, max_lines=max_preview_lines, max_line_length=max_line_length) or []
    elif ext == '.zip':
        zip_file_list = get_zip_preview(file_path, max_files=max_preview_lines)
        zip_file_preview_img = None
        zip_file_preview_lines = None
    elif ext == '.rar':
        try:
            logging.info(f"Processing RAR file: {file_path}")
            import rarfile
            with rarfile.RarFile(file_path) as rf:
                names = rf.namelist()
                preview_lines = [f"RAR file: {len(names)} items"]
                preview_lines += [f"  {name}" for name in names[:max_preview_lines]]
                logging.info(f"Found {len(names)} items in RAR file: {file_path}")
        except Exception as e:
            preview_lines = [f"RAR error: {e}"]
    elif ext == '.gz':
        preview_lines, image_thumb, _ = get_gz_preview(
            file_path, max_bytes=max_preview_lines * 16, preview_box=(max_line_width_pixels, preview_box_height))
        image_thumb = image_thumb  # If image_thumb is None, preview_lines will be used
    elif ext == '.bz2':
        preview_lines = get_bz2_preview(file_path, max_bytes=max_preview_lines * 16)
    elif ext == '.key':
        logging.info(f"****** Processing Keynote file: {file_path}")
        try:
            logging.info(f"Processing Keynote file: {file_path}")
            with zipfile.ZipFile(file_path, 'r') as z:
                names = z.namelist()
                preview_lines = [f"Keynote file: {len(names)} items"]
                preview_lines += [f"  {name}" for name in names[:max_preview_lines]]
                # Find up to 4 images (jpg/png)
                image_files = [name for name in names if name.lower().endswith(('.jpg', '.jpeg', '.png'))][:4]
                thumbs = []
                for name in image_files:
                    with z.open(name) as img_file:
                        img_data = img_file.read()
                        try:
                            img = Image.open(io.BytesIO(img_data))
                            thumbs.append(img)
                        except Exception:
                            continue
                # Make a grid if images found
                if thumbs:
                    grid_cols = 2
                    grid_rows = 2
                    thumb_w = max_line_width_pixels // grid_cols
                    thumb_h = preview_box_height // grid_rows
                    grid_img = Image.new('RGB', (max_line_width_pixels, preview_box_height), (245, 245, 245))
                    for idx, thumb in enumerate(thumbs):
                        thumb.thumbnail((thumb_w, thumb_h))
                        x = (idx % grid_cols) * thumb_w + (thumb_w - thumb.width)//2
                        y = (idx // grid_cols) * thumb_h + (thumb_h - thumb.height)//2
                        grid_img.paste(thumb, (x, y))
                    image_thumb = grid_img
        except Exception as e:
            preview_lines = [f"KEY error: {e}"]
    elif ext == '.pptx' or ext == '.ppt':
        try:
            logging.info(f"Processing PPT(X) file: {file_path}")
            # Extract all images from ppt/media
            with zipfile.ZipFile(file_path, 'r') as z:
                names = z.namelist()
                preview_lines = [f"PPT(X) file: {len(names)} items"]
                preview_lines += [f"  {name}" for name in names[:max_preview_lines]]
                image_files = [name for name in names if name.startswith('ppt/media/') and name.lower().endswith(('.jpg', '.jpeg', '.png'))]
                n_total = len(image_files)
                # Dynamically determine number of preview images
                if n_total <= 6:
                    n_preview = n_total
                elif n_total <= 20:
                    n_preview = min(12, n_total)
                elif n_total <= 50:
                    n_preview = min(16, n_total)
                else:
                    n_preview = min(20, n_total)
                # Select images at evenly distributed intervals
                indices = [0]
                if n_preview > 1 and n_total > 1:
                    import numpy as np
                    remaining = np.linspace(1, n_total - 1, n_preview - 1)
                    indices += [int(round(i)) for i in remaining]
                indices = sorted(set(indices))
                selected_images = [image_files[i] for i in indices if i < n_total]
                thumbs = []
                for name in selected_images:
                    with z.open(name) as img_file:
                        img_data = img_file.read()
                        try:
                            img = Image.open(io.BytesIO(img_data))
                            thumbs.append(img)
                        except Exception:
                            continue
                # Dynamically determine grid_cols and grid_rows
                if thumbs:
                    aspect_ratio = max_line_width_pixels / max(preview_box_height, 1)
                    grid_rows = int(math.ceil(math.sqrt(len(thumbs) / aspect_ratio)))
                    grid_cols = int(math.ceil(len(thumbs) / grid_rows))
                    thumb_w = max_line_width_pixels // grid_cols
                    thumb_h = preview_box_height // grid_rows
                    grid_img = Image.new('RGB', (max_line_width_pixels, preview_box_height), (245, 245, 245))
                    for idx, thumb in enumerate(thumbs):
                        thumb.thumbnail((thumb_w, thumb_h))
                        x = (idx % grid_cols) * thumb_w + (thumb_w - thumb.width)//2
                        y = (idx // grid_cols) * thumb_h + (thumb_h - thumb.height)//2
                        grid_img.paste(thumb, (x, y))
                    image_thumb = grid_img
        except Exception as e:
            preview_lines = [f"PPTX error: {e}"]
    elif ext == '.ai':
        try:
            pages = convert_from_path(str(file_path), first_page=1, last_page=1)
            if pages:
                image_thumb = process_pdf_or_ai_page(pages[0], max_line_width_pixels, preview_box_height)
            else:
                preview_lines = ["AI file: PDF preview not available."]
        except Exception as e:
            preview_lines = [f"AI error: {e}"]
    elif file_type_info['group'] == 'unknown':
        logging.info(f"Unknown file type for {file_path.name}. Attempting to read as text or hex.")
        # First try a lightweight HTML heuristic; if it looks like HTML, render to text/Markdown
        if is_probably_html(file_path):
            logging.info(f"File looks like HTML {file_path.name} - Rendering HTML to text for preview.")
            rendered = render_html_to_text(file_path)
            if rendered:
                # Split into lines and wrap to the card's width
                lines = []
                for raw_line in rendered.splitlines():
                    wrapped = textwrap.wrap(raw_line, width=max_line_length)
                    if not wrapped:
                        lines.append('')
                    else:
                        lines.extend(wrapped)
                preview_lines = lines[:max_preview_lines]
            else:
                # Fallback to plain text preview if rendering returned nothing
                preview_lines = preview_text_content(file_path, max_lines=max_preview_lines, max_line_length=max_line_length) or []
        else:
            preview_lines = get_hex_preview(file_path, max_preview_lines * 16)

    # --- Draw card ---
    if cmyk_mode:
        from pdf_to_images import create_cmyk_image
        img = create_cmyk_image(width, height, (0, 0, 0, 0))
        rgb_mode = False
    else:
        # We already created the image above, just ensuring it's handled consistently
        rgb_mode = True
    draw = ImageDraw.Draw(img)
    if not rgb_mode:
        r, g, b = file_type_info['color']
        if r == 0 and g == 0 and b == 0:
            color = (0, 0, 0, 100)
        else:
            c = 255 - r
            m = 255 - g
            y = 255 - b
            k = min(c, m, y)
            c = (c - k) if k < 255 else 0
            m = (m - k) if k < 255 else 0
            y = (y - k) if k < 255 else 0
            color = (c, m, y, k)
    else:
        color = file_type_info['color']
    # We already set border_width earlier based on scale
    # Header within the content area
    if rgb_mode:
        draw.rectangle([outer_padding, outer_padding, width-outer_padding, outer_padding+header_height], fill=file_type_info['color'])
        text_color = 'white'
    else:
        draw.rectangle([outer_padding, outer_padding, width-outer_padding, outer_padding+header_height], fill=color)
        text_color = (0, 0, 0, 0)
    # Position the file name vertically centered in the header area, accounting for outer padding
    header_text = title.upper() if title is not None else file_path.name.upper()
    draw.text((width//2, outer_padding + header_height//2), header_text, fill=text_color, font=title_font, anchor="mm")
    # draw.text((width//2, outer_padding + header_height//2), file_path.name.upper(), fill=text_color, font=title_font, anchor="mm")
    # Position the icon below the header, accounting for outer padding
    # icon_y = outer_padding + header_height + int(20 * scale)
    # icon_color = file_type_info['color'] if rgb_mode else color
    # draw.text((width//2, icon_y), icon, fill=icon_color, font=title_font, anchor="mm")
    # y = icon_y + 60
    avatar_size = int(120 * scale)
    avatar_img = None

    if 'slack_avatar' in locals() and slack_avatar:
        try:
            #logging.debug(f"Loading avatar from: {slack_avatar}")
            avatar_img = Image.open(slack_avatar).convert('RGB')
            #logging.debug(f"Avatar loaded: size={avatar_img.size}, mode={avatar_img.mode}")
            avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
            #logging.debug(f"Avatar resized: size={avatar_img.size}")
            avatar_img = round_image_corners(avatar_img, radius=int(7 * scale))
            #logging.debug(f"Avatar rounded: size={avatar_img.size}")
        except Exception as e:
            logging.error(f"Error processing avatar image {slack_avatar}: {e}")
            avatar_img = None
            
    if metadata is not None and metadata.get('avatar_path'):
        try:
            avatar_img = Image.open(metadata['avatar_path']).convert('RGB')
            avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
            avatar_img = round_image_corners(avatar_img, radius=int(7 * scale))
        except Exception as e:
            logging.error(f"Error processing metadata avatar image {metadata['avatar_path']}: {e}")
            logging.error(traceback.format_exc())
            avatar_img = None

    avatar_y_coordinate = int(outer_padding + header_height + 5 * scale)
    avatar_x_coordinate = int(outer_padding + 20 * scale)  # 20px from left border, scaled
    
    if avatar_img is not None:
        try:
            # Position avatar relative to the left border (outer_padding)
            #logging.debug(f"Pasting avatar at: x={avatar_x_coordinate}, y={avatar_y_coordinate}")
            img.paste(avatar_img, (avatar_x_coordinate, avatar_y_coordinate), mask=avatar_img)
        except Exception as e:
            logging.error(f"Error pasting avatar image: {e}")
    y = avatar_y_coordinate + 5*scale # avatar and metadata can be horizontally aligned
    
    ########################################
    # DO NOT REMOVE THIS COMMENT EVER
    #
    # THIS IS WHERE THE METADATA IS DRAWN
    #
    # DO NOT REMOVE THIS COMMENT EVER
    ########################################
    logging.debug(f"Drawing metadata -- {file_info}")
    # Initialize variables to safe defaults before conditionals
    meta_pad = int(10 * scale)
    custom_line_spacing_px = 0
    if cmyk_mode:
        bg_fill = (0, 0, 0, 1)  # CMYK very light gray
        bg_outline = (0, 0, 0, 255)  # 100% black
        text_fill = (0, 0, 0, 255)
    else:
        bg_rgb = (255, 255, 255)
        bg_outline_rgb = (0, 0, 0)
        bg_fill = bg_rgb
        bg_outline = bg_outline_rgb
        text_fill = (0, 0, 0)

    if custom_metadata_text:
        # Recompute spacing to match measurement
        y_offset = 0
        tmp_img2 = Image.new("RGBA", (width, height))
        tmp_draw2 = ImageDraw.Draw(tmp_img2)
        l, t, r, b = tmp_draw2.textbbox((0, 0), "Ag", font=info_font)
        single_h = b - t
        custom_line_spacing_px = max(0, int(metadata_line_height - single_h))
        meta_pad = int(10 * scale)

        if cmyk_mode:
            bg_fill = (0, 0, 0, 1)  # CMYK white
            bg_outline = (0, 0, 0, 255)  # 100% black
            text_fill = (0, 0, 0, 255)  # K-only text
        else:
            bg_fill = bg_rgb
            bg_outline = bg_outline_rgb
            text_fill = (0, 0, 0)

        if exclude_file_path is False:
            last_parts = Path(file_path).parts[-3:]
            short_path = "/".join(last_parts)
            filename = Path(file_path).name
            # Truncate filename if longer than 25 characters
            # And if we have one of those huge unwieldly filenames that
            # Instagram produces, just show the last two parts of the file path
            if len(filename) > 50:
                filename = f"{filename[:25]}...{filename[-25:]}"
                short_path = "/".join(last_parts[:-1])
            # Draw the short path (excluding filename) above the filename
            if len(last_parts) > 1:
                draw.text((width//2, outer_padding + header_height + metadata_top_margin), short_path, fill=text_black, font=info_font, anchor="mm")
                draw.text((width//2, outer_padding + header_height + metadata_top_margin + metadata_line_height), filename, fill=text_black, font=info_font, anchor="mm")
                y_offset = metadata_line_height * 2 + 5
            else:
                draw.text((width//2, outer_padding + header_height + metadata_top_margin), filename, fill=text_black, font=info_font, anchor="mm")
                y_offset = metadata_line_height + 5
            logging.debug(f"File Path is {short_path}")
            logging.debug(f"Last Parts is {last_parts} and it is {len(last_parts)} elements long")
        draw_text_box(
            draw,
            custom_metadata_text,
            info_font,
            box=(outer_padding, outer_padding + header_height + metadata_top_margin + y_offset, content_area_width_for_wrap, metadata_height),
            padding=meta_pad,
            line_spacing=custom_line_spacing_px,
            align="left",
            v_align="top",
            fill=text_fill,
            background_fill=bg_fill,
            background_radius=int(3 * scale),
            background_outline=bg_outline,
            background_outline_width=1,
        )
        y = outer_padding + header_height + metadata_top_margin + metadata_height + y_offset
    else:
        for key, value in file_info.items():
            if key == 'Name' or key == 'Filepath' or key == 'filepath' or key == 'created':
                #logging.info(f"Drawing metadata line: {key}: {value}")
                #logging.info(f"File is {file_path.name}")
                line = f"{value}"
            else:
                line = f"{key}: {value}"
            # Wrap the line to fit within the content area width
            wrapped_lines = wrap_text_by_pixel(draw, line, info_font, content_area_width_for_wrap)
            for wrapped_line in wrapped_lines:
                draw.text((outer_padding, y), wrapped_line, fill=text_black, font=info_font, anchor="lt")
                y += metadata_line_height

    # Make sure the preview area starts below the last metadata line
    preview_box_top = max(preview_box_top, int(y + spacing_between_metadata_and_content_preview))
    preview_box_height = preview_box_bottom - preview_box_top - preview_box_padding * 2
    max_preview_lines = max(1, preview_box_height // line_height)

    y = preview_box_top
    draw.rectangle(
        [preview_box_left, preview_box_top, preview_box_right, preview_box_bottom],
        fill=preview_background_color,
        outline='black',
        width=1
    )
    # --- Always show preview_lines for .zip, .gz, .bz2 if present ---
    if ext in {'.zip', '.gz', '.bz2'} and preview_lines:
        text_y = preview_box_top + preview_box_padding
        for line in preview_lines:
            if text_y + line_height > preview_box_bottom - preview_box_padding:
                break

        if '\n' in line:
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font)
        else:
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")

            text_y += line_height
        return img
    # FIT: show GPS map if present, then summary text below
    if ext == '.fit' and fit_gps_thumb is not None:
        img_w, img_h = fit_gps_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        fit_gps_thumb = scale_image(fit_gps_thumb, 0.95)
        img.paste(fit_gps_thumb, (int(x0), int(y0)))
        # Draw summary below the map if space allows
        try:
            fit_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 12)
        except:
            fit_font = ImageFont.load_default()
        text_y = y0 + img_h + 10
        for line in preview_lines:
            if text_y + line_height > preview_box_bottom - preview_box_padding:
                break
            if '\n' in line:
                draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=fit_font)
            else:
                draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=fit_font, anchor="lt")
            text_y += line_height
        return img
    # If no GPS map, just show summary text as before
    if ext == '.fit' and preview_lines:
        try:
            fit_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 12)
        except:
            fit_font = ImageFont.load_default()
        text_y = preview_box_top + preview_box_padding
        for line in preview_lines:
            if text_y + line_height > preview_box_bottom - preview_box_padding:
                break
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=fit_font, anchor="lt")
            text_y += line_height
        return img
    # All other previews (images, pdfs, videos, etc.)
    if pdf_grid_thumb is not None:
        img_w, img_h = pdf_grid_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        img.paste(pdf_grid_thumb, (int(x0), int(y0)))
    elif gpx_thumb is not None:
        img_w, img_h = gpx_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        img.paste(gpx_thumb, (int(x0), int(y0)))
    elif video_thumb is not None:
        # Paste the overview thumbnail into the preview area on the base card (which already has header+metadata)
        img_w, img_h = video_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        img.paste(video_thumb, (int(x0), int(y0)))

        if video_frame_thumbs:
            dpi = 300
            overview_img = img.copy()
            draw_frame = ImageDraw.Draw(overview_img)
            min_border_px = int(border_inch_width * dpi)
            color_border_width = min_border_px
            if cmyk_mode:
                draw_frame.rectangle([0, 0, width, height], outline=rgb_to_cmyk(*border_color), width=color_border_width)
            else:
                draw_frame.rectangle([0, 0, width, height], outline=border_color, width=color_border_width)
            # Always produce an overview card
            if not include_video_frames:
                return overview_img
            # Otherwise, build list: overview first, then one per frame
            cards = [overview_img]
            for frame_thumb in video_frame_thumbs:
                frame_w, frame_h = frame_thumb.size
                frame_x0 = preview_box_left + preview_box_padding + max(0, (box_w - frame_w)//2)
                frame_y0 = preview_box_top + preview_box_padding + max(0, (box_h - frame_h)//2)
                frame_img = img.copy()
                # Clear the preview area before placing an individual frame
                draw_frame = ImageDraw.Draw(frame_img)
                draw_frame.rectangle(
                    [preview_box_left + preview_box_padding, preview_box_top + preview_box_padding,
                     preview_box_right - preview_box_padding, preview_box_bottom - preview_box_padding],
                    fill=preview_background_color
                )
                frame_img.paste(frame_thumb, (int(frame_x0), int(frame_y0)))
                # Add border around the frame card
                dpi = 300
                min_border_px = int(border_inch_width * dpi)
                color_border_width = min_border_px
                if cmyk_mode:
                    draw_frame.rectangle([0, 0, width, height], outline=rgb_to_cmyk(*border_color), width=color_border_width)
                else:
                    draw_frame.rectangle([0, 0, width, height], outline=border_color, width=color_border_width)
                cards.append(frame_img)
            return cards
    elif image_thumb is not None:
        img_w, img_h = image_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        logging.debug(f"Pasting image thumbnail at: x={x0}, y={y0}, size={img_w}x{img_h}")
        img.paste(image_thumb, (int(x0), int(y0)))
    elif fit_gps_thumb is not None:
        img_w, img_h = fit_gps_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        img.paste(fit_gps_thumb, (int(x0), int(y0)))
    elif zip_file_list is not None:
        text_y = preview_box_top + preview_box_padding
        for line in zip_file_list:
            if text_y + line_height > preview_box_bottom - preview_box_padding:
                break

        if '\n' in line:
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font)
        else:
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")

            text_y += line_height
        # Always show preview lines for .zip, .gz, .bz2 if present
        if zip_file_preview_lines is not None:
            for line in zip_file_preview_lines:
                if text_y + line_height > preview_box_bottom - preview_box_padding:
                    break
                if '\n' in line:
                    draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font)
                else:
                    draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")
                text_y += line_height
        if zip_file_preview_img is not None:
            img_w, img_h = zip_file_preview_img.size
            box_w = preview_box_right - preview_box_left - preview_box_padding * 2
            box_h = preview_box_height - preview_box_padding * 2
            x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
            y0 = text_y + 10
            if y0 + img_h > preview_box_bottom - preview_box_padding:
                img_h = preview_box_bottom - preview_box_padding - y0
                zip_file_preview_img = zip_file_preview_img.crop((0, 0, img_w, img_h))
            img.paste(zip_file_preview_img, (int(x0), int(y0)))
    else:
        text_y = preview_box_top + preview_box_padding
        for line in preview_lines:
            if text_y + line_height > preview_box_bottom - preview_box_padding:
                break
            if '\n' in line:
                draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font)
            else:
                draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")
            text_y += line_height
    
    
    # I need to convert from RGB to CMYK
    dpi = 300  # or whatever your output DPI is
    #border_inch_width = 0.125  # Minimum border in inches
    min_border_px = int(border_inch_width * dpi)  # 0.125 * 300 = 37 pixels

    color_border_width = min_border_px #max(min_border_px, int(10 * scale), 20)
    
    # color_border_width = min(int(20 * scale), 20)  # Scales with 'scale', but never exceeds 15
    draw.rectangle([0, 0, width, height], outline=rgb_to_cmyk(*border_color), width=color_border_width)
    return img

def determine_file_type(file_path):
    """Categorize files into different types for appropriate rendering."""
    ext = file_path.suffix.lower()
    # Define file type groups with their extensions and icons
    for group, info in FILE_TYPE_GROUPS.items():
        if ext in info['extensions']:
            return group
    
    # Default to "other" for anything not recognized
    return "other"

def get_slack_user_name(slack_user_id, users_json_path):
    """Get the Slack user name for a given user ID from the users.json file."""
    if not slack_user_id or not users_json_path.exists():
        return None
    try:
        with open(users_json_path, 'r', encoding='utf-8', errors='ignore') as uf:
            users = json.load(uf)
        for user in users:
            if user.get('id') == slack_user_id or user.get('name') == slack_user_id:
                return user.get('real_name') or user.get('profile', {}).get('real_name') or user.get('name')
    except Exception as e:
        logging.error(f"Error reading users.json: {e}")
    return None

def save_card_as_tiff(img, output_path, cmyk_mode=False):
    """
    Save a card image as a TIFF file with proper handling for CMYK mode.
    This function ensures borders are preserved during CMYK conversion.
    
    Args:
        img: The PIL Image object to save
        output_path: The path where the TIFF should be saved
        cmyk_mode: Whether to save in CMYK mode (True) or RGB mode (False)
    """
    try:
        if cmyk_mode:
            # For CMYK mode, we need to make sure the border is even more pronounced
            # Draw an additional solid border around the entire image
            draw = ImageDraw.Draw(img)
            #w, h = img.size
            # for i in range(0, 5):  # Draw 5 concentric borders for visibility
            #     draw.rectangle(
            #         [i, i, w-1-i, h-1-i],
            #         outline=(0, 0, 0, 100),  # Solid black in CMYK
            #         width=4  # Thick line
            #     )
            
            # Save with LibTIFF and specific compression settings
            img.save(
                output_path, 
                format='TIFF',
                compression='none',  # No compression for maximum quality
                dpi=(300, 300)       # Set DPI to 300
            )
            logging.debug(f"Saved CMYK TIFF with reinforced border: {output_path}")
        else:
            # For RGB mode, add a clear border too
            draw = ImageDraw.Draw(img)
            w, h = img.size
            draw.rectangle([0, 0, w-1, h-1], outline=(0, 0, 0), width=5)
            
            # Standard save
            img.save(output_path, format='TIFF', compression='tiff_deflate')
            logging.debug(f"Saved RGB TIFF with reinforced border: {output_path}")
    except Exception as e:
        logging.error(f"Error saving TIFF image: {e}")
        # Fall back to basic save method
        img.save(output_path)
        logging.warning(f"Used fallback save method for: {output_path}")

def process_pdf_or_ai_page(page, max_width, max_height):
    """
    Takes a PIL Image (PDF or AI page), rotates if landscape, and scales to fit the preview box.
    Returns the processed image.
    """
    img_w, img_h = page.size
    # Rotate if landscape
    if img_w > img_h:
        page = page.rotate(90, expand=True)
        img_w, img_h = page.size
    # Scale to fit preview box
    scale_factor = min(max_width / img_w, max_height / img_h, 1) * 0.95
    new_w = int(img_w * scale_factor)
    new_h = int(img_h * scale_factor)
    return page.resize((new_w, new_h), Image.LANCZOS)

def get_excel_preview(file_path, max_rows=10, max_cols=8):
    ext = file_path.suffix.lower()
    preview_lines = []
    try:
        if ext == '.xlsx':
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = wb.active
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if i >= max_rows:
                    break
                row_str = " | ".join(str(cell) if cell is not None else "" for cell in row[:max_cols])
                preview_lines.append(row_str)
        elif ext == '.xls':
            import xlrd
            wb = xlrd.open_workbook(file_path)
            sheet = wb.sheet_by_index(0)
            for i in range(min(max_rows, sheet.nrows)):
                row = sheet.row_values(i)
                row_str = " | ".join(str(cell) if cell is not None else "" for cell in row[:max_cols])
                preview_lines.append(row_str)
        else:
            preview_lines = ["Unsupported Excel format."]
    except Exception as e:
        preview_lines = [f"Excel preview error: {e}"]
    return preview_lines

def is_probably_html(file_path, max_bytes=262144):
    """
    Heuristic check whether a file's contents look like HTML.
    Reads up to `max_bytes` from the file and looks for common HTML markers.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(max_bytes)
        try:
            text = chunk.decode("utf-8", errors="ignore")
        except Exception:
            text = chunk.decode("latin-1", errors="ignore")
        lower = text.lower()
        # Strong signals
        if "<!doctype" in lower or "<html" in lower or "<head" in lower or "<body" in lower:
            return True
        # Common tags
        tags = ["<div", "<span", "<p", "<a ", "<meta", "<script", "<title", "<link", "<!doctype"]
        tag_count = sum(1 for t in tags if t in lower)
        if tag_count >= 2:
            return True
        # Generic tag density heuristic
        lt = lower.count("<")
        gt = lower.count(">")
        if lt > 5 and gt > 5 and re.search(r"<[a-z][\s>/]", lower):
            return True
        return False
    except Exception:
        return False

def render_html_to_text(file_path, max_bytes=262144, max_chars=10000, prefer_markdown=True):
    """
    Convert HTML file contents to readable text (or Markdown when html2text is available).
    - Reads up to max_bytes from the file.
    - Strips scripts/styles before conversion.
    - Returns a truncated string no longer than max_chars.
    """
    try:
        with open(file_path, "rb") as f:
            raw = f.read(max_bytes)
        try:
            html = raw.decode("utf-8", errors="ignore")
        except Exception:
            html = raw.decode("latin-1", errors="ignore")

        # Remove script/style blocks first
        html = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
        html = re.sub(r"(?is)<style.*?>.*?</style>", "", html)

        # Prefer html2text -> Markdown if available and requested
        try:
            if prefer_markdown:
                import html2text  # optional dependency
                h = html2text.HTML2Text()
                h.ignore_images = True
                h.ignore_links = False
                h.body_width = 0
                md = h.handle(html)
                result = md.strip()
            else:
                raise ImportError
        except Exception:
            # Fallback: BeautifulSoup to plain text if available
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                # remove any remaining script/style tags defensively
                for s in soup(["script", "style"]):
                    s.decompose()
                text = soup.get_text(separator="\n")
                # Collapse multiple blank lines
                result = re.sub(r"\n{3,}", "\n\n", text).strip()
            except Exception:
                # Very conservative fallback: strip tags with regex
                text = re.sub(r"(?is)<[^>]+>", "", html)
                result = re.sub(r"\s{2,}", " ", text).strip()

        # Truncate to max_chars and return
        if len(result) > max_chars:
            return result[:max_chars].rstrip() + "\n\n[truncated]"
        return result
    except Exception:
        return ""


def rgb_to_cmyk(r, g, b):
    if r == 0 and g == 0 and b == 0:
        return (0, 0, 0, 100)
    c = 255 - r
    m = 255 - g
    y = 255 - b
    k = min(c, m, y)
    c = (c - k) if k < 255 else 0
    m = (m - k) if k < 255 else 0
    y = (y - k) if k < 255 else 0
    return (c, m, y, k)

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Generate debug file cards for given files")
    parser.add_argument("files", nargs="+", help="One or more input files to generate cards for")
    parser.add_argument("--output-dir", default="./cards_out", help="Directory to write generated TIFFs into")
    parser.add_argument("--width", type=int, default=800, help="Card width in pixels")
    parser.add_argument("--height", type=int, default=1000, help="Card height in pixels")
    parser.add_argument("--cmyk", action="store_true", help="Save cards in CMYK mode")
    parser.add_argument("--include-video-frames", action="store_true", help="If a video, include per-frame cards")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for fp in args.files:
        try:
            cards = create_file_info_card(fp, width=args.width, height=args.height, cmyk_mode=args.cmyk, include_video_frames=args.include_video_frames)
            if isinstance(cards, list):
                for idx, card in enumerate(cards):
                    out_path = out_dir / f"{Path(fp).stem}_{idx}.tiff"
                    save_card_as_tiff(card, str(out_path), cmyk_mode=args.cmyk)
            else:
                out_path = out_dir / f"{Path(fp).stem}.tiff"
                save_card_as_tiff(cards, str(out_path), cmyk_mode=args.cmyk)
            print(f"Saved card(s) for {fp} to {out_dir}")
        except Exception as e:
            logging.error("Error processing %s: %s", fp, e, exc_info=True)