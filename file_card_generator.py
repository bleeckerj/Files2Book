import os
import time
from datetime import datetime
import hashlib
import mimetypes
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io
import math
import textwrap
import zipfile
import bz2
import gzip
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
import requests
import dotenv
import polyline
import logging
import traceback
import random

Image.MAX_IMAGE_PIXELS = 500_000_000  # or any large number
#Image.MAX_IMAGE_PIXELS = None  # disables the limit (use with caution)

# Initialize mimetypes
mimetypes.init()

dotenv.load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s'
)

logging.getLogger("pdf2image").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)

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
        'extensions': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'},
        'icon': "IMAGE",
        'color': (0, 244, 240)  # HEX: 00f4f0
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
    logging.info(f"DEBUG: ext={ext}")
    # Check if the extension is in any of our groups
    for group, info in FILE_TYPE_GROUPS.items():
        if ext in info['extensions']:
            logging.debug(f"DEBUG: Found group {group} for extension {ext} for file {file_path}")
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
    messages_json = parent.parent / "messages.json"
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
        if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.heic'} and preview_box:
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

def get_pdf_preview(file_path, box_w, box_h, max_pages=6):
    try:
        # First, get the total number of pages
        from pdf2image import convert_from_path
        import numpy as np
        logging.debug(f"Attempting to extract PDF preview: {file_path}")
        all_pages = convert_from_path(str(file_path))
        n_total = len(all_pages)
        logging.info(f"PDF {file_path} has {n_total} pages")
        # Dynamically determine number of preview pages
        if n_total <= 6:
            n_preview = n_total
        elif n_total <= 20:
            n_preview = min(8, n_total)
        elif n_total <= 50:
            n_preview = min(12, n_total)
        else:
            n_preview = min(16, n_total)
        if n_preview == 0:
            logging.warning(f"No pages found in PDF: {file_path}")
            return None
        # Select preview page indices: always include first page, then evenly distributed
        indices = [0]
        if n_preview > 1:
            # Evenly distribute remaining pages
            remaining = np.linspace(1, n_total - 1, n_preview - 1)
            indices += [int(round(i)) for i in remaining]
        indices = sorted(set(indices))
        selected_pages = [all_pages[i] for i in indices]
        # Dynamically determine grid layout
        aspect_ratio = box_w / max(box_h, 1)
        grid_rows = int(math.ceil(math.sqrt(len(selected_pages) / aspect_ratio)))
        grid_cols = int(math.ceil(len(selected_pages) / grid_rows))
        thumb_w = box_w // grid_cols
        thumb_h = box_h // grid_rows
        grid_img = Image.new('RGBA', (box_w, box_h), (245, 245, 245))
        for idx, page in enumerate(selected_pages):
            try:
                page.thumbnail((thumb_w, thumb_h))
                x = (idx % grid_cols) * thumb_w + (thumb_w - page.width)//2
                y = (idx // grid_cols) * thumb_h + (thumb_h - page.height)//2
                grid_img.paste(page, (x, y))
                logging.debug(f"Pasted page {indices[idx]+1} at ({x}, {y}), size ({page.width}, {page.height})")
            except Exception as page_e:
                logging.error(f"Error rendering page {indices[idx]+1} of {file_path}: {page_e}")
        logging.debug(f"Preview box: width={box_w}, height={box_h}")
        logging.debug(f"Grid before rotation: width={grid_img.width}, height={grid_img.height}")
        return grid_img
    except Exception as e:
        logging.error(f"PDF preview error for {file_path}: {e}")
        return None

def get_image_thumbnail(file_path, thumb_size=(320, 320)):
    try:
        img = Image.open(file_path)
        img.thumbnail(thumb_size)
        return img
    except Exception:
        return None

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
        logging.debug(f"Grid size: {grid_img.size} for file {file_path}")
        return grid_img
    except Exception:
        return None

# Check for pillow-heif availability
try:
    import pillow_heif
    PILLOW_HEIF_AVAILABLE = True
except ImportError:
    PILLOW_HEIF_AVAILABLE = False

def get_heic_image(file_path):
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

def get_mapbox_tile_for_bounds(min_lat, max_lat, min_lon, max_lon, width, height, api_key=MAPBOX_TOKEN, path_points=None):
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


def create_file_info_card(file_path, width=800, height=1000, cmyk_mode=False):
    file_path = Path(file_path)
    # Proportional scaling
    base_width = 800
    base_height = 1000
    scale = min(width / base_width, height / base_height)
    logging.debug(f"Scaling card to {width}x{height} with scale factor {scale:.2f}")
    # Proportional paddings
    border_width = max(2, int(1 * scale))  # Using a more reasonable but still very visible border width
    outer_padding = max(10, int(25 * scale))  # Padding between border and outer edges of content

    # Calculate dimensions for the content area
    #content_width = width - 2 * outer_padding
    #content_height = height - 2 * outer_padding

    # Create the full-sized image (background)
    img = Image.new('RGBA', (width, height), 'white')
    draw = ImageDraw.Draw(img)

    # Draw the border around the content area
    # Determine the color mode first to avoid variable reference issues
    rgb_mode = not cmyk_mode
    
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
                outline=(0, 0, 0, 100),  # 100% black in CMYK
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
    preview_box_padding = int(8 * scale)
    header_height = int(20 * scale)

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

    # Try to get original timestamp and Slack metadata
    original_dt = get_original_timestamp(file_path)
    slack_channel = None
    slack_message_id = None
    slack_user_id = None
    slack_user_name = None
    slack_avatar = None
    slack_shared_date = None
    parent = file_path.parent
    channel_dir = parent.parent
    messages_json = channel_dir / "messages.json"
    users_json = channel_dir.parent / "users.json"
    avatars_dir = channel_dir.parent / "avatars_40x40"
    user_profile = None
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
                            avatars_dir = channel_dir.parent / "avatars"
                            logging.debug(f"Looking for avatars in: {avatars_dir}")
                            if slack_user_id and avatars_dir.exists():
                                avatar_path = avatars_dir / f"{slack_user_id}.jpg"
                                logging.debug(f"Checking avatar path: {avatar_path}")
                                if avatar_path.exists():
                                    slack_avatar = str(avatar_path)
                                    logging.debug(f"Found avatar for {slack_user_id}: {slack_avatar}")
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
    # Build metadata with Slack Channel at the top if present
    file_info = {}
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
    if original_dt:
        file_info['Original Date'] = original_dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        file_info['Modified'] = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
        file_info['Created'] = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S')
    # Move Name to the end
    file_info['Name'] = file_path.name

    # Fixed card height for 4x5 aspect ratio
    #header_height = int(80 * scale)
    icon_space = int((100 + 40) * scale)
    metadata_lines = len(file_info)
    metadata_height = metadata_lines * metadata_line_height
    logging.debug(f"Metadata height: {metadata_height} for {metadata_lines} lines")
    # Content area dimensions, accounting for outer padding
    content_area_left = outer_padding
    content_area_right = width - outer_padding
    content_area_width = content_area_right - content_area_left
    
    # Preview box within the content area
    preview_box_left = content_area_left + int(content_area_width * 0.1)
    preview_box_right = content_area_right - int(content_area_width * 0.1)
    preview_box_top = outer_padding + header_height + metadata_height + spacing_between_metadata_and_content_preview
    logging.debug(f"Preview box top: {preview_box_top}, icon space: {icon_space}, metadata height: {metadata_height}")
    preview_box_bottom = height - outer_padding - int(30 * scale)
    preview_box_height = preview_box_bottom - preview_box_top
    max_line_width_pixels = preview_box_right - preview_box_left - preview_box_padding * 2
    temp_img = Image.new('RGB', (width, height))
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
    if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'}:
        image = get_image_thumbnail(file_path, thumb_size=(max_line_width_pixels, preview_box_height))
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
            # Convert transparent images to RGB with white/light background
            if image.mode in ("RGBA", "LA"):
                logging.debug(f"Converting transparent image to RGB: {file_path.name}")
                background = Image.new("RGB", image.size, (250, 250, 250))  # light gray
                background.paste(image, mask=image.split()[-1])
                image = background
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
        image = get_heic_image(file_path)
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
                    return 4, 3
                elif frame_count < 1800:
                    return 4, 4
                elif frame_count < 3600:
                    return 5, 4
                else:
                    # For very long videos, cap at 6x5
                    return 6, 5
            except Exception:
                return 3, 3
        grid_cols, grid_rows = get_video_grid_size(file_path)
        video_thumb = get_video_preview(file_path, max_line_width_pixels, preview_box_height, grid_cols=grid_cols, grid_rows=grid_rows)
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
                mapbox_img = get_mapbox_tile_for_bounds(min_lat, max_lat, min_lon, max_lon, min(max_line_width_pixels, 1280), min(preview_box_height, 1280), MAPBOX_TOKEN, path_points=points)
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
                mapbox_img = get_mapbox_tile_for_bounds(min_lat, max_lat, min_lon, max_lon, min(max_line_width_pixels, 1280), min(preview_box_height, 1280), MAPBOX_TOKEN, path_points=points)
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
    elif file_type_info['group'] == 'binary' or ext == '.dfu' or file_type_info['group'] == 'unknown':
        preview_lines = get_hex_preview(file_path, max_preview_lines * 16)
    elif file_type_info['group'] in ['code', 'data', 'document', 'log']:
        # Read a large chunk and wrap
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_lines = []
                for i, line in enumerate(f):
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
    elif ext == '.pptx':
        try:
            logging.info(f"Processing PPTX file: {file_path}")
            # Extract all images from ppt/media
            with zipfile.ZipFile(file_path, 'r') as z:
                names = z.namelist()
                preview_lines = [f"PPTX file: {len(names)} items"]
                preview_lines += [f"  {name}" for name in names[:max_preview_lines]]
                image_files = [name for name in names if name.startswith('ppt/media/') and name.lower().endswith(('.jpg', '.jpeg', '.png'))]
                # Pick up to 12 random images
                num_images = min(12, len(image_files))
                selected_images = random.sample(image_files, num_images) if num_images > 0 else []
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
                    # Try to make grid as square as possible, but favor more rows for tall preview
                    grid_rows = int(math.ceil(math.sqrt(num_images / aspect_ratio)))
                    grid_cols = int(math.ceil(num_images / grid_rows))
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
    draw.text((width//2, outer_padding + header_height//2), file_path.name.upper(), fill=text_color, font=title_font, anchor="mm")
    # Position the icon below the header, accounting for outer padding
    # icon_y = outer_padding + header_height + int(20 * scale)
    # icon_color = file_type_info['color'] if rgb_mode else color
    # draw.text((width//2, icon_y), icon, fill=icon_color, font=title_font, anchor="mm")
    # y = icon_y + 60
    avatar_size = int(100 * scale)
    avatar_img = None
    if slack_avatar:
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

    if avatar_img is not None:
        try:
            # Position avatar relative to the left border (outer_padding)
            avatar_x_coordinate = int(outer_padding + 60 * scale)  # 15px from left border, scaled
            avatar_y_coordinate = int(outer_padding + header_height + 5 * scale)
            #logging.debug(f"Pasting avatar at: x={avatar_x_coordinate}, y={avatar_y_coordinate}")
            img.paste(avatar_img, (avatar_x_coordinate, avatar_y_coordinate), mask=avatar_img)
        except Exception as e:
            logging.error(f"Error pasting avatar image: {e}")
    y = avatar_y_coordinate + 5*scale # avatar and metadata can be horizontally aligned
    for key, value in file_info.items():
        if key == 'Name':
            # For the Name field, don't show the label
            line = f"{value}"
        else:
            line = f"{key}: {value}"
        draw.text((width//2, y), line, fill='black', font=info_font, anchor="mm")
        y += metadata_line_height
    y = preview_box_top - 30
    #draw.text((width//2, y), "Content Preview:", fill='black', font=info_font, anchor="mm")
    y = preview_box_top
    preview_background_color = (245, 245, 245) if rgb_mode else (0, 0, 0, 4)
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
        img_w, img_h = video_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
        img.paste(video_thumb, (int(x0), int(y0)))
    elif image_thumb is not None:
        img_w, img_h = image_thumb.size
        box_w = preview_box_right - preview_box_left - preview_box_padding * 2
        box_h = preview_box_height - preview_box_padding * 2
        x0 = preview_box_left + preview_box_padding + max(0, (box_w - img_w)//2)
        y0 = preview_box_top + preview_box_padding + max(0, (box_h - img_h)//2)
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
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")
            text_y += line_height
        # Always show preview lines for .zip, .gz, .bz2 if present
        if zip_file_preview_lines is not None:
            for line in zip_file_preview_lines:
                if text_y + line_height > preview_box_bottom - preview_box_padding:
                    break
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
            draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")
            text_y += line_height
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
            w, h = img.size
            for i in range(0, 5):  # Draw 5 concentric borders for visibility
                draw.rectangle(
                    [i, i, w-1-i, h-1-i],
                    outline=(0, 0, 0, 100),  # Solid black in CMYK
                    width=4  # Thick line
                )
            
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