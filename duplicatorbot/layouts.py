"""Grid layouts used when duplicating an image.

A layout describes the (rows, columns) grid used for a given duplicate count.
Every cell holds one copy of the source image, so the number of copies always
matches the requested count while the tiles themselves stay perfectly square
(undistorted).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

#: Duplicate counts the bot understands, in the order shown in the keyboard.
SUPPORTED_COUNTS: Tuple[int, ...] = (2, 4, 6, 8)

#: (rows, columns) for each supported duplicate count.
_GRIDS: Dict[int, Tuple[int, int]] = {
    2: (1, 2),
    4: (2, 2),
    6: (2, 3),
    8: (4, 2),
}


@dataclass(frozen=True)
class Layout:
    """A rows x columns arrangement able to hold exactly ``count`` tiles."""

    count: int
    rows: int
    cols: int

    @property
    def slots(self) -> int:
        """Number of available cells (may exceed ``count`` for some grids)."""

        return self.rows * self.cols

    def position(self, index: int) -> Tuple[int, int]:
        """Return the ``(row, column)`` of the tile at ``index`` (0-based)."""

        return divmod(index, self.cols)


def get_layout(count: int) -> Layout:
    """Return the layout for ``count`` duplicates.

    Unknown counts fall back to the nearest supported value and
    ``ValueError`` is never raised so a stale keyboard can not crash the bot.
    """

    if count in _GRIDS:
        rows, cols = _GRIDS[count]
        return Layout(count=count, rows=rows, cols=cols)

    nearest = min(SUPPORTED_COUNTS, key=lambda value: (abs(value - count), value))
    rows, cols = _GRIDS[nearest]
    return Layout(count=nearest, rows=rows, cols=cols)
