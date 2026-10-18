# IRIS and Glue work plan

This plan drives glue-solar, with the irispy and glue work it needs, toward an IRIS quicklook in Glue covering what SolarSoft's CRISPEX offers; each item names the CRISPEX features (F001-F203) it serves. The plan and `IRIS_PLAN_PROTOTYPES/` live on glue-solar's pushed branch `plan`, never merged or opened as a PR, and it lists open work only. Each item is one glue-solar PR on a branch from `main` without the plan or prototypes, opened as a draft and marked ready and merged once CI passes (user, 2026-09-30); irispy, glue, glue-qt and astropy work stays drafts or the user's fork, on the user's direction.

## How to use this plan

- Start at [Current state](#current-state) and refresh PR states with `gh`.
- Pick an open item in the earliest open milestone; read its done-when and Depends.
- Trace the code on `main` before writing or porting a prototype; this plan overrides prototypes.
- Stage named files only.
- When an item's PR merges, delete the item and its key from other items' Depends and the checklist; the PR and git history keep the record, so Current state gets no line. Say "on main", not "released".

## Scope

In scope:

- The CRISPEX and IRIS-SolarSoft features from the user's 2026-09-30 review: 'keep' ones are M1 to M3 items (fitting M4), 'later' ones L items, and those already on main or in Glue have none (the feature map and earlier plan text are in this branch's git history).
- CRISPEX (and `iris_xfiles` for discovery) is the behavior reference; it has no license, so no code is ported.
- Features only other missions need come last ([WP13](#wp13-other-missions)).

Out of scope:

- Level-3 FITS writing (F188), EIS (F019, F048), the detector mosaic (F123, needs Level 1), and OBS XML and pipeline-log viewers (F042, F043).
- The IRIS-9 tutorial and its event-finding workflow (F093), and online context and search (GOES, AIA, HMI, SWPC, HCR, IRIS search: F016-F018, F041, F044-F047).
- AIA reference panels, reference spectra and AIA blink (F103, F107; second IRIS windows are on main, D42): AIA and Hinode cubes are imaging only, like SJIs.
- PostScript, IDL and legacy CRISPEX formats (F189): images export in normal formats, derived data as FITS or ASDF.
- SST-only inputs (F023, F028, F029, F129) and IDL details Glue replaces.

## Current state

**Resume here.** Main is at ce12fcc (#314). M0, M2 and M3 are done; M1's last item, `wp0-release-tracking`, follows each release (astropy 8.0.2 recorded); Later items are under way. No PR is open.

**Next.** 2026-10-17/18 (D85-D87): #306-#313 are on main (the full CI matrix again, saturated samples shown at their value, Stokes scaled with their noise, sessions at their values' size, per-wcslib-call locking, the review's lean pass, the coordinator forgetting removed data, 'IRIS: line fit maps'). In flight: #314 (worktree `~/Git/glue-solar-wp6-fit-builder` from 4ebb16a; its glue-qt seams go on branches of the user's fork from `~/Git/glue-qt` worktrees), then irispy draft #241 once the user merges it (glue-solar's `_starts` gives way to `starts_from_model`); then M4 work on the user's direction. Items run as an Opus implementer, a Fable review and an Opus fix pass, shipped with `ship_locked.sh`; agents follow the session archive's `RULES.md`. CI's core job runs with coverage on four xdist workers, several times slower than local runs: keep test fits small (#313's stack test fits one iteration).

**Waiting on the user.** Reviewing irispy draft #241 (`starts_from_model`); `wp0-qt68-macos-pass`; filing `wp0-qt-fitter-settings`'s PR from its pushed branch (text in the archive's `briefs/glue-qt-fitter-pr.md`); the audits' other proposals (`audit2/` in the archive); the drag-into-/Applications check of the app (`~/Downloads/Glue Solar.dmg`, built from f073033's recipe; a dmg from #275's recipe would also check Finder and Dock opening); an exact report of the linking and slider-sync problems the user saw in the app (2026-10-09), whose steps, rerun with `glue` from `iris-plan-qt6-802`, tell an app problem from a Qt 6 or glue-solar one; raising the matplotlib-free WCSAxes core prototype in person (no PR, issue or upstream notice); M4 and OM work. Offered, not started: #207's leftover (viewers opened after the time marker exists get its layer: about 10% slower steps with a second quicklook).

**Waiting on others.** irispy #209 (`wp5-irispy-line-database`, then `wp5-l-line-groups` and `wp5-l-lines-in-range`).

**Versions.** glue-core 1.27.0 and glue-qt 0.4.2 (all fixes glue-solar needs). irispy from git main (D47): 9229d06 since 2026-10-18 (#239, #240; unreleased; its last release is 0.9.1), in the `-9229` envs; the user's drafts irispy #209 (line database) and #182 (gWCS rasters, D14) are open. The glue-qt change of #223 is f19f2bca on branch `layer-action-applies` of the user's fork nabobalis/glue-qt (no PR).

**Environments and data.** The envs are in [Validation](#validation-environments-and-data). IRIS data is in `~/DATA/IRIS`, SST cubes in `~/DATA/SST/` (D62); the data disk has about 25 GB free, so keep session saves and extractions small. `/Applications/Glue Solar.app`, an older install under the old id `org.sunpy.glue-solar`, is the user's: leave it alone.

**Worktrees.** `~/Git/glue-solar` (this plan); a long probe gets its own detached main checkout as its `TREE` (`git -C ~/Git/glue-solar worktree add --detach <dir> origin/main`). irispy: `~/Git/irispy-line-database` (`line-database`, draft #209), `~/Git/irispy-saturation-mask` (`saturation-mask`, draft #239); `~/Git/irispy` is the user's (on `integrate-window`, draft #223). Upstream speed fixes are branches `perf-g*` of `~/Git/glue`, `perf-q*` of `~/Git/glue-qt` and astropy's `perf-a1-wcsaxes-pytest-import`, on the user's forks (WP0 notes); the WCSAxes core is astropy fork branches `wcsaxes-layout-core`, `-core-demos`, `-core-minimal` and `wcsaxes-layout-model` (the study: `git show 09be127:GLUE_SPEED.md`). Never touch `~/Git/astropy`, the user's own checkout.

**Tooling and archives.** Prototypes and probes of merged work were removed from `IRIS_PLAN_PROTOTYPES/` on 2026-10-17; they are in git at 7b0234a. `IRIS_PLAN_PROTOTYPES/plan_tooling/`: `ship_locked.sh KEY TITLE BODYFILE CTYPE CTEXT`, with PLAN_SCRATCH set to the session scratchpad, and `plan-item-workflow.js` for the Workflow tool (args key, item, extra, scratch). Never SendMessage an agent inside a running workflow: it starts a duplicate. The sessions' working files (the choice review with the user's marks, decision notes, plan helpers, PR descriptions, `briefs/fitting.md`) are in `IRIS_PLAN_PROTOTYPES/session_20261015.tar.gz`, a superset of `session_20261014.tar.gz`, and 2026-10-17's in `session_20261017.tar.gz` (`briefs/fit-tool/`); all stay local, out of git (the repository is public), and RESTORE.md says how to pick them up. The stress survey is GLUE_SPEED.md 'SST and IRIS stress survey, 2026-10-10' with `IRIS_PLAN_PROTOTYPES/sst_stress_20261010.tar.gz`; the profiling survey's scripts are `perf_survey_20261001.tar.gz` and `wcsaxes_study_20261001.tar.gz`, and its upstream findings are the M4 `wp0-perf-*` items.

## Decisions

Settled by the user; reopen only with the user. The session archives keep how each was reached.

- **D1:** Keep `link_hpc`, the only exact per-frame spatial link between IRIS datasets (glue #2595's use frame 0). Pair by physical type; no SJI world-time link; no equal-hop paths with different values.
- **D2:** Build in glue-solar and irispy first via glue's public registries; nothing waits for an upstream release; upstream work is M4, on the user's direction. Workarounds switch on a behavior probe, never a version.
- **D3:** Arcsec and Å on `_GlueWCS` IRIS data. sunpy Maps keep glue's plain astropy WCS, so glue autolinks and saves them; `link_hpc` links them to IRIS data on request (D64).
- **D4:** Analysis products are dataset `layer_action`s adding Data and links without a viewer; derived maps use `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`; a per-sample expression of one dataset (DN/s, radiometric calibration) is a glue derived component.
- **D5:** Baseline: released glue-core 1.27.0 and glue-qt 0.4.2, and irispy's git main (D47), on PyQt6 (D56).
- **D6:** Selection is the stock Pixel tool plus Clear point, with hover-follow and click-to-lock (D39).
- **D7:** The point is a fixed detector pixel; time is an index axis with timestamp readouts: nearest exposure, ties earlier, no match (grayed, never clamped) past half the partner's median cadence or outside its coverage. The raster is the default time master.
- **D8:** The coordinator moves sliders from 1-D nearest-index arrays and adds no glue links: no pixel-component, `JoinLink`, lambda or closure links.
- **D9:** One `Coordinator` per DataCollection behind the registered `solar:coordinate` tool; restored viewers re-register; never wrap `app.new_data_viewer`; menus use `SimpleToolMenu`.
- **D10:** Negative-step rasters keep irispy's orientation; `revert_v34=True` is the documented alternative.
- **D11:** Rest wavelength: explicit override, else the packaged vacuum line list, else none (none for multi-line windows, no km/s for continuum, never TWAVE); float Å in `meta['rest_wavelength']`, read through the WP5 helper.
- **D12:** -200 and -199 are missing, in AIA cutouts too (-199 is IRIS SolarSoft's convention, named by no header keyword); saturation is +Inf (D57); negatives are data; stored masks are uint8.
- **D13:** Sessions add the Quantity saver only if none exists, save `_GlueWCS` via `__gluestate__`, never replace glue's `VisualAttributes` serialization globally, and save added components as 1-D vectors.
- **D14:** irispy work targets LM-SAL `main`; the gWCS raster work (irispy #182) is the user's to direct.
- **D15:** The quicklook is an MDI tab with explicit viewer geometry.
- **D16:** Doppler is red minus blue, I(λ0 + Δ) − I(λ0 − Δ), positive for redshift, in `meta['doppler_sign']`.
- **D17:** Missing data are NaN; no sentinel values.
- **D18:** Do not re-implement glue: configure, default, document or call glue's API first.
- **D19:** Each quicklook tab has its own Point group, and its point drives only its own panels; a Pixel click on its slit-jaw image moves the point to the raster pixel there, and only a click on a viewer showing the frame axis stays a slit-jaw point.
- **D20:** `link_hpc` links every dataset to the first (a star); 'Open quicklook' starts ticked and the browser skips glue's autolinker.
- **D21:** A NO MATCH readout gives the nearest frame's offset; a follower moved by hand shows its own, grayed beyond half a cadence.
- **D22:** After Clear point a scanning raster's time stays at the last point's step; a sit-and-stare's exposure slider and a stack map's scan slider keep driving the time. Under a slit-jaw master with a point, a hand-moved raster exposure or scan, or a click on another, snaps back; a hand-moved slit-jaw follower keeps its frame until the next sync.
- **D23:** The quicklook marks the point with a thin line on the spectrogram and λ–t panels.
- **D24:** The moments and red-blue dialogs take a typed line center, pre-filled as D11 gives it (#179).
- **D25:** Sessions re-read IRIS files through glue's load log, with the Profile display-unit restore patch (#197).
- **D26:** Multi-instrument links and Level-3 input are not planned (D62, D82); the Hinode/SOT reader is #212.
- **D27:** The time marker is glue's own range subset (#207).
- **D29:** Every Image viewer of a sit-and-stare raster shows the exposure label and integer exposure ticks only, with no helioprojective ticks on the far edge.
- **D30:** 'Hide axes' hides the whole axes, with no pixel-coordinate ticks instead, since the mouse-over readout keeps world coordinates. On rolled views each axis label stays with its own coordinate's ticks (glue-solar's label patch), not glue's spine-based labels.
- **D31:** IRIS world values reach glue in Å and arcsec, high-level objects included, with glue's and WCSAxes' text precision (the mouse-over readout's is fixed); -TAB round trips hold to the wrapped WCS's own error (1.3-2.7e-6 px); a longitude or latitude that barely changes across a panel, beside a non-angle coordinate, loses its tick labels, while an image of the two angles keeps both.
- **D32:** Lazy loading: raw int16 through irispy's memmap view (a plane reader is the swap point if SIGBUS or resident memory bite); gzipped SJIs held as raw int16 in RAM; the mask is a glue derived component; the quicklook's spectrum never computes whole-cube profiles; the lazy loaders raise the open-file soft limit.
- **D33:** Lazy color limits count raw codes exactly over up to 512 MiB of planes per window, within 1% of the eager 99.5% limits. The < 10% memory budget is the peak RSS increase over the no-viewer post-import baseline (the absolute peak beside it); per-element budgets are tracemalloc figures; resident memory is #204.
- **D34:** The GitHub wiki stays off; its history, with the user's 2026-09-22 edit, is `IRIS_PLAN_PROTOTYPES/glue-solar-wiki-20261001.bundle`.
- **D35:** Every sunpy colormap is listed, with glue-qt's colormap icons drawn once per colormap and width (#177) until glue-qt caches them (`wp0-perf-qt`).
- **D36:** The browser's background load (#106) covers the quicklook too (its color-limit counts, archive extraction, an event-loop turn between viewers); Stop keeps the picks read in full, counted on the worker, while Esc or closing drops the load; a gzipped SJI is decompressed once; each raster file is read on its own, so a stop acts between files.
- **D37:** `link_hpc` anchors on the first IRIS dataset, linking helioprojective maps to it with `LinkSameWithUnits` (IRIS pairs keep `LinkSame`), so value selections between two maps pass through IRIS, ignoring their observers (documented); `_GlueWCS` wraps a map's 0-360° longitudes to the raster's; `sji_to_raster` applies D7's half-cadence limit on sit-and-stare rasters only; the readout's fixed precision is for IRIS Å and helioprojective arcsec only, with no angle along a sit-and-stare exposure axis; 'Regrid on time' times a stack's scans at their middle step, keeps real exposure times in `Time` and includes exactly 0.75 steps.
- **D38:** 'Go to UTC', typed in any viewer, moves the observation's time master, and the followers follow; region tools on any quicklook panel make a new subset and leave the Point alone; the Point window sits in the quicklook tab under its panels; a slit-jaw click beside a sit-and-stare slit takes the level row at any distance, as one undoable assignment.
- **D39:** A region on a quicklook's slit-jaw image reaches other data at the pointing of the frame shown when it was drawn, clipped to that frame's pixel centers, and is glue's own region on the slit-jaw image or a view showing the frame axis; a Pixel click on a picked region replaces it. Wavelength, time and point lines go on the quicklook's own panels only (a stack's λ–step panel gets only the point's); the time line snaps to the nearest step, exposure or scan; the spectrum panel's x range goes one way, to the wavelength panel; a Collapse is marked at its center; a map wavelength step redraws the wavelength and spectrum panels, without blitting. Follow/lock is on every Image viewer (Pixel stays the quicklook's default); the lock belongs to the point group, stays when the mouse moves to another viewer and at Clear point, and Undo of the lock click unlocks it. D/F move the time master from any viewer of its observation, wrapping, ignoring a Loop and without stopping playback; A/S step the current quicklook tab's wavelength sliders, else the viewer's own; Space plays the time master's looped slider first; Profile viewers get these keys; modifiers are ignored; quicklook panels get glue-qt's Tab and Backspace.
- **D40:** 'Raster overlays' (View menu, #257) toggles an observation's overlays on all its viewers, off by default and never saved: on slit-jaw images, a thin white line per step's or exposure's slit (a stack's at its timing scan; a sit-and-stare's in one column), through the frame nearest its time with no half-cadence limit, the same in every frame; on viewers of steps or exposures against slit, the dashed map line at the shown scan.
- **D41:** Spectral blink: A is what the viewer shows; 'Set blink partner here' (Coordinate menu) stores the current full slider position (dataset and every slice) as B, so two frames blink the same way and #166's temporal blink reuses it; a 'Blink' toggle runs it every 0.25, 0.5, 1 or 2 s (default 0.5 s), leaving Pixel mode, the point, the other sliders and time sync as they are.
- **D42:** Several windows (#125): the quicklook shows the browser's ticked windows (`quicklook`'s `window` takes a list): the main window (D60) with the full panels, and each other window of the same file or stack (`_same_file`: one observation, the same shape but wavelength, the same DATE_OBS and raster files) with a spectrum panel and, on a sit-and-stare raster or a stack (not a single scanning raster), a λ–time or λ–scan panel, in rows of four below; the Plugins entry and the command line open one window. Each other window's scan, step or exposure and slit pixels are linked to the shown window's with `LinkSame`, skipping linked pairs (D8's one exception), and the coordinator moves a file's windows as one cube: with the point, with each other, by a Pixel click on any of their panels, and by time sync when there is no point. The Point window lists the shown window and the slit-jaw images only.
- **D43:** Default stretches on quicklook panels (#133): slit-jaw 1330 and 1400 log, 2796 sqrt, 2832 linear; raster windows by band: FUV (TWAVE < 2000 Å) log, Mg II k and h (within 10 Å of 2800 Å) sqrt, other NUV linear; color limits stay 99.5%; glue's layer controls change either.
- **D44:** Line list: the main lines ship as a small glue-solar table at NIST ASD vacuum wavelengths (#134), each with a toggle, on the quicklook's spectrum panels and any Profile viewer of IRIS data; a larger database goes to irispy (`wp5-irispy-line-database`); line groups (`wp5-l-line-groups`) and 'lines in this range' (`wp5-l-lines-in-range`) are lower priority.
- **D45:** The line moments dialog requires the line center and a range (in km/s, D57), so its blocking and memory limits hold; the continuum is optional (D48).
- **D46:** Line moments (#136) take raster windows and stacks (each scan at its own coordinates, #180) and refuse other data with a message. The map `<label> moments <center>` has meta OBSID, STARTOBS, `moments_center` and `moments_velocity_range`, never INSTRUME or `Time`, so it groups with its observation but stays out of time sync. `calculate_moments` runs on glue-qt's `Worker` on the range's wavelengths only, at most 2**21 samples a call; a pixel missing throughout the range is NaN in every map, other missing and negative samples count as irispy's 0; the status bar shows the run.
- **D47:** The git repositories are the versions that count: glue-solar depends on irispy's git main (Python ≥ 3.13 since irispy #208) and calls its API directly, with no probe for what main has; PyPI releases of glue-solar and irispy wait until the changes settle and the upstream fixes are in (M4).
- **D48:** Continuum windows: Å ranges in one optional field (`1401.6-1402.1, 1403.5-1404.3`, either end first), which `subtract_background` fits with a constant for one window and a straight line for more, so one window's slope is never extrapolated across the line; a pixel with too few continuum samples is NaN in every map; `moments_continuum` and `moments_continuum_degree` go in the meta only with a continuum.
- **D49:** Saturation (sources in `IRIS_PLAN_PROTOTYPES/saturation_sources_20261008.tar.gz` and `saturation_observation_20261008.tar.gz`; flare files in `~/DATA/IRIS/saturated/`): Level 2 never holds +Inf; 16182 DN (raw 32760) is the writer's clipping ceiling, so a sample there is saturated or merely bright; the header counts (NSATPIX, TSATPXn, HISTORY) never count a file's saturated samples, so the status bar counts the data's. irispy detects saturation (D57; the open questions are in irispy #226). Line moments get DN/s from the loader's `per_second` on the slab already read (#141).
- **D50:** Zoom 1:1 is removed (#302, D83); the color bar (#144) stays right of the image, ticks only; frame and movie export (#145) stays at 10 frames per second; irispy's one HISTORY card per keyword stays, the saturation recipe (#146) reading HISTORY in glue's terminal.
- **D51:** `glue-solar[density]` installs fiasco's git main (plasmapy, h5py; CHIANTI downloads on first use) for irispy's `density_diagnostic` and the line ratio dialog's O IV preset (#155, #163); Mg II features take saturation from irispy (D57); the mean spectrum (#152) stays one all-scans float32 mean; red-blue (#150) keeps its per-step DN/s limit; File → Open leaves linking AIA cutouts to 'IRIS: link helioprojective coordinates'; Path diagrams keep L and a new set per Enter (#151); Measure (#147) gets key U.
- **D52:** The line-group items wait for irispy #209; the SOT reader's test files live in irispy's `irispy/data/test/sot/`; ticks the browser filter hides still load (#185); a Profile range sets the moments range for a pre-filled line center too (#180); Undo or Redo of a slit-jaw click returns the slit-jaw viewer to the clicked frame (#193).
- **D53:** 'Light curves of the shown windows and SJI' (#208, #236) adds a 1-D Data (Time, value) per raster window and SJI channel the point's quicklook shows, recomputed as the point moves, in one datetime Scatter plot the time marker marks, with an 'ECSV (with Time)' exporter; #183's 'Light curve of this window' stays, since a subset cannot follow the point across SJI frames.
- **D54:** irispy fixes are draft PRs on LM-SAL/irispy from a branch of origin/main in `~/Git/irispy-<branch>`, with a test and a changelog fragment named after the PR; the user reviews and merges. WCSLIB is never re-implemented: the slow raster world-to-pixel is accepted (R8; D67 is the one exception). glue-solar fills NaN itself (D17).
- **D55:** macOS app (#216): for the user's Mac only, unsigned, Apple Silicon, built locally into a .dmg with an Applications shortcut; no signing, notarization or CI build. Its recipe in glue-solar reuses glue-standalone-apps' PyInstaller spec and hooks (D18, D77) and is rebuilt as the plan's last deliverable (`wp9-m4-release-updates`).
- **D56:** Qt 6 (#214): glue-solar depends on PyQt6 (glue-qt without its PyQt5 `qt` extra), its import refuses Qt 5 with a message before anything registers, its tests, CI and macOS app use PyQt6 (the floor 6.11 since #266, D72), and PyQt5 is not tested.
- **D57:** After irispy #235: its scaled reads give +Inf at the Level 2 ceiling (raw 32760) and its analyses flag saturation from unmasked +Inf, with no `saturation_limit`; `calculate_moments` takes a km/s `velocity_range`, not `wings`; `calculate_red_blue_asymmetry` drops `continuum_windows` and renames `degree` to `spline_degree`; `subtract_background` keeps +Inf where it fits no background (#237). glue-solar follows (#213): lazy reads map raw 32760 to +Inf too (replacing D12's and D49's finite ceiling); the moments dialog, and a Profile range, give a km/s range around the line center (default ±107 km/s, ±0.5 Å at Si IV 1402.77); a continuum costs one irispy call per slab.
- **D58:** Row and column cuts (F145): no port of the user's drafts glue #2596 or glue-qt #70. #183's light curve (a `SliceSubsetState` following the point) generalizes to any non-wavelength axis for the following cuts of raster maps along step and slit ('Row at the point', 'Column at the point', #224), with no glue patch; the slit-jaw cuts are documented.
- **D59:** Every analysis action accepts a stack of raster scans, each scan computed at its own coordinates and exposure times as line moments do, giving maps of (scan, step, slit) (#220); a stack's UV bursts and calibration use its first date (D72).
- **D60:** The browser picks which ticked window is the quicklook's main window, with the full panels (map, spectrogram, λ-step, λ-time or λ-scan), Mg II k by default; 'Show this window's panels' on a spectrum panel switches it, keeping the point, the time and the other windows' panels (#225).
- **D61:** Image viewer buttons: Follow/lock, Modes, Coordinate and View come right after Home, Pan and Zoom, so glue's region tools overflow first; the Coordinate menu holds the time entries and the 'Point' (Clear point, light curves, row and column cuts) and 'Blink' submenus; 'IRIS: ' prefixes all glue-solar adds to glue's shared menus and nothing in its own toolbar menus; data actions name their data where narrow, group by data kind and hide where they cannot apply (a probe-gated `applies(data)`; a branch on the user's glue-qt fork); Path diagram has its own icon and status tip; matplotlib's g/G, l/k/L and p/o keys are dropped as f/s are (g/G back on Profile viewers, D72); glue-solar's text is American (D72).
- **D62:** SST data: the SST archive's SSTRED SOLARNET cubes (large, not co-aligned to IRIS), opened as FITS, the biggest testing speed, memory and I/O; the IRIS-SST database's custom Level 3 CRISPEX files are unsupported for now. `~/DATA/SST/` holds obs 492 (CRISP Ca II 8542, Fe I 6173 and 6302 full-Stokes mosaics), obs 495 (CHROMIS Ca II K), obs 498 (H-beta), obs 167 (Fe I 6173 Stokes) and obs 171 (H-alpha); the 2015-09-17 IRIS raster 3630104144 is in `~/DATA/IRIS`.
- **D63:** The SST and IRIS stress survey (GLUE_SPEED.md 'SST and IRIS stress survey, 2026-10-10', SST1-SST13): its glue-solar fixes are on main; the rest is upstream, in `wp0-perf-qt` (SST8), `wp0-perf-core-links` (SST9), `wp0-perf-core-stats-io` (SST10 as R32, with D70's workaround only) and `wp0-astropy-19174` (SST1); SST13 gets no action.
- **D64:** Link scope (SST3): data from outside the IRIS observations is linked to IRIS only on request, through 'IRIS: link helioprojective coordinates', never by `keep_hpc_linked` as data load or a quicklook opens: SST cubes, other FITS files, sunpy maps (#226), and, since D72, an IRIS observation's own AIA cutouts and SOT cubes (#256).
- **D65:** A quicklook per instrument, SST first: CRISP and CHROMIS SSTRED SOLARNET cubes (D62; time, Stokes, wavelength, y, x, without a length-1 Stokes axis, #232) open one in its own tab from the browser and the Plugins menu, linked to an IRIS quicklook only on request (D64), time-synced, with D68's panels (a virtual slit in place of IRIS's spectrogram). Every panel of either quicklook turns on and off (#228). Other cubes get one from their axes (D78). #307 keeps only Stokes scaling and noise level.
- **D66:** Panel toggles (#228): a checkable 'Panels' list right of the Point window in the quicklook's bottom strip, with an entry per main-window panel and slit-jaw image and a group per other window, on SST too. Shown panels re-tile at a toggle, empty rows go, and manual moves and resizes are lost; a burst of toggles gets one layout, and a panel of unchanged size does not redraw. Sessions leave out panels turned off, so they open shown (wp4-l-restored-strip). A slit-jaw time master turned back on moves to its frame nearest the raster's time.
- **D67:** SST loader (#227): once linked, an SST region or point reaches IRIS data, which lack the cube's time and wavelength, at the scan nearest each IRIS frame's time and the line core. The wavelength axis keeps each scan's nominal values; the cavity-error lookup (CWDIS3) is its own documented component. As D54's one exception, the loader inverts its coordinates itself (a linear solve per scan and tuning of SSTRED's corner tables, wcslib for larger tables); wcslib's -TAB inverse is `wp0-wcslib-tab-inverse`.
- **D68:** SST quicklook (#230): one cube per tab (the browser lists each cube of an archive folder; another opens in its own tab, time-synced). Row 1: the map (wavelength and Stokes sliders), a second wavelength map and the virtual slit (wavelength against y) through the point; row 2: the I, Q, U and V spectra at the point (I only on CHROMIS); row 3: wavelength against time and the light curve at the point; the Point window and Panels list below, as on IRIS.
- **D69:** glue-solar is unreleased, so sessions saved by older glue-solar need not open: no back-compat patches or aliases. Sessions of the current code still save and restore, and items keep their session checks.
- **D70:** SST10: as an exception to D63, SST cubes answer glue's sampled color-limit statistics from 16 evenly spaced planes of 25 rows and 25 columns (sampling: #248), tracked under R32 (`wp0-perf-core-stats-io`) until glue samples cheaply itself.
- **D71:** Every quicklook, IRIS and SST, opens its image panels with the axes hidden, as 'Hide axes' does; an 'Axes' box at the top of the Panels list turns them on and off for all of its image panels; each panel's 'Hide axes' button stays (#231). Since #302 (D83), View → Hide axes on any quicklook image panel is the one axes control; the Axes box and the Preferences pane are gone.
- **D72:** The choice review (2026-10-11; `choices/` in the session archive): every PROVISIONAL of #100-#232 not changed stands and is no longer provisional. The changes are on main, except 206-3 and 206-7 (#297), 205-1 (wp3-l-restore-irispy-meta), 160-x1 (`wp9-m4-release-updates`) and 216-2 (`wp0-qt-run-script`); D56, D59, D61 and D64 read as they changed. Other rules: the analyses keep DN/s in float64 (213-3); the mean spectrum leaves saturated samples out and counts them (213-7); calibration takes rebinned windows (220-5); menu help stays as tooltips (222-3); the cavity error stays in nm, the guide giving km/s (227-2); panel toggles keep their 0 ms layout (228-6); the app has its own icon (216-9); every patch or override on main has a register row with its upstream route, updated by the PR that adds or retires it (D63-2).
- **D73:** After the audit of #226-#235 (`audit/` in the session archive): an SST point reaches linked IRIS data through the widened `_to_linked_pixel_coords` patch (#246); the WCS locks around glue's `world2pixel_single_axis` and `_to_linked_pixel_coords` are lock-only wrappers installed whatever the probes say, retiring with astropy#19174's fix only (#251); an SST cube's WCS has its own `RLock`, linked or not (#240); overrides fixing no upstream fault get 'none: glue-solar feature' or 'kept by decision' rows; 'Glue Session including data' failing on SST cubes and lazy IRIS windows is documented, not a defect.
- **D74:** Whether to drop glue-solar's session support: settled by D81 (kept).
- **D75:** The real-data acceptance run (2026-10-12, main 838d64a; `acceptance/` in the session archive) followed every user guide on full-size data; its fixes are on main, and its session items are #289 and #297's path-diagram case. On macOS `QSettings('glue-solar', 'glue-solar')` ignores a temporary HOME: glue-solar's conftest patches `iris.QSettings`, and probes must too.
- **D76:** The choice review's third pass (#233-#240's 44 choices, chunks d0-d7): 36 kept, every other PROVISIONAL of #233-#240 included; calibration keeps the first scan's dispersion and solid angle but refuses a stack whose scans' CDELT1-3 differ (237-1, 238-6). The changes are on main.
- **D77:** The PyQt6 6.11 floor env keeps the astropy 8.0.0 and ndcube 2.4.0 floors. The glue team allows copying glue-standalone-apps' spec and hooks (216-8, #275). App checks may launch the built app on the user's desktop with `open`, as the Finder does.
- **D78:** One fill builds every quicklook from a panel table per data kind: IRIS raster, slit-jaw only, SST and generic (#277). The generic table follows the cube's WCS axes (spectral, celestial, time, Stokes), giving SST-like panels, with λ–time and the light curve only for a time axis, from a 'Quicklook…' layer action on any cube with one spectral and two spatial axes.
- **D79:** The choice review's fourth pass (#241-#275's 139 choices, chunks d8-h2 in `session_20261015.tar.gz`): 122 kept, 258-1, 262-5, 265-6 and 268-2 after discussion; the changes are on main, 267-7 dropped (D86); 265-8 was a bug (#270); 259-1 to 259-3: D81.
- **D80:** The choice review's fifth pass (#276-#283's 28 choices, chunks h3-i0): 27 kept; on 283-3 (prose says `DN / s` too) the user noted "Make it all match". Changed: 283-4 → #284.
- **D81:** Sessions stay (D74's first option), so the held session items go ahead; `wp0-core-session-reports` and `wp0-core-quantity-saver` stay M4. Fitting (`briefs/fitting.md` in the session archive): one fitter per Profile viewer as a glue-solar stopgap (#287, 259-2); the glue-qt fix, the check-box one-liner included, on a branch of the user's fork with no PR (`wp0-qt-fitter-settings`), the check-box shim staying (259-3); the check boxes stay and 'Number of lines' is added (#291, 259-1); since #314 a component list in the IRIS fitter's own Settings replaces both and the check-box shim (D86), while fits from the line list or a line table of the fitter's own wait. The flaky SST thread test is fixed (#285).

- **D82:** User (2026-10-16): keep the plan concise and the code lean; port CRISPEX's ideas to glue better, faster, sleeker and nicer, not one to one. The plan keeps rules and open items only (git keeps the history; Current state gets no per-PR line), and items with nothing to do are dropped (wp0-optional-proposals, wp0-track-qt66, wp0-track-line-layers, wp8-m3-level3-input, wp1-m3-multi-instrument, wp13-height-cubes; wp0-qt68-cocoa joins wp0-qt68-macos-pass). The audits (`audit2/` in the session archive) found about 820 source and 500 test lines that can go with no visible change (the four `-lean-` items) and one bug (#288). Held for the user: wp13-l-restored-second-map and #297, which a quicklook restored by re-running `quicklook()`, or dropping 'IRIS: restore last session', would replace; and every feature cut or redesign in the audits.

- **D83:** User (2026-10-16), on the audits: a session restores a quicklook by re-running `quicklook()` from a saved recipe (#301, replacing the restored-strip and second-map items); 'IRIS: restore last session' stays, so #297 goes ahead; the irispy-meta branch is dropped. Four consolidations (reopening D4, D24, D45, D48): #296, #299, #298 and #300; and #302 (one axes control, reopening D71 and 221-6; no Zoom 1:1, reopening D50). The user guide is rewritten as task pages of about 9,700 words in all (the wp9-l-guide- items, after the features). astropy 8.0.2 becomes the baseline: its envs are rebuilt conda-native; the floors stay.

- **D84:** User (2026-10-16), the choice review's sixth pass: the 54 choices of #276-#295 (chunks h3-j2), all kept; 283-4 was done as #284.

- **D85:** User (2026-10-17): saturated samples show everywhere (images, spectra, light curves) at their stored value, 16182 DN or its DN / s, not +Inf, which glue skips; irispy keeps the value and marks saturation in its mask, as LM-SAL/irispy #239, and glue-solar follows once it merges (#308). Reverses D57's +Inf.

- **D86:** User (2026-10-17): units print as astropy's default (`str(unit)`: 'km / s', 'DN / s', and WCS `world_axis_units`' VOUnit), with no code overriding astropy's unit formatting anywhere; irispy's text stays as it is (drops 267-7's request, D79). The user merged irispy #239 and #240 on 2026-10-18 (irispy main 9229d06): glue-solar main's saturation tests fail against it until #308 merges, so that item ships first and the others rebase on it. Fitting goes toward models composed in glue's Fit tab and fitted over the window with `parallel_fit_dask`: first fitting every pixel from the Fit tab's fit (#313), then a model builder in the Fit tab's Settings (#314), with per-pixel starts in glue-solar first and then as an irispy draft (`wp0-irispy-fit-starts`); a jdaviz-style fitting panel is not planned. The design brief, with its probes, is `briefs/fit-tool/` in the session archive.

- **D87:** User (2026-10-17), on D85's saturated samples in fits: a saturated sample is a lower bound, not a measurement, so fits leave it out: the Profile Fit tab drops samples the layer's mask marks saturated and its summary says how many it left out, as the window fit (#313) and irispy do (a check: with the peak 4x over the ceiling, fitting them at their value gave 0.29x the amplitude and 1.56x the width; leaving them out gave both exactly, until the whole core saturates, where those spectra are flagged). A rebinned bin is saturated only when all its samples are (as implemented). User (2026-10-18): for a profile combining several pixels (a region's Mean, Median or Sum, or a whole-data layer), a wavelength is left out only where every pixel it combines is saturated, and the fit notes the wavelengths whose mean includes saturated pixels (biased low): with any saturated pixel leaving a wavelength out, a flare window's Mean fit lost its core and gave every pixel of the window fit a broken start.

## Milestones

A milestone is done when it has no items left. M0, M2 (analysis, display and export) and M3 (specialist) are done.

- **M1: navigation and spectral parity.**
- **L: Later.** Deferred by the user (sessions, browser search, light curves); not a gate.
- **M4: upstreaming.** On the user's direction: upstream PRs, reports and the user's drafts, autolink matrix, fit tool; a release with a fix retires its workaround.
- **OM: Other missions.** Last: WP13.

### Checklist by milestone

**M1**
- WP0: `wp0-release-tracking`

**Later**
- WP0: `wp0-qt68-macos-pass`
- WP5: `wp5-l-line-groups`, `wp5-l-lines-in-range`, `wp5-irispy-line-database`

**M4**
- WP0: `wp0-irispy-fit-starts`, `wp0-qt-fitter-settings`, `wp0-irispy-requests`, `wp0-core-image-artist-bugs`, `wp0-core-wcslink-lists`, `wp0-qt-large-data-cancel`, `wp0-astropy-19174`, `wp0-stack-validation`, `wp0-user-review`, `wp0-own-draft-updates`, `wp0-core-quantity-saver`, `wp0-core-derived-units`, `wp0-qt-aggregate-slice`, `wp0-core-datetime-export`, `wp0-core-session-reports`, `wp0-report-candidates`, `wp0-perf-core-draw`, `wp0-astropy-wcsaxes-bugs`, `wp0-perf-core-links`, `wp0-perf-core-stats-io`, `wp0-perf-qt`, `wp0-perf-astropy-irispy`, `wp0-wcslib-tab-inverse`, `wp0-qt-run-script`
- WP1: `wp1-m4-autolink-matrix`
- WP9: `wp9-m4-release-updates`

## Work packages

### WP0: Upstream integration and reports

Upstream work in glue, glue-qt, irispy and astropy that retires the workarounds in `glue_solar/glue_patches.py`.

**M1**

- [ ] **M1** `wp0-release-tracking`: After each glue-core, glue-qt or astropy release past 1.27.0/0.4.2/8.0.2, raise floors and retire workarounds; raise the astropy floor to the first release bundling WCSLIB 8.9 (astropy main 777e811427), whose `wcserr_set` no longer leaks 64 B per pixel outside a -TAB table. Done when each release has a line here naming its PRs, floors and retired workarounds.
  - astropy 8.0.2 (2026-10-15): no PR; floors unchanged (still WCSLIB 8.6); the baseline envs move to it (`iris-plan-qt6-802`, D83) and pass the suite as on 8.0.1; #20221 fixes the wrong second-crossing longitude ticks (seen on sit-and-stare 3660259102, not rolled SJIs), the '#' auto-placement TypeError and the `simplify_labels` IndexError; #19174 still crashes without the lock; no workaround retired.

**L**

- [ ] **L** `wp0-qt68-macos-pass` (F203): Manual macOS check of glue-qt #68 (font, menus, Cmd-Tab, Dock name) on PyQt6; once glue-qt releases #68, check that conda-forge's glue-qt requires `pyobjc-framework-cocoa` on macOS. Done when both are recorded.

**M4**

- [ ] **M4** `wp0-irispy-fit-starts` (D86): draft LM-SAL/irispy#241 (branch `fit-starts`, worktree `~/Git/irispy-fit-starts`, test env `irispy-fit-starts`): `irispy.utils.fitting.starts_from_model(model, cube)`, #313' per-pixel starts as EISPAC's `scale_guess`, plus each line of a blend searching only samples nearer its own center (PROVISIONAL; Mg II k two Gaussians: 2,078 of 2,313 good fits against 1,885 without). glue-solar's `_starts` gives way to it once merged. Done when the user has reviewed it.
- [ ] **M4** `wp0-irispy-requests`: Get irispy's merged #197-#199, #201 and #205-#207 released (0.10.0; changelog fragments in place; D47) and settle the irispy-side checks (exposure times, rolled-SJI gWCS, binned `slit x position`, per-step pointing). Done when a release has them and each check has a test or user decision.
- [ ] **M4** `wp0-core-image-artist-bugs`: Core PR: a hidden Pixel crosshair reappears at (0, 0), `translate_pixel` raises a bare `Exception`, and a linked-layer Pixel crosshair uses its own dataset instead of the viewer's reference data (#107). Done when all three reproducers pass on a release.
- [ ] **M4** `wp0-qt-large-data-cancel`: glue-qt report: cancelling the 'Add large data set?' modal breaks later viewers. Done when filed or declined.
- [ ] **M4** `wp0-astropy-19174`: Add the IRIS -TAB WCS thread crash to astropy#19174, with the survey's non-IRIS reproducer: an SST cube beside an IRIS quicklook (SST1; `verify/beside.py` or `scripts/sst.py --iris sit` without a lock, in `sst_stress_20261010.tar.gz`). Also (#226): glue's `WCSLink.__init__` reads `wcs.wcs.lng` and `.lat` on the struct, outside any lock, when File > Open autolinks a dataset beside a linked SST cube or map; lock the WCS objects there, or include it in the report. Done when reproduced without `WCS_LOCK` and posted or declined.
- [ ] **M4** `wp0-stack-validation`: Merge the upstream heads (core #2595, #2597-#2599, #2601; Qt #70, #74, #75) and run the Qt and `glue_solar` suites. They are the user's drafts: core #2595 WCS autolink, #2597 session cmap and meta, #2598 correlated-axis inverse, #2599 datetime epoch (fix its codestyle), #2601 Profile WCSAxes (contains #2596, Slice profile); Qt #70 Profile sliders and km/s axis, #74 cursor readout, #75 time slider labels. Done when pass counts are recorded.
- [ ] **M4** `wp0-user-review`: The user reviews each upstream draft before it is ready; glue-qt #68 (macOS integration) and #69 (a CI fix overlapping #65) are ready, and glue PRs fail `py311-test-visual` until dhomeier's ready glue #2592 (visual references) merges. Done when each is merged, closed or parked. Depends: wp0-stack-validation.
- [ ] **M4** `wp0-own-draft-updates`: Amend #2595 to keep time axes out of `wcs_autolink`, and Qt #74 to show Solar X/Y. Done when both pass their suites.
- [ ] **M4** `wp0-core-quantity-saver`: Core `u.Quantity` saver (D13) that loads glue-solar's fallback record. Done when its test round-trips Quantities in `Data.meta`.
- [ ] **M4** `wp0-core-derived-units`: Core PR saving `DerivedComponent.units`. Done when its test round-trips `units='DN/s'` and older records still load.
- [ ] **M4** `wp0-qt-aggregate-slice`: glue-qt report and PR: a slider move turns a Profile Collapse `AggregateSlice` into an int. Done when filed or declined.
- [ ] **M4** `wp0-core-datetime-export`: Report that core's exporters fail on datetime64 components (HDF5, FITS, VOTable raise; CSV writes int64). Done when filed or declined.
- [ ] **M4** `wp0-core-session-reports`: Report the 1.27.0 session-restore failures (`stretch_global=False`, lost `stretch_parameters`, sunpy colormap names, a style's `preferred_cmap`, object-array meta, `LinkSameWithUnits`). Done when each is filed or declined.
- [ ] **M4** `wp0-astropy-wcsaxes-bugs`: astropy 8.0.2 WCSAxes bugs from the 2026-10-01 study (GLUE_SPEED.md 'Stock astropy problems found on the way'): `format_coord` raises on a 1-D WCSAxes; line grids, `plot_coord` and `scatter_coord` fail on three-coordinate views such as both Si IV panels; with a sliced-out coordinate, `invert_xaxis()` makes every later draw raise (8.0.2); an off-view tickable gridline raises; zero-size axes raise on draw; a WCSAxes figure cannot be unpickled. Work around those glue-solar hits (a minimized panel may reach zero size); re-check the rest on astropy main and report on the user's direction. Done when each is worked around, filed or declined.
- [ ] **M4** `wp0-qt-fitter-settings` (D81): the user files the glue-qt PR from https://github.com/nabobalis/glue-qt/tree/fitter-settings (f28fa72d: `ProfileTools` keeps one fitter per fitter class for Settings and each fit; f3aad9c0: `update_fitter_from_settings` reads each form item's `value`; each with a test; text in the archive's `briefs/glue-qt-fitter-pr.md`). Done when it is filed.
- [ ] **M4** `wp0-report-candidates`: Other reports, filed only on the user's direction. Done when each is filed or declined.
  - core's path slicer (#151's `PathTool`/`PathData` work around it): `PathSlicedCoordinates` names one world axis per kept pixel axis (IndexError in `axis_label` on SJIs); `PathSlicedData` gives 0 off the data, casts `Time` to float, returns (1, 1) for one pixel, sends its own world components to the parent (a Profile of a diagram raises) and has no saver; `BasePathSlicerMode` works on 3-D data only and, with `persistent = False`, Enter redraws a removed patch; `create_trace` slices every layer along the reference's pixel axes; later Enters update only the first path, and every pair of paths is linked; `drive_parent_slice` truncates the diagram's y with `int` and does not clamp it per axis.
  - core's dask percentile sampling reads only chunk corners.
  - glue-qt ignores Fit constraints; its playback timer outlives the viewer and survives slider rebuilds.
  - glue-qt keys: Tab never cycles windows; keys are looked up by exact viewer class (`QuicklookImageViewer` gets none); Table viewer keys sit on `DataTableModel`; canvases keep matplotlib's keys (F, S, O, P, L, K; G over WCSAxes raises `NotImplementedError`); the Image viewer's profile button has no tooltip.
  - glue-qt Profile Navigate and Collapse compare display-unit x with native values; Collapse drops the range's last sample; an empty `AggregateSlice` raises when drawn.
  - glue's FITS subset-mask importer refuses unsigned integer masks.
  - glue-core's profile thread (`_calculate_profile_thread`, `compute_statistic`) enters `warnings.catch_warnings` off the main thread, which on Python 3.13 swaps the process-wide filters, so its 'ignore all' can stay and silence other warnings (NEXP_PRP); Python 3.14's context-aware warnings fix it (#261).
  - glue-core 1.27.0's FITS exporter fails on a uint8 component in a subset export (`UnboundLocalError` on `blank`) and writes no dask array (glue-solar's `export_fits`).
  - glue-qt's `sync_state_from_sliders` rewrites every slice when any slider moves, ending a Profile Collapse on another axis (documented).
  - wcslib's -TAB inverse stops at 1e-10° (`tab.c`), so IRIS raster round trips hold only to about 1.3e-6 px.
  - fiasco main: `get_chianti_catalog` skips every ion file when the database path contains a skip name such as `em`, `ip` or `dem` as a substring (/Users/emily builds no ions); its progress bar fails off the main thread (the O IV preset passes `show_progress=False`).
  - glue-qt computes a Profile layer over 1e7 samples on a thread, and changing `x_att` meanwhile can cache a profile along the old axis.
  - glue-core's `ApplySubsetState` Redo runs `do` again instead of restoring the subset states it made.
  - glue-core's `compute_statistic` with a `SliceSubsetState` returns only the subset's samples along kept axes, so a Profile with wavelength on x cannot draw a band subset wider than one pixel (#183).
  - glue-core's path slicer has no session support: the collection saver calls `component_ids()` on every dataset (any `PathSlicedData` fails), and `PathSlicedData` and `PathRelativeLink` have no savers.
  - glue-core's `ProfileViewerState._update_priority` ranks `x_display_unit` with `x_att`, so a restored Profile on any axis but the reference data's first raises 'value Angstrom is not in valid choices'.
  - echo's `_find_combo_data` returns the first equal combo entry, so equal-color colormaps show and save another's name (#194).
  - with glue #2595, raster pixel ROIs in an SJI take #2595's frame-0 WCSLink instead of `link_hpc`'s per-frame path; amend #2595 or document it.
  - glue-qt's data collection sets the edit subset from its selection, so a selected dataset makes the next Pixel click a new subset (#288).
  - glue-qt gives a fitter's `summarize` neither the layer nor the viewer (#291).
  - irispy's `maps_from_fit` flags a parameter as at a bound within 1e-8 of the map's largest absolute value, so a few runaway fits (amplitudes near 1e10 on a flare raster) mark most amplitudes up to about 100 DN as at their 0 bound (#313' review; an irispy draft on the user's direction).
  - astropy's analytic Jacobian (`fitting.py` `_wrap_deriv`) drops a tied parameter's part, so tied fits need an estimated one (#291).
  - astropy's `fitter_to_model_params_array` computes each tie from the parameters before any tie (the `Model.parameters` setter copies the array), so a tie to a tied parameter reads its stale start; the IRIS fitter follows each tie to its chain's root (#314).
  - glue's axis labels on SST cubes: `''` for Stokes, and `Hplt` from a glue indexing bug (#227).
  - glue-qt keeps any dataset an Image viewer showed alive after it is removed, the viewer closed or its tab closed (0.4.2 and main; #312's review): `GlueApplication._clear_dashboard` (application.py:678-688) only hides the reparented `options_widget()` (its `viewer_state` and `MultiSliceWidgetHelper._reference_data`, slice_widget.py:79-84) and `layer_view()`, and `LayerArtistView.on_artist_add` (layer_artist_model.py:356-373) adds a style editor per layer artist to a `QStackedLayout` that nothing empties; so a removed observation's memory map stays open. Fix: delete a closed viewer's options and layer widgets and a removed artist's style editor.
- [ ] **M4** `wp0-perf-core-draw`: Profiling survey 2026-10-01 (every finding with its measurements, causes, fixes and scripts: `GLUE_SPEED.md`; ranked page: https://claude.ai/artifact/JgL2D9fjWp72GrXsrSx1nN), glue-core draw path, measured only: (1) `_set_wcs` on every slice change resets the axis labels through WCSAxes `set_xlabel`/`set_ylabel`, 4 eager tick placements, 66% of an SJI frame step (R1); (2) hidden subset layers still update and redraw (R4); (3) a Pixel point is drawn as a full-view RGBA image (R7); (4) a collapsed map re-aggregates on every redraw (R10); (5) float64 composite and 72-dpi FRB on large or HiDPI panels (R19); (6) image-only changes (contrast, a wavelength step) redraw the whole WCSAxes figure (R18). astrofrog's draft glue #2507 speeds up slicing. Done when each is filed, merged or declined on the user's direction.
- [ ] **M4** `wp0-core-wcslink-lists`: Core PR: `WCSLink.__init__` (`glue/plugins/wcs_autolinking/wcs_autolinking.py`, 1.27.0 and main) binds `slicing_axes1 = slicing_axes2 = []`, and the two physical-type lists the same way, so without two celestial WCSes both datasets' axes go into one list: a map opened after an SST cube raises ValueError 'Cannot slice WCS', not `IncompatibleWCS`, and glue shows 'Could not load data' though the map loads (glue-solar documents opening the map first, #227); a 5-axis Stokes cube opened before a 4-axis intensity cube raises IndexError at wcs_autolinking.py:206 on that and every later File > Open (D75). Done when merged and released, and glue-solar's note is dropped.
- [ ] **M4** `wp0-perf-core-links`: glue-core links, measured only: (1) a raster ROI on a linked SJI inverts the raster WCS per screen pixel once per attribute (R2); (2) `discover_links` restarts after each link, about O(N³) (R6); (3) any link change drops every linked mask (R11); (4) removing a dataset runs one update per link (R12); (5) each append runs a full update with an all-pairs pixel-cid pass (R24); (6) the WCS autolinker suggests every pair (R28). SST9: a Path diagram's link change makes the Profile recompute its whole-cube data layer (5.35 s on 8542), R11's Profile data-layer case (`data.py:640-660` → `viewer.py:288-307` → `ProfileLayerArtist.update`). Done when each is filed, merged or declined.
- [ ] **M4** `wp0-perf-core-stats-io`: glue-core statistics, IO and startup, measured only: the Profile y-limit reset computes whole-cube profiles on the main thread (R14); `compute_statistic` copies chunks to float64 (R21); the Histogram builds full-cube masks for a Pixel subset (R23); session save re-serializes everything per pass and writes broadcast components in full (R20); arithmetic with a constant upcasts float32 (R27); startup imports IPython, scipy.optimize and dask eagerly (R22, R25, R26); `import glue` imports glue-qt through `glue.config` (R31). From the 2026-10-10 survey: SST10, as R32: a new Image viewer's Min/Max samples 10,000 random indices over all axes, about 0.7 GB of random reads on a cold memory-mapped cube (sample planes or rows, or sort the indices by page); SST4: R14 and R21 at 10 GB, the Profile button taking 27.4 s cold, 21.2 s of it frozen, as `compute_statistic` chunks only along the profile axis (a whole λ plane per chunk, its float64 copy about 1 GB). Done when each is filed, merged or declined.
- [ ] **M4** `wp0-perf-qt`: glue-qt, measured only: the profile worker polls at 25 Hz and threads by the parent cube's size, so the quicklook spectrum lands about 250 ms late (R3); hidden tabs' canvases do full Agg redraws (R9); the data tree rebuilds and reloads icons per added dataset (R15); slider drags queue every position (R16); colormap combos render every icon on creation and resize (R17; the fix is an icon cache in `glue_qt/utils/colors.py`, which retires glue-solar's, D35); the splash appears late (R29); QtQuick is imported on Qt5 and `QFont('Courier')` builds macOS's alias table (R30); glue-core's `show_axes` state has no control (an axes-options checkbox would let any viewer drop its axes, as glue-solar's Hide axes button does; others' ready glue #2128 is a Hide axes PR). SST8: an SST Pixel drag takes 170-201 ms with a Profile open and 31-34 ms without, about 105 ms of it R3's polling wait and 50 ms the Profile's extra draws. Done when each is filed, merged or declined.
- [ ] **M4** `wp0-wcslib-tab-inverse` (user, 2026-10-09; not started): fix the slow -TAB inverse in WCSLIB's `tab.c` itself (R8, D54), on a fresh astropy clone, as a branch on the user's astropy fork and a diff for WCSLIB's author. Done when the user has both.
- [ ] **M4** `wp0-perf-astropy-irispy`: astropy and irispy, measured only: WCSAxes re-places every tick on every draw with one WCS call per coordinate (R5; GLUE_SPEED.md 'WCSAxes tick rendering', scripts in `IRIS_PLAN_PROTOTYPES/wcsaxes_study_20261001.tar.gz`): a per-placement memo (SJI draw −25%) then batched calls (−50%, needs its failing-WCS fixes) as the first two astropy PRs, a placement cache only after those, and glue's `_set_wcs` label fix (`wp0-perf-core-draw`) before any of them; a gzipped FITS is decompressed 4-5 times on open (R13; irispy main's `read_files` decompresses once); irispy's sit-and-stare -TAB raster WCS makes world-to-pixel slow and ambiguous (R8; accepted, D54). After the WCSAxes fixes, propose a matplotlib-free tick core on reuse grounds, not speed (astropy#9993 and #16464; it would give glue-jupyter's bqplot viewer WCS ticks, glue-jupyter#154): the decoupling study in `git show 09be127:GLUE_SPEED.md`. Done when each is filed, merged or declined.
- [ ] **M4** `wp0-qt-run-script` (D72): glue's own `-x` script option fails in glue-qt 0.4.2, so the macOS app's `smoke.py` runs through glue-solar's `GLUE_SOLAR_APP_CHECK` instead (216-2). Fix `-x` upstream; once it is released, the app check runs `smoke.py` with `-x` and `GLUE_SOLAR_APP_CHECK` goes. Done when the fix is merged and released, or declined.

Notes:
- Few-line speed fixes from `GLUE_SPEED.md` are on the user's forks for review, no PRs, one commit with its test and changelog each: glue `perf-g1a-wcs-labels`, `perf-g2-hidden-subset-layers`, `perf-g3-batch-link-removal`, `perf-g4-scalar-broadcast`, `perf-g5-lazy-scipy-optimize`, `perf-g6-lazy-ipython`, `perf-g7-profile-vminmax`, `perf-g8-slice-histogram`, `perf-g9-session-do-all`, `perf-g10-view-shape`; glue-qt `perf-q1-worker-block`, `perf-q2-slice-profile-sync`, `perf-q3-cmap-icon-cache`, `perf-q4-layer-icon-cache`, `perf-q5-lazy-terminal`, `perf-q6-startup-qt`; astropy `perf-a1-wcsaxes-pytest-import`. The user opens their PRs; until then the perf items count them as not filed.

### WP1: Coordinates, units and links

The coordinate contract (arcsec and Å on `_GlueWCS` IRIS data) and the links between IRIS datasets and sunpy maps.

**M4**

- [ ] **M4** `wp1-m4-autolink-matrix` (F049, F054): Once a core release has #2595, use its `WCSLink` suggestions for IRIS dataset pairs. Done when SJI Pixel points reach rasters and other SJIs without a time link, with `link_hpc` subsets unchanged.

### WP2: Line moments and diagnostics

Products from IRIS spectra, as dataset `layer_action`s that add linked Data and open no viewer, in `glue_solar/sources/moments.py`.

Notes:
- irispy's analysis functions take scaled cubes and raise on memmap ones (`check_scaled`, which trusts the lazy SJI meta's `scaled = True` over the dtype), so pass glue's scaled values, never the loaders' raw int16, and rebin scaled values.
- Velocities are relative to the uncorrected Level-2 wavelength scale (about 5-10 km/s); Mg II and C II are optically thick, so their centroids and widths are proxies.
- The 0.5 s and 3× limits are local acceptance numbers, not CI thresholds; Profile Collapse stays the display-only quicklook.

### WP3: Sessions

Makes Save and Open Session work for the quicklook and every glue-solar dataset through glue's saver registry and LoadLog.

Notes:
- Sessions record `glue_solar` class and function paths; no aliases are kept when they move (D69); each new coords type adds a #181 case.

### WP4: Quicklook preset and coordination

Coordinates the stock glue viewers of the CRISPEX-style IRIS quicklook in `glue_solar/quicklook.py`.

Notes:
- Whisker polish (F143) and CRISPEX entry keywords (F020) are Later.
- The move/stay matrix (`changes()` in `test_quicklook.py`) pins new coordination behavior: one quicklook per data kind, an exact dict per event. A hidden quicklook tab still refreshes its readouts and overlay (a cost only).
- SJI overlays and SJI clicks use the per-frame SJI WCS, never frame-0 pixel links. Overlays and markers stay out of sessions and 'Save Python script' but show in 'Save plot'.

### WP5: Spectral units, rest wavelength, line list, blink and Doppler

The line list, rest wavelength, km/s, blink and Doppler images, in `glue_solar/lines.py` (the main lines, #134) and `glue_solar/tools.py`.

**L**

- [ ] **L** `wp5-l-line-groups`: Optional line groups beside the main lines from irispy's database (flare, transition region, chromospheric neutrals, photospheric, molecular), each a toggle (D44). Done when each group shows only its lines. Depends: wp5-irispy-line-database.
- [ ] **L** `wp5-l-lines-in-range`: 'Lines in this range…' on a Profile range selection or the visible range lists the lines there, strongest first for a chosen region type (quiet Sun, active region, flare, sunspot), unpredicted ones after; a click labels one (D44). Done when a Si IV 1403 range lists Si IV 1402.77 first for the quiet Sun. Depends: wp5-irispy-line-database.
- [ ] **L** `wp5-irispy-line-database`: irispy ships an IRIS line database as ECSV with a query function: NIST ASD vacuum wavelengths for the IRIS passbands from a generation script (astroquery), cross-checked against iris_lmsalpy's `branch_ASD` extracts, and fiasco (CHIANTI) intensities for the quiet Sun, an active region, a flare and a sunspot; lines CHIANTI cannot predict (photospheric, molecular) are listed unranked (D44). The NIST query keeps forbidden and Ritz-only lines and the full passbands (iris_lmsalpy's FUV 1 table lacks Fe XII 1349.40 and Mg II 2798.754). The user's draft irispy #209 (branch `line-database`, `~/Git/irispy-line-database`, aed7854) has it, `irispy/data/iris_lines.ecsv` from `tools/make_line_database.py` and `irispy.utils.lines.get_lines` (no sunspot yet); glue-solar's `lines.py` then reads it. Done when a release has it.

### WP6: Fitting

Map fitting of IRIS spectra on glue's Profile Fit tab, planned with the user when it starts.

Notes:
- irispy main has starting models for `parallel_fit_dask` (`irispy.utils.fitting`: `profiles_on_background`, `si_iv_1403_model`, `mg_ii_model`, #220) and `maps_from_fit` (#221); the fit items and #167 wrap them rather than writing their own. Models need analytic derivatives.

### WP8: Browser, discovery and inputs

Covers the observation browser, the header scanner (`scan.py`) and the IRIS readers (`iris.py`).

Notes:
- WP1, WP3, WP4 and WP10 also edit `finalize`, `iris_loader.ui` and `test_importer.py`.

### WP9: Documentation and tutorials

Keeps `docs/user_guide/` true to what ships; WP9 owns the cross-cutting guides and recipes.

**M4**

- [ ] **M4** `wp9-m4-release-updates`: Update the guides as glue #2596/#2601 and glue-qt #70/#74 ship. Rebuild the macOS app (#216, `packaging/macos/build_app.sh`, D55) on the final releases as the plan's last deliverable. Once a release has the IRIS guide, 'IRIS: user guide and issues' opens the installed release's docs, not 'latest' (160-x1, D72). Done when each has shipped and no guide still names a glue-core 1.27.0 or glue-qt 0.4.2 caveat it lifts.

Notes:
- The IRIS user guide is five pages: loading, `iris-quicklook`, `viewer-tools-and-windows`, the Profile guide and `scripting-iris-data`; `docs/make_screenshots.py` regenerates its three IRIS images.
- `docs/` PRs build warning-free in `iris-plan-docs-qt6-802`, test no glue behavior, and never present planned features as shipped.
- Later: a SPECTFILE-style mean-spectrum reference (F031; a full-dataset Profile with function Mean) and scripting beyond #77's recipe (F033).

### WP10: Loader robustness and performance

Keeps the IRIS loaders in `glue_solar/sources/loaders/` correct and fast on files up to 20 GB.

Notes:
- IRIS Level 2 image HDUs are int16 (BSCALE 0.25, BZERO 7992; fill is raw -32768/-32764). glue-solar reads SJIs and AIA cutouts through irispy main's `read_sji_lvl2(memmap=True)`, whose raw int16 keeps the fill under a lazy mask; a `.fits.gz` is decompressed once into bytes that irispy views (#140).

### WP11: Display, readouts and inspection tools

Display and inspection tools for stock Image and Profile viewers, in `glue_solar/tools.py` and `glue_solar/quicklook.py`.

Notes:
- glue-qt takes B, C, G, H, K, M, P, R, X, Y, Z, Tab and Backspace, and dispatches keys by exact viewer type; glue-solar takes D, F, A, S, U and Space, and drops matplotlib's canvas keys (D61, D72; register).
- Not planned: zoom ×2/÷2, centering and a percentile menu (glue has them), or a CRISPEX control-panel clone.

### WP12: Export and derived diagrams

Frame, movie and data export plus path diagrams, built on glue's 'save' subtools, exporters and core's path slicer.

Notes:
- Paths and curves sample at the master's exposure. Not rebuilt: phi-slit sliders, path width, PostScript, IDL save files.

### WP13: Other missions

Features only other missions need, planned with the user once suitable data exist.

Notes:
- Known SST limits, kept: a Pixel point on an SST cube reaches linked data at the first tuning (glue takes index 0 on free axes); on a mosaic cube, a point placed on IRIS data does not reach the SST cube.

## Workaround register

Gated workarounds on main. Raw-WCS readers hold `WCS_LOCK` or use a deep copy; never fake an all-ones `axis_correlation_matrix`. Each row names the upstream route of a patch or override of glue, glue-qt, echo, astropy or wcslib behavior: an item key, a fork branch, 'report candidate', or 'none: glue-solar feature' / 'kept by decision' (D72, D73). A PR that adds or retires one adds or drops its row; planned workarounds are named in their items.

| Workaround | Switch | Retiring fix |
| --- | --- | --- |
| Correlated-axis `world2pixel_single_axis` (#71) | `needs_inverse_workaround()` | glue #2598 |
| Date epoch in `datetime64_to_mpl` and `mpl_to_datetime64` (#128) | `needs_date_epoch_workaround()` | glue #2599 |
| An empty `AggregateSlice` range drawn as its first sample (#132) | `needs_empty_collapse_workaround()` | a glue fix, not yet reported |
| `_GlueWCS` `WCS_LOCK` (#60) | Always on (not safely probeable) | astropy#19174's fix, once 20 unlocked race runs give 0 crashes |
| `_LockedWCS`: each plain WCS beneath a `_GlueWCS` becomes one in place at construction (`_lock_wcslib`: a raster's, a stack's scans' and scan axis's, a rebinned or restored window's, AIA and SOT cubes'), so the analyses hold `WCS_LOCK` per wcslib call, never across irispy's calls, calibration only around irispy's struct reads of spectral dispersion and solid angle (review F3, F6; `test_the_analyses_hold_the_wcs_lock_in_each_wcslib_call_not_across_irispy`); and each plain WCS `link_hpc` links on request becomes one in place, its transforms, copies and struct properties holding `WCS_LOCK` (`_HeldWCS`; names pinned by `test_the_link_patches_hold_the_wcs_lock`); an SST cube's `_LockedTabularWCS` holds the cube's own `RLock` instead, linked or not (#240). Lock-only wrappers of glue's `world2pixel_single_axis` and `PixelSubsetState._to_linked_pixel_coords` (`_hold_wcs_lock`), installed whatever the probes say, run glue's function, or the probe-gated fix, inside `WCS_LOCK`, the point wrapper taking no lock for a plain WCS `link_hpc` has not locked (#232). `WCSAxes.reset_wcs` holds the WCS's `_held()` lock; a cube's lock comes after `WCS_LOCK` (#226, #251, D73) | Always on | astropy#19174's fix, with the `_GlueWCS` lock; for the SST cube's lock, also wcslib's -TAB transforms no longer writing the shared tabprm's scratch fields (`tabx2s`), which astropy#19819 does not change |
| `_GlueWCS.has_celestial = False` (#66) | Always on | glue #2595 |
| Generic `solar:cursor_readout` | `not hasattr(ImageViewer, 'cursor_status')` | glue-qt #74 |
| Slice-slider drag throttle (#68) | Always on | glue-qt slider coalescing (`wp0-perf-qt`) |
| PV-slice slices (`sync_pv_slice`, #81) | `needs_pv_slice_workaround()` | a glue-qt fix (none filed); guard the import (glue-qt #66 deletes `PVSliceWidget`) |
| Pixel point off a linked dataset, or whose fixed axes reach no pixel axis of it (the SST quicklook's scan and Stokes), placed at its own slices (`PixelSubsetState._to_linked_pixel_coords`, #76/#85, #246) | `needs_pixel_point_workaround()` (either probe) | `wp0-core-image-artist-bugs` for the NaN; glue's round-trip check accepting a subset of the fixed axes (report candidate: `set(check_dimensions) <= set(dimensions)` and either `check_dimensions` non-empty or no fixed axes) |
| PV slicer on lazy (dask) data (`pv_slice_from_path`, #96) | `needs_pv_dask_workaround()`, on the first PV slice (#168) | glue-qt's PV slicer accepting dask data |
| FITS export of lazy data and of uint8 components in a subset (`export_fits`, #96) | `needs_fits_export_dask_workaround()` | glue-core's exporter writing dask arrays and uint8 subsets (report candidate) |
| No (0,0) Pixel crosshair (`ImageSubsetLayerArtist._update_visual_attributes`, #87) | `needs_crosshair_workaround()` | `wp0-core-image-artist-bugs` |
| A linked layer's Pixel crosshair placed from the reference data (`ImageSubsetLayerArtist._update_data`, #107) | `needs_reference_crosshair_workaround()` | `wp0-core-image-artist-bugs` |
| Axis labels set on the WCSAxes coordinate without placing ticks (`ImageViewer.update_x/y_axislabel`, #90) | `needs_axis_label_workaround()` | glue's `_set_wcs` label fix (`wp0-perf-core-draw`; fork branch `perf-g1a-wcs-labels`) |
| Slice playback stopped when its viewer closes (`ImageViewer.closeEvent`, #115) | Per close: a slider still playing after glue-qt's own close | glue-qt stopping play timers on close (report candidate) |
| Quicklook panels out of sight draw once in sight: `_arrange` sets each panel canvas's `_draw_idle` to `_draw_in_sight`, leaving the draw due while the shown panel has no visible region (`quicklook.py`, #235, #254) | Always on for panels `_arrange` lays out (not restored ones); a panel hidden itself draws at once | matplotlib's Qt canvas or glue-qt's `MplCanvas` leaving a queued draw out of sight to its paint (report candidate) |
| Quicklook Image panels take Pixel as their window becomes active (`QuicklookImageViewer.set_focus`, #244), since glue-qt turns the last viewer's mouse mode off and, with none, a click empties the edit subset | Always on (quicklook Image panels with no mouse mode on) | glue-qt keeping a viewer's mouse mode across focus changes, or its default mode leaving the edit subset alone (report candidate) |
| Image viewer keys, glue-qt's Tab and Backspace included, copied to `QuicklookImageViewer` (`_add_keys` in `setup`, #120) | Always on (adds only keys the class lacks) | glue-qt dispatching keys by `isinstance` (report candidate) |
| matplotlib's full-screen, save, grid, log-scale, pan and zoom keys dropped from glue-qt's canvases, g/G kept on Profile viewers (`MplCanvas.__init__`, `canvas_init`, `_DROPPED_KEYMAPS`, `_PROFILE_KEYMAPS`, #120, #222, #257) | Per canvas: a figure manager connecting matplotlib's key handler | glue-qt dropping matplotlib's key bindings (report candidate) |
| Redo of a subset change puts back the subset states its first run made (`ApplySubsetState.do`, #182) | `needs_redo_workaround()` | glue's `ApplySubsetState` keeping its states (`wp0-report-candidates`) |
| `u.Quantity` saver and loader for sessions (`save_quantity`, #186, D13) | Only while glue has no `u.Quantity` saver | `wp0-core-quantity-saver` |
| `LinkSameWithUnits` saved by its two components (#205) | `needs_link_restore_workaround()` | glue's saver (`wp0-core-session-reports`) |
| For glue's link editor: `LinkSameWithUnits` ends named `x`/`y`, taking `cids1`/`cids2`; `PathRelativeLink` ends `k_from`/`k_to`, its conversions with one-argument signatures (#245) | `needs_link_editor_workaround()` (two OK rounds) | glue naming both classes' ends apart, `LinkSameWithUnits` accepting `cids1`/`cids2`, and the editor's `link` keeping a `ComponentLink`'s names (report candidate) |
| A time linked from another dataset kept a datetime (`DerivedComponent.datetime`, #208) | `needs_derived_datetime_workaround()` | glue reading a derived component's datetime kind (report candidate) |
| Profile display units restored after `x_att` (`ProfileViewerState._update_priority`, #197) | `needs_profile_restore_workaround()` | glue ranking the display units after `x_att` (`wp0-report-candidates`) |
| Toolbar menu tooltips on the button and its entries (`BasicToolbar.add_tool`, #222) | Per button: no tooltip, or menu tooltips hidden | a glue-qt fix (report candidate) |
| One fitter per Profile viewer and fitter class for glue-qt's Fit Settings and fits (`glue_patches._get_fitter`, `_on_settings`, `_fit`, #287) | While `ProfileTools` has no `_get_fitter` (`_on_settings` also while `needs_fitter_settings_workaround()`) | glue-qt's `ProfileTools._get_fitter` (`wp0-qt-fitter-settings`) |
| glue-qt's `ProfileTools._fit` replaced, for the IRIS fitter, by its own loop over the layers: each layer's saturated samples left out of the fit (D87), and the model given the layer's rest wavelength, attribute, x unit, function, range and saturated counts for `summarize` and 'IRIS: line fit maps' (`fitters._fit`, #291, #313); with glue-qt's own `ProfileTools._get_fitter`, it fits with the fitter glue-qt passes | Always on | glue-qt passing the layer to a fitter's `fit` and `summarize` (`wp0-report-candidates`) |
| A quicklook panel makes its Point the edit subset at a Pixel or Follow/lock press while a dataset is selected (`QuicklookImageViewer._edit_point`, #288) | Always on | glue-qt's data collection leaving the edit subset alone when a dataset is selected (`wp0-report-candidates`) |
| Analysis result viewers open with glue-qt's default mouse mode off (`moments._view`, #300) | Always on | glue-qt's data collection leaving the edit subset alone (`wp0-report-candidates`) |
| The IRIS fitter's `set_constraint` replacing a parameter's entry, so a value or bound cleared in Settings clears (#259) | Always on | glue-core's `BaseFitter1D.set_constraint` taking None as a clear (report candidate) |
| Settings on the Fit tab opens a fitter's own `settings_widget`, the IRIS fitter's component list (`glue_patches._on_settings`, `fitters._Settings`, #314, D86) | `needs_fitter_settings_workaround()`, or while `ProfileTools` has no `_get_fitter` | glue-qt's `_on_settings` using `fitter.settings_widget` (fork branch `fitter-settings-widget`, dba71453, no PR) |
| The Fit tab keeps every artist a fitter's `plot` returns, so Clear removes each IRIS line's dashed curve (`glue_patches._plot_fit`, #314) | `needs_fit_artists_workaround()` | glue-qt's `_plot_fit` keeping every artist (fork branch `fit-artists`, d6655bc5, no PR) |
| 'IRIS: line fit maps' asks `parallel_fit_dask` for only `("param_cov", "success")` and makes each `FitInfoSubset` a plain dict, as all of the fit info took a C II window's main process to 5.9 GB (3.2 GB so) (`fit_maps._fit_maps`, #314) | Always on | astropy's `FitInfoSubset.__getattr__` raising AttributeError, not KeyError, which `FitInfoArrayContainer.__getitem__`'s `hasattr(result, "ndim")` and so irispy's `maps_from_fit` trip over (report candidate) |
| Colormap icons drawn once per colormap and width (`QColormapCombo._update_icons`, #177) | `needs_icon_cache_workaround()`, at the first combo | glue-qt caching icons (`wp0-perf-qt`; fork branch `perf-q3-cmap-icon-cache`) |
| A colormap matched to its own combo entry (echo's `_find_combo_data`, #194) | `needs_combo_match_workaround()` | echo matching the entry that is the value first (`wp0-report-candidates`) |
| Layer actions hidden where `applies(data)` refuses with a ValueError, shown when the check raises anything else (`UserAction._can_trigger`, #223, #257) | `needs_layer_action_applies_workaround()` | glue-qt's layer actions taking `applies` (fork branch `layer-action-applies`, no PR) |
| Lazy data's sampled statistics: raw-code counts (D33), random samples of derived attributes (`LazyData.compute_statistic`, `loaders/lazy.py`) | Always on | glue sampling dask arrays at random, not at chunk corners (`wp0-report-candidates`) |
| SST cubes' color-limit sample (`_Cube.compute_statistic`, #230, #248, D70): 16 planes of 25 evenly spaced rows and columns, plane k at the k-th of 16 even tunings, Stokes k modulo their number and the (7k mod 16)-th of 16 even scans; all planes of a cube of 16 or fewer | Always on | glue sampling cheaply (`wp0-perf-core-stats-io`, R32) |
| `_TabularWCS.has_celestial = False` against wcslib's SIGSEGV in glue's autolinker (#227) | Always on | wcslib cutting a -TAB table's celestial axes safely (report candidate) |
| SPECSYS 'TOPOCENT' on ground-based files without one (`sst.py`, #227, SST2) | Files with no SPECSYS | astropy treating a missing SPECSYS as no spectral observer (report candidate) |
| `_TabularWCS.__gluestate__`/`__setgluestate__` in place of glue's `_save_wcs`/`_load_wcs`, which raise 'HDUList is required to retrieve -TAB coordinates' (`sst.py`, #227, SST5) | Always on (SST cubes) | glue saving a -TAB WCS with its tables (report candidate) |
| `_TabularWCS.axis_correlation_matrix` from the tables, where astropy's says each -TAB world axis depends on its own pixel axis only (`sst.py`, #227) | Always on (SST cubes) | astropy computing a -TAB WCS's matrix from its tables (report candidate) |
| The SST cube's own inverse, `_TabularWCS.world_to_pixel_values`, falling back to wcslib's (`sst.py`, #227, D67) | Always on (SST cubes) | kept by decision (D67; `wp0-wcslib-tab-inverse`) |
| A quicklook saved as a recipe on its first panel's record and rebuilt by `_reopen` (`quicklook._recipe`, `_reopen_quicklooks` session patch, #301) | Always on | none: glue-solar feature |
| `GlueApplication.closeEvent` wrapped to keep the last session on quit, telling a replaced window by glue-qt's private `_new_application` (`__init__.py`, #206, #297) | Always on | none: glue-solar feature |
| glue's unit converter default set to `lines.DopplerConverter` (`__init__.py`) | Always on | none: glue-solar feature |
| The mouse-over readout places WCSAxes ticks before formatting (`_readout`, `tools.py`, #90) | Always on | WCSAxes `format_coord` without a tick placement (report candidate) |
| Path diagram overrides of core's path slicer and their session savers (`PathTool`, `PathData`, #151, #191), with `PathTool._close_slice_viewers` closing diagrams with `close(warn=False)` (#243) and `PathCrosshairTool._on_move` rounding and clamping each axis (#262) | Always on | core's path slicer fixes (`wp0-report-candidates`; for #243, `MultiTracePathSlicerMixin._close_slice_viewers` calling `close(warn=False)`; for #262, `drive_parent_slice` rounding and clamping) |
| Sunpy colormaps a session names listed before glue restores them, and registered in matplotlib under their own names (`_add_session_colormaps`, a `@session_patch`, and `maps._add_colormap`, #98, #129) | Always on | glue restoring sunpy colormaps by name (`wp0-core-session-reports`) |
| Raster windows of one restore read together (`_read_logged_windows_together`, a `@session_patch`, and `raster_files_data`'s `_RESTORING`, #234) | Always on | glue's LoadLog restoring one file's logs in one load (`wp0-core-session-reports`) |
| A dataset's style saved with its preferred colormap (`maps._Style`, #189) | Always on | glue-core saving and restoring `preferred_cmap` (`wp0-core-session-reports`) |
| The Slope table's Table viewers reset after new rows (`SlopeTool`, `tools.py`, #175) | Always on | glue-qt's Table viewer showing and sorting rows added to its dataset (report candidate) |
| A Table viewer of data with a time searches each value of its search column as the text the table shows (`glue_patches.get_filter_mask`, #260) | `needs_table_time_workaround()` | glue-qt's Table search matching `str(x)`, as its cells show (report candidate) |
| A tooltip for glue-qt's Profile viewer button (`ProfileViewerTool.tool_tip`, `setup`, #222) | `ProfileViewerTool.tool_tip is None` | glue-qt giving the button a tooltip (`wp0-report-candidates`) |
| A Profile viewer adds a quicklook spectrum panel's raster (S13, #95), and any cube of `large_data_size` (1e8) values or more not from the IRIS reader (#233, SST4), with its data layer hidden, a status-bar note and the range fitted once to the first computed subset profile (`hidden_cube_profile`, `_FitOnceComputed`) | the viewer's `large_data_size` and the data's `_role`; the quicklook's `_solar_hidden` | glue's `_reset_y_limits` using cached profiles only (R14) and `compute_statistic` without the float64 copy (R21), or glue-qt adding large data hidden (`wp0-perf-core-stats-io`) |
| mpl-scatter-density's 0.5 s hold after a canvas resize, ended before each saved frame: `SaveSequenceTool` calls `on_release()` on each `BaseImageArtist` in the viewer's axes (#270) | Always on | mpl-scatter-density ignoring the hold while matplotlib saves (`canvas._is_saving`; report candidate) |

## Validation, environments and data

Run all Python in a micromamba env, never a `.venv`; create a new env rather than change one.

- `iris-plan-qt6-802` (since 2026-10-16, D83) and `iris-plan-floor-qt6-611` (D56; since #266, D77): the baseline and the floors, PyQt6 6.11.0 on Qt 6.11 in both (astropy 8.0.2 and 8.0.0, ndcube 2.4.2 and 2.4.0, sunpy 8.0.0; glue-core 1.27.0, glue-qt 0.4.2 `--no-deps`, irispy git main 8c220d4 `--no-deps`, conda-forge's `qtconsole-base`, since `qtconsole` pulls PyQt5); every PR passes in both. `iris-plan-docs-qt6-802` builds the docs (pip's `sphinx-changelog` and `sunpy-sphinx-theme`). The `-802` envs are `micromamba create --file` of their 8.0.1 sources' explicit lists with astropy and astropy-base at 8.0.2, then the same pip packages `--no-deps` (recipes in the session archive's `items/envs-802/`); the 8.0.1 envs `iris-plan-qt6`, `iris-plan-docs-qt6` and `glue-solar-app-pin` stay as they were. `iris-plan-qt6-802-9229` and `iris-plan-floor-qt6-611-9229` are APFS copies (`cp -cR`) of the two with irispy main 9229d06 installed `--no-deps` (#239, #240), the envs every PR uses since #308 (the plain `-802` and `-611` envs keep irispy 8c220d4, whose saturation behavior main no longer matches). The floor env was made with `micromamba create -n iris-plan-floor-qt6-611 -c conda-forge python=3.13 astropy=8.0.0 ndcube=2.4.0 sunpy=8.0.0 glue-core=1.27.0 pyqt6=6.11.0 qt6-main=6.11.2 qtpy qtconsole-base ...` (the full list in #266's run), then glue-qt 0.4.2 and irispy 8c220d4 by pip `--no-deps`.
- `glue-solar-app-pin-802` (astropy 8.0.2; `glue-solar-app-pin` before): builds the macOS app since #275 (the docs recipe's `glue-solar-app`, with fiasco main, plasmapy, h5py and ffmpeg, and irispy pinned at 8c220d4); the envs `glue-solar-app` (#216) and `glue-solar-app-l` (#268) are older.
- `ruff-0161`: glue-solar's pinned Ruff.
- `irispy-ports`: irispy development; its editable irispy points at the removed `~/Git/irispy-bursts`, so always run it with `PYTHONPATH=<worktree>` from a neutral cwd, never from `~/Git/irispy`.
- Retired: `iris-plan-floor-qt6` (PyQt6 6.8.1, #266) and the PyQt5 envs `iris-plan-main`, `iris-plan-floor-main`, `iris-plan`, `iris-plan-floor` and `iris-plan-docs` (#214; left at irispy ca27ee9). The `glue-solar` and `astropy-wcsaxes-core` envs are editable installs of removed checkouts and no baseline; reinstall before use.

Headless runs use a scratch `HOME` (glue rewrites `~/.glue/settings.cfg`), offscreen Qt and Agg; glue-solar's conftest keeps tests off macOS QSettings (D75). Regenerate upstream PR exports before use (macOS purges temporary directories). Run tests from a checkout of the code under test, never `~/Git/glue-solar` (on `plan`); `run_checks.py` makes its own HOME and caches and removes them when it ends:

```sh
P=~/Git/glue-solar/IRIS_PLAN_PROTOTYPES
env PYTHONPATH=$P ~/mamba/envs/iris-plan-qt6-802/bin/python -B $P/run_checks.py \
  "$PWD:$P" glue_solar --remote-data=any
```

glue-solar tests only the GUI and glue side, with the loaded dataset's own coordinates as oracle; irispy's reading, WCS and numerics are irispy's tests. Real-data tests are `@pytest.mark.remote_data` tests on LM-SAL/irispy-data release assets (tag `v1`) via the `irispy_data` fixture, never local paths or committed data; a missing cutout goes into irispy-data first, on the user's direction. irispy's decimated CI fixtures (`find_irispy_test_file`) are not physical validation.
