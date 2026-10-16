"""Entry point for DuplicatorBot.

Usage::

    python main.py

The script works from any working directory: it adds its own folder to
``sys.path`` so the sibling ``duplicatorbot`` package is always importable.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make ``duplicatorbot`` importable even when the script is launched from
# another directory (e.g. ``python d:/DuplicatorBot/main.py``).
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from duplicatorbot.bot import run  # noqa: E402
from duplicatorbot.config import load_settings  # noqa: E402


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=logging.INFO,
    )

    settings = load_settings()
    if not settings.token:
        print(
            "TELEGRAM_BOT_TOKEN is missing.\n"
            "Copy .env.example to .env and paste the token from @BotFather.",
            file=sys.stderr,
        )
        return 1

    run(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
