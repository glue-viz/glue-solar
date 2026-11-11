# Performance findings: the detail the tables do not carry

The section tables say what each performance finding (R1-R37) is, where it is and which fork branch has it. This
page keeps what they leave out and a PR needs: the approach, and the measurement that argues for it. It is what was
still accurate and still needed in GLUE_SPEED.md, which left the plan branch on 2026-11-11.

Checked on 2026-11-11 by reading the named functions in the installed releases (glue-core 1.28.0, glue-qt 0.4.2,
astropy 8.0.2, dkist 1.18.1): every fault below is still there, and no upstream commit since 2026-10-28 touches one.
Nothing was re-measured. Unless a line says otherwise, numbers are from the 2026-10-01 survey (glue-core 1.27.0,
glue-qt 0.4.2, astropy 8.0.1, macOS, offscreen Qt with Agg, IRIS 4000255147: Si IV cube 1600x417x262, SJI 1400).
Line numbers are the installed releases'. What each fork branch already contains was taken from the tables, not from
the branch diffs: check a branch before pasting its line into a PR.

## glue-core

- **R1 (with `perf-g1a`).**
  - `x_att` and `y_att` each call `_set_wcs` (`viewers/image/viewer.py:47-48`), so an axis change runs it twice:
    coalesce them.
  - The coords-label fix must run in every `_set_wcs`, not only on slice changes: quicklook open 1.91 to 1.29 s,
    against -0.14 s slice-only.
  - Gains: SJI frame step 105-109 to 38-41 ms; Pixel click 378 to 247 ms; canvas, ticks and labels identical in 15
    of 15 steps.
- **R2 (glue-core row 39 has no numbers).**
  - Where: `RoiSubsetStateNd.to_mask` (`core/subset.py:562-564`) evaluates each attribute through
    `world2pixel_single_axis` (`coordinate_helpers.py:122-124`), and `fixed_resolution_buffer.py:312` asks for every
    screen pixel.
  - Approach 1: one `world_to_pixel_values` per `to_mask`/`get_mask`, cached on (coords, input cids, view) and shared
    by sibling `CoordinateComponentLink`s.
  - Approach 2: map the ROI outline forward and evaluate the inverse only inside its bounding box plus a margin; fall
    back where the forward chain is missing or not finite.
  - Measurement: 4.79 s per SJI frame with a raster ROI shown, against 0.10 s without. Approach 1 alone 4.64 to
    2.26 s; both 4.64 to 0.21 s (21.8x). At twice the buffer, 29.7 to 2.92 s.
  - Limits of the evidence: masks identical, rectangular ROIs only; 67% of each inversion is outside the footprint.
- **R4 (`perf-g2`).** -27 to -35 ms per Point move for each viewer with a hidden subset layer. Five tiled SJI viewers
  with four hidden: 157.6 to 44.3 ms. Two quicklooks: 416 to 277 ms.
- **R6, the medium follow-up after `perf-discover-links`.** Index links by input cid once per update and expand level
  by level with missing-input counters. Compute `self._links | self._inverse_links` once per update (today once per
  dataset, `link_manager.py:250`). Prototype: 249 to 0.37 s for N=99 all-pairs.
- **R7.**
  - For a `PixelSubsetState`, draw the crosshair only, or an image whose extent is the bounding box of the selected
    pixels (keeps the tint when zoomed in), in place of the full-view RGBA (`viewers/image/layer_artist.py:253-278,
    303-307`).
  - Build `SliceSubsetState` masks for index-array views from the indices (`start <= index < stop`), not
    `np.zeros(data.shape, bool)` (`subset.py:1380-1384`): 0.04 ms against 0.3-1.5 ms.
  - Maximized spectrogram draw: 66.9 to 44.6 ms at DPR 1, 125.2 to 78.5 ms at DPR 2.
- **R10, beyond `perf-g10`.**
  - `viewers/image/state.py:477-480` applies the data's aggregation function to subset masks too. Use `np.any`:
    nanmedian on the bool mask takes 54 ms, `np.any` 0.4 ms.
  - Cache the aggregated 2-D result keyed on bounds and function (the buffer cache holds the array before
    aggregation), or collapse once at native resolution.
  - Redraw on a 588x347 canvas: plain slice 16.9 ms, nanmedian over 100 px 218 ms (317 ms with the Point layer).
  - `np.nanmedian` was 2.5x slower than sort-and-count on short axes in numpy 2.5.3: re-check before reporting.
- **R11.** After any link change the next SJI draw with a linked ROI takes 4.71-4.74 s, against 0.030 s cached. Link
  Data's OK with no edits costs the same, because `dialogs/link_editor/state.py:317-331` builds new link objects;
  comparing links by from/to ids and function fixes only that case. On a 9.9 GB SST cube the same message recomputes
  the Profile data layer's whole-cube maximum: 5.35 s (2026-10-10).
- **R14.**
  - Recipe for `_reset_y_limits` (`viewers/profile/state.py:212-242`; called from the `normalize` and `function`
    callbacks at 66-67 and from `reset_limits` at 158-161): use only cached profiles; let glue-qt's artist reset the y
    limits when its computation ends; do not force `reset=True` when the cache was just filled.
  - Argument: Function-change freezes of 661 ms (mean) and 2.80 s (median) on the sit-and-stare cube. On a 9.9 GB
    SST cube the Profile button takes 27.4 s cold, 21.2 s of it a main-thread freeze, with 9.2 GB read (2026-10-10).
- **R21.**
  - Mean as `sum(dtype=float64, where=)` over `count_nonzero`; minimum and maximum with `initial=±inf` plus an
    all-NaN rule; fold the subset mask into the same `where=`. Result: 673 to 441 ms, peak 713 to 75 MiB.
  - Chunks run along the profile axis only (`core/data.py:1710-1725`), so one chunk is a whole plane: 1.24e8 values,
    about 1 GB as float64, on the SST cube.
- **R23, the half `perf-g8` leaves.** `utils/array.py:546-572` builds a keep mask and copies `x[keep]`, though
  `histogram1d` already drops NaN and out-of-range values. Pass the raw 1-D unweighted array, keeping the
  `10 * spacing` nudge at line 605. Whole cube: 679 to 490 ms, peak 728 to 0.1 MiB, identical counts.
- **R24 (glue-core row 55 has no approach).** Skip the pairwise `equivalent_pixel_cids` pass
  (`link_manager.py:257-265`) when no identity link touches a pixel cid; recompute only datasets whose links changed;
  cache the component lists per update. Profile: 15.7 of 18.1 s, mostly `_find_identical_reference_cid`. 102 datasets
  appended one at a time take 5.38 s, against 0.158 s for one `extend`.
- **R26.** Three import sites: `utils/array.py:10-14`, `core/data.py:42`, `core/component.py:11`.
- **Startup, per launch without glue-solar.** R22 0.155 s, R25 0.169 s, R26 0.136 s, R31 0.28 s (non-Qt use only).
- **R32 / SST10.** A new Image viewer on a cold memory-mapped cube reads 0.68-0.74 GB in about 10,000 page-ins:
  1.75-1.82 s cold against 0.53-0.55 s warm (2026-10-10). The caller is `StateAttributeLimitsHelper`
  (`core/state_objects.py:405-422`).
- **R18, for whoever unparks it.** A single `copy_from_bbox` is not enough, because ticks and frame overlay the
  image: the decorations need their own cached layer above it. Upper bound: SJI contrast event 31 to about 8 ms.

## glue-qt

- **R22, the third site.** `GlueApplication.start()` calls `_fix_ipython_pylab()` (`app/application.py:1222`, defined
  at 48-51), which imports IPython. Return early unless `'IPython' in sys.modules`. `perf-g6` and `perf-q5` alone save
  0.072 s of the 0.155 s. Whether `perf-q5` already has this was not checked.
- **R9.** With two quicklooks open, the hidden tab's 6 draws take 117-120 ms of a 416-431 ms Point move, with 0
  paints. Ten hidden SJI viewers: 328 to 17 ms emulated.
- **R16.** A 2 s drag of 120 uncompressed positions gives 0.5 SJI draws/s and finishes after 8.2-8.3 s. Coalesced:
  9.7 draws/s at 110 ms lag. X11-like compressed input already matches coalescing.
- **R29.** The splash appears at about 1.36 s of 2.44 s; a first launch with an empty font cache shows nothing for
  9.3 s. `main.py:6-8` imports glue at module level, and `get_splash` (207-211) imports `glue_qt.app.splash_screen`,
  which runs `glue_qt/app/__init__`. Create the QApplication and splash first; move `QtSplashScreen` out of
  `glue_qt.app` or make that `__init__` lazy.
- **R15, the second PR.** 99 datasets added take 1.365 s, against 0.185 s with the model unsubscribed. A cheaper
  route than `beginInsertRows`: coalesce the add messages with `hub.delay_callbacks` in `DataCollection.extend`.

## astropy

**R5, WCSAxes tick placement, as PRs.** There is no fork branch: the prototypes are in
`wcsaxes_study_20261001.tar.gz`, on the Linux machine only (OPERATIONS.md). The placement code is unchanged in 8.0.2
(`core.py:509-514, 524-565`; `coordinate_helpers.py:990, 1018-1044`); two wcsaxes PRs since (#20783, #20784) mean a
rebase, not a redesign. State numbers on solar data in each PR: the maintainer asked for that on #16366.

1. **PR 1, memo.** Reuse `pixel_to_world_values` results within one placement.
   - Change: `core.py` only, about 30 lines (the archive's `minimal/upstream_core.diff`, +55/-16), the same scope and
     argument as #16366's `_coord_range`. Pass `values` through unchanged in the wrapper.
   - Gain: calls 37 to 21 per draw and 33 to 17 per `set_xlabel`; SJI draw 28.1 to 21.4 ms.
   - Bring: a non-image test counting calls on a 2-D WCS; a test that no `transform` attribute is left behind and no
     result array is shared; unchanged figure hashes (`py312-test-image-mpl380-cov`); a `performance` changelog
     entry; the `benchmark` label (`time_basic_plot_with_grid_and_overlay` moves -23 to -26%); a new asv benchmark on
     a sliced 3-D or slow APE-14 WCS, since the five existing ones use 2-D FITS headers.
   - Expected objection: instance-attribute shadowing. Have the explicit-cache alternative ready; it loses the
     overlay gain.
2. **PR 2, batching.** Sample the frame and the tick-angle shifts once per placement, in one transform call shared
   by all coordinate helpers.
   - Change: `frame.py` (`Spine.data` setter, `world` getter, `sample`), `coordinate_helpers.py` (`_update_ticks`,
     about 10 lines plus a helper), `core.py` (`_update_tick_and_label_positions`). The archive's prototype 2 plus
     `batch_fix.py`.
   - Gain: calls 37 to 3; -11.6 ms per SJI placement.
   - Before opening: fold in both skeptic fixes; choose how the now-lazy `Spine.world` behaves; consider evaluating
     shifts only for the spines stock evaluates; measure it stacked on PR 1 (not done; estimate 19 to 13 ms per SJI
     draw).
   - Bring: the call-count test; tests for WCSes that raise outside their domain, all-NaN spines and zero-size axes;
     hashes on Linux CI (the x86 last-bit risk); the archive's `batch/compare.py` as evidence.
3. **PR 3, placement cache across draws.** Only after PRs 1 and 2 are merged and re-measured.
   - Then worth about 4.3 ms per unchanged SJI redraw (16 ms today). It helps contrast and bias drags, not glue's
     slice steps, which make a new transform each time.
   - Open an issue first, asking which invalidation the maintainer accepts: an explicit `invalidate` hook plus cheap
     key fields, not a probe.
   - Bring tests that redraw after every kind of change (the archive's `cache/ident.py`); today's suite passes with a
     cache that never invalidates.
   - A cache must reproduce the second draw: the first and second differ in the last bits of one label position.
   - The alternative is R18 in glue.
4. **PR 4, lazy `set_xlabel`/`set_ylabel`.** Skip it if `perf-g1a` lands in glue.
   - After PRs 1 and 2 it saves 3.8 ms per label call.
   - It changes when a label picks its coordinate, needs a hand-kept list of 12 flushing methods, and breaks
     `test_set_label_properties`. Marking the ticks stale is not enough: the coordinate is chosen from the tick
     update.
   - Ask first whether the eager call in 46a541d624 was only for the tests.
5. **Drive-by for PR 1 or 2.** `coords.frame.update()` in `_update_tick_and_label_positions` (`core.py:510`) is
   reported as a no-op. Remove it unless a custom frame defines `update()`; check sunpy's frames.

**R13, the location for others row 21.** `_BaseHDU.readfrom` seeks past each HDU's data after reading its header
(`io/fits/hdu/base.py:364`). On a gzip stream that inflates the data; reading it later seeks back and inflates
again. One inflation of the 129.6 MB SJI takes 0.357 s, and `load_data` makes five.

## WCSLIB

**R8, the ideas for `tabs2x()`** (the email's text is not on this branch; `upstream_drafts_20261029/wcslib/` has the
measurements and the reproducer):

- For M = 2, solve the bilinear cell directly in `tabvox()` (a quadratic), as an exact containment test.
- Start the search at the previous point's cell.
- Index the cell bounding boxes in place of the row walk.
- Ask what the right answer is where cells overlap: the first cell, the one nearest a hint, or a not-unique status.
- Measurements: 6.2 ms per point on 4000255147 (2026-10-09); 7.8 ms synthetic and 11.5 ms on 4204700143
  (2026-10-29, WCSLIB 8.6); 42 µs for a 0.35" scan.

## matplotlib (no row in any table)

- **R9, the other home.** `FigureCanvasQT._draw_idle` (`backends/backend_qt.py:515-526`) checks only deletion and
  size, not visibility. glue-qt row 4 says to report first, to settle glue-qt against matplotlib.
- **R19.** For an opaque RGBA image, matplotlib premultiplies, resamples and demultiplies at device resolution
  (`image.py`, about 533-557 in 3.11.2; not re-read). Skip the demultiply when alpha is 1, or use a faster
  nearest-neighbour upsample. Resample is 42.3 ms of an 86.9 ms maximized SJI draw at DPR 2.

## dkist

**R34.** Of a 1.24 ms one-point inverse, building the frame's inverse model takes 0.42 ms and evaluating a built one
0.098 ms (2026-10-20, dkist 1.17.0). That split argues for the per-frame inverse cache after the #762 successor.

## The USB slow-I/O check that main cites

`glue_solar/sources/sst.py:287` and `docs/dev_guide/workarounds.rst:130` on main cite "GLUE_SPEED.md, 2026-10-31"
for these, until `wp0-q-readable` re-points them. Cold, the 2022 / 2024 SST cubes on the Mac over USB:

- Slit panel read: plain map 817 / 727 ms; with per-page MADV_WILLNEED 48 / 44 ms (Linux NVMe 146 / 94 to 10 /
  11 ms).
- Full slit: plain map 2249 / 1704 ms; per-page hint 3103 / 2046 ms; one sequential read per plane of the band
  470 / 477 ms.
- Whole band hinted: 3052 / 2038 ms. MADV_RANDOM alone is slower than no hint on both machines.
