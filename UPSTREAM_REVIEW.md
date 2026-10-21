# Upstream review (D89)

What glue-solar should send upstream, report, keep or drop, re-verified on 2026-10-19 against the latest releases and
mains: glue-core 1.27.0 and main 0039c22, glue-qt 0.4.2 and main 9780eaf9, astropy 8.0.2 and main a64a40b (WCSLIB
8.10), echo, mpl-scatter-density, matplotlib, fiasco main and irispy main. glue-solar main was 089a5b5. Every fault was
reproduced on both the release and main, or the row says why not. Delta-refreshed 2026-10-21 against glue-solar 3332410
and upstream mains glue fa1b58b3, glue-qt 9780eaf9, astropy 7d7cf6d, irispy fb7552f and dkist 2a4b15b (echo,
mpl-scatter-density and fiasco unchanged); see 'Delta 2026-10-21'.

The detail is in three sections, one table row per item with its re-verification, upstream status, recommendation and
the glue-solar code it retires: [glue-core](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-core.md) (75 items),
[glue-qt](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-qt.md) (44),
[astropy, WCSLIB, dkist and the rest](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/others.md) (46). Their reproducers
are in the folders beside them (the sections name them by their scratch paths; the files are the same). The brief the
reviewers followed is [BRIEF.md](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/BRIEF.md).

## In numbers

| Recommendation | glue-core | glue-qt | others | All |
| --- | --- | --- | --- | --- |
| UPSTREAM-PR | 58 | 32 | 14 | 104 |
| REPORT | 3 | 5 | 16 | 24 |
| WAIT | 7 | 3 | 4 | 14 |
| KEEP | 4 | 4 | 5 | 13 |
| DROP | 1 | 0 | 7 | 8 |

glue-core also has one parked draft (#2601) and one pointer row.

No upstream main fixes any glue-core or glue-qt fault in the register. glue main fa1b58b3 is 1.27.0 plus unrelated
commits (#2603's line layers among them; 1.28.0 is part-way through release), and glue-qt main is 0.4.2 plus two
commits. glue-qt main's CI has been red since 2026-02, which is why the user's drafts #68, #70, #74 and #75 show failing
jobs; #69 (the CI fix, approved) passes, and its 4 failing checks are allowed failures. Elsewhere, the only upstream
fixes since 2026-10-19 are dkist #764 and #765 (unreleased) and irispy's merges.

## Delta 2026-10-21

Refreshed for glue-solar #327-#367 and the register at 758c335. A second reviewer checked each section's delta, and the
checks' corrections are applied. What changed:

- **22 new rows.**
  - glue-core #69-#75: six small PRs and R36's report.
  - glue-qt 41-44: the close box leaving `_closed` unset, closed viewers saved in sessions, the `_Refit._limits`
    requeue, and a private `rng_mode` read.
  - others 36-46: dkist joins the section with the slit-jaw gWCS rows (`_off_frames`, NaN frames, R33, R34). Also R36's
    irispy half (DROP), R37, D95's 3x peak, the raster's single in-memory open, FITS card config reads, irispy's
    per-window WCS and meta, and the Mg II names.
- **Upstream fixed nothing in glue or glue-qt.**
  - dkist #765 (merged, unreleased) fixes the off-table inverse.
  - irispy merged #257, #258 and #260, so their WAITs are DROPs now.
  - irispy's #320 is a second way to retire the `FitInfoSubset` conversion.
- **The glue drafts' red `py311-test-visual` is fixed on main.** Rebase the drafts onto main; a CI re-run alone builds
  the old head and fails again. #2592 is no longer needed.
- **glue-core 1.28.0 (with the pytest plugin) is part-way through release.** Its tag build failed twice on 2026-10-21.
- **glue's `perf-g7` now retires glue-solar code** (`_Refit._limits`, #363), and so do glue-qt's `perf-q1`/`perf-q2`.
- **The three glue-qt Fit branches are not stacked** and conflict with each other: restack them before opening.
- **Done in glue-solar:** #329 dropped the SJI gzip-to-bytes step.

## Order to upstream

1. **Ready now, on the user's forks, each one commit with its test** (open as PRs):
   - glue `perf-g1a` … `perf-g10`: ten PRs, each applying cleanly to upstream main (merge-tree clean on fa1b58b3) and
     needing a CHANGES line (the SJI frame step 105 → 39 ms with g1a; startup, hidden subsets, link removal,
     histograms, sessions). g7 also retires the quicklook's `_Refit._limits`.
   - glue drafts #2598 and #2599 (fix its codestyle): mergeable. Their only red job, `py311-test-visual`, fails on two
     `TestWCSRegionDisplay` hashes that main has updated. Rebase each onto main, or merge main in. #2595 and #2597 go
     after their amendments (time axes out of `wcs_autolink`; restore `preferred_cmap` and save Quantities instead of
     skipping meta), and they need the same rebase.
   - glue-qt Fit tab: `fitter-settings` (one fitter per viewer, check boxes; also fixes Fit constraints being ignored),
     `fitter-settings-widget`, `fit-artists`: retire about 130 lines of `glue_patches.py`. Open `fitter-settings`
     first, then rebase the other two on it. Today they sit on main and conflict: in `_on_settings` and the test file
     for `fitter-settings-widget`, and in the test file only for `fit-artists`.
   - glue-qt `perf-q1` and `perf-q2` (the profile worker: 84 ms → 0.1 ms twice per point move; the quicklook spectrum
     about 250 ms sooner; either also retires `_Refit._limits`), `perf-q3` and `perf-q4` (icon caches: 45 ms → 0.2 ms
     per colormap combo; 473 icon loads → 1), `perf-q5` and `perf-q6` (startup). `perf-q6` and #68 conflict in a test
     file: rebase whichever merges second.
   - astropy `perf-a1-wcsaxes-pytest-import` (42 ms per process; merge-tree clean on main 7d7cf6d).
   - **astropy#19174, a comment** with a reproducer on astropy's own `tab-time-last-axis.fits`: 8 threads give wrong
     `all_pix2world` values in about 2,380 of 2,400 calls on 8.0.2 and on main; a lock gives none. The cause is
     WCSLIB's `tabx2s` writing scratch fields on the shared table (tab.c:1237-1247). Every glue-solar WCS lock waits
     on it; the plan's retirement test ("20 unlocked runs with 0 crashes") is too weak, as main corrupts silently.
     Still not posted (no activity on the issue since 2026-09-29).
2. **Small fixes to write** (2-10 lines each, a test each):
   - glue:
     - `WCSLink`'s shared slicing lists, `ProfileViewerState._update_priority`, `DerivedComponent.datetime`, the FITS
       subset-mask importer's integer check, `axis_label`'s index (SST's '' and 'Hplt'), the FITS exporter's `blank`,
       an empty `AggregateSlice`.
     - New, each riding with a PR already planned: `PixelSelectionTool._select_pixel` off the image (with the
       Pixel-point PR), `_update_slice_subset` as the data go (with the `stretch_global=False` faults),
       `_get_model_fitter` keeping a model's bound for a `None` limit (with `set_constraint`),
       `MplPathROI.finalize_selection`'s stale background and `DaskComponent` index arrays through `vindex` (with the
       path-slicer pieces).
   - glue-qt: `glue -x` (broken outright), a cancelled 'Add large data set?' breaking later viewers, playback outliving
     its viewer, the Table viewer's added rows and datetime search, missing tooltips, a slider move turning a Collapse
     into an int, Collapse dropping the range's last sample. New: the close box leaving `_closed` unset and closed
     viewers kept in `GlueApplication.viewers` (one PR, 2 lines, retiring about 18 lines).
   - astropy: `FitInfoSubset.__getattr__` (1 line; irispy #320 now reads the private `_fit_info_array` around it), the
     tie chain in `fitter_to_model_params_array` (about 3 lines), WCSAxes `grid(which='minor')`.
   - fiasco: the skip-name substring check (1 line).
   - dkist: `sanitize_index` taking a non-finite frame index as off the table (about 3 lines).
3. **Medium PRs:**
   - glue sessions: `LinkSameWithUnits`, Quantity and `preferred_cmap` savers, the `stretch_global=False` restore crash
     and lost `stretch_parameters` (both new), `DerivedComponent.units` (glue-solar's units are lost in sessions
     today), a -TAB WCS saver, the path slicer's savers.
   - glue's image artists (crosshairs, the Pixel point; upstream #2054): about 120 lines of `glue_patches.py`.
   - glue's profiles and statistics: cached-profile y limits (R14), native-dtype reductions (R21: 435 MiB for a
     92 MiB float32 cube), padded slice-subset results, row-wise sampling (R32); then the link manager (R6, R12, R24).
   - glue-qt keys by `isinstance`, matplotlib's keys off the canvas, slider coalescing while dragging (R16), a closed
     viewer's dashboard widgets deleted (removed data stays alive today).
   - astropy, in this order after the two above:
     - a -TAB `axis_correlation_matrix` from the tables (about 15 lines).
     - WCSAxes tick placement: a memo, then batched calls (R5: still 37 WCS calls per unchanged redraw on main).
     - io.fits reading `conf.strip_header_whitespace` once per header, not at each card (82% of a header walk, a
       third of irispy's raster read).
     - viewing a `decompress_in_memory` buffer instead of copying it (D95's 3x peak). This is small if the data may
       be read-only, medium if they must stay writeable.
   - irispy: one tabular WCS and one header dict per raster file, not per window (-31 s of a 75 s read; the user's
     pick in `wp10-l-big-stack-load`).
   - dkist: a vectorised `VaryingCelestialTransform` (R33, a human-written successor to the closed #762, on dkist#279)
     and a cached per-frame inverse (R34).
4. **Reports, not PRs** (24, mostly astropy and WCSLIB):
   - the SST -TAB `w.celestial` SIGSEGV
   - WCSAxes on one- and three-coordinate views, zero-size axes and unpickling
   - `parallel_fit_dask` resending every start array with each chunk
   - echo's combo match, mpl-scatter-density's resize hold
   - astropy.modeling's per-call overhead, as a comment on #6161 (R37)
   - a glue hook giving WCSAxes the shown frame's 2-D WCS (R36)
   - and the rest in the sections.
5. **Generic glue-solar features glue users would want**, after the above and on the user's call:
   - the Fit tab's model builder (about 330 lines, with its Save/Open)
   - Loop's range options (about 80), Blink (about 100), Follow/lock as a hover mode of glue's Pixel tool (about 90),
     keys (about 75)
   - Save frames or movie (170), Save profiles (34), a path's vertices typed in (19)
   - smaller tools: per-frame limits, the color bar, the wavelength band, physical aspect, Measure, gamma stretches.

   Hide axes is glue#2128 (open). Some wait on glue-qt#72 (subtool menus) and glue-qt#73 (lines; glue#2603 merged
   2026-10-21).

## Glue-solar changes now

- **Add a register row** for the gzipped raster's single in-memory open (`_raster_windows_data`,
  `_window_scaling(opened=)`, #345 and #352; others row 43, KEEP).
- **Fix the plan's Versions line:** irispy #182 (gWCS rasters, D14) was closed unmerged on 2026-10-19.
- **Release WAITs to track** (in the plan's `wp0-release-tracking`):
  - glue-core 1.28.0, with #2587's pytest plugin. It is part-way through release: the tag build failed twice on
    2026-10-21, and PyPI is at 1.27.0. Once glue-solar floors glue-core at 1.28.0 (`pyproject.toml:20`), drop
    `conftest.py:21-24`'s `CFG_DIR` lines.
  - A dkist release with #765: drop `_off_frames` (`iris.py:170-187`, `:318-319`).
  - glue-solar's astropy floor reaching 8.0.2 (#20462): drop `_jacobian`'s `epsilon=1e-12`.
  - An irispy pin past fb7552f (#320): drop the `FitInfoSubset` dict conversion (`fit_maps.py:209-213`). The
    follow-irispy PR to 34ff675 stops five merges short of it.

Done since:
- glue-solar follows irispy #256's dust detection (#327).
- #329 dropped the gzip-to-bytes step in `loaders/iris.py`: irispy reads a `.gz` once itself (the plan's
  `wp10-l-gzip-from-irispy`).
- glue-solar follows irispy #257, #258 and #260 (`residual=False`, `active_mask`).
- The plan's upstream items are folded into this review (`wp0-upstream`). That drops the stale entries:
  `translate_pixel`'s bare `Exception`, the two WCSAxes cases that did not reproduce, and irispy's `py314-devdeps`
  failure.

## Keep in glue-solar

Thirteen items:
- solar and IRIS features: the quicklook recipe, the last-session keeper, the Doppler unit converter, the mouse-over
  readout's ticks
- the user's decisions: D67's SST inverse, D70's sampling, D73's lock wrappers until astropy#19174 is fixed
- new since 2026-10-21: the gzipped raster's single in-memory open, D96's Mg II k and h names, and the private
  `rng_mode` read until glue-qt has a public one

Their rows say why. Some rows keep a part while the rest goes upstream, such as the velocity wording of the Doppler axis
label (glue-core #25).
