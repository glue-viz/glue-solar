Datasets whose `coords` only implement the low-level APE-14 API (a `BaseWCSWrapper` around gWCS or a `-TAB` WCS, as glue-solar builds for IRIS data) never autolink: `wcs_autolink` keeps `BaseHighLevelWCS` only, and `WCSLink(sji, raster)` crashes on `has_celestial`.

- `wcs_autolink` accepts `BaseLowLevelWCS`; `WCSLink` wraps it in `HighLevelWCSWrapper`.
- The celestial cross-frame special case applies to astropy `WCS` pairs only; everything else matches on `world_axis_physical_types`.
- Pixel axes per matched world axis come from `axis_correlation_matrix`; axes that only drive unmatched world axes are sliced away (an SJI's time axis: the link is exact at exposure 0).
- Matched types in a different order transform through world values with an explicit permutation.
- Mismatched or untransformable pairs raise `IncompatibleWCS` and are skipped.

Verified on real IRIS Level 2 data (SJI gWCS + raster `-TAB`): one link, sky positions agree to 3e-7 arcsec, exact round trip. 11 new tests on synthetic low-level WCS fixtures; existing tests unchanged.

Note for wrapper authors (#2152): a wrapper that changes `world_axis_units` must keep `world_axis_object_classes`/`components` coherent, or the pair is reported incompatible.

Refs #2152. Downstream: glue-viz/glue-solar#44.

Label: enhancement.
