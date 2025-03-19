# timeclock

A script to keep track of cumulative time worked on various tasks.

## Usage

* You don't need the project files or any venv. Right click the file `src/timeclock/timeclock.py` and save it somewhere convenient. When you double click it (presuming you have Python installed and associated with `*.py` files, the script will create a folder, `timeclock_data` and clock you in. When you double click it again, it will clock you out. If you were clocked in or clocked out for less than five minutes, the entry will be ignored.

Each time you clock in or clock out, you will see a report.

```
## timeclock_data
state: clocked IN as of 240919 14:49.
initial clock in: 240919 14:49
cumulative time: 0:00:00
virtual clock out: 240919 14:49

Press enter to continue.
```

"Virtual clock out" is the time you *would have* clocked out if you'd clocked in at "initial clock in" and never taken any breaks or done any other tasks.

You can close the window, or you can press enter. If you press enter, you will see a short report for each day a time entry has beed recorded.

```
## timeclock_data
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
```

With one line per day.

## Multiple clocks

You can copy and rename `timeclock.py` to create multiple `name_data` folders and track multiple times. When you clock into one task, the others automatically clock out. Dedicate one folder for all timeclocks you want to run.

```
my_timeclocks
    work.py
    cooking.py
    garden.py
    coding.py
```

Click one of the `*.py` files each time you change tasks. You will see a display of what you've clocked out of and what you've just clocked into. If you're not sure what you're clocked into, you can click any of your `*.py` files to see the current state then restore it by clicking the file of your choice. Any such clicking around won't even be counted unless you stay clocked in or clocked out somewhere for more than 5 minutes.
