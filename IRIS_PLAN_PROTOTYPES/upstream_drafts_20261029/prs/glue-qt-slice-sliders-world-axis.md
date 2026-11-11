# Slice sliders: read the world axis glue's world components use

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:slice-sliders-world-axis` at `6b271e515a` (pushed 2026-11-12)
- Label: bug

## Body

~~~~~markdown
For data with more world axes than array axes (glue-viz/glue#2574), a slice slider is labeled with one world axis and shows the values and unit of another.

The slider of array axis `i` reads world axis `ndim - 1 - i`, and passes that index as its pixel axis too. Since glue-viz/glue#2573 (glue-core 1.27.0), glue's world component of axis `i` reads world axis `world_n_dim - 1 - i`. The slider now reads that world axis, along pixel axis `ndim - 1 - i`.

Example, from the new test: a 4-D WCS (longitude, latitude, wavelength, Stokes) sliced at one latitude pixel has 3 pixel axes and keeps 4 world axes. Its Stokes slider showed `6.3002e-07 m` four times. It now shows Stokes 1 to 4.

Data with as many world axes as array axes are unchanged.

`test_sliders_show_world_axis_of_data_with_more_world_axes` in `glue_qt/viewers/common/tests/test_multi_slice_helper.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Existing fork branch, to force-push: it now holds only the world-axis commit, on main. The hide commit is `hide-replaced-slice-sliders`.
- From `qt-small/patches/slider-world-axis-alone-on-main.diff`, with two changes to the test so that it merges with `hide-replaced-slice-sliders` without conflict (the patch as it is conflicts with that commit in the test file's imports and at the top of the class): the data are `arange(120).reshape((4, 5, 6))` in place of `zeros((4, 5, 6))`, and `assert_allclose` is imported in the block with the astropy imports, so the `numpy` and `qtpy` import lines are left for the other branch. The source hunk and the assertions are the patch's.
- `glue-viz/glue#2573` and `glue-viz/glue#2574` are written in full in the message, the PR body and the two code comments.
- Not checked: glue-core older than 1.27.0 (glue-qt allows 1.23.0) with such data, where glue's world component still reads `ndim - 1 - i`.
- Tests on the branch: `test_multi_slice_helper.py`, 2 passed. Without the source change: `AssertionError: assert 'm' == ''`, 1 failed, 1 passed.
- ruff: passes.
- `slice-widget-time-axis` (#75) and `slice-slider-dependent-axis-warning` are stacked on this one.
