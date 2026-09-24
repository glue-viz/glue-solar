Datasets whose `coords` only implement the low-level APE-14 API (a `BaseWCSWrapper` around gWCS or an astropy `-TAB` WCS, as glue-solar builds for IRIS data to present arcseconds - the "wrapper that preserves units" of #2152) never autolink today: `wcs_autolink` keeps only `BaseHighLevelWCS` coords (0 links, no message) and a direct `WCSLink(sji, raster)` dies with `AttributeError: '_GlueWCS' object has no attribute 'has_celestial'`.

Changes
- `wcs_autolink` accepts `BaseLowLevelWCS`; `WCSLink` wraps bare low-level coords in `HighLevelWCSWrapper` and works on `.low_level_wcs`.
- The celestial cross-frame special case (SkyCoord galactic<->equatorial) is guarded behind `isinstance(..., astropy.wcs.WCS)` for both datasets; everything else uses physical-type matching.
- Pixel axes kept per matched world axis come from `axis_correlation_matrix` (`kept_numpy_axes`) instead of assuming world axis i <-> pixel axis `world_n_dim - i - 1`, which APE 14 does not guarantee (wrong for `-TAB` celestial axes and gWCS). Pixel axes that also drive unmatched world axes are sliced away when every matched world axis stays supported (an SJI's time axis: the link is exact at exposure 0).
- Slice tuples are sized by `pixel_n_dim` (astropy silently pads short tuples); `slicing_axes1/2` were aliased to one list (IndexError for mixed-ndim pairs); ndim mismatch and untransformable pairs raise `IncompatibleWCS` and are skipped by the autolinker instead of tracebacking.
- Matched types in a different order on the two sides (SJI lon,lat vs raster lat,lon) are transformed through world values with an explicit type permutation and unit conversion (`permuted_values_functions`); `pixel_to_pixel` pairs plain Quantities positionally and would transpose them. The probe fast path is only taken when both coords natively implement the high-level API.

Verified on real IRIS Level 2 data (irispy test files): SJI 1400 (62,40,37) gWCS + raster (187,40,20) `-TAB`, both wrapped low-level: 1 `WCSLink` pairing SJI [x, y] with raster [slit, step]; sky positions from either WCS agree to 3e-7 arcsec; round trip raster (20,50) -> SJI (88.612, 20.662) -> raster (19.999999, 49.999999). 0 links on 1.27.0. (That raster is sit-and-stare, so its 187-long "step" axis is really an exposure index; the link pairs it to SJI x through the pointing drift at SJI exposure 0, which is what the WCS says, not a temporal join.)

Note for wrapper authors (the #2152 use case): pairs whose matched types are in the same order still transform through `HighLevelWCSWrapper` objects, so a wrapper that changes `world_axis_units` must keep `world_axis_object_classes` / `world_axis_object_components` coherent with the new units (otherwise SkyCoord construction fails and the pair is reported incompatible). Happy to switch every wrapped low-level pair to the values path if you prefer that over the coherence requirement.

Known, pre-existing, unchanged: sessions containing low-level coords cannot be saved (only `@saver(astropy.wcs.WCS)` exists); `clone(link)` on such data raises `GlueSerializeError` for the coords, not for the link.

Tests: 11 new (`test_wcs_autolink_low_level`, `_low_level_and_fits_wcs`, `_low_level_disjoint`, `_low_level_transform_failure`, `_correlated_axes`, `_low_level_disjoint_same_ndim`, `_low_level_world_order_permutation`, `_ndim_mismatch`, `_low_level_11d`, `_all_axes_coupled`, `_iris_like`) on synthetic `BaseLowLevelWCS` fixtures with settable types/units/correlation matrix; the 20 existing astropy-WCS tests are unchanged.

Refs #2152. Downstream: glue-viz/glue-solar#44.

Label: enhancement (I cannot set labels on this repo).
