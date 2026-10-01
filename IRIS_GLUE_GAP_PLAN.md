# IRIS and Glue work plan

This plan drives glue-solar, with the irispy and glue work it needs, toward an IRIS quicklook in Glue covering what SolarSoft's CRISPEX offers; each item names the CRISPEX features (F001-F203) it serves. The plan and `IRIS_PLAN_PROTOTYPES/` live on glue-solar's pushed branch `plan`, never merged or opened as a PR, and it lists open work only. Each item is one draft PR on a branch from `main` without the plan or prototypes. Commit, push, or open, ready or merge a PR only when the user asks.

## How to use this plan

- Start at [Current state](#current-state-2026-09-30) and refresh PR states with `gh`.
- Pick an open item in the earliest open milestone; read its done-when and Depends.
- Trace the code on `main` before writing or porting a prototype; this plan overrides prototypes.
- Stage named files only.
- When an item's PR merges, delete the item and its key from other Depends lines, and add one line to Current state. Say "on main", not "released".

## Scope

In scope:

- The CRISPEX and IRIS-SolarSoft features from the user's 2026-09-30 review: 'keep' ones are M0 to M3 items (fitting M4), 'later' ones L items; [Features available today](#features-available-today) lists what Glue already covers.
- CRISPEX (and `iris_xfiles` for discovery) is the behaviour reference; it has no licence, so no code is ported.
- Features only other missions need come last ([WP13](#wp13-other-missions)).

Out of scope ([Features excluded](#features-excluded)):

- Level-3 FITS writing, EIS, the detector mosaic (needs Level 1), and OBS XML and pipeline-log viewers.
- The IRIS-9 tutorial, and online context and search (GOES, AIA, HMI, SWPC, HCR, IRIS search).
- AIA reference panels, reference spectra and AIA blink: AIA and Hinode cubes are imaging only, like SJIs.
- PostScript and IDL formats: images export in normal formats, derived data as FITS or ASDF.
- SST-only inputs and IDL details Glue replaces.

## Current state, 2026-09-30

**Resume here.** Main is at 5eae565 and no glue-solar PR is open. Merged on 2026-09-30: the M0 quicklook (#72-#79), #81 (PV-slice patch), #82 (review follow-ups and a CI fix), #83 (slit line and raster point on slit-jaw viewers), #85 (re-lands #76's launch entries), #84 (drops the sunpy Map directory importer), #86 (link-graph tests), #87 (sit-and-stare exposure axes and the (0,0) crosshair patch) and #88 (the M0 guides). PRs are marked ready and merged once CI passes. On 2026-09-30 this plan was restructured after the user's review of all 203 features, a glue-overlap audit and the decisions in Scope and Decisions; the previous text, the feature map and the retired prototypes are in the plan branch's git history.

**Next.** A one-line guard so the Frame time readout does not crash on an empty Collapse range; `wp4-tests` (also set `GLUE_TESTING` suite-wide in conftest, as glue does, so a viewer error fails a test instead of opening a modal box); `wp10-m0-acceptance` (a synced step is 0.30 s against its 0.25 s budget; #87 adds about 25 ms to a slit move). A profiling survey of glue-core and glue-qt on IRIS workflows (draw, links, statistics, IO, events, startup) is running; its ranked findings go into WP0 as M4 work, measured only, nothing patched. Then M1, starting with `wp10-m1-lazy-loading` and `wp1-m1-wrapper-coherence` (wavelength axes show metres with overlapping tick labels).

**Releases.** glue-core 1.27.0, glue-qt 0.4.2, irispy-lmsal 0.9.1 (all fixes glue-solar needs). irispy drafts for the user's review: #197 (UV bursts), #198 (wavelength drift), #199 (Mg II features), #201 (moment uncertainties).

**Confirmed by the user (2026-09-30)**, formerly provisional: each quicklook tab has its own Point group; `link_hpc` links every dataset to the first (a star); a NO MATCH readout gives the nearest frame's offset, and a follower moved by hand shows its own, greyed beyond half a cadence; 'Open quicklook' starts ticked and the browser skips glue's autolinker; a quicklook's point drives only its own panels, and an SJI point leaves the spectrum empty until the next raster click (until `wp4-sji-click-to-raster`); lazy-loading limits from a sample of the raw ints within 1 % of the eager 99.5 % limits; moments and red-blue dialogs take a typed line centre until the Later line list; radiometric calibration is a glue derived component (D4); the time marker is glue's own range subset; F098 is covered by glue's Pan; `wp1-m3-multi-instrument` is Other missions with Level-3 input; the Profile display-unit restore patch goes to Later with sessions, sessions re-read IRIS files through glue's load log, and the Hinode/SOT reader is its own Later item. Also confirmed: the sit-and-stare exposure label and integer ticks apply to every Image viewer of such a raster, with exposure ticks only (no helioprojective ticks on the far edge); a thin point line on the spectrogram and λ–t panels comes with `wp4-m1-spectral-coupling`; the loading guide is split into topic pages in M1 (`wp9-m1-split-guide`).

**Worktrees.** `~/Git/glue-solar` (this plan); irispy ports in `~/Git/irispy-bursts`, `-wavecorr`, `-mg-features`, `-moments-uncertainty`. The other `~/Git/glue-solar-*` worktrees are merged and removable.

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
- **D12:** -200 and -199 are missing (AIA: -200 only), +Inf is saturation, negatives are data; stored masks are uint8.
- **D13:** Sessions add the Quantity saver only if none exists, save `_GlueWCS` via `__gluestate__`, never replace glue's `VisualAttributes` serialization globally, and save added components as 1-D vectors.
- **D14:** irispy work targets LM-SAL `main`; the gWCS raster work (irispy #182) is the user's to direct.
- **D15:** The quicklook is an MDI tab with explicit viewer geometry.
- **D16:** Doppler is red minus blue, I(λ0 + Δ) − I(λ0 − Δ), positive for redshift, in `meta['doppler_sign']`.
- **D17:** Missing data are NaN; no sentinel values.
- **D18:** Do not re-implement glue: configure, default, document or call glue's API first.

## Milestones

A milestone is done when all its items are ticked; M0 also needs `wp10-m0-acceptance` within its budgets.

- **M0: quicklook, finishing.** Wavelength-time panel labels, link-graph regression, interaction tests, docs over glue's features, full-data acceptance.
- **M1: navigation and spectral parity.** Lazy loading first (files reach 20 GB), then SJI to raster, hover-lock, spectral coupling, multi-window, blink, time controls, overlays, readouts, non-blocking load.
- **M2: analysis, display and export.** Moments, colour bar, distance and zoom, image and movie export, path slicer.
- **M3: specialist.** Stack WCS, pointing, calibration, Mg II, density and temperature, red-blue maps, reference blink, AIA context cubes (low priority).
- **L: Later.** Deferred by the user (sessions, browser search, light curves); revisit after M3; not a gate.
- **M4: upstreaming.** After M3, on the user's direction: upstream PRs, reports and the user's drafts, autolink matrix, fit tool; a release with a fix retires its workaround.
- **OM: Other missions.** Last: WP13 and `wp8-m3-level3-input`.

### Checklist by milestone

**M0**
- WP4: `wp4-tests`
- WP9: `wp9-m0-wiki-digest`
- WP10: `wp10-m0-acceptance`

**M1**
- WP0: `wp0-release-tracking`, `wp0-irispy-requests`
- WP1: `wp1-m1-wrapper-coherence`, `wp1-m1-sunpy-maps`, `wp1-m1-sji-to-raster`, `wp1-dn-per-s`
- WP4: `wp4-m1-hover-lock-tool`, `wp4-sji-click-to-raster`, `wp4-m1-spectral-coupling`, `wp4-m1-multi-window`, `wp4-time-controls`, `wp4-raster-overlays`
- WP5: `wp5-m1-spectral-blink`
- WP8: `wp8-derived-files`
- WP9: `wp9-m1-screenshots`, `wp9-m1-split-guide`
- WP10: `wp10-m1-lazy-loading`, `wp10-nonblocking-load`, `wp10-m1-roi-world-polygon`
- WP11: `wp11-cursor-readout`, `wp11-selected-point-panel`, `wp11-histo-opt-scaling`, `wp11-gamma-stretch`, `wp11-raster-cmap`, `wp11-physical-aspect`, `wp11-keyboard-shortcuts`
- WP12: `wp12-time-regrid`

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
- WP4: `wp4-profile-aggregation`
- WP5: `wp5-m1-line-list`, `wp5-m1-rest-wavelength-policy`, `wp5-m1-velocity-axis`, `wp5-m1-doppler-image`
- WP8: `wp8-filter-stop`, `wp8-text-filter`, `wp8-prescan-search`, `wp8-search-ui`, `wp8-browser-conveniences`, `wp8-browser-metadata`, `wp8-sot-cubes`
- WP9: `wp9-l-deferred-recipes`
- WP10: `wp10-m3-sit-stare-chunks`
- WP11: `wp11-scaling-extras`
- WP12: `wp12-derived-data-export`, `wp12-date-labels`, `wp12-time-marker`, `wp12-point-light-curves`, `wp12-path-persist`, `wp12-saved-path-reuse`, `wp12-profile-values-export`, `wp12-export-options`

**M4**
- WP0: `wp0-core-image-artist-bugs`, `wp0-qt-large-data-cancel`, `wp0-astropy-19174`, `wp0-stack-validation`, `wp0-user-review`, `wp0-own-draft-updates`, `wp0-core-quantity-saver`, `wp0-core-derived-units`, `wp0-track-line-layers`, `wp0-qt-aggregate-slice`, `wp0-track-qt66`, `wp0-core-datetime-export`, `wp0-qt68-cocoa`, `wp0-core-session-reports`, `wp0-report-candidates`, `wp0-optional-proposals`, `wp0-upstream-draw-speed`
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

- [ ] **M1** `wp0-release-tracking`: After each glue-core, glue-qt, irispy or astropy release past 1.27.0/0.4.2/0.9.1, raise floors and retire workarounds. Done when each release has a line here naming its PRs, floors and retired workarounds.
- [ ] **M1** `wp0-irispy-requests`: Get irispy drafts #197-#199 and #201 (bursts, wavelength drift, Mg II features, moment errors) released and settle the irispy-side checks (exposure times, rolled-SJI gWCS, binned `slit x position`, per-step pointing). Done when a release has all four and each check has a test or user decision.

**L**

- [ ] **L** `wp0-core-profile-restore-priority`: Gated `setup()` wrapper so restored spectrum panels do not raise ValueError on core 1.27.0. Done when a cube with its spectral axis off axis 0 restores.
- [ ] **L** `wp0-qt68-macos-pass` (F203): Manual macOS check of glue-qt #68 (font, menus, Cmd-Tab, Dock name). Done when PyQt6 and PyQt5 results are recorded.

**M4**

- [ ] **M4** `wp0-core-image-artist-bugs`: Core PR: a hidden Pixel crosshair reappears at (0, 0), and `translate_pixel` raises a bare `Exception`. Done when both reproducers pass on a release.
- [ ] **M4** `wp0-qt-large-data-cancel`: glue-qt report: cancelling the 'Add large data set?' modal breaks later viewers. Done when filed or declined.
- [ ] **M4** `wp0-astropy-19174`: Add the IRIS -TAB WCS thread crash to astropy#19174. Done when reproduced without `WCS_LOCK` and posted or declined.
- [ ] **M4** `wp0-stack-validation`: Merge the upstream heads (core #2595, #2597-#2599, #2601; Qt #70, #74, #75) and run the Qt and `glue_solar` suites. Done when pass counts are recorded.
- [ ] **M4** `wp0-user-review`: The user reviews each upstream draft before it is ready. Done when each is merged, closed or parked. Depends: wp0-stack-validation.
- [ ] **M4** `wp0-own-draft-updates`: Amend #2595 to keep time axes out of `wcs_autolink`, and Qt #74 to show Solar X/Y. Done when both pass their suites. Depends: wp11-cursor-readout.
- [ ] **M4** `wp0-core-quantity-saver`: Core `u.Quantity` saver (D13) that loads glue-solar's fallback record. Done when its test round-trips Quantities in `Data.meta`.
- [ ] **M4** `wp0-core-derived-units`: Core PR saving `DerivedComponent.units`. Done when its test round-trips `units='DN/s'` and older records still load.
- [ ] **M4** `wp0-track-line-layers`: Track glue #2603 and glue-qt #73, which retire WP5's line-list workaround. Done when both are released or the user parks them.
- [ ] **M4** `wp0-qt-aggregate-slice`: glue-qt report and PR: a slider move turns a Profile Collapse `AggregateSlice` into an int. Done when filed or declined.
- [ ] **M4** `wp0-track-qt66`: Track glue-qt #66 (generic `path_slicer`), which WP12 builds on. Done when merged before WP12 starts or its author is asked.
- [ ] **M4** `wp0-core-datetime-export`: Report that core's exporters fail on datetime64 components (HDF5, FITS, VOTable raise; CSV writes int64). Done when filed or declined.
- [ ] **M4** `wp0-qt68-cocoa`: Once glue-qt releases #68, check conda-forge's glue-qt requires `pyobjc-framework-cocoa` on macOS. Done when checked or requested.
- [ ] **M4** `wp0-core-session-reports`: Report the 1.27.0 session-restore failures (`stretch_global=False`, lost `stretch_parameters`, sunpy colormap names, object-array meta, `LinkSameWithUnits`). Done when each is filed or declined.
- [ ] **M4** `wp0-report-candidates`: Other reports, filed only on the user's direction. Done when each is filed or declined.
  - core `PathSlicedData` crashes on IRIS data (`world_axis_names` per kept pixel axis) and has generic gaps: 3-D-only enable, zeros not NaN, datetime cast, no session saver.
  - core dask percentile sampling reads only chunk corners.
  - glue-qt ignores Fit constraints; its playback timer outlives the viewer.
  - irispy `memmap=True` zeroes SJI fill.
  - glue-qt keyboard shortcuts: Tab never cycles windows (Qt focus takes it), keys are looked up by exact viewer class (subclasses such as `QuicklookImageViewer` get none), Table viewer keys are registered on `DataTableModel`; the Image viewer's profile button has no tooltip.
  - glue-qt Profile Navigate and Collapse compare display-unit x with native values; Collapse drops the range's last sample, and an empty `AggregateSlice` raises when drawn.
  - glue's FITS subset-mask importer refuses unsigned integer masks.
  - astropy WCSAxes `auto_assign_coord_positions` raises `TypeError` when no consistent tick-label placement exists.
  - with glue #2595, raster pixel ROIs in an SJI take #2595's frame-0 WCSLink instead of `link_hpc`'s per-frame path (shorter link chain); amend #2595 or document it.
- [ ] **M4** `wp0-optional-proposals`: Non-blocking proposals: core Profile x-label units, percentiles and interpolation; glue-qt gamma slider and playback modes; irispy NaN float rasters; astropy fitter reuse after `parallel_fit_dask`. Done when each is filed or declined.
- [ ] **M4** `wp0-upstream-draw-speed`: Take the two Image-draw costs (0.065 s per draw on 3860259453 Si IV), slow -TAB evaluation and WCSAxes tick sampling, upstream. Done when each is filed, merged or declined.

Notes:
- A behaviour probe, not a version, enables each workaround; retiring fixes: `world2pixel_single_axis` (core #2598), `has_celestial = False` (#2595), `WCS_LOCK` (astropy#19174), cursor readout (Qt #74), drag throttle (`wp0-upstream-draw-speed`).

### WP1: Coordinates, units and links

The coordinate contract (arcsec and Å on `_GlueWCS` IRIS data) and the links between IRIS datasets and sunpy maps.

**M0**


**M1**

- [ ] **M1** `wp1-m1-wrapper-coherence` (F024, F058): Make `_GlueWCS` report Å and arcsec through every API glue uses, for all IRIS WCS kinds. Done when on 3610108077 the slider, readout and Profile x show Å within 1e-6 Å of irispy, HPLN/HPLT read arcsec, and pixel→world→pixel holds to 1e-9 px.
- [ ] **M1** `wp1-m1-sunpy-maps`: Keep sunpy maps on glue's plain astropy WCS; `link_hpc` links them to IRIS data with `LinkSameWithUnits`. Done when two overlapping maps autolink, and a synthetic map over the sns fixture SJI 1400 places it within 0.05 px at the first and last frames. Depends: wp1-m1-wrapper-coherence.
- [ ] **M1** `wp1-m1-sji-to-raster`: `sji_to_raster()` maps an SJI pixel at the displayed frame to a raster step (nearest `Time` for sit-and-stare) and slit row. Done when (step 32, slit 385) round-trips through 4000005156 SJI 2796 frame 7 within 0.5 px and 4000255147 SJI 1400 frames 0, 200, 399 give exposures 1, 801, 1597.
- [ ] **M1** `wp1-dn-per-s` (F165): The loader adds '<label> DN/s' (flux over a positive `Exposure time`, else NaN) as a glue `DerivedComponent`. Done when it matches on 3610108077 Si IV (NaN at the 0-s step 157) and 4000255147 SJI 1400, and viewers show 'DN/s'.

**M3**

- [ ] **M3** `wp1-stack-per-scan-wcs` (F115): Per-scan spatial coordinates with an inverse for 4D stacks. Done when scan-k pixel→world matches scan k's WCS to 1e-6″ on the 3400109360 and 3602506433 stacks and round-trips.
- [ ] **M3** `wp1-nexp-prp` (F116): Warn once that world→pixel on NEXP_PRP > 1 rasters returns the first exposure per position. Done when a synthetic NEXP_PRP=2 raster warns once and sit-and-stare data do not.
- [ ] **M3** `wp1-m3-pointing-offset` (F051, F052): An optional arcsec pointing offset set from a 'Shift pointing…' layer action, plus a co-alignment recipe. Done when (+2″, −1″) on 4000005156 SJI 2796 shifts its readout by that.

**M4**

- [ ] **M4** `wp1-m4-autolink-matrix` (F049, F054): Once a core release has #2595, use its `WCSLink` suggestions for IRIS dataset pairs. Done when SJI Pixel points reach rasters and other SJIs without a time link, with `link_hpc` subsets unchanged. Depends: wp1-m1-wrapper-coherence, wp1-m1-sunpy-maps.

**OM**

- [ ] **OM** `wp1-m3-multi-instrument` (F055): Docs only: a recipe linking a co-aligned IRIS–SST pair in glue's link editor. Done when a Pixel point on the SST cube gives the IRIS spectrum there. Depends: wp8-m3-level3-input.

Notes:
- Sessions are Later: `wp3-wcs-saver` must carry the stack tables and pointing offset.
- #84 replaces the map directory importer with File → Open's multi-select and the 'sunpy Map' loader.

### WP2: Line moments and diagnostics

Products from IRIS spectra, as dataset `layer_action`s that add linked Data and open no viewer, in `glue_solar/sources/moments.py`.

**M2**

- [ ] **M2** `wp2-m2-moment-maps` (F152, F153): 'IRIS: line moments…' adds irispy's `calculate_moments` maps of a per-scan window as one linked Data, with no viewer. Done when 4000005156 C II intensity is NaN over fill and 4000255147 Si IV blocks the GUI ≤ 0.5 s at peak RSS ≤ 3× the float32 window. Depends: wp10-m1-lazy-loading.
- [ ] **M2** `wp2-m2-line-definition` (F154, F155): The dialog takes a required centre in Å (never TWAVE), wings (default ±0.5 Å) and an optional continuum window. Done when on 3610108077 Mg II k 2796.352 Å sets `moments_centre` and a blank centre adds nothing. Depends: wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-input-quality` (F165, F170): Moments use '<flux> DN/s' when present, mask NaN and -Inf, NaN a pixel on +Inf or saturation, and warn on NSATPIX or TSATPXn > 0. Done when the 3610108077 Si IV DN/s intensity equals DN intensity / exposure time. Depends: wp1-dn-per-s, wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-tests-docs` (F153, F155, F156): Test against direct `calculate_moments` calls on a synthetic cube and irispy-data's remote 3400109360 cutout; add a guide page (FWHM ≈ 2.355 σ, optically thick lines). Done when `test_moments.py` passes and Sphinx builds with `-W`. Depends: wp2-m2-line-definition, wp2-m2-input-quality.

**M3**

- [ ] **M3** `wp2-m3-moments-extensions` (F153, F154): Moments on 4-D stacks, and a Profile range tool (glue-qt's `RangeMouseMode`) giving the wings. Done when a stack's scan 0 equals the per-scan maps. Depends: wp2-m2-line-definition.
- [ ] **M3** `wp2-m3-window-data` (F160): Opt-in uncertainties, moment error maps (irispy #201) and 'Rebin…' via `NDCube.rebin`. Done when 3610108077 Si IV 1403 errors equal irispy's and a 2×2 rebin keeps the finite mean. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-irispy-calibration-actions` (F166, F169): 'Remove dust' adds `SJICube.remove_dust` output as Data; radiometric calibration is a glue derived component on '<flux> DN/s' (D4). Done when both equal direct irispy calls (rtol 1e-6). Depends: wp1-dn-per-s, wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-mg-features` (F162): 'IRIS: Mg II features…' wraps irispy's `calculate_mg_features` (#199) into k and h feature velocity and intensity maps. Done when they equal a direct irispy call on 3824262996. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-density-temperature` (F163): Add a log n_e or T map from two same-grid intensity maps via irispy's `density_diagnostic` or `map_ratio_to_quantity` (fiasco optional). Done when a synthetic ratio matches irispy. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-red-blue` (F158): 'Red-blue asymmetry…' wraps irispy's `calculate_red_blue_asymmetry` with a required rest and an iris_xfiles preset. Done when on 3610108077 Mg II k it equals a direct irispy call. Depends: wp2-m2-moment-maps.

**L**

- [ ] **L** `wp2-burst-detection` (F130): 'IRIS: detect UV bursts' wraps irispy's burst finders (#197). Done when its labels equal irispy's. Depends: wp2-m2-moment-maps.

Notes:
- Prototype: `IRIS_PLAN_PROTOTYPES/chk_wp2/` (a moments module and its tests).
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
- [ ] **L** `wp3-coordination-reattach`: Restored viewers re-register with the coordinator. Done when a restored quicklook keeps its time master and offsets, and Pixel drags drive the other panels. Depends: wp1-m1-sji-to-raster, wp3-wcs-saver, wp3-quantity-meta, wp3-style-cmap.
- [ ] **L** `wp3-app-session-acceptance` (F175): A pytest-qt test restores two quicklook sessions twice by file reference; then drop the guide's 'Saving sessions' warning. Done when coords, slices, cmaps, units, `link_hpc` links and meta match. Depends: wp3-wcs-saver, wp3-file-references, wp3-session-budget, wp3-coordination-reattach, wp0-core-profile-restore-priority, wp1-m1-sunpy-maps, wp1-m1-wrapper-coherence, wp5-m1-velocity-axis.
- [ ] **L** `wp3-last-session` (F176): Autosave on quit, skipping sessions over 1 MB, with a menu action to restore. Done when a quicklook restores from the menu and a failed save writes nothing. Depends: wp3-app-session-acceptance.

Notes:
- Sessions record `glue_solar` class and function paths, so keep aliases if they move; each new coords type adds a `wp3-wcs-saver` case.
- Until WP3 lands, the loading guide says glue-solar sessions fail to save. Prototypes: `IRIS_PLAN_PROTOTYPES/wp3_impl.py`, `wp3chk_test_sessions.py`.

### WP4: Quicklook preset and coordination

Coordinates the stock glue viewers of the CRISPEX-style IRIS quicklook in `glue_solar/quicklook.py`.

**M0**

- [ ] **M0** `wp4-tests`: Extend `test_quicklook.py` into a move/stay matrix over SJI frame, map click, λ-panel click, scan or exposure and slider changes, with V34-raster and sit-and-stare-label regressions and a manual native-GUI checklist. Done when it passes in `iris-plan` with HOME and QSettings isolated, uses only LM-SAL/irispy-data, and CI runs the fixture and `online` cases.

**M1**

- [ ] **M1** `wp4-m1-hover-lock-tool` (F094, F095): A 'Follow/lock' `PixelSelectionTool` subclass: hover moves the point (50 ms throttle, no undo entry), a left click locks it with one undoable `ApplySubsetState`, a right click or Esc unlocks. Done when on 3860258481, 3824262996 and 4000255147 hover updates the spectrum within 0.35 s, 100 motion events give ≤ 1 update per 50 ms, and the lock survives scan and exposure steps.
- [ ] **M1** `wp4-sji-click-to-raster` (F049): Map an SJI Pixel point to the raster point with `sji_to_raster()` (Replace mode, re-entrancy guard, one undo entry); off-FOV points show 'outside raster FOV'. Done when on 4000255147 and 4000005156 the `wp1-m1-sji-to-raster` 0.5 px cases pass through the UI, and one click makes one assignment that one undo reverts. Depends: wp1-m1-sji-to-raster.
- [ ] **M1** `wp4-m1-spectral-coupling` (F068, F075): Add what glue's Navigate lacks: Image wavelengths as Profile lines, wavelength and master-time lines on λ–t panels, a thin line at the point's slit on the spectrogram and at its exposure on λ–t (user, 2026-09-30), and the Profile x-range copied to λ–t x-limits. Done when on 4000005156 scan 0 and 4000255147 slider index k marks λ[k] in Å and nm, λ–t lines follow axis swaps, Navigate to λ[j] moves the map to j (Å needs Qt #70), and markers update in < 5 ms. Depends: wp1-m1-wrapper-coherence.
- [ ] **M1** `wp4-m1-multi-window` (F072, F073, F074, F108): For each ticked window of one file, open a Profile and any λ–t panel, and link step, exposure, scan and slit pixels with idempotent glue `LinkSame` links. Done when on 4000005156 scan 0 with three windows a point at (s, y) gives each Profile cube_w[s, y, :] and each map a crosshair, rerunning adds 0 links, and on 4000255147 all windows share one exposure. Depends: wp10-m1-lazy-loading.
- [ ] **M1** `wp4-time-controls` (F088, F091): Add 'Go to UTC' and a [lo, hi] loop to glue's slider playback, and stop the play timer when its viewer closes. Done when on 4000255147 SJI 1400 'Go to 2013-09-02T17:00:00' picks the nearest exposure and the raster follows, a [100, 120] loop visits only frames 100-120, and closing the master stops playback.
- [ ] **M1** `wp4-raster-overlays` (F125, F126): A toggle draws each raster step's slit on SJIs, in the SJI frame nearest that exposure, and a dashed map line at the step nearest the master time (hidden on NO MATCH). Done when on 4000005156 and 3860258481 each slit lies within 1 SJI px, and on 4000005156 SJI frames 0-15 mark scan 0 steps 3, 7, …, 63 and frames 16-31 scan 1.

**M3**

- [ ] **M3** `wp4-playback-extras` (F086, F087, F119): Add frame increment, bounce, 'N frames around current' and temporal blink (via `wp5-m1-spectral-blink`) to the `wp4-time-controls` loop. Done when each works on 4000255147 SJI 1400. Depends: wp4-time-controls, wp5-m1-spectral-blink.

**L**

- [ ] **L** `wp4-profile-aggregation`: A band light curve at the point: a glue `SliceSubsetState` over the Profile's Collapse range that follows the point. Done when it equals the band nanmean on 4000255147. Depends: wp4-m1-spectral-coupling.

Notes:
- The Point subset is the point spectrum: the merged coupling and time sync (#75, #78) keep it on the matched scan or exposure, so `wp4-slice-profiles` is done.
- Done already: the preset, point, time sync, SJI panels and slit/point overlay. Whisker polish (F143) and CRISPEX entry keywords (F020) are Later.
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
- [ ] **L** `wp5-m1-velocity-axis` (F147, F150): 'km / s' in glue's `unit_converter` registry and a velocity top axis on Profiles. Done when Mg II k reads 0 km/s at rest. Depends: wp5-m1-rest-wavelength-policy, wp1-m1-wrapper-coherence.
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

**M1**

- [ ] **M1** `wp8-derived-files`: The scanner lists an IRIS `SPEC` file only if `DATA_LEV == 2`, counting skipped derived files; a load failure names the file. Done when on `iris_tree` a derived fixture is never a window and progress reports 1 skipped file; locally the scan skips 1 of 130.

**M3**

- [ ] **M3** `wp8-m3-context-cubes` (F104): Low priority. File → Open reads aligned `aia_l2_*` cutouts through `image_data`, as the browser does. Done when a 3640107442 `aia_l2_*.fits` opens with `Time` and `_GlueWCS`, and `link_hpc` and time sync reach it.

**L**

- [ ] **L** `wp8-filter-stop` (F005): Run the scan in glue-qt's `Worker` with a working Stop. Done when Stop returns within 0.5 s and the tests pass 20 runs. Depends: wp8-derived-files, wp10-nonblocking-load.
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

**M0**

- [ ] **M0** `wp9-m0-wiki-digest`: Only on request, fix the wiki's `Home.md:4` and `Short-Term-Roadmap.md:1` and add the milestone digest. Done when no section reference dangles.

**M1**

- [ ] **M1** `wp9-m1-screenshots`: Restore `docs/make_screenshots.py` from commit 93d05f05 (unpushed `backup/iris-observation-browser-pre-rebase`) or record dropping it. Done when it regenerates `docs/user_guide/images/` with HOME isolated.
- [ ] **M1** `wp9-m1-split-guide`: Split the IRIS loading guide into short topic pages (loading IRIS data, the quicklook, viewer tools and windows) with no new text (user, 2026-09-30). Done when the docs build with `-W` and no section is lost.

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

**M0**

- [ ] **M0** `wp10-m0-acceptance`: Measure the quicklook with a manual probe under `IRIS_PLAN_PROTOTYPES/` on full 4000255147, 4000005156 (+ deconvolved SJI 2796), 3824262996, 3400109360 and 3602506433. Done when recorded (24 GB machine, offscreen, warm cache): image step ≤ 0.10 s, λ–t slit step ≤ 0.15 s, click to spectrum ≤ 0.35 s, SJI step ≤ 0.15 s, synced step ≤ 0.25 s, `quicklook()` ≤ 3 s, ≤ 6 B/element (≤ 10 peak) on 4000005156 scan 0, stack < 12 GB, 20 runs crash-free.

**M1**

- [ ] **M1** `wp10-m1-lazy-loading` (F034): Hold raster and SJI data as raw int16 in glue `DaskComponent`s scaled per requested slice (fill to NaN), with the mask a derived component, lazy stacks, and colour limits set once from our own raw-int sample. Done when lazily opening all windows of 3824262996 and 4000255147 peaks below 10 % of eager RSS, slices, NaNs and masks equal eager (also on 3400109360), and limits are within 1 % of eager 99.5 %. Depends: wp10-m0-acceptance.
- [ ] **M1** `wp10-nonblocking-load` (F201): Run importer reads in glue-qt's `Worker` with a progress bar, a stop between raster files, Data added on the GUI thread and superseded loads dropped. Done when loading 3824262996 Mg II k or 4000255147 keeps GUI gaps ≤ 0.2 s, and a stop in the 3602506433 stack acts within one file and keeps earlier picks.
- [ ] **M1** `wp10-m1-roi-world-polygon`: Override `apply_roi` on `QuicklookImageViewer` so a raster ROI becomes a lon/lat `PolygonalROI` (edges sampled once per step through `_GlueWCS`), and give raster viewers back their `select:*` tools. Done when on 4000005156 Si IV with deconvolved SJI 2796 frame 5 a raster rectangle selects the same 108,300 SJI pixels as the pixel subset in ≤ 0.5 s per frame, and sit-and-stare matches the pixel result.

**L**

- [ ] **L** `wp10-m3-sit-stare-chunks` (F036): Benchmark lazy sit-and-stare; add an exposure-range load only if it passes 12 GB or 0.15 s per slit step. Done when benchmarked and, if built, ranges match the full load. Depends: wp10-m1-lazy-loading.

Notes:
- IRIS Level 2 image HDUs are int16 (BSCALE 0.25, BZERO 7992; fill is raw -32768/-32764). irispy `memmap=True` zeroes SJI fill, so SJIs need our own astropy read, and `.fits.gz` SJIs an eager int16 read.
- Raster world→pixel is slow (31 µs/pt at 400 steps, 7 ms/pt on sit-and-stare), so bulk SJI→raster mapping needs an analytic inverse.

### WP11: Display, readouts and inspection tools

Display and inspection tools for stock Image and Profile viewers, in `glue_solar/tools.py` and `glue_solar/quicklook.py`.

**M1**

- [ ] **M1** `wp11-cursor-readout` (F100, F101, F113): `solar:frame_time` adds the hovered pixel's `Time`, exposure and Doppler km/s to the readout. Done when step s of the 4000005156 Si IV map shows its UTC (within 1 ms) and exposure. Depends: wp1-m1-wrapper-coherence.
- [ ] **M1** `wp11-selected-point-panel` (F099, F191): A read-only quicklook dock lists the Pixel point's indices, coordinates, time, exposure and value per dataset, plus the time master and SJI–raster offset. Done when on 3860258481 (3D and 4D) each field equals a direct read and the unrelated 3880012095 SJI shows 'no match'. Depends: wp1-m1-wrapper-coherence.
- [ ] **M1** `wp11-histo-opt-scaling` (F061, F064): A checkable 'Per-frame limits' tool toggles each layer's `ImageLayerState.stretch_global`. Done when on 3610108077 a wavelength step gives that slice's 99.5-percentile limits when on and whole-cube limits when off. Sessions saved with per-frame limits fail to restore on glue 1.27.0 (`wp0-core-session-reports`).
- [ ] **M1** `wp11-gamma-stretch` (F062): Register 'Gamma 0.4', '0.75', '1.5' and '2.2' as `PowerStretch` subclasses via `glue.config.stretches.add`. Done when 'Gamma 0.75' is in glue-qt 0.4.2's Stretch combo and a second `setup()` raises nothing.
- [ ] **M1** `wp11-raster-cmap` (F059): Set glue's `preferred_cmap` to 'irissjiFUV' or 'irissjiNUV' by detector band. Done when 3610108077's C II and Si IV open in irissjiFUV and Mg II k and 2832 in irissjiNUV, also in a 2-scan 4000005156 stack.
- [ ] **M1** `wp11-physical-aspect` (F193): `solar:physical_aspect` scales glue's aspect by the arcsec-per-pixel ratio. Done when a 10″×10″ square renders square within 5% on 4000005156 (about 12:1) and 3400109360 (about 3:1) after resize and zoom.
- [ ] **M1** `wp11-keyboard-shortcuts` (F197): Register D/F (frame), A/S (wavelength), Space (play) and quicklook Tab/Backspace via `glue_qt.config.keyboard_shortcut`. Done when `QTest.keyClick` on glue-qt 0.4.2 steps with wrap and plays, and quicklook D/F move the time master and A/S only wavelength.

**M2**

- [ ] **M2** `wp11-colourbar` (F060): A checkable 'Colour bar' tool draws the reference layer's bar with glue's normalisation. Done when it follows limits, stretch, cmap, Contrast/Bias and slices and shows in `mpl:save` PNGs. Depends: wp11-gamma-stretch.
- [ ] **M2** `wp11-distance-measure` (F131): A `solar:measure` mode (glue's `ToolbarModeBase`) reports a dragged line in pixels, arcsec and km. Done when a 100-pixel line on 4000255147 SJI 1400 reads 16.6″ (within 0.01″ of WCS) and 12,172 km (within 0.1%).
- [ ] **M2** `wp11-zoom-steps` (F097): A 'Zoom 1:1' action makes one data pixel one screen pixel about the view centre. Done when the axes width in screen pixels equals x_max − x_min on an irispy raster.

**M3**

- [ ] **M3** `wp11-band-average` (F083): Map bands of 1, 5, 9 or 15 wavelength pixels via Collapse's Mean `AggregateSlice`, following the slider. Done when a width-5 map equals the `nanmean` over k±2; scan steps wait for `wp0-qt-aggregate-slice`.
- [ ] **M3** `wp11-north-up` (F054, F120): Show rolled SJIs north-up by reprojecting onto a north-up helioprojective grid. Done when the rolled 3860608353 SJI 2832 shows north up within 0.5°.

**L**

- [ ] **L** `wp11-scaling-extras` (F066, F067): Per-band default stretches in the preset; glue's controls adjust them. Done when each IRIS band opens with its default. Depends: wp11-gamma-stretch.

Notes:
- glue-qt already takes B, C, G, H, K, M, P, R, W, X, Y, Z, Tab, Backspace and L, and dispatches keys by exact viewer type.
- Not planned: zoom ×2/÷2, centring and a percentile menu (glue has them), or a CRISPEX control-panel clone.

### WP12: Export and derived diagrams

Frame, movie and data export plus path diagrams, built on glue's 'save' subtools, exporters and core's path slicer.

**M1**

- [ ] **M1** `wp12-time-regrid` (F089, F090): 'Regrid on time' resamples a sit-and-stare raster, SJI or scan stack at its median exposure spacing, taking the nearest exposure within 0.75 × median, else NaN. Done when 4000255147 Si IV (median 2.89 s) gives ceil(span/2.89)+1 pixels, a 10-exposure gap is NaN only there, and a raster step axis is refused.

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
| Slice-slider drag throttle (#68) | Always on | none (`wp0-upstream-draw-speed`) |
| PV-slice slices (`sync_pv_slice`, #81) | `needs_pv_slice_workaround()` | a glue-qt fix (none filed); guard the import (glue-qt #66 deletes `PVSliceWidget`) |
| Pixel point off a linked dataset (`PixelSubsetState._to_linked_pixel_coords`, #76/#85) | `needs_pixel_point_workaround()` | `wp0-core-image-artist-bugs`'s fix |
| No (0,0) Pixel crosshair (`ImageSubsetLayerArtist._update_visual_attributes`, #87) | `needs_crosshair_workaround()` | `wp0-core-image-artist-bugs`'s fix |

Planned workarounds are named in their items.

## Upstream PRs

States on 2026-09-30; "ready" means not a draft.

| PR | Owner, state | Relevance |
| --- | --- | --- |
| glue #2595, #2596, #2601 | user, drafts | WCS autolink (retires `has_celestial`); Slice profile; Profile WCSAxes (contains #2596) |
| glue #2597, #2598, #2599 | user, drafts | Session cmap and meta; correlated-axis inverse; datetime epoch (fix codestyle) |
| glue-qt #68, #69 | user, ready | macOS integration; glue-qt CI fix (overlaps #65) |
| glue-qt #70, #74, #75 | user, drafts | Profile sliders and km/s axis; cursor readout; time slider labels |
| glue #2603, #2507, glue-qt #73, #66 | astrofrog, drafts | Line layers; slicing speed-up; path slicer (WP12) |
| glue #2592 | dhomeier, ready | Visual references; glue PRs fail `py311-test-visual` until it merges |
| glue #2128, glue-qt #72 | others, ready | Hide axes; subtool enabling (WP12) |
| irispy #197-#199, #201, #182 | user, drafts | Bursts, wavelength drift, Mg II, moment errors; gWCS rasters (D14) |

## Validation, environments and data

Run all Python in a micromamba env, never a `.venv`; create a new env rather than change one.

- `iris-plan`: the D5 baseline (Python 3.13, PyQt5, astropy 8.0.1, sunpy 8.0.0, editable glue-solar).
- `iris-plan-floor`: the dependency floors (astropy 8.0.0, ndcube 2.4.0); every PR passes in both.
- `iris-plan-docs`: `iris-plan` plus Sphinx.
- `ruff-0161`: glue-solar's pinned Ruff.
- `irispy-ports`: irispy development (editable `~/Git/irispy-bursts`); test other worktrees with `PYTHONPATH=<worktree>`, never from `~/Git/irispy`.

The `glue-solar` env follows the editable checkouts and is not a baseline.

Headless runs use a scratch `HOME` (glue rewrites `~/.glue/settings.cfg`), offscreen Qt and Agg; glue-solar's conftest keeps tests off macOS QSettings (#63). Regenerate upstream PR exports before use (macOS purges temporary directories). Run tests from a checkout of the code under test, never `~/Git/glue-solar` (on `plan`):

```sh
P=~/Git/glue-solar/IRIS_PLAN_PROTOTYPES
env HOME="$(mktemp -d)" PYTHONPATH=$P \
  ~/mamba/envs/iris-plan/bin/python -B $P/run_checks.py \
  "$PWD:$P" glue_solar --remote-data=any
```

glue-solar tests only the GUI and glue side, with the loaded dataset's own coordinates as oracle; irispy's reading, WCS and numerics are irispy's tests. Real-data tests are `@pytest.mark.remote_data` tests on LM-SAL/irispy-data release assets (tag `v1`) via the `irispy_data` fixture, never local paths or committed data; a missing cutout goes into irispy-data first, on the user's direction. irispy's decimated CI fixtures (`find_irispy_test_file`) are not physical validation.

Full-size checks are manual probes under `IRIS_PLAN_PROTOTYPES/` (`wp4_quicklook_probe.py`, `wp4_time_sync_probe.py`, `wp10_slider_probe.py`) on `~/DATA/IRIS`, with results in Current state. `IRIS_PLAN_PROTOTYPES/idl_reference/` holds the IDL reference run behind the irispy ports; delete it once #197-#199 and #201 merge. Acceptance data: 4000255147 (sit-and-stare, SJI 1400), 4000005156 (two-scan raster, deconvolved SJI 2796), 3824262996 (400-step Mg II raster), 3400109360 (negative step), 3602506433 (99 scans, memory only), 3860259453 (slider speed).

Docs build: write the checkout's `glue_solar/version.py` with `~/mamba/envs/iris-plan-docs/bin/python -m setuptools_scm --root <checkout> --config <checkout>/pyproject.toml --force-write-version-files`, then from a scratch directory run `env HOME="$(mktemp -d)" QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=<checkout> ~/mamba/envs/iris-plan-docs/bin/sphinx-build -W --keep-going -b html <checkout>/docs <scratch>/html` (about 12 s); never `tox -e build_docs`.

## Features available today

Covered on main (#83 and #85 being merged) or by glue; none marked 'improve'.

| ID | Feature | How |
| --- | --- | --- |
| F008 | Observation summary list | Browser rows |
| F009 | Group files of one observation | Browser groups by OBSID, STARTOBS |
| F011 | Open files | Browser 'Load selected', File → Open |
| F012 | Raster opens quicklook with matching SJIs | Browser 'Open quicklook' (#85) |
| F013 | Preview an SJI movie | Load, then play the slider |
| F015 | Quicklook mode launcher | 'IRIS: quicklook…' entries (#85) |
| F021 | Main image cube input | IRIS Level 2 factory and browser |
| F022 | Transposed spectral cube | Any axis pair in an Image viewer |
| F026 | Select spectral windows | Browser window checkboxes |
| F032 | SCALE_CUBES factor | Arithmetic attributes |
| F035 | Fast spectrum-vs-time access | Wavelength-time step in 0.07 s |
| F038 | Date and OBSID labels | Browser columns, dataset labels |
| F050 | Time-dependent SJI pointing and slit geometry | `link_hpc` per-frame links |
| F053 | Raster scan direction | irispy flips negative steps |
| F056 | Main image window | Quicklook raster-map panel |
| F057 | X-Y vs λ-Y image toggle | Quicklook spectrogram and λ–t panels |
| F063 | Limits, stretch, reset | Layer style editor |
| F065 | Independent scaling per display | Per-panel 99.5 % limits |
| F069 | Default starting wavelength | Quicklook preset |
| F070 | Reference spectral position and lock | Separate viewers; Profile Navigate |
| F071 | Detailed spectrum window | Quicklook Profile panel |
| F077 | Spectrum y-range and styling | Profile options, axes editor |
| F078 | Per-window multiplier | One Profile per window; Normalize |
| F081 | Custom axis titles | Profile axes editor |
| F085 | Frame slider and playback | Slice-widget playback |
| F092 | Spectrogram animation | Play the step slider |
| F096 | Numeric X/Y position sliders | Step and slit sliders move the point |
| F098 | Pan and go-to-cursor | glue's Pan; centring on the point not planned |
| F102 | Linked image and spectrum panels | Pixel point drives every panel |
| F105 | SJI and context cubes | Browser lists SJIs and AIA cutouts |
| F109 | Slit-jaw image windows | SJI panels, slit/point overlay (#83) |
| F111 | Master time selection | 'Time master' |
| F112 | Raster timing offset | Signed Δt readout, NO MATCH |
| F114 | 4-D raster time series | Browser stacking (later irispy gWCS) |
| F117 | Per-exposure readouts | `Exposure time`, Frame time tool |
| F118 | Nearest-in-time SJI panel | Time sync to the nearest exposure |
| F121 | SJI thumbnails | Channel checkboxes |
| F122 | SJI map movie | SJI slider playback |
| F124 | Mask cube and contours | Mask subsets, 'Import subset mask(s)' |
| F128 | Overlay and marker styling | Style editor, Preferences |
| F136 | Draw a multi-point path | Slice tool path mode |
| F144 | Per-position spectrogram panels | Step slider |
| F164 | Missing-data handling | NaN fill, mask component |
| F177 | Preferences window | glue Preferences |
| F180 | Image export | Save plot, normal formats, no PostScript |
| F190 | Coordinated default layout | Quicklook tab |
| F194 | Resizable windows | MDI subwindows |
| F195 | Gather windows | Canvas → Gather Windows |
| F196 | Multiple instances | Separate processes, tabs |
| F200 | About and release notes | Help → Version information; changelog |
| F202 | Developer menu | `glue -v`, console log, plugin manager |

## Features excluded

| ID | Feature | Why |
| --- | --- | --- |
| F016 | IRIS data search web page | Online search |
| F017 | SSW remote query | Online search |
| F018 | Quicklook movies before download | Online search |
| F019 | EIS data sources | EIS |
| F023 | Folded third-axis ordering | SST storage; the WCS gives IRIS axes |
| F028 | La Palma binary format | SST only |
| F029 | SINGLE_CUBE keyword | SST only |
| F041 | HCR metadata | Online context |
| F042 | OBS XML viewer | Excluded by the user |
| F043 | Pipeline log viewer | Excluded by the user |
| F044 | GOES light curve | Online context |
| F045 | SWPC flare list | Online context |
| F046 | Full-disk AIA context | Online context |
| F047 | AIA request GUI | Online context |
| F048 | Hinode/EIS co-temporal list | EIS |
| F093 | Event-finding workflow | Dropped with the tutorial |
| F103 | Reference cube | AIA and Hinode are imaging only; second windows are `wp4-m1-multi-window` |
| F107 | Reference image window | As F103 |
| F123 | Detector view | Needs Level 1 data |
| F129 | Detection-file extraction | SST only |
| F188 | Level-3 FITS generation | Non-goal |
| F189 | Conversion utilities | Legacy CRISPEX formats |
