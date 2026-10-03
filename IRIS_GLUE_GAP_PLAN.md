# IRIS and Glue work plan

This plan drives glue-solar, with the irispy and glue work it needs, toward an IRIS quicklook in Glue covering what SolarSoft's CRISPEX offers; each item names the CRISPEX features (F001-F203) it serves. The plan and `IRIS_PLAN_PROTOTYPES/` live on glue-solar's pushed branch `plan`, never merged or opened as a PR, and it lists open work only. Each item is one glue-solar PR on a branch from `main` without the plan or prototypes, opened as a draft and marked ready and merged once CI passes (user, 2026-09-30); irispy, glue, glue-qt and astropy work stays drafts or the user's fork, on the user's direction.

## How to use this plan

- Start at [Current state](#current-state-2026-10-01) and refresh PR states with `gh`.
- Pick an open item in the earliest open milestone; read its done-when and Depends.
- Trace the code on `main` before writing or porting a prototype; this plan overrides prototypes.
- Stage named files only.
- When an item's PR merges, delete the item and its key from other items' Depends and the checklist; the PR and git history keep the record, so Current state gets no line. Say "on main", not "released".

## Scope

In scope:

- The CRISPEX and IRIS-SolarSoft features from the user's 2026-09-30 review: 'keep' ones are M1 to M3 items (fitting M4), 'later' ones L items, and those already on main or in Glue have none (the feature map and earlier plan text are in this branch's git history).
- CRISPEX (and `iris_xfiles` for discovery) is the behaviour reference; it has no licence, so no code is ported.
- Features only other missions need come last ([WP13](#wp13-other-missions)).

Out of scope:

- Level-3 FITS writing (F188), EIS (F019, F048), the detector mosaic (F123, needs Level 1), and OBS XML and pipeline-log viewers (F042, F043).
- The IRIS-9 tutorial and its event-finding workflow (F093), and online context and search (GOES, AIA, HMI, SWPC, HCR, IRIS search: F016-F018, F041, F044-F047).
- AIA reference panels, reference spectra and AIA blink (F103, F107; second IRIS windows are `wp4-m1-multi-window`): AIA and Hinode cubes are imaging only, like SJIs.
- PostScript, IDL and legacy CRISPEX formats (F189): images export in normal formats, derived data as FITS or ASDF.
- SST-only inputs (F023, F028, F029, F129) and IDL details Glue replaces.

## Current state, 2026-10-02

**Resume here.** M0 is done. Main is at aafc4ba (#107-#115; the IRIS guide is three pages: loading, `iris-quicklook`, `viewer-tools-and-windows`); glue-solar PRs are marked ready and merged once CI passes. No PR is open. In progress: `wp10-m1-roi-world-polygon` (worktree `~/Git/glue-solar-wp10-m1-roi-world-polygon`, D38's new-subset regions), being rebased onto #115. Verifying irispy main 0ee8fad (#207) for glue-solar is in progress.

**Next.** The profiling survey's upstream findings are the M4 `wp0-perf-*` items (every finding in `GLUE_SPEED.md`, scripts in `IRIS_PLAN_PROTOTYPES/perf_survey_20261001.tar.gz` and `wcsaxes_study_20261001.tar.gz`). The matplotlib-free WCSAxes core prototype is on the user's astropy fork only, for the user to raise in person (GLUE_SPEED.md 'Matplotlib-free core prototype'; scripts and design in `IRIS_PLAN_PROTOTYPES/wcsaxes_core_20261001.tar.gz`); no PR, issue or upstream notice.

**Releases.** glue-core 1.27.0, glue-qt 0.4.2, irispy-lmsal 0.9.1 (all fixes glue-solar needs). irispy main (57813b8, unreleased) has #197 (UV bursts), #198 (wavelength drift), #199 (Mg II features), #201 (moment uncertainties), #205 and #206 (both fill codes masked, memmap SJIs keep raw fill, one gunzip); glue-solar passes against it since #112, but its lazy opens regress (`wp0-irispy-requests`). Awaited: astropy 8.0.2, with a WCSAxes tick-crossing fix for rolled views (`wp0-release-tracking`).

**Worktrees.** `~/Git/glue-solar` (this plan); `~/Git/glue-solar-accept`, a detached main checkout the acceptance probe runs against; irispy ports `~/Git/irispy-bursts`, `-wavecorr`, `-mg-features`, `-moments-uncertainty`, merged and removable (the `irispy-ports` env imports `irispy-bursts`); upstream speed fixes in `~/Git/glue-perf-*`, `~/Git/glue-qt-perf-*` and `~/Git/astropy-perf-a1-wcsaxes-pytest-import` (WP0 notes); `~/Git/glue-solar-main` is a stale detached checkout (2fdb847), removable. WCSAxes core: clone `~/Git/astropy-wcsaxes-core` (branches `wcsaxes-layout-core` and `-demos`, remote `fork` = the user's astropy fork, upstream push disabled), env `astropy-wcsaxes-core` (editable astropy from that clone), demos history in `~/Git/wcsaxes-core-demos`. Never touch `~/Git/astropy`, the user's own checkout.

## Decisions

Settled by the user; reopen only with the user.

- **D1:** Keep `link_hpc`, the only exact per-frame spatial link between IRIS datasets (glue #2595's use frame 0). Pair by physical type; no SJI world-time link; no equal-hop paths with different values.
- **D2:** Build in glue-solar and irispy first via glue's public registries; nothing waits for an upstream release; upstream work is M4, on the user's direction. Workarounds switch on a behaviour probe, never a version.
- **D3:** Arcsec and Angstrom on `_GlueWCS` IRIS data. sunpy Maps keep glue's plain astropy WCS, so glue autolinks and saves them; `link_hpc` links them to IRIS data.
- **D4:** Analysis products are dataset `layer_action`s adding Data and links without a viewer; derived maps use `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`. A product that is a per-sample expression of one dataset (DN/s, radiometric calibration) is a glue derived component instead (user, 2026-09-30).
- **D5:** Baseline: released glue-core 1.27.0, glue-qt 0.4.2, irispy-lmsal 0.9.1.
- **D6:** Selection is the stock Pixel tool plus Clear point; M1 adds hover-follow with click-to-lock.
- **D7:** The point is a fixed detector pixel; time is an index axis with timestamp readouts. Nearest exposure, ties earlier; no match (greyed, never clamped) past half the partner's median cadence or outside its coverage. The raster is the default time master.
- **D8:** The coordinator moves sliders from 1-D nearest-index arrays and adds no glue links: no pixel-component, `JoinLink`, lambda or closure links.
- **D9:** One `Coordinator` per DataCollection behind the registered `solar:coordinate` tool; restored viewers re-register; never wrap `app.new_data_viewer`; menus use `SimpleToolMenu`.
- **D10:** Negative-step rasters keep irispy's orientation; `revert_v34=True` is the documented alternative.
- **D11:** Rest wavelength: explicit override, else the packaged vacuum line list, else none (none for multi-line windows, no km/s for continuum, never TWAVE); float Å in `meta['rest_wavelength']`, read through the WP5 helper.
- **D12:** -200 and -199 are missing, in AIA cutouts too (as irispy main reads them; real cutouts hold neither, user 2026-10-02), +Inf is saturation, negatives are data; stored masks are uint8. -200 and Inf are documented (ITN 45, ITN 26); -199 is IRIS SolarSoft's convention only (`iris_make_fits_level3` v1.29 NaNs values < -198.5, `iris_raster_browser` has `missing=[-200.,-199.]`), seen in the files as raw -32764 (1905 samples in 4000255147 SJI 1400), with no header keyword naming it.
- **D13:** Sessions add the Quantity saver only if none exists, save `_GlueWCS` via `__gluestate__`, never replace glue's `VisualAttributes` serialization globally, and save added components as 1-D vectors.
- **D14:** irispy work targets LM-SAL `main`; the gWCS raster work (irispy #182) is the user's to direct.
- **D15:** The quicklook is an MDI tab with explicit viewer geometry.
- **D16:** Doppler is red minus blue, I(λ0 + Δ) − I(λ0 − Δ), positive for redshift, in `meta['doppler_sign']`.
- **D17:** Missing data are NaN; no sentinel values.
- **D18:** Do not re-implement glue: configure, default, document or call glue's API first.
- **D19:** Each quicklook tab has its own Point group, and its point drives only its own panels; a Pixel click on its slit-jaw image moves the point to the raster pixel there (#114), and only a click on a viewer showing the frame axis stays a slit-jaw point.
- **D20:** `link_hpc` links every dataset to the first (a star); 'Open quicklook' starts ticked and the browser skips glue's autolinker.
- **D21:** A NO MATCH readout gives the nearest frame's offset; a follower moved by hand shows its own, greyed beyond half a cadence.
- **D22:** After Clear point a scanning raster's time stays at the last point's step, while a sit-and-stare's exposure slider and a stack map's scan slider keep driving the time. Under a slit-jaw master the master rules: while there is a point, a hand-moved raster exposure or scan, or a click on another, snaps back, and a hand-moved slit-jaw follower keeps its frame until the next sync.
- **D23:** A thin point line on the spectrogram and λ–t panels comes with `wp4-m1-spectral-coupling`.
- **D24:** Moments and red-blue dialogs take a typed line centre until the Later line list (`wp5-m1-line-list`).
- **D25:** Sessions are Later: the Profile display-unit restore patch (`wp0-core-profile-restore-priority`) goes with them, and sessions re-read IRIS files through glue's load log.
- **D26:** The Hinode/SOT reader is its own Later item (`wp8-sot-cubes`); `wp1-m3-multi-instrument` is Other missions with Level-3 input.
- **D27:** The Later time marker is glue's own range subset (`wp12-time-marker`).
- **D29:** Every Image viewer of a sit-and-stare raster shows the exposure label and integer exposure ticks only, with no helioprojective ticks on the far edge.
- **D30:** 'Hide axes' hides the whole axes, with no pixel-coordinate ticks instead, since the mouse-over readout keeps world coordinates. On rolled views each axis label stays with its own coordinate's ticks (glue-solar's label patch), not glue's spine-based labels.
- **D31:** IRIS world values reach glue in Å and arcsec, high-level objects included; their texts keep glue's and WCSAxes' precision (the mouse-over readout gives IRIS Å and arcsec at a fixed precision, #109); -TAB round trips hold to the wrapped WCS's own error (1.3-2.7e-6 px); a longitude or latitude beside a non-angle coordinate that barely changes across a panel loses its tick labels, while an image of the two angles alone keeps both (user, 2026-10-01).
- **D32:** Lazy loading (design synthesis in `IRIS_PLAN_PROTOTYPES/wp10_lazy_design_20261001.tar.gz`): raw int16 through irispy's memmap view, with a plane reader as the swap point if SIGBUS or resident memory while viewing bite; gzipped SJIs held as raw int16 in RAM; the mask is a glue derived component; the quicklook's spectrum never computes whole-cube profiles; the lazy loaders raise the open-file soft limit.
- **D33:** Lazy colour limits come from an exact count of raw codes over up to 512 MiB of planes per window, within 1 % of the eager 99.5 % limits. The < 10 % memory budget is the peak RSS increase over the post-import baseline with no viewer, the absolute peak reported beside it; the per-element memory budgets are tracemalloc figures, and resident memory is `wp10-l-resident-memory`.
- **D34:** The GitHub wiki stays off rather than refreshed; its history, with the user's 2026-09-22 edit, is `IRIS_PLAN_PROTOTYPES/glue-solar-wiki-20261001.bundle`.
- **D35:** glue-solar registers only the IRIS and AIA colormaps (since #98) until glue-qt's colormap combo stops re-rendering every icon; the user wants every sunpy colormap back then, through `wp11-l-all-colormaps` or the upstream fix in `wp0-perf-qt` (2026-10-01).
- **D38:** User (2026-10-02, batch 4): 'Go to UTC' moves the observation's time master, whichever viewer it is typed in, and the followers follow; region tools on a quicklook's raster panels make a new subset and leave the Point as it was; the Point window sits inside the quicklook tab under its panels; a slit-jaw click beside a sit-and-stare slit takes the level row at any distance, and one click is one undoable assignment; Redo after Undo of a slit-jaw click is documented until `wp4-l-redo-sji-click`.
- **D37:** Provisional (2026-10-02, batch 3): `link_hpc` anchors on the first IRIS dataset and links helioprojective maps to it with `LinkSameWithUnits` (IRIS pairs keep `LinkSame`), so value selections between two maps pass through IRIS and ignore their observers, documented; `_GlueWCS` wraps a map's 0-360° longitudes back to the raster's; `sji_to_raster` applies D7's half-cadence limit on sit-and-stare rasters only, never to a stack's scans; the readout gives fixed precision only for IRIS Å and helioprojective arcsec, and drops the angle along a sit-and-stare exposure axis; 'Regrid on time' regrids a stack by scans timed at their middle step, keeps real exposure times in `Time`, and includes exactly 0.75 steps.
- **D36:** The observation browser's background load (#106) covers the quicklook too (colour-limit counts for the datasets it will show on the worker, an event-loop turn between its viewers) and moves archive extraction to the worker; Stop keeps the picks read in full while Esc or closing drops the load; a gzipped SJI is decompressed once; every raster file is read on its own so a stop acts between files (user, 2026-10-02); what Stop keeps is still counted on the worker, a result 0.15-0.2 s later rather than a 0.4 s freeze as its first viewer opens (provisional, 2026-10-02; design and measurements in `IRIS_PLAN_PROTOTYPES/wp10_nonblocking_design_20261002.tar.gz`).

## Milestones

A milestone is done when it has no items left.

- **M1: navigation and spectral parity.** SJI to raster, hover-lock, spectral coupling, multi-window, blink, time controls, overlays, readouts, non-blocking load.
- **M2: analysis, display and export.** Moments, colour bar, distance and zoom, image and movie export, path slicer.
- **M3: specialist.** Stack WCS, pointing, calibration, Mg II, density and temperature, red-blue maps, reference blink, AIA context cubes (low priority).
- **L: Later.** Deferred by the user (sessions, browser search, light curves); revisit after M3; not a gate.
- **M4: upstreaming.** After M3, on the user's direction: upstream PRs, reports and the user's drafts, autolink matrix, fit tool; a release with a fix retires its workaround.
- **OM: Other missions.** Last: WP13 and `wp8-m3-level3-input`.

### Checklist by milestone

**M1**
- WP0: `wp0-release-tracking`, `wp0-irispy-requests`
- WP4: `wp4-m1-hover-lock-tool`, `wp4-m1-spectral-coupling`, `wp4-m1-multi-window`, `wp4-raster-overlays`
- WP5: `wp5-m1-spectral-blink`
- WP9: `wp9-m1-screenshots`
- WP10: `wp10-m1-roi-world-polygon`, `wp10-m1-canvas-teardown`
- WP11: `wp11-keyboard-shortcuts`

**M2**
- WP2: `wp2-m2-moment-maps`, `wp2-m2-line-definition`, `wp2-m2-input-quality`, `wp2-m2-tests-docs`
- WP11: `wp11-colourbar`, `wp11-distance-measure`, `wp11-zoom-steps`
- WP12: `wp12-sequence-export`, `wp12-path-slicer`

**M3**
- WP1: `wp1-stack-per-scan-wcs`, `wp1-nexp-prp`, `wp1-m3-pointing-offset`
- WP2: `wp2-m3-moments-extensions`, `wp2-m3-window-data`, `wp2-irispy-calibration-actions`, `wp2-m3-mg-features`, `wp2-m3-density-temperature`, `wp2-m3-red-blue`
- WP4: `wp4-playback-extras`
- WP5: `wp5-m3-rest-from-measurement`, `wp5-m3-reference-blink`, `wp5-m3-mean-spectrum-compare`
- WP8: `wp8-m3-context-cubes`
- WP9: `wp9-m3-saturation-recipe`, `wp9-m3-spectral-recipes`, `wp9-m3-shortcuts-help`
- WP11: `wp11-band-average`, `wp11-north-up`
- WP12: `wp12-export-annotations`, `wp12-path-overlays-slopes`, `wp12-path-batch`

**Later**
- WP0: `wp0-core-profile-restore-priority`, `wp0-qt68-macos-pass`
- WP2: `wp2-burst-detection`
- WP3: `wp3-style-cmap`, `wp3-wcs-saver`, `wp3-quantity-meta`, `wp3-file-references`, `wp3-session-budget`, `wp3-coordination-reattach`, `wp3-app-session-acceptance`, `wp3-last-session`
- WP4: `wp4-l-redo-sji-click`, `wp4-profile-aggregation`
- WP5: `wp5-m1-line-list`, `wp5-m1-rest-wavelength-policy`, `wp5-m1-velocity-axis`, `wp5-m1-doppler-image`
- WP8: `wp8-filter-stop`, `wp8-text-filter`, `wp8-prescan-search`, `wp8-search-ui`, `wp8-browser-conveniences`, `wp8-browser-metadata`, `wp8-sot-cubes`
- WP9: `wp9-l-deferred-recipes`
- WP10: `wp10-m3-sit-stare-chunks`, `wp10-l-resident-memory`
- WP11: `wp11-l-all-colormaps`, `wp11-scaling-extras`
- WP12: `wp12-derived-data-export`, `wp12-date-labels`, `wp12-time-marker`, `wp12-point-light-curves`, `wp12-path-persist`, `wp12-saved-path-reuse`, `wp12-profile-values-export`, `wp12-export-options`

**M4**
- WP0: `wp0-core-image-artist-bugs`, `wp0-qt-large-data-cancel`, `wp0-astropy-19174`, `wp0-stack-validation`, `wp0-user-review`, `wp0-own-draft-updates`, `wp0-core-quantity-saver`, `wp0-core-derived-units`, `wp0-track-line-layers`, `wp0-qt-aggregate-slice`, `wp0-track-qt66`, `wp0-core-datetime-export`, `wp0-qt68-cocoa`, `wp0-core-session-reports`, `wp0-report-candidates`, `wp0-optional-proposals`, `wp0-perf-core-draw`, `wp0-astropy-wcsaxes-bugs`, `wp0-perf-core-links`, `wp0-perf-core-stats-io`, `wp0-perf-qt`, `wp0-perf-astropy-irispy`
- WP1: `wp1-m4-autolink-matrix`
- WP6: `wp6-glue-fit-tool`
- WP9: `wp9-m4-release-updates`

**Other missions**
- WP1: `wp1-m3-multi-instrument`
- WP8: `wp8-m3-level3-input`
- WP13: `wp13-stokes`, `wp13-solarnet-tab-wcs`, `wp13-height-cubes`

## Work packages

### WP0: Upstream integration and reports

Upstream work in glue, glue-qt, irispy and astropy that retires the workarounds in `glue_solar/glue_patches.py`.

**M1**

- [ ] **M1** `wp0-release-tracking`: After each glue-core, glue-qt, irispy or astropy release past 1.27.0/0.4.2/0.9.1, raise floors and retire workarounds. astropy 8.0.2 carries the backport of a WCSAxes fix (merged on main 2026-09-11) for a wrong value at a second tick crossing of an arcsec longitude on one spine, which rolled IRIS views can show on 8.0.1: on its release, move D5's baseline and the `iris-plan` envs to it and check a rolled SJI. At the irispy release with #206, also correct the comments and docs that describe 0.9.1's mask and SJI zeroing (`sources/loaders/iris.py`'s "irispy masks only -200" and `_image_cube_data` docstring, `stack_spectrograms.py`, `test_importer.py`'s "irispy masks only -200", `docs/dev_guide/loader-customization.rst`). Done when each release has a line here naming its PRs, floors and retired workarounds.
- [ ] **M1** `wp0-irispy-requests`: Get irispy's merged #197-#199, #201, #205 and #206 released (0.10.0; changelog fragments in place) and settle the irispy-side checks (exposure times, rolled-SJI gWCS, binned `slit x position`, per-step pointing). Done when a release has them and each check has a test or user decision. Before that release (2026-10-02, measured, `IRIS_PLAN_PROTOTYPES/irispy_main_check_20261002.tar.gz`): #206's memmap fill mask (`np.isin` at `io/spectrograph.py:257-259`, `io/sji.py:256-257`) reads every value at open, so a lazy open of 4000255147 goes 0.12 → 1.46 s and +3.5 GB RSS (3824262996 0.08 → 1.09 s, +2.7 GB); fix with no mask or a lazy (dask) one under memmap, two int16 `==` compares rather than float `np.isin`; #206 also broke irispy's remote `test_sji_first_frames_match_idl`. If 0.10.0 ships the full read, cap irispy below it.

**L**

- [ ] **L** `wp0-core-profile-restore-priority`: Gated `setup()` wrapper so restored spectrum panels do not raise ValueError on core 1.27.0. Done when a cube with its spectral axis off axis 0 restores.
- [ ] **L** `wp0-qt68-macos-pass` (F203): Manual macOS check of glue-qt #68 (font, menus, Cmd-Tab, Dock name). Done when PyQt6 and PyQt5 results are recorded.

**M4**

- [ ] **M4** `wp0-core-image-artist-bugs`: Core PR: a hidden Pixel crosshair reappears at (0, 0), and `translate_pixel` raises a bare `Exception`. Done when both reproducers pass on a release.
- [ ] **M4** `wp0-qt-large-data-cancel`: glue-qt report: cancelling the 'Add large data set?' modal breaks later viewers. Done when filed or declined.
- [ ] **M4** `wp0-astropy-19174`: Add the IRIS -TAB WCS thread crash to astropy#19174. Done when reproduced without `WCS_LOCK` and posted or declined.
- [ ] **M4** `wp0-stack-validation`: Merge the upstream heads (core #2595, #2597-#2599, #2601; Qt #70, #74, #75) and run the Qt and `glue_solar` suites. They are the user's drafts: core #2595 WCS autolink, #2597 session cmap and meta, #2598 correlated-axis inverse, #2599 datetime epoch (fix its codestyle), #2601 Profile WCSAxes (contains #2596, Slice profile); Qt #70 Profile sliders and km/s axis, #74 cursor readout, #75 time slider labels. Done when pass counts are recorded.
- [ ] **M4** `wp0-user-review`: The user reviews each upstream draft before it is ready; glue-qt #68 (macOS integration) and #69 (a CI fix overlapping #65) are ready, and glue PRs fail `py311-test-visual` until dhomeier's ready glue #2592 (visual references) merges. Done when each is merged, closed or parked. Depends: wp0-stack-validation.
- [ ] **M4** `wp0-own-draft-updates`: Amend #2595 to keep time axes out of `wcs_autolink`, and Qt #74 to show Solar X/Y. Done when both pass their suites.
- [ ] **M4** `wp0-core-quantity-saver`: Core `u.Quantity` saver (D13) that loads glue-solar's fallback record. Done when its test round-trips Quantities in `Data.meta`.
- [ ] **M4** `wp0-core-derived-units`: Core PR saving `DerivedComponent.units`. Done when its test round-trips `units='DN/s'` and older records still load.
- [ ] **M4** `wp0-track-line-layers`: Track glue #2603 and glue-qt #73, which retire WP5's line-list workaround. Done when both are released or the user parks them.
- [ ] **M4** `wp0-qt-aggregate-slice`: glue-qt report and PR: a slider move turns a Profile Collapse `AggregateSlice` into an int. Done when filed or declined.
- [ ] **M4** `wp0-track-qt66`: Track astrofrog's draft glue-qt #66 (generic `path_slicer`) and others' ready glue-qt #72 (subtool enabling), which WP12 builds on. Done when each is merged before WP12 starts or its author is asked.
- [ ] **M4** `wp0-core-datetime-export`: Report that core's exporters fail on datetime64 components (HDF5, FITS, VOTable raise; CSV writes int64). Done when filed or declined.
- [ ] **M4** `wp0-qt68-cocoa`: Once glue-qt releases #68, check conda-forge's glue-qt requires `pyobjc-framework-cocoa` on macOS. Done when checked or requested.
- [ ] **M4** `wp0-core-session-reports`: Report the 1.27.0 session-restore failures (`stretch_global=False`, lost `stretch_parameters`, sunpy colormap names, object-array meta, `LinkSameWithUnits`). Done when each is filed or declined.
- [ ] **M4** `wp0-astropy-wcsaxes-bugs`: astropy WCSAxes bugs the 2026-10-01 WCSAxes study met on 8.0.1, unchanged by every prototype (GLUE_SPEED.md 'Stock astropy problems found on the way'): `format_coord` raises on a 1-D WCSAxes; line grids, `plot_coord` and `scatter_coord` fail on three-coordinate views such as both Si IV panels; automatic ('#') label positions raise with a sliced-out coordinate; `simplify_labels` raises on a swapped cube; an off-view tickable gridline raises; zero-size axes raise on draw; a WCSAxes figure cannot be unpickled. Check whether glue-solar hits any (a minimised quicklook panel may reach zero size) and work around those here; re-check the rest on astropy main and report on the user's direction. Done when each is worked around, filed or declined.
- [ ] **M4** `wp0-report-candidates`: Other reports, filed only on the user's direction. Done when each is filed or declined.
  - core `PathSlicedData` crashes on IRIS data (`world_axis_names` per kept pixel axis) and has generic gaps: 3-D-only enable, zeros not NaN, datetime cast, no session saver.
  - core dask percentile sampling reads only chunk corners.
  - glue-qt ignores Fit constraints; its playback timer outlives the viewer, and keeps running when the sliders are rebuilt for new data or axes.
  - Still open on irispy main (57813b8): `verify("silentfix")` on every HDU (`io/sji.py:216`, `io/spectrograph.py:163`, `:190`; each raster file is opened twice, 198 calls for 99 files): the 99-file stack reads 0.7 s faster without it.
  - irispy's `remove_dust` and `radiometric_calibration` skip `check_scaled` (on raw int16 input `remove_dust` returns raw codes, `radiometric_calibration` −2.2e7), and `check_scaled` trusts `meta["scaled"]` over the dtype.
  - irispy's readers and burst finders treat -199 as fill, but the dust mask (`utils/utils.py:157`), `calculate_mg_features` (`mg_features.py:109`) and the wobble trim (`wobble.py:102`) still test -200 only. -199 is SolarSoft's convention, not ITN 26's (D12).
  - irispy imports `sunpy.map` at import time (`irispy/sji.py:13`, 0.43 s at the first load).
  - glue-qt keyboard shortcuts: Tab never cycles windows (Qt focus takes it), keys are looked up by exact viewer class (subclasses such as `QuicklookImageViewer` get none), Table viewer keys are registered on `DataTableModel`; the Image viewer's profile button has no tooltip.
  - glue-qt Profile Navigate and Collapse compare display-unit x with native values; Collapse drops the range's last sample, and an empty `AggregateSlice` raises when drawn.
  - glue's FITS subset-mask importer refuses unsigned integer masks.
  - glue-core 1.27.0's FITS exporter fails on any uint8 component in a subset export (`UnboundLocalError` on `blank`, `data_exporters/gridded_fits.py`), so a subset export of IRIS data with its uint8 mask crashes on main; it also writes no dask array. glue-solar's `export_fits` replaces the exporter behind a probe.
  - glue-qt's `MultiSliceWidgetHelper.sync_state_from_sliders` rewrites every slice when any slider of a viewer moves, so a Profile Collapse on one axis ends when another slider moves (the Profile guide says so).
  - astropy WCSAxes `auto_assign_coord_positions` raises `TypeError` when no consistent tick-label placement exists.
  - wcslib's -TAB inverse stops at 1e-10° (`tab.c`), so IRIS raster pixel→world→pixel holds only to about 1.3e-6 px.
  - with glue #2595, raster pixel ROIs in an SJI take #2595's frame-0 WCSLink instead of `link_hpc`'s per-frame path (shorter link chain); amend #2595 or document it.
- [ ] **M4** `wp0-optional-proposals`: Non-blocking proposals: core Profile x-label units, percentiles and interpolation; glue-qt gamma slider and playback modes; irispy NaN float rasters; astropy fitter reuse after `parallel_fit_dask`. Done when each is filed or declined.
- [ ] **M4** `wp0-perf-core-draw`: Profiling survey 2026-10-01 (every finding with its measurements, causes, fixes and scripts: `GLUE_SPEED.md`; ranked page: https://claude.ai/artifact/JgL2D9fjWp72GrXsrSx1nN), glue-core draw path, measured only. (1) `_set_wcs` on every slice change resets the axis labels through WCSAxes `set_xlabel`/`set_ylabel`, 4 eager tick placements, 66 % of an SJI frame step (105 → 39 ms with labels on the coordinate helpers); (2) subset layers that are hidden still update and redraw (−27 to −35 ms per point move, −33 % with two quicklooks); (3) a Pixel point is drawn as a full-view RGBA image (−14 to −31 ms per large redraw); (4) a collapsed map re-aggregates on every redraw (275 → 50 ms per point move); (5) float64 composite and 72-dpi FRB on large or HiDPI panels. astrofrog's draft glue #2507 speeds up slicing. Done when each is filed, merged or declined on the user's direction.
- [ ] **M4** `wp0-perf-core-links`: glue-core links, measured only. (1) A raster ROI on a linked SJI inverts the raster WCS per screen pixel once per attribute (4.8 s → 0.21 s per frame with one inversion and a footprint cull); (2) `discover_links` restarts after each link, about O(N³) (6.8 s per change at 102 datasets; 64-664× with an indexed expansion); (3) any link change drops every linked mask; (4) removing a dataset runs one update per link (30 s → 0.9 s at 53); (5) each append runs a full update with an all-pairs pixel-cid pass; (6) the WCS autolinker suggests every pair. Done when each is filed, merged or declined.
- [ ] **M4** `wp0-perf-core-stats-io`: glue-core statistics, IO and startup, measured only: the Profile y-limit reset computes whole-cube profiles on the main thread (0.4 s of quicklook open, 0.4-2.8 s freezes on Function changes); `compute_statistic` copies chunks to float64 (−34 %, 713 → 75 MiB); the Histogram builds full-cube masks for a Pixel subset; session save re-serialises everything per pass and writes broadcast components in full; arithmetic with a constant upcasts float32; startup imports IPython, scipy.optimize and dask eagerly (about 0.4 s). Done when each is filed, merged or declined.
- [ ] **M4** `wp0-perf-qt`: glue-qt, measured only: the profile worker polls at 25 Hz and threads by the parent cube's size, so the quicklook spectrum lands about 250 ms late (368 → 115 ms); hidden tabs' canvases do full Agg redraws (−25 % per point move with two quicklooks); the data tree rebuilds and reloads icons per added dataset (1.2 s for 99); slider drags queue every position (seconds of backlog on Wayland-like input); colormap combos render every icon on creation and resize (GLUE_SPEED R17: 28 ms per combo with 102 colormaps against 4 ms with glue's 15; the fix is an icon cache in `glue_qt/utils/colors.py`, after which glue-solar registers every sunpy colormap again, D35); the splash appears late; glue-core's `show_axes` state has no control (an axes-options checkbox would let any viewer drop its axes, as glue-solar's Hide axes button does for Image viewers (#90); others' ready glue #2128 is a Hide axes PR). Done when each is filed, merged or declined.
- [ ] **M4** `wp0-perf-astropy-irispy`: astropy and irispy, measured only: WCSAxes re-places every tick on every draw with one WCS call per coordinate (37-59 calls, 17-20 distinct); prototyped 2026-10-01 ('WCSAxes tick rendering' in GLUE_SPEED.md, scripts in `IRIS_PLAN_PROTOTYPES/wcsaxes_study_20261001.tar.gz`): a per-placement memo (SJI draw −25 %, confirmed) then batched calls (−50 %, needs its failing-WCS fixes) as the first two astropy PRs, a placement cache only after those, and glue's `_set_wcs` label fix (`wp0-perf-core-draw`) before any of them; a gzipped FITS is decompressed 4-5 times on open (astropy seeks past data; irispy and glue reopen; 2.9× with one decompression; irispy main's `read_files` decompresses once, #206); irispy's sit-and-stare -TAB raster WCS makes world-to-pixel slow and ambiguous (6 ms per point, round trips off by up to 6 exposures). After the WCSAxes fixes, propose a matplotlib-free tick core on reuse grounds, not speed (astropy#9993 and #16464; it would give glue-jupyter's bqplot viewer WCS ticks, glue-jupyter#154): GLUE_SPEED.md 'Decoupling WCSAxes from matplotlib'. Done when each is filed, merged or declined.

Notes:
- Few-line speed fixes from `GLUE_SPEED.md` are on the user's forks for review, no PRs (2026-10-02), one commit with its test and changelog each: glue `perf-g1a-wcs-labels`, `perf-g2-hidden-subset-layers`, `perf-g3-batch-link-removal`, `perf-g4-scalar-broadcast`, `perf-g5-lazy-scipy-optimize`, `perf-g6-lazy-ipython`, `perf-g7-profile-vminmax`, `perf-g8-slice-histogram`, `perf-g9-session-do-all`, `perf-g10-view-shape`; glue-qt `perf-q1-worker-block`, `perf-q2-slice-profile-sync`, `perf-q3-cmap-icon-cache`, `perf-q4-layer-icon-cache`, `perf-q5-lazy-terminal`, `perf-q6-startup-qt`; astropy `perf-a1-wcsaxes-pytest-import`. The user opens their PRs; until then the perf items count them as not filed.
- A behaviour probe, not a version, enables each workaround; retiring fixes: `world2pixel_single_axis` (core #2598), `has_celestial = False` (#2595), `WCS_LOCK` (astropy#19174), cursor readout (Qt #74), drag throttle (`wp0-perf-qt`).

### WP1: Coordinates, units and links

The coordinate contract (arcsec and Å on `_GlueWCS` IRIS data) and the links between IRIS datasets and sunpy maps.

**M1**


**M3**

- [ ] **M3** `wp1-stack-per-scan-wcs` (F115): Per-scan spatial coordinates with an inverse for 4D stacks. Done when scan-k pixel→world matches scan k's WCS to 1e-6″ on the 3400109360 and 3602506433 stacks and round-trips.
- [ ] **M3** `wp1-nexp-prp` (F116): Warn once that world→pixel on NEXP_PRP > 1 rasters returns the first exposure per position. Done when a synthetic NEXP_PRP=2 raster warns once and sit-and-stare data do not.
- [ ] **M3** `wp1-m3-pointing-offset` (F051, F052): An optional arcsec pointing offset set from a 'Shift pointing…' layer action, plus a co-alignment recipe. Done when (+2″, −1″) on 4000005156 SJI 2796 shifts its readout by that.

**M4**

- [ ] **M4** `wp1-m4-autolink-matrix` (F049, F054): Once a core release has #2595, use its `WCSLink` suggestions for IRIS dataset pairs. Done when SJI Pixel points reach rasters and other SJIs without a time link, with `link_hpc` subsets unchanged.

**OM**

- [ ] **OM** `wp1-m3-multi-instrument` (F055): Docs only: a recipe linking a co-aligned IRIS–SST pair in glue's link editor. Done when a Pixel point on the SST cube gives the IRIS spectrum there. Depends: wp8-m3-level3-input.

Notes:
- Sessions are Later: `wp3-wcs-saver` must carry the stack tables and pointing offset.

### WP2: Line moments and diagnostics

Products from IRIS spectra, as dataset `layer_action`s that add linked Data and open no viewer, in `glue_solar/sources/moments.py`.

**M2**

- [ ] **M2** `wp2-m2-moment-maps` (F152, F153): 'IRIS: line moments…' adds irispy's `calculate_moments` maps of a per-scan window as one linked Data, with no viewer. Done when 4000005156 C II intensity is NaN over fill and 4000255147 Si IV blocks the GUI ≤ 0.5 s at peak RSS ≤ 3× the float32 window.
- [ ] **M2** `wp2-m2-line-definition` (F154, F155): The dialog takes a required centre in Å (never TWAVE), wings (default ±0.5 Å) and an optional continuum window. Done when on 3610108077 Mg II k 2796.352 Å sets `moments_centre` and a blank centre adds nothing. Depends: wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-input-quality` (F165, F170): Moments use '<flux> DN/s' when present, mask NaN and -Inf, NaN a pixel on +Inf or saturation, and warn on NSATPIX or TSATPXn > 0. Done when the 3610108077 Si IV DN/s intensity equals DN intensity / exposure time. Depends: wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-tests-docs` (F153, F155, F156): Test against direct `calculate_moments` calls on a synthetic cube and irispy-data's remote 3400109360 cutout; add a guide page (FWHM ≈ 2.355 σ, optically thick lines). Done when `test_moments.py` passes and Sphinx builds with `-W`. Depends: wp2-m2-line-definition, wp2-m2-input-quality.

**M3**

- [ ] **M3** `wp2-m3-moments-extensions` (F153, F154): Moments on 4-D stacks, and a Profile range tool (glue-qt's `RangeMouseMode`) giving the wings. Done when a stack's scan 0 equals the per-scan maps. Depends: wp2-m2-line-definition.
- [ ] **M3** `wp2-m3-window-data` (F160): Opt-in uncertainties, moment error maps (irispy #201) and 'Rebin…' via `NDCube.rebin`. Done when 3610108077 Si IV 1403 errors equal irispy's and a 2×2 rebin keeps the finite mean. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-irispy-calibration-actions` (F166, F169): 'Remove dust' adds `SJICube.remove_dust` output as Data; radiometric calibration is a glue derived component on '<flux> DN/s' (D4). Done when both equal direct irispy calls (rtol 1e-6). Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-mg-features` (F162): 'IRIS: Mg II features…' wraps irispy's `calculate_mg_features` (#199) into k and h feature velocity and intensity maps. Done when they equal a direct irispy call on 3824262996. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-density-temperature` (F163): Add a log n_e or T map from two same-grid intensity maps via irispy's `density_diagnostic` or `map_ratio_to_quantity` (fiasco optional). Done when a synthetic ratio matches irispy. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-red-blue` (F158): 'Red-blue asymmetry…' wraps irispy's `calculate_red_blue_asymmetry` with a required rest and an iris_xfiles preset. Done when on 3610108077 Mg II k it equals a direct irispy call. Depends: wp2-m2-moment-maps.

**L**

- [ ] **L** `wp2-burst-detection` (F130): 'IRIS: detect UV bursts' wraps irispy's burst finders (#197). Done when its labels equal irispy's. Depends: wp2-m2-moment-maps.

Notes:
- Prototype: `IRIS_PLAN_PROTOTYPES/chk_wp2/` (a moments module and its tests).
- irispy's analysis functions take scaled float cubes (`read_files(..., memmap=False)`), never the loaders' raw int16 data: glue-solar marks its memmap SJI `meta["scaled"] = True`, so irispy's `check_scaled` would pass raw values. Rebin scaled values too.
- Measured on irispy main (2026-10-02): moments with ±0.5 Å wings meet the 0.5 s and 3× limits, without wings they do not; error maps need `uncertainty=True` on read; `calculate_mg_features` runs one scan at a time; the burst finders need `meta["exposure time"]`; radiometric calibration goes through `calculate_dn_to_radiance_factor`.
- Velocities are relative to the uncorrected Level-2 wavelength scale (about 5-10 km/s); Mg II and C II are optically thick, so their centroids and widths are proxies.
- The 0.5 s and 3× limits are local acceptance numbers, not CI thresholds; Profile Collapse stays the display-only quicklook.

### WP3: Sessions

Makes Save and Open Session work for the quicklook and every glue-solar dataset through glue's saver registry and LoadLog.

**L**

- [ ] **L** `wp3-style-cmap`: Register sunpy colormaps under their `.name` so sessions restore them by name. Done when an AIA map session restores cmap `sdoaia171`.
- [ ] **L** `wp3-wcs-saver`: Save `_GlueWCS` for embedded and derived data; file-referenced data take coords from glue's reload. Done when SJI, raster, stack and moments round-trip twice within 1e-9.
- [ ] **L** `wp3-quantity-meta`: Save Quantity meta and make SJI `frame_wcs_headers` session-safe. Done when a raster's exposure time and an SJI session restore.
- [ ] **L** `wp3-file-references`: Load browser data through path-first factories so LoadLog references the files, which dask data need. Done when sessions save under 100 KB and restore after the files move.
- [ ] **L** `wp3-session-budget`: Guard session size. Done when a 4000255147 quicklook session is ≤ 1 MB and saves in ≤ 2 s. Depends: wp3-file-references.
- [ ] **L** `wp3-coordination-reattach`: Restored viewers re-register with the coordinator. Done when a restored quicklook keeps its time master and offsets, and Pixel drags drive the other panels. Depends: wp3-wcs-saver, wp3-quantity-meta, wp3-style-cmap.
- [ ] **L** `wp3-app-session-acceptance` (F175): A pytest-qt test restores two quicklook sessions twice by file reference; then drop the guide's 'Saving sessions' warning. Done when coords, slices, cmaps, units, `link_hpc` links and meta match. Depends: wp3-wcs-saver, wp3-file-references, wp3-session-budget, wp3-coordination-reattach, wp0-core-profile-restore-priority, wp5-m1-velocity-axis.
- [ ] **L** `wp3-last-session` (F176): Autosave on quit, skipping sessions over 1 MB, with a menu action to restore. Done when a quicklook restores from the menu and a failed save writes nothing. Depends: wp3-app-session-acceptance.

Notes:
- Sessions record `glue_solar` class and function paths, so keep aliases if they move; each new coords type adds a `wp3-wcs-saver` case.
- Until WP3 lands, the loading guide says glue-solar sessions fail to save. Prototypes: `IRIS_PLAN_PROTOTYPES/wp3_impl.py`, `wp3chk_test_sessions.py`.

### WP4: Quicklook preset and coordination

Coordinates the stock glue viewers of the CRISPEX-style IRIS quicklook in `glue_solar/quicklook.py`.

**M1**

- [ ] **M1** `wp4-m1-hover-lock-tool` (F094, F095): A 'Follow/lock' `PixelSelectionTool` subclass: hover moves the point (50 ms throttle, no undo entry), a left click locks it with one undoable `ApplySubsetState`, a right click or Esc unlocks. Done when on 3860258481, 3824262996 and 4000255147 hover updates the spectrum within 0.35 s, 100 motion events give ≤ 1 update per 50 ms, and the lock survives scan and exposure steps.
- [ ] **M1** `wp4-m1-spectral-coupling` (F068, F075): Add what glue's Navigate lacks: Image wavelengths as Profile lines, wavelength and master-time lines on λ–t panels, a thin line at the point's slit on the spectrogram and at its exposure on λ–t (user, 2026-09-30), and the Profile x-range copied to λ–t x-limits. Done when on 4000005156 scan 0 and 4000255147 slider index k marks λ[k] in Å and nm, λ–t lines follow axis swaps, Navigate to λ[j] moves the map to j (a Profile unit other than the data's, such as nm, needs Qt #70), and markers update in < 5 ms.
- [ ] **M1** `wp4-m1-multi-window` (F072, F073, F074, F108): For each ticked window of one file, open a Profile and any λ–t panel, and link step, exposure, scan and slit pixels with idempotent glue `LinkSame` links. Done when on 4000005156 scan 0 with three windows a point at (s, y) gives each Profile cube_w[s, y, :] and each map a crosshair, rerunning adds 0 links, and on 4000255147 all windows share one exposure.
- [ ] **M1** `wp4-raster-overlays` (F125, F126): A toggle draws each raster step's slit on SJIs, in the SJI frame nearest that exposure, and a dashed map line at the step nearest the master time (hidden on NO MATCH). Done when on 4000005156 and 3860258481 each slit lies within 1 SJI px, and on 4000005156 SJI frames 0-15 mark scan 0 steps 3, 7, …, 63 and frames 16-31 scan 1.

**M3**

- [ ] **M3** `wp4-playback-extras` (F086, F087, F119): Add frame increment, bounce, 'N frames around current' and temporal blink (via `wp5-m1-spectral-blink`) to the `wp4-time-controls` loop. Done when each works on 4000255147 SJI 1400. Depends: wp4-time-controls, wp5-m1-spectral-blink.

**L**

- [ ] **L** `wp4-l-redo-sji-click`: Redo after Undo of a slit-jaw click repeats the click in the frame shown then, so it can land on another exposure or scan; store the raster point on glue's undo command (a probe-gated workaround in `glue_patches.py`). Done when Undo then Redo of a sit-and-stare slit-jaw click gives the same exposure after the frame has moved.
- [ ] **L** `wp4-profile-aggregation`: A band light curve at the point: a glue `SliceSubsetState` over the Profile's Collapse range that follows the point. Done when it equals the band nanmean on 4000255147. Depends: wp4-m1-spectral-coupling.

Notes:
- Whisker polish (F143) and CRISPEX entry keywords (F020) are Later.
- The move/stay matrix (`changes()` in `test_quicklook.py`) is how new coordination behaviour is pinned: one quicklook per data kind, an exact dict per event. A quicklook tab that is hidden still refreshes its readouts and overlay from the shown tab's point and time (invisible, and right again when shown; a cost only).
- SJI overlays and SJI clicks use the per-frame SJI WCS, never frame-0 pixel links. Overlays and markers stay out of sessions and 'Save Python script' but show in 'Save plot'.

### WP5: Spectral units, rest wavelength, line list, blink and Doppler

Blink and wavelength calibration now; line list, rest wavelength, km/s and Doppler images later; in `glue_solar/spectral.py` and `glue_solar/tools.py`.

**M1**

- [ ] **M1** `wp5-m1-spectral-blink` (F076): An Image tool alternates two (dataset, wavelength) positions in one viewer; design the interaction first (proposal: the slider gives one, a Blink menu the other and an interval). Done when on 4000005156 Mg II k against Si IV 1403 flips exactly, ≤ 0.25 s each. Depends: wp4-m1-multi-window.

**M3**

- [ ] **M3** `wp5-m3-rest-from-measurement` (F167, F168): A Gaussian + constant Profile Fit fitter (`fit_plugin`) and a recipe shifting the moments centre by a fitted photospheric line (drift: irispy #198). Done when the fitted O I 1355.598 centre equals a direct astropy fit. Depends: wp2-m2-line-definition.
- [ ] **M3** `wp5-m3-reference-blink` (F110): With the interaction designed for `wp5-m1-spectral-blink`, Blink two SJI channels in playback, each with its own limits, paired by the time sync. Done when on the 20210905 fixture SJI 1400 and 2796 align within 1 pixel. Depends: wp5-m1-spectral-blink.
- [ ] **M3** `wp5-m3-mean-spectrum-compare` (F079): 'Subtract mean spectrum' adds flux minus the fill-excluded nanmean spectrum as a derived component. Done when a Pixel-subset Profile equals spectrum minus nanmean within 1e-6 on 4000005156 Si IV 1403 and a 4-D stack.

**L**

- [ ] **L** `wp5-m1-line-list` (F151): Ship an IRIS line list that labels Profiles. Done when Mg II k labels sit on their wavelengths.
- [ ] **L** `wp5-m1-rest-wavelength-policy` (F146): One rest-wavelength source (never TWAVE), from the line list or typed. Done when Mg II k pre-selects 2796.352 Å. Depends: wp5-m1-line-list.
- [ ] **L** `wp5-m1-velocity-axis` (F147, F150): 'km / s' in glue's `unit_converter` registry and a velocity top axis on Profiles. Done when Mg II k reads 0 km/s at rest. Depends: wp5-m1-rest-wavelength-policy.
- [ ] **L** `wp5-m1-doppler-image` (F148, F149): 'Doppler image…' adds red-minus-blue wing planes as linked Data. Done when a symmetric synthetic line gives zero. Depends: wp5-m1-rest-wavelength-policy, wp2-m2-moment-maps.

Notes:
- km/s as a Profile x unit waits for glue-qt #70; glue #2603 / glue-qt #73 line layers could draw the line list.
- Same-cube blink needs no limit code: glue's limits are whole-cube.

### WP6: Fitting

Map fitting of IRIS spectra on glue's Profile Fit tab, planned with the user when it starts.

**M4**

- [ ] **M4** `wp6-glue-fit-tool` (F157, F158, F159, F161): Fit IRIS models over a window into a linked map on glue's Fit tab (`fit_plugin`, `parallel_fit_dask`), closing its upstream gaps. Done when a user does this in the GUI. Depends: wp5-m3-rest-from-measurement, wp2-m2-input-quality.

Notes:
- Models need analytic derivatives. Level-2 saturation is the int16 top code (about 16182 DN).

### WP8: Browser, discovery and inputs

Covers the observation browser, the header scanner (`scan.py`) and the IRIS readers (`iris.py`).

**M3**

- [ ] **M3** `wp8-m3-context-cubes` (F104): Low priority. File → Open reads aligned `aia_l2_*` cutouts through `image_data`, as the browser does. Done when a 3640107442 `aia_l2_*.fits` opens with `Time` and `_GlueWCS`, and `link_hpc` and time sync reach it.

**L**

- [ ] **L** `wp8-filter-stop` (F005): Run the scan in glue-qt's `Worker` with a working Stop. Done when Stop returns within 0.5 s and the tests pass 20 runs; the browser's load (#106, `_start`) shows the pattern.
- [ ] **L** `wp8-text-filter`: A case-insensitive filter on browser rows. Done when `iris_tree` tests filter by line and date and the filter survives a rescan. Depends: wp8-filter-stop.
- [ ] **L** `wp8-prescan-search` (F003, F010): Time-window and glob arguments for `scan_directory` that prune by filename, and `find_observation_files`. Done when a 2013-09-02 window reads only 2013-09-01/02 headers. Depends: wp8-filter-stop.
- [ ] **L** `wp8-search-ui` (F001, F002, F004): Start/Stop time fields, named search locations and recent searches. Done when tests set and restore the scan window. Depends: wp8-prescan-search.
- [ ] **L** `wp8-browser-conveniences` (F006, F007, F014): Persist browser options, an editable Folder field and double-click to load. Done when tests restore the settings and a typed path rescans. Depends: wp8-text-filter, wp3-file-references.
- [ ] **L** `wp8-browser-metadata` (F039, F040): Row tooltips from headers `scan.py` already reads. Done when the 20140329 C II tooltip shows its wavelength range and detector, with header reads unchanged.
- [ ] **L** `wp8-sot-cubes` (F106): Read Hinode/SOT cubes in IRIS SJI format (ITN 32) after porting the reader to irispy main (prototype: `IRIS_PLAN_PROTOTYPES/itn32_sot/`). Done when an ITN 32 cube opens with `Time` and pointing that `link_hpc` reaches. Depends: wp8-m3-context-cubes.

**OM**

- [ ] **OM** `wp8-m3-level3-input` (F025): A `data_factory` that loads a Level-3 `*_im.fits` as one Data. Done when synthetic ITN 26 files load and Level-2 files are not claimed.

Notes:
- Prototypes for `wp8-filter-stop` and `wp8-text-filter`: `wp8_scan.py`, `wp8_proto.py`, `wp8_loader.ui`; keep the object names `filter`, `stop_scan`, `progress`.
- WP1, WP3, WP4 and WP10 also edit `finalize`, `iris_loader.ui` and `test_importer.py`.

### WP9: Documentation and tutorials

Keeps `docs/user_guide/` true to what ships; WP9 owns the cross-cutting guides and recipes.

**M1**

- [ ] **M1** `wp9-m1-screenshots`: Restore `docs/make_screenshots.py` from commit 93d05f05 (unpushed `backup/iris-observation-browser-pre-rebase`) or record dropping it. Done when it regenerates `docs/user_guide/images/` with HOME isolated.

**M3**

- [ ] **M3** `wp9-m3-saturation-recipe` (F170): A 'Was it saturated?' recipe: NSATPIX/TSATPXn in View metadata, then an `np.isinf` subset. Done when checked on 4000005156 Si IV (NSATPIX 0).
- [ ] **M3** `wp9-m3-spectral-recipes` (F080, F084): Recipes for an average spectrum over scans, photospheric context and per-window flux × k. Done when each reproduces on 3602506433, 3660259102 and 3640107442.
- [ ] **M3** `wp9-m3-shortcuts-help` (F198, F199): A table of keys glue's tooltips omit and an 'IRIS: user guide and issues' `menubar_plugin` entry. Done when a test covers every shortcut and both URLs. Depends: wp11-keyboard-shortcuts, wp12-path-slicer.

**L**

- [ ] **L** `wp9-l-deferred-recipes` (F037, F145): Document Ctrl+I as the FITS header viewer, and row/column cuts once glue's Slice profile ships. Done when both reproduce on 4000005156 Si IV.

**M4**

- [ ] **M4** `wp9-m4-release-updates`: Update the guides as glue #2596/#2601 and glue-qt #70/#74 ship. Done when `docs/` has no 'unreleased' text.

Notes:
- `docs/` PRs build warning-free in `iris-plan-docs`, test no glue behaviour, and never present planned features as shipped.
- Later: a SPECTFILE-style mean-spectrum reference (F031; a full-dataset Profile with function Mean) and scripting beyond #77's recipe (F033).

### WP10: Loader robustness and performance

Keeps the IRIS loaders in `glue_solar/sources/loaders/` correct and fast on files up to 20 GB.

**M1**

- [ ] **M1** `wp10-m1-roi-world-polygon`: Override `apply_roi` on `QuicklookImageViewer` so a raster ROI becomes a lon/lat `PolygonalROI` (edges sampled once per step through `_GlueWCS`), and give raster viewers back their `select:*` tools. Done when on 4000005156 Si IV with deconvolved SJI 2796 frame 5 a raster rectangle selects the same 108,300 SJI pixels as the pixel subset in ≤ 0.5 s per frame, and sit-and-stare matches the pixel result.
- [ ] **M1** `wp10-m1-canvas-teardown`: An idle draw on a deleted `MplCanvas` intermittently fails `test_linking.py::test_a_sunpy_map_over_quicklook_panels_leaves_one_crosshair` at teardown (2 of 8 full `iris-plan` runs on the region branch, once on the regrid branch; the conftest's `_canvas_errors_fail` turns it into an error). Find the canvas whose draw outlives its viewer and stop it at close. Done when 20 full runs in each env pass.

**L**

- [ ] **L** `wp10-l-resident-memory`: Bring resident memory within the M0 budgets too: by RSS, 4000005156 scan 0 keeps 8.8 and peaks at 12.3 B/element with the quicklook open (tracemalloc: 5.15 and 9.53; 2026-10-01, `acceptance_20261001.tar.gz`). Since #96 (lazy loading) the RSS increase at open with the quicklook is 1.9 B/element on 4000005156 scan 0, within both; what remains is viewing, which brings a whole map's pages into resident memory (+0.5-0.8 GB on a Mg II k map). Done when the acceptance probe's RSS figures stay ≤ 6 and ≤ 10 B/element after viewing every panel.
- [ ] **L** `wp10-m3-sit-stare-chunks` (F036): Benchmark lazy sit-and-stare; add an exposure-range load only if it passes 12 GB or 0.15 s per slit step. Done when benchmarked and, if built, ranges match the full load.

Notes:
- IRIS Level 2 image HDUs are int16 (BSCALE 0.25, BZERO 7992; fill is raw -32768/-32764). irispy 0.9.1's `memmap=True` zeroes SJI fill and irispy main's reads the whole file for its mask, so SJIs keep glue-solar's own astropy read, and `.fits.gz` SJIs an eager int16 read; once a release does neither, `image_data` can pass its gunzipped bytes to `read_sji_lvl2` (−0.2 GB on a `.gz`).
- Raster world→pixel is slow (31 µs/pt at 400 steps, 7 ms/pt on sit-and-stare), so bulk SJI→raster mapping needs an analytic inverse.
- The lazy-loading RSS and eager-equality probes (`open_rss.py`, `mem.py`, `sji_mem.py` for the irispy SJI fill report) are in `IRIS_PLAN_PROTOTYPES/wp10_lazy_probe_20261001.tar.gz`, for `wp10-l-resident-memory` and `wp10-m3-sit-stare-chunks`.

### WP11: Display, readouts and inspection tools

Display and inspection tools for stock Image and Profile viewers, in `glue_solar/tools.py` and `glue_solar/quicklook.py`.

**M1**

- [ ] **M1** `wp11-keyboard-shortcuts` (F197): Register D/F (frame), A/S (wavelength), Space (play) and quicklook Tab/Backspace via `glue_qt.config.keyboard_shortcut`. Done when `QTest.keyClick` on glue-qt 0.4.2 steps with wrap and plays, and quicklook D/F move the time master and A/S only wavelength.

**M2**

- [ ] **M2** `wp11-colourbar` (F060): A checkable 'Colour bar' tool draws the reference layer's bar with glue's normalisation. Done when it follows limits, stretch, cmap, Contrast/Bias and slices and shows in `mpl:save` PNGs.
- [ ] **M2** `wp11-distance-measure` (F131): A `solar:measure` mode (glue's `ToolbarModeBase`) reports a dragged line in pixels, arcsec and km. Done when a 100-pixel line on 4000255147 SJI 1400 reads 16.6″ (within 0.01″ of WCS) and 12,172 km (within 0.1%).
- [ ] **M2** `wp11-zoom-steps` (F097): A 'Zoom 1:1' action makes one data pixel one screen pixel about the view centre. Done when the axes width in screen pixels equals x_max − x_min on an irispy raster.

**M3**

- [ ] **M3** `wp11-band-average` (F083): Map bands of 1, 5, 9 or 15 wavelength pixels via Collapse's Mean `AggregateSlice`, following the slider. Done when a width-5 map equals the `nanmean` over k±2; scan steps wait for `wp0-qt-aggregate-slice`.
- [ ] **M3** `wp11-north-up` (F054, F120): Show rolled SJIs north-up by reprojecting onto a north-up helioprojective grid. Done when the rolled 3860608353 SJI 2832 shows north up within 0.5°.

**L**

- [ ] **L** `wp11-l-all-colormaps`: Register every sunpy colormap again, with glue-qt's colormap icons cached by a probe-gated patch (`glue_patches.py`) until glue-qt caches them itself (`wp0-perf-qt`, D35). Done when every sunpy colormap is in the Image viewer's combo and building a combo stays within 2 ms of the IRIS-and-AIA-only time.
- [ ] **L** `wp11-scaling-extras` (F066, F067): Per-band default stretches in the preset; glue's controls adjust them. Done when each IRIS band opens with its default.

Notes:
- glue-qt already takes B, C, G, H, K, M, P, R, W, X, Y, Z, Tab, Backspace and L, and dispatches keys by exact viewer type.
- Not planned: zoom ×2/÷2, centring and a percentile menu (glue has them), or a CRISPEX control-panel clone.

### WP12: Export and derived diagrams

Frame, movie and data export plus path diagrams, built on glue's 'save' subtools, exporters and core's path slicer.

**M1**


**M2**

- [ ] **M2** `wp12-sequence-export` (F178, F179): `solar:save_sequence` saves PNG frames or a movie (`FFMpegWriter`, else GIF) along one slice axis at fixed colour limits. Done when 4000255147 SJI 1400 frames 0-9 give 10 PNGs equal to `mpl:save`, a 10-frame GIF, and Cancel keeps partial output. Depends: wp4-time-controls.
- [ ] **M2** `wp12-path-slicer` (F135, F137): `solar:path` and a crosshair mode subclass core's path slicer for 3D and 4D data. Done when on 4000255147 a 3-vertex path gives (400, N) SJI 1400 and (λ, N) raster diagrams, a 4-scan 3602506433 stack gives (scan, λ, N), and traces agree within 0.5 px. Depends: wp11-distance-measure.

**M3**

- [ ] **M3** `wp12-export-annotations` (F133): Add a UTC timestamp option to `solar:save_sequence`. Done when each 4000255147 SJI 1400 frame's text equals its `Time` to 0.01 s. Depends: wp12-sequence-export.
- [ ] **M3** `wp12-path-overlays-slopes` (F132): A two-click slope readout on distance-time diagrams gives speed (km/s) and acceleration as Table rows. Done when an injected feature is recovered within 1% and 2%. Depends: wp12-path-slicer, wp11-distance-measure.
- [ ] **M3** `wp12-path-batch` (F138): Add 'nearest' and 'linear' path sampling beside core's truncation. Done when both match references to 1e-6 on a synthetic ramp. Depends: wp12-path-slicer.

**L**

- [ ] **L** `wp12-derived-data-export` (F182, F187): Export derived data as FITS (or ASDF) with IRIS coordinates and `Time`, never IDL save files. Done when moment and sliced maps round-trip their coordinates. Depends: wp2-m2-moment-maps.
- [ ] **L** `wp12-date-labels`: Port glue-core #2599's datetime tick fix into `glue_patches.py` until it is released. Done when a 2021 Scatter shows 2021 ticks.
- [ ] **L** `wp12-time-marker`: The master exposure shows as a glue time-range subset on datetime Scatter plots, moved with the master. Done when it follows the master and survives a session reopen. Depends: wp12-date-labels, wp3-app-session-acceptance.
- [ ] **L** `wp12-point-light-curves` (F140, F141): 'Light curves at this point' adds time series per raster window and SJI. Done when raster curves equal `cube[:, y, k]` and ECSV keeps `Time`. Depends: wp12-time-marker.
- [ ] **L** `wp12-path-persist` (F185, F186): Save paths in sessions and as ECSV. Done when a reopened path reloads the same diagram. Depends: wp12-path-slicer, wp3-wcs-saver.
- [ ] **L** `wp12-saved-path-reuse` (F127, F139): Saved paths redraw on every viewer of their parent and re-extract on other datasets. Done when each ticked window gets one product. Depends: wp12-path-persist.
- [ ] **L** `wp12-profile-values-export` (F184): `solar:save_profile` writes the visible profiles to one ECSV file. Done when re-read values equal the viewer's arrays. Depends: wp12-point-light-curves.
- [ ] **L** `wp12-export-options` (F181, F183): Simple sequence export options: scale bar, frame numbers, default name. Done when a 10″ bar spans 10″ ±1 px. Depends: wp12-sequence-export, wp11-distance-measure.

Notes:
- Paths and curves sample at the master's exposure; stack paths use the scan-0 WCS until `wp1-stack-per-scan-wcs`. Core's `PathSlicedData` crashes on IRIS data, so `solar:path` overrides four of its methods until the WP0 reports are fixed.
- glue's CSV writes `Time` as int64 (`wp0-core-datetime-export`). Not rebuilt: phi-slit sliders, path width, PostScript, IDL save files.

### WP13: Other missions

Features only other missions need, planned with the user once suitable data exist.

**OM**

- [ ] **OM** `wp13-stokes` (F171, F172, F173, F174): Stokes selection, multi-Stokes spectra, scaling and noise level, Stokes main cubes. Done when a real Stokes cube shows each parameter.
- [ ] **OM** `wp13-solarnet-tab-wcs` (F027): Load SOLARNET files with a tabulated (-TAB) WCS. Done when a real -TAB file loads.
- [ ] **OM** `wp13-height-cubes` (F030): Load simulation and height cubes. Done when one slices by height.

Notes:
- IRIS Level-3 input (F025) is `wp8-m3-level3-input`, also OM.

## Workaround register

Gated workarounds on main. Raw-WCS readers hold `WCS_LOCK` or use a deep copy; never fake an all-ones `axis_correlation_matrix`.

| Workaround | Switch | Retiring fix |
| --- | --- | --- |
| Correlated-axis `world2pixel_single_axis` (#71) | `needs_inverse_workaround()` | glue #2598 |
| `_GlueWCS` `WCS_LOCK` (#60) | Always on (not safely probeable) | astropy#19174's fix, once 20 unlocked race runs give 0 crashes |
| `_GlueWCS.has_celestial = False` (#66) | Always on | glue #2595 |
| Generic `solar:cursor_readout` | `not hasattr(ImageViewer, 'cursor_status')` | glue-qt #74 |
| Slice-slider drag throttle (#68) | Always on | glue-qt slider coalescing (`wp0-perf-qt`) |
| PV-slice slices (`sync_pv_slice`, #81) | `needs_pv_slice_workaround()` | a glue-qt fix (none filed); guard the import (glue-qt #66 deletes `PVSliceWidget`) |
| Pixel point off a linked dataset (`PixelSubsetState._to_linked_pixel_coords`, #76/#85) | `needs_pixel_point_workaround()` | `wp0-core-image-artist-bugs`'s fix |
| PV slicer on lazy (dask) data (`pv_slice_from_path`, #96) | `needs_pv_dask_workaround()` | glue-qt's PV slicer accepting dask data |
| FITS export of lazy data and of uint8 components in a subset (`export_fits`, #96) | `needs_fits_export_dask_workaround()` | glue-core's exporter writing dask arrays and uint8 subsets (report candidate) |
| No (0,0) Pixel crosshair (`ImageSubsetLayerArtist._update_visual_attributes`, #87) | `needs_crosshair_workaround()` | `wp0-core-image-artist-bugs`'s fix |
| Pixel crosshair of a linked layer placed from the reference data (`ImageSubsetLayerArtist._update_data`, #107) | `needs_reference_crosshair_workaround()` | `wp0-core-image-artist-bugs`'s fix |
| Axis labels set on the WCSAxes coordinate without placing ticks (`ImageViewer.update_x/y_axislabel`, #90) | `needs_axis_label_workaround()` | glue's `_set_wcs` label fix (`wp0-perf-core-draw`; the user's fork branch `perf-g1a-wcs-labels`) |
| Slice playback stopped when its viewer closes (`ImageViewer.closeEvent`, #115) | Per close: a slider still playing after glue-qt's own close | glue-qt stopping play timers on close (report candidate) |

Planned workarounds are named in their items.

## Validation, environments and data

Run all Python in a micromamba env, never a `.venv`; create a new env rather than change one.

- `iris-plan`: the D5 baseline (Python 3.13, PyQt5, astropy 8.0.1, sunpy 8.0.0, editable glue-solar).
- `iris-plan-floor`: the dependency floors (astropy 8.0.0, ndcube 2.4.0); every PR passes in both.
- `iris-plan-docs`: `iris-plan` plus Sphinx.
- `ruff-0161`: glue-solar's pinned Ruff.
- `irispy-ports`: irispy development (editable `~/Git/irispy-bursts`); test other worktrees with `PYTHONPATH=<worktree>`, never from `~/Git/irispy`.

The `glue-solar` env follows the editable checkouts and is not a baseline.

Headless runs use a scratch `HOME` (glue rewrites `~/.glue/settings.cfg`), offscreen Qt and Agg; glue-solar's conftest keeps tests off macOS QSettings. Regenerate upstream PR exports before use (macOS purges temporary directories). Run tests from a checkout of the code under test, never `~/Git/glue-solar` (on `plan`):

```sh
P=~/Git/glue-solar/IRIS_PLAN_PROTOTYPES
env HOME="$(mktemp -d)" PYTHONPATH=$P \
  ~/mamba/envs/iris-plan/bin/python -B $P/run_checks.py \
  "$PWD:$P" glue_solar --remote-data=any
```

glue-solar tests only the GUI and glue side, with the loaded dataset's own coordinates as oracle; irispy's reading, WCS and numerics are irispy's tests. Real-data tests are `@pytest.mark.remote_data` tests on LM-SAL/irispy-data release assets (tag `v1`) via the `irispy_data` fixture, never local paths or committed data; a missing cutout goes into irispy-data first, on the user's direction. irispy's decimated CI fixtures (`find_irispy_test_file`) are not physical validation.

Full-size checks are manual probes under `IRIS_PLAN_PROTOTYPES/` (`wp4_time_sync_probe.py` for time-sync correctness, `wp10_slider_probe.py` for on-screen slider latency, `wp1_wrapper_probe_20261001.tar.gz` (`core.py`: units, round trips and WCS links per IRIS WCS kind; `gui.py`: overlapping and clipped tick labels per quicklook panel), and the acceptance probe in `acceptance_20261001.tar.gz`, whose time, memory and crash modes measure any of the acceptance observations, offscreen with a warm cache, as `TREE=<main checkout> ./acceptance.sh time|memory|crash OBSID`) on `~/DATA/IRIS`, with results in the item's PR description. Acceptance data: 4000255147 (sit-and-stare, SJI 1400), 4000005156 (two-scan raster, deconvolved SJI 2796), 3824262996 (400-step Mg II raster), 3400109360 (negative step), 3602506433 (99 scans, memory only), 3860259453 (slider speed).

Docs build: write the checkout's `glue_solar/version.py` with `~/mamba/envs/iris-plan-docs/bin/python -m setuptools_scm --root <checkout> --config <checkout>/pyproject.toml --force-write-version-files`, then from a scratch directory run `env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=<checkout> ~/mamba/envs/iris-plan-docs/bin/sphinx-build -W --keep-going -b html <checkout>/docs <scratch>/html` (about 12 s); never `tox -e build_docs`.
