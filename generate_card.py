"""Generate glassmorphism card PNGs from Figma CSS specs."""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


SCALE = 3
WIDTH, HEIGHT = 430 * SCALE, 270 * SCALE
RADIUS = 20 * SCALE
BASE = "c:/Users/서지원/OneDrive/Documents/Coding/AMIC x PETRA Platform"


def rounded_rect_mask(w: int, h: int, r: int) -> Image.Image:
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return mask


def add_noise(card: Image.Image, strength: int = 15) -> Image.Image:
    w, h = card.size
    noise_arr = np.random.randint(0, 255, (h, w), dtype=np.uint8)
    alpha = np.clip(noise_arr.astype(np.int16) - (255 - strength), 0, strength).astype(
        np.uint8
    )
    noise_layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    noise_layer.putalpha(Image.fromarray(alpha))
    return Image.alpha_composite(card, noise_layer)


def radial_gradient_arr(
    w: int,
    h: int,
    cx_pct: float,
    cy_pct: float,
    rx_pct: float,
    ry_pct: float,
    color: tuple[int, int, int],
    max_alpha: float,
) -> np.ndarray:
    """Return RGBA numpy array for a radial gradient."""
    arr = np.zeros((h, w, 4), dtype=np.float64)
    cx, cy = w * cx_pct, h * cy_pct
    rx, ry = max(w * rx_pct, 1), max(h * ry_pct, 1)

    ys, xs = np.mgrid[0:h, 0:w]
    dist = np.sqrt(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2)
    a = np.clip(1.0 - dist, 0.0, 1.0) * max_alpha * 255

    arr[:, :, 0] = color[0]
    arr[:, :, 1] = color[1]
    arr[:, :, 2] = color[2]
    arr[:, :, 3] = a
    return arr.astype(np.uint8)


# ── Card 02: Purple glassmorphism + wave pattern ────────────────────────────


def make_card_02() -> Image.Image:
    # Start with a semi-opaque purple base (simulating glass over dark bg)
    bg_arr = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    for y in range(HEIGHT):
        t = y / HEIGHT
        bg_arr[y, :, 0] = int(40 + 30 * t)  # R: dark purple tint
        bg_arr[y, :, 1] = int(20 + 15 * t)  # G
        bg_arr[y, :, 2] = int(80 + 40 * (1 - t))  # B: richer blue-purple at top
        bg_arr[y, :, 3] = 255
    card = Image.fromarray(bg_arr, "RGBA")

    # Bright purple glow in center
    glow = radial_gradient_arr(
        WIDTH,
        HEIGHT,
        cx_pct=0.4,
        cy_pct=0.5,
        rx_pct=0.8,
        ry_pct=0.9,
        color=(154, 118, 255),
        max_alpha=0.35,
    )
    card = Image.alpha_composite(card, Image.fromarray(glow, "RGBA"))

    # Wave pattern
    wave_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wave_layer)
    num_waves = 70
    for i in range(num_waves):
        phase = i * 0.15
        amplitude = WIDTH * 0.06 + i * 1.2
        y_offset = -HEIGHT * 0.6 + i * (HEIGHT * 2.0 / num_waves)
        points = []
        for x in range(0, WIDTH + 5, 3):
            t = x / WIDTH
            y = y_offset + amplitude * math.sin(t * math.pi * 2.5 + phase)
            y += amplitude * 0.3 * math.sin(t * math.pi * 4 + phase * 1.5)
            points.append((x, y))
        a = max(30, min(120, 40 + i))
        draw.line(points, fill=(190, 160, 255, a), width=max(1, SCALE))
    card = Image.alpha_composite(card, wave_layer)

    # Noise
    card = add_noise(card, 12)

    # Paypass icon (top-right)
    icon = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    idraw = ImageDraw.Draw(icon)
    cx, cy = int(WIDTH * 0.87), int(HEIGHT * 0.20)
    for j in range(3):
        r = 32 * SCALE * (0.3 + j * 0.3)
        idraw.arc(
            [cx - r, cy - r, cx + r, cy + r],
            start=-45,
            end=45,
            fill=(250, 250, 250, 160),
            width=max(2, SCALE),
        )
    card = Image.alpha_composite(card, icon)

    # Apply rounded mask + border
    mask = rounded_rect_mask(WIDTH, HEIGHT, RADIUS)
    card.putalpha(mask)

    border = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [1, 1, WIDTH - 2, HEIGHT - 2],
        radius=RADIUS,
        outline=(200, 180, 255, 90),
        width=SCALE,
    )
    card = Image.alpha_composite(card, border)

    return card


# ── Card 01: Pink/blue/cyan radial gradient glassmorphism ───────────────────


def make_card_01() -> Image.Image:
    # Base: warm pink rgba(255, 173, 187, 0.5) over simulated dark bg
    bg_arr = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    for y in range(HEIGHT):
        t = y / HEIGHT
        bg_arr[y, :, 0] = int(140 + 40 * (1 - t))  # R: pinkish
        bg_arr[y, :, 1] = int(80 + 30 * (1 - t))  # G
        bg_arr[y, :, 2] = int(100 + 20 * (1 - t))  # B
        bg_arr[y, :, 3] = 255
    card = Image.fromarray(bg_arr, "RGBA")

    # Radial 1: blue glow at left-center
    grad1 = radial_gradient_arr(
        WIDTH,
        HEIGHT,
        cx_pct=-0.0459,
        cy_pct=0.3315,
        rx_pct=0.82,
        ry_pct=1.73,
        color=(80, 87, 255),
        max_alpha=0.45,
    )
    card = Image.alpha_composite(card, Image.fromarray(grad1, "RGBA"))

    # Radial 2: cyan glow at top-right
    grad2 = radial_gradient_arr(
        WIDTH,
        HEIGHT,
        cx_pct=1.0523,
        cy_pct=0.0213,
        rx_pct=0.81,
        ry_pct=2.06,
        color=(21, 255, 241),
        max_alpha=0.35,
    )
    card = Image.alpha_composite(card, Image.fromarray(grad2, "RGBA"))

    # Stronger pink overlay
    pink = Image.new("RGBA", (WIDTH, HEIGHT), (255, 173, 187, 50))
    card = Image.alpha_composite(card, pink)

    # Noise
    card = add_noise(card, 12)

    # Rounded mask + border
    mask = rounded_rect_mask(WIDTH, HEIGHT, RADIUS)
    card.putalpha(mask)

    border = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [1, 1, WIDTH - 2, HEIGHT - 2],
        radius=RADIUS,
        outline=(255, 210, 220, 70),
        width=SCALE,
    )
    card = Image.alpha_composite(card, border)

    return card


# ── Output ──────────────────────────────────────────────────────────────────


def save_on_dark_bg(card: Image.Image, filename: str) -> None:
    pad = 20 * SCALE
    cw, ch = WIDTH + pad * 2, HEIGHT + pad * 2
    canvas = Image.new("RGBA", (cw, ch), (12, 8, 24, 255))

    # Shadow
    mask = rounded_rect_mask(WIDTH, HEIGHT, RADIUS)
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (80, 40, 160, 60))
    shadow.putalpha(mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    canvas.paste(shadow, (pad + 8, pad + 10), shadow)

    canvas.paste(card, (pad, pad), card)

    final = canvas.resize((cw // SCALE, ch // SCALE), Image.LANCZOS)
    path = f"{BASE}/{filename}"
    final.save(path, "PNG")
    print(f"Saved: {path} ({final.size[0]}x{final.size[1]}px)")


def main() -> None:
    save_on_dark_bg(make_card_02(), "card-02-purple-waves.png")
    save_on_dark_bg(make_card_01(), "card-01-pink-gradient.png")


if __name__ == "__main__":
    main()
