"""Test functions in mod.py.

:author: Shay Hill
:created: 2025-03-19
"""

# pyright: reportPrivateUsage=false

from __future__ import annotations
from timeclock import timeclock as mod

import shutil

import datetime

import tempfile
from unittest.mock import patch
from pathlib import Path


TEMP_DIR = Path(tempfile.gettempdir())


class TestStrConversion:
    def test_dt_to_str(self):
        dt = datetime.datetime(2024, 9, 19, 13, 45)
        assert mod._dt_to_str(dt) == "240919 13:45"

    def test_str_to_dt(self):
        assert mod._str_to_dt("240919 13:45") == datetime.datetime(2024, 9, 19, 13, 45)

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
        assert mod._next_midnight_str("240919") == "240919 23:59"


class TestInterpretTimeEntries:
    def test_is_clocked_in(self):
        """Return True if the number of entries is odd."""
        assert mod._is_clocked_in(["240919 13:45"]) is True
        assert mod._is_clocked_in(["240919 13:45", "240919 14:45"]) is False
        assert (
            mod._is_clocked_in(["240919 13:45", "240919 14:45", "240919 15:45"]) is True
        )
        assert mod._is_clocked_in([]) is False

    def test_get_cumulative_time(self):
        """Only testing clocked out cumulative time. Clocked in time would require
        mocking the current time.
        """
        entries = [
            "240919 13:45",
            "240919 14:45",
            "240919 15:45",
            "240919 16:45",
        ]
        assert mod._get_cumulative_time(entries) == datetime.timedelta(hours=2)


class TestReadAndWriteTimeEntries:

    def test_read_date_file(self):
        test_lines = [
            "240919 13:45",
            "   ",
            "240919 14:45",
            mod._REPORT_DELIMITER,
            "blah blah blah",
        ]

        data_dir = TEMP_DIR / "timeclock_data"
        data_dir.mkdir(exist_ok=True)
        test_file = data_dir / "240919.txt"
        _ = test_file.write_text("\n".join(test_lines))
        result = mod._read_data_file(test_file)
        try:
            assert result == ["240919 13:45", "240919 14:45"]
        except AssertionError as exc:
            raise exc
        finally:
            test_file.unlink()
            shutil.rmtree(data_dir)


class TestFindLatestEntries:
    def test_latest_has_entries(self):
        """If there are entries, return them."""
        data_dir = TEMP_DIR / "timeclock_data"
        data_dir.mkdir(exist_ok=True)

        entries = ["240919 13:45", "240919 14:45"]
        test_file = data_dir / "240919.txt"
        _ = test_file.write_text("\n".join(entries))
        result = mod._find_latest_entries(data_dir)
        try:
            assert result == (test_file.stem, entries)
        except AssertionError as exc:
            raise exc
        finally:
            test_file.unlink()
            shutil.rmtree(data_dir)

    def test_empty_file_more_recent(self):
        """If the file is empty, return the entries from the previous day."""
        data_dir = TEMP_DIR / "timeclock_data"
        data_dir.mkdir(exist_ok=True)

        entries = ["240918 13:45", "240918 14:45"]
        prev_day = "240918"
        this_day = "240919"
        with patch("timeclock.timeclock._DATA_DIR", TEMP_DIR):
            test_file_prev = data_dir / f"{prev_day}.txt"
            _ = test_file_prev.write_text("\n".join(entries))
            test_file_next = data_dir / f"{this_day}.txt"
            _ = test_file_next.write_text("")
            result = mod._find_latest_entries(data_dir)
        try:
            assert result == (prev_day, entries)
        except AssertionError as exc:
            raise exc
        finally:
            test_file_prev.unlink()
            test_file_next.unlink()
            shutil.rmtree(data_dir)
