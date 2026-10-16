"""Offline smoke test for the image engine (no Telegram token required).

Run with::

    python selftest.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from duplicatorbot.imaging import ORIENTATIONS, RESIZE_PRESETS, ROTATIONS, RenderOptions, build_pattern
from duplicatorbot.keyboards import OPTION_CALLBACK, parse_callback, option_callback
from duplicatorbot.layouts import SUPPORTED_COUNTS, get_layout

OUTPUT_DIR = Path("selftest_output")


def make_sample(width: int = 640, height: int = 400) -> Image.Image:
    """Create a simple gradient sample image."""

    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (x * 255 // width, y * 255 // height, 128)
    return image


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    sample = make_sample()
    created = []

    for count in SUPPORTED_COUNTS:
        layout = get_layout(count)
        assert layout.slots >= count, f"layout {layout} cannot hold {count} tiles"

    for count in SUPPORTED_COUNTS:
        for orientation in ORIENTATIONS:
            for rotation in ROTATIONS:
                options = RenderOptions(
                    count=count,
                    orientation=orientation,
                    rotation=rotation,
                    resize="small",
                )
                result = build_pattern(sample, options, max_output_edge=3000)
                assert max(result.size) <= RESIZE_PRESETS["small"] + 2, result.size

                if orientation == "landscape":
                    assert result.width >= result.height, (orientation, result.size)
                elif orientation == "portrait":
                    assert result.height >= result.width, (orientation, result.size)

                name = f"{count}_{orientation}_{rotation}.jpg"
                result.save(OUTPUT_DIR / name, quality=88)
                created.append(name)

    namespace, key, value = parse_callback(option_callback("count", "8"))
    assert (namespace, key, value) == (OPTION_CALLBACK, "count", "8")

    print(f"OK - generated {len(created)} patterns in '{OUTPUT_DIR}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
