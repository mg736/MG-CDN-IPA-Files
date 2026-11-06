#!/usr/bin/env python3
"""Generate a branded install QR: the code itself, with the app name on a
coloured band underneath.

    ./make_qr.py <app-key> [out.png] [--style band|text] [--color blue|green|...]

The app key is a key in apps.json; the title and URL are read from there, so the
label can never drift from what the install page actually says.

The QR modules stay pure black on white with a full quiet zone — the label lives
outside that area, so scanning is unaffected.
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://mg736.github.io/MG-CDN-IPA-Files"

# Appy Pie brand palette, sampled from appypie-logo.png
COLORS = {
    "blue":   "#1FC0F1",
    "green":  "#2DB92D",
    "yellow": "#F6B32E",
    "orange": "#F5811F",
    "red":    "#F04410",
}
DEFAULT_COLOR = "blue"

FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]

MARGIN = 36        # white border around everything
GAP = 28           # space between QR and label band
BAND_PAD_Y = 20    # vertical padding inside the band
BAND_PAD_X = 28
RADIUS = 16


def load_font(size):
    for path in FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def render_qr(url):
    """qrencode to a temp PNG, then load it. -m 2 keeps the required quiet zone."""
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        subprocess.run(
            ["qrencode", "-o", tmp, "-s", "10", "-m", "2", "-l", "H", url],
            check=True,
        )
        # qrencode writes a palette PNG carrying byte transparency; going via
        # RGBA avoids Pillow's warning about converting that straight to RGB.
        return Image.open(tmp).convert("RGBA").convert("RGB")
    finally:
        os.unlink(tmp)


def fit_text(draw, text, max_width, start=46, floor=20):
    """Largest font size at which the name still fits on one line."""
    for size in range(start, floor - 1, -2):
        font = load_font(size)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return load_font(floor)


def build(title, url, color_hex, style):
    qr = render_qr(url)
    qw, qh = qr.size

    # Work out the label size first so the canvas can be sized to fit it.
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    text_max = max(qw, 560) - 2 * BAND_PAD_X
    font = fit_text(probe, title, text_max)
    bbox = probe.textbbox((0, 0), title, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    band_w = max(qw, tw + 2 * BAND_PAD_X)
    band_h = th + 2 * BAND_PAD_Y
    W = band_w + 2 * MARGIN
    H = MARGIN + qh + GAP + band_h + MARGIN

    canvas = Image.new("RGB", (W, H), "white")
    canvas.paste(qr, ((W - qw) // 2, MARGIN))
    draw = ImageDraw.Draw(canvas)

    band_x0 = (W - band_w) // 2
    band_y0 = MARGIN + qh + GAP
    box = [band_x0, band_y0, band_x0 + band_w, band_y0 + band_h]

    if style == "band":
        draw.rounded_rectangle(box, radius=RADIUS, fill=color_hex)
        fill = "white"
    else:  # "text": coloured name with a coloured rule above it
        rule_y = band_y0 - GAP // 2
        draw.rounded_rectangle(
            [band_x0, rule_y, band_x0 + band_w, rule_y + 6], radius=3, fill=color_hex
        )
        fill = color_hex

    # textbbox offsets matter for vertical centring — subtract bbox origin.
    tx = box[0] + (band_w - tw) // 2 - bbox[0]
    ty = box[1] + (band_h - th) // 2 - bbox[1]
    draw.text((tx, ty), title, font=font, fill=fill)
    return canvas


def main():
    args = [a for a in sys.argv[1:]]
    style, color = "band", DEFAULT_COLOR
    for flag, setter in (("--style", "style"), ("--color", "color")):
        if flag in args:
            i = args.index(flag)
            val = args[i + 1]
            if setter == "style":
                style = val
            else:
                color = val
            del args[i:i + 2]

    if not args:
        sys.exit(__doc__)
    key = args[0]
    out = args[1] if len(args) > 1 else os.path.join(ROOT, f"{key}-qr.png")

    apps = json.load(open(os.path.join(ROOT, "apps.json")))["apps"]
    if key not in apps:
        sys.exit(f"ERROR: '{key}' is not a key in apps.json. "
                 f"Known keys: {', '.join(apps)}")
    if color not in COLORS:
        sys.exit(f"ERROR: unknown colour '{color}'. Choose from: {', '.join(COLORS)}")

    title = apps[key]["title"]
    url = f"{BASE}/{key}.html"
    build(title, url, COLORS[color], style).save(out)
    print(f"{out}  ({title} -> {url}, {style}/{color})")


if __name__ == "__main__":
    main()
