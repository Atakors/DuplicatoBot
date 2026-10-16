"""Convenience launcher that can be executed from any directory.

Usage::

    python d:/DuplicatorBot/start_bot.py

Unlike ``python main.py``, this wrapper always resolves the project folder
first, so the ``duplicatorbot`` package is importable no matter where the
command is run from.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
