"""Runtime configuration loaded from the environment (and optionally a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import FrozenSet

try:  # python-dotenv is optional at import time, but listed in requirements.txt
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - graceful degradation
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_MAX_OUTPUT_EDGE = 3000
DEFAULT_CANVAS_BACKGROUND = "FFFFFF"


def _parse_int(value: str | None, fallback: int) -> int:
    if value is None or not value.strip():
        return fallback
    try:
        parsed = int(value.strip())
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback


def _parse_user_ids(value: str | None) -> FrozenSet[int]:
    if not value:
        return frozenset()
    ids = set()
    for chunk in value.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError:
            continue
    return frozenset(ids)


def _parse_hex_colour(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    candidate = value.strip().lstrip("#")
    if len(candidate) != 6:
        return fallback
    try:
        int(candidate, 16)
    except ValueError:
        return fallback
    return candidate.upper()


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the bot configuration."""

    token: str
    allowed_user_ids: FrozenSet[int] = field(default_factory=frozenset)
    max_output_edge: int = DEFAULT_MAX_OUTPUT_EDGE
    canvas_background: str = DEFAULT_CANVAS_BACKGROUND

    def is_user_allowed(self, user_id: int | None) -> bool:
        if not self.allowed_user_ids:
            return True
        return user_id is not None and user_id in self.allowed_user_ids


def load_settings(env_file: str | None = ".env") -> Settings:
    """Load settings from the environment, reading ``env_file`` when present."""

    if load_dotenv is not None and env_file:
        load_dotenv(env_file, override=False)

    return Settings(
        token=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip(),
        allowed_user_ids=_parse_user_ids(os.getenv("ALLOWED_USER_IDS")),
        max_output_edge=_parse_int(os.getenv("MAX_OUTPUT_EDGE"), DEFAULT_MAX_OUTPUT_EDGE),
        canvas_background=_parse_hex_colour(
            os.getenv("CANVAS_BACKGROUND"), DEFAULT_CANVAS_BACKGROUND
        ),
    )
