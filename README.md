# Timeclock

Small Windows-oriented helpers in `timeclocks/` that log clock-in and clock-out times to CSV, and show state by renaming the caller script and changing the desktop background.
f
## Quick start

1. **Create a new caller**  
   In the `timeclocks` directory, make a copy of `example_client.py`. In the script and documentation, such `.py` files are referred to as "callers".

2. **Rename the copy**  
   Use a name that matches the client, project, or activity (for example `acme_corp.py`). The file name (without `.py`) is used to find your data file and optional wallpaper, so keep it stable once you have history. See more information under the `Optional wallpaper per caller` heading, but one reliable naming conventions for callers is `snake_case_client-subcategory`.

3. **Run the script**  
   Double-click the `.py` file, or run it with Python (for example from a terminal: `python timeclocks\acme_corp.py`).  
   Each run **toggles** between clocked-in and clocked-out for *that* caller. On success there is no output, but you may notice a brief flash of a terminal.

4. **Do not run the core module directly**
   `src/timeclock/main.py` is meant to be imported from caller scripts. Running it on its own is blocked with an error, by design.

## One active caller at a time

When you clock **in** to a caller, the program first clocks **out** any other caller that was still clocked in. So only one timeclock category should be “in” at a time, matching the idea of one focused task on the machine.

## Where your data is stored

For a caller script named `timeclocks/<name>.py`, punch data is stored in:

`timeclocks/data/<name>_data.csv`

The `data` folder is the single place the app uses for all category CSVs. You can back up that folder, sync it, or add it to version control if you want a history of your own.

## Editing CSV files by hand

You can open and edit a `*_data.csv` file to fix forgotten punches or add entries.

Each row has this shape:

`date,clock_in,clock_out,description`

Column meaning:

- `date`: day in `YYMMDD` format
- `clock_in`: start of one time bracket (`HH:MM`)
- `clock_out`: end of that time bracket (`HH:MM`, can be blank for the active in-progress bracket)
- `description`: text description for that interval

Each bracket is one CSV line. Multiple brackets on the same day will appear as multiple
rows with the same `date`.

When you clock out, the app prompts for a description. If you submit blank input, the previous interval description is kept.

The file is validated the next time you run a caller. The rules enforced by the script (see the module docstring in `src/timeclock/main.py`) are:

- **Each row must have a valid date and clock-in time**
- **Only the last row may have a blank `clock_out`** (active in-progress interval)

If these are violated, the run will fail with a validation error and your CSV is not written over until the problem is fixed.

## Other behavior to know

- Gaps of **less than five minutes** between adjacent intervals are merged away when descriptions match (same-day only), so brief same-task interruptions do not create extra fragments.

If you work past **midnight** and then clock out, the logic clocks you out at 23:59 then back in at 00:00 the next day.

## Side effects when you clock in or out (Windows)

These are in addition to updating the CSV and printing the report.

1. **Caller script rename**  
   While clocked **in**, the script file is renamed to start with `CLOCKED_IN_` (for example `CLOCKED_IN_acme_corp.py`). When you clock **out**, the prefix is removed so the name returns to `acme_corp.py`. The code resolves either name, so you can run the file no matter which name it currently has, as long as it exists in `timeclocks/`.

2. **Desktop background**  
   - **Clocked in:** if a custom wallpaper image exists (see below), it is set as the desktop background; otherwise your background is set to solit teal.
   - **Clocked out:** if you are not clocked in to any activity, your desktop background is set to safety orange, a color that looks bad enough with most icons that it should motivate you to get back to work.

## Optional wallpaper per caller

To use a custom image (instead of solid teal) when you are clocked in to a given caller:

1. Put a wallpaper image in `timeclocks/wallpapers/`.
2. Use one of these extensions: `.png`, `.jpg`, `.jpeg`, `.bmp`.
3. Wallpaper lookup tries these stems in order.
   - full caller stem
   - fallback stem up to the first dash (`-`)
4. Examples:
   - `acme_corp.py` -> tries `acme_corp.*`
   - `acme_corp-marketing.py` -> tries `acme_corp-marketing.*`, then `acme_corp.*`
   - `acme_corp-rate2.py` -> tries `acme_corp-rate2.*`, then `acme_corp.*`
5. Example wallpaper files:
   - `acme_corp.png`
   - `acme_corp.jpg`
   - `acme_corp.jpeg`
   - `acme_corp.bmp`
6. `webp` is not allowed because the underlying Windows wallpaper API used by this project does not support it reliably.

This dash-based fallback is useful for ad-hoc subcategories (for example, `acme_corp-non_billable`) where you still want some visual cue on your wallpaper, but you want that time on another clock. It is not the preferred daily pattern because reusing a base wallpaper gives less precise indication of exactly what you are clocked in to.

## Desktop shortcut

For quick access, create a **shortcut** to the `timeclocks` folder on the desktop or taskbar.
