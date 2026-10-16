"""Entry point for DuplicatorBot.

Usage::

    python main.py
"""

from __future__ import annotations

import logging
import sys

from duplicatorbot.bot import run
from duplicatorbot.config import load_settings


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
