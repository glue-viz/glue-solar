# IRIS and Glue cross-repository work plan

Updated 2026-09-29. The single work plan for glue-core (`~/Git/glue`), glue-qt
(`~/Git/glue-qt`), glue-solar (`~/Git/glue-solar`) and irispy (`~/Git/irispy`),
toward an IRIS quicklook in Glue that covers what SolarSoft's CRISPEX offers
IRIS users. It lists only open work: finished items, history and review
evidence are in git history and under `IRIS_PLAN_PROTOTYPES/`.

The plan and `IRIS_PLAN_PROTOTYPES/` live on the glue-solar branch `plan`,
which is pushed to the public glue-viz/glue-solar repository and is never
merged or opened as a PR. Production work happens on feature branches from
`main`; never stage the plan or the prototypes there. Commit or push plan
updates, and open, ready, review or merge any PR, only when the user asks.
Write only repo-relative or `~/` paths here.

Companion files:

- [IRIS_CRISPEX_FEATURES.md](IRIS_CRISPEX_FEATURES.md): the 203 CRISPEX and
  IRIS-SolarSoft features (F001-F203), each mapped to a checkbox key below or
  marked available, excluded or covered by an equivalent.
- [IRIS_PLAN_PROTOTYPES/README.md](IRIS_PLAN_PROTOTYPES/README.md): the
  prototypes still worth porting (see [Prototypes to port](#prototypes-to-port)).

## How to use this plan

1. Start at [Current state](#current-state-2026-09-29) and refresh PR states
   with `gh`.
2. Pick an unchecked item in the earliest open milestone. Read its task, done
   condition and dependencies, and trace the current code before adapting a
   prototype. This file takes precedence over prototypes.
3. Run all Python in a micromamba environment ([Validation](#validation-environments-and-data)).
4. Stage named files only, and only when a commit is requested.
5. When an item is done, delete it here, remove it from other items'
   Depends, and add one line to Current state (PR, commit, test result, any
   limit). Merged glue-solar code is not released code.
6. The GitHub wiki (`glue-viz/glue-solar.wiki`) is a public digest refreshed
   from this file only on request (`wp9-m0-wiki-digest`); keep local paths
   and prototype links out of it.

Checkbox format: `- [ ] **M<n>** `key`: task. Done when: … Depends: …`.

## Goal and scope

CRISPEX is the reference for the browsing workflow and `iris_xfiles` for local
observation discovery ([CRISPEX](https://github.com/grviss/crispex),
[IRIS-9 CRISPEX exercises (archived)](https://web.archive.org/web/20250429073324/https://tiagopereira.space/iris9/exercises/tutorials_idl.html#crispex),
[ITN 26](https://iris.lmsal.com/itn26/)). CRISPEX has no licence file, so
features are reimplemented from their documented behaviour; no CRISPEX code
is ported.

In scope: every feature in the companion file, including Level-3 file input,
density and temperature diagnostics and the browser search extras.
Priorities set the milestone, not whether a feature is in scope. Out of scope:

- Level-3 FITS writing and EIS support (permanent non-goals).
- The detector mosaic viewer, an OBS XML table viewer and a pipeline-log
  viewer (excluded by the user).
- Stokes/polarimetry, SST/CRISP-only inputs and other instruments' loaders.
- IDL implementation details Glue replaces (transposed "sp" cube, window IDs,
  the control-panel clone, `SPECTFILE`/`LINE_CENTER`/`NO_WARP`), pixel-identical
  IDL layouts, the IDL PostScript device and a generic annotation framework.

## Current state, 2026-09-29

**Releases.** glue-core 1.27.0 (2026-06-25), glue-qt 0.4.2 (2026-02-11),
irispy-lmsal 0.9.1 (2026-09-28; 0.9.1post1 has the same code). irispy 0.9.1
contains every irispy fix glue-solar needs (#176-#181: V34 rasters flip mask,
uncertainty and per-step meta; the raster -TAB WCS has no step index; SJI and
AIA gWCS use CRPIX − 1 and slit positions are pixels, still 1-based; negative
counts get readout noise only; meta tolerates missing keys; no uncertainty
from memmap data).

**glue-solar `main` (c6681e8).** The IRIS observation browser and loader
(#44, #50); a datetime64 `Time` component and the `solar:frame_time` and
`solar:cursor_readout` Image tools (#52); transparent NaN pixels (#53);
-200/-199 fill loaded as NaN, AIA cutouts -200 only (#54); the D5 baseline:
`irispy-lmsal>=0.9.1`, glue-core ≥ 1.27.0 and glue-qt ≥ 0.4.2 instead of the
irispy git pin (#57, merged 2026-09-29; 37 passed, 1 skipped in `iris-plan`
and `iris-plan-floor`). Merged 2026-09-29: changelog entries for #52/#53 and
own toolbar icons for `solar:cursor_readout` and `solar:frame_time` (#58);
`<label> mask` is `isnan(data)` as uint8, so loading keeps 5.0 B/element on
4000005156 scan 0 and the 99-scan 3602506433 stack peaks at 9.47 GiB RSS,
with the dev guide updated (#59); `WCS_LOCK` around `_GlueWCS` conversions,
with a subprocess thread test (#60). Slider latency on irispy 0.9.1 needs no
code (measured 2026-09-29 on main, 4000255147 Si IV, offscreen): a spectrogram
slice step (set + draw) takes 0.049-0.050 s at exposures 1-1599 with no growth,
and λ–t (wavelength × exposure) equals `cube[:, y, :]` at 0.070 s per slit
step. #61 (merged 2026-09-29): SJIs and aligned AIA cutouts take glue-solar's
helioprojective axis names, like rasters. No release. On
released core, saving a session that holds any glue-solar dataset (sunpy Maps
from File → Open included) fails (WP3).

Merged 2026-09-29 as well: deconvolved SJIs list and load beside the plain
ones (#62); tests keep off the user's QSettings and `~/.glue` (#63); an
`Exposure time` component and SJI pointing in meta, shown by Frame time (#64);
remote-data tests on LM-SAL/irispy-data (`irispy_data` fixture, `online` tox
factor and CI job), starting with the 3400109360 negative-step orientation
(#65).

**glue-solar draft waiting for the user's review:** #66 (`wcs-link-editor`,
worktree `~/Git/glue-solar-wcs-link-editor`, from c6681e8): the link editor's
"WCS link" raised `AttributeError: has_celestial` on IRIS datasets;
`_GlueWCS.has_celestial = False` sends glue down its APE-14 path, so SJI↔SJI
links and SJI↔raster gets glue's `IncompatibleWCS` (printed by glue-qt's
editor; `link_hpc` is the route for that pair). Suite 43 passed, 2 skipped.
Also a draft: #67 (`ci-matrix`): CI runs only core (Linux 3.12), Linux 3.14,
Linux 3.13 online and the docs; Linux 3.13, Windows, macOS and devdeps dropped
for now at the user's request (tox envs unchanged).

**Slider speed** (user, 2026-09-29: slow on PyQt5 on their Linux/Wayland
machine with 3860259453; measure now, optimise later). Probe:
`IRIS_PLAN_PROTOTYPES/wp10_slider_probe.py FILE [--window W] [--steps N]
[--profile]` times set, draw, paint and one slider tick on screen, with the
share spent in glue-solar's WCS. Baseline on the reference Mac, offscreen,
4000255147 Si IV (1600 steps): set 0.028 s, draw 0.018 s, paint 0.018 s (WCS
0.022 s of it, mostly WCSAxes tick updates), tick 0.030 s. Waiting for the
user's Linux numbers.

**irispy (LM-SAL/irispy main 8751589).** Draft PRs waiting for the user's
review, each branched from main 51c0ec2, tested against an IDL 9.2 reference
run, and documented where they deliberately differ from IDL:

| PR | Branch (worktree `~/Git/<name>`) | Adds | Used by |
| --- | --- | --- | --- |
| #197 | `uv-burst-detection` (`irispy-bursts`) | `irispy.utils.bursts.find_si_iv_bursts`, `find_sji_bursts` | `wp2-burst-detection` |
| #198 | `wavelength-drift` (`irispy-wavecorr`) | `irispy.utils.wavelength_drift.calculate_wavelength_drift` | `wp5-m3-rest-from-measurement` |
| #199 | `mg-features` (`irispy-mg-features`) | `irispy.utils.mg_features.calculate_mg_features` | `wp2-m3-mg-features` |
| #201 | `moments-uncertainty` (`irispy-moments-uncertainty`) | a `StdDevUncertainty` on each `calculate_moments` map | `wp2-m3-window-data` |

CI is green except the online gallery job on #199 and #201, where two
existing coalign examples fail to query JSOC (unrelated); rerun with
`gh run rerun <run id> --repo LM-SAL/irispy --failed`. #200 (a second IDL test
of the throughput fit) is merged. The user's draft irispy #182 (gWCS rasters)
is theirs to direct (D14). The IDL reference outputs are untracked in
`~/Git/irispy/iris_ref_out/`; the comparison with GDL and the scripts that
built the fixtures are in `IRIS_PLAN_PROTOTYPES/idl_reference/comparison_20260929/`.

**Upstream glue PRs** (checked 2026-09-29 evening; heads unchanged since
2026-09-22, except #2604, 2026-09-25). "Ready" means the draft flag is off, not
approval. No M0-M3 item depends on any of them; working on them is M4 (D2).

| PR | Branch | State | Head | Relevance |
| --- | --- | --- | --- | --- |
| glue #2595 | `ape14-wcs-autolink` | Draft | `c49aeb1af14a` | APE-14 WCS autolinking; also fixes the `has_celestial` crash glue-solar #66 works around (WP1, M4) |
| glue #2596 | `profile-slice` | Draft | `1deff2999c9a` | Slice profile function; land before #2601 |
| glue #2601 | `profile-wcsaxes` | Draft | `acaf4e1c0ef8` | Profile WCSAxes; contains #2596 |
| glue #2597 | `fix-session-style-meta` | Draft | `bfe16085ea57` | Colormap/meta session fixes (WP3) |
| glue #2598 | `fix-world2pixel-correlated-axes` | Draft | `ca3fb185e5a4` | Correlated-axis inverse (WP1 workaround until released) |
| glue #2599 | `fix-datetime-epoch` | Draft | `dd881a47bb40` | Datetime epoch (WP7 GOES dates) |
| glue #2603 | `line-layer-artists` | Draft | `34d1f0c622d5` | Line layers; later base for WP4/WP5/WP7 lines |
| glue #2604 | `fix-region-wcs-image-2600` | Ready (not the user's) | `d2ddfa57774f` | Regions on WCS images (WP7 FOV) |
| glue-qt #66 | `path-slicer` | Draft (upstream author) | `0797f6254188` | Generic path slicer (WP12) |
| glue-qt #68 | `macos-integration` | Ready | `aefab0dda25c` | macOS integration (WP0) |
| glue-qt #69 | `ci-fixes` | Ready | `b5778ef5027a` | CI fixes (WP0) |
| glue-qt #70 | `profile-wcs-pr` | Draft | `f1471b7ad843` | Profile sliders and WCSAxes wiring |
| glue-qt #73 | `line-layer-artists` | Draft | `2f9ccfb65c5e` | Qt side of #2603 |
| glue-qt #74 | `status-bar-cursor-readout` | Draft | `6b579814eb7c` | Generic cursor readout |
| glue-qt #75 | `slice-widget-time-axis` | Draft | `8852fcd13ca8` | Absolute-time slider labels |

PR notes (2026-09-29):
- CI. The six glue drafts pass everything except CircleCI `py311-test-visual`,
  which fails on every glue PR (#2603, #2604 too) until dhomeier's #2592
  updates the visual references; #2599 also fails `initial_checks /
  codestyle` and pre-commit.ci, to fix before it is marked ready. glue-qt
  main's own CI has failed since 2026-02: #68, #70, #74 and #75 fail 20
  required test jobs plus 12 allowed failures, while #69 (the CI fix) passes
  every required job and fails 4 allowed ones.
- Reviews. astrofrog (2026-09-07, on #2595) will review the glue drafts, or
  ask dhomeier to, once the user marks them ready; the user said they review
  them first. dhomeier (2026-09-08) found #69's viewer-test and config changes
  duplicate his glue-qt #65, leaving the matplotlib-failure handling there,
  and is still checking #69's PluginManager fixes; on #68 (2026-09-11 and -16)
  he tested it on macOS Tahoe and liked the larger toolbar icons and labels.
  Open on #68: the Dock and menu-bar name (the standalone apps from
  glue-standalone-apps already show "glueviz").
- Merging. Core pairs merge cleanly; Qt #70 and #75 conflict only add/add in
  `glue_qt/viewers/common/tests/test_multi_slice_helper.py` (keep both tests);
  #69 conflicts with #68 and #70 in `glue_qt/app/tests/test_plugin_manager.py`.
  Qt #68 and #70 carry only reworded cherry-picks of #69's plugin-test fix;
  #74 and #75 lack #69, which is why they fail the required jobs. Qt #70's
  nearest-index/display-unit correction in `profile_tools.py` could become its
  own PR if a maintainer asks.
- Others' open PRs that matter here: glue #2592 (visual references, ready);
  #2507 (astrofrog, draft since 2025-03: fixed-resolution-buffer speed-up, the
  image slicing path the slider latency measurements exercise); #2128 (hide
  Matplotlib axes, changes requested; `wp12-sequence-export`); glue-qt #72
  (Carifio24, ready: enable and disable subtools, relevant to glue-solar's
  `save` subtools in WP12); #65 (dhomeier, tox cleanup, overlaps #69).

**Next steps.**
1. The user reviews #66 and #67, and runs the slider probe on the Linux
   machine.
2. The rest of M0, in glue-solar only: since 2026-09-29 upstream PRs,
   reports and tracking wait for M4 (D2); next are `wp4-coordinator` and
   `wp4-time-sync`.
3. When the user has merged and irispy has released #197-#199 and #201, raise
   the irispy floor (`wp0-irispy-requests`).

**Worktrees.**

| Path | Branch | State |
| --- | --- | --- |
| `~/Git/glue-solar` | `plan` | This plan |
| `~/Git/irispy-bursts` | `uv-burst-detection` | Draft #197; the `irispy-ports` env imports irispy from here |
| `~/Git/irispy-wavecorr` | `wavelength-drift` | Draft #198 |
| `~/Git/irispy-mg-features` | `mg-features` | Draft #199 |
| `~/Git/irispy-moments-uncertainty` | `moments-uncertainty` | Draft #201 |

Removable (merged): `~/Git/glue-solar-wp10-fill-nan`,
`~/Git/glue-solar-irispy-git-pin`, `~/Git/glue-solar-irispy-pin-bump`,
`~/Git/glue-solar-irispy-baseline`, `~/Git/glue-solar-m0-quick`,
`~/Git/glue-solar-mask-uint8`, `~/Git/glue-solar-wcs-lock`,
`~/Git/glue-solar-axis-names`, `~/Git/glue-solar-sji-variants`,
`~/Git/glue-solar-qsettings-isolation`, `~/Git/glue-solar-exposure-readout`,
`~/Git/glue-solar-descending-step`,
`~/Git/irispy-response-2013`. `~/Git/irispy` is the user's checkout (on main
today): never check out, stash or edit in it, and never run Python with it as
the working directory; branch into a separate worktree from `origin/main`.

## Decisions and contracts

Settled by the user. Do not re-open them without the user.

- **D1 (link_hpc):** keep `link_hpc` permanently. It is the only spatial link
  between IRIS datasets on released core and gives exact, per-frame,
  time-aware world coordinates. APE-14 `WCSLink`s (core #2595) describe
  frame-0 geometry (42.2 arcsec off at the last frame of the 4.8-hour
  sit-and-stare fixture); when present they are the 1-hop path and win every
  pixel path. Never add an SJI world-time link.
- **D2 (where code lives, user decision 2026-09-29):** everything goes into
  glue-solar (and irispy) first, through public glue registries (viewer tools,
  layer actions, menubar plugins, startup actions, data factories, unit
  converters, savers). Upstreaming starts once M0-M3 are in place (M4): until
  then no glue, glue-qt or astropy PR, report or tracking step is on the path,
  and no item waits for an upstream release.
  - A behaviour probe, never a version number, switches each workaround on;
    each names the upstream fix that would retire it, and floors change only
    when a release contains that fix.
  - Private-method patches are allowed where a feature needs one, each gated,
    tested, in the WP0 register and with a signature test on the released
    baseline (today: Profile restore priority, Pixel crosshair visibility and
    physical aspect).
  - Opening, readying, requesting review of or merging any PR needs the user's
    direction.
- **D3 (display units):** arcsec for helioprojective axes and Angstrom for
  wavelength, in low-level values and high-level objects, for `_GlueWCS` IRIS
  data and glue-solar's sunpy Map loaders (wrapped in M1).
- **D4 (analysis products):** moments, fits and other products are dataset
  `layer_action`s that add Data and links without opening a viewer.
- **D5 (baseline):** released glue-core 1.27.0, glue-qt 0.4.2 and
  irispy-lmsal 0.9.1. No unreleased PR is an M0 prerequisite.
- **D6 (selection):** M0 uses the stock Pixel tool (drag follows, release
  holds) plus "Clear point"; M1 adds a required hover-follow tool with
  click-to-lock.
- **D7 (coordination defaults):** the selected point is a fixed detector
  pixel. Time axes stay index axes with timestamp readouts (a regridded UTC
  axis is `wp12-time-regrid`, M1). Nearest-exposure ties go to the earlier
  exposure; there is no match beyond half the partner's median cadence or
  outside its coverage, and the partner is then greyed with the offset shown,
  never clamped. The raster is the default time master; a control switches
  it to an SJI.
- **D8 (time sync):** in M0 the coordinator moves sliders itself from 1-D
  nearest-index and signed-offset arrays derived from each dataset's `Time`;
  it adds no glue links and never resolves `data[other_pixel_cid]`. Links
  from main components into pixel component IDs are forbidden. Index links
  (design B) may come later only for time-gated subsets, as identity
  `ComponentLink`s on precomputed index components: never
  `JoinLink`/`join_on_key`, lambda or closure links.
- **D9 (coordination architecture):** the registered viewer tool
  `solar:coordinate` plus one coordinator per DataCollection, on Image
  viewers from M0 and Profile viewers from M1. glue-qt instantiates tools for
  restored viewers, so they re-register; never wrap `app.new_data_viewer`.
- **D10 (negative-step rasters, STEPS_AV < -0.01):** keep irispy's default
  orientation (irispy ≥ 0.9.1 flips data, mask, uncertainty, times and
  per-step meta together); `revert_v34=True` is the documented alternative.
  `nearest` accepts unsorted and duplicate references with first-index
  semantics.
- **D11 (rest wavelength):** an explicit override, else the packaged
  line-list (vacuum) value matching the window, else none. Multi-line windows
  (C II 1334/1335, Mg II k/h) get no rest on load and the user picks; the
  dialog pre-selects the window's named line. Never fall back to TWAVE (the
  Mg II k window's TWAVE is about 16 km/s off). Continuum windows get no
  km/s. Store `meta['rest_wavelength']` as a float in Å.
- **D12 (missing and saturated data):** -200 and -199 are missing and become
  NaN (AIA cutouts: -200 only). Saturation is +Inf (ITN 26). Negative values
  are noise and stay data (33-62 % of valid FUV samples). Masks are uint8,
  because glue coerces bool to int64.
- **D13 (session savers):** register the Quantity saver only if none exists,
  and propose it to core. Port WP3 as `_GlueWCS.__gluestate__`/`__setgluestate__`
  and named factory functions, never by importing prototype modules.
- **D14 (irispy):** irispy work targets `main` only, from worktrees off
  `origin/main`. The gWCS raster work (the user's draft #182) is the user's
  to direct; propose nothing from it until the glue-solar loader accepts both
  APIs (`wp0-irispy-gwcs-branch`).
- **D15 (layout):** the quicklook uses an MDI tab with explicit viewer
  geometry, not the experimental fixed-layout tab.
- **D16 (Doppler sign):** red minus blue, D(Δ) = I(λ0 + Δ) − I(λ0 − Δ);
  positive means redshift. Recorded in the component name and
  `meta['doppler_sign']`.

Cross-package contracts:

- `link_hpc(data_collection)` returns links (`dc.add_link(link_hpc(dc))`); it
  is idempotent, pairs world components by physical type, assumes `_GlueWCS`
  gives arcsec, never links degrees to arcsec, and skips Data that
  `wp12-time-regrid` marks in meta.
- Keep the SJI `Time (Utc)` world axis distinct from the datetime64 `Time`
  component. Match physical types, never labels (glue title-cases gWCS names,
  so `Time (UTC)` shows as `Time (Utc)`).
- Never fake an all-ones `axis_correlation_matrix`; until core #2598 is
  released, use its fix through the gated WP1 workaround.
- Glue gives no order among equal-hop link paths, so an IRIS link graph must
  never have two equal-hop paths giving different values for one component;
  `wp1-m0-link-graph-regression` checks every add order.
- Derived spatial maps (WP2, WP5, WP6) use `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`
  from the source's raw WCS, never irispy's rebuilt 2-axis -TAB WCS (the
  saver cannot store it).
- Components added after load are saved in full: derived index or broadcast
  components must be compact classes that save only their 1-D vector (WP3).
- Code reads the rest wavelength only through the WP5 helper
  (`meta.get("rest_wavelength")`); irispy's `SGMeta.rest_wavelength` is TWAVE
  and is never read.
- The `_GlueWCS` lock (`WCS_LOCK`, #60) covers only calls through
  `_GlueWCS`; code reading the raw astropy WCS holds the exported lock or
  works on its own deep copy.
- glue-qt 0.4.2 attaches menus only to `DropdownTool`/`SimpleToolMenu`: use a
  `SimpleToolMenu` whose subtools restore the active mouse mode, or a panel
  shown while a checkable tool is active.
- WP3 must not replace the `VisualAttributes` serialization globally; plain
  sessions stay portable.
- Say "on main" or "merged" for glue-solar code and "released" only for
  tagged releases.

## Milestones

### M0: coordinated IRIS quicklook on released core

On the D5 baseline, a user opens an observation and gets a quicklook: a preset
per observation type (raster map or slit-versus-time, spectrogram, step- or
time-versus-wavelength panel, point spectrum, one SJI viewer per channel with
slit and point overlays); a held Pixel point driving the other panels; SJI and
raster time sync from an explicit master with offsets and a no-match state;
acquisition-time readouts; and the loader blockers fixed (masks, WCS thread
crash, large-data modal, slider latency, raster-ROI guard).

Done when every M0 item is ticked, `wp10-m0-acceptance` passes the budgets and
`wp9-m0-iris9-acceptance` passes the workflow. GUI gaps while loading are an
M1 gate (`wp10-nonblocking-load`).

Acceptance data (full files in `~/DATA/IRIS` for manual probes; tests use
LM-SAL/irispy-data cutouts): 4000255147 (20130902_163935, sit-and-stare
+ SJI 1400); 4000005156 (20130902_182935, two-scan raster + deconvolved SJI
2796 only); 3824262996 (20140708_114109, 400-step Mg II raster); 3400109360
(20250328_225628, negative step); 3602506433 (20260209_215233, 99 scans,
memory checks only). CI uses the irispy fixtures 3620258102 (20210905
sit-and-stare with SJI 1330/1400/2796/2832) and 3860258481 (20140329, 13 files
of 8 steps).

### M1: CRISPEX navigation and spectral parity

SJI click → raster spectrum on released core (WP1, WP4); Angstrom and high-level coherence and wrapped sunpy
maps (WP1); IRIS sessions (WP3); rest wavelength, velocity, line list, blink
and Doppler image (WP5); hover-lock, spectral markers, multi-window, AIA
reference panels, time controls and raster overlays (WP4); labelled readouts,
the selected-point panel, scaling, colour tables, physical aspect and keys
(WP11); non-blocking load and world-polygon ROIs (WP10); derived-file
filtering (WP8); the regridded time axis (WP12); point-spectrum slice profiles (WP4).

Done when every M1 item is ticked and the IRIS-9 CRISPEX tasks run end to end
(`wp9-m1-iris9-tutorial`) and a saved quicklook reopens with coordination
working (`wp3-app-session-acceptance`). The ongoing `wp0-release-tracking`
and probe-gated sub-checks do not hold M1 open.

### M2: analysis, context, display and export

Moment maps (WP2) and Gaussian fit maps (WP6); GOES and AIA context (WP7);
browser filter, stop and text filter (WP8); lazy loading (WP10); the remaining
display tools (WP11); image and movie export, FITS/ECSV export of derived
data, point light curves and path diagrams (WP12).

### M3: later and specialist

Conveniences, Level-3 input, density and temperature diagnostics, burst and
Mg II feature maps, template fits and browser search extras.

### M4: upstreaming

Once M0-M3 are in place (D2): the glue, glue-qt and astropy PRs, reports and
tracking (WP0), the user's own drafts (glue #2595-#2604, glue-qt #66-#75), the
#2595 autolink matrix (WP1) and the docs that follow upstream releases (WP9).
Each release containing a fix retires the matching glue-solar workaround
(`wp0-release-tracking`).

### Checklist by milestone

**M0**
- WP0: `wp0-workaround-register`, `wp0-readme-runner`
- WP1: `wp1-m0-inverse-workaround`, `wp1-m0-link-hpc`, `wp1-m0-link-graph-regression`
- WP4: `wp4-coordinator`, `wp4-quicklook-preset`, `wp4-launch-entry`, `wp4-m0-point-fixed-index`, `wp4-time-sync`, `wp4-m0-time-wavelength-panels`, `wp4-sji-panels`, `wp4-slit-point-overlay`, `wp4-tests`
- WP9: `wp9-m0-user-guide-corrections`, `wp9-m0-viewer-tools-docs`, `wp9-m0-browsing-recipes`, `wp9-m0-mask-overlays`, `wp9-m0-workflow-recipes`, `wp9-m0-scripting-recipe`, `wp9-m0-iris9-tutorial`, `wp9-m0-iris9-acceptance`, `wp9-m0-docs-build`, `wp9-m0-wiki-digest`
- WP10: `wp10-m0-large-data-modal`, `wp10-m0-roi-guard`, `wp10-m0-acceptance`

**M1**
- WP0: `wp0-release-tracking`, `wp0-core-profile-restore-priority`, `wp0-irispy-requests`, `wp0-irispy-gwcs-branch`
- WP1: `wp1-m1-wrapper-coherence`, `wp1-m1-sunpy-maps`, `wp1-m1-sji-to-raster`, `wp1-dn-per-s`
- WP3: `wp3-style-cmap`, `wp3-wcs-saver`, `wp3-quantity-meta`, `wp3-plain-meta`, `wp3-file-references`, `wp3-session-budget`, `wp3-coordination-reattach`, `wp3-app-session-acceptance`
- WP4: `wp4-m1-hover-lock-tool`, `wp4-sji-click-to-raster`, `wp4-profile-aggregation`, `wp4-slice-profiles`, `wp4-m1-spectral-coupling`, `wp4-m1-multi-window`, `wp4-context-reference`, `wp4-time-controls`, `wp4-raster-overlays`
- WP5: `wp5-m1-line-list`, `wp5-m1-rest-wavelength-policy`, `wp5-m1-velocity-axis`, `wp5-m1-spectral-blink`, `wp5-m1-doppler-image`
- WP8: `wp8-derived-files`
- WP9: `wp9-m1-iris9-tutorial`, `wp9-m1-screenshots`
- WP10: `wp10-nonblocking-load`, `wp10-m1-roi-world-polygon`
- WP11: `wp11-cursor-readout`, `wp11-selected-point-panel`, `wp11-histo-opt-scaling`, `wp11-gamma-stretch`, `wp11-raster-cmap`, `wp11-physical-aspect`, `wp11-keyboard-shortcuts`
- WP12: `wp12-time-regrid`

**M2**
- WP2: `wp2-m2-moment-maps`, `wp2-m2-line-definition`, `wp2-m2-input-quality`, `wp2-m2-tests-docs`
- WP6: `wp6-m2-fit-maps`, `wp6-m2-quality-filter`, `wp6-m2-products`, `wp6-m2-rest-key`, `wp6-m2-worker`, `wp6-m2-profile-fitter`, `wp6-m2-tests`, `wp6-m2-docs`
- WP7: `wp7-context-port`, `wp7-goes-context`, `wp7-goes-marker`, `wp7-goes-date-labels`, `wp7-aia-context`
- WP8: `wp8-filter-stop`, `wp8-text-filter`
- WP10: `wp10-m2-lazy-loading`
- WP11: `wp11-colourbar`, `wp11-distance-measure`, `wp11-zoom-steps`
- WP12: `wp12-sequence-export`, `wp12-derived-data-export`, `wp12-point-light-curves`, `wp12-path-slicer`, `wp12-path-persist`

**M3**
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

**M4**
- WP0: `wp0-core-image-artist-bugs`, `wp0-qt-large-data-cancel`, `wp0-astropy-19174`, `wp0-stack-validation`, `wp0-user-review`, `wp0-own-draft-updates`, `wp0-core-quantity-saver`, `wp0-core-derived-units`, `wp0-core-profile-unit-label`, `wp0-track-line-layers`, `wp0-qt68-macos-pass`, `wp0-qt-aggregate-slice`, `wp0-track-2604`, `wp0-track-qt66`, `wp0-core-datetime-export`, `wp0-qt68-cocoa`, `wp0-optional-proposals`
- WP1: `wp1-m4-autolink-matrix`
- WP9: `wp9-m4-release-updates`

## Work packages

### WP0: Upstream integration and reports

All cross-repository work: glue and glue-qt PRs, reports to glue, glue-qt,
irispy and astropy, and the register of workarounds they retire. Paths:
`glue_solar/__init__.py`, `glue_solar/glue_patches.py` (gated patches),
`pyproject.toml` (floors), `IRIS_PLAN_PROTOTYPES/upstream/<slug>.py`
(reproducers, run on the released baseline in `iris-plan`). Every PR, issue
or comment needs the user's direction (D2). Until M0-M3 are in place, WP0's
work is glue-solar's workaround register and irispy releases; every glue,
glue-qt and astropy PR, report and tracking item is M4.

Workaround register. A behaviour probe switches each row on unless stated;
the first release with the "Retired by" fix retires it. "(private)" marks one
of D2's three private patches; "(private call/override)" patches nothing and
a released-baseline test pins it.

| Workaround (owner) | Switched on by | Retired by |
| --- | --- | --- |
| Correlated-axis `world2pixel_single_axis` (WP1, `glue_patches.py`) | A time-dependent SJI gWCS inverts at exposure 0 | core #2598 |
| Pixel crosshair visibility (WP4) (private: `ImageSubsetLayerArtist._update_visual_attributes`) | The line shows on an axis-incompatible panel | `wp0-core-image-artist-bugs` |
| `x_display_unit` restore priority (WP0) (private: `ProfileViewerState._update_priority`) | `orig(None, 'x_display_unit') == orig(None, 'x_att')` | `wp0-core-profile-restore-priority` |
| Physical aspect (WP11 `solar:physical_aspect`) (private: per-instance `_set_axes_aspect_ratio`) | No 'Physical pixels' aspect choice | the `core-physical-aspect` PR (`wp11-physical-aspect`) |
| `AggregateSlice` re-applied (WP11 `wp11-band-average`) | `sync_state_from_sliders` replaces an `AggregateSlice` | `wp0-qt-aggregate-slice` |
| `_GlueWCS` RLock (WP10) | Always on: the race cannot be probed safely | astropy fix for #19174, once #60's thread test and 20 runs of `review_20260927/probes/wp10/test_race.py` give 0 crashes unlocked |
| `_GlueWCS.has_celestial = False` (WP1, #66) | Always on: glue's `WCSLink` fallback reads FITS-only attributes of any WCS that claims celestial axes | glue #2595 (draft), which checks for an astropy `WCS` instead of reading `has_celestial`; harmless once released (M4) |
| Datetime epoch port (WP7 `wp7-goes-date-labels`; runtime port of #2599's two functions, never `rcParams['date.epoch']`) | `datetime64_to_mpl(t) != date2num(t)` | core #2599 |
| Quantity saver fallback (WP3, D13) | No Quantity saver registered | `wp0-core-quantity-saver` |
| `DerivedComponent` subclass saving `units` (WP1 `wp1-dn-per-s`) | Core's saver drops `units` | `wp0-core-derived-units`; the class stays importable |
| Generic part of `solar:cursor_readout` (WP11) | `not hasattr(ImageViewer, 'cursor_status')` | Qt #74; IRIS time, exposure and km/s stay in `solar:frame_time` |
| Line-list artist (WP5; public `layer_artist_maker`) | Always on: a feature, not a patch | reconsidered after #2603 and Qt #73 release |
| `SolarVisualAttributes` (WP3 `wp3-style-cmap`) | Core's `VisualAttributes` saver emits a Colormap object | core #2597; the class stays importable |
| km/s Profile x-unit gate (WP5 `wp5-m1-velocity-axis`) (private call: `ProfileTools._get_axis_and_pixel_slice`) | A non-native x display unit fails on a tiny nm-x Data | Qt #70 |
| `ProfileViewerState._update_x_display_unit_choices` in the km/s-axis tool (WP5) (private call) | Always on with the tool; signature test | none tracked |
| `SliceWidget._adjust_play` for Space outside the quicklook (WP11 `wp11-keyboard-shortcuts`) (private call) | Always on; the key test covers it | none tracked |
| Path tools (WP12 `wp12-path-slicer`, `wp12-path-batch`) (private override) | Always on; signature test on 1.27.0 | Qt #66 or the WP12 core proposals |

Reports and requests (each closes with a URL or the user's decision not to file):

| Slugs (checkbox) | URLs or decisions |
| --- | --- |
| `core-pixel-crosshair` (issue and PR), `core-translate-pixel` (`wp0-core-image-artist-bugs`); `core-physical-aspect` (issue and PR; `wp11-physical-aspect`) | |
| `qt-large-data-cancel`, `qt-aggregate-slice`, `astropy-19174` (comment) | |
| `core-profile-restore-priority` (issue and PR), `core-quantity-saver`, `core-derived-units`, `core-profile-unit-label` (optional), `core-datetime-export` | |
| `qt73-style-editor` (comment; `wp0-track-line-layers`) | |
| `irispy-bursts`, `irispy-wavecorr`, `irispy-mg-features`, `irispy-moments-uncertainty`, `irispy-itn32` (`wp0-irispy-requests`) | drafts LM-SAL/irispy#197, #198, #199, #201; `irispy-itn32` not filed |
| `irispy-asdf-converters` (`wp0-irispy-gwcs-branch`, only if that work proceeds) | not filed (D14) |
| One row per proposal (`wp0-optional-proposals`) | |

**M0**

- [ ] **M0** `wp0-workaround-register`: Apply D2 to every workaround (probes, not versions: PR-source installs report 1.27.0). Done when each workaround on main has a register row, a comment naming its probe (or why it is always on) and its fix (or 'none tracked' plus a signature test), and a test passing on the released baseline with the probe on, and off where a source export has the fix.
- [ ] **M0** `wp0-readme-runner`: In `IRIS_PLAN_PROTOTYPES/review_20260923/README.md`, replace the four `.venv/bin/python` runner lines and `/tmp/iris-plan-validation-*` roots with the Validation runner. Done when no runner instruction outside `IRIS_PLAN_PROTOTYPES/archive/` uses `.venv`.

**M1**

- [ ] **M1** `wp0-release-tracking`: Date each glue-core, glue-qt, irispy-lmsal or astropy release after the D5 baseline (1.27.0, 0.4.2, 0.9.1). A fix counts only if its merge commit is reachable from the tag; then raise the floor, retire register rows, close report rows and switch on gated work (#2595: WP1 SJI↔raster pixel paths; #2596/#2601 + Qt #70: slice profiles; #2599: WP7 date labels; glue #2128, hidden axes: `wp12-sequence-export` drops its `set_axis_off()` fallback). Done when each such release has a line here naming its PRs, floors and rows.
- [ ] **M1** `wp0-core-profile-restore-priority`: `ProfileViewerState._update_priority` ranks `x_att` and `x_display_unit` equally (glue/viewers/profile/state.py:333-341@v1.27.0), so restoring any IRIS spectrum panel raises ValueError ('value Angstrom is not in valid choices'). `setup()` ranks `*_display_unit` 0.5 (after `x_att` 1, before limits 0), idempotent, probe in try/except (register row); the one-line core PR waits for M4 (`wp0-optional-proposals`). Done when, on 1.27.0, a GlueApplication save/restore of synthetic 3-D Data with a spectral WCS (Profile `x_att` on it, Å and nm) restores `x_att`, unit and limits with the wrapper and raises without it.
- [ ] **M1** `wp0-irispy-requests`: (1) Get the four irispy ports released: the user reviews drafts #197 (bursts), #198 (wavelength drift), #199 (Mg II features) and #201 (moment uncertainties); once a release contains them, `wp0-release-tracking` raises glue-solar's irispy floor for WP2 and WP5. (2) Hinode/SOT cubes in the IRIS SJI format (ITN 32) for `wp4-context-reference`: port to irispy main (estimate 2-3 days; prototype `IRIS_PLAN_PROTOTYPES/irispy_ports_20260927/itn32-sot/`), keying cubes so NFI Stokes I and V of one observation do not overwrite each other (`read_files` keys by TDESC1), with shrunken fixtures that keep HDU 2. Done when an irispy release contains the four ports and either ITN32 cubes load through `read_files` in a release or the user declines (2).
- [ ] **M1** `wp0-irispy-gwcs-branch`: Only if the user proceeds with the gWCS raster work (#182, D14). With it the loader makes one 2-D dataset per exposure (about 1500 per raster file), loses wavelength and fails with `stack=True`; its raster transforms lack ASDF converters and glue saves `data.coords` for every dataset, so multi-file raster sessions fail until irispy ships converters (`irispy-asdf-converters`) or a `_GlueWCS` record re-derives the WCS from the files. Done when its fate is recorded; a proposal also needs a passing `glue_solar` run on it and a WP3 multi-file raster session round trip.

**M4**

- [ ] **M4** `wp0-core-image-artist-bugs`: Two glue-core 1.27.0 bugs, a PR for the first: (1) `ImageSubsetLayerArtist._update_visual_attributes` re-shows the hidden Pixel crosshair at (0, 0) on λ–t and spectrogram panels after `_update_data` hid it on `IncompatibleAttribute` (the PR re-shows it only when a position was found); (2) `translate_pixel`'s bare `Exception` escapes `ImageLayerArtist`, so draws fail instead of showing 'Cannot visualize this layer' (propose `IncompatibleAttribute`). Done when both reproducers fail on released core and both rows close.
- [ ] **M4** `wp0-qt-large-data-cancel`: glue-qt report: after Cancel on the Profile 'Add large data set?' modal, the closed viewer's `LayerArtistView` stays hub-subscribed, so every later `new_data_viewer` raises 'wrapped C/C++ object of type LayerArtistView has been deleted'. Done when a minimal script reproduces it on glue-qt 0.4.2 and main and its row closes.
- [ ] **M4** `wp0-astropy-19174`: Add the IRIS case to astropy#19174 (Profile worker and GUI-thread WCSAxes crash in wcslib `tabx2s` on a shared -TAB WCS). Done when the reproducer crashes without the lock in `iris-plan` and its row closes.
- [ ] **M4** `wp0-stack-validation`: Test the combined upstream heads (core #2601, #2595, #2597-#2599; Qt #70, #74, #75; #68 if wanted) after resolving the conflicts in Current state: on regenerated exports in `iris-plan`, run the Qt common+profile suites, `glue_solar` (both sides of the `cursor_status` gate) and `IRIS_PLAN_PROTOTYPES/review_20260923/test_existing_workflows.py`. Done when heads, resolutions and pass counts are recorded here and an IRIS-raster Slice profile with an out-of-range reference slice shows 'Incompatible data'. Depends: wp0-readme-runner.
- [ ] **M4** `wp0-user-review`: The user reviews each of their drafts (core #2595-#2599, #2601; Qt #70, #74, #75; irispy #197-#199, #201) before it is marked ready. Done when each is merged, closed or parked by the user. Depends: wp0-stack-validation.
- [ ] **M4** `wp0-own-draft-updates`: Amend the user's drafts: (1) #2595's `wcs_autolink` leaves time axes out between datasets, so WP4 owns time (today frame 0 maps to NaN and a Pixel point on SJI 1400 misses SJI 2796); (2) Qt #74's `cursor_status` labels Solar X/Solar Y, longitude first, at sub-arcsec precision independent of zoom, and shows pixel and world positions together. Done when each amended head, as a source root, passes its suite and the owning WP's test (WP1: SJI/SJI Pixel propagation; WP11: raster-map readout); check (c) of `wp1-m4-autolink-matrix` is written here and run on the amended #2595 export. Depends: wp1-m0-link-graph-regression, wp11-cursor-readout.
- [ ] **M4** `wp0-core-quantity-saver`: Core PR beside #2597 with a `@saver(u.Quantity)`/`@loader(u.Quantity)` pair (D13) from `IRIS_PLAN_PROTOTYPES/wp3_impl.py`, writing WP3's fallback record (saved type, protocol version 1, `{"value", "unit"}`). Done when its core session test round-trips a scalar and an array Quantity in `Data.meta`, a session saved by the solar fallback loads with the core loader, and the row has the PR URL.
- [ ] **M4** `wp0-core-derived-units`: Core PR saving `DerivedComponent.units`, still loading records without it (register row until released). Done when the PR's session test round-trips a `DerivedComponent` with `units='DN/s'` and its row closes.
- [ ] **M4** `wp0-core-profile-unit-label`: Optional: port `IRIS_PLAN_PROTOTYPES/wp5_label.py` (display unit in the Profile x label) as a core PR, not a glue-solar patch. Done when the PR's test shows a velocity profile labelled in km/s in both the numeric and WCSAxes paths.
- [ ] **M4** `wp0-track-line-layers`: Track draft glue #2603 and glue-qt #73; WP5 keeps its `layer_artist_maker` line-list artist and the stock Profile style editor. Comment on Qt #73 that its exact-class editor lookup misses `QThreadedProfileLayerArtist`. Done when the comment is posted or declined and the register row names both PRs.
- [ ] **M4** `wp0-qt68-macos-pass`: Manual macOS pass for Qt #68 (scratch HOME, isolated QSettings): first the saved font override (an old 9-point value hides the new default); then menu title, About/Hide/Quit, Cmd-Tab and Dock name, and clipping at native font sizes (preferences, link editor, importers, fixed-geometry dialogs), on PyQt6/Retina and PyQt5. Keep the slice label's 0.75x scale unless unreadable. Done when each result per binding is recorded here.
- [ ] **M4** `wp0-qt-aggregate-slice`: glue-qt report and PR: `MultiSliceWidgetHelper.sync_state_from_sliders` (glue_qt/viewers/common/slice_widget.py:54) rebuilds every slice from `slice_center`, so any slider move turns a Profile Collapse `AggregateSlice` into an int; keep it on unmoved axes (register row until released). Done when a 0.4.2 reproducer (Collapse, then one scan-slider step on a 4D stack map) shows the loss and its row closes.
- [ ] **M4** `wp0-track-2604`: Track glue #2604 (regions on WCS images); WP7 keeps its pixel `PolygonalROI` FOV subset until a core release has it, then reconsiders a `RegionData` footprint. Done when that release's tracking line names #2604 and WP7's decision is recorded.
- [ ] **M4** `wp0-track-qt66`: Track draft glue-qt #66 (generic `path_slicer` on core `PathSlicedData`, idle since 2026-05-27); WP12 builds on core `BasePathSlicerMode` and #66 or its successor, never on the `PVSliceWidget` #66 deletes. Done when #66 is merged before WP12 starts, or the user has asked its author about it first.
- [ ] **M4** `wp0-core-datetime-export`: Report that core's HDF5, FITS-table and VOTable exporters fail on datetime64 components such as every IRIS `Time` ('No conversion path for dtype <M8[ns]'). Done when a 1.27.0 reproducer fails in each format and its row closes.
- [ ] **M4** `wp0-qt68-cocoa`: Once a glue-qt release has #68, check that conda-forge's glue-qt depends on `pyobjc-framework-cocoa` on macOS; if not, request it. Done when the recipe check and any request URL are recorded.
- [ ] **M4** `wp0-optional-proposals`: Proposals, none blocking, filed only on the user's direction: the one-line core PR ranking `*_display_unit` below `x_att` (retires the `wp0-core-profile-restore-priority` patch), the register's 'Path tools' hooks, and:
  - glue-core: `coerce_numeric` keeping bool as uint8; 99.9/99.8/99.98 percentiles; a `_load_cmap` fallback to glue's colormap registry; gWCS axis names not title-cased to 'Time (Utc)'; image interpolation; once working in glue-solar, the `PathSlicedData` saver, 4D path-slicer gate, per-axis parent driving and nearest/linear sampling.
  - glue-qt: a gamma slider on `stretch_parameters`; playback below 2 fps, bounce playback and a frame sub-range in the slice widget; modifier-aware `keyboard_shortcut` dispatch; Tab/Backspace registered for `TableViewer`, not `DataTableModel` (keyboard_shortcuts.py:32-52@0.4.2).
  - irispy: NaN-filled float raster data as for SJIs; `memmap=True` returning scaled, masked data; a `read_files` exposure-range argument; a (position, exposure) reshape for NEXP_PRP > 1 rasters.
  - astropy: reusing a fitter after `parallel_fit_dask(fit_info=...)` raises `KeyError: '__deepcopy__'` (8.0.1).

  Done when each is filed or declined and recorded in the reports table.

Notes:
- Qt #75 labels only WCS time axes, not the standalone `Time` of raster exposure and stack axes.
- Profile contract for #2601 and Qt #70: numeric and unit-overridden profiles stay out of WCSAxes mode; slice translation and `x_limits_pixel` session state stay.
- Beyond #68 (separate requests): native Preferences/About menu roles, `QFileOpenEvent`, Dock feedback, dark mode, pinch zoom; a notarized `.app` bundle is a separate project.

### WP1: Coordinates, units and links

The coordinate contract (D3) and link graph (D1) for IRIS data and
glue-solar's maps. Tests run in both `iris-plan` and `iris-plan-floor`; each PR
carries a changelog fragment and its guide change.

**M0**

- [ ] **M0** `wp1-m0-inverse-workaround`: Add `glue_solar/glue_patches.py` (imported from `glue_solar/__init__.py`; also home of `wp7-goes-date-labels`). Its #2598 fix of `world2pixel_single_axis` (exposure-0 inverse) installs only when `needs_inverse_workaround()` finds the bug (register row); no all-ones `axis_correlation_matrix`. Done when the probe patches 1.27.0, `test_world_links_into_the_sji_use_each_exposure_time` recovers every frame's pixel to 1e-6 px, with #2598 in core the probe is False and glue untouched, and WCSAxes readouts are unchanged. Depends: wp0-workaround-register.
- [ ] **M0** `wp1-m0-link-hpc`: Port `link_hpc(data_collection)` to `glue_solar/sources/loaders/iris.py` (D1), called by `browse_iris` and a menubar action 'IRIS: link helioprojective coordinates'. Done when, without time links: (1) a second call adds 0 links and both callers add them; (2) 4000005156 Si IV + SJI 2796: at frames 0 and N−1 a raster-map ROI selects exactly the SJI pixels whose per-frame header-WCS position is in its world footprint (0.05 px edge band exempt); (3) the sns fixture and 4000255147 Si IV + SJI 1400: the selected SJI column moves ΔXCENIX/CDELT1 ± 1 px from frame 0 to N−1 (about 78 px on 4000255147), xfail until (4); (4) the released-core sit-and-stare full-width stripe (37/37 columns) is diagnosed; if inherent, the guide records it and (3) stays xfail; (5) lon/lat world subsets propagate both ways, and SJI pixel subsets stay IncompatibleAttribute on the raster; (6) no link targets SJI world time. `browse_iris` installs `link_hpc` by default only in a release that also carries `wp10-m0-roi-guard` and `wp10-m0-acceptance`; until `wp10-m1-roi-world-polygon`, the guide documents the stock raster-ROI freeze (about 10 s per SJI frame). Depends: wp1-m0-inverse-workaround.
- [ ] **M0** `wp1-m0-link-graph-regression`: In `glue_solar/tests/test_linking.py`, open 4000005156 Si IV + SJI 2796 via `browse_iris` with the real autolinker (mocked dialog), `link_hpc` and WP4's link-free coordinator. A `wcs_autolink` probe picks the expectation: False (1.27.0), only `link_hpc` links and (b) = the `wp1-m0-link-hpc` (2) footprint; True (#2595), SJI/raster `WCSLink`s too and (b) = the frame-0 footprint in every SJI frame. No link maps a main or world component into a pixel component ID (D8) or targets SJI world time. Checks: (a) a raster Pixel point gives the marker and spectrum in the other windows; (b) the raster-map ROI's SJI selection; (c) time sync leaves `len(dc.links)` and every component list unchanged, and the coordinator's frame↔step indices equal the `nearest()` reference; (d) lon/lat world subsets propagate; (e) the SJI layer draws in the raster viewer and vice versa, and a layer without a pixel path shows glue's incompatible state. A CI variant on the irispy `sns` SJI 1400 + Si IV 1403 fixtures, ported from `IRIS_PLAN_PROTOTYPES/review_20260927/probes/linkgraph/test_linkgraph.py` (its order/allocation matrix only), runs (a) and (c)-(e) in both baseline envs. Done when all checks agree over every add order and perturbed-allocation reruns, and all minimum-hop paths to each target component agree. Later items (`wp4-m1-multi-window`, `wp7-goes-context`, `wp12-point-light-curves`, `wp12-path-slicer`) extend it under the same bans. Depends: wp1-m0-link-hpc, wp4-time-sync.

**M1**

- [ ] **M1** `wp1-m1-wrapper-coherence`: Angstrom and arcsec across `world_axis_units`, both value methods, `world_axis_object_components`, `world_axis_object_classes` (3- or 4-tuples in astropy's argument order, tested with positional args), compound stacks, sliced maps and bare-array 1-D WCSs; keep `WCS_LOCK`. The F058 pixel toggle is WCSAxes' 'w' readout plus the Profile pixel/world x. Land before `wp3-app-session-acceptance`. Done when, on 3610108077, the Image wavelength slider, cursor readout and Profile x show Å (|Δ| ≤ 1e-6 Å against irispy; nm and m still offered); HPLN/HPLT stay arcsec with identical labels on SJI, raster (including 4000255147), 4D stack and a sliced map; pixel→world→pixel agrees to 1e-9 px through both APIs; scalar and array inputs give identical results in both baseline envs; the guides, recipes and screenshots show Å, not m.
- [ ] **M1** `wp1-m1-sunpy-maps`: Wrap map WCSs in `_GlueWCS` in `_parse_sunpy_map` (`glue_solar/sources/maps.py`) and `load_sunpy_map` (`glue_solar/sources/loaders/maps.py`) (D3); the 'sunpy Map' factory gets a 2-D-helioprojective identifier at priority 150, between glue's FITS reader (100) and IRIS (200). Done when a 2-D AIA-style map FITS shows 'Helioprojective Longitude/Latitude' in arcsec via File → Open and the map importer; with `link_hpc`, `sji[map.pixel_component_ids]` at SJI frames 0 and N−1 equals the map-pixel projection of the SJI header WCS to 0.05 px and a map ROI selects the SJI pixels inside it; a non-map FITS table still opens with glue's reader; the map round-trips through a session. Depends: wp1-m1-wrapper-coherence, wp1-m0-link-hpc, wp3-wcs-saver (session check).
- [ ] **M1** `wp1-m1-sji-to-raster`: `sji_to_raster()` in `glue_solar/sources/loaders/iris.py`: SJI pixel → world at the displayed frame; step by WCS (scanning) or nearest `Time` (sit-and-stare); slit row by WCS. `wp4-sji-click-to-raster` wires it in. Done when (step 32, slit 385) projected into 4000005156 SJI 2796 frame 7 returns (32, 385) within 0.5 px; slit 208 projected into 4000255147 SJI 1400 frames 0, 200 and 399 returns slit 208 within 0.5 px and exposures 1, 801 and 1597; a point outside the raster FOV returns no index; with #2595, frame N−1 returns the per-frame index, not the frame-0 WCSLink's.
- [ ] **M1** `wp1-dn-per-s`: `_cube_data` adds '<label> DN/s', a `DerivedComponent` (`units='DN/s'`) dividing flux by `Exposure time` under `np.where(... > 0, ..., np.nan)`; while a probe finds core drops `units` from sessions it is a subclass whose `__gluestate__`/`__setgluestate__` save `units` (register row, retired by `wp0-core-derived-units`; kept importable). Done when on 3610108077 Si IV it equals flux / 7.999 s at normal steps and NaN at the 0-s step 157; a synthetic 0-s exposure gives NaN, not ±inf; on 4000255147 SJI 1400 it equals flux / EXPTIMES per frame; Profile y and the Image layer show 'DN/s'; a saved session keeps the expression and unit. Depends: wp3-app-session-acceptance (session check).

**M3**

- [ ] **M3** `wp1-stack-per-scan-wcs`: Per-scan 4D-stack spatial coordinates with an inverse (Scan slider = CRISPEX 'File no.'), inverting the forward table model of `IRIS_PLAN_PROTOTYPES/archive/probes-2026-09/cc_stackwcs.py`. Done when, on one window of the 8-scan 3400109360 and 99-scan 3602506433 stacks, scan-k pixel→world equals the scan-k file's WCS to 1e-6″ and round-trips to 1e-6 px within memory for one 99-scan window; on the 4000005156 2-scan stack a lon/lat subset from SJI 2796 selects the scan-k pixels; a `test_sessions.py` round trip passes. Depends: wp1-m0-link-hpc, wp3-wcs-saver.
- [ ] **M3** `wp1-nexp-prp`: NEXP_PRP > 1 scanning rasters repeat positions, so world→pixel returns each first exposure: warn once (not for sit-and-stare) and document it. Done when a synthetic NEXP_PRP=2 raster warns once and world→pixel returns steps 0, 2, …, 14; a spatial ROI selects both exposures of every position; 4000255147 (NEXP_PRP 1600) and the sns fixture give no warning.
- [ ] **M3** `wp1-m3-pointing-offset`: An optional `_GlueWCS` (dx, dy) arcsec offset in both directions, set by a 'Shift pointing…' `layer_action` (CRISPEX OFFSET_SJI) and saved by `wp3-wcs-saver`, plus a recipe checking FUV/NUV/SJI co-alignment on the slit fiducials. Done when (+2″, −1″) on 4000005156 SJI 2796 shifts its readout by exactly that and a raster ROI's SJI footprint by dx/CDELT px; (0, 0) restores it; it survives a session round trip; the recipe finds the fiducials in the Si IV 1403 and Mg II k spectrograms and SJI 2796 of 4000005156. Depends: wp1-m0-link-hpc, wp3-wcs-saver.
- [ ] **M3** `wp1-m3-multi-instrument`: Record a co-aligned IRIS–SST Level-3 pair from Rouppe van der Voort et al. (2020, A&A 641, A146), open it through the Level-3 input and link it by WCS autolinking, or by identity pixel links without an accepted celestial WCS. Done when a Pixel point on the SST cube gives the linked IRIS spectrum at the same position. Depends: wp8-m3-level3-input.

**M4**

- [ ] **M4** `wp1-m4-autolink-matrix`: When a `wcs_autolink` probe finds #2595, apply every stock suggestion under the adopted policies and extend `wp1-m0-link-graph-regression` (both-way ROI propagation) to: 4000005156 Si IV/SJI 2796, 4000255147 raster/SJI 1400, two 4000005156 scans, 3602506433 stack/scan, raster/sliced map, map/map, fixture SJI 1400/2796, rolled 3860608353 SJI 2832 and a 3640107442 AIA cutout, each against a covering map. Done when: (a) an SJI Pixel point gives the raster marker and spectrum; (b) scanning: a raster ROI selects the frame-0 WCSLink footprint in every SJI frame (documented); sit-and-stare: the 0 px result is diagnosed or pixel-ROI reach is declared unsupported; (c) an SJI/SJI Pixel point propagates with no time-axis link (xfail until `wp0-own-draft-updates` amends #2595); (d) WCSLinks leave `link_hpc` subsets unchanged; (e) results are identical over add orders; the rolled SJI readout matches the header WCS to 0.05 px; gated tests skip cleanly on 1.27.0. Depends: a core #2595 release, wp1-m1-wrapper-coherence, wp1-m1-sunpy-maps, wp1-m0-link-graph-regression.

### WP2: Line moments and diagnostics

Derived maps from IRIS spectra as D4 `layer_action`s: rewrap the Data as an
irispy cube, keep the numerics in irispy (except the continuum mean and the
saturation guard), add one linked Data and open no viewer. Files:
`glue_solar/sources/moments.py` (new, imported from `glue_solar.setup()`),
`glue_solar/tests/test_moments.py`, a `docs/user_guide/` page, `changelog/`.
No new required dependency.

**M2**

- [ ] **M2** `wp2-m2-moment-maps`: Port 'IRIS: line moments…' (data only, single selection) from `IRIS_PLAN_PROTOTYPES/chk_wp2/`. A rewrap helper builds a `SpectrogramCube` from a per-scan raster (component, mask, unit and a `copy.deepcopy` of the raw WCS taken under `WCS_LOCK`) and calls `calculate_moments` with an explicit centre (irispy falls back to TWAVE when the rest is None); SJIs and 4D stacks are refused with a message. The added Data has `intensity`, uint8 `mask` (D12), `centroid` and `sigma` (Å), `velocity` and `sigma_velocity` (km/s) and the source `Time`, all NaN and masked where the wings hold no valid sample (irispy gives 0); coords `_GlueWCS(SlicedLowLevelWCS(wcs_copy, (slice(None), slice(None), 0)))`; plain meta `moments_centre` (Å), `rest_wavelength` and `rest_wavelength_source` only when a rest applies, and `velocity_caveat` (WP5's `LEVEL2_CAVEAT`); exactly two `LinkSame` links between the spatial pixel components. Data, `Time`, meta and links go through WP5's derived-product helper (`wp5-m1-doppler-image`). Windows above about 5e7 elements run in a glue-qt `Worker`; Data and links are added on the main thread. Done when: on 4000005156 Si IV scan 0 exactly one such Data with two links is added and no viewer opens; on 4000005156 C II scan 0 intensity is NaN, not 0, where spectra are -200 across the wings; a WP3 session with the map reopens with equal world coordinates; SJI, stack and failing inputs add nothing and the dialog stays open after an error; on 4000255147 Si IV the GUI thread blocks ≤ 0.5 s and peak RSS grows ≤ 3× the float32 window bytes. Depends: wp3-wcs-saver, wp3-plain-meta, wp5-m1-rest-wavelength-policy, wp5-m1-doppler-image.
- [ ] **M2** `wp2-m2-line-definition`: Take the line from WP5's rest helper and in-window candidate list (D11), never TWAVE. The dialog prefills the dataset's rest; with none it asks, pre-selecting the first `default_for` candidate; confirming a listed line stores it on the source as 'user choice' and the helper copies it to products. The centre and wing fields are a reusable widget (also `wp6-m2-fit-maps`'s fit window). Wings are required (default ±0.5 Å); a blank wing or centre adds nothing. Continuum windows (no packaged line) omit velocities and say why. An optional continuum window's per-pixel mean is subtracted first and published as `continuum`. Mg II h/k and C II windows get meta `line_regime = 'optically thick: centroid/width are proxies, not line-of-sight velocity'` and a warning. The last centre, wings and continuum range per window persist as `meta['moments_last']` on the source. Done when: on 3610108077 Mg II k the dialog asks for the line, pre-selecting 2796.352 Å with wings ±0.5 Å, and the median velocity has |v| < 5 km/s; C II 1336 asks for 1334.53 or 1335.71 Å, pre-selecting neither; the 2832 window publishes no velocity and no `rest_wavelength`; `continuum` and the subtracted intensity equal a numpy reference; after the user confirms Mg II k, source and products carry 2796.352 ('user choice') and the products `line_regime`; after a WP3 save and reopen the dialog opens with the last definition. Depends: wp5-m1-rest-wavelength-policy, wp3-plain-meta, wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-input-quality`: The input is the flux or WP1's '<flux> DN/s' (the default when present); the minimum intensity is in that unit (times Å when integrating). NaN and -Inf samples are masked. Saturation is tested in DN on the raw flux inside the wings, because irispy zeroes non-finite samples first: any +Inf sample (ITN 26) or a peak above the limit makes the pixel NaN and masked in every product. The dialog warns when any NSATPIX/TSATPXn count is above 0. The saturation test and warning are one helper, reused by `wp6-m2-quality-filter`. Done when on 3610108077 Si IV, at non-zero-exposure steps, DN/s intensity equals DN intensity / exposure time; a synthetic spectrum with one +Inf sample is NaN in all products and one with a -Inf sample matches that sample masked; a DN limit flags the same pixels for DN and DN/s input; a header with TSATPX1 > 0 shows the warning. Depends: wp1-dn-per-s, wp2-m2-moment-maps.
- [ ] **M2** `wp2-m2-tests-docs`: irispy fixtures (via `find_irispy_test_file`; decimated 10×, Mg II 0.2546 Å/px, so ±0.5 Å holds about 4 samples) test only shapes, units, masks and plumbing, plus: a continuum window gives no velocity, a blank centre or invalid input adds nothing, spatial subsets propagate both ways, and the WP3 round trip holds. Numbers are tested on a synthetic `SpectrogramCube` (Gaussian plus noise, masked samples, one +Inf, one -Inf) against the truth, and on irispy-data's 3400109360 cutout (remote data) against a numpy reference. Port the TWAVE-fallback and layer-action-trigger checks from `IRIS_PLAN_PROTOTYPES/wp2_moments_proto.py`. Add a user-guide page, API entry and changelog fragment covering product choice, FWHM ≈ 2.355 σ, sigma inflation for faint lines from irispy zeroing bad samples and the minimum-intensity threshold that limits it, thin versus optically thick lines, and Profile Collapse. Done when `test_moments.py` passes on the D5 baseline and Sphinx builds with `-W`. Depends: wp2-m2-moment-maps, wp2-m2-line-definition, wp2-m2-input-quality.

**M3**

- [ ] **M3** `wp2-m3-moments-extensions`: (1) 4D stacks: (scan, step, slit) maps with three pixel links, via WP6's sliced-coords contract. (2) Profile-range wings: a Profile `viewer_tool` subclassing glue-qt's public `RangeMouseMode` opens `MomentsDialog` with the dragged range, converted from `x_display_unit` to Å, as wings (a `layer_action` gets no viewer or range); never read the private `_profile_tools.rng_mode`. Done when a 4D stack from the irispy fixture gives maps of its (scan, step, slit) shape with three links, scan 0 equals the per-scan action and the map survives a WP3 round trip; a dragged range opens the dialog with those wings, and one not containing the centre is refused. Depends: wp2-m2-moment-maps, wp2-m2-line-definition.
- [ ] **M3** `wp2-m3-window-data`: Uncertainties, error maps and binning. (1) Opt-in `read_files(..., uncertainty=True, memmap=False)` in `glue_solar/sources/loaders/iris.py` adds '<flux> uncertainty' (eager float64, about 3× the float32 window); irispy ≥ 0.9.1 flips it with the data and gives none for memmap. (2) Once an irispy release has #201, the moments action adds `intensity_error`, `centroid_error`, `width_error`, `velocity_error` and `velocity_width_error` from each map's `StdDevUncertainty` (statistical only, per #201's notes). (3) 'Rebin…' wraps `NDCube.rebin` for spatial and spectral binning in a `layer_action` adding a Data with `_GlueWCS(ResampledLowLevelWCS(...))` coords, linked by `link_hpc`. Done when on 3610108077 Si IV 1403 the uncertainty equals the irispy-loaded cube's; on 3400109360 it follows the data's step order; the error maps equal irispy's output; a 2×2 spatial rebin halves both spatial dimensions and preserves the mean of finite samples; the rebinned Data links through `link_hpc` and survives a WP3 round trip. Depends: wp2-m2-moment-maps, wp1-m0-link-hpc, a `wp3-wcs-saver` record for `ResampledLowLevelWCS` (rebin only), an irispy release with #201 (error maps only).
- [ ] **M3** `wp2-irispy-calibration-actions`: Two D4 actions on the rewrap helper, which here keeps the SGMeta and restores the 'exposure time' extra coordinate from WP4's 'Exposure time' component: 'Remove dust' (`SJICube.remove_dust`) on an SJI and 'Radiometric calibration' (`irispy.utils.spectrograph.radiometric_calibration`, packaged response, no download; 0 s exposures become NaN) on a per-scan raster. Each adds one Data linked on every pixel axis and opens no viewer; data without SGMeta (for example restored from a session) is refused. Done when on 4000255147 SJI 1400 'Remove dust' equals the direct `remove_dust` (`exposure_normalize=True`); on 4000005156 Si IV scan 0 calibration equals the direct call (rtol 1e-6) and the Profile shows erg s⁻¹ sr⁻¹ cm⁻² Å⁻¹; a raster given to 'Remove dust', or an SJI given to calibration, adds nothing. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-m3-mg-features`: A D4 'IRIS: Mg II features…' action on a per-scan raster window covering Mg II k and/or h calls `irispy.utils.mg_features.calculate_mg_features` (#199) through the rewrap helper and adds one Data with the velocity (km/s) and intensity of k2v, k3, k2r, h2v, h3 and h2r, NaN and masked where not found, linked to the source like the moment maps, with the `line_regime` proxy meta; no viewer. Done when, on 3824262996 Mg II k, the components equal a direct irispy call, spectra with missing data are NaN, and the maps link to the source raster with no viewer opened. Depends: wp2-m2-moment-maps, an irispy release with #199.
- [ ] **M3** `wp2-m3-density-temperature`: A D4 action on two same-grid WP2 intensity maps (for example O IV 1399.77/1401.16 from the Si IV 1403 window) calling `irispy.utils.density.density_diagnostic` with a fiasco `Ion`, or `map_ratio_to_quantity` for temperature ratios, adding one linked log n_e (or T) map; fiasco and CHIANTI stay optional. Done when, with fiasco installed, a synthetic ratio map gives the same densities as a direct irispy call; a real O IV pair gives a linked log n_e map; without fiasco the action refuses and adds nothing. Depends: wp2-m2-moment-maps.
- [ ] **M3** `wp2-burst-detection`: A D4 'IRIS: detect UV bursts' action calls `irispy.utils.bursts.find_si_iv_bursts` on a raster window covering Si IV 1402.77 Å (chosen by wavelength coverage, so 'Si IV 1394' windows that span it qualify) or `find_sji_bursts` on an SJI 1400 (#197), and adds the int32 event-label map as a Data linked to the source on its pixel axes, with the events table as a second Data; no viewer. Done when on 4000255147 SJI 1400 and Si IV 1403 (4 pixels in one event at the default threshold) the labels equal irispy's, have the source's spatial and time shape, a subset on them propagates to the source, and other SJI channels and windows not covering 1402.77 Å are refused with a message. Depends: wp2-m2-moment-maps, an irispy release with #197.

Notes:
- Profile Collapse is a display-only quicklook: no dataset, index-based moments, NaN if any sample is NaN.
- Velocities are relative to the uncorrected Level-2 wavelength scale (`velocity_caveat`); irispy #198 measures the orbital drift but nothing here applies it yet. Mg II and C II centroids and widths are proxies.
- The +Inf guard covers a code path only: local int16 Level-2 files cannot store Inf, and all show NSATPIX 0.
- The 0.5 s and 3× limits are local acceptance numbers, not CI thresholds. The rewrap deep-copies the raw WCS under the lock; the Worker and map coords use only that copy.

### WP3: Sessions

Save and Open Session must work on released core for a coordinated IRIS
quicklook and every glue-solar dataset (SJI, raster windows, stacks, sunpy
Maps, derived maps), through glue's hooks and registries (D13). No M0 work:
until M1 the docs say sessions with any glue-solar dataset fail to save.

Port: `IRIS_PLAN_PROTOTYPES/wp3_impl.py` (parts: module-level record builders
in `glue_solar/sources/loaders/iris.py`, `read_iris_rasters` as a named
factory, `image_data` replacing `read_iris_image`; no import-time rebinding)
and `IRIS_PLAN_PROTOTYPES/wp3chk_test_sessions.py` (the 6 tests and helpers
into `glue_solar/tests/test_sessions.py`, with `find_irispy_test_file`
fixtures, a < 100,000 B size assertion and the production style `_type`).

**M1**

- [ ] **M1** `wp3-style-cmap`: Make styles and colormaps session-safe without core #2597: `SolarVisualAttributes`, whose `__gluestate__` saves `preferred_cmap` by name (unknown names restore as `None`), used by `_cube_data` and both map loaders only while a probe shows core saving a Colormap object (register row; the class stays importable); `setup()` registers matplotlib's named colormap copies so core's `_load_cmap` resolves `cmap.name`. No global `VisualAttributes` saver. Add a changelog fragment and a sessions note in `docs/user_guide/loading-aia-and-hmi.rst`. Done when an application session holding only an AIA map opened with the 'sunpy Map' factory restores with cmap `sdoaia171`; `SolarVisualAttributes(preferred_cmap='irissji1400')` on a plain `Data` round-trips through `GlueSerializer`; a plain `Data` style record keeps glue's `_type` and has no `_protocol`.
- [ ] **M1** `wp3-wcs-saver`: `_GlueWCS.__gluestate__`/`__setgluestate__` in `glue_solar/sources/loaders/iris.py` (builders module-level, for WP12's export). Records: gWCS as ASDF; FITS WCS as header plus `pixel_shape`; -TAB (irispy's 3-axis raster layout only) as header plus the rebuilt WCS-TABLE, table axes from `PSi_1` and an index column only where `PSi_2` exists (irispy ≥ 0.9.1 writes none); `SlicedLowLevelWCS`/`CompoundLowLevelWCS` recursively with slices, mapping and shape, any `numbers.Integral` index cast to `int`. Anything else raises a `GlueSerializeError` naming it. Declare `asdf` and `gwcs`. Done when `test_sessions.py` round-trips each case twice with pixel↔world agreeing to 1e-9 on integer and +0.37 pixel grids and equal axis names, units, labels, arrays, masks and `Time`: a real SJI; a raster window; a 3-scan stack; a 3400109360 negative-step window (local); a wrapped sunpy Map and a mixed collection; an `np.int64`-indexed `SlicedLowLevelWCS`; the WP2 moments form on a real raster's -TAB WCS. irispy's `make_spatial_template`/`dropaxis` 2-D -TAB WCS raises `GlueSerializeError` naming the layout, with nothing written.
- [ ] **M1** `wp3-quantity-meta`: Save Quantity meta as value and unit without mutating the live meta (D13): register `@saver(u.Quantity)` only if `u.Quantity not in GlueSerializer.dispatch`, and the loader only if absent, using `wp0-core-quantity-saver`'s version-1 record so either saver's sessions load with the other; retire when a core release has it. Document that core omits `Time`/`SkyCoord` meta ('auxiliary times', 'exposure FOV center'). Done when a real raster restores `meta['exposure time']` as an equal `Quantity` in s, and importing glue-solar after another Quantity saver and loader are registered raises nothing.
- [ ] **M1** `wp3-plain-meta`: Make window identity and rest wavelength survive sessions as plain JSON meta: `meta['spectral_window']` (TDESC; scan 0's for stacks), `rest_wavelength` (float, Å) and `rest_wavelength_source` written by `wp5-m1-rest-wavelength-policy`, plus the derived products' `moments_centre`, `line_regime`, `velocity_caveat`, `doppler_sign`, `fit_seed_center` and the source's `moments_last`. Readers use only these keys; restored datasets have no SGMeta. Done when, on 3824262996 r00000: Si IV 1403, saved with an Å Profile showing the km/s top axis, reopens with that axis, rest 1402.77 ('line list') and `spectral_window` unchanged; Mg II k has no rest after load, and after the user picks k it saves and reopens with 2796.352 ('user choice'); C II 1336 with no line picked has neither key; once the `wp5-m1-velocity-axis` probe passes, km/s Profile x axes reopen offering km/s; the derived-product keys survive as plain JSON. Depends: wp5-m1-rest-wavelength-policy, wp5-m1-velocity-axis, wp3-quantity-meta, wp0-core-profile-restore-priority.
- [ ] **M1** `wp3-file-references`: Route browser loads through `load_data` so sessions reference files: `QtIRISImporter` calls a new path-first factory `read_iris_rasters(path, files=None, windows=None, stack=False)` (`files` relative to the first file's folder) and the public `image_data(path)`; derived maps stay embedded. These two paths and File → Open's `glue_solar.sources.iris.read_iris_file` are a session format (keep aliases if they move). Done when a browser-loaded SJI 1400 and a 3-scan C II 1336 stack have `_load_log`, their `include_data=False, absolute_paths=False` session is < 100 KB with relative names; after moving files and session to a new folder it restores, re-saves and restores again with equal data; a raster opened with File → Open restores from its file with every window.
- [ ] **M1** `wp3-session-budget`: Keep sessions small. Released core embeds every component without a LoadLog, even with `include_data=False` (21.3 MB for one int32 (100, 200, 200) broadcast). Factory-built components (`Time`, `Exposure time`, uint8 masks) are LoadLog-referenced; a full-shape post-load component is an expression `DerivedComponent` or a `BroadcastComponent` saving only its 1-D values, axis and shape. WP6 products add at most 2× their 2-D map bytes; the opt-in float32 residual is embedded outside the budget. Done when a file-referencing session of 4000255147 with Si IV, one more window and SJI 1400, time sync and a Pixel point is ≤ 1 MB and saves in ≤ 2 s; the fixture session stays < 100 KB; a test fails if an IRIS dataset gains a component with no LoadLog that is neither derived nor compact. Depends: wp3-file-references, wp4-time-sync.
- [ ] **M1** `wp3-coordination-reattach`: Re-attach WP4 coordination after a restore through the D9 tools, which glue-qt recreates for restored viewers; each registers with the per-DataCollection coordinator (created on demand, held strongly), which at creation scans `dc.subset_groups` for a `PixelSubsetState` (a restore sends no `SubsetUpdateMessage`). Persist only the time master and timing step as `meta['quicklook_time_master']` and `meta['quicklook_timing_step']`; recompute the rest. Done when, after restoring a saved quicklook in a new `GlueApplication`: no slider moves until the user acts; the saved master is still master with the same offsets and NO MATCH labels; Pixel drags on raster map and SJI drive the other panels; one click gives one `group.subset_state` assignment and at most one `SubsetUpdateMessage` per dataset; the 'Exposure time' component and per-frame meta arrays equal their pre-save values. Depends: wp4-time-sync, wp4-m0-point-fixed-index, wp1-m1-sji-to-raster, wp3-wcs-saver, wp3-quantity-meta, wp3-style-cmap.
- [ ] **M1** `wp3-app-session-acceptance`: A pytest-qt test saves and restores, file-referencing and twice, (a) 4000255147 sit-and-stare + SJI 1400 and (b) 4000005156 raster + SJI 2796, each with an AIA map from File → Open, covering raster-map, spectrogram, SJI and spectrum viewers; a Profile with a non-default `x_att` in Å and nm (km/s once the `wp5-m1-velocity-axis` probe passes); Pixel and ROI subsets; WCS and `link_hpc` links; the MDI tab geometry. Then replace the 'Saving sessions' warning in the IRIS loading guide and add a changelog fragment. Done when viewer types, attributes, slices, limits, stretch, `cmap_bad`, layer `visible`/`zorder` and cmaps (`irissji1400`, `sdoaia171`) equal the originals; raster viewers return as the `wp10-m0-roi-guard` subclass from `glue_solar/quicklook.py`; subsets, links and tab geometry are equal; the `wp3-coordination-reattach` checks pass and the session meets `wp3-session-budget`. Depends: the other WP3 M1 items, wp0-core-profile-restore-priority, wp4-quicklook-preset, wp1-m0-link-hpc, wp1-m1-sunpy-maps, wp5-m1-velocity-axis, wp1-m1-wrapper-coherence.

**M3**

- [ ] **M3** `wp3-last-session`: Reopen the last session (CRISPEX LAST_SESSION). The quicklook entry connects `QApplication.aboutToQuit` on first run (never in `setup()`). The handler returns if the components glue would embed exceed 1 MB; else `GlueSerializer(app, absolute_paths=True).dumps()`, swallowing every exception, and writes a result ≤ 1 MB made in ≤ 2 s via a temp file and `os.replace` to `iris_last_session.glu` under `glue.config.CFG_DIR`. Add a menubar action 'IRIS: reopen last session' and a `startup_action` 'iris_last_session'. Done when, headless with `CFG_DIR` in `tmp_path`, the handler after a quicklook writes the file and a new app plus the menu action restores the viewers; with a 100 MB embedded dataset it returns in < 0.1 s and writes nothing; a serialization error writes nothing and opens no dialog. Depends: wp3-app-session-acceptance, wp4-launch-entry.

Notes:
- Sessions record `glue_solar` class and function paths, so loading needs glue-solar.
- New coords types (WP1, `wp2-m3-window-data`'s `ResampledLowLevelWCS`, WP12) each reuse or add a record kind and a round-trip case. `wp1-m1-sunpy-maps` merges after or with `wp3-wcs-saver`; wrapping maps earlier breaks their sessions.
- LoadLog cannot replace the WCS saver: glue saves `data.coords` for every dataset.
- Known gaps: 'include data' sessions embed every array and are unbudgeted; the colormap combo labels `sdoaia171` as GOES-R SUVI 171 (cosmetic).

### WP4: Quicklook preset and coordination

A CRISPEX-style IRIS quicklook from stock Glue viewers (new
`glue_solar/quicklook.py`; `glue_solar/tools.py`); M0 runs on the D5 baseline
with no glue links (D8).

Panels (plus per-channel SJI viewers and the point spectrum; stacks open only
from the browser and menu):

| Observation | Map | Spectrogram | λ vs step or time |
|---|---|---|---|
| Raster (step, slit, λ) | step × slit at λ0 | λ × slit at the point's step | whisker: λ × step at the point's slit |
| Sit-and-stare (exposure, slit, λ) | 'Slit vs time': exposure × slit at λ0 | λ × slit at the point's exposure | λ–t: λ × exposure at the point's slit |
| Stack (scan, step, slit, λ) | step × slit at (current scan, λ0) | λ × slit at (scan, point's step) | λ–t: λ × scan at the point's (step, slit) |

Port (see [Prototypes to port](#prototypes-to-port)): `nearest`,
`exposure_times` and `observation_key` from `wp4_common.py`; approach C of
`slit_check.py`; the `mouse()`/`select_point()` helpers and point-drag test
from `review_20260923/test_existing_workflows.py` into
`glue_solar/tests/helpers.py`, finding components by physical type, with a
modal guard, asserting band intersection only for same-dataset points.

**M0**

- [ ] **M0** `wp4-coordinator`: One `Coordinator` (`HubListener`) per DataCollection, held strongly on it, plus a registered `solar:coordinate` `SimpleToolMenu` (D9; 'Time master', 'Clear point') that registers viewers in `__init__` and unregisters idempotently in `close()`; each subtool restores the previous mouse mode. It couples only equal `observation_key`s (OBSID + STARTOBS), follows the last group given a `PixelSubsetState`, re-applies the point on axis or reference-data changes, and writes only on change under one busy guard. Done when: viewers opened later or restored join and closed ones leave (a second unregister raises nothing); one map click on a 3D raster gives one `group.subset_state` assignment, ≤ 1 `SubsetUpdateMessage` per dataset and no coordinator assignment, while on a 4D stack map the coordinator adds exactly one assignment pinning the scan (≤ 2 messages, no feedback); Pixel stays active after 'Clear point' and 'Time master'; after the stock combo swaps the 4000005156 map to λ × slit, its step slider equals the point's and no wavelength slider moved; a second loaded observation is never coupled.
- [ ] **M0** `wp4-quicklook-preset`: `quicklook(app, datasets)` opens the panel table in a new MDI tab (D15), wiring in `wp10-m0-roi-guard` and `wp10-m0-large-data-modal` in the same PR. Roles come from INSTRUME or cube class; sit-and-stare from STEPS_AV == 0 and NRASTERP; the window is the browser's tick, else Mg II k 2796, else the first; λ0 is nearest TWAVE (mid-window without TWAVE), never index 0 or the D11 rest. Given 'SJI_<c>' and 'SJI_<c> (deconvolved)' (#62), open the plain one and offer the other. Raster and SJI layers get `percentile = 99.5`; aspect 'auto' on rasters until `wp11-physical-aspect`, 'equal' on SJIs; the Profile shows the bare Pixel subset's mean with a y = 0 line and no x display-unit override; the point starts at the map centre in a new edit-subset group 'Point' with Pixel active. Done when offscreen pytest-qt on 4000255147, 3824262996, 4000005156 (stack, deconvolved SJI 2796), 3620258102 and 3860258481 (one scan; 13 stacked) shows each viewer's `x_att`, `y_att` and `slices` match its row; `app.viewers` lists every panel; layers have percentile 99.5 and finite v_min < v_max; the Profile shows only the seeded Pixel subset; the stock axis combo still swaps spectrogram and map; no modal appears with the large-data prompt unpatched; a 3640107442 AIA cutout rewritten to 4000255147's OBSID and STARTOBS gets no SJI role or slit. Depends: wp4-coordinator, wp1-m0-link-hpc.
- [ ] **M0** `wp4-launch-entry`: Entry points: `@startup_action('iris_quicklook')`; an 'Open quicklook' checkbox beside 'Stack' in `iris_loader.ui`, with `browse_iris` building one quicklook per loaded observation (`finalize` records each dataset's observation and kind through a per-window helper that `wp10-nonblocking-load` reuses); a menubar action 'IRIS: quicklook…' grouping data by `observation_key` and asking when several match. Startup cannot stack: it opens the single-raster preset on the first scan, labels files by rNNNNN and notes that stacks need the browser. Its guide section maps CRISPEX entry keywords and xcontrol modes to their owners (no CLI parser). Done when, with warnings and message boxes patched to fail: on 3620258102 + SJI 1400 the three paths open identical viewers; with two observations loaded, browser and menu open only the chosen one; startup on the 13 3860258481 files gives 13 distinct labels and the single-raster preset; with #2595 (probe-gated) `--startup=iris_quicklook` opens no AutoLinkPreview; a manual 4000255147 run shows no 'Add large data set?' dialog. Depends: wp4-quicklook-preset, wp10-m0-large-data-modal.
- [ ] **M0** `wp4-m0-point-fixed-index`: The stock Pixel point is the selected detector pixel (D6, D7). On each point update the coordinator writes its step, exposure or scan and slit into the other same-dataset panels' non-displayed `slices` (a stack's point stays on the current scan), coalescing drag updates latest-only with a single-shot QTimer. A λ-panel click is canonicalised once: the point takes that panel's fixed indices and the clicked non-λ index, and the map moves to the clicked λ; nothing else writes a wavelength slice. Slider edits move the point. 'Clear point' or any non-Pixel state stops point updates and hides markers; time sync continues. SJI points mark only the SJI until `wp4-sji-click-to-raster`. Done when, on 3860258481 (one scan; 13-scan stack), 3824262996, 4000005156 (stack) and 4000255147: a map click at (s, y) sets the spectrogram step to s and the whisker/λ–t slit to y with no wavelength slider moving; the spectrum is cube[s, y, :] (cube[k, s, y, :] at scan k) and follows scan changes; on 4000005156 scan 0 a spectrogram click at (λj, y) moves the map to λj and the point to (s, y); typing step s′ moves crosshair and spectrum with one `group.subset_state` assignment; slit (and on rasters and stacks the step) stays fixed while scan, exposure or SJI master steps; a Profile Collapse `AggregateSlice` raises nothing and is never overwritten. Depends: wp4-coordinator, wp4-quicklook-preset.
- [ ] **M0** `wp4-time-sync`: The coordinator caches per-pair nearest-index and signed-offset arrays from `nearest()` over each dataset's 1-D `Time` (D7, D8, D10) and adds no links or components after load. The raster is the default master ('Time master' switches to an SJI); its timing step is the point's step (mid-raster without a point). An SJI master moves only time axes (for a stack, the scan whose timing-step `Time` is nearest). A single scanning raster has no time axis: it shows its signed Δt at the timing step and is NO MATCH only outside its coverage. `solar:frame_time` shows 'time master' and the timing step on the master, the signed Δt on matched followers and 'NO MATCH Δt = …' on greyed followers, which keep their frame. Every registered viewer tool (WP7 `solar:time_marker`, WP12 light curves) gets each master-time change and exposure duration. Done when:
  1. 4000005156 2-scan stack + SJI 2796 (32 frames, 11.69 s), point at step 32. SJI master: frames 0-15 select scan 0 and 16-31 scan 1; frames 0, 20, 31 show Δt +85.0, +38.1, −90.5 s; step and slit unchanged; with scan 0 alone frames 16-31 are NO MATCH. Raster (scan 0) master: step 0 makes the SJI NO MATCH (Δt 8.611 s > 5.845 s); steps 1-3 match (5.581, 2.721, 0.069 s).
  2. 4000255147 (1600 × 2.89 s) + SJI 1400 (400 × 11.88 s): indices are argmin|Δt|; in coverage |Δt| ≤ 1.445 s (raster), ≤ 5.94 s (SJI); an SJI master keeps the slit fixed.
  3. 3400109360 (descending `Time` per scan), one scan and a 2-scan stack, with a synthetic SJI spanning them: indices equal the argsort reference, matched |Δt| < half the cadence, ties go to the earlier time and duplicates to the first index.
  4. `nearest()` units: an exact tie, duplicates, a gap, a NaT reference frame (raises), times before and after coverage.
  5. Wavelength and slit sliders never move; a Profile Collapse `AggregateSlice` on the master gives the time index by `.center` and is left in place on a follower.

  Depends: wp4-coordinator, wp4-m0-point-fixed-index, wp1-m0-link-hpc.
- [ ] **M0** `wp4-m0-time-wavelength-panels`: Whisker and λ–t panels are stock ImageViewers (x wavelength pixel; y step, exposure or scan; unwarped), titled 'step (acquisition order)', 'exposure' or 'scan'. On a sit-and-stare step axis `solar:frame_time` sets the label 'Exposure (acquisition order)' and integer exposure-index ticks, re-applied after every `_set_wcs` label reset and axis change. A probed private patch (D2) stops the Pixel crosshair reappearing at (0,0) after an IncompatibleAttribute. Done when: on 4000255147 Si IV 1403 a point at slit y makes λ–t equal cube[:, y, :] and the label shows the UTC range, surviving a slit move and an axis swap; on the 3860258481 13-scan stack and 3602506433 (99 scans) λ–t equals stack[:, s, y, :] and follows a drag; on 4000005156 scan 0 the whisker equals cube[:, y, :]; no (0,0) crosshair appears on spectrogram, whisker or λ–t panels, and the patch turns off when its probe sees the upstream fix. Depends: wp4-quicklook-preset, wp4-m0-point-fixed-index.
- [ ] **M0** `wp4-sji-panels`: One ImageViewer per selected SJI channel, titled with channel and variant, following `wp4-time-sync`, with limits of the raster footprint plus a margin; off-frame points show 'outside SJI FOV'. Done when the 3620258102 fixture with SJI 1330, 1400, 2796 and 2832 opens four titled SJI viewers that follow the master; on 4000005156 + SJI 2796 the limits contain the four raster-footprint corners; test points > 2 SJI px inside and outside the FOV get the expected label. Depends: wp4-quicklook-preset, wp4-time-sync, wp1-m0-link-hpc.
- [ ] **M0** `wp4-slit-point-overlay`: `solar:coordinate` draws on SJI viewers a slit line at the frame's SLTPX1IX − 1 (the slit extra coordinates are 1-based; irispy ≥ 0.9.1's gWCS uses CRPIX − 1), hidden for a displayed frame axis or a 0/NaN value, and the raster point via `show_crosshairs`, projected through the frame's SJI WCS. No `pixel_stride` or 'Slit x' component enters the API; fixture tests rescale the stride-10 SJIs themselves. Done when on the full-resolution 4000255147 SJI 1400 (400×417×388) the line is within 0.5 SJI px of the projected raster slit at frames 0 and N−1 and 1 px at every frame (`slit_check.py` approach C); on the binned 3860608353 SJI 2832, at frames 0, N//2 and N−1 it lies within 0.5 binned px of the dark slit trough in that frame's column-median profile; the marker follows the frame, hides off the FOV and stays with `link_hpc` and time sync active. Depends: wp4-sji-panels.
- [ ] **M0** `wp4-tests`: Write `glue_solar/tests/test_quicklook.py` test-first on named data with the ported helpers, QSettings isolation plus an isolated HOME, dialogs patched to fail, and a manual native-GUI checklist. Each interaction (SJI frame change, map click, λ-panel click, scan/exposure change, spectrogram slider edit) asserts which panels move and which stay. Regressions: V34 rasters, sit-and-stare labels, AIA classification. Crash stress runs belong to `wp10-m0-acceptance`. Done when the suite passes in `iris-plan`, real-data tests are remote-data tests on LM-SAL/irispy-data files, and CI runs the fixture and `online` cases. Depends: wp4-quicklook-preset.

**M1**

- [ ] **M1** `wp4-m1-hover-lock-tool`: A 'Follow/lock' `PixelSelectionTool` subclass with its own icon. Unlocked, motion sets the followed group's `subset_state` on each new rounded pixel, latest-only at 50 ms and outside the command stack; the first hover creates the group if needed and leaving the axes stops updates. A left click locks through one undoable `ApplySubsetState`; a right click, Esc or the toggle unlocks (middle click is `wp11-distance-measure`'s). Done when, via canvas motion events on 3860258481, 3824262996 and 4000255147, hovering moves crosshairs and point spectrum within the WP10 click budget; 100 motion events give ≤ 1 subset update per 50 ms and leave the command stack unchanged; the lock survives scan and exposure stepping; a right click unlocks; stock Pixel is unchanged. Depends: wp4-m0-point-fixed-index.
- [ ] **M1** `wp4-sji-click-to-raster`: The coordinator maps an SJI Pixel point with `sji_to_raster()` to the raster `PixelSubsetState`, which replaces the SJI state in the group (Replace mode, re-entrancy guard); off-FOV points set nothing and show 'outside raster FOV'. The SJI click's `ApplySubsetState` is the only undo entry, so one undo reverts both. Done when, on 4000255147 and 4000005156, the `wp1-m1-sji-to-raster` 0.5 px cases pass through the UI with the spectrum equal to the raster data there; one SJI click gives the SJI assignment plus exactly one coordinator assignment and one undo restores the previous point; the `wp1-m0-link-graph-regression` checks pass with this path active. Depends: wp1-m1-sji-to-raster, wp4-m0-point-fixed-index, wp4-time-sync.
- [ ] **M1** `wp4-profile-aggregation`: An 'Aggregation' subtool on the Profile's `solar:coordinate` picks single sample, mean, sum or a wavelength band. Single sample is the bare Pixel point's mean; mean and sum are native Profile functions; a band light curve is a data-only subset the coordinator updates with the point, never intersected with Pixel. Done when on 4000255147 Si IV the band light curve equals nanmean(cube[:, y, j0:j1], axis=1) and follows a drag; with a band active on 4000005156 the linked-window marker and spectra still appear, and titles name the choice. Depends: wp4-m0-point-fixed-index, wp4-m1-spectral-coupling.
- [ ] **M1** `wp4-slice-profiles`: A glue-solar point spectrum for the Profile viewers: the coordinator keeps one data-only subset per raster dataset that selects exactly the Pixel point's step and slit and the master-matched scan or exposure (`==` subset states on the pixel components, ANDed), and updates it with the point and the WP4 master; the Profile's Mean of it is the spectrum at those indices. It is never intersected with the Pixel subset, which keeps the crosshair. Public glue API only, no patch. Done when on a ≥ 4-scan 3602506433 stack a Pixel point gives a Profile layer equal to `stack[k, s, y, :]` exactly, with k the scan matched to the master time, and it follows a drag and a master change; on 4000255147 it equals `cube[e, y, :]` at the matched exposure e; the Pixel crosshair stays visible. Depends: wp4-m0-point-fixed-index, wp4-time-sync, wp4-profile-aggregation.
- [ ] **M1** `wp4-m1-spectral-coupling`: `solar:coordinate` joins `ProfileViewer.tools` and draws plain lines: each same-dataset Image viewer's wavelength in every Profile; wavelength and master-time lines on whisker and λ–t panels; a Doppler-mirror line at 2λ0 − λ from the WP5 rest. The km/s top axis is `wp5-m1-velocity-axis`'s. It adds an 'Average spectrum' toggle and copies the Profile x-range to the λ–t x-limits. Accepted gaps: global cross-window ranges, restricted slider stepping, stepping across concatenated windows. Done when, on 4000005156 scan 0 (Si IV 1403, Mg II k) and 4000255147 with a λ–t panel: slider index k puts the marker at λ[k] in Å and nm and it hides for a Scan or pixel x axis; λ–t lines follow their sliders through axis swaps and resets; Navigate to λ[j] moves the map to j (km/s sub-check xfail on a Qt #70 symbol); Profile limits of ±100 km/s around Mg II k set the matching λ–t limits (Å limits on 0.4.2); a marker update costs < 5 ms; markers survive a WP3 save and restore and closing a viewer removes its callbacks. Depends: wp4-m0-time-wavelength-panels, wp4-time-sync, wp5-m1-rest-wavelength-policy, wp5-m1-velocity-axis, wp1-m1-wrapper-coherence, wp3-coordination-reattach.
- [ ] **M1** `wp4-m1-multi-window`: Per ticked window the preset opens a spectrum Profile and, if the type has one, a λ–t panel. An idempotent helper adds identity `LinkSame` links between the step/exposure/scan and slit pixel axes of same-file windows, so one Pixel point drives every window; WP5's derived-product helper reuses them. Done when, on 4000005156 scan 0 with Si IV 1403, C II 1336 and Mg II k ticked, exactly three Profiles open and a point at (s, y) gives each cube_w[s, y, :]; re-running the helper adds 0 links; each window's Image viewer has the crosshair at (s, y); with #2595 (probe-gated) an inter-window WCSLink changes no result; a Pixel click on a synthetic derived map linked by the helper moves the source panels. Depends: wp4-quicklook-preset, wp4-m0-time-wavelength-panels, wp1-m0-link-graph-regression.
- [ ] **M1** `wp4-context-reference`: An aligned AIA cutout (paired by OBSID + STARTOBS) opens a reference ImageViewer that follows `wp4-time-sync` and draws the IRIS slit and footprint from the raster WCS via `link_hpc`. `is_iris_fits` reuses `scan._is_supported_file`, so File → Open also accepts `aia_l2_*` files with INSTRUME AIA*. Hinode/SOT (ITN 32) cubes follow once irispy reads them (`wp0-irispy-requests`). Done when File → Open of a 3640107442 `aia_l2_*.fits` gives a Data with `Time` and `_GlueWCS` that follows the master; a generic AIA FITS is not claimed by the IRIS factory; with the matching 3640107442 IRIS raster and SJI (skipped if absent) the reference slit is within 0.5 AIA px of the raster-WCS slit at the matched time. Depends: wp4-sji-panels, wp4-time-sync, wp1-m0-link-hpc, wp1-m1-sunpy-maps.
- [ ] **M1** `wp4-time-controls`: A 'Playback' viewer_tool drives the master's `slices` with a QTimer: 'Go to UTC' (nearest master exposure), a frame range [lo, hi] with reset, and a play/stop toggle that `wp11-keyboard-shortcuts` binds to Space. Done when, with explicit timer ticks on 4000255147 SJI 1400, 'Go to 2013-09-02T17:00:00' selects argmin|Δt| and the raster follows; a [100, 120] loop visits only frames 100-120; the toggle starts and stops the timer and closing the viewer stops it. Depends: wp4-time-sync.
- [ ] **M1** `wp4-raster-overlays`: A 'Raster overlays' toggle shows the SJI footprint (a data-only subset ORing one thin `RangeSubsetState` per raster step at that step's slit position, projected through the SJI frame nearest its exposure; `slit_check.py` approach C) and a dashed map line at the current scan's step exposed nearest the master time, hidden on NO MATCH. Done when on 4000005156 (64 steps, SJI 2796) and 3860258481 (8 steps) the footprint has one column per distinct projected step, each within 1 SJI px of the header-derived position, and 4000255147 gives one column; on the 4000005156 stack with an SJI master and the point at step 32, frames 0-15 put the map line on scan 0 steps 3, 7, …, 63 and frames 16-31 on scan 1; both overlays survive closing and reopening viewers; a saved session grows < 10 KB. Depends: wp4-slit-point-overlay, wp4-time-sync, wp3-session-budget.

**M3**

- [ ] **M3** `wp4-playback-extras`: The `wp4-time-controls` popup gains fps, a frame increment k, bounce and 'N frames around current'; temporal blink (N ↔ N+k) reuses `wp5-m1-spectral-blink`. Done when, with explicit ticks on 4000255147 SJI 1400, bounce reverses at both ends; increment 3 steps by 3; the interval is 1000/fps ms; 'N = 10 around' sets [k−10, k+10], clipped; blink with k = 5 alternates N and N+5. Depends: wp4-time-controls, wp5-m1-spectral-blink.

Notes:
- SJI overlays and SJI-click translation use the per-frame SJI WCS, never frame-0 pixel links. A master change overwrites hand-moved follower sliders by design. With no SJI world-time link (D1), time-dependent pixel-ROI reach is a documented limitation.
- M0 saves no coordination state; from M1 the coordinator reads `wp3-coordination-reattach`'s meta keys. Overlays and markers are omitted from sessions and 'Save Python script', shown in 'Save plot' and redrawn on restore.
- MDI windows do not reflow; a reference-data change resets slices (documented in the guide).

### WP5: Spectral units, rest wavelength, line list, blink and Doppler

D11 rest wavelengths, km/s views, line labels, CRISPEX-style blink and the
Doppler image, through public registries (D2), in `glue_solar/spectral.py`
(new), `glue_solar/tools.py`, `glue_solar/data/iris_lines.csv` and
`glue_solar/sources/loaders/iris.py`. Each item ships with its guide section
and changelog fragment.

Port: `iris_lines.csv`, `wp5_units.py`, `wp5_override.py` (:13-28),
`wp5_linelist_mod.py` (without `brentq` and the exact-class style dict) and
`wp5_blink.py` (without the toolbar spinbox); tests
`review_20260905/test_line_positions.py` → `glue_solar/tests/test_linelist.py`
(adding a multi-axis session case, xfail until
`wp0-core-profile-restore-priority`) and
`review_20260905/test_refresh.py::test_blink_close_restores_original_visibility`
→ `glue_solar/tests/test_blink.py`.

**M1**

- [ ] **M1** `wp5-m1-line-list`: Ship `glue_solar/data/iris_lines.csv` with columns `wavelength` (vacuum Å), `name`, `source` (NIST ASD, CHIANTI or paper), `default_for` (a TDESC) and `calibration`. Keep the 11 lines; add Fe XII 1349.40, Mg II 2791.60/2798.75/2798.82, O IV 1404.78, S IV 1404.81/1406.02, Ni I 2799.474, S I 1401.515; Fe XXI is 1354.106. Ni I, S I and O I 1355.598 are calibration lines. `default_for`: Fe XII 1349 → 1349.40, Cl I 1352 → 1351.657, O I 1356 → 1355.598, Si IV 1394 → 1393.755, Si IV 1403 → 1402.770, Mg II k 2796 → 2796.352 and 2803.53; C II 1336 none. `LineListArtist` draws on Profile viewers via `layer_artist_maker` with the stock style editor; in WCSAxes mode it inverts the trace with `np.interp`, omitting markers off the trace. 'IRIS: Add line list' adds the list once as a plain Data to the active Profile. Done when on 3610108077 Mg II k labels for 2796.352, 2803.53, 2791.60, 2798.75 and 2798.82 sit within 1 display pixel in Å and nm; Fe XII 1349.40 appears in the 4000005156 Fe XII window; labels follow unit, visibility, colour and linewidth, vanish for a non-spectral x and go with their callbacks on removal; a later stock layer keeps its style editor; ported tests pass for both cdelt signs; the list round-trips through stock serializers; the CSV is in the wheel; the WCSAxes branch passes on the `wp0-stack-validation` roots (recorded).
- [ ] **M1** `wp5-m1-rest-wavelength-policy`: Implement D11 as one helper in `glue_solar/spectral.py`, the only rest source for WP2, WP4, WP6 and WP11: it returns `meta.get('rest_wavelength')` or None and never reads SGMeta or TWAVE. A second function returns the packaged lines inside the window, the `default_for` pre-selection and an ambiguity flag. The loader writes `meta['spectral_window']` on every raster window and stack, and `rest_wavelength` with `rest_wavelength_source` 'line list' only when exactly one `default_for` row lies in the window. 'Set rest wavelength…' (`layer_action`) shows value, source and `LEVEL2_CAVEAT` (velocities relative to the uncorrected Level-2 scale, good to about 5-10 km/s; ITN 26 §5.1, ITN 38 §4.2), lists in-window lines pre-selecting the first `default_for` candidate, and accepts a free Å value ('user choice' for a listed line, 'override' for a typed one); 'Reset to default' restores the default or deletes both keys; writes broadcast `NumericalDataChangedMessage`; windows with no packaged line are refused. Done when every window of 4000005156 has exactly the `default_for` value or no key and a stack takes scan 0's window; on 3824262996 the Mg II k window has no key after load, the candidate function and dialog pre-select 2796.352 and offer 2803.53, 2798.75, 2798.82 and 2799.474 with the ambiguity flag, confirming k stores 2796.352 ('user choice') and Reset removes both keys; C II 1336 has no key and offers 1334.53 and 1335.71; 2832 is refused, changing nothing. Depends: wp5-m1-line-list.
- [ ] **M1** `wp5-m1-velocity-axis`: In `setup()`, replace `unit_converter.members['default']` with a `SimpleAstropyUnitConverter` subclass adding 'km / s' (`u.doppler_optical(rest)`) only for the spectral world component and `centroid` of data with a rest, never for widths. A probe for glue-qt #70 (`ProfileTools._get_axis_and_pixel_slice` on a tiny nm-x Data) withholds km/s from world coordinate components until it passes. A Profile tool draws a top axis 'v [km/s], Level-2 λ scale' (`secondary_xaxis`) when x is spectral with a rest, sets `state.x_axislabel` to '<label> [<unit>]', and on `NumericalDataChangedMessage` calls the private `_update_x_display_unit_choices` (register rows). Done when on 3824262996 Mg II k with rest 2796.352 the top axis reads 0 km/s at 2796.352 Å through zoom, pan and Å/nm bottom units, and is absent for a non-spectral x, a km/s bottom axis or no rest; setting 1334.53 in an open C II Profile adds it and Reset removes it; on glue-qt 0.4.2 Profile x choices lack km/s but an Å `centroid` with a rest offers km/s as an Image colour unit (not `sigma`); non-IRIS 'm' still offers glue's 131 length units; nothing is written to settings.cfg; a saved Å Profile reopens with its top axis; once the probe passes, km/s appears in the Profile x choices, x-range selection and Collapse pick the same slices as in Å, labels sit within 1 display pixel in km/s, and a saved km/s multi-axis Profile reopens. Depends: wp5-m1-rest-wavelength-policy, wp1-m1-wrapper-coherence, wp0-core-profile-restore-priority.
- [ ] **M1** `wp5-m1-spectral-blink`: A checkable Image `viewer_tool`, registered idempotently, alternates two (dataset, wavelength index) positions in one viewer. Same-cube blink changes only slices with shared colour limits by default (optionally each plane's 99.5 percentile); cross-window blink alternates windows sharing the step×slit grid via WP4 pixel-identity links with per-position limits, setting `reference_data`, x_att, y_att and slices in one `delay_callback`, then restoring zoom. Partner, interval (0.3-2 s, default 0.5 s) and limit mode sit in a panel shown only while active; stopping or closing restores reference data, slices, limits and visibility. Done when on 4000005156 scan 0 Mg II k index 93 against wing index j alternates exactly between `cube[:, :, 93]` and `cube[:, :, j]` with identical limits; Si IV 1403 index 286 against Mg II k 93 alternates reference data and slices, keeps the crosshair's (step, slit) and restores limits, with switch plus draw ≤ 0.25 s; scan slice and point survive 20 flips; stopping restores the originals; closing stops the timer; inactive viewers get no extra widget. Depends: wp4-m1-multi-window, wp4-quicklook-preset.
- [ ] **M1** `wp5-m1-doppler-image`: A D4 'Doppler image…' action for a raster window or stack with rest λ0 (else refused). It adds one Data with planes D(λ) = I(λ) − I(2λ0 − λ) for λ ≥ λ0 whose mirror is in the window (CRISPEX lp_dop), I(2λ0 − λ) linearly interpolated and NaN if either neighbour is; coords `_GlueWCS(SlicedLowLevelWCS(raw_wcs, (..., slice(k0, k1))))` keep the axis in Å; sign D16. It owns the derived-product helper that WP2 and WP6 reuse: add the Data, copy `rest_wavelength`, `rest_wavelength_source` and window meta, add a broadcast `Time`, write `meta['velocity_caveat']`, add WP4 pixel-identity links on the spatial axes, open no viewer. Done when a synthetic line shifted +10 km/s gives D > 0 near +10 km/s and an unshifted symmetric line gives D = 0 within 1e-6; on 3610108077 Mg II k with rest 2796.352 every plane equals an `np.interp` reference to float32 precision with fill NaN, and the WP11 readout on the plane nearest +50 km/s shows 50 km/s within half a pixel; a Pixel click on the map shows the source spectrum at the same (step, slit); the product survives a WP3 round trip. Depends: wp5-m1-rest-wavelength-policy, wp4-m1-multi-window, wp11-cursor-readout, wp3-wcs-saver.

**M3**

- [ ] **M3** `wp5-m3-rest-from-measurement`: 'Use displayed wavelength' in the rest dialog stores the active slice wavelength as 'override' (the guide says it is not a laboratory rest). Document the ITN 26 §5.1 / ITN 38 §4.2 check: fit O I 1355.598 or S I 1401.515 with the stock Profile Fit tool and enter rest + (λ_fit − λ_lab); the Ni I 2799.474 recipe uses WP6's baseline model. Per-exposure orbital drift is measured by irispy #198 (`calculate_wavelength_drift`); once released, the recipe points to it. Done when on 4000005156 scan 0 a test fits O I 1355.598 in the O I 1356 window with the stock Gaussian fitter and entering the corrected rest moves the top axis's zero by c·Δλ/λ; 'Use displayed wavelength' stores the slice wavelength as 'override'; the recipe page builds with Sphinx -W. Depends: wp5-m1-rest-wavelength-policy, wp5-m1-velocity-axis.
- [ ] **M3** `wp5-m3-reference-blink`: Extend blink to SJI against SJI or an aligned AIA cutout, taking the partner frame from `wp4-time-sync` each flip so it runs during playback. A 2-D `link_hpc` reference blinks by layer visibility; a 3-D partner uses the reference-data switch with zoom mapped through both WCS (prototype first). Optional normalisation gives each stream its own limits. Done when on the irispy 20210905 fixture (SJI 1400 against SJI 2796) the streams alternate at the set interval during playback, show the same region within 1 SJI pixel with `solar:frame_time` naming the visible stream's time; with normalisation each stream's limits are its own 99.5 percentile; stopping restores visibility and limits; the same runs on a 3640107442 SJI against its AIA 1600 cutout once that SJI is local. Depends: wp5-m1-spectral-blink, wp4-time-sync, wp4-context-reference.
- [ ] **M3** `wp5-m3-mean-spectrum-compare`: 'Subtract mean spectrum' adds flux − mean[λ pixel] to a raster window or stack (1-D nanmean over space and scans, fill excluded), computed lazily by a `ComponentLink` subclass whose `__gluestate__`/`__setgluestate__` save the component references and the mean as a list. 'Scale to maximum of average' is documented as Profile Normalize. Done when on 4000005156 scan 0 Si IV 1403 the component's Pixel-subset Profile equals `cube[s, y, :] − nanmean(...)` within 1e-6 with no cube-sized array stored; it works in an image slice and on a 4-D stack and survives a WP3 round trip still derived. Depends: wp3-app-session-acceptance.

Notes:
- Mg II and C II velocities are optically thick proxies. km/s as a Profile x unit waits for glue-qt #70 (on 0.4.2 a non-native x unit makes Navigate and Collapse pick the wrong slice); until then km/s is on the top axis, in the WP11 readout and in product meta.
- The Doppler product keeps an Å axis, is float32 with at most half the source planes, and embeds its array in sessions.
- Upstream line layers (glue #2603 / Qt #73) could replace `LineListArtist`.

### WP6: Gaussian fit maps

Gaussian fit maps of IRIS raster windows (a D4 action: one linked map
dataset, no viewer) and Profile Fit tab fitters, in
`glue_solar/sources/fitting.py` (new, registered from `setup()`).

Port: the single-Gaussian path of `IRIS_PLAN_PROTOTYPES/wp6_fitting.py`
(`fit_gaussians_action`, `start_fit` with `_WORKERS` and the progress-dialog
reference) fixed as below; `wp6_test_fitting.py` → `glue_solar/tests/test_fitting.py`
(7 tests with `find_irispy_test_file`, a window of at least ±2 Å, plus the two
`worker.progress.isVisible()` asserts of `wp6_test_fitting_final.py`; the two
double-Gaussian tests wait for M3); only `test_wp3_roundtrips_wp6_fitted_map`
from `review_20260905/test_plan_integration.py` → `glue_solar/tests/test_sessions.py`.
`wp6_chk_real_fixed.{py,log}` (the only 4-D stack fit) and
`wp6_full_raster.{py,log}` (the `wp6-m2-worker` baseline) stay as evidence.

**M2**

- [ ] **M2** `wp6-m2-fit-maps`: D4 'IRIS: Gaussian fit maps…' fitting the shared Gaussian + constant model (`wp6-m2-profile-fitter`) with `LMLSQFitter` through astropy `parallel_fit_dask`. Flux defaults to '<flux> DN/s', else the first main component. Fit only inside a window from the reusable WP2 widget (`wp2-m2-line-definition`), default WP5 rest ± 0.5 Å; without a rest the user enters the window and velocities are off. Masking: `mask = ~isfinite(window)`, `window[mask] = 0`, pass `mask=` (no clip or `nan_to_num`); spectra with valid samples ≤ free parameters get NaN. Seed the centre at the maximum of the in-window NaN-ignoring mean spectrum, or an optional seed; never TWAVE. Outputs `background`, `amplitude`, `centroid`, `sigma` (Å, 1σ), plus `velocity` and `sigma_velocity` (km/s) with a WP5 rest; Mg II h/k and C II windows get the `line_regime` meta. Done when a noisy (peak SNR 50) zero-background synthetic cube with partly missing spectra gives amplitude and sigma within 5% and centroid within 0.005 Å; on 3610108077 Si IV 1403 no fully masked spectrum gets a finite fit (today 1687/1687 do); `velocity` equals the WP5 conversion of `centroid`; on that raster's Mg II k window the dialog pre-selects 2796.352 Å and the default-window fit gives |median centroid − 2796.352 Å| ≤ 0.01 Å; a local Si IV 1403 fit runs with and without the window and prints the median centroid shift. Depends: wp2-m2-line-definition, wp5-m1-rest-wavelength-policy, wp1-dn-per-s (soft).
- [ ] **M2** `wp6-m2-quality-filter`: Publish |sigma| where amplitude > 0; NaN fits with amplitude ≤ 0 or sigma = 0, a centroid outside the window, status ≤ 0 (`fit_info=('status',)`), or saturation by the `wp2-m2-input-quality` check, warning on NSATPIX/TSATPXn > 0. Done when on 3610108077 Si IV 1403 (today sigma < 0 in 6.0%, amplitude < 0 in 11.2%) the maps contain no amplitude ≤ 0, sigma ≤ 0 or out-of-window centroid; synthetic spectra with one +Inf sample or a peak above the DN limit are NaN in every map; the rejected fraction is in the map meta and the completion message. Depends: wp6-m2-fit-maps, wp2-m2-input-quality.
- [ ] **M2** `wp6-m2-products`: One new Data holds the maps of a 3D raster or 4D stack: coords `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`; one `LinkSame` pixel link per non-spectral axis; the source `Time`, window meta and rest keys via WP5's derived-product helper; no viewer. The residual is opt-in (float32, source shape, on the source). Done when a (13, 8, 109, 17) stack gives (13, 8, 109) maps with 3 links and a 3D raster 2 links; a default run adds no source component and an opted-in residual is float32; subsets propagate both ways; fit products add at most 2× the 2-D map bytes to a saved session without the residual. Depends: wp6-m2-fit-maps, wp3-session-budget, wp5-m1-doppler-image.
- [ ] **M2** `wp6-m2-rest-key`: The fit map carries the rest used for `velocity` as `meta['rest_wavelength']` (float, Å), and none when none was used, plus `rest_wavelength_source` and `velocity_caveat`; a seed centre goes under `fit_seed_center`, never as a rest. Done when the WP5 helper returns the used rest and the Image viewer offers km/s for `centroid`; a seed-only fit offers no km/s; `rest_wavelength` and `fit_seed_center` survive a WP3 round trip. Depends: wp5-m1-rest-wavelength-policy.
- [ ] **M2** `wp6-m2-worker`: The main thread computes wavelengths, window indices and mask; a glue-qt `Worker` runs only `parallel_fit_dask` (`'processes'`; tests `'single-threaded'`), and the result slot builds maps and links on the main thread. While holding the WP10 lock it deep-copies `coords._wcs` and builds the `SlicedLowLevelWCS` on that copy. Keep references to Workers and the parentless progress dialog, show progress for the Worker's lifetime, offer no cancel, and on error show the traceback and publish nothing. Done when an action test adds the maps with the progress dialog visible during the fit and hidden after; a spy on the source `_GlueWCS` records no Worker-thread call; a subprocess test building maps while a second thread loops on `pixel_to_world_values` exits 0 in 20 of 20 runs; a full 3610108077 window fit (320×548 spectra) takes ≤ 60 s with GUI timer gaps ≤ 0.2 s and process-tree peak ≤ 12 GB (baseline 25.3 s). Depends: wp6-m2-fit-maps.
- [ ] **M2** `wp6-m2-profile-fitter`: Shared unbounded named-parameter `custom_model`s (`background, amplitude, mean, stddev` and the two-Gaussian version), not `Const1D + Gaussian1D`. In `setup()`, register 'Gaussian + constant' and 'Two Gaussians + constant' through glue's `fit_plugin` registry as `AstropyFitter1D` subclasses (`LevMarLSQFitter`; guesses from finite samples), so the stock Fit tab fits Pixel-point or ROI-mean spectra; the fit is unweighted (the Fit tab passes no dy) and drops non-finite samples. Done when both fitters appear and fit with no warning under `filterwarnings = error`; 'Gaussian + constant' Fit-tab fits of a Pixel-point and an ROI-mean spectrum (Profile function Mean) on the irispy 20210905 fixture and the 3610108077 Si IV 1403 core, in Å and m display, match a direct Å fit to 1e-6 relative; 'Two Gaussians + constant' recovers both components of a synthetic two-line spectrum; the guide has the recipe and calls two-Gaussian Mg II or C II fits proxies.
- [ ] **M2** `wp6-m2-tests`: Port the suite: the synthetic, 4D, subset, residual and Worker/WCS-lock checks above, plus noiseless recovery (amplitude and sigma rtol 1e-4, centroid rtol 1e-6), NaN for valid samples ≤ free parameters, irispy raster shapes and units (±2 Å) and SJI rejection. Physical checks use synthetic cubes and irispy-data cutouts as remote-data tests (the fixtures are 10×-decimated). Reference fits use the same unbounded model. Done when the suite passes in `iris-plan` under `filterwarnings = error` and the WP3 round trip restores values, links and `rest_wavelength`. Depends: wp6-m2-fit-maps, wp6-m2-products, wp3-wcs-saver (session test).
- [ ] **M2** `wp6-m2-docs`: A user-guide page, an API entry and a changelog fragment covering the fit window, masking and the valid-sample minimum, 1σ sigma (FWHM = 2.355σ), the rejected fraction, the unweighted fit and its unit, thick versus thin lines, `LEVEL2_CAVEAT`, and that the maps are not calibrated; claim session support only after `wp6-m2-tests` passes. Done when Sphinx builds with `-W`, the API page lists `glue_solar.sources.fitting`, and the page walks one Si IV fit from the action to a km/s centroid map. Depends: wp6-m2-fit-maps.

**M3**

- [ ] **M3** `wp6-m3-rba-double-gaussian`: Both parts run in the Worker on main-thread data from WP2's rewrap helper. A D4 'Red-blue asymmetry…' action wraps `irispy.utils.red_blue.calculate_red_blue_asymmetry`, always passing the WP5 rest and `return_profiles=False`, with `continuum_windows` and an 'IDL iris_xfiles' preset (5-100 km/s steps, 30-50 km/s summed) beside irispy's default; the RB map and its quality flags form one linked dataset. The fit action gains the two-Gaussian model ('Mg II k2v/k2r proxy'), seeded from rest ± 0.15 Å or the two highest interior maxima of the mean spectrum, used only where |RB| exceeds a threshold (default 0.1); uint8 `rb_mask` records the choice. Done when on 3610108077 Mg II k the RB map equals a direct irispy call with the same parameters; a window without a rest adds nothing and says why; the IDL preset changes only the velocity grid; `rb_mask` is 2 exactly where |RB| exceeds the threshold, 1 where not and 0 where RB is not finite; the double-Gaussian tests pass; an error publishes nothing. Depends: wp6-m2-fit-maps, wp6-m2-worker, wp5-m1-rest-wavelength-policy, wp2-m2-moment-maps.
- [ ] **M3** `wp6-m3-template-fits`: N-component Gaussian + constant templates seeded from the in-window WP5 line list (Si IV 1403: O IV 1399.77/1401.16, Si IV 1402.77). With uncertainties loaded (`wp2-m3-window-data`), weight by 1/σ and publish 1σ errors (`amplitude_error`, `centroid_error`, `sigma_error`, `velocity_error`) from `fit_info=('status', 'param_cov')`. Done when a synthetic 3-line window recovers each component; with uncertainties the maps equal a direct `parallel_fit_dask(weights=1/σ)` call to rtol 1e-6 and the error maps equal its √diag(param_cov); on the real Si IV 1403 window high-SNR O IV and Si IV centroids fall within ±0.1 Å of the list. Depends: wp6-m2-fit-maps, wp5-m1-line-list, wp2-m3-window-data.

Notes:
- `parallel_fit_dask` swallows per-pixel warnings; astropy 8.0.1 deprecates `LMLSQFitter` on bounded models, hence the unbounded model; create one fitter per call (reuse after `fit_info=` raises `KeyError: '__deepcopy__'`).
- Level-2 saturation is the kept int16 top code (about 16182 DN), hence the DN-limit check.

### WP7: GOES and SDO context

On request, GOES XRS and SDO/AIA context for a loaded observation with glue's
own viewers, `link_hpc` and `Time` links, in `glue_solar/sources/context.py`
(new), `glue_solar/glue_patches.py` and `glue_solar/tests/test_context.py`.
Each PR carries its guide section: when a fetch beats local LMSAL `aia_l2`
cutouts, the first-exposure FOV limit, and that GOES 8-15 curves are
unscaled while SWPC/HEK classes use the old scale (X1.0 ≈ 1.4e-4 W/m² on the
curve).

Port: all of `IRIS_PLAN_PROTOTYPES/wp7chk/context_chk.py` and its ten mocked
tests (not `conftest.py`), with expected footprints from an astropy WCS built
from the header, never `to_maps(0)` or pinned numbers; the GOES success-path
recipe (viewer, log axis, time link) of
`archive/probes-2026-09/wp7_timelink.py`/`wp7_goes.py`, not its `EPOCH=1`
path; `wp0_bug_epoch_viewer.py` as the 1.27.0 assertion of
`wp7-goes-date-labels`.

**M2**

- [ ] **M2** `wp7-context-port`: Menubar actions 'IRIS: GOES context…' and 'IRIS: SDO context…'; `pyproject.toml` moves to `sunpy[map,net,timeseries]`. Each opens one confirm dialog listing IRIS datasets only; OK is consent to go online. Footprints are computed on the GUI thread; search, download, file reads and AIA processing run in glue-qt's `Worker` with the `wp10-nonblocking-load` lifecycle (stale results discarded by id); Data, links, subsets and viewers are made in the result slot; errors become message boxes. Done when Cancel makes no network call (Fido, HEK or HCR); a mocked network error shows a message and changes nothing; a 50 ms QTimer sees no gap above 0.2 s during a mocked 2 s download, and closing the app then adds and raises nothing; imports raise no warnings; the ported tests pass, including SJI, raster and stack footprints against the header-WCS oracle. Depends: wp1-m0-link-hpc, wp10-nonblocking-load.
- [ ] **M2** `wp7-goes-context`: `goes_xrs` fetches 1-minute XRS for STARTOBS–ENDOBS from one satellite: auto (the lowest-numbered covering the whole interval, else the longest coverage, named in the message) or one chosen in the dialog. Non-zero `xrsa_quality`/`xrsb_quality` samples become NaN; data are truncated to the interval in W/m², with a datetime64 `time`, in a Scatter viewer with `y_log=True`. GOES `time` gets `LinkSame` to the `Time` of every loaded dataset of the observation, never a pixel ID or SJI 'Time (Utc)'. Done when mocked `Fido` with satellites [15, 13] both covering fetches 13 and NaNs the flagged sample, and a chosen 15 fetches 15, with W/m² units and times inside the interval; with none covering, the longest is fetched and named; a GOES time-range subset selects the matching SJI frames and raster steps; `wp1-m0-link-graph-regression` passes with GOES linked; a manual fetch for 20140329 3860258481 shows the X1.0 flare in xrsb near 17:48 UTC at about 1.4e-4 W/m². Depends: wp7-context-port, wp1-m0-link-graph-regression.
- [ ] **M2** `wp7-goes-marker`: A `solar:time_marker` tool on `ScatterViewer.tools` draws, for a datetime `x_att`, an `axvspan` over the WP4 master exposure (start to start + `Exposure time`), redrawn on master changes, converting with `glue.utils.matplotlib.datetime64_to_mpl` looked up at call time. Done when, with raster and SJI masters, moving the master moves the span; with the #2599 port on 1.27.0 it lies inside the axes limits over the GOES samples at the master time; on a datetime Scatter without GOES data (WP12 light curves) it still follows the master; a session with GOES reopens with `y_log` True and the span redrawn. Depends: wp7-goes-context, wp7-goes-date-labels, wp4-time-sync, wp3-app-session-acceptance.
- [ ] **M2** `wp7-goes-date-labels`: Until a core release has #2599, `glue_patches.py` installs a port of its `datetime64_to_mpl`/`mpl_to_datetime64` (epoch from `matplotlib.dates.get_epoch()`), rebound in `glue.utils.matplotlib`, `glue.utils` and the by-name importers (scatter, matplotlib viewer, histogram modules), only when a probe finds `datetime64_to_mpl(t) != date2num(t)`; never set `rcParams['date.epoch']`. Done when on 1.27.0 mocked 2021-09-05 GOES ticks show 2021 (3990 without the port) and `state.x_min`/`x_max` are 2021 values; an xrange ROI over 00:20-00:30 gives subset bounds in that range; with #2599 in core the probe is False. Depends: wp1-m0-inverse-workaround.
- [ ] **M2** `wp7-aia-context`: One download of the AIA 171 image nearest STARTOBS gives a full-disk locator resampled to about 1024 px and an FOV crop (the first-exposure footprint plus a dialog margin, default 100 arcsec). The crop is offered only when no same-observation `aia_l2` cutout is loaded (the action does not scan disk); the dialog then points to the browser's AIA rows. Corners are transformed inside `propagate_with_solar_surface(), SphericalScreen(iris_observer, only_off_disk=True)` with the IRIS observer at Earth at STARTOBS. Views go through `_parse_sunpy_map` (D3), link with `link_hpc`, and carry a pixel `PolygonalROI` FOV subset. Done when (mocked) an off-limb FOV (corners near Tx 1000″) against an AIA frame with an SDO observer 5 s later crops without NaN or error; the locator is uncropped at about 1024 px and its FOV subset covers the footprint; with a same-observation cutout loaded only the locator is made; a session with locator, crop, links and subset reopens intact; a manual fetch for 4000255147 is recorded. Depends: wp7-context-port, wp1-m0-link-hpc, wp1-m1-sunpy-maps, wp3-app-session-acceptance.

**M3**

- [ ] **M3** `wp7-flare-list`: 'IRIS: SWPC flares…' (same confirm dialog) queries `HEKClient` for SWPC flares in the interval into a Data (start, peak, end, class, location) in a Table viewer, plus one time-range subset per flare on a loaded GOES `time`; no events adds nothing and says so. Done when a mocked HEK response gives rows and subsets, a network error adds nothing, and a manual check for 20140329 3860258481 lists the X1.0 flare near 17:48 UTC. Depends: wp7-context-port, wp7-goes-context.
- [ ] **M3** `wp7-hcr-metadata`: 'IRIS: HCR metadata…' (same confirm dialog) queries `https://www.lmsal.com/hek/hcr?cmd=search-events3&outputformat=json&instrument=IRIS&startTime=…&stopTime=…` with STARTOBS/ENDOBS, takes the event whose obsId equals OBSID (nearest start if several), and stores obsTitle, goal, target, noaaNum and planners as `HCR_*` meta on every dataset of the observation. Browser scans never query HCR. Done when a mocked response gives, for obsId 3860258481, 'IHOP251 with Sac Peak at AR12017', target 'AR', NOAA '12017'; the nearest-start rule holds; no match or a network error changes no meta; a browser scan makes no HCR request. Depends: wp7-context-port.
- [ ] **M3** `wp7-aia-channels`: The `wp7-aia-context` dialog can add AIA 94-1700 Å channels and HMI (continuum, magnetogram) to the same fetch; each gives an FOV crop (or nothing beyond the locator when a same-observation cutout is loaded), built like AIA 171; if one fails nothing is added. Done when a mocked 1600/304/HMI-continuum request gives three linked crops and a mocked failure leaves the collection unchanged. Depends: wp7-aia-context.

Notes:
- First exposure only: pointing drift (42.2 arcsec over 4.8 h on the 20210905 fixture) is not followed. AIA is one image per channel; no time series, co-registration, JSOC login or aiapy.
- sunpy 8.0.0 does not mask XRS quality flags; GOES-19 needs sunpy ≥ 8.1.
- The marker appears in 'Save plot' but not the Python-script export. The `PolygonalROI` subset stays until a release has #2604.

### WP8: Browser, discovery and inputs

The observation browser (`QtIRISImporter`, `iris_loader.ui`), the header
scanner (`glue_solar/sources/loaders/scan.py`) and the IRIS readers
(`glue_solar/sources/loaders/iris.py`, `glue_solar/sources/iris.py`).

Port: `wp8_scan.py` (only the `stop` keyword and poll) and `wp8_proto.py` +
`wp8_loader.ui` (scan and filter methods and .ui hunks, on the
`wp10-nonblocking-load` lifecycle; not `populate_threads` or
`_stop_scan`'s `worker.wait()`) for `wp8-filter-stop` and `wp8-text-filter`;
`wp8_test_proto.py`, `wp8_test_shipped.py` and `wp8_chk_test_text.py` into
`test_scan.py`/`test_importer.py`, gated on a `threading.Event` (rewrite
`test_scan_directory_stop_kwarg`; add `qtbot.waitUntil(lambda: not dlg.scanning)`
at the 10 construction, toggle and finalize sites; invert
`review_20260927/probes/wp8/test_v_wp8.py` f2/f3/f4/f11 into regressions).
Fix first: loading during a rescan, stopping inside the directory walk, the
'Scan stopped' wording.

**M1**

- [ ] **M1** `wp8-derived-files`: `_is_supported_file` accepts an IRIS `SPEC` file only if its primary header has `DATA_LEV == 2`, which the derived `iris_l2_20140910_fexxi_rb_steps` lacks. Skipped files are not listed and the progress text counts them; a load failure names the file. Fixtures: `_header` gains DATA_LEV=2; a new derived fixture copies rb_steps' name and layout with OBS_A's OBSID and STARTOBS. Done when on `iris_tree` the derived fixture is never a window, OBS_A keeps its 2 rasters, OBS_S and the irispy fixtures are listed, and the progress reports 1 skipped file; `test_reader_failure_stays_in_dialog` asserts the file name; locally the scan finds 13 observations (14 today) and skips 1 of 130 files.

**M2**

- [ ] **M2** `wp8-filter-stop`: Run `scan_directory` in glue-qt's `Worker` with a cooperative `stop` predicate polled during the walk and once per file; populate on the GUI thread; reuse the `wp10-nonblocking-load` lifecycle (stop and drop results by scan id on rescan, directory change, accept, reject and close; no GUI-thread `wait()`). Load is disabled during a scan; after a Stop, truncated observations show '(partial scan)' with Stack disabled; `_scan_over` fixes the progress value after `setRange(0, 100)`. Done when event-gated pytest-qt tests show Stop or reject during a slowed walk returns after at most one further `is_file` call and within 0.5 s; Load during a gated rescan cannot load from the replaced list; after an early Stop a 2-raster observation shows 1 file and the partial marker; Stop after completion never shows 'Scan stopped'; stale scan ids are ignored; the suite passes 20 consecutive runs; locally GUI timer gaps stay ≤ 0.2 s and the median header read ≤ 5 ms/file. Depends: wp8-derived-files, wp10-nonblocking-load.
- [ ] **M2** `wp8-text-filter`: A case-insensitive `filter` QLineEdit in `iris_loader.ui` matching STARTOBS, OBSID, description and the child rows' window, SJI and AIA names (keep the object names `filter`, `stop_scan` and `progress`). Done when on `iris_tree` 'mg ii' keeps only OBS_A with its Mg II row, '2023-02' keeps only OBS_B, a hidden ticked observation makes Load read 'Load selected (1 hidden)' and still loads, and the filter survives a rescan. Depends: wp8-filter-stop.

**M3**

- [ ] **M3** `wp8-prescan-search`: Keyword-only `start`, `stop`, `glob`, `date_tree`, `max_duration` (default 1 day) and `first_raster_header_only=False` for `scan_directory`, pruning before any header read (filename stamps outside [start − max_duration, stop] skipped; `glob` via `fnmatch` on `strip_pooch(name)`; date-tree mode enters only YYYY/MM/DD inside the interval; observations kept if STARTOBS ≤ stop and ENDOBS ≥ start; `QtIRISImporter` passes `first_raster_header_only=True`). Add `find_observation_files(time, root, sji=False, nearest=False)` (iris_find_file parity). Done when header-read-counting tests on a YYYY/MM/DD symlink tree of local files (CI variant on `iris_tree`) show a 2013-09-02 window reads only headers stamped 2013-09-01/02 and lists only 4000255147 and 4000005156; `glob='iris_l2_2025*'` lists only 3400109360 and 3893010094; `find_observation_files('2013-09-02T17:00', root)` returns the 4000255147 raster (with `sji=True` its SJI 1400) and `nearest=True` returns the closest for an uncovered time; `first_raster_header_only=True` reads 1 SPEC header for 3602506433 and OBS_A and lists the same rasters and windows; with no new arguments results equal today's. Depends: wp8-filter-stop.
- [ ] **M3** `wp8-search-ui`: Start/Stop UTC fields with 'Last 5 days', 'Up until now' and 'Ignore times'; named search locations (root, date tree, subfolders, glob) with one 'local' default; 'Recent searches'. Stored beside `iris/last_dir` in `QSettings('glue-solar', 'glue-solar')` and passed to `wp8-prescan-search`. Done when isolated-QSettings tests show 'Last 5 days' sets now − 5 d to now; 'Ignore times' equals an unwindowed scan; a location can be added, edited, removed and restored; the recent list stops at 10 and restores Start/Stop. Depends: wp8-prescan-search.
- [ ] **M3** `wp8-browser-conveniences`: Persist 'Search subfolders', 'Stack' and the filter text; make the Folder field editable (rescan on `editingFinished`); double-clicking a row loads only its payload; record source paths in `data.meta['SOURCE_FILES']` (display only). Done when isolated-QSettings tests show values restored on reopen; a typed path rescans and an invalid one shows a message and keeps the list; double-clicking a leaf loads only it and a parent only expands; a loaded SJI stores its path and OBS_A's two-raster stack both paths, shown by `MetadataDialog` and kept through a session. Depends: wp8-text-filter, wp3-file-references.
- [ ] **M3** `wp8-browser-metadata`: Tooltips on observation rows and window/SJI items from the primary headers `scan.py` already reads: TWMINn/TWMAXn/TDETn, window size from TSCn/TECn/TSRn/TERn, NRASTERP, FOVX/FOVY, STEPT_AV, binning (SUMSPTRF/SUMSPTRN/SUMSPAT), OBSLABEL/OBSTITLE and the `irispy.obsid.ObsID` decoding. Done when the irispy 20140329 fixture's C II tooltip starts 'C II 1336: 1332.73–1337.22 Å, FUV1'; every tooltip number on the local 2013, 2014 and 2018 observations equals its header value; counted header reads are unchanged.
- [ ] **M3** `wp8-remote-search`: 'IRIS: search online…': `sunpy.net.Fido` search on `a.Time` and `a.Instrument('IRIS')`, an OBSID filter, `Fido.fetch` of ticked rows in the `Worker` into a chosen folder, then `QtIRISImporter` on it, with a link to the LMSAL search page. Done when mocked tests show results grouped by observation, a working OBSID filter, no network work on Cancel and nothing changed after a fetch error; the LMSAL link is checked by hand; an opt-in network test downloads the ~39 MB SJI 1400 record of 3660259102 and the browser lists it. Depends: wp8-filter-stop.
- [ ] **M3** `wp8-m3-level3-input`: A `data_factory` 'IRIS Level 3 FITS' claiming `*_im.fits` names with the three Level-3 extensions at priority 210, reading the (x, y, wave, time) cube with `astropy.io.fits`: wavelengths from extension 1, extension-2 times (seconds since DATE_OBS, (nx, ntime)) as a datetime64 `Time`, extension-3 slit positions as components, and the spatial WCS from the header, with VER_RF3 (the iris_xfiles r1.41 cutoff) selecting which exposure CRVALn refers to; transposed sp files are not claimed. Read `iris_xfiles`/`iris_make_fits_level3` first for the header keyword and VER_RF3 mapping (no real Level-3 file is local); add a header-keyword test once a real file confirms one. Done when synthetic ITN 26-layout im files with VER_RF3 on each side of the cutoff load as one Data with matching wavelengths, `Time` = DATE_OBS + extension 2 and the right spatial WCS, and the factory claims neither Level-2 fixtures nor irispy files.

Notes:
- `finalize`, `iris_loader.ui` and `test_importer.py` are also edited by WP3, WP4, WP10 and WP1; land WP8 M2 after them. Each PR documents its behaviour in the loading guide.
- Deconvolved SJIs are recognised by filename only.

### WP9: Documentation and tutorials

Keep the `docs/` guides accurate for what ships and maintain an IRIS-9-style
CRISPEX tutorial whose steps are the acceptance script. Recipe checks live in
`glue_solar/tests/test_documented_workflows.py`. Each feature PR documents its
own capability; WP9 owns cross-cutting guides, corrections, the tutorial and
acceptance, and no doc claims planned features ship. Every docs item also
needs a passing `wp9-m0-docs-build`. M0 event finding starts on the raster
map: stock SJI Pixel subsets give no raster spectrum on released core.

**M0**

- [ ] **M0** `wp9-m0-user-guide-corrections`: Correct the user guides, adding only missing text. In `loading-iris-level-2-raster-and-sji-data.rst`: aligned `aia_l2_*.fits` cutouts need no `_SDO` directory; SJIs and cutouts carry a per-frame datetime64 `Time` shown by the Frame time tool; stacks are floating memmaps; -200/-199 fill becomes NaN (AIA cutouts -200 only), +Inf saturation is kept, the mask is 0/1 uint8, and negative-step rasters keep irispy's default orientation with `revert_v34=True` as the documented alternative; quote labels as displayed, in Glue order; fix the manual-link paragraph and state its directional limit; replace the restore-only warning with "Saving a session that contains IRIS data can fail before any file is written." In `loading-aia-and-hmi.rst`: the same note for sunpy Maps; alt text "AMI" → "AIA". Profile guide: float/NaN; collapse versus a one-pixel subset with Mean versus the unreleased Slice profile; Maximum is the default function and Mean gives CRISPEX's average spectrum. Done when `git grep` over `docs/` finds no "AMI", "folder is present" or "cannot currently be restored", and both guides carry the session warning.
- [ ] **M0** `wp9-m0-viewer-tools-docs`: In the IRIS guides, document glue-qt 0.4.2 tools by action text and tooltip, shortcuts as Ctrl+… "(Cmd on macOS)": "Pixel" (`image:point_selection`) versus "Cursor readout"; "Frame time"; Ctrl+I "View metadata/header"; the "Contrast/Bias" drag; gamma < 1 as Custom limits + sqrt until `wp11-gamma-stretch`; windows (minimise, Ctrl+N, Gather Windows Ctrl+G, Tab/Backspace only in Image, Scatter and Histogram viewers). Done when a glue-qt 0.4.2 test asserts Tab and Backspace cover ImageViewer, ScatterViewer and HistogramViewer but not TableViewer or ProfileViewer, quoted tooltips and shortcut texts match the sources, and no added text says "the crosshair icon" without the tool name.
- [ ] **M0** `wp9-m0-browsing-recipes`: In the loading guide, document no-code browsing: list columns and grouping, "Load selected"; large or multi-scan observations need the browser (File → Open and `glue --startup` load every window and cannot stack); several SJI/AIA channels and "Stack sequential raster scans"; playback (extra Forward presses: round(500/n) ms; wraps) and arrow keys on a focused slider; SJI log stretch, Arithmetic scaling, Home/Pan/Zoom, the Save menu (PNG/JPEG/PDF/PS/EPS/SVG), layer colour, alpha and linewidth, Preferences colours and font size. Done when a glue-qt 0.4.2 test asserts the round(500/|n|) interval and wrap, that the stack option yields 4D Data with a per-pixel `Time`, and that a saved `.eps` starts with `%!PS-Adobe` and has a `%%BoundingBox` line.
- [ ] **M0** `wp9-m0-mask-overlays`: In the loading guide, document overlays from the 0/1 uint8 `<label> mask`: "Create faceted subsets" first; a Histogram x-range subset works, but its "Add large data set?" modal defaults to Cancel above 2e7 elements (4000255147 SJI 1400: 6.47e7); "Import subset mask(s)" takes same-shape signed-integer FITS HDUs (BITPIX 16/32/64, no unsigned BZERO). Done when a fixture test shows the faceted-subset count equals `mask.sum()`, as does a recorded manual check on the real 4000255147 SJI 1400 and raster.
- [ ] **M0** `wp9-m0-workflow-recipes`: Extend the profile guide with released-Glue recipes, naming axes by role: four panels by hand (raster as spectrogram and map, SJI, Profile, Pixel, Gather Windows; Profiles above 1e8 elements ask "Add large data set?"); axis choices for spectrogram, raster map and time–wavelength (the sit-and-stare exposure axis reads "Helioprojective Longitude" but is acquisition order); the step slider as iris_xraster's spectroheliogram; Pixel follows on drag, holds on release and replaces the active subset, intersections work only within one dataset (on a linked dataset the AND gives an all-NaN profile) and hide the crosshair; Profile Navigate moves the Image slice only while its line moves, and on glue-qt 0.4.2 Navigate and Collapse pick the wrong slice under a non-native display unit; Slice Extraction (P) needs 3D data and makes no Data object; Collapse "Maximum"; light curves; `Time` as readouts. Done when the text states that P works on 3D data only and a test runs one check per recipe on the irispy fixtures on released core, driving Pixel with the ported `mouse()`/`select_point()` helpers (in `glue_solar/tests/helpers.py`, shared with `wp4-tests`), with the Pixel & band check asserting the same-dataset band spectrum and the missing crosshair.
- [ ] **M0** `wp9-m0-scripting-recipe`: A recipe for the Terminal button, `raster_data`/`image_data`, `data.coords.pixel_to_world_values` and `data['Time']`. Done when a doctest or offscreen check on the irispy 20210905 fixture shows `pixel_to_world_values` at a Pixel point equals the status-bar readout and the raster's Profile Mean equals `np.nanmean` over the non-spectral axes.
- [ ] **M0** `wp9-m0-iris9-tutorial`: Add `docs/user_guide/iris9-crispex-tutorial.rst` (linked from the index): every IRIS-9 §3.3 CRISPEX task with local stand-in data, Glue steps where supported and "not yet supported in Glue" otherwise. §3.3.1 (OBSID 3840007146; stand-in 3824262996, Si IV 1403, Mg II k): gamma < 1, ~2 frames/s core blink, a feature's solar (x, y). §3.3.2 (stand-ins 3602506433, and 4000005156 for raster + SJI): run and find the end time; Doppler range; mouse lock with T-slice; raster positions on the SJI. Event finding: play, pause on a brightening, select on the raster map (sit-and-stare: slit–time panel), zoom, read spectrum and matched times. Done when every task appears with its stand-in, the M0 steps are those `wp9-m0-iris9-acceptance` runs, and no rst text names a WP or milestone. Depends: wp4-quicklook-preset, wp4-m0-point-fixed-index, wp4-time-sync, wp4-sji-panels.
- [ ] **M0** `wp9-m0-iris9-acceptance`: `glue_solar/tests/test_iris9_acceptance.py`, a pytest-qt remote-data run of the M0 tutorial steps through the quicklook on released core, on irispy-data files for 4000005156 two-scan stack + deconvolved SJI 2796 and 4000255147 + SJI 1400 (irispy-data lacks 4000005156 scan 1 and the deconvolved SJI 2796, and its 4000255147 raster cutout is 439 MB, so smaller cutouts go into irispy-data first, on the user's direction): switch the master to the SJI and play; stop at the frame with the highest 99.9th percentile in the raster footprint (sit-and-stare: slit column ±1 px); click the brightest in-region position via the WCS and zoom (4000005156 raster map: step from the WCS, scan argmin|dt|, shown offset = Time[scan, step] − SJI time; 4000255147 slit–time panel at the matched exposure and WCS slit row); the spectrum panel equals the raster spectrum there and zooming keeps the selection; on 4000005156 in a fresh preset, closing the SJI viewer and opening a new raster Image viewer joins it to coordination, and a spectrum with raw -200/-199 shows NaN gaps. Done when the script passes on both observations. Depends: wp9-m0-iris9-tutorial.
- [ ] **M0** `wp9-m0-docs-build`: Build with `sphinx-build -W --keep-going -b html docs <out>` in a new micromamba env `iris-plan-docs` (the `iris-plan` packages plus the `docs` extra), not `tox -e build_docs`, with QSettings isolation. Done when the env recipe is in Validation and main plus the M0 edits build with no warnings.
- [ ] **M0** `wp9-m0-wiki-digest`: Only on request, fetch and refresh the public wiki; fix `Home.md:4` and `Short-Term-Roadmap.md:1`; replace "In preferred order" with M0-M3; no local paths or prototype links. Done when the wiki shows the milestone digest with no dangling section references.

**M1**

- [ ] **M1** `wp9-m1-iris9-tutorial`: As each dependency lands, add its tutorial steps and acceptance run. Done when every tutorial task has a Glue step list and a passing acceptance run. Depends: wp1-m1-sji-to-raster, wp4-m1-hover-lock-tool, wp5-m1-spectral-blink, wp5-m1-doppler-image, wp4-raster-overlays, wp11-gamma-stretch.
- [ ] **M1** `wp9-m1-screenshots`: Re-add `docs/make_screenshots.py` from 93d05f05 (local branch `backup/iris-observation-browser-pre-rebase`, never pushed) or drop it. Done when the helper is on main and regenerates `docs/user_guide/images/` from a named local observation with HOME isolated, or the drop is recorded.

**M3**

- [ ] **M3** `wp9-m3-saturation-recipe`: "Was it saturated?": check NSATPIX/TSATPXn, then subset on an Arithmetic `np.isinf(<data component>)` (ITN 26 §6.4). Done when on a synthetic cube with one Inf sample the subset holds exactly that sample and shows in a linked Image viewer, and the dialog reports NSATPIX 0 for 4000005156 Si IV.
- [ ] **M3** `wp9-m3-spectral-recipes`: Profile-guide recipes: (1) average spectrum over a scan/exposure range on the 3602506433 stack; (2) photospheric context from 3660259102's 2832/2826/2814 windows and 3640107442's AIA 1600/1700 cutouts; (3) row/column cuts with the Slice profile once released, subset + Mean until then; (4) y-limits, line width, axis-label edits, and Normalize or per-window Profiles in place of CRISPEX's per-window multiplier. Done when each recipe reproduces on the named data (recipe 3's Slice step once released). Depends: wp9-m0-workflow-recipes.
- [ ] **M3** `wp9-m3-shortcuts-help`: A keyboard/mouse table (Pixel, Navigate, P, Ctrl+I, Ctrl+G, Tab/Backspace; `w` for pixel/world in WCSAxes' readout; the `wp11-keyboard-shortcuts` keys D/F, A/S, Space; L for 'Solar path (3D/4D)') and a menubar action "IRIS: user guide and issues" (`webbrowser.open`). Done when tests show every glue-solar keyboard and tool shortcut is in the table, the Plugins menu shows the entry, and (mocked) both URLs open. Depends: wp11-keyboard-shortcuts, wp12-path-slicer.

**M4**

- [ ] **M4** `wp9-m4-release-updates`: On core #2596/#2601 + Qt #70, drop "unreleased" from the Slice-profile text and the Navigate/Collapse display-unit caveat; on Qt #74, rewrite "Cursor readout"; on the Tab/Backspace fix, update the window text. Done when `git grep` over `docs/` finds no stale label or "unreleased" text. Depends: the core #2596/#2601 + Qt #70 release, the Qt #74 release.

### WP10: Loader robustness and performance

Correct and fast IRIS loaders for the M0 quicklook, then lazy loading. Code
in `glue_solar/sources/loaders/`, tests in `glue_solar/tests/`.

**M0**

- [ ] **M0** `wp10-m0-large-data-modal`: In `glue_solar/quicklook.py`, create the Profile viewer empty, set its instance `large_data_size = None`, then `add_data`, so the 1e8-point 'Add large data set?' modal cannot abort the preset; the status bar notes the size, or why `add_data` returned False; user settings and the class attribute are untouched. Done when, at real size and without patching `warn`, the preset opens with the Profile layer and `warn` is never called on the 4000255147 windows (1.7e8-3.7e8 elements), 3824262996 Mg II k (2.35e8) and the 99-scan 3602506433 stack (4.6e8). Depends: wp4-quicklook-preset.
- [ ] **M0** `wp10-m0-roi-guard`: An ImageViewer subclass in `glue_solar/quicklook.py` whose `tools` is glue-qt's `ImageViewer.tools` (read after `setup()`) minus the five `select:*` tools; the preset creates its raster viewers from it via `app.new_data_viewer`. Done when the preset's raster viewers expose no `select:*` tool, and an SJI frame step with the Pixel point active stays within the `wp10-m0-acceptance` SJI step budget on 4000005156 with the deconvolved SJI 2796 (32×771×1506). Depends: wp4-quicklook-preset, wp1-m0-link-hpc.
- [ ] **M0** `wp10-m0-acceptance`: CI tier on irispy fixtures: the thread test and uint8 mask assertions (on main since #59, #60). Data tier, a manual probe under `IRIS_PLAN_PROTOTYPES/` on the full files in `~/DATA/IRIS` (glue-solar tests never read local paths): 4000255147, 4000005156 (2 scans + deconvolved SJI 2796), 3824262996, 3400109360 (NaN positions, peak RSS) and 3602506433 (memory only). It logs sizes, per-window load time, latency, peak RSS and the per-frame cost of a stock raster pixel ROI with `link_hpc` on the 4000005156 and 4000255147 raster/SJI pairs (`browse_iris` installs `link_hpc` by default only after this is recorded). Budgets (fixed for the 24 GB reference machine, offscreen, warm cache; changed only by a recorded decision): image slice step ≤ 0.10 s at any exposure index; λ–t slit step ≤ 0.15 s; Pixel click to drawn spectrum ≤ 0.35 s; SJI frame step ≤ 0.15 s; one step across the synced image viewers ≤ 0.25 s at exposures 1, 800 and 1599 (WP4 sync ≤ 0.1 s of it); `quicklook()` ≤ 3 s with no modal; WP4's cached index state ≤ 1 MB; the #59 memory budgets (≤ 6 B/element kept and ≤ 10 peak on 4000005156 scan 0; the 99-scan 3602506433 stack below 12 GB); 0 crashes in 20 consecutive offscreen runs of `review_20260927/probes/wp10/test_race.py` and of the quicklook with 3 Pixel clicks on 3824262996 Mg II k and on 4000255147. Done when both tiers pass and the results, machine and load average are recorded. Depends: wp10-m0-large-data-modal, wp10-m0-roi-guard, wp4-quicklook-preset, wp4-m0-point-fixed-index, wp4-time-sync.

**M1**

- [ ] **M1** `wp10-nonblocking-load`: Run the reads in `QtIRISImporter.finalize` (`raster_data`/`image_data`, `extract_archive`) in glue-qt's `Worker` with the progress bar visible and OK disabled: build the Data in the worker without touching viewer-held WCS, extend `datasets` on the GUI thread, drop cancelled or superseded loads by load id, record results through the `wp4-launch-entry` per-window helper, never `wait()` on the GUI thread, and check for a stop between raster files. Messages stay visible after the worker ends. `wp8-filter-stop` reuses this lifecycle. Done when loading 3824262996 Mg II k or 4000255147 keeps GUI timer gaps ≤ 0.2 s; a stop in the middle of the 3602506433 stack takes effect within one file, adds nothing half-built and leaves earlier picks usable; the per-file assembly equals the one-call read on 4000005156; tests gate on counted reads, not sleeps, and the crash scenarios still give 0 crashes.
- [ ] **M1** `wp10-m1-roi-world-polygon`: Override `apply_roi` on the `wp10-m0-roi-guard` subclass: for IRIS raster data, map the ROI edges, sampled once per raster step, through `_GlueWCS.pixel_to_world_values` into a `PolygonalROI` `RoiSubsetState` on the lon/lat components; other data keep `roi_to_subset_state`; then restore the `select:*` tools. Done when on 4000005156 Si IV with the deconvolved SJI 2796 at frame 5 a raster rectangle selects the same 108,300 SJI pixels as the pixel-component subset (range tools likewise) in ≤ 0.5 s per full-resolution frame, and on sit-and-stare the result equals the pixel result; if `wp1-m0-link-hpc` check (4) finds the sit-and-stare stripe inherent, sit-and-stare maps keep no `select:*` tools. Depends: wp10-m0-roi-guard, wp1-m0-link-hpc.

**M2**

- [ ] **M2** `wp10-m2-lazy-loading`: Open raster and SJI files with irispy `memmap=True` (raw int16, no BSCALE/BZERO, no mask; fill reads -32768) and publish glue `DaskComponent`s computing `raw*BSCALE + BZERO`, the fill rule and the uint8 mask per requested slice; build the 4D stack from lazy scans; lazy opens use the `wp10-nonblocking-load` Worker; eager loading stays the default until the lazy path passes the same tests. Add `dask[array]` to `pyproject.toml` in the PR that first imports dask. Done when opening all windows of 3824262996 (3.17 GB float32) and 4000255147 (4.14 GB) lazily keeps peak RSS before any viewer opens below 10% of the eager peak (record both); sampled slices' values, NaN positions and masks equal the eager loader's, including on 3400109360; GUI gaps stay ≤ 0.2 s and the M0 budgets hold. Depends: wp10-m0-acceptance, wp10-nonblocking-load.

**M3**

- [ ] **M3** `wp10-m3-sit-stare-chunks`: Only if a recorded sit-and-stare run still exceeds 12 GB peak RSS or the M0 λ–t slit-step budget after lazy loading: a sit-and-stare exposure-range field in the browser that slices the lazy cube before conversion, keeping the chunk's `Time` and WCS. Done when on 4000255147 loading exposures 400-799 gives `Time` and world coordinates equal to the full load's there, peak RSS scales with the chunk, and navigation inside it is unchanged. Depends: wp10-m2-lazy-loading.

Notes:
- Stack storage stays a `np.result_type(scan 0, float32)` memmap with scan 0's spatial WCS (`wp1-stack-per-scan-wcs`).
- Raster world→pixel is slow (31 µs/pt at 400 steps, 7 ms/pt on sit-and-stare); bulk SJI→raster mapping needs an analytic inverse.
- Outside the preset M0 stays stock: the 'profile-viewer' tool keeps the modal, raster ROIs cost about 10 s per SJI frame with `link_hpc` until `wp10-m1-roi-world-polygon`, and histograms warn at 2e7 points.

### WP11: Display, readouts and inspection tools

CRISPEX-level display and inspection on stock Image and Profile viewers
through `setup()` registries and one dock widget; its one private patch is
gated (D2). On main already: `solar:frame_time`, `solar:cursor_readout`,
sliders, playback, alpha/mix and transparent NaN pixels.

**M1**

- [ ] **M1** `wp11-cursor-readout`: Split `CursorReadoutTool` so Qt #74 cannot remove the IRIS readout. The generic part, gated on glue-qt lacking `cursor_status` and with a `ProfileViewer` branch, retires with a Qt #74 release and shows pixel and world position, then value, from `pixel_to_world_values` at the full index as `Solar X`, `Solar Y` (arcsec to 0.01″) and λ (Å). The permanent `solar:frame_time` label adds the hovered pixel's `Time` and `Exposure time`, and km/s only with `meta.get("rest_wavelength")`. Done when on the 4000005156 Si IV scan-0 map, hovering step s: Solar X/Y equal `pixel_to_world_values` to 0.01″ at two zoom levels, λ is in Å, and the label shows step s's UTC (within 1 ms) and exposure, restoring the frame range on leaving; on 4000255147 SJI 1400 the label shows the displayed frame's time, data without `Time` shows none, and km/s appears only with a rest; a raster-spectrum Profile reads x in Å; with `ImageViewer.cursor_status` patched in, the gated tool is absent and the label still works. Depends: wp5-m1-rest-wavelength-policy (km/s only), wp1-m1-wrapper-coherence (Å).
- [ ] **M1** `wp11-selected-point-panel`: A read-only dock widget (CRISPEX's parameter overview), toggled by a `viewer_tool` and opened by the quicklook: for the Pixel point, per dataset, pixel indices, Solar X/Y, λ and its index, km/s (with a rest), scan/step, SJI frame, UTC, exposure and value, then the WP4 master and the signed SJI–raster offset or 'no match'. Done when, on the irispy 20140329 3860258481 raster (one scan as 3D, all scans as 4D) after a Pixel click, each field equals a direct read at the same indices and persists after the mouse moves; closing the quicklook removes the panel and its callbacks; the unrelated 3880012095 SJI 1400 fixture shows 'no match'; on 4000255147 + SJI 1400 the frame row equals WP4's nearest exposure and switching the master shows the signed offset; with `wp1-m1-sji-to-raster`, a point clicked on either fills the other's rows. Depends: wp4-quicklook-preset, wp4-m0-point-fixed-index, wp4-time-sync, wp1-m1-wrapper-coherence, wp5-m1-rest-wavelength-policy.
- [ ] **M1** `wp11-histo-opt-scaling`: A 'Scaling' `SimpleToolMenu` for Image viewers; 'Histogram opt' (c = 1e-2, 1e-3 (IRIS) or 1e-4 (CRISPEX)) sets Custom limits `np.nanpercentile(layer_state.get_sliced_data(), [100·c, 100·(1−c)])`; 'Follow frames' re-applies them on slice changes; 'Per-frame auto limits' toggles `stretch_global`. No new percentile choices (restored sessions reject them). From M1 `wp4-quicklook-preset` calls the same helper. Done when on 3610108077 with c = 1e-3 the limits equal the displayed slice's 0.1/99.9 nanpercentiles with v_min > −200; 'Follow frames' moves them on a wavelength step; per-frame limits change with the slider; a saved session restores the Custom limits.
- [ ] **M1** `wp11-gamma-stretch`: In `setup()`, add 'Gamma 0.4', 'Gamma 0.75', 'Gamma 1.5' and 'Gamma 2.2' through `glue.config.stretches.add`, each a no-argument astropy `PowerStretch` subclass, skipping labels already registered. Done when 'Gamma 0.75' is in the Stretch combo on glue-qt 0.4.2, its rendered values equal `PowerStretch(0.75)` of the linear ones, a session using it restores, calling `setup()` twice raises nothing, and the IRIS-9 'gamma < 1' step works in the preset.
- [ ] **M1** `wp11-raster-cmap`: In `_raster_collection_data`, pass `cmap=` 'irissjiFUV' or 'irissjiNUV' for per-scan rasters and stacks from each window's `SGMeta.detector_band`, read before stacking flattens the meta. Done when on 3610108077 layers default to irissjiFUV for C II and Si IV and irissjiNUV for Mg II k and 2832, the same holds for a 2-scan 4000005156 stack, and such a layer restores from a session. Depends: wp3-style-cmap.
- [ ] **M1** `wp11-physical-aspect`: A `viewer_tool` `solar:physical_aspect` wrapping the private `state._set_axes_aspect_ratio` to scale the ratio by the displayed axes' arcsec-per-pixel ratio (1 unless both axes are helioprojective with non-zero steps), re-running `_on_resize()` on axis changes; the preset sets `aspect='equal'` on maps. D2 probe: no 'Physical pixels' aspect choice (WP11 drafts the core PR on the user's direction; register row). Done when on released core 4000005156 (about 12:1) and 3400109360 (about 3:1) render a 10″×10″ solar square as square within 5% at the preset size, after a resize and a zoom; the factor is 1.03 on 3610108077 and 1 on sit-and-stare; a restored session re-installs the tool; with a release containing the upstream choice, the probe turns the workaround off. Depends: wp4-quicklook-preset, wp0-workaround-register.
- [ ] **M1** `wp11-keyboard-shortcuts`: Register plain keys for `ImageViewer`, `ProfileViewer` and the `wp10-m0-roi-guard` subclass: D/F previous/next frame on the WP4-synced axis, A/S previous/next wavelength, Space play/stop, wrapping. In the quicklook and Profiles, D/F move the WP4 master, A/S the wavelength index, and Space toggles `wp4-time-controls`; elsewhere Space calls the slice widget's private `_adjust_play` (register row). Skip keys already registered, bind glue's Tab/Backspace functions to the subclass, and name the keys in tooltips and the guide. Done when, with `QTest.keyClick` on glue-qt 0.4.2: D/F step ±1 with wrap and Space starts and stops playback on real SJI and raster viewers; after clicking the slice widget's buttons and with its slider focused, Space toggles exactly once and D/F/A/S still step (else another free key is documented); in the quicklook D/F move the master and its partner and A/S only the wavelength; calling `setup()` twice raises nothing; Tab and Backspace work from stock viewers and the quicklook map. Depends: wp4-quicklook-preset, wp4-time-sync, wp4-time-controls, wp10-m0-roi-guard.

**M2**

- [ ] **M2** `wp11-colourbar`: A checkable `viewer_tool` 'Colour bar' for Image viewers until glue releases one (glue #1087): it widens the right margin and draws the reference layer's colorbar in an inset axes through glue's normalisation, contrast/bias and stretch chain, refreshed on layer and slice changes. Done when on a raster and an SJI viewer the bar follows limits, stretch (log, gamma), cmap, a contrast/bias drag and slices with `stretch_global=False`; with aspect 'auto' and 'equal' the bar and ticks lie inside the figure at the default size; an `mpl:save` PNG includes it; toggling off restores the margins and closing the viewer disconnects the callbacks. Depends: wp11-gamma-stretch.
- [ ] **M2** `wp11-distance-measure`: A checkable `viewer_tool` `solar:measure`: a press–drag–release line shows in the status bar pixels, arcsec (`angular_separation` of the ends' lon/lat from `pixel_to_world_values`, not the high-level API) and km (× DSUN_OBS; arcsec only without it). Expose the separation and arcsec-to-km helpers in `glue_solar/tools.py` for WP12. Done when on 4000255147 SJI 1400 (CDELT1 0.16635″, DSUN_OBS 1.50921e11 m) a 100-pixel horizontal line reports 16.635″ within 0.01″ and about 12,172 km within 0.1%; on a 4000005156 raster map and 3660259102 C II 1336 the arcsec value equals the endpoints' WCS separation; the tool is disabled on non-celestial planes and leaves no artists after deactivation.
- [ ] **M2** `wp11-zoom-steps`: A `SimpleToolMenu` with 'Zoom 1:1' (one data pixel per screen pixel), 'Zoom ×2' and 'Zoom ÷2' about the view centre. Done when offscreen on an irispy raster fixture the axes width in screen pixels equals x_max − x_min after 'Zoom 1:1', '×2' halves both ranges about the centre, and Home restores the full view.

**M3**

- [ ] **M3** `wp11-centre-on-point`: 'Centre on selected point' in the `wp11-zoom-steps` menu moves the view centre to `PixelSubsetState.get_xy` at the same zoom. Done when the Pixel point then lies at the view centre with both ranges unchanged. Depends: wp11-zoom-steps, wp4-m0-point-fixed-index.
- [ ] **M3** `wp11-scaling-extras`: 'IRIS standard scaling' (SSW IRIS_INTSCALE: Custom limits at the 0.2 and 99.9 percentiles of finite values ≥ 0, low 0.5 for SJI 2796; 'log' with `a = v_max/v_min − 1` for FUV and SJI 1330/1400, 'sqrt' for NUV, 'Gamma 0.75' for SJI 2796, linear for SJI 2832) and 'Match scaling' (copy limits, stretch and cmap to the same dataset's layers elsewhere). Done when on 3610108077 Si IV (log) and Mg II k (sqrt), 4000255147 SJI 1400 (log) and 4000005156 SJI 2796 (γ 0.75) the action sets that stretch with limits equal to those percentiles within 1e-6 relative, log renderings equal the expected normalisation within 1e-6, and 'Match scaling' makes a spectrogram and a λ–t viewer of one stack identical. Depends: wp11-histo-opt-scaling, wp11-gamma-stretch.
- [ ] **M3** `wp11-band-average`: A band width of 1, 5, 9 or 15 wavelength pixels (CRISPEX default 5) for map views, written as Profile Collapse's `AggregateSlice`, re-applied by a `slices` callback because glue-qt's `sync_state_from_sliders` turns it into an int (D2 probe; register row; `wp0-qt-aggregate-slice`). Done when in a map view of a ≥ 4-scan 3602506433 stack with N = 2 the displayed array equals `nanmean(stack[scan, :, :, k-2:k+3], -1)`, stepping the scan keeps the band and stepping wavelength moves it, and `solar:frame_time`, the readout and `wp4-time-sync` accept it. Depends: wp0-workaround-register, wp4-time-sync.
- [ ] **M3** `wp11-north-up`: An optional north-up view for rolled SJIs: a north-up helioprojective grid (TAN WCS over the SJI FOV, same frame count) as reference data, linked with `link_hpc` plus a frame-axis pixel `LinkSame`, so glue's reprojection rotates the display; first a probe confirms 3D-onto-3D reprojection through mixed links and `wp1-m0-link-graph-regression` passes. Done when on the rolled 3860608353 SJI 2832 (SAT_ROT 45°) solar north is up within 0.5°, the readout on the rotated view matches the SJI's WCS within one pixel, and frame stepping works. Depends: wp1-m0-link-hpc, wp1-m0-link-graph-regression.

Notes:
- glue-qt key dispatch matches the exact viewer type, ignores modifiers and skips keys the focused widget consumes; B, C, G, H, K, M, P, R, W, X, Y, Z, Tab, Backspace and L (`solar:path`) are taken.
- Declined: a CRISPEX control-panel clone and, for zoom, wheel or keyboard zoom and a zoom-% readout.

### WP12: Export and derived diagrams

CRISPEX's export and derived diagrams (gap-aware time axes, x–t and spectral
path diagrams, multi-window light curves) through glue registries and core's
`BasePathSlicerMode`/`PathSlicedData`, in `glue_solar/export.py`,
`glue_solar/paths.py` and `glue_solar/sources/derived.py`. glue already has
`mpl:save`, playback and glue-qt 0.4.2's 3D 'slice' tool (P; no Data, no 4D).
Each PR adds its guide section.

**M1**

- [ ] **M1** `wp12-time-regrid`: D7's time-axis adapter: a D4 'Regrid on time' action adding a Data regridded at the median Δt of `Time` from a sit-and-stare exposure, SJI frame or fixed-step stack scan axis. Each pixel takes the nearest exposure within 0.75 × median, else NaN; `Time` holds source times (NaT in gaps); the WCS axis is 'Time since start' (s from DATEREF); spatial axes copy the middle matched exposure's calibration. The Data is marked in `meta` and excluded from `link_hpc` (checked in `glue_solar/sources/loaders/iris.py`); the index Data stays the navigation source. Done when on 4000255147 Si IV (1600 exposures, median 2.89 s) the Data has ceil(span/2.89)+1 time pixels with no NaN columns, each equal to its nearest exposure; with 10 exposures removed NaN columns appear only inside the gap; 4000255147 SJI 1400 and a ≥ 4-scan 3602506433 stack pass the same checks; WCSAxes labels 'Time since start' (s); exactly one Data, no viewer and no `link_hpc` link are added; the step axis of 4000005156 scan 0 is refused; the Data survives a WP3 round trip, rebuilt from the grid in `meta`. Depends: wp3-wcs-saver, wp1-m0-link-hpc.

**M2**

- [ ] **M2** `wp12-sequence-export`: `viewer_tool` `solar:save_sequence`, appended to 'save' after `setup()` deep-copies `ImageViewer.subtools`, steps one slice axis over a range prefilled from `wp4-time-controls` with frozen colour limits and a Cancel button, then restores slice, master and axes. Frames by `figure.savefig` (axes off until glue #2128) or whole-window `GlueApplication.screenshot()`; movies as MP4 with ffmpeg on PATH, else GIF. Done when on 4000255147 SJI 1400 frames 0-9 give 10 PNGs with identical limits, frame i equal to `mpl:save` at slice i; whole-window mode writes 10 window-size PNGs and restores the master; a 20-index wavelength scan on a 4000005156 raster map writes 20 PNGs; the GIF has 10 frames (MP4 too with ffmpeg); Cancel after 3 frames keeps and labels the partial output; no other viewer's 'save' list changes. Depends: wp4-time-sync, wp4-time-controls (prefill only).
- [ ] **M2** `wp12-derived-data-export`: A `data_exporter` 'FITS (IRIS WCS + Time)' for Data with `_GlueWCS` over an astropy `WCS` (WP2 moments, WP6 fits, WP5 Doppler image, sliced raster maps, wrapped sunpy maps); other Data is refused by name. One ImageHDU per numerical component with the raw WCS header (sliced maps: `raw.sub(<kept axes>)` plus a WAVELNTH or comment card), a WCS-TABLE HDU for -TAB axes, the uint8 mask, and `Time` as MJD with TIMESYS='UTC'. Done when on 4000005156 Si IV scan 0, its WP2 moments map and a sliced raster map, `WCS(header, fobj=hdul)` reproduces glue's world coordinates at 5 pixels within 1e-6 arcsec/Å; the sliced map records its fixed wavelength; `Time` round-trips within 1 ms and the mask equals the mask; a WP6 fit map exports all its components; `sunpy.map.Map` opens the export of a sunpy map; an SJI or light curve raises the message. Depends: wp3-wcs-saver, wp2-m2-moment-maps, wp6-m2-fit-maps, wp6-m2-products, wp5-m1-doppler-image, wp1-m1-sunpy-maps (map case only).
- [ ] **M2** `wp12-point-light-curves`: A D4 'Light curves at this point' action on a bare Pixel subset adds one 1D Data (datetime64 `Time`, value, optional mean normalisation) per chosen raster window (an index, or `nanmean` over ±N) and per SJI or loaded `aia_l2` channel, `LinkSame`-linked on `Time` and value to the first curve; no viewer. SJI frame t samples the point's world position at the WP4-matched exposure via the per-frame SJI WCS (D8). The coordinator recomputes them on subset updates and after a restore. Also a `data_exporter` 'ECSV (with Time)' for 1D Data. Done when on 4000255147 with a point at slit y the Mg II k, C II core and SJI 1400 curves exist; raster curves equal `cube_w[:, y, k]` (and the band variant its `nanmean`); the SJI curve has 400 samples equal to `sji[t, row(t), col(t)]`, NaN at NO MATCH frames; normalised curves average 1; all layers show in one Scatter with 2013-09-02 date ticks; dragging updates every curve and `solar:time_marker` follows the master, also after a WP3 round trip; ECSV re-reads keep `Time` within 1 ms; `wp1-m0-link-graph-regression` passes with the curve links. Depends: wp4-time-sync, wp1-m0-link-hpc, wp7-goes-marker, wp7-goes-date-labels, wp3-coordination-reattach.
- [ ] **M2** `wp12-path-slicer`: 4D solar-coordinate path diagrams on core's path slicer (1.26.0+, covered by the 1.27.0 floor), not the legacy PV widget. `solar:path` ('Solar path (3D/4D)', key L) and `solar:path_crosshair` subclass `BasePathSlicerMode` and `BasePathSlicerCrosshairMode`: allow 3D/4D; build one `PathSlicedData` per raster, SJI or AIA layer from vertices converted into that layer's own pixel frame via world coordinates at the WP4 master frame; store drawn and reference-frame vertices in `meta['solar_path']`; `_on_move` moves only the represented parent axis. Axes: cumulative arcsec 'Distance along path' (the `wp11-distance-measure` helper) and UTC on exposure and scan axes. If a glue-qt release has #66 first, subclass its tools. Done when on 4000255147 SJI 1400 a 3-vertex path adds a (400, N) Data with arcsec and UTC axes; the sit-and-stare raster gives (λ, N) and a ≥ 4-scan 3602506433 stack (scan, λ, N); with the 4000005156 stack and SJI 2796 in one viewer (probe-gated on #2595) each layer gives one trace agreeing within 0.5 px, and clicking frame t in the SJI trace's diagram sets the raster scan to the matched exposure's; clicking a raster result moves only the represented slider; no two Image tools share a shortcut; a signature test of the overridden private hooks passes on 1.27.0; the link-graph regression passes with a path product. Depends: wp1-m0-link-hpc, wp4-time-sync, wp0-workaround-register, wp11-distance-measure.
- [ ] **M2** `wp12-path-persist`: A session saver and loader for `PathSlicedData` storing the parent, pixel components and `meta['solar_path']`; the loader rebuilds via `set_xy(vertices, spacing)` in arcsec and sets `parent_viewer` if a viewer shows the parent. 'Save path'/'Load path' on the `solar:path` menu use ECSV. Done when on 4000255147 SJI 1400 and a two-scan 4000005156 stack a path survives two save/reopen cycles with identical shape and values and vertices within 1e-9 px; a saved path ECSV reloads the same diagram; 'Export data values' as FITS writes every component, and HDF5 raises on `Time` until `wp0-core-datetime-export` is fixed; the product at any retained index equals the parent sampled along the path. Depends: wp12-path-slicer, wp3-wcs-saver, wp3-app-session-acceptance, wp3-session-budget.

**M3**

- [ ] **M3** `wp12-export-annotations`: Options on `solar:save_sequence`: UTC text, an arcsec scale bar (`AnchoredSizeBar`, sized with the `wp11-distance-measure` helper), frame numbers, and an editable default name `<OBSID>_<STARTOBS>_<label>_<axis><i0>-<i1>.<ext>`. Done when on 4000255147 SJI 1400 frame i's text equals Time[i] (ISO, 0.01 s), a 10-arcsec bar spans 10/CDELT1 pixels ±1 px, frame numbers equal slice indices, the default name is proposed and editable, and a visible subset overlay appears in the PNG. Depends: wp12-sequence-export, wp11-distance-measure.
- [ ] **M3** `wp12-profile-values-export`: `viewer_tool` `solar:save_profile` (after `setup()` deep-copies `ProfileViewer.subtools`) writes each visible layer's profile to one ECSV (the light-curve writer) with x name and unit, layer label, a Pixel subset's pixel and world position, and per-sample UTC on exposure or scan axes. Done when on 4000255147 with a Pixel subset and x on exposures the re-read x/y equal the viewer's arrays, the Time column equals `Time` at that pixel, two visible layers give two column sets, empty layers are skipped with a note, and no other viewer's 'save' list changes. Depends: wp12-point-light-curves.
- [ ] **M3** `wp12-path-overlays-slopes`: `solar:path` draws every saved path on any viewer showing the parent, with a line style and optional 'only at wavelength index w'. A TANAT-style two-click slope readout on distance–time diagrams gives projected speed in km/s and a three-point parabolic acceleration, appended with an ID and flag to an ECSV table. Done when saved paths redraw with their styles after a round trip and 'Load path', wavelength-restricted paths show only at w, an injected feature of known slope and acceleration on a copy of 4000255147 SJI 1400 is recovered within 1% and 2%, and ECSV rows round-trip. Depends: wp12-path-persist, wp11-distance-measure.
- [ ] **M3** `wp12-path-batch`: 'Re-extract along this path' applies a saved path to other ticked datasets and windows; a `PathSlicedData` subclass adds 'nearest' (`np.rint`, CRISPEX's default) and 'linear' (`map_coordinates(order=1)`) sampling beside core's truncation, recorded in `meta['solar_path']`. Done when a path re-extracted on another 4000005156 window uses identical vertices; all ticked windows get one product each; on a synthetic ramp 'nearest' equals `np.rint` sampling and 'linear' matches `map_coordinates(order=1)` to 1e-6; the default equals stock `PathSlicedData`. Depends: wp12-path-persist.

Notes:
- Paths, SJI traces and curves use the WP4 master frame or matched exposure; a fixed pixel path ignores pointing drift. Stack paths use the scan-0 WCS until `wp1-stack-per-scan-wcs`.
- glue's gridded FITS writer drops non-astropy WCS and datetime64 `Time`; other formats fail on datetime64 (`wp0-core-datetime-export`).
- Not rebuilt: CRISPEX phi-slit sliders, path width, IDL .csav/.clsav/.cint/.cses (FITS, ECSV and sessions replace them).
- Private hooks overridden (register row 'Path tools'): `BasePathSlicerMode._on_reference_data_change`, `_open_or_update`, `_refresh_overlays`, `BasePathSlicerCrosshairMode._on_move` and `PathSlicedData._get_pix_coords`, all at 1.27.0.

## Prototypes to port

None is copied over glue-solar wholesale; each port lands on a feature branch
from `main` with the listed fixes. Paths are under `IRIS_PLAN_PROTOTYPES/`.

| Prototype | Port | To | Fix first |
| --- | --- | --- | --- |
| `wp1/glue_solar/`: `link_hpc`, browser call, link menu action, gated `glue_patches`, axis-name flip | Port | `sources/loaders/iris.py`, `sources/iris.py`, `glue_patches.py` (WP1, M0) | Delete the `"time": "Time"` axis-name entry with the flip; the gate is a behaviour probe |
| `wp1/glue_solar/sources/loaders/iris.py` unit and high-level `_GlueWCS` hunk | Parts | `sources/loaders/iris.py` (WP1, M1) | `_converting_constructor` argument order |
| `wp1/glue_solar/tests/test_linking.py` | Port | `tests/test_linking.py` (WP1) | Use `find_irispy_test_file` |
| `review_20260927/probes/linkgraph/test_linkgraph.py` | The order/allocation matrix and checks (a), (c)-(e) | `tests/test_linking.py` CI variant (WP1, M0) | Drop the pixel-ID time-link and design-B link sets (D8) |
| `wp1/glue_solar/tests/test_importer.py` | Three hunks only | `tests/test_importer.py` (WP1) | Do not copy the file; it reverts #50/#52 |
| `wp4_common.py`: `nearest`, `exposure_times`, `observation_key` | Parts | `glue_solar/quicklook.py` (WP4, M0) | `nearest` accepts unsorted/duplicate references and returns the offset and a no-match flag; nothing else is ported |
| `slit_check.py`, approach C | Parts | WP4 slit overlay (M0) and raster footprint (M1) | Use `nearest` and the no-match rule; lon/lat by physical type; compact per-frame arrays |
| `review_20260923/test_existing_workflows.py` | Parts | `tests/test_quicklook.py`, `tests/helpers.py` (WP4, M0) | Gate the display-unit branch on a Qt #70 capability |
| `review_20260905/test_refresh.py` | Parts | `tests/test_quicklook.py` (WP4); blink test to WP5 | Flip the encoded defects: descending references accepted, no match instead of clamping |
| `review_20260923/test_wcs_capabilities.py` | Parts | `tests/test_linking.py` (WP1, M1, gated on #2595) | Assert footprint columns and frames, not "any pixel selected" |
| `wp3_impl.py`, `wp3chk_test_sessions.py` | Parts / port | `_GlueWCS` savers, scoped styles, named factories, `tests/test_sessions.py` (WP3, M1) | Index column only where `PSi_2` exists; derived-map contract with `GlueSerializeError` otherwise; integer slices; guarded Quantity saver |
| `chk_wp2/wp2_moments_module.py`, `chk_wp2/test_wp2_moments.py`, `wp2_moments_proto.py` (two checks) | Port | `sources/moments.py`, `tests/test_moments.py` (WP2, M2) | Wings required; explicit D11 rest; saveable map WCS; NaN/Inf handling |
| `wp5_units.py`, `wp5_override.py`, `iris_lines.csv`, `wp5_linelist_mod.py` + `review_20260905/test_line_positions.py`, `wp5_blink.py` | Parts | `spectral.py`, `data/iris_lines.csv`, `tools.py`, `tests/test_linelist.py` (WP5, M1) | No global unit narrowing or TWAVE fallback; lines as `wp5-m1-line-list`; stock style editor; `np.interp` not `brentq`; blink alternates (dataset, slice) pairs |
| `wp6_chk_real_fixed.{py,log}`, `wp6_full_raster.{py,log}` | Test evidence | WP6 4D stack test and the `wp6-m2-worker` budget baseline | none |
| `wp5_label.py` | Upstream PR only | glue-core Profile axis label (`wp0-core-profile-unit-label`) | Not a solar patch |
| `wp6_fitting.py`, `wp6_test_fitting.py` (+ two asserts of `wp6_test_fitting_final.py`) | Parts / port | `sources/fitting.py`, `tests/test_fitting.py` (WP6, M2) | Source mask via `mask=`; no clipping; reject amp ≤ 0, out-of-window and unconverged fits; publish \|sigma\|; float32 opt-in residual |
| `wp7chk/context_chk.py`, `test_context.py`; `archive/probes-2026-09/wp7_timelink.py`, `wp7_goes.py`; `wp0_bug_epoch_viewer.py` | Parts | `sources/context.py`, `tests/test_context.py` (WP7, M2) | Off-limb crop; XRS quality flags; header-WCS footprint oracle; not the `EPOCH=1` path |
| `wp8_scan.py`, `wp8_proto.py`, `wp8_loader.ui` + `wp8_test_proto.py`, `wp8_test_shipped.py`, `wp8_chk_test_text.py` | Parts / port | `scan.py`, `iris.py`, `iris_loader.ui`, tests (WP8, M2; the Worker pattern also for `wp10-nonblocking-load`) | Load during rescan; stop inside the walk; 'Scan stopped' wording; event-based tests |
| `review_20260905/test_plan_integration.py` | `test_wp3_roundtrips_wp6_fitted_map` only | `tests/test_sessions.py` (WP6, M2) | Drop the stubbed quicklook test |

## Validation, environments and data

Run all Python in a micromamba environment, never a `.venv` or the system
Python. Create a new named env rather than changing an existing one.

- **`iris-plan`** (the D5 baseline): Python 3.13, glue-core 1.27.0
  (conda-forge), glue-qt 0.4.2 (PyPI wheel with `--no-deps`; conda-forge's
  osx-arm64 has only noarch 0.2.0), PyQt5, irispy-lmsal 0.9.1 (conda-forge),
  ndcube 2.4.2, astropy 8.0.1, sunpy 8.0.0 with cdflib and h5netcdf,
  pytest-doctestplus, pytest-qt, glue-solar editable. Baseline: `glue_solar`
  gives 37 passed, 1 skipped on main e9e6a11 (the skip needs core #2595).
  It has no pytest-mpl, so glue `@visual_test` comparisons do not run.
- **`iris-plan-floor`**: `iris-plan` with irispy 0.9.1's floors, astropy
  8.0.0 and ndcube 2.4.0 (conda-forge, plus pvextractor), and the glue-qt
  wheel and editable glue-solar installed `--no-deps`. Baseline: 37 passed,
  1 skipped on main e9e6a11. WP1 items pass in both envs.
- **Checks on both envs (2026-09-29):** scalar and array inputs to both
  `_GlueWCS` value methods agree exactly on every irispy raster window and
  the SJI. The WP2/WP5/WP6 prototype checks (`chk_wp2/test_wp2_moments.py`,
  `wp6_test_fitting.py`, `review_20260905/test_line_positions.py`, run with
  the fixtures symlinked to their pre-0.9.0 names) give 14 passed, 2 failed;
  the same 2 fail on irispy 0.9.0 (counts measured on 0.8.1 fixtures), so the
  ports derive them from the fixtures. irispy 0.9.1 still falls back to TWAVE
  when `rest_wavelength` is None, so WP2 always passes it (D11).
- **`iris-plan-docs`** (`wp9-m0-docs-build` creates it): the `iris-plan` pins
  plus the `docs` extra. Build with
  `sphinx-build -W --keep-going -b html docs <out>`, never `tox -e build_docs`.
- **`irispy-ports`**: irispy development, Python 3.14, irispy `[tests,docs]`
  editable from `~/Git/irispy-bursts`. Test another irispy worktree from a
  neutral directory with `PYTHONPATH=<worktree>` and
  `-c <worktree>/pytest.ini --rootdir=<worktree>`; never run Python from
  `~/Git/irispy`. Docs doctests: `pytest docs --remote-data=any` with
  `COLUMNS=300`; a quick docs check is
  `sphinx-build -b html -D plot_gallery=0 -W --keep-going docs <out>`;
  `pre-commit` is installed there.
- **`glue-solar`**: imports glue, glue-qt and irispy editable from the
  checkouts, so it follows whatever branches are checked out; not for
  baselines. **`ruff-0161`**: glue-solar's pinned ruff. The old
  `irispy-v34-fix` env imports irispy from a removed worktree and can be removed.
- `<scratch>` below is a disposable directory outside the repositories (for
  example from `mktemp -d`).
- **Runner.** Run from a checkout of the code under test (a feature worktree
  or `git -C ~/Git/glue-solar worktree add --detach ~/Git/glue-solar-main origin/main`),
  never from `~/Git/glue-solar`, which is on `plan`:

  ```sh
  P=~/Git/glue-solar/IRIS_PLAN_PROTOTYPES/review_20260905
  env HOME="$(mktemp -d)" PYTHONPATH=$P \
    ~/mamba/envs/iris-plan/bin/python -B $P/run_checks.py \
    "$PWD:$P" glue_solar
  ```

  `run_checks.py` sets offscreen Qt/Agg and temporary Glue, Matplotlib and
  SunPy config directories; glue-solar's own conftest keeps the tests off the
  real QSettings and `~/.glue` (#63). To test an unreleased irispy commit, add a detached worktree as an extra
  root (`git -C ~/Git/irispy worktree add --detach <scratch>/irispy-<sha> <sha>`;
  not `git archive`, because irispy reads its version from git) and print
  `irispy.__file__`.
- **Unreleased upstream PRs** are tested as extra roots from exports
  (`git -C <repo> archive <head> | tar -x -C <scratch>/<name>`), regenerated
  before use because macOS purges temporary directories; drop missing roots
  (an empty export shadows the package). Do not run core and Qt suites in one
  pytest run. Never spoof a version to pass a gate; mock modal dialogs in
  headless tests.
- **Fixtures**: `glue_solar/conftest.py`'s `find_irispy_test_file` (prefer the
  `sns/` copy). irispy's fixtures are full windows decimated 10×: derive
  expected values from the fixture and do not call them physical validation.
- **Data** (user rule 2026-09-29): glue-solar tests never read local paths or
  commit test data. Real-data tests are `@pytest.mark.remote_data` tests on
  LM-SAL/irispy-data release assets (tag `v1`), fetched and SHA-256-checked
  with pooch through the `irispy_data` fixture (#65) and run by the `online`
  tox factor or `--remote-data=any`; a file irispy-data lacks is added there
  first (its `make_cutouts.py`, on the user's direction). irispy-data v1 has
  cutouts of 3610108077, 3824262996, 4000255147 (Mg II k and C II, 439 MB),
  4000005156 (scan 0), 3660259102, 3400109360 (scan 0, Mg II k), 3602506433
  (scan 10), 3893012099 and the 3640107442 SDO tarball, plus 4000255147 SJI
  1400 (`_f050`), 4000005156 r00000 Si IV and the Fe XXI rb_steps product.
  Full-size acceptance and performance checks are manual probes under
  `IRIS_PLAN_PROTOTYPES/` on `~/DATA/IRIS` (the M0 list), with results recorded
  here. The `iris-plan` envs have pooch and pytest-remotedata. Also local: 3610108077
  (20180102_153155 raster), 3660259102 (20210429_110908 raster), 3640107442
  (20250519_165924 AIA cutouts only), 3860608353 (20140919_051712 rolled SJI
  2832), 3893010094 (20250710_121126 deconvolved SJI 2832) and
  `iris_l2_20140910_fexxi_rb_steps` (a derived product). The IRIS-9
  observations are not local.
- **Linters**: repo-pinned Ruff (core 0.15.20, Qt 0.14.14, solar 0.16.1 in
  `ruff-0161`, irispy through its pre-commit); do not weaken a baseline for
  newer rules.
- **IDL**: the reference-run package and GDL harness are in
  `IRIS_PLAN_PROTOTYPES/idl_reference/`; GDL comes from MacPorts
  `gnudatalanguage`, Ubuntu, or the GDL weekly macOS `.dmg`.
