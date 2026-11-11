# Import scipy.optimize only when approximating a WCS link as affine

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g5-lazy-scipy-optimize`, commit a220d958 (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
The WCS autolinking plugin is loaded when glue starts, and its module imports `leastsq` from `scipy.optimize` at the top level, although only `WCSLink.as_affine_link` uses it. Importing `scipy.optimize` pulls in much of scipy, so every glue session pays for it even if no WCS link is ever approximated.

`leastsq` is now imported inside `as_affine_link`. With `glue.config` already imported, importing the plugin module goes from about 215 ms to under 1 ms (median of 11 fresh processes, Python 3.13 on macOS), and `scipy.optimize` is no longer in `sys.modules` afterwards.

`test_import_does_not_import_scipy_optimize` imports the plugin module in a subprocess and checks `sys.modules`. The line added to `.ruff.toml` allows that subprocess call (S603) in the test file, as for `test_python_export.py`.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, shortened. The review marks the branch ready as it is.
- `perf-g6-lazy-ipython` adds a line at the same place in `.ruff.toml`. The review found that all the branches merge cleanly with each other, so the two lines do not collide.
- The tracker wants this opened before row 13: the review says `ape14-wcs-link` conflicts with it in the test file.
- It touches `glue/plugins/wcs_autolinking/`, which another agent is working in; I changed nothing there.
