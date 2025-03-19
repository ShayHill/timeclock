# timeclock

A script to keep track of cumulative time worked daily.

## Usage

* You don't need the project files or any venv. Put the file `src/timeclock/timeclock.py` somewhere convenient. When you double click it (presuming you have Python installed and associated with `*.py` files, the script will create a folder, `timeclock_data` and clock you in. When you double click it again, it will clock you out. If you were clocked in or clocked out for less than five minutes, the entry will be ignored.

Each time you clock in or clock out, you will see a report.

```
state:
clocked IN as of 240919 14:49.

initial clock in:
240919 14:49

cumulative time:
0:00:00

Virtual clock out:
240919 14:49

Press enter to continue.
```

"Virtual clock out" is the time you *would* have clocked out if you'd clocked in at "initial clock in" and never taken any breaks.

You can close the window, or you can press enter. If you press enter, you will see a short report for each day a time entry has beed recorded.

```
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
initial clock in | virtual clock out | cumulative time
```

## Multiple clocks

You can copy and rename `timeclock.py` to create multiple `name_data` folders and track multiple times. When you clock into one task, the others automatically clock out (if the `_data` dirs are all in the same place). If you have these scripts in a folder with other Python scripts and directories named `something_data`, there is a chance for problems, so it's best to keep all the `timeclock.py` scripts together in a folder with no other files.
