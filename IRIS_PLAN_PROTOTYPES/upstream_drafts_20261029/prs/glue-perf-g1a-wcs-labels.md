# Set the image viewer axis labels once when the WCS is reset

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g1a-wcs-labels`, commit 9e9270fd (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`MatplotlibImageMixin._set_wcs` resets `state.x_axislabel` and `state.y_axislabel` to `''` and then back to the world labels, so each label is set twice on the axes. Since astropy 7.0, `WCSAxes.set_xlabel` and `set_ylabel` work out every tick position before they set the label, which is costly with a slow WCS. Changing the slice of a cube whose displayed world coordinates depend on the slice resets the WCS, so every slice step pays for four tick placements only to restore the labels.

`_set_wcs` now sets the labels on the new axes from the state. The state's labels no longer go to `''` and back, so their callbacks fire only when a label changes. The label calls per slice change go from 4 to 2, and the rendered canvas is the same.

Measured in the Qt image viewer (offscreen, median of 25 slice steps) on a solar slit-jaw cube whose celestial axes depend on time, a slice step goes from 103 ms to 71 ms.

`test_slice_change_sets_axis_labels_once` counts the label calls for a slice change.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt and not run by me: the text is the commit message, shortened. It quotes 103 to 71 ms, the commit's own number, as the review asks (not the 105 to 39 ms of UPSTREAM_REVIEW.md, which needs a second half that is not in this branch).
- The commit message also gives 61 to 45 ms for a spectral raster; left out to keep the body short.
- The commit message names IRIS twice. That is an instrument, not glue-solar, so it can stay.
