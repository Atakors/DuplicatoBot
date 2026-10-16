# DuplicatorBot — [@Duplicayoredz_bot](https://t.me/Duplicayoredz_bot)

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
start_bot.py                launcher that works from any directory
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
   Requires **Python 3.9 – 3.12** (3.12.7 recommended; see
   [Python version](#python-version)).
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Create your environment file:

   ```
   copy .env.example .env
   ```

   Then edit `.env` and set `TELEGRAM_BOT_TOKEN`.

4. Run the bot from the project folder:

   ```
   cd d:/DuplicatorBot
   python main.py
   ```

   Or, from any other directory, use the launcher:

   ```
   python d:/DuplicatorBot/start_bot.py
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

## Troubleshooting

**`ModuleNotFoundError: No module named 'duplicatorbot'`**

Python could not see the package because the command was run from a different
working directory. Either run it from the project folder, or use the launcher
which resolves the path itself:

```
cd d:/DuplicatorBot && python main.py
python d:/DuplicatorBot/start_bot.py
```

**`TELEGRAM_BOT_TOKEN is missing`**

The `.env` file was not created yet, or it lives in a different folder. Create it
next to `main.py`:

```
copy d:\DuplicatorBot\.env.example d:\DuplicatorBot\.env
```

Then paste the token from [@BotFather](https://t.me/BotFather) after
`TELEGRAM_BOT_TOKEN=`.

**`Conflict: terminated by other getUpdates request`**

Another copy of the bot is already polling with the same token. Stop the other
process before starting a new one.

## Deploying to Render

The repository ships a [`render.yaml`](render.yaml:1) Blueprint that runs the bot as a
**background worker** (long polling needs no public port or webhook).

1. Push this repository to GitHub.
2. In Render choose **New → Blueprint**, point it at the repository and apply.
3. When prompted, set `TELEGRAM_BOT_TOKEN` — it is declared with `sync: false`, so the
   value is entered in the dashboard and never committed to git.

### Python version

The Blueprint pins `PYTHON_VERSION=3.12.7`. This matters: `Pillow==10.4.0` publishes no
cp314 wheels, and python-telegram-bot 21.6 relies on `asyncio.get_event_loop()`, whose
auto-creating behaviour was removed in Python 3.14. `3.12.7` avoids both problems.

If you must run on 3.13/3.14, [`_install_event_loop()`](duplicatorbot/bot.py:436) already
installs an event loop explicitly, so the polling error is handled. On 3.14 you would also
need `Pillow>=11.3` (or a working compiler) so the native extension can build.

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
