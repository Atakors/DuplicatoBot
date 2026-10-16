"""Allow ``python -m duplicatorbot`` to start the bot.

This is the entry point used by hosting platforms (see ``render.yaml``) and is
equivalent to running ``python main.py``.
"""

from __future__ import annotations

import logging
import sys

from .config import load_settings


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=logging.INFO,
    )

    # Imported lazily so that ``python -m duplicatorbot`` fails with a helpful
    # message instead of a dependency traceback when Pillow is missing.
    from .bot import run

    settings = load_settings()
    if not settings.token:
        print(
            "TELEGRAM_BOT_TOKEN is missing.\n"
            "Set it in the environment (Render dashboard) or in a .env file.",
            file=sys.stderr,
        )
        return 1

    run(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
