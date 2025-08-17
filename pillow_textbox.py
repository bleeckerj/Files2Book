from __future__ import annotations
from typing import Iterable, List, Tuple, Union
from PIL import ImageDraw, ImageFont

Number = Union[int, float]
Box = Tuple[int, int, int, int]  # (x, y, width, height)

def _norm_padding(pad: Union[Number, Tuple[Number, Number], Tuple[Number, Number, Number, Number]]) -> Tuple[int, int, int, int]:
    """Normalize padding to (left, top, right, bottom) ints."""
    if isinstance(pad, (int, float)):
        return int(pad), int(pad), int(pad), int(pad)
    if len(pad) == 2:
        x, y = pad
        return int(x), int(y), int(x), int(y)
    l, t, r, b = pad  # type: ignore
    return int(l), int(t), int(r), int(b)

def _text_width(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, s: str) -> int:
    l, t, r, b = draw.textbbox((0, 0), s, font=font)
    return r - l

def _text_height(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, s: str) -> int:
    l, t, r, b = draw.textbbox((0, 0), s if s else " ", font=font)
    return b - t

def wrap_text_to_width(
    text: str,
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    break_long_words: bool = True,
) -> List[str]:
    """
    Simple greedy word-wrap that respects single newlines.
    Returns a list of lines whose pixel width <= max_width.
    """
    lines: List[str] = []
    for para in text.split("\n"):
        # preserve explicit blank lines
        if not para.strip():
            lines.append("")
            continue

        words = para.split(" ")
        cur = ""
        for w in words:
            candidate = w if not cur else f"{cur} {w}"
            if _text_width(draw, font, candidate) <= max_width:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                if break_long_words and _text_width(draw, font, w) > max_width:
                    # hard-wrap inside a single long word
                    piece = ""
                    for ch in w:
                        if _text_width(draw, font, piece + ch) <= max_width:
                            piece += ch
                        else:
                            lines.append(piece)
                            piece = ch
                    cur = piece
                else:
                    cur = w
        if cur:
            lines.append(cur)
    return lines

def draw_text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    box: Box,
    padding: Union[Number, Tuple[Number, Number], Tuple[Number, Number, Number, Number]] = 0,
    line_spacing: int = 0,
    align: str = "left",      # 'left' | 'center' | 'right'
    v_align: str = "top",      # 'top' | 'middle' | 'bottom'
    fill: Union[str, Tuple[int, int, int, int]] = "black",
    stroke_width: int = 0,
    stroke_fill: Union[str, Tuple[int, int, int, int], None] = None,
    break_long_words: bool = True,
    # New: optional background
    background_fill: Union[str, Tuple[int, int, int, int], None] = None,
    background_radius: int = 0,
    background_outline: Union[str, Tuple[int, int, int, int], None] = None,
    background_outline_width: int = 0,
    background_inset: int = 0,
) -> dict:
    """
    Draw wrapped text inside a rectangular box with padding and alignment options.

    Returns a dict with:
      - 'lines': list[str] of wrapped lines
      - 'anchor_xy': (x, y) top-left where drawing began (after vertical alignment)
      - 'used_size': (w, h) total drawn text block size
      - 'truncated': bool (False; this function does not clip — it draws only what fits width)
    """
    x, y, w, h = box

    # Optional background behind the text box
    if background_fill is not None or background_outline is not None:
        bx0 = x + int(background_inset)
        by0 = y + int(background_inset)
        bx1 = x + w - int(background_inset)
        by1 = y + h - int(background_inset)
        try:
            draw.rounded_rectangle(
                [bx0, by0, bx1, by1],
                radius=max(0, int(background_radius)),
                fill=background_fill,
                outline=background_outline,
                width=max(0, int(background_outline_width)),
            )
        except Exception:
            # Fallback if rounded_rectangle is unavailable
            draw.rectangle(
                [bx0, by0, bx1, by1],
                fill=background_fill,
                outline=background_outline,
                width=max(0, int(background_outline_width)),
            )

    pad_l, pad_t, pad_r, pad_b = _norm_padding(padding)
    inner_w = max(0, w - pad_l - pad_r)
    inner_h = max(0, h - pad_t - pad_b)

    # Wrap lines to inner width
    lines = wrap_text_to_width(text, draw, font, inner_w, break_long_words=break_long_words)

    # Compute line heights and total block height
    line_heights = [_text_height(draw, font, ln) for ln in lines]
    if not lines:
        line_heights = []
    total_h = sum(line_heights) + (len(lines) - 1) * max(0, line_spacing)
    total_h = max(0, total_h)

    # Vertical alignment inside the inner box
    if v_align == "top":
        start_y = y + pad_t
    elif v_align == "middle":
        start_y = y + pad_t + max(0, (inner_h - total_h) // 2)
    elif v_align == "bottom":
        start_y = y + pad_t + max(0, inner_h - total_h)
    else:
        raise ValueError("v_align must be 'top', 'middle', or 'bottom'.")

    # Draw each line with horizontal alignment
    cur_y = start_y
    for i, line in enumerate(lines):
        lw = _text_width(draw, font, line if line else " ")
        if align == "left":
            cur_x = x + pad_l
        elif align == "center":
            cur_x = x + pad_l + max(0, (inner_w - lw) // 2)
        elif align == "right":
            cur_x = x + w - pad_r - lw
        else:
            raise ValueError("align must be 'left', 'center', or 'right'.")

        draw.text(
            (cur_x, cur_y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        cur_y += line_heights[i] + (line_spacing if i < len(lines) - 1 else 0)

    used_w = min(inner_w, max([_text_width(draw, font, ln) for ln in lines], default=0))
    return {
        "lines": lines,
        "anchor_xy": (x + pad_l, start_y),
        "used_size": (used_w, total_h),
        "truncated": False,
    }