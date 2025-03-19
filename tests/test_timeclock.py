"""Test functions in timeclock.py.

:author: Shay Hill
:created: 2025-03-19
"""

# pyright: reportPrivateUsage=false

from timeclock import timeclock
import datetime


class TestStrConversion:
    def test_dt_to_str(self):
        dt = datetime.datetime(2025, 3, 19, 13, 45)
        assert timeclock._dt_to_str(dt) == "250319 13:45"

    def test_str_to_dt(self):
        assert timeclock._str_to_dt("250319 13:45") == datetime.datetime(
            2025, 3, 19, 13, 45
        )

    def test_now_str(self):
        """This one could potentially fail due to a race condition.
        If it does, just run it again.
        """
        assert timeclock._now_str() == datetime.datetime.now().strftime(
            timeclock._TIME_FORMAT
        )

    def test_prev_midnight_str(self):
        assert timeclock._prev_midnight_str() == timeclock._dt_to_str(
            datetime.datetime.combine(datetime.date.today(), datetime.time())
        )

    def test_next_midnight_str(self):
        assert timeclock._next_midnight_str("250319") == "250319 23:59"


class TestInterpretTimeEntries:
    def test_is_clocked_in(self):
        """Return True if the number of entries is odd."""
        assert timeclock._is_clocked_in(["250319 13:45"]) is True
        assert timeclock._is_clocked_in(["250319 13:45", "250319 14:45"]) is False
        assert timeclock._is_clocked_in(["250319 13:45", "250319 14:45", "250319 15:45"]) is True
        assert timeclock._is_clocked_in([]) is False

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
        assert timeclock._get_cumulative_time(entries) == datetime.timedelta(hours=2)
