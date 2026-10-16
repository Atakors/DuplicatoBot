# DuplicatorBot

A Telegram bot that duplicates an image into a predefined pattern (**2, 4, 6 or 8** copies)
with **rotation**, **resize** and **Landscape / Portrait** controls.

Tiles are always centre-cropped squares, so the pattern never distorts the original image.

## Features

| Control | Options | Notes |
| --- | --- | --- |
| Pattern | 2, 4, 6, 8 | 2 = 1x2, 4 = 2x2, 6 = 2x3, 8 = 4x2 grid of the same image |
| Rotation | 0, 90, 180, 270 | Rotates the finished collage clockwise |
| Resize | small, medium, large, huge | 720 / 1080 / 1440 / 2160 px on the long edge |
| Mode | Auto, Landscape, Portrait | Landscape/Portrait letterbox the collage to 4:3 / 3:4 |

Additional behaviour:

* Accepts photos and image files (up to the Telegram bot download limit of 20 MB).
* EXIF orientation is applied automatically.
* Per-user settings are remembered between images.
* Optional user allow-list.

## Project layout

```
main.py                     entry point
selftest.py                 offline image-engine smoke test (no token needed)
requirements.txt
.env.example
duplicatorbot/
    __init__.py
    bot.py                  handlers, sessions, rendering
    config.py               environment settings
    imaging.py              duplicate / rotate / resize / orientation engine
    keyboards.py            inline keyboard builders
    layouts.py              grid definitions for 2/4/6/8
```

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create your environment file:

   ```
   copy .env.example .env
   ```

   Then edit `.env` and set `TELEGRAM_BOT_TOKEN`.

4. Run the bot:

   ```
   python main.py
   ```

## Usage

1. Send `/start` to the bot.
2. Send a photo, or open a **compressed-as-file** image (documents with an image type work too).
3. Tap the buttons to choose the pattern, rotation, resize and mode.
4. Tap **Render** to receive the duplicated image.

### Commands

| Command | Description |
| --- | --- |
| `/start` | Welcome message and the control panel |
| `/help` | Explains every option |
| `/settings` | Re-open the control panel for the stored image |
| `/reset` | Restore default options (4 copies, 0°, medium, Auto) |
| `/cancel` | Forget the stored image |

## Configuration

All settings live in `.env`:

| Variable | Default | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | *(required)* | Token from @BotFather |
| `ALLOWED_USER_IDS` | *(empty)* | Comma separated numeric ids; empty allows everyone |
| `MAX_OUTPUT_EDGE` | `3000` | Safety cap in pixels for the long edge |
| `CANVAS_BACKGROUND` | `FFFFFF` | Background hex colour, no `#` |

## Verifying the image engine

`selftest.py` renders every combination of pattern/orientation/rotation and asserts the
output geometry, without needing a bot token:

```
python selftest.py
```

Results are written to `selftest_output/` (48 JPEG files).

## Implementation notes

* `build_pattern()` in [`imaging.py`](duplicatorbot/imaging.py) performs the pipeline:
  EXIF normalise → build the grid → rotate → letterbox for the orientation → resize.
* Rotation uses `expand=True` and the configured background colour, so no corners are lost.
* Landscape / Portrait use letterboxing rather than extra duplication, so the requested
  copy count is never silently changed.
* Rendering runs in a worker thread (`asyncio.to_thread`) to keep the bot responsive.
