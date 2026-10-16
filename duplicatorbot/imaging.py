"""Image processing: duplicate + pattern + rotate + resize + orientation."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageColor, ImageOps

from .layouts import Layout, get_layout

ORIENTATION_AUTO = "auto"
ORIENTATION_LANDSCAPE = "landscape"
ORIENTATION_PORTRAIT = "portrait"

#: Choices exposed in the bot UI.
ORIENTATIONS = (ORIENTATION_AUTO, ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT)

#: Rotation steps exposed in the bot UI (degrees, clockwise).
ROTATIONS = (0, 90, 180, 270)

#: Resize presets exposed in the bot UI: key -> target long edge in pixels.
RESIZE_PRESETS = {
    "small": 720,
    "medium": 1080,
    "large": 1440,
    "huge": 2160,
}

#: Aspect ratios (width / height) enforced for each orientation by letterboxing.
ORIENTATION_ASPECT = {
    ORIENTATION_LANDSCAPE: 4 / 3,
    ORIENTATION_PORTRAIT: 3 / 4,
}

#: Breathing room around the pattern, as a fraction of one tile.
GUTTER_RATIO = 0.05


@dataclass(frozen=True)
class RenderOptions:
    """Everything needed to render a duplicated pattern."""

    count: int = 4
    orientation: str = ORIENTATION_AUTO
    rotation: int = 0
    resize: str = "medium"
    background: str = "FFFFFF"

    def normalised(self) -> "RenderOptions":
        """Return a copy with every field clamped to a supported value."""

        return RenderOptions(
            count=self.count,
            orientation=self.orientation
            if self.orientation in ORIENTATIONS
            else ORIENTATION_AUTO,
            rotation=self.rotation if self.rotation in ROTATIONS else 0,
            resize=self.resize if self.resize in RESIZE_PRESETS else "medium",
            background=self.background,
        )


def _background_colour(value: str) -> tuple:
    """Convert a hex string into an RGB tuple, falling back to white."""

    candidate = (value or "FFFFFF").strip().lstrip("#")
    try:
        return ImageColor.getrgb("#" + candidate)
    except ValueError:
        return (255, 255, 255)


def _square_tile(source: Image.Image, side: int) -> Image.Image:
    """Centre-crop the source into a square tile of ``side`` pixels.

    Cropping (rather than stretching) guarantees the duplicated pattern never
    distorts the original image.
    """

    return ImageOps.fit(source, (side, side), method=Image.LANCZOS, centering=(0.5, 0.5))


def _compose_grid(tile: Image.Image, layout: Layout, gap: int, background: tuple) -> Image.Image:
    """Paste ``layout.count`` copies of ``tile`` onto a fresh canvas."""

    canvas_w = tile.width * layout.cols + gap * (layout.cols + 1)
    canvas_h = tile.height * layout.rows + gap * (layout.rows + 1)
    canvas = Image.new("RGB", (canvas_w, canvas_h), background)

    for index in range(layout.count):
        row, col = layout.position(index)
        left = gap + col * (tile.width + gap)
        top = gap + row * (tile.height + gap)
        canvas.paste(tile, (left, top))

    return canvas


def _fit_aspect(canvas: Image.Image, orientation: str, background: tuple) -> Image.Image:
    """Letterbox the canvas so it matches the requested orientation ratio."""

    aspect = ORIENTATION_ASPECT.get(orientation)
    if aspect is None:
        return canvas

    current = canvas.width / canvas.height
    if abs(current - aspect) < 0.01:
        return canvas

    if current > aspect:
        target_size = (canvas.width, int(round(canvas.width / aspect)))
    else:
        target_size = (int(round(canvas.height * aspect)), canvas.height)

    framed = Image.new("RGB", target_size, background)
    framed.paste(canvas, ((target_size[0] - canvas.width) // 2, (target_size[1] - canvas.height) // 2))
    return framed


def _scale_to_long_edge(canvas: Image.Image, long_edge: int) -> Image.Image:
    """Scale the canvas so its longest side equals ``long_edge`` pixels."""

    current = max(canvas.size)
    if current == long_edge or current == 0:
        return canvas

    scale = long_edge / current
    new_size = (max(1, int(round(canvas.width * scale))), max(1, int(round(canvas.height * scale))))
    return canvas.resize(new_size, Image.LANCZOS)


def build_pattern(
    image: Image.Image,
    options: RenderOptions | None = None,
    max_output_edge: int = 3000,
) -> Image.Image:
    """Duplicate ``image`` according to ``options`` and return the new image.

    Steps, in order:
        1. EXIF normalisation and conversion to RGB
        2. duplication into the pattern grid (2, 4, 6 or 8 copies)
        3. rotation in 90 degree steps
        4. landscape / portrait aspect enforcement (letterboxed, never cropped)
        5. resize so the long edge matches the requested preset
    """

    options = (options or RenderOptions()).normalised()

    source = ImageOps.exif_transpose(image)
    if source.mode != "RGB":
        source = source.convert("RGB")

    layout = get_layout(options.count)
    background = _background_colour(options.background)
    long_edge = min(RESIZE_PRESETS[options.resize], max_output_edge)

    # Size each tile so the finished grid already lands on the requested
    # long edge, then the final scale step becomes a no-op refinement.
    grid_span = max(layout.rows, layout.cols)
    gap = int(round((long_edge / grid_span) * GUTTER_RATIO)) if layout.slots > 1 else 0
    side = max(1, (long_edge - gap * (grid_span + 1)) // grid_span)

    tile = _square_tile(source, side)
    canvas = _compose_grid(tile, layout, gap, background)

    if options.rotation:
        canvas = canvas.rotate(-options.rotation, expand=True, fillcolor=background)

    canvas = _fit_aspect(canvas, options.orientation, background)
    return _scale_to_long_edge(canvas, long_edge)


def describe(options: RenderOptions) -> str:
    """Human readable summary of the current options (used in captions)."""

    options = options.normalised()
    orientation = {
        ORIENTATION_AUTO: "Auto (pattern native)",
        ORIENTATION_LANDSCAPE: "Landscape",
        ORIENTATION_PORTRAIT: "Portrait",
    }[options.orientation]
    return (
        f"Pattern: *{options.count}* copies\n"
        f"Rotation: *{options.rotation}deg*\n"
        f"Resize: *{options.resize}* ({RESIZE_PRESETS[options.resize]}px long edge)\n"
        f"Mode: *{orientation}*"
    )
