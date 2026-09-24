# Existing Glue capabilities: 2026-09-23 audit

This evidence supports the [corrected feature plan](../../IRIS_GLUE_GAP_PLAN.md#what-the-missing-features-mean-at-the-keyboard).
The earlier plan overstated missing point/profile navigation, time–wavelength
extraction and slit tools. No production feature or prototype controller was
implemented in this audit; the new code consists of capability probes.

## Results

| Check | Result | Interpretation |
| --- | --- | --- |
| Existing workflows, released glue-core 1.27.0 + Qt #74 checkout | 7 passed, 2 skipped | Pixel subset spectra/evolution, axis-swapped 4D images, Navigate, 3D PV extraction/parent navigation and playback work. Draft Slice tests are skipped. |
| Existing workflows, core #2601 + #2595 changes and Qt #70 | 9 passed | Adds draft fixed-index profiles and a real 3-scan IRIS stack: displayed arrays match direct slices; `Time` is not offered as a Profile x axis. Initially run together with three WCS probes: 12 passed. |
| Real-data WCS matrix, same combined sources with solar main | 4 passed | Confirms working SJI/raster link AND the current wrapper's rejected raster/stack/map pairings. “Passed” does not mean all pairings link. |
| Same WCS matrix with refreshed WP1 package | 4 passed | All five tested pairings suggest a link; SJI/raster geometry, ROI propagation, point-spectrum extraction and marker coordinates checked. Other pairs are link-creation checks. |

The main-versus-WP1 result is:

| Pair | Main | WP1 |
| --- | --- | --- |
| SJI/raster | 1 WCS link | 1 WCS link |
| Raster/raster | 0 | 1 |
| Stack/scan | 0 | 1 |
| Raster/derived spatial map | 0 | 1 |
| Derived map/derived map | 0 | 1 |

For the matched 2021 SJI/raster fixture, selecting SJI pixel `(25, 25)`
translated to raster `(step=3, slit=24)` and extracted the expected spectrum.
The WCS link omits the SJI frame and raster wavelength axes. At the sampled
pixels, its first-exposure geometry differs from the last SJI frame by
42.2202 arcsec. Exact first-frame agreement is checked only inside the
shared footprint where FITS-TAB inversion is defined; off-footprint values
can be NaN. This is not full temporal/spatial co-registration.

Main's raster high-level WCS conversion raises a latitude-range error
because arcsec values are interpreted as degrees. The WP1 wrapper corrects
that contract. SJI high-level conversion already agrees with main's declared
units. The tests compare both configurations rather than assuming all main
wrappers are broken.

The pixel path uses `PixelSubsetState.get_xy` / `to_array` and the Profile
aggregation path. It is not proof that every generic mask or draft Slice
profile automatically works on every linked dataset. Draft Slice uses its
own fixed indices, and the probe explicitly confirms that moving an image
point does not change those sliders or another image plane's fixed indices.

## Evidence and source locations

- [Workflow probes](test_existing_workflows.py): actual Pixel mouse events,
  subset-band aggregation, axis switching, navigation callbacks, native PV
  extraction and parent navigation, playback, and real stacked IRIS arrays.
- [WCS probes](test_wcs_capabilities.py): native `wcs_autolink` suggestions,
  link installation, round trips, world coordinates, late-frame discrepancy,
  spatial ROIs and linked pixel extraction. WP1 does not install additional
  world/time links during these checks.
- Core `glue/viewers/image/pixel_selection_mode.py`: click/drag/release.
- Core `glue/viewers/image/pixel_selection_subset_state.py`: linked pixel
  extraction/marker coordinates. `glue/core/data.py` uses this path for
  subset profile statistics; `glue/viewers/image/layer_artist.py` uses it
  for point markers.
- Core `glue/viewers/image/state.py`: `numpy_slice_aggregation_transpose`,
  `get_sliced_data`. No new extraction needed for axis-parallel planes.
- Core draft `glue/viewers/profile/state.py`: `slice_view`, `update_profile`;
  Profile x-axis helper excludes arbitrary numeric/datetime components.
- Qt `glue_qt/viewers/profile/profile_tools.py`: Navigate, Collapse, Fit.
- Qt `glue_qt/plugins/tools/pv_slicer/pv_slicer.py`: registered legacy
  3D tool, standalone PV window and parent crosshair/slice callbacks.
- Core `glue/plugins/tools/path_slicer/`: newer derived-data/path helpers;
  the inspected Qt entry point does not call them. Their presence alone
  does not imply that Qt's active tool supports 4D or their newer behavior.
- Qt `glue_qt/viewers/common/data_slice_widget.py`: playback and wrapping.
- Qt `glue_qt/app/application.py`: tiling, fixed-layout registration and
  session actions. Core `glue/core/units.py`: ordinary unit conversion.
- Core `glue/core/aggregate.py`: generic moments in pixel coordinates;
  `glue/core/fitters.py`: Gaussian/polynomial profile fitters.

Official [Profile tools](https://docs.glueviz.org/en/latest/gui_guide/spectrum.html)
and [Slice Extraction](https://docs.glueviz.org/en/latest/gui_guide/slice.html)
document the pre-existing workflows. Their versioned pages lag source, so
code and probes establish the present details.

## Reproduction

The baseline environment is unchanged from the [prototype refresh](../README.md#validation-2026-09-23).
GitHub heads rechecked for this audit:

- Core #2601: `acaf4e1c0ef88d513aecc158f81c8b9dcef9c28b` (includes #2596).
- Core #2595: `c49aeb1af14a8504c8f75a42d3a36883be5e9776`.
- Shared core base: `77dc9b886979d185fbeb3eb27c82094acb2c497f`.
- Qt #70: `f1471b7ad843b453bf0c8f4e92e743cce04c6e7d`.

Export #2601 to a temporary directory using `git archive`, then apply
`git diff 77dc9b8 c49aeb1 -- glue/plugins/wcs_autolinking` there. This applies
both #2595 files (implementation and upstream tests), passes `git apply
--check`, and leaves the real checkouts untouched. Export Qt #70 separately.
This is a limited source combination, not an eleven-PR integration test.

The actual combined directory is `/tmp/iris-plan-validation-20260923/core-combined`;
Qt is `/tmp/iris-plan-validation-20260922/qt-profile`.
From the solar repository root:

```sh
iris_root="$PWD"
iris_protos="$iris_root/IRIS_PLAN_PROTOTYPES"
iris_runner="$iris_protos/review_20260905/run_checks.py"
iris_core="/tmp/iris-plan-validation-20260923/core-combined"
iris_qt="/tmp/iris-plan-validation-20260922/qt-profile"

# Existing baseline; skips only the two draft-Slice cases.
.venv/bin/python -B "$iris_runner" "$iris_root" \
  "$iris_protos/review_20260923/test_existing_workflows.py" -p glue_solar.conftest

# Existing workflows with the draft features and main solar.
.venv/bin/python -B "$iris_runner" "$iris_core:$iris_qt:$iris_root" \
  "$iris_protos/review_20260923/test_existing_workflows.py" -p glue_solar.conftest

# Native WCS autolinking with main's wrapper.
.venv/bin/python -B "$iris_runner" "$iris_core:$iris_qt:$iris_root" \
  "$iris_protos/review_20260923/test_wcs_capabilities.py" -p glue_solar.conftest -s

# Same matrix, with the proposed wrapper correction.
.venv/bin/python -B "$iris_runner" "$iris_core:$iris_qt:$iris_protos/wp1" \
  "$iris_protos/review_20260923/test_wcs_capabilities.py" -p glue_solar.conftest -s
```

PV checks filter only two pre-existing deprecations: spectral-cube's
`COPY_IF_NEEDED` import under Astropy 8, and the legacy standalone viewer's
colormap `color` key. Without these filters the repo's warnings-as-errors
policy stops the probe before the actual tool behavior. No library code was
patched to make the PV test pass. Initial probe mistakes (tuple versus list
for DataCollection, PV canvas access, and off-footprint test pixels) were
corrected before recording results.

Limits: offscreen Qt, bundled small fixtures and a synthetic 4D cube; no
science download, full native GUI walkthrough, large-data performance test,
new hover mode, all-PR integration, full AIA registration or complete linked
IRIS application-session test. CI status was not checked.
