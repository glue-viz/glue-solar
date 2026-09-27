Adds a `'slice'` collapse function to the profile viewer: the profile shows the data along the profile axis at the point given by the new `ProfileViewerState.slices` property (mirrors `ImageViewerState.slices`) instead of a collapsed statistic. Subset layers mask values outside the subset with NaN; display units apply as before.

For layers whose dataset is not the reference data, `ProfileLayerState.slice_view` translates the slice point through the pixel links and raises `IncompatibleDataException` (layer disabled) for unlinked axes or out-of-range points. The python export emits the equivalent code and now takes x values from the parent data rather than the Subset.

Motivation: a single-pixel spectrum (IRIS raster browsing) cannot be expressed as a statistic. First of two PRs restarting #2248; the second adds opt-in WCSAxes formatting, and glue-qt sliders follow in a glue-qt PR.

Known limitation: `slices` out of range for the reference data itself raises IndexError (the Qt sliders are bounded).

Label: enhancement.
