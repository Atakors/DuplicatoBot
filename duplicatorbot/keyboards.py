"""Inline keyboards for configuring the duplication pattern."""

from __future__ import annotations

from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .imaging import ORIENTATIONS, RESIZE_PRESETS, ROTATIONS
from .layouts import SUPPORTED_COUNTS

#: Callback prefixes: ``opt`` changes an option, ``act`` triggers an action.
OPTION_CALLBACK = "opt"
ACTION_CALLBACK = "act"

ACTION_RENDER = "render"
ACTION_RESET = "reset"

_ORIENTATION_LABELS: Dict[str, str] = {
    "auto": "Auto",
    "landscape": "Landscape",
    "portrait": "Portrait",
}


def _marker(active: bool) -> str:
    return "\u2705" if active else "\u25ab\ufe0f"


def option_callback(key: str, value: str) -> str:
    """Build callback data for an option change (kept short for Telegram)."""

    return f"{OPTION_CALLBACK}:{key}:{value}"


def parse_callback(data: str) -> tuple:
    """Split callback data into ``(namespace, key, value)``."""

    parts = (data or "").split(":", 2)
    while len(parts) < 3:
        parts.append("")
    return parts[0], parts[1], parts[2]


def build_keyboard(options: Dict[str, object]) -> InlineKeyboardMarkup:
    """Render the full control panel for the given option state."""

    count = int(options.get("count", 4))
    rotation = int(options.get("rotation", 0))
    orientation = str(options.get("orientation", "auto"))
    resize = str(options.get("resize", "medium"))

    rows = [
        [
            InlineKeyboardButton(
                f"{_marker(count == value)} {value}",
                callback_data=option_callback("count", str(value)),
            )
            for value in SUPPORTED_COUNTS[:4]
        ],
        [
            InlineKeyboardButton(
                f"{_marker(rotation == value)} {value}\u00b0",
                callback_data=option_callback("rotation", str(value)),
            )
            for value in ROTATIONS
        ],
        [
            InlineKeyboardButton(
                f"{_marker(orientation == value)} {_ORIENTATION_LABELS[value]}",
                callback_data=option_callback("orientation", value),
            )
            for value in ORIENTATIONS
        ],
        [
            InlineKeyboardButton(
                f"{_marker(resize == key)} {key.capitalize()} ({px}px)",
                callback_data=option_callback("resize", key),
            )
            for key, px in RESIZE_PRESETS.items()
        ],
        [
            InlineKeyboardButton("\U0001f5bc\ufe0f Render", callback_data=f"{ACTION_CALLBACK}:{ACTION_RENDER}:"),
            InlineKeyboardButton("\u267b\ufe0f Reset", callback_data=f"{ACTION_CALLBACK}:{ACTION_RESET}:"),
        ],
    ]

    return InlineKeyboardMarkup(rows)
