Stacked on #2596 (first two commits).

With `wcs=True` (the image viewer's mechanism) and world coordinates shown in their native unit, the profile axes are reset to the reference data's WCS sliced to 1D (`RectangularFrame1D`), so tick labels are WCS-formatted. In that mode the profile, x limits and ROIs are in pixel coordinates, as in the image viewer. A display-unit override, or data without real coords, falls back to the existing plain-axes behaviour unchanged. `x_limits_pixel` records which kind of limits a session saved, so a viewer restored in the other mode does not open blank.

Off by default: `SimpleProfileViewer` keeps plain axes unless `wcs=True`; glue-qt is unaffected until its viewer passes it (separate, feature-gated PR).

Salvaged from #2248 with its defects fixed (reference_data guard, slice indices from `slices`, no state mutation in getters, hidden y axis restored); #2248 is closed in favour of this.

Label: enhancement.
