# Label slice sliders of WCS time axes with absolute times

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:slice-widget-time-axis` at `26ca431286` (pushed 2026-11-12)
- Open PR: #75 (draft)
- Needs: `slice-sliders-world-axis` (stacked on it)
- Label: enhancement

## Body

~~~~~markdown
A slice slider along a WCS time axis shows seconds from the reference time of the WCS, with `s` as the unit: `60.0 s`, not `2021-09-05T00:01:00`.

When the WCS gives astropy `Time` objects for that axis (a FITS WCS with `MJDREF` or `DATEREF`, or a gWCS temporal frame), the slider now shows ISO times in the time scale of the WCS, with the name of the scale (`UTC`, `TAI`, ...) in place of the unit. Typing an ISO time moves to the nearest slice. Milliseconds are shown only when some of the times need them.

The numbers are kept:
- for a FITS WCS without `MJDREF` or `DATEREF`, which astropy counts from MJD 0, so that it would show dates in 1858;
- for a time scale that astropy does not know (an unrecognized `TIMESYS` raises `ValueError`);
- for any world axis that does not come back as a `Time`.

`world_axis_times` in `glue_qt/viewers/common/slice_widget.py` gets the times from `HighLevelWCSWrapper.pixel_to_world`, at the center of the other axes as `world_axis` does. `SliceWidget` formats `datetime64` world values with `numpy.datetime_as_string`.

This is now one commit, stacked on #WORLD-AXIS-PR (read the world axis glue's world components use); only the last commit is new. It no longer changes the dependent-axis warning, which is #WARNING-PR.

Tests: `test_time_axis_slider_shows_times` in `test_multi_slice_helper.py` and `test_slice_world_datetime` in `test_data_slice_widget.py`. Both fail without the change.
~~~~~

## Notes for the owner (not to paste)

- Replace `#WORLD-AXIS-PR` and `#WARNING-PR` with the numbers of the `slice-sliders-world-axis` and `slice-slider-dependent-axis-warning` PRs.
- Existing fork branch, to force-push (#75). One commit on `slice-sliders-world-axis`: 4 files, +149 -5. The warning commit is out (now `slice-slider-dependent-axis-warning`).
- In it: the first commit; `pixel_axis=self.data.ndim - 1 - i` for the times; `world_axis_times` not in `__all__`; no dates for a FITS WCS without a reference time; the `except Exception` narrowed.
- The reference-time check is `isinstance(wcs, WCS) and not wcs.wcs.mjdref.any()`, not the patch's nested `getattr` (which would also take any object with a `.wcs.mjdref`): easier to read. LIMIT, as for the patch: it sees only a bare `astropy.wcs.WCS`. A FITS WCS inside `SlicedLowLevelWCS` without MJDREF still shows 1858 dates (probed: `['1858-11-17T00:00:00', '1858-11-17T00:01:00']`). A header with only DATEREF is fine: astropy's `fix()` sets MJDREF from it (probed); `wcs.wcs.dateref = ...` set by hand is not.
- `except Exception` is now `except ValueError`, the error astropy raises for a time scale it does not know. It is raised by `wcs.world_axis_object_components`, which the old code read outside the `try`, so an unrecognized TIMESYS raised while the sliders were built. That read is now inside the `try`, with an assertion for it. A WCS class that raises something else from its high-level API is no longer swallowed.
- The times are looked up after `world_label`, not before `world_warning`, so that this branch and the warning branch do not touch adjacent lines (they would conflict).
- Not pinned by a test: the `pixel_axis=self.data.ndim - 1 - i` line. Reverting it to `world_axis_index` passes all tests; it only matters for a time axis in data with more world than pixel axes. A probe with a 4-D FITS WCS sliced to 3 pixel axes shows the right times with the line as it is. Pinning it needs a 4-D WCS and about 12 more test lines: say if you want it.
- The test builds a fresh WCS for each case: astropy caches a WCS's high-level classes and does not notice a later change of TIMESYS or MJDREF, on the object or on a `deepcopy` of it (seen while writing the test).
- Seen with the reviewer's probe, unchanged from the original: cadences below a millisecond give equal labels; typing text that is not a time raises `ValueError`, as typing text that is not a number does on main.
- Tests on the branch: `test_multi_slice_helper.py` and `test_data_slice_widget.py`, 7 passed. With the test files on `slice-sliders-world-axis`: `ImportError: cannot import name 'world_axis_times'`, and `test_slice_world_datetime` fails with `UFuncNoLoopError: ufunc 'absolute' ... DateTime64DType` (1 failed, 3 passed). Removing the `ValueError` guard gives `ValueError: Unrecognized time CTYPE=TIME`; removing the reference-time check gives the 1858 times.
- ruff: passes.
