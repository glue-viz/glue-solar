# Upstream review (D89)

What glue-solar should send upstream, report, keep or drop. Every row was re-verified on 2026-10-19 and refreshed on
2026-10-21 and 2026-10-28 against the latest releases and mains: glue-core 1.28.0 (= main 3683f07c), glue-qt 0.4.2
and main 9780eaf9, astropy 8.0.2 and main e91800f (WCSLIB 8.10), irispy 134c299, dkist 2a4b15b, gwcs 7f7e664, fiasco
a3445e0 and pytest a7b2446 (echo, mpl-scatter-density and reproject unchanged), with glue-solar at 6072b60. Every
fault was reproduced on both the release and main, or the row says why not. Nothing has been refreshed since: check a
row against the current main before acting on it. Seen on 2026-11-18, without re-verifying any row: dkist 1.19.0
(with #764 and #765), astropy 8.0.3 (still WCSLIB 8.6), echo 0.17.0, numpy 2.5.5 and PyQt6 6.12.1 are out; glue-qt
main has #65, #72 and test fixes; glue main is unchanged; irispy #360 was closed for #368.

The detail is in four sections, one table row per item with its re-verification, upstream status, recommendation and
the glue-solar code it retires (where each patch stands as a PR is in [UPSTREAM_TRACKER.md](UPSTREAM_TRACKER.md)): [glue-core](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-core.md) (86 items),
[glue-qt](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/glue-qt.md) (46),
[astropy, WCSLIB, irispy and the rest](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/others.md) (46) and
[dkist, gwcs and asdf](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/dkist.md) (10, new). Their reproducers are in the
folders beside them (the sections name them by their scratch paths; the files are the same). The brief the reviewers
followed is [BRIEF.md](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/BRIEF.md).

For the performance findings (R1-R37) the tables give what, where and the fork branch;
[performance-detail.md](IRIS_PLAN_PROTOTYPES/upstream_review_20261019/performance-detail.md) gives the approach and the
measurement that argues for each, and the plan for the four astropy WCSAxes PRs.

## In numbers

| Recommendation | glue-core | glue-qt | others | dkist | All |
| --- | --- | --- | --- | --- | --- |
| UPSTREAM-PR | 62 | 34 | 11 | 7 | 114 |
| REPORT | 6 | 5 | 18 | 1 | 30 |
| WAIT | 7 | 3 | 3 | 1 | 14 |
| KEEP | 7 | 4 | 6 | 1 | 18 |
| DROP | 2 | 0 | 8 | 0 | 10 |

glue-core also has one parked draft (#2601) and one pointer row.

No upstream release fixes any glue-core or glue-qt fault in the register (2026-11-18, not re-verified row by row).

## Order to upstream

1. **The fork branches already built and the live drafts:** [UPSTREAM_TRACKER.md](UPSTREAM_TRACKER.md) lists each as
   the PR it is or should become, in the order to open them, with what is left to do before opening, and the
   issue and comment texts still to post (among them the astropy#19174 comment, on which every glue-solar WCS
   lock waits).
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

   Hide axes is glue#2128 (open). Some wait on glue-qt#72 (subtool menus; merged 2026-11-13, unreleased) and
   glue-qt#73 (lines; glue#2603 is in glue-core 1.28.0).

## From irispy #360's profile (2026-10-29)

Drafts in `IRIS_PLAN_PROTOTYPES/upstream_drafts_20261029/reports/perf360-*.md` (reproducers run on the latest releases; mains read
from source): filelock 4.2.4's import-time audit hook makes every `id()`, so every deepcopy step, call Python (an
issue: install it at the first lock; #652 added it); ndcube's `_NDMetaSlicer` deep-copies the whole meta on each
slice (a PR branch on the user's fork, `ndmeta-slice-shallow-copy`, and an issue; #815); gwcs's `WCS(model)` always copies the model (an issue: a copy
option or the steps form, which shares the caller's model); astropy.io.fits reads its config at every card (a PR branch on the user's fork,
`fits-card-config-reads`, ref #12504; its side finding, the record-valued keyword setting ignored for parsed cards, an
issue draft).

## Candidates from the code review (2026-11-11)

Found while reviewing main at c930a4a (CODE_REVIEW.md). None is a row of the section tables yet, and none was checked
against the upstream mains: do that first, then give each a row.

- **glue-qt:**
  - A plain tool ends the active mouse mode (`tools._keep_mouse_mode` turns it back on, twelve uses). Report.
  - Subtool menus: `tools._ToolMenu` writes its entries into `toolbar.tools` and `toolbar.actions` and adds its own
    shortcuts. Route: glue-qt#72.
  - `LayerAction.update_enabled` runs only on a change of selection, not after an action
    (`glue_patches.refresh_layer_actions`). Small PR.
  - A slider move resets an `AggregateSlice` (`tools.BandTool`'s `slices` validator); with the list's "a slider move
    turning a Collapse into an int".
  - `matplotlib`'s `canvas.manager` set to None for saved frames (`tools.SaveSequenceTool`), `layer_action.members`
    sorted in place and `python_export` imported early to list "save:python" once (`__init__.py`). Check each.
  - An empty Collapse range is made by `ProfileTools._on_collapse` (glue-qt), so its fix belongs there; glue-solar's
    probe, `needs_empty_collapse_workaround`, tests glue-core and will not see it: remove the patch by hand then.
  - Order for the Fit tab branches: a glue-qt release with `fitter-settings` (`ProfileTools._get_fitter`) but
    without `fitter-settings-widget` makes glue-solar's Settings edit another fitter than fits use
    (`glue_patches._on_settings`). Land both in one release; otherwise update `_on_settings` when that release is out (D113).
- **glue-core:**
  - `ApplySubsetState.undo` deletes every subset made since the command, not only those it made. Not reported yet.
  - Per-frame limits (`stretch_global=False`) raise IndexError for layers of another shape
    (`tools.PerFrameLimitsTool._whole_cube_again`); with the medium PR on its restore.
  - No public way to tell a Profile viewer its x unit conversion changed: `lines.VelocityTool._rest_changed` sets
    the private `_previous_x_att` and calls `_update_x_display_unit_choices` and `_reset_x_limits`. Report.
  - A broadcast component is saved at full size (R20): `loaders.iris._BroadcastComponent` replaces the saver. With
    the sessions PR.
  - The path crosshair sets every other slider of a 4-D or 5-D parent to the diagram's y index, and takes x as the
    path index on a transposed diagram; glue-solar's `PathCrosshairTool` copies it on purpose. Report.
  - A Profile viewer takes NaN x limits from a world axis of NaN (`glue_patches._reset_x_limits`, on
    `follow-irispy-main`). Report.
- **astropy:** the IRIS `_GlueWCS.pixel_to_world_values` memo is the same stopgap as DKIST's for others row 5 (the
  WCSAxes memo); it retires with that PR.
- **irispy:**
  - Private names glue-solar imports: `utils.bursts._SI_IV` and `utils.mg_features._REST_WAVELENGTH`. Ask for public
    constants (`_SI_IV` could use `get_lines(main_only=True)`; `_REST_WAVELENGTH` differs from the catalog by about
    0.001 Å).

## Glue-solar changes now

- **Release WAITs to track** (in the plan's `wp0-release-tracking`):
  - An irispy pin past fb7552f (#320): drop the `FitInfoSubset` dict conversion (`fit_maps.py:209-213`). Past d377c27
    (#335, #341), the raster read is about twice as fast, with nothing to drop.
  - A pytest release fixing #15287 (any of #15100, #15118, #15136): `test_dkist.py:354-356` and `test_quicklook.py:582`
    go back to `monkeypatch.setattr(settings, ...)` (others row 48).

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
