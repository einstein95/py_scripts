#!/usr/bin/env python3
"""
SCI Font Renderer
Reads a SCI engine font resource file and renders all characters
into a grid image (8 characters wide).

Usage:
    python sci_font_render.py <font_file> [output_image]

If no output path is given, it defaults to <font_file>.png
"""

import sys
import struct
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")


def read_u16le(data: bytes, offset: int) -> int:
    """Read a 16-bit little-endian unsigned integer."""
    return struct.unpack_from("<H", data, offset)[0]


def parse_font(data: bytes) -> tuple[int, list[dict[str, str | int | list]]]:
    """
    Parse a SCI font resource.

    Returns:
        (line_height, characters)
        where characters is a list of dicts with keys:
            width, height, bitmap (list of rows, each a list of bools)
    """
    if len(data) < 6:
        raise ValueError("File too short to be a SCI font resource.")

    _always_zero: int = read_u16le(data, 0)
    numchar: int = read_u16le(data, 2)
    line_height: int = read_u16le(data, 4)

    # Read the offset table (starts at byte 6, one u16 per character)
    offsets: list[int] = []
    for nr in range(numchar):
        off = read_u16le(data, 6 + nr * 2)
        offsets.append(off)

    characters: list[bytes] = []
    for nr, char_offset in enumerate(offsets):
        if char_offset + 2 > len(data):
            raise ValueError(
                f"Character #{nr} offset 0x{char_offset:04X} is out of bounds."
            )

        char_w: int = data[char_offset]
        char_h: int = data[char_offset + 1]

        # Bytes per row = ceil(width / 8)
        bytes_per_row: int = math.ceil(char_w / 8) if char_w > 0 else 0
        bitmap_size: int = char_h * bytes_per_row

        bm_start: int = char_offset + 2
        bm_end: int = bm_start + bitmap_size
        if bm_end > len(data):
            raise ValueError(
                f"Character #{nr} bitmap extends past end of file "
                f"(needs {bitmap_size} bytes at 0x{bm_start:04X})."
            )

        raw: bytes = data[bm_start:bm_end]

        # Decode bitmap into rows of booleans (True = pixel on)
        rows: list[list[bool]] = []
        for row in range(char_h):
            row_bytes: bytes = raw[row * bytes_per_row : (row + 1) * bytes_per_row]
            pixels: list[bool] = []
            for col in range(char_w):
                byte_idx: int = col // 8
                bit_idx: int = 7 - (col % 8)  # MSB first
                pixel = bool(row_bytes[byte_idx] & (1 << bit_idx))
                pixels.append(pixel)
            rows.append(pixels)

        characters.append(
            {
                "index": nr,
                "width": char_w,
                "height": char_h,
                "bitmap": rows,
            }
        )

    return line_height, characters


def render_font_grid(
    line_height: int,
    characters: list[dict],
    cols: int = 8,
    scale: int = 1,
    padding: int = 0,
    bg_color: tuple = (0, 0, 0),
    fg_color: tuple = (255, 255, 255),
) -> Image.Image:
    """
    Render all characters into a grid image.

    Args:
        line_height:   Font line height from header (used for cell height).
        characters:    Parsed character list.
        cols:          Number of columns in the grid (default 8).
        scale:         Pixel scale factor (1 = native, 2 = 2x zoom, etc.)
        padding:       Padding in (unscaled) pixels around each cell's glyph.
        bg_color:      Overall background colour.
        fg_color:      Glyph pixel colour.
        cell_bg_color: Per-cell background colour.
    """
    # LABEL_H = 8  # unscaled pixels reserved at the bottom of each cell for index label

    numchar: int = len(characters)
    rows: int = math.ceil(numchar / cols)

    # Cell dimensions (unscaled)
    cell_w: int = padding * 2 + max((c["width"] for c in characters), default=8)
    cell_h: int = padding * 2 + line_height

    img_w: int = cols * cell_w * scale
    img_h: int = rows * cell_h * scale

    img: Image = Image.new("RGB", (img_w, img_h), bg_color)
    draw: ImageDraw = ImageDraw.Draw(img)

    for char in characters:
        nr: int = char["index"]
        col: int = nr % cols
        row: int = nr // cols

        # Cell origin in final (scaled) image
        cx: int = col * cell_w * scale
        cy: int = row * cell_h * scale

        # Draw cell background
        # draw.rectangle(
        #     [
        #         cx + scale,
        #         cy + scale,
        #         cx + cell_w * scale - scale - 1,
        #         cy + cell_h * scale - scale - 1,
        #     ],
        #     fill=cell_bg_color,
        # )

        # Draw glyph pixels
        glyph_x: int = cx + padding * scale
        glyph_y: int = cy + padding * scale

        for ry, row_pixels in enumerate(char["bitmap"]):
            for rx, pixel in enumerate(row_pixels):
                if pixel:
                    px: int = glyph_x + rx * scale
                    py: int = glyph_y + ry * scale
                    draw.rectangle(
                        [px, py, px + scale - 1, py + scale - 1],
                        fill=fg_color,
                    )

    return img


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    font_path = Path(sys.argv[1])
    out_path: Path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else font_path.with_suffix(".png")
    )

    print(f"Reading:  {font_path}")
    data: bytes = font_path.read_bytes()[2:]

    line_height, characters = parse_font(data)
    print(f"  Characters : {len(characters)}")
    print(f"  Line height: {line_height} px")

    # Choose a scale so small fonts are still readable
    # (native SCI fonts are often 4–8 px tall)
    # auto_scale: int = max(1, 16 // max(line_height, 1))
    # scale: int = min(auto_scale, 4)  # cap at 4×

    img: Image = render_font_grid(line_height, characters, cols=8)  # , scale=scale)
    img.save(out_path)
    print(f"Saved:    {out_path}  ({img.width}×{img.height} px)")  # , scale={scale}×)")


if __name__ == "__main__":
    main()
