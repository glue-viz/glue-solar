# Show the position under the mouse in the viewer status bar

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:status-bar-cursor-readout` at `790072e656` (pushed 2026-11-12; #74 as it was, with the value readout, is kept as `status-bar-cursor-value`)
- Open PR: #74 (draft)
- Label: enhancement

## Body

~~~~~markdown
Matplotlib viewers do not show the position under the mouse anywhere. glue's toolbar once forwarded matplotlib's cursor position to the viewer's status bar (glue-viz/glue@97bc1333, 2012). Since the toolbar refactor of 2016 (glue-viz/glue@49a41578), which kept a hidden `NavigationToolbar2QT` for home, pan and zoom only, the position goes to that hidden toolbar's own label.

`MatplotlibDataViewer` now shows `axes.format_coord` for the mouse position in the status bar. On the Image viewer's WCSAxes this is the world position (the `w` key switches it to pixels); on the other viewers it is matplotlib's `(x, y)` text.

- The position is in a permanent label at the right of the status bar, so the status tip of the active tool stays where it is.
- It is cleared when the mouse leaves the axes or the figure.
- A long position does not widen the viewer: the label's minimum width is 1.
- `ValueError` and `OverflowError` from `format_coord` are ignored, as in matplotlib's own toolbar.

This PR is now the position only, in one commit. The value under the mouse in the Image viewer, which was part of it, is left for a later PR.

`test_cursor_position_in_status_bar` in `glue_qt/viewers/matplotlib/tests/test_data_viewer.py` runs for the image, scatter, histogram, profile and dendrogram viewers and fails for each without the change.
~~~~~

## Notes for the owner (not to paste)

- One commit on main, 2 files, +46: only `glue_qt/viewers/matplotlib/data_viewer.py` and its shared test. Out: the image value readout with its test, and the attribute-renaming lines.
- From `qt-large/scripts/status_fix.diff`, with these differences:
  - no public `cursor_status()` method: with the value readout gone nothing overrides it. The value PR can add the hook it needs.
  - `figure_leave_event` is connected as well as `motion_notify_event`. With motion alone the last position stays when the mouse leaves the figure straight from the axes; the test pins this (without the line: `assert '2 1.0 (world)' == ''`).
  - the `(ValueError, OverflowError)` guard, copied from matplotlib's `NavigationToolbar2._mouse_event_to_message`. `format_coord` does raise `OverflowError` on a date axis for a position far out of range (probed). I did not try what the viewer does with that error without the guard.
- That is 46 lines against the tracker's 30: 18 of source, 28 of test.
- Checked with the reviewer's `probe_status_fix.py`: the tool's tip stays, the label clears outside the axes, and the status bar's minimum width stays 3 with `setMinimumWidth(1)` (147 without it).
- Not seen on a screen: only Qt's offscreen platform here. How the label looks beside a long status tip in a narrow viewer is worth one look before marking it ready.
- Tests on the branch: the `*Common` classes of the five viewers' `test_data_viewer.py`, 162 passed, 3 skipped, 1 xfailed. With the test on main: 5 failed, `AttributeError: 'ImageViewer' object has no attribute '_cursor_label'` and the same for the other four.
- ruff: passes.
