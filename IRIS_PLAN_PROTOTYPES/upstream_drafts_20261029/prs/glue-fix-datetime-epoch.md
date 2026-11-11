# Use matplotlib's date epoch in datetime64 <-> mpl conversions

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:fix-datetime-epoch`, commit 704d2187 (pushed 2026-11-12)
- Open PR: #2599 (draft)
- Label: bug

## Body

~~~~~markdown
`datetime64_to_mpl` and `mpl_to_datetime64` count days from 0001-01-01 (plus one), but matplotlib >= 3.3 counts from a configurable epoch that defaults to 1970-01-01, and glue never calls `set_epoch`. So every datetime axis is mislabelled: `num2date(datetime64_to_mpl(np.datetime64('2021-09-05')))` gives 3990-09-06, and a scatter viewer with a datetime x axis shows the wrong day.

- `datetime64_to_mpl` now calls `matplotlib.dates.date2num`.
- `mpl_to_datetime64` counts from `matplotlib.dates.get_epoch()`, whole seconds first and then the fraction, so it also works with an epoch far from the date, such as the one `set_epoch('0000-12-31')` restores (matplotlib's dates before 3.3).
- `get_epoch` needs matplotlib 3.3, so the minimum version and tox's `legacy` pin go from 3.2 to 3.3.
- The conversion code copied from matplotlib is removed, with its licence text: most of the 92 deleted lines.

`test_mpl_datetime64` now checks absolute values, one of them a fractional second before the epoch, and fails on main. `test_mpl_datetime64_old_epoch` covers the 0000-12-31 epoch.
~~~~~

## Notes for the owner (not to paste)

- One commit replaces the four. Against the fork branch, only `mpl_to_datetime64` and the tests differ.
- The NaT fix: the branch counted nanoseconds from the epoch in one int64, which overflows for the 0000-12-31 epoch and gave NaT silently. It now adds whole seconds to the epoch at second resolution, then the fraction in nanoseconds. I wrote these four lines myself from the review's description; the reviewer's own diff was not in the files I could read.
- Tests changed: the assertion that compared `datetime64_to_mpl` with `date2num` (the same function now) checks 18875.5 and -1.5/86400 instead. The four `before_epoch` cases are dropped, as they pass on main; a value before the epoch is kept inside `test_mpl_datetime64`, which fails on main.
- `test_mpl_datetime64_old_epoch` passes on main (main is right under the old epoch) and fails on the fork branch as it was: `assert np.datetime64('NaT','ns') == np.datetime64('2021-09-05T12:00:00')`. It guards the new code only.
- Tests: `glue/utils/tests/test_matplotlib.py` 14 passed, 1 skipped. On upstream/main `test_mpl_datetime64` fails: `[1]: 738038.5 (ACTUAL), 18875.5 (DESIRED)`.
- Not checked: no viewer test in glue uses a datetime axis, so the viewers' use of these functions is covered only by the unit tests. tox's `legacy` env is in no CI job.
- `test_mpl_datetime64` assumes matplotlib's default epoch (1970-01-01); it would fail for someone whose matplotlibrc sets `date.epoch`.
