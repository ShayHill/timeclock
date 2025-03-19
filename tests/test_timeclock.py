"""Test functions in mod.py.

:author: Shay Hill
:created: 2025-03-19
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations
from timeclock import timeclock as mod


import datetime

import tempfile
from unittest.mock import patch
from pathlib import Path


class TestStrConversion:
    def test_dt_to_str(self):
        dt = datetime.datetime(2025, 3, 19, 13, 45)
        assert mod._dt_to_str(dt) == "250319 13:45"

    def test_str_to_dt(self):
        assert mod._str_to_dt("250319 13:45") == datetime.datetime(2025, 3, 19, 13, 45)

    def test_now_str(self):
        """This one could potentially fail due to a race condition.
        If it does, just run it again.
        """
        assert mod._now_str() == datetime.datetime.now().strftime(mod._TIME_FORMAT)

    def test_prev_midnight_str(self):
        assert mod._prev_midnight_str() == mod._dt_to_str(
            datetime.datetime.combine(datetime.date.today(), datetime.time())
        )

    def test_next_midnight_str(self):
        assert mod._next_midnight_str("250319") == "250319 23:59"


class TestInterpretTimeEntries:
    def test_is_clocked_in(self):
        """Return True if the number of entries is odd."""
        assert mod._is_clocked_in(["250319 13:45"]) is True
        assert mod._is_clocked_in(["250319 13:45", "250319 14:45"]) is False
        assert (
            mod._is_clocked_in(["250319 13:45", "250319 14:45", "250319 15:45"]) is True
        )
        assert mod._is_clocked_in([]) is False

    def test_get_cumulative_time(self):
        """Only testing clocked out cumulative time. Clocked in time would require
        somehow moccing the current time.
        """
        entries = [
            "250319 13:45",
            "250319 14:45",
            "250319 15:45",
            "250319 16:45",
        ]
        assert mod._get_cumulative_time(entries) == datetime.timedelta(hours=2)


class TestReadAndWriteTimeEntries:
    def test_get_date_filename(self):
        assert mod._get_date_filename("250319") == mod._DATA_DIR / "250319.txt"
        today = mod._now_str()[:6]
        assert mod._get_date_filename() == mod._DATA_DIR / f"{today}.txt"

    def test_read_date_file(self):
        test_file = Path(tempfile.gettempdir()) / "250319.txt"
        test_lines = [
            "250319 13:45",
            "   ",
            "250319 14:45",
            mod._REPORT_DELIMITER,
            "blah blah blah",
        ]
        _ = test_file.write_text("\n".join(test_lines))

        def mock_get_date_filename(yymmdd: str | None = None) -> Path:
            return test_file

        with patch("timeclock.timeclock._get_date_filename", mock_get_date_filename):
            result = mod._read_date_file()

        assert result == ["250319 13:45", "250319 14:45"]

