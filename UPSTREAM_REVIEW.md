# Upstream review (D89)

What glue-solar should send upstream, report, keep or drop, re-verified on 2026-10-19 against the latest releases and
mains: glue-core 1.27.0 and main 0039c22, glue-qt 0.4.2 and main 9780eaf9, astropy 8.0.2 and main a64a40b (WCSLIB
8.10), echo, mpl-scatter-density, matplotlib, fiasco main and irispy main. glue-solar main was 089a5b5. Every fault was
reproduced on both the release and main, or the row says why not. Delta-refreshed 2026-10-21 against glue-solar 3332410
and upstream mains glue fa1b58b3, glue-qt 9780eaf9, astropy 7d7cf6d, irispy fb7552f and dkist 2a4b15b (echo,
mpl-scatter-density and fiasco unchanged); see 'Delta 2026-10-21'. Delta-refreshed 2026-10-28 against glue-solar
6072b60 and upstream mains glue 3683f07c (= glue-core 1.28.0), glue-qt 9780eaf9, astropy e91800f, irispy 134c299,
dkist 2a4b15b, gwcs 7f7e664, fiasco a3445e0 and pytest a7b2446 (echo, mpl-scatter-density and reproject unchanged);
see 'Delta 2026-10-28'.

The detail is in four sections, one table row per item with its re-verification, upstream status, recommendation and
the glue-solar code it retires: [glue-core](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-core.md) (86 items),
[glue-qt](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-qt.md) (46),
[astropy, WCSLIB, irispy and the rest](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/others.md) (46) and
[dkist, gwcs and asdf](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/dkist.md) (10, new). Their reproducers are in the
folders beside them (the sections name them by their scratch paths; the files are the same). The brief the reviewers
followed is [BRIEF.md](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/BRIEF.md).

## In numbers

| Recommendation | glue-core | glue-qt | others | dkist | All |
| --- | --- | --- | --- | --- | --- |
| UPSTREAM-PR | 62 | 34 | 11 | 7 | 114 |
| REPORT | 6 | 5 | 18 | 1 | 30 |
| WAIT | 7 | 3 | 3 | 1 | 14 |
| KEEP | 7 | 4 | 6 | 1 | 18 |
| DROP | 2 | 0 | 8 | 0 | 10 |

glue-core also has one parked draft (#2601) and one pointer row.

No upstream release or main fixes any glue-core or glue-qt fault in the register. glue-core 1.28.0 (2026-10-22) is
main 3683f07c, and its only change for glue-solar is the pytest plugin (glue-core #68, done). glue-qt main is 0.4.2
plus two commits. glue-qt main's CI has been red since 2026-02, which is why the user's drafts #68, #70, #74 and #75
show failing jobs; #69 (the CI fix, approved) passes, and its 4 failing checks are allowed failures. Elsewhere, the
only upstream fixes since 2026-10-19 are dkist #764 and #765 (still unreleased) and irispy's merges (#257, #258 and
#260; #335 and #341 for the per-window raster read).

## Delta 2026-10-28

Refreshed for glue-solar #368-#391 (the DKIST work, D102-D108) and the register at 896b0ca. A second reviewer checked
each section's delta, and the checks' corrections are applied. What changed:

- **23 new rows, and a dkist section.**
  - glue-core #76-#86: four small PRs (undo, APE-14 `WCSLink` on the new fork branch `ape14-wcs-link`, the Dask
    bounding box, `cmap_bad`), three reports (world axes, on glue#2574; equal-depth link paths; the layer buffer's
    footprint), three KEEPs and the spanning-set autolink (WAIT).
  - glue-qt 45-46: the slice sliders (replaced ones shown again, the world axis read as `ndim - 1 - i`) and the edit
    subset emptied by a data-tree rebuild.
  - others 47-50: WCSAxes on an all-NaN range, pytest 9.2's `monkeypatch` undo and `approx` with None, and the mosaic's
    fitted tile WCSes (KEEP).
  - dkist.md: others 36-39 become its rows 1-4, plus six new rows: the shared model's thread race, `Unravel`,
    whole-file reads (#226), `target`, the Ravel ends (KEEP) and a relative `files.basepath`.
- **Upstream:** glue-core 1.28.0 was released (CI-only commits since fa1b58b3). irispy main fixed the per-window raster
  read (others row 45, now DROP). Nothing else was released or fixed.
- **New, worth noting:** R6's one-pass `discover_links` is a small PR now (glue-core #42: 11.2 s → 0.25 s at N=99). The
  closed dkist #762's head fixes three dkist rows and halves a fourth, so its successor comes first of dkist's PRs.
- **Stacking:** the 13 glue branches (g1a…g10, #2597-#2599) still merge cleanly together on 3683f07c. g2 conflicts with
  the new #2604; g5 with #2595 and `ape14-wcs-link`; g7 with #2596/#2601.
- **Done in glue-solar:** #372 follows glue-core 1.28.0 and dropped `conftest.py`'s `CFG_DIR` lines (glue-core #68).
  #382 floors astropy at 8.0.2. `_jacobian`'s `epsilon=1e-12` stays: on 8.0.2 the documented C II recipe converges with it
  and hits the evaluation limit with the default step (bug hunt wave 8, FIT8-1; others row 24).

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
   - glue `perf-g1a` … `perf-g10`: ten PRs, each applying cleanly to upstream main (merge-tree clean on 3683f07c =
     1.28.0) and needing a CHANGES line (the SJI frame step 105 → 39 ms with g1a; startup, hidden subsets, link removal,
     histograms, sessions). g7 also retires the quicklook's `_Refit._limits`. g2 conflicts with the new #2604 in a test
     file's imports: rebase g2 if #2604 lands first.
   - glue `ape14-wcs-link` (new: APE-14 coordinates in `WCSLink`; retires about 100 lines of `glue_patches.py`). First
     add a trial at the middle, first and last pixel, and refuse a non-finite one. Open it before #2595, which
     conflicts with it in both files and rebases onto it.
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
   - astropy `perf-a1-wcsaxes-pytest-import` (42 ms per process; merge-tree clean on main e91800f, 154 commits behind).
   - **astropy#19174, a comment** with a reproducer on astropy's own `tab-time-last-axis.fits`: 8 threads give wrong
     `all_pix2world` values in about 2,380 of 2,400 calls on 8.0.2 and on main; a lock gives none. The cause is
     WCSLIB's `tabx2s` writing scratch fields on the shared table (tab.c:1237-1247). Every glue-solar WCS lock waits
     on it; the plan's retirement test ("20 unlocked runs with 0 crashes") is too weak, as main corrupts silently.
     Still not posted (no activity on the issue since 2026-09-29).
2. **Small fixes to write** (1-10 lines each, a test each):
   - glue:
     - `WCSLink`'s shared slicing lists, `ProfileViewerState._update_priority`, `DerivedComponent.datetime`, the FITS
       subset-mask importer's integer check, `axis_label`'s index (SST's '' and 'Hplt'), the FITS exporter's `blank`,
       an empty `AggregateSlice`.
     - Each riding with a PR already planned: `PixelSelectionTool._select_pixel` off the image (with the Pixel-point
       PR), `_update_slice_subset` as the data go (with the `stretch_global=False` faults), `_get_model_fitter` keeping
       a model's bound for a `None` limit (with `set_constraint`), `MplPathROI.finalize_selection`'s stale background
       and `DaskComponent` index arrays through `vindex` (with the path-slicer pieces). New: `ApplySubsetState.undo`
       removing only what its `do` made (with Redo), and the Image buffer reading a `DaskComponent`'s samples through
       the same `vindex`.
     - New on their own: a restored `cmap_bad` given to the image (1 line), and the one-pass `discover_links` (R6,
       about 15 lines; its test compares derived cids and depths, as equal-depth ties may take another link).
   - glue-qt: `glue -x` (broken outright), a cancelled 'Add large data set?' breaking later viewers, playback outliving
     its viewer, the Table viewer's added rows and datetime search, missing tooltips, a slider move turning a Collapse
     into an int, Collapse dropping the range's last sample. The close box leaving `_closed` unset and closed viewers
     kept in `GlueApplication.viewers` (one PR, 2 lines, retiring about 18 lines). New: the slice sliders (hide a
     replaced one before closing it; read world axis `world_n_dim - 1 - i`: 4 lines retiring 32; open it before #75),
     and the edit subset kept through a tree rebuild (two parts, about 10 lines, tried).
   - astropy: `FitInfoSubset.__getattr__` (1 line; irispy now reads the private `_fit_info_array` around it), the tie
     chain in `fitter_to_model_params_array` (about 3 lines), WCSAxes `grid(which='minor')`. New: WCSAxes' guard for
     an all-NaN coordinate range (2 lines; it retires `_world`'s time clip).
   - fiasco: the skip-name substring check (1 line, citing the user's issue #482).
   - dkist: `Unravel` on N-d input and a NaN index (about 6 lines), `target` proxied on `DKISTFileManager` (1 line), a
     resolved `files.basepath` (1 line, on #366), and `sanitize_index` taking a non-finite frame index as off the
     table (about 3 lines, or in the #762 successor).
3. **Medium PRs:**
   - glue sessions: `LinkSameWithUnits`, Quantity and `preferred_cmap` savers, the `stretch_global=False` restore crash
     and lost `stretch_parameters`, `DerivedComponent.units` (glue-solar's units are lost in sessions today), a -TAB
     WCS saver, the path slicer's savers.
   - glue's image artists (crosshairs, the Pixel point; upstream #2054): about 120 lines of `glue_patches.py`.
   - glue's profiles and statistics: cached-profile y limits (R14), native-dtype reductions (R21: 435 MiB for a
     92 MiB float32 cube), padded slice-subset results, row-wise sampling (R32); then the link manager's index by input
     cid (R6, R24).
   - glue-qt keys by `isinstance`, matplotlib's keys off the canvas, slider coalescing while dragging (R16), a closed
     viewer's dashboard widgets deleted (removed data stays alive today).
   - astropy, in this order after the two above:
     - a -TAB `axis_correlation_matrix` from the tables (about 15 lines).
     - WCSAxes tick placement: a memo, then batched calls (R5: still 37 WCS calls per unchanged redraw on main).
     - io.fits reading `conf.strip_header_whitespace` once per header, not at each card (82% of a header walk; 18% of
       irispy main's raster read).
     - viewing a `decompress_in_memory` buffer instead of copying it (D95's 3x peak). This is small if the data may
       be read-only, medium if they must stay writeable.
   - dkist, first of dkist's: a human-written successor to the closed #762 (a vectorised `VaryingCelestialTransform`,
     rebased on main, on dkist#279). It fixes R33, the shared model's thread race and the NaN cast, and halves R34. Then
     a cached per-frame inverse for the rest of R34.
   - irispy's one tabular WCS and one header dict per raster file is done upstream (#335, #341).
4. **Reports, not PRs** (30, mostly astropy and WCSLIB):
   - the SST -TAB `w.celestial` SIGSEGV
   - WCSAxes on one- and three-coordinate views, zero-size axes and unpickling
   - `parallel_fit_dask` resending every start array with each chunk
   - echo's combo match, mpl-scatter-density's resize hold
   - astropy.modeling's per-call overhead, as a comment on #6161 (R37)
   - a glue hook giving WCSAxes the shown frame's 2-D WCS (R36)
   - new: world axes by `axis_correlation_matrix`, as a comment on glue#2574; glue's layer buffer spanning the whole
     view (draft ready) and its equal-depth link paths; a comment on dkist #226 (whole-file reads, draft ready); pytest
     9.2's `monkeypatch` undo (a comment on #15287) and `approx` with None (a regression from #14647)
   - and the rest in the sections.
5. **Generic glue-solar features glue users would want**, after the above and on the user's call:
   - the Fit tab's model builder (about 330 lines, with its Save/Open)
   - Loop's range options (about 80), Blink (about 100), Follow/lock as a hover mode of glue's Pixel tool (about 90),
     keys (about 75)
   - Save frames or movie (170), Save profiles (34), a path's vertices typed in (19)
   - smaller tools: per-frame limits, the color bar, the wavelength band, physical aspect, Measure, gamma stretches.
   - new: a spanning-set autolinker (a star per compatible group; glue-core #80), and the DKIST mosaic's fitted tile
     WCSes, as a comment on dkist's draft #343 (`reproject_vbi`).

   Hide axes is glue#2128 (open). Some wait on glue-qt#72 (subtool menus) and glue-qt#73 (lines; glue#2603 is in
   glue-core 1.28.0).

## Glue-solar changes now

- **Gate `glue_patches.sync_sliders_from_state`** (653-684): it is always on, with no probe. Give it a `_needs` probe
  or a version gate before glue-qt's fix is released (glue-qt row 45).
- **Add register rows** for the edit subset kept through a tree rebuild (`quicklook._Application.__setgluestate__`,
  `_new_group`, the light curves; glue-qt row 46), dkist's private `target` read (`sources/dkist.py:758-761`, or a
  clause in the `_Files` row; dkist row 8) and the absolute path before `dkist.load_dataset` (`sources/dkist.py:932`;
  dkist row 10).
- **Correct register rows:**
  - The DKIST axis-order row (and D102) names a glue fork branch for world axes by `axis_correlation_matrix`. None
    exists: the route is a comment on glue#2574 (glue-core #77).
  - "dkist's inverse given raveled 1-D values" says dkist 1.17. The fault is the same on 1.18.1 and main (dkist row 6).
- **Release WAITs to track** (in the plan's `wp0-release-tracking`):
  - A dkist release with #765: drop `_off_frames` (`iris.py:170-187`, `:316-319`) and DKIST's NotImplementedError path
    (`sources/dkist.py:264-270`). With #764 in it, change `_world`'s off test to the raveled index against the time
    table (dkist row 9).
  - An irispy pin past fb7552f (#320): drop the `FitInfoSubset` dict conversion (`fit_maps.py:209-213`). Past d377c27
    (#335, #341), the raster read is about twice as fast, with nothing to drop.
  - A pytest release fixing #15287 (any of #15100, #15118, #15136): `test_dkist.py:354-356` and `test_quicklook.py:582`
    go back to `monkeypatch.setattr(settings, ...)` (others row 48).

Done since 2026-10-21:
- #372 follows glue-core 1.28.0 and dropped `conftest.py:21-24`'s `CFG_DIR` lines (glue-core #68).
- #382 floors every dependency at its latest release (D104), astropy 8.0.2 and dkist 1.18.1 among them.
- The register has its row for the gzipped raster's single in-memory open, and the plan's Versions line says irispy
  #182 was closed unmerged.

Done before:
- glue-solar follows irispy #256's dust detection (#327).
- #329 dropped the gzip-to-bytes step in `loaders/iris.py`: irispy reads a `.gz` once itself (the plan's
  `wp10-l-gzip-from-irispy`).
- glue-solar follows irispy #257, #258 and #260 (`residual=False`, `active_mask`).
- The plan's upstream items are folded into this review (`wp0-upstream`). That drops the stale entries:
  `translate_pixel`'s bare `Exception`, the two WCSAxes cases that did not reproduce, and irispy's `py314-devdeps`
  failure.

## Keep in glue-solar

Eighteen items:
- solar and IRIS features: the quicklook recipe, the last-session keeper, the Doppler unit converter, the mouse-over
  readout's ticks
- the user's decisions: D67's SST inverse, D70's sampling, D73's lock wrappers until astropy#19174 is fixed
- since 2026-10-21: the gzipped raster's single in-memory open, D96's Mg II k and h names, and the private `rng_mode`
  read until glue-qt has a public one
- new since 2026-10-28: DKIST rules (the color-limit sample of whole present frames, one for a mosaic's tiles; the
  session record re-read through the load log; the mosaic's fitted tile WCSes, D108; `_world`'s clamp at the Ravel
  ends until astropy's guard), and the SST page hints (D100)

Their rows say why. Some rows keep a part while the rest goes upstream, such as the velocity wording of the Doppler axis
label (glue-core #25).
