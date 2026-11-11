# Use the system fixed-width font for the profile fit log

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:fit-log-fixed-font` at `ab01a4b8fc` (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
The profile viewer's fit log asks for `QFont("Courier")`. Where Courier is not installed, as on recent macOS, Qt fills its table of font aliases to resolve the name, and warns about the cost: creating the first profile viewer took 54.6 ms there, against 2.6 ms with the system font (median of 5 fresh processes). The log now uses the platform's own fixed-width font, `QFontDatabase.systemFont(QFontDatabase.FixedFont)`.

The font was also set only as the default font of the log's document, which `QTextEdit` resets to the widget font whenever that changes. On macOS the style sheet of the tab widget does this once the viewer is in the application, so the log was not in a fixed-width font there. The font is now set on the widget, and kept.

This changes the log's font on every platform: it becomes the system fixed font at its own size, where it was whatever Courier resolved to at Qt's default size. On one Linux machine, for example, Nimbus Mono PS at 12 pt becomes Noto Sans Mono at 9 pt. The time is gained on macOS only.

`test_fit_log_font` in `glue_qt/viewers/profile/tests/test_profile_tools.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- New branch: the other half of `perf-q6-startup-qt`, from `qt-small/patches/q6b-fit-log-font.diff` as it is.
- The macOS numbers are the original commit's, not re-measured (no Mac here). The Linux example is from this machine under Qt's offscreen platform, where the fixed font comes from fontconfig; a desktop theme may give another.
- Tests on the branch: `test_profile_tools.py`, 5 passed. Without the source change: `AssertionError: assert 'Courier' == 'monospace'`, 1 failed, 4 passed.
- ruff: passes. Merges cleanly with the four Fit tab branches, which touch the same two files.
