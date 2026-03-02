"""Generate koibokksu app icon as .ico with multiple sizes.

Draws a minimal Teenage Engineering-style radio: OLED screen with
waveform bars on top, speaker grille rings below, on a cream background.
"""

from PIL import Image, ImageDraw


# Colors
CREAM = (245, 240, 232)
BORDER = (212, 208, 200)
SCREEN = (26, 26, 26)
ACCENT = (255, 91, 26)
DIM = (58, 56, 53)
RING1 = (170, 165, 160)
RING2 = (200, 196, 188)
RING3 = (212, 208, 200)
CENTER = (170, 165, 160)


def draw_icon(size):
    """Draw the radio icon at a given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 512  # scale factor

    # Background rounded rect
    radius = int(108 * s)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=CREAM, outline=BORDER, width=max(1, int(2 * s)))

    # Screen
    sr = int(16 * s)
    sx, sy = int(64 * s), int(64 * s)
    sw, sh = int(384 * s), int(120 * s)
    d.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=sr, fill=SCREEN)

    # Waveform bars
    bar_w = int(24 * s)
    bar_gap = int(36 * s)
    bar_r = max(1, int(5 * s))
    bars = [
        (120, 100, 60, True),
        (156, 86,  74, True),
        (192, 96,  64, True),
        (228, 108, 52, True),
        (264, 100, 60, False),
        (300, 92,  68, False),
        (336, 104, 56, False),
        (372, 112, 48, False),
    ]
    for bx, by, bh, played in bars:
        x = int(bx * s)
        y = int(by * s)
        w = bar_w
        h = int(bh * s)
        color = ACCENT if played else DIM
        d.rounded_rectangle([x, y, x + w, y + h], radius=bar_r, fill=color)

    # Speaker grille rings
    cx, cy = int(256 * s), int(325 * s)

    # Outer ring
    r1 = int(115 * s)
    w1 = max(2, int(20 * s))
    d.ellipse([cx - r1, cy - r1, cx + r1, cy + r1], outline=RING1, width=w1)

    # Middle ring
    r2 = int(72 * s)
    w2 = max(2, int(14 * s))
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=RING2, width=w2)

    # Inner ring
    r3 = int(32 * s)
    w3 = max(1, int(10 * s))
    d.ellipse([cx - r3, cy - r3, cx + r3, cy + r3], outline=RING3, width=w3)

    # Center dot
    r4 = max(2, int(10 * s))
    d.ellipse([cx - r4, cy - r4, cx + r4, cy + r4], fill=CENTER)

    return img


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]

    # Save .ico
    ico_path = "src/static/icon.ico"
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Generated {ico_path} with sizes: {sizes}")

    # Also save a 256px PNG for reference
    png_path = "src/static/icon-256.png"
    images[-1].save(png_path, format="PNG")
    print(f"Generated {png_path}")


if __name__ == "__main__":
    main()
