Adds `'slice'` to the profile viewer collapse functions: instead of collapsing the other dimensions with a statistic, the profile shows the data along the profile axis at the point given by the new `ProfileViewerState.slices` property (defaults to zeros, mirrors `ImageViewerState.slices`; `_set_default_slices` runs on reference-data change). Subset layers show the slice with values outside the mask set to NaN, like the statistical functions. The `UnitConverter` path is shared, so display units apply.

For layers whose dataset is not the reference data, `ProfileLayerState.slice_view` translates the reference-frame slice point into that dataset's own pixel indices through the pixel/coordinate links (`ref[data.pixel_component_ids[axis], point]`), rounds and bounds-checks it, and raises `IncompatibleDataException` (layer disabled) for unlinked axes or out-of-range points. The python export emits the equivalent `get_data`/`get_mask` code, and now fetches x values from the parent data rather than the Subset (indexing a Subset applies the mask and could return fewer values than `profile_values`; this also fixes the latent mismatch in the statistic-function subset export).

Motivation: a single-pixel spectrum (what IRIS `iris_raster_browser` shows) is not expressible with a collapsed statistic. This is the first of two PRs restarting #2248; the second adds opt-in WCSAxes formatting. glue-qt sliders follow in a glue-qt PR.

Tests: `test_slice_function`, `test_slice_function_subset`, `test_slice_function_linked`, `test_slice_function_out_of_bounds`, `test_slice_function_1d` (test_state.py), `test_unit_conversion_slice` (test_viewer.py:177), `test_slice`/`test_slice_subset` (test_python_export.py).

Known limitation: `slices` out of range for the reference data itself raise IndexError from `Component.__getitem__` (the artist is hidden, not disabled); the Qt sliders are bounded so the UI cannot produce it.

Label: enhancement (I cannot set labels on this repo).
