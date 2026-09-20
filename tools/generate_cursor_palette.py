"""Generate the tiny periodic UV palette used by the twelve cursor edges."""
import colorsys
from pathlib import Path
from PIL import Image

PERIOD = 512
ROOT = Path(__file__).resolve().parents[1]


def main():
    image = Image.new('RGB', (PERIOD * 2 + 1, 8))
    for x in range(image.width):
        color = tuple(round(v * 255) for v in colorsys.hsv_to_rgb((x % PERIOD) / PERIOD, .55, .98))
        for y in range(8):
            image.putpixel((x, y), color if y < 4 else (211, 92, 114))
    image.save(ROOT / 'resource_pack/textures/modern_projection/cursor_spectrum.png', optimize=True)


if __name__ == '__main__':
    main()
