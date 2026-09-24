Stacked on #<C> (first two commits are that PR).

When a profile viewer is built with WCSAxes (`wcs=True`, the image viewer's mechanism) and world coordinates are shown on the x axis in their native unit, the axes are reset to the reference data's WCS sliced to 1D (`RectangularFrame1D`, `reset_wcs(slices=wcsaxes_slice, wcs=coords)`), so tick labels are formatted by the WCS (sexagesimal etc.).

Design rule (the open question from #2248, WCSAxes formatting vs `x_display_unit` competing for the same axis): `ProfileViewerState.wcsaxes_active` is true only when the viewer has WCSAxes AND reference coords are real (not None / LegacyCoordinates) AND `x_att` is a world component AND `(x_display_unit or '') == component native unit`. In that mode the profile, the x limits and ROIs are in pixel coordinates (WCSAxes draws world tick labels from pixel positions; same model as the image viewer), so `apply_roi` builds the subset on `x_att_pixel`. Any display-unit override, or data without real coords, falls back to an identity WCS and the existing plain-numeric/`x_display_unit` behaviour, unchanged. Crossing that boundary resets the x limits instead of converting them; `x_limits_pixel` records which kind a session saved so a session restored into a viewer in the other mode does not open blank.

Off by default: `SimpleProfileViewer` keeps plain axes unless `wcs=True`; glue-qt is unaffected until it passes `wcs=True` (glue-qt PR to follow, feature-gated). Python export emits `init_mpl(wcs=True)` / `reset_wcs` code; the whole export suite is re-run against a WCSAxes viewer (`TestExportPythonWCSAxes`). `update_x_ticklabel` uses `axes.coords[ndim - x_att_pixel.axis - 1].set_ticklabel` because `tick_params` is a no-op on a 1D-frame WCSAxes.

Salvaged from #2248 with its defects fixed: `reference_data is None` guard, slice indices read from `slices` instead of a hardcoded 0, no state mutation in property getters, coords index for ndim > 1, hidden y axis restored. #2248 is closed in favour of this.

Tests: `test_wcsaxes_profile`, `test_wcsaxes_identity_fallback`, `test_wcsaxes_slices`, `test_wcsaxes_limits_mode_mismatch`, `TestExportPythonWCSAxes`; units tests unchanged.

Label: enhancement (I cannot set labels on this repo).
