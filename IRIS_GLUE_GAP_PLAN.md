# IRIS and Glue cross-repository work plan

Updated 2026-09-27 (America/Los_Angeles). This file is the single maintained
work plan for glue-core (`~/Git/glue`), glue-qt (`~/Git/glue-qt`) and
glue-solar (`~/Git/glue-solar`). Its target is an IRIS quicklook in Glue that
covers what SolarSoft's CRISPEX offers IRIS users.

This revision restructures the plan after a verified review (2026-09-27).
Branch and validation history moved to the archive. Work is organised by
milestone (M0 to M3) and work package (WP0 to WP12). Each checkbox has a key,
a milestone, a testable done condition and the CRISPEX features it covers.
The previous version is kept in
[archive/2026-09-27-restructure](IRIS_PLAN_PROTOTYPES/archive/2026-09-27-restructure/IRIS_GLUE_GAP_PLAN.md).

This plan and `IRIS_PLAN_PROTOTYPES/` live on the glue-solar branch `plan`
(from 157cf44). That branch is pushed to the public glue-viz/glue-solar
repository and must never be merged or opened as a PR. Production work
happens on feature branches from `main`; never stage the plan or the
prototypes there. Committing or pushing plan updates, and any documentation
commit, push, PR, merge or review request, happens only when the user asks.
Because the branch is public, write only repo-relative or `~/` paths here.

Companion files:

- [IRIS_CRISPEX_FEATURES.md](IRIS_CRISPEX_FEATURES.md): all 203 CRISPEX and
  IRIS-SolarSoft features (F001 to F203), each mapped to a checkbox key or
  marked as available today, excluded, or covered by an equivalent.
- [IRIS_PLAN_PROTOTYPES/README.md](IRIS_PLAN_PROTOTYPES/README.md): the
  prototypes that remain useful and what to port from each.
- [IRIS_PLAN_PROTOTYPES/review_20260927/](IRIS_PLAN_PROTOTYPES/review_20260927/README.md):
  the verified review, feasibility probes and prototype verdicts behind this
  revision. Finding ids such as `wp4-quicklook-1` and `followup-2-1` resolve
  there.

## How to use this plan

1. Pick an unchecked checkbox in the earliest open milestone. Read its done
   condition, the features it lists (in the companion file) and the cited
   findings. Trace the current code before adapting a prototype; this file
   takes precedence over prototypes and archived text.
2. Before acting on a PR or release gate, refresh GitHub state. The
   snapshot below is dated.
3. Run all Python in a micromamba environment (see
   [Validation](#validation-environments-and-data)), never the solar `.venv`.
4. Preserve unrelated changes and the index. Stage named files only when a
   commit is requested.
5. Record completion on the checkbox: branch or commit, test command and
   result, validation limits, and anything left over. A prototype pass is not
   a production implementation, and merged glue-solar code is not released
   code (glue-solar has no release yet).
6. The GitHub wiki (`glue-viz/glue-solar.wiki`) is a public digest refreshed
   from this file (WP9). Never record status there first, and keep local
   paths, prototype links and environment notes out of it.

## Goal and scope

CRISPEX is the reference for the browsing workflow, and `iris_xfiles` for
local observation discovery. Primary references: the
[CRISPEX repository](https://github.com/grviss/crispex) and its
[entry point](https://github.com/grviss/crispex/blob/master/crispex.pro), the
[IRIS-9 CRISPEX exercises (archived copy)](https://web.archive.org/web/20250429073324/https://tiagopereira.space/iris9/exercises/tutorials_idl.html#crispex)
(the live page returns 404), and
[ITN 26](https://iris.lmsal.com/itn26/). CRISPEX has no licence file, so
features are reimplemented from their documented behaviour; no CRISPEX code is
ported.

Scope, set by the user on 2026-09-27: every feature in the companion file
except the exclusions below. That includes Level-3 file input, density and
temperature diagnostics, and the browser search extras. Priorities decide the
milestone, not whether a feature is in scope.

Excluded:

- Permanent non-goals: Level-3 FITS writing and EIS support.
- Excluded by the user on 2026-09-27: the detector mosaic viewer
  (`iris_xdetector`), an OBS XML table viewer and a pipeline-log viewer.
- Not applicable to IRIS: Stokes/polarimetry and SST/CRISP-only inputs
  (La Palma cubes, SOLARNET cube conventions, detection files, simulation
  height cubes, legacy converters).
- IDL implementation details that Glue replaces with an equivalent: the
  transposed "sp" cube, window IDs, the control-panel clone, and the
  `SPECTFILE`, `LINE_CENTER` and `NO_WARP` keywords. The companion file names
  each equivalent.

## Current state, 2026-09-27

On glue-solar `main` (236f0a8): the IRIS observation browser and loader
(#44, with fixtures #50), a datetime64 `Time` component on SJI, raster and
stack datasets, the `solar:frame_time` and `solar:cursor_readout` Image
Viewer tools (#52), and transparent NaN pixels for IRIS image layers (#53).
On released core, sessions that contain any glue-solar dataset fail to save,
including sunpy Maps opened with File → Open (`archive-trace-5`); WP3 fixes
this. No glue-solar release exists yet.

Reference environment (micromamba `iris-plan`): released glue-core 1.27.0,
glue-qt 0.4.2 (PyQt5), irispy-lmsal 0.9.0, astropy 8.0.1, sunpy 8.0.0,
Python 3.13, glue-solar editable. The `glue_solar` suite gives 34 passed,
1 skipped. The skip is the APE-14 autolink test, which needs core #2595.
The solar cursor-readout test runs because glue-qt 0.4.2 lacks
`cursor_status`.

Latest releases: glue-core v1.27.0 (2026-06-25), glue-qt v0.4.2
(2026-02-11), irispy-lmsal v0.9.0 (2026-09-10). Open upstream PRs, checked
with `gh` on 2026-09-27 (heads unchanged since 2026-09-22 except where noted):

| PR | Branch | State | Head | Relevance |
| --- | --- | --- | --- | --- |
| glue #2595 | `ape14-wcs-autolink` | Draft | `c49aeb1af14a` | APE-14 low-level WCS autolinking (WP1, M1) |
| glue #2596 | `profile-slice` | Draft | `1deff2999c9a` | Slice profile function; land before #2601 |
| glue #2601 | `profile-wcsaxes` | Draft | `acaf4e1c0ef8` | Profile WCSAxes; contains #2596 |
| glue #2597 | `fix-session-style-meta` | Draft | `bfe16085ea57` | Colormap/meta session fixes (WP3) |
| glue #2598 | `fix-world2pixel-correlated-axes` | Draft | `ca3fb185e5a4` | Correlated-axis inverse (WP1 workaround until released) |
| glue #2599 | `fix-datetime-epoch` | Draft | `dd881a47bb40` | Datetime epoch (WP7 GOES dates) |
| glue #2603 | `line-layer-artists` | Draft | `34d1f0c622d5` | Upstream line layers; a later base for WP4/WP5/WP7 lines and markers (`wp0-track-line-layers`) |
| glue #2604 | `fix-region-wcs-image-2600` | Ready | `d2ddfa57774f` | Fixes issue #2600 (WP7 FOV overlay) |
| glue-qt #66 | `path-slicer` | Draft (upstream author) | `0797f6254188` | Generic path slicer (WP12) |
| glue-qt #68 | `macos-integration` | Ready | `aefab0dda25c` | macOS integration (WP0) |
| glue-qt #69 | `ci-fixes` | Ready | `b5778ef5027a` | CI fixes (WP0) |
| glue-qt #70 | `profile-wcs-pr` | Draft | `f1471b7ad843` | Profile sliders and WCSAxes wiring |
| glue-qt #73 | `line-layer-artists` | Draft | `2f9ccfb65c5e` | Qt side of #2603 |
| glue-qt #74 | `status-bar-cursor-readout` | Draft | `6b579814eb7c` | Generic cursor readout; a release retires only the generic part of `solar:cursor_readout` |
| glue-qt #75 | `slice-widget-time-axis` | Draft | `8852fcd13ca8` | Absolute-time slider labels |

"Ready" means the draft flag is off, not maintainer approval. WP0 tracks these
PRs; no feature in M0 depends on any of them.

## Decisions and contracts

Settled decisions. Do not re-open them without the user.

- **D1 (link_hpc):** keep `link_hpc` permanently. It supplies exact,
  per-frame, time-aware world coordinates and world-component subsets between
  IRIS datasets. It is the only spatial link between IRIS datasets on
  released glue-core 1.27.0. APE-14 `WCSLink`s (core #2595) describe frame-0
  geometry. When present they are the 1-hop path, so they win every pixel
  path (ROIs, Pixel subsets, markers, overlays). On the 4.8-hour sit-and-stare
  fixture the frame-0 mapping is off by 42.2 arcsec at the last frame
  (irispy 0.8.1 and 0.9.0). Earlier reach figures are withdrawn and are
  never test targets. One came from a forbidden all-ones correlation matrix
  plus a lambda link; the other from irispy 0.8.1's SJI fixture, whose CDELT
  is 10x too small (`wp1-links-2`, `wp1-links-3`, `followup-1-4`). Never add
  an SJI world-time link (`followup-1-5`).
- **D2 (where code lives):** implement IRIS features in glue-solar through
  public glue registries: viewer tools, layer actions, menubar plugins,
  startup actions, data factories, unit converters and savers.
  - Temporary workarounds are switched on by a behaviour probe, not a
    version number. Each one names the upstream fix whose release removes
    it. pyproject floors change only when a release contains that fix.
  - Patching a private method is allowed only for Profile restore priority,
    Pixel crosshair visibility and physical aspect. Each is gated, tested and
    listed in the WP0 workaround register with its upstream PR.
  - Calling a private method, or overriding one in a subclass, is not a
    patch. Each such use still gets a register row and a signature test on
    the released baseline (the WP5 km/s axis tool, the WP11 Space key, the
    WP12 path tools).
  - Always-on rows (the `_GlueWCS` RLock, the WP5 line-list artist) state why
    they have no probe (`archive-trace-7`, `wp1-links-8`).
  - New upstream PRs are appropriate for generic fixes and capabilities, as
    with Qt #74 and #75. Opening, readying, requesting review of or merging
    any PR needs the user's direction (`archive-trace-12`), and solar work
    never waits for it.
- **D3 (display units):** arcsec for helioprojective axes and Angstrom for
  wavelength, in both the low-level values and the high-level coordinate
  objects. This covers `_GlueWCS` IRIS data and glue-solar's own sunpy Map
  loaders. WP1 wraps those maps in `_GlueWCS` in M1, so `link_hpc` covers
  File → Open maps too.
- **D4 (analysis products):** moments and fits are dataset `layer_action`s
  that add data and links without opening a viewer.
- **D5 (M0 baseline):** M0 runs on released glue-core 1.27.0, glue-qt 0.4.2
  and irispy-lmsal 0.9.0. No unreleased PR is an M0 prerequisite.
- **D6 (selection):** M0 uses the stock Pixel tool (click or drag follows,
  release holds) plus an explicit "Clear point". M1 adds a CRISPEX-style
  hover-follow tool with click-to-lock. It is a required M1 tool, not an
  optional one.
- **D7 (coordination defaults for M0):**
  - The selected point is a fixed detector pixel. There is no world tracking
    from the scan-0 stack WCS.
  - Time is shown on index axes (scan, exposure, frame) with timestamp
    readouts. The time-axis adapter is M1: `wp12-time-regrid` adds a
    separate regridded Data for sit-and-stare exposures, SJI frames and stack
    scans.
  - Nearest-exposure ties go to the earlier exposure.
  - There is no match when the offset exceeds half the partner's median
    cadence, or the time is outside the partner's coverage. The partner panel
    is then greyed and shows the offset, never a clamped frame.
  - The raster is the time master by default. A visible control switches it
    to an SJI.
- **D8 (time sync mechanism):** in M0, WP4 time sync uses no glue links. A
  coordinator derives 1-D nearest-index and signed-offset arrays from each
  dataset's `Time` and moves the sliders itself. It never resolves
  `data[other_pixel_cid]` through the link graph.
  - Links from main components into pixel component IDs are forbidden. They
    break the SJI Pixel spectrum path and crash overlays (`wp4-quicklook-1`,
    `followup-1-1`, `followup-1-2`).
  - Links to plain "Exposure index"/"Frame index" components (design B) may
    be added later, only if time-gated subsets are wanted and only with the
    combined-graph permutation regression. Design B uses identity
    `ComponentLink`s on precomputed nearest-index components: never
    `JoinLink`/`join_on_key` (a key join makes otherwise incompatible spatial
    ROIs select the whole partner dataset) and never lambda or closure links
    (not session-safe).
- **D9 (coordination architecture):** coordination is the registered viewer
  tool `solar:coordinate` (the `solar:frame_time` pattern) plus one
  coordinator per DataCollection. The tool is on every Image viewer from M0
  (`wp4-coordinator`) and on Profile viewers from M1
  (`wp4-m1-spectral-coupling`). glue-qt instantiates tools for restored
  viewers too, so restored viewers re-register without a wrapper.
  `wp3-coordination-reattach` (M1) restores the time master and the followed
  point. Never wrap `app.new_data_viewer`.
- **D10 (negative-step rasters, STEPS_AV < -0.01):** keep irispy's default
  orientation.
  - glue-solar derives masks and NaNs from the flipped data values and
    reverses the per-step metadata itself.
  - `nearest` accepts unsorted and duplicate references, with first-index
    semantics.
  - irispy's `revert_v34=True` is the documented alternative.
  - WP0 reports the irispy mask/meta bug.
- **D11 (rest wavelength):** use an explicit override, else the packaged
  line-list laboratory (vacuum) value matching the window, else none. The
  user picks for multi-line windows (C II 1334/1335, Mg II k/h). Never fall
  back to TWAVE silently: the Mg II k window's TWAVE is about 16 km/s off.
  Continuum windows get no km/s. Store the value as a float
  `meta['rest_wavelength']` in Angstrom so it survives sessions. Confirmed
  by the user on 2026-09-27: a multi-line window gets no rest wavelength on
  load, so velocities wait for the user's choice. The dialog pre-selects the
  line the window is named after.
- **D12 (missing and saturated data):** -200 and -199 are missing and become
  NaN, as in IRIS-SolarSoft: `iris_make_fits_level3` NaN-fills values below
  -198.5, and `iris_raster_browser` uses missing=[-200, -199].
  - AIA cutouts count only -200 as missing, because -199 is unverified for
    AIA (`wp10-fill-nan`).
  - Saturation is +Inf (ITN 26).
  - Masks are stored as uint8, because glue coerces bool to int64.
- **D13 (session savers):** register the Quantity saver only if none exists,
  and propose it to core. Port WP3 as `_GlueWCS.__gluestate__` /
  `__setgluestate__` and named factory functions, never by importing
  prototype modules.
- **D14 (irispy development branch):** track irispy `gwcs_raster_clean`
  only. Do not propose it upstream until the glue-solar loader accepts both
  APIs. M0 stays on irispy 0.9.0.
- **D15 (layout):** the quicklook preset uses an MDI tab with explicit
  viewer geometry, not the experimental fixed-layout tab. The fixed-layout
  tab breaks `app.viewers` and is not restored from sessions.
- **D16 (Doppler image sign):** red minus blue,
  D(Δ) = I(λ0 + Δ) − I(λ0 − Δ). A positive value means a brighter red wing,
  i.e. redshift, consistent with positive velocity = redshift. This matches
  CRISPEX's in-program Doppler image (`lp_dop`) and ITN 26. Decided by the
  user on 2026-09-27; the sign is recorded in the component name and
  `meta['doppler_sign']`.

Defaults proposed during the restructure and confirmed by the user on
2026-09-27:

- SJI/SJI links under #2595: amend #2595 so autolinking leaves time axes
  out between datasets. WP4 matching is authoritative for time
  (`core-qt-capabilities-1`, `wp0-own-draft-updates`; acceptance check (c)
  of `wp1-m1-autolink-matrix`).
- SJI and raster when a WCSLink and `link_hpc` coexist: keep both and
  document the frame-0 pixel geometry. The coordinator translates SJI clicks
  itself through per-frame WCS and `Time`, which works on released core.
  This is M1 work (`wp1-m1-sji-to-raster`, `wp4-sji-click-to-raster`); in
  M0 the raster is driven from raster-map clicks only.
- `wp7-aia-context`: one download in a Worker gives a full-disk locator
  plus an FOV crop with a configurable margin (default 100 arcsec). The crop
  is offered only when no same-observation `aia_l2` cutout is loaded. This
  narrows the agreed "no local cutouts exist" rule because the action does
  not scan the disk.
- `wp7-goes-context`: the action picks the lowest-numbered GOES satellite
  covering the whole interval, else the one with the longest coverage, and
  names it. The confirm dialog can choose another.
- `wp1-m0-irispy-baseline`: the first WP1 port PR raises the pyproject floors
  to glue-core 1.27.0 and glue-qt 0.4.2. irispy-lmsal stays >=0.8.1, covered
  by the floor env `iris-plan-floor`.
- `wp1-m0-link-hpc`: until `wp10-m1-roi-world-polygon`, the guide documents
  the ~10 s per SJI frame freeze of stock raster ROIs in browser-opened
  viewers. The alternative is to extend `wp10-m0-roi-guard` to those viewers.
- `wp1-m1-sunpy-maps`: the sunpy Map factory gets a 2-D helioprojective
  identifier at priority 150, below IRIS at 200.
- `wp10-nonblocking-load`: non-blocking load is M1, so each ticked pick
  freezes the GUI for 1.0–3.1 s in M0.
- `wp4-launch-entry`: `glue --startup=iris_quicklook` opens the single-raster
  preset on the first scan. Stacks need the browser's Stack option.
- `wp4-quicklook-preset`: when both SJI variants exist, the plain SJI opens
  first and the deconvolved one is an option.
- `wp3-session-budget`: the opt-in float32 WP6 residual is embedded in
  sessions and is outside the session budget.
- `wp8-derived-files`: non-Level-2 SPEC files are skipped and counted in the
  progress text, not listed.
- `wp8-prescan-search`: the importer passes `first_raster_header_only=True`,
  so a damaged later raster repeat is found only at load time.
- `wp12-time-regrid`: a separate regridded Data, which `link_hpc` skips, not
  an in-place WCS change.
- M0 acceptance data (the M0 list) and the `wp10-m0-acceptance` budgets with
  the `wp10-mask-uint8` memory limits (`plan-integrity-8`): the user may
  replace the datasets or the numbers.

Cross-package contracts:

- `link_hpc(data_collection)` returns links; callers use
  `data_collection.add_link(link_hpc(data_collection))`. It is idempotent,
  pairs by physical type, and assumes `_GlueWCS` standardises angles to
  arcsec. Do not link degrees to arcsec with `LinkSame`. It skips Data that
  `wp12-time-regrid` marks in meta.
- Keep the SJI `Time (Utc)` world axis distinct from the datetime64 `Time`
  component. Match physical types, not labels. Glue title-cases gWCS names,
  so irispy's `Time (UTC)` displays as `Time (Utc)`.
- Never fake an all-ones `axis_correlation_matrix` to repair time-dependent
  inverses. Until core #2598 is released, use its correlated-axis fix
  through the gated WP1 workaround.
- Glue gives no ordering guarantee among equal-hop link paths. The winner
  depends on memory layout, not on the order links were added
  (`followup-1-3`). An IRIS link graph must never contain two equal-hop
  paths that give different values for the same component.
  `wp1-m0-link-graph-regression` runs every add-order permutation and
  asserts that all minimum-hop paths to each target component give equal
  values.
- Derived spatial maps (WP2 moments, WP6 fits and similar) use
  `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`: unwrap the source once,
  slice its raw WCS and rewrap once. Do not use irispy's rebuilt 2-axis -TAB
  WCS, because the saver cannot store it (`wp3-wp5-3`).
- Components added after loading are written into sessions in full.
  Derived index or broadcast components must use a compact component class
  that saves only its 1-D vector (WP3).
- Rest wavelength: code reads only `meta.get("rest_wavelength")`, a float in
  Å, through the WP5 helper (`wp5-m1-rest-wavelength-policy`). irispy's
  SGMeta `rest_wavelength` property returns TWAVE and is never read (D11).
- The `_GlueWCS` RLock (`wp10-m0-wcs-lock`) covers only calls through
  `_GlueWCS`. Code that reads the raw astropy WCS (the WP2 rewrap, the WP6
  map build) holds the exported lock or works on its own deep copy.
- Tool menus: glue-qt 0.4.2 attaches a menu only to
  `DropdownTool`/`SimpleToolMenu` buttons and drops plain
  `Tool.menu_actions` and `CheckableTool` menus. Use a `SimpleToolMenu` whose
  subtools restore the active mouse mode, or a panel shown while a checkable
  tool is active.
- WP3 must not globally replace the `VisualAttributes` serialization for
  ordinary datasets. Plain sessions must stay portable.
- Terminology: say "on main" or "merged" for glue-solar code, and
  "released" only for tagged releases.

## Milestones

### M0: Coordinated IRIS quicklook on released core

A user opens an observation and gets a coordinated quicklook without any
unreleased PR:

- A preset per observation type: a raster map (slit versus time for
  sit-and-stare), a spectrogram, a step- or time-versus-wavelength panel, the
  point spectrum, and one SJI viewer per channel with slit and point
  overlays. WP4 owns the panel table (`wp4-quicklook-preset`) and the fixed
  indices that the selected point sets (`wp4-m0-point-fixed-index`).
- A held Pixel point that drives the other panels' fixed indices.
- Nearest-exposure SJI/raster time sync from an explicit master, showing the
  offset and a no-match state.
- Acquisition-time readouts.
- The WP10 loader blockers fixed: fill values, mask size, negative-step
  rasters, the WCS thread crash, the large-data modal, slider latency and a
  raster-ROI guard.

M0 is done when every M0 checkbox is ticked, `wp10-m0-acceptance` passes
(the budgets) and `wp9-m0-iris9-acceptance` passes (the workflow).
`wp10-m0-acceptance` owns the pass/fail latency, crash-count and
`quicklook()` budgets, and `wp10-mask-uint8` owns the memory limits; this
file does not restate them. GUI gaps while a window loads are an M1 gate
(`wp10-nonblocking-load`).

Acceptance data (confirmed 2026-09-27), local in `~/DATA/IRIS`:

- OBSID 4000255147 (20130902_163935): sit-and-stare with SJI 1400.
- OBSID 4000005156 (20130902_182935): two-scan raster with SJI 2796. Only
  the deconvolved SJI 2796 file is local; `wp8-sji-variants` tests plain
  versus deconvolved keying with a plain-named link.
- OBSID 3824262996 (20140708_114109): 400-step Mg II raster.
- OBSID 3400109360 (20250328_225628): negative-step raster.
- OBSID 3602506433 (20260209_215233): 99-scan repeated raster, for memory
  and large-data checks only.

CI uses the irispy 0.9.0 fixtures: 20210905 OBSID 3620258102 (sit-and-stare
with SJI 1330/1400/2796/2832) and 20140329 OBSID 3860258481 (13 files of 8
steps).

### M1: CRISPEX navigation and spectral parity

M1 adds, by work package:

- WP1 and WP4: SJI click → raster spectrum, through the coordinator's own
  per-frame translation on released core (`wp1-m1-sji-to-raster`,
  `wp4-sji-click-to-raster`).
- WP1: the #2595 native pixel paths, once a release contains #2595 (gated);
  Angstrom and high-level coherence; wrapped sunpy maps.
- WP3: IRIS sessions.
- WP5: rest wavelength, velocity, line list, blink and the Doppler image.
- WP4: hover-follow with click-lock, spectral markers, multi-window, AIA
  reference panels, time controls and raster overlays.
- WP11: labelled readouts, the selected-point panel, histogram-opt and gamma
  scaling, raster colour tables, physical raster aspect and navigation keys.
- WP10: non-blocking load and world-polygon raster ROIs.
- WP8: derived-file filtering (`wp8-derived-files`).
- WP12: the regridded time axis (`wp12-time-regrid`).
- Slice profiles, once core #2596/#2601 and Qt #70 are released.

M1 is done when every M1 checkbox is ticked and two acceptance runs pass:

- The IRIS-9 CRISPEX exercise tasks run end to end in Glue
  (`wp9-m1-iris9-tutorial`).
- A saved quicklook session reopens with coordination working
  (`wp3-app-session-acceptance`).

Items gated on an upstream release, or waiting on a user decision, do not
hold M1 open. They close when the release or decision arrives:

- `wp1-m1-autolink-matrix`, `wp4-slice-profiles` and
  `wp9-m1-release-updates`.
- The "once the probe passes" clauses and probe-gated sub-checks of other
  items (for example the #2595 rows of `wp4-m1-multi-window` and
  `wp4-sji-click-to-raster`).
- `wp0-user-review`, `wp0-own-draft-updates` (both wait on the user's
  direction) and the ongoing `wp0-release-tracking`.

### M2: Analysis, context, display and export extensions

- Moment maps (WP2) and Gaussian fit maps (WP6).
- GOES and AIA context (WP7).
- Browser filter and stop, and the browser text filter (`wp8-text-filter`)
  (WP8).
- Lazy loading (`wp10-m2-lazy-loading`).
- The remaining display and inspection tools (WP11).
- Image/movie export, FITS/ECSV export of derived data, point light curves
  and path diagrams (WP12).

### M3: Later and specialist

- Lower-priority conveniences.
- Level-3 file input.
- Density and temperature diagnostics.
- Template multi-Gaussian fitting.
- Browser search extras.

### Checklist by milestone

The checkbox keys per milestone, for orientation. The work packages below
hold the tasks and their done conditions.

**M0** (49 checkboxes)

- WP0: `wp0-workaround-register`, `wp0-irispy-v34-flip`, `wp0-irispy-crpix`, `wp0-irispy-slit-units`, `wp0-irispy-tab-index`, `wp0-core-image-artist-bugs`, `wp0-qt-large-data-cancel`, `wp0-astropy-19174`, `wp0-readme-runner`
- WP1: `wp1-m0-irispy-baseline`, `wp1-m0-axis-names`, `wp1-m0-inverse-workaround`, `wp1-m0-sji-crpix`, `wp1-m0-link-hpc`, `wp1-m0-descending-step-orientation`, `wp1-m0-link-graph-regression`
- WP4: `wp4-coordinator`, `wp4-quicklook-preset`, `wp4-launch-entry`, `wp4-m0-point-fixed-index`, `wp4-time-sync`, `wp4-m0-time-wavelength-panels`, `wp4-sji-panels`, `wp4-slit-point-overlay`, `wp4-exposure-readout`, `wp4-tests`
- WP8: `wp8-test-qsettings`, `wp8-sji-variants`
- WP9: `wp9-m0-user-guide-corrections`, `wp9-m0-dev-guide-stack`, `wp9-m0-changelog-fragments`, `wp9-m0-viewer-tools-docs`, `wp9-m0-browsing-recipes`, `wp9-m0-mask-overlays`, `wp9-m0-workflow-recipes`, `wp9-m0-scripting-recipe`, `wp9-m0-iris9-tutorial`, `wp9-m0-iris9-acceptance`, `wp9-m0-docs-build`, `wp9-m0-wiki-digest`
- WP10: `wp10-fill-nan`, `wp10-mask-uint8`, `wp10-m0-negative-step`, `wp10-m0-wcs-lock`, `wp10-m0-interaction-latency`, `wp10-m0-large-data-modal`, `wp10-m0-roi-guard`, `wp10-m0-acceptance`
- WP11: `wp11-readout-icon`

**M1** (54 checkboxes)

- WP0: `wp0-stack-validation`, `wp0-user-review`, `wp0-release-tracking`, `wp0-own-draft-updates`, `wp0-core-profile-restore-priority`, `wp0-core-quantity-saver`, `wp0-core-derived-units`, `wp0-core-profile-unit-label`, `wp0-irispy-requests`, `wp0-track-line-layers`, `wp0-irispy-gwcs-branch`, `wp0-qt68-macos-pass`, `wp0-qt-aggregate-slice`
- WP1: `wp1-m1-wrapper-coherence`, `wp1-m1-sunpy-maps`, `wp1-m1-autolink-matrix`, `wp1-m1-sji-to-raster`, `wp1-dn-per-s`
- WP3: `wp3-style-cmap`, `wp3-wcs-saver`, `wp3-quantity-meta`, `wp3-plain-meta`, `wp3-file-references`, `wp3-session-budget`, `wp3-coordination-reattach`, `wp3-app-session-acceptance`
- WP4: `wp4-m1-hover-lock-tool`, `wp4-sji-click-to-raster`, `wp4-profile-aggregation`, `wp4-slice-profiles`, `wp4-m1-spectral-coupling`, `wp4-m1-multi-window`, `wp4-context-reference`, `wp4-time-controls`, `wp4-raster-overlays`
- WP5: `wp5-m1-line-list`, `wp5-m1-rest-wavelength-policy`, `wp5-m1-velocity-axis`, `wp5-m1-spectral-blink`, `wp5-m1-doppler-image`
- WP8: `wp8-derived-files`
- WP9: `wp9-m1-release-updates`, `wp9-m1-iris9-tutorial`, `wp9-m1-screenshots`
- WP10: `wp10-nonblocking-load`, `wp10-m1-roi-world-polygon`
- WP11: `wp11-cursor-readout`, `wp11-selected-point-panel`, `wp11-histo-opt-scaling`, `wp11-gamma-stretch`, `wp11-raster-cmap`, `wp11-physical-aspect`, `wp11-keyboard-shortcuts`
- WP12: `wp12-time-regrid`

**M2** (31 checkboxes)

- WP0: `wp0-track-2604`, `wp0-track-qt66`, `wp0-core-datetime-export`
- WP2: `wp2-m2-moment-maps`, `wp2-m2-line-definition`, `wp2-m2-input-quality`, `wp2-m2-tests-docs`
- WP6: `wp6-m2-fit-maps`, `wp6-m2-quality-filter`, `wp6-m2-products`, `wp6-m2-rest-key`, `wp6-m2-worker`, `wp6-m2-profile-fitter`, `wp6-m2-tests`, `wp6-m2-docs`
- WP7: `wp7-context-port`, `wp7-goes-context`, `wp7-goes-marker`, `wp7-goes-date-labels`, `wp7-aia-context`
- WP8: `wp8-filter-stop`, `wp8-text-filter`
- WP10: `wp10-m2-lazy-loading`
- WP11: `wp11-colourbar`, `wp11-distance-measure`, `wp11-zoom-steps`
- WP12: `wp12-sequence-export`, `wp12-derived-data-export`, `wp12-point-light-curves`, `wp12-path-slicer`, `wp12-path-persist`

**M3** (40 checkboxes)

- WP0: `wp0-qt68-cocoa`, `wp0-optional-proposals`
- WP1: `wp1-stack-per-scan-wcs`, `wp1-nexp-prp`, `wp1-m3-pointing-offset`, `wp1-m3-multi-instrument`
- WP2: `wp2-m3-moments-extensions`, `wp2-m3-window-data`, `wp2-irispy-calibration-actions`, `wp2-m3-mg-features`, `wp2-m3-density-temperature`, `wp2-burst-detection`
- WP3: `wp3-last-session`
- WP4: `wp4-playback-extras`
- WP5: `wp5-m3-rest-from-measurement`, `wp5-m3-reference-blink`, `wp5-m3-mean-spectrum-compare`
- WP6: `wp6-m3-rba-double-gaussian`, `wp6-m3-template-fits`
- WP7: `wp7-flare-list`, `wp7-hcr-metadata`, `wp7-aia-channels`
- WP8: `wp8-prescan-search`, `wp8-search-ui`, `wp8-browser-conveniences`, `wp8-browser-metadata`, `wp8-remote-search`, `wp8-m3-level3-input`
- WP9: `wp9-m3-saturation-recipe`, `wp9-m3-spectral-recipes`, `wp9-m3-shortcuts-help`
- WP10: `wp10-m3-sit-stare-chunks`
- WP11: `wp11-centre-on-point`, `wp11-scaling-extras`, `wp11-band-average`, `wp11-north-up`
- WP12: `wp12-export-annotations`, `wp12-profile-values-export`, `wp12-path-overlays-slopes`, `wp12-path-batch`

## Feasibility of the must-have features

All must-have features are feasible. None needs an unreleased PR for its M0
part. Full probes, measurements and the adversarial verifier's corrections are
in [review_20260927/feas.json](IRIS_PLAN_PROTOTYPES/review_20260927/feas.json).
Effort: S ≤ 1 day, M ≤ 1 week, L ≤ 3 weeks.

| Must-have (features) | Verdict | Milestone, effort | How (owner) |
| --- | --- | --- | --- |
| Quicklook layout per observation type (F190, F056, F109, F142) | Feasible on released core | M0, M | Stock viewers in an MDI tab with explicit geometry, set after the window is shown; one SJI viewer per channel. The raster map uses 'auto' aspect until `wp11-physical-aspect` (M1) (WP4, WP11). |
| Launch entry points (F012, F015, F020) | Feasible on released core | M0, M | `@startup_action("iris_quicklook")` for `glue --startup=iris_quicklook <files>`, an "Open quicklook" option in the browser and an "IRIS: quicklook…" menubar action for loaded data. No console script. Pairing is by OBSID + STARTOBS (`wp4-launch-entry`, WP8). |
| Selected point drives the other panels (F102, F134, F071) | Feasible on released core | M0, M | Registered `solar:coordinate` viewer tool plus one coordinator per DataCollection. It reacts to the Pixel subset, pins the scan on 4D stacks and coalesces drag updates (WP4). |
| Hold/unlock (F095) and hover-follow with click-lock (F094) | Feasible on released core | Hold M0, S; hover M1, M | Hold: the stock Pixel tool plus a "Clear point" subtool of the `solar:coordinate` SimpleToolMenu (`wp4-coordinator`). Lock/unlock and hover: a new throttled mouse mode (`wp4-m1-hover-lock-tool`) (WP4). |
| Master time and nearest-exposure sync with offsets and a no-match rule (F111, F112) | Feasible on released core | M0, M | The coordinator reads `Time`, matches with first-index semantics, shows the offset in the frame-time label and greys the panel on no match (D7, D8) (WP4). |
| Cross-dataset mapping (F049) | Raster → SJI feasible now; SJI click → raster feasible on released core through the coordinator | Raster → SJI M0 (`link_hpc` + overlays), S; SJI click → raster M1 (`wp1-m1-sji-to-raster`, `wp4-sji-click-to-raster`), M; #2595 native paths M1, gated | Port `link_hpc`. The coordinator translates points through per-frame WCS and `Time` and never resolves pixel IDs through the link graph (WP1, WP4). |
| Time-dependent SJI pointing and slit geometry (F050) | Feasible with a glue-solar workaround | M0, S | The point marker uses the per-frame SJI gWCS. The slit line projects the raster slit's world position through the SJI WCS at each frame. Resolve the irispy CRPIX off-by-one with the gated `wp1-m0-sji-crpix` shift before trusting sub-pixel placement (WP1, WP4; WP0 reports). |
| Missing data and histogram scaling (F164, F061) | Feasible with a glue-solar workaround | Fill → NaN M0, S; HISTO_OPT tool M1, M | -200/-199 → NaN in `_cube_data` and the stack, with uint8 masks. The preset uses the 99.5 % limits; a cutoff tool sets Custom limits (D12) (WP10, WP11). |
| Fast spectrum-versus-time access (F035) | Feasible with glue-solar workarounds | M0, S | Eager arrays plus an Image viewer with x = wavelength and y = exposure. Depends on the WCS lock and the index-free -TAB WCS below (WP10). |
| Detailed spectrum (F071) and spectral-position marker (F068) | Feasible on released core | Point spectrum M0, S; markers, mirror and km/s axis M1, M | A Profile viewer with function "mean" on the Pixel subset; controller-owned `axvline` markers; `secondary_xaxis` for km/s (WP4, WP5). |
| Lambda-t diagram at the point (F134) | Feasible on released core | Image M0, S; time/wavelength markers M1, M | A preset Image viewer with fixed indices from the point; the markers are controller-owned lines (WP4). |
| Doppler axes and readouts (F147) | Feasible on released core | M1, M | Needs the D11 rest wavelength and WP1 Angstrom. km/s as the Profile x unit waits for Qt #70, because Navigate picks the wrong slice under display-unit overrides on glue-qt 0.4.2 (WP5). |
| Position, wavelength, time and value readout (F101) | Feasible on released core | M1, M; km/s after WP5 | Split `CursorReadoutTool`: a gated generic readout from `data.coords` at the full pixel index, with a Profile branch, plus hover time and exposure in the always-registered `solar:frame_time` label (`wp11-cursor-readout`). Å needs `wp1-m1-wrapper-coherence`. |
| Physical-unit axes (F058) | Feasible on released core | M1, M | Port the WP1 `_GlueWCS` unit conversion for Angstrom. The WCSAxes "w" readout toggle and the Profile pixel/world x choice cover the pixel toggle; no image pixel-tick toggle is planned (`wp1-m1-wrapper-coherence`). |
| Image-type toggle (F057) | Feasible on released core | M0, S | The preset shows the map and the spectrogram side by side, and the stock axis combo switches a viewer (`wp4-quicklook-preset`). No dedicated tool is planned (WP4). |
| Event-finding workflow (F093) | Partly in M0 | M0 on the SJI and raster-map side; complete once SJI click → raster lands in M1 | Playback, Pixel hold, zoom and the SJI light curve work now. It is documented as an acceptance script (WP9, WP4). |
| Sessions (F175) | Feasible with glue-solar workarounds | M1, L | Port the WP3 savers. Add the gated Profile restore-priority patch, compact broadcast components, plain `rest_wavelength` meta, the index-free -TAB raster WCS record and the colormap registration fix (WP3). |
| M0 blocker: WCS thread-safety crash | Feasible with a glue-solar workaround | M0, S | A module-level `threading.RLock` around `_GlueWCS` pixel/world calls; an RLock because nested wrappers re-enter. Gate: 0 crashes in 20 runs per `wp10-m0-wcs-lock` scenario (18 locked review runs had no crash) (WP10). |
| M0 blocker: slider latency grows with exposure index | Feasible with a glue-solar workaround | M0, S | Rebuild the raster -TAB WCS without the linear RASTER index column, so wcslib indexes in O(1). Keep the original if a probe disagrees, and propose the irispy fix (WP10). |
| M0 blocker: "Add large data set?" modal | Feasible on released core | M0, S | Create the preset's Profile viewer empty, set `large_data_size = None` on that instance, then call `add_data` (`wp10-m0-large-data-modal`). |
| M0 blocker: a stock ROI → full-resolution SJI takes 10–36 s per frame | Feasible with a glue-solar workaround | M0 guard, S; world-polygon ROIs M1, M | The preset's raster viewers expose only Pixel (`wp10-m0-roi-guard`). M1 converts raster pixel ROIs into world polygons and restores the ROI tools (`wp10-m1-roi-world-polygon`) (WP10). |
| Loading blocks the GUI (not an M0 blocker; confirmed) | Feasible on released core | M1, M | Load picks, and extract archives, in the glue-qt `Worker`; OK is disabled while loading (`wp10-nonblocking-load`). In M0 each pick freezes the GUI for 1.0–3.1 s. |
| M0 blockers: masks, negative-step rasters, deconvolved SJIs | Feasible | M0, S each | uint8 masks; data-derived NaN; per-step meta reversal; filename-based deconvolved keying (WP10, WP8). |
| M0 blocker: spurious Pixel crosshair at (0,0) on spectrogram and lambda-t viewers | Feasible with a gated patch | M0, S | A gated patch of the image subset artist's visibility update, plus a core PR (WP4; WP0 register). |

## Work packages

Checkbox format: `- [ ] **M0** `key`: task. Done when: … Features: … Findings: … Depends: …`.

### WP0: Upstream integration and upstream reports

WP0 owns all cross-repository work: glue and glue-qt PRs, reports to glue, glue-qt, irispy and astropy, and the register of workarounds they retire. Primary paths: `glue_solar/__init__.py` and `glue_solar/glue_patches.py` (gated patches), `pyproject.toml` (floors), `IRIS_PLAN_PROTOTYPES/upstream/` (reproducers; add this new live folder to the `IRIS_PLAN_PROTOTYPES/README.md` live-files table). Every PR, issue or comment needs the user's direction; solar work never waits for upstream (D2, D5).

Workaround register. A behaviour probe switches each row on unless it says otherwise; the first release with the "Retired by" fix retires it. "(private)": one of D2's three private-method patches. "(private call)"/"(private override)": calls or overrides a private method, patches nothing, and a released-baseline test pins it.

| Workaround (owner) | Switched on by | Retired by |
| --- | --- | --- |
| Correlated-axis `world2pixel_single_axis` (WP1, `glue_patches.py`) | Probe: a time-dependent SJI gWCS inverts at exposure 0 | core #2598 |
| Pixel crosshair visibility (WP4) (private: `ImageSubsetLayerArtist._update_visual_attributes`) | Probe: the line shows on an axis-incompatible panel | `wp0-core-image-artist-bugs` |
| `x_display_unit` restore priority (WP0) (private: `ProfileViewerState._update_priority`) | `orig(None, 'x_display_unit') == orig(None, 'x_att')` | `wp0-core-profile-restore-priority` |
| Physical aspect (WP11 `solar:physical_aspect`) (private: per-instance `_set_axes_aspect_ratio`) | Probe: no 'Physical pixels' aspect choice | `core-physical-aspect` PR (`wp11-physical-aspect`) |
| `AggregateSlice` re-applied (WP11 `wp11-band-average`) | Probe: `sync_state_from_sliders` replaces an `AggregateSlice` | `wp0-qt-aggregate-slice` |
| `_GlueWCS` RLock (WP10) | Always on: the race cannot be probed safely | astropy fix for #19174, once each 20-run `wp10-m0-wcs-lock` scenario gives 0 crashes unlocked |
| -TAB exposure-index rebuild (WP10) | Probe: the index column is present | `wp0-irispy-tab-index` |
| SJI/AIA CRPIX correction (WP1) and the matching SLTPX1IX shift (WP4 `wp4-slit-point-overlay`) | Probe against astropy `WCS(header)` | `wp0-irispy-crpix` |
| Negative-step per-step meta reversal (WP10, D10) | WCS step-0 longitude compared with `Tx[0]`, `Tx[-1]` | `wp0-irispy-v34-flip` |
| Datetime epoch port (WP7 `wp7-goes-date-labels`; `glue_patches.py`; runtime port of #2599's two functions, never `rcParams['date.epoch']`) | Probe: `datetime64_to_mpl(t) != date2num(t)` | core #2599 |
| Quantity saver fallback (WP3, D13) | No Quantity saver registered | `wp0-core-quantity-saver` |
| `DerivedComponent` subclass whose `__gluestate__` saves `units` (WP1 `wp1-dn-per-s`) | Probe: core's saver drops `units` | `wp0-core-derived-units`; the class stays importable (sessions record its path) |
| Generic part of `solar:cursor_readout` (WP11) | `not hasattr(ImageViewer, 'cursor_status')` | Qt #74; IRIS time, exposure and km/s stay in `solar:frame_time` (`wp11-cursor-readout`) |
| Line-list artist (WP5; public `layer_artist_maker`) | Always on: a feature, not a patch | Reconsidered after #2603 and Qt #73 release |
| `SolarVisualAttributes` (WP3 `wp3-style-cmap`) | Probe: core's `VisualAttributes` saver emits a Colormap object | core #2597; loaders stop using it; the class stays importable for sessions |
| km/s Profile x-unit gate (WP5 `wp5-m1-velocity-axis`) (private call: `ProfileTools._get_axis_and_pixel_slice`) | Probe on a tiny nm-x Data: a non-native x display unit fails | Qt #70 |
| `ProfileViewerState._update_x_display_unit_choices` in the km/s-axis tool (WP5) (private call) | Always on with the tool; signature test | None tracked |
| `SliceWidget._adjust_play` (glue_qt/viewers/common/data_slice_widget.py) for Space outside the quicklook (WP11 `wp11-keyboard-shortcuts`) (private call) | Always on; the key test covers it | None tracked |
| Path tools (WP12 `wp12-path-slicer`, `wp12-path-batch`) (private override: the hooks named in WP12's Notes) | Always on; signature test on 1.27.0 | Qt #66 or the WP12 core items in `wp0-optional-proposals` |

Reports and requests. Reproducers are `IRIS_PLAN_PROTOTYPES/upstream/<slug>.py` on the released baseline in `iris-plan`; the checkbox is `wp0-<slug>` unless given; a slug closes with a URL or the user's decision not to file.

| Slugs | URLs or decisions |
| --- | --- |
| `irispy-v34-flip`, `irispy-crpix`, `irispy-slit-units`, `irispy-tab-index`, `irispy-asdf-converters` (`wp0-irispy-gwcs-branch`, only if the branch proceeds) | |
| `core-pixel-crosshair` (issue and PR), `core-translate-pixel` (both `wp0-core-image-artist-bugs`), `core-physical-aspect` (issue and PR; `wp11-physical-aspect`) | |
| `qt-large-data-cancel`, `qt-aggregate-slice`, `astropy-19174` (comment) | |
| `core-profile-restore-priority` (issue and PR), `core-quantity-saver`, `core-derived-units`, `core-profile-unit-label` (optional), `core-datetime-export` | |
| `qt73-style-editor` (comment; `wp0-track-line-layers`) | |
| `irispy-wavecorr`, `irispy-moments-uncertainty`, `irispy-itn32` (`wp0-irispy-requests`); `irispy-mg-features`, `irispy-bursts` (`wp2-m3-mg-features`, `wp2-burst-detection`) | |
| One row per proposal (`wp0-optional-proposals`) | |

**M0**

- [ ] **M0** `wp0-workaround-register`: Apply D2 to every workaround (probes, not versions: PR-source installs report 1.27.0). Done when each workaround on main has a register row, a comment naming its probe (or why it is always on) and its fix (or 'none tracked' plus its signature test), and a test passing on the released baseline with the probe on, and off where a source export has the fix. Findings: archive-trace-7, wp1-links-8.
- [ ] **M0** `wp0-irispy-v34-flip`: irispy report and a standalone PR off irispy main porting the `gwcs_raster_clean` fix (not the branch, D14): for negative-step rasters (STEPS_AV < -0.01), 0.9.0 flips data and times but not mask, uncertainty or per-step meta. Done when the reproducer shows the mismatch on 0.9.0 with 20250328 OBSID 3400109360 and its row closes. Findings: followup-4-2.
- [ ] **M0** `wp0-irispy-crpix`: irispy report: SJI/AIA gWCS is one pixel off (dkist's `VaryingCelestialTransform` applies the 1-based CRPIX to 0-based pixels): 0.168″ full-resolution SJI, 0.47″ rolled binned SJI, 0.607″ AIA; SLTPX1IX shares the convention; report both. Not zero-valued aux pointing rows: 0.9.0 already fills them (irispy #169). Done when the reproducer compares the gWCS with astropy `WCS(header)` on 0.9.0 and its row closes. Findings: followup-4-3.
- [ ] **M0** `wp0-irispy-slit-units`: irispy report: SLTPX1IX/SLTPX2IX carry `u.arcsec` on pixel values; file it with `wp0-irispy-crpix` if the user agrees. Done when the reproducer prints the arcsec tag beside the pixel-range values on 0.9.0 and its row closes. Findings: wp4-quicklook-3.
- [ ] **M0** `wp0-irispy-tab-index`: irispy report and 2-line PR with test: the -TAB exposure index column (`PS3_2='RASTER'`) makes `pixel_to_world` O(exposure index), up to 0.36 s per synced slider step; the PR drops it from `_create_tabular_wcs`. Done when the reproducer shows the per-call cost growing with the exposure index on 0.9.0 and its row closes. Findings: followup-2-6.
- [ ] **M0** `wp0-core-image-artist-bugs`: Two glue-core 1.27.0 bugs, a PR for the first: (1) `ImageSubsetLayerArtist._update_visual_attributes` re-shows the hidden Pixel crosshair at (0, 0) on λ–t and spectrogram panels after `_update_data` hid it on `IncompatibleAttribute`; the PR re-shows it only when a position was found (or draws only the subset's own axis line); (2) `translate_pixel`'s bare `Exception` escapes `ImageLayerArtist`, so draws fail instead of showing 'Cannot visualize this layer' (propose `IncompatibleAttribute`). Done when both reproducers fail on released core and both rows close. Findings: followup-1-2.
- [ ] **M0** `wp0-qt-large-data-cancel`: glue-qt report: after Cancel on the Profile 'Add large data set?' modal, the closed viewer's `LayerArtistView` stays hub-subscribed, so every later `new_data_viewer` raises 'wrapped C/C++ object of type LayerArtistView has been deleted'. Done when a minimal script reproduces it on glue-qt 0.4.2 and main 9780eaf and its row closes. Findings: followup-2-5.
- [ ] **M0** `wp0-astropy-19174`: Track astropy#19174 and add the IRIS case (Profile worker and GUI-thread WCSAxes crash in wcslib `tabx2s` on a shared -TAB WCS). Done when the reproducer crashes without the lock in `iris-plan` and its row closes. Findings: followup-2-1, followup-3-1.
- [ ] **M0** `wp0-readme-runner`: In `IRIS_PLAN_PROTOTYPES/review_20260923/README.md`, replace the four `.venv/bin/python` runner lines and `/tmp/iris-plan-validation-*` roots with the `iris-plan` runner and this plan's Validation export-regeneration recipe. Done when that README has neither and no runner instruction outside `IRIS_PLAN_PROTOTYPES/archive/` uses `.venv`; the evidence in `review_20260927/` stays unchanged. Findings: followup-1-7, followup-3-9, followup-4-10.

**M1**

- [ ] **M1** `wp0-stack-validation`: Test the combined Current state heads (core #2601, #2595, #2597-#2599; Qt #70, #74, #75; #68 if wanted) after resolving the Notes conflicts: in `iris-plan` on regenerated exports, run the Qt common+profile suites, `glue_solar` (both sides of the `cursor_status` gate) and `IRIS_PLAN_PROTOTYPES/review_20260923/test_existing_workflows.py`. Done when heads, resolutions and pass counts are recorded and an IRIS-raster Slice profile with an out-of-range reference slice shows 'Incompatible data' (core ca9eb3db). Findings: plan-integrity-3, plan-integrity-14, upstream-state-9, solar-main-8. Depends: wp0-readme-runner.
- [ ] **M1** `wp0-user-review`: The user reviews each of their drafts (core #2595-#2599, #2601; Qt #70, #74, #75) before it is marked ready. Done when each is merged, closed or parked by the user. Depends: wp0-stack-validation.
- [ ] **M1** `wp0-release-tracking`: Date each glue-core, glue-qt, irispy-lmsal or astropy release after the 2026-09-27 baseline (1.27.0, 0.4.2, 0.9.0). A fix counts only if its merge commit is reachable from the tag; then raise the floor, retire register rows, close report rows and switch on gated M1 work (#2595: WP1 SJI↔raster pixel paths; #2596/#2601 + Qt #70: WP4/WP5 Slice profiles; #2599: WP7 date labels). Record the release containing glue #2128 (hidden axes); `wp12-sequence-export` then drops its `ax.set_axis_off()` fallback. Done when each such release has a line naming its PRs, floors and rows.
- [ ] **M1** `wp0-own-draft-updates`: Amend the user's drafts: (1) #2595's `wcs_autolink` leaves time axes out between datasets, so WP4's matching owns time (confirmed; today frame 0 maps to NaN and a Pixel point on SJI 1400 misses SJI 2796); (2) Qt #74's `cursor_status` labels Solar X/Solar Y, longitude first, at zoom-independent sub-arcsec precision, and shows pixel and world positions together (if #74 keeps them apart, record that the pixel view then falls back to WCSAxes' 'w' toggle). Done when each amended head, as a source root, passes its suite and the owning WP's test (WP1: SJI/SJI Pixel propagation, run from the amended #2595 head as a source root; WP11: raster-map readout). Check (c) of `wp1-m1-autolink-matrix` is written here and run on the amended #2595 source export before any #2595 release; this item does not wait for that release. Findings: core-qt-capabilities-1, followup-3-10. Depends: wp1-m0-link-graph-regression, wp11-cursor-readout.
- [ ] **M1** `wp0-core-profile-restore-priority`: `ProfileViewerState._update_priority` ranks `x_att` and `x_display_unit` equally (glue/viewers/profile/state.py:333-341@v1.27.0; unchanged in #2601), so restoring any IRIS spectrum panel raises ValueError ('value Angstrom is not in valid choices'). File a core issue and one-line PR ranking `*_display_unit` lower; until released, `setup()` ranks it 0.5 (after `x_att` 1, before limits 0), idempotent, its probe in try/except (register row). Done when, on 1.27.0, a GlueApplication save/restore of synthetic 3-D Data with an astropy spectral WCS (wavelength last numpy axis; Profile `x_att` on it, Angstrom and nm) restores `x_att`, unit and limits with the wrapper and raises the ValueError without it, and the row has the PR URL. The IRIS-raster case (Angstrom, nm; km/s once the `wp5-m1-velocity-axis` probe passes, i.e. glue-qt with #70) belongs to `wp3-app-session-acceptance`. Findings: wp3-wp5-2.
- [ ] **M1** `wp0-core-quantity-saver`: Core PR beside #2597 with a `@saver(u.Quantity)`/`@loader(u.Quantity)` pair (D13) ported from `IRIS_PLAN_PROTOTYPES/wp3_impl.py` as a plain saver (re-registering raises KeyError), writing WP3's fallback record (saved type, protocol version 1, `{"value", "unit"}`). Done when its core session test round-trips a scalar and an array Quantity in `Data.meta`, a session saved by the solar fallback loads with the core loader, and the row has the PR URL. Findings: wp3-wp5-5, usefulness-8.
- [ ] **M1** `wp0-core-derived-units`: Core PR saving `DerivedComponent.units`, still loading records without it (register row until released). Done when the PR's core session test round-trips a `DerivedComponent` with `units='DN/s'` and its row closes. Findings: wp2-wp6-science-9.
- [ ] **M1** `wp0-core-profile-unit-label`: Optional (WP5's upstream route): port `IRIS_PLAN_PROTOTYPES/wp5_label.py` (display unit in the Profile x label) as a core PR, not a glue-solar patch (D2). Done when the PR's test shows a velocity profile labelled in km/s in both the numeric and the WCSAxes path. Findings: archive-trace-8.
- [ ] **M1** `wp0-irispy-requests`: File the irispy requests other WPs cite: (1) per-exposure wavelength-drift correction like `iris_prep_wavecorr_l2`, for `wp5-m3-rest-from-measurement` (until then `LEVEL2_CAVEAT` in `wp5-m1-rest-wavelength-policy` states the limit); (2) uncertainty propagation in `calculate_moments`, for `wp2-m3-window-data`; (3) Hinode/SOT SJI-format (ITN32) cubes, for `wp4-context-reference`. Done when each request's row is closed. Findings: wp3-wp5-10.
- [ ] **M1** `wp0-track-line-layers`: Track draft glue #2603 and glue-qt #73. WP5 keeps its `layer_artist_maker` line-list artist (D2); the stock Profile style editor already covers line-list and later layers (`wp5-m1-line-list` probe, 2026-09-27), so the prototype's rewrite is not ported. Comment on Qt #73 that its exact-class editor lookup misses `QThreadedProfileLayerArtist`. Done when the comment is posted or declined (recorded) and the register row names both PRs. Findings: upstream-state-6, core-qt-capabilities-4.
- [ ] **M1** `wp0-irispy-gwcs-branch`: Track the user's `gwcs_raster_clean` branch only (D14): with it the loader makes 1496 2-D datasets per raster file, loses wavelength and fails with `stack=True`; do not propose or merge it until glue-solar's loader accepts both APIs (M0 and M1 stay on irispy 0.9.0). Its `_RasterSequenceCelestialTransform` and inverse lack ASDF converters and glue saves `data.coords` even for LoadLog data (`_save_data`@1.27.0), so combined multi-file raster sessions fail until irispy ships converters or a `_GlueWCS` record re-derives the WCS from the files (WP3 Notes). Ask irispy for converters first (`irispy-asdf-converters`). Done when its fate is recorded; a proposal also needs a passing `glue_solar` run on it and a WP3 multi-file raster session round-trip with converters. Findings: upstream-state-1, upstream-state-2, wp3-wp5-18.
- [ ] **M1** `wp0-qt68-macos-pass`: Manual macOS pass for Qt #68 (scratch HOME, isolated QSettings): first the saved font override (an old 9-point value hides the new default); then menu title, About/Hide/Quit, Cmd-Tab and Dock name, and clipping at native font sizes (preferences, link editor, importers, fixed-geometry dialogs), on PyQt6/Retina and PyQt5. Keep the slice label's 0.75x scale unless unreadable. Done when each item's result per binding is recorded here. Features: F203. Findings: archive-trace-15.
- [ ] **M1** `wp0-qt-aggregate-slice`: glue-qt report and PR: `MultiSliceWidgetHelper.sync_state_from_sliders` (glue_qt/viewers/common/slice_widget.py:54) rebuilds every slice from `slice_center`, so any slider move turns a Profile Collapse `AggregateSlice` into an int; keep it on unmoved axes (register row until released). Done when a 0.4.2 reproducer (Profile Collapse, then one scan-slider step on a 4D stack map) shows the loss and its row closes.

**M2**

- [ ] **M2** `wp0-track-2604`: Track glue #2604 (regions on WCS images; fixes #2600); WP7 keeps its pixel `PolygonalROI` FOV subset until a core release has it, then reconsiders a `RegionData` footprint. Done when that release's tracking line names #2604 and WP7's decision is recorded. Findings: upstream-state-7.
- [ ] **M2** `wp0-track-qt66`: Track draft glue-qt #66 (astrofrog, idle since 2026-05-27), a generic `path_slicer` on core `PathSlicedData`; WP12 builds on core `BasePathSlicerMode` and #66 or its successor, never on the `PVSliceWidget` that #66 deletes. Done when #66 is merged before WP12 starts, or the user has asked its author about it first. Findings: upstream-state-8, core-qt-capabilities-3.
- [ ] **M2** `wp0-core-datetime-export`: For `wp12-derived-data-export`, report that core's HDF5, FITS-table and VOTable exporters fail on datetime64 components such as every IRIS `Time` ('No conversion path for dtype <M8[ns]'). Done when a 1.27.0 reproducer exporting an SJI with its `Time` fails in each format and its row closes. Findings: followup-3-8.

**M3**

- [ ] **M3** `wp0-qt68-cocoa`: Once a glue-qt release has #68, check that conda-forge's glue-qt depends on `pyobjc-framework-cocoa` on macOS; if not, request it. Done when the recipe check and any request URL are recorded here.
- [ ] **M3** `wp0-optional-proposals`: None blocks a milestone.
  - glue-core: `coerce_numeric` keeping bool as uint8 (WP10); 99.9/99.8/99.98 percentiles (WP11); a `_load_cmap` fallback to glue's colormap registry (WP3); gWCS axis names not title-cased to 'Time (Utc)' (WP9); image interpolation (WP11); once working in glue-solar, the `PathSlicedData` saver, 4D path-slicer gate, per-axis parent driving and nearest/linear sampling (WP12).
  - glue-qt: a gamma slider on `stretch_parameters` (WP11); playback below 2 fps, bounce (ping-pong) playback and a frame sub-range in the stock slice widget (glue-solar: `wp4-playback-extras`, `wp4-time-controls`; wp3-wp5-13); modifier-aware `keyboard_shortcut` dispatch (WP11); Tab/Backspace registered for `TableViewer`, not `DataTableModel` (keyboard_shortcuts.py:32-52@0.4.2; WP9 `wp9-m0-viewer-tools-docs`, `wp9-m1-release-updates`).
  - irispy (WP10 unless noted): NaN-filled float raster data, as for SJIs; `memmap=True` returning scaled, masked data; a `read_files` exposure-range argument; a (position, exposure) reshape for NEXP_PRP > 1 rasters (`wp1-nexp-prp`).
  - astropy: reusing a fitter after `parallel_fit_dask(fit_info=...)` raises `KeyError: '__deepcopy__'` (8.0.1; WP6 uses a fresh fitter per call).

  Done when each is filed or declined and recorded in the reports table. Findings: followup-2-2, usefulness-12, archive-trace-8, followup-3-4, followup-3-12, followup-3-16.

Notes and limits:

- Merge state (2026-09-26/27): core pairs merge cleanly; Qt #70/#75 conflict only add/add in `glue_qt/viewers/common/tests/test_multi_slice_helper.py` (keep both tests, rebase the later PR); #69 conflicts with #68 and #70 in `glue_qt/app/tests/test_plugin_manager.py`; native interactive behaviour is untested.
- PR boundaries (the user's decision; CI repair out of scope): Qt #68/#70 carry only reworded cherry-picks of #69's plugin-test fix (89773fd1, 5c5b08a1), not its CI/viewer cleanup (5e1f0ee7) or `_version` ignore rule; #74/#75 lack #69; #69 overlaps glue-qt #65 (maintainer; upstream-state-10). Qt #70's `profile_tools.py` nearest-index/display-unit correction is independent of its WCSAxes wiring. If a maintainer asks, the user may split it into its own PR (optional; not an instruction to rewrite #70). The km/s x-unit gate row then retires with that PR.
- Qt #75 labels only WCS time axes, not the standalone `Time` of raster exposure and stack axes; no WP relies on it.
- Profile contract for #2601 and Qt #70: numeric and unit-overridden profiles stay out of WCSAxes mode; slice translation and `x_limits_pixel` session state stay.
- A `clone(link)` of a low-level-WCS link is not session-safe; WP3 covers only the IRIS representation.
- Deferred beyond #68 (separate requests or PRs): native Preferences/About menu roles, `QFileOpenEvent`, Dock completion feedback, macOS dark mode, pinch zoom; a notarized `.app` bundle with file associations is a separate distribution project.
- Line-marker tests in numeric and WCSAxes profile modes (changed slices, descending grids, session restore) are owned by `wp5-m1-line-list` and run on #2601 + Qt #70 in `wp0-stack-validation`.

### WP1: Coordinates, units and links

WP1 owns the coordinate contract (D3) and link graph (D1) for IRIS data and glue-solar's maps. Port per the prototype table; tests run in both `wp1-m0-irispy-baseline` envs; each PR carries a changelog fragment and its WP9 guide change.

**M0**

- [ ] **M0** `wp1-m0-irispy-baseline`: Beside `iris-plan`, create the micromamba floor env `iris-plan-floor` (irispy-lmsal 0.8.1 at its declared floors astropy 7.2.x and ndcube 2.4.0, plus glue-core 1.27.0 and glue-qt 0.4.2) and record it in Validation. The existing `iris-plan-irispy081` (irispy 0.8.1 with iris-plan's astropy 8.0.1 and ndcube 2.4.2) only reproduces prototype results; it is not the floor. The first port PR raises the `pyproject.toml` glue floors to match (confirmed); irispy stays >=0.8.1. Fixtures via `find_irispy_test_file` (real names, `sns` filter). Re-run the WP2, WP5 and WP6 prototype checks on 0.9.0 (WP2/WP6 gave 3 failed, 11 passed, 3 errors; wp2-wp6-science-17), including the no-TWAVE path (`SGMeta.rest_wavelength` None). Done when the plan records both envs, test counts, WP2/WP5/WP6 results and the floor decision, main's suite passes in both, and scalar and array inputs to both `_GlueWCS` value methods give identical results in both envs. Features: none. Findings: upstream-state-3, wp1-links-4, wp1-links-5, wp2-wp6-science-17.
- [ ] **M0** `wp1-m0-axis-names`: M0 part of F024: `_AXIS_NAMES` beats gWCS names, so SJI, raster, stack and AIA-cutout axes share 'Helioprojective Longitude/Latitude' and 'Wavelength'; drop `"time": "Time"` so SJI world time stays 'Time (Utc)'. Match physical types, never labels. Done when `test_sji_and_raster_share_axis_names` and the SJI high-level round trip pass, an SJI has one `Time` component (`data.id['Time']`), and the ported SJI label hunk expects 'Helioprojective Longitude'. Features: none. Findings: archive-trace-10. Depends: wp1-m0-irispy-baseline.
- [ ] **M0** `wp1-m0-inverse-workaround`: Port the process-wide patch module `glue_solar/glue_patches.py` (also home of WP7's gated datetime port `wp7-goes-date-labels`), imported from `glue_solar/__init__.py`. Its #2598 fix of `world2pixel_single_axis` (exposure-0 inverse) installs only when `needs_inverse_workaround()` finds the bug, with a `wp0-workaround-register` row; no all-ones `axis_correlation_matrix`. Done when the probe patches 1.27.0, `test_world_links_into_the_sji_use_each_exposure_time` recovers every frame's pixel to 1e-6 px, with #2598 in core the probe is False and glue untouched, and WCSAxes readouts are unchanged. Features: none. Findings: wp1-links-8, archive-trace-7. Depends: wp0-workaround-register.
- [ ] **M0** `wp1-m0-sji-crpix`: A probe-gated `_GlueWCS` pixel shift for SJI and AIA-cutout gWCSs, whose 1-based CRPIX irispy 0.9.0 applies to 0-based pixels, with a removal note naming `wp0-irispy-crpix` and a `wp0-workaround-register` row. `wp4-slit-point-overlay` (owner of the joint SLTPX1IX/CRPIX test) and `wp4-sji-panels` (FOV label) depend on this item. Done when, at frames 0, N//2 and N−1, corners and centre of 4000255147 SJI 1400, 3860608353 SJI 2832 (SAT_ROT 45°), deconvolved 4000005156 SJI 2796 and a 3640107442 AIA cutout match an astropy WCS from CRPIX, CDELT, XCENIX/YCENIX and PCi_jIX to 0.05 px, and the shift stays off without an offset. Features: none. Findings: followup-4-3. Depends: wp0-workaround-register.
- [ ] **M0** `wp1-m0-link-hpc`: Port `link_hpc(data_collection)` to `glue_solar/sources/loaders/iris.py` (D1): `LinkSame` between `_GlueWCS` helioprojective lon/lat world components by physical type, skipping linked pairs, called by `browse_iris` and a menubar action 'IRIS: link helioprojective coordinates'. No two-argument helper or degree↔arcsec link. Done when, without time links: (1) a second call adds 0 links; browser and menu both add them; (2) 4000005156 Si IV + SJI 2796: at frames 0 and N−1 a raster-map ROI selects exactly the SJI pixels whose per-frame header-WCS position is in its world footprint (0.05 px edge band exempt); (3) sns fixture and 4000255147 Si IV + SJI 1400: the selected SJI column moves ΔXCENIX/CDELT1 ± 1 px from frame 0 to N−1 (about 78 px on 4000255147), xfail until (4); (4) diagnose the released-core sit-and-stare full-width stripe (37/37 columns); if inherent, the guide records it and (3) stays xfail; (5) lon/lat world subsets propagate both ways; SJI pixel subsets stay IncompatibleAttribute on the raster (M1 routes SJI clicks through `wp1-m1-sji-to-raster`); (6) no link targets SJI world time. Release gate: `browse_iris` installs `link_hpc` by default only in a release that also carries `wp10-m0-roi-guard` and `wp10-m0-acceptance` (both depend on this item). Features: F050. Findings: wp1-links-2, wp1-links-3, followup-1-4, followup-1-5, wp4-quicklook-12, followup-4-4. Depends: wp1-m0-inverse-workaround, wp1-m0-sji-crpix.
- [ ] **M0** `wp1-m0-descending-step-orientation`: A real-data STEPS_AV < 0 regression in `glue_solar/tests/test_importer.py`, not a `flip_x` flag (D10). Done when, on 3400109360 (STEPS_AV −0.998, CDELT3 −0.998), the per-scan Si IV 1403 map with `flip_x` False has longitude increasing with displayed x; step 0 is at −971.0″ and step 63 at −908.2″ in WCS and cursor readout; a 2-scan stack keeps that orientation; `Time` descends from 23:06:15 (step 0) to 22:56:32 (step 63). Features: F053.
- [ ] **M0** `wp1-m0-link-graph-regression`: In `glue_solar/tests/test_linking.py`, open 4000005156 Si IV + SJI 2796 via `browse_iris` with the real autolinker (mocked dialog), `link_hpc` and WP4's link-free coordinator. A `wcs_autolink` behaviour probe picks the expectation: False (1.27.0), only `link_hpc` links and (b) = the `wp1-m0-link-hpc` (2) footprint; True (#2595), SJI/raster `WCSLink`s too and (b) = the frame-0 footprint in every SJI frame, world subsets still per-frame. No link maps a main or world component into a pixel component ID (D8) or targets SJI world time. Checks: (a) a raster Pixel point gives the native marker and spectrum in the other windows; (b) the raster-map ROI's SJI selection; (c) time sync leaves `len(dc.links)` and every component list unchanged, and the coordinator's SJI-frame→raster-step and raster-step→SJI-frame indices equal the `nearest()` array reference with 0 mismatches; (d) lon/lat world subsets propagate; (e) the SJI layer draws in the raster viewer and vice versa without exception, and a layer with no pixel path shows glue's incompatible state. A CI variant runs on the irispy 20210905 3620258102 `sns` SJI 1400 + Si IV 1403 fixture pair in both `wp1-m0-irispy-baseline` envs, ported from `IRIS_PLAN_PROTOTYPES/review_20260927/probes/linkgraph/test_linkgraph.py` (its order/allocation matrix only, not the pixel-ID time-link design): checks (a) and (c)-(e) and the add-order and minimum-hop equality apply there; (b) there follows `wp1-m0-link-hpc` check (3)/(4), and the (2)-footprint form of (b) runs on local data only. Done when all checks agree over every add order and perturbed-allocation reruns, and all minimum-hop paths to each target component ID agree. Extended, under the same bans and each re-running this test, by `wp4-m1-multi-window` (window pixel links), `wp7-goes-context` (GOES `time`↔IRIS `Time` LinkSame), `wp12-point-light-curves` (curve `Time`/value LinkSame) and `wp12-path-slicer` (PathSlicedData pixel links). Features: none. Findings: plan-integrity-6, followup-1-6, followup-1-3. Depends: wp1-m0-link-hpc, wp4-time-sync.

**M1**

- [ ] **M1** `wp1-m1-wrapper-coherence`: Angstrom and arcsec across `world_axis_units`, both value methods, `world_axis_object_components` (callable or string getters), `world_axis_object_classes` (3- or 4-tuples in astropy's argument order, tested with positional args), compound stacks, sliced maps and bare-array 1-D WCSs. Keep the `wp10-m0-wcs-lock` lock. Land before `wp3-app-session-acceptance`. F058 = the 'w' readout toggle plus Profile pixel/world x (no pixel-tick toggle). Done when, on 3610108077, the Image wavelength slider, cursor readout and Profile x show Å (|Δ| ≤ 1e-6 Å against irispy; nm and m still offered); HPLN/HPLT stay arcsec with identical labels on the SJI, raster (including 4000255147 sit-and-stare), 4D stack and a sliced map; pixel→world→pixel agrees to 1e-9 px through both APIs; the ported stack-unit hunks and the `wp10-m0-wcs-lock` thread test pass; scalar and array inputs to both value methods and the high-level API give identical results in both `wp1-m0-irispy-baseline` envs. Features: F024, F058. Findings: followup-2-1, wp1-links-7, wp1-links-5, wp1-links-6. Depends: wp1-m0-axis-names, wp10-m0-wcs-lock.
- [ ] **M1** `wp1-m1-sunpy-maps`: Wrap map WCSs in `_GlueWCS` in `_parse_sunpy_map` (`glue_solar/sources/maps.py`) and `load_sunpy_map` (`glue_solar/sources/loaders/maps.py`) (D3); the 'sunpy Map' factory gets a 2-D-helioprojective identifier and priority 150, between glue's FITS reader (100) and IRIS (200) (confirmed). Done when a 2-D `make_fitswcs_header` AIA-style map FITS shows 'Helioprojective Longitude/Latitude' in arcsec via File → Open and the map importer; with `link_hpc`, `sji[map.pixel_component_ids]` at SJI frames 0 and N−1 equals the map-pixel projection of the SJI header WCS to 0.05 px, and a map ROI selects the SJI pixels whose header-WCS position is inside it; a non-map FITS table still opens with glue's reader; the map round-trips through a session; `test_link_hpc_leaves_datasets_in_other_units_alone` uses a non-`_GlueWCS` degree WCS. Features: none. Findings: wp1-links-6, archive-trace-17. Depends: wp1-m1-wrapper-coherence, wp1-m0-link-hpc, wp3-wcs-saver (session check).
- [ ] **M1** `wp1-m1-autolink-matrix`: When a `wcs_autolink` behaviour probe finds #2595, apply every stock suggestion under the adopted SJI/raster and SJI/SJI policies (confirmed). Extend `wp1-m0-link-graph-regression` (both-way ROI propagation, not link counts) with 4000005156 Si IV/SJI 2796, 4000255147 raster/SJI 1400, two 4000005156 scans, 3602506433 stack/scan, raster/sliced map, map/map, fixture SJI 1400/2796, and rolled 3860608353 SJI 2832, 4000255147 raster and SJI 1400 and a 3640107442 AIA cutout, each against a covering `make_fitswcs_header` map. Done when: (a) an SJI Pixel point gives the raster marker and spectrum; (b) scanning: a raster ROI selects the frame-0 WCSLink footprint in every SJI frame (documented); sit-and-stare: the 0 px result is diagnosed, or pixel-ROI reach is declared unsupported (use `link_hpc`); (c) an SJI/SJI Pixel point propagates with no time-axis link; (d) WCSLinks leave `link_hpc` subsets unchanged; (e) results are identical over add orders and perturbed allocation; the rolled SJI readout matches the header WCS to 0.05 px and, on the map reference, its layer lands at its frame-0 header-WCS corners within 1 map px; each map row gives every IRIS dataset one WCSLink to the map, matching the header-WCS projection to 0.05 px (SJI frame 0); gated tests skip cleanly on 1.27.0. Check (c) is xfail until `wp0-own-draft-updates` amends #2595, and once this item runs, `wp4-m1-multi-window`'s window links join row (e). Both extend this item's probe-gated tests, run against the #2595 source export; neither `wp4-m1-multi-window` nor `wp0-own-draft-updates` depends on this item or waits for its release gate. Features: F049, F054. Findings: core-qt-capabilities-1, wp1-links-1, followup-4-7, wp4-quicklook-12, followup-1-6, followup-1-3. Depends: core #2595 release, wp1-m1-wrapper-coherence, wp1-m1-sunpy-maps, wp1-m0-link-graph-regression.
- [ ] **M1** `wp1-m1-sji-to-raster`: `sji_to_raster()` in `glue_solar/sources/loaders/iris.py`: SJI pixel → world at the displayed frame; step by WCS (scanning) or nearest `Time` (sit-and-stare); slit row by WCS. `wp4-sji-click-to-raster` wires it into the coordinator and owns click handling (re-entrancy guard, subset replacement, undo, 'outside raster FOV' label). Done when, with `wp1-m0-sji-crpix` active, (step 32, slit 385) projected into 4000005156 SJI 2796 frame 7 and passed to `sji_to_raster()` returns (32, 385) within 0.5 px; slit 208 projected into 4000255147 SJI 1400 frames 0, 200 and 399 returns slit 208 within 0.5 px and exposures 1, 801 and 1597; no test pins an SJI pixel value; a point outside the raster FOV (frame 15, raster edge) returns no raster index; with #2595, frame N−1 returns the per-frame index, not the frame-0 WCSLink's. Features: none. Findings: usefulness-2. Depends: wp1-m0-sji-crpix.
- [ ] **M1** `wp1-dn-per-s`: `_cube_data` adds '<label> DN/s', a `DerivedComponent` (`units='DN/s'`) whose `ParsedComponentLink` divides flux by `Exposure time` under `np.where(... > 0, ..., np.nan)`. While a probe finds released core drops `units` from sessions, it is a `DerivedComponent` subclass in `glue_solar/sources/loaders/iris.py` whose `__gluestate__`/`__setgluestate__` save `units` (`wp0-workaround-register` row, retired by `wp0-core-derived-units`; kept importable for saved sessions). Done when on 3610108077 Si IV it equals flux / 7.999 s at normal steps and NaN at the 0-s step 157; a synthetic unmasked raster with a 0-s exposure gives NaN, not ±inf; on 4000255147 SJI 1400 it equals flux / EXPTIMES per frame; Profile y and the Image layer's `attribute_display_unit` show 'DN/s'; a saved session keeps the expression and the unit. Features: F165. Findings: wp2-wp6-science-9. Depends: wp4-exposure-readout, wp10-fill-nan, wp3-app-session-acceptance (session check).

**M3**

- [ ] **M3** `wp1-stack-per-scan-wcs`: Per-scan 4D-stack spatial coordinates with an inverse (Scan slider = CRISPEX 'File no.'): irispy's per-scan WCS if released (track `wp0-irispy-gwcs-branch`, D14), else invert the forward table model of `IRIS_PLAN_PROTOTYPES/archive/probes-2026-09/cc_stackwcs.py`. Done when, on one window of the 8-scan 3400109360 and 99-scan 3602506433 stacks, scan-k pixel→world equals the scan-k file's WCS to 1e-6″ and world→pixel round-trips to 1e-6 px, within memory for one 99-scan window; on the 4000005156 2-scan stack, a lon/lat subset made on SJI 2796 selects the per-scan dataset's scan-k pixels; the per-scan WCS uses an existing `wp3-wcs-saver` record kind or extends `__gluestate__`/`__setgluestate__`, and a round-trip case in `glue_solar/tests/test_sessions.py` passes. Features: F115. Findings: followup-2-2. Depends: wp1-m0-link-hpc, wp3-wcs-saver.
- [ ] **M3** `wp1-nexp-prp`: NEXP_PRP > 1 scanning rasters repeat positions, so world→pixel returns each first exposure: warn once (not for sit-and-stare) and document it; `wp0-optional-proposals` holds the reshape request. Done when a synthetic NEXP_PRP=2 raster warns once and world→pixel returns steps 0, 2, …, 14; a spatial ROI from a linked grid selects both exposures of every position; 4000255147 (NEXP_PRP 1600) and the 20210905 sns fixture give no warning. Features: F116. Findings: followup-4-9.
- [ ] **M3** `wp1-m3-pointing-offset`: Optional `_GlueWCS` (dx, dy) arcsec offset in both directions, set by a 'Shift pointing…' `layer_action` (CRISPEX OFFSET_SJI) and saved by `wp3-wcs-saver`, plus a WP9 recipe checking FUV/NUV/SJI co-alignment on the slit fiducials with slit-axis Profiles. Done when (+2″, −1″) on 4000005156 SJI 2796 shifts its readout by exactly that and a raster ROI's SJI footprint by dx/CDELT px; (0, 0) restores it; it survives a session round trip (a `test_sessions.py` case); the recipe finds the fiducials in the Si IV 1403 and Mg II k 2796 spectrograms and SJI 2796 of 4000005156. Features: F051, F052. Depends: wp1-m0-link-hpc, wp3-wcs-saver.
- [ ] **M3** `wp1-m3-multi-instrument`: Record a co-aligned IRIS–SST Level-3 pair from Rouppe van der Voort et al. (2020, A&A 641, A146) (date, IRIS OBSID, SST target and instrument), open it through the Level-3 input and link it by stock WCS autolinking, or by identity pixel links without an accepted celestial WCS. Done when the pair opens and a Pixel point on the SST cube gives the linked IRIS spectrum at the same position. Features: F055. Depends: wp8-m3-level3-input.

**Notes and limits**

- Until `wp10-m1-roi-world-polygon`, the guide documents the stock raster-ROI freeze (about 10 s per SJI frame) in browser-opened viewers (followup-4-4; confirmed 2026-09-27).
- Not planned: a differential-rotation `@link_helper`.

### WP2: Line moments and diagnostics

WP2 turns IRIS spectra into derived maps: D4 `layer_action`s that rewrap the Data as an irispy cube, keep the numerics in irispy (except the continuum mean and the saturation guard), add one linked Data and open no viewer. Files: `glue_solar/sources/moments.py` (new, imported from `glue_solar.setup()`), `glue_solar/tests/test_moments.py`, a `docs/user_guide/` page, `changelog/`. No new required dependency; no M0 or M1 work.

**Port from prototypes**

- `IRIS_PLAN_PROTOTYPES/chk_wp2/wp2_moments_module.py` → `glue_solar/sources/moments.py`: `line_moments`, `_in_angstrom`, `_number`, `MomentsDialog`, `moments_action`, keeping the DN·Å threshold and the `Time` copy. The M2 items below fix its defects (their Findings and Depends lines name them).
- `IRIS_PLAN_PROTOTYPES/chk_wp2/test_wp2_moments.py` → `glue_solar/tests/test_moments.py`: all five tests, with fixtures via `find_irispy_test_file` (wp2-wp6-science-17), the step from the WCS and expectations moved to the new rest policy; plus two checks from the archive-verdict `IRIS_PLAN_PROTOTYPES/wp2_moments_proto.py` (:139-166; move it to `IRIS_PLAN_PROTOTYPES/archive/probes-2026-09/` once they are ported): no policy rest gives no TWAVE velocities, and `_can_trigger` rejects subsets.

**M2**

- [ ] **M2** `wp2-m2-moment-maps`: Port 'IRIS: line moments…' (data only, single selection). A rewrap helper builds a `SpectrogramCube` from a per-scan raster (component, mask, unit and a `copy.deepcopy` of the raw WCS taken under `wp10-m0-wcs-lock`) and calls `calculate_moments` with an explicit centre (irispy 0.9.0 falls back to TWAVE when rest is None, utils/moments.py:100-101); SJIs and 4D stacks are refused with a message. The added Data has:
  - `intensity`, uint8 `mask` (D12), `centroid` and `sigma` (Å), `velocity` and `sigma_velocity` (km/s) and the source `Time` at wavelength index 0, all NaN and masked where the wings hold no valid sample (irispy gives 0);
  - coords `_GlueWCS(SlicedLowLevelWCS(wcs_copy, (slice(None), slice(None), 0)))`;
  - plain-dict meta: `moments_centre` (float, Å); when a rest applies, `rest_wavelength` (float, Å) and `rest_wavelength_source`; and `velocity_caveat`, a copy of WP5's `LEVEL2_CAVEAT`;
  - exactly two `LinkSame` links between the spatial pixel components.

  The Data, `Time`, meta and links are added through WP5's derived-product helper (`wp5-m1-doppler-image`), which opens no viewer. Windows above about 5e7 elements run in a `glue_qt.utils.threading.Worker`; the Data and links are added on the main thread. Done when:
  - on 4000005156 Si IV scan 0, exactly one such Data with two links is added and no viewer opens;
  - the meta holds `moments_centre` and `velocity_caveat` equal to `LEVEL2_CAVEAT`, plus `rest_wavelength` and `rest_wavelength_source` only when a rest applies;
  - on 4000005156 C II scan 0, intensity is NaN, not 0, where spectra are -200 across the wings;
  - a WP3 session holding the map reopens with equal world coordinates;
  - SJI, stack and failing inputs add nothing, and the dialog stays open after an error;
  - on 20130902 4000255147 Si IV, the GUI thread blocks ≤ 0.5 s (2.2 s today) and peak RSS grows ≤ 3× the float32 window bytes.

  Features: F153. Findings: wp2-wp6-science-10, wp2-wp6-science-13, wp2-wp6-science-16, wp3-wp5-3, followup-2-7. Depends: wp10-fill-nan, wp10-mask-uint8, wp10-m0-negative-step (followup-4-2, D10), wp10-m0-wcs-lock (followup-2-1), wp3-wcs-saver, wp3-plain-meta, wp5-m1-rest-wavelength-policy, wp5-m1-doppler-image.
- [ ] **M2** `wp2-m2-line-definition`: Take the line from WP5's rest helper and in-window candidate list (D11), never TWAVE. The dialog prefills the dataset's rest; with no rest key it asks, pre-selecting the first `default_for` candidate. Confirming a listed line stores it on the source as WP5's 'Set rest wavelength…' does ('user choice'), and the helper copies it to the products. Multi-candidate windows (Mg II k 2796 with h, C II 1336) load with no `rest_wavelength` (D11). The centre and wing fields are a reusable widget, also used as `wp6-m2-fit-maps`'s fit window.
  - Wings are required (default ±0.5 Å); a blank wing or centre adds nothing and keeps the dialog open.
  - Continuum windows (no packaged line inside the window): the centre only places the wings, velocity components are omitted, and the dialog says why (D11: no km/s for continuum windows).
  - An optional continuum window's per-pixel mean is subtracted first and published as `continuum` (iris_xmap's I(cont)).
  - Mg II h/k and C II windows (by `meta['spectral_window']`) get meta `line_regime = 'optically thick: centroid/width are proxies, not line-of-sight velocity'` and a dialog warning.
  - The last centre, wings and continuum range per window (Å) persist as a plain dict `meta['moments_last']` on the source.

  Done when:
  - on ~/DATA/IRIS 20180102 3610108077 Mg II k, the dialog asks for the line, pre-selecting 2796.352 Å (never TWAVE 2796.20) with wings ±0.5 Å, and the median velocity has |v| < 5 km/s;
  - C II 1336 asks for 1334.53 or 1335.71 Å, pre-selecting neither;
  - the 2832 continuum window publishes no velocity components and no `rest_wavelength`;
  - a blank wing or centre adds nothing;
  - `continuum` and the continuum-subtracted intensity equal a numpy reference;
  - after the user confirms Mg II k, the source and products carry `rest_wavelength` 2796.352 and `rest_wavelength_source` 'user choice', and the products `line_regime`;
  - after a WP3 save and reopen, the dialog opens with the last definition.

  Features: F154, F155. Findings: wp2-wp6-science-1, wp2-wp6-science-2, wp2-wp6-science-6, wp3-wp5-1. Depends: wp5-m1-rest-wavelength-policy, wp3-plain-meta, wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-input-quality`: The input is the flux or WP1's '<flux> DN/s' (the default when present); the minimum intensity is in that unit (times Å when integrating). NaN and -Inf samples are masked. Saturation is tested in DN on the raw flux inside the wings, because irispy zeroes non-finite samples first (utils/moments.py:131-132 vs :173@0.9.0): any +Inf sample (the ITN 26 flag) or a peak above the limit makes the pixel NaN in every product and masked. The dialog warns when any NSATPIX/TSATPXn header count is above 0. The saturation test and this warning are one helper, reused by `wp6-m2-quality-filter`. Done when:
  - on 3610108077 Si IV, at non-zero-exposure steps with no minimum-intensity threshold, DN/s intensity equals DN intensity divided by the exposure time;
  - a synthetic spectrum with one +Inf sample is NaN in all products and masked, and one with a -Inf sample matches the result with that sample masked;
  - a DN limit flags the same pixels for DN and DN/s input;
  - a header with TSATPX1 > 0 shows the warning.

  Features: none (F165 is `wp1-dn-per-s`; F170 is `wp9-m3-saturation-recipe`). Findings: wp2-wp6-science-8, wp2-wp6-science-9. Depends: wp1-dn-per-s, wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-tests-docs`: irispy fixtures (via `find_irispy_test_file`; the 0.9.0 ones are decimated 10×, Mg II 0.2546 Å/px, so ±0.5 Å holds about 4 samples) test only shapes, units, masks and plumbing, plus: a continuum window gives no velocity, a blank centre or invalid input adds nothing, spatial subsets propagate both ways, and the WP3 round trip holds. Numbers are tested on a synthetic `SpectrogramCube` (Gaussian plus noise, masked samples, one +Inf, one -Inf) against the truth, and on local 3400109360 (negative step; skipped when absent) against a numpy reference. Add a user-guide page, API entry and changelog fragment covering product choice, FWHM ≈ 2.355 σ (also in the component descriptions), sigma inflation for faint lines from irispy zeroing bad samples and the minimum-intensity threshold that limits it, thin lines (Si IV, O IV, Fe XII, Fe XXI, O I) versus thick ones (WP5 Doppler image, `wp2-m3-mg-features`), and Profile Collapse. Done when `test_moments.py` passes on iris-plan (irispy 0.9.0, glue-core 1.27.0, glue-qt 0.4.2) and Sphinx builds with `-W`. Features: none (acceptance for F153-F155; F156 already works). Findings: wp2-wp6-science-14, wp2-wp6-science-17, wp2-wp6-science-6, core-qt-capabilities-6, followup-4-2. Depends: wp2-m2-moment-maps, wp2-m2-line-definition, wp2-m2-input-quality.

**M3**

- [ ] **M3** `wp2-m3-moments-extensions`: (1) 4D stacks: (scan, step, slit) maps with three pixel links, via WP6's sliced-coords contract. (2) Profile-range wings: a `layer_action` callback gets only the layers and data collection, no viewer or range (glue_qt/app/layer_tree_widget.py:484-486@0.4.2), so a Profile `viewer_tool` (the `solar:frame_time` pattern) subclassing glue-qt's public `RangeMouseMode` (`glue_qt/viewers/profile/mouse_mode.py:87@0.4.2`) opens `MomentsDialog` for the viewer's reference data with the dragged range, converted from `x_display_unit` to Å, as wings; it never reads the private `_profile_tools.rng_mode` (D2). Done when a 4D stack from the irispy fixture gives maps of its (scan, step, slit) shape with three links, scan 0 equals the per-scan action and the map survives a WP3 round trip; and a dragged range opens the dialog with those wings, while one not containing the centre is refused. Features: none (extends F153/F154). Findings: wp2-wp6-science-2. Depends: wp2-m2-moment-maps, wp2-m2-line-definition.
- [ ] **M3** `wp2-m3-window-data`: Uncertainties, error maps and binning.
  - Opt-in `read_files(..., uncertainty=True, memmap=False)` in `glue_solar/sources/loaders/iris.py` adds '<flux> uncertainty' (eager, doubles memory; `memmap=True` gives unscaled uncertainties, io/spectrograph.py:252-257@0.9.0), reversed along the step axis for negative-step rasters (D10).
  - Once irispy propagates uncertainty in `calculate_moments` (`wp0-irispy-requests`), moments add `intensity_error` and `velocity_error` (iris_xmap's Ierr/Verr).
  - 'Rebin…' wraps `NDCube.rebin` (ndcube 2.4.2) for spatial and spectral binning in a `layer_action` adding a Data with `_GlueWCS(ResampledLowLevelWCS(...))` coords, linked by `link_hpc`.

  Done when: on ~/DATA/IRIS 20180102 Si IV 1403 the uncertainty equals the irispy-loaded cube's; on 3400109360 it follows the data's step order; the error maps equal irispy's output; a 2×2 spatial rebin halves both spatial dimensions and preserves the mean of finite samples; the rebinned Data links to the source through `link_hpc` and survives a WP3 save/reopen with equal world coordinates. Features: F160. Findings: followup-4-2. Depends: wp2-m2-moment-maps, wp1-m0-link-hpc, a `wp3-wcs-saver` branch for `ResampledLowLevelWCS` (rebin only), and an irispy release with moments uncertainty propagation (error maps only).
- [ ] **M3** `wp2-irispy-calibration-actions`: Two D4 `layer_action`s on the moments rewrap helper, which here keeps the SGMeta and restores the 'exposure time' extra coordinate from WP4's 'Exposure time' component (both calls need it): 'Remove dust' (`SJICube.remove_dust`, irispy 0.9.0 sji.py:234) on an SJI and 'Radiometric calibration' (`irispy.utils.spectrograph.radiometric_calibration`, packaged `iris_sra_c_20231106.geny`, no download; 0 s exposures become NaN) on a per-scan raster. Each adds one Data linked on every pixel axis and opens no viewer; data without SGMeta (e.g. restored from a session, wp3-wp5-4) is refused with a message. References are direct irispy calls on the irispy-loaded cube with the same D12 fill (NaN at -200/-199) and exposure times, compared with `equal_nan=True`. Done when: on 4000255147 SJI_1400, 'Remove dust' adds one same-shape Data equal to the reference `remove_dust` (`exposure_normalize=True`); on 4000005156 Si IV scan 0, calibration equals the reference (rtol 1e-6) and the Profile viewer shows erg s⁻¹ sr⁻¹ cm⁻² Å⁻¹; a raster given to 'Remove dust', or an SJI given to calibration, is refused and adds nothing. Features: F166, F169. Depends: wp2-m2-moment-maps, wp4-exposure-readout, wp10-fill-nan.
- [ ] **M3** `wp2-m3-mg-features`: Ask irispy to port `iris_get_mg_features_lev2` (k2v, k2r, k3, h2v, h2r, h3 positions, velocities and intensities; absent from 0.8.1, 0.9.0 and main), contributing it if accepted, and wrap it as a D4 `layer_action` adding one linked map Data; if irispy declines, it becomes a scripting-only recipe (WP9). Done when, on ~/DATA/IRIS 20140708 3824262996 Mg II k, the maps equal a direct irispy call, pixels irispy flags invalid are NaN, and the maps link to the source raster with no viewer opened. Features: F162. Depends: wp2-m2-moment-maps, an irispy release (WP0).
- [ ] **M3** `wp2-m3-density-temperature`: A separate D4 `layer_action` on two same-grid WP2 intensity maps (e.g. O IV 1399.77/1401.16 from the Si IV 1403 window) that calls `irispy.utils.density.density_diagnostic` (density.py:99@0.9.0) with a fiasco `Ion`, or `map_ratio_to_quantity` for temperature ratios, and adds one linked log n_e (or T) map; fiasco and CHIANTI stay optional. Done when: with fiasco installed (the iris-plan env lacks it), a synthetic ratio map gives the same densities as a direct irispy call; a real O IV pair gives a log n_e map linked to the source; without fiasco the action refuses with a message and adds nothing. Features: F163. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-burst-detection`: Port `iris_burst_check` (Si IV, threshold scaled by the time-dependent 1402.77 Å response) and `iris_sji_burst_check` (SJI 1400) to irispy first (0.9.0 has none), then add a D4 `layer_action` 'IRIS: detect UV bursts' adding a uint8 burst-mask Data linked to the source; if irispy declines, it becomes a scripting-only recipe (WP9). Done when the irispy function is released and pinned and, on 4000255147 SJI 1400 and a real Si IV raster window from ~/DATA/IRIS, the output equals irispy's, has the source's spatial and time shape, a subset on it propagates to the source, and other windows and channels are refused with a message. Features: F130. Depends: wp2-m2-moment-maps, an irispy release (WP0).

**Notes and limits**

- Profile Collapse (glue-qt profile_tools.py:31-37@0.4.2) is a display-only quicklook: no dataset, index-based moments, NaN if any sample is NaN.
- Velocities are relative to the uncorrected Level-2 wavelength scale (irispy 0.9.0 has no orbital/thermal drift correction), as `velocity_caveat` (`LEVEL2_CAVEAT`) states. Mg II h/k and C II centroids and widths are proxies.
- The +Inf guard covers a code path only: local int16 Level-2 files cannot store Inf, and all show NSATPIX 0.
- The 0.5 s and 3× limits are local acceptance numbers, not CI thresholds. `wp10-m0-wcs-lock` covers only `_GlueWCS` calls, so the rewrap deep-copies the raw WCS while holding it; the Worker and map coords use only that copy, and the map shares no astropy WCS with its source.
- WP0 tracks the uncertainty request (`wp0-irispy-requests`) and the negative-step mask/uncertainty flip; WP2 files its Mg II and burst requests and records their URLs in the WP0 reports table.

### WP3: Sessions

Save Session and Open Session must work on released core (D5) for a coordinated IRIS quicklook and every glue-solar dataset (SJI, raster windows, stacks, sunpy Maps, derived maps), through glue's own hooks and registries (D13). M0 has no WP3 work; until M1, WP9's docs say sessions with any glue-solar dataset (File→Open Maps included) fail to save. M1 ends with `wp3-app-session-acceptance`; M3 reopens the last session.

Port from prototypes:

- `IRIS_PLAN_PROTOTYPES/wp3_impl.py` (parts): record builders go module-level into `glue_solar/sources/loaders/iris.py`; `read_iris_rasters` becomes a named factory; `image_data` replaces `read_iris_image`; no import-time rebinding or `install_browser_factories()` (D13). Apply the checkbox fixes, then reword the docstring at `wp3_impl.py:4` ('Keep this module importable…'): no saved session references `wp3_impl`.
- `IRIS_PLAN_PROTOTYPES/wp3chk_test_sessions.py`: move the 6 tests and `_assert_same_coords`, `_round_trip`, `_style_record` to `glue_solar/tests/test_sessions.py`, with `find_irispy_test_file` fixtures (wp1-links-4), a `< 100_000` B size assertion (wp3-wp5-19), the production style `_type` asserted, and no import-time install.
- `IRIS_PLAN_PROTOTYPES/review_20260905/test_plan_integration.py`: WP6 ports only `test_wp3_roundtrips_wp6_fitted_map` at M2 (usefulness-7) and drops the stubs (wp4-quicklook-15). WP2's moments round trip stays in `wp2-m2-tests-docs`.

**M1**

- [ ] **M1** `wp3-style-cmap`: Make styles and colormaps session-safe without core #2597. Add `SolarVisualAttributes`, whose `__gluestate__` saves `preferred_cmap` by name (unknown names restore as `None`). `_cube_data` and both map loaders (`glue_solar/sources/maps.py`, `glue_solar/sources/loaders/maps.py`) construct it only while a probe shows core saving a Colormap object (WP0 register); the class stays importable afterwards (sessions record its path). `setup()` registers matplotlib's named colormap copies so core's `_load_cmap` resolves `cmap.name`. No global `VisualAttributes` saver. Add a changelog fragment and a sessions note in `docs/user_guide/loading-aia-and-hmi.rst`.
  Done when: an application session holding only an AIA map opened with the 'sunpy Map' factory restores with layer cmap `sdoaia171`; `SolarVisualAttributes(preferred_cmap='irissji1400')` on a plain-coords `Data` round-trips through `GlueSerializer` with an equal name; a plain `Data` style record keeps glue's `_type` and has no `_protocol`. Features: none. Findings: archive-trace-5, wp3-wp5-5.
- [ ] **M1** `wp3-wcs-saver`: Add `_GlueWCS.__gluestate__`/`__setgluestate__` in `glue_solar/sources/loaders/iris.py` (builders module-level for WP12's export). Records: gWCS as ASDF; FITS WCS as header plus `pixel_shape`; `-TAB` (irispy's 3-axis raster layout only) as header plus the rebuilt WCS-TABLE, table axes from `PSi_1`, an index column only where `PSi_2` exists (WP10 drops `PS3_2`; followup-2-6); `SlicedLowLevelWCS`/`CompoundLowLevelWCS` recursively with slices, mapping and shape, indices any `numbers.Integral` cast to `int`. Anything else raises a `GlueSerializeError` naming it. Declare `asdf` and `gwcs`.
  Done when `test_sessions.py` round-trips each case twice with `pixel_to_world_values`/`world_to_pixel_values` agreeing to 1e-9 on integer and +0.37 pixel grids, and equal world axis names, units, component labels, arrays, masks and `Time`: a real SJI (gWCS); a raster window in both WP10 forms (index-free rebuild; original WCS kept when the probe fails); a 3-scan stack (compound, index-free `-TAB` inside); a 3400109360 negative-step window (local; skipped when absent); a `_GlueWCS`-wrapped sunpy Map (D3) and a mixed collection; an `np.int64`-indexed `SlicedLowLevelWCS`; `_GlueWCS(SlicedLowLevelWCS(raw, (slice(None), slice(None), 0)))` with `raw` a real raster window's `-TAB` WCS (the WP2 moments form). The irispy `make_spatial_template`/`dropaxis` 2-D `-TAB` WCS raises `GlueSerializeError` naming the layout, with no `IndexError` and nothing written. Features: none. Findings: wp3-wp5-14, wp3-wp5-3, wp3-wp5-18, followup-2-6, usefulness-8. Depends: `wp10-m0-interaction-latency`.
- [ ] **M1** `wp3-quantity-meta`: Save Quantity meta as value and unit without mutating the live meta (D13). At import, register `@saver(u.Quantity)` only if `u.Quantity not in GlueSerializer.dispatch`, and `@loader(u.Quantity)` only if absent from `GlueUnSerializer.dispatch`. Use the version-1 `{"value", "unit"}` record of `wp0-core-quantity-saver`, so either saver's sessions load with the other; retire when a core release contains it (WP0 register). Document core's omission of `Time`/`SkyCoord` meta ('auxiliary times', 'exposure FOV center').
  Done when a real irispy 0.9.0 raster, whose SGMeta holds the 'exposure time' and 'observer radial velocity' Quantities, restores `meta['exposure time']` as an equal `Quantity` in s, and importing glue-solar after another Quantity saver and loader are registered raises nothing. Features: none. Findings: wp3-wp5-5, usefulness-8.
- [ ] **M1** `wp3-plain-meta`: Make window identity and rest wavelength survive a session as plain JSON meta keys.
  - `wp5-m1-rest-wavelength-policy` writes `meta['spectral_window']` (the TDESC name; scan 0's for stacks) at load, and `meta['rest_wavelength']` (a float in Å) and `meta['rest_wavelength_source']` at load (D11 default) or from its 'Set rest wavelength…' action. This item owns the session round-trip test for all three keys.
  - Derived products' keys also survive: `moments_centre`, `line_regime`, `rest_wavelength`, `rest_wavelength_source`, `velocity_caveat`, `doppler_sign` and `fit_seed_center`, and `moments_last` (a dict of floats) on the source Data.
  - Readers use only these keys; restored datasets have no SGMeta, so `wp2-irispy-calibration-actions` refuses them.

  Done when, on 20140708 3824262996 `r00000` (local):
  - Si IV 1403, saved with an Å Profile showing the km/s top axis, reopens with that axis, `rest_wavelength` 1402.77, `rest_wavelength_source` 'line list' and `spectral_window` unchanged;
  - Mg II k 2796 has no `rest_wavelength` or `rest_wavelength_source` after load (D11: the window contains h); after the user picks k, it saves with the top axis and reopens with it, 2796.352 ('user choice') and `spectral_window` unchanged;
  - C II 1336 with no line picked has neither key after restore;
  - once the `wp5-m1-velocity-axis` probe passes, the Si IV and Mg II k sessions saved with a km/s Profile x axis reopen offering km/s;
  - the derived-product keys above survive as plain JSON.

  Features: none. Findings: wp3-wp5-4, archive-trace-3. Depends: `wp5-m1-rest-wavelength-policy`, `wp5-m1-velocity-axis`, `wp3-quantity-meta`, `wp0-core-profile-restore-priority`.
- [ ] **M1** `wp3-file-references`: Route browser loads through `load_data` so sessions reference files: `QtIRISImporter` calls a new path-first factory, `read_iris_rasters(path, files=None, windows=None, stack=False)` (`files` relative to the first file's folder), and the public `image_data(path)` via `load_data(..., factory=...)`. Derived maps stay embedded. These two `glue_solar.sources.loaders.iris` paths and File→Open's `glue_solar.sources.iris.read_iris_file` are a session format; keep aliases if they move. WP8's `meta['SOURCE_FILES']` is informational; relocation uses LoadLog only.
  Done when: a browser-loaded SJI 1400 and a 3-scan C II 1336 stack have `_load_log`, and their `include_data=False, absolute_paths=False` session is < 100 KB with relative names in the LoadLog kwargs; after the files and the session move to a new folder, it restores, re-saves and restores again with equal data; a raster opened with File→Open ('IRIS Level 2 FITS') restores from its file with every window. Features: none. Findings: wp3-wp5-19.
- [ ] **M1** `wp3-session-budget`: Keep sessions small. Released core embeds every component that lacks a LoadLog, even with `include_data=False` (21.3 MB for one int32 (100,200,200) broadcast). Factory-built components (`Time`, WP4's `Exposure time`, WP10's uint8 masks) are LoadLog-referenced; WP4 adds none after load (D8). A full-shape post-load component (WP4 Design B, 'Slit x') is an expression `DerivedComponent` or a `BroadcastComponent` that saves only its 1-D values, axis and shape, added with its first consumer. WP6 fit products add at most 2x their 2-D map bytes; the opt-in float32 residual is embedded outside the budget (confirmed).
  Done when: a file-referencing session of 4000255147 holding Si IV plus one more window and SJI 1400, with WP4 time sync and a Pixel point active, is ≤ 1 MB and saves in ≤ 2 s on the WP10 reference machine; the fixture session stays < 100 KB; a test fails if an IRIS dataset gains a component that has no LoadLog and is neither derived nor compact. Features: none. Findings: wp3-wp5-8, followup-2-3, archive-trace-1, wp4-quicklook-4. Depends: `wp3-file-references`, `wp4-time-sync`.
- [ ] **M1** `wp3-coordination-reattach`: Re-attach WP4 coordination after a restore through the D9 viewer tools, which glue-qt 0.4.2's `ToolbarInitializer` recreates for restored viewers. Each registers with the per-DataCollection coordinator (created on demand, held strongly), which at creation scans `dc.subset_groups` for a `PixelSubsetState`, since a restore sends no `SubsetUpdateMessage`. Persist only the user's choices, the time master and any timing step, as the plain JSON keys `meta['quicklook_time_master']` and `meta['quicklook_timing_step']` (WP4 Notes); recompute the rest from `Time` and the WCS.
  Done when, in a new `GlueApplication` that has restored a saved quicklook:
  - no slider moves until the user acts;
  - the saved master is still master, and stepping it gives the followers the same offsets and NO MATCH labels as before the save;
  - a Pixel drag on the raster map drives the spectrogram and SJI fixed indices, and one on the SJI drives the raster indices and the time match;
  - one click causes one `group.subset_state` assignment and at most one `SubsetUpdateMessage` per dataset (glue/core/subset_group.py:178-180);
  - the coordinator has read both meta keys at creation;
  - the 'Exposure time' component and the per-frame `data.meta` arrays of `wp4-exposure-readout` (pztx/pzty, xcenix/ycenix, slit x) equal their pre-save values, restored or re-read from the file.

  Features: none. Findings: archive-trace-2, wp3-wp5-7. Depends: `wp4-time-sync`, `wp4-m0-point-fixed-index`, `wp1-m1-sji-to-raster`, `wp3-wcs-saver`, `wp3-quantity-meta`, `wp3-style-cmap`.
- [ ] **M1** `wp3-app-session-acceptance`: A pytest-qt test saves and restores, file-referencing and twice, (a) 4000255147 sit-and-stare + SJI 1400 and (b) 4000005156 raster + SJI 2796, each with an AIA map opened through File→Open, which `wp1-m1-sunpy-maps` routes to the 'sunpy Map' factory. It covers the raster-map, spectrogram, SJI and spectrum viewers; a Profile with a non-default `x_att` in Å and nm, plus km/s once the `wp5-m1-velocity-axis` probe passes, and on 0.4.2 an Å Profile with its km/s top axis; Pixel point and ROI subsets; WCS and `link_hpc` links; the MDI tab geometry (D15). Then replace the 'Saving sessions' warning in `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst` (relative paths relocate; glue-solar is needed; 'include data' embeds every array) and add a changelog fragment.
  Done when:
  - viewer types, `x_att`/`y_att`, slices, limits, stretch, `cmap_bad`, each layer's `visible` and `zorder`, and the cmaps (SJI 1400 `irissji1400`, AIA `sdoaia171`) equal the originals;
  - the raster viewers come back as the `wp10-m0-roi-guard` ImageViewer subclass imported from `glue_solar/quicklook.py` (its class path is a session format; keep an alias if it moves);
  - subsets, links and the tab's viewer positions and sizes are equal;
  - the `wp3-coordination-reattach` checks pass, and the session meets `wp3-session-budget` and embeds no source arrays.

  WP2, WP4, WP5, WP6, WP7 and WP12 keep their own save/reopen tests. Features: F175. Findings: wp3-wp5-7, archive-trace-2, archive-trace-5, core-qt-capabilities-5, wp3-wp5-2. Depends: the other WP3 M1 checkboxes, `wp0-core-profile-restore-priority`, `wp4-quicklook-preset`, `wp1-m0-link-hpc`, `wp1-m1-sunpy-maps`, `wp5-m1-velocity-axis`, `wp1-m1-wrapper-coherence`.

**M3**

- [ ] **M3** `wp3-last-session`: Reopen the last session (CRISPEX LAST_SESSION). The WP4 quicklook entry connects `QApplication.aboutToQuit` on its first run (never in `setup()`, which every glue-qt process runs). The handler returns if the components glue would embed (no `_load_log`; not derived, broadcast or coordinate) exceed 1 MB; else it calls `GlueSerializer(app, absolute_paths=True).dumps()`, swallowing every exception (not `app.save_session`, whose `@catch_error` opens a dialog). Only a result ≤ 1 MB made in ≤ 2 s is written, via a temp file and `os.replace`, to `iris_last_session.glu` under `glue.config.CFG_DIR` (read at call time). Add a `menubar_plugin` 'IRIS: reopen last session' and a `startup_action` 'iris_last_session'.
  Done when, headless with `glue.config.CFG_DIR` monkeypatched to `tmp_path`: the handler run after a quicklook writes the file, and a new `GlueApplication` plus the menu action restores the same viewers; with a 100 MB embedded dataset it returns in < 0.1 s and writes nothing; a serialization error writes nothing and opens no dialog. Features: F176. Depends: `wp3-app-session-acceptance`, `wp4-launch-entry`. Upstream alternative: glue-qt 'Open Recent' or autosave.

**Notes and limits**

- Sessions record `glue_solar` class and function paths, so loading needs glue-solar and its Qt imports; while the solar Quantity pair is active, so does any glue-solar-saved session with Quantity meta, and Quantity subclasses return as plain `Quantity` (wp3-wp5-5).
- Derived-map contract (wp3-wp5-3): derived spatial maps (WP2, WP6) use `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))` from the source's raw WCS; a bare outer sliced wrapper or irispy's `dropaxis` template fails the whole save. New coords types (WP1, WP2 `wp2-m3-window-data` `ResampledLowLevelWCS`, WP12) each reuse or add a record kind and a round-trip case in their own checkbox. `wp1-m1-sunpy-maps` (D3) merges after or with `wp3-wcs-saver`: map sessions work after `wp3-style-cmap` because their raw WCS saves natively; wrapping them in `_GlueWCS` earlier breaks them.
- Scoped to glue-solar coords: no generic `-TAB` framework, no core fix for low-level WCS wrappers or `clone(link)`, no dependencies beyond `asdf` and `gwcs`.
- LoadLog cannot replace the WCS saver: glue saves `data.coords` for every dataset (wp3-wp5-18). If irispy's `gwcs_raster_clean` (D14) lands with transforms lacking ASDF converters, combined-raster sessions fail until irispy ships them (WP0, upstream-state-2) or the record re-derives the WCS from the file.
- Known gaps: 'include data' sessions embed every array and are unbudgeted; the colormap combo labels `sdoaia171` as GOES-R SUVI 171 (cosmetic).

### WP4: Quicklook preset and coordination

WP4 builds a CRISPEX-style IRIS quicklook from stock Glue viewers (new `glue_solar/quicklook.py`; `glue_solar/tools.py`); M0 runs on the D5 baseline with no glue links (D8). Data, by OBSID:
- ~/DATA/IRIS 4000255147 (sit-and-stare + SJI 1400); 4000005156 (2-scan raster + deconvolved SJI 2796); 3824262996 (400-step Mg II); 3400109360 (negative step);
- CI: irispy 0.9.0 fixtures 3620258102 (20210905 sit-and-stare, 187 exposures, four SJI channels) and 3860258481 (20140329 raster, 13 files of 8 steps).

Panels (plus per-channel SJI viewers and the point spectrum; stacks open only from the browser and menu):

| Observation | Map | Spectrogram | λ vs step or time |
|---|---|---|---|
| Raster (step, slit, λ) | step × slit at λ0 | λ × slit at point's step | whisker: λ × step at point's slit |
| Sit-and-stare (exposure, slit, λ) | 'Slit vs time': exposure × slit at λ0 | λ × slit at point's exposure | λ–t: λ × exposure at point's slit |
| Stack (scan, step, slit, λ) | step × slit at (current scan, λ0) | λ × slit at (scan, point's step) | λ–t: λ × scan at point's (step, slit) |

**Port** (per the prototype table): before archiving `wp4_common.py`, re-point the features.json glue_evidence rows citing it (F050, F069-F072, F102-F104, F106-F109, F111, F112, F118, F125, F126, F143, F190). The `mouse()`/`select_point()` helpers (in `glue_solar/tests/helpers.py`, shared with `wp9-m0-workflow-recipes`) and the point-drag test (`test_existing_workflows.py`) also find components by physical type (wp1-links-4), add the modal guard (usefulness-16) and assert band intersection only for same-dataset points (core-qt-capabilities-2).

**M0**

- [ ] **M0** `wp4-coordinator`: One `Coordinator` (`HubListener`) per DataCollection, held strongly on it, plus a registered `solar:coordinate` `SimpleToolMenu` (D9; 'Time master', 'Clear point') that registers viewers in `__init__` and unregisters idempotently in `close()`. Each subtool restores the previous mouse mode. It couples only equal `observation_key`s (OBSID + STARTOBS), follows the last group given a `PixelSubsetState`, re-applies the point on axis or reference-data changes, and writes only on change under one busy guard. Done when:
  - viewers opened later or restored via `cls(session, state=...)` join; closed ones leave; a second unregister raises nothing;
  - one map click on a 3D raster gives one `group.subset_state` assignment, ≤ 1 `SubsetUpdateMessage` per dataset and no coordinator assignment. On a 4D stack map the coordinator adds exactly one assignment, which pins the scan (the stock Pixel tool leaves it `slice(None)`, glue/viewers/image/pixel_selection_mode.py:56-58@1.27.0). The stack then gets ≤ 2 `SubsetUpdateMessage`s and no further feedback;
  - Pixel stays active after 'Clear point' and 'Time master';
  - after the stock combo swaps the 4000005156 map to λ × slit, its step slider equals the point's and no wavelength slider moved;
  - a second loaded observation is never coupled.

  Features: —. Findings: wp4-quicklook-9, usefulness-5.
- [ ] **M0** `wp4-quicklook-preset`: `quicklook(app, datasets)` opens the panel table in a new MDI tab (D15). The same PR (no dependency edge) wires in `wp10-m0-roi-guard` and `wp10-m0-large-data-modal`. Rules:
  - roles from INSTRUME or cube class, not physical types; sit-and-stare from STEPS_AV == 0 and NRASTERP; window: the browser's tick, else Mg II k 2796, else the first; λ0 nearest TWAVE (mid-window without TWAVE), never index 0 or the D11 rest;
  - given 'SJI_<c>' and 'SJI_<c> (deconvolved)' (`wp8-sji-variants`), open the plain one and offer the other (confirmed);
  - raster and SJI layers get `percentile = 99.5`; from M1, `wp11-histo-opt-scaling` also sets `stretch_global = False` on the map (M0 keeps glue's default);
  - aspect 'auto' on rasters until `wp11-physical-aspect`, 'equal' on SJIs; the Profile shows the bare Pixel subset's mean with a y = 0 line and no x display-unit override on 0.4.2; the point starts at the map centre in a new edit-subset group 'Point', with Pixel active on the map.

  Done when offscreen pytest-qt on 4000255147, 3824262996, 4000005156 (Stack ticked, deconvolved SJI 2796), 3620258102 and 3860258481 (one scan; 13 stacked) shows:
  - each viewer's `x_att`, `y_att` and `slices` match its row; `app.viewers` lists every panel;
  - raster and SJI layers have percentile 99.5; map planes have finite v_min < v_max;
  - the Profile shows only the seeded Pixel subset; the stock axis combo still swaps spectrogram and map;
  - no modal appears with the large-data prompt unpatched;
  - a 3640107442 AIA cutout rewritten to 4000255147's OBSID and STARTOBS gets no SJI role or slit.

  Features: F190, F056, F057, F065, F069, F071. Findings: usefulness-3, usefulness-4, wp4-quicklook-7, wp4-quicklook-14, followup-4-8, followup-2-5, core-qt-capabilities-5, core-qt-capabilities-8, core-qt-capabilities-9, plan-integrity-9, plan-integrity-13. Depends: wp4-coordinator, wp1-m0-link-hpc, wp8-sji-variants, wp10-fill-nan, wp10-mask-uint8, wp10-m0-wcs-lock.
- [ ] **M0** `wp4-launch-entry`: Entry points: `@startup_action('iris_quicklook')`; an 'Open quicklook' checkbox beside 'Stack' in `iris_loader.ui`, with `browse_iris` building one quicklook per loaded observation (`finalize` records each dataset's observation and kind through a per-window helper that `wp10-nonblocking-load` reuses unchanged; shared with WP8 M2); a `menubar_plugin` 'IRIS: quicklook…' grouping data by `observation_key`, asking when several match. Startup, which cannot stack, opens the single-raster preset on the first scan, labels files by rNNNNN scan and notes in the status bar that stacks need the browser's Stack option. Its guide section maps CRISPEX entry keywords and xcontrol modes to owners (no CLI parser; owners include `wp2-m2-line-definition`, `wp4-m0-time-wavelength-panels` and `wp9-m0-workflow-recipes`; Detector excluded). Done when, with `dialogs.warn` and QMessageBox patched to fail:
  - on 3620258102 + SJI 1400 the three paths open identical viewers;
  - with two observations loaded, browser and menubar open only the chosen one;
  - startup on the 13 3860258481 files gives 13 distinct labels and the single-raster preset;
  - with #2595 (probe-gated), `--startup=iris_quicklook` opens no AutoLinkPreview;
  - a manual 4000255147 run shows no 'Add large data set?' dialog.

  Features: F012, F015, F020. Findings: usefulness-11, core-qt-capabilities-9. Depends: wp4-quicklook-preset, wp10-m0-large-data-modal, wp10-mask-uint8.
- [ ] **M0** `wp4-m0-point-fixed-index`: The stock Pixel point is the selected detector pixel (D6, D7). On each point update the coordinator writes its step, exposure or scan and slit into the other same-dataset panels' non-displayed `slices` (a stack's point stays on the current scan), coalescing drag updates latest-only with a single-shot QTimer. A λ-panel click is canonicalised once: the point takes that panel's fixed indices and the clicked non-λ index, and the map moves to the clicked λ; nothing else writes a wavelength slice. Slider edits move the point (F096). 'Clear point' or any non-Pixel state stops point updates and hides markers; time sync continues. SJI points mark only the SJI until `wp4-sji-click-to-raster`. The subset stays bare. Done when, on 3860258481 (one scan; 13-scan stack), 3824262996, 4000005156 (stack) and 4000255147:
  - a map click at (s, y) sets the spectrogram step to s and the whisker/λ–t slit to y; no wavelength slider moves;
  - the spectrum is cube[s, y, :] (cube[k, s, y, :] at scan k) and follows scan changes;
  - on 4000005156 scan 0 a spectrogram click at (λj, y) moves the map to λj and the point to (s, y), keeping the spectrum cube[s, y, :];
  - typing step s′ in the spectrogram moves crosshair and spectrum to s′ with one `group.subset_state` assignment;
  - the slit (and on scanning rasters and stacks the step) stays fixed while scan, exposure or SJI master steps;
  - a Profile Collapse AggregateSlice raises nothing, and the coordinator reads its `.center` and never writes over it; reopening a panel keeps the behaviour.

  Features: F102, F096. Findings: wp4-quicklook-13, followup-3-5, usefulness-3, usefulness-5, wp4-quicklook-7, wp4-quicklook-10, core-qt-capabilities-2. Depends: wp4-coordinator, wp4-quicklook-preset, wp10-m0-interaction-latency, wp10-m0-wcs-lock.
- [ ] **M0** `wp4-time-sync`: The coordinator caches per-pair nearest-index and signed-offset arrays from `nearest()` over each dataset's 1-D `Time` (D7, D8, D10) and adds no links or components after load (archive-trace-1). The raster is the default master ('Time master' switches to an SJI); its timing step is the point's step (mid-raster without a point, F112). An SJI master moves only time axes (for a stack, the scan whose timing-step `Time` is nearest). A single scanning raster has no time axis: it shows its signed Δt against `Time` at the timing step and is NO MATCH only outside its coverage. `solar:frame_time` shows 'time master' and the timing step on the master, the signed Δt on matched followers and 'NO MATCH Δt = …' on greyed NO MATCH followers, which keep their frame. Every registered viewer tool (WP7 `solar:time_marker`, WP12 light curves) gets each master-time change and exposure duration from either master. Done when:
  1. 4000005156 2-scan stack + SJI 2796 (32 frames, 11.69 s), point at step 32. SJI master: frames 0-15 select scan 0, 16-31 scan 1; frames 0, 20, 31 show Δt +85.0, +38.1, −90.5 s against Time[scan, 32]; step and slit unchanged; with scan 0 alone frames 16-31 are NO MATCH. Raster (scan 0) master: step 0 makes the SJI NO MATCH (Δt 8.611 s > 5.845 s); steps 1-3 match (5.581, 2.721, 0.069 s).
  2. 4000255147 (1600 × 2.89 s) + SJI 1400 (400 × 11.88 s): indices are argmin|Δt|; in coverage |Δt| ≤ 1.445 s (raster), ≤ 5.94 s (SJI); an SJI master keeps the slit fixed.
  3. 3400109360 (STEPS_AV −0.998), one scan and a 2-scan stack (descending `Time` per scan), with a synthetic SJI spanning them: indices equal the argsort reference, matched |Δt| < half the cadence, nothing raises; ties go to the earlier time, duplicates to the first index. `wp10-m0-negative-step` relies on this check.
  4. `nearest()` units: an exact tie, duplicates, a gap, a NaT reference frame (raises), times before and after coverage.
  5. Wavelength and slit sliders never move; a Profile Collapse AggregateSlice raises nothing: on the master its `.center` gives the time index, and on a follower the aggregate is left in place, not replaced by an int.

  Features: F111, F112. Findings: wp4-quicklook-1, wp4-quicklook-2, wp4-quicklook-4, wp4-quicklook-5, wp4-quicklook-10, wp4-quicklook-11, followup-4-1, followup-1-1, followup-1-2, followup-1-3, followup-2-3, followup-3-13, wp3-wp5-8, usefulness-15. Depends: wp4-coordinator, wp4-m0-point-fixed-index, wp1-m0-link-hpc.
- [ ] **M0** `wp4-m0-time-wavelength-panels`: Whisker and λ–t panels are stock ImageViewers (x wavelength pixel; y step, exposure or scan; unwarped, F082), titled 'step (acquisition order)', 'exposure' or 'scan', never 'step/time'. On a displayed sit-and-stare step axis, `solar:frame_time` sets the label 'Exposure (acquisition order)' and integer exposure-index ticks, re-applying both after every `_set_wcs` label reset and `x_att`/`y_att` change; the axis stays an index axis (UTC axes: `wp12-time-regrid`). A probed private patch (D2) stops the Pixel crosshair reappearing at (0,0) after an IncompatibleAttribute. Done when:
  1. on 4000255147 Si IV 1403, a point at slit y makes λ–t equal cube[:, y, :] and `solar:frame_time` shows the UTC range; label and ticks survive a slit-slider move and an axis swap;
  2. on the 3860258481 13-scan stack (CI) and ~/DATA/IRIS 3602506433 (99 scans), λ–t equals stack[:, s, y, :] at (s, y) and follows a drag;
  3. on 4000005156 scan 0 the whisker equals cube[:, y, :] (x wavelength, y step);
  4. no (0,0) crosshair appears on spectrogram, whisker or λ–t panels; the patch turns off when its probe sees the upstream fix.

  Features: F134, F142, F143, F082. Findings: archive-trace-10, plan-integrity-13, wp4-quicklook-14, usefulness-4. Depends: wp4-quicklook-preset, wp4-m0-point-fixed-index, wp1-m0-axis-names, wp0-core-image-artist-bugs (register row, not the upstream PR).
- [ ] **M0** `wp4-sji-panels`: One ImageViewer per selected SJI channel, titled with channel and variant, following `wp4-time-sync`, with limits of the raster footprint plus a margin; off-frame points show 'outside SJI FOV'. Done when:
  - the 3620258102 fixture with SJI 1330, 1400, 2796 and 2832 opens four titled SJI viewers that follow the master;
  - on 4000005156 + SJI 2796 the limits contain the four raster-footprint corners;
  - test points > 2 SJI px inside and outside the FOV get the expected label, with `wp1-m0-sji-crpix` active.

  Features: F109, F118. Findings: followup-4-8. Depends: wp4-quicklook-preset, wp4-time-sync, wp1-m0-link-hpc, wp8-sji-variants, wp1-m0-sji-crpix.
- [ ] **M0** `wp4-slit-point-overlay`: `solar:coordinate` draws on SJI viewers a slit line at the frame's SLTPX1IX (`wp4-exposure-readout`), hidden for a displayed frame axis or a 0/NaN value, and the raster point via `show_crosshairs`, projected through the frame's SJI WCS. The 1-based SLTPX1IX shift switches on with `wp1-m0-sji-crpix` in one joint test that this item owns. No `pixel_stride` or 'Slit x' component enters the production API; fixture tests rescale the stride-10 irispy SJIs themselves. Done when:
  - on the full-resolution 4000255147 SJI 1400 (400×417×388) the line sits at SLTPX1IX (195.0 at frame 0) in the joint test's convention, within 0.5 SJI px of the projected slit at frames 0 and N−1 and 1 px at every frame (`slit_check.py` approach C);
  - on the binned 3860608353 SJI 2832 (SUMSPAT 2), at frames 0, N//2 and N−1 the drawn line lies within 0.5 binned px of the centroid of the dark slit trough in that frame's column-median profile (probe 2026-09-27: 183.8-184.0 0-based against SLTPX1IX 184.75, which is 1-based). The raster-projection oracle is added once a 3860608353 raster is downloaded;
  - the marker follows the frame, hides off the FOV, and stays with link_hpc and time sync active.

  Features: — (overlay part of F109). Findings: wp4-quicklook-3, plan-integrity-21, usefulness-18, wp4-quicklook-16. Depends: wp4-sji-panels, wp4-exposure-readout, wp1-m0-sji-crpix.
- [ ] **M0** `wp4-exposure-readout`: The IRIS loader's `_cube_data` adds a per-frame 'Exposure time' [s] component at load (raster values as reordered by `wp10-m0-negative-step`; stacks per scan) and keeps the SJI's pztx/pzty, xcenix/ycenix and slit x in `data.meta`. `solar:frame_time` shows 'UTC start · exp N s' (a range for maps) with the pointing in its tooltip. Done when:
  - on 4000255147 SJI 1400 frame k shows EXPTIMES[k] (about 2.000 s); the tooltip equals the stored pztx/pzty;
  - on ~/DATA/IRIS 3610108077 Si IV step 157 shows 'exp 0 s', the other steps 7.999 s;
  - 4000005156 stack scan-1 values equal the r00001 file's;
  - 3400109360 values equal aux EXPTIMEF (FUV) or EXPTIMEN (NUV), reversed.

  Features: F117. Findings: followup-3-11, plan-integrity-22. Depends: wp10-m0-negative-step.
- [ ] **M0** `wp4-tests`: Write `glue_solar/tests/test_quicklook.py` test-first on named data with the ported helpers, qs_isolate plus an isolated HOME, `dialogs.warn`/QMessageBox patched to fail, and a manual native-GUI checklist. Each interaction (SJI frame change, map click, λ-panel click, scan/exposure change, spectrogram slider edit) asserts which panels move and which stay; a `quicklook(app, [])` run with `new_data_viewer` patched out is not coverage. Regressions: V34 rasters, sit-and-stare labels, AIA classification (add-order, no-links and layer-overlay checks are `wp1-m0-link-graph-regression`'s). The quicklook crash stress runs (0 crashes in 20 offscreen runs, 3 Pixel clicks on 3824262996 and 4000255147) belong to `wp10-m0-acceptance`; WP4 adds no second stress harness. Done when the suite passes in `iris-plan` on released core, real-data tests skip cleanly without ~/DATA/IRIS, and CI runs the fixture cases.

  Features: —. Findings: usefulness-16, wp4-quicklook-15, usefulness-3. Depends: wp4-quicklook-preset, wp10-m0-wcs-lock.

**M1**

- [ ] **M1** `wp4-m1-hover-lock-tool`: A 'Follow/lock' `PixelSelectionTool` subclass with its own icon. Unlocked, motion sets the followed group's `subset_state` on each new rounded pixel, latest-only at 50 ms and outside the command stack; the first hover creates the group if none exists and leaving the axes stops updates. A left click locks through one undoable `ApplySubsetState`; a right click, Esc or the toggle unlocks; middle click is `wp11-distance-measure`'s. F095's auto-contrast cursor colouring is left out. Done when, via canvas `motion_notify_event` on 3860258481, 3824262996 and 4000255147:
  - hovering moves the crosshairs and point spectrum within the WP10 click budget;
  - 100 motion events give ≤ 1 subset update per 50 ms and leave the `command_stack` length unchanged;
  - the lock survives scan and exposure stepping; a right click unlocks; stock Pixel is unchanged.

  Features: F094, F095. Findings: followup-3-5, solar-main-3. Depends: wp4-m0-point-fixed-index, wp10-m0-interaction-latency.
- [ ] **M1** `wp4-sji-click-to-raster`: The coordinator maps an SJI Pixel point with `sji_to_raster()` (`wp1-m1-sji-to-raster`) to the raster `PixelSubsetState`, which replaces the SJI state in the group (Replace mode, re-entrancy guard). Off-FOV points set nothing and show 'outside raster FOV'. The SJI click's `ApplySubsetState` is the only undo entry (the coordinator writes outside the command stack), so one undo reverts both. Route (D1) and undo rule: confirmed. Done when, on 4000255147 and 4000005156:
  - the `wp1-m1-sji-to-raster` 0.5 px round-trip cases pass through the UI, and the spectrum equals the raster data there;
  - one SJI click gives the SJI assignment plus exactly one coordinator assignment; one undo restores the previous point;
  - the `wp1-m0-link-graph-regression` checks pass with this path active (and the `wp1-m1-autolink-matrix` rows once its probe finds #2595).

  Features: — (F049's coordinator part). Findings: wp4-quicklook-13. Depends: wp1-m1-sji-to-raster, wp4-m0-point-fixed-index, wp4-time-sync.
- [ ] **M1** `wp4-profile-aggregation`: An 'Aggregation' subtool on the Profile's `solar:coordinate` picks single sample, mean, sum or a wavelength band. Single sample is the bare Pixel point's mean (exact per scan through the pinned scan); mean and sum are native Profile `function`s. A band light curve is a data-only subset the coordinator updates with the point, never intersected with Pixel. Done when:
  - on 4000255147 Si IV the band light curve equals nanmean(cube[:, y, j0:j1], axis=1) and follows a point drag;
  - with a band active on 4000005156 the linked-window marker and spectra still appear, and the titles name the choice.

  Features: —. Findings: plan-integrity-7, core-qt-capabilities-2. Depends: wp4-m0-point-fixed-index, wp4-m1-spectral-coupling.
- [ ] **M1** `wp4-slice-profiles`: A probe gates this on both core `ProfileViewerState.slices` (#2596/#2601) and the Qt #70 Profile slider symbol being released. Then the coordinator writes the point and master-matched time indices into Profile `slices`; until then the M0 subset mean stays. Done when, with the capability, a Pixel point sets the scan/step/slit sliders and the spectrum equals cube[k, s, y, :] exactly, and without it the tests skip on the probe, not a version number.

  Features: —. Findings: plan-integrity-9, core-qt-capabilities-8. Depends: wp0-release-tracking (#2596/#2601 + Qt #70), wp4-profile-aggregation.
- [ ] **M1** `wp4-m1-spectral-coupling`: `solar:coordinate` joins `ProfileViewer.tools` and draws plain lines: each same-dataset Image viewer's wavelength in every Profile; wavelength and master-time lines on whisker and λ–t panels; a Doppler-mirror line at 2λ0 − λ from the WP5 rest (D11, `wp5-m1-rest-wavelength-policy`). The km/s top axis is `wp5-m1-velocity-axis`'s (no second `secondary_xaxis`). It adds an 'Average spectrum' toggle (F071) and copies the Profile x-range (Å; km/s once a released Qt #70 allows it) to the λ–t x-limits. Released #2603 + Qt #73 line layers may replace them (`wp0-track-line-layers`). Accepted F075 gaps: global cross-window ranges and restricted slider stepping (per-window viewers instead), Shift+A/S (`wp11-keyboard-shortcuts`), stepping across concatenated windows (Level-2 non-goal). Done when, on 4000005156 scan 0 (Si IV 1403, Mg II k 2796) and 4000255147 with a λ–t panel:
  - slider index k puts the marker at λ[k] in Å and nm; it hides for a Scan or pixel x axis;
  - λ–t lines follow their sliders through axis swaps and reference-data resets;
  - Navigate to λ[j] moves the map to j in native Å; its km/s sub-check is an xfail gated on a Qt #70 symbol;
  - Profile limits of ±100 km/s around Mg II k set the matching λ–t limits (xfail until the `wp5-m1-velocity-axis` probe passes; on 0.4.2 it runs with equivalent Å limits);
  - a marker update costs < 5 ms;
  - markers reappear and follow after a WP3 save and restore; closing a viewer removes its callbacks.

  Features: F068, F075. Findings: core-qt-capabilities-4, core-qt-capabilities-8. Depends: wp4-m0-time-wavelength-panels, wp4-time-sync, wp5-m1-rest-wavelength-policy, wp5-m1-velocity-axis, wp1-m1-wrapper-coherence, wp3-coordination-reattach.
- [ ] **M1** `wp4-m1-multi-window`: Per ticked window the preset opens a spectrum Profile and, if the type has one, a λ–t panel. An idempotent helper adds identity `LinkSame` links between the step/exposure/scan and slit pixel axes of same-file windows, so one Pixel point drives every window; WP5's derived-product helper reuses them for derived maps (`wp5-m1-doppler-image`). The links join `wp1-m0-link-graph-regression`. Done when, on 4000005156 scan 0 with Si IV 1403, C II 1336 and Mg II k 2796 ticked:
  - exactly three Profiles open; a point at (s, y) gives each window's cube_w[s, y, :];
  - re-running the helper adds 0 links;
  - each window's own Image viewer has the crosshair at (s, y), with the other windows' layers disabled there (expected);
  - with #2595 (probe-gated) an inter-window WCSLink changes no result; this sub-check closes with `wp1-m1-autolink-matrix`;
  - a Pixel click on a synthetic derived map linked by the helper moves the source panels' fixed indices.

  Features: F072, F073, F074, F108. Findings: —. Depends: wp4-quicklook-preset, wp4-m0-time-wavelength-panels, wp1-m0-link-graph-regression.
- [ ] **M1** `wp4-context-reference`: An aligned AIA cutout (paired by OBSID + STARTOBS) opens a reference ImageViewer that follows `wp4-time-sync` and draws the IRIS slit and footprint from the raster WCS via link_hpc. `is_iris_fits` reuses `scan._is_supported_file`, so it also accepts `aia_l2_*` files with INSTRUME AIA*, giving File → Open context `_GlueWCS` and `Time`. ITN32 SJI cubes wait on irispy. Done when:
  - File → Open of a 3640107442 `aia_l2_*.fits` gives a Data with `Time` and `_GlueWCS` that follows the master once shown;
  - a generic, non-cutout AIA FITS is not claimed by the IRIS factory (it reaches the sunpy Map factory after `wp1-m1-sunpy-maps`);
  - with the matching 3640107442 IRIS raster and SJI (skipped if absent), the reference slit is within 0.5 AIA px of the raster-WCS slit at the matched time, with `wp1-m0-sji-crpix` active (followup-4-3).

  Features: F103, F104, F106, F107. Findings: followup-4-8. Depends: wp4-sji-panels, wp4-time-sync, wp1-m0-link-hpc, wp1-m0-sji-crpix, wp1-m1-sunpy-maps.
- [ ] **M1** `wp4-time-controls`: A 'Playback' viewer_tool drives the master's `slices` with a QTimer. It has a 'Go to UTC' field (nearest master exposure), a frame range [lo, hi] with a reset, and a play/stop toggle, a method that `wp11-keyboard-shortcuts` binds to Space. Done when, with explicit timer ticks on 4000255147 SJI 1400:
  - 'Go to 2013-09-02T17:00:00' selects argmin|Δt| and the raster follower moves;
  - a [100, 120] loop visits only frames 100-120;
  - the play/stop toggle starts and stops the timer; closing the viewer stops it.

  Features: F088, F091. Findings: followup-3-12, wp3-wp5-13. Depends: wp4-time-sync.
- [ ] **M1** `wp4-raster-overlays`: A 'Raster overlays' toggle shows the SJI footprint, a data-only subset that ORs one thin `RangeSubsetState` per raster step at that step's slit position projected through the SJI frame nearest its exposure (`slit_check.py` approach C), and a dashed map line at the current scan's step exposed nearest the master time, hidden on NO MATCH. Done when:
  - on 4000005156 (64 steps, deconvolved SJI 2796) and 3860258481 (8 steps) the footprint has one column per distinct projected step, each within 1 SJI px of the header-derived position with `wp1-m0-sji-crpix` active; 4000255147 gives one column;
  - on the 4000005156 stack, SJI master, point at step 32: frames 0-15 put the map line on scan 0 steps 3, 7, …, 63 and frames 16-31 on scan 1 at the same steps (ties to the earlier exposure);
  - both overlays survive closing and reopening viewers; a saved WP3 session grows < 10 KB.

  Features: F125, F126. Findings: wp4-quicklook-8, archive-trace-9, followup-3-7, followup-3-2. Depends: wp4-slit-point-overlay, wp4-time-sync, wp1-m0-sji-crpix, wp3-session-budget.

**M3**

- [ ] **M3** `wp4-playback-extras`: The `wp4-time-controls` popup gains fps, a frame increment k, bounce and 'N frames around current'. Temporal blink (N ↔ N+k) reuses `wp5-m1-spectral-blink`; movie export is `wp12-sequence-export`. Done when, with explicit timer ticks on 4000255147 SJI 1400: bounce reverses at both ends; increment 3 steps by 3; the interval is 1000/fps ms; 'N = 10 around' sets [k−10, k+10], clipped; blink with k = 5 alternates N and N+5.

  Features: F086, F087, F119. Findings: wp3-wp5-13. Depends: wp4-time-controls, wp5-m1-spectral-blink.

**Notes and limits**

- **Selection geometry.** SJI overlays and SJI-click translation use the per-frame SJI WCS, never frame-0 pixel links. A master change overwrites hand-moved follower sliders by design. No SJI world-time link is added (D1), so time-dependent pixel-ROI reach is a documented limitation (followup-1-5).
- **Sessions.** M0 saves no coordination state; from M1 the coordinator reads `wp3-coordination-reattach`'s time-master and timing-step `meta` keys on creation. Overlays and markers are omitted from sessions and 'Save Python script', shown in 'Save plot', and redrawn on restore (D9).
- **Limits.** MDI windows do not reflow; a reference-data change resets slices (`_set_default_slices`; see the guide).
- **Upstream.** WP0 also tracks `wp0-irispy-v34-flip`. SJI/SJI links under #2595 (confirmed): amend #2595 to leave time axes out of autolinking; WP4 matching stays authoritative for time.

### WP5: Spectral units, rest wavelength, line list, blink and Doppler

D11 rest wavelengths, km/s views, line labels, CRISPEX-style blink and the Doppler wing-difference image, through public registries (D2), in `glue_solar/spectral.py` (new), `glue_solar/tools.py`, `glue_solar/data/iris_lines.csv` and `glue_solar/sources/loaders/iris.py`. No M0 work; each M1 item ships with its guide section and changelog.

**Port from prototypes** (under `IRIS_PLAN_PROTOTYPES/`)

- `iris_lines.csv`, `wp5_units.py`, `wp5_override.py` (:13-28), `wp5_linelist_mod.py` (without `brentq` and the exact-class style dict) and `wp5_blink.py` (without the toolbar spinbox). `wp5_label.py` is not ported (`wp0-core-profile-unit-label`).
- Tests: `review_20260905/test_line_positions.py` -> `glue_solar/tests/test_linelist.py`, adding a multi-axis session case (xfail until `wp0-core-profile-restore-priority`) and the layer-colour and float-rest checks of `archive/probes-2026-09/wp5_ll_session.py` (its km/s check waits for the `wp5-m1-velocity-axis` probe); `review_20260905/test_refresh.py::test_blink_close_restores_original_visibility` -> `glue_solar/tests/test_blink.py`.

**M1**

- [ ] **M1** `wp5-m1-line-list`: Ship `glue_solar/data/iris_lines.csv` with columns `wavelength` (vacuum Å), `name`, `source` (NIST ASD, CHIANTI or paper), `default_for` (a TDESC) and `calibration`.
  - Keep the 11 lines; add Fe XII 1349.40, Mg II 2791.60/2798.75/2798.82, O IV 1404.78, S IV 1404.81/1406.02, Ni I 2799.474, S I 1401.515; Fe XXI is 1354.106 (Young, Tian and Jaeggli 2015). Ni I, S I and O I 1355.598 are calibration lines.
  - `default_for`: Fe XII 1349 → 1349.40, Cl I 1352 → 1351.657, O I 1356 → 1355.598, Si IV 1394 → 1393.755, Si IV 1403 → 1402.770, Mg II k 2796 → 2796.352 and 2803.53; C II 1336 none.
  - `LineListArtist` draws on Profile viewers via `layer_artist_maker` (glue/config.py:807@1.27.0) with the stock style editor (no `_layer_style_widget_cls` patch; probe 2026-09-27). In WCSAxes mode it inverts the trace with `np.interp`, omitting markers off the trace or on a non-monotonic one.
  - 'IRIS: Add line list' (`menubar_plugin`) adds the list once as a plain Data to the active Profile viewer.

  Done when:
  - On ~/DATA/IRIS 20180102 3610108077 Mg II k (2790.65–2809.95 Å), labels for 2796.352, 2803.53, 2791.60, 2798.75 and 2798.82 sit within 1 display pixel in Å and nm; Fe XII 1349.40 appears in the 4000005156 Fe XII 1349 window.
  - Labels follow unit, visibility, colour and linewidth, vanish for a non-spectral x, and go with their callbacks when the layer is removed. A stock layer added afterwards keeps its style editor.
  - Ported tests pass for both cdelt signs; the list round-trips through stock serializers (no new saver); the CSV is in the wheel. On core #2601 + Qt #70 source exports (the `wp0-stack-validation` roots), the WCSAxes branch must also pass: markers at pixel positions, following a slice change to (2, 0), for both cdelt signs and after a session restore. On 1.27.0 that branch does not run, so record that run's result here.

  Features: F151. Findings: wp3-wp5-9, followup-3-14, wp3-wp5-15, wp3-wp5-17, wp3-wp5-12, core-qt-capabilities-4, upstream-state-6.

- [ ] **M1** `wp5-m1-rest-wavelength-policy`: Implement D11 as one helper in `glue_solar/spectral.py`, the only rest source for WP2, WP4, WP6 and WP11. It returns `meta.get('rest_wavelength')` (a float in Å) or None and never reads SGMeta or TWAVE (irispy's `SGMeta.rest_wavelength` attribute is TWAVE in nm). A second function returns the packaged lines inside the window, the `default_for` pre-selection and an ambiguity flag (more than one candidate); the WP2 moments and WP6 fit dialogs reuse it.
  - This item owns the loader write of `meta['spectral_window']` (the TDESC) on every raster window and stack. `wp3-plain-meta` tests that it, `rest_wavelength` and `rest_wavelength_source` survive sessions.
  - The loader writes `rest_wavelength` and `rest_wavelength_source` 'line list' only when exactly one row with that `default_for` lies in the window.
  - 'Set rest wavelength…' (`layer_action`) shows value, source and `LEVEL2_CAVEAT` (velocities relative to the uncorrected Level-2 scale, good to about 5–10 km/s; ITN 26 §5.1, ITN 38 §4.2), a constant in `glue_solar/spectral.py`. Derived products store it as `meta['velocity_caveat']` (the `wp5-m1-doppler-image` helper; WP2, WP6).
  - The dialog lists in-window lines, pre-selects the first `default_for` candidate (never TWAVE 2796.20) and accepts a free Å value. A listed line is source 'user choice', a typed one 'override'; 'Reset to default' restores the default or deletes both keys. Writes broadcast `NumericalDataChangedMessage`. Windows with no packaged line are refused.

  Done when:
  - A test over every window of ~/DATA/IRIS 20130902 4000005156 finds exactly the `default_for` value above or no key; a 4000005156 stack takes scan 0's window.
  - On 20140708 3824262996 the Mg II k 2796 window (2792.98–2806.63 Å, contains h) has no key after load.
  - There the candidate function and the dialog pre-select 2796.352 and offer 2803.53, 2798.75, 2798.82 and 2799.474, with the ambiguity flag set; confirming k stores 2796.352 as 'user choice'; Reset removes both keys.
  - C II 1336 has no key and its dialog offers 1334.53 and 1335.71. For 2832 there are no candidates and the action is refused with a message, changing nothing.

  Features: F146. Findings: wp3-wp5-1, wp2-wp6-science-1, archive-trace-4, wp3-wp5-4, archive-trace-3, wp2-wp6-science-16, archive-trace-13, wp3-wp5-12, wp3-wp5-10, wp2-wp6-science-11. Depends: wp5-m1-line-list.

- [ ] **M1** `wp5-m1-velocity-axis`: In `setup()`, replace `unit_converter.members['default']` with a `SimpleAstropyUnitConverter` subclass adding 'km / s' (`u.doppler_optical(rest)`) to `list(super().equivalent_units(...))` only for the spectral world component and for `centroid` of data with a rest; never for widths (`sigma`, whose velocity form is `sigma_velocity`).
  - Probe for glue-qt #70: `ProfileTools._get_axis_and_pixel_slice` on a tiny Data with x in nm; any exception fails. Until it passes, km/s is withheld from world coordinate components but not from value components such as `centroid`.
  - A Profile tool in `glue_solar/tools.py`, added to `ProfileViewer.tools` in `setup()` (`solar:frame_time` pattern), draws a top axis 'v [km/s], Level-2 λ scale' (`Axes.secondary_xaxis`) when x is spectral with a rest, sets `state.x_axislabel` to '<label> [<unit>]', and on `NumericalDataChangedMessage` calls the private `ProfileViewerState._update_x_display_unit_choices`. The gate and this call are `wp0-workaround-register` rows.

  Done when:
  - On 3824262996 Mg II k with rest 2796.352 the top axis reads 0 km/s at 2796.352 Å through zoom, pan and bottom units Å and nm; it is absent for a non-spectral x, a km/s bottom axis or no rest; the x label shows the unit.
  - In an open C II 1336 Profile, setting 1334.53 adds the top axis and Reset removes it, without exception.
  - On glue-qt 0.4.2 the probe fails and Profile x choices lack km/s. A Data with an Å `centroid` and `rest_wavelength` offers km/s as an Image colour unit; without the key it does not. A WP2/WP6 map with `rest_wavelength` offers km/s for `centroid` but not for `sigma`.
  - A non-IRIS 'm' component still offers glue's 131 length units and 'rad' still offers 'mas'. `settings.UNIT_CONVERTER` stays 'default'; nothing is written to settings.cfg. A saved IRIS Profile in Å reopens with its top axis.
  - Once the probe passes: km/s appears in the open C II Profile's x choices after the override, and Reset falls back to Å; km/s x-range selection and Collapse pick the same slices as in Å; line-list labels sit within 1 display pixel in km/s; a saved multi-axis IRIS Profile in km/s reopens (today ValueError, wp3-wp5-2).

  Features: F147. Findings: usefulness-6, wp3-wp5-6, archive-trace-8, wp3-wp5-2, wp3-wp5-10. Depends: wp5-m1-rest-wavelength-policy, wp1-m1-wrapper-coherence, wp0-core-profile-restore-priority.

- [ ] **M1** `wp5-m1-spectral-blink`: A checkable Image `viewer_tool` in `glue_solar/tools.py`, registered idempotently, alternates two (dataset, wavelength index) positions in one viewer.
  - Same-cube blink changes only slices, with shared colour limits by default (optionally each plane's own 99.5 percentile). Cross-window blink alternates windows sharing the step×slit grid via WP4 pixel-identity links with per-position limits, setting `reference_data`, x_att, y_att and slices in one `delay_callback`, then restoring zoom.
  - Partner, interval (0.3–2 s, default 0.5 s) and limit mode sit in a panel shown only while active (0.4.2 never attaches `menu_actions()` to a CheckableTool); stopping or closing the viewer restores reference data, slices, limits and visibility.

  Done when, on 4000005156 scan 0:
  - Mg II k index 93 against wing index j alternates the displayed array exactly between `cube[:, :, 93]` and `cube[:, :, j]`, with identical v_min/v_max by default.
  - Si IV 1403 index 286 against Mg II k 93 alternates reference data and slices; arrays match each map, the Pixel crosshair keeps its (step, slit), x/y limits are restored, and switch plus draw takes ≤0.25 s.
  - Scan slice and point survive 20 flips; stopping restores the originals; closing stops the timer without exceptions; inactive viewers get no extra toolbar widget.

  Features: F076. Findings: usefulness-14, followup-3-6, wp3-wp5-13, wp3-wp5-16, followup-3-12. Depends: wp4-m1-multi-window, wp4-quicklook-preset.

- [ ] **M1** `wp5-m1-doppler-image`: A D4 'Doppler image…' `layer_action` for a raster window or stack with rest λ0 (else refused with a message).
  - It adds one Data with planes D(λ) = I(λ) − I(2λ0 − λ) for λ ≥ λ0 whose mirror is in the window (CRISPEX lp_dop, crispex.pro:21000-21002); I(2λ0 − λ) is linearly interpolated and NaN if either neighbour is.
  - Coords `_GlueWCS(SlicedLowLevelWCS(raw_wcs, (..., slice(k0, k1))))` (the WP3 derived-map contract) keep the axis in Å; the ±50 km/s map is the plane nearest λ0(1 + 50/c).
  - Sign red minus blue (D16), named in component `I(red)-I(blue)` and `meta['doppler_sign']`.
  - It owns the derived-product helper that `wp2-m2-moment-maps` and `wp6-m2-products` reuse: add the Data, copy `rest_wavelength`, `rest_wavelength_source` and window meta, add a broadcast `Time`, write `meta['velocity_caveat']`, add WP4 pixel-identity links on the spatial axes, open no viewer.

  Done when:
  - A synthetic line shifted +10 km/s gives D > 0 near +10 km/s; an unshifted symmetric line with λ0 on a pixel centre gives D = 0 within 1e-6.
  - On ~/DATA/IRIS 20180102 3610108077 Mg II k with rest 2796.352 Å ('user choice'), every plane equals an `np.interp` reference to float32 precision; fill and masked samples are NaN. The WP11 readout on the plane nearest +50 km/s shows 50 km/s within half a pixel (about 1.4 km/s).
  - A Pixel click on the map shows the source spectrum at the same (step, slit) and moves the source panels' fixed indices. The product survives a WP3 save and reopen.

  Features: F148, F149, F152. Findings: wp3-wp5-11, wp2-wp6-science-5. Depends: wp5-m1-rest-wavelength-policy, wp10-fill-nan, wp10-m0-negative-step, wp4-m1-multi-window, wp11-cursor-readout, wp3-wcs-saver.

**M3**

- [ ] **M3** `wp5-m3-rest-from-measurement`: 'Use displayed wavelength' in the rest dialog stores the active Image slice wavelength as 'override'; the guide says it is not a laboratory rest.
  - Document the ITN 26 §5.1 / ITN 38 §4.2 check: fit O I 1355.598 (ITN 26) or S I 1401.515 (P. Young) with the stock Profile Fit tool, then enter rest + (λ_fit − λ_lab). The Ni I 2799.474 recipe waits for WP6 (Gaussian1D has no baseline).
  - The irispy request for per-exposure orbital and thermal drift correction (`iris_prep_wavecorr_l2`; irispy 0.9.0 has only 'orbital phase' meta) is `wp0-irispy-requests` item (1), `irispy-wavecorr`.

  Done when:
  - On 4000005156 scan 0 a test fits O I 1355.598 in the O I 1356 window (1354.85–1356.33 Å) with the stock Gaussian fitter; entering the corrected rest moves the top axis's zero by c·Δλ/λ.
  - 'Use displayed wavelength' stores the slice wavelength as 'override'. The recipe page builds with Sphinx -W. WP0 records the request's URL or the user's decision not to file it.

  Features: F150, F167, F168. Findings: wp3-wp5-10, wp2-wp6-science-11. Depends: wp5-m1-rest-wavelength-policy, wp5-m1-velocity-axis, wp0-irispy-requests.

- [ ] **M3** `wp5-m3-reference-blink`: Extend blink to SJI against SJI or an aligned AIA cutout, taking the partner frame from `wp4-time-sync` each flip so it runs during playback.
  - A 2-D link_hpc reference blinks by layer visibility, re-read each tick. A 3-D partner has no time link (D1), so it uses the M1 reference-data switch with zoom mapped through both WCS (prototype this first). Optional normalisation gives each stream its own limits without copying data.

  Done when:
  - On the irispy 20210905 sit-and-stare fixture (SJI_1400 against SJI_2796) the streams alternate at the set interval during playback; the same runs on a 3640107442 SJI against its AIA 1600 cutout once that SJI is local.
  - In both, the streams show the same region within 1 SJI pixel and `solar:frame_time` names the visible stream's time. With normalisation, each stream's v_min/v_max is its own 99.5 percentile. Stopping restores visibility and limits.

  Features: F110. Findings: wp3-wp5-16. Depends: wp5-m1-spectral-blink, wp4-time-sync, wp4-context-reference.

- [ ] **M3** `wp5-m3-mean-spectrum-compare`: 'Subtract mean spectrum' (`layer_action`) adds flux − mean[λ pixel] to a raster window or stack (mean: 1-D nanmean over space and scans, fill excluded), computed lazily by a ComponentLink subclass whose `__gluestate__`/`__setgluestate__` (D13 pattern) save the flux and wavelength-pixel component references and the mean (a list; a closure cannot be saved). 'Scale to maximum of average' is documented as Profile Normalize with per-layer limits.

  Done when:
  - On 4000005156 scan 0 Si IV 1403, the component's Pixel-subset Profile equals `cube[s, y, :] − nanmean(cube over step and slit, fill excluded)` within 1e-6; no cube-sized array is stored.
  - It is correct in an image slice and on a 4-D stack, and survives a WP3 save and restore still derived.

  Features: F079. Depends: wp10-fill-nan, wp3-app-session-acceptance.

**Notes and limits**

- Mg II and C II velocities are optically thick proxies. km/s as a Profile x unit waits for glue-qt #70 (on 0.4.2 any non-native x unit, nm included, makes Navigate and Collapse hit slice 28 instead of 20); until then km/s is on the top axis, in the WP11 readout and in product meta. Image-axis velocity and annotation frameworks are out of scope; sliders show wavelength.
- The Doppler product keeps an Å axis (the WP3 contract, wp3-wp5-3, not wp3-wp5-11's km/s), ignores the source map's wavelength (part of the F148 gap), is float32 with at most half the source planes, and embeds its array in sessions.
- Blink scope: frame sub-ranges and Go-to-UTC are `wp4-time-controls` (M1); temporal blink N↔N+k, bounce/CYCLE, fps (also below 2) and frame increment are `wp4-playback-extras` (M3; F086, F087 'could'); the raster timing offset is `wp4-time-sync` (M0).
- Upstream line layers (glue #2603 / glue-qt #73, `wp0-track-line-layers`) would replace `LineListArtist`. Pyoung's 91-line CHIANTI table is not adopted (licence unchecked).

### WP6: Gaussian fit maps

WP6 adds Gaussian fit maps of IRIS raster windows (a D4 `layer_action`: one linked map dataset, no viewer) and Profile Fit tab fitters in `glue_solar/sources/fitting.py` (new, registered from `setup()`). There is no M0 or M1 work.

**Port from prototypes**

- `IRIS_PLAN_PROTOTYPES/wp6_fitting.py` → `glue_solar/sources/fitting.py`: the single-Gaussian path (`fit_gaussians_action`, `start_fit` with `_WORKERS` and the progress-dialog reference, and their helpers), fixed as the M2 checkboxes say.
- `IRIS_PLAN_PROTOTYPES/wp6_test_fitting.py` → `glue_solar/tests/test_fitting.py`: all 7 test functions (8 collected items), with `find_irispy_test_file`, a window of at least ±2 Å and updated residual and masked-sample asserts, plus the two `worker.progress.isVisible()` asserts of `wp6_test_fitting_final.py`, which is then archived. Its two double-Gaussian tests wait for M3.
- `IRIS_PLAN_PROTOTYPES/review_20260905/test_plan_integration.py` → `glue_solar/tests/test_sessions.py`, after `wp3-wcs-saver`: only `test_wp3_roundtrips_wp6_fitted_map`, importing `glue_solar.sources.fitting` without `import wp3_impl` or the `module_name` parametrize (D13, usefulness-7). Add no WP2 moments variant: WP2's own round trip (`wp2-m2-tests-docs`) and `wp3-wcs-saver`'s sliced -TAB case cover it. Drop the stubbed quicklook (wp4-quicklook-15) and WP8 `.ui` tests.
- Keep `IRIS_PLAN_PROTOTYPES/wp6_chk_real_fixed.{py,log}` (the only 4-D stack fit) until the 4-D test lands, and `wp6_full_raster.{py,log}` beside it as the `wp6-m2-worker` baseline.

**M2**

- [ ] **M2** `wp6-m2-fit-maps`: D4 `layer_action` 'IRIS: Gaussian fit maps…' fitting the shared Gaussian + constant model (`wp6-m2-profile-fitter`) with `LMLSQFitter` through astropy `parallel_fit_dask`. Flux defaults to WP1's '<flux> DN/s', else the first main component. Fit only inside a window taken from the reusable WP2 rest/wings widget (`wp2-m2-line-definition`), whose line choice comes from WP5's candidate list; the default is the WP5 rest ± 0.5 Å. Without a rest, the user enters the window and velocities are off, with a message.
  - Masking (D10, followup-4-2): after `wp10-fill-nan` missing samples are NaN, so `mask = ~isfinite(window)` with no irispy mask term; `window[mask] = 0`, pass `mask=` (a NaN under a zero weight NaNs the fit); no clip or `nan_to_num`. Spectra with valid samples ≤ free parameters get NaN.
  - Seed the centre at the maximum of the in-window NaN-ignoring mean spectrum (`nanmean` over spectra, then argmax), or at an optional in-window seed centre; never TWAVE; no mean-spectrum prefit.
  - Outputs `background`, `amplitude`, `centroid`, `sigma` (Å, 1σ; FWHM = 2.355σ), plus `velocity` and `sigma_velocity` (km/s, optical) when a WP5 rest is known.
  - Mg II h/k and C II windows (`meta['spectral_window']`) get the `line_regime` proxy meta shared with WP2 and a dialog warning.

  Done when:
  - a noisy (peak SNR 50), zero-background synthetic cube with partly missing spectra (gaps on the line flank) gives finite fits for them, amplitude and sigma within 5% and centroid within 0.005 Å of the truth; the old clip + `nan_to_num` misses them (proposed);
  - on `~/DATA/IRIS` 20180102 3610108077 Si IV 1403, no fully masked spectrum gets a finite fit (today 1687/1687 do);
  - `velocity` equals the WP5 conversion of `centroid`;
  - on that raster's Mg II k window, which has no rest key under D11, the dialog asks for the line and pre-selects 2796.352 Å (never TWAVE 2796.20), and the default-window fit gives |median centroid − 2796.352 Å| ≤ 0.01 Å (proposed, unverified);
  - a local run fits Si IV 1403 (which includes O IV) with and without the window; both complete and the test prints the median Si IV centroid shift.

  Features: F157. Findings: wp2-wp6-science-3, wp2-wp6-science-7, wp2-wp6-science-8, wp2-wp6-science-6, wp2-wp6-science-9, wp2-wp6-science-13. Depends: wp2-m2-line-definition, wp5-m1-rest-wavelength-policy, wp10-fill-nan, wp1-dn-per-s (soft: the default falls back to DN).
- [ ] **M2** `wp6-m2-quality-filter`: Publish |sigma| where amplitude > 0 (the model uses sigma²). NaN fits with amplitude ≤ 0 or sigma = 0, a centroid outside the window, status ≤ 0 (`fit_info=('status',)`, read by `fit_info.get_property_as_array('status')`), or saturation by the `wp2-m2-input-quality` check on the raw DN (any +Inf sample or a peak above the DN limit inside the window), warning with NSATPIX/TSATPXn when either is above 0.

  Done when: on `~/DATA/IRIS` 20180102 3610108077 Si IV 1403 (unfiltered today: sigma < 0 6.0%, amplitude < 0 11.2%) the maps contain no amplitude ≤ 0, sigma ≤ 0 or out-of-window centroid; synthetic spectra with one +Inf sample, or a peak above the DN limit, are NaN in every map; the rejected fraction (spectra NaN'd by this filter, saturated included / spectra fitted) is in the map meta and the completion message.

  Features: none. Findings: wp2-wp6-science-4, wp2-wp6-science-8. Depends: wp6-m2-fit-maps, wp2-m2-input-quality.
- [ ] **M2** `wp6-m2-products`: One new `Data` holds the maps of a 3D raster or 4D stack: coords `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))` (irispy's rebuilt WCS or an outer sliced wrapper breaks session save); one `LinkSame` pixel link per non-spectral axis (the helper's spatial links, plus the scan-axis link for 4D stacks); the source `Time`, the window meta and the rest keys, all added through WP5's derived-product helper (`wp5-m1-doppler-image`); no viewer. The residual is opt-in (float32, source shape, on the source).

  Done when: a (13, 8, 109, 17) stack gives (13, 8, 109) maps with 3 links and a 3D raster gives 2 links; a default run adds no source component and an opted-in residual is float32; subsets propagate both ways between source and maps; fit products add at most 2× the 2-D map bytes to a saved session without the residual.

  Features: none. Findings: wp2-wp6-science-12, followup-2-4, wp2-wp6-science-15. Depends: wp6-m2-fit-maps; wp3-session-budget; wp5-m1-doppler-image.
- [ ] **M2** `wp6-m2-rest-key`: The fit map carries the rest used for `velocity` (window value or dialog choice) as `meta['rest_wavelength']` (float, Å), and no key when none was used. It also writes `rest_wavelength_source` and copies WP5's `LEVEL2_CAVEAT` (`wp5-m1-rest-wavelength-policy`) into `meta['velocity_caveat']`. A seed centre goes under `fit_seed_center`, never as a rest or `rest_wavelength_angstrom`.

  Done when: the WP5 helper returns the used rest and the Image viewer offers km/s for `centroid` through the WP5 converter; a seed-centre-only fit offers no km/s; the map meta carries `rest_wavelength_source` and `velocity_caveat` equal to `LEVEL2_CAVEAT`; `rest_wavelength` and `fit_seed_center` survive a WP3 round trip.

  Features: none. Findings: archive-trace-13, wp2-wp6-science-16. Depends: wp5-m1-rest-wavelength-policy.
- [ ] **M2** `wp6-m2-worker`: The main thread computes wavelengths (via `data.coords`), window indices and mask; a `glue_qt.utils.threading.Worker` runs only `parallel_fit_dask` on those arrays (`'processes'`; tests `'single-threaded'`), and the result slot builds maps and links on the main thread. While holding the WP10 module-level RLock, it takes its own `copy.deepcopy` of `coords._wcs` (WP2's helper refuses 4D stacks) and builds the `SlicedLowLevelWCS` on that copy, so no fit map shares an astropy WCS with its source. Keep references to Workers and the parentless progress dialog, show progress for the Worker's lifetime, offer no cancel, and on error show the traceback and publish nothing.

  Done when:
  - an action test (`_ask`, `QMessageBox` monkeypatched) adds the maps, with the progress dialog visible during the fit and hidden after;
  - a spy on the source `_GlueWCS` records no Worker-thread call;
  - a subprocess test building the maps while a second thread loops on the source's `pixel_to_world_values` exits 0 in 20 of 20 runs;
  - a full 2018 3610108077 window fit (320×548 spectra) meets the followup-2-8 WP6 budget, owned here: ≤ 60 s, GUI timer gaps ≤ 0.2 s, process-tree peak ≤ 12 GB (baseline 25.3 s).

  Features: none. Findings: followup-2-1, followup-2-8. Depends: wp6-m2-fit-maps; wp10-m0-wcs-lock (with the lock importable from `glue_solar/sources/loaders/iris.py`).
- [ ] **M2** `wp6-m2-profile-fitter`: Define the shared unbounded named-parameter `custom_model`s `background, amplitude, mean, stddev` (per pixel) and `background, amplitude_1, mean_1, stddev_1, amplitude_2, mean_2, stddev_2`, not `Const1D + Gaussian1D` (glue builds `model_cls(**params)`). In `setup()`, register 'Gaussian + constant' and 'Two Gaussians + constant' through glue's `fit_plugin` registry as `AstropyFitter1D` subclasses (`fitting_cls = LevMarLSQFitter`; `parameter_guesses` from finite samples), so the stock Fit tab fits Pixel-point or ROI-mean spectra (iris_sum_spec + spec_gauss_iris). The Fit tab passes no dy: the fitter drops non-finite samples and the fit is documented as unweighted. Rescale x only if the metre check below fails after `wp10-fill-nan` (today the fixture's 35,027/216,920 −200 samples make even the Å fit diverge, stddev 205 Å).

  Done when:
  - both fitters appear in the Fit tab and fit with no warning under `filterwarnings = error`;
  - 'Gaussian + constant' Fit-tab fits of a Pixel-point and an ROI-mean spectrum (Profile function Mean, not the default Maximum), on the irispy 20210905 fixture and the Si IV 1403 core of `~/DATA/IRIS` 20180102 3610108077 in Å and m display (m converted to Å) match a direct Å fit of the same finite samples, model, fitter class and seeds to 1e-6 relative (proposed);
  - 'Two Gaussians + constant' recovers both components of a synthetic two-line spectrum;
  - the user guide has the recipe (ROI, Mean, zoom to 2794-2799 Å, fit) and calls two-Gaussian Mg II or C II fits proxies.

  Features: F161. Findings: followup-3-3, wp2-wp6-science-6. Depends: wp10-fill-nan.
- [ ] **M2** `wp6-m2-tests`: Port the suite to `glue_solar/tests/test_fitting.py`: the synthetic, 4D, subset, residual and Worker/WCS-lock checks of the M2 items, plus noiseless recovery (amplitude and sigma rtol 1e-4, centroid rtol 1e-6), NaN for valid samples ≤ free parameters, irispy raster shapes and units (±2 Å window) and SJI rejection. Port `test_wp3_roundtrips_wp6_fitted_map` to `glue_solar/tests/test_sessions.py`. Real-fixture finite/NaN checks are regressions only (the 0.9.0 fixtures are 10×-decimated); physical checks use synthetic cubes and `~/DATA/IRIS`. Reference fits use the same unbounded model, never a bounded `Gaussian1D` with `LMLSQFitter`.

  Done when the suite passes in `iris-plan` (D5 baseline, astropy 8.0.1) under `filterwarnings = error`, and the WP3 round trip restores the fit maps' values, links and `rest_wavelength`.

  Features: none. Findings: wp2-wp6-science-15, wp2-wp6-science-17, wp3-wp5-3, usefulness-7. Depends: wp6-m2-fit-maps, wp6-m2-products; wp3-wcs-saver (session test).
- [ ] **M2** `wp6-m2-docs`: A `docs/user_guide/` page, a `docs/api_reference.rst` entry and a `changelog/` fragment. The page covers the fit window, masking and the valid-sample minimum; 1σ sigma (FWHM = 2.355σ); the rejected fraction, saturation included; the unweighted fit and its unit (DN/s by default); Mg II/C II proxies versus thin lines (Si IV, O IV, Fe XII, Fe XXI, O I); `LEVEL2_CAVEAT`; and that the maps are not calibrated. It claims session support only after the `wp6-m2-tests` round trip passes.

  Done when Sphinx builds with `-W`, the API page lists `glue_solar.sources.fitting`, and the page walks one Si IV fit from the right-click action to a km/s centroid map.

  Features: none. Findings: wp2-wp6-science-3, wp2-wp6-science-6. Depends: wp6-m2-fit-maps.

**M3**

- [ ] **M3** `wp6-m3-rba-double-gaussian`: Both parts run in the Worker on main-thread data from WP2's rewrap helper. A D4 'Red-blue asymmetry…' action wraps `irispy.utils.red_blue.calculate_red_blue_asymmetry` (@0.9.0), always passing the WP5 policy rest (irispy falls back to TWAVE on `None`, which D11 forbids) and `return_profiles=False`, with `continuum_windows` and an 'IDL iris_xfiles' preset (5-100 km/s steps, 30-50 km/s summed) beside irispy's default (50-150 km/s, dv 10 km/s); the RB map and its quality flags form one linked dataset. The fit action gains the two-Gaussian model, labelled 'Mg II k2v/k2r proxy', seeded from rest ± 0.15 Å or the two highest interior maxima of the mean valid spectrum, and used only where |RB| exceeds a dialog threshold (default 0.1, proposed, unverified). uint8 `rb_mask` records the choice (1 and 0 get the single Gaussian).

  Done when: on `~/DATA/IRIS` 20180102 3610108077 Mg II k the RB map equals a direct irispy call with the same parameters and an explicit rest; a window without a policy rest adds nothing and says why; the IDL preset changes only the velocity grid; `rb_mask` is 2 exactly where |RB| exceeds the threshold, 1 where it does not and 0 where RB is not finite; the prototype's double-Gaussian tests pass; an error publishes nothing partial.

  Features: F158. Findings: wp2-wp6-science-6. Depends: wp6-m2-fit-maps, wp6-m2-worker, wp5-m1-rest-wavelength-policy, wp2-m2-moment-maps (rewrap helper).
- [ ] **M3** `wp6-m3-template-fits`: N-component Gaussian + constant templates seeded from the in-window WP5 line list (Si IV 1403: O IV 1399.77/1401.16, Si IV 1402.77). With WP2's uncertainties loaded, weight by 1/σ (`parallel_fit_dask(weights=...)`, `weights[mask] = 0`) and publish 1σ errors (`amplitude_error`, `centroid_error`, `sigma_error`, `velocity_error`; IDL Ierr/Verr) from `fit_info=('status', 'param_cov')` with `calc_uncertainties=True`. The maps, opt-in residual, a Pixel point and `wp6-m2-profile-fitter` replace iris_fit_viewer. No EIS/SSW dependency.

  Done when: a synthetic 3-line window recovers each component; with uncertainties loaded, the maps equal a direct `parallel_fit_dask(weights=1/σ)` call with the same model, window and mask to rtol 1e-6, and the error maps equal its √diag(param_cov); on the real Si IV 1403 window, high-SNR O IV and Si IV centroids fall within ±0.1 Å of the list values (unverified).

  Features: F159. Depends: wp6-m2-fit-maps, wp5-m1-line-list, wp2-m3-window-data.

**Notes and limits**

- Net-flux maps and `parallel_fit_dask` diagnostics files stay out (net flux = √(2π)·amplitude·sigma via glue's Arithmetic attributes).
- No new dependency (dask comes with irispy-lmsal). `parallel_fit_dask` swallows per-pixel warnings, deprecations included, so `filterwarnings = error` never sees them; astropy 8.0.1 deprecates `LMLSQFitter` on bounded models (`Gaussian1D`'s stddev bound), hence the unbounded model. A fitter reused after `fit_info=` raises `KeyError: '__deepcopy__'`; create one per call.
- Timings are machine-specific, not CI thresholds; the `wp6-m2-worker` budget stays proposed (followup-2-8) until measured.
- Level-2 saturation is the kept int16 top code (about 16182 DN), hence the DN-limit check; the +Inf path (ITN 26) is tested only synthetically, as all local files show NSATPIX = 0.

### WP7: GOES and SDO context

Goal: on request, add GOES XRS and SDO/AIA pointing context to a loaded IRIS observation with glue's own viewers, `link_hpc` and `Time` links. Code: `glue_solar/sources/context.py` (new), `glue_solar/glue_patches.py`, `glue_solar/tests/test_context.py`. Each WP7 PR carries its own user-guide section and changelog fragment (the WP9 rule). `wp7-aia-context` documents when a fetch beats local LMSAL `aia_l2` cutouts (none loaded, or full-disk context wanted), that the action sees only loaded cutouts, and the first-exposure FOV limit. `wp7-goes-context` documents that GOES 8-15 curves are unscaled science data while SWPC/HEK classes use the old scale (X1.0 ≈ 1.4e-4 W/m² on the curve). No M0 or M1 work.

**Port from prototypes**

- `IRIS_PLAN_PROTOTYPES/wp7chk/context_chk.py` and `test_context.py` → `glue_solar/sources/context.py` and `glue_solar/tests/test_context.py`: all functions, both menubar plugins and the ten mocked tests (not `conftest.py`), with the checkbox fixes. Repair the 6 tests irispy 0.9.0 broke: use `find_irispy_test_file`; expected footprints from an astropy WCS built from the header (SJI/AIA: CRPIX, CDELT, XCENIX/YCENIX, PCi_jIX; raster/stack: window extension header at step 0), never `to_maps(0)` or pinned numbers. SJI/AIA agree to 0.05 px only with `wp1-m0-sji-crpix` active (followup-4-3).
- `IRIS_PLAN_PROTOTYPES/archive/probes-2026-09/wp7_timelink.py` and `wp7_goes.py` → the GOES success-path test (wp7-wp8-8): viewer, log-axis and time-link recipe only, not the `EPOCH=1` path.
- `IRIS_PLAN_PROTOTYPES/wp0_bug_epoch_viewer.py` → the 1.27.0 assertion of `wp7-goes-date-labels`; archive it after.

**M2**

- [ ] **M2** `wp7-context-port`: Menubar actions 'IRIS: GOES context…' and 'IRIS: SDO context…', imported by `glue_solar.setup()`; `pyproject.toml` moves to `sunpy[map,net,timeseries]`. Each opens one confirm dialog listing IRIS datasets only (not loaded `aia_l2` cutouts); OK is consent to go online. Footprints are computed on the GUI thread; search, download, file reads and AIA processing run in glue-qt's `Worker`, reusing the lifecycle of `wp10-nonblocking-load` (a stale result is discarded by id, with no GUI-thread `wait()`); Data, links, subsets and viewers are made in its result slot. Errors become message boxes.
  Done when:
  - Cancel makes no network call (Fido, HEK or HCR); a mocked network error shows a message and changes no datasets or links.
  - A 50 ms QTimer sees no gap above 0.2 s during a mocked 2 s download; closing the app during that download adds nothing and raises nothing.
  - Imports raise no warnings on `iris-plan`; the ported tests pass on irispy 0.9.0, including SJI, raster and stack footprints against the header-WCS oracle and the non-spatial-dataset error.

  Features: none (shared plumbing). Findings: wp7-wp8-9. Depends: wp1-m0-link-hpc, wp1-m0-sji-crpix, wp10-nonblocking-load.
- [ ] **M2** `wp7-goes-context`: `goes_xrs` fetches 1-minute XRS for STARTOBS–ENDOBS from one satellite. Satellite choice (confirmed): auto (lowest-numbered covering the whole interval, else longest coverage, named in the message) or one chosen in the dialog. Non-zero `xrsa_quality`/`xrsb_quality` samples become NaN (wp7-wp8-5); data are truncated to the interval in `W / m2`, with a datetime64 `time` added last, in a Scatter viewer with `y_log=True`. GOES `time` gets `LinkSame` to the `Time` of every loaded dataset of the observation, never a pixel ID or SJI 'Time (Utc)' (D1, D8).
  Done when:
  - Mocked `Fido` returns int64 `SatelliteNumber` [15, 13], both covering, one flagged row: satellite 13 is fetched and the flagged sample is NaN. With satellite 15 chosen in the dialog, satellite 15 is fetched. In both cases `xrsa`/`xrsb` carry unit 'W / m2' and every `time` lies within STARTOBS–ENDOBS.
  - Mocked, none covers the whole interval: the longest-coverage satellite is fetched and named.
  - `y_log` is True; a GOES time-range subset with datetime64 bounds selects the matching SJI frames and raster steps.
  - `wp1-m0-link-graph-regression` passes with GOES linked, its allowed set extended by the `time`↔`Time` main-component `LinkSame` links; no link targets a pixel ID or 'Time (Utc)'.
  - Manual live fetch recorded for 20140329 OBSID 3860258481 (14:09–17:54 UTC): the X1.0 flare in xrsb peaks near 17:48 UTC at about 1.4e-4 W/m².

  Features: none (F044 is completed in wp7-goes-marker). Findings: wp7-wp8-5, wp7-wp8-6, wp7-wp8-8. Depends: wp7-context-port, wp1-m0-axis-names, wp1-m0-link-graph-regression.
- [ ] **M2** `wp7-goes-marker`: A `solar:time_marker` tool appended to `ScatterViewer.tools` in `setup()` (D9). With a datetime `x_att` it draws an `axvspan` over the WP4 master exposure (start to start + `Exposure time`) and redraws on master-slice changes. It converts times with `glue.utils.matplotlib.datetime64_to_mpl` looked up at call time (never a by-name import), so it uses the same function as the Scatter layer.
  Done when:
  - With the raster master (D7 default) and with an SJI master, moving the master slider moves the span to `datetime64_to_mpl(master start)`…start + `Exposure time`.
  - With the #2599 port active on 1.27.0, the span lies inside `axes.get_xlim()` and over the GOES samples at the master time.
  - On a Scatter viewer with a datetime x and no GOES data loaded (for example WP12 light curves), the span still follows the master through the coordinator's master-time notices (`wp4-time-sync`).
  - A session with GOES and its `Time` links reopens with `y_log` True and the span redrawn.

  Features: F044. Depends: wp7-goes-context, wp7-goes-date-labels, wp4-time-sync, wp4-exposure-readout, wp3-app-session-acceptance.
- [ ] **M2** `wp7-goes-date-labels`: Until a glue-core release contains #2599, `glue_solar/glue_patches.py` installs a port of #2599's `datetime64_to_mpl`/`mpl_to_datetime64` (epoch from `matplotlib.dates.get_epoch()`), rebound in `glue.utils.matplotlib`, `glue.utils` and the by-name importers `glue.viewers.{scatter.layer_artist, scatter.viewer, matplotlib.viewer, histogram.state, histogram.viewer}`, only when a probe finds `datetime64_to_mpl(t) != matplotlib.dates.date2num(t)` (D2). It never sets `rcParams['date.epoch']`.
  Done when:
  - On 1.27.0 the mocked 2021-09-05 GOES ticks show 2021 (3990 without the port); `state.x_min`/`x_max` are 2021 datetime64 values.
  - An xrange ROI over 00:20–00:30 gives subset bounds in that range.
  - On the `wp0-stack-validation` environment (has #2599) the probe is False and nothing is rebound.

  Features: none. Findings: wp7-wp8-7. Depends: wp1-m0-inverse-workaround (adds `glue_solar/glue_patches.py`) and its `wp0-workaround-register` row ('Datetime epoch port (WP7)'). Removed through `wp0-release-tracking`.
- [ ] **M2** `wp7-aia-context`: One VSO download of the AIA 171 image nearest STARTOBS (one JSOC file, about 65 MiB) gives a full-disk locator resampled to about 1024 px and an FOV crop (confirmed). The crop is the first-exposure footprint plus a margin set in the dialog, default 100 arcsec. The crop is offered only when no same-observation (`_observation_label`) `aia_l2` cutout is loaded, not when cutouts merely exist on disk; the action does not scan disk. This narrows the agreed "no local cutouts exist" rule (confirmed). The dialog then points to the browser's AIA rows. Corners are transformed inside `propagate_with_solar_surface(), SphericalScreen(iris_observer, only_off_disk=True)`, IRIS observer at Earth at STARTOBS (wp7-wp8-1). Views go through `_parse_sunpy_map` (D3), link with `link_hpc`, and carry a pixel `PolygonalROI` FOV subset, not `RegionData` (#2600).
  Done when (mocked unless stated):
  - An off-limb FOV (corners near Tx 1000″) against an AIA frame with an SDO observer and obstime 5 s later crops without NaN or ValueError.
  - The locator is an uncropped map resampled to about 1024 px, and its FOV subset covers the IRIS footprint.
  - With an `aia_l2` cutout and an IRIS dataset with OBSID and STARTOBS copied from the 3640107442 headers, no crop is offered and only the locator is made.
  - A session with locator, crop, their `link_hpc` links and the FOV subset reopens intact.
  - Manual live fetch recorded for local 20130902 OBSID 4000255147 (SJI 1400), network path forced.

  Features: F046. Findings: wp7-wp8-1, wp7-wp8-9, upstream-state-7. Depends: wp7-context-port, wp1-m0-link-hpc, wp1-m0-sji-crpix, wp1-m1-sunpy-maps, wp3-app-session-acceptance.

**M3**

- [ ] **M3** `wp7-flare-list`: 'IRIS: SWPC flares…' (same confirm dialog) queries `sunpy.net.hek.HEKClient` for SWPC flares in the interval into a Data (start, peak, end, GOES class, location) in a Table viewer, plus one time-range subset per flare on a loaded GOES `time`. No events: 'No SWPC flares for this period', nothing added.
  Done when:
  - A mocked HEK response gives rows with class and peak time plus the subsets; a network error shows a message and adds nothing.
  - Manual live check for 20140329 OBSID 3860258481 lists the X1.0 flare peaking near 17:48 UTC.

  Features: F045. Depends: wp7-context-port, wp7-goes-context (for the subsets).
- [ ] **M3** `wp7-hcr-metadata`: Menubar action 'IRIS: HCR metadata…' (same confirm dialog). After OK it queries `https://www.lmsal.com/hek/hcr?cmd=search-events3&outputformat=json&instrument=IRIS&startTime=…&stopTime=…` with startTime/stopTime = the dataset's STARTOBS/ENDOBS. It takes the HCR event whose obsId equals OBSID (if several match, the one whose start is nearest STARTOBS) and stores its obsTitle, goal, target, noaaNum and planners as `HCR_*` strings in the meta of every loaded dataset of the observation (shown by Ctrl+I). Browser scans never query HCR; tooltips show these only after a confirmed fetch.
  Done when:
  - A mocked response recorded from the live 2014-03-29 14:00–15:00 query (checked 2026-09-27) gives, for obsId 3860258481, 'IHOP251 with Sac Peak at AR12017', target 'AR', NOAA '12017'. The request carries STARTOBS/ENDOBS as startTime/stopTime; with a second mocked event for the same obsId, the one starting nearest STARTOBS is used.
  - No matching obsId, or a network error, shows a message and changes no meta; a browser scan makes no HCR request.

  Features: F041. Depends: wp7-context-port.
- [ ] **M3** `wp7-aia-channels`: The `wp7-aia-context` dialog can add AIA 94–1700 Å channels and HMI (continuum, line-of-sight magnetogram) to the same Worker fetch. The AIA 171 locator stays the only full-disk view: each extra channel gives an FOV crop (or, when a same-observation `aia_l2` cutout is loaded, a locator only), built through `_parse_sunpy_map` and `link_hpc` like AIA 171. If one fails, the message names it and nothing is added.
  Done when:
  - A mocked 1600/304/HMI-continuum request with no cutout loaded gives three crops, each `link_hpc`-linked to the IRIS data; a mocked failure of one leaves the collection unchanged.

  Features: F047. Depends: wp7-aia-context.

**Notes and limits**

- First exposure only: drift (42.2 arcsec over 4.8 h, 2021-09-05 irispy SJI fixture, OBSID 3620258102) is not followed (D1). AIA is one image per channel placed by header WCS and `link_hpc`; no time series or co-registration.
- Not built: context viewers, cadence sync via spatial links, JSOC login, aiapy, cross-correlation.
- GOES: sunpy 8.0.0 does not mask XRS quality flags; SWPC names only the current primary (GOES-18, 2026-09-22), so there is no historical "primary"; GOES-19 needs sunpy ≥ 8.1.
- The marker artist appears in 'Save plot to file' but not the Python-script export (glue #2603 / glue-qt #73 Line layers could replace it). The `PolygonalROI` subset stays until a release contains #2604 (`wp0-track-2604`).

### WP8: Browser, discovery and inputs

WP8 owns the observation browser (`QtIRISImporter`, `iris_loader.ui`), the header scanner (`glue_solar/sources/loaders/scan.py`) and the IRIS readers (`glue_solar/sources/loaders/iris.py`, `glue_solar/sources/iris.py`): correct labels and isolated test settings at M0, derived files hidden at M1, a threaded, stoppable, filterable scan at M2, search and Level-3 input at M3. All on the D5 baseline, with no upstream PR.

Port from prototypes (fix the named findings first):
- `IRIS_PLAN_PROTOTYPES/wp8_scan.py` (only the `stop` keyword and poll) and `wp8_proto.py` + `wp8_loader.ui` (the scan and filter methods and .ui hunks, rebased onto the `wp10-nonblocking-load` lifecycle; not the `iris.UI_MAIN` override, `populate_threads` or `_stop_scan`'s `worker.wait()`) → `wp8-filter-stop` and `wp8-text-filter`, after `wp8-sji-variants` and `wp8-derived-files`. Fix first the findings listed in those two checkboxes.
- `IRIS_PLAN_PROTOTYPES/wp8_test_proto.py`, `wp8_test_shipped.py`, `wp8_chk_test_text.py` (its stop-message test with the `ProtoImporter` case only) → `test_scan.py`/`test_importer.py`, gated on a `threading.Event` (wp7-wp8-12). Rewrite `test_scan_directory_stop_kwarg` (it assumes one poll per sorted file), add `qtbot.waitUntil(lambda: not dlg.scanning)` at the 10 construction, toggle and finalize sites in `test_importer.py`, and invert `IRIS_PLAN_PROTOTYPES/review_20260927/probes/wp8/test_v_wp8.py` tests f2/f3/f4/f11 into regressions. Archive `wp8_chk_proto_fix.py` (evidence only) once that test is ported without its parametrization.
- `IRIS_PLAN_PROTOTYPES/review_20260905/qs_isolate.py` → only `IsolatedQSettings`, into `wp8-test-qsettings` (plan-integrity-2).

#### M0
- [ ] **M0** `wp8-test-qsettings`: In `glue_solar/conftest.py`, an autouse fixture swaps `glue_solar.sources.loaders.iris.QSettings` for a minimal `IsolatedQSettings` (from `qs_isolate.py`, not imported) writing IniFormat under `tmp_path` (`set_directory` writes `iris/last_dir` even under an isolated HOME), and `glue.config.CFG_DIR` points at a temporary directory as in `glue_qt/conftest.py:63-66` (glue-qt's `get_qapp` saves `~/.glue/settings.cfg` when FONT_SIZE is unset). Done when a test asserts `iris.QSettings('glue-solar', 'glue-solar').fileName()` lies under `tmp_path`, and a plain `pytest glue_solar` run in the iris-plan env leaves `defaults read com.glue-solar.glue-solar` (macOS) and the mtime of `~/.glue/settings.cfg` unchanged. Features: none (test infrastructure). Findings: plan-integrity-2.
- [ ] **M0** `wp8-sji-variants`: Key SJIs in `scan_directory` by TDESC1 plus the filename variant ('SJI_2796 (deconvolved)' for `_deconvolved.` names, which today overwrite the plain entry), and pass the path to `_image_cube_data` (`loaders/iris.py:121-125`) so both load routes label it 'SJI_2796_deconvolved-<OBSID>-<STARTOBS>'. Done when:
  - CI: a `tmp_path` test like `test_load_selected_real_sji` copies irispy's `iris_l2_20210905_001833_3620258102_SJI_1400_t000` to a plain and a `_deconvolved` name; the scan lists 'SJI_1400' and 'SJI_1400 (deconvolved)', both load through the dialog and `read_iris_file` with different labels, the second naming the variant; `iris_tree` is unchanged.
  - Local (skipped without ~/DATA/IRIS): 4000005156's `SJI_2796_t000_deconvolved.fits.gz` plus a symlink to it without `_deconvolved` list and load as two entries; every other observation's SJI, raster and window counts are unchanged.
  - No existing test fails or changes its assertions (labels, colormaps, (OBSID, STARTOBS to the second) grouping). Features: F009. Findings: followup-4-5.

#### M1
- [ ] **M1** `wp8-derived-files`: Make `_is_supported_file` (`scan.py:110-115`) accept an IRIS `SPEC` file only if its primary header has `DATA_LEV == 2` (no extension read), which the derived `iris_l2_20140910_fexxi_rb_steps` lacks. Skipped files are not listed and the progress text counts them (confirmed); a load failure names the file, not just the window. Fixtures: `_header` gains DATA_LEV=2; OBS_S stays stem-less (`{MD5}sparse_l2_raster.fits.gz`, DATA_LEV=2, no OBS_DESC/ENDOBS) so `test_sparse_header_falls_back_to_obsid_description` keeps its coverage; a new derived fixture copies rb_steps' name and layout (TELESCOP 'IRIS', INSTRUME 'SPEC', no DATA_LEV) with OBS_A's OBSID and STARTOBS. Done when:
  - on `iris_tree` the derived fixture is never a window, OBS_A keeps its 2 rasters (`a.nfiles == 4`), OBS_S and the irispy Level-2 fixtures are listed, and the progress text reports 1 skipped file;
  - `test_reader_failure_stays_in_dialog` asserts the failing file's name is in the message;
  - locally (skipped without ~/DATA/IRIS) the scan finds 13 observations (14 today), skips 1 of the 130 FITS files and lists the rb_steps file nowhere. Features: none. Findings: followup-4-6.

#### M2
- [ ] **M2** `wp8-filter-stop`: Run `scan_directory` in glue-qt's `Worker` with a cooperative `stop` predicate, polled while the tree is enumerated and once per file, so a stop takes effect within one header read. Populate on the GUI thread. Reuse the worker lifecycle that `wp10-nonblocking-load` writes first: on rescan, directory change, accept, reject and close, stop the previous worker and drop its results by scan id, with no GUI-thread `wait()`; do not write a second lifecycle. Load is disabled during a scan and archive-extraction messages stay; after a Stop, truncated observations show '(partial scan)' with Stack disabled; `_scan_over` fixes an invalid progress value after `setRange(0, 100)` but leaves a completed extraction at 100. Done when:
  - deterministic pytest-qt tests (header reads gated on a `threading.Event`, no sleeps) show: Stop or reject during a slowed walk returns after at most one further `is_file` call and within 0.5 s; Load during a gated rescan cannot load from the replaced list; after an early Stop a 2-raster observation shows 1 file and the partial marker; Stop after completion never shows 'Scan stopped'; stale scan ids are ignored; the suite passes 20 consecutive runs;
  - locally on ~/DATA/IRIS (13 observations), GUI timer gaps stay ≤ 0.2 s and the median header read is ≤ 5 ms/file. Features: F005. Findings: wp7-wp8-2, wp7-wp8-3, wp7-wp8-4, wp7-wp8-11, wp7-wp8-12, archive-trace-16, followup-2-8 (WP8 thresholds only). Depends: wp8-sji-variants, wp8-derived-files, wp8-test-qsettings, wp10-nonblocking-load.
- [ ] **M2** `wp8-text-filter`: Add a case-insensitive `filter` QLineEdit to `iris_loader.ui` matching STARTOBS, OBSID, description and the child rows' window, SJI and AIA names (column 6 for single-entry rows); keep the object names `filter`, `stop_scan` and `progress`. Done when on `iris_tree` 'mg ii' keeps only OBS_A and shows its Mg II child row, '2023-02' keeps only OBS_B, a hidden ticked observation makes Load read e.g. 'Load selected (1 hidden)' and still loads, and the filter text survives a rescan. Features: none (usability; ISO date substrings give a partial date filter; the time-window search is `wp8-search-ui`). Findings: wp7-wp8-13. Depends: wp8-filter-stop.

#### M3
- [ ] **M3** `wp8-prescan-search`: Add keyword-only `start`, `stop`, `glob`, `date_tree`, `max_duration` (default 1 day) and `first_raster_header_only=False` to `scan_directory`, pruning before any header read: in window or date-tree mode, skip files whose `_key_from_name` stamp is outside [start − max_duration, stop] (unstamped files count as skipped, unread); match `glob` with `fnmatch` on `strip_pooch(name)`; in date-tree mode enter only YYYY/MM/DD directories inside the interval; after reading keep observations with STARTOBS ≤ stop and ENDOBS ≥ start; with `first_raster_header_only=True` add an observation's further `_raster_t###_r#####` files unread (`QtIRISImporter` passes True; confirmed). Add `find_observation_files(time, root, sji=False, nearest=False)`, returning the raster repeats (or SJIs) of the observation covering `time`, `nearest` falling back to the closest (iris_find_file parity). Done when tests counting `fits.getheader` calls on a temporary YYYY/MM/DD symlink tree of real ~/DATA/IRIS files (local), with a CI variant on `iris_tree`, show:
  - a 2013-09-02 window reads only headers stamped 2013-09-01 to 2013-09-02 and lists only 4000255147 and 4000005156, and date-tree mode enters no directory outside the interval;
  - `glob='iris_l2_2025*'` lists only 3400109360 and 3893010094, not the 3640107442 AIA cutouts;
  - `find_observation_files('2013-09-02T17:00', root)` returns the 4000255147 raster and with `sji=True` its SJI_1400 (it runs 16:39:35–17:58:48), and `nearest=True` on an uncovered time returns the closest observation;
  - `first_raster_header_only=True` reads 1 SPEC header for 3602506433 (99 rasters, local) and for OBS_A (2 rasters, CI) and still lists every raster and the same windows;
  - with no new arguments, results equal today's scan. Features: F003, F010. Findings: wp7-wp8-10. Depends: wp8-filter-stop.
- [ ] **M3** `wp8-search-ui`: Add Start/Stop UTC `QDateTimeEdit` fields with 'Last 5 days', 'Up until now' and 'Ignore times'; named search locations (root, date tree, search subfolders, glob) in a combo with one 'local' default (IDL's free/LMSAL/UIO presets only with roots cited to iris_xfiles source); and 'Recent searches'. Store them beside `iris/last_dir` in `QSettings('glue-solar', 'glue-solar')` and pass them to `wp8-prescan-search`. Done when pytest-qt with isolated QSettings shows that 'Last 5 days' sets Start to now − 5 d and Stop to now; 'Ignore times' equals an unwindowed scan; a location can be added, edited and removed, and restores its root, date-tree, subfolder and glob values after reopening; and the recent list stops at 10, a chosen entry restoring Start/Stop. Features: F001, F002, F004. Depends: wp8-prescan-search, wp8-test-qsettings.
- [ ] **M3** `wp8-browser-conveniences`: Persist 'Search subfolders', 'Stack' and the filter text in the same store; make the Folder QLineEdit editable, rescanning on `editingFinished`; double-clicking a row loads only its payload. Record source path(s) in `data.meta['SOURCE_FILES']` inside `raster_data`, `image_data` and `iris_data`, which the `wp3-file-references` load routes (`read_iris_rasters`, `image_data` and File→Open's `read_iris_file`) call; it is display-only (relocation uses WP3's LoadLog). Done when pytest-qt with isolated QSettings shows values set before closing restored on reopen; Enter on a typed path rescans, while an invalid path shows a message and keeps the list; with another row ticked, double-clicking a leaf or single-entry row loads only it and double-clicking a parent row only expands or collapses it; a loaded SJI stores its absolute path in `meta['SOURCE_FILES']`, OBS_A's two-raster stack stores both paths, and `MetadataDialog` lists them; and a session save and restore keeps `meta['SOURCE_FILES']` as a list of str. Features: F006, F007, F014. Depends: wp8-text-filter, wp8-test-qsettings, wp3-file-references.
- [ ] **M3** `wp8-browser-metadata`: Add tooltips (not columns) to observation rows and window/SJI items from the primary headers `scan.py` already reads, stored on `Observation` at scan time: TWMINn/TWMAXn/TDETn, window size from TSCn/TECn/TSRn/TERn, NRASTERP, FOVX/FOVY, STEPT_AV, binning from SUMSPTRF/SUMSPTRN/SUMSPAT (SUMSPAT is the spatial bin, unlike IDL's label), OBSLABEL/OBSTITLE and the ObsID decoding. Done when the irispy 20140329 fixture raster's C II tooltip starts 'C II 1336: 1332.73–1337.22 Å, FUV1'; on the local 2013, 2014 and 2018 observations every tooltip number equals the header value (e.g. 3824262996 C II 1336 = 1332.70–1337.58 Å); and the scan tests' counted header reads are unchanged. Features: F039, F040.
- [ ] **M3** `wp8-remote-search`: Add a `menubar_plugin` 'IRIS: search online…': `sunpy.net.Fido` search on `a.Time` and `a.Instrument('IRIS')` (verified 2026-09-27: per-observation LMSAL Level-2 records), an OBSID filter on `fileid`, `Fido.fetch` of ticked rows in the existing `Worker` into a chosen folder, then `QtIRISImporter` on it. Link to the LMSAL search page; do not rebuild it. Done when mocked-network tests show results grouped by observation, a working OBSID filter, no network work on Cancel, and an unchanged folder and data collection after a fetch error; the dialog's LMSAL search-page link is checked by hand in a browser before merge; and an opt-in network test (skipped by default) downloads the ~39 MB SJI_1400 record of the 2021-04-29 observation 3660259102, which the browser then lists under that observation. Features: F016, F017, F018. Depends: wp8-filter-stop.
- [ ] **M3** `wp8-m3-level3-input`: Register a `data_factory` 'IRIS Level 3 FITS' in `glue_solar/sources/iris.py` claiming `*_im.fits` names with the three Level-3 extensions at priority 210 (above `is_iris_fits` at 200); add a header-keyword test once a real file confirms one. Read the (x, y, wave, time) cube with `astropy.io.fits`: wavelengths from extension 1, extension-2 times (seconds since DATE_OBS, shape (nx, ntime)) as a datetime64 `Time` component, extension-3 slit positions as components, and the spatial WCS from the header, VER_RF3 (the iris_xfiles r1.41 cutoff) selecting which exposure time CRVALn refers to. Transposed sp files are not claimed. Done when synthetic ITN26-layout im files with VER_RF3 on each side of the cutoff each load as one Data whose wavelengths match extension 1, whose `Time` equals DATE_OBS + extension 2 and whose spatial WCS matches the header at the selected exposure, and the factory claims neither the Level-2 fixtures nor the irispy files. Features: F025.

Notes and limits:
- The scan Worker reads only primary headers, never QSettings or widgets. M2 does not reduce scan work; `first_raster_header_only` (M3) does (wp7-wp8-10). Loading off the GUI thread is `wp10-nonblocking-load` (followup-2-9, followup-2-1).
- Deconvolved SJIs are recognised by filename only (identical headers), so a renamed deconvolved file cannot be told apart.
- `finalize`, `iris_loader.ui` and `test_importer.py` are also edited by WP3 (`wp3-file-references`), WP4 (`wp4-launch-entry`: 'Open quicklook' option and per-dataset observation record; `wp4-quicklook-preset` chooses between the plain and deconvolved SJIs that `wp8-sji-variants` lists), WP10 (`wp10-nonblocking-load`) and WP1; land WP8 M2 after them.
- Each WP8 PR documents its own behaviour in the loading guide (the WP9 rule): the deconvolved-SJI labels (`wp8-sji-variants`), the skipped-file count (`wp8-derived-files`) and, with `wp8-remote-search`, F016's workflow (search the LMSAL page, then open the downloaded folder in the browser).
- Non-goals: OBS XML viewer, pipeline-log viewer, EIS sources (F019), Level-3 writing, new dependencies. Unverified: `Fido` downloads end to end, the LMSAL page URL (iris.lmsal.com returned 403), the Level-3 header keyword and VER_RF3 mapping (read iris_xfiles / `iris_make_fits_level3` source first; no real Level-3 file exists locally), IDL location roots, date-tree pruning on a real mirror.

### WP9: Documentation and tutorials

WP9 keeps the `docs/` guides accurate for what ships (M0: the D5 baseline plus solar main) and maintains an IRIS-9-style CRISPEX tutorial (link in Goal and scope) whose steps are the acceptance script. Recipe checks live in `glue_solar/tests/test_documented_workflows.py`. Every docs checkbox also needs a passing `wp9-m0-docs-build`.

#### M0

- [ ] **M0** `wp9-m0-user-guide-corrections`: Correct the user guides; add only missing text.
  - `loading-iris-level-2-raster-and-sji-data.rst`:
    - aligned `aia_l2_*.fits` cutouts need no `_SDO` directory; SJIs and aligned AIA cutouts carry a datetime64 `Time` component per frame (#52), which the Frame time tool displays; stacks are floating memmaps;
    - state the WP10 loader behaviour: -200/-199 fill becomes NaN (IRIS-SSW convention; AIA cutouts use -200 only); +Inf saturation is kept; the mask is 0/1 uint8; negative-step rasters keep irispy's default orientation, with `revert_v34=True` as the documented alternative (not the default: it mirrors the map relative to the SJI);
    - quote labels as displayed at PR time, in Glue order (SJI `Time (Utc)`, `Latitude`, `Longitude`; raster `Helioprojective Longitude`, `Helioprojective Latitude`, `Wavelength` in m);
    - fix the manual-link paragraph (it pairs Helioprojective names the SJI lacks) and state the directional limit, as before `wp1-m0-link-hpc`;
    - replace the restore-only warning with "Saving a session that contains IRIS data can fail before any file is written."
  - `loading-aia-and-hmi.rst`: the same note for sunpy Maps; alt text "AMI" → "AIA".
  - Profile guide: float/NaN; collapse versus one-pixel subset with Mean versus the unreleased Slice profile; Maximum is the default function, Mean gives CRISPEX's average spectrum.

  `wp3-app-session-acceptance` (M1) replaces both session notes. Done when `git grep` over `docs/` finds no "AMI", "folder is present" or "cannot currently be restored", and the IRIS and AIA/HMI guides both carry the session warning. Features: none. Findings: solar-main-5, solar-main-6, plan-integrity-10, plan-integrity-17, followup-3-18. Depends: wp10-fill-nan (Mean sentence and fill text), wp10-mask-uint8, wp10-m0-negative-step.
- [ ] **M0** `wp9-m0-dev-guide-stack`: Document the stack storage in `docs/dev_guide/loader-customization.rst`. Done when the page states: the data is a memmap of dtype `np.result_type(first scan, float32)`; irispy-masked samples and -200/-199 fill are NaN (D12); `<label> mask` is `isnan(data)` as uint8; so +Inf saturated samples stay unmasked. Features: none. Findings: plan-integrity-17, solar-main-6. Depends: wp10-fill-nan, wp10-mask-uint8.
- [ ] **M0** `wp9-m0-changelog-fragments`: Add `changelog/52.feature.rst` (SJI/AIA-cutout datetime64 `Time`; `solar:frame_time`, `solar:cursor_readout`) and `changelog/53.bugfix.rst` (transparent NaN pixels); raster/stack `Time` is already in `44.feature.rst`. Add no ndcube fragment, and do not edit README to mirror this plan. Done when `towncrier build --draft` lists both and neither mentions raster or stack Time. Features: none. Findings: solar-main-4.
- [ ] **M0** `wp9-m0-viewer-tools-docs`: In the IRIS guides, document glue-qt 0.4.2 tools by action text and tooltip, shortcuts as Ctrl+… "(Cmd on macOS)": "Pixel" (`image:point_selection`) versus "Cursor readout" (`solar:cursor_readout`); `wp11-readout-icon` replaces "the crosshair icon" at profile rst:54 in its own PR; "Frame time"; Ctrl+I "View metadata/header"; the "Contrast/Bias" toolbar drag (`image:contrast_bias`); in the style editor, gamma < 1 is Custom limits + sqrt until `wp11-gamma-stretch`; windows (CRISPEX's Displays tab): minimise, Ctrl+N, Gather Windows (Ctrl+G), and Tab/Backspace only in Image, Scatter and Histogram viewers. Done when a glue-qt 0.4.2 test asserts Tab and Backspace cover ImageViewer, ScatterViewer and HistogramViewer, not TableViewer or ProfileViewer (`glue_qt/app/keyboard_shortcuts.py:32-52`); quoted tooltips and Ctrl+I/Ctrl+G text match the sources; no text WP9 adds says "the crosshair icon" without the tool name. Features: F037, F192. Findings: solar-main-3, solar-main-4, followup-3-4.
- [ ] **M0** `wp9-m0-browsing-recipes`: In the loading guide, document no-code browsing:
  - list columns and grouping; "Load selected";
  - large or multi-scan observations need the browser (window choice, Stack): File→Open and `glue --startup` load every window of every file and cannot stack scans;
  - several SJI/AIA channels (plain and deconvolved SJI collide until `wp8-sji-variants`); "Stack sequential raster scans";
  - playback (extra Forward presses: round(500/n) ms; wraps); arrow keys on a focused slider;
  - SJI log stretch as xsji_image except north-up (`wp11-north-up`); Arithmetic scaling; Home/Pan/Zoom; Save menu (PNG/JPEG/PDF/PS/EPS/SVG); layer colour, alpha and linewidth in the style editor, Preferences colours and font size.

  Done when a glue-qt 0.4.2 test asserts the round(500/|n|) interval and wrap (`data_slice_widget.py`), that the stack option yields 4D Data with a per-pixel `Time`, and that a saved `.eps` starts with `%!PS-Adobe` and has a `%%BoundingBox` line. Features: none. Findings: followup-3-16.
- [ ] **M0** `wp9-m0-mask-overlays`: In the loading guide, document overlays from the 0/1 uint8 `<label> mask` (D12): "Create faceted subsets" first; a Histogram x-range subset works, but its "Add large data set?" modal defaults to Cancel above 2e7 elements (4000255147 SJI_1400: 6.47e7); "Import subset mask(s)" takes same-shape signed-integer FITS HDUs, BITPIX 16/32/64 without unsigned BZERO (`glue/io/formats/fits/subset_mask.py:24`). Done when a fixture test shows the faceted-subset count equals `mask.sum()`, as does a recorded manual check on the real 4000255147 SJI_1400 and raster. Features: none. Depends: wp10-mask-uint8, wp10-m0-negative-step.
- [ ] **M0** `wp9-m0-workflow-recipes`: Extend the profile guide with released-Glue recipes, naming axes by role:
  - four panels by hand (raster as spectrogram and map, SJI, Profile, Pixel, Gather Windows); Profiles above 1e8 elements ask "Add large data set?", default Cancel;
  - axis choices for spectrogram (wavelength × slit), raster map (step × slit) and time–wavelength (scan/exposure × wavelength; that axis is an index, `Time` gives UTC); on sit-and-stare the stock exposure axis reads "Helioprojective Longitude" (drifting ~42 arcsec) but is acquisition order (the quicklook labels it Exposure);
  - the step slider gives iris_xraster's per-position "Spectroheliogram";
  - Pixel follows on drag, holds on release, replaces the active subset; intersecting it with a band or scan subset works only within one dataset (on a linked dataset the AND gives an all-NaN profile, data.py:1733-1735@v1.27.0), and any intersected subset hides the Pixel crosshair even there (image layer_artist.py:319-331@v1.27.0); Ctrl+K clears it only when the layer tree has focus;
  - Profile Navigate sets its x-axis slice in every Image viewer of the dataset only while its line moves; their sliders are otherwise independent. On glue-qt 0.4.2, Navigate and Collapse pick the wrong slice when the Profile display unit is not the native unit.
  - Slice Extraction (P; click vertices, Enter/Esc) needs 3D data: SJI time–distance or a single-scan raster's spectral virtual slits, not 4D stacks (until `wp12-path-slicer`); it makes no Data object. Collapse "Maximum"; light curves; `Time` as readouts.

  Done when the text states that P works on 3D data only; a test runs one check per recipe (including the four panels, time–wavelength, Navigate and the sit-and-stare light curve) on the irispy 0.9.0 fixtures on released core, driving Pixel with the press/drag/release helpers (`mouse()`/`select_point()` from `review_20260923/test_existing_workflows.py`), ported into `glue_solar/tests/helpers.py` by whichever of this item and `wp4-tests` lands first; the Pixel & band recipe check asserts the band spectrum on the same dataset and the missing crosshair; and neither the tests nor a manual walk-through on 4000005156 and 4000255147 uses the prototype. Features: none. Findings: plan-integrity-5, usefulness-19, plan-integrity-4, archive-trace-10. Depends: none (released Glue only; lands before WP4 code).
- [ ] **M0** `wp9-m0-scripting-recipe`: Add a recipe for the Terminal button, `raster_data`/`image_data`, `data.coords.pixel_to_world_values` and `data['Time']`; no NDCube `data_translator` until asked. Done when a doctest or offscreen check on the irispy 0.9.0 20210905 fixture shows `pixel_to_world_values` at a Pixel point equals the status-bar readout and the raster's Profile Mean equals `np.nanmean` over the non-spectral axes. Features: F033. Depends: wp10-fill-nan (Mean check).
- [ ] **M0** `wp9-m0-iris9-tutorial`: Add `docs/user_guide/iris9-crispex-tutorial.rst` (linked from the index): every IRIS-9 §3.3 CRISPEX task with local stand-in data, Glue steps where supported, "not yet supported in Glue" otherwise.
  - §3.3.1 (OBSID 3840007146; stand-in 3824262996, Si IV 1403, Mg II k 2796): gamma < 1 (M0 workaround; `wp11-gamma-stretch`); ~2 frames/s core blink (`wp5-m1-spectral-blink`); a feature's solar (x, y) (M0).
  - §3.3.2 (2014-11-07 4-step × 80 flare; stand-ins 3602506433, and 4000005156 for raster + SJI): run and find the end time (M0); Doppler range (`wp5-m1-doppler-image`); mouse lock with T-slice (`wp4-m1-hover-lock-tool`); raster positions on the SJI (`wp4-raster-overlays`).
  - Event finding (M0): play, pause on a brightening, select on the raster map (sit-and-stare: slit–time panel), zoom, read spectrum and matched times.

  Done when every task appears with its stand-in, the M0 step lists are those `wp9-m0-iris9-acceptance` runs, and no rst text names a WP or milestone. Features: none. Findings: archive-trace-14, usefulness-13, followup-3-17, followup-3-4. Depends: wp4-quicklook-preset, wp4-m0-point-fixed-index, wp4-time-sync, wp4-sji-panels, wp4-exposure-readout.
- [ ] **M0** `wp9-m0-iris9-acceptance`: Add `glue_solar/tests/test_iris9_acceptance.py`, a pytest-qt run of the M0 tutorial steps through the quicklook on released core, skipped without `~/DATA/IRIS`. Data: 4000005156 two-scan stack + SJI_2796 (deconvolved only); 4000255147 sit-and-stare + SJI_1400.
  1. It switches the master to the SJI and plays.
  2. It stops at the frame with the highest 99.9th percentile in the raster footprint (sit-and-stare: slit column ±1 px).
  3. It clicks the brightest in-region position (via the WCS) and zooms. 4000005156, raster map: step from the WCS position, scan argmin|dt|, shown offset = Time[scan, step] − SJI frame time. 4000255147, slit–time panel at (argmin|dt| exposure, WCS slit row): both indices.
  4. Both: the spectrum panel equals the raster spectrum at those indices; zooming keeps the selection.
  5. On 4000005156, in a fresh preset (raster master), it closes the SJI viewer and opens a new Image viewer on the raster; the new viewer joins coordination and the closed one leaves. At a position whose raw FITS spectrum contains -200/-199, the spectrum panel shows NaN gaps, not -200. Reopening a saved session is `wp3-app-session-acceptance` (M1).

  Performance and the frame-stepping crash (followup-2-1, followup-3-1) belong to `wp10-m0-acceptance`; SJI clicks join via `wp1-m1-sji-to-raster`. Done when the script passes on both observations. Features: F093. Findings: usefulness-13, plan-integrity-8, followup-3-17. Depends: wp9-m0-iris9-tutorial, wp10-fill-nan, wp10-m0-wcs-lock, wp10-m0-interaction-latency.
- [ ] **M0** `wp9-m0-docs-build`: Build with `sphinx-build -W --keep-going -b html docs <out>` in a new micromamba env `iris-plan-docs` (iris-plan's packages plus the `docs` extra), not `tox -e build_docs`; also run the tests with QSettings isolation. Done when the env recipe is in the Validation section and main plus the M0 edits build with no warnings. Features: none.
- [ ] **M0** `wp9-m0-wiki-digest`: Only on request, fetch and refresh the public wiki (remote 5ef5fa1 is past local 63f0400); fix `Home.md:4` and `Short-Term-Roadmap.md:1`; replace "In preferred order" with M0-M3; no local paths or prototype links. Done when the wiki shows the milestone digest with no dangling section references. Features: none. Findings: plan-integrity-11, upstream-state-5.

#### M1

- [ ] **M1** `wp9-m1-release-updates`: On core #2596/#2601 + Qt #70, drop "unreleased" from the Slice-profile text and remove the Navigate and Collapse display-unit caveat; on Qt #74, rewrite "Cursor readout"; on the Tab/Backspace fix, update the window text; when `wp1-m0-axis-names` and `wp1-m1-wrapper-coherence` land on main, replace SJI `Latitude`/`Longitude` with the helioprojective names and metres with Å in every guide, recipe and screenshot. Done when `git grep` over `docs/` finds no stale label, unit or "unreleased" text for any released or merged item. Features: none. Findings: plan-integrity-4, followup-3-18, solar-main-3, archive-trace-10. Depends: core #2596/#2601 + glue-qt #70 release; glue-qt #74 release; wp1-m0-axis-names, wp1-m1-wrapper-coherence.
- [ ] **M1** `wp9-m1-iris9-tutorial`: As each dependency lands, add its tutorial steps and its acceptance run. Done when every tutorial task has a Glue step list and a passing acceptance run on its stand-in data. Features: none. Findings: usefulness-13, archive-trace-14. Depends: wp1-m1-sji-to-raster, wp4-m1-hover-lock-tool, wp5-m1-spectral-blink, wp5-m1-doppler-image, wp4-raster-overlays, wp11-gamma-stretch.
- [ ] **M1** `wp9-m1-screenshots`: Re-add `docs/make_screenshots.py` from 93d05f05 (local branch `backup/iris-observation-browser-pre-rebase`) or drop it. Done when the helper is on main and regenerates `docs/user_guide/images/` from a named local observation with HOME isolated, or the plan records the drop. Features: none. Findings: solar-main-1, usefulness-19.

#### M3

- [ ] **M3** `wp9-m3-saturation-recipe`: Add "Was it saturated?": check NSATPIX/TSATPXn in the header, then subset on an Arithmetic `np.isinf(<data component>)` (ITN 26 §6.4). The moments action already flags +Inf and warns on NSATPIX/TSATPXn (`wp2-m2-input-quality`). Done when, on a synthetic cube with one Inf sample, the subset holds exactly that sample and shows in a linked Image viewer, and the dialog reports NSATPIX 0 for 4000005156 Si IV. Features: F170. Findings: wp2-wp6-science-8.
- [ ] **M3** `wp9-m3-spectral-recipes`: Add profile-guide recipes: (1) average spectrum over a scan/exposure range on the 3602506433 stack (99 scans): create a new subset, x-range on a Scan/exposure Profile, then Mean; (2) photospheric context from 3660259102's 2832/2826/2814 windows and 3640107442's AIA 1600/1700 cutouts (no local pair; fetching SDO data needs user approval); (3) row/column cuts with the Slice profile once released, subset + Mean until then; (4) notes on y-limits, line width, axis-label edits (reset when x changes), and Normalize or per-window Profile viewers in place of CRISPEX's per-window multiplier. Done when each recipe reproduces on the named data (recipe 3's Slice step once released). Features: F080, F084, F145. Findings: archive-trace-18. Depends: wp9-m0-workflow-recipes; core #2596/#2601 + glue-qt #70 release (recipe 3's Slice step only).
- [ ] **M3** `wp9-m3-shortcuts-help`: Add a keyboard/mouse table:
  - Pixel, Navigate, P, Ctrl+I, Ctrl+G, Tab/Backspace;
  - `w` for pixel/world in WCSAxes' own readout (and Qt #74's `format_coord` readout); `wp11-cursor-readout` shows both at once;
  - the `wp11-keyboard-shortcuts` keys (D/F, A/S, Space) and L for 'Solar path (3D/4D)' (`wp12-path-slicer`).

  Add a `menubar_plugin` "IRIS: user guide and issues" (`webbrowser.open`). Done when tests show every glue-solar `keyboard_shortcut` and viewer-tool shortcut is in the table, the Plugins menu shows the entry, and (with `webbrowser.open` mocked) both URLs open. Features: F198, F199. Depends: wp11-keyboard-shortcuts, wp12-path-slicer.

#### Notes and limits

- Each feature PR documents its own capability; WP9 owns cross-cutting guides, corrections, the tutorial and acceptance. No doc claims planned features ship.
- M0 event finding starts on the raster map: stock SJI Pixel subsets give no raster spectrum on released core, and #2595's frame-0 path is off by 78 SJI px across 4000255147.

### WP10: Loader robustness and performance

WP10 makes the IRIS loaders correct and fast for the M0 quicklook, then lazy. Code is in `glue_solar/sources/loaders/`, tests in `glue_solar/tests/`. Non-blocking load is M1 because the M0 blocker list omits it (confirmed; effort M), so each M0 pick freezes the GUI for 1.0-3.1 s.

Port from prototypes:
- `IRIS_PLAN_PROTOTYPES/wp8_proto.py` and `wp8_scan.py` → the pattern only for `wp10-nonblocking-load` (code ports under `wp8-filter-stop`). Fix first: wp7-wp8-3, wp7-wp8-2.

- [ ] **M0** `wp10-fill-nan`: In `_cube_data`, set -200/-199 to NaN (D12; exact codes, not SSW's `< -198.5`, as irispy float fixtures hold real values below -200) by `np.isin` on the already-flipped data, never from irispy's unflipped `cube.mask` (`irispy/io/spectrograph.py:251@0.9.0`); convert with `astype(np.result_type(dtype, np.float32), copy=False)` only when fill is present (writing into irispy's cube, safe only while the loader discards it). AIA cutouts (TDESC1 not starting 'SJI') treat only -200 as missing (-199 unverified for AIA); saturation (+Inf, int16 16182 DN) is unchanged. `stack_spectrograms.py` applies the fill rule per scan as it writes the memmap, replacing the irispy-mask NaN; the stack's `_cube_data` call skips the fill step. Done when:
  - CI: `raster_data` on the irispy fixture `iris_l2_20210905_001833_3620258102_raster_t000_r00000_test.fits` Si IV 1403 gives 0 values of -200/-199 and exactly 35,027 NaN of 216,920 samples; a synthetic negative-step fixture (flipped data, unflipped mask) gets NaN exactly at the flipped fill positions; the `test_importer.py` stack mask assertions use `isnan`.
  - 4000005156 Si IV scan 0 has no -200/-199 and a NaN count equal to the raw count of those codes (3,050,445); the default percentile lower limit is no longer -200 and per-scan and stack limits agree; a one-pixel Pixel-subset Mean spectrum equals the raw spectrum with fill as NaN.
  - On 3400109360 the NaN positions of each scan and of the 2-scan stack equal the flipped raw fill positions.
  - A synthetic int16 AIA-like cutout with injected -200 renders those pixels transparent (#53); a fill-free cutout stays int16.

  Features: F164, F031. Findings: followup-3-3, followup-4-2, followup-3-2.
- [ ] **M0** `wp10-mask-uint8`: After the fill step, store every SJI, per-scan and stack mask as `Component(np.isnan(values).view(np.uint8))` with no second in-RAM copy (D12). Done when every mask component is uint8 and equals `isnan(data)` (real SJIs: `cube.mask` plus the -199 pixels), with the `test_importer.py` mask assertions updated; `raster_data` on all 9 windows of 4000005156 scan 0 retains ≤ 6 B/element and peaks ≤ 10 B/element, and stacking all 7 windows of the 99-scan 3602506433 peaks below 12 GB (50 scans measured 10.07 GB; 99 untested; memory limits: confirmed). If these hold, lazy loading stays in M2. Features: none. Findings: followup-2-2, usefulness-12. Depends: wp10-fill-nan.
- [ ] **M0** `wp10-m0-negative-step`: In `_cube_data`, when STEPS_AV < -0.01 and the probe `abs(Tx[0] - lon(step 0)) > abs(Tx[-1] - lon(step 0))` fires (Tx: x of `meta['exposure FOV center']`; lon: WCS longitude at the FOV-centre slit row), set `data.meta` to a copy of `cube.meta` with the step axis reversed in the five per-step keys (auxiliary times, exposure time, exposure FOV center, observer radial velocity, orbital phase); never modify `cube.meta` (D10). It retires with `wp0-irispy-v34-flip`. Done when:
  - The probe fires for every 3400109360 scan (8 local, r00000-r00007) and not for 4000005156, 4000255147 or 3824262996.
  - On a synthetic negative-step raster with varying exposure times, `data.meta['exposure time'][k]` equals the file's EXPTIMEF at row N-1-k.
  - Nearest-index on 3400109360: `wp4-time-sync` check 3.
  - Descending-step SJI slit and marker positions are recorded as untested until a 3400109360 SJI is fetched (with the user's approval).

  Features: none. Findings: followup-4-2. Depends: wp10-fill-nan, wp1-m0-descending-step-orientation.
- [ ] **M0** `wp10-m0-wcs-lock`: Guard `_GlueWCS.pixel_to_world_values`, `world_to_pixel_values` and `axis_correlation_matrix` with one module-level `threading.RLock` (re-entrant: a `_GlueWCS` can wrap a sliced one; module-level: derived datasets share one astropy WCS). Export it publicly next to `_GlueWCS` in `glue_solar/sources/loaders/iris.py` (for example `WCS_LOCK`). Raw astropy WCS users (`data.coords._wcs`, `SlicedLowLevelWCS(raw_wcs)` in the WP2 and WP6 prototypes) go through `data.coords`, hold the lock, or deep-copy under it; WP2's rewrap and `wp6-m2-worker` build `SlicedLowLevelWCS` on the main thread, never in a Worker. It retires with `wp0-astropy-19174`. Done when a CI subprocess test with two threads each making 20,000 calls on one `_GlueWCS` of the irispy raster fixture exits 0, and 4000255147 Si IV in stock viewers (2 Image, 1 Profile), stepping the slice from 100 to 300, gives 0 crashes in 20 consecutive offscreen runs (today 4 of 8 threaded runs crash). If it still crashes with the lock, find the remaining shared state before M0 closes. Features: none. Findings: followup-2-1, followup-3-1.
- [ ] **M0** `wp10-m0-interaction-latency`: Add `_without_step_index(wcs)`, applied in `_cube_data` and to the stack's `target_wcs`: for a -TAB WCS with the exposure-index column (`PS3_2 = 'RASTER'`), rebuild it from `to_header()` without `PS3_2` plus a 2-node index, and use the rebuild only if both agree to 1e-12 at probe points (else keep the original and log). It retires with `wp0-irispy-tab-index`. No transposed cube; λ–t is an Image axis choice. If a budget still fails, use `QSlider.setTracking(False)` on the preset's `value_slice_center` sliders, then a numpy slit-table evaluator (exact to 1e-10″, 0.07-0.08 s/step), not a cache. Done when:
  - On 4000255147 Si IV a spectrogram slice step (set + draw) takes ≤ 0.10 s and stays within 20% across exposures 1, 800 and 1599.
  - The rebuild matches the original to 1e-12 deg (pixel→world) and 1e-9 px (world→pixel) at the far slit end and at fractional steps on 4000255147, 4000005156 and 3824262996.
  - The λ–t image at the selected point equals `cube[:, y, :]`.
  - The existing SJI tests in `test_importer.py` pass unchanged and SJI coords still wrap the gWCS.

  Features: F035, F022. Findings: followup-2-6. Depends: wp10-m0-wcs-lock.
- [ ] **M0** `wp10-m0-large-data-modal`: In `glue_solar/quicklook.py`, create the Profile viewer empty, set its instance `large_data_size = None`, then `add_data`, so the 1e8-point 'Add large data set?' modal (default Cancel) cannot abort the preset. The status bar notes the size, or why `add_data` returned False (the preset continues without the Profile layer); user settings and the class attribute are untouched. Done when, at real size and without monkeypatching `warn`, the preset opens with the Profile layer and `warn` is never called on the 4000255147 sit-and-stare windows (1.7e8-3.7e8 elements), 3824262996 Mg II k (2.35e8) and the 99-scan 3602506433 stack (4.6e8). Features: none. Findings: followup-2-5, usefulness-12. Depends: wp4-quicklook-preset.
- [ ] **M0** `wp10-m0-roi-guard`: Add an ImageViewer subclass to `glue_solar/quicklook.py` whose `tools` is glue-qt's `ImageViewer.tools` (read after `setup()` appends the solar tools) minus the five `select:*` tools (rectangle, xrange, yrange, circle, polygon); the preset creates its raster image viewers from it via `app.new_data_viewer` (D9). Done when a test shows the preset's raster viewers expose no `select:*` tool, and an SJI frame step with the Pixel point active stays within the `wp10-m0-acceptance` SJI step budget on 4000005156 with the deconvolved SJI 2796 (32×771×1506). Features: none. Findings: followup-4-4. Depends: wp4-quicklook-preset, wp1-m0-link-hpc.
- [ ] **M0** `wp10-m0-acceptance`: CI tier, on irispy fixtures: the `wp10-m0-wcs-lock` thread test, the index-free WCS equality check, and the `wp10-fill-nan`/`wp10-mask-uint8` fixture assertions. Data tier, `glue_solar/tests/test_performance.py`, skipped without `~/DATA/IRIS`: 4000255147 (sit-and-stare + SJI 1400), 4000005156 (2 scans + the deconvolved SJI 2796), 3824262996 (400-step Mg II), 3400109360 (`wp10-fill-nan` NaN positions, `wp10-m0-negative-step` probe, peak RSS) and 3602506433 (99 scans, memory only). It logs sizes, per-window load time (s/GB), latency, peak RSS, and the per-frame cost of a stock raster pixel ROI with `link_hpc` on the 4000005156 and 4000255147 raster/SJI pairs (followup-4-4; browser-opened viewers keep ROI tools (confirmed); `wp1-m0-link-hpc` needs this record before `browse_iris` installs `link_hpc` by default). Budgets (confirmed 2026-09-27) are fixed for the 24 GB reference machine (offscreen, warm cache; 1.5-1.9x headroom; the synced step rests on an unverified 0.22 s estimate) and change only by a recorded decision. Done when both tiers pass and the results, machine and load average are recorded with the M0 validation:
  - image slice step ≤ 0.10 s at any exposure index; λ–t slit step ≤ 0.15 s; Pixel click to drawn spectrum ≤ 0.35 s; SJI frame step ≤ 0.15 s;
  - one step across the preset's synced image viewers ≤ 0.25 s at exposures 1, 800 and 1599, of which WP4 sync uses ≤ 0.1 s;
  - `quicklook()` ≤ 3 s with no modal; WP4's cached nearest-index/offset state ≤ 1 MB; the `wp10-mask-uint8` memory budgets hold;
  - 0 crashes in 20 consecutive offscreen runs per scenario: the `wp10-m0-wcs-lock` stock-viewer scenario, and the quicklook with 3 Pixel clicks on 3824262996 Mg II k and on 4000255147.

  Load time and ROI cost have no budget; `wp10-nonblocking-load` gates load-time GUI gaps. Features: none. Findings: plan-integrity-8, followup-2-8, usefulness-12. Depends: wp10-fill-nan, wp10-mask-uint8, wp10-m0-negative-step, wp10-m0-wcs-lock, wp10-m0-interaction-latency, wp10-m0-large-data-modal, wp10-m0-roi-guard, wp4-quicklook-preset, wp4-m0-point-fixed-index, wp4-time-sync.

- [ ] **M1** `wp10-nonblocking-load`: Run the reads in `QtIRISImporter.finalize` (`raster_data`/`image_data`, `extract_archive`) in glue-qt's `Worker`, with the progress bar visible and OK disabled: build the Data in the worker touching no viewer-held WCS, extend `datasets` on the GUI thread, drop cancelled or superseded loads by load id, record each result through the `wp4-launch-entry` per-window helper, never `wait()` on the GUI thread, and check a stop between raster files (`raster_data` reads per file and assembles each window's sequence). Extraction, stop and 'Loading X failed' texts stay visible after the worker ends. `wp8-filter-stop` reuses this lifecycle (stop and discard on rescan, directory change, accept, reject and close). F201 is met by glue's plugin splash and Preferences 'Reset visibility of info messages and warnings'; no precomputation is needed. Done when:
  - Loading 3824262996 Mg II k or 4000255147 keeps GUI timer gaps ≤ 0.2 s.
  - A stop in the middle of the 3602506433 stack takes effect within one file, adds nothing half-built and leaves earlier picks usable.
  - The per-file assembly gives Data equal to the one-call read (values, `Time`, meta) on 4000005156.
  - Tests gate on counted reads, not sleeps, and the `wp10-m0-wcs-lock` and `wp10-m0-acceptance` crash scenarios still give 0 crashes.

  Features: F201. Findings: followup-2-9, usefulness-12. Depends: wp10-m0-wcs-lock.
- [ ] **M1** `wp10-m1-roi-world-polygon`: Override `apply_roi` on the `wp10-m0-roi-guard` subclass: for IRIS raster data, map the ROI edges, sampled once per raster step, through `_GlueWCS.pixel_to_world_values` into a `PolygonalROI` `RoiSubsetState` on the lon/lat component IDs; other data keep `roi_to_subset_state`. Then restore the five `select:*` tools. Done when, on 4000005156 Si IV with the deconvolved SJI 2796 at frame 5, a raster rectangle selects the same 108,300 SJI pixels as the pixel-cid subset (0 differing; range tools likewise) in ≤ 0.5 s per full-resolution SJI frame, and on sit-and-stare the result equals the pixel result exactly. If `wp1-m0-link-hpc` check (4) finds the sit-and-stare stripe inherent, sit-and-stare maps keep no `select:*` tools and that check is dropped; never assert equality with a stripe result. Features: none. Findings: followup-4-4. Depends: wp10-m0-roi-guard, wp1-m0-link-hpc.

- [ ] **M2** `wp10-m2-lazy-loading`: Open raster and SJI files with irispy `memmap=True` (`irispy/io/utils.py:148@0.9.0`: raw int16, no BSCALE/BZERO, `mask=None`; on 4000005156 a raw -31972 is -1 DN and fill reads -32768) and publish glue `DaskComponent`s computing `raw*BSCALE + BZERO`, the `wp10-fill-nan` rule and the uint8 mask per requested slice; build the 4D stack from lazy scans. Lazy opens use the `wp10-nonblocking-load` Worker; eager loading stays the default until the lazy path passes the same tests. Add `dask[array]` to `pyproject.toml` in the PR that first imports dask. Done when:
  - On 3824262996 (3.17 GB float32) and 4000255147 (4.14 GB), opening all windows lazily keeps peak RSS before any viewer opens below 10% of the eager peak (proposed threshold; record both values).
  - Sampled slices' values, NaN positions and masks equal the eager loader's, including on 3400109360.
  - GUI timer gaps during load stay ≤ 0.2 s, and the M0 budgets still hold, including the λ–t slit step.

  Features: F034. Findings: usefulness-12, followup-2-2, followup-2-9. Depends: wp10-m0-acceptance, wp10-mask-uint8, wp10-nonblocking-load.

- [ ] **M3** `wp10-m3-sit-stare-chunks`: Only if a recorded sit-and-stare run still exceeds 12 GB peak RSS or the M0 λ–t slit-step budget after `wp10-m2-lazy-loading`, add a sit-and-stare exposure-range field to the browser that slices the lazy cube before conversion, keeping the chunk's `Time` and WCS. Done when, on 4000255147 (1600 exposures), loading exposures 400-799 gives Data whose `Time` and world coordinates equal the full load's at those exposures, peak RSS scales with the chunk, not the file, and navigation inside the chunk is unchanged. Features: F036. Depends: wp10-m2-lazy-loading.

Notes and limits:
- Stack storage stays as on main: a `np.result_type(scan 0, float32)` memmap with scan 0's spatial WCS, not resampled (`wp1-stack-per-scan-wcs`). `irispy.io.read_files` still reads files; unstacked data keep detector arrays, uint8 masks, meta, units, WCS and exact exposure times.
- Why the lock: threaded Profile layers (above 1e7 elements) and histograms share the -TAB WCS with GUI-thread WCSAxes, and wcslib is not thread-safe (astropy#19174). Other WCS attribute reads stay unlocked (0 crashes in 18 locked runs). Crash tests run only in a subprocess.
- Raster world→pixel stays slow without the step index (31 µs/pt at 400 steps, 7 ms/pt on sit-and-stare); bulk SJI→raster mapping needs an analytic inverse.
- Outside the preset M0 stays stock: the 'profile-viewer' tool keeps the modal (`wp0-qt-large-data-cancel`), raster ROIs cost about 10 s per SJI frame with `link_hpc` until `wp10-m1-roi-world-polygon`, and histograms warn at 2e7 points. Timings are offscreen Agg at load average 3-11; on-screen, cold-cache and network-drive loads are unmeasured.

### WP11: Display, readouts and inspection tools

WP11 brings CRISPEX-level display and inspection to stock Glue Image and Profile viewers through `setup()` registries and one dock widget; its one private patch is gated (D2). Already on `main`: `solar:frame_time`, `solar:cursor_readout`, sliders, playback, alpha/mix and transparent NaN pixels.
- **M0:** the readout no longer shares the Pixel tool's icon. This is M0 because D6 makes Pixel the M0 selection tool, and the shared icon hides it.
- **M1:** labelled readouts with hover time, a selected-point panel, IRIS scaling and colour tables, physical aspect and navigation keys.
- **M2:** colour bar, distance and zoom tools.
- **M3:** optional conveniences; F120 keeps only its north-up rotation here.

#### M0

- [ ] **M0** `wp11-readout-icon`: Give `solar:cursor_readout` its own icon in `glue_solar/tools.py` (it shares `glue_crosshair` with Pixel), and name the 'Pixel' tool instead of 'the crosshair icon' in `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst:54`. Done when: on released glue-qt 0.4.2 an Image viewer shows different icons for 'Pixel' and 'Cursor readout', and the guide no longer mentions a crosshair icon. Features: none. Findings: solar-main-3.

#### M1

- [ ] **M1** `wp11-cursor-readout`: Split `CursorReadoutTool` so Qt #74 cannot remove the IRIS readout. The generic part, gated on glue-qt lacking `cursor_status` and with a `ProfileViewer` branch, retires with a Qt #74 release (`wp0-own-draft-updates` (2) aligns its labels) and shows pixel and world position, then value, from `pixel_to_world_values` at the full index as `Solar X`, `Solar Y` (arcsec to 0.01″) and λ (Å). The permanent `solar:frame_time` label adds the hovered pixel's `Time` and `Exposure time`, and km/s only with `meta.get("rest_wavelength")` (D11). Done when:
  - local 4000005156 Si IV scan-0 raster map, hovering step s: Solar X/Y equal `pixel_to_world_values` to 0.01″ at two zoom levels, λ is in Å, the label shows step s's UTC (within 1 ms of irispy's time extra coord) and exposure, and leaving the axes restores the frame range;
  - 4000255147 SJI_1400: the label shows the displayed frame's time; data without `Time` shows no time; km/s appears only with a rest wavelength;
  - a raster-spectrum Profile viewer reads x in Å (km/s: gated sub-check closed with `wp5-m1-velocity-axis`);
  - with `ImageViewer.cursor_status` monkeypatched in, the gated tool is absent and the label still shows hover time and exposure.

  Features: F100, F101, F113. Findings: followup-3-10, followup-3-11. Depends: wp4-exposure-readout, wp10-m0-wcs-lock, wp5-m1-rest-wavelength-policy (km/s only), wp1-m1-wrapper-coherence (Å).
- [ ] **M1** `wp11-selected-point-panel`: A read-only dock widget for CRISPEX's parameter overview, toggled by a `viewer_tool` and opened by the quicklook. For the Pixel point it lists, per dataset, pixel indices, Solar X/Y, λ and its index, km/s (only with `meta.get("rest_wavelength")`), scan/step, SJI frame, UTC, exposure and value, then the WP4 master and the signed SJI–raster offset or 'no match', taking other indices from WP4's `state.slices`. Done when:
  - CI, irispy 0.9.0 20140329 3860258481 raster (one scan as 3D, all scans as 4D), after a Pixel click: each field equals a direct read at the same indices (`pixel_to_world_values`, `Time`, `Exposure time`, `data[...]`) and persists after the mouse moves; closing the quicklook removes the panel and disconnects its callbacks; with the unrelated 3880012095 SJI_1400 fixture the SJI row shows 'no match';
  - local 4000255147 + SJI_1400: the SJI frame row equals WP4's nearest exposure, and switching the master shows the signed offset (D7);
  - sub-check closed with `wp1-m1-sji-to-raster`: a point clicked on either the SJI or the raster fills the other's rows.

  Features: F099, F191. Findings: plan-integrity-22, core-qt-capabilities-1. Depends: wp4-quicklook-preset, wp4-m0-point-fixed-index, wp4-time-sync, wp4-exposure-readout, wp1-m1-wrapper-coherence, wp5-m1-rest-wavelength-policy.
- [ ] **M1** `wp11-histo-opt-scaling`: Add a glue-solar 'Scaling' `SimpleToolMenu` for Image viewers (glue-qt 0.4.2 drops plain `Tool.menu_actions` menus); each subtool re-activates the mouse mode its click deactivates, as in `wp4-coordinator`. 'Histogram opt' (c = 1e-2, 1e-3 (IRIS) or 1e-4 (CRISPEX)) sets Custom limits `np.nanpercentile(layer_state.get_sliced_data(), [100·c, 100·(1−c)])`; 'Follow frames' re-applies them on slice changes; 'Per-frame auto limits' toggles `stretch_global`. No new percentile choices (restored sessions reject them). From M1, `wp4-quicklook-preset` calls the same helper (a WP11 change to `glue_solar/quicklook.py`). Done when: local 3610108077 after `wp10-fill-nan`, cutoff 1e-3: limits equal the displayed slice's nanpercentiles at 0.1 and 99.9, with v_min > −200; 'Follow frames' on: a wavelength step moves the limits to the new slice's percentiles; per-frame limits on: stock percentile limits change with the slider; a saved session restores the Custom limits. Features: F061, F064. Findings: followup-3-4, followup-3-2. Depends: wp10-fill-nan.
- [ ] **M1** `wp11-gamma-stretch`: In `setup()`, add 'Gamma 0.4', 'Gamma 0.75', 'Gamma 1.5' and 'Gamma 2.2' through `glue.config.stretches.add`, each a no-argument astropy `PowerStretch` subclass, skipping labels already registered. Done when: 'Gamma 0.75' is listed in the Stretch combo on released glue-qt 0.4.2; its rendered normalised values equal `PowerStretch(0.75)` of the linear ones; a session using it restores; calling `setup()` twice raises nothing; the IRIS-9 'gamma < 1' step works in the preset. Features: F062. Findings: usefulness-17, followup-3-4.
- [ ] **M1** `wp11-raster-cmap`: In `_raster_collection_data` (`glue_solar/sources/loaders/iris.py`), pass `cmap=` 'irissjiFUV' or 'irissjiNUV' for per-scan rasters and stacks from each window's `SGMeta.detector_band` (not the raw `TDET1`), read before stacking flattens the meta. Done when: on local 3610108077, layers default to irissjiFUV for C II and Si IV and to irissjiNUV for Mg II k and 2832; the same holds for a 2-scan 4000005156 stack; such a layer restores from a session. Features: F059. Depends: wp3-style-cmap.
- [ ] **M1** `wp11-physical-aspect`: A `viewer_tool` `solar:physical_aspect` (D9) wraps the private `state._set_axes_aspect_ratio` to scale the ratio by the displayed axes' arcsec-per-pixel ratio (|Δ| per axis; 1 unless both are helioprojective with non-zero steps) and re-runs `_on_resize()` on axis changes; the preset sets `aspect='equal'` on maps. D2 probe: no 'Physical pixels' aspect choice (WP11 drafts the glue-core PR, filed on the user's direction); `wp0-workaround-register` row. Done when, on released core: (a) local 4000005156 (about 12:1) and 3400109360 (about 3:1) render a 10″×10″ solar square as square within 5% at the preset size, after a resize and after a zoom; (b) the scale factor is 1.03 on the dense 3610108077 raster and 1 on sit-and-stare, and a restored session re-installs the tool. Gated sub-check (c), closed with `wp0-release-tracking`: with a release containing the upstream choice, (a) and (b) pass and the probe turns the workaround off. Features: F193. Depends: wp4-quicklook-preset, wp10-m0-negative-step, wp0-workaround-register.
- [ ] **M1** `wp11-keyboard-shortcuts`: Register plain keys for `ImageViewer`, `ProfileViewer` and the `wp10-m0-roi-guard` subclass in glue-qt's `keyboard_shortcut` registry: D/F previous/next frame on the WP4-synced axis, A/S previous/next wavelength, Space play/stop; steps wrap. In the quicklook and in Profile viewers, D/F move the WP4 master, A/S the wavelength index, and Space toggles `wp4-time-controls`; elsewhere Space calls the slice widget's private `_adjust_play` (a `wp0-workaround-register` row). Skip keys already registered and bind glue's Tab/Backspace functions to the subclass; name the keys in tool tips and the IRIS guide. Done when, on released glue-qt 0.4.2 with `QTest.keyClick`:
  - real SJI and raster viewers: D/F step ±1 with wrap, and Space starts and stops playback;
  - after clicking the slice widget's forward and stop buttons, and with its slider focused, Space toggles playback exactly once and D/F/A/S still step (else use another free key and document it);
  - quicklook, raster map active: D/F move the master and its synced partner, while A/S move only the wavelength index;
  - calling `setup()` twice raises nothing, and Tab and Backspace cycle and close windows from stock viewers and the quicklook raster map.

  Features: F197. Findings: followup-3-16, usefulness-17. Depends: wp4-quicklook-preset, wp4-time-sync, wp4-time-controls, wp10-m0-roi-guard.

#### M2

- [ ] **M2** `wp11-colourbar`: A checkable `viewer_tool` 'Colour bar' for Image viewers until glue releases one (glue #1087). It widens the right margin (`viewer.axes.resizer.margins`) and draws the reference layer's colorbar in an inset axes through glue's normalisation, contrast/bias and stretch chain, refreshed on layer and slice changes. Done when: on a raster and an SJI viewer, the bar's limits and colours follow limits, stretch (log, gamma), cmap, an `image:contrast_bias` drag (glue_qt/viewers/image/data_viewer.py:44@0.4.2) and slices with `stretch_global=False`; with aspect 'auto' and 'equal', the bar and its tick labels lie inside the figure bbox at the default viewer size; an `mpl:save` PNG includes the bar; toggling off removes the bar and restores the margins, and closing the viewer disconnects the callbacks. Features: F060. Depends: wp11-gamma-stretch.
- [ ] **M2** `wp11-distance-measure`: A checkable `viewer_tool` `solar:measure` for Image viewers: a press–drag–release line, kept until the next measurement, shows in the status bar pixels, arcsec (`angular_separation` of the ends' lon/lat from `pixel_to_world_values`, picked by `world_axis_physical_types` and wrapped in `world_axis_units`; not the high-level API before `wp1-m1-wrapper-coherence`) and km (× DSUN_OBS in metres; arcsec only without it). Expose the arcsec separation and the arcsec-to-km conversion as helpers in `glue_solar/tools.py`; `wp12-path-slicer`, `wp12-export-annotations` and `wp12-path-overlays-slopes` reuse them. Done when: on local 4000255147 SJI_1400 (CDELT1 0.16635″, DSUN_OBS 1.50921e11 m), a 100-pixel horizontal line reports 16.635″ within 0.01″ and about 12,172 km within 0.1%; on a 4000005156 raster map and on 3660259102 C II 1336, the arcsec value equals the endpoints' WCS separation; the tool is disabled on non-celestial planes (λ × slit) and leaves no artists after deactivation. Features: F131. Findings: followup-3-15.
- [ ] **M2** `wp11-zoom-steps`: Add one glue-solar `SimpleToolMenu` (subtools that restore the active mouse mode, as in `wp11-histo-opt-scaling`) with 'Zoom 1:1' (one data pixel per screen pixel), 'Zoom ×2' and 'Zoom ÷2' about the view centre. Done when, offscreen on an irispy 0.9.0 raster fixture: after 'Zoom 1:1' the axes width in screen pixels equals x_max − x_min; '×2' halves both ranges about the centre; Home restores the full view. Features: F097.

#### M3

- [ ] **M3** `wp11-centre-on-point`: Add 'Centre on selected point' to the `wp11-zoom-steps` menu, moving the view centre to `PixelSubsetState.get_xy` at the same zoom. Done when: afterwards the Pixel point lies at the view centre and both ranges are unchanged. Features: F098. Depends: wp11-zoom-steps, wp4-m0-point-fixed-index.
- [ ] **M3** `wp11-scaling-extras`: Two optional 'Scaling' actions. 'IRIS standard scaling' (SSW IRIS_INTSCALE) sets Custom limits at the 0.2 and 99.9 percentiles of finite values ≥ 0 over the cube (low 0.5 for SJI 2796) and a stretch: 'log' with `stretch_parameters={'a': v_max/v_min − 1}` for FUV and SJI 1330/1400, 'sqrt' for NUV, 'Gamma 0.75' for SJI 2796, 'linear' for SJI 2832. 'Match scaling' copies v_min/v_max/stretch/stretch_parameters/cmap to the same dataset's layers in other viewers. Done when: local 3610108077 Si IV (log) and Mg II k (sqrt), 4000255147 SJI_1400 (log) and 4000005156 SJI_2796 (γ 0.75): the action sets that stretch, with limits equal to those percentiles within 1e-6 relative; for the log cases, rendered values equal (log10 x − log10 v_min)/(log10 v_max − log10 v_min) within 1e-6; 'Match scaling' then gives a spectrogram viewer and a λ–t viewer of the same stack identical settings. Features: F066, F067. Depends: wp11-histo-opt-scaling, wp11-gamma-stretch.
- [ ] **M3** `wp11-band-average`: A band width of 1, 5, 9 or 15 wavelength pixels (CRISPEX default 5) for map views, written as Profile Collapse's `AggregateSlice` (nanmean over ±N). glue-qt's `sync_state_from_sliders` turns it into an int on any slider change, so a `slices` callback re-applies it (D2; probe: an `AggregateSlice` on another axis returns as an int after a slider sync; `wp0-qt-aggregate-slice` names the upstream fix; `wp0-workaround-register` row). Done when, in a map view of a ≥4-scan stack of local 3602506433 with N=2: the displayed array equals `nanmean(stack[scan, :, :, k-2:k+3], -1)`; stepping the scan slider keeps the band (stock glue drops it), and stepping wavelength moves it; `solar:frame_time`, the cursor readout and `wp4-time-sync` accept the `AggregateSlice` without errors. Features: F083. Depends: wp0-qt-aggregate-slice, wp0-workaround-register, wp4-time-sync.
- [ ] **M3** `wp11-north-up`: An optional north-up view for rolled SJIs: a north-up helioprojective grid (TAN WCS over the SJI FOV, same frame count) as reference data, linked to the SJI with `link_hpc` plus a frame-axis pixel `LinkSame` (D1), so glue's reprojection rotates the display. First a probe must confirm 3D-onto-3D reprojection through mixed world and pixel links, and `wp1-m0-link-graph-regression` must pass with the helper present. Done when, on the rolled local 3860608353 SJI_2832 (SAT_ROT 45°): solar north is up within 0.5°; the cursor readout on the rotated view matches the SJI's own WCS value within one SJI pixel; frame stepping still works. Features: F120. Depends: wp1-m0-link-hpc, wp1-m0-link-graph-regression.

#### Notes and limits

- **SJI coordinates.** SJI world values are correct once `wp1-m0-sji-crpix` (M0) is active. That item keeps the 0.05 px check; the upstream report is `wp0-irispy-crpix` (followup-4-3).
- **Keys.** glue-qt dispatch matches the exact viewer type, passes only the session, ignores modifiers and skips keys the focused widget consumes. B, C, G, H, K, M, P, R, W, X, Y, Z, Tab, Backspace and L (`solar:path`, `wp12-path-slicer`) are already taken.
- **Upstream.** glue-qt's `sync_state_from_sliders` bug also breaks stock Profile Collapse on 4D stack maps; `wp0-qt-aggregate-slice` reports it. F067's interpolation preference is declined.
- **Owned elsewhere or declined.** The playback range and Go to UTC (followup-3-12) belong to `wp4-time-controls` (M1); fps, frame increment and bounce belong to `wp4-playback-extras` (M3). Declined: a CRISPEX control-panel clone (F191) and, for F097, wheel or keyboard zoom and a zoom-% readout.

### WP12: Export and derived diagrams

Goal: CRISPEX's export and derived diagrams (gap-aware time axes, x–t and spectral path diagrams, multi-window light curves) through glue registries and core's released `BasePathSlicerMode`/`PathSlicedData`, in `glue_solar/export.py`, `glue_solar/paths.py` and `glue_solar/sources/derived.py`. glue already has `mpl:save`, playback and glue-qt 0.4.2's 3D 'slice' tool (P; no Data, no 4D; draft glue-qt #66 deletes it), which WP9 documents for SJI x–t until M2.

WP12 is the only home of movie, sequence and path work (plan-integrity-15). Each WP12 PR adds its own guide section (the WP9 rule): 'Regrid on time' (next to the `wp9-m0-workflow-recipes` exposure-axis caveat), 'Solar path (3D/4D)' (L) and its crosshair, sequence and movie export, the FITS exporter (not Level-3; -TAB exports need astropy with the HDUList, not `sunpy.map.Map`), the ECSV exporters and light curves.

**M1**

- [ ] **M1** `wp12-time-regrid`: D7's M1 time-axis adapter: a D4 `layer_action` 'Regrid on time' (`glue_solar/sources/derived.py`) adding a Data (confirmed) rather than feas F142's in-place `_GlueWCS` step-as-time variant, regridded at the median Δt of `Time` from a sit-and-stare exposure, SJI frame or fixed-step stack scan axis. Each pixel takes the nearest exposure within 0.75 × median, else NaN; `Time` holds source times (NaT in gaps; one exposure may fill two pixels); the WCS axis is 'Time since start' (s from DATEREF, distinct from `Time`). Spatial axes copy the middle matched exposure's calibration. The Data is therefore marked in `meta` and excluded from `link_hpc` (confirmed; this item adds that check in `glue_solar/sources/loaders/iris.py`), and the index Data stays the navigation source. Done when: on 4000255147 Si IV (1600 exposures, cadence 2.71–3.29 s, median 2.89 s) the Data has ceil(span/2.89)+1 time pixels, 0 NaN columns, each column equal to its nearest exposure; with 10 consecutive exposures removed, NaN columns appear only inside the gap; 4000255147 SJI 1400 (400 frames) and a fixed-step stack of ≥ 4 scans of 3602506433 pass the same checks; WCSAxes labels the axis 'Time since start' (s); exactly one Data is added, with no viewer and no `link_hpc` link; the step axis of 4000005156 scan 0 is refused with a message; the Data survives a WP3 session round trip, rebuilt from the source label, axis, fixed index and grid in `meta`. Features: F089, F090. Findings: plan-integrity-7. Depends: `wp3-wcs-saver` (session rebuild), `wp1-m0-link-hpc`.

**M2**

- [ ] **M2** `wp12-sequence-export`: `viewer_tool` `solar:save_sequence` (`glue_solar/export.py`), appended to 'save' after `setup()` sets `ImageViewer.subtools = deepcopy(ImageViewer.subtools)`, steps one slice axis over a range prefilled from `wp4-time-controls`, with frozen colour limits and a Cancel button, then restores slice, master and axes. Frames: `figure.savefig` (axes off until glue #2128) or whole-window `GlueApplication.screenshot()` (viewer as D7 master). Movies: `FFMpegWriter` MP4 if ffmpeg is on PATH (not a dependency), else `PillowWriter` GIF. Done when an offscreen pytest on 4000255147 SJI_1400 shows: frames 0–9 give 10 PNGs with identical colour limits, frame i equal to `mpl:save` at slice i; whole-window mode writes 10 window-size PNGs and restores the previous master; a 20-index wavelength scan on a 4000005156 raster map writes 20 PNGs; the GIF has 10 frames (PIL `n_frames`), the MP4 10 if ffmpeg is present (else skipped); Cancel after 3 frames keeps and labels the partial output and restores the slider; `MatplotlibDataViewer.subtools['save'] == ['mpl:save']` and no Scatter or Histogram 'save' list has `solar:save_sequence`. Features: F178, F179. Findings: core-qt-capabilities-9. Depends: `wp4-time-sync`, `wp10-m0-interaction-latency`, `wp4-time-controls` (range prefill only).

- [ ] **M2** `wp12-derived-data-export`: `data_exporter` 'FITS (IRIS WCS + Time)' (`glue_solar/export.py`) for Data with `_GlueWCS` over an astropy `WCS` (WP2 moments, WP6 fits, WP5 Doppler image, sliced raster maps, wrapped sunpy maps); other Data (gWCS SJI/AIA, light curves, `PathSlicedData`, tables) is refused by name. Output: one ImageHDU per numerical component with the raw WCS header (m, deg; sliced maps: `raw.sub(<kept axes>)` plus a WAVELNTH or comment card), a WCS-TABLE HDU for `-TAB` axes (WP3's module-level record), the uint8 mask, and `Time` as MJD, TIMESYS='UTC'. `-TAB` exports need the HDUList (`WCS(header)` alone raises) and do not open in `sunpy.map.Map`; a linearised TAN header is not planned. Done when, on 4000005156 Si IV scan 0, its WP2 moments map and a sliced raster map: `WCS(header, fobj=hdul)` reproduces glue's world coordinates at 5 pixels within 1e-6 arcsec/Å after unit conversion and ±180° wrapping; the sliced map's header records its fixed wavelength; `Time` round-trips within 1 ms and the mask HDU equals the mask; a WP6 fit map exports all its parameter components; `sunpy.map.Map` opens the export of a sunpy map; exporting an SJI or a WP12 light curve raises the message. Features: F182, F187. Findings: followup-3-8. Depends: `wp3-wcs-saver` (`-TAB` record), `wp2-m2-moment-maps`, `wp6-m2-fit-maps`, `wp6-m2-products`, `wp5-m1-doppler-image`, `wp1-m1-sunpy-maps` (sunpy-map case only).

- [ ] **M2** `wp12-point-light-curves`: D4 `layer_action` 'Light curves at this point' (`glue_solar/sources/derived.py`) on a bare Pixel subset (never ANDed with a band) adds one 1D Data (datetime64 `Time`, value, optional mean normalisation) per chosen raster window (an index, or `nanmean` over ±N) and per SJI or AIA channel, `LinkSame`-linked on `Time` and value to the first curve (else Scatter disables the other layers); no viewer opens. SJI frame t samples the point's world position at the WP4-matched exposure via the per-frame SJI WCS, not the link graph (D8). AIA channels are loaded `aia_l2` cutouts, sampled like SJIs; single images fetched by WP7 get no curve. The D9 coordinator recomputes them on subset updates and re-attaches them after a restore from their `meta`. Also a `data_exporter` 'ECSV (with Time)' for 1D Data, `Time` as ISO UTC (.cint parity). Done when, on 4000255147 with a point at slit pixel y: curves exist for Mg II k (index nearest the line-list 2796.35 Å), the C II core and SJI 1400; raster curves equal `cube_w[:, y, k]` (1600 samples) and the band variant `nanmean(cube_w[:, y, k-N:k+N+1], -1)`; the SJI curve has 400 samples equal to `sji[t, row(t), col(t)]`, NaN at NO MATCH frames; mean-normalised curves average 1; all curve layers are enabled in one Scatter viewer with date ticks reading 2013-09-02; dragging the point updates every curve and the `solar:time_marker` follows the master frame, also after a WP3 session round trip; the Mg II k and SJI 1400 curves re-read from ECSV with `Time` within 1 ms; `wp1-m0-link-graph-regression` passes with the curve links. Features: F140, F141. Findings: core-qt-capabilities-2, plan-integrity-7. Depends: `wp4-time-sync`, `wp1-m0-link-hpc`, `wp10-fill-nan`, `wp7-goes-marker` (`solar:time_marker`), `wp7-goes-date-labels` (#2599 or its gated workaround), `wp3-coordination-reattach`.

- [ ] **M2** `wp12-path-slicer`: 4D solar-coordinate path diagrams (`glue_solar/paths.py`) on core's path slicer, not the legacy PV widget. The glue-core floor (1.27.0 from `wp1-m0-irispy-baseline`) covers `BasePathSlicerMode` (1.26.0); if the user rejects that default, raise it to >=1.26 here. `solar:path` ('Solar path (3D/4D)', key 'L') and `solar:path_crosshair` subclass `BasePathSlicerMode` and `BasePathSlicerCrosshairMode`. `_on_reference_data_change` allows 3D/4D; `_open_or_update` builds one `PathSlicedData` per raster, SJI or AIA layer from vertices converted into that layer's own pixel frame via world coordinates at the WP4 master frame, sampling that layer's own pixel components (core passes the reference layer's `x_att`/`y_att` to every layer, `common.py:77-90`@1.27.0), storing drawn and reference-frame vertices in `meta['solar_path']`, which `_refresh_overlays` and crosshair `activate` draw; `_on_move` moves only the represented parent axis (nearest-exposure arrays for other layers, D8). Core's pixel-to-pixel path links stay (not main-to-pixel, D8). Axes: cumulative arcsec 'Distance along path' at the master frame, UTC on exposure and scan axes. Distances use the `wp11-distance-measure` separation helper (low-level lon/lat, `angular_separation`), never the high-level API, which raises a latitude error on raster maps until `wp1-m1-wrapper-coherence`. If a glue-qt release has #66 first, subclass its tools. Done when: on 4000255147 SJI 1400 (400×417×388) a 3-vertex path adds a (400, N) Data with an arcsec path axis and a UTC frame axis; the 4000255147 sit-and-stare raster gives (λ, N) and a ≥ 4-scan 3602506433 stack (scan, λ, N); with the 4000005156 two-scan stack and SJI 2796 in one viewer (probe-gated sub-check: it runs once a `wcs_autolink` probe finds #2595 and closes with `wp1-m1-autolink-matrix`), each layer gives one trace, samples agree within 0.5 px at the master frame, and clicking frame t in the SJI trace's diagram sets the raster scan slider to the WP4-matched exposure's scan; clicking a raster result moves only the represented parent slider; no two Image-viewer tools share a shortcut; a signature test of the overridden private hooks passes on released 1.27.0; `wp1-m0-link-graph-regression` passes with a path product present. Features: F135, F137. Findings: core-qt-capabilities-3, upstream-state-8. Depends: `wp1-m0-link-hpc`, `wp4-time-sync`, `wp0-track-qt66`, `wp0-workaround-register`, `wp11-distance-measure`.

- [ ] **M2** `wp12-path-persist`: Session saver and loader for `PathSlicedData` (core has none) storing the parent, pixel components and `meta['solar_path']` (vertices in pixels and arcsec, master frame, spacing, sampling mode, line style). The loader rebuilds via `set_xy(vertices, spacing)` in arcsec, never from `psd.x`/`psd.y`, and sets `parent_viewer` if a viewer shows the parent (D9), else crosshair navigation stays off. 'Save path'/'Load path' on the `solar:path` menu use ECSV. Done when, on 4000255147 SJI 1400 and a two-scan 4000005156 stack, a drawn path survives two session save/reopen cycles with identical `PathSlicedData` shape and values and stored vertices within 1e-9 px; a saved path ECSV reloads to the same diagram; 'Export data values' as FITS writes every numerical component without a WCS header, and HDF5 raises on `Time` until `wp0-core-datetime-export` is fixed; the product at any retained index (another wavelength or scan) equals the parent sampled along the path. Features: F185, F186. Findings: followup-3-8, followup-3-15. Depends: `wp12-path-slicer`, `wp3-wcs-saver`, `wp3-app-session-acceptance`, `wp3-session-budget` (no embedded arrays), `wp0-track-qt66`.

**M3**

- [ ] **M3** `wp12-export-annotations`: Fixed options on `solar:save_sequence` (one index gives one frame): UTC text (the `solar:frame_time` value), an arcsec scale bar (`AnchoredSizeBar`, sized with the `wp11-distance-measure` separation helper), frame numbers, and an editable default name `<OBSID>_<STARTOBS>_<label>_<axis><i0>-<i1>.<ext>`. Done when, on 4000255147 SJI_1400: frame i's text equals Time[i] (ISO, 0.01 s); a 10-arcsec bar spans 10/CDELT1 pixels ±1 px; frame numbers equal the slice indices; the dialog proposes the default name and accepts an edit; a visible subset overlay appears in the PNG. Features: F133, F181, F183. Depends: `wp12-sequence-export`, `wp11-distance-measure`.

- [ ] **M3** `wp12-profile-values-export`: `viewer_tool` `solar:save_profile` (Profile 'save', after `setup()` sets `ProfileViewer.subtools = deepcopy(ProfileViewer.subtools)`, as `wp12-sequence-export` does for `ImageViewer`; glue-qt 0.4.2 defines `subtools` only on `MatplotlibDataViewer`) writes each visible layer's `ProfileLayerState.profile` to one ECSV (the `wp12-point-light-curves` writer) with x name and unit, layer or subset label, a Pixel subset's pixel and world position, and per-sample UTC when x is a sit-and-stare exposure or stack scan axis (.cint parity). Done when, on the 4000255147 sit-and-stare with a Pixel subset and x on the exposure axis: re-read x/y equal the viewer's profile arrays; the Time column equals `Time` at that pixel; two visible layers give two column sets; empty layers are skipped with a note; no Scatter or Histogram 'save' list has `solar:save_profile`. Features: F184. Findings: archive-trace-18. Depends: `wp12-point-light-curves` (ECSV writer).

- [ ] **M3** `wp12-path-overlays-slopes`: `solar:path` draws every saved path (restored `wp12-path-persist` products, loaded path ECSVs) on any viewer showing the parent, with a line style (solid, dotted, dashed) and optional 'only at wavelength index w' in `meta['solar_path']`. A TANAT-style two-click slope readout on distance–time diagrams gives projected speed in km/s (the `wp11-distance-measure` helper: km = sep[rad] × DSUN_OBS[m] / 1000; Δt from `Time`) and a three-point parabolic acceleration, appended with an ID and flag to an ECSV table. Done when: after a WP3 session round trip and after 'Load path', saved paths are drawn with their line styles and wavelength-restricted paths appear only at index w; on an x–t diagram from a copy of 4000255147 SJI_1400 with an injected feature of known slope and acceleration, speed is recovered within 1% and acceleration within 2%; ECSV rows round-trip. Features: F127, F132. Findings: followup-3-15. Depends: `wp12-path-persist`, `wp11-distance-measure`.

- [ ] **M3** `wp12-path-batch`: 'Re-extract along this path' `layer_action` applies a saved path (ECSV or stored arcsec vertices) to other ticked datasets and windows, converting as `solar:path` does. A `PathSlicedData` subclass overriding `_get_pix_coords`/`get_data` adds 'nearest' (`np.rint`, CRISPEX's default) and 'linear' (`scipy.ndimage.map_coordinates(order=1)`) beside core's truncation; `meta['solar_path']` records the mode. Done when: a path saved in a session and re-extracted on another 4000005156 window uses identical vertices; re-extracting over all ticked windows adds one product each; on a synthetic ramp cube 'nearest' equals `np.rint` sampling and 'linear' matches `map_coordinates(order=1)` to 1e-6; the default still equals stock `PathSlicedData`. Features: F138, F139. Findings: followup-3-15. Depends: `wp12-path-persist`.

**Notes and limits**

- **Pointing.** Paths, SJI traces and SJI curves use the WP4 master frame or matched exposure; a fixed pixel path ignores pointing drift (D1). Stack paths use the scan-0 WCS until `wp1-stack-per-scan-wcs` (M3).
- **Stock exporters.** glue's gridded FITS writer drops non-astropy WCS and datetime64 `Time` (`gridded_fits.py:52`@1.27.0); other formats fail on datetime64 (`wp0-core-datetime-export`).
- **Not rebuilt.** CRISPEX phi-slit sliders (a polyline covers them), path width, IDL .csav/.clsav/.cint/.cses (FITS, ECSV and sessions replace them), Level-3 writing and EIS.
- **Upstream (WP0).** The private hooks overridden are `BasePathSlicerMode._on_reference_data_change`, `_open_or_update` (multi_trace.py), `_refresh_overlays` and `BasePathSlicerCrosshairMode._on_move` (`wp12-path-slicer`), and `PathSlicedData._get_pix_coords` (`wp12-path-batch`), all at 1.27.0; the `wp0-workaround-register` 'Path tools' row covers them, each with its `wp0-optional-proposals` offer. WP0 tracks glue #2128, #2599 and glue-qt #66 (`wp0-track-qt66`).

## Prototypes: what to port

Yes, some prototypes are still needed: about a dozen hold code or tests worth
porting. None is copied over glue-solar wholesale. Each port lands on a
feature branch from `main`, together with the fixes listed. On 2026-09-27,
186 historical probes, logs, diffs and reports moved to
[archive/probes-2026-09](IRIS_PLAN_PROTOTYPES/archive/probes-2026-09/). Nothing
was deleted. Full verdicts, including verifier corrections, are in
[review_20260927/protos.json](IRIS_PLAN_PROTOTYPES/review_20260927/protos.json).

| Prototype (under `IRIS_PLAN_PROTOTYPES/`) | Port | To (WP, milestone) | Fix first |
| --- | --- | --- | --- |
| `wp1/glue_solar/`: `link_hpc`, browser call, link menu action, gated `glue_patches`, axis-name flip | Port | `sources/loaders/iris.py`, `sources/iris.py`, `glue_patches.py` (WP1, M0) | Delete the `"time": "Time"` axis-name entry with the flip, or the SJI gets two `Time` components; the gate is a behaviour probe (D2) |
| `wp1/glue_solar/sources/loaders/iris.py`: unit and high-level `_GlueWCS` hunk | Parts | `sources/loaders/iris.py` (WP1, M1) | `_converting_constructor` argument order (`wp1-links-7`) |
| `wp1/glue_solar/tests/test_linking.py` | Port | `tests/test_linking.py` (WP1, M0 subset, rest M1) | Use `find_irispy_test_file` (irispy 0.9.0 names, `wp1-links-4`) |
| `review_20260927/probes/linkgraph/test_linkgraph.py` | Parts: the order/allocation matrix and checks (a), (c)-(e) | `tests/test_linking.py` CI variant (WP1, M0) | Drop the pixel-ID time-link and design-B link sets (D8); `wp4_common.link_time` is not ported |
| `wp1/glue_solar/tests/test_importer.py` | Three hunks only | `tests/test_importer.py` (WP1) | Do not copy the file; it reverts #50/#52 (`wp1-links-5`) |
| `wp4_common.py`: `nearest`, `exposure_times`, `observation_key` | Parts | `glue_solar/quicklook.py` (WP4, M0) | `nearest` must accept unsorted/duplicate references and return offset plus a no-match flag (D7, D10). Nothing else is ported: time links, slit subset, sync wrapper and the old `quicklook` are replaced (D8, D9) |
| `slit_check.py`, approach C | Parts | WP4 slit overlay (M0); raster footprint (F125, M1) | Use `nearest` and the no-match rule; select lon/lat by physical type; keep per-frame arrays compact |
| `review_20260923/test_existing_workflows.py` | Parts | `tests/test_quicklook.py` (WP4, M0; Navigate test M1) | Gate the display-unit branch on a Qt #70 capability, not on core (`core-qt-capabilities-8`) |
| `review_20260905/test_refresh.py` | Parts | `tests/test_quicklook.py` (WP4, M0); blink test to WP5 | Flip the encoded defects: descending references accepted, no match instead of clamping |
| `review_20260923/test_wcs_capabilities.py` | Parts | `tests/test_linking.py` (WP1, M1, gated on #2595 behaviour) | Assert footprint columns and frames, not "any pixel selected" (`wp4-quicklook-12`) |
| `review_20260905/run_checks.py` (+ `qs_isolate.py`) | QSettings isolation only | autouse fixture in `glue_solar/conftest.py` (WP8, M0) | The runner alone writes the real macOS QSettings (`plan-integrity-2`) |
| `wp3_impl.py` | Parts | `_GlueWCS.__gluestate__`/`__setgluestate__`, scoped styles, named factories (WP3, M1) | Write the index column only where `PSi_2` exists (`followup-2-6`); follow the derived-map contract and raise `GlueSerializeError` otherwise (`wp3-wp5-3`); integer slices (`wp3-wp5-14`); guarded Quantity saver (D13) |
| `wp3chk_test_sessions.py` | Port | `tests/test_sessions.py` (WP3, M1) | Fixture names; 100 KB size budget; production class paths |
| `chk_wp2/wp2_moments_module.py` and `chk_wp2/test_wp2_moments.py` | Port | `sources/moments.py`, `tests/test_moments.py` (WP2, M2) | Wings required; D11 rest (irispy 0.9.0 still falls back to TWAVE when rest is None); saveable map WCS; NaN/Inf handling |
| `wp2_moments_proto.py` | Keep until two checks become tests | WP2 tests | The TWAVE fallback check and the layer-action trigger check |
| `wp5_units.py`, `wp5_override.py` | Parts | `glue_solar/spectral.py` (WP5, M1) | No global unit narrowing (`usefulness-6`); no TWAVE fallback (D11); no import-time side effects |
| `iris_lines.csv` | Port, extended | `glue_solar/data/iris_lines.csv` package data (WP5, M1) | Add Fe XII 1349.40, the Mg II triplet, O IV 1404.78, S IV 1404.81/1406.02, Fe XXI 1354.106, Ni I 2799.474 and S I 1401.515, with `source`, `default_for` and `calibration` columns (`wp5-m1-line-list`) |
| `wp5_linelist_mod.py` + `review_20260905/test_line_positions.py` | Parts | `spectral.py`, `tests/test_linelist.py` (WP5, M1) | Delete the exact-class style dict and keep the stock style editor (`wp3-wp5-15`); `np.interp` instead of `brentq` (`wp3-wp5-17`); add an IRIS-raster session case |
| `wp5_blink.py` | Timer/restore skeleton only | `tools.py` (WP5, M1) | Blink alternates (dataset, slice) pairs, for same-cube and cross-window blink (`followup-3-6`) |
| `wp5_label.py` | Upstream PR only | glue-core Profile axis label (WP0, optional) | Not a solar monkeypatch |
| `wp6_fitting.py`, `wp6_test_fitting.py` (+ two asserts from `wp6_test_fitting_final.py`) | Parts / port | `sources/fitting.py`, `tests/test_fitting.py` (WP6, M2) | Use the source mask via `mask=`; no clipping; reject amp ≤ 0 / out-of-window / unconverged fits and publish \|sigma\|; float32 opt-in residual; fixture names |
| `wp6_fitting_brief.py` | Archive once `review_20260905/test_plan_integration.py` drops its parameter and this index drops it (`usefulness-7`) | none | none |
| `wp6_chk_real_fixed.{py,log}`, `wp6_full_raster.{py,log}` | Test evidence | WP6 4-D stack test (archive `wp6_chk_real_fixed` once `tests/test_fitting.py` has it) and the WP6 budget baseline (`wp6-m2-worker`) | none |
| `wp7chk/context_chk.py`, `test_context.py`, `conftest.py` | Parts | `sources/context.py` (WP7, M2) | Off-limb crop (`wp7-wp8-1`); XRS quality flags; fixture names |
| `wp0_bug_epoch_viewer.py` | Test evidence | WP7 date-label test, gated until #2599 is released | none |
| `archive/probes-2026-09/wp7_timelink.py`, `wp7_goes.py` | Parts: the success-path recipe (viewer, log axis, time link) | `tests/test_context.py` (WP7, M2) | Not `wp7_goes.py`'s `EPOCH=1` `rcParams` path; update the pre-0.9.0 fixture name (`wp7-wp8-8`) |
| `wp8_scan.py`, `wp8_proto.py`, `wp8_loader.ui` + `wp8_test_proto.py`, `wp8_test_shipped.py`, `wp8_chk_test_text.py`, `wp8_chk_proto_fix.py` | Parts / port | `sources/loaders/scan.py`, `iris.py`, `iris_loader.ui`, tests (WP8, M2); the Worker pattern also serves `wp10-nonblocking-load` (M1) | Load during rescan (`wp7-wp8-2`); stop inside the directory walk (`wp7-wp8-3`); "Scan stopped" wording (`wp7-wp8-11`); event-based tests (`wp7-wp8-12`) |
| `review_20260927/probes/wp10/unit_thread.py` | Port | `wp10-m0-wcs-lock` CI subprocess test (WP10, M0) | Replace `<session-scratch>` sys.path entries; fixture via `find_irispy_test_file` |
| `review_20260927/probes/wp10/noindex_fix.py` | Parts | `_without_step_index` (`wp10-m0-interaction-latency`, M0) | Keep the 1e-12/1e-9 agreement check |
| `review_20260905/test_plan_integration.py` | WP6 round-trip test only | `tests/test_sessions.py` (WP6, M2) | Drop the stubbed quicklook test and the brief-variant parameter |
| `review_20260923/README.md` | Reference only | none | Its SJI (25,25) → step 3 figures are specific to the irispy 0.8.1 fixture (step 40 on 0.9.0); `wp0-readme-runner` replaces its `.venv` runner lines |

## Deferred work and non-goals

- **Permanent non-goals:** Level-3 FITS writing and EIS support.
- **Excluded by the user on 2026-09-27:** the detector mosaic viewer, the
  OBS XML table viewer and the pipeline-log viewer.
- **Not applicable to IRIS:** Stokes/polarimetry workflows and SST/CRISP-only
  inputs. Broader instrument loaders (SST, DKIST, generic NDCube) remain
  outside this plan.
- **No IDL clone:** no pixel-identical widget layout, no IDL PostScript-device
  workflow (Glue's Save menu already writes PS/EPS; `wp9-m0-browsing-recipes`)
  and no generic annotation/plugin framework. Glue viewers, registries and presets
  provide the equivalents listed in the companion file.
- **Deferred inside the plan (with a milestone, not dropped):**
  - Per-scan absolute WCS inside the 4D stack. The forward gWCS table model
    works; its inverse for links and subsets is the open problem. Load scans
    separately meanwhile (`wp1-stack-per-scan-wcs`, M3).
  - Lazy/dask loading. It needs irispy scaling and fill applied lazily, or a
    glue-solar dask component (`wp10-m2-lazy-loading`, M2;
    `wp10-m3-sit-stare-chunks`, M3).
  - Physical UTC axes on the index datasets themselves. `wp12-time-regrid`
    (M1) instead adds a separate regridded Data for sit-and-stare exposures,
    SJI frames and stack scans; nothing else is scheduled.
  - A decoded `irispy.obsid.ObsID` display (browser tooltips,
    `wp8-browser-metadata`, M3).
- **Recorded for context:** 4D moments and wings from a Profile range are
  WP2 M3 (`wp2-m3-moments-extensions`); red–blue asymmetry is WP6 M3
  (`wp6-m3-rba-double-gaussian`). Density and temperature diagnostics are in scope
  (WP2, M3); they need two intensity maps plus CHIANTI/fiasco.

## Validation, environments and data

Run all Python in a micromamba environment, never the solar `.venv` or the
system Python.

- Reference environment `iris-plan` (`~/mamba/envs/iris-plan`): released
  glue-core 1.27.0 (conda-forge), glue-qt 0.4.2 (PyPI wheel installed with
  `--no-deps`, because conda-forge has no osx-arm64 glue-qt newer than the
  noarch 0.2.0; linux-64, osx-64 and win-64 have 0.4.2), PyQt5,
  irispy-lmsal 0.9.0, ndcube 2.4.2, astropy 8.0.1, sunpy 8.0.0 with the timeseries
  dependencies (cdflib, h5netcdf), pytest with pytest-doctestplus and
  pytest-qt, Python 3.13, glue-solar editable. Baseline: `glue_solar` gives
  34 passed, 1 skipped.
- `iris-plan` has no pytest-mpl, so glue and glue-qt `@visual_test` image
  comparisons do not run. Pass counts (for example in
  `wp0-stack-validation`) do not certify rendering; record this as a
  validation limit.
- The existing `glue-solar` micromamba env imports glue, glue-qt and irispy
  editable from the checkouts. Its irispy checkout is on
  `gwcs_raster_clean`, which breaks the raster loader (D14), so do not use
  it for baselines. If a check needs a different package set (for example
  irispy 0.8.1), create a new named env rather than changing an existing one.
- Runner, from the glue-solar root, with an isolated `HOME` and QSettings:

  ```sh
  env HOME="$(mktemp -d)" PYTHONPATH=IRIS_PLAN_PROTOTYPES/review_20260905 \
    ~/mamba/envs/iris-plan/bin/python -B IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py \
    "$PWD:$PWD/IRIS_PLAN_PROTOTYPES/review_20260905" glue_solar -p qs_isolate
  ```

  `run_checks.py` sets offscreen Qt/Agg and temporary Glue, Matplotlib and
  SunPy config directories. `qs_isolate.py` redirects
  `QSettings('glue-solar', 'glue-solar')` to a temporary INI file; without
  it, the importer tests overwrite the user's real `iris.last_dir`. Once
  `wp8-test-qsettings` lands, drop the plugin.
- Unreleased PR sources are prepended as extra roots. Exports are
  disposable, and macOS periodic cleanup purges `/tmp`. Regenerate one before
  use with `git -C <repo> archive <head> | tar -x -C <scratch>/<name>`, using
  the heads above. An emptied export directory shadows the installed package
  as a namespace package and breaks imports, so drop missing roots. Do not
  combine upstream core and Qt repository suites in one pytest run: their
  conftests register the same option.
- Keep actual import paths and installed metadata distinct when testing a
  source export. Never spoof a version to pass a feature gate. Mock modal
  dialogs in headless tests.
- Fixtures: use `glue_solar/conftest.py` `find_irispy_test_file`, which
  handles both the 0.8.1 names and the 0.9.0 `*_test.fits` names. Prefer the
  `sns/` copy when raster names repeat. irispy 0.9.0 bundles full windows
  decimated 10x, so expectations measured on 0.8.1 cropped windows fail;
  derive expected values from the fixture. Choose explicit in-window
  wavelengths for numerical checks and do not call them physical validation.
- Real data for acceptance and performance checks is in `~/DATA/IRIS`
  (listed under M0). Those checks are manual gates; CI uses the irispy
  fixtures.
- Other local data the work packages use: 20180102_153155 OBSID 3610108077
  (raster), 20210429_110908 OBSID 3660259102 (raster), 20250519_165924 OBSID
  3640107442 (AIA cutouts only), 20140919_051712 OBSID 3860608353 (rolled
  SJI 2832), 20250710_121126 OBSID 3893010094 (deconvolved SJI 2832) and
  `iris_l2_20140910_fexxi_rb_steps` (a derived product, not Level 2). The
  IRIS-9 observations (for example OBSID 3840007146) are not local.
- Linters: use the repo-pinned Ruff versions (core 0.15.20, Qt 0.14.14,
  solar 0.16.1). Recheck the configuration before installing tools, and do
  not weaken a baseline for newer lint rules.
- Floor env (`wp1-m0-irispy-baseline` creates it): `iris-plan-floor`, a
  named micromamba env with irispy-lmsal 0.8.1 at its declared floors
  astropy 7.2.x and ndcube 2.4.0, on glue-core 1.27.0 and glue-qt 0.4.2.
  Install the glue-qt wheel and the editable glue-solar with `--no-deps`, as
  in `iris-plan`. WP1 items pass in both `iris-plan` and `iris-plan-floor`.
- Prototype-reproduction env `iris-plan-irispy081`: a clone of `iris-plan`
  with irispy-lmsal 0.8.1 but iris-plan's astropy 8.0.1 and ndcube 2.4.2. It
  reproduces prototype results on irispy 0.8.1 and is not the floor env.
  After cloning, reinstall the glue-qt wheel and the editable glue-solar
  with `--no-deps`.
- Docs env (`wp9-m0-docs-build`): `iris-plan-docs`, the `iris-plan` pins plus
  the pyproject `docs` extra. Build with
  `sphinx-build -W --keep-going -b html docs <out>`, never
  `tox -e build_docs`.

## Archive

Historical snapshots. Each keeps its original relative links, some of which
no longer resolve after later moves. None is a maintained work list.

| Snapshot | Contents |
| --- | --- |
| [archive/2026-09-27-restructure/](IRIS_PLAN_PROTOTYPES/archive/2026-09-27-restructure/IRIS_GLUE_GAP_PLAN.md) | The plan and prototype index just before this restructure: branch snapshots, cleanup log, validation tables, the 2020 wiki roadmap reconciliation and the capability tables |
| [archive/2026-09-23-prototype-refresh/](IRIS_PLAN_PROTOTYPES/archive/2026-09-23-prototype-refresh/) | Originals of the prototypes refreshed on 2026-09-23 and the index before that refresh |
| [archive/2026-09-23-before-capability-audit/](IRIS_PLAN_PROTOTYPES/archive/2026-09-23-before-capability-audit/IRIS_GLUE_GAP_PLAN.md) | The plan before the 2026-09-23 existing-capability audit |
| [archive/2026-09-22/](IRIS_PLAN_PROTOTYPES/archive/2026-09-22/IRIS_GLUE_GAP_PLAN.md) | The 2026-09-05 plan with full 40-character PR heads |
| [archive/2026-09-05/](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/) | The six pre-consolidation documents: prior 6,746-line plan, branch review, SolarSoft capability audit, APE-14, profile and macOS TODOs |
| [archive/probes-2026-09/](IRIS_PLAN_PROTOTYPES/archive/probes-2026-09/) | Historical probes, logs, diffs, WP0 PR drafts, findings and the 2026-08-29 plan, moved on 2026-09-27 |

The local branch `backup/iris-observation-browser-pre-rebase` (never
pushed) points at 93d05f05. It keeps `docs/make_screenshots.py`, the helper
that regenerates the 1D-profile guide screenshots (see WP9).
