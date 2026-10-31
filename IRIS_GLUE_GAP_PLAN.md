# IRIS and Glue work plan

This plan drives glue-solar, with the irispy and glue work it needs, toward an IRIS quicklook in Glue covering what SolarSoft's CRISPEX offers; items name the CRISPEX features (F001-F203) they serve. The plan and `IRIS_PLAN_PROTOTYPES/` live on glue-solar's pushed branch `plan`, never merged or opened as a PR, and it lists open work only. Each item is one glue-solar PR on a branch from `main` without the plan or prototypes, opened as a draft and marked ready and merged once CI passes (user, 2026-09-30); irispy, glue, glue-qt and astropy work stays drafts or the user's fork, on the user's direction.

## How to use this plan

- Start at [Current state](#current-state) and refresh PR states with `gh`.
- Pick an open item in the earliest open milestone; read its done-when and Depends.
- Trace the code on `main` before writing or porting a prototype; this plan overrides prototypes.
- Stage named files only.
- When an item's PR merges, delete the item and its key from other items' Depends and the checklist; the PR and git history keep the record, so Current state gets no line. Say "on main", not "released".
- Versions, environments, data, worktrees, archives and tooling are in [IRIS_PLAN_PROTOTYPES/OPERATIONS.md](IRIS_PLAN_PROTOTYPES/OPERATIONS.md), by machine. The workaround register is `docs/dev_guide/workarounds.rst` on main.

## Scope

In scope:

- The CRISPEX and IRIS-SolarSoft features from the user's 2026-09-30 review: 'keep' ones were M1 to M3 items (fitting M4), 'later' ones L items, and those already on main or in Glue have none (the feature map and earlier plan text are in this branch's git history).
- CRISPEX (and `iris_xfiles` for discovery) is the behavior reference; it has no license, so no code is ported.
- Features only other missions need came last (WP13: DKIST, on main as #371-#403).

Out of scope:

- Level-3 FITS writing (F188), EIS (F019, F048), the detector mosaic (F123, needs Level 1), and OBS XML and pipeline-log viewers (F042, F043).
- The IRIS-9 tutorial and its event-finding workflow (F093), and online context and search (GOES, AIA, HMI, SWPC, HCR, IRIS search: F016-F018, F041, F044-F047).
- AIA reference panels, reference spectra and AIA blink (F103, F107; second IRIS windows are on main, D42): AIA and Hinode cubes are imaging only, like SJIs.
- PostScript, IDL and legacy CRISPEX formats (F189): images export in normal formats, derived data as FITS or ASDF.
- SST-only inputs (F023, F028, F029, F129) and IDL details Glue replaces.

## Current state

**Resume here.** Main is at 047193f5 (#406). glue-solar pins irispy main f058705 (#347, D91); following irispy waits for its gwcs port, #360 (D106). M0, M2, M3 and WP13 are done. Open: the held follow-irispy PR (`wp10-follow-irispy`), release tracking on each release, and M4's upstreaming on the user's direction.

**Next.** Merged work is recorded by its PRs and git history, not here. The follow-irispy PR, branch `follow-irispy-main` (on main cae1af6; irispy pinned to #360's head 5d662b1, whose code the user calls settled, docs changes to come; batched stack reads, b1, user 2026-10-29; 778 passed, 4 skipped in the Linux env `iris-plan-irispy-360`; PR body `fix25/follow-batched/body.md` in the Linux session archive; the head before the rebase kept as `follow-irispy-main-before-batch`), opens once #360 merges: retargeted to #360's merge commit, its gwcs fixes checked again against #360's final API, and rerun (D106). How items run: an Opus implementer, a Fable review and an Opus fix pass (`IRIS_PLAN_PROTOTYPES/plan_tooling/plan-item-workflow.js`, and the Linux archive's `workflows/`), every probe and test on the Linux machine under a 24 GB memory scope (systemd-run); branches made beside each other are merged and suite-run together before their PRs, which go one at a time. CI's core job runs with coverage on four xdist workers, several times slower than local runs: keep test fits small and waits at 60 s. A batch of irispy merges gets one follow-irispy PR (D91, D92).

**Waiting on the user.** (1) Trying the fitting in the GUI ('Fit every spectrum', the model builder; OBS 3610108077's C II and Si IV windows, the flare 3860258481 for saturation, which loads once the follow-irispy PR is in; the builder's options are settled, D98, D99). (2) `wp0-qt68-macos-pass`. (3) The macOS app's drag-into-/Applications check, after a rebuild on current main (`wp0-release-tracking`; the 2026-10-20 build is gone from this Mac). (4) An exact report of the linking and slider-sync problems seen in the app on 2026-10-09 (4000255147's raster and SJI 1400, or 4000005156's two scans and SJI 2796), if still seen on current main. (5) The `wp0-upstream` items, all in `~/Downloads/glue-solar-upstream/` on the Linux machine (its README is the checklist, in order, 26 items): eleven fork branches to open as PRs (glue: restored `cmap_bad`, one-pass `discover_links`, DaskComponent sampled reads, stable link order, `ape14-wcs-link`; glue-qt: slice sliders, edit subset; astropy: WCSAxes' non-finite range, the FITS config reads per card; dkist: NaN lookup indices; ndcube: the shallow meta slice), with `PLACEHOLDER` changelog fragments to rename; the six rebased drafts #2595-#2599 and #2601 to review and mark ready; the issue and comment texts to paste; the irispy #360 handoff and the c58ef2b benchmark; and the WCSLIB email. (6) irispy #360's merge, which the follow-irispy PR waits for.

**Waiting on others.** The user's upstream drafts, on their human reviewers (`wp0-upstream`); an irispy release (`wp0-irispy-release`).

## Decisions

Settled by the user; reopen only with the user. One line each: the full text, with how each was reached, is at plan commit 683e1e7 (`git show 683e1e7:IRIS_GLUE_GAP_PLAN.md`) and in the session archives. A number cited by code, the register or UPSTREAM_REVIEW.md resolves here.

- **D1:** Keep `link_hpc`, the exact per-frame spatial link between IRIS datasets; pair by physical type; no SJI world-time link; no equal-hop paths with different values.
- **D2:** Build in glue-solar and irispy first via glue's public registries; nothing waits for an upstream release; upstream work is M4; workarounds switch on a behavior probe, never a version.
- **D3:** Arcsec and Å on `_GlueWCS` IRIS data; sunpy Maps keep glue's plain astropy WCS and link to IRIS on request (D64).
- **D4:** Analysis products are dataset `layer_action`s adding Data and links without a viewer; derived maps use `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`; a per-sample expression of one dataset is a glue derived component.
- **D5:** Superseded by D104 (every floor at its latest release), D47 (irispy git main) and D56 (PyQt6).
- **D6:** Selection is the stock Pixel tool plus Clear point, with hover-follow and click-to-lock (D39).
- **D7:** The point is a fixed detector pixel; time is an index axis with timestamp readouts: nearest exposure, ties earlier, no match (grayed, never clamped) past half the partner's median cadence; the raster is the default time master.
- **D8:** The coordinator moves sliders from 1-D nearest-index arrays and adds no glue links (D42's `LinkSame` between a file's windows is the one exception).
- **D9:** One `Coordinator` per DataCollection behind the registered `solar:coordinate` tool; restored viewers re-register; never wrap `app.new_data_viewer`; menus use `SimpleToolMenu`.
- **D10:** Negative-step rasters keep irispy's orientation; `revert_v34=True` is the documented alternative.
- **D11:** Rest wavelength: explicit override, else the packaged vacuum line list, else none (none for multi-line windows, never TWAVE); float Å in `meta['rest_wavelength']`.
- **D12:** -200 and -199 are missing, in AIA cutouts too; negatives are data; stored masks are uint8; saturation per D85.
- **D13:** Sessions add the Quantity saver only if none exists, save `_GlueWCS` via `__gluestate__`, never replace glue's `VisualAttributes` serialization globally, and save added components as 1-D vectors.
- **D14:** irispy work targets LM-SAL `main`; the gWCS raster work is the user's (irispy #182 closed unmerged; #360 is the port, D106).
- **D15:** The quicklook is an MDI tab with explicit viewer geometry.
- **D16:** Doppler is red minus blue, positive for redshift, in `meta['doppler_sign']`.
- **D17:** Missing data are NaN; no sentinel values.
- **D18:** Do not re-implement glue: configure, default, document or call glue's API first.
- **D19:** Each quicklook tab has its own Point group driving only its own panels; a Pixel click on its slit-jaw image moves the point to the raster pixel there; only a click on a viewer showing the frame axis stays a slit-jaw point.
- **D20:** `link_hpc` links every dataset to the first (a star); 'Open quicklook' starts ticked and the browser skips glue's autolinker.
- **D21:** A NO MATCH readout gives the nearest frame's offset; a follower moved by hand shows its own, grayed beyond half a cadence.
- **D22:** After Clear point a scanning raster's time stays at the last point's step; a sit-and-stare's exposure slider and a stack's scan slider keep driving the time; under a slit-jaw master with a point a hand-moved raster snaps back, a hand-moved slit-jaw follower keeps its frame until the next sync.
- **D23:** The quicklook marks the point with a thin line on the spectrogram and λ–t panels.
- **D24:** The moments and red-blue dialogs take a typed line center, pre-filled as D11 gives it.
- **D25:** Sessions re-read IRIS files through glue's load log, with the Profile display-unit restore patch.
- **D26:** Multi-instrument links and Level-3 input are not planned (D62, D82); the Hinode/SOT reader is #212.
- **D27:** The time marker is glue's own range subset.
- **D29:** Every Image viewer of a sit-and-stare raster shows the exposure label and integer exposure ticks only, no helioprojective ticks on the far edge.
- **D30:** 'Hide axes' hides the whole axes, with no pixel-coordinate ticks instead; on rolled views each axis label stays with its own coordinate's ticks.
- **D31:** IRIS world values reach glue in Å and arcsec, high-level objects included, with glue's and WCSAxes' text precision (the readout's is fixed); -TAB round trips hold to the wrapped WCS's own error.
- **D32:** Lazy loading: raw int16 through irispy's memmap view; gzipped SJIs held as raw int16 in RAM; the mask is a glue derived component; the quicklook's spectrum never computes whole-cube profiles; the lazy loaders raise the open-file soft limit.
- **D33:** Lazy color limits count raw codes exactly over up to 512 MiB of planes per window, within 1 % of the eager 99.5 % limits; the memory budget is the peak RSS increase over the no-viewer post-import baseline.
- **D34:** The GitHub wiki stays off; its history is `IRIS_PLAN_PROTOTYPES/glue-solar-wiki-20261001.bundle`.
- **D35:** Every sunpy colormap is listed, with glue-qt's colormap icons drawn once per colormap and width until glue-qt caches them.
- **D36:** The browser's background load covers the quicklook too; Stop keeps the picks read in full, Esc or closing drops the load; a gzipped SJI is decompressed once; each raster file is read on its own.
- **D37:** `link_hpc` anchors on the first IRIS dataset (maps with `LinkSameWithUnits`, IRIS pairs `LinkSame`); `_GlueWCS` wraps a map's longitudes to the raster's; `sji_to_raster` applies the half-cadence limit on sit-and-stare rasters only; the readout's fixed precision is for IRIS Å and arcsec only; 'Regrid on time' times a stack's scans at their middle step and includes exactly 0.75 steps.
- **D38:** 'Go to UTC', typed in any viewer, moves the observation's time master; region tools make a new subset and leave the Point alone; the Point window sits under the quicklook's panels; a slit-jaw click beside a sit-and-stare slit takes the level row at any distance, as one undoable assignment.
- **D39:** A region on a quicklook's slit-jaw image reaches other data at the pointing of the frame shown when drawn; wavelength, time and point lines go on the quicklook's own panels only; the time line snaps to the nearest step; Follow/lock is on every Image viewer, belongs to the point group and stays at Clear point; D/F move the time master, A/S step wavelength sliders, Space plays the time master's looped slider; quicklook panels get glue-qt's Tab and Backspace.
- **D40:** 'Raster overlays' (View menu) toggles an observation's overlays on all its viewers, off by default and never saved: a thin white line per step's or exposure's slit on slit-jaw images, the dashed map line at the shown scan on step or exposure views.
- **D41:** Spectral blink: 'Set blink partner here' stores the full slider position as B; a 'Blink' toggle runs it every 0.25 to 2 s (default 0.5 s), leaving Pixel mode, the point, the other sliders and time sync as they are.
- **D42:** Several windows: the quicklook shows the browser's ticked windows, the main window (D60) with the full panels and each other window of the same file or stack with a spectrum panel (and a λ–time or λ–scan panel on a sit-and-stare raster or a stack), in rows of four below; each other window's scan, step and slit pixels are `LinkSame`-linked to the shown window's, and the coordinator moves a file's windows as one cube.
- **D43:** Default stretches: slit-jaw 1330 and 1400 log, 2796 sqrt, 2832 linear; raster windows FUV log, Mg II k and h sqrt, other NUV linear; color limits 99.5 %; glue's layer controls change either.
- **D44:** Amended by D96: the main lines are irispy's documented ones; line groups are dropped and 'Lines in this range…' replaces them.
- **D45:** The line moments dialog requires the line center and a range in km/s, so its blocking and memory limits hold; the continuum is optional (D48).
- **D46:** Line moments take raster windows and stacks (each scan at its own coordinates) and refuse other data; the map's meta keeps OBSID, STARTOBS, `moments_center` and `moments_velocity_range`, never INSTRUME or `Time`; `calculate_moments` runs on glue-qt's `Worker` on the range's wavelengths only, at most 2**21 samples a call; missing and negative samples count as irispy's 0.
- **D47:** glue-solar depends on irispy's git main (Python ≥ 3.13), pinned per D91, and calls its API directly with no probe for what main has; PyPI releases of glue-solar and irispy wait for M4.
- **D48:** Continuum windows: Å ranges in one optional field, which `subtract_background` fits with a constant for one window and a straight line for more; too few continuum samples give NaN in every map; the continuum meta goes in only with a continuum.
- **D49:** Level 2 never holds +Inf; 16182 DN (raw 32760) is the writer's clipping ceiling; the header's saturation counts never count a file's samples, so the status bar counts the data's; irispy detects saturation; line moments take DN/s from the loader's `per_second`.
- **D50:** Zoom 1:1 is removed (D83); the color bar stays right of the image, ticks only; frame and movie export stays at 10 frames per second; the saturation recipe reads HISTORY in glue's terminal.
- **D51:** `glue-solar[density]` installs fiasco for irispy's `density_diagnostic` and the O IV preset; Mg II features take saturation from irispy; the mean spectrum is one all-scans float32 mean; red-blue keeps its per-step DN/s limit; File → Open leaves linking AIA cutouts to 'IRIS: link helioprojective coordinates'; Path diagrams keep L and a new set per Enter; Measure gets key U.
- **D52:** The SOT reader's test files live in irispy; ticks the browser filter hides still load; a Profile range sets the moments range for a pre-filled line center too; Undo or Redo of a slit-jaw click returns the slit-jaw viewer to the clicked frame.
- **D53:** 'Light curves of the shown windows and SJI' adds a 1-D Data (Time, value) per raster window and SJI channel the point's quicklook shows, recomputed as the point moves, in one datetime Scatter plot with an 'ECSV (with Time)' exporter; 'Light curve of this window' stays.
- **D54:** irispy fixes are draft PRs on LM-SAL/irispy from origin/main with a test and a changelog fragment; the user reviews and merges; WCSLIB is never re-implemented, the slow raster world-to-pixel accepted (D67 is the one exception); glue-solar fills NaN itself.
- **D55:** macOS app: for the user's Mac only, unsigned, Apple Silicon, a local .dmg reusing glue-standalone-apps' PyInstaller spec and hooks; rebuilt as the plan's last deliverable (`wp0-release-tracking`).
- **D56:** Qt 6: glue-solar depends on PyQt6 (glue-qt without its PyQt5 extra), refuses Qt 5 at import, and does not test PyQt5.
- **D57:** Reversed by D85 for +Inf; its API choices stand: `calculate_moments` takes a km/s `velocity_range` (default ±107 km/s), `calculate_red_blue_asymmetry` has `spline_degree`, a continuum costs one irispy call per slab.
- **D58:** Row and column cuts: no port of glue #2596 or glue-qt #70; 'Row at the point' and 'Column at the point' are `SliceSubsetState`s following the point, with no glue patch; the slit-jaw cuts are documented.
- **D59:** Every analysis action accepts a stack of raster scans, each scan at its own coordinates and exposure times, giving maps of (scan, step, slit); a stack's UV bursts and calibration use its first date.
- **D60:** The browser picks the quicklook's main window, Mg II k by default; 'Show this window's panels' on a spectrum panel switches it, keeping the point, the time and the other windows' panels.
- **D61:** Image viewer buttons: Follow/lock, Modes, Coordinate and View right after Home, Pan and Zoom; the Coordinate menu holds the time entries and the 'Point' and 'Blink' submenus; 'IRIS: ' prefixes glue-solar's adds to glue's shared menus; data actions hide where they cannot apply (`applies(data)`); matplotlib's g/G, l/k/L and p/o keys are dropped as f/s are (g/G back on Profile viewers); glue-solar's text is American.
- **D62:** SST data: SSTRED SOLARNET cubes opened as FITS (large, not co-aligned to IRIS); the IRIS-SST database's Level 3 CRISPEX files are unsupported.
- **D63:** The SST and IRIS stress survey (GLUE_SPEED.md, SST1-SST13): its glue-solar fixes are on main, its upstream findings in UPSTREAM_REVIEW.md; SST13 gets no action.
- **D64:** Data from outside the IRIS observations link to IRIS only on request, through 'IRIS: link helioprojective coordinates', never as data load or a quicklook opens.
- **D65:** A quicklook per instrument: CRISP and CHROMIS cubes open one in its own tab from the browser and the Plugins menu, linked to IRIS on request, time-synced; every panel turns on and off; other cubes get one from their axes (D78); #307 keeps only Stokes scaling and noise level.
- **D66:** Panel toggles: a checkable 'Panels' list right of the Point window; shown panels re-tile at a toggle; sessions leave out panels turned off; a slit-jaw time master turned back on moves to its frame nearest the raster's time.
- **D67:** SST loader: once linked, an SST region or point reaches IRIS data at the scan nearest each IRIS frame's time and the line core; the cavity-error lookup is its own component; the loader inverts its coordinates itself (D54's one exception), wcslib for larger tables.
- **D68:** SST quicklook: one cube per tab; row 1 the map, a second wavelength map and the virtual slit; row 2 the I, Q, U and V spectra (I only on CHROMIS); row 3 wavelength against time and the light curve; the Point window and Panels list below.
- **D69:** glue-solar is unreleased, so sessions saved by older glue-solar need not open: no back-compat patches or aliases.
- **D70:** As an exception to D63, SST cubes answer glue's sampled color-limit statistics from 16 planes of 25 rows and columns, tracked under R32 until glue samples cheaply itself.
- **D71:** Every quicklook opens its image panels with the axes hidden; since #302 (D83) View → Hide axes on any quicklook image panel is the one axes control.
- **D72:** The choice review of #100-#232: every PROVISIONAL not changed stands; the analyses keep DN/s in float64; the mean spectrum leaves saturated samples out and counts them; calibration takes rebinned windows; menu help stays as tooltips; the cavity error stays in nm; the app has its own icon; every patch or override on main has a register entry with its upstream route, updated by the PR that adds or retires it.
- **D73:** After the audit of #226-#235: an SST point reaches linked IRIS data through the widened `_to_linked_pixel_coords` patch; the WCS locks around glue's `world2pixel_single_axis` and `_to_linked_pixel_coords` are lock-only wrappers installed whatever the probes say, retiring with astropy #19174's fix only; an SST cube's WCS has its own `RLock`; 'Glue Session including data' failing on SST cubes and lazy IRIS windows is documented, not a defect.
- **D74:** Superseded by D81: sessions stay.
- **D75:** On macOS `QSettings('glue-solar', 'glue-solar')` ignores a temporary HOME, so glue-solar's conftest patches `iris.QSettings`, and probes must too.
- **D76:** The choice review of #233-#240: every PROVISIONAL stands or changed on main; calibration keeps the first scan's dispersion and solid angle but refuses a stack whose scans' CDELT1-3 differ.
- **D77:** The glue team allows copying glue-standalone-apps' spec and hooks; app checks may launch the built app on the user's desktop with `open`. (Its floor env went with D104.)
- **D78:** One fill builds every quicklook from a panel table per data kind: IRIS raster, slit-jaw only, SST and generic; the generic table follows the cube's WCS axes, from a 'Quicklook…' layer action on any cube with one spectral and two spatial axes.
- **D79:** The choice review of #241-#275: every PROVISIONAL stands or changed on main; 259-1 to 259-3 are D81's, 267-7 is dropped (D86).
- **D80:** The choice review of #276-#283: every PROVISIONAL stands or changed on main; prose and labels write units alike.
- **D81:** Sessions stay (D74's first option); fitting: one fitter per Profile viewer as a glue-solar stopgap (#287), the glue-qt fix on a branch of the user's fork; since #314 a component list in the IRIS fitter's own Settings replaces the check boxes and 'Number of lines'.
- **D82:** User (2026-10-16): keep the plan concise and the code lean; port CRISPEX's ideas to glue better, faster, sleeker and nicer, not one to one; the plan keeps rules and open items only, and items with nothing to do are dropped.
- **D83:** A session restores a quicklook by re-running `quicklook()` from a saved recipe (#301); 'IRIS: restore last session' stays; the four consolidations #296, #298-#300 and #302 (one axes control, no Zoom 1:1, reopening D50, D71); the user guide is task pages; astropy 8.0.2 became the baseline.
- **D84:** The choice review of #276-#295: all stand.
- **D85:** Saturated samples show everywhere (images, spectra, light curves) at their stored value, 16182 DN or its DN / s, not +Inf; irispy keeps the value and marks saturation in its mask (irispy #239; #308). Reverses D57's +Inf.
- **D86:** Units print as astropy's default (`str(unit)` and WCS `world_axis_units`' VOUnit), with no code overriding astropy's unit formatting anywhere; fitting goes through models composed in glue's Fit tab and fitted over the window with `parallel_fit_dask` (#313, #314); no jdaviz-style fitting panel.
- **D87:** Fits leave saturated samples out and say how many (the window fit and irispy too); a rebinned bin is saturated only when all its samples are; a profile combining several pixels leaves a wavelength out only where every pixel it combines is saturated, noting the biased ones.
- **D88:** #307's Stokes limits (Q and U at ±5σ, V at ±10σ) stay the quicklook's default; #312's emptying of a Point on removed data stays; #314's model builder stays as built; a fit made in km/s converts exactly to Å; 'Fit every spectrum' sits beside Fit on the Fit tab (#317).
- **D89:** No PR to glue, glue-qt or astropy until the glue-solar work is done; then a full review decides what is upstreamed and what stays (UPSTREAM_REVIEW.md, `wp0-upstream`), re-verifying every report candidate and perf finding first; smaller ports go on fork branches meanwhile; the matplotlib-free WCSAxes core is raised with astropy in person and not tracked here.
- **D90:** Do all the polish (#316, #319, #321-#323, #326), one light-curves entry against Time and one path tool on IRIS viewers; keep Loop, Blink and Follow/lock (upstream candidates), the browser, every colormap and gamma stretch, and every analysis, quicklook and tool extra; none of the audits' internal changes.
- **D91:** glue-solar pins irispy main at a commit it is tested with, and a 'follow irispy' PR moves the pin with glue-solar's fixes after each batch of irispy changes, so an irispy merge never turns CI red. Amends D47.
- **D92:** irispy main settled after the pre-beta PRs (its history was rewritten): glue-solar tracks irispy's git main again, the follow-irispy PR unpinning it; D91's pin returns only while irispy changes in batches.
- **D93:** #328 keeps astropy's default `chunk_n_max` (500): slabs alone cut a Si IV window's pickled data from 28.8 to 3.1 GiB.
- **D94:** After irispy #256, 'IRIS: remove dust' refuses a rebinned or regridded slit-jaw image up front (#327).
- **D95:** #329 drops the loader's gzip step, accepting about a 3x transient peak while a gzipped SJI opens; the lasting cure is astropy's `_array_from_file` viewing a `BytesIO` (a fork branch, `wp0-upstream`).
- **D96:** The main lines are irispy's documented ones (`get_lines(main_only=True)`, 25 lines), Mg II k and h named by glue-solar, a window of several lines taking its own ion's line nearest its name (#330); line groups are dropped; 'Lines in this range…' (#332) is irispy's ranked query for the quiet Sun, an active region or a flare.
- **D97:** SST cubes and other non-IRIS data link to each other without IRIS data ('Link helioprojective coordinates' anchors on the first helioprojective dataset); 'Link points across cubes' is on by default (#337); 'Lines in this range…' offers coronal or photospheric abundances; gzipped rasters are inflated once, by an irispy fix first (#345); IRIS-only wording on shared features was fixed (#333); the WCSLIB -TAB inverse goes to WCSLIB's author by the user's email.
- **D98:** SST spectrum and light-curve panels refit their y range only while showing the last fit's range or Home's (#343); IRIS fits draw in a darker shade of the layer's color, 1.5 times its width (#335); 'Lines in this range…' lists its lines with check boxes, per viewer and not saved (#338); the IRIS fitter's Settings get an 'Mg II two peaks' preset (#334).
- **D99:** A path's vertices can be typed (#341); the model builder gets Save and Open of a model (#340); explicit emission or absorption, ties to any line and an editable degree are not worth adding.
- **D100:** The SST stress survey was re-run on current main on the Mac and the Linux machine, extended to the quicklook era (GLUE_SPEED.md 'SST performance survey 2, 2026-10-20'); Linux runs use scripts in `IRIS_PLAN_PROTOTYPES/scale_checks/` the user pulls and runs.
- **D101:** An IRIS observation's own data keep linking as the browser and quicklook load them (D20); all other data (SST, SOT, AIA, maps, files opened) link only on request, to whatever they can be linked to, IRIS loaded or not; no automatic linking of all overlapping data.
- **D102:** DKIST loader: glue gets its own APE-14 coords, the world axes reordered to glue's one-per-pixel-axis order and longitude and latitude wrapped to ±180°; a slit raster's step axis is longitude when it scans and time when it is sit-and-stare; glue's WCS autolinker gets a probe-gated patch of its general path; DKIST datasets link to each other through glue's WCSLink and to IRIS through 'Link helioprojective coordinates' with time links; a VBI mosaic opens one Data per tile, linked to the centre tile, as layers of one Image viewer; an IRIS point reaches a DKIST raster with repeats or measurements by slit position too, nothing past half a step (user, 2026-10-28).
- **D103:** After profiling the six complete DKIST datasets (every cost is CPU): no frame cache; GlueWCS keeps its last 64 coordinate calls, DKIST data read only the file tiles a view touches, an Image buffer reads only the pixels glue samples (#383); a DKIST point profile is taken at the viewer's current Stokes, repeat and measurement; the quicklook shows a Cryo-NIRSP measurement axis as a slider; spectrograph quicklook maps are drawn as IRIS's; dkist's one-sided `Ravel` clip and out-of-range inverse are worked around in GlueWCS, with dkist reports drafted; a mosaic's tiles keep their links; DKIST data keep up to 4096 FITS files open; CARJML's remaining cost goes to glue as reports.
- **D104:** glue-solar follows the latest release of every package it imports: each dependency floor is its latest release, raised as new ones come out (`wp0-release-tracking`); one env of the latest releases replaces the baseline and floor envs; no code for older releases (#382).
- **D105:** 'Quicklook…' on a ViSP or Cryo-NIRSP spectrograph dataset adds a loaded context imager observed at the same time over the same field, as IRIS's quicklook adds slit-jaw images; a VBI mosaic shows all its tiles; the raster and the imager follow each other both ways in time; the imager panel draws the raster's current slit and the shared point (#387).
- **D106:** Following irispy's gwcs port (#360): glue gets each IRIS raster's FITS -TAB WCS (`cube.fits_wcs`), not a wrapper of irispy's gWCS, whose inverse needs the raster step as a world input glue's links cannot give; the follow-irispy PR waits for #360 to merge, then repins to irispy main's merge commit.
- **D107:** DKIST's lines come from glue-solar's `GROUND_LINES` table (named for the ground-based telescopes since SST cubes take it too, D111, #399), in vacuum or air as the data's spectral axis is; full-Stokes DKIST data scale Q, U and V by their noise level, I by its percentiles; a DL-NIRSP integral-field mosaic is viewed as linked tiles in one Image viewer with a spectrum at the point.
- **D108:** A DKIST mosaic (DL-NIRSP's and VBI's) also gets a stitched image by reproject: a 'Mosaic…' action reprojects the tiles at the viewer's current wavelength, Stokes and frame into one 2-D image, a new dataset linked by 'Link helioprojective coordinates' (#391); reproject is a dependency at its latest release.
- **D109:** A click on any tile of a VBI mosaic's imager panel moves the pair quicklook's point; a 'Mosaic…' image opens at 99.5 % limits; the noise level is sampled from 4 frames of 2500 values; Q, U and V noise limits stay in the quicklook only; whichever pair panel leads the time moves the other, as IRIS (D7).
- **D110:** Footprints are an overlay on any helioprojective Image viewer, a 'DKIST footprints…' action drawing each loaded DKIST dataset's outline and a raster's slit from the ASDF alone; frame-quality curves are a Profile-style panel against time, linked to the dataset by time; 'Download these frames…' defaults to the files of the current Stokes and repeat over a step or time range, shows their count and size, and sends the FITS files alone (dkist's lower-level transfer, guarded with a fallback).
- **D111:** A session's restored 'Row at the point', 'Column at the point' and light curves stay where they were saved, as #224 made them; SST cubes label their lines from glue-solar's table in air, as SSTRED's wavelengths are, a cube of two table lines taking the one at its line core (#398).

## Milestones

A milestone is done when it has no items left. M0, M2 (analysis, display and export), M3 (specialist) and WP13 (other missions) are done.

- **M1: navigation and spectral parity.**
- **L: Later.** Deferred by the user; not a gate. Deferred without an item: whisker polish (F143), CRISPEX entry keywords (F020), a SPECTFILE-style mean-spectrum reference (F031) and scripting beyond #77's recipe (F033).
- **M4: upstreaming.** On the user's direction: upstream PRs and reports (UPSTREAM_REVIEW.md), the user's drafts, irispy's release; a release with a fix retires its workaround.

### Checklist by milestone

**M1**
- WP0: `wp0-release-tracking`
- WP10: `wp10-follow-irispy`

**Later**
- WP0: `wp0-qt68-macos-pass`

**M4**
- WP0: `wp0-upstream`, `wp0-irispy-release`, `wp0-wcslib-tab-inverse`

## Work packages

### WP0: Upstream integration, reviews and releases

Upstream work in glue, glue-qt, irispy, astropy and dkist that retires the workarounds in `glue_solar/glue_patches.py` and the loaders, the reviews of main, and release tracking.

**M1**

- [ ] **M1** `wp0-release-tracking`: After each release of a package glue-solar imports, raise its floor to it (D104) in a new env of the latest releases, retire the workarounds it fixes (`docs/dev_guide/workarounds.rst`) and update the guides it affects. Release WAITs (UPSTREAM_REVIEW.md 'Glue-solar changes now'): a dkist release with #765 drops `_off_frames` and DKIST's NotImplementedError path; an irispy pin past #320 drops the `FitInfoSubset` dict conversion; a pytest release fixing #15287 restores `monkeypatch.setattr(settings, ...)` in `test_dkist.py` and `test_quicklook.py`; the astropy floor rises to the first release bundling WCSLIB 8.9, whose `wcserr_set` no longer leaks 64 B per pixel outside a -TAB table; once glue-qt releases a `glue -x` fix, the macOS app's check runs `smoke.py` with `-x` and `GLUE_SOLAR_APP_CHECK` goes (216-2); as glue #2596/#2601 and glue-qt #70/#74 ship, the guides drop the caveats they lift. The macOS app (#216, `packaging/macos/build_app.sh`, D55) is rebuilt on the final releases as the plan's last deliverable, and 'IRIS: user guide and issues' then opens the installed release's docs, not 'latest' (160-x1). Done when each release's PR names its floors and retired workarounds; no line here.

**L**

- [ ] **L** `wp0-qt68-macos-pass` (F203): Manual macOS check of glue-qt #68 (font, menus, Cmd-Tab, Dock name) on PyQt6; once glue-qt releases #68, check that conda-forge's glue-qt requires `pyobjc-framework-cocoa` on macOS. Done when both are recorded.

**M4**

- [ ] **M4** `wp0-upstream` (D89): work through [UPSTREAM_REVIEW.md](UPSTREAM_REVIEW.md) on the user's direction: 165 items re-verified against the latest releases and mains (104 UPSTREAM-PR, 24 REPORT, 14 WAIT, 13 KEEP, 8 DROP; reproducers in `IRIS_PLAN_PROTOTYPES/upstream_review_20261019/`), each with its recommendation and the glue-solar code it retires, in the review's order: the ready fork branches (glue `perf-g*` and `ape14-wcs-link`, glue-qt `fitter-settings`, `fitter-settings-widget`, `fit-artists` and `perf-q*`, astropy `perf-a1-wcsaxes-pytest-import`, and the branches in `~/Downloads/glue-solar-upstream/` on the Linux machine), the user's drafts (glue #2595 WCS autolink, #2597 session cmap and meta, #2598 correlated-axis inverse, #2599 datetime epoch, #2601 Profile WCSAxes; glue-qt #68 macOS integration and #69 CI fix, ready; #70 Profile sliders and km/s axis, #74 cursor readout, #75 time slider labels), with the Qt and `glue_solar` suites run on the merged heads before they are marked ready and the user reviewing each, the astropy#19174 comment, then small fixes, medium PRs, reports and the generic glue-solar features. Once a core release has #2595, its `WCSLink` suggestions serve IRIS dataset pairs (F049, F054), retiring `_GlueWCS.has_celestial = False` with `link_hpc` subsets unchanged. glue-solar has no guard against zero-size WCSAxes (a minimized panel), to add if one is seen. Done when each row is filed, merged, kept or dropped, and each draft is merged, closed or parked.
- [ ] **M4** `wp0-irispy-release`: an irispy release after #360 merges (D47), with the irispy-side checks settled (exposure times, rolled-SJI gWCS, binned `slit x position`, per-step pointing), each with a test or a user decision; glue-solar then tracks irispy's git main again (D92) and the PyPI releases follow. Done when a release has them.
- [ ] **M4** `wp0-wcslib-tab-inverse` (user, 2026-10-09; the user emails WCSLIB's author first, D97; the email and its reproducer, redrafted on 2026-10-29, are in `~/Downloads/glue-solar-upstream/wcslib/` on the Linux machine): fix the slow -TAB inverse in WCSLIB's `tab.c` itself (R8, D54), on a fresh astropy clone, as a branch on the user's astropy fork and a diff for WCSLIB's author. Done when the user has both.

### WP10: Loader robustness and performance

Keeps the IRIS loaders in `glue_solar/sources/loaders/` correct and fast on files up to 20 GB.

**M1**

- [ ] **M1** `wp10-follow-irispy` (D91, D106; user 2026-10-20 to 2026-10-29): the follow-irispy PR, branch `follow-irispy-main` (its state in Current state), opened once irispy #360 merges. It carries (a) empty raster files: IRIS Level 2 raster files with no data (every window raw fill, DATE_OBS and DATE_END empty, an empty last table; 3660100039 has 8 of 450, the flare 3860258481 5 of 180) made irispy's `read_files` raise and fail the whole observation; irispy #301 (merged 2026-10-21) reads them as missing with their times and pointing worked out, and glue-solar makes `Coordinator.point_on` return None for a NaN pixel; (b) the big stack: 3860107071 (1230 files, 9 windows and 3 SJIs) loaded in 73 s and restored in 75 s on main with irispy f058705 and 161 s on #360's early head; batched reads from #360's 4-D cubes and the user's irispy-side changes (c58ef2b, 5d662b1) bring it to 24.6 s and 24.3 s (`bench360b/RESULTS.md` in the Linux session archive); (c) two register entries, the Profile patch's (FI6-1) and the batched reads' (`fix25/follow-batched/register-row.md`). Done when the PR is on main, both observations open in the browser and quicklook with their empty scans at their times, and the big stack loads in about 25 s.

Notes:
- IRIS Level 2 image HDUs are int16 (BSCALE 0.25, BZERO 7992; fill is raw -32768/-32764). glue-solar reads SJIs and AIA cutouts through irispy's `read_sji_lvl2(memmap=True)`, whose raw int16 keeps the fill under a lazy mask; a `.fits.gz` SJI is decompressed once into memory (#329, D95); a gzipped raster file is opened in memory once, just before irispy reads it (#345, #352, D97).

## Workaround register

The register is [`docs/dev_guide/workarounds.rst`](https://github.com/glue-viz/glue-solar/blob/main/docs/dev_guide/workarounds.rst) on main: one entry per patch or override of glue, glue-qt, echo, astropy, WCSLIB, dkist or mpl-scatter-density, with its switch and the upstream change that retires it; a PR that adds or retires one edits it, and UPSTREAM_REVIEW.md re-verifies each entry. Planned workarounds are named in their items (the follow-irispy PR adds two, `wp10-follow-irispy`).

## Validation, environments and data

Run all Python in a micromamba env, never a `.venv`; create a new env rather than change one. The envs, data and machines are in [IRIS_PLAN_PROTOTYPES/OPERATIONS.md](IRIS_PLAN_PROTOTYPES/OPERATIONS.md).

Headless runs use a scratch `HOME` (glue rewrites `~/.glue/settings.cfg`), offscreen Qt and Agg; glue-solar's conftest keeps tests off macOS QSettings (D75). Run tests from a checkout of the code under test, never `~/Git/glue-solar` (on `plan`); `run_checks.py` makes its own HOME and caches and removes them when it ends, but for astropy's cache, kept so the IERS tables download about monthly:

```sh
P=~/Git/glue-solar/IRIS_PLAN_PROTOTYPES
env PYTHONPATH=$P <env>/bin/python -B $P/run_checks.py "$PWD:$P" glue_solar --remote-data=any
```

glue-solar tests only the GUI and glue side, with the loaded dataset's own coordinates as oracle; irispy's reading, WCS and numerics are irispy's tests. Real-data tests are `@pytest.mark.remote_data` tests on LM-SAL/irispy-data release assets (tag `v1`) via the `irispy_data` fixture, never local paths or committed data; a missing cutout goes into irispy-data first, on the user's direction. irispy's decimated CI fixtures (`find_irispy_test_file`) are not physical validation. CI's core job runs with coverage on four xdist workers, several times slower than local runs: keep test fits small and waits at 60 s.
