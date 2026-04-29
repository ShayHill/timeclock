"""Toggle a stopwatch for one task category.

:author: Shay Hill
:created: 2025-12-23
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.timeclock.main import toggle_clock  # noqa: E402

if __name__ == "__main__":
    toggle_clock(Path(__file__))
