# README_pillow_textbox.py

## Overview

`pillow_textbox` is a Python module that extends the capabilities of the Pillow imaging library by providing advanced text box rendering features. It allows you to draw multi-line, wrapped, and aligned text inside a specified rectangular area on a PIL image, with support for custom fonts, padding, line spacing, background fill, rounded corners, and outlines.

## Key Features
- Draws text inside a bounding box with automatic word wrapping.
- Supports horizontal and vertical alignment (left, center, right, top, middle, bottom).
- Customizable padding and line spacing between text lines.
- Optional background fill, rounded corners, and outline for the text box.
- Works with any PIL ImageDraw object and font.

## Typical Usage
```python
from PIL import Image, ImageDraw, ImageFont
from pillow_textbox import draw_text_box

img = Image.new('RGB', (400, 200), color='white')
draw = ImageDraw.Draw(img)
font = ImageFont.truetype('arial.ttf', 16)
text = "This is a long string that will be wrapped and aligned inside the box."
draw_text_box(
    draw,
    text,
    font,
    box=(20, 20, 360, 160),
    padding=10,
    line_spacing=4,
    align="left",
    v_align="top",
    fill=(0, 0, 0),
    background_fill=(240, 240, 240),
    background_radius=8,
    background_outline=(100, 100, 100),
    background_outline_width=2,
)
img.show()
```

## Use Cases
- Rendering metadata or multi-line labels on images.
- Creating visually appealing cards, posters, or previews with text overlays.
- Any scenario where you need precise control over text layout in images.

## Requirements
- Python 3.x
- Pillow

## Documentation
See the module's docstrings or source code for detailed API documentation and options.
