"""A stopwatch that works without staying open.

Import and run ``toggle_clock(Path(__file__))`` from a caller script. Each run toggles
that caller between clocked-in and clocked-out.

**Data model**

Work intervals are stored as a reverse-linked list of ``Interval`` nodes (``prev`` chain
from the current tail). ``Punchclock`` holds the tail and keeps the intervals synced
with a CSV file.

**CSV file**

Each data file is ``timeclocks/data/<stem>_data.csv`` (stem from the caller name). Rows
are written as four columns (date, time-in, time-out, description). No header row.

**Clocking rules**

Clocking in to one caller runs ``_clock_out_all`` first so at most one caller stays
clocked in. Clock-out prompts for a description; a blank input (or just closing the
window) keeps the previous interval description (handled in ``Interval.clock_out``).

If clock-out falls on a later calendar day than clock-in, ``Interval`` inserts
end-of-day and start-of-day boundary intervals so the chain stays consistent. You will
be clocked in for 24 hours each during any intervening days.

When the gap between adjacent intervals is under ``MIN_TIME_DELTA_TO_RECORD`` (time off)
and descriptions match, the intervals are merged. When a new interval is created, the
previous interval is dropped if it is too short.

**Windows side effects**

Clocked-in callers rename to ``CLOCKED_IN_<stem>.py`` and set the desktop background
from ``timeclocks/wallpapers`` when a matching image exists (otherwise a solid color).
When clocked out, the plain ``<stem>.py`` name is restored and a different solid color
is used.

**``toggle_clock``**

On success there is no stdout output. On exception the traceback is printed; the
``finally`` block prompts to press Enter only when an error occurred.

Do not run this module as ``__main__``; use a category caller in ``timeclocks/``.

:author: Shay Hill
:created: 2025-04-27
"""

from __future__ import annotations

import csv
import ctypes
import datetime as dt
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterator


# ===================================================================================
#   Configuration Values
# ===================================================================================

# This is it for configuration. Changing anything else in this modul is likely to break
# something if you don't know what you're doing.

# The default colors for the desktop background when clocked in and out. If no image is
# found in the wallpapers directory for a caller script, default to `CLOCKED_IN_COLOR`.
# When not clocked in to anything, use `CLOCKED_OUT_COLOR`. These values could can be
# either RGB tuples or Paths to wallpaper images.
CLOCKED_OUT_COLOR = (255, 95, 21)
CLOCKED_IN_COLOR = (1, 133, 116)

# Ignore brief periods between clock in and out. These may have been solely to see the
# report. This value is arbitrary. If you clock in for a short phonecall, it won't be
# charged as time on. If you walk into the next room to refill your coffee, it won't be
# charged as time off.
MIN_TIME_DELTA_TO_RECORD = dt.timedelta(minutes=5)


# ===================================================================================
#   Punchclock Type
# ===================================================================================


class Interval:
    """Represent a time interval with a clock-in and clock-out linked-list node."""

    def __init__(
        self,
        clock_in: dt.datetime | None = None,
        prev: Interval | None = None,
    ) -> None:
        """Initialize an Interval instance.

        :param clock_in: The datetime of the clock-in
        :param prev: The previous interval. If None, this is the first interval.

        If no args, create a dummy interval with dt.datetime.min for beg and end. This
        0-duration interval will be removed when the first clock-in occurs.
        """
        self.beg = dt.datetime.min if clock_in is None else clock_in
        self.prev = prev
        self.end = dt.datetime.min if clock_in is None else None
        self.description = ""

    @property
    def is_clocked_in(self) -> bool:
        """Return True if this interval is still clocked in."""
        return self.end is None

    @property
    def duration(self) -> dt.timedelta:
        """Return interval duration, or zero when still clocked in."""
        if self.end is None:
            return dt.timedelta()
        return self.end - self.beg

    def clock_in(self, clock_in: dt.datetime) -> Self:
        """Clock in and return a new interval (presumable self is already clocked out).

        :param clock_in: The datetime of the clock-in
        :return: A new interval

        Drop previous interval if it is too short. Drop previous interval if it is the
        dummy interval created by init.
        """
        if self.is_clocked_in:
            msg = "Cannot clock in if already clocked in."
            raise ValueError(msg)
        prev = None if self.beg == dt.datetime.min else self  # drom dummy interval
        return type(self)(clock_in, prev=prev)

    def clock_out(self, clock_out: dt.datetime, description: str) -> Interval:
        """Clock out and potentially merge with previous interval.

        :param clock_out: The datetime of the clock-out
        :param description: The description of the interval
        :return: The tail of the list. If this interval was not merged, it will be the
            tail. If it was merged, it will be the previous interval and this interval
            will not be referenced.

        If the clock-out period between the previous interval and this interval is less
        than MIN_TIME_DELTA_TO_RECORD *and the descriptions match*, then the previous
        interval is extended to include this interval and this interval disappears.
        """
        if not self.is_clocked_in:
            msg = "Cannot clock out if not clocked in."
            raise ValueError(msg)
        description = description.strip()
        if not description and self.prev:
            description = self.prev.description or ""

        node = self._fill_any_intervening_days(clock_out, description)
        node.end = clock_out
        node.description = description
        return node.merge_with_prev_if_break_was_short(description)

    def _fill_any_intervening_days(
        self,
        clock_out: dt.datetime,
        description: str,
    ) -> Interval:
        """Fill days when `clock_out` and `clock_in` are on different days.

        :param clock_out: clock-out datetime
        :param description: description text for boundary intervals
        """
        node: Interval = self
        ci_date = self.beg.date()
        co_date = clock_out.date()
        if ci_date != co_date:
            days = list(_date_range(ci_date, co_date))
            for day in days[:1]:
                end_of_day = dt.datetime.combine(day, dt.time.max)
                node = node.clock_out(end_of_day, description)
            for day in days[1:-1]:
                beg_of_day = dt.datetime.combine(day, dt.time.min)
                node = node.clock_in(beg_of_day)
                end_of_day = dt.datetime.combine(day, dt.time.max)
                node = node.clock_out(end_of_day, description)
            for day in days[-1:]:
                beg_of_day = dt.datetime.combine(day, dt.time.min)
                node = node.clock_in(beg_of_day)
        return node

    def merge_with_prev_if_break_was_short(self, description: str | None) -> Interval:
        """Collapse any brief break between intervals with the same description.

        :param description: Description text for this interval
        """
        if not self.prev:
            return self
        if self.prev.description != description:
            return self
        if self.prev.end is None:
            msg = "Unexpected error: Previous interval has no end time."
            raise RuntimeError(msg)
        if self.beg - self.prev.end >= MIN_TIME_DELTA_TO_RECORD:
            return self
        if self.beg.date() != self.prev.end.date():
            return self
        self.prev.end = self.end
        return self.prev


class PunchclockPaths:
    """Resolve caller and csv-data paths from one input path.

    Determine where required paths are located and read and write csv data files.

    :param caller_or_data: a Path to one of Caller (`*.py`) path or data path (`*.csv`)
    """

    def __init__(self, caller_or_data: Path) -> None:
        """Initialize with caller or data path.

        :param caller_or_data: Caller ``*.py`` path or data path
        """
        if caller_or_data.suffix == ".py":
            self.stem = caller_or_data.stem.removeprefix(_CLOCKED_IN_PREFIX)
            self.csv_data = _DATA_DIR / f"{self.stem}_data.csv"
        elif caller_or_data.suffix == ".csv":
            self.stem = caller_or_data.stem.removesuffix("_data")
            self.csv_data = caller_or_data
        else:
            msg = f"Unsupported caller/data suffix: {caller_or_data.suffix}"
            raise ValueError(msg)
        self._caller_plain = _DATA_PARENT / f"{self.stem}.py"
        self._caller_prefixed = _DATA_PARENT / f"{_CLOCKED_IN_PREFIX}{self.stem}.py"
        # Optional wallpaper path for this caller. If missing, CLOCKED_IN_COLOR is used.
        self.wallpaper = self._find_wallpaper()

    @property
    def caller(self) -> Path:
        """Return the existing caller path."""
        if self._caller_prefixed.exists():
            return self._caller_prefixed
        if self._caller_plain.exists():
            return self._caller_plain
        msg = (
            "No caller file exists for inferred paths: "
            f"{self._caller_prefixed} or {self._caller_plain}"
        )
        raise FileNotFoundError(msg)

    def _find_wallpaper(self) -> Path | None:
        """Return matching wallpaper path for this caller stem, if any.

        First match the full stem. If not found, fall back to the stem prefix before
        the first dash so callers like `acme-rate2` can reuse `acme.png` wallpaper.
        """
        allowed_suffixes = {".png", ".jpg", ".jpeg", ".bmp"}
        fallback_stem = self.stem.split("-", maxsplit=1)[0]
        preferred_stems = (self.stem, fallback_stem)

        for wanted_stem in preferred_stems:
            if not wanted_stem:
                continue
            for candidate in _WALLPAPERS.iterdir():
                if not candidate.is_file():
                    continue
                if candidate.stem.lower() != wanted_stem:
                    continue
                if candidate.suffix.lower() in allowed_suffixes:
                    return candidate
        return None

    def _pad_csv_rows(self, csv_rows: list[list[str]]) -> Iterator[list[str]]:
        """Pad CSV rows with empty strings to make them 4 columns wide."""
        for row in csv_rows:
            yield [*row, *([""] * 4)][:4]

    def read_csv(self) -> Interval:
        """Read csv rows and return the tail of the linked list."""
        tail = Interval()
        if not self.csv_data.exists():
            return tail
        with self.csv_data.open(encoding="utf-8", newline="") as file:
            csv_rows = list(csv.reader(file))

        def raise_invalid_svg(detail: str, exc: Exception | None = None) -> None:
            msg_prefix = f"Invalid CSV: {self.csv_data}, "
            raise ValueError(msg_prefix + detail) from exc

        try:
            for i, row in enumerate(self._pad_csv_rows(csv_rows)):
                date, ci, co, desc = row
                beg, end = _parse_timestamp_cells(date, ci, co)
                if beg:
                    tail = tail.clock_in(beg)
                else:
                    raise_invalid_svg(f"Missing clock_in, row {i}: {row}.")
                if end:
                    tail = tail.clock_out(end, desc)
                elif i < len(csv_rows) - 1:
                    raise_invalid_svg(f"Missing clock_out, row {i}: {row}.")
        except ValueError as e:
            raise_invalid_svg("Failed to parse CSV", e)
        return tail

    def write_csv(self, tail: Interval | None) -> None:
        """Write linked-list intervals to this instance csv path."""
        csv_rows: list[list[str]] = []
        node = tail
        while node is not None:
            date = node.beg.strftime(_DATE_ONLY_FORMAT)
            csv_rows.append(
                [date, *_punches_to_csv_cells(node.beg, node.end), node.description],
            )
            node = node.prev
        csv_rows.reverse()
        with self.csv_data.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(csv_rows)


class Punchclock:
    """Represent punch data with report and CSV-row views.

    :param caller_or_data: a Path to one of Caller (`*.py`) path or data path (`*.csv`)

    State is held as a linked list of Interval objects. The list tail is `_tail`.
    """

    tail: Interval
    paths: PunchclockPaths

    def __init__(self, caller_or_data: Path) -> None:
        """Initialize from a list of punch datetimes."""
        self.paths = PunchclockPaths(caller_or_data)
        self.tail = self.paths.read_csv()

    def clock_in(self, punch_at: dt.datetime) -> None:
        """Clock in and persist to CSV."""
        self.tail = self.tail.clock_in(punch_at)
        self.paths.write_csv(self.tail)

    def clock_out(self, description: str) -> None:
        """Clock out and persist to CSV."""

        self.tail = self.tail.clock_out(dt.datetime.now(), description)
        self.paths.write_csv(self.tail)

    @property
    def previous_interval_description(self) -> str:
        """Return description for most recent previous interval, if any."""
        prev = self.tail.prev
        if prev is None:
            return ""
        return prev.description

    @property
    def is_clocked_in(self) -> bool:
        """Return True if the latest row is clocked in."""
        return self.tail.is_clocked_in


# ===================================================================================
#   Hard-Coded Paths
# ===================================================================================

# Directory containing category scripts and the ``data/`` subdirectory
_DATA_PARENT = Path(__file__).parents[2] / "timeclocks"

# Wallpaper images keyed by caller script name
_WALLPAPERS = _DATA_PARENT / "wallpapers"

# All ``*_data.csv`` files live here
_DATA_DIR = _DATA_PARENT / "data"


# ===================================================================================
#   Hard-Coded Values
# ===================================================================================

# prepend this string to the caller script name when clocked in.
_CLOCKED_IN_PREFIX = "CLOCKED_IN_"

_TIME_ONLY_FORMAT = "%H:%M"
_DATE_ONLY_FORMAT = "%y%m%d"


# ===================================================================================
#   Platform State Display - Update the desktop background and caller script name to
#   reflect clock-in state.
# ===================================================================================


def _set_desktop_background(spec: tuple[int, int, int] | Path | str) -> None:
    """Set the Windows desktop to a solid color or a wallpaper image.

    :param spec: RGB tuple or path to an image file (e.g. bmp, jpg, png)

    Pass an (r, g, b) tuple for a solid desktop color, or a path to an image file for
    wallpaper. Does not persist after reboot.
    """
    if isinstance(spec, tuple):
        r, g, b = spec
        color = (b << 16) | (g << 8) | r
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, ctypes.c_wchar_p(""), 0)
        ctypes.windll.user32.SetSysColors(
            1,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.byref(ctypes.c_int(color)),
        )
        return
    path = Path(spec).resolve()
    if not path.is_file():
        msg = f"Desktop wallpaper image not found: {path}"
        raise FileNotFoundError(msg)
    ctypes.windll.user32.SystemParametersInfoW(
        0x0014,
        0,
        ctypes.c_wchar_p(str(path)),
        0x02,
    )


def _display_clocked_in_state(punchclock: Punchclock) -> None:
    """Show the clocked-in state in caller name and desktop background.

    :param punchclock: Punchclock instance with caller path context
    """
    caller = punchclock.paths.caller
    if caller.exists():
        new_filename = f"{_CLOCKED_IN_PREFIX}{punchclock.paths.stem}.py"
        _ = caller.rename(new_filename)

    wp_path = punchclock.paths.wallpaper or CLOCKED_IN_COLOR
    _set_desktop_background(wp_path)


def _display_clocked_out_state(punchclock: Punchclock) -> None:
    """Show the clocked-out state in caller name and desktop background.

    :param punchclock: Punchclock instance with caller path context
    """
    caller = punchclock.paths.caller
    if caller.exists():
        new_filename = f"{punchclock.paths.stem}.py"
        _ = caller.rename(new_filename)
    _set_desktop_background(CLOCKED_OUT_COLOR)


# ===================================================================================
#   Datetime and Formatting Helpers
# ===================================================================================


def _parse_timestamp_cells(row_date: str, *cells: str) -> Iterator[dt.datetime | None]:
    """Return a datetime from a row date and a ``HH:MM`` CSV cell."""
    for cell in (x.strip() for x in cells):
        if not cell:
            yield None
            continue
        dt_date = dt.datetime.strptime(row_date, _DATE_ONLY_FORMAT).date()
        dt_time = dt.datetime.strptime(cell, _TIME_ONLY_FORMAT).time()
        yield dt.datetime.combine(dt_date, dt_time)


def _punches_to_csv_cells(*punches: dt.datetime | None) -> Iterator[str]:
    """Format a datetimes for CSV storage."""
    for punch in punches:
        yield "" if punch is None else punch.strftime(_TIME_ONLY_FORMAT)


def _date_range(beg: dt.date, end: dt.date) -> Iterator[dt.date]:
    """Yield dt.datetime objects for every day from start to end (inclusive)."""
    if beg > end:
        return
    current = beg
    while current <= end:
        yield current
        current += dt.timedelta(days=1)


# ===================================================================================
#   Clock State and Punch Logic
# ===================================================================================


def _clock_in(punchclock: Punchclock) -> None:
    """Clock in then apply clocked-in side effects.

    :param punchclock: Punchclock instance for one caller
    """
    _clock_out_all()
    punchclock.clock_in(dt.datetime.now())
    _display_clocked_in_state(punchclock)


def _clock_out(punchclock: Punchclock) -> None:
    """Clock out then apply clocked-out side effects.

    :param punchclock: Punchclock instance for one caller
    """
    beg_tail = punchclock.tail
    prev_desc = punchclock.previous_interval_description
    punchclock.clock_out("")
    _display_clocked_out_state(punchclock)
    prompt = f"Description for {punchclock.paths.stem}"
    prompt += f" interval (blank=continue '{prev_desc}'): "
    description = input(prompt)
    if description:
        node = punchclock.tail
        while node is not None:
            node.description = description
            if node == beg_tail:
                break
            node = node.prev


def _clock_out_all() -> None:
    """Clock out of all time clocks."""
    if not (_DATA_PARENT / "data").exists():
        return
    for csv_file in (_DATA_PARENT / "data").glob("*.csv"):
        punchclock = Punchclock(csv_file)
        if punchclock.is_clocked_in:
            _clock_out(punchclock)


def toggle_clock(caller: Path) -> None:
    """Clock in if clocked out and vice versa. Update filename to reflect state."""
    ran_without_error = True
    try:
        punchclock = Punchclock(caller)
        if punchclock.is_clocked_in:
            _clock_out(punchclock)
        else:
            _clock_in(punchclock)
    except Exception:  # noqa: BLE001
        ran_without_error = False
        traceback.print_exc()
    finally:
        if not ran_without_error:
            _ = input("\nPress Enter to close the window...")


if __name__ == "__main__":
    msg = "Do not run this core function. Run one of the category.py"
    msg += " apps in the parent folder (e.g., client_name.py)"
    raise NotImplementedError(msg)
