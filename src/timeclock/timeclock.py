"""A stopwatch that works without staying open.

Run the script to toggle between clocking in and out. The script will build a file

in
out
in
out
...

Then print a clock in time, cumulative time, and virtual clock out time. The "virtual
clock out time" is the time you *would* have clocked out if you'd clocked in at the
initial clock in time then worked the cumulative time without interruption. This
keeps entries in the Microsoft timeclock app simple and helps with clients that want
time rounded to large intervals.

Time entries are simple to be tolerant of manual editing.

Time intervals less than 5 minutes are ignored. This means you can toggle the
clock-in and clock-out states to see the report without creating new entries.

If you do end up working past midnight then clocking out, the script will clock you
out at midnight the last day you were clocked in then clock you in at midnight on the
current day. If you stay clocked in through two midnights, you're on your own.

:author: Shay Hill
"""

from __future__ import annotations

import datetime
import itertools as it
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterable

_DATA_DIR = Path(__file__).parent / "timeclock_data"
_DATA_DIR.mkdir(exist_ok=True)

_TIME_FORMAT = "%y%m%d %H:%M"

# Ignore brief periods between clock in and out. These may have been solely to see
# the report.
_MIN_DELTA = datetime.timedelta(minutes=5)

# Print a report (the same report that is displayed when you run the script) at the
# bottom of the file after each update. Use this string to let _read_today_file know
# where the time entries end. Do not change this string ever, because you will break
# any previously generated reports.
_REPORT_DELIMITER = "----------"


_T = TypeVar("_T")


def _get_time_brackets(seq: Iterable[_T]) -> Iterable[tuple[_T, _T]]:
    """Return pairs of clock in and clock out times."""
    a, b = it.tee(seq)
    return zip(it.islice(a, 0, None, 2), it.islice(b, 1, None, 2))


# ===================================================================================
#   Format datetime objects as strings
# ===================================================================================


def _dt_to_str(dt: datetime.datetime) -> str:
    """Convert a datetime instance to a string.

    :param dt: A string in the format "yymmdd hh:mm"
    """
    return dt.strftime(_TIME_FORMAT)


def _str_to_dt(yymmddhhmm: str) -> datetime.datetime:
    """Convert a string to a datetime instance.

    :param yymmddhhmm: A string in the format "yymmdd hh:mmk
    """
    return datetime.datetime.strptime(yymmddhhmm, _TIME_FORMAT)


def _now_str() -> str:
    """Return the current time as a string."""
    return _dt_to_str(datetime.datetime.now())


def _today_str() -> str:
    """Return the current date as a string."""
    return _now_str()[:6]


def _prev_midnight_str() -> str:
    """Return the time of the previous midnight as a string."""
    return _today_str() + " 00:00"


def _next_midnight_str(yymmdd: str) -> str:
    """Return the time of the next midnight as a string."""
    return yymmdd + " 23:59"


# ===================================================================================
#   interpret time entries
# ===================================================================================


def _is_clocked_in(entries: list[str]) -> bool:
    """Return True if the last entry is a clock in."""
    return len(entries) % 2 == 1


def _get_cumulative_time(entries: list[str]) -> datetime.timedelta:
    """Return the cumulative time from time entries."""
    entries = [*entries, _now_str()]  # to cover time deltas to right now
    deltas = [out - in_ for in_, out in _get_time_brackets(map(_str_to_dt, entries))]
    return sum(deltas, datetime.timedelta())


def _generate_report(entries: list[str]) -> str:
    """Get enough information to inform user of state and enter vals in timeclock."""
    report: list[str] = []
    if _is_clocked_in(entries):
        report.append(f"state:\nclocked IN as of {entries[-1]}.")
    else:
        report.append(f"state:\nclocked OUT as of {entries[-1]}.")

    report.append(f"initial clock in:\n{entries[0]}")
    cumulative_time = _get_cumulative_time(entries)
    report.append(f"cumulative time:\n{cumulative_time}")

    virtual_clock_out = _str_to_dt(entries[0]) + cumulative_time
    report.append(f"Virtual clock out:\n{_dt_to_str(virtual_clock_out)}")
    return "\n\n".join(report)


# ===================================================================================
#   read and write time entries
# ===================================================================================


def _get_date_filename(yymmdd: str | None = None) -> Path:
    """Return a filename based on today's date.

    :param date: optionally give a date to use instead of today's date. "yymmdd"
    """
    if yymmdd is None:
        yymmdd = _today_str()
    return _DATA_DIR / f"{yymmdd}.txt"


def _is_not_report_delimiter(line: str) -> bool:
    """Return True if the line is the delimiter."""
    return line != _REPORT_DELIMITER


def _read_date_file(yymmdd: str | None = None) -> list[str]:
    """Return the time entries in file.

    :param date: optionally give a date to use instead of today's date. "yymmdd"
    """
    filename = _get_date_filename(yymmdd)
    if not filename.exists():
        return []
    with filename.open() as file:
        lines = filter(None, map(str.strip, file.readlines()))
    return list(it.takewhile(_is_not_report_delimiter, lines))


def _overwrite_date_file(entries: list[str], date: str | None = None) -> None:
    """Overwrite a date file with given entries. Delete file if no entries.

    :param entries: the time entries to write.
    :param date: optionally give a date to use instead of today's date. "yymmdd"
    """
    filename = _get_date_filename(date)
    if not entries:
        if filename.exists():
            filename.unlink()
        return
    report = _generate_report(entries)
    with filename.open("w") as file:
        _ = file.write("\n".join([*entries, _REPORT_DELIMITER, report]))


# ===================================================================================
#   find clock in and clock out times
# ===================================================================================


def _find_latest_entries() -> tuple[str | None, list[str]]:
    """Return the stem of the file with the latest entries. None if no entries.

    Will ignore empty files in case you manually edited a file to remove all entries
    and did not delete it.
    """
    for data_file in reversed(list(_DATA_DIR.iterdir())):
        entries = _read_date_file(data_file.stem)
        if not entries:
            continue
        return data_file.stem, entries
    return None, []


def _find_latest_clock_in() -> tuple[str | None, list[str]]:
    """Return the stem of the file with the latest clock in. None if not clocked in."""
    yymmdd, entries = _find_latest_entries()
    if _is_clocked_in(entries):
        return yymmdd, entries
    return None, []
