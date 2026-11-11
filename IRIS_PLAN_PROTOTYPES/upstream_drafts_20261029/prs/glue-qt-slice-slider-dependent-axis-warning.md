# Slice sliders: warn only if the world axis shown depends on another axis

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:slice-slider-dependent-axis-warning` at `38dd104520` (pushed 2026-11-12)
- Needs: `slice-sliders-world-axis` (stacked on it)
- Label: bug

## Body

~~~~~markdown
A slice slider shows a warning, and starts in pixel coordinates, when the world value it shows is only right at the center of the other axes. It does so whenever any world axis that depends on the slider's pixel axis also depends on another pixel axis (`dependent_axes`), even if the world axis that the slider shows depends on its own pixel axis alone.

Example: an image sequence whose pointing drifts with time. Right ascension depends on the time pixel axis, so the time slider is flagged and shows slice numbers, although the time it would show is exact.

The slider now looks at the row of `axis_correlation_matrix` for the world axis it shows, and warns unless that axis depends on the slider's pixel axis and on no other. This applies to every slice slider. Sliders of coupled axes, such as right ascension and declination, keep the warning.

This is stacked on #WORLD-AXIS-PR (read the world axis glue's world components use), which changes the lines just above; only the last commit is new.

`test_world_warning_only_for_dependent_world_axis` in `glue_qt/viewers/common/tests/test_multi_slice_helper.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Replace `#WORLD-AXIS-PR` with the number of the `slice-sliders-world-axis` PR.
- New branch, not yet in the tracker. It is the second commit of the fork's `slice-widget-time-axis` (8852fcd1), rewritten to stand on `slice-sliders-world-axis` without the time-axis commit: the pixel axis is `self.data.ndim - 1 - i` (the second line of `pr75_followup.diff`), the now unused `dependent_axes` import is dropped, and the test is new (the old one was four lines inside the time-axis test). Its own commit: 2 files, +29 -2.
- Subject is 72 characters, at the limit. The longer title in your prompt is 103.
- The profile viewer's options widget (`glue_qt/viewers/profile/options_widget.py`) has the same broad `dependent_axes` test for its own warning. Not changed here.
- Tests on the branch: `test_multi_slice_helper.py`, 3 passed. With the test file on `slice-sliders-world-axis`: `assert False` for `helper._sliders[0].state.use_world` (`use_world: False`, `slider_label: 0`), 1 failed, 2 passed.
- ruff: passes.
