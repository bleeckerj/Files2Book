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

# Initialize mimetypes
mimetypes.init()

# Define file type groups with recognizable icons
FILE_TYPE_GROUPS = {
    'code': {
        'extensions': {'.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h', '.sh', '.rb', '.swift', '.php', '.go'},
        'icon': "< / >",
        'color': (0, 80, 180)  # Blue
    },
    'data': {
        'extensions': {'.json', '.csv', '.xml', '.yaml', '.yml', '.toml', '.ini'},
        'icon': "{ }",
        'color': (0, 130, 0)  # Green
    },
    'spreadsheet': {
        'extensions': {'.xlsx', '.xls', '.ods', '.numbers'},
        'icon': "TABLE",
        'color': (0, 140, 70)  # Green-blue
    },
    'document': {
        'extensions': {'.doc', '.docx', '.txt', '.md', '.rtf', '.odt', '.pdf', '.tex'},
        'icon': "DOC",
        'color': (100, 0, 120)  # Purple
    },
    'archive': {
        'extensions': {'.zip', '.tar', '.gz', '.bz2', '.rar', '.7z'},
        'icon': "ZIP",
        'color': (180, 100, 0)  # Orange
    },
    'executable': {
        'extensions': {'.exe', '.bin', '.app', '.sh', '.bat', '.dll', '.so', '.dylib'},
        'icon': "EXE",
        'color': (180, 0, 0)  # Red
    },
    'binary': {
        'extensions': {'.hex', '.bin', '.dat', '.dfu', '.oci'},
        'icon': "BIN",
        'color': (80, 80, 80)  # Dark gray
    },
    'gps': {
        'extensions': {'.gpx', '.fit', '.tcx'},
        'icon': "GPS",
        'color': (0, 120, 160)  # Teal
    },
    'log': {
        'extensions': {'.log', '.txt', '.out'},
        'icon': "LOG",
        'color': (120, 120, 120)  # Gray
    }
}

def get_file_type_info(file_path):
    """Determine file type group and icon information."""
    ext = file_path.suffix.lower()
    
    # Check if the extension is in any of our groups
    for group, info in FILE_TYPE_GROUPS.items():
        if ext in info['extensions']:
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
                'color': (70, 70, 70)  # Dark gray
            }
        elif mime_type.startswith('application/'):
            return {
                'group': 'application',
                'icon': "APP",
                'color': (120, 0, 0)  # Darker red
            }
    
    # Default for unknown types
    return {
        'group': 'unknown',
        'icon': "FILE",
        'color': (100, 100, 100)  # Medium gray
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
    """Get a preview of text content if the file is text-based."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                # Truncate long lines
                if len(line) > max_line_length:
                    lines.append(line[:max_line_length] + '...')
                else:
                    lines.append(line.rstrip('\n'))
            return lines
    except Exception:
        return None

def create_file_info_card(file_path, width=800, height=1000, cmyk_mode=False):
    """Create an information card for any file type with dynamic height adjustment for preview content."""
    file_path = Path(file_path)
    
    # Try to load fonts
    try:
        title_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 48)
        info_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 24)
        preview_font = ImageFont.truetype("/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf", 14)
    except:
        title_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        preview_font = ImageFont.load_default()

    file_type_info = get_file_type_info(file_path)
    icon = file_type_info['icon']

    try:
        size = os.path.getsize(file_path)
        modified_time = os.path.getmtime(file_path)
        created_time = os.path.getctime(file_path)
    except (FileNotFoundError, PermissionError):
        size = 0
        modified_time = 0
        created_time = 0

    file_info = {
        'Name': file_path.name,
        'Type': f"{file_path.suffix[1:].upper()} ({file_type_info['group']})",
        'Size': format_file_size(size),
        'Modified': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S'),
        'Created': datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S'),
    }

    # Fixed card height for 4x5 aspect ratio
    height = int(width * 5 / 4)

    # --- Calculate layout ---
    header_height = 80
    icon_space = 100 + 40
    metadata_lines = len(file_info)
    metadata_line_height = 30
    metadata_height = metadata_lines * metadata_line_height
    spacing = 10 + 30 + 20
    preview_box_padding = 15
    preview_box_left = int(width * 0.1)
    preview_box_right = int(width * 0.9)
    preview_box_top = header_height + icon_space + metadata_height + spacing
    preview_box_bottom = height - 20  # leave a little bottom margin
    preview_box_height = preview_box_bottom - preview_box_top
    max_line_width_pixels = preview_box_right - preview_box_left - preview_box_padding * 2

    # Calculate font metrics
    temp_img = Image.new('RGB', (width, height))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), 'A', font=preview_font)
    line_height = bbox[3] - bbox[1] + 3
    char_bbox = temp_draw.textbbox((0, 0), 'A', font=preview_font)
    char_width = char_bbox[2] - char_bbox[0]
    max_line_length = max(10, max_line_width_pixels // char_width)
    max_preview_lines = max(1, preview_box_height // line_height)

    # --- Read and wrap preview content ---
    preview_lines = []
    if file_type_info['group'] in ['code', 'data', 'document', 'log']:
        # Read a large chunk of the file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_lines = []
                for i, line in enumerate(f):
                    if i > 1000:  # hard limit for performance
                        break
                    raw_lines.append(line.rstrip('\n'))
        except Exception:
            raw_lines = []
        # Wrap lines to fit preview box width
        for raw_line in raw_lines:
            wrapped = textwrap.wrap(raw_line, width=max_line_length)
            if not wrapped:
                preview_lines.append('')
            else:
                preview_lines.extend(wrapped)
        # Only keep as many lines as fit in the preview box
        preview_lines = preview_lines[:max_preview_lines]

    # --- Draw card ---
    if cmyk_mode:
        from pdf_to_images import create_cmyk_image
        img = create_cmyk_image(width, height, (0, 0, 0, 0))
        rgb_mode = False
    else:
        img = Image.new('RGB', (width, height), 'white')
        rgb_mode = True
    draw = ImageDraw.Draw(img)

    # Convert RGB color to CMYK if needed
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

    border_width = 5
    draw.rectangle([0, 0, width-1, height-1], outline='black', width=border_width)

    # Header
    if rgb_mode:
        draw.rectangle([border_width, border_width, width-border_width, header_height], fill=file_type_info['color'])
        text_color = 'white'
    else:
        draw.rectangle([border_width, border_width, width-border_width, header_height], fill=color)
        text_color = (0, 0, 0, 0)
    draw.text((width//2, header_height//2), file_path.suffix.upper(), fill=text_color, font=title_font, anchor="mm")

    # Icon
    icon_y = header_height + 40
    icon_color = file_type_info['color'] if rgb_mode else color
    draw.text((width//2, icon_y), icon, fill=icon_color, font=title_font, anchor="mm")

    # Metadata
    y = icon_y + 40
    for key, value in file_info.items():
        line = f"{key}: {value}"
        draw.text((width//2, y), line, fill='black', font=info_font, anchor="mm")
        y += 30

    # Preview label
    y = preview_box_top - 30
    draw.text((width//2, y), "Content Preview:", fill='black', font=info_font, anchor="mm")
    y = preview_box_top

    # Preview box
    preview_background_color = (245, 245, 245) if rgb_mode else (0, 0, 0, 4)
    draw.rectangle(
        [preview_box_left, preview_box_top, preview_box_right, preview_box_bottom],
        fill=preview_background_color,
        outline='black',
        width=1
    )
    text_y = preview_box_top + preview_box_padding
    for line in preview_lines:
        draw.text((preview_box_left + preview_box_padding, text_y), line, fill='black', font=preview_font, anchor="lt")
        text_y += line_height

    return img

def determine_file_type(file_path):
    """Categorize files into different types for appropriate rendering."""
    ext = file_path.suffix.lower()
    
    # Images, videos, PDFs
    if ext in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.mp4', '.mov', '.avi', '.mkv', '.pdf', '.heic', '.PNG', '.JPG', '.JPEG', '.HEIC'}:
        return "media"
    
    # Other types
    for group, info in FILE_TYPE_GROUPS.items():
        if ext in info['extensions']:
            return group
    
    # Default to "other" for anything not recognized
    return "other"
