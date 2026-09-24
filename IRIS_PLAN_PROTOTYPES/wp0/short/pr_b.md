Wires up glue-viz/glue#2596 ('slice' collapse function) and glue-viz/glue#2601 (opt-in WCSAxes) in the Qt profile viewer.

- `MultiSliceWidgetHelper` works with any viewer state that has `x_att`/`slices`/`reference_data` (guards for a missing `y_att`, `x_att_pixel` support, stale sliders cleared, no sync while `len(slices) != ndim`).
- The profile options widget shows the slice sliders when the collapse function is `'slice'`.
- `ProfileViewer` passes `wcs=True` when glue-core has WCSAxes profile support; `ProfileTools` convert to the display unit before nearest-index lookups (pre-existing bug).

Everything is gated on `hasattr` checks: with released glue-core 1.27.0 behaviour is unchanged and 13 tests skip (68 passed / 14 skipped); with the two glue-core PRs applied, 81 passed / 1 skipped.

Label: enhancement.
