# Profile tools: use the display unit for Navigate and Collapse

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:profile-tools-display-unit` at `e13674d9cd` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
With an x display unit other than the unit of the data, the Navigate and Collapse tools of the profile viewer pick the wrong slices. The profile is plotted in the display unit, but `ProfileTools._get_axis_and_pixel_slice` compares the position picked on it with the world values in the data's own unit.

Example, from the new test: data with a frequency axis of 1, 2 and 3 GHz, shown in MHz. A click at 3000 MHz gave slice 0, not slice 2, as 3000 is nearest to the first value in Hz.

The world values are now converted to the display unit before the comparison, with `UnitConverter.to_unit`, as glue-core does for the profile itself. Without a display unit, and in pixel coordinates, nothing changes.

`test_profile_tools_unit_override` in `glue_qt/viewers/profile/tests/test_data_viewer.py` fails without the change (`assert (0, 0) == (0, 2)`). It needs nothing newer than released glue-core.
~~~~~

## Notes for the owner (not to paste)

- New branch, from the fork's `profile-wcs-pr`: the source hunk is `qt-large/scripts/unit_fix.diff` as it is; the test is `test_profile_tools_unit_override` without its WCSAxes block, and without `settings.UNIT_CONVERTER = 'test-spectral2'`, which it does not need (GHz to MHz works with the default converter).
- Needs neither glue PR: run against installed glue-core 1.28.0.
- The test calls the private `_get_axis_and_pixel_slice`, as the original does.
- Tests on the branch: `test_data_viewer.py` and `test_profile_tools.py` of the profile viewer, 51 passed, 1 skipped. Without the source change: `assert (0, 0) == (0, 2)`, 1 failed, 46 passed, 1 skipped.
- ruff: passes.
