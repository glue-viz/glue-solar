> Historical snapshot, archived 2026-09-05. Not an active checklist.
> Original location: `glue-solar/IRIS_GLUE_GAP_PLAN.md`. Body preserved verbatim; paths and status claims describe that original context and may be stale.
> Current instructions: [the central work plan](../../../IRIS_GLUE_GAP_PLAN.md).

# Plan: closing the IRIS capability gaps

Companion to [`IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`](IRIS_IDL_GLUE_CAPABILITY_AUDIT.md).
The 2026-09-05 review, fixes and verified pushed commit IDs are recorded in
[`IRIS_BRANCH_REVIEW.md`](IRIS_BRANCH_REVIEW.md). That status takes precedence
over the historical 2026-09-02 execution logs below. Do not rerun completed
branch creation, force-push, reset, PR publication or review-request steps.
Rewritten 2026-09-02 after a code-level review of every item of the 2026-08-29
plan against glue-solar, the glue and glue-qt forks, irispy-lmsal 0.8.1, sunpy
8.0.0, ndcube 2.4.1 and astropy 8.0.1 (27 audit agents, every claim re-run by an
independent verifier, then one implementation brief per work package, each
re-checked). The previous plan is kept for reference as
`IRIS_PLAN_PROTOTYPES/IRIS_GLUE_GAP_PLAN.2026-08-29.md`; findings cite its line
numbers.

This file is the working TODO. Part 1 is the summary and the order of attack.
Part 2 holds one self-contained implementation brief per work package (WP0 to
WP9), written for an agent with no prior context: current state with
file:line evidence, decisions, exact steps, code that was run on 2026-09-02
with its output, tests, pitfalls and acceptance criteria.

## How to use this file

- Pick a work package from the order below, read its brief in Part 2
  (`grep -n '^# WP' IRIS_GLUE_GAP_PLAN.md` lists the section starts), and follow
  its steps. Briefs cross-reference each other by WP number.
- Scratch paths inside the briefs (`$S`, `<scratchpad>`, `<scratch>`,
  `IRIS_PLAN_PROTOTYPES/...`) all refer to the session scratch directory of the
  review. Available scripts, modules, tests, diffs and logs were
  copied to `IRIS_PLAN_PROTOTYPES/` (flat, plus the subdirectories `wp1/`,
  `wp3_sess/`, `wp7chk/`, `chk_wp2/`, `wp9chk/`, `verify/`, `findings/`). The
  briefs also paste the final form of every snippet inline, so the copies are a
  convenience, not a requirement. `findings/` holds the raw audit JSON per area
  plus `critic.md`; `audit-findings-condensed.txt` and
  `brief-checker-reports.txt` are readable summaries. The throwaway git clones
  (`glue-split`, `glueqt-split`, `gs-*`) and the ruff binaries were not copied;
  WP0 records how they were created. The historical `wp4_common.py.writer`
  was not retained. Long PR drafts are directly under `wp0/`, not `wp0/long/`.
  The missing `wp8_loader.ui` was reconstructed from its inline diff on
  2026-09-05. Old absolute scratch paths are historical, not portable commands.
- `IRIS_PLAN_PROTOTYPES/` and this file are untracked. Never `git add -A` in
  this repository; add files by name.
- References of the form `briefs/wpN-<name>.md` mean the WPn section of this
  file.

## Current status (2026-09-05)

- The branch review found regressions despite the earlier green local tests.
  Branch fixes and fresh local test results are tracked in `IRIS_BRANCH_REVIEW.md`.
  All eight affected branches were committed and pushed on 2026-09-05 without
  rewriting history; fresh remote CI has not yet been validated. The planning
  documents and prototype fixes remain local and untracked.
- Core local main is `dae530c3`; upstream main is `751871df` (two commits
  ahead, one changed file: `glue/core/state_path_patches.txt`). Qt and solar
  mains still match upstream at `9780eaf9` and `5b229fbc` respectively.
- `loadable-iris-fixtures` (`383dec2`) is a separate solar branch above the
  browser branch. Its irispy 0.8.1 compatibility fixes are in the
  `~/Git/glue-fixes/solar-fixtures` worktree; there is no PR yet.

- glue-solar PR #44 (observation browser, branch `iris-observation-browser`,
  head d3a2bd3) is open and mergeable with CI green. No reviews were
  requested: the user reviews every diff first (decision, 2026-09-02).
- Everything in Phase 1 and Phase 2 of the old plan is unimplemented. That part
  of the old plan was accurate.
- The three "detailed working TODOs" were already implemented on fork branches
  with passing tests in the originally tested environment. WP0 published them on 2026-09-02 as DRAFT PRs with short
  bodies and shortened commit messages (trees unchanged; SHAs quoted in the
  briefs and TODO files are the pre-rewrite ones):
  - APE-14 autolink (old Phase 3.1): glue-viz/glue#2595 from
    `ape14-wcs-autolink`. Real IRIS SJI + raster autolink verified: one
    `WCSLink`, sky positions agree to 3e-7 arcsec, exact round trip.
  - Profile viewer WCS: glue-viz/glue#2596 (piece C, `profile-slice`),
    glue-viz/glue#2601 (piece A, `profile-wcsaxes`, stacked on C) and
    glue-viz/glue-qt#70 (piece B, `profile-wcs-pr`, feature-gated: 68 passed /
    14 skipped on released glue-core, 81 / 1 with the core PRs). Stale glue
    PR #2248 closed, fork branch `1dprofile_wcs` deleted.
  - macOS integration: the CI repairs are glue-viz/glue-qt#69 (`ci-fixes`);
    the #68 rewrite/push/body/draft update is complete. The follow-up CI test
    correction is pushed on `ci-fixes` (`5cc9e23e`) and merged into
    `macos-integration` (`0b16dd55`) and `profile-wcs-pr` (`f5444473`).
    #70 now contains the shared CI repairs; land #69 first.
    The historical `macos-integration-v2` alias remains at `4d93c64f`.
  - One-line glue-core bug fixes: glue-viz/glue#2597 (session save: colormap
    and Quantity meta), #2598 (`world2pixel_single_axis` time freeze), #2599
    (datetime epoch); issue #2600 (`RegionData` crash).
- The three TODO files in the forks were updated on 2026-09-02 to match
  (checkboxes ticked, wrong statements fixed, PR numbers recorded).
- Environment used for the historical 2026-09-02 verification: glue-core 1.27.0 from
  PyPI, glue-qt editable from `~/Git/glue-qt` (currently on
  `macos-integration`), irispy-lmsal 0.8.1, sunpy 8.0.0, ndcube 2.4.1, astropy
  8.0.1, dask 2026.8.0, PyQt6, Python 3.14 in `.venv`.

## Decisions (final)

- **D1. Phase 1.4 `link_hpc` is permanent.** The fork's APE-14 `WCSLink` is
  frame-0 geometry (the SJI time axis is not part of the link). On the real
  4.8 h rotation-tracked sit-and-stare test observation the pointing drifts
  42 arcsec, so the pixel link reaches 14 of 187 raster steps versus 186 with
  world-component links. The two are complementary; nothing is "deleted once
  autolink lands".
- **D2. glue-solar first.** Old Phases 3.2 to 3.6 ship from glue-solar through
  public glue-core registries (`unit_converter`, `layer_artist_maker`,
  `viewer_tool` and `ImageViewer.tools`, `saver`/`loader`, `__gluestate__`).
  Upstream PRs are opened only for work that already exists on the fork
  branches, plus one-line glue-core bug fixes that glue-solar works around
  meanwhile. Guiding principle 3 of the old plan ("viewer behaviour belongs
  upstream") becomes "upstream later, never a gate".
- **D3. Display units: arcsec for helioprojective axes (already), Angstrom
  for wavelength.** `_GlueWCS` converts wavelength from the stored metres the
  same way it converts degrees to arcsec, in the values API and in the
  high-level object API. Angstrom rather than nm because IRIS headers
  (`TWAVE`), IRIS line names (C II 1336, Mg II k 2796) and the IDL tools all
  use Angstrom; switching to nm later is a one-word change in `_AXIS_UNITS`.
  irispy itself reports `meta.rest_wavelength` and moment maps in nm; WP2
  converts them. This lands in WP1 and every later WP assumes Angstrom.
- **D4. The moments action is a right-click `layer_action` that adds the
  result dataset and does not open a viewer.** A `layer_action` callback
  receives only `(layer, data_collection)`; opening a viewer would force a
  `menubar_plugin` with a dataset picker. Same rule for the fitting action.
- Kept from 2026-08-29: Level-3 FITS generation and EIS support are permanent
  non-goals; the first science PR is moments only with numeric wings fields.

## What the 2026-08-29 plan got wrong (verified)

- Phases 3.3 to 3.6 need no glue-core or glue-qt work. Velocity units are
  about 15 lines on the existing converter registry; the line list is about
  50 lines via `layer_artist_maker`; "mix" already exists (per-layer alpha and
  the "One color per layer" mode) so only a timed blink tool is missing;
  sessions are about 120 lines in glue-solar and the "all or nothing" rule is
  refuted. Session saving already crashes for every glue-solar dataset today,
  including sunpy maps, because of a one-line glue-core colormap bug.
- Phase 3.2 is small, not the "largest upstream effort". Slice translation
  through links exists in glue-core (`translate_pixel`, `data[cid, view]`);
  cross-viewer sync was demonstrated end to end in about 100 lines of
  glue-solar code. The proposed `join_on_key` "nearest" extension is not needed
  and a `JoinLink` must not be used at all (it makes an SJI selection select
  the entire raster, WP4).
- Phase 3.1 only links SJI to raster until glue-solar fixes its wrapper: the
  arcsec conversion leaves the high-level object classes in degrees, so
  raster-to-raster and map-to-raster autolink fail with `IncompatibleWCS`. The
  fix is about 15 lines in glue-solar (WP1) and makes moment maps autolink.
- The moments PR needs no loader prerequisite: a Data can be rewrapped into a
  `SpectrogramCube` and fed to irispy directly. Outputs are one Data with five
  components, pixel-linked to the source. The test rasters lack `TWAVE`, so
  tests pass an explicit rest wavelength. Stacked 4D datasets are plain
  NDCubes; v1 covers per-scan datasets.
- glue-qt already has the interactive moment UI: the Profile viewer's Collapse
  tab drives the Image viewer with sum, mean, moment 1 and moment 2 over a
  drawn wavelength range. The two "Missing" moment rows are Partial.
- `dask` is already a hard irispy dependency: no `fitting` extra.
  `parallel_fit_dask` exists since astropy 7.0.0. Fits cost about 1 ms per
  spectrum; seeding, not threading, is the correctness-critical part.
- `density_diagnostic` is not cube-in cube-out: it needs fiasco and CHIANTI
  plus two intensity maps. Dropped. Red-blue asymmetry is fine (WP2
  follow-up).
- GOES needs the `sunpy[timeseries]` extra, a Scatter viewer (the Profile
  viewer raises on a datetime-first dataset) and a workaround for a glue-core
  datetime epoch bug that mislabels every date axis today, including the
  raster `Time` component.
- The irispy coalign gallery is a cross-correlation recipe needing aiapy and
  sunkit-image, not the SDO retrieval recipe; the aligned AIA cutouts the
  browser already loads cover most of that row. `propagate_with_solar_surface`
  is a context manager and changes nothing for a co-temporal image.
- The slit overlay is a per-frame subset built from the SJI aux slit-position
  columns irispy already exposes, not a linked scatter dataset (which would
  draw every frame's slit at once).
- Log files: no public Level 2 download, irispy sample or pooch cache contains
  a `.log`; only level1to2 pipeline mirrors do. Dropped.
- The spectroheliogram view is the default Image viewer layout for a raster
  window; only the whisker preset needs code.
- Threading the directory scan is about mirror-scale trees: a real 140-file
  tree scans in 0.5 s.
- Unlisted gaps: no movie or sequence export exists anywhere in glue; the
  detector-view row has no phase and irispy has no full-detector reader; the
  per-scan stack WCS non-goal had a wrong premise (a gwcs tabular model
  reproduces every scan's coordinates exactly, only the inverse model is
  work); `irispy.obsid.ObsID` gives free OBS metadata; a sit-and-stare raster
  already loads with time as axis 0.

## Where each gap lands now

| Audit row | Status 2026-09-02 | Work package | Size |
| --- | --- | --- | --- |
| Search and group local observations | Partial | WP8: text filter (ISO `STARTOBS` doubles as a date filter), cancellable threaded scan | small |
| Display observation metadata (OBS XML) | Partial, non-goal for XML | none scheduled; `irispy.obsid.ObsID` could be surfaced later | n/a |
| Display log files | Dropped | WP8 records the evidence so it stays closed | n/a |
| SJI inspection | Partial | WP4 slit subset; WP5 blink (mix exists); playback exists; sequence export is an unlisted, unscheduled gap | small |
| Detector view (mosaic) | Partial | none scheduled (no irispy full-detector reader) | n/a |
| Coordinated raster browser | Partial | WP4 quicklook layout; per-pixel spectrum needs the profile-wcs `'slice'` function (WP0) or a one-pixel subset | small |
| Multiple-raster navigation (per-scan WCS) | Partial, deferred | premise reworded (WP4 docs); inverse gwcs model is the open piece | medium |
| Sit-and-stare navigation | Covered by default | WP4 whisker preset gives the wavelength-versus-time layout | trivial |
| Spectroheliogram panels | Default Image viewer layout | WP4 documents it; no code | none |
| Whisker plot | Missing | WP4 preset (about 10 lines) | trivial |
| Zeroth-moment intensity map | Partial (Profile viewer Collapse tab) | WP2 `IRIS: line moments...` layer action | small |
| Profile moments | Partial (Collapse tab moment 1 and 2) | WP2 | small |
| Single/double Gaussian fitting | Partial (single-spectrum Fit tab) | WP6 per-pixel maps via `parallel_fit_dask` | medium |
| Wavelength/velocity and line IDs | Partial | WP1 Angstrom; WP5 velocity converter and line-list layer | small |
| SJI and raster temporal coordination, autolink | Partial | WP0 upstream PR (3.1); WP1 `_GlueWCS` coherence and `link_hpc`; WP4 time link and slice sync | small |
| GOES context | Missing | WP7 (needs `sunpy[timeseries]`) | small |
| SDO pointing context | Partial (aligned cutouts load) | WP7 live AIA submap and FOV polygon subset | medium |
| Level-3 FITS generation | Will not implement | none | n/a |
| Session round trips | Missing (save crashes) | WP3, glue-solar only | small |
| EIS data and housekeeping | Will not implement | none | n/a |

## Work packages and order of attack

| Step | WP | What | Depends on | Unblocks |
| --- | --- | --- | --- | --- |
| 1 | WP0 | PR publication and #68 rewrite complete. Local follow-up fixes are tracked in `IRIS_BRANCH_REVIEW.md`; commit/push and fresh remote CI remain pending, then user review before marking drafts ready | nothing | WP1's gated autolink test needs a glue release with #2595 |
| 1 | WP9 | Doc corrections to the audit (applied 2026-09-02), the user-guide rst pages and the dev guide (still to commit on `iris-observation-browser`) | nothing | keeps PR #44 honest |
| 2 | WP1 | Linking basics: `_GlueWCS` in Angstrom and coherent for the high-level API, one naming for SJI and raster axes, `link_hpc`, the `world2pixel_single_axis` workaround, gated autolink regression test | #44 merged (or branch from it) | WP2 to WP7 |
| 3 | WP2 | Moments layer action (one Data, five components, two pixel links) plus the red-blue asymmetry follow-up | WP1 (names, Angstrom) | nothing else; first science feature |
| 4 | WP3 | Sessions: `_GlueWCS.__gluestate__` (asdf for gwcs, rebuilt `-TAB` table, recursive sliced/compound), Quantity meta saver, colormap saver workaround, browser through `load_data` | WP1 | WP4 to WP7 outputs become saveable |
| 5 | WP4 | Quicklook bundle: whisker preset, quicklook layout, per-frame slit subset, SJI `Time` component, time link, cross-viewer slice sync | WP1 | coordinated browsing |
| 6 | WP5 | Velocity display units, blink tool, line-list layer with an IRIS line list | WP1 | nothing |
| 7 | WP6 | Gaussian fit maps (single, then double) in a background `Worker` | WP1; WP3 for saving the sliced-WCS outputs | nothing |
| 8 | WP7 | GOES light curve and SDO context actions | WP1 (AIA in `_GlueWCS`, `link_hpc`); `sunpy[timeseries]` | nothing |
| any | WP8 | Browser filter and cancellable scan | nothing (touches `test_importer.py`, so land it in a separate PR from WP1) | nothing |

Rationale for the order: WP0 and WP9 are pure shipping and cost nothing to
start. WP1 is the root of every later glue-solar package (names, units,
coherence, links). WP2 is the decided first science feature and is cheaper
than planned. WP3 comes early because every session save crashes today and
later packages produce datasets people will want to save. WP4 to WP7 are
independent of each other after WP1 and WP3.

Sizes measured on the prototypes: WP1 about 120 lines, WP2 about 110 lines
plus tests, WP3 about 120 lines, WP4 about 150 lines, WP5 about 150 lines plus
a CSV, WP6 about 175 lines, WP7 about 120 lines, WP8 about 60 lines plus seven
test edits.

## Cross-package resolutions

These settle disagreements between briefs; the later ruling wins and is
already reflected in the briefs.

- Time link (WP4): identity `ComponentLink`s on precomputed nearest-index
  components only. The `JoinLink` proposed by the audit critic is rejected:
  with it, any SJI selection selects the whole raster (216920 of 216920
  pixels) through `Data.get_mask`'s key-join fallback.
- SJI-drawn selections onto the raster: the safe workaround is the
  `world2pixel_single_axis` wrap in `glue_solar/glue_patches.py` (WP1). An
  all-ones `axis_correlation_matrix` override is rejected: it makes the Image
  viewer's coordinate readout raise `OverflowError` on every mouse move.
- `_GlueWCS` coherence is the 15-line version (object classes AND object
  components), not the 3-line classes-only version; the getters are used by
  `world_to_pixel`.
- Line-list layers (WP5) round-trip through sessions with the stock
  `LayerArtist.__gluestate__`; the audit critic's "needs its own saver" is
  superseded.
- WP2 converts moment maps to Angstrom itself and rewraps the raw (metres)
  WCS, so it does not depend on WP1's order; once WP5's `rest_wavelength()`
  helper exists, WP2 should call it instead of reading `TWAVE` directly.
- WP6 outputs carry `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`; WP3's
  `_GlueWCS` saver can therefore reach its `{"kind": "sliced"}` record.
  A bare outer `SlicedLowLevelWCS` is not covered by that saver.
- Moment maps autolink to their source on the fork glue only after WP1's
  coherence fix; on released glue 1.27.0 the two explicit pixel `LinkSame`
  links do the job either way.

## Dropped (with the reason)

- Log-file listing (no public data has `.log` files).
- `density_diagnostic` wrapper (needs fiasco and CHIANTI; arrays-in, dict-out).
- The `fitting` extra for dask (dask is an irispy hard dependency).
- The `join_on_key` nearest-value extension and any `JoinLink` (see above).
- glue-core work for velocity units, line lists, blink, sessions (D2); only
  the one-line bug fixes in WP0 go upstream.
- A Spectroheliogram preset (it is the default layout).
- Filename-pattern presets and date widgets in the browser (a text filter on
  the ISO start time covers dates).
- Loader "cube handle" prerequisite for moments (rewrap instead).
- `RegionData` for the FOV polygon (crashes with WCS coords; `PolygonalROI`
  subset instead).
- Rebasing glue PR #2248 (closed in favour of the restart).

## Explicit non-goals

- Level-3 FITS generation and EIS support (decided 2026-08-29, unchanged).
- OBS XML dependency resolution / `IRISsim_showXML`.
- Reimplementing the IDL widget layouts (detector mosaic chrome, per-raster
  panel grids, PostScript export paths).
- Per-scan absolute WCS inside the 4-D stack: deferred, not impossible. A gwcs
  model over the stacked `-TAB` tables reproduces every scan's own
  coordinates exactly in the forward direction; the missing piece is an
  inverse model for links and subsets. glue-core needs no change.
- Movie or sequence export (new, unlisted gap): not scheduled; open an issue
  if a workflow needs it.

## Environment and pitfalls that apply to every package (all verified)

- Python: `/Users/nabil/Git/glue-solar/.venv/bin/python` (3.14). The Bash tool
  in Claude Code runs a zsh-like shell even though the login shell is fish:
  quote glob arguments (`--include='*.py'`).
- Run every glue or Qt script with an isolated `HOME` (for example
  `HOME=/tmp/glue-home QT_QPA_PLATFORM=offscreen MPLBACKEND=agg`). A headless
  run of main-based glue-qt writes `font_size = 9.0` into
  `~/.glue/settings.cfg`, which the macOS branch then treats as a permanent
  9 pt override, and a persisted non-default `unit_converter` name makes
  `import glue` raise `KeyError`. Today the file reads `font_size = -1.0`,
  `unit_converter = "default"`; keep it so.
- `pytest` needs `-o addopts=''` in this venv (`pytest.ini` passes
  `--doctest-rst` but pytest-doctestplus is not installed), and
  `filterwarnings = error` is active, so new warnings fail tests.
- `ruff` is not installed in the venv or on PATH. Pre-commit pins: glue-solar
  0.16.1, glue 0.15.20, glue-qt 0.14.14; install a pinned copy with
  `pip install --target <dir> ruff==<version>` and run `<dir>/bin/ruff`.
- irispy 0.8.1 ships two files named
  `iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits`; only the
  `sns/` copy loads (the `raster/` copy fails with "Expected 187 NUV source
  filename rows, found 1872"). Select test files by parent directory, not by
  name alone. The test SJIs are stride-10 decimations, and every bundled
  raster window excludes its own line core (`TWAVE`), so tests must pass
  explicit rest wavelengths.
- Modal dialogs (`QMessageBox`, glue-qt's autolink preview on the fork glue)
  hang offscreen; tests monkeypatch them.
- `gh` is authenticated as nabobalis with admin on glue-viz/glue-solar but no
  triage access on glue-viz/glue and glue-viz/glue-qt: `--label` fails there;
  ask for the label in the PR body.
- `git config --global rerere.enabled` is true: a bad conflict resolution is
  replayed silently on the next identical cherry-pick. Disable it per repo
  before the WP0 splits.
- `glue/_version.py` is untracked and not ignored in `~/Git/glue`; glue-qt's
  `profile-wcs` branch even committed `glue_qt/_version.py`. Add files by
  name.
- glue-core 1.27.0 bugs that the packages work around (fix PRs in WP0):
  `_save_style` returns a `Colormap` object (JSON crash); `_save_data_5`
  catches only `GlueSerializeError` (Quantity meta crashes `np.save`);
  `world2pixel_single_axis` collapses uncorrelated world inputs to their first
  element (time frozen at frame 0); `datetime64_to_mpl` uses the pre-3.3
  matplotlib epoch (dates labelled in the year 3990); `RegionData` crashes on
  a Data with WCS coords.

---

# Part 2: implementation briefs



---

# WP0 - Ship the existing fork work upstream

**Published 2026-09-02 (added after execution).** Every branch below was
rebuilt in throwaway worktrees, re-verified, given concise commit messages
(trees unchanged, so the SHAs quoted in this brief and in the TODO files are
the pre-rewrite ones), pushed to the forks and opened as a DRAFT with a short
body (`IRIS_PLAN_PROTOTYPES/wp0/short/`; long drafts are directly in `wp0/`).
No reviews were requested; the user reviews each diff before marking it ready.

| Item | Where |
| --- | --- |
| APE-14 autolink (a) | glue-viz/glue#2595, branch `ape14-wcs-autolink` (tip bad24b99, force-pushed over 016d9cf2) |
| Profile piece C (b) | glue-viz/glue#2596, branch `profile-slice` |
| Profile piece A (b), stacked on C | glue-viz/glue#2601, branch `profile-wcsaxes` |
| glue-qt piece B (b) | glue-viz/glue-qt#70, branch `profile-wcs-pr` |
| glue-qt CI fixes (c) | glue-viz/glue-qt#69, branch `ci-fixes` |
| Session style/meta fix (d1) | glue-viz/glue#2597, branch `fix-session-style-meta` |
| world2pixel fix (d2) | glue-viz/glue#2598, branch `fix-world2pixel-correlated-axes` |
| datetime epoch fix (d3) | glue-viz/glue#2599, branch `fix-datetime-epoch` |
| RegionData issue (d4) | glue-viz/glue#2600 |
| glue PR #2248 | closed with a pointer to #2596 and #2601; `origin/1dprofile_wcs` deleted |

Completed: the #68 rewrite, push, body and draft update. The later CI-test
fix is now pushed at `macos-integration:0b16dd55`; the historical
`macos-integration-v2` alias remains at `4d93c64f`. Do not repeat the old
force-push/reset steps. Reviews on glue-solar #44
were deliberately not requested (user decision).

**Current goal.** Validate fresh CI for the published fixes, resolve the visual-reference differences, and let the user review each draft. Planning/prototype changes remain local. Do not request reviews on #44 automatically.

### Historical WP0 execution record — not an active checklist

The remaining WP0 instructions, unchecked boxes and terminal output record
the 2026-09-02 split/publication procedure. PRs now exist, #2248 is closed,
and the old branch was deleted. Use the current status above for next actions.
The old claim that the permission-test checkbox change was a no-op was wrong:
newer core skips unchanged saves, so the test must create a pending edit.

**Pre-publication state (2026-09-02, superseded).**
- glue fork `/Users/nabil/Git/glue`, main = upstream/main = dae530c3 (no drift; all branches have merge-base dae530c3). Untracked: `APE14_AUTOLINK_TODO.md`, `PROFILE_WCS_RESTART_TODO.md`, `glue/_version.py` (NOT gitignored on main; never `git add -A`).
  - `ape14-wcs-autolink` = b16a3703 + 016d9cf2 (pushed, origin identical). +574/-61 in `glue/plugins/wcs_autolinking/wcs_autolinking.py` and its tests. Pinned ruff 0.15.20 clean. Current ruff 0.16.5 adds 2 PLR0917 hits (`wcs_autolinking.py:82` get_cids_and_functions 6 positional args, `:148` transform 7) that main does not have. No upstream PR; glue-viz/glue#2152 still OPEN (2020).
  - `profile-wcs` = 175e7129 (C: 'slice' function) -> f767d320 (A: WCSAxes) -> 98d7bb7c (C fix: slice_view across links) -> c3bcd75b (A fix: x_limits_pixel). Pushed, origin identical. Pinned ruff 0.15.20 FAILS: 3 x RUF059 (`glue/viewers/profile/tests/test_state.py:229`, `:257`; `tests/test_viewer.py:336`), unsafe-fix only, so pre-commit.ci would go red. No upstream PR.
  - glue-viz/glue#2248 (`nabobalis:1dprofile_wcs`, 586d1948): OPEN draft, CONFLICTING, last commit 2022-05-07, 1 self-review, 1 comment. `origin/1dprofile_wcs` still exists.
- glue-qt fork `/Users/nabil/Git/glue-qt`, main = upstream/main = 9780eaf9. Checked out: `macos-integration` (bd4dce6b = PR #68 head). Untracked: `MACOS_INTEGRATION_TODO.md`.
  - `profile-wcs` = 1133c0e9 (pushed). Carries the generated file `glue_qt/_version.py` as a committed blob (`git ls-tree profile-wcs -- glue_qt/_version.py` -> 100644 blob 0b097aeb). main's `.gitignore` does not list it; only `macos-integration` adds the ignore line. Pinned ruff for glue-qt is **v0.14.14** (not 0.15.20; `.pre-commit-config.yaml:57` on main, profile-wcs and macos-integration): clean, also clean on 0.15.20.
  - #68 `macos-integration`: 4 commits d8a3f715 (the feature, 11 files), a34a2180 "remove tox all?!", b596af69 "try to fix some CI?!", bd4dce6b "maybe?!!!!". OPEN, MERGEABLE, no labels, no reviews, no comments, body says "WARNING: AI SLOP" and asks an unrelated Qt5/py<3.12 question. All required CI jobs green; pyside/windows allowed_failures red (same as main).
- glue-solar PR #44 (head d3a2bd3 == local HEAD): OPEN, MERGEABLE, all checks SUCCESS, reviews [], reviewRequests []. Repo collaborators: astrofrog, ChrisBeaumont, nabobalis, Carifio24.
- `gh api user` -> nabobalis (works). Checker re-run 17:35: `gh auth status` is clean ("Logged in to github.com account nabobalis (keyring)", scopes gist/read:org/repo/workflow); the writer saw "The token in keyring is invalid" earlier in the day. If a write command fails, `gh auth refresh -h github.com` first.
- nabobalis has NO push/triage access on glue-viz/glue and glue-viz/glue-qt (`gh api repos/glue-viz/glue/collaborators/nabobalis/permission` -> HTTP 403 "Must have push access"; glue-solar -> admin). Consequence: every `--label` below on those two repos will be rejected. Open the PRs WITHOUT `--label` and put "Label: enhancement" / "Label: bug" as the last line of the body so a maintainer applies it (release notes are label-driven). `gh pr close 2248`, `gh pr edit 68 --body-file`, and `git push` to the fork work without push access.
- `git config --global rerere.enabled` = true. A recorded resolution replays silently on the next identical conflict (I hit this today in the scratch clone: a broken resolution was re-applied). Run `git config rerere.enabled false` in the repo (or `git rerere clear`) before the cherry-picks below.

**Decisions already made.**
- D1: Phase 1.4 `link_hpc` stays permanently. The ape14 PR body and the TODO edits say "complementary", never "deletes Phase 1.4".
- D2: only work that already exists on the fork branches goes upstream here (3.1 autolink, profile-wcs C/A/B, #68) plus the tiny glue-core bug fixes in section (d). Nothing else upstream in WP0.
- D3: wavelength in Angstrom is WP1 (glue-solar `_GlueWCS`); it is only mentioned in PR A's body as the reason IRIS wavelength ticks currently read `0.00000013328`.
- Audit-settled: profile-wcs commit 98d7bb7c is intra-viewer per-layer slice translation, NOT Phase 3.2; the WCSAxes design rule is the TODO's own proposal (implemented as `_wcsaxes_with_unit`); apply_roi uses `x_att_pixel` only in WCSAxes mode (deliberate reinstatement); #2248 is closed, not rebased; the three "?!" commits of #68 are unrelated CI repairs; the `_checkboxes` tweak in bd4dce6b is a no-op; pyobjc stays a hard darwin-only dep; on macOS the menu/About/Quit names come from CFBundleName only (setApplicationName/DisplayName do nothing there); the glue-core RegionData crash is an issue, not a one-line PR.

**Dependencies / order.**
1. Independent, do first: (a) ape14 PR; (b1) PR C; (c) #68 split + rewrite; (d) tiny glue-core PRs; (e) #44 review request; (f) TODO edits. None of these depend on each other.
2. (b2) PR A is stacked on PR C (reads `slices`, `_set_default_slices`). Open it right after C with both commit sets; rebase when C merges.
3. (b3) glue-qt PR B after C and A exist (reference both). It is mergeable before they merge because everything is feature-gated (68 passed / 14 skipped on released glue-core today).
4. Close #2248 + delete `origin/1dprofile_wcs` any time after PR A is open (A's commit message documents the salvage).
5. Unblocks: WP1 (glue-solar `_GlueWCS` coherence fix + Angstrom) needs nothing from WP0 but its regression test for autolink waits for a glue release with the ape14 PR. glue-solar session savers (WP3.6) can drop their VisualAttributes v2 saver and meta filter once the state.py PR ships.

**Files to touch.**
- glue `glue/plugins/wcs_autolinking/wcs_autolinking.py`: make `forwards`/`backwards` of `get_cids_and_functions` and the four extras of `permuted_values_functions.transform` keyword-only (PLR0917). One commit on top of `ape14-wcs-autolink`.
- glue `glue/viewers/profile/tests/test_state.py:226,229,257`, `tests/test_viewer.py:336`: `x, y = ...` -> `_, y = ...` / `x, _ = ...` (RUF059). Fold into the C-fix and A commits respectively (or one fixup per branch).
- glue `glue/viewers/profile/python_export.py`: one conflict hunk when cherry-picking 98d7bb7c onto main+175e7129 and again when cherry-picking f767d320 onto the C branch (resolutions below).
- glue `glue/core/state.py:746` (`_save_style`) and `:1033` (`_save_data_5`), `glue/core/coordinate_helpers.py:104`, `glue/utils/matplotlib.py:449-485` + `glue/utils/tests/test_matplotlib.py:186`, `pyproject.toml:29` matplotlib floor: three tiny PRs (diffs in `$S/wp0_fix_state.diff`, `wp0_fix_w2p.diff`, `wp0_fix_epoch.diff`). NOTE (checker): neither `wp0_fix_epoch.diff` nor commit 41982f92 on `$S/gs-main` touches `pyproject.toml`; edit `"matplotlib>=3.2",` (line 29) to `"matplotlib>=3.3",` by hand in the epoch PR.
- glue-qt: new branch `ci-fixes` = a34a2180 + b596af69 + bd4dce6b minus the `test_plugin_manager.py` tweak, plus the `.gitignore` line from d8a3f715. New branch for #68 = d8a3f715 minus `.gitignore`, minus `setApplicationDisplayName('glue')` (`glue_qt/utils/app.py:82`), plus `test_mac_bundle_name` in `glue_qt/utils/tests/test_app.py`. `glue_qt/viewers/common/data_slice_widget.py:46` (0.75x) unchanged by default.
- glue-qt `profile-wcs`: recreate 1133c0e9 without `glue_qt/_version.py` (`git rm --cached`).
- glue-solar: nothing in code. `IRIS_GLUE_GAP_PLAN.md:10-17, 141-147, 194-195` (docs section). `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:57-59` stays until a glue release (WP1 notes it).
- `~/Git/glue/APE14_AUTOLINK_TODO.md`, `~/Git/glue/PROFILE_WCS_RESTART_TODO.md`, `~/Git/glue-qt/MACOS_INTEGRATION_TODO.md`: edits listed at the end.

**Step-by-step.**

(a) glue-core PR: APE-14 autolink.
1. `cd ~/Git/glue && git fetch upstream && git checkout ape14-wcs-autolink` (branch is on dae530c3 == upstream/main; no rebase needed today; re-check with `git merge-base --is-ancestor upstream/main HEAD`).
2. Apply the keyword-only change (exact patch in Verified code, "ape14 PLR0917"), commit as `Make forwards/backwards and transform options keyword-only`.
3. Lint with both pins: `pip install --target $S/ruff15 ruff==0.15.20; pip install --target $S/ruffpkg ruff==0.16.5; $S/ruff15/bin/ruff check glue/plugins/wcs_autolinking; $S/ruffpkg/bin/ruff check glue/plugins/wcs_autolinking` -> expect "All checks passed!" and only CPY001 (preview rule, also on main) respectively.
4. `PYTHONPATH=. python -m pytest glue/plugins/wcs_autolinking glue/core/tests/test_links.py glue/core/tests/test_link_helpers.py glue/core/tests/test_link_manager.py -q -rxX` -> 69 passed, 1 xfailed, 1 xpassed (the XPASS `test_2d_and_1d_data_cubes_with_no_celestial_axes` is a pre-existing non-strict xfail that also xpasses on 1.27.0).
5. `git push origin ape14-wcs-autolink`, then `gh pr create -R glue-viz/glue --head nabobalis:ape14-wcs-autolink --base main --title "Support APE-14 low-level WCS in WCSLink and wcs_autolink" --body-file $S/pr_ape14.md` (no `--label`: nabobalis cannot label on glue-viz/glue; the body ends with "Label: enhancement". CHANGES.md is generated from labels via `.github/release.yml`, categories enhancement / bug / documentation; no changelog file, no doc change: `doc/api.rst:195` automodapi and `__all__` at `wcs_autolinking.py:14` exclude the new helpers).
6. PR body (`$S/pr_ape14.md`):

```
Datasets whose `coords` only implement the low-level APE-14 API (a `BaseWCSWrapper` around gWCS or an astropy `-TAB` WCS, as glue-solar builds for IRIS data to present arcseconds - the "wrapper that preserves units" of #2152) never autolink today: `wcs_autolink` keeps only `BaseHighLevelWCS` coords (0 links, no message) and a direct `WCSLink(sji, raster)` dies with `AttributeError: '_GlueWCS' object has no attribute 'has_celestial'`.

Changes
- `wcs_autolink` accepts `BaseLowLevelWCS`; `WCSLink` wraps bare low-level coords in `HighLevelWCSWrapper` and works on `.low_level_wcs`.
- The celestial cross-frame special case (SkyCoord galactic<->equatorial) is guarded behind `isinstance(..., astropy.wcs.WCS)` for both datasets; everything else uses physical-type matching.
- Pixel axes kept per matched world axis come from `axis_correlation_matrix` (`kept_numpy_axes`) instead of assuming world axis i <-> pixel axis `world_n_dim - i - 1`, which APE 14 does not guarantee (wrong for `-TAB` celestial axes and gWCS). Pixel axes that also drive unmatched world axes are sliced away when every matched world axis stays supported (an SJI's time axis: the link is exact at exposure 0).
- Slice tuples are sized by `pixel_n_dim` (astropy silently pads short tuples); `slicing_axes1/2` were aliased to one list (IndexError for mixed-ndim pairs); ndim mismatch and untransformable pairs raise `IncompatibleWCS` and are skipped by the autolinker instead of tracebacking.
- Matched types in a different order on the two sides (SJI lon,lat vs raster lat,lon) are transformed through world values with an explicit type permutation and unit conversion (`permuted_values_functions`); `pixel_to_pixel` pairs plain Quantities positionally and would transpose them. The probe fast path is only taken when both coords natively implement the high-level API.

Verified on real IRIS Level 2 data (irispy test files): SJI 1400 (62,40,37) gWCS + raster (187,40,20) `-TAB`, both wrapped low-level: 1 `WCSLink` pairing SJI [x, y] with raster [slit, step]; sky positions from either WCS agree to 3e-7 arcsec; round trip raster (20,50) -> SJI (88.612, 20.662) -> raster (19.999999, 49.999999). 0 links on 1.27.0. (That raster is sit-and-stare, so its 187-long "step" axis is really an exposure index; the link pairs it to SJI x through the pointing drift at SJI exposure 0, which is what the WCS says, not a temporal join.)

Note for wrapper authors (the #2152 use case): pairs whose matched types are in the same order still transform through `HighLevelWCSWrapper` objects, so a wrapper that changes `world_axis_units` must keep `world_axis_object_classes` / `world_axis_object_components` coherent with the new units (otherwise SkyCoord construction fails and the pair is reported incompatible). Happy to switch every wrapped low-level pair to the values path if you prefer that over the coherence requirement.

Known, pre-existing, unchanged: sessions containing low-level coords cannot be saved (only `@saver(astropy.wcs.WCS)` exists); `clone(link)` on such data raises `GlueSerializeError` for the coords, not for the link.

Tests: 11 new (`test_wcs_autolink_low_level`, `_low_level_and_fits_wcs`, `_low_level_disjoint`, `_low_level_transform_failure`, `_correlated_axes`, `_low_level_disjoint_same_ndim`, `_low_level_world_order_permutation`, `_ndim_mismatch`, `_low_level_11d`, `_all_axes_coupled`, `_iris_like`) on synthetic `BaseLowLevelWCS` fixtures with settable types/units/correlation matrix; the 20 existing astropy-WCS tests are unchanged.

Refs #2152. Downstream: glue-viz/glue-solar#44.

Label: enhancement (I cannot set labels on this repo).
```

(b) profile-wcs: PR C, PR A, glue-qt PR B, #2248.
1. `cd ~/Git/glue && git config rerere.enabled false && git fetch upstream`.
2. PR C branch: `git checkout -b profile-slice upstream/main && git cherry-pick 175e7129 && git cherry-pick 98d7bb7c` -> one conflict in `glue/viewers/profile/python_export.py` (three-way hunk around line 44). Resolve to the C-only block (no `wcsaxes_active`):
```python
    script += "# Extract the values for the x-axis\n"
    script += "axis_view = [0] * layer_data.ndim\n"
    script += "axis_view[profile_axis] = slice(None)\n"
    # NOTE: x values come from base_data - indexing a Subset applies the
    # subset mask, which would give a different length than profile_values
    script += "profile_x_values = base_data['{0}', tuple(axis_view)]\n".format(layer._viewer_state.x_att)
    if layer._viewer_state.function == 'slice':
```
   `git add glue/viewers/profile/python_export.py && git cherry-pick --continue`. Then RUF059: in `glue/viewers/profile/tests/test_state.py` change lines 226, 229 and 257 from `x, y = layerN.profile` to `_, y = layerN.profile` (all three; fixing only 229/257 makes ruff flag 226 next). `git commit -am` (or `--amend` into the 98d7bb7c pick). Check: `grep -rn 'wcsaxes\|x_limits_pixel' glue/viewers/profile` -> nothing; `$S/ruff15/bin/ruff check glue/viewers/profile` -> clean; `PYTHONPATH=. pytest glue/viewers/profile -q` -> 36 passed, 1 skipped.
3. PR A branch: `git checkout -b profile-wcsaxes profile-slice && git cherry-pick f767d320` -> same file conflicts; resolve by taking the branch tip's file: `git show profile-wcs:glue/viewers/profile/python_export.py > glue/viewers/profile/python_export.py && git add glue/viewers/profile/python_export.py && git cherry-pick --continue && git cherry-pick c3bcd75b` (clean; c3bcd75b does not touch python_export.py). RUF059: `glue/viewers/profile/tests/test_viewer.py:336` `x, y = viewer.state.layers[0].profile` -> `x, _ = ...`. Check: `git diff profile-wcs` shows only the four RUF059 lines; ruff clean; `PYTHONPATH=. pytest glue/viewers/profile -q` -> 57 passed, 1 skipped.
4. `git push -u origin profile-slice profile-wcsaxes`.
5. `gh pr create -R glue-viz/glue --head nabobalis:profile-slice --base main --title "Add a 'slice' collapse function to the profile viewer" --body-file $S/pr_c.md` (no `--label`, see Current state):
```
Adds `'slice'` to the profile viewer collapse functions: instead of collapsing the other dimensions with a statistic, the profile shows the data along the profile axis at the point given by the new `ProfileViewerState.slices` property (defaults to zeros, mirrors `ImageViewerState.slices`; `_set_default_slices` runs on reference-data change). Subset layers show the slice with values outside the mask set to NaN, like the statistical functions. The `UnitConverter` path is shared, so display units apply.

For layers whose dataset is not the reference data, `ProfileLayerState.slice_view` translates the reference-frame slice point into that dataset's own pixel indices through the pixel/coordinate links (`ref[data.pixel_component_ids[axis], point]`), rounds and bounds-checks it, and raises `IncompatibleDataException` (layer disabled) for unlinked axes or out-of-range points. The python export emits the equivalent `get_data`/`get_mask` code, and now fetches x values from the parent data rather than the Subset (indexing a Subset applies the mask and could return fewer values than `profile_values`; this also fixes the latent mismatch in the statistic-function subset export).

Motivation: a single-pixel spectrum (what IRIS `iris_raster_browser` shows) is not expressible with a collapsed statistic. This is the first of two PRs restarting #2248; the second adds opt-in WCSAxes formatting. glue-qt sliders follow in a glue-qt PR.

Tests: `test_slice_function`, `test_slice_function_subset`, `test_slice_function_linked`, `test_slice_function_out_of_bounds`, `test_slice_function_1d` (test_state.py), `test_unit_conversion_slice` (test_viewer.py:177), `test_slice`/`test_slice_subset` (test_python_export.py).

Known limitation: `slices` out of range for the reference data itself raise IndexError from `Component.__getitem__` (the artist is hidden, not disabled); the Qt sliders are bounded so the UI cannot produce it.

Label: enhancement (I cannot set labels on this repo).
```
6. `gh pr create -R glue-viz/glue --head nabobalis:profile-wcsaxes --base main --title "Add opt-in WCSAxes support to the profile viewer" --body-file $S/pr_a.md` (no `--label`):
```
Stacked on #<C> (first two commits are that PR).

When a profile viewer is built with WCSAxes (`wcs=True`, the image viewer's mechanism) and world coordinates are shown on the x axis in their native unit, the axes are reset to the reference data's WCS sliced to 1D (`RectangularFrame1D`, `reset_wcs(slices=wcsaxes_slice, wcs=coords)`), so tick labels are formatted by the WCS (sexagesimal etc.).

Design rule (the open question from #2248, WCSAxes formatting vs `x_display_unit` competing for the same axis): `ProfileViewerState.wcsaxes_active` is true only when the viewer has WCSAxes AND reference coords are real (not None / LegacyCoordinates) AND `x_att` is a world component AND `(x_display_unit or '') == component native unit`. In that mode the profile, the x limits and ROIs are in pixel coordinates (WCSAxes draws world tick labels from pixel positions; same model as the image viewer), so `apply_roi` builds the subset on `x_att_pixel`. Any display-unit override, or data without real coords, falls back to an identity WCS and the existing plain-numeric/`x_display_unit` behaviour, unchanged. Crossing that boundary resets the x limits instead of converting them; `x_limits_pixel` records which kind a session saved so a session restored into a viewer in the other mode does not open blank.

Off by default: `SimpleProfileViewer` keeps plain axes unless `wcs=True`; glue-qt is unaffected until it passes `wcs=True` (glue-qt PR to follow, feature-gated). Python export emits `init_mpl(wcs=True)` / `reset_wcs` code; the whole export suite is re-run against a WCSAxes viewer (`TestExportPythonWCSAxes`). `update_x_ticklabel` uses `axes.coords[ndim - x_att_pixel.axis - 1].set_ticklabel` because `tick_params` is a no-op on a 1D-frame WCSAxes.

Salvaged from #2248 with its defects fixed: `reference_data is None` guard, slice indices read from `slices` instead of a hardcoded 0, no state mutation in property getters, coords index for ndim > 1, hidden y axis restored. #2248 is closed in favour of this.

Tests: `test_wcsaxes_profile`, `test_wcsaxes_identity_fallback`, `test_wcsaxes_slices`, `test_wcsaxes_limits_mode_mismatch`, `TestExportPythonWCSAxes`; units tests unchanged.

Label: enhancement (I cannot set labels on this repo).
```
7. glue-qt PR B: `cd ~/Git/glue-qt && git fetch upstream && git checkout -b profile-wcs-pr upstream/main && git cherry-pick 1133c0e9 && git rm --cached glue_qt/_version.py && git commit --amend --no-edit` (verify `git show --stat HEAD | grep _version` -> nothing; 8 files, +361/-69). Lint: `$S/ruff14/bin/ruff check $(git diff --name-only upstream/main | grep '\.py$')` (pin v0.14.14) -> clean. Tests: with released glue-core `QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=. pytest glue_qt/viewers/profile glue_qt/viewers/common -q -rs` -> 68 passed, 14 skipped (13 x "installed glue-core has no WCSAxes profile support" / "no slice collapse function" + 1 pre-existing); with `PYTHONPATH=~/Git/glue:.` (branch profile-wcsaxes checked out there) -> 81 passed, 1 skipped; `glue_qt/viewers/image` -> 69 passed, 2 skipped, 1 xfailed (slider helper refactor). `git push -u origin profile-wcs-pr` and:
   `gh pr create -R glue-viz/glue-qt --head nabobalis:profile-wcs-pr --base main --title "Profile viewer: slice sliders and WCSAxes wiring (gated on glue-core capabilities)" --body-file $S/pr_b.md` (no `--label`):
```
Wires up glue-viz/glue#<C> ('slice' collapse function + `slices` state) and glue-viz/glue#<A> (opt-in WCSAxes) in the Qt profile viewer.

- `MultiSliceWidgetHelper` (already shared in `glue_qt/viewers/common/slice_widget.py`) now works with any viewer state that has `x_att`/`slices`/`reference_data`: `y_att`/`z_att` callbacks and axis lookups are hasattr-guarded (ProfileViewerState has no `y_att`), `x_att_pixel` is used when `x_att` is a world component, stale sliders are cleared when data/attributes become None (they used to stay interactive and crash on drag), and syncing is skipped while `len(slices) != ndim` (the profile state's reference_data handler is a 2-arg echo callback and runs after this helper's 1-arg one; switching to a dataset of different ndim used to IndexError).
- The profile options widget gets the slice sliders, shown only when the collapse function is 'slice'.
- `ProfileViewer` passes `wcs=hasattr(ProfileViewerState, 'wcsaxes')` to `MatplotlibDataViewer`, so with a WCSAxes-capable glue-core the profile is drawn in pixel coordinates with WCS-formatted world tick labels, and `ProfileTools` range/navigation lookups follow the same rule (they also now convert to the display unit before the nearest-index search; on main they ignored `x_display_unit`, a pre-existing bug).

Gating: every new code path is behind `hasattr(ProfileViewerState, 'slices')` / `hasattr(ProfileViewerState, 'wcsaxes')`. Against released glue-core (1.27.0) behaviour is unchanged and the 13 tests that encode the new behaviour skip with an explicit reason (68 passed / 14 skipped); with the two glue-core PRs applied they run (81 passed / 1 skipped). The `-dev` tox environments install glue from git main, so CI exercises the new paths once the core PRs merge. The hasattr gates can become a version floor after the next glue-core release.

Label: enhancement (I cannot set labels on this repo).
```
8. Close #2248: `gh pr close 2248 -R glue-viz/glue --comment "Superseded by #<C> and #<A>: restarted off current main (the viewer code this branch touched moved to glue-qt in 2023 and the branch tip was internally broken). The salvageable parts (_set_wcs, wcsaxes_slice, update_x_ticklabel) are in #<A> with the defects fixed."` then `git -C ~/Git/glue push origin --delete 1dprofile_wcs`.

(c) glue-qt #68.
1. CI PR first (rehearsed, 0 conflicts): `cd ~/Git/glue-qt && git checkout -b ci-fixes upstream/main && git cherry-pick a34a2180 b596af69 bd4dce6b && git checkout upstream/main -- glue_qt/app/tests/test_plugin_manager.py && printf 'glue_qt/_version.py\n' >> .gitignore && git add .gitignore glue_qt/app/tests/test_plugin_manager.py && git commit -m "Fix CI: drop pytest-flake8 and the nonexistent all extra, close leaked viewers in tests, ignore generated _version.py"`; then `git rebase -i` is not available, so squash with `git reset --soft upstream/main && git commit -m "<same message>"`. Result: 4 files, +3/-6 (`.gitignore`, `glue_qt/viewers/common/tests/test_data_viewer.py` two `app.close()`, `pyproject.toml` -5 (pytest-flake8 + flake8-ignore), `tox.ini` -1). Verify `pytest glue_qt/viewers/common/tests/test_data_viewer.py glue_qt/viewers/image/tests/test_data_viewer.py::TestImageViewer::test_removed_subset` -> 19 passed (main: 1 failed, `assert 3 == 1`, leaked viewers). Push, `gh pr create -R glue-viz/glue-qt --head nabobalis:ci-fixes --base main --title "Fix CI: pytest-flake8 vs pytest 9, nonexistent 'all' extra, leaked viewers in tests"` (no `--label`; end the body with "Label: bug") with body: "First push of #68 failed every test job with `pluggy._manager.PluginValidationError: Plugin flake8 for hook pytest_collect_file` (pytest-flake8 1.3.0 vs pytest 9.1.1; ruff replaced flake8 already); after that `TestImageViewer::test_removed_subset` failed with `assert 3 == 1` because `test_viewer_title`/`test_viewer_title_tool` leak viewers (fixed with `app.close()`); tox's `all: all` extra does not exist in pyproject; `glue_qt/_version.py` is generated by setuptools-scm and was untracked but not ignored. Split out of #68 so main goes green on its own."
2. Rewrite #68 on top: `git checkout -b macos-integration-v2 ci-fixes && git cherry-pick d8a3f715` (applies cleanly: `ci-fixes` already carries the identical `glue_qt/_version.py` line, so git merges it, no duplicate). Verify: `git diff ci-fixes -- .gitignore` prints nothing; `git show --stat HEAD | tail -1` says 10 files (d8a3f715's 11 minus `.gitignore`); `git diff origin/macos-integration --stat` lists only `glue_qt/app/tests/test_plugin_manager.py | 2 --` (the dropped no-op tweak). Do NOT run `git checkout upstream/main -- .gitignore` (it stages a deletion of the line; the writer's scratch clone still has that staged by mistake).
3. Edit `glue_qt/utils/app.py`: delete the line `qapp.setApplicationDisplayName('glue')` (keep `QApplication(['glue'])` and `setApplicationName('glue')`). Reason: on macOS the menu title/About/Hide/Quit come from CFBundleName (qtbase `qcocoahelpers.mm` `qt_mac_applicationName` reads `CFBundleGetValueForInfoDictionaryKey(..., 'CFBundleName')` first), so the display name does nothing there; on Linux/Windows the QPA plugin appends the display name to native top-level window titles (`qplatformwindow.cpp:526-534 formatWindowTitle`, case-sensitive `endsWith`), so the main window title `Glue` (`application.py:1021-1026`) would render as `Glue - glue`. MDI viewer sub-windows are unaffected. Alternative if a maintainer wants the suffix: `setApplicationDisplayName('Glue')`.
4. Append `test_mac_bundle_name` to `glue_qt/utils/tests/test_app.py` (code in Verified code; add `import platform` and `import pytest` to the existing imports; 3 passed today, ruff 0.14.14 clean; the same test FAILS on glue-qt main with `assert 'Python' == 'glue'`, so it guards the fix). The TODO's "automated test can only assert applicationName()" is wrong; CFBundleName is headless-testable.
5. `git push -f origin macos-integration-v2:macos-integration` (force-push the rewritten branch onto the PR branch so #68 keeps its number). Note in the PR that it is based on the CI PR until that merges.
6. `gh pr edit 68 -R glue-viz/glue-qt --body-file $S/pr_68.md` (`--add-label` is rejected without triage access; the body asks for the label):
```
On macOS the menu bar showed "python" instead of "glue", and in-app text was noticeably smaller than the system UI (screenshot below). This PR:

- Renames the process for Cocoa: `CFBundleName` of the running Python framework bundle is set to `glue` through pyobjc before the `QApplication` exists (the native menu is built at app init). Qt takes the menu title and the About/Hide/Quit labels from `CFBundleName` (`qt_mac_applicationName`), so this is the whole macOS fix; `QApplication(['glue'])` + `setApplicationName('glue')` are kept for argv/QSettings hygiene. New dependency `pyobjc-framework-Cocoa; sys_platform == 'darwin'` (10 MB, 0.04 s import); without it (e.g. conda-forge until the feedstock adds it) the code falls back silently to today's behaviour. Test: `test_mac_bundle_name` asserts the bundle name after `get_qapp()` (skips off macOS).
- Uses the platform default font everywhere: the old `__get_font_size_offset` subtracted 2 pt on macOS and 1 pt elsewhere. **Effect on Linux/Windows: in-app text grows by 1 pt.** `FONT_SIZE = -1` now means "track the platform default" and is not persisted; a saved value equal to the current default is migrated to -1 once; preferences show the effective size.
- Removes hardcoded sizes: status bar `font-size:10px`, link-editor labels `setPointSize(10)`; the Qt5-only tab-title workaround now writes `pt` (was `px`) and is skipped on Qt6, which propagates the app font natively.
- Toolbar/list icon sizes follow `style().pixelMetric(PM_ToolBarIconSize)` capped at 24 px instead of fixed 12-16 px.

Not changed: `data_slice_widget.py` keeps its 0.75x label font (checked visually on macOS, still readable).
Side effect: `setApplicationName('glue')` moves the default `QSettings` file on macOS from `org.python.python.Python.plist` to `org.python.python.glue.plist`; glue-qt has no direct `QSettings` use (grep), and glue-solar passes an explicit org/app, so nothing is lost.
Not covered here: the CI repairs are in #<ci-fixes>. Question about dropping Qt5 / Python < 3.12 moved to #<discussion or issue>.

Label: enhancement (I cannot set labels on this repo).

Before / after screenshots: (keep the two existing images)
```
7. Manual pass on a real macOS session before pinging maintainers (cannot be automated): first set `font_size = -1.0` in `~/.glue/settings.cfg` (today it is -1.0; any headless run of main-based glue_qt rewrites it to 9.0, which the branch treats as a permanent 9 pt override since 9 != 13); then check menu title, About, Quit, Cmd-Tab, Dock name; open Preferences, Link Editor, data importers for clipping; look at a slice slider label (0.75x). Decision on the 0.75x font: default keep (no code change, no new dependency on taste); delete `data_slice_widget.py:44-47` only if the label is unreadable at 13 pt, and say which in the PR body.
8. conda-forge follow-up after the glue-qt release containing this: `gh issue create -R conda-forge/glue-qt-feedstock --title "Add pyobjc-framework-cocoa run dependency on osx (glue-qt >= <version>)" --body "glue-viz/glue-qt#68 sets the Cocoa CFBundleName so the menu bar reads 'glue' instead of 'python'; it needs \`pyobjc-framework-cocoa  # [osx]\` in recipe/meta.yaml run requirements (pyproject: pyobjc-framework-Cocoa; sys_platform == 'darwin'). Without it the import fails silently and conda users see no change."` (recipe today: `python.app [osx]`, `pyqt`, no pyobjc).

(d) Tiny glue-core PRs (all verified today; diffs saved in the scratchpad).
1. `state.py`: PR "Serialize preferred_cmap by name and skip any unserializable meta value" (`$S/wp0_fix_state.diff`, 2 hunks). Body: repro 1 (any `Data` whose `style.preferred_cmap` is a Colormap object -> `TypeError: Object of type ListedColormap is not JSON serializable`; `_load_style` removes `preferred_cmap` anyway so saving the name loses nothing) and repro 2 (`data.meta['exposure time'] = 4 * u.s` -> `TypeError: no implementation found for 'numpy.save'` because a Quantity reaches `@saver(np.ndarray)`; `_save_data_5` only catches `GlueSerializeError`). Tests: 171 passed in `glue/core/tests/test_state.py glue/utils/tests/...` today; add `test_save_style_colormap_object` (save a Data with `style.preferred_cmap = matplotlib.colormaps['viridis']`, assert dumps works and the rec has `'viridis'`) and `test_save_meta_quantity` (meta with a Quantity is dropped, other keys kept) in `glue/core/tests/test_state.py`. Label bug.
2. `coordinate_helpers.py`: PR "world2pixel_single_axis: keep world inputs that share a pixel axis with the requested one" (`$S/wp0_fix_w2p.diff`, 5 lines). Body: `world_dep = axis_correlation_matrix[:, pixel_axis]` collapses every world input whose row is 0 to `.flat[0]`, but inverting pixel axis x of a cube whose celestial axes depend on (x, y, t) needs the time world value per element; today the derived x uses t of the first element. Synthetic repro below (direct `world_to_pixel_values` gives x = [5, 5, 5], glue gives [5, 15, 25]); on a real IRIS SJI gWCS the derived pixel x for frames 0/30/61 is [21.05, 144.96, 275.06] vs direct [21.05, 20.62, 21.24]. Test: add the `W` class from the repro to `glue/core/tests/test_coordinate_links.py` (or `test_coordinates.py`) and assert `world2pixel_single_axis(w, lon, t, pixel_axis=0) == [5, 5, 5]`. Existing: `test_component_link.py`, `test_coordinate_links.py`, `test_coordinates.py`, `test_data_region.py`, `test_state.py` -> 247 passed today. Label bug. No upstream issue exists (gh search: axis_correlation_matrix / world2pixel_single_axis -> none).
3. `utils/matplotlib.py`: PR "Use matplotlib's date epoch in datetime64 <-> mpl conversions" (`$S/wp0_fix_epoch.diff`). Body: `datetime64_to_mpl` counts days from 0001-01-01 (+1), matplotlib >= 3.3 counts from a configurable epoch (default 1970-01-01), and glue never calls `set_epoch`, so every datetime axis is mislabeled: `mdates.num2date(datetime64_to_mpl(2021-09-05T00:18:47)) = 3990-09-06`, and a `SimpleScatterViewer` with a datetime x_att shows ticks `06 00:20` for 2021-09-05 data. Fix: `_t0()` = `np.datetime64(dates.get_epoch())` in both directions, drop the +1/-1 day. Bump `matplotlib>=3.2` to `>=3.3` in `pyproject.toml:29` by hand (`get_epoch` exists since 3.3, released 2020); this hunk is NOT in `$S/wp0_fix_epoch.diff` / commit 41982f92. Test: `test_mpl_datetime64` updated (old value 719313 encoded the old epoch; with the new epoch it is year 3939 and overflows ns) to round-trip 18875.5 and assert `datetime64_to_mpl(dt) == mdates.date2num(dt)`. Label bug. No upstream issue (gh search "datetime epoch", "date2num": none).
4. RegionData with WCS coords: file an ISSUE, not a PR: `gh issue create -R glue-viz/glue --title "RegionData overlay crashes when the image Data has WCS coords" --body-file $S/issue_region.md` with the repro below (`AttributeError: 'tuple' object has no attribute 'shape'` at `coordinate_helpers.py:42` via `data_region.py:219`; `coords=None` renders). Note in the issue that `np.asarray` on the inputs of `conv_function` stops the crash but the layer then disables itself with "depends on attributes that cannot be derived", so the transform chain (center -> pixel LinkSame -> world coordinate link) needs a real look; issue #2464 (closed, "X and Y problems with ScatterRegions") is a different ScatterRegion x/y problem, not this crash. Cross-reference from the glue-solar FOV-overlay work (uses PolygonalROI subsets instead).
5. glue-solar keeps its workarounds until these ship in a release: VisualAttributes v2 saver + meta filter (WP3.6), `world2pixel_single_axis` wrap only if/when a synthesised time link exists (WP3.2), nothing for the epoch bug until P1.5 GOES plots exist (then `matplotlib.rcParams['date.epoch'] = '0000-12-31T00:00:00'` is the one-line stopgap).

(e) glue-solar #44: `gh pr edit 44 -R glue-viz/glue-solar --add-reviewer astrofrog,Carifio24` (both merged the last 15 glue-core PRs; ChrisBeaumont is inactive). Optionally a one-line comment: "Ready for review; glue-core follow-ups for autolinking are in glue-viz/glue#<ape14>." Do not add the untracked planning docs to #44.

(f) TODO file edits: see the last section.

**Verified code.** All runs today, HOME isolated (`HOME=$S/home-wp0`), `$S` = the scratchpad, venv python 3.14, glue-core 1.27.0 site-packages unless `PYTHONPATH` says otherwise. Throwaway worktrees/clones: `$S/wt-wp0-*` (user repos, removed at the end), `$S/glue-split` and `$S/glueqt-split` (clones).

Pinned ruff on every branch:
```
$ $S/ruff15/bin/ruff --version; $S/ruff14/bin/ruff --version; $S/ruffpkg/bin/ruff --version
ruff 0.15.20 / ruff 0.14.14 / ruff 0.16.5
$ cd $S/wt-wp0-ape14 && $S/ruff15/bin/ruff check --no-fix glue/plugins/wcs_autolinking/wcs_autolinking.py glue/plugins/wcs_autolinking/tests/test_wcs_autolinking.py
All checks passed!
$ $S/ruffpkg/bin/ruff check --no-fix <same files>          # ruff 0.16.5
CPY001 ... (x2, also on main)
PLR0917 Too many positional arguments (6 > 5)  --> glue/plugins/wcs_autolinking/wcs_autolinking.py:82:5   def get_cids_and_functions(wcs1, wcs2, pixel_cids1, pixel_cids2, forwards=None, backwards=None)
PLR0917 Too many positional arguments (7 > 5)  --> glue/plugins/wcs_autolinking/wcs_autolinking.py:148:9  def transform(wcs_in, wcs_out, types_in, units_in, types_out, units_out, pixel_input)
Found 4 errors.
$ cd $S/wt-wp0-pw && $S/ruff15/bin/ruff check --no-fix $(git diff --name-only main...profile-wcs)
RUF059 Unpacked variable `x` is never used --> glue/viewers/profile/tests/test_state.py:229:5   x, y = layer2.profile
RUF059 Unpacked variable `x` is never used --> glue/viewers/profile/tests/test_state.py:257:5   x, y = layer1.profile
RUF059 Unpacked variable `y` is never used --> glue/viewers/profile/tests/test_viewer.py:336:8  x, y = viewer.state.layers[0].profile
Found 3 errors.  No fixes available (3 hidden fixes can be enabled with the `--unsafe-fixes` option).
$ cd $S/wt-wp0-qtpw && $S/ruff14/bin/ruff check --no-fix $(git diff --name-only main...profile-wcs | grep '\.py$')
All checks passed!
$ cd $S/wt-wp0-qtmac && $S/ruff14/bin/ruff check --no-fix $(git diff --name-only main...macos-integration | grep '\.py$')
All checks passed!
```

ape14 PLR0917 keyword-only patch (applied in the scratch clone, branch `ape14-kw`):
```
$ git diff HEAD~1 -- glue/plugins/wcs_autolinking/wcs_autolinking.py
-def get_cids_and_functions(wcs1, wcs2, pixel_cids1, pixel_cids2,
+def get_cids_and_functions(wcs1, wcs2, pixel_cids1, pixel_cids2, *,
                            forwards=None, backwards=None):
-    def transform(wcs_in, wcs_out, types_in, units_in, types_out, units_out, pixel_input):
+    def transform(wcs_in, wcs_out, pixel_input, *, types_in, units_in, types_out, units_out):
     def forwards(*pixel_input):
-        return transform(wcs1, wcs2, types1, units1, types2, units2, pixel_input)
+        return transform(wcs1, wcs2, pixel_input, types_in=types1, units_in=units1,
+                         types_out=types2, units_out=units2)
     def backwards(*pixel_input):
-        return transform(wcs2, wcs1, types2, units2, types1, units1, pixel_input)
+        return transform(wcs2, wcs1, pixel_input, types_in=types2, units_in=units2,
+                         types_out=types1, units_out=units1)
$ $S/ruffpkg/bin/ruff check --no-fix glue/plugins/wcs_autolinking/ | grep -v CPY001   -> Found 4 errors (all CPY001, baseline)
$ $S/ruff15/bin/ruff check --no-fix glue/plugins/wcs_autolinking/                    -> All checks passed!
$ PYTHONPATH=$S/gs-ape python -m pytest glue/plugins/wcs_autolinking glue/core/tests/test_links.py glue/core/tests/test_link_helpers.py glue/core/tests/test_link_manager.py -q -rxX
XPASS glue/plugins/wcs_autolinking/tests/test_wcs_autolinking.py::test_2d_and_1d_data_cubes_with_no_celestial_axes
69 passed, 1 xfailed, 1 xpassed, 11 warnings in 0.47s
```
(Three call sites on the branch: `wcs_autolinking.py:219` and `:318` pass only the four positional arguments; `:311` passes `forwards=`/`backwards=` by keyword. None passes them positionally, so the change is API-safe.)

IRIS autolink, installed 1.27.0 vs branch (`$S/sv2_ape14c.py`, irispy test SJI_1400 + raster Mg II k):
```
$ python sv2_ape14c.py                                   # glue 1.27.0
IndexError: list index out of range        # wcs_autolink(dc) returned []
$ PYTHONPATH=$S/wt-wp0-ape14 python sv2_ape14c.py       # branch
SJI px (x=29,y=20) -> raster (step=5.79, slit=19.29); world SJI=(-51.552,-399.681) raster=(-51.552,-399.681) arcsec; max diff 3.27e-07
reverse direction finite fraction: 1.0 sample raster[90,20,0] -> sji (x,y)= 143.77386559622255 20.40106750783438
```

Profile-wcs split (scratch clone `$S/glue-split`, rerere disabled):
```
$ git checkout -b profile-slice origin/main && git cherry-pick 175e7129 && git cherry-pick 98d7bb7c
CONFLICT (content): Merge conflict in glue/viewers/profile/python_export.py
# resolved to the C-only block shown in step (b)2; then the three test_state.py lines -> `_, y = ...`
$ $S/ruff15/bin/ruff check --no-fix glue/viewers/profile        -> All checks passed!
$ grep -rn 'wcsaxes\|x_limits_pixel' glue/viewers/profile/*.py glue/viewers/profile/tests/*.py | wc -l   -> 0
$ PYTHONPATH=$S/gs-c python -m pytest glue/viewers/profile -q     -> 36 passed, 1 skipped, 5 warnings in 35.89s
$ git checkout -b profile-wcsaxes profile-slice && git cherry-pick f767d320
CONFLICT (content): Merge conflict in glue/viewers/profile/python_export.py
$ git show origin/profile-wcs:glue/viewers/profile/python_export.py > glue/viewers/profile/python_export.py && git add ... && git cherry-pick --continue && git cherry-pick c3bcd75b
# then test_viewer.py:336 -> `x, _ = ...`
$ $S/ruff15/bin/ruff check --no-fix glue/viewers/profile        -> All checks passed!
$ git diff origin/profile-wcs --stat
 glue/viewers/profile/tests/test_state.py  | 6 +++---
 glue/viewers/profile/tests/test_viewer.py | 2 +-      # only the four RUF059 lines
$ PYTHONPATH=$S/glue-split python -m pytest glue/viewers/profile -q   -> 57 passed, 1 skipped, 6 warnings in 74.85s
```
Pitfall reproduced: fixing only lines 229 and 257 leaves ruff reporting `test_state.py:226:5 RUF059 x, y = layer1.profile`; fix all three.

glue-qt B (worktree of `profile-wcs` at 1133c0e9):
```
$ git ls-tree profile-wcs -- glue_qt/_version.py   -> 100644 blob 0b097aebe2c67b70f393c8dbbd0f19b6752021ac  glue_qt/_version.py
$ git show main:.gitignore | grep -c _version       -> 0        (macos-integration:.gitignore:47 has it)
$ PYTHONPATH=$S/glue-split:$S/wt-wp0-qtpw python -m pytest glue_qt/viewers/profile glue_qt/viewers/common -q     -> 81 passed, 1 skipped, 12 warnings in 16.89s
$ PYTHONPATH=$S/wt-wp0-qtpw python -m pytest glue_qt/viewers/profile glue_qt/viewers/common -q -rs             -> 68 passed, 14 skipped, 8 warnings in 9.59s
$ grep -c 'installed glue-core has no' $S/wp0_t_qt_inst.log   -> 13
```

#68 (worktree of `macos-integration`; `$S/chk_branch.py`):
```
$ HOME=$S/home-wp0 QT_QPA_PLATFORM=offscreen PYTHONPATH=$S/wt-wp0-qtmac python chk_branch.py
bundle /opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/Resources/Python.app
CFBundleName before Python __NSDictionaryM
CFBundleName after glue
applicationName glue | displayName glue | argv ['glue']
style fusion PM_ToolBarIconSize 24
default_font_size 9 qapp font pt 9
settings.FONT_SIZE after -1.0        # no settings.cfg written in the isolated HOME
```
Test appended to `glue_qt/utils/tests/test_app.py` (needs `import platform` / `import pytest` at the top):
```python
def test_mac_bundle_name():
    # The macOS menu-bar title and the About/Hide/Quit labels come from the
    # main bundle's CFBundleName (Qt reads it in qt_mac_applicationName),
    # which get_qapp rewrites through pyobjc before creating the QApplication.
    if platform.system() != 'Darwin':
        pytest.skip('macOS only')
    NSBundle = pytest.importorskip('Foundation').NSBundle
    app.get_qapp()
    bundle = NSBundle.mainBundle()
    info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    assert info['CFBundleName'] == 'glue'
```
```
$ HOME=$S/home-wp0 QT_QPA_PLATFORM=offscreen python -m pytest glue_qt/utils/tests/test_app.py -q   -> 3 passed in 0.01s
$ $S/ruff14/bin/ruff check --no-fix glue_qt/utils/tests/test_app.py                                 -> All checks passed!
```
CI split rehearsal (scratch clone `$S/glueqt-split`):
```
$ git checkout -b ci-fixes origin/main && git cherry-pick a34a2180 b596af69 bd4dce6b        -> 0 conflicts
$ git checkout origin/main -- glue_qt/app/tests/test_plugin_manager.py; printf 'glue_qt/_version.py\n' >> .gitignore; git commit -a
$ git diff --stat origin/main...HEAD
 .gitignore | 1 +   glue_qt/viewers/common/tests/test_data_viewer.py | 2 ++   pyproject.toml | 5 -----   tox.ini | 1 -
$ git checkout -b macos-only ci-fixes && git cherry-pick d8a3f715                             -> 0 conflicts
$ git diff origin/macos-integration --stat   -> .gitignore | 1 -   glue_qt/app/tests/test_plugin_manager.py | 2 --   (nothing else)
$ pytest glue_qt/viewers/common/tests/test_data_viewer.py glue_qt/viewers/image/tests/test_data_viewer.py::TestImageViewer::test_removed_subset
origin/main worktree: 1 failed, 18 passed        ci-fixes: 19 passed
```
Qt source for the menu claim, fetched 17:45: `curl 'https://code.qt.io/cgit/qt/qtbase.git/plain/src/plugins/platforms/cocoa/qcocoahelpers.mm?h=6.8'` lines 184-190: `QString qt_mac_applicationName() { ... CFTypeRef string = CFBundleGetValueForInfoDictionaryKey(CFBundleGetMainBundle(), CFSTR("CFBundleName")); if (string) appName = QString::fromCFString(...); if (appName.isEmpty()) { QString arg0 = QGuiApplicationPrivate::instance()->appName(); ...`. Qt source for the title claim (`$S/qplatformwindow.cpp:526-534`): `if (QGuiApplicationPrivate::displayName && !title.endsWith(*QGuiApplicationPrivate::displayName)) { ... fullTitle += separator; fullTitle += *displayName; }`; `glue_qt/app/application.py:1021-1026` sets the main window title to `"Glue"`. `QString::endsWith` is case-sensitive by default, so `Glue` gets the ` - glue` suffix on xcb/windows; cocoa never calls `formatWindowTitle`.

Tiny glue-core bugs, repro before / after the fix (`PYTHONPATH=$S/gs-main` = upstream main + the three fix commits 6760b00e, 916c8946, 41982f92):
```
$ cat wp0_bug_cmap.py  (core)
d = Data(x=[1, 2, 3], label='d'); d.style.preferred_cmap = matplotlib.colormaps['viridis']
GlueSerializer(DataCollection([d])).dumps()
1.27.0:   save FAILS: TypeError Object of type ListedColormap is not JSON serializable
fixed:    save OK
$ cat wp0_bug_meta.py  (core)
d.meta['exposure time'] = 4 * u.s; GlueSerializer(DataCollection([d])).dumps()
1.27.0:   save FAILS: TypeError no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.quantity.Quantity'>]
fixed:    save OK ; object() value: saved 1418 bytes (filtered)
$ cat wp0_bug_w2p.py
class W(BaseLowLevelWCS):      # pixel (x, t); world lon = x + 10*t, time = t; matrix [[1,1],[0,1]]
lon = [5., 15., 25.]; t = [0., 1., 2.]
direct world_to_pixel x:   [5. 5. 5.]
1.27.0 world2pixel_single_axis x: [ 5. 15. 25.]
fixed  world2pixel_single_axis x: [5. 5. 5.]
$ python slit_workaround.py (real SNS SJI 1400 gWCS, lon/lat/time LinkSame, derived SJI pixel x mid-slit, frames 0/30/61)
1.27.0: [21.05, 144.96, 275.06] (direct gWCS: 21.05 / 20.62 / 21.24)
fixed:  [21.05, 20.62, 21.24]
$ cat wp0_bug_epoch.py ; wp0_bug_epoch_viewer.py (SimpleScatterViewer, x_att datetime64)
1.27.0: matplotlib 3.11.1 epoch 1970-01-01T00:00:00 ; glue datetime64_to_mpl -> [738038.01] -> num2date: 3990-09-06T00:18:47 ; matplotlib date2num -> [18875.01]
        x tick labels: ['06 00:20', '06 00:30', '06 00:40', '06 00:50'] ; xlim as dates: ['3990-09-06', '3990-09-06']
fixed:  glue datetime64_to_mpl -> [18875.01304398] -> num2date: 2021-09-05T00:18:47 ; x tick labels: ['05 00:20', ...] ; xlim as dates: ['2021-09-05', '2021-09-05']
$ cat wp0_bug_region.py  (core, SimpleImageViewer, Data with 2D HPLN/HPLT astropy WCS, RegionData polygon, centers LinkSame'd to the pixel cids)
coords=WCS:      v.add_data(reg) -> AttributeError: 'tuple' object has no attribute 'shape'
                 data_region.py:219 conv_function -> component_link.py:393 using -> coordinate_helpers.py:42 pixel2world_single_axis
NOCOORDS=1:      draw OK, layers [('ImageLayerArtist', True), ('ScatterRegionLayerArtist', True)]
np.asarray patch in conv_function: draw OK but ScatterRegionLayerArtist enabled=False, disabled_message 'depends on attributes that cannot be derived ... linked with: img'   # not a one-liner -> issue
```
Fix diffs (as committed on `$S/gs-main`, branch core-fixes; `$S/wp0_fix_*.diff`):
```
--- a/glue/core/state.py
 def _save_style(style, context):
-    return dict((a, getattr(style, a)) for a in style._atts)
+    result = dict((a, getattr(style, a)) for a in style._atts)
+    # preferred_cmap may be a Colormap object, which is not JSON-serializable
+    # (and is never restored by _load_style) - store its name instead
+    if 'preferred_cmap' in result:
+        result['preferred_cmap'] = getattr(result['preferred_cmap'], 'name', result['preferred_cmap'])
+    return result
@@ def _save_data_5
-        except GlueSerializeError:
+        except Exception:  # noqa: BLE001 - e.g. np.save TypeError on Quantity values   (BLE001 is already ignored repo-wide; the noqa is optional)
--- a/glue/core/coordinate_helpers.py   (world2pixel_single_axis)
-    world_dep = wcs.axis_correlation_matrix[:, pixel_axis]
+    matrix = wcs.axis_correlation_matrix
+    world_dep = matrix[:, pixel_axis].copy()
+    # Also keep world axes that share a pixel axis with those: they are
+    # needed to invert the requested pixel axis (e.g. the time axis of a
+    # cube whose celestial axes depend on time) - transitive closure
+    for _ in range(matrix.shape[0]):
+        world_dep |= (matrix & matrix[world_dep].any(axis=0)).any(axis=1)
--- a/glue/utils/matplotlib.py
-T0 = np.datetime64('0001-01-01T00:00:00').astype('datetime64[s]')
+def _t0():
+    # matplotlib >= 3.3 counts days from a configurable epoch (1970-01-01 by
+    # default) rather than from 0001-01-01 (+1 day); follow it so that the
+    # date locators/formatters label glue's datetime64 axes correctly
+    return np.datetime64(dates.get_epoch()).astype('datetime64[s]')
 (datetime64_to_mpl)   - T0 -> - _t0();   dt = dt / SEC_PER_DAY + 1.0  ->  dt = dt / SEC_PER_DAY
 (mpl_to_datetime64)   dt = (dt - 1.0) * SEC_PER_DAY -> dt = dt * SEC_PER_DAY;   T0.astype(np.int64) -> _t0().astype(np.int64)
--- a/glue/utils/tests/test_matplotlib.py  (test_mpl_datetime64)
-    mpl1 = 719313
+    mpl1 = 18875.5
     mpl2 = datetime64_to_mpl(mpl_to_datetime64(mpl1)); assert mpl1 == mpl2
+    dt = np.array(['2021-09-05T12:00:00'], dtype='datetime64[s]')
+    assert_allclose(datetime64_to_mpl(dt), mdates.date2num(dt))
+    assert mpl_to_datetime64(mdates.date2num(dt)) == dt
```
```
$ PYTHONPATH=$S/gs-main python -m pytest glue/core/tests/test_state.py glue/core/tests/test_component_link.py glue/core/tests/test_coordinate_links.py glue/core/tests/test_coordinates.py glue/core/tests/test_data_region.py glue/utils/tests/test_matplotlib.py glue/utils/tests/test_array.py -q
(before the test update) 1 failed, 247 passed, 1 skipped   # test_mpl_datetime64: OverflowError, 719313 days from 1970 = year 3939 overflows ns
(after)  glue/utils/tests/test_matplotlib.py glue/utils/tests/test_array.py glue/core/tests/test_state.py -> 171 passed, 1 skipped
$ $S/ruff15/bin/ruff check --no-fix glue/core/state.py glue/core/coordinate_helpers.py glue/utils/matplotlib.py glue/utils/tests/test_matplotlib.py -> All checks passed!
```

Checker re-run (2026-09-02 17:20-17:50, fresh worktrees `$S/wt-chk-*` from the scratch clones, `HOME=$S/home-chk0`, all removed afterwards). Every number above reproduced; only deltas are noted.
```
$ ruff (pinned per repo) on the untouched branch tips
  ape14 (016d9cf2)  0.15.20: All checks passed!   0.16.5: CPY001 x2 (also on main) + PLR0917 wcs_autolinking.py:82:5 (6 > 5), :148:9 (7 > 5)
  profile-wcs (c3bcd75b) 0.15.20: RUF059 test_state.py:229:5, :257:5, test_viewer.py:336:8 (No fixes available, 3 hidden unsafe fixes)
  glue-qt profile-wcs (1133c0e9) 0.14.14 and 0.15.20: All checks passed!    glue-qt macos-integration (bd4dce6b) 0.14.14: All checks passed!
  gs-ape (ape14 + keyword-only ffc62fdc) 0.15.20: All checks passed!; 0.16.5: only CPY001 x4
  gs-main (core-fixes) 0.15.20 on the 4 changed files: All checks passed!
$ RUF059 cascade (wt-chk-pw, sed 229/257 -> `_, y`): ruff 0.15.20 -> test_state.py:226:5 RUF059 Unpacked variable `x` is never used; Found 1 error.   (reverted)
$ pytest (chk_run_tests.sh; logs $S/chk_t_*.log)
  gs-ape  wcs_autolinking + test_links/test_link_helpers/test_link_manager: 69 passed, 1 xfailed, 1 xpassed (XPASS test_2d_and_1d_data_cubes_with_no_celestial_axes)
  gs-c    glue/viewers/profile: 36 passed, 1 skipped (34 s)        glue-split (profile-wcsaxes): 57 passed, 1 skipped (75 s)
  glue-qt profile-wcs + glue-split core: glue_qt/viewers/profile + common: 81 passed, 1 skipped;  glue_qt/viewers/image: 69 passed, 2 skipped, 1 xfailed
  glue-qt profile-wcs + released 1.27.0: 68 passed, 14 skipped (13 x "installed glue-core has no WCSAxes profile support" / "no slice collapse function", 1 unconditional test_data_viewer.py:60)
  glue-qt main (9780eaf9) common/test_data_viewer.py + image TestImageViewer::test_removed_subset: 1 failed (assert 3 == 1), 18 passed;  ci-fixes: 19 passed
  gs-main core-fixes, 7 test files incl. updated test_mpl_datetime64: 248 passed, 1 skipped
$ split rehearsal from origin/main with `git config rerere.enabled false` (wt-chk-split)
  cherry-pick 175e7129: clean (6 files, +127/-6);  cherry-pick 98d7bb7c: CONFLICT python_export.py, diff3 hunk lines 44-64 (HEAD = `layer_data[...]` one-liner; theirs = wcsaxes_active block + base_data)
  resolved with the C-only block (copied from $S/gs-c) -> `git diff profile-slice --stat` = test_state.py | 6 +++--- (the three RUF059 lines only)
  cherry-pick f767d320 on top: CONFLICT python_export.py; `git show origin/profile-wcs:glue/viewers/profile/python_export.py > ...`; cherry-pick c3bcd75b: clean (c3bcd75b does not touch python_export.py)
  `git diff origin/profile-wcs --stat` -> empty;  `git diff profile-wcsaxes --stat` -> 2 files, 4 insertions, 4 deletions (the four RUF059 lines)
$ glueqt-split: `git diff --stat origin/main...ci-fixes` = .gitignore +1, common/tests/test_data_viewer.py +2, pyproject.toml -5, tox.ini -1 (4 files, +3/-6)
  `git diff ci-fixes macos-only --stat` = 10 files, +126/-49 (d8a3f715 minus .gitignore); `git diff ci-fixes macos-only -- .gitignore` empty; `git show macos-only:.gitignore | grep -n _version` -> 47 (once)
$ IRIS autolink ($S/sv2_ape14c.py): 1.27.0 -> IndexError (0 links); wt-chk-ape14 and gs-ape (keyword-only) -> identical output:
  SJI px (x=29,y=20) -> raster (step=5.79, slit=19.29); world SJI=(-51.552,-399.681) raster=(-51.552,-399.681) arcsec; max diff 3.27e-07 / reverse finite fraction 1.0, raster[90,20,0] -> sji (143.774, 20.401)
$ chk_branch.py (PYTHONPATH=wt-chk-qtmac): CFBundleName before Python -> after glue; applicationName glue | displayName glue | argv ['glue']; PM_ToolBarIconSize 24; default_font_size 9; settings.FONT_SIZE after -1.0
$ test_mac_bundle_name (standalone copy $S/chk_test_mac_bundle.py, then appended to the branch's test_app.py): branch -> 1 passed / 3 passed in 0.01s, ruff 0.14.14 clean; glue-qt MAIN -> FAILED AssertionError: assert 'Python' == 'glue'  (so it is a real regression test)
$ fresh-HOME get_qapp(): main -> $HOME/.glue/settings.cfg written with font_size = 9.0;  branch -> no .glue directory
$ bug repros: cmap 1.27.0 "save FAILS: TypeError Object of type ListedColormap is not JSON serializable" / gs-main "save OK"; meta "save FAILS: TypeError no implementation found for 'numpy.save'" / "save OK"; w2p [ 5. 15. 25.] / [5. 5. 5.]; epoch 738038.01 -> 3990-09-06 / 18875.01 -> 2021-09-05; viewer ticks '06 00:20' / '05 00:20'; region coords=WCS AttributeError 'tuple' object has no attribute 'shape' at coordinate_helpers.py:42 on both 1.27.0 and gs-main (unfixed by design), NOCOORDS=1 draws with both layers enabled
$ slit_workaround.py run(False) (real sns SJI 1400): 1.27.0 [21.05, 144.96, 275.06]; gs-main [21.05, 20.62, 21.24] (direct gWCS 21.05 / 20.62 / 21.24)
$ irispy 0.8.1 read_files(..., spectral_windows=['Mg II k 2796']): sns/ copy of iris_l2_20210905_..._raster_t000_r00000.fits OK RasterCollection; raster/ copy FAILS ValueError Expected 187 NUV source filename rows, found 1872
$ gh: PR 44 OPEN MERGEABLE head d3a2bd3 reviews 0 reviewRequests []; PR 68 OPEN MERGEABLE head bd4dce6 labels [] reviews 0 comments 0 files 14, body has "WARNING: AI SLOP" + "Side question: ... QT5 and Python <3.12"; PR 2248 OPEN draft CONFLICTING head 586d194 updated 2022-06-28; #2152 OPEN; conda-forge glue-qt-feedstock recipe run: python.app [osx], pyqt, no pyobjc; labels `bug`/`enhancement` exist on both repos
```

**Tests to add.**
- glue ape14 PR: none beyond the 11 on the branch. Optional if a reviewer asks: `test_wcs_autolink_iris_like_clone` is NOT possible (low-level coords have no saver); say so.
- glue PR C / A: none beyond the branch tests (listed in the PR bodies).
- glue-qt PR B: none beyond the branch (`test_state_without_y_att`, `test_slice_function_sliders`, `test_wcsaxes_profile`, `test_reference_data_ndim_change`, `test_slice_sliders_data_removed`, `test_profile_tools_unit_override`; gates `requires_slice_function`, `requires_wcsaxes`).
- glue-qt #68: `test_mac_bundle_name` (above; skips off Darwin and without pyobjc; passes on the branch, fails on main with `'Python' == 'glue'`).
- glue state.py PR: `test_save_style_colormap_object` and `test_save_meta_quantity` in `glue/core/tests/test_state.py` (assertions: `GlueSerializer(DataCollection([d])).dumps()` succeeds; loaded style has no `preferred_cmap`; loaded meta lacks the Quantity key and keeps the scalar keys).
- glue coordinate_helpers PR: the synthetic `W` class + `assert_allclose(world2pixel_single_axis(w, lon, t, pixel_axis=0), [5, 5, 5])` and, for symmetry, `pixel_axis=1` -> `[0, 1, 2]`.
- glue matplotlib PR: the updated `test_mpl_datetime64` (above).
- glue-solar (WP1, gated): `glue_solar/tests/test_autolink.py::test_sji_raster_autolink` skipping unless `from glue.plugins.wcs_autolinking.wcs_autolinking import kept_numpy_axes` imports; uses the `sns/` copies of `iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits` and `..._raster_t000_r00000.fits` from `irispy_test_files` (the `raster/` copy of that raster fails in irispy 0.8.1 with "Expected 187 NUV source filename rows, found 1872"); asserts `len(wcs_autolink(DataCollection([sji, raster]))) == 1`, link cids = SJI [Pixel Axis 2 [x], Pixel Axis 1 [y]] <-> raster [Pixel Axis 1 [y], Pixel Axis 0 [z]], and world agreement < 1e-5 arcsec at one pixel.

**Pitfalls (verified).**
- `rerere.enabled=true` globally: a bad first resolution of the python_export.py conflict is replayed silently on the next cherry-pick (seen today). Disable it for the split, or `git rerere clear` after any mistake.
- Resolve the `python_export.py` conflict by hand or by copying the whole file (`cp` from a known-good tree); a scripted `re.sub` whose replacement contains `\n` turns the `"...\n"` string literals of the exported script into real newlines (SyntaxError).
- RUF059: the pinned ruff 0.15.20 flags 229/257/336; after fixing those it flags `test_state.py:226`. Fix all four lines. The hook runs `--fix` but these are unsafe fixes, so pre-commit.ci will not fix them for you.
- ruff 0.16.5 adds PLR0917 to the ape14 branch (not to main) and CPY001 everywhere (also main). pre-commit.ci autoupdates monthly (`autoupdate_schedule: 'monthly'`), so open the PR with the keyword-only change already in.
- glue-qt pins ruff v0.14.14, not 0.15.20. Both are clean on both glue-qt branches today.
- `glue_qt/_version.py` is committed on glue-qt `profile-wcs` and is NOT ignored on main; `glue/_version.py` is untracked-and-not-ignored in the glue main checkout. Use explicit paths with `git add`.
- The glue-qt A/C dependency: B's viewer passes `wcs=hasattr(ProfileViewerState, 'wcsaxes')`; a glue-qt release before the glue-core release is harmless (gated), but the 13 skips will look odd in glue-qt CI's non-dev jobs; say so in the PR.
- `test_slice_function_out_of_bounds` covers non-reference layers only; reference-data out-of-range slices raise IndexError (`state.py:582`) and the artist is hidden, not disabled (`_calculate_profile_error` only handles IncompatibleAttribute/IncompatibleDataException). Reviewer may ask; the PR body states it.
- Headless runs of main-based glue_qt (outside pytest) write `font_size = 9.0` into `~/.glue/settings.cfg` (offscreen default); the branch cannot migrate 9 (Cocoa default is 13) and renders 9 pt. Today the file has `font_size = -1.0` (mtime 08:36); keep HOME isolated for every headless run (`HOME=$S/home-wp0`), which wrote nothing today.
- On macOS `setApplicationName/DisplayName` change nothing visible; without pyobjc (conda-forge) the mac fix is a no-op. Say both in the PR.
- `_checkboxes['test'] = QTreeWidgetItem()` in bd4dce6b is a no-op (`PluginConfig.save()` writes unconditionally; the test passes with and without); drop it in the CI PR.
- The epoch fix makes the old `test_mpl_datetime64` value (719313 days) mean year 3939 and overflow `timedelta64[ns]`; update the test in the same PR and bump the matplotlib floor to 3.3 (`get_epoch`).
- The RegionData `np.asarray` patch is not a fix (layer disables itself); do not open it as a PR.
- The ape14 `XPASS test_2d_and_1d_data_cubes_with_no_celestial_axes` is pre-existing (non-strict xfail "only fails under py310"), do not touch it.
- `gh auth status` was reported invalid by the writer but is clean at 17:35; refresh only if a write fails.
- No triage access on glue-viz/glue and glue-viz/glue-qt: `--label` / `--add-label` fail with 403. Ask for labels in the PR body.
- `$S/wp0_bug_cmap.py` has a broken tail (`saver.members` does not exist -> AttributeError after the first `dumps()`); only the first printed line ("save FAILS" / "save OK") is the repro. `wp0_bug_meta.py`, `wp0_bug_w2p.py`, `wp0_bug_epoch*.py`, `wp0_bug_region.py` run clean.
- Running any test that calls `get_qapp()` OUTSIDE the glue_qt package tree (no `glue_qt/conftest.py` -> no `CFG_DIR` redirect) on main-based glue_qt writes `font_size = 9.0` into `$HOME/.glue/settings.cfg`. Reproduced 17:40 with a fresh HOME: main -> `font_size = 9.0` written; branch -> no `.glue` directory at all. Never run those with the real HOME.

**Acceptance criteria.**
- [ ] glue PR "Support APE-14 low-level WCS in WCSLink and wcs_autolink" open from `nabobalis:ape14-wcs-autolink`, labelled enhancement, body references #2152 and glue-solar #44 and states the wrapper coherence requirement; pre-commit.ci green; 69 passed / 1 xfailed / 1 xpassed locally.
- [ ] glue PR C open from `nabobalis:profile-slice` (2 commits + RUF059 fix), no `wcsaxes` reference in the tree, 36 passed / 1 skipped, ruff 0.15.20 clean.
- [ ] glue PR A open from `nabobalis:profile-wcsaxes` (C + 2 commits + RUF059 fix), body carries the WCSAxes-vs-x_display_unit rule and the pixel-coordinate ROI model, 57 passed / 1 skipped, tree == `profile-wcs` tip except the four RUF059 lines.
- [ ] glue-qt PR B open from a branch without `glue_qt/_version.py`, references C and A, states the hasattr gating and the 68/14 vs 81/1 numbers.
- [ ] #2248 closed with the pointer comment; `origin/1dprofile_wcs` deleted.
- [ ] glue-qt CI PR open (4 files, +3/-6) and #68 rewritten on top of it: no `setApplicationDisplayName`, `test_mac_bundle_name` present and passing, body lists the Linux/Windows +1 pt effect, the CFBundleName mechanism, the pyobjc fallback, the 0.75x decision; label enhancement; Qt5/py<3.12 question moved out.
- [ ] Manual macOS pass done with `font_size = -1.0`.
- [ ] Three glue-core PRs open (state.py, coordinate_helpers.py, utils/matplotlib.py + `pyproject.toml` floor bump to `matplotlib>=3.3`, added by hand) each with the repro in the body and a test; one glue-core issue for RegionData with the repro.
- [ ] Every upstream PR body on glue / glue-qt ends with the requested label (no `--label` was possible).
- [ ] `gh pr view 44 --json reviewRequests` shows astrofrog and Carifio24.
- [ ] The three TODO files updated per the list below; `IRIS_GLUE_GAP_PLAN.md:10-17` rewritten.
- [ ] Scratch worktrees removed from both user repos (`git worktree list` shows only the main checkouts).

**Dropped / out of scope.**
- Switching every wrapped low-level pair to the values path in the ape14 PR: offered to reviewers in the body, not implemented (glue-solar fixes `_GlueWCS` coherence in WP1 instead).
- Clamp/IncompatibleDataException for out-of-range reference slices in PR C: UI cannot hit it; stated as known limitation.
- Splitting the `profile_tools.py` unit-override fix out of PR B: one PR less to babysit; mention it as "independent bug fix included".
- `setApplicationDisplayName('Glue')` variant: dropping the call is the zero-behaviour-change option.
- Removing the 0.75x slice-widget font: unchanged unless the manual pass says it is unreadable.
- Skipping the FONT_SIZE migration under offscreen QPA: not needed once HOME is isolated for headless runs; upstream can ask.
- RegionData PR: the obvious patch does not fix it (layer disabled).
- glue-solar user-guide Linking paragraph and regression test: gated on a glue release (WP1 owns the text; the test skeleton is above).
- Any glue-solar code change (D2 keeps WP0 to upstream shipping only).

**Docs.**
- `IRIS_GLUE_GAP_PLAN.md:10-17` -> "**Current status (2026-09-02):** glue-solar PR #44 is open and mergeable with CI green on d3a2bd3 (reviewers requested: astrofrog, Carifio24). Phase 3.1 is implemented on `~/Git/glue` branch `ape14-wcs-autolink` (SJI+raster autolink verified on irispy test data) and is open as glue-viz/glue#<ape14>; it complements Phase 1.4 (kept, D1). The profile-viewer restart (`~/Git/glue/PROFILE_WCS_RESTART_TODO.md`, Pieces A-C) is implemented on `profile-wcs` in glue and glue-qt and open as glue-viz/glue#<C>, #<A> and glue-viz/glue-qt#<B>; the macOS work is glue-viz/glue-qt#68 (code complete, CI green, awaiting review). The TODO files are untracked local files. The first glue-solar work after #44 is WP1 (`_GlueWCS` coherence + wavelength in Angstrom, D3) then the moments action (Phase 2.1, a `layer_action` that adds the result Data without opening a viewer, D4)."
- `IRIS_GLUE_GAP_PLAN.md:141-147`: "(audit §4a)" -> "(audit, 'Data loading and representation' bullet and the 'SJI and raster temporal coordination' row)"; "This single change makes IRIS autolinking work and removes Phase 1 item 4." -> "This makes SJI<->raster autolinking work (frame-0 geometry); raster<->raster additionally needs the glue-solar `_GlueWCS` object-class coherence fix (WP1). Phase 1.4 stays: it links world components by physical type and is time-aware, so the two are complementary (D1)."
- `IRIS_GLUE_GAP_PLAN.md:144-146` "Generalize link discovery to match on `world_axis_physical_types` and transform through `pixel_to_world_values`/`world_to_pixel_values` only." -> "Generalize link discovery to match on `world_axis_physical_types`; pairs whose matched types are in a different order transform through world values with an explicit permutation, same-order pairs still go through `HighLevelWCSWrapper` objects (which is why `_GlueWCS` must keep its object classes/components coherent, WP1)." (doc-accuracy finding: the branch does not use the values path for every pair.)
- `IRIS_GLUE_GAP_PLAN.md:39` and the Phase 3.2 item at `:148-153`: append one sentence to the Phase 3.2 item: "Note: glue `profile-wcs` commit 98d7bb7c only translates the slice point between layers inside one profile viewer (`ProfileLayerState.slice_view`); it is not cross-viewer synchronisation and does not advance this item." (profile-wcs finding `98d7bb7c`.)
- `IRIS_GLUE_GAP_PLAN.md:195`: "| 2 | Phase 3.1 (APE-14 autolink) | Small, well-scoped glue-core PR; deletes Phase 1.4 |" -> "| 2 | Phase 3.1 (APE-14 autolink) | Small glue-core PR, open; complements Phase 1.4 |".
- glue-solar `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:57-59`: unchanged in WP0. WP1 replaces it with a version-gated note ("with glue-core > 1.27.0 the SJI and raster datasets link automatically; on 1.27.0 pair `Longitude`/`Latitude` (SJI) with `Helioprojective Longitude`/`Helioprojective Latitude` (raster) in the link editor").
- No CHANGES.md / changelog fragments anywhere: glue and glue-qt generate release notes from PR labels (`.github/release.yml`); glue-solar has no WP0 change.

**TODO file edits (old -> new).**

`~/Git/glue/APE14_AUTOLINK_TODO.md`
- L3-4 `Target: one PR to \`glue-viz/glue\` against \`main\` (audited at \`dae530c3\`,\n2026-08-29).` -> `Target: one PR to \`glue-viz/glue\` against \`main\`. Implemented on branch\n\`ape14-wcs-autolink\` (b16a3703, 016d9cf2; merge-base dae530c3 == upstream/main\non 2026-09-02); PR pending the PLR0917 keyword-only tweak (WP0 brief).`
- L9-10 `The glue-solar capability audit (§4a of\n\`IRIS_IDL_GLUE_CAPABILITY_AUDIT.md\` in that repo) measured that autolinking` -> `The glue-solar capability audit ('Data loading and representation' bullet,\nlines 129-131, and the 'SJI and raster temporal coordination' row, line 182, of\n\`IRIS_IDL_GLUE_CAPABILITY_AUDIT.md\` in that repo) measured that autolinking`
- L11-12 `This PR\nalso deletes a planned glue-solar workaround (its gap plan, Phase 1 item 4).` -> `glue-solar\nkeeps its Phase 1.4 \`link_hpc\` helper (world links by physical type, time-aware);\nthis PR adds the complementary frame-0 pixel WCSLink (decision D1, 2026-09-02).`
- L56, L61, L69, L74, L80: `- [ ]` -> `- [x]` (all five section-2 boxes).
- L88, L91, L93, L94, L98: `- [ ]` -> `- [x]`.
- L96-97 `- [ ] Round-trip: \`forwards\`/\`backwards\` agree with direct\n      \`pixel_to_pixel\` on the sliced-and-wrapped WCSes.` -> `- [x] Forwards/backwards asserted against analytic expected values in every\n      new test (stronger than a \`pixel_to_pixel\` comparison; \`pixel_to_pixel\`\n      is not called by the new tests).`
- L103-106: keep `- [ ]`; append `      Gate: skip unless \`from glue.plugins.wcs_autolinking.wcs_autolinking\n      import kept_numpy_axes\` succeeds; use the \`sns/\` copies of the irispy\n      files (the \`raster/\` copy of the 2021 raster does not load in irispy 0.8.1).`
- L107-110: keep `- [ ]`; append `      Verified broken 2026-09-02: \`_GlueWCS\` inherits deg object classes, so\n      \`HighLevelWCSWrapper(_GlueWCS(raster)).pixel_to_world\` raises\n      \`ValueError: Latitude angle(s) must be within -90 deg <= angle <= 90 deg\`\n      and raster<->raster pairs get 0 links even on the branch. Fix (WP1):\n      override \`world_axis_object_classes\` (arcsec unit kwarg; entries are\n      mixed 3-/4-tuples, unpack \`cls, args, kwargs, *rest\`) and\n      \`world_axis_object_components\` getters (~15 lines).`
- L111-112 `- [ ] Delete "explicit link helper" (gap plan Phase 1.4) from the glue-solar\n      plan once the released glue autolinks IRIS data.` -> `- [x] Decided 2026-09-02 (D1): Phase 1.4 \`link_hpc\` stays; it is complementary\n      (time-aware world links), not replaced by this PR.`
- L116, L118, L119: `- [ ]` -> `- [x]`.
- L122: keep `- [ ]`; append `      (needs \`forwards\`/\`backwards\` and \`transform\` options keyword-only first:\n      PLR0917 under ruff 0.16, see WP0 brief).`

`~/Git/glue/PROFILE_WCS_RESTART_TODO.md`
- L8-10 `**Verdict: do NOT rebase. Restart fresh off \`main\`, in three separate\npieces.** Keep \`origin/1dprofile_wcs\` untouched as reference until the\nsalvage below is copied out; then it can be deleted.` -> `**Verdict: do NOT rebase. Restart fresh off \`main\`, in three separate\npieces.** Salvage is complete (commit f767d320 on \`profile-wcs\`): close\nglue-viz/glue#2248 and delete \`origin/1dprofile_wcs\`.\n\nStatus 2026-09-02: Pieces A-C are implemented on \`glue:profile-wcs\` (175e7129,\nf767d320, 98d7bb7c, c3bcd75b) and \`glue-qt:profile-wcs\` (1133c0e9); suites\ngreen (glue profile 57/1; glue-qt 81/1 with both forks, 68/14 on released\nglue-core). Not PR-ready as-is: 3 RUF059 lint hits (test_state.py:229/257,\ntest_viewer.py:336), reorder into C then A (one python_export.py conflict each),\ndrop the committed \`glue_qt/_version.py\`. Steps in the WP0 brief.`
- L50-54: append after `Whatever\nthe decision, it goes in the PR description.`: `\n\nDecided (f767d320): WCSAxes formatting only when reference coords are real (not\nNone/LegacyCoordinates), \`x_att\` is a world component, and\n\`(x_display_unit or '') == component native unit\` (\`_wcsaxes_with_unit\`). In that\nmode the profile, x limits and ROI are in pixel coordinates (image-viewer model);\ncrossing the unit boundary resets x limits; \`x_limits_pixel\` records the mode in\nsessions.`
- L65, L80, L83, L86: `- [ ]` -> `- [x]`.
- L75-79 `- [ ] \`wcsaxes_slice\` idea ... make it a plain method, not a state-mutating\n      property getter ...` -> `- [x] \`wcsaxes_slice\`: reads the per-axis index from \`self.slices\`, reversed to\n      WCS order; implemented as a read-only property (no state mutation).`
- L83-85: append `(apply_roi builds the subset on \`x_att_pixel\` only when \`wcsaxes_active\`)`.
- L93-95 `- The \`x_att → x_att_pixel\` swaps in \`apply_roi\` /\n  \`is_convertible_to_single_pixel_cid\` (main deliberately went the other\n  way for units).` -> `- The \`x_att -> x_att_pixel\` swap in \`is_convertible_to_single_pixel_cid\`.\n  (The \`apply_roi\` swap was deliberately reinstated, but only while\n  \`wcsaxes_active\`: the profile is in pixel coordinates in that mode.)`
- L108, L117, L120: `- [ ]` -> `- [x]`.
- L111-116 `One fix needed upstream: it\n      registers the \`y_att\` callback unconditionally ...` -> `Done as a refactor: \`y_att\`/\`z_att\`\n      are hasattr-guarded in a loop, \`_plot_atts\` uses \`x_att_pixel\` when\n      present, stale sliders are cleared when data/atts become None, and sync\n      is skipped while \`len(slices) != ndim\`.`
- L120-123 `gated on Piece A being\n      present in the installed glue-core (version floor).` -> `gated by\n      \`hasattr(ProfileViewerState, 'wcsaxes')\` feature detection (no release\n      contains A yet); switch to a version floor after the glue-core release.`
- L129, L135, L138, L141: `- [ ]` -> `- [x]`.
- L146-148: `1. Piece C ...` -> `1. Piece C -> glue PR from \`profile-slice\` (175e7129 + 98d7bb7c + RUF059 fix).\n2. Piece A -> glue PR from \`profile-wcsaxes\` stacked on C (f767d320 + c3bcd75b + RUF059 fix).\n3. Piece B -> glue-qt PR from 1133c0e9 without \`glue_qt/_version.py\`.`
- L150-152: keep both `- [ ]`; append to L150 `(blocked only on opening PR A; do it right after)`.

`~/Git/glue-qt/MACOS_INTEGRATION_TODO.md`
- L22-28: replace `This fixes window titles, and on macOS Qt uses the display name for\n      the auto-generated About/Quit menu-item labels.` with `On macOS the menu title and the About/Hide/Quit labels come from\n      \`CFBundleName\` (qtbase \`qcocoahelpers.mm\` \`qt_mac_applicationName\`), so\n      the Qt-side names change nothing there. On Linux/Windows the QPA plugin\n      appends the display name to native top-level window titles\n      (\`qplatformwindow.cpp\` \`formatWindowTitle\`, case-sensitive \`endsWith\`), so\n      the main window \`Glue\` would read \`Glue - glue\`: drop\n      \`setApplicationDisplayName\` (decided 2026-09-02). \`QSettings\` grep done:\n      no direct use in glue-qt.`
- L46-49: append `Follow-up: the conda-forge glue-qt-feedstock recipe has no pyobjc\n      (\`python.app [osx]\`, \`pyqt\` only); open a feedstock issue after the\n      release (\`pyobjc-framework-cocoa  # [osx]\`).`
- L53-55 `Automated test can only assert\n      \`applicationName()\`/\`applicationDisplayName()\`.` -> `Automated test: \`test_mac_bundle_name\` asserts\n      \`NSBundle.mainBundle().infoDictionary()['CFBundleName'] == 'glue'\` after\n      \`get_qapp()\` (headless-verifiable; 3 passed offscreen).` and tick the box once the test is committed.
- L88-91 `(make it 0; decide whether to keep the\n      1-point reduction elsewhere or zero both)` -> `(zeroed on every platform; Linux/Windows in-app text grows\n      by 1 pt, stated in the PR body)`.
- L98-101: split into `- [x] Sweep the hardcoded sizes: status bar and link-editor overrides deleted.` and `- [ ] \`data_slice_widget.py:46\` still scales its label to 0.75x; default keep,\n      check in the manual pass, delete only if unreadable at 13 pt.`
- L110-111: `- [ ]` -> `- [x]` (no change needed; guarded try/except at \`app.py:104-107\`).
- L120-121: `- [ ]` -> `- [x]` (both screenshots are in the PR body).
- L122-123: `- [ ] No clipped dialogs on macOS at the new sizes; Linux/Windows CI green\n      (the offset change affects them too if zeroed).` -> `- [ ] No clipped dialogs on macOS at the new sizes (manual).\n- [x] Linux/Windows CI green (main was already red before the branch:\n      pytest-flake8 vs pytest 9, leaked viewers; those fixes are split into\n      their own PR).`
- After L126 add `- [ ] Before judging visually: \`~/.glue/settings.cfg\` must say \`font_size = -1.0\`;\n      headless runs of main-based glue_qt write 9.0 there, which the branch keeps\n      as a 9 pt override.`


---

# WP1 - Linking basics in glue-solar

**Note (2026-09-02, after WP0).** The APE-14 autolinker is now draft PR glue-viz/glue#2595 (branch `ape14-wcs-autolink`, tip rewritten to bad24b99 with the same tree); cite #2595 in the `skipif` reason and in the PR description.

**Goal.** Make every IRIS dataset glue-solar loads speak one coordinate language (helioprojective axes in arcsec, wavelength in Angstrom, identical component names on SJI, raster, stack and map), make that language coherent for astropy's high-level WCS API so Glue's autolinker can pair IRIS datasets once glue-core ships the APE-14 autolinker, and give users the world-coordinate links (`link_hpc`) automatically from the observation browser and from a menu action. Everything ships in glue-solar on released glue-core 1.27.0.

## Current state (2026-09-02)

All evidence below is on `/Users/nabil/Git/glue-solar` branch `iris-observation-browser` (= PR glue-viz/glue-solar#44, head d3a2bd3, CI green, no reviews). Nothing in this WP exists yet: `grep -rn "LinkSame\|link_hpc\|wcs_autolink\|WCSLink" glue_solar/` returns nothing.

- `glue_solar/sources/loaders/iris.py:27-32` `_AXIS_NAMES` maps physical type to name but `:41` reads `name or _AXIS_NAMES.get(...)`, so irispy's own gWCS names win. Result (re-verified today with `wp1_inspect.py`): SJI world components are `['Time (Utc)', 'Latitude', 'Longitude']`, raster `['Helioprojective Longitude', 'Helioprojective Latitude', 'Wavelength']`. The `"time": "Time"` entry is dead code (no irispy WCS has an unnamed time axis).
- `glue_solar/sources/loaders/iris.py:35-69` `_GlueWCS(BaseWCSWrapper)` overrides `world_axis_names`, `world_axis_units` (deg -> arcsec for helioprojective only), `pixel_to_world_values`, `world_to_pixel_values`. Wavelength stays in metres: raster `world_axis_units == ('m', 'arcsec', 'arcsec')`, stack `('m', 'arcsec', 'arcsec', '')` (asserted at `glue_solar/tests/test_importer.py:176`).
- `_GlueWCS` inherits `world_axis_object_classes` / `world_axis_object_components` from the wrapped WCS. For the FITS `-TAB` raster those say `SkyCoord ... unit=(deg, deg)` while the values are arcsec, so `HighLevelWCSWrapper(_GlueWCS(raster)).pixel_to_world` raises `ValueError: Latitude angle(s) must be within -90 deg <= angle <= 90 deg, got -399.83 deg` (ape14 P3.1-sec4 and viewer-composition APE14-TODO-4.2, both verifier-confirmed). The SJI gWCS is natively arcsec so it happens to be coherent. Today's `wp1_inspect.py` output of the four inner WCS kinds:

```
== SJI gwcs: inner gwcs.wcs._wcs.WCS
  names ('Longitude', 'Latitude', 'Time (UTC)') | types ('custom:pos.helioprojective.lon', 'custom:pos.helioprojective.lat', 'time') | units ('arcsec', 'arcsec', 's')
  components [('celestial', 0, '<callable function>'), ('celestial', 1, '<callable function>'), ('temporal', 0, '<callable function>')]
  class celestial SkyCoord () {'frame': 'Helioprojective', 'unit': (Unit("arcsec"), Unit("arcsec"))} rest 0
  class temporal Time () {'unit': Unit("s"), ...} rest 1
== raster -TAB: inner astropy.wcs.wcs.WCS
  names ['', '', ''] | types ['em.wl', 'custom:pos.helioprojective.lat', 'custom:pos.helioprojective.lon'] | units ['m', 'deg', 'deg']
  components [('spectral', 0, '<callable function>'), ('celestial', 1, '<callable function>'), ('celestial', 0, '<callable function>')]
  class celestial SkyCoord () {'frame': 'Helioprojective', 'unit': (Unit("deg"), Unit("deg"))} rest 0
  class spectral Quantity () {} rest 1
== stack compound: inner ndcube.wcs.wrappers.compound_wcs.CompoundLowLevelWCS
  names ('', '', '', 'Scan') | types ('em.wl', 'custom:pos.helioprojective.lat', 'custom:pos.helioprojective.lon', None) | units ('m', 'deg', 'deg', '')
  components [('spectral_0', 0, '<callable function>'), ('celestial_0', 1, ...), ('celestial_0', 0, ...), ('linear__1', 0, 'value')]
  class celestial_0 SkyCoord () {'frame': 'Helioprojective', 'unit': (Unit("deg"), Unit("deg"))} rest 0
  class spectral_0 Quantity () {} rest 1
  class linear__1 Quantity () {'unit': Unit(dimensionless)} rest 0
== moment map 2D: inner astropy.wcs.wcs.WCS
  types ['custom:pos.helioprojective.lat', 'custom:pos.helioprojective.lon'] | units ['deg', 'deg']
  class celestial SkyCoord () {'frame': 'Helioprojective', 'unit': (Unit("deg"), Unit("deg"))} rest 0
```

  Note: the spectral class is a 4-tuple `(Quantity, (), {}, spectralcoord_from_value)` with no `unit` kwarg (astropy 8 `fitswcs.py:699-712`, the unit lives inside the closure). The celestial class is a 3-tuple. The stack's `Scan` getter is the string `'value'`, every other getter is a callable. The coherence fix must handle all of that, which is why it wraps constructors and getters rather than editing a `unit` kwarg (see Verified code).

- `glue_solar/sources/iris.py:30-48` `browse_iris` loads through `QtIRISImporter`, calls `app.add_datasets`, opens one `ImageViewer`. No links. `glue_qt.app.application.GlueApplication.add_datasets` (glue-qt `application.py:1444-1447`) runs `run_autolinker` afterwards; on glue-core 1.27.0 `wcs_autolink` skips low-level WCS (`wcs_autolinking.py:321` keeps `BaseHighLevelWCS` only) so nothing is suggested.
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:54-59` Linking section tells users to pair `Helioprojective Longitude`/`Helioprojective Latitude` by hand; the SJI does not expose those names (doc-accuracy doc-4, verifier-confirmed: "the manual-pairing instruction as written cannot be followed for SJI").
- glue-core 1.27.0 `glue/core/coordinate_helpers.py:104` `world_dep = wcs.axis_correlation_matrix[:, pixel_axis]` collapses every world input not directly correlated with the requested pixel axis to `.flat[0]`. For the SJI gWCS (matrix `[[1,1,1],[1,1,1],[0,0,1]]`) world->pixel for x/y therefore always uses exposure 0. Re-verified today (`wp1_timepatch.py`): the same SJI pixel (10, 10) at frames 0/30/61 derives back as x = 10.0 / 134.34 / 263.82 through world links. No fork branch touches this file (`git log v1.27.0..{main,ape14-wcs-autolink,profile-wcs} -- glue/core/coordinate_helpers.py glue/core/component_link.py` is empty on all three; slit-overlay P1.6-dep).
- glue fork `/Users/nabil/Git/glue` branch `ape14-wcs-autolink` (016d9cf2 = v1.27.0-20-g016d9cf2): APE-14 autolinker, 31 passed/1 xfailed/1 xpassed. Upstream PR not opened. With stock `_GlueWCS` it links SJI<->raster only (the permuted-types values path); raster<->raster and raster3D<->map2D give `IncompatibleWCS` because the same-order path goes through SkyCoord and hits the ValueError above (ape14 P3.1-sec4; science-moments verifier; critic section 2).

## Decisions already made

- D1: `link_hpc` (LinkSame on world components by physical type) is permanent. It is complementary to the fork's `WCSLink` (pixel link, exact at SJI exposure 0, ~250 full-frame px off after the 4.8 h sit-and-stare; sv_reach: 14/187 raster steps reached by the fork link vs 186/187 time-aware). Do not write "deleted once autolink lands" anywhere.
- D2: everything here is glue-solar code on released glue-core 1.27.0 + glue-qt main. The only glue-core changes referenced are the existing fork branch (3.1) and the one-function `world2pixel_single_axis` fix, which glue-solar monkeypatches meanwhile.
- D3: wavelength display unit is Angstrom, string `"Angstrom"` (`str(u.AA)`), converted in `world_axis_units`, `pixel_to_world_values`, `world_to_pixel_values` and (new) the high-level object classes/components, mirroring arcsec. Every later WP assumes wavelength values in Angstrom (P3.3 native unit, P2.2 wavelength extraction, P1.3 `x_display_unit`, P3.6 saver tests).
- Coherence fix = the ~15-line version (both `world_axis_object_classes` AND `world_axis_object_components`), not the 3-line classes-only version (critic section 2: the getters are used by `world_to_pixel`).
- Time-aware SJI ROI -> raster: the SAFE workaround is the wrap of `glue.core.coordinate_helpers.world2pixel_single_axis`, rebound in `glue.core.component_link`. NOT an all-ones `axis_correlation_matrix` (breaks `ImageViewer.format_coord` with `OverflowError: cannot convert float infinity to integer` in astropy `wcsaxes/formatter_locator.py:642`; slit-overlay verifier, critic section 2, re-run by the critic with `v_qt.py PATCH=1`).
- Axis names: `_AXIS_NAMES` by physical type wins over irispy's name; irispy's name is the fallback, then the physical type string. The `"time"` entry is removed so the SJI time axis keeps irispy's `Time (UTC)` (rendered `Time (Utc)` by glue) and does not collide with the datetime64 `Time` *component* that rasters carry now and the sync-slicing WP will add to SJIs.
- `link_hpc` links only datasets whose `coords` is a `_GlueWCS` (all IRIS/AIA-cutout data from glue-solar loaders). A bare sunpy-map WCS (`glue_solar/sources/maps.py:27`) is in degrees; `LinkSame` does not convert, so linking it would be silently wrong by 3600x. Wrapping sunpy maps in `_GlueWCS` is the SDO-context WP's call.
- Regression test for autolink is gated on glue version with `pytest.mark.skipif`; exact check below.
- Moments (D4) not touched here; this WP only guarantees that a 2D map made with `_cube_data` autolinks to its 3D source on the fork glue (verified) and can be pixel-LinkSame'd on stock glue (moments WP).

## Dependencies / order

- Lands first, before every other glue-solar WP: the moments WP needs Angstrom + coherent `_GlueWCS` (raster3D<->map2D autolink on the fork; consistent names); the quicklook/slit/sync-slicing WPs need `link_hpc` and the `world2pixel_single_axis` patch; the profile-wcs and units WPs need `world_axis_units == 'Angstrom'`.
- Depends on nothing unreleased. The `ape14-wcs-autolink` glue PR is independent; this WP makes that PR pay off beyond SJI<->raster (verified below) and carries the glue-solar regression test that the PR's TODO section 4 asks for.
- Unblocks: upstream tiny PR to glue-core `coordinate_helpers.world2pixel_single_axis` (the patched function body is the PR; file it after this lands, remove `glue_patches.py` when released).

## Files to touch

- `glue_solar/sources/loaders/iris.py`: drop `"time"` from `_AXIS_NAMES`, add `_AXIS_UNITS`, rewrite `_GlueWCS` (names rule, units, value conversions via `_units`, new `world_axis_object_components`/`world_axis_object_classes` with converting getters/constructors), add `link_hpc(data_collection)`, extend `__all__`. New imports: `from functools import reduce`, `from glue.core.link_helpers import LinkSame`.
- `glue_solar/sources/iris.py`: import `link_hpc`; `browse_iris` calls `data_collection.add_link(link_hpc(data_collection))` right after `app.add_datasets(...)`; new `@menubar_plugin("IRIS: link helioprojective coordinates") def link_iris(session, data_collection)`; `__all__` gains `"link_iris"`.
- `glue_solar/glue_patches.py` (new, 30 lines): `world2pixel_single_axis` override + the two rebinding lines. Marked `# ponytail: monkeypatch, remove when glue-core fixes coordinate_helpers`.
- `glue_solar/__init__.py`: `from glue_solar import glue_patches` before the `sources` import (the package is imported by glue's plugin entry point `glue_solar:setup`, so the patch is active whenever the plugin is).
- `glue_solar/tests/test_importer.py`: three expectation changes (line 112 label, line 176 units tuple, lines 189-197 loop converts every axis to the shown unit).
- `glue_solar/tests/test_linking.py` (new): 11 tests (10 functions, one parametrised x2), listed below.
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: Linking section rewritten; loading paragraph mentions Angstrom.
- `changelog/<PR>.feature.rst` (new) and `changelog/44.feature.rst` (one clause).

## Step-by-step

1. Branch from `iris-observation-browser` (or from `main` after #44 merges; the diff is the same).
2. In `glue_solar/sources/loaders/iris.py` replace lines 26-69 (`_AXIS_NAMES` comment through `world_to_pixel_values`) with the `_AXIS_NAMES`/`_AXIS_UNITS`/`_GlueWCS`/`link_hpc` block from Verified code. Add the two imports. Update `__all__`.
3. In `glue_solar/sources/iris.py` apply the diff from Verified code (import, one line in `browse_iris`, the `link_iris` action, `__all__`).
4. Create `glue_solar/glue_patches.py` from Verified code; add the import line to `glue_solar/__init__.py`.
5. Update the three expectations in `glue_solar/tests/test_importer.py` (diff in Verified code).
6. Add `glue_solar/tests/test_linking.py` (full file in Verified code).
7. Run `QT_QPA_PLATFORM=offscreen MPLBACKEND=agg python -m pytest glue_solar -q` -> expect 37 passed, 1 skipped (`test_wcs_autolink_pairs_iris_datasets` skipped on 1.27.0). Run `ruff check glue_solar` -> clean (verified with ruff 0.16.1 = the pre-commit pin, 0.16.5 and 0.15.20).
8. Optionally prove the fork path: `git -C ~/Git/glue worktree add --detach <scratch>/wt ape14-wcs-autolink` (the branch is checked out elsewhere, so `--detach`), then `QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=<wt> python -c "import glue; glue.__version__='1.27.1.dev20'; import pytest; pytest.main(['glue_solar/tests/test_linking.py'])"` -> 11 passed (the Qt browse test included: it neutralises glue-qt's autolink dialog, see Pitfalls). `--detach` and the `__version__` override are needed because `glue.__version__` is `importlib.metadata.version('glue-core')` (glue `__init__.py:11`) and still says 1.27.0 with a worktree on `PYTHONPATH`. Remove the worktree.
9. Docs and changelog per the Docs section. Open the PR; in its description point the ape14 glue PR at `test_wcs_autolink_pairs_iris_datasets` as the downstream regression test.

## Verified code

All snippets below were run today in a scratch copy of the package (`<scratchpad>/wp1/glue_solar`, `PYTHONPATH=<scratchpad>/wp1`, `HOME=<scratchpad>/home-wp1`, `QT_QPA_PLATFORM=offscreen MPLBACKEND=agg`, python = `/Users/nabil/Git/glue-solar/.venv/bin/python`, glue-core 1.27.0 unless "fork" is stated). The user's repositories were not modified (`git status` in glue-solar and glue shows only the pre-existing untracked files; my worktree `wt-wp1-ape14` was removed).

### 1. `glue_solar/sources/loaders/iris.py`: names, units, coherent `_GlueWCS`, `link_hpc`

Replaces lines 26-69 of the current file. New imports at the top: `from functools import reduce` (stdlib block) and `from glue.core.link_helpers import LinkSame` (after `from glue.core.data import Data`). `__all__` becomes `["QtIRISImporter", "image_data", "iris_data", "last_directory", "link_hpc", "raster_data"]`.

```python
# irispy's FITS WCSes carry no axis names (Glue would say "World N") and its gWCS uses other ones ("Longitude"),
# so one name per physical type keeps SJI, raster and map components identically labelled.
_AXIS_NAMES = {
    "em.wl": "Wavelength",
    "custom:pos.helioprojective.lon": "Helioprojective Longitude",
    "custom:pos.helioprojective.lat": "Helioprojective Latitude",
}
# Display units, whatever the file stores: helioprojective axes in arcsec, wavelength in Angstrom.
_AXIS_UNITS = {
    "em.wl": u.AA,
    "custom:pos.helioprojective.lon": u.arcsec,
    "custom:pos.helioprojective.lat": u.arcsec,
}


class _GlueWCS(BaseWCSWrapper):
    """
    Present named helioprojective coordinates in arcsec and wavelengths in Angstrom to Glue.

    The low-level values API and the high-level object API (`~astropy.wcs.wcsapi.HighLevelWCSWrapper`,
    `~astropy.wcs.utils.pixel_to_pixel`, hence Glue's WCS autolinker) both speak the display units.
    """

    def _units(self, world_axis):
        """``(stored unit, display unit)`` of a world axis, or `None` when it is shown as stored."""
        target = _AXIS_UNITS.get(self._wcs.world_axis_physical_types[world_axis])
        return (u.Unit(self._wcs.world_axis_units[world_axis]), target) if target else None

    @property
    def world_axis_names(self):
        return [
            _AXIS_NAMES.get(physical_type) or name or physical_type or ""
            for name, physical_type in zip(self._wcs.world_axis_names, self._wcs.world_axis_physical_types)
        ]

    @property
    def world_axis_units(self):
        return tuple(str(units[1]) if (units := self._units(i)) else unit for i, unit in enumerate(self._wcs.world_axis_units))

    def pixel_to_world_values(self, *pixel_arrays):
        values = list(self._wcs.pixel_to_world_values(*pixel_arrays))
        for i, physical_type in enumerate(self.world_axis_physical_types):
            if units := self._units(i):
                stored, target = units
                values[i] = np.asarray(values[i])
                if physical_type.endswith(".lon"):
                    full_circle = (360 * u.deg).to_value(stored)
                    values[i] = (values[i] + full_circle / 2) % full_circle - full_circle / 2
                values[i] = (values[i] * stored).to_value(target)
        return tuple(values)

    def world_to_pixel_values(self, *world_arrays):
        values = list(world_arrays)
        for i in range(self.world_n_dim):
            if units := self._units(i):
                stored, target = units
                values[i] = (np.asarray(values[i]) * target).to_value(stored)
        return self._wcs.world_to_pixel_values(*values)

    # The high-level API builds objects from, and reads values back through, the two properties below; they
    # must use the same units as the value methods above or SkyCoord sees arcsec as degrees.
    @property
    def world_axis_object_components(self):
        components = []
        for i, (key, index, getter) in enumerate(self._wcs.world_axis_object_components):
            if units := self._units(i):
                getter = self._converting_getter(getter, *units)
            components.append((key, index, getter))
        return components

    @staticmethod
    def _converting_getter(getter, stored, target):
        def convert(obj):
            value = getter(obj) if callable(getter) else reduce(getattr, getter.split("."), obj)
            return (np.asarray(value) * stored).to_value(target)

        return convert

    @property
    def world_axis_object_classes(self):
        classes = {}
        for key, (cls, args, kwargs, *rest) in self._wcs.world_axis_object_classes.items():
            construct = rest[0] if rest else cls
            converted = {
                index: units
                for i, (k, index, _) in enumerate(self._wcs.world_axis_object_components)
                if k == key and (units := self._units(i))
            }
            if converted:
                construct = self._converting_constructor(construct, cls, len(args), converted)
            classes[key] = (cls, args, kwargs, construct)
        return classes

    @staticmethod
    def _converting_constructor(construct, cls, n_args, converted):
        def convert(*values, **kwargs):
            values = list(values)
            for index, (stored, target) in converted.items():
                value = values[n_args + index]
                if not isinstance(value, cls):  # a bare value in display units, not an already-built object
                    values[n_args + index] = (np.asarray(value) * target).to_value(stored)
            return construct(*values, **kwargs)

        return convert


def link_hpc(data_collection):
    """
    Links pairing every IRIS dataset's helioprojective longitude and latitude with those of the first one that has them.

    Matching is by world axis physical type, so it does not matter what the components are called. Only datasets
    whose coordinates are a `_GlueWCS` take part: those are all in arcsec, whereas a bare sunpy map WCS is in
    degrees and `~glue.core.link_helpers.LinkSame` does not convert. Pairs that are already linked are skipped,
    so calling this again after loading more data is safe. The caller adds the links::

        data_collection.add_link(link_hpc(data_collection))

    Returns
    -------
    list of `~glue.core.link_helpers.LinkSame`
    """
    linked = {(link.get_to_id(), *link.get_from_ids()) for link in data_collection.links}
    anchors, links = {}, []
    for data in data_collection:
        if not isinstance(data.coords, _GlueWCS):
            continue
        physical_types = list(data.coords.world_axis_physical_types)[::-1]  # world components are in numpy order
        for physical_type, cid in zip(physical_types, data.world_component_ids):
            if physical_type and physical_type.startswith("custom:pos.helioprojective."):
                anchor = anchors.setdefault(physical_type, cid)
                if anchor is not cid and (cid, anchor) not in linked:
                    links.append(LinkSame(anchor, cid))
    return links
```

Design notes that were verified, not guessed:
- Why constructors, not a `unit` kwarg swap: the spectral class is `(Quantity, (), {}, spectralcoord_from_value)` with no `unit` kwarg (astropy 8 `fitswcs.py:711`), so the swap the auditors prototyped for celestial cannot make wavelength Angstrom. Wrapping the constructor (the 4th tuple element, or the class itself for 3-tuples) handles both uniformly; `values_to_high_level_objects` calls `klass_gen(*args, *values, **kwargs)` with values in component-index order (`high_level_api.py:390`).
- Why `isinstance(value, cls)` pass-through: `high_level_objects_to_values` (`high_level_api.py:254`) pushes an already-built `SpectralCoord` through `klass_gen` again; without the guard the first version turned 1398.7 A into 1.4e-17 m and `world_to_pixel` returned x = -54977 for pixel 3 (seen today, fixed, re-verified).
- Why `values[n_args + index]` is safe on both astropy paths: `values_to_high_level_objects` calls `klass_gen(*args, *values)` (values after the positional args), while `high_level_objects_to_values` calls `klass_gen(obj, *args)` (object first) but only for non-`SkyCoord` classes (`high_level_api.py:248-254`), which on IRIS data all have a single component at index 0 (spectral, temporal, the stack's `linear__1`); and every IRIS class has `args == ()` (`wp1_inspect.py` output above), so `n_args` is 0 throughout. `# ponytail:` ceiling: a wrapped WCS whose object class has positional `args` and whose objects are not `SkyCoord` would index the wrong slot on the object path; none exists in irispy/ndcube today.
- String getters (`'value'` on the stack's Scan axis) are handled by `reduce(getattr, ...)`; today every converted axis has a callable getter, the string branch costs one expression.
- `link_hpc` idempotency: `LinkSame` has no `__eq__` (only `JoinLink` does, `link_helpers.py:535`), so `LinkManager.add_link` would happily append duplicates; the `linked` set of `(to_id, from_id)` pairs from `data_collection.links` (`link_manager.py:291` returns `list(self._links)`, all `ComponentLink`s, which have `get_to_id`/`get_from_ids`, `component_link.py:208-237`) makes a second call return `[]`.
- Star topology (everything linked to the first dataset's cids) is enough: glue derives transitively (test `test_link_hpc_chains_every_dataset_through_the_first`: 3 datasets, 4 links, the C II window evaluates the Si IV window's latitude cid).

### 2. `glue_solar/sources/iris.py`

```diff
-from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory
+from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory, link_hpc

-__all__ = ["browse_iris", "read_iris_file"]
+__all__ = ["browse_iris", "link_iris", "read_iris_file"]
@@ def browse_iris(session, data_collection):
-    Browse a folder by observation, load the selection and open the first image in an Image Viewer.
+    Browse a folder by observation, load the selection, link helioprojective coordinates and open the first image.
@@
     app.add_datasets(dialog.datasets)
+    data_collection.add_link(link_hpc(data_collection))
     if dialog.first_image is not None:
@@ (end of file)
+
+
+@menubar_plugin("IRIS: link helioprojective coordinates")
+def link_iris(session, data_collection):
+    """
+    Link the helioprojective longitude and latitude of every loaded dataset (the browser does this on its own).
+    """
+    data_collection.add_link(link_hpc(data_collection))
```

`link_hpc(data_collection)` runs over the whole collection, so a second browse pass or a File -> Open load followed by the menu action links new data to data loaded earlier; "when both SJI and raster are loaded" needs no special case (one dataset yields no links; two raster windows of one scan get lon/lat-linked, which is what you want for subsets across windows).

### 3. `glue_solar/glue_patches.py` (new) and `glue_solar/__init__.py`

```python
"""Workarounds for glue-core bugs that IRIS data hits; each names the upstream change that makes it removable."""

import numpy as np
from glue.core import component_link, coordinate_helpers
from glue.core.coordinate_helpers import unbroadcast


def world2pixel_single_axis(wcs, *world, pixel_axis=None):
    # ponytail: monkeypatch, remove when glue-core fixes coordinate_helpers.world2pixel_single_axis. 1.27.0
    # (line 104) keeps only the world axes directly correlated with ``pixel_axis`` and collapses the others to
    # their first element, so a gWCS whose lon/lat depend on time (irispy SJI) is inverted at exposure 0 for
    # every frame. Only the three "needed" lines differ from upstream.
    if pixel_axis is None:
        raise ValueError("pixel_axis needs to be set")
    if np.size(world[0]) == 0:
        return np.array([], dtype=float)
    matrix = wcs.axis_correlation_matrix
    needed = matrix[:, pixel_axis].copy()
    for _ in range(matrix.shape[0]):  # transitive closure: world axes sharing a pixel axis with a needed one
        needed |= (matrix & matrix[needed].any(axis=0)).any(axis=1)
    original_shape = world[0].shape
    world = np.broadcast_arrays(*[unbroadcast(w) if keep else w.flat[0] for w, keep in zip(world, needed)])
    if len(world) == 1 and world[0].ndim > 1:  # astropy#12154: a 1D WCS cannot take arbitrary shapes
        result = wcs.world_to_pixel_values(world[0].ravel()).reshape(world[0].shape)
    else:
        result = wcs.world_to_pixel_values(*world)
        if len(world) > 1:
            result = result[pixel_axis]
    return np.broadcast_to(result, original_shape)


coordinate_helpers.world2pixel_single_axis = world2pixel_single_axis
component_link.world2pixel_single_axis = world2pixel_single_axis  # imported there by name
```

`glue_solar/__init__.py`: add `from glue_solar import glue_patches` above `from glue_solar.sources import iris, maps` (the `__init__.py` per-file-ignores already allow F401/I).

This is the upstream `world2pixel_single_axis` body with the `needed` closure in place of `world_dep = wcs.axis_correlation_matrix[:, pixel_axis]`; `component_link.py:9-11` imports the function by name, hence the second rebinding. The `axis_correlation_matrix` is untouched, so WCSAxes readouts keep working (see run 6 below and the browse test's `format_coord` assertion).

Effect (run today, `wp1_timepatch.py`, stock glue; same SJI pixel (10, 10) at every exposure, linked back through lon/lat/time world cids):

```
$ HOME=<scratch>/home-wp1 PYTHONPATH=<scratch>/wp1 .venv/bin/python wp1_timepatch.py
glue-core 1.27.0 original    derived SJI x at frames 0/30/61: [10.0, 134.34, 263.82]  (truth: 10.0 everywhere) | max |x-10| = 2.54e+02
glue_solar.glue_patches      derived SJI x at frames 0/30/61: [10.0, 10.0, 10.0]  (truth: 10.0 everywhere) | max |x-10| = 1.28e-09
axis_correlation_matrix untouched: [[1, 1, 1], [1, 1, 1], [0, 0, 1]]
```

What this does and does not change for `link_hpc` users on stock glue (verified in `test_link_hpc_pairs_lon_lat_by_physical_type`):
- raster-drawn image ROI -> SJI: works (inverts the raster -TAB, no time needed).
- world-coordinate subsets (e.g. `Helioprojective Longitude > x`) -> both directions: work.
- SJI-drawn image ROI -> raster: still `IncompatibleAttribute`, because the raster has no component linked to the SJI's `Time (Utc)` world cid. The patch makes the inverse *correct* once such a time link exists; supplying it (raster datetime64 `Time` -> SJI seconds-since-reference, serialisable form per critic `cc_timelink.py`) is the sync-slicing WP, not this one.

### 4. `glue_solar/tests/test_importer.py` diff

```diff
-    longitude = next(component for component in data.world_component_ids if component.label == "Longitude")
+    longitude = next(component for component in data.world_component_ids if component.label == "Helioprojective Longitude")
@@
-    assert data.coords.world_axis_units == ("m", "arcsec", "arcsec", "")
+    assert data.coords.world_axis_units == ("Angstrom", "arcsec", "arcsec", "")
@@
-    for expected, actual, unit, physical_type in zip(
-        source_world,
-        stacked_world[:3],
-        sequence[0].wcs.world_axis_units,
-        sequence[0].wcs.world_axis_physical_types,
+    for expected, actual, unit, shown in zip(
+        source_world, stacked_world[:3], sequence[0].wcs.world_axis_units, data.coords.world_axis_units
     ):
-        if physical_type.startswith("custom:pos.helioprojective."):
-            expected = (expected * u.Unit(unit)).to_value(u.arcsec)
-        np.testing.assert_allclose(actual, expected)
+        np.testing.assert_allclose(actual, (expected * u.Unit(unit)).to_value(u.Unit(shown)))
```

These are the only existing assertions on metres or on the SJI `Longitude` label (`grep -rn '"m"\|world_axis_units\|"Longitude"' glue_solar/`). `test_plugin.py` asserts nothing unit- or name-related. No `.rst` mentions metres; the 1D-profile guide only names the `Wavelength` axis, which is unchanged.

### 5. `glue_solar/tests/test_linking.py` (new, full file)

```python
import shutil

import glue
import numpy as np
import pytest
from glue.core import Data, DataCollection
from glue.core.exceptions import IncompatibleAttribute
from glue.core.link_helpers import LinkSame
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from packaging.version import Version
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar.sources.iris import browse_iris
from glue_solar.sources.loaders.iris import QtIRISImporter, _cube_data, image_data, link_hpc, raster_data

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
HPC = ["Helioprojective Longitude", "Helioprojective Latitude"]
# glue-core 1.27.0 autolinks astropy WCS only; the APE-14 autolinker is glue-viz/glue branch ape14-wcs-autolink
AUTOLINKS_IRIS = Version(glue.__version__) > Version("1.27.0")


def _real(files, name):
    return next(path for path in files if path.name == name and path.parent.name == "sns")


def _cid(data, label):
    return next(cid for cid in data.world_component_ids if cid.label == label)


@pytest.fixture
def sns(irispy_test_files):
    """The matched sit-and-stare SJI 1400 + Si IV 1403 raster pair shipped with irispy."""
    [raster] = raster_data([_real(irispy_test_files, RASTER)], ["Si IV 1403"])
    return image_data(_real(irispy_test_files, SJI)), raster


def test_wavelength_axis_is_in_angstrom(sns):
    _, raster = sns
    assert raster.coords.world_axis_units == ("Angstrom", "arcsec", "arcsec")
    wavelength = _cid(raster, "Wavelength")
    assert raster.get_component(wavelength).units == "Angstrom"
    assert 1380 < np.nanmin(raster[wavelength]) < np.nanmax(raster[wavelength]) < 1420
    world = raster.coords.pixel_to_world_values(3, 20, 50)
    assert world[0] == pytest.approx(raster.coords._wcs.pixel_to_world_values(3, 20, 50)[0] * 1e10)
    assert raster.coords.world_to_pixel_values(*world) == pytest.approx((3, 20, 50), abs=1e-4)  # float32 -TAB


def test_sji_and_raster_share_axis_names(sns):
    sji, raster = sns
    assert [c.label for c in sji.world_component_ids] == ["Time (Utc)", *HPC[::-1]]
    assert [c.label for c in raster.world_component_ids] == [*HPC, "Wavelength"]


@pytest.mark.parametrize(("which", "pixel"), [("sji", (10, 10, 5)), ("raster", (3, 20, 50))])
def test_high_level_api_round_trips_in_display_units(sns, which, pixel):
    data = sns[which == "raster"]
    wcs = HighLevelWCSWrapper(data.coords)
    objects = wcs.pixel_to_world(*pixel)
    values = data.coords.pixel_to_world_values(*pixel)
    types = list(data.coords.world_axis_physical_types)
    sky = next(o for o in objects if hasattr(o, "Tx"))
    assert sky.Tx.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lon")])
    assert sky.Ty.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lat")])
    if which == "raster":
        assert objects[0].to_value(u.AA) == pytest.approx(values[0])
    assert wcs.world_to_pixel(*objects) == pytest.approx(pixel, abs=1e-4)


def test_link_hpc_pairs_lon_lat_by_physical_type(sns):
    sji, raster = sns
    dc = DataCollection([sji, raster])
    links = link_hpc(dc)
    assert len(links) == 2
    assert all(isinstance(link, LinkSame) for link in links)
    dc.add_link(links)
    assert link_hpc(dc) == []  # idempotent
    for label in HPC:
        np.testing.assert_allclose(raster[_cid(sji, label)], raster[_cid(raster, label)])
    # propagated: subsets drawn on the raster map, and subsets on world coordinates
    raster_roi = RoiSubsetState(
        xatt=raster.pixel_component_ids[0], yatt=raster.pixel_component_ids[1], roi=RectangularROI(40, 120, 10, 30)
    )
    assert 0 < sji.get_mask(raster_roi).sum() < sji.size
    lon = _cid(sji, HPC[0])
    assert 0 < raster.get_mask(lon > float(np.nanmedian(sji[lon]))).sum() < raster.size
    # not propagated: a subset drawn on the SJI image needs the SJI exposure time, which the raster cannot supply
    sji_roi = RoiSubsetState(
        xatt=sji.pixel_component_ids[2], yatt=sji.pixel_component_ids[1], roi=RectangularROI(10, 25, 10, 30)
    )
    with pytest.raises(IncompatibleAttribute):
        raster.get_mask(sji_roi)


def test_link_hpc_chains_every_dataset_through_the_first(sns, irispy_test_files):
    sji, raster = sns
    [other] = raster_data([_real(irispy_test_files, RASTER)], ["C II 1336"])
    dc = DataCollection([sji, raster, other])
    dc.add_link(link_hpc(dc))
    assert len(dc.external_links) == 4
    np.testing.assert_allclose(other[_cid(raster, HPC[1])], other[_cid(other, HPC[1])])


def test_world_links_into_the_sji_use_each_exposure_time(sns):
    """glue-core 1.27 inverts a time-dependent gWCS at exposure 0; glue_solar.glue_patches keeps the time."""
    sji, _ = sns
    frames = np.arange(sji.shape[0], dtype=float)
    lon, lat, time = sji.coords.pixel_to_world_values(10.0, 10.0, frames)
    points = Data(label="points", lon=lon, lat=lat, t=time)
    dc = DataCollection([sji, points])
    dc.add_link([LinkSame(points.id[k], _cid(sji, label)) for k, label in zip("lon lat t".split(), [*HPC, "Time (Utc)"])])
    np.testing.assert_allclose(points[sji.pixel_component_ids[2]], 10, atol=1e-6)
    np.testing.assert_allclose(points[sji.pixel_component_ids[1]], 10, atol=1e-6)


def test_link_hpc_leaves_datasets_in_other_units_alone(sns):
    import sunpy.data.test
    import sunpy.map

    from glue_solar.sources.maps import _parse_sunpy_map

    aia = _parse_sunpy_map(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia")
    assert set(aia.coords.world_axis_units) == {"deg"}
    assert len(link_hpc(DataCollection([*sns, aia]))) == 2


def test_wcs_autolink_does_not_crash_on_iris_data(sns):
    from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink

    assert len(wcs_autolink(DataCollection(list(sns)))) <= 1  # 0 on glue-core 1.27.0, 1 with the APE-14 autolinker


@pytest.mark.skipif(not AUTOLINKS_IRIS, reason="needs the APE-14 WCS autolinker (glue-viz/glue ape14-wcs-autolink)")
def test_wcs_autolink_pairs_iris_datasets(sns, irispy_test_files):
    from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, wcs_autolink
    from irispy.io import read_files
    from irispy.utils.moments import calculate_moments

    sji, raster = sns
    [link] = wcs_autolink(DataCollection([sji, raster]))
    assert isinstance(link, WCSLink)
    assert [c.label for c in link.cids1] == ["Pixel Axis 2 [x]", "Pixel Axis 1 [y]"]  # SJI x, y
    assert [c.label for c in link.cids2] == ["Pixel Axis 1 [y]", "Pixel Axis 0 [z]"]  # raster slit, step
    paths = sorted(p for p in irispy_test_files if "3860258481_raster_t000_r0000" in p.name)[:2]
    scan0, scan1 = raster_data(paths, ["Mg II k 2796"])
    assert len(wcs_autolink(DataCollection([scan0, scan1]))) == 1
    cube = read_files(paths[:1], spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"][0]
    velocity = _cube_data(calculate_moments(cube)["velocity"], "velocity")
    [scan0] = raster_data(paths[:1], ["Mg II k 2796"])  # a Data belongs to one DataCollection
    assert len(wcs_autolink(DataCollection([scan0, velocity]))) == 1


def test_browse_iris_links_what_it_loads(qtbot, tmp_path, irispy_test_files, monkeypatch):
    from glue_qt.app import GlueApplication

    for name in (SJI, RASTER):
        shutil.copy2(_real(irispy_test_files, name), tmp_path / name)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    # glue-qt pops a modal autolink dialog when glue suggests links (the APE-14 fork does); this test is about link_hpc
    monkeypatch.setattr("glue_qt.app.application.run_autolinker", lambda data_collection: None)

    def tick_everything_and_load(dialog):
        dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
        dialog.finalize()
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtIRISImporter, "exec", tick_everything_and_load)
    app = GlueApplication()
    browse_iris(app.session, app.data_collection)
    dc = app.data_collection
    assert len(dc) > 2  # the SJI and every raster window
    assert all(isinstance(link, LinkSame) for link in dc.external_links)
    assert len(dc.external_links) == 2 * (len(dc) - 1)
    viewer = app.viewers[0][0]
    viewer.figure.canvas.draw()
    assert viewer.axes.format_coord(18, 20).endswith("(world)")  # the patched inverse leaves WCSAxes readouts intact
    app.close()
```

The skipif gate, exactly: `import glue` + `from packaging.version import Version` (packaging is an astropy dependency, already installed) and `AUTOLINKS_IRIS = Version(glue.__version__) > Version("1.27.0")`. When the glue PR is released, tighten to the release (`>= Version("1.28.0")` or whatever ships) and cite the PR number in `reason`. Until then a pip-installed fork reports `1.27.1.dev20+g016d9cf2` (setuptools_scm defaults `guess-next-dev` + `node-and-date` on a clean tree, glue's `[tool.setuptools_scm]` sets only `version_file`; `git describe --tags ape14-wcs-autolink` = `v1.27.0-20-g016d9cf2`; NOT installed to keep the venv untouched) which is `> 1.27.0`, so the gate opens for anyone installing the branch; a `PYTHONPATH` worktree does not open it (metadata stays 1.27.0), hence the `glue.__version__` override in step 8. Known risk, accepted: the gate also opens for any glue-core release above 1.27.0 that does not contain the autolinker (a hypothetical 1.27.1 bugfix release), which would turn the skip into a CI failure; the day such a release appears, bump the gate to the version that ships the PR.

### 6. Runs

Full suite on stock glue-core 1.27.0 in the scratch copy:

```
$ HOME=<scratch>/home-wp1 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=<scratch>/wp1 .venv/bin/python -m pytest <scratch>/wp1/glue_solar -q -o addopts='' -p no:cacheprovider -W ignore -rs
.....................s................                                   [100%]
SKIPPED [1] glue_solar/tests/test_linking.py:138: needs the APE-14 WCS autolinker (glue-viz/glue ape14-wcs-autolink)
37 passed, 1 skipped in 7.97s
$ <scratch>/ruffpkg/bin/ruff check --config /Users/nabil/Git/glue-solar/.ruff.toml glue_solar/     # ruff 0.16.5
All checks passed!
$ <scratch>/ruffpkg15/bin/ruff check ... (ruff 0.15.20)
All checks passed!
```

(27 tests on the branch today + 11 new = 38; the one skip is the gated autolink test.)

Checker re-run (2026-09-02, fresh `HOME=<scratch>/home-wp1chk`, fresh detached worktree `wt-wp1chk-ape14` at 016d9cf2, removed afterwards): the suite, ruff at 0.16.1 (pre-commit pin) / 0.16.5 / 0.15.20 / 0.14.14, `wp1_inspect.py`, `wp1_timepatch.py`, `wp1_viewers.py` and `wp1_autolink.py` (stock and fork) all reproduced the outputs quoted in this section byte-for-byte, and `git log v1.27.0..{main,ape14-wcs-autolink,profile-wcs} -- glue/core/coordinate_helpers.py glue/core/component_link.py` is 0/0/0.

All linking tests against the fork worktree (glue `ape14-wcs-autolink` at 016d9cf2, `--detach` worktree, gate forced open; the Qt browse test runs too because it replaces `glue_qt.app.application.run_autolinker` with a no-op, see Pitfalls):

```
$ HOME=... QT_QPA_PLATFORM=offscreen MPLBACKEND=agg PYTHONPATH=<scratch>/wt-wp1chk-ape14:<scratch>/wp1 .venv/bin/python -c "
import glue; assert 'wt-wp1chk-ape14' in glue.__file__; glue.__version__ = '1.27.1.dev20+g016d9cf2'
import pytest, sys; sys.exit(pytest.main(['<scratch>/wp1/glue_solar/tests/test_linking.py', '-q', '-o', 'addopts=', '-p', 'no:cacheprovider', '-W', 'ignore', '-rs']))"
...........
11 passed in 5.83s
```

The three ways of running that browse test on the fork (`wp1chk_browse_fork.py`, `perl -e 'alarm 75; exec @ARGV'` as the timeout): without the no-op the process prints nothing and is killed at 75 s (the modal `exec_()`); with `settings.AUTOLINK["Astronomy WCS"] = "always_accept"` it fails at `assert all(isinstance(link, LinkSame) for link in dc.external_links)` (the accepted `WCSLink` is in `external_links`); with the `run_autolinker` no-op it passes in 1 s.

Autolink proof, same script on both glues (`wp1_autolink.py`; datasets rebuilt per pair; `direct` = calling `WCSLink(a, b)` by hand):

```
=== stock glue 1.27.0
glue from /Users/nabil/Git/glue-solar/.venv/lib/python3.14/site-packages/glue/__init__.py metadata version 1.27.0
  SJI<->raster       autolink=0 direct=AttributeError: '_GlueWCS' object has no attribute 'has_celestial'
  raster<->raster    autolink=0 direct=AttributeError: '_GlueWCS' object has no attribute 'has_celestial'
  raster3D<->map2D   autolink=0 direct=AttributeError: '_GlueWCS' object has no attribute 'has_celestial'
  map2D<->map2D      autolink=0 direct=AttributeError: '_GlueWCS' object has no attribute 'has_celestial'

=== fork ape14-wcs-autolink (016d9cf2)
glue from <scratch>/wt-wp1-ape14/glue/__init__.py metadata version 1.27.0
  SJI<->raster       autolink=1 direct=WCSLink ok cids ['Pixel Axis 2 [x]', 'Pixel Axis 1 [y]'] <-> ['Pixel Axis 1 [y]', 'Pixel Axis 0 [z]']
  raster<->raster    autolink=1 direct=WCSLink ok cids ['Pixel Axis 2 [x]', 'Pixel Axis 1 [y]', 'Pixel Axis 0 [z]'] <-> ['Pixel Axis 2 [x]', 'Pixel Axis 1 [y]', 'Pixel Axis 0 [z]']
  raster3D<->map2D   autolink=1 direct=WCSLink ok cids ['Pixel Axis 1 [y]', 'Pixel Axis 0 [z]'] <-> ['Pixel Axis 1 [x]', 'Pixel Axis 0 [y]']
  map2D<->map2D      autolink=1 direct=WCSLink ok cids ['Pixel Axis 1 [x]', 'Pixel Axis 0 [y]'] <-> ['Pixel Axis 1 [x]', 'Pixel Axis 0 [y]']
```

Same check with a sunpy-map dataset (`_parse_sunpy_map(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia")`, astropy WCS in degrees; `wp1chk_aia.py`, checker run):

```
=== fork ape14-wcs-autolink (016d9cf2)
raster<->AIA(astropy WCS, deg): autolink=1 direct=ok cids ['Pixel Axis 1 [y]', 'Pixel Axis 0 [z]'] <-> ['Pixel Axis 1 [x]', 'Pixel Axis 0 [y]']
sji<->AIA(astropy WCS, deg): autolink=1 direct=ok cids ['Pixel Axis 2 [x]', 'Pixel Axis 1 [y]'] <-> ['Pixel Axis 1 [x]', 'Pixel Axis 0 [y]']
=== stock glue 1.27.0
raster<->AIA(astropy WCS, deg): autolink=0 direct=AttributeError: '_GlueWCS' object has no attribute 'has_celestial'
sji<->AIA(astropy WCS, deg): autolink=0 direct=AttributeError: '_GlueWCS' object has no attribute 'has_celestial'
```

So with the coherent `_GlueWCS` the fork also links IRIS data to a plain sunpy map (`WCSLink` converts units itself); the critic's worry that the fork's SkyCoord path needs to catch `ValueError` for raster<->AIA (critic section 4, P2.4) does not arise once WP1 is in. `link_hpc` still skips sunpy maps (LinkSame does not convert deg to arcsec).

Stock glue: `wcs_autolink` returns 0 links and does not raise (it never reaches `WCSLink` for low-level coords); only a *direct* `WCSLink(...)` call raises on 1.27.0, so never call it directly. Fork: all four pairs link, which with the stock `_GlueWCS` was 1/4 (SJI<->raster only; ape14 P3.1-sec4, cc_forkmap.py). raster3D<->map2D links slit/step to the map's x/y, so on the fork the moments WP gets its source<->map link for free (D2/critic section 2).

Display units reach the viewers, and the high-level API works for the 4D stack (compound WCS) and 2D moment map too (`wp1_viewers.py`, stock glue, offscreen glue-qt):

```
4D stack: units ('Angstrom', 'arcsec', 'arcsec', '') | low-level [1332.829, 279.533, 491.968, 1.0] | SkyCoord Tx,Ty arcsec 491.968,279.533 | round trip [3.0, 50.0, 4.0, 1.0]
2D moment map: units ('arcsec', 'arcsec') | low-level [279.533, 491.968] | SkyCoord Tx,Ty arcsec 491.968,279.533 | round trip [50.0, 4.0]
raster ImageViewer default axes: Wavelength / Helioprojective Latitude | format_coord(10, 20): 1398.9 −400" −52.87" (world) | xlabel: Wavelength
ProfileViewer x=Wavelength range: 1398.63 1399.34 | x_display_unit: Angstrom
SJI ImageViewer axes: Helioprojective Longitude / Helioprojective Latitude | format_coord(18, 20): −53" −400" (world)
```

## Tests to add

All in `glue_solar/tests/test_linking.py` (file above). Fixture: real irispy 0.8.1 test files via the session fixture `irispy_test_files` from `glue_solar/conftest.py`; the `sns` pair = `sns/iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits` (62, 40, 37) + `sns/..._raster_t000_r00000.fits` window `Si IV 1403` (187, 40, 29); the multi-scan raster = `iris_l2_20140329_140938_3860258481_raster_t000_r0000{0,1}.fits` window `Mg II k 2796`. The synthetic `iris_tree` fixture is not used (its zero-filled cubes carry no WCS worth linking).

| test | asserts |
| --- | --- |
| `test_wavelength_axis_is_in_angstrom` | `world_axis_units == ("Angstrom", "arcsec", "arcsec")`; `Wavelength` component `.units == "Angstrom"`; values in 1380-1420; `pixel_to_world_values(3,20,50)[0] == inner * 1e10`; inverse round trip `abs=1e-4` |
| `test_sji_and_raster_share_axis_names` | SJI labels `['Time (Utc)', 'Helioprojective Latitude', 'Helioprojective Longitude']`; raster `['Helioprojective Longitude', 'Helioprojective Latitude', 'Wavelength']` |
| `test_high_level_api_round_trips_in_display_units[sji,raster]` | `HighLevelWCSWrapper(data.coords).pixel_to_world` gives a SkyCoord whose `Tx/Ty` in arcsec equal the low-level values; raster spectral object `.to_value(u.AA)` equals the low-level value; `world_to_pixel(*objects)` returns the pixel (`abs=1e-4`) |
| `test_link_hpc_pairs_lon_lat_by_physical_type` | 2 `LinkSame`; second call `[]`; cross-evaluated lon/lat equal; raster ROI -> SJI mask non-trivial; SJI lon inequality -> raster mask non-trivial; SJI pixel ROI -> raster raises `IncompatibleAttribute` |
| `test_link_hpc_chains_every_dataset_through_the_first` | SJI + 2 windows: 4 external links; window B evaluates window A's latitude cid |
| `test_world_links_into_the_sji_use_each_exposure_time` | SJI pixel (10, 10) at all 62 exposures, linked back via lon/lat/`Time (Utc)`, derives x == y == 10 (`atol=1e-6`); fails without `glue_patches` (x = 134/264 at frames 30/61) |
| `test_link_hpc_leaves_datasets_in_other_units_alone` | sunpy AIA test map (deg) in the collection: still exactly 2 links |
| `test_wcs_autolink_does_not_crash_on_iris_data` | `len(wcs_autolink(dc)) <= 1` (0 on 1.27.0, 1 on the fork) |
| `test_wcs_autolink_pairs_iris_datasets` (skipif gate) | SJI<->raster: one `WCSLink`, cids `[x, y] <-> [y(slit), z(step)]`; raster scan0<->scan1: 1; raster3D<->velocity map: 1 |
| `test_browse_iris_links_what_it_loads` (Qt, `qtbot`) | `QFileDialog.getExistingDirectory`, `QtIRISImporter.exec` and `glue_qt.app.application.run_autolinker` (no-op) monkeypatched; after `browse_iris`: `len(dc) > 2`, all external links `LinkSame`, count `2 * (len(dc) - 1)`; the SJI viewer's `format_coord(18, 20)` ends with `(world)` |

## Pitfalls (verified)

- A `Data` belongs to one `DataCollection`: reusing one in a second collection raises `AttributeError: Data has already been assigned to a different hub` (glue `data.py:1398`). Hit today in the proof scripts and in the first version of the gated test; rebuild datasets per collection.
- astropy `high_level_objects_to_values` (`high_level_api.py:254`) re-runs the class constructor on objects the caller already built. A converting constructor must pass `isinstance(value, cls)` through untouched, otherwise `world_to_pixel` for the raster returned x = -54977 instead of 3 (seen, fixed).
- The spectral object class has no `unit` kwarg (4-tuple with a closure); only constructor wrapping can put wavelength in Angstrom. The celestial `unit` kwarg is left alone on purpose: values are converted back to the stored unit before the original constructor sees them.
- `HighLevelWCSWrapper.pixel_to_world` returns a bare `SkyCoord` (not a list) for a 2D map; a scalar `SkyCoord` is not iterable (`astropy/utils/shapes.py:281`). Wrap in a list when writing generic checks.
- -TAB inverse precision is ~1.5e-6 px (float32 lookup table): `pytest.approx(..., abs=1e-6)` fails, use `1e-4` (the existing stack test already uses `atol=3e-6`).
- glue title-cases world labels (`coordinate_helpers.axis_label`, line 189 `.title()`): irispy's `Time (UTC)` shows as `Time (Utc)`; `Helioprojective Longitude` survives.
- An all-ones `axis_correlation_matrix` on the SJI wrapper makes glue-qt `ImageViewer.format_coord` raise `OverflowError` on every mouse move (astropy `wcsaxes/formatter_locator.py:642`; `v_qt.py PATCH=1`, slit-overlay verifier, critic). The `world2pixel_single_axis` wrap leaves the matrix alone (`[[1,1,1],[1,1,1],[0,0,1]]` printed above) and `format_coord` keeps returning `−53" −400" (world)`.
- On the fork glue, `GlueApplication.add_datasets` -> `run_autolinker` -> `AutoLinkPreview.suggest_links` opens a modal `exec_()` dialog whenever links are suggested and `settings.AUTOLINK[...] == 'always_show'` (glue-qt `dialogs/autolinker/autolinker.py:80-84`). Offscreen this blocks (verified: the browse test without the no-op prints nothing and had to be killed at 75 s on the fork). `settings.AUTOLINK["Astronomy WCS"] = "always_accept"` is NOT a fix for this test: the accepted `WCSLink` lands in `dc.external_links` and the LinkSame-only assertion fails (verified). The test therefore does `monkeypatch.setattr("glue_qt.app.application.run_autolinker", lambda data_collection: None)` (`application.py:23` imports it by name, `:1446` calls it); it passes on 1.27.0 and on the fork.
- `LinkSame` between a `_GlueWCS` dataset (arcsec) and a raw sunpy-map dataset (deg, `maps.py:27`) would be silently wrong by 3600x; `link_hpc` therefore only takes `_GlueWCS` coords (test `..._leaves_datasets_in_other_units_alone`).
- Never call `WCSLink(a, b)` directly on glue-core 1.27.0 with `_GlueWCS` coords: `AttributeError: '_GlueWCS' object has no attribute 'has_celestial'` (`wcs_autolinking.py:146-158`). `wcs_autolink` is safe (0 links).
- irispy 0.8.1 ships two copies of `iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits`; the `raster/` copy fails `read_files` (slit-overlay verifier). Select by `path.parent.name == "sns"` as `_real` does.
- ruff (repo config selects E, F, W, UP, PT, I): PT018 rejects compound `assert a and b`; E731 rejects lambda assignment (hence nested `def convert`); isort sections put `astropy` and `sunpy` in their own blocks.
- `glue.__version__` is `importlib.metadata.version("glue-core")`, so a worktree on `PYTHONPATH` keeps reporting 1.27.0; the gated test only opens for an installed build (or with the override in step 8).
- The irispy 0.8.1 test SJI headers are stride-10 decimations and the SNS one has an inconsistent `CDELT1` (repaired in irispy main bc5e39e, slit-overlay verifier): do not hard-code slit pixel positions like 21.05/20.62/21.24 in tests; compare against the WCS itself, as the time test does.

## Acceptance criteria

- [ ] `pytest glue_solar` on glue-core 1.27.0: 37 passed, 1 skipped (`test_wcs_autolink_pairs_iris_datasets`); `ruff check glue_solar` clean with ruff 0.16.1 (pre-commit pin); pre-commit (codespell, trailing whitespace) clean.
- [ ] Raster/stack `world_axis_units` start with `"Angstrom"`; the `Wavelength` component has units `Angstrom`; ImageViewer readout on a raster shows wavelength like `1398.9`, ProfileViewer `x_display_unit` is `Angstrom` (run above).
- [ ] SJI, raster, stack and moment-map datasets all expose `Helioprojective Longitude` / `Helioprojective Latitude`; SJI keeps `Time (Utc)`.
- [ ] `HighLevelWCSWrapper(data.coords).pixel_to_world` / `world_to_pixel` round-trip for SJI (gWCS), raster (-TAB), stack (compound) and 2D map, with SkyCoord in arcsec and the spectral object convertible to Angstrom (runs above).
- [ ] With glue `ape14-wcs-autolink` on the path: SJI<->raster, raster<->raster, raster3D<->map2D, map2D<->map2D (and raster/SJI<->sunpy AIA map) each autolink to exactly 1 `WCSLink` (runs above); all 11 tests in `test_linking.py` pass with the gate forced open, the Qt browse test included (11 passed above).
- [ ] `link_hpc(dc)` returns 2 `LinkSame` for an SJI+raster pair, `[]` on repeat, links every `_GlueWCS` dataset to the first one, ignores non-`_GlueWCS` data.
- [ ] `browse_iris` adds the links after loading (Qt test); `Plugins -> IRIS: link helioprojective coordinates` exists and links File -> Open loads (`test_setup_registers_hooks`-style check optional: `"IRIS: link helioprojective coordinates" in [label for label, _ in menubar_plugin]`).
- [ ] `glue_solar.glue_patches` is imported by `glue_solar/__init__.py`; the time test passes and `format_coord` still works with the patch active.
- [ ] Docs and changelog updated as below; the user guide no longer says "Glue does not currently autolink" without the version qualifier, and no longer asks users to pair names the SJI does not have.

## Dropped / out of scope

- All-ones `axis_correlation_matrix` on the SJI wrapper: breaks WCSAxes `format_coord` (critic decision; slit-overlay verifier).
- A raster `Time` -> SJI `Time (Utc)` link (what would make SJI-drawn ROIs reach the raster): needs a per-SJI reference epoch; closure links do not serialise, the component-based nearest-index form is the sync-slicing WP (critic `cc_timelink.py`).
- Wrapping sunpy maps (`maps.py:27`) in `_GlueWCS` so AIA context maps join `link_hpc` and get arcsec: SDO-context WP; here they are simply skipped.
- Upstream PR for `world2pixel_single_axis`: file it after this lands (the patched function body is the PR); D2 says tiny glue-core bug fixes go upstream only after glue-solar works around them.
- Feature-detecting the autolinker (`hasattr(wcs_autolinking, "kept_numpy_axes")`) instead of the version gate: private helper name, may change in review; the version gate is what was asked for.
- Linking the wavelength axis between raster windows: different windows do not overlap in wavelength; nothing to gain.
- Renaming the SJI time axis to `Time`: would collide with the datetime64 `Time` component later WPs add to SJIs and rasters already have.
- Session serialisation of `_GlueWCS` (its `__gluestate__`): sessions WP; this WP does not make sessions worse (`_GlueWCS` was already unserialisable). Same for the fork's `WCSLink` between `_GlueWCS` datasets: `clone(link)` raises `GlueSerializeError` because glue-core only has `@saver(astropy WCS)` (`glue/core/state.py:655`; ape14 P3.1-sec3 verifier), a pre-existing gap the sessions WP covers.
- Autolinking IRIS data to sunpy maps: nothing to do here; on the fork it already works with the coherent `_GlueWCS` (run above), on stock glue nothing autolinks. Only `link_hpc` (LinkSame, no unit conversion) excludes sunpy maps.
- ruff-driven cosmetic changes elsewhere in the touched files: none needed (both files are clean).

## Docs

`docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`:

- Line 31-32 ("The data are added to the data collection and the first slit-jaw (or AIA) cube is opened in an Image Viewer; use its slider to step through time.") append: "Helioprojective coordinates are shown in arcseconds and wavelengths in Angstrom for every IRIS dataset, whatever the file stores."
- Replace the Linking section (lines 54-59) with:

```rst
Linking
-------

Every dataset loaded by ``glue-solar`` exposes the same ``Helioprojective Longitude`` and
``Helioprojective Latitude`` world components, in arcseconds. The browser links them across everything
it loads, so a subset defined on those coordinates, or drawn on a raster map, shows up on the slit-jaw
images and on every other raster window. Data opened through "File -> Open Data Set" are linked the same
way with "Plugins -> IRIS: link helioprojective coordinates" (running it again is harmless). If you prefer
the Data Manager's link editor, pair those two components; the names are identical on all datasets.

Two limits apply with the released glue-core 1.27. A region drawn on a slit-jaw image cannot be transferred
to a raster, because the slit-jaw pointing changes from exposure to exposure and the raster carries no
slit-jaw exposure time; select on world coordinates or on the raster instead. And glue's own WCS
autolinker only handles astropy WCS objects, so it offers no pixel links for IRIS data; once a glue-core
release contains the APE-14 autolinker (glue-viz/glue branch ``ape14-wcs-autolink``) it will additionally
offer pixel-to-pixel links between slit-jaw images, rasters and derived maps. Those are exact at the first
slit-jaw exposure and complement, not replace, the coordinate links above.
```

- `changelog/44.feature.rst`: "helioprojective coordinates are shown in arcseconds" -> "helioprojective coordinates are shown in arcseconds and wavelengths in Angstrom" (only if this lands in #44; otherwise leave #44 alone and put everything in the new fragment).
- New `changelog/<PR>.feature.rst`: "IRIS datasets now share one set of world component names (``Helioprojective Longitude``/``Latitude``, ``Wavelength``) in arcseconds and Angstrom, work with astropy's high-level WCS API (so glue's WCS autolinker can pair them once it supports APE-14 WCS), and the observation browser links their helioprojective coordinates automatically; "Plugins -> IRIS: link helioprojective coordinates" does the same for files opened through File -> Open."
- New `changelog/<PR>.bugfix.rst`: "World-coordinate links into a slit-jaw cube now use each exposure's own pointing instead of the first exposure's (works around glue-core ``world2pixel_single_axis`` collapsing uncorrelated world axes)."
- `IRIS_GLUE_GAP_PLAN.md` (untracked planning doc): Phase 1.4 text "deleted once Phase 3's autolink work lands upstream", Phase 3.1 "removes Phase 1 item 4" and order-of-attack row 2 "deletes Phase 1.4" -> "kept; autolink adds the pixel link" (D1). Phase 3.1 note: "raster<->raster and raster<->map autolink also need the glue-solar ``_GlueWCS`` coherence fix (WP1)". `~/Git/glue/APE14_AUTOLINK_TODO.md` section 4 bullets 2-3: coherence fix done in glue-solar WP1; regression test = `test_wcs_autolink_pairs_iris_datasets`; delete-helper bullet dropped.
- No change to `guide-to-glue-1dprofile-viewer-for-iris-data.rst` (axis name `Wavelength` unchanged; optionally add "(in Angstrom)" at line 41).


---

# WP2 - Moment maps action (`IRIS: line moments…`)

**Goal.** Add a right-click dataset action to glue-solar that runs `irispy.utils.moments.calculate_moments` on one per-scan IRIS raster window and adds the five moment maps as ONE 2D dataset, pixel-linked to its source. No loader changes, no new dependencies, no upstream work, no viewer opened.

## Current state (2026-09-02)

- glue-solar has nothing: `grep -rn -i moment glue_solar docs/*.rst docs/user_guide/*.rst changelog` returns 0 hits (run today).
- Branch `iris-observation-browser` = PR glue-viz/glue-solar#44: `gh pr view 44 --json state,reviewDecision,statusCheckRollup` today (checker re-run, real HOME): `state OPEN`, `reviewDecision ""`, 21 check rows all `SUCCESS`/`SKIPPED` (one `null` conclusion row). Commits on top of main: 742c508, da17fa3, d3a2bd3. WP2 branches from this branch (or from main once #44 merges).
- Baseline suite today: `HOME=<scratch> QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest glue_solar -q -o addopts='' -p no:cacheprovider` -> `27 passed, 2 warnings in 1.66s` (checker re-run: `27 passed, 2 warnings in 1.74s`; `-o addopts=''` because `pytest-doctestplus` is not installed in the venv; `pytest.ini:23` `--doctest-rst` needs it; `pytest.ini:26-28` `filterwarnings = error`).
- Loader pieces WP2 reuses, all in `/Users/nabil/Git/glue-solar/glue_solar/sources/loaders/iris.py`:
  - `_GlueWCS(BaseWCSWrapper)` :35-69. `data.coords._wcs` is the raw irispy WCS (today: `WCS ['m','deg','deg'] ['WAVE','HPLT-TAB','HPLN-TAB']` for the sns raster; the wrapper reports `('m','arcsec','arcsec')`). WP1 (D3) will make the wrapper report `Angstrom` and convert; `_wcs` stays raw metres.
  - `_cube_data(cube, label, *, color=None, cmap=None)` :72-85: `data.coords = _GlueWCS(cube.wcs.low_level_wcs)`, `data.meta = cube.meta`, main component named `label`, `f"{label} mask"` when the cube has a mask, `Time` component from the `time` extra coord.
  - `_raster_collection_data` :93-107: per-scan datasets are 3D `(step, slit, wavelength)` with `SGMeta` meta; stacked datasets are 4D `ndcube.NDCube` with `meta=dict(...)` (`stack_spectrograms.py:80`).
- Registration pattern: `glue_solar/__init__.py:5` `from glue_solar.sources import iris, maps` (import = registration); `glue_solar/sources/iris.py:30` `@menubar_plugin("IRIS: browse observations…")`; `tests/test_plugin.py:9-15` asserts the hooks.
- irispy 0.8.1 (installed, `.venv/lib/python3.14/site-packages/irispy`): `utils/moments.py:33-35` `calculate_moments(cube, *, rest_wavelength=None, wings=None, integrated=False, min_intensity=None, saturation_limit=None)`; :100-104 auto rest from `cube.meta.rest_wavelength` (`meta.py:194-198`: `float(TWAVE{_iwin}) * u.AA -> nm`); :112-125 wings crop, raises `ValueError("No wavelength points found within the specified wings")`; :181-209 returns `RasterCollection` of 2D `SpectrogramCube`s keyed `intensity, centroid, width` (+ `velocity, velocity_width` when a rest wavelength is known). `utils/_spectral.py:49-75` `make_spatial_template` slices wavelength index 0, so the maps share the source's `(step, slit)` pixel grid exactly. Shipped since irispy 0.7.0 (audit), glue-solar pins `>=0.8.1` (`pyproject.toml:22`). `moments.py:109` converts the cube's wavelengths to nm whatever the WCS unit, so the rewrap works with a raw WCS in m or Angstrom. `moments.py:161-166` accepts `min_intensity` as a Quantity and converts it to the zeroth-moment unit (`DN nm` when `integrated=True`, `moments.py:146-151`); `saturation_limit` is compared in `cube.unit` (`:168-171`).
- glue-qt (editable, `/Users/nabil/Git/glue-qt`): `glue_qt/config.py:114-152` `LayerActionRegistry.__call__(label, callback=None, tooltip=None, icon=None, single=False, data=False, subset_group=False, subset=False)` used as a decorator; `glue_qt/app/layer_tree_widget.py:481-486` `UserAction._do_action` calls `callback(layer, data_collection)` — no session, no application. `glue.config.layer_action is glue_qt.config.layer_action` -> `True` (glue/config.py:950-951 re-export). The editable install's metadata string is `0.1.dev6892+ga9c8a0640` (stale, from an earlier macos-integration commit); the code that runs is the working tree at `bd4dce6b9` (macos-integration HEAD today).
- glue-core 1.27 Image viewer: `ImageLayerState.attribute_display_unit` (`glue/viewers/image/state.py:500, 629-642`) offers display-unit choices only for units astropy can parse on its own; `DN_IRIS_NUV nm` is not parseable outside irispy's `add_enabled_units` context, so wavelength-bearing outputs are converted to Angstrom at source (D3) instead of relying on the viewer.
- Audit findings this brief implements: `findings/science-moments.json` P2.1, P2.1-link, P2.1-stack, P2.3a, P2.3b (all verifier-agreed); `critic.md` §2 "Cube-handle prerequisite ... unnecessary (cc_rewrap.py)", §2 "P2.1 UI hook", §3.1 Collapse tab, §5 "Moments-only first PR".

## Decisions already made

- D2: ships entirely in glue-solar through `glue_qt.config.layer_action`. No glue-core/glue-qt change.
- D3: Angstrom in AND out. The dialog takes Angstrom everywhere (rest wavelength, wings); values become `astropy` Quantities (`* u.AA`) before reaching irispy. irispy returns `centroid`/`width` in nm and the integrated intensity in `DN nm`; the module converts every map with `_in_angstrom` (`NDCube.to`, replaces the `nm` base by `Angstrom`, verified below) so the stored components are `Angstrom`, `Angstrom`, and `Angstrom DN_IRIS_<band>`; `km / s` maps are untouched. With `integrated=True` the minimum-intensity threshold is passed as a Quantity in `DN Angstrom` (irispy would otherwise compare the typed number against `DN nm`, a silent factor 10). The rewrap passes `data.coords._wcs` (raw irispy WCS, metres today) and irispy converts to nm internally (`moments.py:109`), so WP2 does not care whether `_GlueWCS` reports metres or Angstrom and never reads wavelengths through `data.coords`. (Checker correction 2026-09-02: the writer's version left `nm` outputs, contradicting D3 and its own checkbox label.)
- D4: `layer_action("IRIS: line moments…", single=True, data=True)`, callback `(layer, data_collection)`. The result is appended to the data collection; NO viewer is opened (the callback has no application handle anyway; `Session.application` is a weakref never passed, critic §2).
- Audit-settled (do not reopen):
  - No loader cube handle. Rewrap the glue Data into a `SpectrogramCube` (verified recipe below). Zero loader changes (critic §2, `cc_rewrap.py`).
  - ONE Data per run, five maps as components, plus the first map's mask and the source's `Time`. Not five datasets; not components on the 3D source (`add_component` of a 2D array on a 3D Data raises `ValueError`, P2.1-link).
  - Two `LinkSame` links on pixel components 0 and 1 (step, slit). `wcs_autolink` returns `[]` for every pairing on glue-core 1.27 (`_GlueWCS` is a `BaseLowLevelWCS`, filtered out at `wcs_autolinking.py:320-321`), so links must be explicit. On the fork + the `_GlueWCS` coherence fix they would become automatic (critic §2); the explicit links stay harmless.
  - Build the Data without storing intensity twice (verifier nit on P2.1): `_cube_data(first_map, "intensity")` then relabel the Data, not `_cube_data(first, label)` + `add_component("intensity")`.
  - v1 = per-scan datasets only. A 4D stack (dict meta, no `wavelength_axis`, no `rest_wavelength`) and any non-raster dataset get one clear `ValueError` shown in a message box. The wrap recipe for stacks is recorded under "Dropped" for a follow-up.
  - Tests use the real irispy sns raster with an EXPLICIT in-window rest wavelength (every window of both irispy test rasters excludes its TWAVE; auto rest + wings raises).
  - `density_diagnostic` is de-scoped (fiasco + CHIANTI, arrays-in/dict-out). Red-blue asymmetry is a follow-up second `layer_action` on the same skeleton.
  - Rest wavelength blank in the dialog = irispy's default (auto TWAVE via `SGMeta.rest_wavelength`). Wings blank = whole window. Exactly one wing filled = error.

## Dependencies / order

- Code dependencies: none. Runs on released glue-core 1.27.0 + glue-qt main + irispy 0.8.1 (all verified today). Independent of WP1 (WP1 edits `_GlueWCS` only; WP2 uses `_wcs` and Quantities; the WP1 brief did not exist yet when this brief was checked, and irispy's own nm conversion makes WP2 robust to any raw-WCS unit). Independent of the fork branches.
- Branch base: on top of PR #44 (`iris-observation-browser`) or main after #44 merges. The loader functions it imports (`_cube_data`, `raster_data`) exist on that branch.
- Unblocks: WP-RBA (second `layer_action`, same `MomentsDialog` shape, "Dropped" section), the "prefill wings from the Profile viewer Collapse range" follow-up, and any WP that wants a 2D map dataset linked to a raster (e.g. Gaussian fit maps reuse `_cube_data(first, name)` + relabel + 2 `LinkSame`).

## Files to touch

- `glue_solar/sources/moments.py` (NEW, 107 lines, verified text below): `line_moments()`, `MomentsDialog`, `moments_action` registered with `@layer_action`.
- `glue_solar/__init__.py`: line 5 `from glue_solar.sources import iris, maps` -> `from glue_solar.sources import iris, maps, moments`; line 9 `__all__` add `"moments"`. Importing the module is what registers the action.
- `glue_solar/tests/test_moments.py` (NEW, verified text below, 5 tests, real sns raster + real 2014 raster stack + real SJI).
- `glue_solar/tests/test_plugin.py::test_setup_registers_hooks`: add `assert "IRIS: line moments…" in [item.label for item in layer_action]` (import `layer_action` from `glue.config` next to `menubar_plugin` on line 1).
- `docs/user_guide/line-moments-of-a-raster-window.rst` (NEW) and `docs/user_guide/index.rst` toctree (add after `guide-to-glue-1dprofile-viewer-for-iris-data`).
- `docs/api_reference.rst`: add `.. automodapi:: glue_solar.sources.moments` / `:no-inheritance-diagram:` (docs/api stubs are gitignored, `.gitignore:77-78`, generated at build).
- `changelog/<PR>.feature.rst` (NEW).
- Optional one-liners in the untracked planning docs (see Docs).

## Step-by-step

1. `git switch -c iris-line-moments iris-observation-browser` (or main after #44 merges).
2. Create `glue_solar/sources/moments.py` with the verified module text below, verbatim. Keep the label `"IRIS: line moments…"` with the same `…` character as `browse_iris` (`sources/iris.py:30`).
3. Edit `glue_solar/__init__.py`: import `moments` alongside `iris, maps`; add to `__all__`.
4. Create `glue_solar/tests/test_moments.py` from the verified test text (identical to `scratchpad/chk_wp2/test_wp2_moments.py`), replacing the import line `from wp2_moments_module import MomentsDialog, line_moments` with `from glue_solar.sources.moments import MomentsDialog, line_moments` and deleting the local `irispy_test_files` fixture (the repo's `glue_solar/conftest.py:94-100` provides it).
5. Extend `test_plugin.py::test_setup_registers_hooks` with the `layer_action` assertion.
6. Run `HOME=<scratch dir> QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python -m pytest glue_solar -q -o addopts=''` (scratch HOME so glue never writes `~/.glue/settings.cfg`) -> expect 27 + 5 = 32 passed (plus the extended plugin test). The repo `pytest.ini` turns warnings into errors; the verified tests pass under it.
7. Run ruff with the repo config: `ruff check --config .ruff.toml glue_solar/sources/moments.py glue_solar/tests/test_moments.py` -> `All checks passed!` (verified today on the module and on the test file with the repo import line, ruff 0.16.5; pre-commit pins v0.16.1). Run `pre-commit run --all-files` if available (codespell, sphinx-lint, trailing whitespace).
8. Docs: add the user-guide page and toctree entry, the `automodapi` block, the changelog fragment (texts in Docs). Build with `sphinx-build -W` if the docs extra is installed (`tox -e build_docs`).
9. Manual smoke (optional): `glue`, Plugins -> IRIS: browse observations…, load one raster window, right-click the dataset in the data collection -> "IRIS: line moments…", press OK, drag the `...-moments` dataset onto the canvas as 2D Image and pick `velocity`. The action is disabled for subsets and hidden for multi-selection (`single=True, data=True`).
10. Open the PR with the changelog fragment named after its number.

## Verified code

All runs today (2026-09-02) with `HOME=<scratch>/home-wp2 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg` and `/Users/nabil/Git/glue-solar/.venv/bin/python` (glue-core 1.27.0 site-packages, glue-qt editable `0.1.dev6892+ga9c8a0640`, irispy 0.8.1). Scratch files: the CORRECTED (Angstrom) module and tests are `scratchpad/chk_wp2/wp2_moments_module.py` and `scratchpad/chk_wp2/test_wp2_moments.py` (checker, 2026-09-02); the writer's pre-Angstrom originals `scratchpad/wp2_moments_module.py`, `scratchpad/test_wp2_moments.py` and `scratchpad/wp2_moments_proto.py` (module + extra checks) are still there and SHADOW the corrected module when a script runs with the scratchpad root as cwd (cwd is first on `sys.path`; the checker hit this). Run from `scratchpad/chk_wp2/`. `scratchpad/wp2_collapse_reach.py` is unaffected.

### The module (`glue_solar/sources/moments.py`), ruff-clean against `.ruff.toml`

```python
"""
Line moments of an IRIS raster window, computed by irispy and added as one linked 2D dataset.
"""

import numpy as np
from glue.core.component import Component
from glue.core.link_helpers import LinkSame
from glue_qt.config import layer_action
from irispy.spectrograph import SpectrogramCube
from irispy.utils.constants import DN_UNIT
from irispy.utils.moments import calculate_moments
from qtpy import QtWidgets

import astropy.units as u

from glue_solar.sources.loaders.iris import _cube_data

__all__ = ["MomentsDialog", "line_moments", "moments_action"]


def _in_angstrom(cube):
    """D3: wavelengths in Angstrom. irispy reports nm (centroid, width) and DN nm (integrated intensity)."""
    unit = cube.unit
    return cube.to(u.CompositeUnit(1, [u.AA if base == u.nm else base for base in unit.bases], unit.powers))


def line_moments(data, *, rest_wavelength=None, wings=None, integrated=False, min_intensity=None, saturation_limit=None):
    """Run irispy's ``calculate_moments`` on one per-scan raster window; return one 2D Data with five components."""
    if data.ndim != 3 or "em.wl" not in data.coords.world_axis_physical_types:
        msg = "Line moments need a per-scan raster window (raster step, slit, wavelength). Load scans without stacking."
        raise ValueError(msg)
    cid = data.main_components[0]
    mask_cid = data.find_component_id(f"{cid.label} mask")
    with u.add_enabled_units(list(DN_UNIT.values())):  # DN_IRIS_* are irispy-defined units
        cube = SpectrogramCube(data[cid], data.coords._wcs, None, u.Unit(data.get_component(cid).units), data.meta,
                               mask=None if mask_cid is None else data[mask_cid])
        if integrated and min_intensity is not None:
            min_intensity = min_intensity * cube.unit * u.AA  # the integrated zeroth moment is DN Angstrom, not DN
        maps = calculate_moments(cube, rest_wavelength=rest_wavelength, wings=wings, integrated=integrated,
                                 min_intensity=min_intensity, saturation_limit=saturation_limit)
        maps = [(name, _in_angstrom(cube)) for name, cube in maps.items()]
    (first_name, first), *rest = maps
    result = _cube_data(first, first_name)  # component named after the map; coords, mask and Time come for free
    result.label = f"{data.label}-moments"
    for name, cube in rest:
        result.add_component(Component(np.asarray(cube.data), units=str(cube.unit)), name)
    if data.find_component_id("Time") is not None:  # the rewrap drops irispy's time extra coord; copy the loader's per-step times
        result.add_component(data["Time"][..., 0], "Time")
    return result


def _number(line_edit):
    text = line_edit.text().strip()
    return float(text) if text else None


class MomentsDialog(QtWidgets.QDialog):
    """Ask for the calculate_moments parameters, run, add the result to the data collection and link it."""

    def __init__(self, data, data_collection, parent=None):
        super().__init__(parent)
        self.data, self.data_collection, self.moments = data, data_collection, None  # not 'result': QDialog.result() is a method
        self.setWindowTitle(f"Line moments of {data.label}")
        self.rest, self.low, self.high, self.minimum, self.saturation = (QtWidgets.QLineEdit() for _ in range(5))
        self.integrated = QtWidgets.QCheckBox("Integrate over wavelength (unit DN Angstrom) instead of summing (DN)")
        try:
            self.rest.setText(f"{data.meta.rest_wavelength.to_value(u.AA):.2f}")
        except (AttributeError, TypeError, ValueError):
            pass  # no TWAVE (or dict meta): the user types it
        form = QtWidgets.QFormLayout(self)
        form.addRow("Rest wavelength [Angstrom]", self.rest)
        form.addRow("Blue wing, Angstrom below rest (blank = whole window)", self.low)
        form.addRow("Red wing, Angstrom above rest", self.high)
        form.addRow("Minimum zeroth moment [DN, or DN Angstrom when integrating]", self.minimum)
        form.addRow("Saturation limit, peak [DN]", self.saturation)
        form.addRow(self.integrated)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.run)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def run(self):
        try:
            rest, low, high = _number(self.rest), _number(self.low), _number(self.high)
            if (low is None) != (high is None):
                raise ValueError("Enter both wings, or leave both blank to use the whole window.")
            self.moments = line_moments(
                self.data,
                rest_wavelength=None if rest is None else rest * u.AA,
                wings=None if low is None else (low * u.AA, high * u.AA),
                integrated=self.integrated.isChecked(),
                min_intensity=_number(self.minimum),
                saturation_limit=_number(self.saturation),
            )
        except Exception as error:  # noqa: BLE001 - show irispy's message and keep the dialog open
            QtWidgets.QMessageBox.critical(self, "Line moments failed", str(error))
            return
        self.data_collection.append(self.moments)
        for source, target in zip(self.data.pixel_component_ids[:2], self.moments.pixel_component_ids):
            self.data_collection.add_link(LinkSame(source, target))  # maps share the raster's (step, slit) pixel grid
        self.accept()


@layer_action("IRIS: line moments…", single=True, data=True)
def moments_action(layer, data_collection):
    """Right-click on a raster dataset: compute line moments with irispy and add the maps as one linked dataset."""
    MomentsDialog(layer, data_collection, parent=QtWidgets.QApplication.activeWindow()).exec()
```

Notes on the choices in the module (each verified below):
- `_in_angstrom` (D3): `cube.to(u.CompositeUnit(1, [AA if base == nm else base ...], powers))` keeps mask, SGMeta and WCS (verified below); `km / s` maps go through an identity conversion. Cost: one array copy per 7480-px map.
- `min_intensity` when integrating: `min_intensity * cube.unit * u.AA` so irispy's `min_intensity.to_value(intensity_unit)` (`moments.py:162`) compares in `DN nm` correctly. Verified: 50 DN Angstrom keeps 4472 of 7480 px finite, 50 DN (summed) keeps 6545; without the line, 50 is read as 50 DN nm and every pixel is NaN.
- `data.main_components[0]` is the science array (`cid.label == data.label` -> `True` for loader datasets); the mask is looked up by `f"{cid.label} mask"` so a user-renamed dataset still works. `data[cid]` is an `ndarray` (not dask).
- `# ponytail: wings/rest/min/saturation are QLineEdit + float()`; a non-numeric entry raises `ValueError` from `float()` and lands in the same message box. Upgrade to `QDoubleSpinBox` only if someone asks.
- `# ponytail: pixel_component_ids[:2]`; irispy rasters are always `(step, slit, wavelength)` (`cube.wavelength_axis == 2` on both test rasters) and `make_spatial_template` drops only the wavelength axis, so the map's pixel axes are the source's first two. If a future loader ever puts wavelength elsewhere, derive the spatial axes from `cube.wavelength_axis`.
- `# ponytail: synchronous call`; 20-46 ms per run for 7480 px measured today with the corrected module (first call 46 ms, warm 21-23 ms; the writer measured 13-29 ms before the Angstrom conversions), so no thread, no busy cursor.
- The "Time" copy is `data["Time"][..., 0]` because the loader broadcasts per-step times over the wavelength axis (`loaders/iris.py:82-84`).

### Prototype run (writer's script, embeds the PRE-Angstrom module): `python -u scratchpad/wp2_moments_proto.py`

Re-run by the checker today; identical output except RBA timing (`0.29s ... 39 us/px; est 17s`). The two lines marked `# superseded` show `nm` units that the corrected module turns into Angstrom (see the next block); everything else holds for the corrected module.

```
sns raster: Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0 (187, 40, 52) wavelength window [A] 2793.4401006592966 .. 2794.7385606194453 | step 0.02545999921860094
source comps: ['Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0', 'Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0 mask', 'Time']
registered: True
prefilled rest (TWAVE): '2796.20' | using in-window rest: 2794.09
accepted: True | dc: ['Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0', 'Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0-moments']
result: Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0-moments (187, 40) [('intensity', 'DN_IRIS_NUV'), ('intensity mask', ''), ('centroid', 'nm'), ('width', 'nm'), ('velocity', 'km / s'), ('velocity_width', 'km / s'), ('Time', '')]   # superseded: centroid/width are 'Angstrom' with the corrected module
world: ['Helioprojective Longitude', 'Helioprojective Latitude'] ('arcsec', 'arcsec')
velocity finite where intensity > 50: True | finite px 6545 / 7480 | nanmedian v -2.6366990903731957
external links: 2 ['LinkSame', 'LinkSame']
ROI on map: 38 px -> source: 1976 px; nwave = 52
ROI on source: 8892 px -> map: 171 px
MESSAGEBOX: No wavelength points found within the specified wings
error path: ['No wavelength points found within the specified wings'] | still open: True | dc size unchanged: True
MESSAGEBOX: Enter both wings, or leave both blank to use the whole window.
half wings: Enter both wings, or leave both blank to use the whole window.
no rest, no wings: ['intensity', 'intensity mask', 'centroid', 'width', 'velocity', 'velocity_width', 'Time']
integrated unit: DN_IRIS_NUV nm   # superseded: 'Angstrom DN_IRIS_NUV' with the corrected module
rejected 4 D dict -> Line moments need a per-scan raster window (raster step, slit, wavelength). Load scans without stacking.
rejected 3 D SJIMeta -> Line moments need a per-scan raster window (raster step, slit, wavelength). Load scans without stacking.
layer tree action can trigger on data: True
... on a subset: False
RBA return_profiles=False: keys ['red_blue_asymmetry', 'quality'] 0.27s / 7480 px = 36 us/px; 1096x400 est 16s
fiasco: No module named 'fiasco'
```
("no rest, no wings" still yields velocity maps because irispy auto-resolves TWAVE = 2796.20 A from `SGMeta`; the `layer tree action can trigger` lines come from `GlueApplication(dc)` + `app._layer_widget.ui.layerTree.set_selected_layers([d])` + `app._layer_widget._actions["IRIS: line moments…"]._can_trigger()`.)

### Corrected module, dialog run with the integrated checkbox (checker, `cd scratchpad/chk_wp2 && python - <<EOF ...`)

```python
# cwd = scratchpad/chk_wp2 (so the corrected module wins), HOME=<scratch>/home-chk2, QT_QPA_PLATFORM=offscreen
import numpy as np
from qtpy import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
from glue.core import DataCollection
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from wp2_moments_module import MomentsDialog
path = next(p for p in get_test_data_filenames() if p.name == "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits" and p.parent.name == "sns")
r = raster_data([path], ["Mg II k 2796"])[0]
dc = DataCollection([r])
d = MomentsDialog(r, dc)
d.rest.setText("2794.09"); d.low.setText("0.5"); d.high.setText("0.5"); d.minimum.setText("50"); d.integrated.setChecked(True)
d.run()
m = dc[1]
print("accepted:", d.result() == QtWidgets.QDialog.Accepted, "| label:", m.label, m.shape)
print("units:", [(c.label, m.get_component(c).units) for c in m.main_components])
print("centroid median [A]:", round(float(np.nanmedian(m['centroid'])), 3), "| width median [A]:", round(float(np.nanmedian(m['width'])), 4))
print("velocity finite:", int(np.isfinite(m['velocity']).sum()), "of", m['velocity'].size, "| finite iff intensity>=50 DN A:", bool((np.isfinite(m['velocity']) == (m['intensity'] >= 50)).all()))
print("links:", len(dc.external_links))
```
```
accepted: True | label: Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0-moments (187, 40)
units: [('intensity', 'Angstrom DN_IRIS_NUV'), ('intensity mask', ''), ('centroid', 'Angstrom'), ('width', 'Angstrom'), ('velocity', 'km / s'), ('velocity_width', 'km / s'), ('Time', '')]
centroid median [A]: 2794.064 | width median [A]: 0.3197
velocity finite: 4472 of 7480 | finite iff intensity>=50 DN A: True
links: 2
```

### `NDCube.to` keeps mask, meta and WCS (checker)

```
# calculate_moments(cube, rest_wavelength=2794.09*u.AA, wings=(0.5*u.AA, 0.5*u.AA), min_intensity=50, integrated=True), then per map:
intensity unit DN_IRIS_NUV nm -> target Angstrom DN_IRIS_NUV | has .to: True
centroid unit nm -> target Angstrom | has .to: True
velocity unit km / s -> target km / s | has .to: True
type after to: SpectrogramCube unit Angstrom DN_IRIS_NUV mask kept: True meta same type: SGMeta wcs same: True
values x10: True
_cube_data unit: Angstrom DN_IRIS_NUV comps ['intensity', 'intensity mask']
str units: ['Angstrom DN_IRIS_NUV', 'Angstrom', 'Angstrom', 'km / s', 'km / s']
```
(`str()` of the composite puts `Angstrom` first; the test asserts that exact string. That run also showed the min-intensity trap: `min_intensity=50` with `integrated=True` and no Quantity left every centroid NaN, because 50 was read as 50 DN nm.)

### The moments Data keeps a sliced `SGMeta` (verifier P2.1 note 3, checker re-run)

```
result.meta: SGMeta is source meta: False | rest_wavelength: 279.61999511700003 nm | OBSID: 3620258102
result.coords: _GlueWCS ('arcsec', 'arcsec') | raw: WCS ['deg', 'deg']
```

### The rewrap recipe alone: `python scratchpad/cc_rewrap.py` (2014 raster, Mg II k, scan 0)

```
components: ['Mg_II_k_2796-3860258481-2014-03-29T14:09:38-scan-0', '... mask', 'Time'] units: DN_IRIS_NUV
rewrapped: [  8. 109.  63.] pix wavelength_axis 2 rest 279.61999511700003 nm
moments keys: ['intensity', 'centroid', 'width', 'velocity', 'velocity_width']
ingest: (8, 109) ['Helioprojective Longitude', 'Helioprojective Latitude'] median v 0.5002691616124236
```

### Raw WCS handle under the wrapper (what the rewrap passes)

```
coords: _GlueWCS ('m', 'arcsec', 'arcsec') | raw _wcs: WCS ['m', 'deg', 'deg'] ['WAVE', 'HPLT-TAB', 'HPLN-TAB']
meta: SGMeta rest_wavelength: 279.61999511700003 nm | main comp: True | data type: ndarray
```

### Tests under the repo's `pytest.ini` (warnings are errors)

```
$ PYTHONPATH=scratchpad python -m pytest -c /Users/nabil/Git/glue-solar/pytest.ini --rootdir=scratchpad scratchpad/test_wp2_moments.py -q -o addopts='' -o testpaths= -p no:cacheprovider
5 passed, 2 warnings in 2.21s      # checker re-run with the corrected files (PYTHONPATH=scratchpad/chk_wp2 --rootdir=scratchpad/chk_wp2); the 2 warnings are PytestConfigWarning for doctest_plus/text_file_format (plugin not installed)
```

### Ruff with the repo config

```
$ sed 's/from wp2_moments_module import/from glue_solar.sources.moments import/' scratchpad/chk_wp2/test_wp2_moments.py > scratchpad/chk_wp2/test_moments_repoimport.py
$ ruff check --config .ruff.toml --no-cache --output-format concise scratchpad/chk_wp2/wp2_moments_module.py scratchpad/chk_wp2/test_moments_repoimport.py
All checks passed!
# with the scratch import line `from wp2_moments_module import ...` ruff reports I001 when run from the repo root (module not first-party there); irrelevant once the import is the repo one
```
(ruff 0.16.5 from `scratchpad/ruffpkg/bin/ruff`; pre-commit pins v0.16.1.)

### Registry identity and the layer_action decorator

```
$ python -c "import glue.config, glue_qt.config; print(glue.config.layer_action is glue_qt.config.layer_action)"
True
```
`glue_qt/config.py:138-152`: with `callback=None` the call returns `adder(func)` which stores `item(label, tooltip, func, icon, single, data, subset_group, subset)`.

### The existing interactive complement: Profile viewer "Collapse" tab (`python scratchpad/wp2_collapse_reach.py`)

```
ProfileTools: ProfileTools | tabs: ['Navigate', 'Fit', 'Collapse']
mode: collapse | collapse_function default: nanmean
x_range: (np.float64(2.793694700651483e-07), np.float64(2.794458500628041e-07)) (units: m )
image slice after collapse: AggregateSlice slice(10, 40, None) nansum
collapsed map == nansum over wl 10:40 (upper bound exclusive) -> (187, 40) True
```
Reached as `profile_viewer.toolbar.tools["profile-analysis"]._profile_tools` (`glue_qt/viewers/profile/profile_tools.py:48`); `COLLAPSE_FUNCS` :31-37 = Mean/Median/Minimum/Maximum/Sum/Moment 1/Moment 2 (`glue.core.aggregate.mom1/mom2`, pixel units); `_on_collapse` :302-331 writes an `AggregateSlice(slice(imin, imax), center, func)` into every Image viewer showing the data. This is zero-plugin-code "draw a wavelength range, see Sum/Moment maps live", in pixel units and without rest wavelength, masking, velocity. Document it next to the action.

## Tests to add

File `glue_solar/tests/test_moments.py` (verified text; adapt the import and drop the local fixture, see step 4). Fixtures: the repo's `irispy_test_files` (real irispy files) only; no synthetic data (the synthetic `iris_tree` rasters have no WCS/TWAVE and are for the browser tests).

```python
import numpy as np
import pytest
from glue.core import DataCollection
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue_qt.config import layer_action
from qtpy import QtWidgets

from glue_solar.sources.loaders.iris import image_data, raster_data
from wp2_moments_module import MomentsDialog, line_moments  # ships as glue_solar.sources.moments

SNS_RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
IN_WINDOW_REST = "2794.09"  # the test window spans 2793.44-2794.74 A; TWAVE (2796.20 A) lies outside it


@pytest.fixture(scope="session")
def irispy_test_files():
    from irispy.data.test import get_test_data_filenames

    return get_test_data_filenames()


@pytest.fixture
def raster(irispy_test_files):
    path = next(p for p in irispy_test_files if p.name == SNS_RASTER and p.parent.name == "sns")  # listed twice
    return raster_data([path], ["Mg II k 2796"])[0]


def test_action_is_registered():
    assert "IRIS: line moments…" in [item.label for item in layer_action]


def test_dialog_adds_one_linked_moments_dataset(qtbot, raster):
    dc = DataCollection([raster])
    dialog = MomentsDialog(raster, dc)
    qtbot.addWidget(dialog)
    assert dialog.rest.text() == "2796.20"  # prefilled from TWAVE
    dialog.rest.setText(IN_WINDOW_REST)
    dialog.low.setText("0.5")
    dialog.high.setText("0.5")
    dialog.minimum.setText("50")
    dialog.run()

    assert dialog.result() == QtWidgets.QDialog.Accepted
    assert [d.label for d in dc] == [raster.label, f"{raster.label}-moments"]
    maps = dc[1]
    assert maps.shape == raster.shape[:2]
    assert [(c.label, maps.get_component(c).units) for c in maps.main_components] == [
        ("intensity", "DN_IRIS_NUV"),
        ("intensity mask", ""),
        ("centroid", "Angstrom"),
        ("width", "Angstrom"),
        ("velocity", "km / s"),
        ("velocity_width", "km / s"),
        ("Time", ""),
    ]
    assert [c.label for c in maps.world_component_ids] == ["Helioprojective Longitude", "Helioprojective Latitude"]
    assert maps.coords.world_axis_units == ("arcsec", "arcsec")
    intensity, velocity = maps["intensity"], maps["velocity"]
    assert np.isfinite(velocity[intensity > 50]).all()
    assert np.isnan(velocity[~(intensity > 50)]).all()
    assert abs(np.nanmedian(velocity)) < 20  # rest wavelength inside the window: no bulk offset
    np.testing.assert_array_equal(maps["Time"], raster["Time"][..., 0])

    assert len(dc.external_links) == 2
    dc.new_subset_group(
        "map roi", RoiSubsetState(xatt=maps.pixel_component_ids[1], yatt=maps.pixel_component_ids[0], roi=RectangularROI(10, 30, 2, 5))
    )
    assert maps.subsets[0].to_mask().sum() == 38
    assert raster.subsets[0].to_mask().sum() == 38 * raster.shape[2]


def test_failure_keeps_dialog_open(qtbot, raster, monkeypatch):
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: shown.append(args[2]))
    dc = DataCollection([raster])
    dialog = MomentsDialog(raster, dc)
    qtbot.addWidget(dialog)
    dialog.rest.setText("3000")
    dialog.low.setText("0.1")
    dialog.high.setText("0.1")
    dialog.run()
    assert shown == ["No wavelength points found within the specified wings"]
    assert dialog.result() == 0
    assert len(dc) == 1
    dialog.rest.setText(IN_WINDOW_REST)
    dialog.high.clear()
    dialog.run()
    assert shown[-1].startswith("Enter both wings")
    assert len(dc) == 1


def test_integrated_zeroth_moment_is_dn_angstrom(raster):
    summed = line_moments(raster)
    maps = line_moments(raster, integrated=True, min_intensity=50)
    assert maps.get_component(maps.id["intensity"]).units == "Angstrom DN_IRIS_NUV"
    integrated = summed["intensity"] * 0.02546  # the window's wavelength step in Angstrom
    finite = np.isfinite(maps["intensity"])
    assert finite.sum() == (integrated >= 50).sum()  # the threshold is applied in DN Angstrom, not DN nm
    np.testing.assert_allclose(maps["intensity"][finite], integrated[finite], rtol=1e-3)


def test_stack_and_sji_are_rejected(irispy_test_files):
    scans = sorted(p for p in irispy_test_files if "20140329_140938_3860258481_raster_t000_r" in p.name)
    stack = raster_data(scans, ["Mg II k 2796"], stack=True)[0]
    sji = image_data(next(p for p in irispy_test_files if p.name == "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"))
    for data in (stack, sji):
        with pytest.raises(ValueError, match="per-scan raster window"):
            line_moments(data)
```

What each test pins:
- `test_action_is_registered`: the import side effect (also add the same assert to `test_plugin.py::test_setup_registers_hooks`).
- `test_dialog_adds_one_linked_moments_dataset`: TWAVE prefill `"2796.20"`; output shape `(187, 40)`; component order and units exactly `intensity DN_IRIS_NUV, intensity mask, centroid Angstrom, width Angstrom, velocity km / s, velocity_width km / s, Time`; world axes named and in arcsec; velocity finite iff intensity > min (6545 of 7480 px finite); `|nanmedian(velocity)| < 20 km/s` (2.6 today; with the out-of-window TWAVE it would be hundreds); `Time` equals the source per-step times; exactly 2 external links; ROI 38 px on the map -> `38 * 52 = 1976` px on the raster.
- `test_failure_keeps_dialog_open`: irispy's `ValueError` text surfaces in `QMessageBox.critical`, dialog stays open (`result() == 0`), nothing appended; half-filled wings rejected.
- `test_integrated_zeroth_moment_is_dn_angstrom`: unit string `"Angstrom DN_IRIS_NUV"`; the integrated map equals the summed map times the window step 0.02546 Angstrom (rtol 1e-3) where finite; the number of finite pixels equals the count of `summed * 0.02546 >= 50`, which pins the `DN Angstrom` threshold (would be 0 finite px if irispy compared 50 against `DN nm`).
- `test_stack_and_sji_are_rejected`: the 4D stack (dict meta) and a 3D SJI cube both raise the one clear message.

## Pitfalls (verified)

- `get_test_data_filenames()` lists the 2021 sns raster TWICE (`sns/` and `raster/` copies of `iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits`). Selecting by substring gives two files and `read_files` fails with `ValueError: Expected 187 NUV source filename rows, found 1872` (hit today). Select by `p.name == ... and p.parent.name == "sns"` (the fixture above) or by exact name with `next(...)` like `test_importer.py::_real`.
- Every window of both irispy test rasters excludes its own TWAVE (sns Mg II k: 2793.44-2794.74 A vs TWAVE 2796.20 A). Auto rest + any wings -> `ValueError("No wavelength points found within the specified wings")`. Tests must pass an explicit in-window rest (2794.09 A). Without wings the auto TWAVE still produces velocity maps, offset by hundreds of km/s on test data; do not assert on those.
- A blank rest wavelength does NOT mean "no velocity": irispy falls back to `SGMeta.rest_wavelength` (TWAVE). The dialog prefills it precisely so the user sees what is used.
- `QDialog.result()` is a method: an attribute named `result` on the dialog shadows it (`TypeError: 'NoneType' object is not callable`, hit today). The module uses `self.moments`.
- A modal `QMessageBox.critical` under `QT_QPA_PLATFORM=offscreen` blocks forever (the first prototype run hung > 120 s). Tests monkeypatch `QtWidgets.QMessageBox.critical`; never call `.exec()` in tests, call `dialog.run()`.
- A `Data` can belong to one `DataCollection` only (`AttributeError: Data has already been assigned to a different hub`, hit today). Reload or reuse one collection per test; the `raster` fixture is function-scoped for this reason.
- `min_intensity` with `integrated=True`: irispy compares the threshold against the zeroth moment in ITS unit, `DN nm` (`moments.py:146-151, 161-166`); a plain number typed as `DN Angstrom` is off by 10x (50 -> every pixel NaN on the sns window, hit by the checker). The module passes `min_intensity * cube.unit * u.AA` when integrating. Keep the dialog label "Minimum zeroth moment [DN, or DN Angstrom when integrating]".
- Two copies of the module live in the scratchpad: `scratchpad/wp2_moments_module.py` (writer, nm outputs) and `scratchpad/chk_wp2/wp2_moments_module.py` (corrected). A script started with the scratchpad root as cwd imports the stale one even with `PYTHONPATH=scratchpad/chk_wp2` (cwd wins); pytest with `--rootdir=scratchpad/chk_wp2` imports the corrected one. The brief's module text is the corrected one.
- `DN_IRIS_NUV`/`DN_IRIS_FUV` are irispy-defined units: `u.Unit("DN_IRIS_NUV")` fails outside `u.add_enabled_units(list(DN_UNIT.values()))`; both the rewrap and `calculate_moments` (which multiplies `cube.unit * nm` for `integrated=True`) must run inside the context.
- `data.coords.pixel_to_world_values(*pixel)` takes and returns axes in WCS order (wavelength, lat, lon), the reverse of numpy order; the first prototype fed `(0, 0, arange)` and read the wrong axis. WP2 never needs it; the test hardcodes the window range.
- `wcs_autolink` on glue-core 1.27 returns `[]` for raster<->map, map<->map and map<->SJI (`_GlueWCS` is low-level, filtered at `wcs_autolinking.py:320-321`); the two `LinkSame` links are mandatory. Wavelength-axis ROIs on the source are `IncompatibleAttribute` on the map (expected).
- `src.add_component(2D map)` on the 3D source raises `ValueError` (dimensions incompatible); `np.broadcast_to` fakes it but is semantically wrong (P2.1-link). Keep the separate Data.
- The `layer_action` callback receives `(layer, data_collection)` only; there is no way to open a viewer from it (D4). Parent the dialog on `QApplication.activeWindow()`.
- The rewrap drops irispy's `time` extra coord, so the map's `_cube_data` output has no `Time`; the module copies `data["Time"][..., 0]` (verified equal to the loader's per-step times).
- `pytest.ini` sets `filterwarnings = error`; the verified tests pass under it (no astropy/numpy warnings escaped). Run with `-o addopts=''` in this venv because `pytest-doctestplus` is missing; CI installs the `tests` extra and does not need it.
- The Profile viewer Collapse tool's `AggregateSlice.slice` upper bound is exclusive (`slice(10, 40)` == `nansum(data[:, :, 10:40])`); a future "prefill from x_range" must not off-by-one.
- The verifier's earlier recipe `_cube_data(first, label)` + `add_component(..., "intensity")` stores the intensity array twice; the module avoids it with `_cube_data(first, "intensity")` + `result.label = ...` (`Data.label` setter, `glue/core/data.py:802-808`, broadcasts nothing before the Data joins a hub).
- ruff isort sections (`.ruff.toml`): `astropy` imports go in their own block AFTER third-party (`qtpy`, `irispy`, `glue*`) and BEFORE `glue_solar`; the module text above is already in that order.
- Environment notes in older findings about `~/.glue/settings.cfg` (`unit_converter = "iris-velocity"`) are stale (critic §2); still run Qt code with `HOME=<scratch>` so glue never writes settings into the user's config.

## Acceptance criteria

- [ ] `glue_solar/sources/moments.py` exists with `line_moments`, `MomentsDialog`, `moments_action`; imported from `glue_solar/__init__.py`.
- [ ] Right-clicking a per-scan raster dataset in the glue data collection shows "IRIS: line moments…"; it is absent for subsets and multi-selection.
- [ ] Dialog fields: rest wavelength [Angstrom] prefilled from TWAVE when present, blue/red wings [Angstrom], minimum zeroth moment [DN, or DN Angstrom when integrating], saturation limit [DN], integrated checkbox; OK runs, Cancel closes.
- [ ] Result: one 2D Data labelled `<source label>-moments`, components `intensity, intensity mask, centroid, width, velocity, velocity_width, Time` with units `DN_IRIS_<band>` (or `Angstrom DN_IRIS_<band>` when integrated), `Angstrom`, `Angstrom`, `km / s`, `km / s` (D3: no `nm` anywhere); world axes Helioprojective Longitude/Latitude in arcsec.
- [ ] Exactly two `LinkSame` external links per run; an ROI on the map selects `n * nwave` pixels on the source and a spatial ROI on the source selects `n` pixels on the map.
- [ ] Any exception (irispy `ValueError`, non-numeric entry, half-filled wings, stack or SJI dataset) shows a `QMessageBox.critical` with the message and keeps the dialog open; nothing is appended.
- [ ] No viewer is opened by the action.
- [ ] `pytest glue_solar` passes with warnings-as-errors (32+ tests); `ruff check --config .ruff.toml` clean; pre-commit clean.
- [ ] Docs page, toctree entry, `automodapi` block and changelog fragment present; `sphinx-build -W` passes.
- [ ] No change to `glue_solar/sources/loaders/*`, no new dependency in `pyproject.toml`.

## Dropped / out of scope

- 4D stacked datasets: rejected with a message in v1. Follow-up recipe (verified by the audit and verifier, `verify_moments2.py`): `SpectrogramCube(stack.data, stack.wcs, None, stack.unit, stack.meta, mask=stack.mask)` gives `wavelength_axis == 3`; with an explicit `rest_wavelength` (dict meta has no `.rest_wavelength`; TWAVE would need a `TDESC` lookup) `calculate_moments` returns `(13, 8, 109)` maps that `_cube_data` ingests with world axes `Scan, Helioprojective Longitude, Helioprojective Latitude`; scan 0 equals the single-scan result; link with THREE `LinkSame` (scan, step, slit); no `Time` extra coord, copy `data["Time"][..., 0]` as here. Reason: doubles the test matrix and the docs must explain the scan-0-only WCS; nobody asked for it.
- Opening an Image viewer on `velocity`: impossible from `layer_action` (no application handle) and excluded by D4.
- Prefilling wings from a drawn Profile-viewer range: follow-up. Read `profile_viewer.toolbar.tools["profile-analysis"]._profile_tools.rng_mode.state.x_range` (world values of the profile `x_att`: metres today, Angstrom after WP1; pixel indices in the fork's WCSAxes `'slice'` mode, critic §1) and set `low = rest - x_range[0]`, `high = x_range[1] - rest` in Angstrom. Needs a viewer handle, so it lives in a `menubar_plugin` or a Profile-viewer `viewer_tool`, not in this `layer_action`.
- Red-blue asymmetry (`irispy.utils.red_blue.calculate_red_blue_asymmetry(cube, *, rest_wavelength=None, velocity_range=(50,150) km/s, dv=10 km/s, continuum_windows=None, degree=3, min_intensity=None, saturation_limit=None, return_profiles=True)`): second `layer_action("IRIS: red-blue asymmetry…", single=True, data=True)` with the same rewrap and the same `_cube_data(first, name)` + relabel + 2 `LinkSame` tail; fields: rest wavelength, velocity range lo/hi [km/s], dv [km/s], polynomial degree; call with `return_profiles=False` (the profile cubes are the source resampled in velocity, no value inside glue); outputs `red_blue_asymmetry` (float, dimensionless) and `quality` (uint8 flags) as two components. Always pass the dialog's rest wavelength explicitly: installed 0.8.1 raises `TypeError` from `float(None)` for windows without TWAVE (verifier P2.3a). Measured today: `0.27 s / 7480 px = 36 us/px`, about 16 s for a full 1096x400 raster, so it needs a busy cursor or a `QThread` (moments does not). Reason for deferral: sibling dialog with different fields; ship moments first.
- `density_diagnostic`: de-scoped. It is arrays-in/dict-out (two integrated-intensity maps + density grid + `fiasco.Ion` + two transition wavelengths -> dict, no WCS), needs `fiasco` (`import fiasco` -> `ModuleNotFoundError` today, not declared in `pyproject.toml`) plus the CHIANTI database, and two prior wings-restricted moments runs on two O IV lines. Not "one entry in the same action list".
- Loader cube handle (`data.irispy_cube = cube`, plan L113-115): unnecessary, the rewrap works from the Data alone.
- Background thread, progress bar, `QDoubleSpinBox` validators, remembering last-used parameters: YAGNI at 20-46 ms per run.
- Keeping irispy's `time` extra coord through the rewrap (`ExtraCoords.from_lookup_tables`): the two-line `Time` component copy gives the same glue-visible result.
- Session save/restore of the moments Data: sessions with `_GlueWCS`/`SGMeta` datasets are already documented as unsupported (`loading-iris-level-2-raster-and-sji-data.rst:61-66`); WP-sessions covers it.

## Docs

- `docs/user_guide/line-moments-of-a-raster-window.rst` (NEW), added to `docs/user_guide/index.rst` toctree after `guide-to-glue-1dprofile-viewer-for-iris-data`:

```rst
.. _glue_solar_users_guide_line_moments:

=================================
Line moments of a raster window
=================================

Right-click a raster window dataset (a per-scan ``<window>-<OBSID>-<STARTOBS>-scan-<n>`` entry)
in the data collection and choose "IRIS: line moments...". The dialog wraps
``irispy.utils.moments.calculate_moments`` (irispy-lmsal):

- Rest wavelength [Angstrom]: prefilled from the window's ``TWAVE`` header card when present; edit it
  to centre the calculation on another line of the window. Leave it blank to let irispy use ``TWAVE``.
- Blue and red wings [Angstrom]: the spectral range below and above the rest wavelength used for
  the moments. Leave both blank to use the whole window.
- Minimum zeroth moment [DN, or DN Angstrom when integrating]: pixels whose zeroth moment is below this
  value get NaN in every map.
- Saturation limit [DN]: pixels whose peak exceeds this value get NaN in every map.
- Integrate over wavelength: report the zeroth moment as an integral (``DN Angstrom``) instead of a sum (``DN``).

Press OK. One new 2D dataset labelled ``<source>-moments`` is added to the data collection with the
components ``intensity`` (DN, or DN Angstrom when integrating), ``centroid`` and ``width`` (Angstrom),
and, when a rest wavelength is known, ``velocity`` and ``velocity_width`` (km/s), plus the
``intensity mask`` and the per-step ``Time``.
The new dataset is pixel-linked to its source, so a region drawn on a moment map selects the same
raster steps and slit positions in the spectrogram (and its spectra in the Profile viewer), and a
spatial selection on the raster shows up on the maps. Drag the new dataset onto the canvas as a
2D Image and pick the component to display; no viewer is opened automatically.

Moments are computed per raster scan. Stacked 4D datasets and slit-jaw images are refused with a
message; load the scans without stacking to compute their moments.

An interactive alternative that needs no rest wavelength is the Profile viewer's "Collapse" tab:
open a Profile viewer on the raster with ``Wavelength`` as the x-axis, draw a wavelength range, and
choose Sum, Mean, Moment 1 or Moment 2. Every Image viewer showing the same dataset then displays
that quantity over the drawn range, live. Its moments are in pixel units and ignore the mask, the
rest wavelength and velocities; use "IRIS: line moments..." for calibrated maps.
```

- `docs/api_reference.rst`: append

```rst
.. automodapi:: glue_solar.sources.moments
   :no-inheritance-diagram:
```

- `changelog/<PR>.feature.rst`:

```rst
Right-click a raster window dataset and choose "IRIS: line moments…" to compute the line intensity, centroid, width, velocity and velocity width maps of the window with ``irispy.utils.moments.calculate_moments`` (rest wavelength prefilled from ``TWAVE``, optional spectral wings in Angstrom, minimum intensity and saturation limit). Wavelength outputs are in Angstrom. The maps are added as one 2D dataset that is pixel-linked to its source, so selections propagate between the maps and the spectrogram.
```

- `docs/conf.py:74` `intersphinx_mapping` has only `python`, `default_role = "py:obj"` (:69), no `nitpicky`: unresolved `irispy` references render as literals without a warning under `-W`, so the texts above use double backticks. `https://docs.sunpy.org/projects/irispy-lmsal/en/stable/objects.inv` returned HTTP 404 today; do not add an intersphinx entry without finding the right URL.
- `docs/dev_guide/loader-customization.rst:7-8` (optional, one sentence): after "menu plugins" add "and per-dataset context-menu actions (``glue_qt.config.layer_action``, see ``glue_solar/sources/moments.py``)".
- Untracked planning docs (only if they are kept): `IRIS_GLUE_GAP_PLAN.md:99` "released in irispy-lmsal 0.8.1" -> "since irispy-lmsal 0.7.0"; :108-109 "add the maps as datasets linked to the source" -> "add the maps as one dataset with five components, pixel-linked to the source (no autolink on glue-core 1.27)"; :113-115 prerequisite paragraph -> delete (rewrap); :127-131 -> RBA is cube-in/cube-out but slow (~36 us/px), density is arrays-in/dict-out and needs fiasco. `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md:178-179` -> "Partial" (Profile viewer Collapse tab gives pixel-unit Sum/Moment maps today) until WP2 lands, then "Done".


---

# WP3 - Session save/restore for IRIS datasets

**Goal.** Make "File -> Save Session" and "File -> Restore Session" work for every dataset glue-solar produces (SJI/AIA cubes, raster scans, 4-D stacks, sunpy Maps) with coordinates restored to numerical identity, and make browser-loaded datasets reference their FITS files instead of embedding arrays. Everything ships from glue-solar on released glue-core 1.27.0; no glue-core, glue-astronomy, astropy or ndcube change is required.

## Current state (2026-09-02)

Repo: /Users/nabil/Git/glue-solar, branch `iris-observation-browser` (HEAD d3a2bd3 = PR glue-viz/glue-solar#44). Environment: glue-core 1.27.0 (site-packages), astropy 8.0.1, asdf 5.3.1, asdf-astropy 0.11.0, gwcs 1.0.3, ndcube 2.4.1, irispy 0.8.1.

Saving fails three independent ways, all re-run today (`wp3_stock.py`, output in "Verified code" 1):

- `glue_solar/sources/loaders/iris.py:35-69`: `_GlueWCS(BaseWCSWrapper)` has no `__gluestate__`, and glue-core registers a saver only for `astropy.wcs.WCS` (`glue/core/state.py:655-663`, header string). SJI save raises `GlueSerializeError: Don't know how to serialize <_GlueWCS>`.
- `loaders/iris.py:76` `data.meta = cube.meta`: irispy `SGMeta` (rasters, and the stack's `dict(scan0.meta)`) holds two `Quantity` values, `exposure time` (8,) s and `observer radial velocity` (8,) m/s. glue's meta filter (`state.py:1023-1038`) catches only `GlueSerializeError`; a Quantity matches `@saver(np.ndarray)` by MRO and `np.save` raises `TypeError` (`state.py:1266-1270`). Raster and stack saves die here, before the WCS is reached. `Time` (`auxiliary times`) and `SkyCoord` (`exposure FOV center`) raise `GlueSerializeError` and are silently dropped, which is fine. SJI `SJIMeta` has 148 scalar keys and round-trips completely.
- `loaders/iris.py:77` `VisualAttributes(color=color, preferred_cmap=cmap)` and `glue_solar/sources/maps.py:30` `preferred_cmap=scan_map.cmap`: glue-core `_save_style` (`state.py:744-746`) writes the raw `Colormap` object; `json.dumps` raises `TypeError: Object of type LinearSegmentedColormap is not JSON serializable`. This already breaks every session containing a sunpy Map on glue-solar `main`, independent of the IRIS branch (verified today with a synthetic AIA map). `_load_style` (`state.py:749-756`) always discards `preferred_cmap`, so glue never restores it even after an upstream fix.

Stock-glue reload failure mode, stated correctly (verifier correction to the audit): on astropy 8.0.1 `WCS.to_header_string()` on the irispy -TAB WCS does NOT raise. glue's `_save_wcs` writes a 2880-char header carrying the `PS2_0/PS2_1/PS2_2/PS3_*` keys but no table. The session then fails to LOAD: `_load_wcs` -> `WCS(Header)` -> `ValueError: HDUList is required to retrieve -TAB coordinates and/or indices`. A Data with the bare -TAB WCS as coords saves (82 KB) and fails to restore. astropy has no -TAB writer (`WCS.to_fits()` returns PRIMARY only; `Tabprm` exposes `coord`, `K`, `M`, `map`, `crval` but no index vectors; `wcs.py:254-267` is the read-only `_load_tab_bintable` callback); pickle and asdf-astropy fail the same way (`KeyError: Extension ('WCS-TABLE', 1) not found`).

Browser path and LoadLog: `loaders/iris.py:288-302` `QtIRISImporter.finalize` calls `raster_data`/`image_data` directly and `sources/iris.py:44` does `app.add_datasets(dialog.datasets)`, so no `LoadLog` is attached. glue embeds every array in base64 unless `component._load_log` exists and `include_data=False` (`state.py:1093-1101`). "File -> Open" goes through `load_data(path, factory=read_iris_file)` (`sources/iris.py:22-27`) and does get a LoadLog (`glue/core/data_factories/helpers.py:238-300`, `LoadLog.__gluestate__/__setgluestate__` at 154-184). `Data.coords` is always restored from the record (`state.py:923-925`), so a coords saver is required on both paths.

Docs: `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:61-66` says sessions "cannot currently be restored reliably". Understated: saving itself raises, nothing is written (glue-core `application_base.py:101-131` dumps first and only then opens the output file, so no partial `.glu` is left). What the user sees (checker correction; the audit verifier and the first draft of this brief had it wrong): `Application.save_session` is wrapped in `@catch_error("Failed to save session")` (glue-core `application_base.py:100`, decorator at `:18-30`), which calls `GlueApplication.report_error` (`glue_qt/app/application.py:1303-1315`), a modal `QMessageBox.Critical` titled "Error" with the text "Failed to save session" plus the exception message and the traceback under "Show Details". glue-qt `_choose_save_session` (`glue_qt/app/application.py:1032-1062`) itself has no `@messagebox_on_error`, but it does not need one. Verified today (`wp3chk_dialog.py`, "Verified code" 9): `report_error called: 1`, message `Failed to save session | Don't know how to serialize <_GlueWCS ...>`, `file written: False`.

Planning docs: `IRIS_GLUE_GAP_PLAN.md:52` ("glue-core + glue-solar ... done completely or not at all") and `:165-171`, `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md:141-144`. Both refuted by the audit and by today's runs: the pieces are independent and all glue-solar-side. No fork branch (`glue` ape14-wcs-autolink / profile-wcs, `glue-qt` profile-wcs) touches session code; glue-astronomy has no serializers.

## Decisions already made

- D2: ship from glue-solar through public hooks: `__gluestate__`/`__setgluestate__` on our own classes and `glue.core.state.saver/loader` for `astropy.units.Quantity`. Upstream: at most the two glue-core one-liners listed under "Dropped / out of scope" (optional, release-gated, glue-solar keeps its workaround).
- D3: the WCS record stores only the wrapped low-level WCS. Display-unit conversion (arcsec today, Angstrom after WP1) is code in `_GlueWCS`, not state, so WP1 changes nothing in the session format; the tests below compare the wrapper's `pixel_to_world_values` on both sides and therefore hold in Angstrom as well.
- D4: moment-map Data from WP2 gets `_cube_data` coords (WP2 brief: `_cube_data(first_map, "intensity")` on irispy's 2-D astropy WCS, `_GlueWCS ('arcsec', 'arcsec') | raw: WCS ['deg', 'deg']`, so `_wcs_record` emits the `"fits"` kind) and no LoadLog; they embed on save (small 2-D arrays). Covered without extra work; WP2's `layer_action` does not touch sessions.
- D1 / Phase 1.4 `link_hpc`: `ComponentLink`s between world components serialize with stock glue. Only closure-based links (`using=lambda`) are unserializable (critic §2); P3.2 must use component-based links, not WP3's problem.
- Metadata: keep `data.meta = cube.meta` untouched at load time; register `@saver(u.Quantity)` / `@loader(u.Quantity)` in glue-solar. In the file a Quantity is `{value: <ndarray record>, unit: "s"}`, on reload it is a `Quantity` again with the same values and unit (verified). No float+string flattening, no dropping, no change to the live meta. `Time`/`SkyCoord` keep being dropped by glue-core's filter (2 of 400 keys).
- Colormap: the audit-verified version-2 `VisualAttributes` saver/loader is NOT the chosen form. Verified today (`wp3_style_trap.py`): registering `@saver(VisualAttributes, version=2)` stamps `_protocol: 2` on the style record of EVERY dataset saved while glue-solar is installed, and a plain interpreter without glue-solar then fails to load such a session (`GlueSerializeError: Don't know how to load objects of type VisualAttributes`), even if it contains no solar data at all. Chosen form: a subclass `SolarVisualAttributes(VisualAttributes)` with `__gluestate__`/`__setgluestate__`, used only by `_cube_data` and `_parse_sunpy_map`. Plain datasets keep the stock record (`_type: glue.core.visual.VisualAttributes`, no `_protocol`), solar datasets carry the cmap NAME and restore it (verified). Same line count as the v2 override. If a reviewer insists on the v2 override, the 8 lines in `ver_sess1.py` work; the portability trap above is the price.
- LoadLog: the browser builds datasets through `glue.core.data_factories.load_data`. SJI/AIA: `load_data(str(path), factory=read_iris_file)`. Rasters: a new plain function `read_iris_rasters(path, files=None, windows=None, stack=False)` (not a registered data factory; File -> Open keeps `read_iris_file`) called as `load_data(files[0], factory=read_iris_rasters, files=<names relative to dirname(files[0])>, windows=[name], stack=...)`. Measured today: SJI 22 KB instead of 1225 KB, 9-window raster file 249 KB instead of 4455 KB, 3-scan stack 32 KB instead of 1190 KB. Relative-path sessions relocate together with the data (verified by copying data + session to another folder and reloading there).
- -TAB: rebuild the WCS-TABLE from `Tabprm.coord` plus linear index vectors, exactly irispy's construction (site-packages `irispy/io/spectrograph.py:56-111`, `_create_tabular_wcs`: `SPATIAL = (CRVAL2 + CDELT2*([1, NAXIS2] - CRPIX2))*arcsec_to_deg`, `RASTER = arange(1, NAXIS3+1)`, `PS{2,3}_0 = WCS-TABLE`, `PS{2,3}_1 = COORDS`, `PS2_2 = SPATIAL`, `PS3_2 = RASTER`). Marked `# ponytail: relies on irispy WCS-TABLE layout`. Generic astropy -TAB export stays an upstream gap that IRIS does not need.
- gWCS: base64 asdf blob (`asdf.AsdfFile({"wcs": gwcs}).write_to`), ~15.7 KB per SJI. asdf and asdf-astropy are already installed transitively (`irispy-lmsal -> gwcs>=1.0.0 -> asdf>=3.3.0, asdf-astropy>=0.8.0`, checked with `importlib.metadata.requires`); no new dependency in `pyproject.toml`.
- Stacks: recursive record `{"kind": "compound", parts, mapping}` / `{"kind": "sliced", wcs, slices}` using ndcube/astropy private attributes `_wcs`, `mapping.mapping`, `_slices_array`. No ndcube change.

## Dependencies / order

- Lands after WP1 (D3 Angstrom) only to avoid touching `_GlueWCS` in two PRs at once; there is no code dependency. If it lands first, WP1 must keep `_GlueWCS.__init__` signature-compatible with `cls(inner_wcs)`.
- Independent of WP2 (moments), the fork branches, and glue-qt #68.
- Unblocks: any later WP that says "sessions work" (P3.2 sync links, P3.4 line lists need their own savers, see Dropped), and lets the docs drop the "unsupported" paragraph.
- glue-solar must be importable when a session is loaded: `_type` strings `glue_solar.sources.loaders.iris._GlueWCS`, `glue_solar.sources.loaders.iris.SolarVisualAttributes`, and LoadLog factories `glue_solar.sources.iris.read_iris_file` / `glue_solar.sources.iris.read_iris_rasters` are baked into `.glu` files. glue's plugin loader imports `glue_solar` at startup, so the Qt app is fine; plain glue-core without Qt cannot load these sessions because `glue_solar` imports `glue_qt`/`qtpy` at package import (pre-existing).

## Files to touch

- `glue_solar/sources/loaders/iris.py`
  - imports: `base64`, `io`, `asdf`, `gwcs`, `from astropy.io import fits`, `from astropy.wcs import WCS`, `from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS`, `from ndcube.wcs.wrappers import CompoundLowLevelWCS`, `from glue.core.state import GlueSerializeError, loader, saver`, `from glue.core.data_factories import load_data`, `from glue.utils import as_list`.
  - add module functions `_tab_record`, `_wcs_record`, `_wcs_from_record` (verbatim from "Verified code" 2).
  - add `__gluestate__` / `__setgluestate__` methods to `_GlueWCS`.
  - add `_save_quantity` / `_load_quantity` (`@saver(u.Quantity)` / `@loader(u.Quantity)`).
  - add `class SolarVisualAttributes(VisualAttributes)`.
  - `_cube_data`: `data.style = SolarVisualAttributes(color=color, preferred_cmap=cmap)`.
  - `QtIRISImporter.finalize`: build datasets through `load_data` (step 6).
  - `__all__`: add `"SolarVisualAttributes"`.
- `glue_solar/sources/iris.py`: `import os`; extend the loaders import to `from glue_solar.sources.loaders.iris import QtIRISImporter, iris_data, last_directory, raster_data`; add `read_iris_rasters` next to `read_iris_file` (plain function, no decorator, in `__all__`; body = "Verified code" 2 with `L.raster_data` -> `raster_data`). `finalize` imports it lazily (`sources/iris.py` imports `loaders/iris.py`, so a module-level import would be circular).
- `glue_solar/sources/maps.py:30`: `from glue_solar.sources.loaders.iris import SolarVisualAttributes` (replace the `from glue.core.visual import VisualAttributes` import at `maps.py:6`, otherwise unused); `result.style = SolarVisualAttributes(color="#FDB813", preferred_cmap=scan_map.cmap)`. No circular import: `glue_solar/__init__.py` imports `sources.iris` (which loads `loaders.iris`) before `sources.maps` (verified, suite passes).
- `glue_solar/tests/test_sessions.py`: new, see "Tests to add".
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:61-66`: replace the paragraph (see Docs).
- `changelog/<PR>.feature.rst` and `changelog/<PR>.bugfix.rst` (see Docs).
- `IRIS_GLUE_GAP_PLAN.md:52,165-171` and `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md:141-144`: reword (see Docs).

## Step-by-step

1. In `loaders/iris.py` paste `_tab_record`, `_wcs_record`, `_wcs_from_record` from "Verified code" 2 (lines 28-83 of `wp3_impl.py`) above `class _GlueWCS`. Keep the `# ponytail:` comment on `_tab_record`. Keep `slices` in ARRAY order (`wcs._slices_array`), not `_slices_pixel` (pitfall 1). Keep `"shape"` in the record and `wcs.pixel_shape = tuple(rec["shape"])` on load (pitfall 2). Keep the -TAB header as a separate string, not inside the table HDUList's PrimaryHDU (pitfall 3).
2. Add to `_GlueWCS`:
   ```python
       def __gluestate__(self, context):
           return {"wcs": _wcs_record(self._wcs)}

       @classmethod
       def __setgluestate__(cls, rec, context):
           return cls(_wcs_from_record(rec["wcs"]))
   ```
   glue dispatches on `__gluestate__` before the saver registry (`state.py:378-381`) and on `__setgluestate__` before the loader registry (`state.py:490-500`), so no `@saver(_GlueWCS)` registration is needed.
3. Add `_save_quantity` / `_load_quantity` (lines 96-104 of `wp3_impl.py`) at module level. Registration happens at import; `glue_solar/__init__.py` imports `sources.iris` which imports this module, and glue's plugin loader imports `glue_solar` at startup.
4. Add `SolarVisualAttributes` (lines 107-121) and switch `_cube_data` and `maps.py` to it. Do not register a `VisualAttributes` saver of any version.
5. Add `read_iris_rasters` to `glue_solar/sources/iris.py` (lines 124-133, replace `L.raster_data` with the imported `raster_data`).
6. Rewrite the loading loop of `QtIRISImporter.finalize` (`loaders/iris.py:288-302`):
   ```python
           from glue_solar.sources.iris import read_iris_file, read_iris_rasters  # sources.iris imports this module

           self.datasets, self.first_image = [], None
           for n, (i, kind, name) in enumerate(picks):
               self.progress.setValue(int(100 * n / len(picks)))
               get_qapp().processEvents()
               obs = self.observations[i]
               try:
                   if kind == "raster":
                       files = [str(p) for p in obs.rasters]
                       folder = os.path.dirname(files[0])
                       loaded = load_data(files[0], factory=read_iris_rasters,
                                          files=[os.path.relpath(f, folder) for f in files],
                                          windows=[name], stack=self.stack.isChecked())
                       self.datasets.extend(as_list(loaded))
                   else:
                       image = load_data(str(obs.sji[name] if kind == "sji" else obs.sdo[name]), factory=read_iris_file)
                       self.datasets.append(image)
                       self.first_image = self.first_image or image
               except Exception as error:  # noqa: BLE001 - third-party reader errors must stay inside the dialog
                   self.progress.setFormat(f"Loading {name} failed: {error}")
                   return
   ```
   Notes: `load_data` is `@contract(path='string')`, pass `str`. `load_data` unpacks a 1-element list to a bare `Data` (`helpers.py:314-316`), hence `as_list`. Passing `factory=` bypasses `is_iris_fits`, so AIA cutouts (blank `TELESCOP`) load through `read_iris_file` exactly as `image_data` did. `load_data` pops `coord_first`/`force_coords` before calling the factory (`helpers.py:260-261`); only `files`/`windows`/`stack` reach `read_iris_rasters` and are what LoadLog stores. `load_data` only sets a label when the factory left it empty (`helpers.py:293-294`), so existing label assertions keep passing. Checker: this exact edit (plus steps 1-5 and the test file of step 7) was applied to a throwaway worktree of `d3a2bd3` (`wp3chk_patch.py`) and the whole suite passed: 33 tests (27 existing + 6 new), see "Verified code" 9. The browser session of one SJI plus a 3-scan stack is 56 KB with relative paths.
7. Add `glue_solar/tests/test_sessions.py` (below). Run `QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python -m pytest glue_solar -o addopts='' -q`. `pytest.ini` has `filterwarnings = error`; the verified code emits no warnings on save or load (the "caught []" column in "Verified code" 3; 33 passed today with that setting).
8. Run `pre-commit run --all-files` (ruff v0.16.1 with the isort rule `I` enabled in `.ruff.toml:17`; `ruff` is not installed in `.venv`, so the checker could not lint). Expect it to reorder the new imports; in `maps.py` drop the now-unused `from glue.core.visual import VisualAttributes` (F401).
9. Update docs and changelog fragments (Docs section). Reword the two planning docs.

## Verified code

All run today, 2026-09-02, with `HOME=<scratch>/home-wp3 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg /Users/nabil/Git/glue-solar/.venv/bin/python`. Scripts live in `IRIS_PLAN_PROTOTYPES/` (`wp3_impl.py`, `wp3_stock.py`, `wp3_roundtrip.py`, `wp3_loadlog.py`, `wp3_style_trap.py`, `wp3_meta.py`, `wp3_map.py`, `wp3_stackdbg.py`; checker additions `wp3chk_dialog.py`, `wp3chk_patch.py` (applies steps 1-6 to a worktree), `wp3chk_test_sessions.py` (the test file), `wp3chk_editbrief.py`). The repo was not modified (`git status`: only the two untracked planning docs); the checker's full-suite run used a detached throwaway worktree of `d3a2bd3` under the scratchpad, removed afterwards. Sections 1-8 were re-run by the checker on 2026-09-02 and match the pasted output line for line (except the `wp3_roundtrip.py` tail, see the note in section 3).

### 1. Stock failure modes today (`wp3_stock.py`)

```
== as loaded (branch iris-observation-browser, stock glue-core 1.27.0) ==
[SJI] SAVE FAIL GlueSerializeError: Don't know how to serialize <glue_solar.sources.loaders.iris._GlueWCS object at 0x11a98f380>
[raster] SAVE FAIL TypeError: no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.qu
[stack] SAVE FAIL TypeError: no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.qu
[SJI coords=None] SAVE FAIL TypeError: Object of type LinearSegmentedColormap is not JSON serializable
== stock @saver(WCS) applied to the bare irispy -TAB WCS ==
_save_wcs OK: header chars 2880 | PS2_0 in header: True
_load_wcs FAIL ValueError: HDUList is required to retrieve -TAB coordinates and/or indices.
== Data whose coords is that bare -TAB WCS (no _GlueWCS, clean meta, no cmap) ==
[bare -TAB Data] SAVE OK 82 KB
reload FAIL ValueError: HDUList is required to retrieve -TAB coordinates and/or indices.
== sunpy Map through glue_solar.sources.maps (main branch code, unrelated to IRIS) ==
[sunpy map] SAVE FAIL TypeError: Object of type LinearSegmentedColormap is not JSON serializable
```

### 2. The implementation (`wp3_impl.py`, applied by monkeypatch; lines 28-133 are the code to copy)

```python
def _tab_record(wcs):
    """Header string plus a rebuilt WCS-TABLE extension: astropy can read -TAB tables but not write them."""
    # ponytail: relies on irispy's WCS-TABLE layout (irispy/io/spectrograph.py _create_tabular_wcs):
    # one table, PS2_1 == PS3_1 == the coordinate column, and linear index vectors
    # psi(1)..psi(NAXIS) with K samples. astropy exposes Tabprm.coord but not the index vectors.
    header = fits.Header.fromstring(wcs.wcs.to_header(relax=True))
    table = wcs.wcs.tab[0]
    columns = {header["PS2_1"]: np.ascontiguousarray(table.coord)}
    for axis in (2, 3):
        pixels = np.array([1, wcs.pixel_shape[axis - 1]], dtype=float)
        psi = wcs.wcs.crval[axis - 1] + wcs.wcs.cdelt[axis - 1] * (pixels - wcs.wcs.crpix[axis - 1])
        columns[header[f"PS{axis}_2"]] = np.linspace(psi[0], psi[1], table.K[axis - 2])
    record = np.array([tuple(columns.values())], dtype=[(k, float, v.shape) for k, v in columns.items()])
    buffer = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(record, name=header["PS2_0"])]).writeto(buffer)
    return {"kind": "fits-tab", "header": header.tostring(), "table": base64.b64encode(buffer.getvalue()).decode()}


def _wcs_record(wcs):
    """JSON-safe record of any WCS the IRIS loaders produce, recursing through wrappers."""
    if isinstance(wcs, gwcs.WCS):
        buffer = io.BytesIO()
        asdf.AsdfFile({"wcs": wcs}).write_to(buffer)
        return {"kind": "asdf", "b64": base64.b64encode(buffer.getvalue()).decode()}
    if isinstance(wcs, WCS):
        shape = None if wcs.pixel_shape is None else [int(n) for n in wcs.pixel_shape]
        if any(ctype.endswith("-TAB") for ctype in wcs.wcs.ctype):
            return {**_tab_record(wcs), "shape": shape}
        return {"kind": "fits", "header": wcs.to_header_string(), "shape": shape}
    if isinstance(wcs, SlicedLowLevelWCS):
        # array order: that is what the SlicedLowLevelWCS constructor takes (_slices_pixel is reversed)
        slices = [s if isinstance(s, int) else [s.start, s.stop, s.step] for s in wcs._slices_array]
        return {"kind": "sliced", "wcs": _wcs_record(wcs._wcs), "slices": slices}
    if isinstance(wcs, CompoundLowLevelWCS):
        return {"kind": "compound", "parts": [_wcs_record(w) for w in wcs._wcs], "mapping": [int(m) for m in wcs.mapping.mapping]}
    raise GlueSerializeError(f"Cannot save a {type(wcs).__name__} in a session")


def _wcs_from_record(rec):
    kind = rec["kind"]
    if kind == "asdf":
        with asdf.open(io.BytesIO(base64.b64decode(rec["b64"])), lazy_load=False, memmap=False) as af:
            return af["wcs"]
    if kind == "sliced":
        slices = [s if isinstance(s, int) else slice(*s) for s in rec["slices"]]
        return SlicedLowLevelWCS(_wcs_from_record(rec["wcs"]), slices)
    if kind == "compound":
        return CompoundLowLevelWCS(*map(_wcs_from_record, rec["parts"]), mapping=rec["mapping"])
    header = fits.Header.fromstring(rec["header"])
    if kind == "fits-tab":
        wcs = WCS(header, fits.open(io.BytesIO(base64.b64decode(rec["table"]))))
    else:
        wcs = WCS(header)
    if rec.get("shape"):
        wcs.pixel_shape = tuple(rec["shape"])  # to_header drops NAXISn; the -TAB rebuild needs it on a re-save
    return wcs


# methods of _GlueWCS (glue checks __gluestate__ before its saver registry, state.py:378)
def __gluestate__(self, context):
    return {"wcs": _wcs_record(self._wcs)}


@classmethod
def __setgluestate__(cls, rec, context):
    return cls(_wcs_from_record(rec["wcs"]))


@saver(u.Quantity)
def _save_quantity(quantity, context):
    # glue-core routes Quantity to its ndarray saver, and np.save raises on it
    return {"value": context.do(np.asarray(quantity.value)), "unit": quantity.unit.to_string()}


@loader(u.Quantity)
def _load_quantity(rec, context):
    return u.Quantity(context.object(rec["value"]), rec["unit"])


class SolarVisualAttributes(VisualAttributes):
    """Style whose preferred colormap survives a session (glue-core writes the Colormap object, which is not JSON)."""

    def __gluestate__(self, context):
        atts = {name: getattr(self, name) for name in self.DEFAULT_ATTS}
        atts["preferred_cmap"] = getattr(atts["preferred_cmap"], "name", atts["preferred_cmap"])
        return atts

    @classmethod
    def __setgluestate__(cls, rec, context):
        atts = {name: rec[name] for name in cls.DEFAULT_ATTS}
        try:
            return cls(**atts)
        except ValueError:  # colormap name unknown in this environment; keep the rest of the style
            return cls(**{**atts, "preferred_cmap": None})


def read_iris_rasters(path, files=None, windows=None, stack=False):
    """
    Data-factory form of `raster_data` so `load_data` can log how to re-read the files.

    ``path`` is the first raster file; ``files`` lists every raster file of the observation
    relative to its folder (so a session saved with relative paths can move with the data).
    """
    folder = os.path.dirname(path)
    files = [path] if files is None else [os.path.join(folder, name) for name in files]
    return L.raster_data(files, windows, stack)
```

Applied in the prototype with `L._GlueWCS.__gluestate__ = __gluestate__; L._GlueWCS.__setgluestate__ = __setgluestate__; L.VisualAttributes = SolarVisualAttributes; M.VisualAttributes = SolarVisualAttributes` (the last two are what "use `SolarVisualAttributes` in `_cube_data` and `_parse_sunpy_map`" means).

### 3. End-to-end round trips, full pixel grid (`wp3_roundtrip.py`)

Each line: `GlueSerializer(DataCollection([data])).dumps()` then `GlueUnSerializer.loads(s).object("__main__")[0]`; `pixel_to_world_values` compared on the full pixel grid and on the grid shifted by 0.37 px with `atol=1e-9`; NaN counts equal; `world_to_pixel_values` of the original vs the restored on the same world grid (`<= 1e-9`); `world_axis_names`, `world_axis_units` and world component labels equal. "caught" is the set of warning classes raised during save+load.

```
versions: {'glue': '1.27.0', 'astropy': '8.0.1', 'asdf': '5.3.1', 'gwcs': '1.0.3', 'ndcube': '2.4.1', 'irispy': '0.8.1'}
-- browser path (arrays embedded) --
SJI_1330 (gwcs via asdf): 1225 KB | coords _GlueWCS(WCS) | p2w<=1e-9 on 76960 px | w2p orig-vs-restored 0.0e+00 (p2w->w2p closure 1.8e-09) | meta 148/148 | cmap irissji1330 | caught []
SJI_1400 3880012095 (raster/ dir): 624 KB | coords _GlueWCS(WCS) | p2w<=1e-9 on 38804 px | w2p orig-vs-restored 0.0e+00 (p2w->w2p closure 1.8e-09) | meta 148/148 | cmap irissji1400 | caught []
raster C II 1336 (-TAB rebuild): 415 KB | coords _GlueWCS(WCS) | p2w<=1e-9 on 14824 px | w2p orig-vs-restored 3.1e-13 (p2w->w2p closure 2.1e-06) | meta 398/400 | cmap None | caught []
raster C II 1336 saved AGAIN from the restored dataset: 415 KB | coords _GlueWCS(WCS) | p2w<=1e-9 on 14824 px | w2p orig-vs-restored 0.0e+00 (p2w->w2p closure 2.1e-06) | meta 398/398 | cmap None | caught []
sit-and-stare raster 3620258102 C II 1336: 3547 KB | coords _GlueWCS(WCS) | p2w<=1e-9 on 134640 px | w2p orig-vs-restored 1.0e-11 (p2w->w2p closure 3.3e-06) | meta 365/367 | cmap None | caught []
stack 3 scans (compound + sliced + -TAB): 1190 KB | coords _GlueWCS(CompoundLowLevelWCS) | p2w<=1e-9 on 44472 px | w2p orig-vs-restored 3.1e-13 (p2w->w2p closure 2.1e-06) | meta 398/400 | cmap None | caught []
stack saved AGAIN from the restored dataset: 1190 KB | coords _GlueWCS(CompoundLowLevelWCS) | p2w<=1e-9 on 44472 px | w2p orig-vs-restored 0.0e+00 (p2w->w2p closure 2.1e-06) | meta 398/398 | cmap None | caught []
```
("coords _GlueWCS(WCS)" for the SJI is `gwcs.wcs._wcs.WCS`, the class name collides with astropy's.) Checker note: re-run today reproduces every line above verbatim; after them the script's trailing "sunpy Map" section dies on its own print statement (`AttributeError: 'WCS' object has no attribute '_wcs'`, the report line assumes a `_GlueWCS` wrapper), which is a script bug, not an implementation failure. The sunpy Map round trip is covered by `wp3_map.py` (section 4) and by `test_sunpy_map_session_saves_and_keeps_colormap` (section 9). Records seen in the JSON:
```
coords record: {'_type': 'glue_solar.sources.loaders.iris._GlueWCS', 'wcs': {'b64': '<15748 chars b64 asdf>', 'kind': 'asdf'}}
style record (inline in the Data record): {'_type': 'wp3_impl.SolarVisualAttributes', 'alpha': 0.8, 'color': '#595959', 'linestyle': 'solid', 'linewidth': 1, 'marker': 'o', 'markersize': 3, 'preferred_cmap': 'irissji1330'}
meta Quantity round trip: {'exposure time': ('Quantity', (8,), 's'), 'observer radial velocity': ('Quantity', (8,), 'm / s')} | equal: True | dropped: ['auxiliary times', 'exposure FOV center']
Time component intact: True datetime64[ns]
```
Stack axis names (`wp3_stackdbg.py`), the check that caught pitfall 1:
```
names ['Wavelength', 'Helioprojective Latitude', 'Helioprojective Longitude', 'Scan'] -> ['Wavelength', 'Helioprojective Latitude', 'Helioprojective Longitude', 'Scan']
units ('m', 'arcsec', 'arcsec', '') -> ('m', 'arcsec', 'arcsec', '')
```
(`'m'` is today's wrapper output; after WP1/D3 the same line reads `'Angstrom'` on both sides. The record stores the raw metre WCS either way, so nothing in WP3 changes with D3.)

### 4. sunpy Map from `maps.py` and a plain dataset in one session (`wp3_map.py`)

```
sunpy AIA map: 10 KB | style SolarVisualAttributes | cmap sdoaia171 | coords WCS | p2w maxdiff 0.0 | meta 31 of 31 | data equal True
  style record of 'plain': _type=glue.core.visual.VisualAttributes _protocol=None preferred_cmap=None
  style record of 'sunpy-map-AIA 171.0 Angstrom 2020-01-01 00:00:00': _type=wp3_impl.SolarVisualAttributes _protocol=None preferred_cmap='sdoaia171'
```

### 5. LoadLog through `load_data` and relocation (`wp3_loadlog.py`)

Data copied to `<scratch>/wp3_sess/a/data/`, cwd set to `<scratch>/wp3_sess/a` (glue's `save_session`/`restore_session` chdir to the session folder), sessions saved with `include_data=False, absolute_paths=False`, then the whole folder copied to `wp3_sess/b`, the original deleted, and the sessions reloaded from `b`.

```
SJI via read_iris_file: 1 dataset(s) | relative-paths session 22 KB (data embedded: 1225 KB) | biggest records [('_GlueWCS', 15837), ('Data', 4838)]
   LoadLog record: {'factory': {'_type': 'types.FunctionType', 'function': 'glue_solar.sources.iris.read_iris_file'}, 'kwargs': [[]], 'path': 'data/iris_l2_20210905_001833_3620258102_SJI_1330_t000.fits'}
raster file, all 9 windows: 9 dataset(s) | relative-paths session 249 KB (data embedded: 4455 KB) | biggest records [('_GlueWCS', 130787), ('Data', 97291)]
   LoadLog record: {'factory': {'_type': 'types.FunctionType', 'function': 'wp3_impl.read_iris_rasters'}, 'kwargs': [[]], 'path': 'data/iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits'}
3 scans of C II 1336, stacked: 1 dataset(s) | relative-paths session 32 KB (data embedded: 1190 KB) | biggest records [('_GlueWCS', 17579), ('Data', 10853)]
   LoadLog record: {'factory': {'_type': 'types.FunctionType', 'function': 'wp3_impl.read_iris_rasters'}, 'kwargs': [[['files', ['iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits', 'iris_l2_20140329_140938_3860258481_raster_t000_r00001.fits', 'iris_l2_20140329_140938_3860258481_raster_t000_r00002.fits']], ['windows', ['C II 1336']], ['stack', True]]], 'path': 'data/iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits'}
3 scans of C II 1336, separate: 3 dataset(s) | relative-paths session 86 KB (data embedded: 1245 KB) | biggest records [('_GlueWCS', 43596), ('Data', 32433)]
-- relocate data + sessions to another folder and reload there --
SJI via read_iris_file: reloaded 1 dataset(s) from s0.glu | shape (52, 40, 37) | coords WCS | p2w maxdiff 0.0e+00 | components identical True | labels ['SJI_1330-3620258102-2021-09-05T00:18:33']
raster file, all 9 windows: reloaded 9 dataset(s) from s1.glu | shape (8, 109, 17) | coords WCS | p2w maxdiff 5.7e-14 | components identical True | labels ['C_II_1336-3860258481-2014-03-29T14:09:38-scan-0', '1343-3860258481-2014-03-29T14:09:38-scan-0']
3 scans of C II 1336, stacked: reloaded 1 dataset(s) from s2.glu | shape (3, 8, 109, 17) | coords CompoundLowLevelWCS | p2w maxdiff 5.7e-14 | components identical True | labels ['C_II_1336-3860258481-2014-03-29T14:09:38-stack']
3 scans of C II 1336, separate: reloaded 3 dataset(s) from s3.glu | shape (8, 109, 17) | coords WCS | p2w maxdiff 5.7e-14 | components identical True | labels ['C_II_1336-3860258481-2014-03-29T14:09:38-scan-0', 'C_II_1336-3860258481-2014-03-29T14:09:38-scan-1']
LOADLOG OK
```
The 249 KB of the 9-window session is 131 KB of nine -TAB records (one per window, each carrying its own 8x2x2 coordinate table plus header) and 97 KB of Data records (component ids, links). The audit's "23 KB / 255 KB" numbers are reproduced within a few KB (the header-string change shaved ~9 KB).

### 6. The version-2 style override trap (`wp3_style_trap.py`)

```
v2 style record of a plain dataset: {'_protocol': 2, '_type': 'glue.core.visual.VisualAttributes', 'alpha': 0.8, 'color': '#595959', 'linestyle': 'solid', 'linewidth': 1, 'marker': 'o', 'markersize': 3, 'preferred_cmap': None}
in-process reload with v2 registered: plain
-- fresh interpreter WITHOUT glue_solar --
wp3_stock.glu -> plain
wp3_v2.glu -> FAIL GlueSerializeError: Don't know how to load objects of type <class 'glue.core.visual.VisualAttributes
glue_solar imported: False
```

### 7. Metadata survey over every irispy test file (`wp3_meta.py`, condensed)

```
iris_l2_20140329_140938_3860258481_raster_t000_r000NN   SGMeta    400 keys  non-scalar: {'auxiliary times': 'Time(8,)', 'exposure time': 'Quantity(8,) [s]', 'exposure FOV center': 'SkyCoord(8,)', 'observer radial velocity': 'Quantity(8,) [m / s]', 'orbital phase': 'ndarray(8,)'}   (all 13 scans identical)
iris_l2_20210905_001833_3620258102_raster_t000_r00000.f read_files FAIL ValueError: Expected 187 NUV source filename rows, found 1872
iris_l2_20210905_001833_3620258102_SJI_{1330,1400,2796,2832}_t000.fits   SJIMeta   148 keys  non-scalar: {}
iris_l2_20230408_110821_3880012095_SJI_{1400,2796,2832}_t000.fits        SJIMeta   148 keys  non-scalar: {}
u.Unit('DN_IRIS_NUV') -> ValueError (irispy does not enable its units globally; only Component.units strings carry them, no Quantity does)
```

### 8. `pixel_shape` regression guard

```
record keys ['b64', 'kind', 'shape'] shape [17, 109, 8]        (pre-rename run; keys are now header/kind/shape/table)
without the stored shape: pixel_shape = None
re-save of that WCS fails: TypeError 'NoneType' object is not subscriptable
with the stored shape: pixel_shape = (17, 109, 8) | re-save bytes 11520
```

### 9. Checker run: the brief applied end to end in a throwaway worktree (`wp3chk_patch.py`, `wp3chk_dialog.py`)

`git -C /Users/nabil/Git/glue-solar worktree add --detach <scratch>/wt-wp3chk d3a2bd3`, then `wp3chk_patch.py` pasted "Verified code" 2 into `loaders/iris.py` / `sources/iris.py` / `maps.py` exactly as steps 1-6 say (including the `finalize` rewrite) and wrote `glue_solar/tests/test_sessions.py` as specified below. `git diff --stat`: `sources/iris.py +18 -1`, `loaders/iris.py +120 -9`, `maps.py +4 -2`.

```
$ cd <scratch>/wt-wp3chk && HOME=<scratch>/home-wp3chk QT_QPA_PLATFORM=offscreen MPLBACKEND=agg \
    /Users/nabil/Git/glue-solar/.venv/bin/python -m pytest glue_solar -o addopts='' -q -p no:cacheprovider
.................................                                        [100%]
33 passed in 3.54s
```
(27 existing + 6 new; `filterwarnings = error` from `pytest.ini` active. First attempt failed only because the browser test ticked the raster observation's top-level row, which loads all 9 windows -> 10 datasets; tick the "C II 1336" child instead, as the test spec below now says.)

Browser dialog on a folder holding `..._3620258102_SJI_1400_t000.fits` plus the three `3860258481` `r00000..r00002` raster files, SJI row and the "C II 1336" child ticked, `stack` checked, `finalize()`, cwd = that folder:
```
datasets: ['SJI_1400-3620258102-2021-09-05T00:18:33', 'C_II_1336-3860258481-2014-03-29T14:09:38-stack'] | load_log: [True, True] | first_image: SJI_1400-3620258102-2021-09-05T00:18:33
relative-paths session: 56 KB
  LoadLog: iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits [[]] glue_solar.sources.iris.read_iris_file
  LoadLog: iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits [[['files', ['iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits', 'iris_l2_20140329_140938_3860258481_raster_t000_r00001.fits', 'iris_l2_20140329_140938_3860258481_raster_t000_r00002.fits']], ['windows', ['C II 1336']], ['stack', True]]] glue_solar.sources.iris.read_iris_rasters
reloaded: ['SJI_1400-3620258102-2021-09-05T00:18:33', 'C_II_1336-3860258481-2014-03-29T14:09:38-stack']
```

Save-failure UI on the unpatched branch (`wp3chk_dialog.py`: `GlueApplication()`, `image_data(SJI_1330)` appended, `app.report_error` stubbed, `app.save_session(path, include_data=False, absolute_paths=False)`):
```
report_error called: 1
message: Failed to save session | Don't know how to serialize <glue_solar.sources.loaders.iris._GlueWCS object at
file written: False
report_error uses QMessageBox: True
```

## Tests to add

File `glue_solar/tests/test_sessions.py`. The complete file that passed today is `<scratchpad>/wp3chk_test_sessions.py`; copy it verbatim (the bullets below describe it). Real files from the `irispy_test_files` fixture (`glue_solar/conftest.py:94-101`); no synthetic FITS (the synthetic `iris_tree` files in `conftest.py` contain no WCS-TABLE or gWCS, grep count 0). Helpers:

```python
def _round_trip(data):
    dc = DataCollection([data])  # a Data can join only one DataCollection (hub); build a fresh Data per test
    s = GlueSerializer(dc).dumps()
    return s, GlueUnSerializer.loads(s).object("__main__")

def _real(files, name):
    return next(path for path in files if path.name == name)  # same helper as test_importer.py:28

def _style_record(s, label):
    # the style dict is inline in the Data record; find the Data record by label
    return next(rec for rec in json.loads(s).values() if isinstance(rec, dict) and rec.get("label") == label)["style"]

def _assert_same_coords(original, restored):
    grid = np.meshgrid(*[np.arange(n) for n in original.shape[::-1]], indexing="ij")
    for shift in (0, 0.37):
        pixels = [g + shift for g in grid]
        for expected, actual in zip(original.coords.pixel_to_world_values(*pixels), restored.coords.pixel_to_world_values(*pixels)):
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
    world = original.coords.pixel_to_world_values(*grid)
    for expected, actual in zip(original.coords.world_to_pixel_values(*world), restored.coords.world_to_pixel_values(*world)):
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
    assert restored.coords.world_axis_names == original.coords.world_axis_names
    assert restored.coords.world_axis_units == original.coords.world_axis_units
    assert [c.label for c in restored.world_component_ids] == [c.label for c in original.world_component_ids]
```
Do not assert the pixel->world->pixel closure at 1e-9: wcslib's iterative -TAB inverse closes only to ~2e-6 px on the ORIGINAL WCS too (measured 2.1e-6 on 3860258481, 3.3e-6 on the sit-and-stare file). Compare restored-vs-original inverses, as above (3e-13).

- `test_sji_session_restores_gwcs_meta_and_colormap(irispy_test_files)`: `image_data(sns/..._SJI_1330_t000.fits)`; `_round_trip`; `_assert_same_coords`; `assert type(restored.coords._wcs).__module__.startswith("gwcs")`; `assert len(restored.meta) == 148`; `assert restored.style.preferred_cmap.name == "irissji1330"`; `style = _style_record(s, original.label)`; `assert style["_type"] == "glue_solar.sources.loaders.iris.SolarVisualAttributes"` and `"_protocol" not in style`.
- `test_raster_session_rebuilds_the_tab_table(irispy_test_files)`: `raster_data([3860258481 r00000], ["C II 1336"])[0]`; `_round_trip`; `_assert_same_coords`; `assert list(restored.coords._wcs.wcs.ctype)[1:] == ["HPLT-TAB", "HPLN-TAB"]` (passes as written today); `assert isinstance(restored.meta["exposure time"], u.Quantity)` and `np.testing.assert_array_equal(restored.meta["exposure time"], original.meta["exposure time"])` with `.unit == u.s`; `assert "auxiliary times" not in restored.meta and "exposure FOV center" not in restored.meta`; `np.testing.assert_array_equal(restored["Time"], original["Time"])`; then `_round_trip(restored)` must succeed again and `_assert_same_coords(original, restored2)` (guards the `pixel_shape` regression; pass the restored DataCollection's Data, it already belongs to a hub, so serialize its own collection: `GlueSerializer(dc2).dumps()`).
- `test_stack_session_restores_compound_wcs(irispy_test_files)`: 3 scans of 3860258481, `raster_data(paths, ["C II 1336"], stack=True)[0]`; `_round_trip`; `_assert_same_coords`; `assert restored.coords.world_axis_names[-1] == "Scan"` (guards the slice-order bug); `assert isinstance(restored.coords._wcs, CompoundLowLevelWCS)`; `Time` and `<label> mask` components equal (`np.testing.assert_array_equal`); `np.testing.assert_array_equal(restored[label], original[label])` (NaN-safe: use `equal_nan=True` via `np.array_equal`).
- `test_sunpy_map_session_saves_and_keeps_colormap()`: synthetic map as in `ver_sess4.py` (`sunpy.map.make_fitswcs_header(np.zeros((16, 16)), SkyCoord(0*u.arcsec, 0*u.arcsec, obstime="2020-01-01", observer="earth", frame=Helioprojective), scale=[2, 2]*u.arcsec/u.pix, instrument="AIA", wavelength=171*u.angstrom, telescope="SDO")`), `_parse_sunpy_map(Map, "sunpy-map")`; `_round_trip` must not raise; `assert restored.style.preferred_cmap.name == "sdoaia171"`; `assert len(restored.meta) == 31`; coords equal on the 16x16 grid.
- `test_browser_datasets_reference_their_files(qtbot, tmp_path, irispy_test_files, monkeypatch)`: copy `iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits` and the three `3860258481` raster files `r00000..r00002` into `tmp_path`; `dialog = QtIRISImporter(tmp_path)`, `qtbot.addWidget(dialog)`. Two top-level rows appear (order not guaranteed): the SJI-only observation (`childCount() == 0`, tick the row itself) and the raster observation (tick ONLY the child whose `text(0).startswith("C II 1336")`; ticking the raster row loads all 9 windows and gives 10 datasets). `dialog.stack.setChecked(True)`, `dialog.finalize()`; `assert len(dialog.datasets) == 2`; `assert all(hasattr(d, "_load_log") for d in dialog.datasets)`; `monkeypatch.chdir(tmp_path)`; `s = GlueSerializer(DataCollection(dialog.datasets), include_data=False, absolute_paths=False).dumps()`; `assert len(s) < 200_000` (measured 56 KB); LoadLog records are the JSON values whose `_type` ends with `LoadLog`; the one with non-empty `kwargs` has `kwargs == [[["files", [three basenames]], ["windows", ["C II 1336"]], ["stack", True]]]`; every LoadLog `path` has no `/` (relative to `tmp_path`); reload with `GlueUnSerializer.loads(s).object("__main__")`, pick the dataset whose label ends with `-stack` on both sides, `np.array_equal(..., equal_nan=True)` on the science component and `_assert_same_coords`. Passed today as written.
- `test_plain_data_keeps_the_stock_style_record()`: `Data(x=[1, 2, 3])`; style record `_type == "glue.core.visual.VisualAttributes"` and no `_protocol` (guards against someone reintroducing the v2 override).

## Pitfalls (verified)

1. `SlicedLowLevelWCS` slices: the constructor takes ARRAY-order slices; `_slices_pixel` is the reversed copy. Storing `_slices_pixel` and feeding it back flips the kept axis. On the stack this was numerically invisible (both axes of the scan WCS are `crpix=1, crval=0, cdelt=1`) and only showed as `world_axis_names[-1] == ''` instead of `'Scan'`. The audit's 50-random-pixel check did not catch it. Use `_slices_array` (`astropy/wcs/wcsapi/wrappers/sliced_wcs.py:139-141`).
2. `WCS.to_header()` drops `NAXISn`, so a restored WCS has `pixel_shape = None`; the -TAB rebuild indexes `pixel_shape` and a re-save of a restored session raised `TypeError: 'NoneType' object is not subscriptable`. Store `"shape"` and reassign `pixel_shape` on load (verified code 8).
3. Putting the WCS header into the table HDUList's PrimaryHDU makes astropy write `NAXIS = 0`, and `WCS(hdulist[0].header, hdulist)` then emits `FITSFixedWarning: The WCS transformation has more axes (3) than the image it is associated with (0)`. `pytest.ini` has `filterwarnings = error`, so that would fail every raster/stack test. Keep the header as its own string in the record (final code emits no warning: "caught []").
4. Stock glue -TAB behaviour is save-OK/load-fail, not save-fail: `_save_wcs` writes the header (2880 chars, PS keys present, table gone); `_load_wcs` raises `ValueError: HDUList is required to retrieve -TAB coordinates and/or indices`. The plan/audit wording "raises rather than silently dropping" is backwards.
5. `wcslib` -TAB inverse closure is ~2e-6 px on the original WCS (verified code 3); tests that assert `world_to_pixel(pixel_to_world(p)) == p` at 1e-9 fail for reasons unrelated to serialization. Compare inverses of original vs restored instead.
6. The version-2 `VisualAttributes` override makes ALL sessions saved with glue-solar installed unloadable without it (verified code 6). `VersionedDict` cannot re-register version 1 (`state.py:235-237`, `KeyError: Cannot overwrite version`), so an in-process override has to be a new version; the subclass sidesteps it.
7. `Quantity` in `data.meta` hits `@saver(np.ndarray)` by MRO; glue's meta filter only catches `GlueSerializeError` (`state.py:1027-1033`), so the `TypeError` from `np.save` propagates. Registering `@saver(u.Quantity)` wins the MRO walk (`Quantity` precedes `ndarray`).
8. `irispy.io.read_files` on the sit-and-stare test raster `sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits` with `spectral_windows=None` raises `ValueError: Expected 187 NUV source filename rows, found 1872`; every window loads on its own (verified, 8 windows, shapes `(187, 40, n)`). Pre-existing irispy 0.8.1 issue, so `read_iris_file` (File -> Open) fails on that file today. Tests must pass `windows=[...]` for it.
9. A `Data` can belong to one `DataCollection` only (`Data has already been assigned to a different hub`); build fresh datasets per test and serialize a restored dataset through the DataCollection it was restored into.
10. "Glue Session including data" (`include_data=True`) base64-embeds every component: 1.2 MB for the 52x40x37 test SJI, 4.5 MB for one 9-window test raster file; real observations are GB. The default filter in glue-qt is "relative paths", which is the LoadLog path. Browser-loaded data without a LoadLog silently embeds even under "relative paths" (that is what step 6 fixes).
11. Relative-path sessions: glue chdirs to the session folder for save and restore (`application_base.py:120-127, 157-163`). LoadLog only relativises its `path`; extra kwargs are stored verbatim, hence `files` are stored relative to `dirname(path)` and rejoined in `read_iris_rasters`.
12. `load_data` unpacks a 1-element result to a bare `Data` (`helpers.py:314-316`); use `glue.utils.as_list` in `finalize`.
13. `asdf.open(..., lazy_load=False, memmap=False)`: asdf 5 API (`copy_arrays` is gone). The returned gWCS is fully materialised and usable after the context manager closes (verified on two SJI files).
14. A save failure IS reported in a modal error box ("Failed to save session", `application_base.py:100` `@catch_error` -> `GlueApplication.report_error`, verified today), not only in the log widget; the earlier claim that only the console button reddens was wrong. After WP3 nothing in glue-solar raises, but a foreign coords type would raise `GlueSerializeError("Cannot save a X in a session")` from `_wcs_record` into that box, and no file is written.
15. `SolarVisualAttributes.__setgluestate__` restores the cmap by NAME through the `preferred_cmap` setter (`glue/core/visual.py:124-142`, `matplotlib.colormaps[name]` then `glue.config.colormaps`); `import glue_solar` alone registers `irissji*`/`sdoaia*` with matplotlib (its `__init__` imports `sunpy.visualization.colormaps`; verified today: `'irissji1330' in matplotlib.colormaps` is False before and True after the import, `VisualAttributes(preferred_cmap='irissji1330')` resolves without `setup()`), and `glue_solar.setup()` additionally adds them to glue's registry. An unregistered name falls back to `None` rather than failing the load.
16. Reloaded `data.meta` is an `OrderedDict`, not `SGMeta`/`SJIMeta` (glue-core behaviour, `state.py:1059-1060` does `result.meta.update(...)`). Nothing in glue-solar depends on the Meta class.

## Acceptance criteria

- [ ] `GlueSerializer(...).dumps()` and `GlueUnSerializer.loads(...)` succeed for: a real SJI (gWCS), a real raster window (-TAB), a 3-scan stack (compound), a sunpy Map, and a mixed collection with a plain `Data`.
- [ ] Full-grid `pixel_to_world_values` (grid and grid+0.37) agree to `atol=1e-9`; `world_to_pixel_values` of original vs restored agree to `1e-9`; `world_axis_names`, `world_axis_units`, world component labels identical; stack `world_axis_names[-1] == "Scan"`.
- [ ] A restored dataset can be saved and restored again with the same guarantees (pixel_shape retained).
- [ ] `meta["exposure time"]` and `meta["observer radial velocity"]` come back as `Quantity` with equal values and units; SJI keeps 148/148 keys; raster keeps 398/400.
- [ ] `preferred_cmap` restored by name for SJI/AIA (`irissji1330`, `sdoaia171`); plain datasets' style records unchanged (no `_protocol`, stock `_type`).
- [ ] Browser-loaded datasets carry `_load_log`; "relative paths" session of the test SJI < 100 KB and of a 3-scan stack < 100 KB; relocated data+session folder reloads with identical components and coordinates.
- [ ] `pytest glue_solar -o addopts=''` passes with `filterwarnings = error` (no `FITSFixedWarning`, no asdf warnings).
- [ ] Existing tests (27) still pass; `test_load_selected_real_sji`, `test_duplicate_real_raster_is_listed_and_loaded_once`, `test_reader_failure_stays_in_dialog` unchanged (checker: 33 passed in the worktree with the brief applied verbatim).
- [ ] `pre-commit run --all-files` clean (ruff isort ordering of the new imports, unused `VisualAttributes` import removed from `maps.py`).
- [ ] No new entry in `pyproject.toml` dependencies (asdf/gwcs come via irispy).
- [ ] Docs paragraph and changelog fragments updated; planning docs reworded.

## Dropped / out of scope

- Savers for `astropy.time.Time` and `SkyCoord` meta values: glue drops them silently and nothing in glue-solar reads them.
- Generic astropy `-TAB` writer / `Tabprm` index exposure upstream: large, IRIS does not need it; the `# ponytail:` comment names it as the upgrade path.
- glue-core one-liners (optional, release-gated; glue-solar keeps its code either way): `_save_style` -> `preferred_cmap: getattr(style.preferred_cmap, "name", style.preferred_cmap)` (`state.py:746`), and `_save_data_5` `except GlueSerializeError` -> `except Exception` (`state.py:1033`). Neither has an upstream issue; open them only if someone wants glue-core to stop crashing for other plugins.
- The version-2 `VisualAttributes` saver/loader: works but poisons non-solar sessions (verified code 6).
- Registering `read_iris_rasters` as a `@data_factory`: File -> Open already routes IRIS files to `read_iris_file`; the factory exists only to be re-run by LoadLog.
- `TUNITn` keys on the rebuilt WCS-TABLE: wcslib does not apply them for -TAB coordinates (irispy's own comment; equality verified without them).
- Qt-free placement of `_GlueWCS` so plain glue-core could load solar sessions: `glue_solar/__init__.py` imports `sources.iris` which imports `qtpy`, so the package is Qt-bound regardless; a separate refactor.
- Viewer-state and layer restoration for P3.4 line-list layers (`layer_artist_maker`): needs its own saver; not part of WP3.
- Restoring the browser's `first_image` viewer on session load: glue restores viewers itself.
- The irispy 0.8.1 `read_files(spectral_windows=None)` failure on the sit-and-stare test file (pitfall 8): irispy bug, report upstream separately.

## Docs

`docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`, replace lines 61-66 with:

```
Saving sessions
---------------

"File -> Save Session" stores and restores IRIS datasets, including irispy's time-varying SJI gWCS,
the raster ``-TAB`` lookup tables, stacked 4D cubes and the preferred colormaps. Datasets loaded
through the observation browser or "File -> Open Data Set" are saved as references to the Level 2
files (the "relative paths" and "absolute paths" session types), so keep the session next to the
data or choose absolute paths; "including data" embeds the cubes themselves and is only practical
for small files. Metadata values that are astropy ``Time`` or ``SkyCoord`` objects
(``auxiliary times``, ``exposure FOV center``) are not kept in the session; every other entry of
``data.meta`` is, ``Quantity`` values included.
```

`changelog/<PR>.feature.rst`:
```
Glue sessions now save and restore IRIS datasets: irispy's SJI gWCS, the raster ``-TAB`` lookup tables, stacked 4D cubes, ``Quantity`` metadata and the preferred colormaps all survive a round trip, and datasets loaded through the observation browser are saved as references to their Level 2 files instead of embedded arrays.
```

`changelog/<PR>.bugfix.rst`:
```
Saving a session containing a sunpy Map loaded by glue-solar no longer fails with "Object of type LinearSegmentedColormap is not JSON serializable"; the map's colormap is restored with the session.
```

`IRIS_GLUE_GAP_PLAN.md:52`: "Session round trips | Missing | glue-solar | `__gluestate__` on `_GlueWCS` (gWCS via asdf, `-TAB` table rebuilt from `Tabprm`, compound/sliced records), `Quantity` saver, `SolarVisualAttributes`, browser through `load_data`". `:165-171`: replace "glue-core + glue-solar ... Only as a complete unit ... keep documenting sessions as unsupported" with "glue-solar only; the pieces are independent (gWCS, -TAB, compound, meta, colormap, LoadLog); ~120 lines plus tests; no glue-core or glue-astronomy saver exists or is needed". `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md:141-144`: "Sessions containing IRIS datasets could not be saved at all (three independent exceptions: `_GlueWCS` unserializable, `Quantity` metadata, `Colormap` in `preferred_cmap`); a header-only WCS saver would have saved and then failed to load with `HDUList is required`. Fixed in glue-solar by WP3."


---

# WP4 - Quicklook bundle: whisker preset, quicklook layout, slit subset, time link and slice sync

**Goal.** Make "Plugins -> IRIS: browse observations…" open the IDL-style quicklook (SJI viewer with the slit drawn per frame, raster map viewer, mean-spectrum Profile viewer), with the datasets linked in space (WP1 `link_hpc`) and in time (nearest exposure), and with every Image Viewer slider following the others. Add a one-click whisker preset. Everything ships in glue-solar on released glue-core 1.27.0 + glue-qt main; nothing here needs a fork branch.

Checked 2026-09-02 (checker pass): every file:line below re-opened, every run re-executed with `HOME=<scratch>/home-wp4chk`. One design change versus the writer's draft, backed by a new run: the `JoinLink` is dropped (see Pitfall 1). All link counts, tests and docs below already reflect that.

## Current state (2026-09-02)

- `glue_solar/sources/iris.py:30-48` `browse_iris`: loads through `QtIRISImporter`, calls `app.add_datasets(dialog.datasets)` (`:44`) and opens ONE `ImageViewer` on `dialog.first_image` (`:45-48`). No links, no presets, no profile viewer (grep of `glue_solar/` for `LinkSame|ComponentLink|add_link|x_att|whisker|slit|SLTPX` finds nothing).
- `glue_solar/sources/loaders/iris.py:72-85` `_cube_data`: adds a datetime64 `Time` component only when `cube.extra_coords` has a `time` key (`:81-84`). Rasters have it; SJI cubes do not (`SJICube.extra_coords` keys are `exposure time, obs_vrix, ophaseix, pztx, ...`), so SJI datasets carry time only as the gWCS world axis `Time (Utc)` in seconds since the frame reference epoch (verified in (d)).
- `glue_solar/sources/loaders/iris.py:110-114` `_image_cube_data`: no slit information although irispy 0.8.1 `io/sji.py:209-218` already exposes the aux columns `SLTPX1IX/SLTPX2IX` as `extra_coords['slit x position'|'slit y position']` (unit label `u.arcsec`; the values are SJI pixel indices). AIA cutouts go through the same reader (`io/utils.py:196-200`, `read_sji_lvl2`; class `AIACube` at `io/sji.py:239`).
- `glue_solar/sources/loaders/stack_spectrograms.py` produces the 4D stack `(scan, step, slit, wavelength)` with a `Time` array of shape `(nscan, nstep, nslit)` broadcast into the cube by `_raster_collection_data` (`loaders/iris.py:97-102`, `add_component` at `:101`). The stacked cube's WCS physical types are `('em.wl', lat, lon, None)`: no `time` axis, no extra coords (verified below).
- glue-core 1.27 (site-packages, byte-identical to the fork's main for these files): `ImageViewerState.x_att/y_att` are pixel cids (`glue/viewers/image/state.py:76-79`), `slices` is a tuple of ints of length `ndim` (`:90`); entries on the displayed axes are ignored (`:318 _set_default_slices`, `:336-349`). `ProfileViewerState.x_att` accepts a world or pixel cid (`profile/state.py:37`), `function` choices are `maximum/minimum/mean/median/sum` (`:22-26`), no `slices` attribute (only on the fork branch `profile-wcs`: `slices` at its `state.py:52`, `'slice'` function at `:28`). glue-qt `MultiSliceWidgetHelper` listens to viewer-state `slices` (`glue_qt/viewers/common/slice_widget.py:26`), so programmatic slice changes move the Qt sliders. No viewer-added hub message exists (`glue/core/message.py` has none; `GlueApplication.new_data_viewer` at `glue_qt/app/application.py:1014` broadcasts nothing). `Data.get_mask` (`glue/core/data.py:1436-1440`) falls back to `get_mask_with_key_joins` (`glue/core/joins.py:35`) on `IncompatibleAttribute`.
- Default Image Viewer for a 3D raster window is already `x=Pixel Axis 2` (wavelength), `y=Pixel Axis 1` (slit), slider on axis 0 (step): that IS the spectroheliogram (verified in (a)). Only the whisker needs code.
- Docs: `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:31-32` describes the single viewer; `:57-59` tells users to pair `Helioprojective Longitude/Latitude` by hand and names SJI components that do not exist (SJI world cids are `Time (Utc)`, `Latitude`, `Longitude`).
- Planning docs under review: `IRIS_GLUE_GAP_PLAN.md` table rows L37/L39/L42/L43, Phase 1.2 (L67-72), 1.3 (L73-77), 1.6 (L86-89), Phase 3.2 (L148-154), non-goal L186-188, order table L198; `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md:171-182`.
- Baseline today: `pytest glue_solar -q -o addopts="" -p no:cacheprovider` -> `27 passed, 2 warnings in 1.52s`.

## Decisions already made

- D1: `link_hpc` (WP1, world components by physical type) is permanent. The quicklook calls it; the fork's APE-14 WCSLink is additive and not required.
- D2: everything below is glue-solar code through public glue APIs (`menubar_plugin`, `Data.add_component`, `Data.new_subset`, `ComponentLink`, `DataCollection.add_link`, `ImageViewerState.slices`, `echo` callbacks). No glue-core or glue-qt PR.
- D3: WP1 switches `_GlueWCS` wavelength to Angstrom. WP4 does not touch units; the Profile viewer keeps the native unit (`x_display_unit` untouched), so it shows Angstrom once WP1 is in. Nothing in WP4 hard-codes metres or Angstrom.
- D4 (moments = `layer_action`) does not touch WP4.
- Audit (viewer-composition, verified): Spectroheliogram = default layout, document only; whisker = `x_att=pix[-1], y_att=pix[-3]`, slider on the slit axis; quicklook extends `browse_iris` rather than a new action; Profile viewer must have `x_att` set to the `Wavelength` world cid (default is `Helioprojective Longitude`) and `function='mean'` (default `maximum`), gated to `'slice'` with `hasattr(ProfileViewerState, 'slices')` for the fork.
- Audit (slit-overlay, verified): slit overlay = subset on the SJI dataset built from `SLTPX1IX` (`extra_coords['slit x position']`), not a scatter dataset linked through HPC. Test SJIs are stride-10 decimations with original-resolution aux indices, so divide by the detected factor. The `axis_correlation_matrix` all-ones patch is rejected (breaks `format_coord`).
- Audit (sync-slicing, verified) + critic §2: time link = precomputed int32 nearest-index components + identity `ComponentLink` (no closures, serializable); the sync callback must use the `data[cid, view]` idiom because `translate_pixel` refuses non-pixel dependencies; hook viewers opened later explicitly; the 4D stack needs a link per stack exposure axis plus a reverse link.
- Correction (writer, kept): the slit subset is a data-only `Data.new_subset(...)`, not `DataCollection.new_subset_group(...)`. A group becomes the edit-subset target at once (`edit subset after new_subset_group: ['Slit']`, so the user's next ROI would overwrite the slit), is listed as a global subset in the data tree and as a disabled layer in every raster/profile viewer (`IncompatibleAttribute` on the raster), and with any key join in place it selects the entire raster. The audit's "pick the group" verdict predates these runs.
- Correction (checker, new): NO `JoinLink`. The audit/critic added one "so it shows in the Link Editor". Verified today (`wp4_chk_join.py`, Pitfall 1): with the `JoinLink` every subset that is `IncompatibleAttribute` on the partner falls back to the key join and selects the partner WHOLE (an SJI-viewer rectangle ROI -> `216920/216920` raster px; a spectroheliogram ROI -> `91760/91760` SJI px). Without it, slice translation and frame/exposure-range propagation are identical, such subsets stay `IncompatibleAttribute` (layer disabled, same as today), and the identity `ComponentLink`s are listed and removable in the Link Editor (`wp4_chk_linkeditor.py`). 2 links per scan, 3 per 4D stack.
- Per-scan WCS in the 4D stack stays deferred (see Dropped) with reworded reason: forward gwcs is exact, the inverse model is the actual work; glue-core needs nothing.

## Dependencies / order

- Needs WP1 first: import `link_hpc` from `glue_solar.sources.loaders.iris`; its signature is `link_hpc(data_collection) -> list[LinkSame]`, and callers add the returned links. Use the real helper, not a stand-in. WP1 also supplies the `_GlueWCS` Angstrom and object-API coherence fixes.
- Independent of the moments WP and of every fork/upstream PR.
- Unblocks WP3 (sessions): the links added here are serializable by construction (verified); WP3 must handle the extra broadcast components (size, see Pitfall 9). Unblocks a future ProfileViewer `slices` hook on the fork (out of scope now).
- Order inside WP4: (d) SJI `Time` component -> (c) slit subset -> (e) `link_time` -> (a) whisker -> (f) `sync_slices` -> (b) `quicklook` + `browse_iris` -> tests -> docs.

## Files to touch

- `glue_solar/sources/loaders/iris.py`
  - `_cube_data`: replace the `extra_coords` time block (`:81-84`) by `_cube_times(cube)` that falls back to the gWCS `time` world axis (SJI, AIA cutout). Adds `Time` (datetime64[ns], broadcast) to SJI datasets.
  - new `_slit_x(cube)` (aux slit x per frame, decimation factor detection) and in `_image_cube_data`: add the broadcast `Slit x` component and `data.new_subset(state, label="Slit", color="#00ff00")` when `'slit x position'` is an extra coord.
- `glue_solar/sources/iris.py`
  - new `nearest(query, ref)`, `exposure_times(raster)`, `link_time(data_collection, sji, raster)`.
  - new `whisker(app, data, slit_index=None)`, `sync_slices(app)` (+ `_install_slice_sync`), `quicklook(app, datasets)`.
  - `browse_iris`: replace the single-viewer block (`:45-48`) by `quicklook(app, dialog.datasets)`.
  - new `@menubar_plugin("IRIS: whisker plot…") whisker_plot(session, data_collection)` using `QtWidgets.QInputDialog.getItem` to pick the raster dataset.
  - `__all__` += `link_time`, `quicklook`, `sync_slices`, `whisker`.
- `glue_solar/tests/test_importer.py`: update `main_components` expectations (Pitfall 10).
- new `glue_solar/tests/test_quicklook.py` (tests listed below).
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`, `changelog/<PR>.feature.rst`, `IRIS_GLUE_GAP_PLAN.md`, `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` (see Docs).

## Step-by-step

1. Loader, `Time` for SJI (`loaders/iris.py`). Add
   ```python
   def _cube_times(cube):
       """datetime64 acquisition time per leading-axis index, or None."""
       if cube.extra_coords and "time" in cube.extra_coords.keys():        # rasters
           times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0]
       elif "time" in cube.wcs.world_axis_physical_types:                  # SJI / AIA cutout gWCS
           times = cube.axis_world_coords("time")[0]
       else:
           return None
       return times.utc.to_value("datetime64")
   ```
   and in `_cube_data` replace lines 81-84 by `times = _cube_times(cube)` / `if times is not None: data.add_component(np.broadcast_to(times.reshape((len(times),) + (1,) * (cube.data.ndim - 1)), cube.shape), "Time")`. The stack path (`_raster_collection_data:101`) still adds its own 4D `Time`; the stacked cube has no `time` world axis and no extra coords, so `_cube_times` returns `None` there (verified: `cube_times(stack) -> None`), no duplicate.
2. Loader, slit (`loaders/iris.py`). Add `_slit_x(cube)` exactly as `slit_x` in the verified module below, then at the end of `_image_cube_data`:
   ```python
   data = _cube_data(cube, f"{desc}-{_observation_label(cube.meta)}", cmap=cmap)
   if cube.extra_coords and "slit x position" in cube.extra_coords.keys():
       data.add_component(np.broadcast_to(_slit_x(cube).reshape(-1, 1, 1), cube.shape), "Slit x")
       px = data.pixel_component_ids[2]
       data.new_subset((px > data.id["Slit x"] - 0.5) & (px <= data.id["Slit x"] + 0.5), label="Slit", color="#00ff00")  # ponytail: any colour but SUBSET_COLORS[0] (#E31A1C), which the user's first ROI gets
   return data
   ```
   Data-only subset (no group): it renders as an `ImageSubsetLayerArtist` per slice in every viewer that opens the SJI (the viewer's `add_data` adds `data.subsets`), is not evaluated on other datasets and does not hijack the edit subset. It is not listed in the data tree (only in each viewer's layer list; `Data.new_subset`'s own docstring warns "Manually-instantiated subsets will not be represented properly by the UI", `glue/core/data.py:199-201`); acceptable, the slit is an overlay, not a selection. `Data.new_subset(subset=<SubsetState>, label=..., color=...)` is the signature (`data.py:183-211`).
3. `link_time` (`sources/iris.py`). Copy `nearest`, `exposure_times`, `link_time` from the verified module. Semantics: for every raster exposure axis (one for a scan, `scan` and `step` for a stack) the SJI gets an int32 component `Nearest <name>: <raster.label>` holding the nearest exposure index per frame, linked by an identity `ComponentLink` to that raster pixel cid; the raster gets `Nearest frame: <sji.label>` linked by an identity `ComponentLink` to the SJI frame pixel cid. 2 links for a scan, 3 for a stack. No `JoinLink` (Pitfall 1). The Link Editor lists them as `Nearest exposure: … -> Pixel Axis 0 [z]` and `Nearest frame: … -> Pixel Axis 0 [z]` rows next to WP1's `LinkSame` rows, and removing a row there removes the link (verified). Labels include the partner label so several SJI bands or windows do not collide.
4. `whisker` (`sources/iris.py`). Copy from the verified module. `x_att = pix[-1]` (wavelength), `y_att = pix[-3]` (step; time for sit-and-stare), optional `slit_index` written into `slices[ndim - 2]`. Works for 3D scans and the 4D stack (extra `Scan` slider). Menubar action (flow verified offscreen with the dialog auto-accepted, `wp4_chk_extra.py` (d)):
   ```python
   @menubar_plugin("IRIS: whisker plot…")
   def whisker_plot(session, data_collection):
       app = session.application
       rasters = [d for d in data_collection if d.ndim >= 3 and "em.wl" in getattr(d.coords, "world_axis_physical_types", ())]
       if not rasters:
           return
       label, ok = QtWidgets.QInputDialog.getItem(app, "Whisker plot", "Raster window", [d.label for d in rasters], 0, False)
       if ok:
           whisker(app, rasters[[d.label for d in rasters].index(label)])
   ```
   The slit slider starts at 0; the user drags it (no slit dialog, audit P1.2). A whisker opened after `sync_slices` is hooked automatically (wrapped `new_data_viewer`).
5. `sync_slices` (`sources/iris.py`). Copy `sync_slices` + `_install_slice_sync` from the verified module. Design: one registry per `GlueApplication` (stored as `app._iris_hook_viewer`), a `slices` callback on every `ImageViewerState`, one shared re-entrancy guard, translation of the source slice point into every other viewer's leading (exposure) axes via `ref[cid, point]`, clipping to the axis length, skipping axes that are displayed in the target. A viewer whose leading axes are displayed (whisker, raster map) never drives. Viewers opened later are covered by wrapping `app.new_data_viewer` on the instance: `command.NewDataViewer.do` (`glue/core/command.py:235`) calls `session.application.new_data_viewer(...)`, and the "New viewer" menu/toolbar (`glue_qt/app/application.py:992-1011 choose_new_data_viewer -> self.do(cmd)`) and MDI drag-drop (`glue_qt/app/mdi_area.py:54 -> choose_new_data_viewer`) all go through it. Calling `sync_slices(app)` again only hooks new viewers (idempotent, verified). Closed viewers stay in the registry; writing `slices` to a dead state is harmless (verified, Pitfall 14).
6. `quicklook` (`sources/iris.py`). Copy from the verified module (it already contains the OBSID guard and the `coords is None` guard). Opens: SJI viewer (first dataset with a `time` world axis), raster map viewer (`x=pix[-3]` step, `y=pix[-2]` slit, wavelength slider at the window centre; the world axes are `Helioprojective Longitude/Latitude`), Profile viewer (`x_att = raster.world_component_ids[-1]` = `Wavelength`, `function = 'slice' if hasattr(ProfileViewerState, 'slices') else 'mean'`), then `sync_slices(app)`. Only the first raster window gets viewers; all loaded SJI/raster pairs of the same observation get links. OBSID compare uses `str(meta.get("OBSID")).split("_")[-1]` because AIA cutouts spell OBSID as `<date>_<time>_<obsid>` (see `_observation_label`, `loaders/iris.py:88-90`, and `tests/test_importer.py:127`); SJI and raster metas hold the plain string (`'3620258102' == '3620258102'`, verified).
7. `browse_iris`: replace lines 45-48 by `quicklook(app, dialog.datasets)`. Keep `dialog.first_image` (tests use it).
8. Tests, docs, changelog as below. Run `pytest glue_solar -q -o addopts="" -p no:cacheprovider` (27 existing + new) and `ruff`.

## Verified code

Reference implementation: `IRIS_PLAN_PROTOTYPES/wp4_common.py`. The 2026-09-02 runs below used an incompatible stand-in; the 2026-09-05 correction imports WP1's real helper and was verified by `review_20260905/test_plan_integration.py`. Put both `IRIS_PLAN_PROTOTYPES/wp1` and `IRIS_PLAN_PROTOTYPES` on `PYTHONPATH` when running the archived version. The writer's original `wp4_common.py.writer` was not retained. Historical run output remains below; it is not evidence for the corrected integration.

```python
import numpy as np
from glue.core.component_link import ComponentLink
from glue.core.exceptions import IncompatibleAttribute
from glue.viewers.image.state import ImageViewerState
from glue_solar.sources.loaders.iris import link_hpc


# ---- loader additions (loaders/iris.py)
def cube_times(cube):
    """datetime64 acquisition time per leading-axis index, or None (rasters: extra coord; SJI: gWCS time axis)."""
    if cube.extra_coords and "time" in cube.extra_coords.keys():
        times = cube.axis_world_coords("time", wcs=cube.extra_coords)[0]
    elif "time" in cube.wcs.world_axis_physical_types:
        times = cube.axis_world_coords("time")[0]
    else:
        return None
    return times.utc.to_value("datetime64")


def add_time(data, cube):
    times = cube_times(cube)
    if times is not None:
        data.add_component(np.broadcast_to(times.reshape((len(times),) + (1,) * (cube.data.ndim - 1)), cube.shape), "Time")


def slit_x(cube):
    """Slit x position in SJI image pixels per frame from the aux SLTPX1IX column (irispy extra coord)."""
    n = cube.data.shape[0]
    x = np.asarray(cube.extra_coords["slit x position"].wcs.pixel_to_world_values(np.arange(n)), dtype=float)
    # ponytail: irispy's bundled test SJIs are stride-10 decimations whose aux table keeps original-resolution
    # indices; real level 2 files never put the slit outside the image, so a factor > 1 only ever triggers there.
    factor = 1
    while np.nanmax(x) / factor > cube.data.shape[-1]:
        factor *= 10
    return x / factor


def add_slit(data, cube):
    if cube.extra_coords and "slit x position" in cube.extra_coords.keys():
        data.add_component(np.broadcast_to(slit_x(cube).reshape(-1, 1, 1), cube.shape), "Slit x")


def slit_subset_state(data):
    px = data.pixel_component_ids[2]
    return (px > data.id["Slit x"] - 0.5) & (px <= data.id["Slit x"] + 0.5)


# ---- time link (next to link_hpc)
def nearest(query, ref):
    """Index of the nearest ref time for every query time (both datetime64; ref sorted)."""
    ref = np.asarray(ref, dtype="datetime64[ns]").astype("int64")
    q = np.asarray(query, dtype="datetime64[ns]").astype("int64")
    if len(ref) < 2:
        return np.zeros(len(q), dtype=np.int32)
    i = np.clip(np.searchsorted(ref, q), 1, len(ref) - 1)
    return np.where(np.abs(q - ref[i - 1]) <= np.abs(ref[i] - q), i - 1, i).astype(np.int32)


def exposure_times(raster):
    """datetime64 per exposure: shape (nstep,) for one scan, (nscan, nstep) for a stack."""
    return raster["Time"][(slice(None),) * (raster.ndim - 2) + (0, 0)]


def link_time(data_collection, sji, raster):
    """Nearest-exposure links SJI <-> raster (or 4D stack): precomputed int32 index components + identity ComponentLinks (serializable).
    No JoinLink: a key join would make every subset that is IncompatibleAttribute on the partner select the partner whole."""
    t_sji = sji["Time"][:, 0, 0]
    t_ras = exposure_times(raster)
    near = np.unravel_index(nearest(t_sji, t_ras.ravel()), t_ras.shape)      # per SJI frame: (step,) or (scan, step)
    back = nearest(t_ras.ravel(), t_sji).reshape(t_ras.shape)               # per exposure: SJI frame
    names = ["exposure"] if t_ras.ndim == 1 else ["scan", "step"]
    links = []
    for axis, (name, index) in enumerate(zip(names, near)):
        label = f"Nearest {name}: {raster.label}"
        sji.add_component(np.broadcast_to(index.astype(np.int32).reshape((-1,) + (1,) * (sji.ndim - 1)), sji.shape), label)
        links.append(ComponentLink([sji.id[label]], raster.pixel_component_ids[axis]))
    label = f"Nearest frame: {sji.label}"
    raster.add_component(np.broadcast_to(back.reshape(back.shape + (1, 1)), raster.shape), label)
    links.append(ComponentLink([raster.id[label]], sji.pixel_component_ids[0]))
    data_collection.add_link(links)
    return links


# ---- viewers (sources/iris.py)
def whisker(app, data, slit_index=None):
    """Image Viewer with wavelength along x, raster step (time for sit-and-stare) along y, slider on slit."""
    from glue_qt.viewers.image import ImageViewer

    pix = data.pixel_component_ids  # ponytail: irispy cubes are always (..., step, slit, wavelength)
    viewer = app.new_data_viewer(ImageViewer, data=data)
    viewer.state.x_att, viewer.state.y_att = pix[-1], pix[-3]
    if slit_index is not None:
        slices = list(viewer.state.slices)
        slices[data.ndim - 2] = slit_index
        viewer.state.slices = tuple(slices)
    return viewer


def sync_slices(app):
    """Keep the slice sliders of every Image Viewer (open now or later) on the nearest linked exposure/frame."""
    hook = getattr(app, "_iris_hook_viewer", None)
    if hook is None:
        hook = app._iris_hook_viewer = _install_slice_sync(app)
    for tab in app.viewers:
        for viewer in tab:
            hook(viewer)
    return hook


def _install_slice_sync(app):
    hooked, busy = {}, []

    def push(src):
        ref = src.reference_data
        if busy or ref is None:
            return
        lead = ref.ndim - 2
        if src.x_att.axis < lead or src.y_att.axis < lead:
            return  # ponytail: leading axes are exposure axes in IRIS cubes; a whisker viewer (step on y) does not drive
        point = tuple(np.array([int(s)]) for s in src.slices)
        busy.append(True)
        try:
            for dst in list(hooked):
                other = dst.reference_data
                if dst is src or other is None:
                    continue
                new = list(dst.slices)
                for axis in range(other.ndim - 2):
                    cid = other.pixel_component_ids[axis]
                    if cid in (dst.x_att, dst.y_att):
                        continue
                    try:
                        index = src.slices[axis] if other is ref else int(np.round(ref[cid, point][0]))
                    except (IncompatibleAttribute, ValueError):  # not linked along this axis / NaN
                        continue
                    new[axis] = int(np.clip(index, 0, other.shape[axis] - 1))
                dst.slices = tuple(new)
        finally:
            busy.pop()

    def hook(viewer):
        state = getattr(viewer, "state", None)
        if isinstance(state, ImageViewerState) and state not in hooked:
            hooked[state] = state.add_callback("slices", lambda *_: push(state))
        return hooked

    original = app.new_data_viewer

    def new_data_viewer(*args, **kwargs):
        viewer = original(*args, **kwargs)
        hook(viewer)
        return viewer

    app.new_data_viewer = new_data_viewer
    return hook


def quicklook(app, datasets):
    """SJI viewer + raster map viewer + mean-spectrum Profile viewer, linked in space and time, sliders synced."""
    from glue.viewers.profile.state import ProfileViewerState
    from glue_qt.viewers.image import ImageViewer
    from glue_qt.viewers.profile import ProfileViewer

    dc = app.data_collection
    dc.add_link(link_hpc(dc))
    types = {d: getattr(d.coords, "world_axis_physical_types", ()) for d in datasets}  # coords may be None
    sjis = [d for d in datasets if "time" in types[d]]
    rasters = [d for d in datasets if "em.wl" in types[d]]
    obs = lambda d: str(d.meta.get("OBSID")).split("_")[-1]  # AIA cutouts spell OBSID as <date>_<time>_<obsid>
    for sji in sjis:
        for raster in rasters:
            if obs(sji) == obs(raster):  # nearest indices across observations are meaningless
                link_time(dc, sji, raster)
    viewers = []
    if sjis:
        viewers.append(app.new_data_viewer(ImageViewer, data=sjis[0]))
    if rasters:
        raster = rasters[0]
        pix = raster.pixel_component_ids
        image = app.new_data_viewer(ImageViewer, data=raster)
        image.state.x_att, image.state.y_att = pix[-3], pix[-2]  # step (or time) x slit: a map with world lon/lat axes
        slices = list(image.state.slices)
        slices[-1] = raster.shape[-1] // 2
        image.state.slices = tuple(slices)
        profile = app.new_data_viewer(ProfileViewer, data=raster)
        profile.state.x_att = raster.world_component_ids[-1]  # 'Wavelength'
        profile.state.function = "slice" if hasattr(ProfileViewerState, "slices") else "mean"
        viewers += [image, profile]
    sync_slices(app)
    return viewers
```

Historical stand-in behavior: a dataset with `coords=None` raised `AttributeError`. The corrected code imports WP1's helper, which ignores datasets without `_GlueWCS`; no duplicate helper or additional quicklook guard is needed.

### (a) Whisker preset

Script `wp4_a_whisker.py` (sns Si IV 1403 raster, 3-scan 20140329 Mg II k stack; slider labels read from `options_widget().slice_helper.layout`).

```
$ python wp4_a_whisker.py
glue 1.27.0 | raster (187, 40, 29) | stack (3, 8, 109, 63)
default 3D view: x Pixel Axis 2 [x] y Pixel Axis 1 [y] slices (0, 0, 0) sliders [('Helioprojective Longitude', 0)] (== spectroheliogram)
whisker 3D: x Pixel Axis 2 [x] y Pixel Axis 0 [z] slices (0, 20, 0) | x_att_world Wavelength | y_att_world Helioprojective Longitude | sliders [('Helioprojective Latitude', 20)]
whisker 4D: x Pixel Axis 3 y Pixel Axis 1 slices (0, 0, 50, 0) | x_att_world Wavelength | y_att_world Helioprojective Longitude | sliders [('Scan', 0), ('Helioprojective Latitude', 50)]
image shapes drawn: (187, 29) (8, 63) | OK
```

State attributes on glue 1.27: `viewer.state.x_att`, `viewer.state.y_att` take `data.pixel_component_ids[i]`; `viewer.state.slices` is a full-length tuple; `x_att_world`/`y_att_world` are derived read-outs; `reference_data` is set by `new_data_viewer(..., data=...)`. Picking cids: irispy cubes are `(step|time, slit, wavelength)` and stacks `(scan, step, slit, wavelength)`, so `pix[-1]` is always wavelength and `pix[-3]` the step/time axis; the slit slider is axis `ndim - 2`. For the sns sit-and-stare the y world label is `Helioprojective Longitude` because the loader stores time as a component, not a coordinate (audit P1.2 nuance); the pixel axis is nevertheless time.

### (b) Quicklook layout

Script `wp4_b_quicklook.py` (sns SJI_1400 + sns raster windows Si IV 1403 and C II 1336; `add_time` applied to the SJI as the loader will).

```
$ python wp4_b_quicklook.py
ProfileViewerState has slices (fork profile-wcs): False
ProfileViewer default x_att: Helioprojective Longitude | function: maximum
viewers: ['ImageViewer', 'ImageViewer', 'ProfileViewer'] | external links: 10
SJI viewer: x Longitude y Latitude slices (0, 0, 0)
map viewer: x Helioprojective Longitude y Helioprojective Latitude slices (0, 0, 14)
profile: x_att Wavelength | x_att_pixel Pixel Axis 2 [x] | function mean | x unit m
profile x range 1.3986284038699979e-07 1.3993407238699309e-07 (metres today; Angstrom after WP1 D3) | n 29 | layers enabled [True]
SJI components: ['Time (Utc)', 'Latitude', 'Longitude', 'SJI_1400-...', 'SJI_1400-... mask', 'Time', 'Nearest exposure: Si_IV_1403-...-scan-0', 'Nearest exposure: C_II_1336-...-scan-0']
raster components: ['Helioprojective Longitude', 'Helioprojective Latitude', 'Wavelength', 'Si_IV_1403-...-scan-0', 'Si_IV_1403-...-scan-0 mask', 'Time', 'Nearest frame: SJI_1400-...']
OK
```

10 external links = 3 pairs x 2 `LinkSame` (WP1) + 2 SJI/raster pairs x 2 time links (OBSID guard passed: all three datasets are OBSID `3620258102`). Edge cases (`wp4_g_slit_loader.py`): `quicklook(app, [sji])` -> `['ImageViewer']`; `quicklook(app, rasters)` -> `['ImageViewer', 'ProfileViewer']`; empty link lists are accepted by `dc.add_link([])`.

### (c) Slit subset on the SJI

Script `wp4_c_slit.py` (sns SJI_1400: sit-and-stare; 20230408 SJI_1400: 64-step raster with 2 frames).

```
$ python wp4_c_slit.py
3620258102_SJI_1400 NAXIS1 37 extra_coords keys ['exposure time', 'obs_vrix', 'ophaseix', 'pztx'] ...
   slit x per frame: [18.7 18.7 ... 18.7]           (62 frames, SLTPX1IX = 187 / factor 10)
3880012095_SJI_1400 NAXIS1 178 extra_coords keys ['exposure time', 'obs_vrix', 'ophaseix', 'pztx'] ...
   slit x per frame: [ 54.9  126.87]                (SLTPX1IX 548.99, 1268.71 / factor 10)
group subset: frame-0 flagged columns [19] | true px per frame [40]
   rendered at slice 0: shape (40, 37, 4) flagged column [19]
   rendered at slice 30: shape (40, 37, 4) flagged column [19]
   rendered at slice 61: shape (40, 37, 4) flagged column [19]
edit subset after new_subset_group: ['Slit']
group evaluated on the raster (no links): IncompatibleAttribute
group evaluated on the raster WITH link_hpc + link_time (identity links, no JoinLink): IncompatibleAttribute (raster layer disabled)
   ...and with a JoinLink added on top (rejected design): 216920 of 216920 px selected
data-only subset: layers in a viewer opened afterwards: [('ImageLayerArtist', 'SJI_1400-3620258'), ('ImageSubsetLayerArtist', 'Slit'), ('ImageSubsetLayerArtist', 'Slit (data-only)')] | dc.subset_groups 1 | raster subsets ['Slit']
2023 SJI: flagged column per frame [[55], [127]] (slit sweeps across the SJI: overlay must be per frame)
OK
```

Loader placement check (`wp4_g_slit_loader.py`: subset created before the Data joins a DataCollection, viewer opened afterwards):

```
subset before dc: Slit | sji.subsets ['Slit']
viewer layers: [('ImageLayerArtist', True), ('ImageSubsetLayerArtist', True)] | flagged column at slice 30: [19] | subset_groups 0 | edit subset []
```

Colour kwarg and duplicate-Time check (`wp4_chk_final.py`):

```
subset colour kwarg: Slit #00ff00 | default would be #E31A1C
stack physical types: ('em.wl', 'custom:pos.helioprojective.lat', 'custom:pos.helioprojective.lon', None) | extra_coords empty: True | cube_times(stack) -> None
```

Decimation factor detection: real level 2 files always have `1 <= SLTPX1IX <= NAXIS1` (the slit is inside the SJI FOV by construction). The irispy test files keep the original-resolution aux values after a stride-10 decimation (local checkout `/Users/nabil/Git/irispy/irispy/data/test/compress.py:28 STRIDE = 10`, `_decimate_wcs` at `:35-41` rescales `CDELT`/`CRPIX` only; the installed 0.8.1 copy does the same with a `factor` variable at `:59-71`) and carry no keyword recording the stride (checked: no `STRIDE`/`DECIM` key, HISTORY ends with `level2 Version L12-2019-08-08`). So the factor is inferred from `max(SLTPX1IX) > NAXIS1` (187 vs 37 -> 10; 1268.7 vs 178 -> 10; real files -> 1). Values are treated as 0-based pixel indices, as irispy's `examples/coalign/03_offset_sji_sg.py` does when feeding them to `pixel_to_world`; agreement with the raster `-TAB` projection is ~1 px either way (slit-overlay verifier on the repaired irispy-main files: `-TAB` 19.52-19.70 vs 18.7). The half-pixel window `(px > x - 0.5) & (px <= x + 0.5)` flags exactly one column per frame.

Why not a linked scatter dataset (re-run of `slit_check.py` today):

```
A pixel-linked scatter: enabled = True | n points drawn = 2480 | x range (20.17, 21.95)
   after slices=(30,0,0): points drawn = 2480 (scatter is NOT sliced by the slider)
B world-linked (lon/lat only): enabled = False | disabled reason: Cannot visualize this layer: This layer depends on attributes that cannot be derived ...
B world-linked (+time):        enabled = True | n points 2480 | x range (21.05, 275.06)
B derived SJI pixel-x vs A direct: frames 0/30/61: [(21.05, 21.05), (20.62, 144.96), (21.24, 275.06)]
```

A scatter layer ignores the image slider (all frames drawn at once; fatal for raster observations where the slit sweeps 549 -> 1269 px), and an HPC-linked scatter is either disabled (lon/lat need SJI time) or mispositioned by glue-core `coordinate_helpers.py:104` freezing time at frame 0.

### (d) SJI `Time` component

Script `wp4_d_time.py`.

```
$ python wp4_d_time.py
SJI extra_coords has 'time': False | wcs physical types: ('custom:pos.helioprojective.lon', 'custom:pos.helioprojective.lat', 'time')
axis_world_coords('time') -> Time (62,) | datetime64: ['2021-09-05T00:18:47.390024796' '2021-09-05T00:23:25.140038624'] datetime64[ns]
main_components before: 2
main_components after: 3 | Time shape (62, 40, 37) datetime64[ns] | Time[:, 0, 0] == Time[:, -1, -1]: True
reference epoch: 2021-09-05T00:18:47.390024796 | max |Time - (epoch + Time (Utc))| = 9.5e-10 s
raster Time still from extra coords: ['2021-09-05T00:18:37.809578953' '2021-09-05T00:20:11.232932360'] | span SJI 00:18:47 -> 05:07:22 | raster 00:18:37 -> 05:07:31
```

### (e) Time link

Script `wp4_e_timelink.py`. Real sns pair (SJI 62 frames, raster 187 exposures) with `link_time` alone, after `link_hpc`, and before `link_hpc` (the world path never shadows the identity link); `translate_pixel` refusal; frame/exposure-range subset propagation through the identity links; session round trip with meta/coords/cmap stripped (those savers are WP6, unrelated to the links); real 3-scan stack (3, 8, 109, 63) with a synthetic SJI whose 11 frames span the stack.

```
$ python wp4_e_timelink.py
[time only] links 2 | sji[ras step, frame 5] = [15] expect 15 | ras[sji frame, exposure 100] = [33] expect 33
[hpc then time] links 2 | sji[ras step, frame 5] = [15] expect 15 | ras[sji frame, exposure 100] = [33] expect 33
[time then hpc] links 2 | sji[ras step, frame 5] = [15] expect 15 | ras[sji frame, exposure 100] = [33] expect 33
translate_pixel refuses: Exception ('Dependency on non-pixel component', Nearest exposure: Si_IV_1403-...-scan-0)
SJI frames 10..11 -> raster exposures [30 31 32 33 34 35] | expect exposures whose nearest frame is 10 or 11: [30 31 32 33 34 35]
raster exposures 30..35 -> SJI frames [10 11] | expect frames that are nearest to one of them: [10 11]
session round trip: 9655 KB | after reload sji[ras step, frame 5] = [15] | external links 2 | key joins 0
stack (3, 8, 109, 63) | links ['ComponentLink', 'ComponentLink', 'ComponentLink'] | SJI comps ['Nearest scan: Mg_II_k_2796-...-stack', 'Nearest step: Mg_II_k_2796-...-stack']
frame 7 -> (scan, step) (np.int64(2), np.int64(0)) | via links: [2] [0]
stack (scan 2, step 3) -> frame [8] | expect [8]
4D session round trip: 5165 KB | frame 7 -> [2] [0]
```

The verifier's "third, 2-input reverse `ComponentLink([scan, step] -> sji_t)`" applied to closure links. With precomputed components the reverse is the single identity link from the stack's `Nearest frame` component (it is stored per `(scan, step)`, so it already depends on both). Synthetic form re-run today (`cc_timelink.py`, which still adds the critic's `JoinLink`, so its `key joins: 1` line is not what WP4 produces): `translate sji frame 3 -> exposure 5 (expect 5)`, `translate exposure 6 -> frame 4 (expect 4)`, `serialized OK, 6745 bytes`, `after reload translate frame 3 -> 5 | key joins: 1`.

JoinLink versus identity links only (`wp4_chk_join.py`, sns pair with `link_hpc` + `link_time`, then the `JoinLink` removed; `RoiSubsetState` rectangles as the Image Viewer draws them):

```
$ python wp4_chk_join.py
=== JoinLink present: external links 5 | key joins 1
  slice translation: sji[ras step, frame 5] = [15] | ras[sji frame, exposure 100] = [33]
  SJI frames 10..11 -> raster exposures [30 31 32 33 34 35]
  raster exposures 30..35 -> SJI frames [10 11]
  SJI viewer rectangle ROI (x 10-20, y 10-20) -> raster: 216920/216920 px | on SJI itself: 5022/91760 px
  raster MAP ROI (step 40-60, slit 10-20) -> SJI: 2220/91760 px
  raster SPECTROHELIOGRAM ROI (wl 5-10, slit 10-20) -> SJI: 91760/91760 px
  Slit subset state -> raster: 216920/216920 px
=== JoinLink removed: external links 4 | key joins 0
  slice translation: sji[ras step, frame 5] = [15] | ras[sji frame, exposure 100] = [33]
  SJI frames 10..11 -> raster exposures [30 31 32 33 34 35]
  raster exposures 30..35 -> SJI frames [10 11]
  SJI viewer rectangle ROI (x 10-20, y 10-20) -> raster: IncompatibleAttribute (layer disabled) | on SJI itself: 5022/91760 px
  raster MAP ROI (step 40-60, slit 10-20) -> SJI: 2220/91760 px
  raster SPECTROHELIOGRAM ROI (wl 5-10, slit 10-20) -> SJI: IncompatibleAttribute (layer disabled)
  Slit subset state -> raster: IncompatibleAttribute (layer disabled)
  session round trip without JoinLink: 10611 KB | after reload sji[ras step, frame 5] = [15] | external links 2
```

(The last line strips `coords`, which drops WP1's world-cid `LinkSame` pairs from the session; the two time links survive. Real sessions are WP6.)

Link Editor listing without the `JoinLink` (`wp4_chk_linkeditor.py`, `LinkEditorWidget(dc).state` with `data1=sji, data2=raster`):

```
$ python wp4_chk_linkeditor.py
external links: 4 | Link Editor rows for SJI<->raster: 4
   ('LinkSame', ['Latitude', '<->', 'Helioprojective Latitu'])
   ('LinkSame', ['Longitude', '<->', 'Helioprojective Longit'])
   ('ComponentLink', ['Nearest exposure: Si_I', '->', 'Pixel Axis 0 [z]'])
   ('ComponentLink', ['Nearest frame: SJI_140', '->', 'Pixel Axis 0 [z]'])
after removing the last row via the editor: 3 rows; dc.external_links after update: 3
OK
```

### (f) Slice sync

Script `wp4_f_sync.py`: offscreen `GlueApplication`, real sns pair, `link_hpc` + `link_time`, viewers A (SJI) and B (raster default) open before `sync_slices(app)` (called twice), C (whisker) and D (raster map) opened after it, driven through the Qt sliders (`options_widget().slice_helper._sliders[...].state.slice_center`).

```
$ python wp4_f_sync.py
hooked states after calling sync_slices twice: 4 | viewers: 4
A slider -> 5: A (5, 0, 0) B (15, 0, 0) (expect step 15) B slider [('Helioprojective Longitude', 15)] | C (whisker) (0, 20, 0) (slit untouched=20) | D (map) (0, 0, 0) (wl untouched)
B slider -> 100: B (100, 0, 0) A (33, 0, 0) (expect frame 33) A slider [('Time (Utc)', 33)]
C (whisker) slit slider -> 30: C (0, 30, 0) | A (33, 0, 0) B (100, 0, 0) (unchanged: whisker does not drive)
D (map) wl slider -> 7: D (0, 0, 7) | B (100, 0, 0) (B shows wl on x: untouched) A (33, 0, 0)
B slider -> 0: A (0, 0, 0) (expect frame 0) | D (0, 0, 7) (D displays step: untouched) | C (0, 30, 0)
all four drew | layers enabled: [[True], [True], [True], [True]]
echo drift over 62 frames: []
OK
```

Chosen approach for later viewers: wrap `app.new_data_viewer` on the instance (verified: C and D were hooked at creation and a real slider on B moved A while C/D kept their own sliders). Dropped alternatives: rescanning `app.viewers` inside each callback (a new viewer's own slider is dead until some other slider moves), a glue-solar `ImageViewer` subclass (a second viewer class in the registry for 6 lines of hooking), a hub message (none exists).

Extras (`wp4_chk_extra.py`): OBSID guard types, data-only subset created after the data is in the app, closed viewer in the registry, `whisker_plot` through a real `QInputDialog` (auto-accepted by a `QTimer`), `coords=None` guard, test-1 assertion form:

```
$ python wp4_chk_extra.py
(a) OBSID: '3620258102' '3620258102' '3860258481' | sns equal: True | stack type dict
(b) data-only subset after add: created OK | logged errors: []
(c) after closing B: viewers 1 | hooked 2 | drive A after B closed: OK, B state now (15, 0, 0)
(d) whisker_plot via QInputDialog: ImageViewer x Pixel Axis 2 [x] y Pixel Axis 0 [z] ref Si_IV_1403-3 | hooked now 3
(e) coords=None dataset raises: AttributeError 'NoneType' object has no attribute 'world_axis_physical_types'   (stand-in link_hpc; quicklook now guards)
(f) max |dT - dTimeUtc| = 9.531504474580288e-10 s (< 1e-6)
(g) Slit subset colour/label: Slit-after #e31a1c
OK
```

### Per-scan WCS non-goal reword (re-run of `cc_stackwcs.py` today)

```
physical types: ('custom:SCAN', 'pos.eq.ra', 'pos.eq.dec', 'em.wl') corr rows: [[1,0,0,0],[1,1,1,0],[1,1,1,0],[0,0,0,1]]
scan 0: gwcs lon/lat 489.966/279.546 vs per-scan -TAB 489.966/279.546  dlon=0.00e+00
scan 1: gwcs lon/lat 490.137/279.579 vs per-scan -TAB 490.137/279.579  dlon=0.00e+00
scan 2: gwcs lon/lat 490.308/279.581 vs per-scan -TAB 490.308/279.581  dlon=0.00e+00
numerical_inverse failed: ValueError too many values to unpack (expected 2)
world_to_pixel_values failed: ValueError too many values to unpack (expected 2)
```

## Tests to add

File `glue_solar/tests/test_quicklook.py`; fixtures: `irispy_test_files` (real, from the installed irispy 0.8.1; `glue_solar/conftest.py:94-101`; pick files with the existing `_real(files, name)` helper from `test_importer.py:28`, both the `sns/` and `raster/` copies of the sns raster load with `spectral_windows=["Si IV 1403"]`) and small synthetic `Data` objects; Qt tests build `GlueApplication()` offscreen (conftest sets `QT_QPA_PLATFORM`) and call `app.close()`.

1. `test_sji_gets_datetime_time_component` (real `sns/..._SJI_1400_t000.fits`): `data["Time"].shape == (62, 40, 37)`, dtype `datetime64[ns]`, `data["Time"][:, 0, 0]` equals `data["Time"][:, -1, -1]`, and `(Time[:,0,0] - Time[0,0,0]) / np.timedelta64(1, "s")` matches `Time (Utc)[:,0,0] - Time (Utc)[0,0,0]` (world cid 0) to `1e-6` s (measured 9.5e-10).
2. `test_slit_subset_flags_one_column_per_frame` (real sns SJI_1400 and `raster/..._3880012095_SJI_1400_t000.fits`): `np.unique(data["Slit x"]) == [18.7]`; `data.subsets[0].label == "Slit"`; mask columns per frame `[19]` with 40 px each (sns); `[[55], [127]]` for the 2023 file; `DataCollection([data]).subset_groups == []`.
3. `test_link_time_translates_both_ways` (real sns SJI_1400 + raster `Si IV 1403`): `len(links) == 2`, all `ComponentLink`; `sji[ras.pixel_component_ids[0], (np.array([5]), np.array([0]), np.array([0]))] == [15]`; `ras[sji.pixel_component_ids[0], (np.array([100]), ...)] == [33]`; subset `frames 10..11` (`(sp0 >= 10) & (sp0 <= 11)`) -> `ras.get_mask(...)` true on exposures `[30..35]` only; subset `exposures 30..35` -> SJI frames `[10, 11]` only; a `RoiSubsetState(xatt=sp[2], yatt=sp[1], roi=RectangularROI(10, 20, 10, 20))` raises `IncompatibleAttribute` on the raster (no whole-raster fallback); result independent of calling `link_hpc` before or after.
4. `test_link_time_is_serializable` (synthetic: `Data(x=zeros((5,3,3)))` with a `Time` component, `Data(y=zeros((7,3)))` with `Time`): `GlueSerializer(dc).dumps()` succeeds; after `GlueUnSerializer.loads(...)` the translation still holds and `len(dc2.external_links) == 2`.
5. `test_link_time_stack` (real 20140329 3-scan `Mg II k 2796` stack + synthetic SJI `Data` with 11 `Time` values spanning the stack): `len(links) == 3`; SJI components `Nearest scan: ...` and `Nearest step: ...` exist; frame 7 -> `(2, 0)` via `sji[stack.pixel_component_ids[0|1], point]`; `(scan 2, step 3)` -> frame 8.
6. `test_whisker_preset` (real sns raster and the 3-scan stack, `GlueApplication`): `x_att is pix[-1]`, `y_att is pix[-3]`, `slices[ndim - 2] == 20`, `x_att_world.label == "Wavelength"`; the default viewer has `(x_att, y_att) == (pix[2], pix[1])`; both draw (`viewer.figure.canvas.draw()`).
7. `test_quicklook_opens_trio_and_syncs` (real sns pair, `GlueApplication`): `quicklook` returns `[ImageViewer, ImageViewer, ProfileViewer]`; profile `x_att.label == "Wavelength"`, `function in ("mean", "slice")`; `len(dc.external_links) == 4`; a raster viewer opened AFTER quicklook via `app.new_data_viewer(ImageViewer, data=raster)` (default layout, slider on step) follows: set SJI viewer `state.slices = (5, 0, 0)` -> its `slices[0] == 15`; set its `slices = (100, 0, 0)` -> SJI `slices == (33, 0, 0)`; the quicklook map viewer keeps `slices[-1] == 14` throughout; a whisker viewer keeps `slices[1]` when the SJI moves; calling `sync_slices(app)` again leaves the hooked count unchanged; sweeping SJI frames 0..61 never changes the frame just set (no echo drift). Assert on `state.slices`, not on the private `_sliders`.
8. `test_whisker_plot_action` (real sns raster, `GlueApplication`, `monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", lambda *a, **k: (raster.label, True))`): `whisker_plot(app.session, dc)` opens one `ImageViewer` with `x_att is pix[-1]`; with only an SJI in the collection it opens nothing.
9. Update `test_importer.py`: `test_real_sji_adapter_preserves_mask_units_and_coordinates` (`:107`) unpack `science, mask = data.main_components[:2]`; `test_aia_cube_uses_the_same_irispy_adapter` (`:134`) `len(data.main_components) == 4` (the test AIA file is a renamed SJI file, so it gets `Time` and `Slit x`). `:157` (raster, 3) is unchanged.

## Pitfalls (verified)

1. `JoinLink` (audit P3.2-c / critic §2) is REJECTED. `Data.get_mask` (`glue/core/data.py:1436-1440`) falls back to `get_mask_with_key_joins` on `IncompatibleAttribute`, and the join maps "any flagged pixel in frame f" to every raster exposure joined to f. Image Viewer ROIs never restrict the frame axis, so an SJI-drawn rectangle selects the whole raster (`216920/216920 px`), a spectroheliogram ROI selects the whole SJI (`91760/91760 px`) and a `Slit` subset group selects the whole raster (`wp4_chk_join.py`, `wp4_c_slit.py`). The identity `ComponentLink`s alone give the same slice translation and the same frame/exposure-range propagation, keep such subsets `IncompatibleAttribute` (layer disabled, as today), and are visible/removable in the Link Editor.
2. `DataCollection.new_subset_group` for the slit is rejected regardless of links: the new group becomes the edit subset at once (`edit subset after new_subset_group: ['Slit']`), so the user's next ROI would overwrite it, and it appears as a disabled layer in every raster/profile viewer. Use `Data.new_subset` (data-only). Data-only subsets are not listed in the glue-qt data tree (`glue_qt/core/data_collection_model.py:418-421 _on_add_subset` indexes subset groups only); they do appear in each viewer's layer list and render per slice (`ImageSubsetLayerArtist`, `flagged column at slice 30: [19]`). Creating one while the Data is already in a running `GlueApplication` logs no error either (`wp4_chk_extra.py` (b)).
3. `translate_pixel` (`glue/core/fixed_resolution_buffer.py:48`) raises `Exception('Dependency on non-pixel component', ...)` for the identity links; `is_convertible_to_single_pixel_cid` returns `None` for the same reason. Use `ref[cid, point]` (`Data.__getitem__` with a view), as the fork's `ProfileLayerState.slice_view` (profile-wcs `state.py:505`, translation at `:527`) does.
4. `ComponentLink(using=lambda ...)` closures are not serializable (`GlueSerializer` -> `ValueError "Object '__main__.<lambda>' not found"`, sync-slicing verifier); precomputed int32 components + identity links round-trip (9655 KB embedded for the tiny test pair, 6.7 KB synthetic).
5. No viewer-added hub message; `GlueApplication.new_data_viewer` broadcasts nothing (sync-slicing verifier: a viewer created after the action stayed at `(0,0,0)`). Wrapping the instance method covers menu, toolbar and drag-drop because `command.NewDataViewer.do` calls `session.application.new_data_viewer` (`glue/core/command.py:235`). Session restore creates viewers through `add_widget` (`glue_qt/app/application.py:1456 __setgluestate__ -> :1469 add_widget`), so after loading a session the user must re-run the browser action (or WP3 re-installs the sync).
6. With `link_hpc` in place, a generic "translate every non-displayed axis" callback would also translate the raster slit axis from the SJI corner pixel through the `-TAB` inverse (garbage or NaN) and, for two viewers of the same raster, copy a stale wavelength entry. The verified callback translates leading (exposure) axes only and refuses to drive from viewers whose leading axes are displayed (`C (whisker) slit slider -> 30: A/B unchanged`; the quicklook map viewer, `x=step`, never drives and never receives on its displayed step axis).
7. `ProfileViewer` default `x_att` is `Helioprojective Longitude` and `function` is `maximum` (`wp4_b_quicklook.py`); the quicklook must set both. `x_display_unit` stays at the native unit (`m` today, Angstrom after WP1).
8. `cube.axis_world_coords('slit x position', wcs=cube.extra_coords)` raises `ValueError` in ndcube 2.4.1 (physical type `custom:CUSTOM`, slit-overlay verifier); use `cube.extra_coords['slit x position'].wcs.pixel_to_world_values(np.arange(n))` (returns `[187.0, ...]`).
9. Broadcast components are materialised on save: the sns pair session is 9.6 MB embedded although the arrays are zero-stride views. A real SJI (1000 x 1096 x 1096) gets an int32 `Nearest exposure` component per linked raster window (4.8 GB if embedded). WP3 must either skip these on save and re-run `link_time`, or rely on the LoadLog path for loader-made components (`Time`, `Slit x` come back from re-running the loader; `Nearest ...` are post-load and would be embedded per `glue/core/state.py:1093-1101`). Flag this in WP3.
10. Existing tests count `main_components` (2 for SJI and AIA, `test_importer.py:107` and `:134`); `Time` and `Slit x` raise it to 4 for SJI-derived files.
11. irispy 0.8.1 test SJI headers are self-inconsistent (`CDELT1=0.16635` unscaled, `CRPIX1=18.45` rescaled; repaired in irispy main `bc5e39e`), so do not assert agreement between the aux slit and a `-TAB` projection on the installed files. The aux route needs no WCS at all.
12. The all-ones `axis_correlation_matrix` shortcut for time-aware world links breaks glue-qt `ImageViewer.format_coord` (`OverflowError` in astropy WCSAxes, slit-overlay verifier / critic §2). WP4 avoids world-time links entirely: the time link is component-based.
13. `link_time` assumes both time arrays are monotonic (searchsorted); irispy exposures are time ordered. A 1-exposure raster returns index 0 everywhere.
14. Closed viewers stay in the sync registry (`hooked 2` with 1 viewer open); writing `slices` to the dead state is harmless (`wp4_chk_extra.py` (c)). Not worth pruning.
15. AIA cutouts spell `OBSID` as `<date>_<time>_<obsid>` (`test_importer.py:127`); compare `str(...).split("_")[-1]` or the AIA cutout never gets a time link.
16. The new SJI `Time` component is datetime64 like the raster's; glue-core's datetime axis bug (critic §3.5: `glue/utils/matplotlib.py:449` epoch 0001-01-01 vs matplotlib 3.11's 1970-01-01) mislabels dates in any Scatter/Histogram of `Time`. Pre-existing for rasters; not a WP4 concern.

## Acceptance criteria

- [ ] `browse_iris` with an SJI band + a raster window ticked opens exactly three viewers (SJI, raster map with `Helioprojective Longitude/Latitude` axes, Profile with `Wavelength` x-axis and `Mean`), the SJI viewer shows the `Slit` layer moving per frame, `dc.external_links` holds the WP1 `LinkSame` pairs plus 2 time links per same-observation SJI/raster pair, and the Link Editor lists them as `Nearest exposure: … -> Pixel Axis 0 [z]` / `Nearest frame: … -> Pixel Axis 0 [z]` rows.
- [ ] Dragging the SJI slider moves the step slider of any default-layout (spectroheliogram) raster viewer to the nearest exposure and back (sns: frame 5 -> step 15, step 100 -> frame 33); a viewer opened afterwards joins the sync; the quicklook map viewer's wavelength slider and a whisker viewer's slit slider change nothing else.
- [ ] An ROI drawn on the SJI viewer does not select the whole raster (its raster layer is disabled, `IncompatibleAttribute`); an ROI drawn on the raster map appears on the SJI.
- [ ] "Plugins -> IRIS: whisker plot…" opens `x=Wavelength`, `y=step` with a slit slider for the chosen raster (3D and 4D).
- [ ] SJI datasets have a `Time` datetime64 component equal to the gWCS time axis; `Slit x` is in image pixels for real and decimated test files.
- [ ] `test_quicklook.py` (8 tests) green with real irispy test files; `test_importer.py` updated; full suite green offscreen; ruff clean.
- [ ] No lambda/closure links, no `JoinLink`; `GlueSerializer` accepts the links (synthetic test).
- [ ] Docs and changelog updated as below; planning docs reworded.

## Dropped / out of scope

- `JoinLink` on the nearest-frame component: whole-partner fallback for every undrivable subset (Pitfall 1); the identity links already give frame/exposure-range propagation and Link Editor visibility.
- Spectroheliogram preset: it is the default Image Viewer layout for every raster window (verified); documentation only.
- Slit-position dialog for the whisker: the slit slider is there; drag it.
- Menubar "sync sliders" / "link in time" actions for File > Open loads: `browse_iris` covers the workflow; add later on demand (`link_time`/`sync_slices` are public functions).
- Time-aware SJI ROI -> raster propagation (world-time link + `world2pixel_single_axis` wrap): a glue-core monkeypatch (critic §2). Without it an SJI-drawn ROI stays `IncompatibleAttribute` on the raster (layer disabled), exactly as today with lon/lat links only.
- ProfileViewer slice sync (`function='slice'`, `ProfileViewerState.slices`): fork profile-wcs only; gate exists in `quicklook`, hooking its state comes when the fork lands.
- Upstream `join_on_key(nearest=True)` (YAGNI, and key joins are not used at all now).
- Hidden component ids for `Slit x`/`Nearest ...`: visible components cost nothing; revisit if the attribute combos get noisy.
- Pruning closed viewers from the sync registry (Pitfall 14).
- Per-scan absolute WCS inside the 4D stack: keep deferred, reworded. glue-core needs nothing: `gwcs` + `astropy.modeling.tabular.tabular_model(3)` over the stacked `-TAB` tables reproduces every scan's coordinates exactly in the forward direction (`dlon = 0.00e+00`, re-run today); the missing piece is an inverse model (`numerical_inverse`/`world_to_pixel_values` fail with `too many values to unpack`), which links and subsets need. Loading scans separately stays the supported way.
- Sequence/movie export, blink, line lists, OBS metadata: other WPs.

## Docs

- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:31-32`: replace "The data are added to the data collection and the first slit-jaw (or AIA) cube is opened in an Image Viewer; use its slider to step through time." with: "The data are added to the data collection and the quicklook opens: the first slit-jaw (or AIA) cube in an Image Viewer with the spectrograph slit drawn on every frame (the ``Slit`` layer, from the file's own slit-position table), the first raster window as a helioprojective map at the window's central wavelength, and a 1D Profile viewer showing the window's mean spectrum. The datasets are linked by helioprojective coordinates and by time (nearest exposure), so the time sliders of the Image Viewers follow each other, including viewers you open later. Selections drawn on one dataset propagate to the other through the links where the coordinates allow it (see Linking)."
- Same file, after the stacking paragraph (`:39`), add a "Viewer presets" paragraph: "Every raster window opens by default as a spectroheliogram (wavelength along x, slit along y, slider over raster position or time). "Plugins -> IRIS: whisker plot..." opens the whisker layout instead (wavelength along x, raster position or time along y, slider over slit position); pick the window in the dialog and drag the slider to the slit position of interest."
- Same file, Linking section (`:54-59`): replace with: "The browser links slit-jaw and raster datasets of the same observation automatically: ``Longitude``/``Latitude`` (slit-jaw) with ``Helioprojective Longitude``/``Helioprojective Latitude`` (raster), and the slit-jaw frame with the nearest raster exposure (the ``Nearest exposure``/``Nearest frame`` components, listed in the Link Editor). Selections drawn on a raster map (raster position against slit position) appear on the slit-jaw viewer; a range of slit-jaw frames selects the matching raster exposures and vice versa. Selections drawn on the slit-jaw image or on a spectroheliogram cannot be evaluated on the other dataset (the layer is shown as disabled) because the slit-jaw pixel coordinates depend on time and the raster has no wavelength axis in the slit-jaw. Datasets opened through "File -> Open Data Set" are not linked; use the browser, or pair the components in the Link Editor." (Adjust to WP1's exact wording for the HPC part.)
- `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst:41-43`: unchanged (already describes the default spectroheliogram axes); optionally add one sentence pointing to the whisker action.
- `changelog/<PR>.feature.rst`: "The IRIS observation browser now opens a quicklook: the slit-jaw viewer draws the spectrograph slit on every frame, a raster map viewer and a mean-spectrum Profile viewer open alongside it, slit-jaw and raster datasets of the same observation are linked in space and time (nearest exposure), and the Image Viewer time sliders follow each other. Slit-jaw datasets gain a ``Time`` component. A new "IRIS: whisker plot..." action opens a wavelength-versus-raster-position (or time) view at a chosen slit position."
- `IRIS_GLUE_GAP_PLAN.md`: Phase 1.2 (L67-72) -> whisker only, spectroheliogram is the default layout; Phase 1.3 (L73-77) -> "opens the SJI, raster-map and Profile viewers, links in space (1.4) and time, syncs sliders (was Phase 3.2)"; Phase 1.6 (L86-89) -> "per-frame ``Slit`` subset on the SJI dataset from the aux ``SLTPX1IX`` column, not a linked scatter dataset"; Phase 3.2 -> done in glue-solar (delete "largest upstream effort" at L198 and "glue-core state + glue-qt UI" / "time-nearest join primitive" at L148-154); table row L39 "Coordinated raster browser" home -> glue-solar; row L37 "SJI inspection" -> slit overlay covered, blink stays; L42/L43 -> whisker action, spectroheliogram default; non-goal bullet L186-188 "Per-scan absolute WCS" -> reworded as in Dropped.
- `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md:171-182`: rows "SJI inspection" (L171, slit overlay now present), "Coordinated raster browser" (L173), "Whisker plot" (L177), "SJI and raster temporal coordination" (L182) move to the covered column with the remaining gaps (blink/mix, export, GOES panel) listed.


---

# WP5 - Velocity display units, blink tool, line-list layer

**Goal.** Let the glue-qt 1D Profile viewer show IRIS spectra on a `km / s` axis (rest wavelength from the window's `TWAVE` card, per-dataset override), draw a shipped IRIS line list as labelled vertical lines that follow the display unit, and give the Image viewer a timed blink tool. Everything ships from glue-solar through public glue-core/glue-qt registries; no fork branch is involved.

**Current state (2026-09-02).**

- glue-solar `iris-observation-browser` (PR #44): nothing for units, blink or line lists. `glue_solar/__init__.py:12-15` `setup()` only adds sunpy colormaps. `glue_solar/sources/loaders/iris.py:35-69` `_GlueWCS` maps helioprojective axes to arcsec; wavelength stays in `m` today (`world_axis_units` at :45-50). `:76` `data.meta = cube.meta` (an irispy `SGMeta`, a `dict` subclass with a read-only `rest_wavelength` property computed from `TWAVE<n>`; irispy `meta.py:194-198`). Stack branch `:97-103` builds the 4-D cube whose meta is `dict(cube_sequence[0].meta)` (`stack_spectrograms.py:80`), so stacks have NO `rest_wavelength` attribute.
- glue-core 1.27.0 (site-packages, identical to fork main): `glue/core/units.py:9-56` `UnitConverter` instantiates `unit_converter.members[settings.UNIT_CONVERTER]()` on every call and passes `(data, cid)` through to the helper; `:49-56` `SimpleAstropyUnitConverter` registered as `'default'`; `:59-71` `find_unit_choices` (catches `ValueError` only). `glue/config.py:567-583` `UnitConverterRegistry` (plain dict `members`), `:833` instance, `:936-942` `check_unit_converter` validator raising `KeyError` for an unknown name. `glue/viewers/profile/state.py:271-284` x choices via `find_unit_choices`; `:266` and `:292` read `layer_state.attribute` for every layer; `:307-308` call `layer.reset_cache()` for every layer on reference change; `:129-131` and `:219-221` read `layer.profile` inside `try/except Exception`. `glue/viewers/profile/viewer.py:22-23` sets `x_axislabel = x_att.label` (unit ignored); `:47-58` `apply_roi` converts display to native through `UnitConverter().to_native`. `glue/viewers/common/viewer.py:26-34` `get_layer_artist_from_registry`, consulted at `:212` (`add_data`) and `:259` (`add_subset`); `:397-411` session restore rebuilds layer artists from `_type` + saved layer state. `glue/viewers/common/tool.py:60-79` `CheckableTool` (`activate` :68, `deactivate` :74; `Tool.close` :54-57 sets `self.viewer = None`). `glue/viewers/image/state.py:500` `attribute_display_unit` is for colour levels only; image axes have no display units.
- glue-qt (editable checkout, `macos-integration` = upstream main for these files): `glue_qt/viewers/profile/data_viewer.py:19` `_layer_style_widget_cls = ProfileLayerStyleEditor` (single class), `:22-23` data/subset artist = `QThreadedProfileLayerArtist`; `glue_qt/core/layer_artist_model.py:365-370` dict form does an exact-class lookup (`:364-369` on glue-qt main; the venv imports the `macos-integration` checkout); `glue_qt/viewers/matplotlib/data_viewer.py:59` reads `layer_artist.is_computing` for every layer; `glue_qt/viewers/image/data_viewer.py:42-45` `ImageViewer.tools` is a plain class-level list; `glue_qt/viewers/common/toolbar.py:106-136` builds a `QAction` for a `CheckableTool` and only calls `setMenu` for `DropdownTool`, `:178-192` builds a menu from `menu_actions()` that is then dropped for non-dropdown tools; `glue_qt/viewers/common/data_viewer.py:161-182` creates `self.toolbar` (:165) before instantiating tools (:171-180). `glue_qt/viewers/profile/tests/test_data_viewer.py:340-352` already tests a custom `@unit_converter` with `u.spectral()`, so the profile path is upstream-supported.
- Mix already exists: per-layer alpha (`glue_qt/viewers/image/layer_style_editor.py:18`, composited in `glue/viewers/image/composite_array.py:170-190`) and `color_mode = 'One color per layer'` (`glue/viewers/image/state.py:91-94,129`). Verified today: composite alphas `[0.8, 0.5, 0.8]`, choices `['Colormaps', 'One color per layer']`.
- Fork branches (`glue` ape14-wcs-autolink, profile-wcs; `glue-qt` profile-wcs): no unit, blink or line-list work (audit checks). profile-wcs keeps `x_display_unit` as the owner of axis units and drops WCSAxes formatting whenever the display unit differs from the native unit (`state.py` `_wcsaxes_with_unit`, `PROFILE_WCS_RESTART_TODO.md:44-52`), so `km / s` is compatible.
- irispy 0.8.1 (installed) `SGMeta.rest_wavelength` is `(float(self.get(f"TWAVE{self._iwin}")) * u.AA).to(u.nm)` with no guard: a window without `TWAVE` raises `TypeError` (verified below). The checkout (newer) returns `None`.
- irispy ships no line list (`grep` for the wavelengths in irispy and sunpy: 0 hits; `obsid.py` 'linelist' is the OBS line-list number).
- irispy 0.8.1 test data (checker, 2026-09-02): `get_test_data_filenames()` returns TWO files named `iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits`, `irispy/data/test/sns/` (5322240 bytes, last HDU 187 rows x 9 columns) and `irispy/data/test/raster/` (5817600 bytes, last HDU 1872 rows x 7 columns). Same headers (NWIN 8, same TDESC/TWAVE). Any NUV window (`Mg II k 2796`, `2832`, `2814`) from the `raster/` copy raises `ValueError: Expected 187 NUV source filename rows, found 1872` (`irispy/io/spectrograph.py:33-36`, called at :221); FUV windows (`C II 1336`) load from both. `next(p for p in files if p.name == ...)` (the `_real` helper in `glue_solar/tests/test_importer.py:28-29`) picks whichever `os.walk` lists first. WP5 tests must select by `p.parent.name == "sns"` for that file, or use the 2014 rasters for Mg II k (their TWAVE is the same 2796.19995117).
- No prototype code exists in any repo; the scratch prototypes (this brief) are the only implementation.

**Decisions already made.**

- D2: all three items ship from glue-solar via `unit_converter`, `viewer_tool` + `ImageViewer.tools`, `layer_artist_maker`, `menubar_plugin`, `glue_qt.config.layer_action`. Upstream PRs are limited to the two tiny changes glue-solar monkeypatches around (glue-qt `_layer_style_widget_cls` dict, optional glue-core `x_axislabel [unit]`).
- D3: WP1 changes `_GlueWCS` so the wavelength axis is native `Angstrom`. This brief assumes that (choices become `['Angstrom', 'nm', 'km / s']`) but every snippet was also run with today's native `m` and works unchanged; the line list stores Angstrom and converts through the reference dataset's native unit.
- D4 pattern (layer_action, no viewer opened) is reused for the optional "Set rest wavelength…" override.
- Install the converter by overriding `unit_converter.members['default']`. Never register a new name and point `settings.UNIT_CONVERTER` at it (persisted settings break `import glue`; reproduced below).
- Velocity convention: `u.doppler_optical` (linear Δλ/λ·c). This is exactly what `irispy.utils.moments.calculate_moments` uses (`moments.py:187-194`, `(centroid - rest)/rest * c`), so WP2 moments and WP5 agree.
- Rest wavelength source order: `data.meta['rest_wavelength']` (float, Angstrom; written by the loader for stacks or by the user override) then irispy `SGMeta.rest_wavelength` (TWAVE) then `None` (no `km / s` offered).
- Stack rest wavelength comes from `sequence[0].meta` (an `SGMeta`, `rest_wavelength(sequence[0])` = 2796.1999511699996 Angstrom verified today), NOT from `stack.meta.get('TWAVE1')` as the verifier suggested: the stack's `dict(scan0.meta)` keeps `TWAVE1..TWAVE9` for every window of the file and loses `_iwin`; for the 2014 Mg II k stack the right card is `TWAVE9` (`TWAVE1` is C II 1336, verified today).
- Choices pruned to `Angstrom`, `nm`, `km / s` for wavelength axes and `arcsec`, `arcmin`, `deg` for angle axes (astropy's default list is 131 prefixed units).
- Blink = ~35-line `CheckableTool` with a `QTimer`, cycling the layers that are enabled, visible and data (not subsets) at activation; the interval is a `QSpinBox` added to the viewer toolbar (menu_actions is dead for checkable tools, see pitfalls). Mix is treated as done.
- Line list = `LineListState(ProfileLayerState)` + `LineListArtist(MatplotlibLayerArtist)` registered with `layer_artist_maker`; positions go through `UnitConverter` so they follow `x_display_unit`; the style-widget dict is keyed on `QThreadedProfileLayerArtist` (plus `LineListArtist`). The IRIS line list ships as `glue_solar/iris_lines.csv` (11 lines) added through a menubar action.
- Session behaviour of the line-list layer: NO saver and NO drop-on-save. Verified today that the stock `LayerArtist.__gluestate__` + `ProfileLayerState` round trip restores the layer, its colour, `km / s` and positions with zero extra code. What blocks sessions containing IRIS data is WP3 (SGMeta `Quantity` values, `_GlueWCS`, `preferred_cmap`), not this layer.

**Dependencies / order.**

- WP1 (D3 Angstrom in `_GlueWCS`) first, so docs and tests describe `['Angstrom', 'nm', 'km / s']`. Not a hard blocker: all snippets ran with native `m`.
- Independent of the link work; blink is only useful once two SJI/AIA layers share a viewer (link_hpc / autolink), and the blink test links its synthetic images with `LinkSame` because an unlinked second layer is disabled at draw time.
- WP3 (sessions, `briefs/wp3-sessions.md`) must keep `meta['rest_wavelength']` (a float; round-trips through glue's meta filter, verified by `wp5_ll_session.py`) and needs no line-list saver. `wp3-sessions.md:40` and `:440` ("P3.4 line lists need their own savers") and `critic.md` line 42 ("not restorable without their own saver") are superseded by today's run: the stock `LayerArtist.__gluestate__` (`glue/viewers/common/layer_artist.py:49`) + `ProfileLayerState` restore the layer, colour, `km / s` and positions. WP3 should drop that "Dropped" item.
- The profile-wcs fork WP (WP0) must place line-list positions in pixel coordinates when `wcsaxes_active` is true (fork `glue/viewers/profile/state.py:190-198` property, `:597-600` profile x values become `x_att_pixel` indices); on released glue-core 1.27 nothing is needed.
- Unblocks: WP2 moments velocity maps share the same convention and rest-wavelength helper; the "Set rest wavelength…" action gives moments its `rest_wavelength` argument for free. `wp2-moments.md:138-140` reads `data.meta.rest_wavelength` directly inside `try/except`; once WP5 lands it should call `rest_wavelength(data)` instead (same behaviour, one place).

**Files to touch.**

- `glue_solar/viewers.py` (new, ~150 lines): `IRISUnitConverter`, `BlinkTool`, `LineListState`, `LineListArtist`, `line_list_artist` maker, `add_iris_line_list` menubar action, `set_rest_wavelength` layer action, `install()`. Importing `glue_qt`/`qtpy` at module level adds no new dependency: `glue_solar/sources/loaders/iris.py:10-13` already does (`from glue_qt.utils import get_qapp, load_ui`, `from qtpy import QtWidgets`) and `pyproject.toml:20` pins `glue-qt[qt]>=0.4.0`.
- `glue_solar/iris_lines.csv` (new, git-tracked so setuptools_scm ships it; `include-package-data = true`, `MANIFEST.in` only excludes).
- `glue_solar/sources/loaders/iris.py`: add `rest_wavelength(data)` helper next to `_GlueWCS` (the converter, the loader and the override all use it) and two lines in the stack branch of `_raster_collection_data` (:100-102) writing `data.meta["rest_wavelength"]`.
- `glue_solar/__init__.py`: import `viewers`, call `viewers.install()` from `setup()`, add `"viewers"` to `__all__`.
- `glue_solar/conftest.py`: autouse fixture setting `settings._save_to_disk = False` and `settings.SHOW_INFO_PROFILE_OPEN = False`.
- `glue_solar/tests/test_viewers.py` (new).
- `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst`, `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`, `changelog/<PR>.feature.rst`, the two planning docs (table rows).
- Upstream (separate, optional): glue-qt `glue_qt/viewers/profile/data_viewer.py:19` dict form; glue-core `glue/viewers/profile/viewer.py:16,23` label with unit.

**Step-by-step.**

1. In `glue_solar/sources/loaders/iris.py` add, after `_GlueWCS`:

   ```python
   def rest_wavelength(data):
       """Rest wavelength of a dataset's (or cube's) spectral window as a Quantity, or None.

       ``meta['rest_wavelength']`` (float, Angstrom; written for 4-D stacks and by the user override)
       wins over irispy's ``SGMeta.rest_wavelength`` (from the TWAVE card).
       """
       meta = getattr(data, "meta", None)
       if meta is None:
           return None
       try:
           rest = meta["rest_wavelength"] if "rest_wavelength" in meta else meta.rest_wavelength
       except (AttributeError, TypeError, ValueError):  # plain dict, or irispy 0.8.1 with no TWAVE card
           rest = None
       return None if rest is None else u.Quantity(rest, u.AA)
   ```
   Export it in `__all__`. In `_raster_collection_data`, stack branch, after `data = _cube_data(cube, label, color="#7A617C")`:
   ```python
               rest = rest_wavelength(sequence[0])  # scan 0's SGMeta; the stack's own meta is a plain dict
               if rest is not None:
                   data.meta["rest_wavelength"] = rest.to_value(u.AA)
   ```
2. Create `glue_solar/iris_lines.csv` with exactly:
   ```
   wavelength,name
   1334.53,C II 1334
   1335.71,C II 1335
   1351.66,Cl I 1351
   1354.08,Fe XXI 1354
   1355.60,O I 1355
   1393.76,Si IV 1394
   1399.77,O IV 1400
   1401.16,O IV 1401
   1402.77,Si IV 1403
   2796.35,Mg II k
   2803.53,Mg II h
   ```
   Values are vacuum wavelengths in Angstrom. Sources checked today: C II 1334.53/1335.71 Rathore, Pereira, Carlsson & De Pontieu 2015 (arXiv:1510.04845, "formation of IRIS diagnostics VIII"); Si IV 1393.76/1402.77 and O IV 1399.77/1401.16 Dudík et al. 2017 ApJ (arXiv:1705.02104, ar5iv text quotes "1393.76 Å and 1402.77 Å", "1399.77 Å, 1401.16 Å"), also Young 2015 (arXiv:1509.05011) Table 1 O IV 1399.766/1401.157; Mg II k 2796.35 / h 2803.53 Kerr et al. 2015 A&A 582 A50 ("rest vacuum wavelengths are 2803.53 Å and 2796.35 Å"); Fe XXI 1354.08 Young, Tian & Jaeggli 2015 ApJ 799 218; Fe XXI 1354.08, O I 1355.60, Cl I 1351.66 and C II 1335.71 P. R. Young, "Line lists for the IRIS far ultraviolet wavelength bands", v1.5, 21 Nov 2017 (pyoung.org/iris/iris_line_list.pdf; text extracted below). The IRIS L2 headers themselves carry TWAVE = 1335.71 (C II 1336), 1402.77 (Si IV 1403), 1355.60 (O I 1356) for the shipped test rasters.
3. Create `glue_solar/viewers.py` with the verified code below (converter, blink, line list, actions, `install()`), imports ordered the way `loaders/iris.py` does it (stdlib; glue/glue_qt/qtpy; astropy; local).
4. `glue_solar/__init__.py`:
   ```python
   from glue_solar import viewers
   from glue_solar.sources import iris, maps
   ...
   __all__ = ["setup", "__version__", "iris", "maps", "viewers"]

   def setup():
       for _, ctable in sorted(cmlist.items()):
           colormaps.add(ctable.name, ctable)
       viewers.install()
   ```
   `install()` is idempotent (guards on the list and the dict) because `setup()` runs once at plugin load (`glue/main.py:13 load_plugins`, called from `glue_qt/app/application.py:296`) and again in `test_plugin.py:10`.
5. `glue_solar/conftest.py`: add
   ```python
   @pytest.fixture(autouse=True)
   def _quiet_glue_settings():
       from glue.config import settings
       settings._save_to_disk = False          # never write ~/.glue/settings.cfg from a test run
       settings.SHOW_INFO_PROFILE_OPEN = False  # the profile viewer's info dialog is modal offscreen
   ```
6. Add `glue_solar/tests/test_viewers.py` (section "Tests to add").
7. Docs and changelog (section "Docs").
8. Optional upstream PRs, after the glue-solar PR is merged: glue-qt `profile/data_viewer.py:19` `_layer_style_widget_cls = {QThreadedProfileLayerArtist: ProfileLayerStyleEditor}`; glue-core `profile/viewer.py` add `self.state.add_callback('x_display_unit', self._update_axes)` after :18 (end of `setup_callbacks`, :15-18) and make :23 `self.state.x_axislabel = f'{self.state.x_att.label} [{self.state.x_display_unit}]' if self.state.x_display_unit else self.state.x_att.label` (verified by monkeypatch below; the profile-wcs branch sets `x_axislabel = ''` in WCSAxes mode, keep that precedence). Once the glue-qt change is released, drop the `isinstance(..., dict)` branch in `install()`; the glue-core change needs no glue-solar code.

**Verified code.** Scratch harnesses: `IRIS_PLAN_PROTOTYPES/wp5_*.py` (all run today with `HOME=<scratch>/home-wp5 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python`). The shipping code is reproduced here verbatim from those files.

Checker re-run (2026-09-02, `HOME=<scratch>/home-chk5 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg`): `wp5_conv.py`, `wp5_override.py`, `wp5_label.py`, `wp5_blink.py`, `wp5_linelist.py`, `wp5_ll_session.py`, `ulb_conv.py`, `ulb_blink.py`, `ulb_ll2.py 1`, `linelist_proto.py` and the persisted-setting trap all reproduce the outputs below byte for byte (only `np.float64(...)` reprs differ). `~/.glue/settings.cfg` still `unit_converter = "default"`, mtime 08:36. Additional checker harnesses: `chk5_twave.py` (TWAVE table), `chk5_misc.py` (stack `sequence[0]` rest wavelength, y-choice pollution), `chk5_bisect3.py` (duplicate 2021 raster).

(a) Velocity converter (`wp5_units.py`, target `glue_solar/viewers.py`):

```python
import astropy.units as u
from glue.config import unit_converter
from glue.core.units import SimpleAstropyUnitConverter

WAVELENGTH_UNITS = ("Angstrom", "nm")   # ponytail: fixed short list instead of astropy's 131 prefixed length units
ANGLE_UNITS = ("arcsec", "arcmin", "deg")
VELOCITY_UNIT = "km / s"


class IRISUnitConverter(SimpleAstropyUnitConverter):
    """glue's default converter plus wavelength <-> velocity for datasets with a rest wavelength."""

    def _equivalencies(self, data):
        rest = rest_wavelength(data)
        return [] if rest is None else u.doppler_optical(rest)

    def equivalent_units(self, data, cid, units):
        unit = u.Unit(units)
        if unit.is_equivalent(u.m):
            velocity = [VELOCITY_UNIT] if rest_wavelength(data) is not None else []
            return [x for x in WAVELENGTH_UNITS if x != units] + velocity
        if unit.is_equivalent(u.deg):
            return [x for x in ANGLE_UNITS if x != units]
        return super().equivalent_units(data, cid, units)

    def to_unit(self, data, cid, values, original_units, target_units):
        return (values * u.Unit(original_units)).to_value(target_units, equivalencies=self._equivalencies(data))


def install():
    # Override the built-in 'default' entry. Do NOT register a new name and point settings.UNIT_CONVERTER
    # at it: glue-qt persists that setting to ~/.glue/settings.cfg and `import glue` then fails with
    # KeyError (glue/config.py:938) whenever the plugin is not importable at startup.
    unit_converter.members["default"] = IRISUnitConverter
```
`rest_wavelength` is the helper from step 1 (in `wp5_units.py` it lives in the same file).

Run (`wp5_conv.py`: real 2014-03-29 raster, Mg II k window; `_AngstromWCS` in the script simulates D3 by mapping `em.wl` to Angstrom with the same pattern `_GlueWCS` uses for arcsec):
```
$ HOME=$S/home-wp5 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python $S/wp5_conv.py
native units today: 'm' | rest_wavelength(data): 2796.1999511699996 Angstrom
pruned choices (m): ['m', 'Angstrom', 'nm', 'km / s']
pruned choices (arcsec): ['arcsec', 'arcmin', 'deg']
settings.UNIT_CONVERTER still: default
native units after D3: 'Angstrom' | choices: ['Angstrom', 'nm', 'km / s']
x_display_unit choices: ['Angstrom', 'nm', 'km / s']
x native Angstrom [:2]: [2790.51220075 2790.53766075] | xlim: (2790.5122007492964, 2792.0907207008495)
x km/s [:2]: [-609.80784954 -607.07817503] | xlim: (-609.81, -440.57) | axis label: Wavelength
ROI -50..50 km/s -> native subset range (Angstrom): (2795.734, 2796.666) att: Wavelength
expected from doppler_optical: [2795.734, 2796.666]
after override + NumericalDataChangedMessage: x km/s [:2]: [-625.8616363  -623.13210826] | shift: -16.05 km/s
stack meta type: dict | hasattr rest_wavelength: False | rest_wavelength(stack) before loader key: None
stack choices without key: ['m', 'Angstrom', 'nm']
stack choices with key: ['m', 'Angstrom', 'nm', 'km / s']
DONE
```
Missing TWAVE and unparseable data units (same session, `wp5_units.rest_wavelength`):
```
helper without TWAVE -> None
choices without TWAVE: ['m', 'Angstrom', 'nm']
data unit string: 'DN_IRIS_FUV' -> ValueError (caught by find_unit_choices): 'DN_IRIS_FUV' did not parse as unit
y choices for DN component: ['DN_IRIS_FUV']
```
Without the try/except, irispy 0.8.1 raises: `SGMeta.rest_wavelength without TWAVE raises TypeError float() argument must be a string or a real number, not 'NoneType'`.

Auditor's original 12-line converter re-run today (`ulb_conv.py`, native `m`, default choice list): `default 'm' choices count: 131`, `km / s in choices: True | n choices: 132`, `x km/s: [-675.65510997 -669.82853646] | xlim: -675.65 -576.60`, `to_native(-675 km/s) m: [1.33269959e-07]`, `draw OK; ax xlabel: Wavelength`.

Persisted-setting trap (reproduced in a scratch HOME):
```
$ mkdir -p $S/home-trap/.glue && printf '[main]\nunit_converter = "iris-velocity"\n' > $S/home-trap/.glue/settings.cfg
$ HOME=$S/home-trap .venv/bin/python -c "import glue; print('import glue OK')"
  File ".../glue/config.py", line 938, in check_unit_converter
    raise KeyError(f'Unit converter {value} is not defined')
KeyError: 'Unit converter iris-velocity is not defined'
$ printf '[main]\nunit_converter = "default"\n' > $S/home-trap/.glue/settings.cfg && HOME=$S/home-trap .venv/bin/python -c "import glue; print('import glue OK')"
import glue OK
```
glue-qt writes every setting on `save_settings()` (`glue/_settings_helpers.py:8-27`, callers `glue_qt/core/dialogs.py:44`, `app/preferences.py:170`, `utils/app.py:96`), and `glue/__init__.py:35 load_settings` runs before any plugin registers.

Optional per-dataset override (`wp5_override.py`, target `glue_solar/viewers.py`):
```python
from glue.core.message import NumericalDataChangedMessage
from glue_qt.config import layer_action
from qtpy import QtWidgets


@layer_action("Set rest wavelength…", single=True, data=True)
def set_rest_wavelength(data, data_collection, value=None):
    """Store a rest wavelength (Angstrom) on ``data.meta`` and refresh open viewers."""
    current = rest_wavelength(data)
    if value is None:
        value, ok = QtWidgets.QInputDialog.getDouble(
            None, "Rest wavelength", "Rest wavelength [Angstrom] (0 removes the override):",
            0.0 if current is None else current.to_value(u.AA), 0.0, 1e5, 3)
        if not ok:
            return
    if value:
        data.meta["rest_wavelength"] = float(value)
    else:
        data.meta.pop("rest_wavelength", None)
    if data.hub is not None:
        data.hub.broadcast(NumericalDataChangedMessage(data))  # profile layers recompute (common/viewer.py:288-302, data branch :300-302)
```
```
$ .venv/bin/python $S/wp5_override.py
registered: ['Set rest wavelength…'] | callback signature: (layer, data_collection)
TWAVE rest -> x[0] = -295.90 km/s; override 2796.35 -> x[0] = -311.97 km/s; shift -16.07 km/s
override removed -> rest_wavelength(data): 2796.1999511699996 Angstrom | x[0] back: -295.9
```
(`QInputDialog` itself is not exercised offscreen; the `value=` path is what the test calls.)

TWAVE versus literature rest wavelengths (real test headers, `astropy.io.fits`; checker `chk5_twave.py`, offset = `(TWAVE - lit) / lit * c`, i.e. the change in every displayed velocity when the override replaces TWAVE by the literature value; matches the -16.05 km/s shift measured above):
```
$ HOME=$S/home-chk5 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python $S/chk5_twave.py
C II 1336    TWAVE=1335.7100 lit=1335.71 -> zero-point offset -0.0 km/s
O I 1356     TWAVE=1355.6000 lit=1355.60 -> zero-point offset -0.0 km/s
Si IV 1403   TWAVE=1402.7700 lit=1402.77 -> zero-point offset +0.0 km/s
Mg II k      TWAVE=2796.2000 lit=2796.35 -> zero-point offset -16.1 km/s
Si IV 1394   TWAVE=1393.7800 lit=1393.76 -> zero-point offset +4.3 km/s
```

Optional glue-core label PR, verified by monkeypatch (`wp5_label.py`, synthetic WAVE WCS in Angstrom):
```
Angstrom -> 'Wave [Angstrom]'
nm -> 'Wave [nm]'
km / s -> 'Wave [km / s]'
```

(b) Blink tool (`wp5_blink.py`, target `glue_solar/viewers.py`):
```python
from glue.config import viewer_tool
from glue.core import BaseData
from glue.viewers.common.tool import CheckableTool
from glue_qt.viewers.image import ImageViewer
from qtpy import QtCore, QtWidgets


@viewer_tool
class BlinkTool(CheckableTool):
    """Show the visible image layers one at a time in turn; the spinbox next to the button sets the interval."""

    tool_id = "image:blink"
    icon = "glue_replace"
    action_text = "Blink layers"
    tool_tip = "Blink: show the visible image layers one at a time in turn"

    def __init__(self, viewer):
        super().__init__(viewer)
        self._timer = QtCore.QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._step)
        self._layers = []
        self._index = 0
        # ponytail: Tool.menu_actions() is never attached for a CheckableTool (glue_qt toolbar.py:106-136 only
        # calls setMenu for DropdownTool), so the interval knob is a plain toolbar widget instead.
        self._interval = QtWidgets.QSpinBox()
        self._interval.setRange(50, 5000)
        self._interval.setSingleStep(50)
        self._interval.setSuffix(" ms")
        self._interval.setValue(self._timer.interval())
        self._interval.setToolTip("Blink interval")
        self._interval.valueChanged.connect(self._timer.setInterval)
        viewer.toolbar.addWidget(self._interval)

    def _step(self):
        if not self._layers:
            return
        self._index = (self._index + 1) % len(self._layers)
        for i, layer in enumerate(self._layers):
            layer.state.visible = i == self._index

    def activate(self):
        # ponytail: the set of blinked layers is frozen at activation; toggle the tool to pick up new layers
        self._layers = [layer for layer in self.viewer.layers
                        if layer.enabled and layer.state.visible and isinstance(layer.layer, BaseData)]
        self._index = 0
        self._step()
        self._timer.start()

    def deactivate(self):
        self._timer.stop()
        for layer in self._layers:
            layer.state.visible = True
        self._layers = []

    def close(self):
        self._timer.stop()
        super().close()


# in install(): ImageViewer.tools is a plain list on the class (glue_qt/viewers/image/data_viewer.py:42-45)
if "image:blink" not in ImageViewer.tools:
    ImageViewer.tools = [*ImageViewer.tools, "image:blink"]
```
```
$ .venv/bin/python $S/wp5_blink.py     # three 20x20 images a,b,c pixel-linked with LinkSame; c hidden by the user
toolbar has blink: True | spinbox in toolbar: True | interval: 500
activate  -> visible: [('a', True, False), ('b', True, True), ('c', True, False)] | timer active: True | blinked: ['a', 'b']
step      -> visible: [('a', True, True), ('b', True, False), ('c', True, False)]
step      -> visible: [('a', True, False), ('b', True, True), ('c', True, False)]
spinbox 200 -> timer interval: 200
timer-driven states seen: [(('a', True, False), ('b', True, True), ('c', True, False)), (('a', True, True), ('b', True, False), ('c', True, False))]
deactivate -> visible: [('a', True, True), ('b', True, True), ('c', True, False)] | timer active: False
mix already exists: composite alphas [0.8, 0.5, 0.8] | color_mode choices: ['Colormaps', 'One color per layer']
with a subset layer: layers ['ImageLayerArtist', 'ImageLayerArtist', 'ImageLayerArtist', 'ImageSubsetLayerArtist', 'ImageSubsetLayerArtist', 'ImageSubsetLayerArtist'] | blinked: ['a', 'b']
viewer closed; timer active: False | tool.viewer: None
DONE
```
`glue.icons.icon_path('glue_replace')` exists (any name in `glue/icons/*.png` works; `playback_forw` and `glue_rainbow` also checked).

(c) Line list (`wp5_linelist_mod.py`, target `glue_solar/viewers.py`):
```python
import astropy.units as u
from glue.config import layer_artist_maker
from glue.core import Data
from glue.core.units import UnitConverter
from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.profile.state import ProfileLayerState
from glue.viewers.profile.viewer import MatplotlibProfileMixin
from glue_qt.viewers.profile.data_viewer import ProfileViewer
from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist
from glue_qt.viewers.profile.layer_style_editor import ProfileLayerStyleEditor


class LineListState(ProfileLayerState):
    """State of a line-list layer.

    Reusing ProfileLayerState satisfies everything ProfileViewerState touches on its layers
    (``attribute`` at state.py:266/:292, ``reset_cache`` at :308, ``profile`` at :131/:221) and
    gives colour/alpha/linewidth for the style editor. ``attribute`` resolves to the numeric
    ``wavelength`` column on its own.
    """


class LineListArtist(MatplotlibLayerArtist):
    """Labelled vertical lines at the wavelengths (Angstrom) of a line-list table, in the viewer's display unit."""

    _layer_state_cls = LineListState
    is_computing = False  # read for every layer by glue_qt/viewers/matplotlib/data_viewer.py:59

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)
        for prop in ("x_att", "x_display_unit", "reference_data"):
            self._viewer_state.add_callback(prop, self.update)
        self.state.add_global_callback(self.update)
        self.update()

    def _clear(self):
        for artist in self.mpl_artists:
            artist.remove()
        self.mpl_artists = []

    def update(self, *args, **kwargs):
        self._clear()
        state, data = self._viewer_state, self.layer
        # the reference_data callback can fire while x_att still belongs to the previous reference
        if state.reference_data is None or state.reference_data is data or state.x_att not in state.reference_data.components:
            return
        native = state.reference_data.get_component(state.x_att).units or ""
        if not native or not u.Unit(native).is_equivalent(u.m):
            return  # x axis is not a wavelength axis (pixels, helioprojective angles, time): nothing to mark
        positions = (data["wavelength"] * u.AA).to_value(native)
        positions = UnitConverter().to_unit(state.reference_data, state.x_att, positions, state.x_display_unit)
        style = dict(color=self.state.color, alpha=self.state.alpha, zorder=self.state.zorder, visible=self.state.visible)
        for x, name in zip(positions, data["name"]):
            self.mpl_artists.append(self.axes.axvline(x, linewidth=self.state.linewidth, **style))
            self.mpl_artists.append(self.axes.annotate(str(name), (x, 0.98), xycoords=("data", "axes fraction"),
                                                       rotation=90, ha="right", va="top", fontsize="small", **style))
        self.redraw()

    def remove(self):
        for prop in ("x_att", "x_display_unit", "reference_data"):
            self._viewer_state.remove_callback(prop, self.update)
        super().remove()


@layer_artist_maker("iris-line-list")
def line_list_artist(viewer, data):
    if isinstance(viewer, MatplotlibProfileMixin) and isinstance(data, Data) \
            and {"wavelength", "name"} <= {c.label for c in data.main_components}:
        return LineListArtist(viewer.axes, viewer.state, layer=data)


# in install(): exact-class lookup in glue_qt/core/layer_artist_model.py:365-370 -> key on the Qt artist classes
if not isinstance(ProfileViewer._layer_style_widget_cls, dict):
    ProfileViewer._layer_style_widget_cls = {QThreadedProfileLayerArtist: ProfileLayerStyleEditor,
                                             LineListArtist: ProfileLayerStyleEditor}
```
Menubar action (verified with the scratch CSV path; the real path is `str(files("glue_solar") / "iris_lines.csv")`):
```python
from importlib.resources import files
from glue.config import menubar_plugin
from glue.core.data_factories import load_data


@menubar_plugin("IRIS: add line list")
def add_iris_line_list(session, data_collection):
    data = load_data(str(files("glue_solar") / "iris_lines.csv"))  # glue's table factory: 'wavelength' float, 'name' categorical
    data.label = "IRIS lines"
    data_collection.append(data)
```
```
menubar action -> [('IRIS lines', (11,), ['wavelength', 'name'])]
label: iris_lines | shape: (11,) | components: [('wavelength', 'Component', ''), ('name', 'CategoricalComponent', '')] | has load_log: True
```
Run (`wp5_linelist.py`: real 2021-09-05 raster, C II 1336 window, converter installed):
```
$ .venv/bin/python $S/wp5_linelist.py
add line list -> True | layers: ['QThreadedProfileLayerArtist', 'LineListArtist'] | n mpl artists: 22
style widgets: ['QThreadedProfileLayerArtist', 'LineListArtist'] | layer list rows: 2
C II 1334.53 in native m: 1.3345300000000002e-07
in Angstrom: 1334.53
in nm: 133.453
in km/s (rest = TWAVE 1335.71): -264.84 | expected: -264.84
hidden -> artists visible: {False}
shown  -> artists visible: {True}
style change -> line color/width: #ff0000 2.0 | attribute: wavelength
legend visible draw OK; entries: ['C_II_1336-3620258102-2021-09-05T00:18:33-scan-0', 'IRIS lines']
ROI on the profile -> layers: [('QThreadedProfileLayerArtist', 'C_II_1336-...-scan-0', True), ('LineListArtist', 'IRIS lines', True), ('QThreadedProfileLayerArtist', 'Subset 1', True), ('QThreadedProfileLayerArtist', 'Subset 1', False)] | subsets on line list: ['Subset 1']
after remove_data: layers: ['QThreadedProfileLayerArtist', 'QThreadedProfileLayerArtist'] | axvlines left on axes: 0
unit change after removal raised nothing
line list first -> reference_data: IRIS lines | layers: ['LineListArtist', 'QThreadedProfileLayerArtist'] | artists: 0
after adding the raster and switching reference_data (x_att auto = Helioprojective Longitude) -> artists: 22 | x_att: Wavelength
x_att = Wavelength -> artists: 22
x_att = pixel axis -> artists: 0
MODAL DIALOG SUPPRESSED: Failed to save session
no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.quantity.Quantity'>]
```
(The final save failure is the IRIS raster's SGMeta `Quantity` values, WP3's bug, not the line list. glue-qt's `save_session` swallows the error into that message box, so the script's next lines, `session save OK: 13 KB` and `restored viewers: 1 | with LineListArtist: 1`, read the stale `wp5_lines.glu` written earlier by `wp5_ll_session.py`; ignore them. Note the "x_att auto" line: `_reference_data_changed` had already moved `x_att` to Wavelength by the time the print ran, the `IncompatibleAttribute` and `UnitConversionError` seen before the two guards are recorded under pitfalls.)

Session round trip of the line-list layer alone (`wp5_ll_session.py`: synthetic 1-D `WAVE` WCS in Angstrom, CSV, `km / s`, green lines; `_type` in the file is the module path `wp5_linelist_mod.LineListArtist`, which will be `glue_solar.viewers.LineListArtist`):
```
$ .venv/bin/python $S/wp5_ll_session.py
before save: layers ['QThreadedProfileLayerArtist', 'LineListArtist'] | first line x: -264.84
saved 13548 bytes
restored: layers ['QThreadedProfileLayerArtist', 'LineListArtist'] | x_display_unit 'km / s' | artists: 22 | first line x: -264.84 | color: #00aa00 | _type in file: True
after reload unit switch -> first line x: 1334.53
```
Failure modes reproduced today (why the shims exist):
```
$ .venv/bin/python $S/linelist_proto.py          # auditor's artist with a bare LayerState
MODAL DIALOG SUPPRESSED: Failed to add data
'LayerState' object has no attribute 'attribute'
add_data returned: None | layers: ['QThreadedProfileLayerArtist']
$ .venv/bin/python $S/wp5_linelist.py             # earlier iteration: LayerState + attribute property, line list added first
MODAL DIALOG SUPPRESSED: Failed to add data
'LineListState' object has no attribute 'reset_cache'
$ .venv/bin/python $S/ulb_ll2.py 1                # verifier's style-widget check
style widgets created for: []                     # dict keyed on ProfileLayerArtist
v2 style widgets: ['QThreadedProfileLayerArtist'] # dict keyed on QThreadedProfileLayerArtist
```
Young's line list text (zlib-decoded from the PDF): "Line lists for the IRIS far ultraviolet wavelength bands Version 1.5, 21 November 2017 Peter R. Young"; "Cl I 1351.66 is unusually strong"; "the strongest transition is 1355.844, and 1354.288 blends with Fe XXI 1354.08 during flares"; "The O I 1355.60 wavelength comes from Eriksson & Isberg (1963)"; "the very strong C II 1335.71 transition".

**Tests to add.** File `glue_solar/tests/test_viewers.py`, pytest-qt (`qtbot` present but the viewers are driven through `GlueApplication` as in glue-qt's own tests). Real files: `irispy_test_files` fixture. `RASTER_2014 = "iris_l2_20140329_140938_3860258481_raster_t000_r0000{n}.fits"` n = 0 for the single-scan Mg II k tests (window `Mg II k 2796`, TWAVE 2796.19995117, x range 2790.51..2792.09 Angstrom, verified in `wp5_conv.py`) and n = 0..2 for the stack. `RASTER_2021 = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"` only for the FUV window `C II 1336` (TWAVE 1335.70996094) and selected with `parent.name == "sns"`: the same-named `raster/` copy cannot load NUV windows on irispy 0.8.1 (see Current state). Synthetic: `Data(label=..., x=np.random.random((20, 20)))` images linked with `LinkSame`, and a 1-D `astropy.wcs.WCS(naxis=1)` with `ctype WAVE`, `cunit Angstrom`, `crval 1330`, `cdelt 0.1`.

```python
@pytest.fixture
def app():
    app = GlueApplication()
    yield app
    app.close()

def _real(files, name, parent=None):
    return next(p for p in files if p.name == name and (parent is None or p.parent.name == parent))

def _wavelength(data):
    return next(c for c in data.world_component_ids if c.label == "Wavelength")

@pytest.fixture
def mg2k(irispy_test_files):
    return raster_data([_real(irispy_test_files, RASTER_2014.format(0))], ["Mg II k 2796"])[0]

@pytest.fixture
def c2(irispy_test_files):
    return raster_data([_real(irispy_test_files, RASTER_2021, parent="sns")], ["C II 1336"])[0]
```
1. `test_setup_installs_registries`: `glue_solar.setup(); glue_solar.setup()`; assert `unit_converter.members["default"] is IRISUnitConverter`; `ImageViewer.tools.count("image:blink") == 1`; `ProfileViewer._layer_style_widget_cls[QThreadedProfileLayerArtist] is ProfileLayerStyleEditor`; `ProfileViewer._layer_style_widget_cls[LineListArtist] is ProfileLayerStyleEditor`; `"IRIS: add line list" in [label for label, _ in menubar_plugin]`; `settings.UNIT_CONVERTER == "default"`.
2. `test_rest_wavelength_helper(mg2k)`: `d = mg2k`; `rest_wavelength(d) == pytest.approx(2796.19995117 * u.AA)`; `d.meta["rest_wavelength"] = 2796.35` -> `rest_wavelength(d).to_value(u.AA) == 2796.35`; `del d.meta["rest_wavelength"]; del d.meta[f"TWAVE{d.meta._iwin}"]` -> `rest_wavelength(d) is None`; `rest_wavelength(Data(x=[1])) is None`.
3. `test_wavelength_unit_choices(mg2k)`: `native = d.get_component(_wavelength(d)).units`; `find_unit_choices([(d, _wavelength(d), native)]) == [native] + [x for x in ("Angstrom", "nm") if x != native] + ["km / s"]` (after WP1 this is `["Angstrom", "nm", "km / s"]`); `lat` component choices `== ["arcsec", "arcmin", "deg"]`; after deleting the TWAVE card the list has no `"km / s"`.
4. `test_stack_carries_rest_wavelength(irispy_test_files)`: `stack = raster_data([_real(irispy_test_files, RASTER_2014.format(n)) for n in range(3)], ["Mg II k 2796"], stack=True)[0]`; `type(stack.meta) is dict`; `stack.meta["rest_wavelength"] == pytest.approx(2796.19995117)`; `"km / s" in find_unit_choices([(stack, _wavelength(stack), stack.get_component(_wavelength(stack)).units)])`.
5. `test_profile_velocity_axis_and_roi(app, mg2k)`: `d = mg2k`; `app.data_collection.append(d)`; `v = app.new_data_viewer(ProfileViewer, data=d)`; `v.state.x_att = _wavelength(d)`; `x_native = v.layers[0].state.profile[0].copy()`; `v.state.x_display_unit = "km / s"`; `assert_allclose(v.layers[0].state.profile[0], (x_native * u.Unit(native)).to_value(u.km / u.s, u.doppler_optical(rest_wavelength(d))))`; `v.state.x_axislabel == "Wavelength"`; `v.apply_roi(XRangeROI(-50, 50))`; `ss = d.subsets[0].subset_state`; `(ss.lo, ss.hi) == pytest.approx((( -50 * u.km / u.s).to_value(u.Unit(native), u.doppler_optical(rest)), (50 * u.km / u.s).to_value(...)))`; `ss.att is _wavelength(d)`.
6. `test_set_rest_wavelength_override(app, mg2k)`: same viewer in `km / s`; `x0 = profile x[0]`; `set_rest_wavelength(d, app.data_collection, value=2796.35)`; `profile x[0] - x0 == pytest.approx(-16.05, abs=0.05)`; `set_rest_wavelength(d, app.data_collection, value=0)`; `"rest_wavelength" not in d.meta`; `profile x[0] == pytest.approx(x0)`.
7. `test_blink_tool(app)`: three linked images, `v.layers[2].state.visible = False`; `tool = v.toolbar.tools["image:blink"]`; `v.toolbar.active_tool = "image:blink"`; `[l.state.visible for l in v.layers] == [False, True, False]` and `[l.layer.label for l in tool._layers] == ["a", "b"]`; `tool._step()` -> `[True, False, False]`; `tool._interval.setValue(200)` -> `tool._timer.interval() == 200`; `v.toolbar.active_tool = None` -> `[True, True, False]` and `not tool._timer.isActive()`; `v.apply_roi(RectangularROI(2, 8, 2, 8)); v.toolbar.active_tool = "image:blink"` -> `tool._layers` labels still `["a", "b"]`; `v.close(warn=False)` -> `not tool._timer.isActive()`.
8. `test_line_list_layer(app, c2)`: `add_iris_line_list(None, app.data_collection)`; `lines = app.data_collection[-1]`; `lines.label == "IRIS lines"`, `lines.shape == (11,)`, `list(lines["name"][:2]) == ["C II 1334", "C II 1335"]`; raster `d = c2` (C II 1336, TWAVE 1335.70996094) added, `v.state.x_att = _wavelength(d)`, `v.add_data(lines) is True`; `la = v.layers[1]`; `isinstance(la, LineListArtist)`; `len(la.mpl_artists) == 22`; `set(type(k).__name__ for k in v._view.layout_style_widgets) == {"QThreadedProfileLayerArtist", "LineListArtist"}`; `v.state.x_display_unit = "Angstrom"` -> `la.mpl_artists[0].get_xdata()[0] == pytest.approx(1334.53)`; `"km / s"` -> `== pytest.approx(-264.84, abs=0.01)`; `la.state.visible = False` -> all artists invisible; `la.state.color = "#ff0000"` -> `la.mpl_artists[0].get_color() == "#ff0000"`; `v.state.x_att = d.pixel_component_ids[2]` -> `la.mpl_artists == []`; `v.remove_data(lines)` -> no `LineListArtist` in `v.layers` and no vertical lines left in `v.axes.lines`; `v.state.x_display_unit = "nm"` raises nothing.
9. `test_line_list_session_round_trip(app, tmp_path)`: synthetic WAVE spectrum with `spec.meta["rest_wavelength"] = 1335.71`, line list, `km / s`, colour `#00aa00`; `app.save_session(path, include_data=True)`; `app2 = GlueApplication.restore_session(path)`; the restored `ProfileViewer` has a `LineListArtist` with 22 artists, `x_display_unit == "km / s"`, first line at `-264.84`, `state.color == "#00aa00"`; `app2.close()`.

**Pitfalls (verified).**

- `settings.UNIT_CONVERTER` naming a plugin converter is persisted by glue-qt and then `import glue` raises `KeyError` from `config.py:938` (reproduced above). Override `members['default']` instead; `settings.UNIT_CONVERTER` stays `'default'` (printed in every run).
- The glue-qt style-widget dict must be keyed on `QThreadedProfileLayerArtist`, not `ProfileLayerArtist`: exact-class lookup at `layer_artist_model.py:365-370`. Keyed on the base class the real spectrum silently loses its style editor (`style widgets created for: []`).
- `ProfileViewerState` calls three things on every layer state: `.attribute` (`state.py:266`, `:292`), `.reset_cache()` (`:307-308`, on any reference-data change, e.g. when the line list is the first layer) and `.profile` (`:131`, `:221`, both wrapped in `try/except Exception`). A bare `LayerState` fails with a modal "Failed to add data" (`'LayerState' object has no attribute 'attribute'`, then `'reset_cache'`). Subclass `ProfileLayerState`; no glue-core guard is then needed.
- The artist's `reference_data` callback can run while `x_att` still belongs to the previous reference: `get_component` raised `IncompatibleAttribute: Pixel Axis 0 [x]` until the `x_att not in reference_data.components` guard was added.
- A raster reference defaults to `x_att = Helioprojective Longitude` (arcsec); converting Angstrom positions raised `UnitConversionError: 'Angstrom' (length) and 'arcsec' (angle) are not convertible`. Draw only when the native x unit is a length; pixel and time axes give 0 artists (verified).
- `TWAVE` is the window's reference wavelength, not a laboratory rest wavelength: overriding Mg II k `2796.20` with `2796.35` lowers every displayed velocity by 16.1 km/s, Si IV 1394 `1393.78` -> `1393.76` raises them by 4.3 km/s (table above). Keep the override action; document it.
- The shipped irispy test rasters are cropped windows and every window excludes its own TWAVE (2014 Mg II k spans 2790.51..2792.09 Angstrom, TWAVE 2796.20), so `km / s` values in tests are hundreds of km/s (-609.8 at the window start). That is the data, not a conversion bug; assert against `doppler_optical`, never against "small" numbers. (Same observation in `wp2-moments.md:31`.)
- irispy 0.8.1 `SGMeta.rest_wavelength` raises `TypeError` for a window without `TWAVE` (verified by deleting the card). The helper catches it. Do not call the property directly anywhere else.
- 4-D stacks have a plain-dict meta (`stack_spectrograms.py:80`): no `km / s` unless the loader writes `meta['rest_wavelength']` (with/without key verified). Do not use the verifier's `meta.get('TWAVE1')` fallback: the dict keeps all nine `TWAVE<n>` cards and the Mg II k window is `TWAVE9` (verified today). WP3 must keep that float on reload; after a reload every meta is a plain `OrderedDict`, so the key is also what keeps `km / s` alive for reloaded single scans (WP3 should write it for scans too, one line in `_cube_data`).
- Two irispy test files share the name `iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits`; the `raster/` copy raises `ValueError: Expected 187 NUV source filename rows, found 1872` for every NUV window on irispy 0.8.1, the `sns/` copy works (checker `chk5_bisect3.py`). Select by `parent.name == "sns"` or use the 2014 rasters for Mg II k; a name-only `next(...)` is order-dependent and made the checker's first TWAVE harness fail.
- The line-list `wavelength` column must stay unitless (glue's CSV factory gives `''`). Verified today (`chk5_misc.py`): with `Component(..., units='Angstrom')` the profile viewer's y-axis unit combo becomes `[None, 'Angstrom', 'nm', 'DN_IRIS_FUV']` (`_update_y_display_unit_choices`, `state.py:289-296`); unitless it stays `[None, 'DN_IRIS_FUV']`.
- `Tool.menu_actions()` is dead for a `CheckableTool`: `toolbar.py:184-192` builds the menu but `_make_action` (`:106-136`) only calls `setMenu` on a `DropdownTool` button. `viewer.toolbar` already exists when tools are constructed (`data_viewer.py:165` vs `:171-180`), so `toolbar.addWidget(spinbox)` is the working knob; it lands just before the blink button.
- Blink over unlinked datasets: a second unlinked image layer is disabled at draw time (`('b', False, True)` in the instrumented run), so tests must `LinkSame` the pixel components; real SJI/AIA pairs are linked by WCS/link_hpc.
- `viewer.close()` in offscreen tests can block on glue-qt's confirm-close dialog (`glue_qt/viewers/common/data_viewer.py:126` `close(self, warn=True)`; writer-observed, the checker only ran the `warn=False` form); use `close(warn=False)`. `settings.SHOW_INFO_PROFILE_OPEN = False` (`glue/config.py:929`) for the profile viewer's info dialog; `SHOW_WARN_PROFILE_DUPLICATE` (`:930`) is the other modal on that path.
- Sessions containing IRIS data still fail in WP3's three ways (`numpy.save ... Quantity` reproduced above; `_GlueWCS` unserializable; `preferred_cmap` Colormap not JSON serializable, `findings/session-serialization.json`); the line-list session test must use synthetic data. The line-list layer itself needs no saver.
- Applying an ROI in the profile viewer creates `Subset 1` on every dataset, including the line list; its default profile artist is disabled (`('QThreadedProfileLayerArtist', 'Subset 1', False)`), which is glue's normal behaviour for incompatible subsets. Cosmetic; leave it.
- `x_axislabel` stays `Wavelength` whatever the unit (`viewer.py:22-23`); only the optional glue-core PR changes that.
- Fork profile-wcs (unreleased): in WCSAxes mode (`wcsaxes_active`, fork `glue/viewers/profile/state.py:190-198`, true when `x_display_unit` equals the native unit) profile x values are pixel indices (`:597-600` uses `x_att_pixel`), so `LineListArtist.update` must place lines with `reference_data.coords.world_to_pixel_values` when `getattr(state, "wcsaxes_active", False)`. Not run against the fork (checker: confirmed by `git show profile-wcs:...` only); belongs to WP0's profile-wcs item.
- The converter is global: any dataset with a length-unit axis gets the pruned `Angstrom/nm` list and any dataset with a `rest_wavelength` gets `km / s`. Deliberate (ponytail: fixed short list).

**Acceptance criteria.**

- [ ] `glue_solar.setup()` twice leaves one `image:blink` in `ImageViewer.tools`, `unit_converter.members['default'] is IRISUnitConverter`, `settings.UNIT_CONVERTER == 'default'`, the profile style dict keyed on `QThreadedProfileLayerArtist` and `LineListArtist`.
- [ ] Profile viewer on a real raster window: x unit choices `['Angstrom', 'nm', 'km / s']` (native first), `km / s` values equal `doppler_optical(rest)`, `XRangeROI` in `km / s` yields the correct native subset range, `x_axislabel == 'Wavelength'`.
- [ ] A window without `TWAVE` offers no `km / s`; a 4-D stack offers `km / s`; "Set rest wavelength…" shifts the axis and 0 removes the override.
- [ ] Image viewer: `image:blink` in the toolbar with an interval spinbox; activation cycles exactly the enabled, visible data layers, leaves hidden layers and subsets alone, restores visibility on deactivation, stops on viewer close.
- [ ] "Plugins -> IRIS: add line list" adds `IRIS lines` (11 rows); in a profile viewer it draws 11 lines + 11 labels that move with `Angstrom`/`nm`/`km / s`, hide with the layer checkbox, take colour/linewidth from the style editor, vanish on a non-wavelength x axis and on `remove_data`.
- [ ] Line-list layer survives `save_session`/`restore_session` with synthetic data (no saver code).
- [ ] `~/.glue/settings.cfg` untouched by the test suite (`settings._save_to_disk = False` autouse).
- [ ] `iris_lines.csv` is git-tracked and present in the built wheel (`python -m build` then `unzip -l dist/*.whl | grep iris_lines`).
- [ ] Docs and changelog updated; existing tests still pass (`.venv/bin/python -m pytest glue_solar` with `QT_QPA_PLATFORM=offscreen`); ruff clean. Neither `ruff` nor `pre-commit` is installed in `.venv` or on PATH (checker, 2026-09-02), so run `pipx run ruff check --config .ruff.toml glue_solar` (or `pre-commit run --all-files`, hook `ruff-check` in `.pre-commit-config.yaml:3-6`); import order must follow `.ruff.toml` `I` rules (stdlib; third party; `glue_solar` last), which is what `loaders/iris.py` does.

**Dropped / out of scope.**

- Velocity on image-viewer axes: image axes have no display units (`image/state.py:500` is colour levels only); it would be a WCS-level spectral wrapper, a different feature.
- A saver or drop-on-save for the line-list layer: stock savers already round-trip it (verified).
- Upstream glue-core guards at `profile/state.py:266/:292/:308`: unnecessary once the state subclasses `ProfileLayerState`.
- A generic annotation layer in glue-qt and upstreaming blink: no demonstrated demand beyond IRIS; revisit on request.
- jdaviz-style click-to-advance blink variant: YAGNI.
- Registering the converter under a new name / a lenient `check_unit_converter` upstream: avoided by the `members['default']` override; the upstream validator PR is optional and not part of this WP.
- Full astropy prefixed unit lists: pruned on purpose.
- Extra lines (Fe XII 1349.40, C I 1354.29/1355.84, S IV 1404.85/1406.01, Ni II, Fe II): trivial CSV additions later; v1 ships the 11 requested lines.
- Editing the line list in the GUI, per-line label offsets, blink keyboard shortcut: not requested.

**Docs.**

- `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst`: new section after "Using Glue's 1D Profile viewer to plot the spectrum and scan evolution" (`:59`, last section of the file) titled "Velocity axis and line identifications": "With ``Wavelength`` on the x axis, the x display unit combo offers ``Angstrom``, ``nm`` and ``km / s``. Velocities use the window's ``TWAVE`` reference wavelength as the rest wavelength; right-click the dataset and choose "Set rest wavelength…" to use a laboratory value instead (for Mg II k, 2796.35 Å instead of 2796.20 Å shifts the zero point by 16 km/s). Subsets drawn in ``km / s`` are stored in wavelength. "Plugins -> IRIS: add line list" adds an ``IRIS lines`` table; drag it onto a Profile viewer that already shows a spectrum to draw labelled vertical lines at C II, Cl I, Fe XXI, O I, Si IV, O IV and Mg II h/k; they follow the display unit, and colour and width are set in the layer's style editor. The list is ``glue_solar/iris_lines.csv``; any CSV with ``wavelength`` (Angstrom) and ``name`` columns works the same way."
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: after "Opening a single file" (`:48-53`, before "Linking" `:54`) add "Blinking image layers": "With two linked image layers in one Image Viewer (for example two SJI channels or an SJI and an AIA cutout), the "Blink layers" toolbar button shows them one at a time in turn; the spinbox next to it sets the interval in milliseconds. Blending is the existing per-layer opacity slider and the "One color per layer" colour mode." Keep "Saving sessions" (`loading-iris-level-2-raster-and-sji-data.rst:61`) as is until WP3; WP3 adds that line-list layers restore.
- `changelog/<PR>.feature.rst`: "The 1D Profile viewer can show IRIS spectra on a velocity axis: choose ``km / s`` as the x display unit (rest wavelength from the window's ``TWAVE`` card, or set it per dataset with the right-click action "Set rest wavelength…"); wavelength unit choices are reduced to ``Angstrom``, ``nm`` and ``km / s``. "Plugins -> IRIS: add line list" adds a table of IRIS emission lines that the Profile viewer draws as labelled vertical lines following the display unit. The Image Viewer gains a "Blink layers" tool with an adjustable interval."
- `IRIS_GLUE_GAP_PLAN.md`: table row "Wavelength/velocity + line IDs" home -> glue-solar, "velocity display units + line-list layer via public registries"; row "SJI inspection" -> "blink tool in glue-solar; mix already exists (alpha + one colour per layer)"; §3.3 and §3.4 rewrite: home is glue-solar, glue-core/glue-qt need at most the two optional one-liners; §3.5 "blend with adjustable ratio already exists; only timed blink was missing"; move 3.3-3.5 from "on demonstrated demand" into Phase 1; guiding principle 3 becomes "upstream later, not a gate".
- `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`: row "Wavelength/velocity and line IDs" -> Covered (profile viewer; image axes remain wavelength); row "SJI inspection" difference text drop "blink/mix".


---

# WP6 - Gaussian fit maps (single and double Gaussian, per pixel)

2026-09-05 correction: the map's outer coordinate object must be `_GlueWCS`,
wrapping a slice of the raw source WCS. The code below and both runnable
fitting prototypes now follow that contract; the new integration regression
verifies WP3 save/load. Historical outputs below predate this correction.

**Goal.** Right-click an IRIS raster dataset, choose "1 Gaussian" or "2 Gaussians", and get a new 2D dataset of
fitted background / amplitude / centroid / width maps on the raster's spatial grid (pixel-linked to the source), plus a
data-minus-model residual cube attached to the source dataset. All math is `astropy.modeling.fitting.parallel_fit_dask`;
glue-solar adds 177 lines (seeding, Data construction, Worker, dialog) and 162 lines of tests, both pasted verbatim below.

> Checker pass (2026-09-02, later session): every file:line reference re-opened, every script re-run (outputs below are
> the checker's re-runs unless marked "writer"). One code defect found and fixed in the module: the `QProgressDialog`
> was garbage collected on return from `start_fit`, so the user never saw it. The test module now guards that. The
> full step 1-6 path was executed in a throwaway worktree (`scratchpad/wt-wp6chk`, removed afterwards): 35 passed,
> ruff clean. No repository or `~/.glue` change (`settings.cfg` mtime still 08:36).

## Current state (2026-09-02)

- glue-solar `iris-observation-browser` (d3a2bd3, = PR #44): no fitting, no moments, no `layer_action` anywhere.
  `grep -rn "parallel_fit\|Gaussian\|layer_action\|QThread" glue_solar docs` is empty; the only UI hooks are
  `@data_factory` and `@menubar_plugin` in `glue_solar/sources/iris.py:22,30`. Progress feedback today is
  `get_qapp().processEvents()` loops (`glue_solar/sources/loaders/iris.py:277,291`), which cannot interleave with one
  blocking `dask.compute()`.
- The loader already puts everything the fit needs on the `Data`: array (`data[cid]`), unit string
  (`Component.units`, e.g. `'DN_IRIS_FUV'`), a sliceable APE-14 WCS (`data.coords` is `_GlueWCS(BaseWCSWrapper)`,
  `glue_solar/sources/loaders/iris.py:35-69`), the per-exposure `Time` component (`:81-84`). Wavelength is world axis
  0 in WCS order (`world_axis_physical_types[0] == 'em.wl'`) and the LAST numpy axis of the array. No cube handle needed
  (audit P2.2 + verifier, re-verified today).
- Today `data.coords.world_axis_units == ('m', 'arcsec', 'arcsec')`. WP1 (D3) changes the first entry to `'Angstrom'`.
  The code below converts through `u.Unit(coords.world_axis_units[0]).to_value(u.AA)`, so it is correct before and after
  WP1 (verified with both a metre WCS and an Angstrom WCS today).
- `astropy.modeling.fitting.parallel_fit_dask` exists in installed astropy 8.0.1 (added in astropy 7.0.0: PR #16696,
  milestone v7.0.0, merged 2024-09-03, re-checked with `gh api repos/astropy/astropy/pulls/16696` today; the auditor's
  "7.1.0" was wrong, verifier correction). irispy 0.8.1 pins `astropy>=7.2.0` and `dask[array]>=2024.7.0`
  (irispy `pyproject.toml:35-36`); no extra.
- `glue_qt.utils.threading.Worker` (QThread with `result` / `error` signals, 45 lines) is on glue-qt main and on the
  installed editable `macos-integration` checkout (bd4dce6b, 2026-08-30; file last changed d65c3fe9, 2023-08-11). The
  Profile viewer's fit button (`glue_qt/viewers/profile/profile_tools.py:210-231`: `on_fail`/`on_done` slots,
  `Worker(self._fit, ...)` at :222, `self._fit_worker = w` at :227, `wait_for_fit` at :230-231) is the template.
- The fit emits no warnings: `pytest.ini:26-28` has `filterwarnings = error`, and `gaussian_fit_data` for n=1 and n=2
  ran clean under `python -W error` today (the AstropyDeprecationWarning about LMLSQFitter with bounds only appears in
  the verifier's `bench.py`, which sets explicit bounds; the module sets none).
- Historical 2026-09-02 saves failed on both the source and maps. The claim that WP3 alone covered a bare
  `SlicedLowLevelWCS` was wrong. On 2026-09-05 WP6 was corrected to put `_GlueWCS` OUTSIDE a slice of the raw WCS;
  the WP3/WP6 regression now checks component values/units, metadata and world/pixel coordinates after reload.
- `glue_qt.config.layer_action` is `glue.config.layer_action` (same object, verified). `UserAction._do_action`
  (`glue_qt/app/layer_tree_widget.py:481-486`) calls `callback(layer, data_collection)` for `single=True`. No app or
  session handle reaches the callback (critic §2), hence D4.
- irispy ships no fitting helper (gallery only: `examples/analysis/01_spectral_fitting.py`,
  `07_mg_ii_two_gaussian_fitting.py`; the only v0.8.1 -> main difference is the 20-line percentile-seeding block in 01).
  `irispy.utils.utils.gaussian1d_on_linear_bg` has sqrt(2)*sigma width semantics and no callers: do not use it.
- Real full-window data is on this machine and was used for verification today:
  `/Users/nabil/DATA/IRIS/561757a1b84e36def2ed9e2d89103117-iris_l2_20180102_153155_3610108077_raster/` (the exact
  gallery raster: 320 steps x 548 slit px, Si IV 1403 337 px, Mg II k 380 px, 175,360 spectra per window).

## Decisions already made

- D2: ships entirely in glue-solar through `glue_qt.config.layer_action`; nothing upstream.
- D3: wavelength values in Angstrom everywhere (seeds, centroid/width maps, dialog field). `SIGMA_SEED = {1: 0.05,
  2: 0.08}` A and `SPLIT_SEED = 0.15` A are the gallery's 0.005 nm / 0.008 nm / (279.650 - 279.621)/2 nm.
- D4 mirrored: `@layer_action("IRIS: Gaussian fit maps…", single=True, data=True)`; the result Data is appended to
  the data collection with two pixel `LinkSame` links; no viewer is opened.
- Seed = data driven, not the rest wavelength (verifier correction to P2.2, confirmed on the gallery raster today):
  n=1 seeds at the argmax of the spatially averaged spectrum; n=2 seeds at its two highest interior local maxima
  (k2v, k2r). `rest` stays an optional keyword (task signature): when given and inside the window it is the seed centre
  (n=1) or centre -/+ 0.15 A (n=2, gallery 07 recipe). Background seed = 10th percentile of the mean spectrum.
- No TRF prefit on the mean spectrum (gallery step). Verified today (writer and checker runs of `verify/bench.py`):
  with the argmax seed it degenerates on the bundled sns raster (Const -6.6e5 + Gaussian 6.6e5, stddev 2.3 nm) and
  makes the per-pixel fit 1.8-1.9x slower (11.09 s / 11.70 s vs 6.25 s / 6.29 s) for no NaN gain.
- No TWAVE prefill of the centre field. TWAVE is the window's nominal wavelength (Mg II k: 2796.20 A, core 2796.35 A);
  seeding n=2 from TWAVE -/+ 0.15 agreed with the gallery reference on only 79.1% of pixels vs 99.9% for the local-maxima
  seed, and was 1.7x slower.
- Plain floats, no `data_unit`: `'DN_IRIS_FUV'` does not parse with `u.Unit` unless irispy's unit is enabled; units are
  free anyway (audit unit_cost.py). Units are re-attached as component unit strings.
- `scheduler='processes'` inside `Worker`; `'single-threaded'` in tests. `threads` gives nothing (GIL; 6.23 s vs 6.25 s).
- Residual cube is added as a component on the SOURCE dataset (same shape, zero links, shows next to the data in a
  Profile viewer). Only the 2D parameter maps become a new Data.
- The maps use `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`. Unwrap a source `_GlueWCS` before slicing,
  then rewrap once; this preserves display units/names and makes WP3's existing saver reachable without a new registry entry.
- Generic in `ndim`: `fitting_axes = ndim - 1`, `ndim - 1` links, `(ndim - 1)`-D maps. The optional 4D stack works
  unchanged (verified: maps (13, 8, 109) with world axes Scan / lon / lat, 3 links). No special casing.
- Model choice is a modal form (Model combo + optional "Line centre (A)"), then a modeless indeterminate
  `QProgressDialog` without cancel (parallel_fit_dask has no cancel or progress hook).
- Not in v1 (see Dropped): fit-window half width, velocity / net-flux derived maps, diagnostics files, weights/mask.

## Dependencies / order

- Independent of WP1 (unit conversion is explicit), of the glue fork branches, of glue-qt #68, and of WP2's code.
  Land after WP2 only for a consistent right-click menu ("IRIS: line moments…" then "IRIS: Gaussian fit maps…").
  WP2's `MomentsDialog` (`briefs/wp2-moments.md`, a `QDialog` subclass with rest / wings / min-intensity / saturation /
  integrated fields) has different fields from this one; keep the 20-line `_ask` below, do not share a dialog class.
  The only things to copy from WP2 are conventions: the `…` character in the label, the `test_plugin.py` registration
  assertion, and a new user-guide page plus toctree entry (WP2 adds `line-moments-of-a-raster-window.rst`, not a section).
- Requires the PR #44 branch (`raster_data`, `_GlueWCS`, `Time` component). Nothing else.
- Sessions require WP3 AND the corrected wrapper order in this brief. WP3 serializes `_GlueWCS` and recurses
  through its inner raw sliced WCS; it does not register a saver for arbitrary outer sliced objects.
  This WP adds no saver. Production sessions remain unsupported until the planned work actually lands.
- Unblocks: WP3.3 velocity display units get a `centroid` map in Angstrom plus `meta['rest_wavelength_angstrom']`.

## Files to touch

- `glue_solar/sources/fitting.py` (new, the module under "Verified code"): `wavelength_angstrom`, `fit_gaussians`,
  `gaussian_fit_data`, `add_fit_products`, `_ask`, `start_fit`, `fit_gaussians_action`.
- `glue_solar/__init__.py:5,9`: `from glue_solar.sources import fitting, iris, maps` and add `"fitting"` to `__all__`
  (the module registers the layer action at import time; `glue_solar/sources/__init__.py` is empty).
- `glue_solar/tests/test_fitting.py` (new, pasted verbatim under "Verified code / Test module").
- `glue_solar/tests/test_plugin.py:1,11`: import `layer_action` next to `data_factory, menubar_plugin` and add
  `assert "IRIS: Gaussian fit maps…" in [item.label for item in layer_action]` after the `menubar_plugin` assertion
  in `test_setup_registers_hooks` (same pattern WP2 uses; verified today, ruff clean, 4 passed).
- `docs/api_reference.rst`: add `.. automodapi:: glue_solar.sources.fitting` with `:no-inheritance-diagram:` after
  the `glue_solar.sources.iris` block (the file has three blocks today: `sources.iris`, `sources.maps`,
  `sources.loaders.scan`).
- `docs/user_guide/gaussian-fit-maps-of-a-raster-window.rst` (NEW page, text under "Docs") and
  `docs/user_guide/index.rst` toctree: add the new page after `line-moments-of-a-raster-window` (WP2) or, if WP2 is
  not merged, after `guide-to-glue-1dprofile-viewer-for-iris-data` (the toctree has three entries today).
- `changelog/<PR>.feature.rst` (under "Docs"; existing fragments are `42.breaking.rst`, `42.bugfix.rst`,
  `44.bugfix.rst`, `44.feature.rst`; naming per `changelog/README.rst`).
- No `pyproject.toml` change (no new dependency; dask arrives with irispy-lmsal, astropy>=7.2 via irispy).

## Step-by-step

1. Branch from `iris-observation-browser` (after WP2 if it is merged first).
2. Create `glue_solar/sources/fitting.py` with the module below verbatim (177 lines; ruff-clean under `.ruff.toml`).
3. Edit `glue_solar/__init__.py`: line 5 becomes `from glue_solar.sources import fitting, iris, maps`; line 9 becomes
   `__all__ = ["setup", "__version__", "fitting", "iris", "maps"]`. Check: `python -c "import glue_solar; from
   glue_qt.config import layer_action; print([a.label for a in layer_action])"` prints `['IRIS: Gaussian fit maps…']`
   (plus WP2's label if merged).
4. Create `glue_solar/tests/test_fitting.py` with the test module below verbatim (162 lines, already ruff-sorted:
   `glue_solar.sources.fitting` imports come BEFORE `glue_solar.sources.loaders.iris`, one name per line).
   Edit `glue_solar/tests/test_plugin.py` as listed under "Files to touch".
5. Run `HOME=<scratch> QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python -m pytest glue_solar -q -o addopts=''`
   (pytest.ini's `--doctest-rst` needs pytest-doctestplus, missing in this venv; `filterwarnings = error` stays
   active). Expect `35 passed, 2 warnings` in 2.5-3.5 s (checker: 35 passed in 2.46 s / 3.55 s under load).
6. Run `<scratchpad>/ruffpkg/bin/ruff check --config .ruff.toml glue_solar` (expect `All checks passed!`; ruff
   0.16.5, pre-commit pins ruff-check v0.16.1 with `--fix`) and `ruff format --check --config .ruff.toml
   glue_solar/sources/fitting.py glue_solar/tests/test_fitting.py glue_solar/__init__.py glue_solar/tests/test_plugin.py`
   (expect `4 files already formatted`). Do NOT run `ruff format` on the whole package: `glue_solar/conftest.py`,
   `glue_solar/sources/loaders/maps.py` and `glue_solar/sources/maps.py` are not format-clean on the branch today
   and pre-commit has no `ruff-format` hook; reformatting them is unrelated noise.
7. Manual check in the GUI (the only unautomated step; everything below it was driven offscreen today, see
   "Offscreen end-to-end"): `HOME=<scratch> glue`, Plugins -> IRIS: browse observations…, load one raster window
   (a real one, e.g. the gallery raster above), right-click the dataset in the data collection ->
   "IRIS: Gaussian fit maps…" -> OK. A "Gaussian fit" busy dialog stays up and the window stays responsive; after
   ~25 s (full 320x548 raster, 12 cores) `<label>-gauss1` appears with `background / amplitude / centroid / width /
   Time` and the source gains `<label>-gauss1 residual`. Drag the maps onto a 2D Image viewer; draw a subset on it and
   check it propagates to the raster (and its residual) in a Profile viewer. Right-click an SJI dataset: a warning
   "… is not an IRIS spectrogram (no wavelength axis)". The action is absent for subsets and multi-selection
   (`single=True, data=True`).
8. Docs + changelog (under "Docs"). Open the PR; CI (`tox.ini:51-59`) runs `pytest -vvv -r fEs --pyargs glue_solar
   --cov ... docs` with `pytest.ini` addopts, i.e. the same tests plus `--doctest-rst`.

## Verified code

All commands were run today from `/Users/nabil/Git/glue-solar` with
`HOME=/private/tmp/claude-501/.../scratchpad/home-wp6 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python`
(installed irispy 0.8.1, glue-core 1.27.0, astropy 8.0.1, dask 2026.8.0, 12 CPUs). Scripts live in the scratchpad:
`wp6_fitting.py` (module, patched by the checker with the `worker.progress` line), `wp6_test_fitting.py` (writer's
tests with a scratch import), `wp6_check_synth.py`, `wp6_check_real.py` (BROKEN after a late edit: `"rest (TWAVE)
A:"(d)` raises TypeError; the checker's repaired copy is `wp6_chk_real_fixed.py`), `wp6_seed_double.py`,
`wp6_check_gallery.py`, `wp6_full_raster.py` (+ `.log`), `wp6_check_qt.py`, `wp6_check_dialog.py`. Checker additions:
`wp6_fitting_brief.py` (the module exactly as pasted here; `diff` against the brief text is empty),
`wp6_test_fitting_final.py` (the test module exactly as pasted here; same check), `wp6_chk_e2e.py`,
`wp6_chk_progress.py`, `wp6_chk_slow.log` (bench + gallery + full raster), `wp6_chk_real_fixed.log`. The throwaway
worktree `wt-wp6chk` (branch HEAD d3a2bd3 plus the new/changed files) was removed after the run; the two `_brief` /
`_final` files above are the copies that ran there.

### The module (`glue_solar/sources/fitting.py`)

```python
"""Per-pixel Gaussian fit maps of IRIS raster windows (single or double Gaussian plus constant background)."""

import traceback

import numpy as np
from glue.core.component import Component
from glue.core.data import Data
from glue.core.link_helpers import LinkSame
from glue_qt.config import layer_action
from glue_qt.utils.threading import Worker
from qtpy import QtWidgets

import astropy.units as u
from astropy.modeling import models
from astropy.modeling.fitting import LMLSQFitter, parallel_fit_dask
from astropy.wcs.wcsapi import SlicedLowLevelWCS
from glue_solar.sources.loaders.iris import _GlueWCS

__all__ = ["fit_gaussians", "gaussian_fit_data", "start_fit", "wavelength_angstrom"]

SIGMA_SEED = {1: 0.05, 2: 0.08}  # Angstrom; irispy gallery 01 (0.005 nm) and 07 (0.008 nm)
SPLIT_SEED = 0.15  # Angstrom; half the k2v/k2r seed separation of gallery 07 (279.621 / 279.650 nm)
_WORKERS = []  # keep running fits alive (a Worker that is garbage collected mid-run crashes Qt)


def wavelength_angstrom(data):
    """Wavelength of every spectral pixel (the last pixel axis of a glue-solar raster dataset) in Angstrom."""
    coords = data.coords
    if getattr(coords, "world_axis_physical_types", [None])[0] != "em.wl":
        raise ValueError(f"{data.label} is not an IRIS spectrogram (no wavelength axis)")
    # pixel_to_world_values takes pixel axes in Cartesian order: the wavelength index goes FIRST
    wavelength = coords.pixel_to_world_values(np.arange(data.shape[-1]), *([0] * (data.ndim - 1)))[0]
    return (np.asarray(wavelength, dtype=float) * u.Unit(coords.world_axis_units[0])).to_value(u.AA)


def fit_gaussians(cube, wavelength, n_gaussians=1, rest=None, scheduler="processes"):
    """
    Fit a constant background plus ``n_gaussians`` Gaussians to every spectrum of ``cube``.

    Parameters
    ----------
    cube : array-like
        Spectra along the last axis; NaN and negative values are set to zero (irispy gallery recipe).
    wavelength : array-like
        Wavelength of each spectral pixel in Angstrom.
    n_gaussians : {1, 2}
    rest : float, optional
        Line centre in Angstrom. When given and inside the window it seeds the Gaussian (``n_gaussians=1``) or the
        pair at ``rest -/+ 0.15`` A (``n_gaussians=2``); otherwise the strongest peak(s) of the spatially averaged
        spectrum seed the fit.
    scheduler : str
        dask scheduler. ``"processes"`` for real rasters; ``"single-threaded"`` in tests.

    Returns
    -------
    fit : compound astropy model
        Parameters ``amplitude_0`` (background), ``amplitude_i``, ``mean_i``, ``stddev_i`` for
        ``i`` in 1..n are arrays of shape ``cube.shape[:-1]``, NaN where the fit failed.
    residual : `numpy.ndarray`
        ``cube - fit``, same shape as ``cube``.
    """
    cube = np.nan_to_num(np.asarray(cube, dtype=float).clip(min=0))
    wavelength = np.asarray(wavelength, dtype=float)
    mean = cube.mean(axis=tuple(range(cube.ndim - 1)))
    background = np.percentile(mean, 10)
    if rest is not None and wavelength.min() < rest < wavelength.max():
        centres = [rest] if n_gaussians == 1 else [rest - SPLIT_SEED, rest + SPLIT_SEED]  # gallery 07 recipe
    elif n_gaussians == 1:
        centres = [wavelength[mean.argmax()]]
    else:  # the two highest interior local maxima of the mean spectrum (k2v, k2r), blue first
        peaks = np.flatnonzero((mean[1:-1] > mean[:-2]) & (mean[1:-1] >= mean[2:])) + 1
        peaks = np.sort(peaks[np.argsort(mean[peaks])[-2:]])
        centres = (
            wavelength[peaks] if len(peaks) == 2 else wavelength[mean.argmax()] + np.array([-SPLIT_SEED, SPLIT_SEED])
        )
    model = models.Const1D(amplitude=background)
    for centre in centres:
        model += models.Gaussian1D(amplitude=mean.max() - background, mean=centre, stddev=SIGMA_SEED[n_gaussians])
    # ponytail: no TRF prefit on the mean spectrum (gallery step); it degenerates on cropped windows
    # and made the per-pixel fit 1.8x slower on the bundled sns raster with no NaN gain.
    fit = parallel_fit_dask(
        data=cube,
        fitting_axes=cube.ndim - 1,
        world=(wavelength,),
        model=model,
        fitter=LMLSQFitter(),
        scheduler=scheduler,
    )
    model_cube = fit(wavelength.reshape((-1,) + (1,) * (cube.ndim - 1)))  # (nwl, *spatial)
    return fit, cube - np.moveaxis(model_cube, 0, -1)


def gaussian_fit_data(data, n_gaussians=1, rest=None, scheduler="processes"):
    """
    Fit the raster dataset ``data`` and return ``(maps, residual)``.

    ``maps`` is a new dataset on the spatial pixel grid of ``data`` (its WCS with the wavelength axis
    sliced away) with one component per fitted parameter; ``residual`` is the data-minus-model cube.
    """
    cid = data.main_components[0]
    units = data.get_component(cid).units
    fit, residual = fit_gaussians(data[cid], wavelength_angstrom(data), n_gaussians, rest, scheduler)
    maps = Data(label=f"{data.label}-gauss{n_gaussians}")
    raw_wcs = data.coords._wcs if isinstance(data.coords, _GlueWCS) else data.coords
    maps.coords = _GlueWCS(SlicedLowLevelWCS(raw_wcs, (slice(None),) * (data.ndim - 1) + (0,)))
    maps.meta = {"source": data.label, "n_gaussians": n_gaussians, "rest_wavelength_angstrom": rest}
    maps.add_component(Component(fit.amplitude_0.value, units=units), "background")
    for i in range(1, n_gaussians + 1):
        suffix = f" {i}" if n_gaussians > 1 else ""
        maps.add_component(Component(getattr(fit, f"amplitude_{i}").value, units=units), f"amplitude{suffix}")
        maps.add_component(Component(getattr(fit, f"mean_{i}").value, units="Angstrom"), f"centroid{suffix}")
        maps.add_component(Component(getattr(fit, f"stddev_{i}").value, units="Angstrom"), f"width{suffix}")
    if data.find_component_id("Time") is not None:  # per-exposure time of each spatial pixel (sit-and-stare: axis 0)
        maps.add_component(data["Time"][..., 0], "Time")
    return maps, residual


def add_fit_products(data, data_collection, maps, residual):
    """Add ``maps`` to the collection, pixel-link it to ``data`` and attach the residual cube to ``data``."""
    data_collection.append(maps)
    for source_pixel, map_pixel in zip(data.pixel_component_ids, maps.pixel_component_ids):  # drops wavelength
        data_collection.add_link(LinkSame(source_pixel, map_pixel))
    units = data.get_component(data.main_components[0]).units
    data.add_component(Component(residual, units=units), f"{maps.label} residual")


def _ask(data):
    """Model choice and optional line centre; returns ``(n_gaussians, rest)`` or None when cancelled."""
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle(f"Gaussian fit of {data.label}")
    form = QtWidgets.QFormLayout(dialog)
    model = QtWidgets.QComboBox()
    model.addItems(["1 Gaussian + background", "2 Gaussians + background (Mg II k2v/k2r)"])
    form.addRow("Model", model)
    # no prefill (TWAVE is the window's nominal wavelength, not the line core; seeding from it was worse
    # than the data-driven seed on the gallery raster): blank means seed from the mean spectrum
    centre = QtWidgets.QLineEdit()
    centre.setPlaceholderText("blank: strongest peak(s) of the mean spectrum")
    form.addRow("Line centre (Å)", centre)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() != QtWidgets.QDialog.Accepted:
        return None
    text = centre.text().strip()
    return model.currentIndex() + 1, float(text) if text else None


def start_fit(data, data_collection, n_gaussians=1, rest=None, scheduler="processes"):
    """Run the fit in a background thread; the products are added when it finishes. Returns the Worker."""
    progress = QtWidgets.QProgressDialog(f"Fitting {n_gaussians} Gaussian(s) to {data.label}…", None, 0, 0)
    progress.setWindowTitle("Gaussian fit")
    progress.show()
    worker = Worker(gaussian_fit_data, data, n_gaussians, rest, scheduler)
    worker.progress = progress  # the parentless dialog is Python-owned: without a reference it is deleted on return
    worker.result.connect(lambda result: add_fit_products(data, data_collection, *result))
    worker.error.connect(
        lambda info: QtWidgets.QMessageBox.critical(
            None, "Gaussian fit failed", "".join(traceback.format_exception(*info))
        )
    )
    worker.finished.connect(progress.close)
    worker.finished.connect(lambda: _WORKERS.remove(worker))
    _WORKERS.append(worker)
    worker.start()
    return worker


@layer_action("IRIS: Gaussian fit maps…", single=True, data=True)
def fit_gaussians_action(data, data_collection):
    """Right-click action on a raster dataset: fit every spectrum and add the parameter maps."""
    try:
        wavelength_angstrom(data)
    except ValueError as error:
        QtWidgets.QMessageBox.warning(None, "Gaussian fit", str(error))
        return
    choice = _ask(data)
    if choice is not None:
        start_fit(data, data_collection, *choice)
```

Ponytail ceilings not marked in the code: (1) `np.asarray(cube, dtype=float)` plus the model cube plus the residual
are three float64 copies of the window (3 x 473 MB for the 320x548x337 gallery window, ~1.7 GB peak with the float32
source); cast the residual to float32 if memory bites. (2) `_WORKERS` is a module-level list; one fit per click, no
queueing, no cancel (parallel_fit_dask has none). (3) `float(text)` in `_ask` raises on junk input; let it (glue shows
the traceback), or add a `QDoubleValidator` later.

Lint (checker, in the worktree with the files at their real paths):

```
$ ruffpkg/bin/ruff check --config .ruff.toml glue_solar
All checks passed!
$ ruffpkg/bin/ruff format --check --config .ruff.toml glue_solar/sources/fitting.py glue_solar/tests/test_fitting.py glue_solar/__init__.py glue_solar/tests/test_plugin.py
4 files already formatted
$ ruffpkg/bin/ruff format --check --config .ruff.toml glue_solar
3 files would be reformatted, 13 files already formatted   # conftest.py, loaders/maps.py, sources/maps.py: pre-existing
```

(The writer's scratch copy `wp6_test_fitting.py` reports I001 because its `from wp6_fitting import ...` line is not
first-party there; with the real import path ruff wants the `glue_solar.sources.fitting` block before
`glue_solar.sources.loaders.iris`, one name per line. The test module below is already in that form.)

### Synthetic recovery, Data path, links, wrong-order trap (`wp6_check_synth.py`)

```
$ python wp6_check_synth.py
n=1: cube (6, 5, 40) nan=0 worst rel err=7.61e-07 residual rms=1.35e-06
n=2: cube (6, 5, 40) nan=0 worst rel err=6.67e-07 residual rms=3.81e-06
world_axis_units ('m', 'arcsec', 'arcsec') physical ['em.wl', 'custom:pos.helioprojective.lat', 'custom:pos.helioprojective.lon']
wrong-order wavelength: unique values = 1 -> [1.402e-07]
maps synthetic-gauss1 (6, 5) ['background', 'amplitude', 'centroid', 'width'] ['DN_IRIS_FUV', 'DN_IRIS_FUV', 'Angstrom', 'Angstrom']
maps world ['Helioprojective Longitude', 'Helioprojective Latitude'] ['arcsec', 'arcsec']
maps lon/lat at (2,3): [0.99, 0.70] source: (0.99, 0.70)
dc ['synthetic', 'synthetic-gauss1'] links 12 source components ['synthetic', 'synthetic-gauss1 residual']
ROI on maps 6 px -> source 240 px (= 6 x 40 = 240)
SYNTH OK
```

(The synthetic Data uses an astropy `WCS(naxis=3)` with `ctype = ['WAVE', 'HPLT-TAN', 'HPLN-TAN']`,
`cunit = ['Angstrom', 'arcsec', 'arcsec']` wrapped in `_GlueWCS`; the loader's real WCS reports metres today, and the
same helper handled both.)

### The wrong Cartesian order, on a real raster (from `wp6_check_real.py`)

```
sns Si IV: Si_IV_1403-3620258102-2021-09-05T00:18:33-scan-0 (187, 40, 29) units DN_IRIS_FUV world_axis_units ('m', 'arcsec', 'arcsec')
  wavelength A: [1398.62840387 1399.34072387] step 0.02544 rest (TWAVE) A: 1402.77 -> outside window, argmax seed used
  WRONG order (wavelength index last): unique = [1.3986284e-07]
```

`coords.pixel_to_world_values(np.arange(29), 0, 0)[0]` is the wavelength axis. `coords.pixel_to_world_values(0, 0,
np.arange(29))[0]` silently returns one constant (139.86 nm in metres) 29 times: the last pixel argument is the raster
step, not wavelength. No exception, no warning.

### Which double-Gaussian seed works (`wp6_seed_double.py`, synthetic two-peak profiles)

```
separation 0.3 A: argmax=1402.375 local maxima=[1402.375 1402.625]
  argmax -/+ 0.15 (no centre given)         seeds=[1402.225 1402.525] nan=0 resid rms=4.18e+00 mean_1 med=1402.370 mean_2 med=1402.620
  argmax, argmax + 0.3                      seeds=[1402.375 1402.675] nan=0 resid rms=2.76e-06
  two highest local maxima                  seeds=[1402.375 1402.625] nan=0 resid rms=3.80e-06
  user centre (between peaks) -/+ 0.15      seeds=[1402.375 1402.675] nan=0 resid rms=2.76e-06
separation 0.45 A: argmax=1402.325 local maxima=[1402.325 1402.725]
  argmax -/+ 0.15 (no centre given)         seeds=[1402.175 1402.475] nan=0 resid rms=4.31e+01 mean_1 med=1402.065 mean_2 med=1402.706
  two highest local maxima                  seeds=[1402.325 1402.725] nan=0 resid rms=2.02e-06
  user centre (between peaks) -/+ 0.15      seeds=[1402.4 1402.7]     nan=0 resid rms=3.64e-06
```

Straddling the argmax (the first-draft seed) converges to a wrong minimum without producing NaN. Hence the local-maxima
seed for n=2 and the `rest -/+ 0.15` path when a centre is given.

### Real full-window gallery raster, spatial sub-block of 8000 spectra (`wp6_check_gallery.py`, single-threaded)

```
Si IV 1403 block (40, 200, 337), window 1398.12-1406.67 A, TWAVE 1402.77 (inside), mean-spectrum argmax 1402.80
  n=1 rest=TWAVE, +/-1 A fit window (reference)    4.11 s (0.51 ms/spec, 79 px)  nan=1 resid rms=12.65 mean_1=1402.810
  n=1 argmax seed, whole 8.5 A window              4.78 s (0.60 ms/spec, 337 px) nan=1 resid rms=25.20 mean_1=1402.812
      95.9% of finite centroids within 0.05 A of reference
  n=1 rest=TWAVE seed, whole window                4.84 s (0.60 ms/spec, 337 px) nan=0 resid rms=25.40 mean_1=1402.810
      97.5% of finite centroids within 0.05 A of reference
  n=1 argmax seed, +/-1 A fit window               3.86 s (0.48 ms/spec, 79 px)  nan=0 resid rms=12.94 mean_1=1402.812
      96.5% of finite centroids within 0.05 A of reference
Mg II k block (40, 200, 380), window 2790.65-2809.95 A, TWAVE 2796.20, argmax 2796.21, two highest local maxima [2796.21 2796.51]
  n=2 gallery 07 (crop 2794-2798, fixed seeds, prefit)  4.11 s (0.51 ms/spec, 79 px)  nan=0 resid rms=28.62 mean_1=2796.216 mean_2=2796.513
  n=2 local-maxima seeds, whole 19 A window (k+h)       6.32 s (0.79 ms/spec, 380 px) nan=0 resid rms=135.79 mean_1=2796.220 mean_2=2796.508
      99.9% of finite centroids within 0.05 A of reference
  n=2 rest=TWAVE -/+0.15 seeds, whole window           10.69 s (1.34 ms/spec, 380 px) nan=0 resid rms=136.54 mean_1=2796.218 mean_2=2796.502
      79.1% of finite centroids within 0.05 A of reference
  n=2 local-maxima seeds, +/-2 A fit window             4.23 s (0.53 ms/spec, 79 px)  nan=0 resid rms=26.83
      100.0% of finite centroids within 0.05 A of reference
  n=2 rest=2796.35 -/+0.15 seeds, +/-2 A window         4.21 s (0.53 ms/spec, 79 px)  nan=0 resid rms=26.35
      100.0% of finite centroids within 0.05 A of reference
```

The whole-window residual rms (25 / 136) is the unmodelled O IV / Mg II h lines, not a bad fit of the target line.

### Full raster through the glue-solar path (`wp6_full_raster.py`, `raster_data` -> `gaussian_fit_data`)

```
$ python wp6_full_raster.py        # checker re-run; writer's numbers in brackets
Si IV 1403: Si_IV_1403-3610108077-2018-01-02T15:31:55-scan-0 (320, 548, 337) loaded in 0.1 s
  n=1 processes           24.6 s (0.14 ms/spec, 175360 spectra x 337 px) nan=27 (0.02%) centroid median=1402.800 A   [25.3 s]
  n=1 single-threaded    149.9 s (0.85 ms/spec, 175360 spectra x 337 px) nan=27 (0.02%) centroid median=1402.800 A   [152.6 s]
Mg II k 2796: Mg_II_k_2796-3610108077-2018-01-02T15:31:55-scan-0 (320, 548, 380) loaded in 0.2 s
  n=2 processes           26.2 s (0.15 ms/spec, 175360 spectra x 380 px) nan=15 (0.01%) centroid median=2796.205 A   [25.9 s]
real 202.96
```

`processes` is 6x faster than single-threaded on 12 cores once the raster is large enough to amortise the pool start-up
(~2 s). Budget ~0.9 ms/spectrum single-threaded, ~0.15 ms/spectrum with processes, for 340-380 px spectra.

### Bundled test rasters (`wp6_chk_real_fixed.py`, checker re-run; the fixtures the tests use)

```
$ python wp6_chk_real_fixed.py
sns Si IV: Si_IV_1403-3620258102-2021-09-05T00:18:33-scan-0 (187, 40, 29) units DN_IRIS_FUV world_axis_units ('m', 'arcsec', 'arcsec')
  wavelength A: [1398.62840387 1399.34072387] step 0.02544 rest (TWAVE) A: 1402.77 -> outside window, argmax seed used
  WRONG order (wavelength index last): unique = [1.3986284e-07]
  sns Si IV 1403 (187,40,29)   n=1 single-threaded   6.06 s (0.81 ms/spec) nan=5 centroid median=1399.035 A
  sns Si IV 1403 (187,40,29)   n=1 threads           6.16 s (0.82 ms/spec) nan=5
  sns Si IV 1403 (187,40,29)   n=1 processes         3.83 s (0.51 ms/spec) nan=5
  maps: ...-scan-0-gauss1 (187, 40) [('background','DN_IRIS_FUV'), ('amplitude','DN_IRIS_FUV'), ('centroid','Angstrom'), ('width','Angstrom'), ('Time','')]
  maps world: ['Helioprojective Longitude', 'Helioprojective Latitude'] ['arcsec', 'arcsec']
  residual (187, 40, 29) rms 21.7
  dc: [...-scan-0, ...-scan-0-gauss1] links: 12 source comps: [...-scan-0, '... mask', 'Time', '...-scan-0-gauss1 residual']
sns Mg II k: (187, 40, 52) rest A: 2796.20 window [2793.44 2794.74]
  sns Mg II k (187,40,52)      n=2 single-threaded   5.42 s (0.73 ms/spec) nan=5   (writer's run: 8.21 s)
  sns Mg II k (187,40,52)      n=2 processes         4.31 s (0.58 ms/spec) nan=5
  sns Mg II k (187,40,52)      n=1 single-threaded   3.40 s (0.45 ms/spec) nan=0
  2014 Si IV 1403 (8,109,29)   n=1 single-threaded   0.64 s (0.73 ms/spec) nan=1 centroid median=1399.061 A
  2014 Si IV 1403 (8,109,29)   n=1 processes         2.58 s (2.96 ms/spec) nan=1
  tiled x4 (748, 40, 29)       n=1 single-threaded  24.48 s (0.82 ms/spec)
  tiled x4 (748, 40, 29)       n=1 processes         6.43 s (0.21 ms/spec)
stack: C_II_1336-3860258481-2014-03-29T14:09:38-stack (13, 8, 109, 17) meta type dict rest: None
  stack fit 9.55 s maps (13, 8, 109) world ['Scan', 'Helioprojective Longitude', 'Helioprojective Latitude'] ['arcsec', 'arcsec', ''] nan=13
  stack links: 17
real 74.95
```

The centroids on the bundled files are unphysical (windows are cropped away from the line cores); they are fine for
shape / unit / NaN-fraction smoke tests only. The verifier's `verify/bench.py` re-run by the checker: argmax seed
6.29 / 6.38 / 4.22 s (single / threads / processes, nan=8), TRF-prefit seed 11.70 s with params
`[-6.63e5, 6.63e5, 139.898, 2.325]` (writer's run: 6.25 / 6.23 / 4.31 s and 11.09 s).

### Worker + QProgressDialog + `processes` keeps the event loop alive (`wp6_check_qt.py`)

```
layer_action registered: ['IRIS: Gaussian fit maps…'] single/data: [(True, True)]
workers alive: 1
elapsed 2.8s, GUI timer ticks while fitting: 55, workers alive after: 0
dc: ['synthetic', 'synthetic-gauss1'] links: 12 source comps: ['synthetic', 'synthetic-gauss1 residual']
sync idiom: ['synthetic', 'synthetic-gauss1', 'synthetic-gauss2'] links: 18
QT OK
```

(Checker re-run with the patched module; the writer saw 54 ticks.) A 50 ms QTimer ticked 55 times during a 2.8 s
`processes` fit started from `start_fit` (GUI responsive). The test idiom `worker.wait(); processEvents()` (here
`qtbot.waitUntil`) delivers the queued `result` slot on the main thread.

### The progress dialog must be kept alive (`wp6_chk_progress.py`, checker; the defect the checker fixed)

The writer's `start_fit` created `progress = QtWidgets.QProgressDialog(...)` as a local with no parent, connected
`worker.finished` to `progress.close` and returned. PyQt owns a parentless widget through its Python reference, and a
bound-method connection does not hold one, so the dialog was deleted on return: the timer-tick check above never
looked for it. Same script, module before and after the `worker.progress = progress` line:

```
brief start_fit (without the line): progress dialogs right after return: []
  visible ticks during the fit: 0; after finish: []
fixed start_fit (with the line):    progress dialogs right after return: [('Fitting 1 Gaussian(s) to synthetic…', True)]
  visible ticks during the fit: 46; after finish: [('Fitting 1 Gaussian(s) to synthetic…', False)]
AIA-like astropy WCS: ValueError: aia is not an IRIS spectrogram (no wavelength axis)
no coords: ValueError: table is not an IRIS spectrogram (no wavelength axis)
```

The module above already contains the line; `test_start_fit_adds_products_when_the_worker_finishes` asserts
`worker.progress.isVisible()` right after `start_fit` and `not ...isVisible()` after the collection grows. The last
two lines show the rejection path for a sunpy-map Data (astropy `WCS` with `HPLN-TAN/HPLT-TAN`) and for a
coordinate-less table.

### Offscreen end-to-end through the registered action (`wp6_chk_e2e.py`, checker)

`GlueApplication()` offscreen, synthetic (30, 20, 40) raster in `app.data_collection`, then exactly what
`UserAction._do_action` does: `action.callback(data, app.data_collection)` with a `QTimer.singleShot(0, press_ok)`
that presses OK in the modal `_ask` dialog (run with the writer's module, before the progress fix):

```
registry item: LayerAction ('label', 'tooltip', 'callback', 'icon', 'single', 'data', 'subset_group', 'subset') callback: fit_gaussians_action
dialog: Gaussian fit of synthetic | combo: 1 Gaussian + background
fit done in 4.2s; dc: ['synthetic', 'synthetic-gauss1']
ImageViewer x/y: Pixel Axis 1 [x] Pixel Axis 0 [y] | format_coord(3,2): 1" 1" (world)
ImageViewer axis labels: Helioprojective Latitude / Helioprojective Longitude
ProfileViewer layers: [('synthetic', 'synthetic-gauss1 residual'), ('synthetic', 'synthetic')] x_att: Helioprojective Longitude
subset on maps 12 px -> source 480 px (= 12 x 40)
SJI right-click -> ['SJI_1400-3620258102-2021-09-05T00:18:33 is not an IRIS spectrogram (no wavelength axis)'] | workers: 0 | dc: 2
```

`app.new_data_viewer(ImageViewer, data=maps)` renders the `SlicedLowLevelWCS` maps with world axis labels and a world
`format_coord`; a Profile viewer shows the residual component next to the data; a rectangle subset on the maps selects
`n * nwl` source pixels; the SJI path pops the warning (closed by a timer) and adds nothing. The script's final step,
`app.save_session(...)`, HUNG the process (the `GlueSerializeError` message box is modal and nobody closes it under
offscreen; killed after 4 min). Without the GUI: `GlueSerializer(dc).dumps()` -> `GlueSerializeError: Don't know how
to serialize <_GlueWCS>` for the source, and `<SlicedLowLevelWCS>` for a collection holding the maps only. WP3.

### Dialog under offscreen Qt and registry identity (`wp6_check_dialog.py`)

```
glue.config.layer_action is glue_qt.config.layer_action: True
_ask -> (2, 2796.35)
_ask cancelled -> None
```

### Unguarded `__main__` with `scheduler='processes'` (verifier's `verify/noguard.py`, re-run today)

```
concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly while the future was running or pending.
```

macOS spawn re-imports `__main__`; a script that fits at module level dies. The `glue` console script and pytest are
guarded, so the action is safe; standalone scripts and the tests must use `if __name__ == "__main__":` or
`'single-threaded'`.

### Test suite

```
$ pytest glue_solar -q -o addopts=''                       -> 27 passed, 2 warnings in 1.72s   (baseline, branch d3a2bd3, checker)
$ pytest wp6_test_fitting.py -p glue_solar.conftest -q -o addopts='' --durations=3     (writer's scratch copy, checker re-run)
0.69s call     wp6_test_fitting.py::test_real_raster_smoke
0.13s call     wp6_test_fitting.py::test_image_cubes_are_rejected
0.12s call     wp6_test_fitting.py::test_start_fit_adds_products_when_the_worker_finishes
8 passed in 1.02s
$ # steps 2-6 executed in the throwaway worktree scratchpad/wt-wp6chk (files at their real paths, real imports):
$ python -c "import glue_solar, glue_solar.sources.fitting as f; from glue_qt.config import layer_action; print([m.label for m in layer_action])"
['IRIS: Gaussian fit maps…']
$ python -m pytest glue_solar -q -o addopts='' --durations=3
0.68s call     glue_solar/tests/test_fitting.py::test_real_raster_smoke
0.47s call     glue_solar/tests/test_importer.py::test_real_rasters_stack_without_resampling_and_keep_scan_times
0.31s call     glue_solar/tests/test_importer.py::test_real_sji_adapter_preserves_mask_units_and_coordinates
35 passed, 2 warnings in 2.48s          (3.55 s in a second run while a benchmark used all cores)
```

### Test module (`glue_solar/tests/test_fitting.py`, verbatim, 162 lines; this exact text passed above)

```python
"""Tests for the per-pixel Gaussian fit action (glue_solar.sources.fitting)."""

import numpy as np
import pytest
from glue.core import DataCollection
from glue.core.component import Component
from glue.core.data import Data
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState

from astropy.wcs import WCS

from glue_solar.sources.fitting import (
    _WORKERS,
    add_fit_products,
    fit_gaussians,
    gaussian_fit_data,
    start_fit,
    wavelength_angstrom,
)
from glue_solar.sources.loaders.iris import _GlueWCS, image_data, raster_data

WAVELENGTH = 1402.0 + 0.025 * np.arange(40)  # one Angstrom of an IRIS FUV window


def gaussian(x, amplitude, mean, stddev):
    return amplitude * np.exp(-0.5 * ((x - mean) / stddev) ** 2)


def synthetic_cube(n_gaussians, shape=(6, 5)):
    """Spectra with smoothly varying parameters; returns (cube, {component name: truth map})."""
    x, y = np.meshgrid(np.linspace(0, 1, shape[0]), np.linspace(0, 1, shape[1]), indexing="ij")
    truth = {"background": 5 + 2 * x}
    if n_gaussians == 1:
        truth |= {"amplitude": 100 + 50 * x, "centroid": 1402.45 + 0.1 * y, "width": 0.06 + 0.02 * x}
    else:  # Mg II k like: two peaks either side of a central reversal
        truth |= {"amplitude 1": 100 + 50 * x, "centroid 1": 1402.35 + 0.04 * y, "width 1": 0.08 + 0.01 * x}
        truth |= {"amplitude 2": 70 + 20 * y, "centroid 2": 1402.65 - 0.04 * x, "width 2": 0.08 + 0.005 * y}
    cube = truth["background"][..., None] + np.zeros(WAVELENGTH.size)
    for i in range(1, n_gaussians + 1):
        suffix = f" {i}" if n_gaussians > 1 else ""
        cube = cube + gaussian(
            WAVELENGTH, *(truth[f"{name}{suffix}"][..., None] for name in ("amplitude", "centroid", "width"))
        )
    return cube, truth


@pytest.fixture
def synthetic_raster():
    """A glue-solar-like raster dataset: WAVE first in WCS order, helioprojective TAN axes, Angstrom."""
    cube, truth = synthetic_cube(1)
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]
    wcs.wcs.cunit = ["Angstrom", "arcsec", "arcsec"]
    wcs.wcs.crpix = [1, 1, 1]
    wcs.wcs.crval = [WAVELENGTH[0], 0, 0]
    wcs.wcs.cdelt = [WAVELENGTH[1] - WAVELENGTH[0], 0.33, 0.35]
    data = Data(label="synthetic")
    data.coords = _GlueWCS(wcs)
    data.add_component(Component(cube, units="DN_IRIS_FUV"), "synthetic")
    return data, truth


@pytest.mark.parametrize("n_gaussians", [1, 2])
def test_fit_gaussians_recovers_synthetic_parameters(n_gaussians):
    cube, truth = synthetic_cube(n_gaussians)
    fit, residual = fit_gaussians(cube, WAVELENGTH, n_gaussians, scheduler="single-threaded")
    np.testing.assert_allclose(fit.amplitude_0.value, truth["background"], rtol=1e-4)
    for i in range(1, n_gaussians + 1):
        suffix = f" {i}" if n_gaussians > 1 else ""
        np.testing.assert_allclose(getattr(fit, f"amplitude_{i}").value, truth[f"amplitude{suffix}"], rtol=1e-4)
        np.testing.assert_allclose(getattr(fit, f"mean_{i}").value, truth[f"centroid{suffix}"], rtol=1e-6)
        np.testing.assert_allclose(getattr(fit, f"stddev_{i}").value, truth[f"width{suffix}"], rtol=1e-4)
    assert residual.shape == cube.shape
    assert np.sqrt(np.mean(residual**2)) < 1e-3


def test_double_gaussian_seeds_at_the_given_centre():
    cube, truth = synthetic_cube(2)
    fit, _ = fit_gaussians(cube, WAVELENGTH, 2, rest=1402.5, scheduler="single-threaded")  # gallery 07 recipe
    np.testing.assert_allclose(fit.mean_1.value, truth["centroid 1"], rtol=1e-6)
    np.testing.assert_allclose(fit.mean_2.value, truth["centroid 2"], rtol=1e-6)


def test_wavelength_axis_is_read_in_cartesian_order(synthetic_raster):
    data, _ = synthetic_raster
    np.testing.assert_allclose(wavelength_angstrom(data), WAVELENGTH)
    wrong = data.coords.pixel_to_world_values(0, 0, np.arange(WAVELENGTH.size))[0]  # wavelength index passed last
    assert np.unique(np.asarray(wrong)).size == 1  # silently constant: the trap the helper avoids


def test_maps_share_the_spatial_grid_and_link_back(synthetic_raster):
    data, truth = synthetic_raster
    maps, residual = gaussian_fit_data(data, 1, scheduler="single-threaded")
    assert maps.label == "synthetic-gauss1"
    assert maps.shape == data.shape[:-1]
    assert [c.label for c in maps.main_components] == ["background", "amplitude", "centroid", "width"]
    assert [maps.get_component(c).units for c in maps.main_components] == [
        "DN_IRIS_FUV",
        "DN_IRIS_FUV",
        "Angstrom",
        "Angstrom",
    ]
    assert [c.label for c in maps.world_component_ids] == ["Helioprojective Longitude", "Helioprojective Latitude"]
    assert list(maps.coords.world_axis_units) == ["arcsec", "arcsec"]
    assert maps.coords.pixel_to_world_values(3, 2) == pytest.approx(data.coords.pixel_to_world_values(0, 3, 2)[1:])
    np.testing.assert_allclose(maps["centroid"], truth["centroid"], rtol=1e-6)

    collection = DataCollection([data])
    add_fit_products(data, collection, maps, residual)
    assert [d.label for d in collection] == ["synthetic", "synthetic-gauss1"]
    assert data.get_component(data.id["synthetic-gauss1 residual"]).units == "DN_IRIS_FUV"
    box = RoiSubsetState(maps.pixel_component_ids[1], maps.pixel_component_ids[0], RectangularROI(0.5, 2.5, 0.5, 3.5))
    collection.new_subset_group("box", box)
    n_map = maps.subsets[0].to_mask().sum()
    assert n_map == 6
    assert data.subsets[0].to_mask().sum() == n_map * WAVELENGTH.size


def test_real_raster_smoke(irispy_test_files):
    path = next(p for p in irispy_test_files if p.name == "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    data = raster_data([path], ["Si IV 1403"])[0]
    wavelength = wavelength_angstrom(data)
    assert wavelength.shape == (29,)
    assert (
        1398 < wavelength[0] < wavelength[-1] < 1400
    )  # the bundled window is cropped; the line core (1402.77) is outside
    maps, residual = gaussian_fit_data(data, 1, scheduler="single-threaded")
    assert maps.shape == (8, 109)
    assert residual.shape == (8, 109, 29)
    assert [c.label for c in maps.main_components] == ["background", "amplitude", "centroid", "width", "Time"]
    assert [maps.get_component(c).units for c in maps.main_components[:4]] == [
        "DN_IRIS_FUV",
        "DN_IRIS_FUV",
        "Angstrom",
        "Angstrom",
    ]
    assert [c.label for c in maps.world_component_ids] == ["Helioprojective Longitude", "Helioprojective Latitude"]
    np.testing.assert_array_equal(maps["Time"], data["Time"][..., 0])
    centroid = maps["centroid"]
    assert np.isnan(centroid).mean() < 0.05  # failed fits are NaN, not exceptions
    assert wavelength[0] < np.nanmedian(centroid) < wavelength[-1]


def test_image_cubes_are_rejected(irispy_test_files):
    path = next(p for p in irispy_test_files if p.name == "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    with pytest.raises(ValueError, match="no wavelength axis"):
        wavelength_angstrom(image_data(path))


def test_start_fit_adds_products_when_the_worker_finishes(qtbot, synthetic_raster):
    data, truth = synthetic_raster
    collection = DataCollection([data])
    worker = start_fit(data, collection, 1, None, scheduler="single-threaded")
    assert worker in _WORKERS
    assert worker.progress.isVisible()  # the dialog must outlive start_fit (it is parentless and Python-owned)
    worker.wait()
    qtbot.waitUntil(lambda: len(collection) == 2)  # result/finished signals are delivered on the main thread
    assert _WORKERS == []
    assert not worker.progress.isVisible()
    np.testing.assert_allclose(collection[1]["centroid"], truth["centroid"], rtol=1e-6)
    assert data.id["synthetic-gauss1 residual"] is not None
```

## Tests to add (`glue_solar/tests/test_fitting.py`, verified today as `wp6_test_fitting.py`)

Fixtures: `WAVELENGTH = 1402.0 + 0.025 * np.arange(40)`; `synthetic_cube(n, shape=(6, 5))` returns `(cube, truth)`
with smoothly varying background / amplitude / centroid / width (two peaks at 1402.35 and 1402.65 A for n=2, both
within the 1 A window for every pixel); `synthetic_raster` fixture wraps the n=1 cube in a `Data` with
`_GlueWCS(WCS(naxis=3))` (`ctype WAVE/HPLT-TAN/HPLN-TAN`, `cunit Angstrom/arcsec/arcsec`, component units
`DN_IRIS_FUV`); real files via the existing session fixture `irispy_test_files`. Every fit uses
`scheduler="single-threaded"`.

1. `test_fit_gaussians_recovers_synthetic_parameters[1|2]`: `fit_gaussians(cube, WAVELENGTH, n)`;
   `assert_allclose` of `amplitude_0` and each `amplitude_i` / `stddev_i` to truth with `rtol=1e-4`, `mean_i` with
   `rtol=1e-6`; `residual.shape == cube.shape`; residual rms `< 1e-3`.
2. `test_double_gaussian_seeds_at_the_given_centre`: `fit_gaussians(cube2, WAVELENGTH, 2, rest=1402.5)` (the gallery
   07 path) recovers both centroids at `rtol=1e-6`.
3. `test_wavelength_axis_is_read_in_cartesian_order`: `wavelength_angstrom(data)` equals `WAVELENGTH`; the wrong
   argument order `pixel_to_world_values(0, 0, np.arange(40))[0]` has exactly one unique value.
4. `test_maps_share_the_spatial_grid_and_link_back`: label `synthetic-gauss1`; `maps.shape == data.shape[:-1]`;
   component labels `['background', 'amplitude', 'centroid', 'width']` with units
   `['DN_IRIS_FUV', 'DN_IRIS_FUV', 'Angstrom', 'Angstrom']`; world component labels
   `['Helioprojective Longitude', 'Helioprojective Latitude']`; `list(maps.coords.world_axis_units) == ['arcsec',
   'arcsec']` (SlicedLowLevelWCS returns a list); `maps.coords.pixel_to_world_values(3, 2)` equals the source's lon/lat
   at wavelength index 0; centroid map equals truth. Then `add_fit_products(data, DataCollection([data]), maps,
   residual)`: collection labels `['synthetic', 'synthetic-gauss1']`; the source has `synthetic-gauss1 residual` with
   units `DN_IRIS_FUV`; a `RoiSubsetState` rectangle on the maps (6 px) gives `6 * 40 = 240` px on the source.
5. `test_real_raster_smoke`: `raster_data([iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits], ["Si IV
   1403"])[0]` (872 spectra, 0.7 s); wavelength shape `(29,)` and `1398 < wl[0] < wl[-1] < 1400`; maps shape
   `(8, 109)`, residual `(8, 109, 29)`; labels `['background', 'amplitude', 'centroid', 'width', 'Time']`; units of the
   first four as above; world labels as above; `maps['Time'] == data['Time'][..., 0]`; `isnan(centroid).mean() < 0.05`;
   `wl[0] < nanmedian(centroid) < wl[-1]`. Do not use the sns raster for this: 7480 spectra take 6 s single-threaded,
   and the `raster/` copy of the same-named file fails on NUV windows (see Pitfalls).
6. `test_image_cubes_are_rejected`: `image_data(<sns SJI_1400>)` -> `wavelength_angstrom` raises `ValueError` matching
   `"no wavelength axis"`.
7. `test_start_fit_adds_products_when_the_worker_finishes` (`qtbot`): `start_fit(data, collection, 1, None,
   scheduler="single-threaded")` returns a worker in `_WORKERS`; `worker.progress.isVisible()` is True right after the
   call (regression guard for the garbage-collected dialog); `worker.wait()`; `qtbot.waitUntil(lambda:
   len(collection) == 2)`; `_WORKERS == []`; `not worker.progress.isVisible()`; centroid map equals truth; the
   residual component exists on the source.
8. `glue_solar/tests/test_plugin.py::test_setup_registers_hooks`: `assert "IRIS: Gaussian fit maps…" in [item.label
   for item in layer_action]` (import `layer_action` from `glue.config` on line 1). Verified today: 4 passed, ruff clean.

Neither the `worker.error` path nor the SJI warning is exercised in tests: both are modal message boxes, and a modal
box under `QT_QPA_PLATFORM=offscreen` blocks forever (WP2 pitfall; the checker's e2e script hung the same way on
`save_session`). If a test ever needs them, close the box from `QTimer.singleShot(0, ...)` first, as
`wp6_chk_e2e.py` does for the SJI warning.

## Pitfalls (verified)

- Cartesian argument order in `pixel_to_world_values`: wavelength index FIRST (`(np.arange(nwl), 0, 0)` for a 3D
  raster). Wrong order gives a constant silently (unique = 1 value, both on the synthetic WCS and the real -TAB WCS).
- TRF prefit on the mean spectrum degenerates on windows that do not contain the line core (all 17 bundled test
  windows): params `[-6.63e5, 6.63e5, 139.898 nm, 2.325 nm]`, per-pixel fit 11.09 s instead of 6.25 s. Skip it.
- Seeding a double Gaussian at `argmax -/+ 0.15 A` converges to a wrong solution with no NaN (residual rms 4-43 on
  synthetic doubles). Use the two highest interior local maxima, or a user centre `-/+ 0.15`.
- `dask` `threads` scheduler: no gain (6.23 s vs 6.25 s; GIL). Only `processes` helps, and only for >~4000 spectra
  (872 spectra: 0.63 s single vs 2.58 s processes; pool start-up ~2 s). Keep `'single-threaded'` in tests.
- `scheduler='processes'` from an unguarded `__main__` -> `BrokenProcessPool` on macOS (spawn). Guard scripts.
- `parallel_fit_dask` has no progress or cancel hook; `compute()` is one blocking call, so `processEvents()` loops
  cannot work. `Worker` + indeterminate `QProgressDialog` is the workable form (verified responsive).
- `SlicedLowLevelWCS.world_axis_units` is a `list`, `_GlueWCS.world_axis_units` a `tuple`: compare with `list(...)`.
- `raster_data` on the `raster/` copy of `iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits` loads
  `Si IV 1403` but fails on `Mg II k 2796` with `ValueError: Expected 187 NUV source filename rows, found 1872`
  (irispy 0.8.1; repaired on irispy main e80c51f). `get_test_data_filenames()` lists both copies with the same name;
  select by `"/sns/" in str(path)` if the sns file is ever needed.
- `irispy read_files(memmap=True)` returns unscaled int16 (`[-31952, -31925, ...]` where `memmap=False` gives
  `[4.0, 10.75, ...]`). glue-solar always loads `memmap=False`, so the action is unaffected; do not benchmark with
  memmap (an early run of `wp6_check_gallery.py` did and produced all-zero fits).
- Component units: the fit must not receive `data_unit=u.Unit('DN_IRIS_FUV')` (unparseable without irispy's unit);
  plain floats plus unit strings on the output components.
- `Data.add_component` of a 2D map on the 3D source raises `ValueError` (dimensions); hence a separate 2D Data plus
  pixel `LinkSame`. `wcs_autolink` returns `[]` for raster3D <-> map2D on glue-core 1.27 and raises `IncompatibleWCS`
  on the fork branch (science-moments verifier), so the explicit links stay.
- The `layer_action` callback receives `(layer, data_collection)` only; no `session`/`application`, so no viewer can
  be opened from it (D4 is the consequence, not a choice to revisit).
- `_ask` runs a modal `exec()`; tests bypass it and call `start_fit` / `gaussian_fit_data` directly. The offscreen
  check drives it with a `QTimer.singleShot` when needed.
- Keep a reference to the `Worker` (`_WORKERS`); a QThread collected while running aborts the process.
- Keep a reference to the `QProgressDialog` too (`worker.progress = progress`). A parentless Qt widget is owned by its
  Python reference and `worker.finished.connect(progress.close)` does not hold one; without the line the dialog was
  deleted on return from `start_fit` (0 visible ticks during a 2.8 s fit; 46 with the line, `wp6_chk_progress.py`).
  The writer's timer-tick check measured responsiveness, not the dialog, and missed this.
- Modal boxes under `QT_QPA_PLATFORM=offscreen` block forever: `QMessageBox.warning/critical` in the action and the
  error slot, and glue's own `GlueSerializeError` box on `save_session` (the checker's e2e script hung there and had to
  be killed). Never trigger them in tests without a `QTimer.singleShot(0, close)`.
- Historical saves failed for the source and maps. WP3 covers both only with WP6's corrected outer `_GlueWCS`;
  retain the integrated save/load regression when implementing these packages.
- The two pixel `LinkSame` links are the whole linking story on released glue-core 1.27: `wcs_autolink` drops every
  glue-solar dataset because `_GlueWCS` is a `BaseLowLevelWCS`, not `BaseHighLevelWCS` (`wcs_autolinking.py:320-321`,
  science-moments verifier). On the fork `ape14-wcs-autolink` the stock `_GlueWCS` raises `IncompatibleWCS` for
  raster3D <-> map2D, but with the glue-solar coherence fix (`FixedGlueWCS`, critic §2 / `cc_forkmap.py`) that pair
  autolinks (1 link). Keep the explicit links anyway; they are exact and cost three lines.
- The writer's `wp6_check_real.py` no longer runs (`"rest (TWAVE) A:"(d)` -> `TypeError: 'str' object is not
  callable`, a leftover from removing a `rest_angstrom` helper). Use `wp6_chk_real_fixed.py`; the numbers in this brief
  come from it.

## Acceptance criteria

- [ ] `glue_solar/sources/fitting.py` exists with the seven functions above; `glue_solar/__init__.py` imports it;
      `"IRIS: Gaussian fit maps…"` is in `glue_qt.config.layer_action` after `import glue_solar`.
- [ ] `pytest glue_solar -q -o addopts=''` passes: 35 (27 existing + 8 new, `filterwarnings = error` active) in under
      5 s; `ruff check --config .ruff.toml glue_solar` clean; `ruff format --check` clean for the four new/changed
      files (`sources/fitting.py`, `tests/test_fitting.py`, `__init__.py`, `tests/test_plugin.py`; three other files
      are not format-clean on the branch and stay untouched).
- [ ] `test_plugin.py::test_setup_registers_hooks` asserts the `"IRIS: Gaussian fit maps…"` label is registered.
- [ ] The "Gaussian fit" `QProgressDialog` is visible for the whole fit and closes on `finished`
      (`worker.progress` reference; test 7 asserts it).
- [ ] Synthetic single and double Gaussians recovered to `rtol <= 1e-4` (amplitudes/widths) and `1e-6` (centroids).
- [ ] On the 2014 r00000 Si IV 1403 test raster: maps `(8, 109)`, residual `(8, 109, 29)`, component units
      `DN_IRIS_FUV / DN_IRIS_FUV / Angstrom / Angstrom`, world axes `Helioprojective Longitude / Latitude` in arcsec,
      NaN fraction `< 5%`, `Time` carried over.
- [ ] A subset drawn on the maps selects `n * nwl` pixels on the source (pixel `LinkSame` on the spatial axes only).
- [ ] The residual cube is a component of the source dataset named `<maps label> residual` with the source units.
- [ ] `start_fit` runs `parallel_fit_dask(scheduler='processes')` inside `glue_qt.utils.threading.Worker`; the GUI
      stays responsive (timer ticks) and the products appear on the main thread after `finished`.
- [ ] A 320 x 548 raster window fits in ~25 s with `processes` on a 12-core machine (0.15 ms/spectrum); NaN `< 0.1%`.
- [ ] Right-click on an SJI / AIA cube shows the "not an IRIS spectrogram" warning instead of a traceback.
- [ ] No new dependency in `pyproject.toml`; no `fitting` extra.
- [ ] Docs section and changelog fragment added.

## Dropped / out of scope

- `fitting` extra with dask (PLAN line 124): dask is a hard irispy-lmsal dependency (audit P2.2-dask-extra).
- Loader cube handle (PLAN 113-115): not needed; array, WCS, units, Time are on the Data (verified).
- TRF prefit and TWAVE seeding: worse on cropped and on full windows (numbers above).
- Fit-window half width (restrict the fit to `centre -/+ w`): improves residual rms 2x and speed 20-35% and is the
  only way to fit a secondary line (O IV in the Si IV window); v1 whole-window fits already agree 96-100% with the
  gallery reference. Add on demand; it is a 3-line `keep` mask in `fit_gaussians` plus one form row (mirrors WP2 wings).
- Velocity / width in km/s and net-flux maps: one Arithmetic-dialog line each once WP3.3 (rest wavelength affordance)
  exists; `centroid` is in Angstrom and the chosen centre is in `maps.meta['rest_wavelength_angstrom']`.
- `diagnostics` / `diagnostics_path` (per-pixel error logs) and `fit_info`: failed pixels are NaN; nobody asked for logs.
- Weights, uncertainty and the bad-pixel mask: the gallery clips to zero and ignores the mask; same here.
- A dedicated "open the maps in an Image viewer" step: D4.
- Contributing the recipe to irispy-lmsal (`fit_gaussians` cube-in / maps-out next to `calculate_moments`): later,
  after the glue-solar version has users.
- Cancel button / progress percentage: parallel_fit_dask offers neither.

## Docs

- `docs/user_guide/gaussian-fit-maps-of-a-raster-window.rst` (NEW; WP2 adds its own page the same way, so the user
  guide keeps one page per action) and one toctree line in `docs/user_guide/index.rst` after
  `line-moments-of-a-raster-window` (or after `guide-to-glue-1dprofile-viewer-for-iris-data` if WP2 is not merged):

  ```rst
  .. _glue_solar_gaussian_fit_maps:

  ===================================
  Gaussian fit maps of a raster window
  ===================================

  Right-click a raster dataset in the data collection and choose "IRIS: Gaussian fit maps…". Pick
  "1 Gaussian + background" (Si IV, C II, O I) or "2 Gaussians + background" (Mg II k2v/k2r). Leave "Line
  centre" blank to seed the fit from the strongest peak (or the two strongest peaks) of the spatially
  averaged spectrum, or type a wavelength in Angstrom to pin the line.

  The fit runs in the background (about 25 seconds for a 320-step dense raster on 12 cores; it cannot be
  cancelled) and adds a dataset ``<dataset>-gauss1`` (or ``-gauss2``) with ``background``, ``amplitude``,
  ``centroid`` and ``width`` maps (``amplitude 1``, ``centroid 2``, ... for two Gaussians) plus the
  per-exposure ``Time``. Amplitudes keep the raster's units; centroid and width are in Angstrom. The maps
  share the raster's spatial pixel grid and are linked to it, so a subset drawn on a map selects the same
  positions in the raster. The residual (data minus model) is added to the raster as a
  ``<dataset>-gauss1 residual`` component; plot it in a Profile viewer next to the data. Pixels where the
  fit fails are NaN.

  The fit is :func:`astropy.modeling.fitting.parallel_fit_dask` with a constant plus one or two
  :class:`~astropy.modeling.functional_models.Gaussian1D`; the recipe follows the irispy gallery examples
  "Spectral fitting" and "Mg II two Gaussian fitting" with data-driven seeds. Sessions containing these
  datasets cannot be saved yet; see "Saving sessions" on the raster and SJI page.
  ```
- `docs/api_reference.rst`: add
  ```
  .. automodapi:: glue_solar.sources.fitting
     :no-inheritance-diagram:
  ```
- `changelog/<PR>.feature.rst`: "Right-clicking an IRIS raster dataset offers "IRIS: Gaussian fit maps…", which fits
  one or two Gaussians plus a constant background to every spectrum with
  `astropy.modeling.fitting.parallel_fit_dask` in a background thread and adds background, amplitude, centroid
  (Angstrom) and width (Angstrom) maps as a new dataset linked to the raster, plus a residual cube on the raster."
- `IRIS_GLUE_GAP_PLAN.md` Phase 2.2 (if it is being kept current): drop "Requires `dask` - add as an optional
  `fitting` extra" and "same dialog as moments"; say "layer action, Worker + processes scheduler, no cancel, no cube
  handle, seeds from the mean spectrum (argmax / two local maxima), wavelength in Angstrom". Audit table row
  "Single/double Gaussian fitting": Missing -> Covered once merged.


---

# WP7 - GOES and SDO context actions

**Goal.** Two "Plugins" menu actions in glue-solar that fetch context for a loaded IRIS observation on explicit request: the GOES XRS light curve spanning STARTOBS..ENDOBS (plotted in a Scatter viewer, log flux), and the SDO/AIA 171 image nearest STARTOBS cut around the IRIS field of view with the FOV outlined as a subset (shown in an Image viewer). Both are plain sunpy recipes wrapped in ~125 lines of glue-solar code, no glue-core or glue-qt change, tests run without network.

> Checked 2026-09-02 (checker pass): every file:line reference below was opened and confirmed; every prototype script was re-run with a fresh scratch `HOME` (`home-wp7chk`) and produced the outputs quoted; the module in step 2 was executed verbatim by the 10-test file in "Tests to add" (10 passed under the repo `pytest.ini`, warnings as errors) and passes `ruff check` with the repo `.ruff.toml`. Corrections made by the checker are marked "(checker)".

## Current state (2026-09-02)

- glue-solar `iris-observation-browser` @ `d3a2bd3` (= PR #44): nothing for GOES or live SDO. `grep -rn -i 'goes|fido|timeseries|propagate' glue_solar/ docs/user_guide/ pyproject.toml` hits only one prose line ("propagate spatial selections"). Verified again today: `.venv/bin/python -c "from sunpy.timeseries import TimeSeries"` -> `ModuleNotFoundError: No module named 'h5netcdf'`; `pyproject.toml:21` is `"sunpy[map,net]>=6.0.0"`.
- What exists and is reused:
  - `glue_solar/sources/iris.py:30-48` `browse_iris`: the `@menubar_plugin(label)` pattern, callback `(session, data_collection)`, `app = session.application`, `app.add_datasets(...)`, `app.new_data_viewer(ImageViewer, data=...)`. glue-qt calls it with `nonpartial(function, self.session, self.data_collection)` (`glue_qt/app/application.py:942-948`). `glue.config.menubar_plugin` is the same object as `glue_qt.config.menubar_plugin` (`glue/config.py:949-956` re-imports it).
  - `glue_solar/sources/loaders/iris.py:35-69` `_GlueWCS(BaseWCSWrapper)`: arcsec helioprojective values, names from `_AXIS_NAMES` when the inner WCS has none. `:88-90` `_observation_label(meta)` -> `"3620258102-2021-09-05T00:18:33"`. `:76` `data.meta = cube.meta`, so every IRIS Data carries `STARTOBS`/`ENDOBS` (verified: SJI `SJIMeta`, raster `SGMeta`, both have both keys). WP1 rewrites `_GlueWCS` (names, Angstrom, coherent high-level API) and adds `link_hpc(data_collection)` to the same file; see Dependencies.
  - `glue_solar/sources/maps.py:19-32` `_parse_sunpy_map(map, label)`: any `GenericMap` -> `Data` with `coords = map.wcs` (degrees, labels `Hplt`/`Hpln`), `preferred_cmap = map.cmap` (`:30`).
  - The browser already loads LMSAL's aligned `aia_l2_*` cutouts (`loaders/scan.py:68,111-115,174-175`, `loaders/iris.py:110-131`) with `sdoaia<wave>` colormaps and HPC world axes. Those are per-exposure co-aligned and remain the primary co-aligned product; WP7 adds only what they lack: wider (limb/full-disk-scale) context and the FOV outline.
- Environment: glue-core 1.27.0 (site-packages), glue-qt editable `macos-integration`, sunpy 8.0.0, irispy 0.8.1, astropy 8.0.1, matplotlib 3.11.1, numpy 2.5.2, pandas 3.0.5, parfive 2.3.1, shapely 2.1.2, reproject 0.21.0. `h5netcdf`, `cdflib`, `aiapy`, `sunkit_image` not installed (an `h5netcdf 1.8.1` wheel sits in `~/.cache/uv/archive-v0/jm144Mb-aATYC6j0`, used via `PYTHONPATH` for today's runs; nothing was downloaded).
- Audit basis: `findings/network-context.json` (P1.5 agree, P2.4 corrected by the verifier: match physical types not labels; FOV as a `PolygonalROI` subset needs no link; size small), `findings/session-serialization.json` (P3.6-cmap: `_parse_sunpy_map`'s `preferred_cmap` Colormap crashes session save on main; P3.6-loadlog: datasets added through `app.add_datasets` carry no `LoadLog`, so sessions embed their arrays), `findings/critic.md` §3.4 (`RegionData` rejected), §3.5 (datetime epoch bug already hits the raster `Time` component), §4 (P2.4 ships on released glue 1.27 with the subset FOV; on the fork's 3.1 autolink the AIA astropy-WCS path needs the `_GlueWCS` coherence fix from WP1).

## Decisions already made

- D1: `link_hpc` (WP1, world components paired by `world_axis_physical_types`) is the link mechanism. The AIA context Data must therefore expose the same physical types **and the same unit (arcsec)** as IRIS Data, and (checker) its `coords` must be a `_GlueWCS` instance, because WP1's `link_hpc` skips every dataset whose coords are not `_GlueWCS` (`briefs/wp1-linking.md` L50, L216, L614). Wrap the cutout WCS in `_GlueWCS` (verified below; with the raw degree WCS the FOV subset propagates to 0 IRIS pixels, and `link_hpc` would not even pair it).
- D2: everything in glue-solar. No glue-core/glue-qt change. The glue-core datetime-epoch bug (`glue/utils/matplotlib.py:449-469`, hard-coded 0001-01-01 origin; matplotlib >= 3.3 epoch is 1970-01-01; no `set_epoch` anywhere in glue or glue-qt) is worked around in glue-solar by `matplotlib.rcParams["date.epoch"] = "0000-12-31T00:00:00"` in `glue_solar.setup()`. Verified: it makes the Scatter viewer tick labels correct, and `matplotlib.dates._epoch` is still `None` after `GlueApplication()` finished constructing, so `setup()` (called from `load_plugins`, `glue_qt/main.py:156` and `glue_qt/app/application.py:296`) runs early enough. Optional upstream one-liner (later, not gating): make `datetime64_to_mpl`/`mpl_to_datetime64` call `matplotlib.dates.date2num`/`num2date`.
- D3: wavelength in Angstrom lands in WP1. WP7 only uses the lon/lat world axes, unaffected.
- D4 applies to moments only. WP7 uses `menubar_plugin` (needs `session.application` to open the viewers; `layer_action` callbacks get `(layer, data_collection)` only, critic §2); the `QInputDialog` that picks the observation is the explicit "go online" button (plan §1.5: "button, not automatic; failure non-fatal").
- Audit-settled: Scatter viewer, not Profile (Profile `x_att` is pixel/world-coord only, `glue/viewers/profile/state.py:69-71`). Pick one GOES satellite from the search result (`XRSClient` lists every satellite flying, `sunpy/net/dataretriever/sources/goes.py:150-170`). `propagate_with_solar_surface` is a context manager, used only around the corner transform. VSO, not JSOC (JSOC cutouts need a registered `a.jsoc.Notify` email). No `aiapy`/`sunkit_image` (irispy `examples/coalign/01` and `02` are cross-correlation/pointing-update recipes, not context retrieval). `RegionData` rejected (crashes with WCS coords, trace below).

## Dependencies / order

1. **WP1 first** (`_GlueWCS` Angstrom + `link_hpc`). (checker) WP1 puts `link_hpc` in `glue_solar/sources/loaders/iris.py` with signature `link_hpc(data_collection) -> list[LinkSame]`; the caller adds the links: `data_collection.add_link(link_hpc(data_collection))` (`briefs/wp1-linking.md` L198-224, L247). It only pairs datasets whose `coords` is a `_GlueWCS`, is idempotent (second call returns `[]`), and links everything to the first dataset that has HPC axes. Verified today with WP1's `_GlueWCS` and `link_hpc` code copied from that brief: `_GlueWCS(cutout.wcs)` on the 2-D AIA FITS WCS gives names `['Helioprojective Longitude', 'Helioprojective Latitude']`, units `('arcsec', 'arcsec')`, low-level and high-level round trips exact, and `link_hpc` on `[context, sji]` returns 2 links, FOV subset -> 1371 SJI pixels in frame 0, 0 in the last frame, second call `[]`. If WP7 is built before WP1 merges, the 4-line inline `LinkSame`-by-physical-type loop below is the stand-in and must be replaced by the `link_hpc` call.
2. Independent of PR #44 review, moments (WP2), profile-wcs, autolink (3.1), macOS #68. On the fork's 3.1 autolink the AIA context autolinks only with WP1's coherent `_GlueWCS` (critic §4); not needed on glue 1.27, where `link_hpc` does the pairing.
3. WP3 (sessions) must treat a plain 2-D FITS WCS inside `_GlueWCS` as a leaf (`scratchpad/sess_proto_savers.py:33-36` already has `kind == "fits"` via `to_header_string`), otherwise the AIA context Data is unsaveable. The GOES Data (datetime64 + two float components, no coords) round-trips with stock glue already (verified today: `GlueSerializer`/`GlueUnSerializer` on a Data with `xrsa`, `xrsb` (`W / m2`) and `time` datetime64[us]: components, dtype, values and units intact). Both context datasets are added with `app.add_datasets`, so they carry no `LoadLog` and sessions embed their arrays (P3.6-loadlog); a 346x344 cutout plus a few thousand GOES rows is about 1 MB, acceptable.
4. New runtime dependency: `sunpy[map,net,timeseries]` (adds `h5netcdf`, `cdflib`, `h5py`, `pandas`). Must be the full extra: with only `h5netcdf` present, `import sunpy.timeseries` emits `SunpyUserWarning: ... not installed: ['cdflib>=1.3.2']` (seen today) and `pytest.ini` turns warnings into errors, so `import glue_solar` would fail in CI.

## Files to touch

- `pyproject.toml:21`: `"sunpy[map,net]>=6.0.0"` -> `"sunpy[map,net,timeseries]>=6.0.0"`.
- `glue_solar/sources/context.py` (new, ~125 lines): `goes_xrs`, `fov_polygon`, `aia_context`, `_pick_iris_data`, `goes_context` and `sdo_context` menubar plugins. Full code in "Step-by-step".
- `glue_solar/__init__.py`: import `context` next to `iris, maps` (registers the two plugins); add the `rcParams["date.epoch"]` line to `setup()`; add `"context"` to `__all__`.
- `glue_solar/tests/test_context.py` (new): the 10-test file below, no network (verified today).
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: new "Context data (network)" section after "Opening a single file" (`:48-52`).
- `docs/api_reference.rst`: `.. automodapi:: glue_solar.sources.context` after the `maps` block (`:10-11`).
- `changelog/<PR>.feature.rst` (new; PR number unknown until opened, existing fragments are `42.*`, `44.*`).
- `IRIS_GLUE_GAP_PLAN.md` / `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` wording (untracked planning docs, see Docs).

## Step-by-step

1. `pyproject.toml`: change the sunpy extra as above. Reinstall the venv (`.venv/bin/pip install -e ".[tests]"`; the extras group is `tests`, `pyproject.toml:42`) so `h5netcdf` and `cdflib` are present; `.venv/bin/python -c "from sunpy.timeseries import TimeSeries"` must be silent.
2. Create `glue_solar/sources/context.py` (this exact text passed the tests and ruff today, with `link_hpc` defined locally from WP1's brief instead of imported):

```python
"""
Context for a loaded IRIS observation, fetched on request: the GOES XRS light curve and an SDO/AIA image.
"""

import numpy as np
from glue.config import menubar_plugin
from glue.core import Data
from glue.core.component import Component
from glue.core.link_helpers import LinkSame
from glue.core.roi import PolygonalROI
from glue.core.subset import RoiSubsetState
from glue_qt.utils import set_cursor_cm
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.coordinates import SkyCoord

import sunpy.map
from sunpy.coordinates import Helioprojective, propagate_with_solar_surface
from sunpy.net import Fido
from sunpy.net import attrs as a
from sunpy.time import parse_time
from sunpy.timeseries import TimeSeries

from glue_solar.sources.loaders.iris import _GlueWCS, _observation_label, link_hpc
from glue_solar.sources.maps import _parse_sunpy_map

__all__ = ["aia_context", "fov_polygon", "goes_context", "goes_xrs", "sdo_context"]

_HPC = "custom:pos.helioprojective."


def goes_xrs(start, end):
    """
    GOES XRS 1-minute averages between two times (ISO strings) as a Glue dataset.

    Components ``xrsa`` (0.5-4 A) and ``xrsb`` (1-8 A) in W / m2, then ``time`` (datetime64).
    Needs the network: NOAA file listing, then a download into sunpy's download directory.
    """
    table = Fido.search(a.Time(start, end), a.Instrument.xrs, a.Resolution.avg1m)[0]
    if len(table) == 0:
        raise ValueError(f"No GOES XRS data found between {start} and {end}")
    # ponytail: the client lists every satellite flying; take the first, NOAA's primary designation is not modelled
    table = table[table["SatelliteNumber"] == table["SatelliteNumber"][0]]
    files = Fido.fetch(table, progress=False)
    if files.errors:
        raise OSError(f"{len(files.errors)} GOES file(s) failed to download: {files.errors[0]}")
    series = TimeSeries(sorted(files), source="xrs", concatenate=True).truncate(start, end)
    frame = series.to_dataframe()
    data = Data(label=f"{series.observatory} XRS")
    for column in ("xrsa", "xrsb"):
        data.add_component(Component(frame[column].to_numpy(), units=str(series.units[column])), column)
    data.add_component(frame.index.values, "time")  # last: a datetime default attribute breaks the Profile viewer
    return data


def fov_polygon(data):
    """
    Helioprojective (longitude, latitude) of the four field-of-view corners of ``data``, in arcsec.

    Uses the first exposure/scan (every non-spatial pixel axis at index 0) and pixel centres.
    """
    wcs = data.coords
    types = list(getattr(wcs, "world_axis_physical_types", []))
    if _HPC + "lon" not in types or _HPC + "lat" not in types:
        raise ValueError(f"{data.label} has no helioprojective coordinates")
    lon, lat = types.index(_HPC + "lon"), types.index(_HPC + "lat")
    correlated = wcs.axis_correlation_matrix
    other = [w for w in range(wcs.world_n_dim) if w not in (lon, lat)]
    spatial = [
        p
        for p in range(wcs.pixel_n_dim)
        if (correlated[lon, p] or correlated[lat, p]) and not correlated[other, p].any()
    ]
    if len(spatial) != 2:
        raise ValueError(f"{data.label} has no two-dimensional helioprojective field of view")
    x, y = spatial
    shape = data.shape[::-1]  # pixel-axis order
    corners = np.zeros((4, wcs.pixel_n_dim))  # ponytail: pixel centres, the outline sits half a pixel inside the edge
    corners[:, x] = [0, shape[x] - 1, shape[x] - 1, 0]
    corners[:, y] = [0, 0, shape[y] - 1, shape[y] - 1]
    world = wcs.pixel_to_world_values(*corners.T)
    return np.asarray(world[lon]), np.asarray(world[lat])


def aia_context(data, wavelength=171 * u.AA, margin=100 * u.arcsec):
    """
    The SDO/AIA image nearest the start of ``data``'s observation, cut to the IRIS field of view plus ``margin``.

    Returns the cutout as a Glue dataset and a subset state outlining the IRIS field of view on it.
    Needs the network (VSO search and download).
    """
    start = parse_time(str(data.meta["STARTOBS"]))
    lon, lat = fov_polygon(data)
    # ponytail: IRIS flies in low Earth orbit; an Earth observer is within an arcsecond of its own frame
    corners = SkyCoord(lon * u.arcsec, lat * u.arcsec, frame=Helioprojective(obstime=start, observer="earth"))
    result = Fido.search(
        a.Time(start - 10 * u.min, start + 10 * u.min, near=start), a.Instrument.aia, a.Wavelength(wavelength)
    )
    files = Fido.fetch(result, progress=False)
    if files.errors or not files:
        raise OSError(f"No AIA {wavelength} image could be downloaded for {start.isot}")
    aia = sunpy.map.Map(files[0])
    with propagate_with_solar_surface():  # only changes anything when the image is not co-temporal
        corners = corners.transform_to(aia.coordinate_frame)
    bottom_left = SkyCoord(corners.Tx.min() - margin, corners.Ty.min() - margin, frame=aia.coordinate_frame)
    top_right = SkyCoord(corners.Tx.max() + margin, corners.Ty.max() + margin, frame=aia.coordinate_frame)
    cutout = aia.submap(bottom_left, top_right=top_right)
    context = _parse_sunpy_map(cutout, "SDO context")
    context.label = f"AIA_{int(cutout.wavelength.to_value(u.AA))}_context-{_observation_label(data.meta)}"
    context.coords = _GlueWCS(cutout.wcs)  # arcsec and physical-type names, so link_hpc pairs it with IRIS data
    x, y = cutout.wcs.world_to_pixel(corners)
    fov = RoiSubsetState(
        xatt=context.pixel_component_ids[1], yatt=context.pixel_component_ids[0], roi=PolygonalROI(vx=list(x), vy=list(y))
    )
    return context, fov


def _pick_iris_data(app, data_collection, title, prompt):
    """Ask which loaded IRIS dataset to use. The dialog's OK button is the explicit consent to go online."""
    candidates = [
        d
        for d in data_collection
        if "STARTOBS" in d.meta and d.coords is not None and _HPC + "lon" in d.coords.world_axis_physical_types
    ]
    if not candidates:
        QtWidgets.QMessageBox.warning(app, title, "Load an IRIS dataset first.")
        return None
    label, ok = QtWidgets.QInputDialog.getItem(app, title, prompt, [d.label for d in candidates], 0, False)
    return next(d for d in candidates if d.label == label) if ok else None


@menubar_plugin("IRIS: GOES context…")
def goes_context(session, data_collection):
    """Download the GOES XRS light curve spanning an IRIS observation and plot it."""
    app = session.application
    data = _pick_iris_data(app, data_collection, "GOES context", "Download the GOES XRS light curve (NOAA, via sunpy) for")
    if data is None:
        return
    try:
        with set_cursor_cm(Qt.WaitCursor):
            goes = goes_xrs(str(data.meta["STARTOBS"]), str(data.meta["ENDOBS"]))
    except Exception as error:  # network and reader failures stay a message box, never a crash
        QtWidgets.QMessageBox.critical(app, "GOES context", str(error))
        return
    app.add_datasets(goes)
    time = data.find_component_id("Time")
    if time is not None:  # rasters and stacks carry exact exposure times: a time range on the curve selects raster steps
        data_collection.add_link(LinkSame(goes.id["time"], time))
    from glue_qt.viewers.scatter import ScatterViewer

    viewer = app.new_data_viewer(ScatterViewer, data=goes)
    viewer.state.x_att, viewer.state.y_att, viewer.state.y_log = goes.id["time"], goes.id["xrsb"], True
    viewer.layers[0].state.line_visible = True


@menubar_plugin("IRIS: SDO context…")
def sdo_context(session, data_collection):
    """Download the AIA 171 image nearest the start of an IRIS observation, cut around its field of view, show it."""
    app = session.application
    data = _pick_iris_data(app, data_collection, "SDO context", "Download the AIA 171 Å image nearest the start (VSO, via sunpy) for")
    if data is None:
        return
    try:
        with set_cursor_cm(Qt.WaitCursor):
            context, fov = aia_context(data)
    except Exception as error:  # network and reader failures stay a message box, never a crash
        QtWidgets.QMessageBox.critical(app, "SDO context", str(error))
        return
    app.add_datasets(context)
    data_collection.add_link(link_hpc(data_collection))  # WP1; pairs the AIA lon/lat with every IRIS dataset by physical type
    data_collection.new_subset_group("IRIS FOV", fov)
    from glue_qt.viewers.image import ImageViewer

    app.new_data_viewer(ImageViewer, data=context)
```

   (checker) `link_hpc` returns a list and does not add anything itself; the `data_collection.add_link(link_hpc(data_collection))` form above is WP1's contract (`briefs/wp1-linking.md` L207, L247). Until WP1 merges, drop `link_hpc` from the import and use the verified stand-in loop in its place:

```python
def _by_type(d):
    return {p: c for c, p in zip(d.world_component_ids, d.coords.world_axis_physical_types[::-1])}
for other in (d for d in data_collection if d is not context and "STARTOBS" in d.meta):
    for p in (_HPC + "lon", _HPC + "lat"):
        data_collection.add_link(LinkSame(_by_type(context)[p], _by_type(other)[p]))
```

   Run `pre-commit run ruff-check --files glue_solar/sources/context.py` (repo `.ruff.toml`: line length 120, rules E/F/W/UP/PT/I, isort sections stdlib / third-party / astropy / sunpy / first-party). The import block above already satisfies it (`ruff 0.15.20 check --config .ruff.toml`: "All checks passed!" today; the pre-commit hook pins ruff v0.16.1).

3. `glue_solar/__init__.py` (the `I` and `F401` rules are ignored for `__init__.py` in `.ruff.toml`, so import order is free):

```python
import matplotlib
from glue.config import colormaps
from sunpy.visualization.colormaps import cmlist

from glue_solar.sources import context, iris, maps  # noqa: F401 - importing registers the plugins
...
def setup():
    # glue-core's datetime64_to_mpl counts days from 0001-01-01 (+1); matplotlib >= 3.3 counts from 1970.
    # Point matplotlib at glue's origin before the first date is drawn, or every datetime axis is labelled year 3990.
    matplotlib.rcParams["date.epoch"] = "0000-12-31T00:00:00"
    for _, ctable in sorted(cmlist.items()):
        colormaps.add(ctable.name, ctable)
```

4. Tests (section below), docs, changelog.
5. Manual check with a real observation once (needs network): Plugins -> "IRIS: GOES context…" -> pick the SJI -> Scatter viewer with dates on the x axis and log flux; Plugins -> "IRIS: SDO context…" -> Image viewer with the AIA cutout, the "IRIS FOV" subset drawn on it, and a rectangle drawn on the AIA image selecting raster steps/SJI pixels through the link.

## Verified code

All runs today (2026-09-02) with `HOME=<scratch>/home-wp7 GLUE_TESTING=True QT_QPA_PLATFORM=offscreen MPLBACKEND=agg`; GOES runs additionally used `PYTHONPATH=/Users/nabil/.cache/uv/archive-v0/jm144Mb-aATYC6j0` (the locally cached `h5netcdf 1.8.1` wheel) because the venv lacks it. No network. Scripts: `scratchpad/wp7_goes.py`, `wp7_goes2.py`, `wp7_fido.py`, `wp7_sdo.py`, `wp7_sdo2.py`, `wp7_corners.py`, `wp7_timelink.py`, `wp7_profile_order.py`, `wp7_warn.py`, plus re-runs of `cc_region.py` and `v_goes_c.py`. (checker) All of them were re-run with `HOME=<scratch>/home-wp7chk`; outputs identical to those quoted. glue's INFO logging goes to stderr in a fresh HOME; pipe `2>/dev/null` to read the results.

### 1. Real GOES reader on sunpy's shipped test file, glue Data, Scatter viewer, epoch bug and workaround

`wp7_goes.py` (core lines):

```python
import matplotlib
if os.environ.get("EPOCH"):
    matplotlib.rcParams["date.epoch"] = "0000-12-31T00:00:00"   # glue's datetime64_to_mpl origin
from sunpy.timeseries import TimeSeries
f = sunpy.data.test.get_test_filepath("sci_xrsf-l2-avg1m_g16_d20210101_truncated.nc")
ts = TimeSeries(f, source="xrs")
df = ts.truncate("2021-01-01T22:30:00", "2021-01-01T23:10:00").to_dataframe()
d = Data(label="GOES-16 XRS", time=df.index.values, xrsa=df["xrsa"].to_numpy(), xrsb=df["xrsb"].to_numpy())
app = GlueApplication(DataCollection([d]))
sv = app.new_data_viewer(ScatterViewer, data=d)
sv.state.x_att, sv.state.y_att = d.id["time"], d.id["xrsb"]; sv.state.y_log = True
sv.figure.canvas.draw()
```

```
$ for e in "" 1; do EPOCH=$e ... python -u wp7_goes.py; done
===== EPOCH= =====
parfive.Results.append sig: (self, *, path, url)
Results: ['/tmp/x'] errors: []
Fido.search sig: (*query)
test nc: XRSTimeSeries 2021-01-01T22:20:00.000 2021-01-01T23:59:00.000 cols: ['xrsa', 'xrsb', 'xrsa_quality', 'xrsb_quality'] n: 100
truncate -> 41 rows 2021-01-01 22:30:00 2021-01-01 23:10:00 index dtype: datetime64[us] meta sat: GOES-16
df.index.values dtype: datetime64[us]
kinds: [('time', 'datetime'), ('xrsa', 'numerical'), ('xrsb', 'numerical')]
mpl _epoch before glue_qt import: None
mpl _epoch after glue_qt import: None
mpl _epoch after GlueApplication(): None
x_kinds: {'datetime'} | state x_min/x_max: 2021-01-01T22:28:24.000000 2021-01-01T23:11:36.000000 | y_log: True yscale: log
mpl epoch now: 1970-01-01T00:00:00 | num2date(xlim): ['3990-01-02T22:28:24+00:00', '3990-01-02T23:11:36+00:00']
tick labels: ['02 22:30', '02 22:35', '02 22:40', '02 22:45', '02 22:50', '02 22:55', '02 23:00', '02 23:05', '02 23:10']
===== EPOCH=1 =====
...
mpl epoch now: 0000-12-31T00:00:00 | num2date(xlim): ['2021-01-01T22:28:24+00:00', '2021-01-01T23:11:36+00:00']
tick labels: ['01 22:30', '01 22:35', '01 22:40', '01 22:45', '01 22:50', '01 22:55', '01 23:00', '01 23:05', '01 23:10']
```

Conclusion: the datetime x axis, log y and the viewer all work on stock glue 1.27; without the rcParams line the labels show day "02" of year 3990 for 2021-01-01 data; with it they are right. `_epoch` is unset until the first draw, so `setup()` is early enough.

### 2. Multi-file concatenate + truncate across midnight (locally cached NOAA daily files, `wp7_goes2.py`)

```python
cached = [f"/Users/nabil/sunpy/data/sci_xrsf-l2-avg1m_g15_d2012100{d}_v2-2-1.nc" for d in (5, 6)]
ts = TimeSeries(cached, source="xrs", concatenate=True)
df = ts.truncate("2012-10-05T23:00", "2012-10-06T01:00").to_dataframe()
```

```
[True, True]
concat: XRSTimeSeries 2012-10-05T00:00:00.000 2012-10-06T23:59:00.000 2880
truncate across midnight -> 121 2012-10-05 23:00:00 2012-10-06 01:00:00 | observatory: GOES-15 | units: W / m2
```

(checker) Also verified: `TimeSeries(sorted([one_file]), source="xrs", concatenate=True)` returns a single `XRSTimeSeries` (the one-file case of `goes_xrs`), and `truncate("2021-01-01T22:30:00.640", "2021-01-01T23:10:00.123")` on the test file gives 40 rows, not 41: a fractional-second `STARTOBS` excludes the minute sample at the boundary. Harmless; tests use whole seconds.

### 3. Satellite selection on a real `QueryResponse` without network (`wp7_fido.py`)

```python
qr = QueryResponse(rows_for_sat_16_and_17, client=XRSClient()); tbl = UnifiedResponse(qr)[0]
sub = tbl[tbl["SatelliteNumber"] == tbl["SatelliteNumber"][0]]
```

```
ur[0] type: QueryResponse len: 2 cols: ['Start Time', 'End Time', 'Instrument', 'Physobs', 'Source', 'Provider', 'Resolution', 'SatelliteNumber', 'url']
masked type: QueryResponse len: 1 client kept: XRSClient sat: [np.str_('16')]
download_dir: <HOME>/sunpy/data
empty UnifiedResponse len: 0
```

Boolean masking keeps the `QueryResponse` class and its client, so `Fido.fetch(sub)` is valid. Offline attr construction also checked: `a.Time(t0-1min, t0+1min, near=t0) & a.Instrument.aia & a.Wavelength(171 AA)` and `a.Time(start, end) & a.Instrument.xrs & a.Resolution.avg1m` build without error (`a.Resolution.avg1m` is `<Resolution(avg1m: 1-minute averages of XRS measurements)>`).

(checker) The `[0]` on an empty search is safe: with `XRSClient.search` monkeypatched to return `QueryResponse([], client=self)`, `Fido.search(a.Time(...), a.Instrument.xrs, a.Resolution.avg1m)` returns a `UnifiedResponse` with 1 table, `res[0]` is an empty `QueryResponse` (`len 0`), and `Fido.fetch(res[0], progress=False)` returns an empty `parfive.Results` with no network access.

### 4. FOV polygon, synthetic AIA map, `propagate_with_solar_surface`, submap, `_GlueWCS` cutout, FOV subset, links, Image viewer (`wp7_sdo2.py`)

```
corr matrix SJI_1400-3620258102-2021-09-05T00:18:33 (62, 40, 37)
 [[1 1 1]
 [1 1 1]
 [0 0 1]]
  spatial pixel axes: [0, 1] polygon lon: [-56.4 -50.4 -50.4 -56.3] lat: [-403.  -403.  -396.5 -396.5]
corr matrix Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0 (187, 40, 52)
 [[1 0 0]
 [0 1 1]
 [0 1 1]]
  spatial pixel axes: [1, 2] polygon lon: [-52.9 -52.8 -10.6 -10.7] lat: [-402.8 -396.4 -396.9 -403.3]
corr matrix C_II_1336-3860258481-2014-03-29T14:09:38-stack (2, 8, 109, 17)
 [[1 0 0 0]
 [0 1 1 0]
 [0 1 1 0]
 [0 0 0 1]]
  spatial pixel axes: [1, 2] polygon lon: [483.8 484.  498.1 497.9] lat: [271.2 289.2 289.2 271.2]
same-time transform identical: True True
full map: PixelPair(x=<Quantity 800. pix>, y=<Quantity 800. pix>) -> submap: PixelPair(x=<Quantity 344. pix>, y=<Quantity 346. pix>)
raw map wcs names/units: ['', ''] ['deg', 'deg'] | glue world: ['Hplt', 'Hpln'] units: ['deg', 'deg']
with _GlueWCS: world: ['Helioprojective Latitude', 'Helioprojective Longitude'] units: ['arcsec', 'arcsec'] | IRIS SJI units: ['s', 'arcsec', 'arcsec']
FOV subset on AIA: 100 px of 119024
FOV subset on SJI -> 6948 of 91760 | per frame first 3: [1371 1248 1092] last: 0
FOV subset on raster -> 22308 of 388960 | steps hit: [ 0 10]
SJI pixel ROI -> AIA: IncompatibleAttribute (SJI gWCS needs time to invert; expected)
round-trip FITS: AIAMap 2021-09-05T00:18:33.640 PixelPair(x=<Quantity 800. pix>, y=<Quantity 800. pix>)
dc.links: 20
ImageViewer layers: [('ImageLayerArtist', True), ('ImageSubsetLayerArtist', True), ('ImageSubsetLayerArtist', False)]
```

Synthetic map used (this is what the test writes to `tmp_path`):

```python
ref = SkyCoord(lon.mean() * u.arcsec, lat.mean() * u.arcsec, frame=Helioprojective(obstime=t0, observer="earth"))
hdr = make_fitswcs_header(np.zeros((800, 800)), ref, scale=[0.6, 0.6] * u.arcsec / u.pix, instrument="AIA",
                          telescope="SDO/AIA", observatory="SDO", wavelength=171 * u.AA, exposure=2 * u.s)
aia = sunpy.map.Map(np.random.default_rng(0).random((800, 800)), hdr)   # -> AIAMap, cmap sdoaia171
```

Readings: the correlation-matrix rule picks (x, y) for SJI, (slit, step) for rasters and stacks; the SJI polygon equals the first exposure (the drifting sit-and-stare would otherwise smear the bbox to lon -8.1, see `wp7_sdo.py` run in Pitfalls); the FOV subset (100 AIA px = 6" x 7" at 0.6"/px) propagates through the physical-type links to 1371 of 1480 SJI pixels in frame 0 and to raster steps 0-10, and to 0 pixels in the last SJI frame (4.8 h later, drifted out). The `propagate_with_solar_surface` block is a no-op when the image is co-temporal; with a map 3 h later (`wp7_sdo.py`): `plain Tx [-58.2 -52.0 ...] | propagated Tx [-30.5 -24.2 ...]`, i.e. the rotation is applied only inside the `with`.

(checker) Same flow with WP1's rewritten `_GlueWCS` and `link_hpc` (code copied from `briefs/wp1-linking.md` L92-224 into a scratch module):

```
WP1 _GlueWCS on cutout: names ['Helioprojective Longitude', 'Helioprojective Latitude'] units ('arcsec', 'arcsec')
  p2w(0,0): [-156.28 -503.24] | w2p round trip of (10,20): [10. 20.]
  high-level pixel_to_world(10,20): SkyCoord -150.283 arcsec -491.243 arcsec | back: [10. 20.]
link_hpc (WP1 code, AIA in WP1 _GlueWCS) links: 2 | FOV on SJI frame 0: 1371 last frame: 0 | second call: []
```

### 5. Polygon vs irispy `to_maps(0)` corners (`wp7_corners.py`)

```
fov_polygon lon: [-56.413 -50.425 -50.352 -56.34 ] | to_maps(0) Tx: [-56.337 -50.349 -50.276 -56.264]
fov_polygon lat: [-402.953 -403.021 -396.534 -396.466] | to_maps(0) Ty: [-402.863 -402.93  -396.443 -396.375]
match: False False
```

Difference 0.076"/0.09" = about half an SJI pixel (0.166"), a pixel-convention difference between irispy's gWCS and its FITS map. Test with `atol=0.2`.

### 6. Optional GOES time <-> raster `Time` link and line style (`wp7_timelink.py`)

```python
goes.add_component(t, "time")  # Data.add_component wraps datetime64 in DateTimeComponent itself
dc.add_link(LinkSame(goes.id["time"], ras.id["Time"]))
dc.new_subset_group("hour 1-2", RangeSubsetState(np.datetime64("2021-09-05T01:00:00"), np.datetime64("2021-09-05T02:00:00"), goes.id["time"]))
ls = sv.layers[0].state; ls.line_visible, ls.markers_visible = True, False
```

```
raster Time: datetime64[ns] 2021-09-05T00:18:37.750000000 2021-09-05T05:07:31.400000000
GOES time range -> raster steps 27 .. 65 ( 39 steps ) of 187
layer state attrs ok: True False | y label: xrsb | layers: ['ScatterLayerArtist', 'ScatterLayerArtist']
```

### 7. Component order and the Profile viewer (`wp7_profile_order.py`)

```
time-first -> Profile viewer FAILS: UFuncTypeError
time-last -> Profile viewer OK; x choices: ['Coordinate components', 'Pixel Axis 0 [x]'] y attribute: xrsa
```

Hence `xrsa`, `xrsb` first and `time` last in `goes_xrs`.

### 8. Warnings emitted by the recipes (`wp7_warn.py`, `warnings.simplefilter("always")`)

```
WARNING: SunpyUserWarning: Importing sunpy.timeseries without its extra dependencies may result in errors.
The following packages are not installed: ['cdflib>=1.3.2'] ...
== TimeSeries ==            (none)
== synthetic AIA map + save/load ==   (none)
== IRIS load + corners + transform + submap + Data ==   (none)
```

Only the missing-`cdflib` warning, which the full `sunpy[timeseries]` extra removes. Nothing else to add to `pytest.ini` `filterwarnings`. (checker) `sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits"))`, a real cropped level-1 file, also loads as `AIAMap` 128x128 with zero warnings.

### 9. (checker) The step-2 module under pytest with the repo `pytest.ini` (warnings as errors) and ruff

The module text from step 2 (with `link_hpc` defined locally from WP1's brief) and the test file below, in a scratch directory with a `conftest.py` that re-exports `glue_solar.conftest.irispy_test_files`:

```
$ HOME=<scratch>/home-wp7chk GLUE_TESTING=True QT_QPA_PLATFORM=offscreen MPLBACKEND=agg \
  PYTHONPATH=/Users/nabil/.cache/uv/archive-v0/jm144Mb-aATYC6j0:<scratch>/wp7chk \
  .venv/bin/python -m pytest -c pytest.ini --rootdir=<scratch>/wp7chk -o addopts="" -p no:cacheprovider \
  -W "ignore:Importing sunpy.timeseries" test_context_chk.py -q --durations=3
0.65s call     test_context_chk.py::test_goes_context_shows_message_on_failure
0.37s call     test_context_chk.py::test_sdo_context_end_to_end
0.35s call     test_context_chk.py::test_fov_polygon_sji_first_exposure
10 passed, 2 warnings in 2.01s
$ ruff check --config .ruff.toml --no-cache context_chk.py
All checks passed!
```

(The 2 warnings are `PytestConfigWarning: Unknown config option: doctest_plus/text_file_format`, from running outside the repo without `-p doctestplus`; the `-W "ignore:Importing sunpy.timeseries"` is only needed until the `sunpy[timeseries]` extra is installed.)

## Tests to add

`glue_solar/tests/test_context.py`, verbatim what passed today (rename the import from `context_chk` to `glue_solar.sources.context`). Fixtures: `irispy_test_files` (real files, `glue_solar/conftest.py:94-101`), `tmp_path`, `monkeypatch`. No network: `glue_solar.sources.context.Fido` is replaced with a `types.SimpleNamespace(search=..., fetch=...)`; `Fido.fetch` stubs return a `parfive.Results()` filled with `results.append(path=str(p), url=f"file://{p}")` (keyword-only, verified). (checker) The 2021 raster `r00000` file exists twice in irispy's test tree, under `sns/` and `raster/`; only the `sns/` copy loads. `raster_data([the raster/ copy], ["Mg II k 2796"])` raises `ValueError: Expected 187 NUV source filename rows, found 1872` on its own (verified today, `irispy/io/spectrograph.py:36`), so select by `str(f).endswith("sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")`. The SJI 1400 2021 file exists once (`sns/`).

```python
import types

import numpy as np
import parfive
import pytest
from glue.config import menubar_plugin
from glue.core import Data, DataCollection
from irispy.io import read_files

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable

import sunpy.data.test
import sunpy.map
from sunpy.coordinates import Helioprojective
from sunpy.map.header_helper import make_fitswcs_header

from glue_solar.sources import context
from glue_solar.sources.context import aia_context, fov_polygon, goes_xrs
from glue_solar.sources.loaders.iris import _GlueWCS, image_data, link_hpc, raster_data

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"


def _results(*paths):
    results = parfive.Results()
    for path in paths:
        results.append(path=str(path), url=f"file://{path}")
    return results


def _sji(files):
    return image_data(str(next(f for f in files if f.name == SJI)))


def _synthetic_aia(sji, path):
    """An 800x800 AIA 171 map centred on the SJI field of view at STARTOBS, saved to ``path``."""
    lon, lat = fov_polygon(sji)
    frame = Helioprojective(obstime=str(sji.meta["STARTOBS"]), observer="earth")
    ref = SkyCoord(lon.mean() * u.arcsec, lat.mean() * u.arcsec, frame=frame)
    hdr = make_fitswcs_header(
        np.zeros((800, 800)), ref, scale=[0.6, 0.6] * u.arcsec / u.pix, instrument="AIA", telescope="SDO/AIA",
        observatory="SDO", wavelength=171 * u.AA, exposure=2 * u.s,
    )
    sunpy.map.Map(np.random.default_rng(0).random((800, 800)), hdr).save(path)
    return types.SimpleNamespace(search=lambda *a: None, fetch=lambda *a, **k: _results(path))


def test_setup_registers_context_actions():
    labels = [label for label, _ in menubar_plugin]
    assert "IRIS: GOES context…" in labels
    assert "IRIS: SDO context…" in labels


def test_goes_xrs_reads_one_satellite(monkeypatch):
    fetched = []

    def fetch(table, progress):
        fetched.append(table)
        return _results(sunpy.data.test.get_test_filepath("sci_xrsf-l2-avg1m_g16_d20210101_truncated.nc"))

    monkeypatch.setattr(
        context, "Fido", types.SimpleNamespace(search=lambda *a: [QTable({"SatelliteNumber": ["16", "17"]})], fetch=fetch)
    )
    data = goes_xrs("2021-01-01T22:30:00", "2021-01-01T23:10:00")
    assert len(fetched) == 1
    assert len(fetched[0]) == 1
    assert fetched[0]["SatelliteNumber"][0] == "16"
    assert data.label == "GOES-16 XRS"
    assert data.shape == (41,)
    assert [str(c) for c in data.main_components] == ["xrsa", "xrsb", "time"]
    assert data.get_kind(data.id["time"]) == "datetime"
    assert data.get_component(data.id["xrsb"]).units == "W / m2"
    assert data["time"][0] == np.datetime64("2021-01-01T22:30:00")
    assert data["time"][-1] == np.datetime64("2021-01-01T23:10:00")


def test_goes_xrs_without_data_raises(monkeypatch):
    called = []
    monkeypatch.setattr(
        context,
        "Fido",
        types.SimpleNamespace(search=lambda *a: [QTable({"SatelliteNumber": []})], fetch=lambda *a, **k: called.append(a)),
    )
    with pytest.raises(ValueError, match="No GOES XRS data"):
        goes_xrs("2021-01-01T22:30:00", "2021-01-01T23:10:00")
    assert not called


def test_fov_polygon_sji_first_exposure(irispy_test_files):
    path = next(f for f in irispy_test_files if f.name == SJI)
    lon, lat = fov_polygon(image_data(str(path)))
    m0 = read_files(path, memmap=False, uncertainty=False).to_maps(0)
    ny, nx = m0.data.shape
    expected = m0.wcs.pixel_to_world([0, nx - 1, nx - 1, 0], [0, 0, ny - 1, ny - 1])
    np.testing.assert_allclose(lon, expected.Tx.to_value(u.arcsec), atol=0.2)
    np.testing.assert_allclose(lat, expected.Ty.to_value(u.arcsec), atol=0.2)
    assert lon.max() < -50


def test_fov_polygon_raster_uses_slit_and_step(irispy_test_files):
    path = next(f for f in irispy_test_files if str(f).endswith(RASTER))
    data = raster_data([str(path)], ["Mg II k 2796"])[0]
    lon, lat = fov_polygon(data)
    assert np.ptp(lon) == pytest.approx(42.3, abs=0.5)
    assert np.ptp(lat) == pytest.approx(6.9, abs=0.5)
    assert len(set(zip(lon.round(2), lat.round(2)))) == 4


def test_fov_polygon_stack_uses_slit_and_step(irispy_test_files):
    paths = sorted(str(f) for f in irispy_test_files if "3860258481_raster_t000_r0000" in f.name)[:2]
    data = raster_data(paths, ["C II 1336"], stack=True)[0]
    assert data.shape == (2, 8, 109, 17)
    lon, lat = fov_polygon(data)
    assert np.ptp(lon) == pytest.approx(14.3, abs=0.5)
    assert np.ptp(lat) == pytest.approx(18.0, abs=0.5)


def test_fov_polygon_rejects_non_spatial_data():
    with pytest.raises(ValueError, match="no helioprojective coordinates"):
        fov_polygon(Data(x=np.zeros((3, 3))))


def test_aia_context_from_local_map(monkeypatch, tmp_path, irispy_test_files):
    sji = _sji(irispy_test_files)
    monkeypatch.setattr(context, "Fido", _synthetic_aia(sji, tmp_path / "aia.fits"))
    ctx, fov = aia_context(sji)
    assert isinstance(ctx.coords, _GlueWCS)
    assert [ctx.get_component(c).units for c in ctx.world_component_ids] == ["arcsec", "arcsec"]
    assert ctx.style.preferred_cmap.name == "sdoaia171"
    assert ctx.shape == (346, 344)
    assert ctx.label.startswith("AIA_171_context-3620258102-2021-09-05T00:18:33")
    dc = DataCollection([ctx, sji])
    dc.new_subset_group("FOV", fov)
    assert 80 <= ctx.subsets[0].to_mask().sum() <= 130
    dc.add_link(link_hpc(dc))
    mask = sji.subsets[0].to_mask()
    assert mask[0].sum() > 1300
    assert mask[-1].sum() == 0


def test_goes_context_shows_message_on_failure(monkeypatch, irispy_test_files):
    from glue_qt.app import GlueApplication
    from qtpy import QtWidgets

    sji = _sji(irispy_test_files)
    app = GlueApplication(DataCollection([sji]))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", staticmethod(lambda *a, **k: (sji.label, True)))

    def boom(*args):
        raise OSError("boom")

    monkeypatch.setattr(context, "goes_xrs", boom)
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", staticmethod(lambda parent, title, text: shown.append(text)))
    context.goes_context(app.session, app.data_collection)
    assert shown
    assert "boom" in shown[0]
    assert len(app.data_collection) == 1
    app.close()


def test_sdo_context_end_to_end(monkeypatch, tmp_path, irispy_test_files):
    """The full menubar action offscreen: dataset picker stubbed, Fido stubbed, viewer opened, FOV subset drawn."""
    from glue_qt.app import GlueApplication
    from qtpy import QtWidgets

    sji = _sji(irispy_test_files)
    monkeypatch.setattr(context, "Fido", _synthetic_aia(sji, tmp_path / "aia.fits"))
    app = GlueApplication(DataCollection([sji]))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", staticmethod(lambda *a, **k: (sji.label, True)))
    context.sdo_context(app.session, app.data_collection)
    assert len(app.data_collection) == 2
    assert [sg.label for sg in app.data_collection.subset_groups] == ["IRIS FOV"]
    assert len(app.data_collection.links) >= 2
    viewer = app.viewers[0][-1]
    viewer.figure.canvas.draw()
    assert [type(layer).__name__ for layer in viewer.layers] == ["ImageLayerArtist", "ImageSubsetLayerArtist"]
    app.close()
```

Notes: the two `GlueApplication` tests ran inline in today's check (the `_synthetic_aia` helper is a checker refactor of two verbatim copies of the same 8 lines; the assertions are unchanged). `test_setup_registers_context_actions` makes the `test_plugin.py` label extension unnecessary. Before WP1 merges, `link_hpc` in `test_aia_context_from_local_map` is the stand-in loop from step 2.

Run: `pytest -o addopts="" glue_solar/tests/test_context.py -q` (offscreen via `conftest.py`), then the full `pytest` (warnings are errors). (checker) Until step 1 is done, add `-W "ignore:Importing sunpy.timeseries"` or the module import fails on the `cdflib` warning.

## Pitfalls (verified)

- **`sunpy.timeseries` import fails without the extra.** `ModuleNotFoundError: No module named 'h5netcdf'` today (`sunpy/timeseries/sources/goes.py:7` imports it at module level). With `h5netcdf` alone, `SunpyUserWarning ... ['cdflib>=1.3.2']` is raised at import, and `pytest.ini` `filterwarnings = error` would turn `import glue_solar` into a failure. Use the full `sunpy[timeseries]` extra (sunpy 8.0 metadata: cdflib, h5netcdf, h5py, matplotlib, pandas).
- **Datetime axis labels are wrong on stock glue.** `num2date(xlim)` gives year 3990 and labels the day as "02" for 2021-01-01 data (run 1). `rcParams["date.epoch"] = "0000-12-31T00:00:00"` fixes it, but only if set before the first date conversion in the process; `matplotlib.dates._epoch` was still `None` after `GlueApplication()` returned, so `setup()` qualifies. Do not call `matplotlib.dates.set_epoch` (raises `RuntimeError` if the epoch is already in use); the rcParam never raises.
- **Profile viewer.** A Data whose first component is datetime64 cannot even be added (`UFuncNoLoopError` from `glue/viewers/profile/state.py:331 _reference_data_changed -> :161 reset_limits -> :227 _reset_y_limits`, re-run of `v_goes_c.py` today). With `time` added last the Profile viewer accepts the dataset (run 7). The light curve itself is still a Scatter viewer plot: Profile `x_att` offers only pixel/world coordinates.
- **`Component(datetime64_array)` raises** `TypeError: DateTimeComponent should be used instead of Component`; use `data.add_component(array, label)` which wraps it (run 6; same idiom as `loaders/iris.py:84`).
- **Raw sunpy-map coords link wrongly.** `_parse_sunpy_map` leaves the map WCS in degrees (`world_axis_units ['deg','deg']`, labels `Hplt`/`Hpln`). A physical-type `LinkSame` to IRIS arcsec components then propagates the FOV subset to `0 of 91760` SJI pixels (`wp7_sdo.py` run: "FOV subset on SJI -> 0"). Wrapping with `_GlueWCS(cutout.wcs)` gives arcsec and the counts in run 4. (checker) After WP1 the wrap is also what makes `link_hpc` consider the dataset at all (it skips non-`_GlueWCS` coords). If WP1 changes `_parse_sunpy_map` to wrap in `_GlueWCS` itself (its brief L637 leaves that to this WP), drop the explicit line.
- **All-corner bounding boxes smear the FOV.** Using every pixel corner including the time axis gives `centres bbox: [-56.4 -8.1 ...]` for the 4.8 h rotation-tracked SJI (`wp7_sdo.py`), i.e. 48" of drift. Fix non-spatial pixel axes at 0 (the correlation-matrix rule, run 4).
- **gWCS returns NaN at pixel edges.** Corners at -0.5/n-0.5 give `nan corners: 4` for the SJI gWCS (bounding box); use pixel centres (ponytail, half a pixel).
- **`fov_polygon` on data without HPC coords.** (checker) Without the guard, `Data(x=...)` (coords `None`) gave `AttributeError: 'NoneType' object has no attribute 'world_axis_physical_types'`; the two-line guard in step 2 turns it into the `ValueError` the acceptance criteria ask for (test `test_fov_polygon_rejects_non_spatial_data`).
- **SJI pixel ROI -> AIA is `IncompatibleAttribute`.** The SJI gWCS cannot be inverted without its time pixel, so selections drawn on the SJI image do not reach the AIA context (run 4, matches the P1.4 finding). Selections drawn on the AIA image or the raster propagate; the "IRIS FOV" subset is defined on AIA pixels for that reason.
- **glue-core `RegionData` crashes on WCS data** (critic §3.4, re-run of `cc_region.py` today): `glue/core/data_region.py:219 conv_function -> component_link.py:393 -> coordinate_helpers.py:42 pixel2world_single_axis: AttributeError: 'tuple' object has no attribute 'shape'`. Keep the `PolygonalROI` subset.
- **`XRSClient` lists every satellite** for the interval (`goes.py:150-170`), three `Scraper` listings for post-2017 dates, and `Scraper.filelist` needs network even for search. Pick one satellite before fetching (run 3) or the concatenated series interleaves satellites.
- **`Fido.fetch` writes into sunpy's `download_dir`** (`<HOME>/sunpy/data` by default, run 3). Fine; mention in the docs. A full-disk AIA level-1 file is ~12 MB, 4096x4096; `submap` before `_parse_sunpy_map`.
- **Session save of the AIA context Data fails on main** independent of WP7: `maps.py:30` sets `preferred_cmap` to a Colormap object -> `TypeError: Object of type LinearSegmentedColormap is not JSON serializable` (session-serialization P3.6-cmap). WP6 owns the fix.
- **`parfive.Results.append` is keyword-only** (`(self, *, path, url)`), matters for the test stubs.
- **Offscreen runs need `GLUE_TESTING=True`**, otherwise `messagebox_on_error` blocks in a modal dialog (session-serialization verifier note; `glue_qt/utils/decorators.py:56-61`).
- **irispy duplicate test files**: (checker) the `raster/` copy of the 2021 `r00000` file fails to load on its own (`found 1872`); use the `sns/` copy, see Tests.

## Acceptance criteria

- [ ] `pyproject.toml` requires `sunpy[map,net,timeseries]>=6.0.0`; `python -c "import glue_solar"` is warning-free.
- [ ] "IRIS: GOES context…" and "IRIS: SDO context…" appear under Plugins; both do nothing without a network round-trip unless the user presses OK in the picker; failures produce a `QMessageBox.critical`, never a traceback dialog, and leave the data collection unchanged.
- [ ] GOES: one satellite only; Data label `GOES-<n> XRS`; components `xrsa`, `xrsb` (W / m2), `time` (datetime); truncated to STARTOBS..ENDOBS; Scatter viewer opened with `x=time`, `y=xrsb`, `y_log=True`, line visible; tick labels show the observation date (not year 3990); a raster/stack `Time` component is linked so a time range selects raster steps.
- [ ] SDO: AIA 171 nearest STARTOBS via VSO (`near=`), cut to the FOV of the first exposure plus 100"; Data coords are `_GlueWCS` (arcsec); `preferred_cmap` `sdoaia171`; "IRIS FOV" subset group visible on the AIA Image viewer; `data_collection.add_link(link_hpc(data_collection))` pairs the cutout with the IRIS datasets so the FOV subset shows on SJI frame 0 and the raster, and an AIA rectangle selects IRIS pixels.
- [ ] `fov_polygon` works for SJI (time, y, x), rasters (step, slit, wl) and stacks (scan, step, slit, wl) and raises a clear `ValueError` otherwise (coords `None`, no HPC axes, or no two-dimensional spatial footprint).
- [ ] The 10 tests in `test_context.py` pass with `pytest` (warnings-as-errors) and without network; the existing 27 tests in `test_importer.py`, `test_scan.py`, `test_plugin.py` still pass (27 collected today).
- [ ] `pre-commit run --all-files` clean (ruff E/F/W/UP/PT/I, line length 120).
- [ ] Docs and changelog fragment added; the datetime-epoch workaround has a comment naming the glue-core function it patches around.

## Dropped / out of scope

- Porting irispy `examples/coalign/01` and `02`: they need `aiapy` + `sunkit_image` (not installed, not dependencies) and do cross-correlation/pointing updates, which the LMSAL `aia_l2` cutouts already provide.
- `reproject_to` of AIA onto the IRIS WCS: works (audit demo) but adds a 12 MB reproject for no display gain; the submap plus links already overlays.
- HMI or other AIA bands: one `wavelength=` keyword away; not exposed in the UI (YAGNI).
- JSOC cutout export (`a.jsoc.Cutout`): needs a registered notify email.
- GOES flare list / event overlay (HEK): not in the plan.
- A 5-point FOV line-scatter Data layer: the subset outline does the job without a second dataset or link.
- Threading the download off the GUI thread: wait cursor only; ponytail, add a `QThread` if users complain about multi-minute VSO waits.
- Upstream glue-core epoch fix: optional later PR; the rcParams line stays until a glue release contains it.
- Picking the "selected" layer from `app._layer_widget.selected_layers()`: private API; the `QInputDialog` picker doubles as the consent button.
- Extending `test_plugin.py::test_setup_registers_hooks`: `test_context.py` already asserts both labels.

## Docs

- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: new section after "Opening a single file" (`:48-52`, before "Linking" `:54`):

  ```
  Context data (network)
  ----------------------

  Two entries in the "Plugins" menu fetch context for a loaded IRIS observation through sunpy. Both
  first ask which dataset to use; pressing OK is what starts the download (into sunpy's download
  directory, ``~/sunpy/data`` by default), and a failure only shows a message.

  - "IRIS: GOES context..." downloads the GOES XRS 1-minute averages between ``STARTOBS`` and
    ``ENDOBS`` from NOAA and adds them as a dataset (``xrsa``, ``xrsb`` in W / m2, ``time``), opened
    in a Scatter viewer with a logarithmic flux axis. When the chosen dataset is a raster or a stack,
    its ``Time`` component is linked to the light curve, so a time range selected on the curve
    highlights the corresponding raster steps.
  - "IRIS: SDO context..." downloads the AIA 171 image nearest ``STARTOBS`` from the VSO, cuts it to
    the IRIS field of view plus 100 arcsec, adds it as a dataset (helioprojective coordinates in
    arcsec, linked to the IRIS datasets) and outlines the field of view of the first exposure as the
    "IRIS FOV" subset in an Image viewer. Selections drawn on the AIA image propagate to the raster
    and to the slit-jaw cube; selections drawn on the slit-jaw cube cannot be mapped back onto AIA.
    The co-aligned ``aia_l2`` cutouts listed by the browser stay the per-exposure aligned product.
  ```

- `docs/api_reference.rst`: add `.. automodapi:: glue_solar.sources.context` with `:no-inheritance-diagram:` after the `glue_solar.sources.maps` block (`:10-11`; automodapi writes `docs/api/glue_solar.sources.context.*.rst` on build).
- `changelog/<PR>.feature.rst`: "Two new "Plugins" menu entries fetch context for a loaded IRIS observation on request: "IRIS: GOES context…" adds the GOES XRS light curve spanning the observation (NOAA, via `sunpy.net.Fido`) and plots it, and "IRIS: SDO context…" adds the AIA 171 image nearest the start (VSO), cut around the IRIS field of view, with the field of view outlined as a subset. ``sunpy[timeseries]`` is now a dependency."
- `IRIS_GLUE_GAP_PLAN.md` §1.5 (L82-85): "Profile/Scatter viewer" -> "Scatter viewer"; add the `sunpy[timeseries]` dependency and the datetime-epoch workaround; §2.4 (L132-135): `propagate_with_solar_surface` is a context manager around the corner transform, VSO not JSOC, no aiapy/sunkit_image, the FOV is a `PolygonalROI` subset on the AIA cutout (no link needed for the outline; `link_hpc` by physical type for propagation), the AIA cutout must be wrapped in `_GlueWCS` (arcsec) to link; "Suggested order" (L190-199) row 3 stays "independent" but 2.4 depends on WP1.
- `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` L183 "GOES context | None | Missing" -> "glue-solar `IRIS: GOES context…` | Done (Scatter viewer)"; L184 "SDO pointing context ... no live SDO retrieval, rotation, limb context, or IRIS field-of-view overlay": "rotation" is not a gap for the aligned cutouts; after WP7 the remaining gap is full-disk/limb context beyond the 100" margin (a `margin=` keyword).


---

# WP8 - Browser filter and cancellable scan

**Goal.** Give the IRIS observation browser (`QtIRISImporter`) a one-line text filter over the observation rows and run `scan_directory` in a background `glue_qt.utils.Worker` with a cooperative "Stop scan" button, so mirror-scale trees (thousands of files) neither block the dialog nor have to be scanned to the end. Log-file listing (plan Phase 1.7) is dropped for good; the evidence is recorded below so nobody re-opens it.

## Current state (2026-09-02)

All on `/Users/nabil/Git/glue-solar`, branch `iris-observation-browser` (HEAD `d3a2bd3`, = PR glue-viz/glue-solar#44, open, CI green, no reviews). Nothing on the glue or glue-qt fork branches touches this area (verified by the audit and re-verified: `git diff main...macos-integration -- glue_qt/utils/threading.py` is empty).

- `glue_solar/sources/loaders/iris.py:205-211` `set_directory()` calls `scan_directory()` inline on the GUI thread, then `populate()` rebuilds the whole `QTreeWidget`.
- `glue_solar/sources/loaders/iris.py:186` recursive toggle re-enters `set_directory`; `iris.py:281` and `:284` (extract-archive branch of `finalize()`) re-enter it too.
- `glue_solar/sources/loaders/iris.py:213-249` `populate()`: top-level row columns are `[STARTOBS, OBSID, Description, XCEN, YCEN, SAT_ROT, Files]`; STARTOBS is ISO text (`2014-03-29T14:09:38`), so a substring filter is already a date filter.
- `glue_solar/sources/loaders/iris_loader.ui`: widgets are `directory`, `change`, `recursive`, `obs_tree`, `progress`, `stack`, `cancel`, `ok` only. No filter, no stop button. The `cancel` button at `iris.py:183` is dialog reject, not scan cancellation.
- `glue_solar/sources/loaders/scan.py:118-179` `scan_directory(root, recursive=True)`: single `for path in sorted(...)` loop at `:137`, one `fits.getheader` per FITS file, no progress or stop hook.
- `/Users/nabil/Git/glue-qt/glue_qt/utils/threading.py:8` `Worker(QtCore.QThread)` with `result`/`error` signals, exported as `glue_qt.utils.Worker` (`glue_qt/utils/__init__.py:9` `from .threading import *`). No cancel API of its own; `QThread.requestInterruption()/isInterruptionRequested()` provide a cooperative one. Precedent for the usage pattern: `glue_qt/viewers/profile/profile_tools.py:222-231` (`w = Worker(...)`, `self._fit_worker = w  # hold onto a reference`, `wait_for_fit()` calls `w.wait()`).
- Timing today: the user's real tree `/Users/nabil/DATA/IRIS` (140 files, 14 observations) scans in 0.5-0.6 s (0.57 s writer's run, 0.51 s checker's run), about 4 ms per file. Blocking is only noticeable on mirror-scale trees (10k files is about 40 s).
- `QProgressBar` semantics that matter here (verified, see Pitfalls): `setRange(0, 0)` resets the value to -1 when the current value is above the new maximum, and `text()` is empty whenever the value is invalid (below the minimum), not only while busy. `finalize()` leaves values between 0 and 100 behind (`iris.py:276`, `:290`, `:303`).
- Tests: `glue_solar/tests/test_importer.py` builds `QtIRISImporter(...)` and reads the tree synchronously in the `dialog` fixture (used by 4 tests) and in 4 tests that construct their own dialog; 8 of its 12 tests break once the scan is asynchronous (measured below).
- Env note: the venv has no `pytest-doctestplus`, so pytest needs `-o addopts=''` (pytest.ini's `--doctest-rst` is unknown otherwise). Reproduced today.

## Decisions already made

- Filter = one `QLineEdit` above the tree that hides top-level rows whose STARTOBS, OBSID or Description text does not contain the string (case-insensitive). No `QDateEdit`, no start/end widgets, no filename-pattern presets, no "recent searches". `2014-03` filters March 2014 because STARTOBS is ISO text (audit P1.1 recommendation, verifier agreed).
- Scan = `glue_qt.utils.Worker` (reuse, no new thread class), cooperative `stop` callable kwarg on `scan_directory` polled once per file, `Stop scan` button, busy progress bar (`setRange(0, 0)`) while scanning, tree repopulated from the `result` signal on the GUI thread (audit P1.1).
- Re-entrancy (recursive toggle, extract-archive rescan, Change...): a new `set_directory` cancels the running worker (`requestInterruption()` + `wait()`) before starting the next one; a stale result is ignored by a scan id.
- Stopping keeps what was found so far (partial list shown, progress text "Scan stopped"), so the user can pick from a half-scanned mirror. It does not raise.
- Hidden-but-ticked rows still load (`selected()` unchanged). Filtering only hides rows. Documented, tested.
- Log files: DROPPED (see "Dropped / out of scope"). The `_L2_STEM` regex would key them, but no public data has any.
- Existing tests: keep them, add `qtbot.waitUntil(lambda: not dialog.scanning)` at 7 places (exact list below). No synchronous code path is added to the dialog for tests; `scanning` is a public bool attribute.
- Independent of D1-D4 (the browser never touches WCS, units, moments or links). No dependency on WP1's Angstrom change. Merge-order note: WP1 rewrites `test_importer.py:176` (`world_axis_units == ("m", "arcsec", "arcsec", "")` becomes Angstrom); none of the 7 WP8 insertions touch that line, so either order merges cleanly.
- `set_directory` re-validates the progress bar (`setValue(0)` right after `setRange(0, 0)`) so that "Scan stopped", "Scan failed" and "Extraction failed" are visible after an earlier load left a value above 0 (checker finding, verified below; one line, one test).

## Dependencies / order

- Lands after PR #44 merges (branch from `main` then), or stacked on `iris-observation-browser` if #44 is still open. It edits `iris.py`, `iris_loader.ui`, `scan.py`, `test_importer.py`, `test_scan.py` from that PR.
- Needs nothing from glue-core/glue-qt forks: `Worker` and `QThread.requestInterruption` exist in released glue-qt (pyproject already requires `glue-qt[qt]>=0.4.0`; checked today: `https://raw.githubusercontent.com/glue-viz/glue-qt/v0.4.0/glue_qt/utils/threading.py` is HTTP 200 with `class Worker(QtCore.QThread)` at line 8, identical to the fork's file).
- Unblocks nothing else; the other WPs do not use the browser internals. Do it whenever; it is the smallest WP.

## Files to touch

- `glue_solar/sources/loaders/scan.py`: add `stop=lambda: False` kwarg to `scan_directory`, docstring line, `if stop(): break` at the top of the file loop. Partial results are still grouped and sorted by the code after the loop.
- `glue_solar/sources/loaders/iris_loader.ui`: new `filterLayout` (QLabel `filterLabel` "Filter:" + QLineEdit `filter`, placeholder text, clear button) inserted between `directoryLayout` and `obs_tree`; wrap `progress` in a new `progressLayout` with QPushButton `stop_scan` ("Stop scan", `enabled=false`).
- `glue_solar/sources/loaders/iris.py`: `import functools`; `from glue_qt.utils import Worker, get_qapp, load_ui`; in `__init__` connect `filter.textChanged`, `stop_scan.clicked`, `self.finished`; new attributes `worker`, `scanning`, `_scan_id`; rewrite `set_directory` (busy bar via `setRange(0, 0)` followed by `setValue(0)`); new `_stop_scan`, `_scan_over`, `_scanned`, `_scan_failed`, `_apply_filter`; `populate()` ends with `self._apply_filter()`.
- `glue_solar/tests/test_importer.py`: 7 `qtbot.waitUntil` insertions in existing tests; two extra assertions in `test_extract_archive_then_lists_its_windows`; new fixtures `slow_headers`, `populates`; 7 new tests.
- `glue_solar/tests/test_scan.py`: 1 new test for the `stop` kwarg.
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: one paragraph after the "Open it from the Plugins menu" paragraph.
- `changelog/<PR>.feature.rst`: one fragment.
- `IRIS_GLUE_GAP_PLAN.md`, `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`: row wording (see Docs).

## Step-by-step

1. Branch: `git switch -c browser-filter-and-stop main` (after #44 merges) or from `iris-observation-browser`.
2. `scan.py`: apply the diff in "Verified code / scan.py". Run `pytest glue_solar/tests/test_scan.py -o addopts=''`: still 12 passed (the default `stop` never fires).
3. `iris_loader.ui`: apply the diff in "Verified code / iris_loader.ui". Check it loads: `python -c "from glue_qt.utils import load_ui; from qtpy import QtWidgets; import glue_qt.utils as u; app=u.get_qapp(); d=QtWidgets.QDialog(); load_ui('glue_solar/sources/loaders/iris_loader.ui', d); print(d.filter, d.stop_scan)"` with `QT_QPA_PLATFORM=offscreen`.
4. `iris.py`: apply the class changes in "Verified code / iris.py (final form)". Remove nothing else. `populate()` gets one extra last line.
5. `test_importer.py`: insert the 7 waits (list in "Tests to add"), extend the extract test by two assertions, then add the fixtures and the 7 new tests. `test_scan.py`: add the `stop` test.
6. Run: `HOME=<scratch> QT_QPA_PLATFORM=offscreen MPLBACKEND=agg .venv/bin/python -m pytest glue_solar/tests/test_scan.py glue_solar/tests/test_importer.py -q -o addopts=''`. Expect 23 + 8 = 31 passed (12 in `test_scan.py`, 19 in `test_importer.py`). Run it three times; the stop/rescan tests are deterministic (they gate on a counted `getheader`, not on sleeps) but prove it.
7. Lint. Neither `ruff` nor `pre-commit`, `codespell`, `uvx` is on PATH or in the venv (checked today). Use the pre-commit cache binary that matches the pin `rev: "v0.16.1"` in `.pre-commit-config.yaml:4`: `/Users/nabil/.cache/pre-commit/repocrkdjdbp/py_env-python3.12/bin/ruff check --config .ruff.toml glue_solar` and `/Users/nabil/.cache/pre-commit/repohen6ncnv/py_env-python3.14/bin/codespell docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst changelog` (both ran today). Fallback: `.venv/bin/pip install ruff==0.16.1 codespell`.
8. Manual smoke on the real tree: `Plugins -> IRIS: browse observations...` on `/Users/nabil/DATA/IRIS`; type `2014-0` in Filter (3 of 14 rows stay), press Change... to a bigger folder while it scans, press Stop scan.
9. Docs + changelog + planning-doc row edits (Docs section). Open the PR; the changelog file name must match the PR number (gilesbot checks it).

## Verified code

Everything below was run today (2026-09-02) from the scratchpad with `HOME=<scratch>/home-wp8 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg` and `/Users/nabil/Git/glue-solar/.venv/bin/python`. Prototype files: `wp8_scan.py` (scan.py + stop), `wp8_loader.ui` (edited .ui), `wp8_proto.py` (the dialog methods as a subclass of the shipped `QtIRISImporter` so the repo stays untouched), `wp8_test_proto.py`, `wp8_test_shipped.py`, `wp8_test_importer_nowait.py`, `wp8_test_importer_wait.py`, `wp8_lifetime.py`, `wp8_lifetime2.py`. Checker re-run (2026-09-02, `HOME=<scratch>/home-wp8-check`): every block below was executed again; where numbers differ both are given. Checker files: `wp8_chk_timing.py`, `wp8_chk_worker.py`, `wp8_chk_realtree.py`, `wp8_chk_slotargs.py` (slot-arity and progress-text probes), `wp8_chk_proto_fix.py` (prototype + the `setValue(0)` line), `wp8_chk_test_scan.py` (repo `test_scan.py` pointed at `wp8_scan` + the stop test), `wp8_chk_test_importer_full.py` / `wp8_chk_test_importer_fixed.py` (the shipped-form `test_importer.py`: 7 waits + fixtures + all new tests, against the unfixed / fixed prototype), `wp8_chk_test_text.py` (the visibility bug, parametrised over both prototypes).

### Baseline, timing, Worker availability

```
$ .venv/bin/python -m pytest glue_solar/tests/test_scan.py glue_solar/tests/test_importer.py -q -o addopts=''
23 passed, 2 warnings in 1.49s

$ python -c "scan_directory('/Users/nabil/DATA/IRIS') timed"        # writer
14 observations 130 files 0 archives 0.57 s
total files on disk 140 4.1 ms/file
$ python wp8_chk_timing.py                                              # checker
14 observations 130 files 0 archives 0.51 s
total files on disk 140 3.6 ms/file

$ python -c "from glue_qt.utils import Worker; ..."
from glue_qt.utils import Worker -> <class 'glue_qt.utils.threading.Worker'> | glue 1.27.0
waitUntil (self, callback: collections.abc.Callable[[], bool | None], *, timeout: int = 5000) -> None
PyQt6 6.11.0
True True        # 'requestInterruption' in dir(QThread), 'isInterruptionRequested' in dir(Worker)
```

### scan.py (diff, ran as `wp8_scan.py`)

```diff
-def scan_directory(root, recursive=True):
+def scan_directory(root, recursive=True, stop=lambda: False):
     """
     Group every IRIS Level 2 file below ``root`` into `Observation` objects.
@@
     recursive : bool
         Descend into subdirectories.
+    stop : callable, optional
+        Polled once per file; return `True` to stop early and get what was found so far.
@@
     for path in sorted(p for p in paths if p.is_file()):
+        if stop():
+            break
         name = strip_pooch(path.name)
```

`ruff check --config .ruff.toml wp8_scan.py` -> `All checks passed!` (checker: re-run with ruff 0.16.1 and 0.16.3 from `~/.cache/pre-commit`, no findings for `wp8_scan.py`; `wp8_proto.py` reports only `I001` on its prototype-only `import wp8_scan` line, which does not exist in the shipped `iris.py`).

`# ponytail:` the directory walk (`sorted(root.rglob("*"))`) still runs to completion before the first poll; on a slow network mount that walk itself is the ceiling. Upgrade path: poll inside the generator too. Not needed for local mirrors (the header reads dominate at 4 ms/file).

### iris_loader.ui (diff, ran as `wp8_loader.ui`)

```diff
@@ after </item> closing directoryLayout, before obs_tree
+   <item>
+    <layout class="QHBoxLayout" name="filterLayout">
+     <item>
+      <widget class="QLabel" name="filterLabel">
+       <property name="text">
+        <string>Filter:</string>
+       </property>
+      </widget>
+     </item>
+     <item>
+      <widget class="QLineEdit" name="filter">
+       <property name="placeholderText">
+        <string>Show observations whose start time, OBSID or description contains this text, e.g. 2014-03</string>
+       </property>
+       <property name="clearButtonEnabled">
+        <bool>true</bool>
+       </property>
+      </widget>
+     </item>
+    </layout>
+   </item>
@@ the progress item
-    <widget class="QProgressBar" name="progress">
-     <property name="value">
-      <number>0</number>
-     </property>
-    </widget>
+    <layout class="QHBoxLayout" name="progressLayout">
+     <item>
+      <widget class="QProgressBar" name="progress">
+       <property name="value">
+        <number>0</number>
+       </property>
+      </widget>
+     </item>
+     <item>
+      <widget class="QPushButton" name="stop_scan">
+       <property name="enabled">
+        <bool>false</bool>
+       </property>
+       <property name="text">
+        <string>Stop scan</string>
+       </property>
+      </widget>
+     </item>
+    </layout>
```

### iris.py (final form; identical logic to the verified `wp8_proto.py` subclass plus the `setValue(0)` line verified as `wp8_chk_proto_fix.py`, minus the prototype-only `populate_threads` list)

```python
import functools                                            # new
from glue_qt.utils import Worker, get_qapp, load_ui         # Worker is new

class QtIRISImporter(QtWidgets.QDialog):
    def __init__(self, directory=None, parent=None):
        super().__init__(parent)
        self.ui = load_ui(UI_MAIN, self)
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.finalize)
        self.change.clicked.connect(self.choose_directory)
        self.recursive.toggled.connect(lambda _checked: self.set_directory(self.directory.text()))
        self.filter.textChanged.connect(self._apply_filter)
        self.stop_scan.clicked.connect(self._stop_scan)
        self.finished.connect(self._stop_scan)  # closing the dialog never leaves a QThread running
        self.observations = []
        self.datasets = []
        self.first_image = None
        self._payloads = []
        self.worker = None
        self.scanning = False
        self._scan_id = 0
        self.stack.setToolTip(...)  # unchanged
        if directory:
            self.set_directory(directory)

    def set_directory(self, directory):
        if not directory:
            return
        self.directory.setText(str(directory))
        QSettings(*_SETTINGS).setValue(_LAST_DIR, str(directory))
        self._stop_scan()
        self._scan_id += 1  # a result from the scan just cancelled is ignored by id
        self.worker = Worker(scan_directory, str(directory), recursive=self.recursive.isChecked())
        self.worker.kwargs["stop"] = self.worker.isInterruptionRequested
        self.worker.result.connect(functools.partial(self._scanned, self._scan_id))
        self.worker.error.connect(functools.partial(self._scan_failed, self._scan_id))
        self.scanning = True
        self.progress.setRange(0, 0)  # busy
        self.progress.setValue(0)  # setRange(0, 0) invalidates a value above 0; an invalid value renders no text
        self.progress.setFormat("%p%")
        self.stop_scan.setEnabled(True)
        self.worker.start()

    def _stop_scan(self, *_args):  # *_args: clicked(bool) and finished(int) both land here
        if self.scanning:
            self.worker.requestInterruption()
            self.worker.wait()  # at most one header read; keeps the Worker alive until its thread is done
            self.progress.setFormat("Scan stopped")

    def _scan_over(self, scan_id):
        if scan_id != self._scan_id:
            return False
        self.scanning = False
        self.progress.setRange(0, 100)
        self.stop_scan.setEnabled(False)
        return True

    def _scanned(self, scan_id, observations):
        if self._scan_over(scan_id):
            self.observations = observations
            self.populate()

    def _scan_failed(self, scan_id, exc_info):
        if self._scan_over(scan_id):
            self.progress.setFormat(f"Scan failed: {exc_info[1]}")

    def populate(self):
        ...  # unchanged body
        for column in range(self.obs_tree.columnCount()):
            self.obs_tree.resizeColumnToContents(column)
        self._apply_filter()  # new last line: the filter survives rescans

    def _apply_filter(self):
        text = self.filter.text().casefold()
        for i in range(self.obs_tree.topLevelItemCount()):
            item = self.obs_tree.topLevelItem(i)
            item.setHidden(text not in " ".join(item.text(c) for c in range(3)).casefold())
```

Why each piece exists (all exercised by the tests below): `_scan_id` + `functools.partial` identify results without `QObject.sender()` (no dangling-sender risk after the old Worker is garbage-collected); `wait()` before replacing `self.worker` so the old thread is finished when its Python wrapper dies; `self.finished -> _stop_scan` covers accept/reject/window close while scanning; `_scan_over` only calls `setRange(0, 100)`, so the "Extracted N archive(s)" text that `finalize()` writes after `set_directory()` is not clobbered by the rescan result; `setFormat("%p%")` in `set_directory` resets a previous "Scan stopped"/"Scan failed" text; `setValue(0)` right after `setRange(0, 0)` is accepted even though min == max (Qt skips the range check when both are 0) and keeps the bar's value valid, so the text written later by `_stop_scan`, `_scan_failed` or `finalize()`'s "Extraction failed" is actually rendered (the `finalize()` extract branch still writes its own `setValue(100)` after `set_directory()`, so "Extracted N archive(s)" keeps value 100; verified in the extended extract test).

Ruff (checker, 0.16.1 pinned and 0.16.3, `--config .ruff.toml`): the shipped-form test module `wp8_chk_test_importer_fixed.py` + `wp8_chk_test_scan.py` report only `F811` (18x, the explicit `iris_tree`/`irispy_test_files` fixture imports that the prototype needs and the repo tests get from conftest) and `I001` (2x, the prototype import lines). No finding in any test body, fixture or the dialog code.

### Prototype tests (8 tests, run three times)

```
$ pytest wp8_test_proto.py -c /Users/nabil/Git/glue-solar/pytest.ini --rootdir=. -o addopts='' -o testpaths= -q   (x3)
8 passed, 2 warnings in 3.10s
8 passed, 2 warnings in 3.11s
8 passed, 2 warnings in 3.05s
$ pytest wp8_test_shipped.py ... -q      # the two tests rewritten with monkeypatch instead of a prototype attribute
2 passed, 2 warnings in 2.67s

# checker re-run: 8 passed x3 (3.05s, 3.01s, 3.02s); shipped: 2 passed

# checker: the whole shipped-form suite (repo test_scan.py + stop test, repo test_importer.py + 7 waits + 2 extract assertions + 7 new tests)
$ pytest wp8_chk_test_scan.py wp8_chk_test_importer_fixed.py -c /Users/nabil/Git/glue-solar/pytest.ini --rootdir=. -o addopts='' -o testpaths= -q   (x3, stderr kept)
31 passed, 2 warnings in 4.60s    # grep -c 'QThread: Destroyed' -> 0
31 passed, 2 warnings in 4.57s    # 0
31 passed, 2 warnings in 4.55s    # 0
# same suite without the setValue(0) line and without the visibility test (wp8_chk_test_importer_full.py): 30 passed x3, 0 aborts

# checker: the visibility bug itself, parametrised over the unfixed and fixed prototype
$ pytest wp8_chk_test_text.py ...
FAILED wp8_chk_test_text.py::test_stop_message_is_visible_after_an_earlier_load[ProtoImporter]   # AssertionError: assert '' == 'Scan stopped'
1 failed, 1 passed                                                                              # [ProtoImporterFixed] passes
```

Covered: stop kwarg semantics; tree populated on the GUI thread after the worker finishes (busy bar + Stop enabled before, 0-100 + Stop disabled after); filter by date substring / OBSID / description (case-insensitive); filter survives a rescan and hidden ticked rows still `selected()`; Stop scan keeps the partial list `[OBS_C, OBS_S]` and shows "Scan stopped"; recursive toggle mid-scan cancels the first scan and exactly one `populate()` happens (stale result ignored); extract-archive rescan keeps "Extracted 1 archive(s)..." and value 100; `reject()` mid-scan stops the worker (`isFinished()`, one header read only).

### Existing test_importer.py against the async dialog

```
$ pytest wp8_test_importer_nowait.py ...   # verbatim test_importer.py, QtIRISImporter -> prototype
FAILED test_tree_lists_observations_and_files
FAILED test_ticking_the_observation_ticks_its_files
FAILED test_load_selected_real_sji
FAILED test_single_entry_observation_is_ticked_on_its_own_row
FAILED test_recursive_toggle_rescans
FAILED test_extract_archive_then_lists_its_windows
FAILED test_duplicate_real_raster_is_listed_and_loaded_once
FAILED test_reader_failure_stays_in_dialog
8 failed, 4 passed, 2 warnings in 2.65s

$ pytest wp8_test_importer_wait.py ...     # same file + 7 waitUntil insertions
12 passed, 2 warnings in 2.90s
# checker re-run: same 8 FAILED (StopIteration/AttributeError) + 4 passed without the waits; 12 passed with them
```

### Real tree through the Worker (GUI stays responsive)

```
$ python - (ProtoImporter('/Users/nabil/DATA/IRIS') with a 20 ms QTimer ticking, processEvents loop until not scanning)
real tree via Worker: 14 rows in 0.59 s, GUI timer ticks meanwhile: 25, populate on GUI thread: [True]
filter '2014-0' visible rows: ['2014-07-08T11:41:09', '2014-09-10T11:28:25', '2014-09-19T05:17:12']
$ python wp8_chk_realtree.py    # checker
real tree via Worker: 14 rows in 0.64 s, GUI timer ticks meanwhile: 27, populate on GUI thread: [True]
filter '2014-0' visible rows: ['2014-07-08T11:41:09', '2014-09-10T11:28:25', '2014-09-19T05:17:12']
```

### Slot arity and progress-bar text (checker, `wp8_chk_slotargs.py` and an inline probe)

```
$ python wp8_chk_slotargs.py
clicked -> no-arg slot: ['ok']            # PyQt6 6.11 drops clicked(bool) for a no-arg Python slot; no TypeError
finished -> no-arg slot: ['ok', 'ok']     # same for finished(int)
busy bar text(): '' | format(): '%p%'

$ python - (QProgressBar: value left by finalize(), then set_directory + stop/extract flow, then _scan_over)
prev value   0: stop  no-fix ('Scan stopped', 0)  fix ('Scan stopped', 0)
prev value  50: stop  no-fix ('', -1)             fix ('Scan stopped', 0)     # bug: setRange(0, 0) reset the value to -1, text() is empty
prev value 100: stop  no-fix ('', -1)             fix ('Scan stopped', 0)
prev value  50: extract no-fix ('Extracted 1 archive(s)', 100)  fix ('Extracted 1 archive(s)', 100)   # finalize()'s own setValue(100) covers the extract flow either way
```

Also reproduced through the real dialog (`wp8_chk_test_text.py` above): wait for the first scan, `progress.setValue(50)`, toggle recursive with slow headers, Stop scan: unfixed `text() == ''`, fixed `text() == 'Scan stopped'`.

### Worker lifetime facts

```
$ python wp8_lifetime.py stop
stopped after [9] iterations; isInterruptionRequested() after wait(): False
$ python wp8_lifetime.py drop        # del the only reference 0.1 s into a 1 s Worker
survived drop                        # exit status 0
$ python wp8_lifetime2.py            # same, then pump events 1.5 s so run() returns with no Python ref left
main loop still alive after the worker finished   # exit status 0
```

So on PyQt6 6.11 the running `run()` frame keeps the wrapper alive and dropping the reference did not abort. Keep the `wait()` anyway: it is what makes "one populate per scan" and the "Extracted" flow deterministic, it costs one header read, and PySide/older Qt are not covered by this check.

## Tests to add

All in `glue_solar/tests/`; `iris_tree` and `irispy_test_files` come from `glue_solar/conftest.py` as today. `OBS_*` constants as in conftest (OBS_A and OBS_B share the description "Test raster 1x2 3s"; OBS_C is archive-only; OBS_S has a sparse header and an irispy `ObsID` description).

### Edits to existing `test_importer.py` (7 insertions, verified as `wp8_test_importer_wait.py`)

1. `dialog` fixture: after `qtbot.addWidget(dlg)` add `qtbot.waitUntil(lambda: not dlg.scanning)`.
2. `test_load_selected_real_sji`: after `qtbot.addWidget(dialog)` add `qtbot.waitUntil(lambda: not dialog.scanning)`.
3. `test_recursive_toggle_rescans`: signature becomes `(qtbot, dialog)`; after `dialog.recursive.setChecked(False)` add `qtbot.waitUntil(lambda: not dialog.scanning)`.
4. `test_extract_archive_then_lists_its_windows`: after `qtbot.addWidget(dlg)` add the wait.
5. Same test: after `dlg.finalize()` add `qtbot.waitUntil(lambda: not dlg.scanning)` (the extract branch rescans).
6. `test_duplicate_real_raster_is_listed_and_loaded_once`: after `qtbot.addWidget(dialog)` add the wait.
7. `test_reader_failure_stays_in_dialog`: after `qtbot.addWidget(dialog)` add the wait.

Optional tidy: a module helper `def _wait_scan(qtbot, dlg): qtbot.waitUntil(lambda: not dlg.scanning); return dlg` and use it at the 7 places (not `_scanned`: that name is the dialog's result slot).

### New in `test_scan.py` (verified as `test_scan_directory_stop_kwarg`)

```python
def test_scan_directory_stop_kwarg(iris_tree):
    assert scan_directory(iris_tree, stop=lambda: True) == []
    polls = []

    def stop():
        polls.append(1)
        return len(polls) > 2  # let two files through: the OBS_C archive and the sparse OBS_S file

    partial = scan_directory(iris_tree, stop=stop)
    assert [o.obsid for o in partial] == [OBS_C[2], OBS_S]
    assert len(polls) == 3
    assert len(scan_directory(iris_tree)) == 4  # default: never stops
```

(Deterministic because `sorted()` orders the pooch-prefixed root files by name: `..._20140708_..._raster.tar.gz`, `..._20140910_fexxi_rb_steps.fits.gz`, `..._20230211_...`, `..._20250328_...`.)

### New in `test_importer.py` (verified in `wp8_test_proto.py` / `wp8_test_shipped.py`; all seven together in `wp8_chk_test_importer_fixed.py`, 31 passed x3)

Fixtures:

```python
@pytest.fixture
def slow_headers(monkeypatch):
    """Each header read takes 0.2 s and is counted, so tests can act mid-scan deterministically."""
    real = scan.fits.getheader
    calls = []

    def slow(path, *args, **kwargs):
        calls.append(path)
        time.sleep(0.2)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(scan.fits, "getheader", slow)
    return calls


@pytest.fixture
def populates(monkeypatch):
    """True per populate() call made on the GUI thread."""
    threads = []
    original = QtIRISImporter.populate

    def recording(self):
        threads.append(QThread.currentThread() == QApplication.instance().thread())
        original(self)

    monkeypatch.setattr(QtIRISImporter, "populate", recording)
    return threads
```

(`from glue_solar.sources.loaders import scan`, `from qtpy.QtCore import QThread`, `from qtpy.QtWidgets import QApplication`, `import time`.)

Tests:

```python
def _visible(dlg):
    return [dlg.obs_tree.topLevelItem(i).text(1) for i in range(dlg.obs_tree.topLevelItemCount())
            if not dlg.obs_tree.topLevelItem(i).isHidden()]


def test_tree_is_populated_on_the_gui_thread(qtbot, iris_tree, populates):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    assert dlg.scanning
    assert dlg.progress.maximum() == 0  # busy bar
    assert dlg.stop_scan.isEnabled()
    qtbot.waitUntil(lambda: not dlg.scanning)
    assert populates == [True]
    assert dlg.obs_tree.topLevelItemCount() == 4
    assert dlg.progress.maximum() == 100
    assert not dlg.stop_scan.isEnabled()


def test_filter_hides_non_matching_observations(dialog):
    dialog.filter.setText("2014-07")
    assert _visible(dialog) == [OBS_C[2]]
    dialog.filter.setText(OBS_B[2])
    assert _visible(dialog) == [OBS_B[2]]
    dialog.filter.setText("TEST RASTER")  # case-insensitive, description column (OBS_A and OBS_B share it)
    assert _visible(dialog) == [OBS_B[2], OBS_A[2]]
    dialog.filter.setText("")
    assert len(_visible(dialog)) == 4


def test_filter_survives_rescan_and_hidden_ticks_still_load(qtbot, dialog):
    _row(dialog, OBS_B[2]).setCheckState(0, Qt.Checked)
    dialog.filter.setText("2014-07")
    assert _visible(dialog) == [OBS_C[2]]
    assert [(kind, name) for _, kind, name in dialog.selected()] == [("sji", "SJI_2832")]  # hidden but ticked
    dialog.recursive.setChecked(False)
    qtbot.waitUntil(lambda: not dialog.scanning)
    assert _visible(dialog) == [OBS_C[2]]
    assert dialog.filter.text() == "2014-07"


def test_stop_scan_keeps_what_was_found(qtbot, iris_tree, slow_headers):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)  # the worker is inside its first header read
    dlg.stop_scan.click()
    qtbot.waitUntil(lambda: not dlg.scanning)
    rows = [dlg.obs_tree.topLevelItem(i).text(1) for i in range(dlg.obs_tree.topLevelItemCount())]
    assert rows == [OBS_C[2], OBS_S]  # archive (no header) + the one header that was read
    assert dlg.progress.format() == "Scan stopped"
    assert not dlg.stop_scan.isEnabled()
    assert dlg.progress.maximum() == 100
    assert len(slow_headers) == 1


def test_rescan_while_scanning_cancels_the_running_scan(qtbot, iris_tree, slow_headers, populates):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dlg.recursive.setChecked(False)  # re-enters set_directory while the first scan runs
    qtbot.waitUntil(lambda: not dlg.scanning)
    assert populates == [True]  # the cancelled scan's partial result never reached the tree
    assert _row(dlg, OBS_A[2]).text(6) == "1 — SJI_1400"  # non-recursive result (literal em-dash from populate())
    assert dlg.obs_tree.topLevelItemCount() == 4


def test_closing_the_dialog_stops_the_scan(qtbot, iris_tree, slow_headers):
    dlg = QtIRISImporter(iris_tree)
    qtbot.addWidget(dlg)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dlg.reject()
    assert dlg.worker.isFinished()
    assert len(slow_headers) == 1


def test_stop_message_is_visible_after_an_earlier_load(qtbot, dialog, slow_headers):
    dialog.progress.setValue(50)  # what finalize() leaves behind after a failed load
    dialog.recursive.setChecked(False)
    qtbot.waitUntil(lambda: len(slow_headers) >= 1)
    dialog.stop_scan.click()
    qtbot.waitUntil(lambda: not dialog.scanning)
    assert dialog.progress.text() == "Scan stopped"  # text(), not format(): an invalid bar value renders nothing
```

(The last test is the checker's addition; it fails on the prototype without the `setValue(0)` line, `'' == 'Scan stopped'`, and passes with it. `slow_headers` is requested after `dialog` so the first scan runs at full speed and only the rescan is slowed.)

Also extend the existing `test_extract_archive_then_lists_its_windows` with two lines after the second wait (verified): `assert dlg.progress.format().startswith("Extracted 1 archive(s)")` and `assert dlg.progress.value() == 100`.

Expected total: `test_scan.py` 12 (11 today + 1), `test_importer.py` 19 (12 today + 7), i.e. 31 passed. Verified today as the combined shipped-form suite: 31 passed, three runs, zero `QThread: Destroyed` lines on stderr.

## Pitfalls (verified)

- Eight existing tests read the tree right after construction or right after a re-entrant `set_directory`; without waits they fail with `StopIteration`/`AttributeError` (list above, `8 failed, 4 passed`). The 7 insertions fix all of them (`12 passed`).
- `QThread.isInterruptionRequested()` returns `False` once the thread has finished (`wp8_lifetime.py stop`: `False` after `wait()`), so it cannot be used after the fact to tell a stopped scan from a complete one. The "Scan stopped" text is therefore written by `_stop_scan` itself.
- Stale results: after `wait()` the cancelled worker's `result` may still be queued (or be dropped by the PyQt proxy when the old Worker is collected). Never call `self.sender()` in the slot to tell them apart (the old C++ object may be gone); the `_scan_id` token via `functools.partial` is what the tests verify (`populates == [True]` in the rescan test).
- Progress bar text is invisible while busy (`QProgressBar.text()` is empty when min == max == 0) and also whenever the value is invalid (below the minimum). `setRange(0, 0)` resets the value to -1 if the current value is above 0, which is exactly what `finalize()` leaves behind (`setValue(int(100 * n / len(...)))` at `iris.py:276`/`:290`, `setValue(100)` at `:303` before `accept()`, or a partial value after "Loading ... failed"). Without `setValue(0)` in `set_directory`, a Change.../recursive rescan after such a load ends with value -1 and "Scan stopped"/"Scan failed"/"Extraction failed" (second archive onwards) render as an empty bar. Verified: flow probe (`prev value 50: stop no-fix ('', -1)`) and the dialog test (`'' == 'Scan stopped'` unfixed, passes fixed). `_scan_over` must not touch the format or the "Extracted N archive(s)" message written by `finalize()` after `set_directory()` disappears; verified in the extended extract test (format kept, value 100).
- The synthetic fixture gives OBS_A and OBS_B the same `OBS_DESC` (`conftest.py:33`), so a description filter test must expect both rows; the first prototype run failed on exactly that (`['3880012095', '3400109360'] == ['3400109360']`).
- Timing in tests: gate on the counted `slow_headers` (`waitUntil(len(calls) >= 1)`) and let `wait()` finish the in-flight read; do not `qtbot.wait(ms)` and hope. With the gate, the stopped result is exactly `[OBS_C, OBS_S]` on every run (3 of 3).
- `_stop_scan` is connected to `clicked(bool)` and `finished(int)` and takes `*_args`. Checker correction: on PyQt6 6.11 a no-arg Python slot receives both signals without error (PyQt drops the surplus arguments; `wp8_chk_slotargs.py` prints `['ok', 'ok']`), so `*_args` is not required there. Keep it anyway: it costs nothing, documents the two callers, and avoids relying on binding-specific arity trimming (qtpy also targets PySide).
- `monkeypatch.setattr(scan.fits, "getheader", ...)` patches `astropy.io.fits` globally for the test; every test that uses `slow_headers` must leave the worker thread finished before returning, otherwise the worker keeps calling the patched function after teardown. The stop/rescan/visibility tests do it with `waitUntil(not scanning)`; the closing test relies on the synchronous `wait()` inside `_stop_scan` (its `scanning` flag stays `True` until the queued result is delivered during the next event processing, which is harmless: `_scan_over` then flips it on the closed dialog). Verified: the 31-test suite passes three times in one process with the closing test in the middle of the module.
- pytest in this venv: use `-o addopts=''` (`import pytest_doctestplus` -> `ModuleNotFoundError`, re-checked) or the run errors on `--doctest-rst`. CI installs the `tests` extra and does not need it.
- No `ruff`/`codespell`/`pre-commit` binary in the venv or on PATH; use the pre-commit cache paths from step 7 (verified) or install the pinned versions into the venv.
- The `.ui` must keep the object names `filter`, `stop_scan`, `progress`; `load_ui` exposes them as attributes and the tests use them.
- Do not write to `~/.glue` or the user's QSettings when smoke-testing: `HOME=<scratch>` (QSettings key `iris/last_dir` is written on every `set_directory`).

## Acceptance criteria

- [ ] `scan_directory(root, recursive=True, stop=lambda: False)`; `stop=lambda: True` returns `[]`; a stop after N polls returns the first N files grouped and sorted.
- [ ] `QtIRISImporter(directory)` returns immediately with `scanning is True`, `progress.maximum() == 0`, `stop_scan.isEnabled()`; after the worker finishes: tree populated on the GUI thread, `scanning is False`, `progress.maximum() == 100`, Stop disabled.
- [ ] Typing in `filter` hides top-level rows whose STARTOBS/OBSID/Description do not contain the text, case-insensitively; clearing shows all; the filter persists across rescans; hidden ticked rows still load.
- [ ] Stop scan mid-scan: partial rows shown, format "Scan stopped", Stop disabled, no further header reads.
- [ ] After an earlier load left the bar at a value above 0 (test sets 50), a rescan followed by Stop scan shows `progress.text() == "Scan stopped"` (not only `format()`).
- [ ] Recursive toggle / Change... / extract-archive rescan while scanning: the running worker is interrupted and awaited, exactly one `populate()` for the newest scan, "Extracted N archive(s)" text preserved.
- [ ] Closing/accepting/rejecting the dialog while scanning stops and awaits the worker.
- [ ] `test_scan.py` (12) + `test_importer.py` (19): 31 passed, three runs in a row, no `QThread: Destroyed while thread is still running` on stderr.
- [ ] `ruff check --config .ruff.toml glue_solar` clean with ruff 0.16.1 (pre-commit cache binary or pinned install); codespell clean on the rst and changelog.
- [ ] User guide paragraph, changelog fragment, plan/audit rows updated as in Docs.
- [ ] No new dependency; `pyproject.toml` untouched.

## Dropped / out of scope

- **Log files (plan Phase 1.7, plan L36/L90-91, audit L57/L170): DROPPED.** No public IRIS Level 2 source ships any `.log`; they are by-products of the SolarSoft `level1to2` pipeline (`ssw/iris/idl/uio/level1to2/irisl12_writelogfile.pro:29` `file = filename + method + '.log'`, plus a `.errorlog` variant at line 9; `iris_level1to2.pro:600` names them `iris_l2_<YYYYMMDD_HHMMSS>_<OBSID>[_raster|_sji]`) and exist only on mirrors that ran the pipeline (LMSAL/UiO internal). Evidence re-run today:
  - `irispy.data.test.get_test_data_filenames()`: 31 files, log-like names: `[]`.
  - irispy pooch registry `/Users/nabil/Git/irispy/irispy/data/_sample.py:15-21`: `aia_*_1700_image_lev1.fits`, `iris_l2_20211001_060925_3683602040_raster.tar.gz`, `..._raster_t000_r00000.fits`, four `..._SJI_*_t000.fits.gz`. No log.
  - `/Users/nabil/DATA/IRIS` non-FITS/tar files: `1 .DS_Store` only.
  - Public UiO archive listings (`curl -sL`): `https://sdc.uio.no/vol/fits/iris/level2/2014/03/29/20140329_140938_3860258481/` HTTP 200, 368 entries, 0 containing "log"; `.../2021/10/01/20211001_060925_3683602040/` HTTP 200, 18 entries, 0 containing "log". (The audit's verifier also checked `20210905_001833_3620258102`: 12 entries, 0 logs.)
  - The LMSAL HCR download page for 20140329_140938_3860258481 (audit WebFetch) offers raster/SJI/SDO tarballs, movies, timeline txt/gif and a VOEvent XML; no log.
  - `iris_xfiles.pro` itself has no log search or log file type; it only dumps a picked non-FITS file matching regex `.*log` into a `widget_text` window (audit WebFetch of hesperia `ssw/iris/idl/uio/ql/iris_xfiles.pro`).
  If a pipeline mirror user ever asks: ~25 lines (`logs: list[Path]` on `Observation`, accept `.log`/`.errorlog` keyed by `_key_from_name`, non-checkable child rows, `QPlainTextEdit(readOnly=True)` in a `QDialog` on double-click) plus one test with a synthetic log; not before.
- Date-range widgets (`QDateEdit` start/end): the ISO STARTOBS substring covers the day/month/year cases with zero widgets. Add only on request.
- Time-range *search* over a `level2/yyyy/mm/dd` mirror before scanning (what `iris_xfiles` `tstartval/tstopval` does): post-scan filtering is not that; the audit row stays "Partial" with corrected wording (Docs). Not planned.
- Filename-pattern presets, recent-search windows, IRIS/EIS data-source modes: audit non-goals, unchanged.
- Progress *percentage* during the scan: `Path.rglob` would have to be materialised twice; the busy bar is enough at 4 ms/file.
- Polling `stop` inside the directory walk (see the ponytail note): local mirrors do not need it.
- Persisting the filter text in QSettings: YAGNI.

## Docs

- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`, after the paragraph ending "The last folder used is remembered." (line 21), add:

  ```rst
  The folder is scanned in the background: the progress bar pulses while headers are being read and
  "Stop scan" lists what has been found so far, which is handy on a large ``level2`` mirror. Type in the
  "Filter" box to show only the observations whose start time, OBSID or description contains that text;
  ``2014-03`` keeps March 2014, ``3860`` keeps OBSIDs containing it, ``sit-and-stare`` keeps matching
  descriptions. Matching is case-insensitive. Filtering only hides rows: an observation you ticked
  before filtering it out is still loaded by "Load selected".
  ```

- `changelog/<PR>.feature.rst` (number = the new PR):

  ```rst
  The IRIS observation browser scans folders in the background with a "Stop scan" button that keeps the observations found so far, and gains a "Filter" box that hides observations whose start time, OBSID or description does not contain the typed text (for example ``2014-03`` for March 2014).
  ```

- `IRIS_GLUE_GAP_PLAN.md`:
  - L34 "What to add" column: `Date-range + text filters, background scan with cancel` -> `Text filter (STARTOBS is ISO text, so it doubles as a date filter), scan in glue_qt.utils.Worker with cooperative stop`.
  - L36 row "Display log files": `Missing | glue-solar | List *.log per observation, plain-text dialog (trivial)` -> `Missing | dropped | No public Level 2 download, irispy test/sample file or pooch cache contains a .log; they are level1to2 pipeline by-products found only on pipeline mirrors (decided 2026-09-02).`
  - L62-66 item 1: replace "Add a start/end date filter and a free-text filter (description/OBSID) above the observation tree, and run `scan_directory` in a `QThread` with a cancel button so large trees do not block the dialog." with "Add one free-text filter (STARTOBS/OBSID/description; the ISO start time makes it a date filter) above the observation tree, and run `scan_directory` in `glue_qt.utils.Worker` with a cooperative `stop` kwarg and a 'Stop scan' button. A 140-file tree scans in 0.6 s; this matters for mirror-scale trees (thousands of files). Post-scan filtering is not `iris_xfiles`' time-range search, so the search row stays Partial with narrower wording."
  - L90-91 item 7: replace with "Log files: dropped, see the table."
  - L196 step 3 `Phase 1.5–1.7` -> `Phase 1.5–1.6 (1.7 dropped)`.
- `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`:
  - L167 "Important difference": `No time-range search, filename-pattern presets, recent search windows, search cancellation, or multiple IRIS/EIS data-source modes.` -> `Post-scan text filter (start time/OBSID/description) and a cooperative scan cancel; no pre-scan time-range search of a dated mirror, no filename-pattern presets, recent search windows or IRIS/EIS data-source modes.`
  - L170 "Display log files": `Missing | The browser ignores non-FITS files except supported archives.` -> `Will not implement | Public Level 2 data has no log files; they are level1to2 pipeline by-products on pipeline mirrors only. The browser ignores non-FITS files except supported archives.`


---

# WP9 - Corrections to the capability audit, the user docs and the fork TODO files

**Status 2026-09-02 (added at assembly).** Section A (the 23 audit-document
edits A0 to A22) and section H (the three fork TODO files) were applied on
2026-09-02; `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` now has 15 Partial and 2
Missing rows and the TODO files carry the ticked boxes and the corrected
statements (the `test_mac_bundle_name` box in the macOS TODO stays unticked
until that test is committed). Still to do from this brief: sections B, C, D
and G, the tracked `docs/user_guide/*.rst` and `docs/dev_guide/*.rst` edits,
as one documentation commit on `iris-observation-browser` (PR #44). Line
numbers quoted for the audit file below are pre-edit numbers; locate targets
by quoted text. The acceptance item "`IRIS_GLUE_GAP_PLAN.md` unchanged" is
void: this plan was rewritten wholesale on 2026-09-02.

**Goal.** Apply every verified doc correction from the 27-agent audit (findings JSON + critic.md) as exact edits to `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`, `docs/user_guide/*.rst`, `docs/dev_guide/loader-customization.rst`, and (only if WP0 does not cover them) the three fork TODO files. The audit stays the "information" document: wrong or stale statements are fixed, Coverage cells updated, and the gaps nobody listed are added. `IRIS_GLUE_GAP_PLAN.md` is NOT touched (rewritten wholesale elsewhere).

**Current state (2026-09-02).**
- `/Users/nabil/Git/glue-solar` branch `iris-observation-browser` @ d3a2bd3 = PR glue-viz/glue-solar#44 (re-checked today: OPEN, MERGEABLE, 0 reviews, 0 review requests, checks SUCCESS/SKIPPED). `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` and `IRIS_GLUE_GAP_PLAN.md` are untracked (`git status`: `??`). The rst files, `changelog/*.rst`, `README.rst`, `pyproject.toml` are tracked and part of #44.
- `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst:57-59` tells users to pair `Helioprojective Longitude`/`Helioprojective Latitude`; the SJI dataset actually exposes `Longitude`/`Latitude`/`Time (Utc)` (re-run today, see Verified code). Line 28 claims an `_SDO` folder is required; `scan.py:110-115` accepts any `aia_l2_*` file with `INSTRUME` starting `AIA`. Lines 64-66 say sessions "cannot be restored reliably"; saving itself raises (three distinct exceptions).
- `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`: 234 lines; the comparison table is L165-186; the plugin description is L96-161. Stale/overstated items: L122-124 (axis naming), L129-131 (autolink mechanism), L134-139 + L174 (stack "retains original values"), L141-144 (sessions), L152/L173 (profiles), L178-179 (moment rows Missing although the glue-qt Profile viewer Collapse tab exists), L180 (fitting), L181, L182, L183, L184, L202 (irispy version). Missing rows/notes: no movie/sequence export anywhere in glue, detector-view row with no reader and no phase, per-scan WCS premise, sit-and-stare already loads, `irispy.obsid.ObsID`.
- `changelog/`: `42.breaking.rst`, `42.bugfix.rst`, `44.bugfix.rst`, `44.feature.rst`. `pyproject.toml` adds `ndcube>=2.0` on this branch with no fragment; verifier ruled no fragment is warranted (irispy-lmsal 0.8.1 already requires ndcube, `main` already imported it).
- Fork TODO files are untracked in `/Users/nabil/Git/glue` (`APE14_AUTOLINK_TODO.md`: 19 unchecked / 0 checked; `PROFILE_WCS_RESTART_TODO.md`: 14 / 0) and `/Users/nabil/Git/glue-qt` (`MACOS_INTEGRATION_TODO.md`: 15 / 8) although the branches implement the items (re-checked today: `ape14-wcs-autolink` = b16a3703, 016d9cf2; `profile-wcs` = 175e7129, f767d320, 98d7bb7c, c3bcd75b; glue-qt `profile-wcs` = 1133c0e9; `macos-integration` = d8a3f715..bd4dce6b = PR glue-qt#68 OPEN, 0 reviews).
- `/private/tmp/.../briefs/wp0-upstream.md` did not exist when this brief was written nor at the checker's pass (17:25: `briefs/` holds `wp2-moments.md`, `wp3-sessions.md`, `wp4-quicklook.md`, `wp7-network.md`, `wp8-browser-ux.md`, this file); WP0 worktrees `wt-wp0-ape14`, `wt-wp0-pw`, `wt-wp0-qtpw`, `wt-wp0-qtmac` exist in the scratchpad, so WP0 is in progress. Section H below therefore includes the TODO corrections; drop any that wp0-upstream.md already carries. None of wp2/3/4/7/8 touches the three TODO files (`grep -n "APE14_AUTOLINK_TODO\|PROFILE_WCS_RESTART_TODO\|MACOS_INTEGRATION_TODO" briefs/wp[2-8]*.md` -> no hits).
- The sibling briefs edit the same two files later and cite PRE-WP9 line numbers: wp2 (`loader-customization.rst:7-8`, audit moment rows), wp3 (`loading-iris...rst:61-66`, audit L141-144), wp4 (`loading-iris...rst:31-32`, `:39`, `:54-59`, audit L171-182), wp7 (new rst section after "Opening a single file", audit L183/L184), wp8 (rst after L21, audit L167/L170). WP9's multi-line edits shift those numbers (see Pitfalls); their targets must be located by the quoted text, not by line.

**Decisions already made.**
- D1: Phase 1.4 `link_hpc` stays permanently. Every "deleted once autolink lands" sentence (APE14 TODO L11-12, L111-112) is removed, not softened.
- D2: 3.2-3.6 ship from glue-solar. Audit rows L181/L182 say "glue-solar work through public registries", not "glue-core/glue-qt".
- D3: wavelength display in Angstrom lands in WP1. Audit L122-124 and L181 state "metres today" with a bracketed "(Angstrom after WP1)"; WP1 removes the bracket. No user-guide text mentions wavelength units today (`grep -niE "metre|angstrom|\bnm\b|\bmeters?\b" docs/user_guide/*.rst docs/dev_guide/*.rst docs/*.rst changelog/*.rst README.rst` -> exit 1, no hits; do not grep bare `meter` over `docs/`: it matches "parameters" in `docs/conf.py:101` and the ignored `docs/_build/` tree), so nothing else changes for D3.
- D4: moments = `layer_action`, no viewer opened. Audit row A15 says "wrapping it as a right-click dataset action that adds the maps to the data collection is planned" and nothing more; the implementation belongs to WP2.
- Verifier rulings applied (agree=false wins): doc-3 sub-claims about the detector row vs non-goal, "builds then deletes 1.4", and "rename 0th/1st/2nd" are NOT defects; "promoted to float32" is wrong for the `>f4` inputs (no promotion; only the NaN replacement is real); P3.6-tab: glue's stock `@saver(WCS)` saves the -TAB header silently and the session fails on reload (not "raises on save"); P1.6 direction: raster-drawn selections reach the SJI, SJI-drawn selections do not reach the raster; MACOS-1: macOS menu labels come from `CFBundleName`, not `setApplicationDisplayName`; ndcube fragment not warranted; the SJI inner WCS IS gwcs (auditor side-note refuted); irispy moments exist since 0.7.0.
- critic.md rulings applied: Collapse tab makes moment rows Partial; time-aware all-ones `axis_correlation_matrix` is unsafe (breaks `format_coord`), so the audit does not recommend it; `RegionData` rejected for the FOV polygon; per-scan stack WCS premise wrong (loader-side gwcs, inverse is the blocker); no sequence export anywhere; environment notes (settings.cfg) stale and not to be acted on (today: `font_size = -1.0`, `unit_converter = "default"`, read-only look).
- IDL/SolarSoft-side statements of the audit are not re-verified (per the audit brief) and are not edited.

**Dependencies / order.**
- Nothing blocks WP9. Do it first: the rst edits fix user-facing errors in PR #44 and should be one commit on `iris-observation-browser` before merge (or a follow-up PR if #44 merges first). The audit edits are to a local untracked file.
- WP9 text is re-touched later by: WP1 (drop "(Angstrom after WP1)" brackets in audit L122-124/L181; if WP1 also normalises `_GlueWCS.world_axis_names` to `_AXIS_NAMES`, drop the SJI label parenthetical in rst B3), WP2 = `briefs/wp2-moments.md` (moment rows A15/A16 become "glue-solar `IRIS: line moments...`"), WP3 = `briefs/wp3-sessions.md` (replaces the whole rst "Saving sessions" section B4 and the audit paragraph A4 with "sessions save and restore"), WP4 = `briefs/wp4-quicklook.md` (rewrites the rst "Linking" section B3 to describe automatic links, plus rst :31-32 and a "Viewer presets" paragraph; audit rows A9/A11/A19 move toward covered), WP7 = `briefs/wp7-network.md` (audit GOES/SDO rows A20/A21 after the actions ship), WP8 = `briefs/wp8-browser-ux.md` (audit L167 filter/cancel wording; flips the log-file row A8 from Missing to "Will not implement"), WP0 (delete the TODO files when PRs merge). WP9 lands first; each of those briefs then overwrites the WP9 wording of its own rows, so no WP9 text needs to anticipate them.
- Section H (TODO files) only if `briefs/wp0-upstream.md` does not already list the same edit.

**Files to touch.**
- `/Users/nabil/Git/glue-solar/IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`: 22 edits (section A).
- `/Users/nabil/Git/glue-solar/docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: 4 edits (section B).
- `/Users/nabil/Git/glue-solar/docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst`: 1 edit (section C).
- `/Users/nabil/Git/glue-solar/docs/user_guide/loading-aia-and-hmi.rst`: 1 edit (section D).
- `/Users/nabil/Git/glue-solar/docs/dev_guide/loader-customization.rst`: 1 edit (section G).
- `/Users/nabil/Git/glue-solar/changelog/*.rst`: no change (section E, dropped with reason).
- `/Users/nabil/Git/glue-solar/README.rst`: optional one-liner (section F).
- `/Users/nabil/Git/glue/APE14_AUTOLINK_TODO.md`, `/Users/nabil/Git/glue/PROFILE_WCS_RESTART_TODO.md`, `/Users/nabil/Git/glue-qt/MACOS_INTEGRATION_TODO.md`: section H, conditional on WP0.

**Step-by-step.**
1. `cd /Users/nabil/Git/glue-solar && git status --short` must show only the two untracked md files. Re-grep every line number below with `grep -n '<first words of old>' <file>` before editing; the numbers are from today's `cat -n` and are exact for d3a2bd3.
2. Apply section A to `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` top to bottom (line numbers shift only below each multi-line edit; edit from the bottom up if using line-addressed tools).
3. Apply sections B, C, D, G to the rst files. Keep rst line widths similar to the surrounding text; no new directives.
4. Check rst syntax. Neither docutils nor sphinx is importable from `.venv` (`.venv/bin/python -c "import docutils"` -> `ModuleNotFoundError`), so install docutils into the scratchpad only: `.venv/bin/pip install --quiet --target <scratchpad>/docutils-pkg docutils` (0.23 today), then for each edited file `cd docs && PYTHONPATH=<scratchpad>/docutils-pkg ../.venv/bin/python -m docutils --halt=5 ../<file> /dev/null`. Expected: no output for the three `user_guide` files; exactly two pre-existing messages for `dev_guide/loader-customization.rst` (`:19` and `:35` `(ERROR/3) Unknown interpreted text role "class"`, a Sphinx-only role, present before the edit too). Any new message is a WP9 regression. `tox -e build_docs` is the full check and needs network; the docs CI job of PR #44 is the final gate.
5. `pytest glue_solar -q -o addopts=''` still 27 passed (docs do not affect it; sanity only).
6. Commit the rst changes on `iris-observation-browser` as "Fix user-guide statements about IRIS linking, SDO cutouts, stacking and sessions" (no changelog fragment: doc-only, PR #44 already has one).
7. If `briefs/wp0-upstream.md` exists, diff its TODO edits against section H and apply only the remainder to the three untracked TODO files (edit in place; they are untracked, no commit).
8. Do not touch `IRIS_GLUE_GAP_PLAN.md`.

---

## A. `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` (untracked; line numbers from today's `cat -n`)

Format: **A<n>** file line(s) | old | new | reason (finding).

**A0** L15-16 (after the paragraph ending "manual coordinate linking.") | insert a new paragraph:
```
Glue-side statements were re-verified on 2026-09-02 against glue-core 1.27.0,
glue-qt main (9780eaf9), irispy-lmsal 0.8.1, ndcube 2.4.1 and astropy 8.0.1.
```
Reason: the audit carries a SolarSoft snapshot date (L214) but no Glue-side date; every edit below is dated by this line.

**A1** L122-124 | old:
```
- Gives physical names to wavelength and helioprojective world axes, presents
  helioprojective coordinates in arcseconds, and normalizes longitude to signed
  values for Glue display.
```
new:
```
- Names the wavelength and helioprojective world axes only where irispy leaves
  them unnamed: raster datasets expose `Helioprojective Longitude`,
  `Helioprojective Latitude` and `Wavelength`, while SJI datasets keep irispy's
  gWCS names `Longitude`, `Latitude` and `Time (UTC)`. Helioprojective
  coordinates are presented in arcseconds with longitude normalized to signed
  values; wavelength is exposed in metres today (Angstrom after WP1).
```
Reason: doc-1 (a); verified today (`sv2_probe.py`: SJI world names `Longitude/Latitude/Time (UTC)`, raster `Helioprojective .../Wavelength`, units `('m','arcsec','arcsec')`).

**A2** L129-131 | old:
```
- Adds browser selections through Glue's normal dataset path. Spatial links
  must currently be created manually because Glue does not autolink irispy's
  SJI gWCS and raster `-TAB` WCS.
```
new:
```
- Adds browser selections through Glue's normal dataset path. Spatial links
  must currently be created manually: released glue-core (1.27.0) only offers
  `BaseHighLevelWCS` coordinates to `wcs_autolink`
  (`wcs_autolinking.py:321`), and the plugin's `_GlueWCS` is a low-level
  `BaseWCSWrapper`, so IRIS datasets are skipped (0 links; a direct
  `WCSLink(sji, raster)` raises `AttributeError: has_celestial`). The raw
  irispy gWCS and `-TAB` objects would crash `wcs_autolink` outright. The fork
  branch `glue:ape14-wcs-autolink` fixes this and yields one SJI-raster
  helioprojective `WCSLink`, exact at the first exposure only (see the
  temporal-coordination row below).
```
Reason: doc-1 (d), ape14 P3.1/P3.1-sec5; verified today (`sv2_probe.py`, `sv2_probe_b.py`: 0 links, `AttributeError`, raw objects raise in both orders; `grep -n BaseHighLevelWCS wcs_autolinking.py` -> line 321).

**A3** L134-139 | old:
```
The optional 4-D representation is a Glue visualization feature, not
functionality supplied by `irispy` or required to reproduce `iris_xfiles`.
It preserves each scan's detector values, mask, raster indices, and exact
acquisition times. Scan 0 supplies the stack's nominal spatial WCS; later scans'
distinct absolute helioprojective pointings are available only when those scans
are loaded separately.
```
new:
```
The optional 4-D representation is a Glue visualization feature, not
functionality supplied by `irispy` or required to reproduce `iris_xfiles`.
It keeps each scan's raster indices, exact acquisition times and mask; the
stacked array is a float32 temp-file memmap in which masked pixels (-200 in
the files) are stored as NaN and the mask is rebuilt from `isfinite` (same
pixel count). Only unstacked per-scan datasets keep the raw detector values.
Scan 0 supplies the stack's nominal spatial WCS; later scans' distinct
absolute helioprojective pointings are available only when those scans are
loaded separately. A per-scan stack WCS needs no glue-core change: a `gwcs`
model built from `astropy.modeling.tabular.tabular_model(3)` over the stacked
`-TAB` lookup tables reproduces every scan's own coordinates exactly in the
forward direction; the missing piece is an inverse model
(`world_to_pixel_values` fails), which links and subsets require.
```
Reason: doc-1 (b) as refined by its verifier (no dtype promotion for `>f4`; NaN replacement and memmap are real); critic §1/§3.3 per-scan WCS premise; verified today (`sv2_probe.py`: 2344 masked px -> 2344 NaN, float32 memmap; `cc_stackwcs.py`: dlon = 0.00e+00 for scans 0-2, inverse `ValueError`; code: `stack_spectrograms.py:14` `memmap=True` default, `:42` `np.result_type(dtype, np.float32)`, `:44-45` `tempfile.TemporaryFile()` + `np.memmap(..., "w+")`, `:54-56` mask -> NaN, `:79` `mask=~np.isfinite(output)`, `:80` `meta=dict(...)`; called from `loaders/iris.py:98`).

**A4** L141-144 | old:
```
Glue session round trips are currently unsupported for IRIS datasets. The
irispy metadata, preferred colormap, SJI gWCS, raster `-TAB` lookup table, and
stacked compound WCS require serialization support beyond a header-only saver;
implementing those serializers is outside this branch's scope.
```
new:
```
Glue sessions containing IRIS datasets cannot currently be saved: **File ->
Save Session** raises before anything is written. SJI datasets fail on the
unserializable `_GlueWCS`; rasters and stacks fail first on the two
`Quantity` values in irispy's `SGMeta` (`exposure time`, `observer radial
velocity`, `TypeError` from `numpy.save`), then on `_GlueWCS`; with coords
removed, the `Colormap` object in `preferred_cmap` raises a JSON `TypeError`.
The SJI metadata (148 keys) already round-trips, and glue-core silently drops
`Time`/`SkyCoord` meta values. glue's stock `@saver(WCS)` would save the
`-TAB` header without its table and fail on reload. No glue-core or
glue-astronomy saver is required: a `__gluestate__` on `_GlueWCS` (asdf for
the gWCS, a rebuild of the `-TAB` table from `Tabprm.coord`, a recursive
record for sliced/compound WCS) plus a version-2 `VisualAttributes` saver is
about 60 lines of glue-solar code and round-trips SJI, raster and stack; such
sessions need glue-solar (and its Qt import) importable when the session is
loaded. The `preferred_cmap` crash also breaks sessions for any sunpy Map
loaded through `glue_solar.sources.maps` (`maps.py:30`) on `main` today.
Browser-loaded datasets carry no `LoadLog`, so a session embeds the arrays
instead of referencing the files.
```
Reason: doc-1 (c), session-serialization P3.6/-tab (verifier)/-meta/-cmap/-loadlog, critic §5; verified today (`sv2_probe_b.py`: SJI `GlueSerializeError`, raster `TypeError numpy.save Quantity`, raw astropy -TAB + clean meta OK; `ver_sess3.py`: sunpy map `SAVE FAIL: TypeError Object of type LinearSegmentedColormap is not JSON serializable`; `grep -n preferred_cmap glue_solar/sources/maps.py` -> line 30).

**A5** L152 | old: `- 1-D profiles along a chosen axis;` | new:
```
- 1-D profiles along a chosen axis, always as a collapse statistic (maximum,
  minimum, mean, median, sum) over the other axes in glue-core 1.27.0; a
  single-pixel spectrum needs a one-pixel subset, or the `'slice'` collapse
  function that exists only on the `glue:profile-wcs` fork branch;
```
Reason: profile-wcs.C doc_corrections; verified today (`FUNCTIONS` in `glue/viewers/profile/state.py:22-26` = maximum/minimum/mean/median/sum; `git show profile-wcs:glue/viewers/profile/state.py | grep "'slice'"` -> line 28).

**A6** L157 | old: `- ordinary Glue viewer export facilities.` | new:
```
- export of the current viewer frame through matplotlib's save tool (there is
  no movie or sequence export anywhere in glue-core or glue-qt).
```
Reason: critic §1/§3.6 (unlisted gap); verified today (`grep -rniE "ffmpeg|imageio|FuncAnimation|movie|\.mp4|\.gif"` over glue-core site-packages and `glue_qt`, non-test files: 0 hits; `glue_qt/plugins` = `dendro_viewer`, `tools`; export tools = `mpl:save`, `save`).

**A7** L169 (metadata row) | old cell: `No OBS XML dependency resolution or `IRISsim_showXML` table viewer.` | new cell:
```
No OBS XML dependency resolution or `IRISsim_showXML` table viewer. `irispy.obsid.ObsID(<OBSID>)` decodes the OBS description, SJI filters, field of view, exposure, binning, cadence, compression and linelist offline (no XML) and is not surfaced by the browser yet.
```
Reason: critic §1/§3.2; verified today (`ObsID(3860258481)` prints all nine fields).

**A8** L170 (log row) | old cell: `The browser ignores non-FITS files except supported archives.` | new cell:
```
The browser ignores non-FITS files except supported archives. Public Level 2 downloads, irispy's test/sample data and pooch caches contain no `.log` files; they are level1to2 pipeline by-products (`iris_l2_<ts>_<obsid>[_raster|_sji].log`, also `.errorlog`) present only on local mirrors. `iris_xfiles` itself has no log search either: it only displays a picked non-FITS file whose name matches `.*log`.
```
Reason: browser-ux P1.7 + verifier (sdc.uio.no listings, pipeline source, `iris_xfiles_logdisplay`); not re-run today (network), cited. WP8 later flips this row to "Will not implement"; WP9 keeps "Missing".

**A9** L171 (SJI inspection row) | old cell: `No IRIS movie controls, raster-slit overlay, exposure-aware matching, blink/mix, or IRIS-specific export workflow.` | new cell:
```
Playback (first/previous/back/stop/forward/next/last buttons; repeated back/forward presses change the speed) already exists in the Image Viewer slider. Missing: a raster-slit overlay (the SJI aux `SLTPX1IX`/`SLTPX2IX` columns are already exposed by irispy as the `slit x position`/`slit y position` extra coordinates; the slit sweeps across the frame during rasters, so the overlay must be per frame), exposure-aware matching, timed blink (mix exists through per-layer alpha and the "One color per layer" mode), and any movie or sequence export (none exists in glue-core or glue-qt; only the current frame can be saved).
```
Reason: units-lines-blink P3.5, slit-overlay P1.6 (verifier point 4), critic §3.6; verified today (playback buttons `data_slice_widget.py:50-62`, `QTimer` at :81, speed = `_play_speed` stepped by `_adjust_play` at :146-160 with interval `500 / abs(speed)` ms, no separate speed widget; `sv2_probe.py` SJI extra_coords include `slit x position`, `slit y position`; export grep empty).

**A10** L172 (detector row) | old cell: `No detector mosaic, selected-window layout, detector-aware scales, or linked row/column plots.` | new cell:
```
No detector mosaic, selected-window layout, detector-aware scales, or linked row/column plots. irispy 0.8.1 `read_files` returns one cube per spectral window and has no full-detector reader, so this is a loader gap as well as a layout gap; no work is scheduled for it.
```
Reason: critic §1 (row covered by no finding and no phase); verified today (`sv2_probe.py`: raster labels are one dataset per window).

**A11** L173 (coordinated browser row) | old cell: `Views are not assembled into the synchronized raster/spectrum/SJI/GOES browser provided by IDL.` | new cell:
```
Views are not assembled into the synchronized raster/spectrum/SJI/GOES browser provided by IDL. On glue-core 1.27.0 the Profile viewer shows collapse statistics only; the per-pixel spectrum of `iris_raster_browser` needs the fork's `'slice'` function or a one-pixel subset. With manual lon/lat links a selection drawn on the raster viewer appears on the SJI viewer, but a selection drawn on the SJI viewer cannot be evaluated on the raster (`IncompatibleAttribute`), because the SJI pixel axes depend on time and the raster has no matching time component.
```
Reason: profile-wcs.C, slit-overlay P1.6-dep (verifier), viewer-composition P1.3 (verifier); verified today (`v_qt.py PATCH=0`: raster-drawn ROI -> SJI mask n=12200 OK; SJI-drawn ROI -> raster `IncompatibleAttribute()`).

**A12** L174 (multiple-raster row) | old cell: `The stack retains original values and exact per-pixel times but uses scan 0 as its nominal spatial WCS; `iris_raster_browser` retains every raster's own coordinates.` | new cell:
```
The stack keeps exact per-pixel times and raster indices, stores masked pixels as NaN in a float32 memmap, and uses scan 0 as its nominal spatial WCS; `iris_raster_browser` retains every raster's own coordinates (feasible loader-side with a gwcs lookup-table model, see above; the inverse model is the open piece).
```
Reason: doc-1 (b) + verifier refinement; critic §1; verified today (see A3).

**A13** L175 (sit-and-stare row) | old row:
```
| Sit-and-stare navigation | Generic slicing when the data shape permits it | Partial | No long-observation chunking or specialized time layout. |
```
new row:
```
| Sit-and-stare navigation | Loads today: a sit-and-stare raster file becomes a `(n_exposure, slit, wavelength)` dataset whose axis 0 is time, with a per-exposure `Time` component (irispy `sns` test data: shape (187, 40, 52), 2021-09-05 00:18 to 05:07); wavelength-versus-time is a 2-D slice choice and chunking is a slice range or subset | Partial | No dedicated time layout (the time axis is labelled `Helioprojective Longitude` because `Time` is a component, not a coordinate) and no chunk presets. |
```
Reason: critic §1 (row covered by default, neither doc says so), viewer-composition P1.2 verifier; verified today (`raster_data(sns)` -> `(187, 40, 52)`, world cids `Helioprojective Longitude/Latitude/Wavelength`, `Time` 2021-09-05T00:18:37 .. 05:07:31, `OBS_DESC` "Medium sit-and-stare 0.3x60 1s").

**A14** L176 (spectroheliogram row) | old cell: `A user can select wavelength/slit axes in a Glue Image Viewer` | new cell:
```
The Image Viewer's default layout for a raster window (x = wavelength, y = slit, slider = raster position)
```
Reason: viewer-composition P1.2 (auditor + verifier: default 3-D viewer x = Pixel Axis 2, y = Pixel Axis 1 == spectroheliogram); re-run today by the checker (`wp9chk_axes.py`: 3-D window x=`Wavelength`, y=`Helioprojective Latitude`, slider `Helioprojective Longitude`; 4-D stack adds the `Scan` slider).

**A15** L178 (zeroth-moment row) | old row:
```
| Zeroth-moment intensity map | No plugin calculation | Missing | Glue can display a supplied map but the plugin does not calculate the line moment. `irispy.utils.moments.calculate_moments` (irispy-lmsal >= 0.8.1) provides the calculation; wrapping it is planned. |
```
new row:
```
| Zeroth-moment intensity map | glue-qt Profile viewer **Collapse** tab (no plugin code) | Partial | Drawing a wavelength range in the Profile viewer and choosing Sum makes the linked Image Viewer show the summed map over that range live (`AggregateSlice`); it is pixel-index based, with no rest wavelength, velocity or bad-pixel handling. `irispy.utils.moments.calculate_moments` (since irispy-lmsal 0.7.0; glue-solar pins >= 0.8.1) provides the full calculation; wrapping it as a right-click dataset action that adds the maps to the data collection is planned. |
```
Reason: critic §3.1 (Collapse tab), science-moments doc_corrections (0.7.0), D4 (`layer_action`, no viewer opened); verified today (`cc_collapse.py`: `AggregateSlice(slice(10,40), 20, np.nansum)` map `(8,109)` equals `nansum(data[:,:,10:40])` -> True; `COLLAPSE_FUNCS` = nanmean/nanmedian/nanmin/nanmax/nansum/mom1/mom2; `git -C irispy tag --contains 3b9a506` -> v0.7.0).

**A16** L179 (profile moments row) | old row:
```
| Profile moments | None | Missing | No plugin UI yet; the same `calculate_moments` returns 0th/1st/2nd moments plus velocity maps per spatial pixel. |
```
new row:
```
| Profile moments | Profile viewer **Collapse** tab (Moment 1 / Moment 2, pixel units) | Partial | No plugin UI yet; `calculate_moments` returns `intensity`, `centroid`, `width` (0th/1st/2nd moments) plus `velocity` and `velocity_width` maps per spatial pixel, using `meta.rest_wavelength` (from `TWAVE`); 4-D stacks carry a plain dict meta and need an explicit rest wavelength. |
```
Reason: critic §3.1, doc-3 verifier (keys), science-moments P2.1-stack; verified today (`sv2_probe.py`: keys `intensity/centroid/width/velocity/velocity_width`, `rest_wavelength` 279.62 nm).

**A17** L180 (fitting row) | old row:
```
| Single/double Gaussian fitting | None | Missing | No fit controls, diagnostics, or parameter maps in the plugin; `astropy.modeling.fitting.parallel_fit_dask` plus the irispy gallery recipes provide the batch fitting. |
```
new row:
```
| Single/double Gaussian fitting | Single-spectrum fit only: `glue.core.fitters` and the glue-qt Profile viewer **Fit** tab fit one Gaussian or polynomial to the displayed profile in a background `Worker` | Partial | No per-pixel parameter maps, double-Gaussian model or diagnostics; `astropy.modeling.fitting.parallel_fit_dask` (astropy >= 7.0; `dask` is already a hard irispy-lmsal dependency) plus the irispy gallery recipes provide the batch fitting at about 1 ms per spectrum. Neither the bundled irispy rasters (line cores lie outside every window) nor the synthetic conftest rasters can drive a physical fit. |
```
Reason: science-fitting P2.2 verifier (fitters/Fit tool missed; astropy 7.0; timing artefacts), P2.2-dask-extra; verified today (`glue/core/fitters.py` classes `BaseFitter1D/AstropyFitter1D/BasicGaussianFitter/PolynomialFitter`; `profile_tools.py:16,222,227` `Worker(self._fit, ...)`; `pip show irispy-lmsal` Requires includes `dask`; `parallel_fit_dask: True`).

**A18** L181 (wavelength/velocity row) | old row:
```
| Wavelength/velocity and line IDs | Wavelength WCS only | Partial | No velocity conversion, rest-wavelength selection, or line-identification overlay. |
```
new row:
```
| Wavelength/velocity and line IDs | Wavelength WCS only (metres today; Angstrom after WP1) | Partial | No velocity display unit or line-identification overlay. No rest-wavelength selection UI is needed for the default: irispy supplies `meta.rest_wavelength` from `TWAVE` for every per-scan window (stacks carry a dict meta; fall back to `TWAVE<n>`). Both are glue-solar work through glue-core's public `unit_converter` and `layer_artist_maker` registries. |
```
Reason: units-lines-blink P3.3/P3.4 doc_corrections + verifier (TWAVE fallback; stacks carry `meta=dict(...)`, `stack_spectrograms.py:80`), D2, D3; verified today (units `'m'`; `rest_wavelength` 279.62 nm; `irispy/meta.py:194-198` `rest_wavelength` property = `float(TWAVE{_iwin}) * u.AA` to nm).

**A19** L182 (temporal coordination row) | old row:
```
| SJI and raster temporal coordination | Datasets can be linked manually by available coordinates | Partial | No automatic WCS link, nearest-exposure selection, or synchronized IRIS-specific panels. |
```
new row:
```
| SJI and raster temporal coordination | Manual lon/lat links propagate selections from the raster to the SJI only; SJI-drawn selections cannot be evaluated on the raster (the SJI pixel axes depend on time and the raster has no matching time component) | Partial | No automatic WCS link on released glue-core. The fork branch `glue:ape14-wcs-autolink` autolinks SJI and raster, exact at the first exposure only: on the 4.8 h rotation-tracked `sns` test observation the pointing drifts 42 arcsec, so a time-aware link helper (gap plan Phase 1.4) stays necessary alongside it. No nearest-exposure selection and no synchronized slicing between viewers. |
```
Reason: slit-overlay P1.6 verifier (direction), viewer-composition P1.4 verifier (frame-0, 42 arcsec drift), critic §2 and D1; direction verified today (`v_qt.py`); fork numbers cited from the verifier, not re-run.

**A20** L183 (GOES row) | old cell: `No GOES query or flare/context plot.` | new cell:
```
No GOES query or flare/context plot. A plot needs `sunpy[timeseries]` (`h5netcdf`), which glue-solar does not declare (`pyproject.toml` has `sunpy[map,net]`); the target is the Scatter viewer (the Profile viewer raises on a datetime-first dataset); glue-core 1.27.0 labels datetime axes with the pre-matplotlib-3.3 epoch (`glue/utils/matplotlib.py:449`, no `set_epoch` anywhere), so date ticks read wrong with matplotlib 3.11. That last bug already affects any Scatter or Histogram plot of the raster `Time` component.
```
Reason: network-context P1.5 verifier, critic §3.5; verified today (`import sunpy.timeseries` -> `ModuleNotFoundError: h5netcdf`; `datetime64_to_mpl('2021-09-05T00:16:12')` = 738038.01 -> `num2date` 3990-09-06 vs `date2num` 18875.01; `set_epoch`/`date.epoch` grep: 0 hits; `profile/state.py:69-71` `datetime=False`).

**A21** L184 (SDO row) | old cell: `No live SDO retrieval, rotation, limb context, or IRIS field-of-view overlay.` | new cell:
```
No live SDO retrieval, limb/full-disk context, or IRIS field-of-view overlay ("rotation" is not a gap: the LMSAL cutouts are per-exposure time-matched). The FOV polygon can be a `PolygonalROI` subset on the AIA dataset in its own pixel coordinates, needing no link; glue-core's `RegionData` crashes on a WCS-bearing Data (`coordinate_helpers.py:42`). Cross-dataset linking must match `world_axis_physical_types`, never labels (SJI `Longitude`, raster `Helioprojective Longitude`, sunpy Map `Hpln`).
```
Reason: network-context P2.4 verifier, critic §3.4; verified today (`cc_region.py`: `AttributeError: 'tuple' object has no attribute 'shape'` at `coordinate_helpers.py:42`).

**A22** L202 | old: `` (`irispy.utils.moments.calculate_moments` since irispy-lmsal 0.8.1, and `` | new: `` (`irispy.utils.moments.calculate_moments` since irispy-lmsal 0.7.0, and `` | Reason: science-moments doc_corrections; verified today (`git tag --contains 3b9a506` -> v0.7.0, v0.8.0, v0.8.1; CHANGELOG #124/#125/#126 under 0.7.0).

Unchanged after re-check (do not edit): L57, L167, L170 first clause, L177 (whisker row: accurate, the whisker needs a preset; WP4 owns it), L185-186, L207-210, L118-121, L128, L132, L150-151, L153-156, L159-161, and every IDL-side row.

## B. `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst` (tracked, PR #44)

**B1** L28 | old: `- one entry per co-aligned SDO/AIA cutout when an ``_SDO`` folder is present.` | new:
```
- one entry per co-aligned SDO/AIA cutout (any ``aia_l2_*.fits`` file found under the folder,
  usually inside the ``*_SDO`` directory of a download).
```
Reason: doc-4; verified today (`scan.py:110-115`: `name.startswith("aia_l2_") and instrume.startswith("AIA")`, no folder test).

**B2** L33-34 | old:
```
Tick "Stack sequential raster scans" to place two or more raster scans of a window into a single
4D cube without resampling their detector values. Its leading ``Scan`` coordinate selects the
```
new:
```
Tick "Stack sequential raster scans" to place two or more raster scans of a window into a single
4D cube without resampling (the stacked array is float32 and bad pixels are stored as NaN; the
mask component is kept). Its leading ``Scan`` coordinate selects the
```
Reason: doc-1 (b); verified today (see A3).

**B3** L57-59 | old:
```
Glue does not currently autolink irispy's time-varying SJI gWCS and raster ``-TAB`` WCS. To
propagate spatial selections, open the Data Manager's link editor and manually pair
``Helioprojective Longitude`` and ``Helioprojective Latitude`` between datasets.
```
new:
```
Glue does not currently autolink irispy's time-varying SJI gWCS and raster ``-TAB`` WCS (released
glue-core skips them; an upstream fix is in progress). To propagate spatial selections, open the
Data Manager's link editor and pair the helioprojective longitude and latitude components of the
two datasets: they are labelled ``Helioprojective Longitude`` / ``Helioprojective Latitude`` on
raster datasets and ``Longitude`` / ``Latitude`` on slit-jaw datasets. With these links a
selection drawn on a raster viewer appears on the slit-jaw viewer; a selection drawn on a slit-jaw
viewer cannot be shown on the raster, because slit-jaw pixel coordinates also depend on time.
```
Reason: doc-4, viewer-composition P1.4 verifier, slit-overlay P1.6 verifier (5); verified today (labels via `sv2_probe.py`; direction via `v_qt.py`). Follow-up: if WP1 normalises `_GlueWCS.world_axis_names` to `_AXIS_NAMES` (`loaders/iris.py:39-43`, one-line change: prefer `_AXIS_NAMES.get(physical_type)` over irispy's name), delete the label sentence; that change also renames the SJI time axis `Time (UTC)` to `Time`, which collides with nothing because SJI cubes have no `time` extra coord (doc-4 verifier). WP4 (`briefs/wp4-quicklook.md`) then replaces this whole section with the automatic-link text.

**B4** L64-66 | old:
```
Glue sessions containing these IRIS datasets cannot currently be restored reliably. The irispy
metadata and WCS objects, including SJI gWCS and raster lookup tables, need dedicated serializers;
save derived products separately rather than relying on a Glue session as their only copy.
```
new:
```
Glue sessions containing these IRIS datasets cannot currently be saved: "File -> Save Session"
fails with an error before the file is written, because the irispy metadata and WCS objects
(SJI gWCS, raster lookup tables, the preferred colormap) have no serializers yet. Save derived
products separately rather than relying on a Glue session as their only copy.
```
Reason: session-serialization P3.6 + doc-1 (c); verified today (`sv2_probe_b.py`). Superseded by the sessions WP.

## C. `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst`

**C1** L16-17 | old:
```
"Stack sequential raster scans" to place two or more scans of each selected window into one 4D
cube without resampling their detector values. A window with only one scan loads as its normal 3D
```
new:
```
"Stack sequential raster scans" to place two or more scans of each selected window into one 4D
cube without resampling (bad pixels become NaN in the float32 stack; the mask component is kept).
A window with only one scan loads as its normal 3D
```
Reason: consistency with B2 (doc-1 (b)).

No other change: L41-43 (default x = Wavelength, y = Helioprojective Latitude, sliders Scan + Helioprojective Longitude) re-verified today on a 3-scan stack (`wp9chk_axes.py`, see Verified code); L62-66 describes 1.27.0's statistic profiles correctly; no wavelength unit is mentioned (D3 needs nothing here until WP1 adds a sentence).

## D. `docs/user_guide/loading-aia-and-hmi.rst`

**D1** L43 | old: `   :alt: Overplotting AMI and HMI maps` | new: `   :alt: Overplotting AIA and HMI maps` | Reason: doc-4 (typo); verified today (`cat -n`).

## E. `changelog/*.rst`

No edit. The `ndcube>=2.0` line added to `pyproject.toml` on this branch gets no fragment: `main` already did `from ndcube import NDCube` in `stack_spectrograms.py:8` and irispy-lmsal 0.8.1 requires ndcube (>= 2.4 per its metadata), so the declaration changes nothing for any installable environment (doc-5 verifier ruling; verified today with `pip show irispy-lmsal` Requires and `git show main:glue_solar/sources/loaders/stack_spectrograms.py | grep ndcube`). If a maintainer insists, append to `42.breaking.rst`: `` ``ndcube`` (already pulled in by irispy-lmsal) is now declared as a direct dependency. `` and optionally raise the floor to `ndcube>=2.4` in `pyproject.toml:23`.
`44.feature.rst` "the original detector values" stays: it describes unstacked rasters, which do keep them.

## F. `README.rst`

No finding touches it. Optional one-liner after L27 ("and you can also load files from inside glue."): `IRIS Level 2 folders can be browsed by observation from "Plugins -> IRIS: browse observations...".` Skip unless the maintainer wants the README to mention the browser; the user guide covers it.

## G. `docs/dev_guide/loader-customization.rst`

**G1** L21-23 | old:
```
3. ``stack_spectrograms.py`` optionally stacks two or more raster scans without
   resampling. The 4D result has a leading scan-number axis, a separate exact
   acquisition-time component, and scan 0's WCS as its nominal spatial frame.
```
new:
```
3. ``stack_spectrograms.py`` optionally stacks two or more raster scans without
   resampling into a float32 memmap (masked pixels become NaN and the mask is rebuilt).
   The 4D result has a leading scan-number axis, a separate exact
   acquisition-time component, and scan 0's WCS as its nominal spatial frame.
```
Reason: doc-1 (b); developers need the dtype/NaN fact.

## H. Fork TODO files (apply only the edits `briefs/wp0-upstream.md` does not already carry; as of 17:25 that brief does not exist and no other brief touches these files, so apply H in full unless it appears)

### H-A `/Users/nabil/Git/glue/APE14_AUTOLINK_TODO.md` (untracked)

- **H-A1** L9-10 | old: `(§4a of\n`IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` in that repo)` | new: `(the "Data loading and representation" bullet and the "SJI and raster temporal coordination" row of `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` in that repo)` | Reason: ape14/doc-2 (the audit has no numbered sections; verified today: `grep -n "§" IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` -> none).
- **H-A2** L11-12 | old: `This PR\nalso deletes a planned glue-solar workaround (its gap plan, Phase 1 item 4).` | new: `glue-solar keeps its physical-type link helper (gap plan Phase 1.4): the WCSLink is exact at the first exposure only, the helper covers later exposures.` | Reason: D1; viewer-composition P1.4 verifier.
- **H-A3** L56, L61, L69, L74, L80 | `- [ ]` -> `- [x]` | Reason: P3.1-sec2 verifier (all five done on 016d9cf2).
- **H-A4** L88, L91, L93, L94, L98 | `- [ ]` -> `- [x]`; L96-97 | old: `Round-trip: `forwards`/`backwards` agree with direct\n      `pixel_to_pixel` on the sliced-and-wrapped WCSes.` | new: `- [x] `forwards`/`backwards` checked against analytic expectations on the synthetic fixtures (no literal `pixel_to_pixel` round-trip test; add one if review asks).` | Reason: P3.1-sec3 verifier (`grep pixel_to_pixel` in the test file: none; 11 new tests, 31 passed).
- **H-A5** L106 | old: `(this is the audit §4a measurement flipped to a pass)` | new: `(the audit's "temporal coordination" row flipped to a pass)`. Box stays `[ ]` (needs a glue release).
- **H-A6** L107-110 | keep `[ ]`, append: `Answer (verified 2026-09-02): NOT coherent. `world_axis_object_classes` still carries deg units while values are arcsec, so `HighLevelWCSWrapper(_GlueWCS(raster)).pixel_to_world` raises `ValueError` (latitude -399 deg) and the fork returns `IncompatibleWCS` for raster<->raster and raster<->map pairs. Fix in glue-solar (~15 lines: `world_axis_object_classes` AND the `world_axis_object_components` getters), tracked as WP1.` | Reason: APE14-TODO-4.2 verifier, critic §2 coherence-fix size.
- **H-A7** L111-112 | delete the bullet | Reason: D1.
- **H-A8** L116, L118, L119 | `- [ ]` -> `- [x]` (verified by P3.1-sec5). L122 stays `[ ]`. Add two bullets before L123: `- [ ] Make `forwards`/`backwards` of `get_cids_and_functions` (line 82) and the parameters of `transform` (line 148) keyword-only: ruff 0.16.5 flags PLR0917 there; the CI pin 0.15.20 is clean.` and `- [ ] Expect a review question on `clone(link)` for low-level coords: it raises `GlueSerializeError` because glue-core only has `@saver(astropy.wcs.WCS)`; pre-existing gap, not introduced by this branch.` | Reason: P3.1 verifier codestyle + sec3 gap; verified today (`ruff 0.16.5` on `wt-wp0-ape14`: `wcs_autolinking.py:82:5 PLR0917`, `:148:9 PLR0917` plus 4 CPY001 that `main` also has; `ruff 0.15.20`: All checks passed).

### H-P `/Users/nabil/Git/glue/PROFILE_WCS_RESTART_TODO.md` (untracked)

- **H-P1** L8-10 | old: `Keep `origin/1dprofile_wcs` untouched as reference until the\nsalvage below is copied out; then it can be deleted.` | new: `Salvage complete (2026-09-02, branches `glue:profile-wcs` and `glue-qt:profile-wcs`): delete `origin/1dprofile_wcs` and close draft PR glue-viz/glue#2248 (OPEN, CONFLICTING, last commit 2022-05-07).` | Reason: profile-wcs upstream-prs verifier; PR state re-checked today (`gh pr list` -> #2248 draft, 2021-11-09).
- **H-P2** L50-54 | append after "goes in the PR description.": `Decision (implemented in f767d320): `ProfileViewerState._wcsaxes_with_unit`: WCSAxes formatting only with real coords, a world `x_att`, and `x_display_unit` equal to the component's native unit; otherwise the plain Axes path.` | Reason: profile-wcs.A verifier (verified today: `git show profile-wcs:glue/viewers/profile/state.py | grep _wcsaxes_with_unit` -> lines 109, 198, 200).
- **H-P3** L65, L75, L80, L83, L86 | `- [ ]` -> `- [x]` (f767d320, c3bcd75b); L77-78 | old: `make it a plain method, not a state-mutating\n      property getter` | new: `implemented as a non-mutating `wcsaxes_slice` property (state.py:210) that reads `self.slices[i]`` | Reason: profile-wcs.A verifier; verified today (`@property` + `def wcsaxes_slice` at lines 209-210).
- **H-P4** L91-95 | old: `Explicitly dead — do not carry from the old branch:\n\n- The `x_att → x_att_pixel` swaps in `apply_roi` /\n  `is_convertible_to_single_pixel_cid` (main deliberately went the other\n  way for units).` | new: `Decision: the `apply_roi` swap to `x_att_pixel` is reinstated only when `wcsaxes_active` (subsets are defined on the pixel axis in WCSAxes mode); it stays out otherwise.` and keep the remaining "dead" bullets (L96-100). | Reason: profile-wcs.A verifier ("swap reinstated only when wcsaxes_active"; verified today: `wcsaxes_active` at state.py lines 190, 257, 268, 278).
- **H-P5** L108, L117, L120 | `- [ ]` -> `- [x]` (1133c0e9); L111-116 | old: `One fix needed upstream: it\n      registers the `y_att` callback unconditionally while `z_att` is\n      already `hasattr`-guarded; `ProfileViewerState` has no `y_att`, so\n      guard `y_att` the same way.` | new: `Done, larger than one fix: `hasattr` guards for `y_att`/`z_att`, `x_att_pixel` support, stale-slider clearing, and a guard while `len(slices) != ndim`.`; L122-123 | old: `gated on Piece A being\n      present in the installed glue-core (version floor).` | new: `gated by feature detection, not a version floor: `wcs=hasattr(ProfileViewerState, 'wcsaxes')` (data_viewer.py:34) and `hasattr(viewer_state, 'slices')` (options_widget.py:41); 68 passed / 14 skipped against installed glue-core 1.27.0.` Add after L123: `- [ ] The `profile_tools.py` nearest-index fix (main ignores `x_display_unit` there) is independent of A/C and mergeable today; consider splitting it into its own tiny glue-qt PR.` | Reason: profile-wcs.B auditor + verifier; verified today (`git show profile-wcs:glue_qt/viewers/profile/data_viewer.py | grep hasattr` -> line 34; options_widget.py line 41; the 68/14 test count is the verifier's, not re-run).
- **H-P6** L129, L135, L138, L141 | `- [ ]` -> `- [x]` (175e7129); add after L142: `- [x] (98d7bb7c) `ProfileLayerState.slice_view` translates the reference slice to each linked layer through the links (`ref[data.pixel_component_ids[axis], point]`), raising `IncompatibleDataException` on `IncompatibleAttribute` or out-of-range. Known wart: an out-of-range slice on the reference data itself raises `IndexError` at state.py:582 and the artist is hidden silently.` | Reason: sync-slicing P3.2-d, profile-wcs.C verifier.
- **H-P7** L144-148 | append: `Reorder C -> A verified (cherry-pick 175e7129+98d7bb7c, then f767d320+c3bcd75b; one `python_export.py` conflict per piece; result byte-identical to the branch tip). Before opening the glue-core PRs fix 3 RUF059 (`x, y = ...` -> `_, y = ...`) at `glue/viewers/profile/tests/test_state.py:229`, `:257` and `tests/test_viewer.py:336` (ruff 0.15.20, unsafe-fix only, `main` clean). Before the glue-qt PR drop the committed but gitignored `glue_qt/_version.py` (`.gitignore:47`).` | Reason: profile-wcs upstream-prs verifier; verified today (`ruff 0.15.20` on `wt-wp0-pw`: exactly those 3 RUF059; `main`: All checks passed; `git ls-tree profile-wcs -- glue_qt/_version.py` -> blob 0b097aeb; glue-qt `profile-wcs` ruff clean).
- **H-P8** L150-152 | keep `[ ]`; add a line: `This TODO maps to no gap-plan phase; the nearest is 3.2, but 98d7bb7c is intra-viewer slice translation only, not cross-viewer sync.` | Reason: profile-wcs doc_corrections item 3, phase-3.2 verifier.

### H-M `/Users/nabil/Git/glue-qt/MACOS_INTEGRATION_TODO.md` (untracked)

- **H-M1** L22-25 | old: `This fixes window titles, and on macOS Qt uses the display name for\n      the auto-generated About/Quit menu-item labels.` | new: `On macOS the menu title and the About/Hide/Quit labels come from `CFBundleName` (qtbase `qcocoahelpers.mm`, `qt_mac_applicationName()`), not from `applicationName`/`applicationDisplayName`; the NSBundle mutation below is the entire macOS fix, so conda-forge users (no pyobjc) get no macOS change. `setApplicationDisplayName('glue')` does affect native top-level window titles on Linux/Windows: the main window "Glue" becomes "Glue — glue" because `endsWith` is case-sensitive; use `'Glue'` or drop the call. MDI viewer windows are unaffected.` | Reason: MACOS-1 verifier; the CFBundleName effect verified today (`chk_branch.py` isolated HOME: `CFBundleName before Python`, `after glue`, `applicationName glue`); the qtbase/qplatformwindow claims are the verifier's, not re-run.
- **H-M2** L46-49 | keep `[x]`, add: `- [ ] conda-forge follow-up: the glue-qt feedstock lists no pyobjc; open a feedstock PR after merge.` | Reason: MACOS-1 auditor doc_corrections.
- **H-M3** L53-55 | old: `Automated test can only assert\n      `applicationName()`/`applicationDisplayName()`.` | new: `Headless test (not yet added): on Darwin assert `NSBundle.mainBundle().infoDictionary()['CFBundleName'] == 'glue'` after `get_qapp()`; that key is what feeds the title/About/Quit labels.` | Reason: MACOS-3/MACOS-5 verifier; verified today (`chk_branch.py`).
- **H-M4** L88-89 | old: `(make it 0; decide whether to keep the\n      1-point reduction elsewhere or zero both)` | new: `(both offsets zeroed on the branch)` | Reason: MACOS-2 auditor doc_corrections.
- **H-M5** L98-101 | change `- [x]` to `- [ ]` and append: `Open: the slice-widget 0.75x is still in place (`glue_qt/viewers/common/data_slice_widget.py:46`); decide keep/drop after the visual pass.` | Reason: MACOS-2 auditor; verified today (`grep -n 0.75 data_slice_widget.py` -> line 46).
- **H-M6** L110-111 | `- [ ]` -> `- [x]` (no-op, already correct; verified by MACOS-3: `app.py:104-107`). L120 | `- [ ]` -> `- [x]` (PR #68 body carries the before/after screenshots). L122-123 | append: `Note: `main` was already red (pytest-flake8 vs pytest 9 `PluginValidationError`; leaked viewers in `test_removed_subset`); the branch carries those CI repairs and the PR body should say so.` | Reason: MACOS-3, MACOS-4 verifier.
- **H-M7** L119, L126 | keep `[ ]`.
- **H-M8** Add under "Issue 2" after L101: `Pitfall: any main-based `get_qapp()` run outside pytest writes `font_size = 9.0` into `~/.glue/settings.cfg`; on the branch a real Cocoa session treats that as a user override and renders 9 pt (the symptom this PR fixes). Ensure the line reads `font_size = -1.0` before judging visually (today it does).` | Reason: MACOS-2 verifier; verified today (read-only `grep font_size ~/.glue/settings.cfg` -> `-1.0`).
- L13-18 ("Cause") stays: it describes the pre-fix state (MACOS-2 verifier: not a doc error).

**Verified code.** Everything below was run today (2026-09-02) from `/Users/nabil/Git/glue-solar` with `HOME=<scratchpad>/home-wp9 QT_QPA_PLATFORM=offscreen MPLBACKEND=agg GLUE_TESTING=True` and `.venv/bin/python`, and re-run by the checker at ~17:30 with `HOME=<scratchpad>/home-wp9chk` (outputs identical unless a line says otherwise; blocks marked "checker" were added by the checker). In zsh set the variables inline on the command (`env HOME=... .venv/bin/python ...`); a `$E="env HOME=..."` shorthand does not word-split and fails with "no such file or directory".

```
$ .venv/bin/python <scratchpad>/sv2_probe.py            # labels, autolink, stack, moments
glue 1.27.0 .../site-packages/glue/__init__.py
irispy 0.8.1 astropy 8.0.1
SJI wcs: <class 'gwcs.wcs._wcs.WCS'> names: ('Longitude', 'Latitude', 'Time (UTC)') ptypes: ('custom:pos.helioprojective.lon', 'custom:pos.helioprojective.lat', 'time')
SJI extra_coords: ['exposure time', 'obs_vrix', 'ophaseix', 'pztx', 'pzty', 'slit x position', 'slit y position', 'xcenix', 'ycenix'] mask None: False
SJI Data comps: [..., 'Time (Utc)', 'Latitude', 'Longitude', 'SJI_1400-3620258102-2021-09-05T00:18:33', '... mask']
raster comps: [..., 'Helioprojective Longitude', 'Helioprojective Latitude', 'Wavelength', 'Mg_II_k_2796-...-scan-0', '... mask', 'Time']
raster coords names: ['Wavelength', 'Helioprojective Latitude', 'Helioprojective Longitude'] ('m', 'arcsec', 'arcsec') ctype ['WAVE', 'HPLT-TAB', 'HPLN-TAB']
raster meta Quantity keys: ['exposure time', 'observer radial velocity']
wcs_autolink (installed) links: 0
WCSLink: AttributeError '_GlueWCS' object has no attribute 'has_celestial'
raw autolink sji,ras RAISED AttributeError 'WCS' object has no attribute 'has_celestial'
raw autolink ras,sji RAISED AttributeError Data has already been assigned to a different hub   # script artefact, see sv2_probe_b.py
raster has_celestial: True
serialize SJI_1400-... FAIL AttributeError Data has already been assigned to a different hub    # script artefact
serialize Mg_II_k_2796-...-scan-0 FAIL AttributeError Data has already been assigned to a different hub   # script artefact
serialize raster w/o Quantity meta FAIL GlueSerializeError Don't know how to serialize <glue_solar.sources.loaders.iris._GlueWCS ...>
stack input n: 13 dtype >f4 mask cnt 2344 masked vals [-200.]
stack: C_II_1336-3860258481-2014-03-29T14:09:38-stack float32 memmap nan in scan0: 2344 names: ['Wavelength', 'Helioprojective Latitude', 'Helioprojective Longitude', 'Scan'] Time: datetime64[ns] (13, 8, 109, 17)
calculate_moments sig: (cube, *, rest_wavelength=None, wings=None, integrated=False, min_intensity=None, saturation_limit=None)
rest_wavelength: 279.61999511700003 nm
keys: ['intensity', 'centroid', 'width', 'velocity', 'velocity_width'] RasterCollection
   velocity (187, 40) km / s ['Helioprojective Latitude', 'Helioprojective Longitude']
# ponytail: sv2_probe.py reuses Data objects across DataCollections, so its session lines print
# "already assigned to a different hub"; the session facts come from sv2_probe_b.py below.
```

```
$ .venv/bin/python <scratchpad>/sv2_probe_b.py          # sessions + raw autolink both orders
_GlueWCS isinstance High: False Low: True mro: ['_GlueWCS', 'BaseWCSWrapper', 'BaseLowLevelWCS', 'object']
serialize sji FAIL GlueSerializeError Don't know how to serialize <glue_solar.sources.loaders.iris._GlueWCS ...>
serialize raster FAIL TypeError no implementation found for 'numpy.save' on types that implement __array_function__: [<class 'astropy.units.quantity.Quantity'>]
raster w/o Quantity meta FAIL GlueSerializeError Don't know how to serialize <..._GlueWCS ...>
raster raw astropy -TAB WCS, clean meta: OK
raw autolink sji,ras RAISED AttributeError 'WCS' object has no attribute 'has_celestial'
raw autolink ras,sji RAISED AttributeError 'WCS' object has no attribute 'has_celestial'
parallel_fit_dask: True
```

```
$ .venv/bin/python <scratchpad>/cc_collapse.py          # A15/A16 Collapse tab
map shape (8, 109) == nansum over wl 10:40: True
draw OK; slices: ['int', 'int', 'AggregateSlice']
collapse funcs: [nanmean, nanmedian, nanmin, nanmax, nansum, mom1, mom2]
```

```
$ .venv/bin/python -c "from irispy.obsid import ObsID; print(ObsID(3860258481))"   # A7
IRIS OBS ID 3860258481
Description:           Very large coarse 8-step raster 14x175 8s
SJI filters:                       Si IV   Mg II h/k   Mg II w s
SJI field of view:                                       175x175
Exposure time:                                               8.0 s
Binning:                               Spatial x 1, Spectral x 1
FUV binning:                         FUV spectrally rebinned x 2
SJI cadence:                                 SJI cadence default
Compression:                                 Default compression
Linelist:                                       Flare linelist 1
```

```
$ .venv/bin/python -c "
import warnings; warnings.filterwarnings('ignore')
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
f=[str(p) for p in get_test_data_filenames() if 'sns/' in str(p) and 'raster' in str(p)][0]
d=raster_data([f],['Mg II k 2796'])[0]
t=d.get_component('Time').data
print('OBS_DESC:', d.meta['OBS_DESC']); print(d.label, d.shape, [c.label for c in d.world_component_ids], t.min(), t.max())"   # A13
OBS_DESC: Medium sit-and-stare 0.3x60 1s  C II   Si IV   Mg II h/k   Mg II w s
Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0 (187, 40, 52) ['Helioprojective Longitude', 'Helioprojective Latitude', 'Wavelength'] True 2021-09-05T00:18:37.750000000 2021-09-05T05:07:31.400000000
```

```
$ .venv/bin/python <scratchpad>/cc_stackwcs.py          # A3/A12 per-scan gwcs stack WCS
scan 0: gwcs lon/lat 489.966/279.546 vs per-scan -TAB 489.966/279.546  dlon=0.00e+00
scan 1: gwcs lon/lat 490.137/279.579 vs per-scan -TAB 490.137/279.579  dlon=0.00e+00
scan 2: gwcs lon/lat 490.308/279.581 vs per-scan -TAB 490.308/279.581  dlon=0.00e+00
numerical_inverse failed: ValueError too many values to unpack (expected 2)
world_to_pixel_values failed: ValueError too many values to unpack (expected 2)
```

```
$ grep -rniE "ffmpeg|imageio|FuncAnimation|movie|\.mp4|\.gif" <site-packages>/glue /Users/nabil/Git/glue-qt/glue_qt --include='*.py' -l | grep -v /tests/
(no output)                                              # A6/A9: no sequence export anywhere
$ ls /Users/nabil/Git/glue-qt/glue_qt/plugins
__init__.py  dendro_viewer  tools
$ grep -n "playback\|QTimer" /Users/nabil/Git/glue-qt/glue_qt/viewers/common/data_slice_widget.py | head -3
50:        self.button_first.setIcon(get_icon('playback_first'))
52:        self.button_prev.setIcon(get_icon('playback_prev'))
81:        self._play_timer = QtCore.QTimer()
```

```
$ sed -n 22,26p <site-packages>/glue/viewers/profile/state.py                     # A5/A11
FUNCTIONS = OrderedDict([('maximum', 'Maximum'), ('minimum', 'Minimum'), ('mean', 'Mean'), ('median', 'Median'), ('sum', 'Sum')])
$ grep -n "^class " <site-packages>/glue/core/fitters.py                            # A17
17:class BaseFitter1D(object)   173:class AstropyFitter1D(BaseFitter1D)   269:class BasicGaussianFitter(BaseFitter1D)   348:class PolynomialFitter(BaseFitter1D)
$ grep -n "Worker\|_fit_worker" /Users/nabil/Git/glue-qt/glue_qt/viewers/profile/profile_tools.py
16:from glue_qt.utils import Worker   222:        w = Worker(self._fit, fitter, xlim=x_range)   227:        self._fit_worker = w
```

```
$ PATCH=0 .venv/bin/python <scratchpad>/v_qt.py           # A11/A19/B3 selection direction
ROI drawn on RASTER viewer -> mask on raster: OK n=16758 | on SJI: OK n=12200
ROI drawn on SJI viewer -> mask on SJI: OK n=25172 | on raster: IncompatibleAttribute()
coords string at (18,20): −33" −400" (world)
```

```
$ .venv/bin/python -c "import sunpy.timeseries"                                    # A20
ModuleNotFoundError: No module named 'h5netcdf'
$ .venv/bin/python -c "
import numpy as np
from glue.utils.matplotlib import datetime64_to_mpl
from matplotlib.dates import num2date, date2num
t=np.array(['2021-09-05T00:16:12'],dtype='datetime64[s]')
v=datetime64_to_mpl(t)
print('glue value', v, '-> mpl num2date', num2date(v[0]), '| mpl date2num', date2num(t))"
glue value [738038.01125] -> mpl num2date 3990-09-06 00:16:12+00:00 | mpl date2num [18875.01125]
$ grep -rn "set_epoch\|date.epoch" <site-packages>/glue /Users/nabil/Git/glue-qt/glue_qt --include='*.py'
(no output)
$ grep -n "0001" <site-packages>/glue/utils/matplotlib.py
449:T0 = np.datetime64('0001-01-01T00:00:00').astype('datetime64[s]')
```

```
$ .venv/bin/python <scratchpad>/cc_region.py            # A21 RegionData on WCS Data
  File ".../glue/core/coordinate_helpers.py", line 42, in pixel2world_single_axis
    original_shape = pixel[0].shape
AttributeError: 'tuple' object has no attribute 'shape'
$ .venv/bin/python <scratchpad>/ver_sess3.py            # A4 sunpy Map session crash on main code
converted via read_sunpy_map <class 'glue.core.data.Data'>
meta type MetaDict coords WCS cmap LinearSegmentedColormap
SAVE FAIL: TypeError Object of type LinearSegmentedColormap is not JSON serializable
```

```
$ .venv/bin/pip show irispy-lmsal | grep Requires        # E (ndcube) and A17 (dask)
Requires: astropy, dask, dkist, gwcs, mpl-animators, ndcube, pandas, scipy, sunpy, sunraster
$ git show main:glue_solar/sources/loaders/stack_spectrograms.py | grep -n ndcube
8:from ndcube import NDCube
$ git diff main...HEAD -- pyproject.toml | grep '^+  "ndcube'
+  "ndcube>=2.0",
$ grep -n "aia_l2_\|INSTRUME" glue_solar/sources/loaders/scan.py | head -3          # B1
112:    instrume = str(header.get("INSTRUME", ""))
115:    return name.startswith("aia_l2_") and instrume.startswith("AIA")
$ git -C /Users/nabil/Git/irispy log --diff-filter=A --format=%h -- irispy/utils/moments.py | tail -1 | xargs git -C /Users/nabil/Git/irispy tag --contains
v0.7.0  v0.8.0  v0.8.1                                    # A15/A22
```

```
$ gh pr view 44 -R glue-viz/glue-solar --json state,mergeable,reviews,reviewRequests,headRefOid
{"state":"OPEN","mergeable":"MERGEABLE","reviews":0,"reviewRequests":0,"head":"d3a2bd3","checks":[null,"SKIPPED","SUCCESS"]}
$ gh pr view 68 -R glue-viz/glue-qt ...   -> {"state":"OPEN","reviews":0,"createdAt":"2026-08-29T13:40:59Z","head":"bd4dce6"}
$ gh pr list -R glue-viz/glue --author nabobalis --state open  -> only #2248 (draft, 2021-11-09)
$ grep -c '\[ \]' /Users/nabil/Git/glue/APE14_AUTOLINK_TODO.md            -> 19   (checked: 0)
$ grep -c '\[ \]' /Users/nabil/Git/glue/PROFILE_WCS_RESTART_TODO.md       -> 14   (checked: 0)
$ grep -c '\[ \]' /Users/nabil/Git/glue-qt/MACOS_INTEGRATION_TODO.md       -> 15   (checked: 8)
$ git -C /Users/nabil/Git/glue-qt ls-tree profile-wcs -- glue_qt/_version.py
100644 blob 0b097aebe2c67b70f393c8dbbd0f19b6752021ac	glue_qt/_version.py         # H-P7
```

```
$ (cd <scratchpad>/wt-wp0-pw && <scratchpad>/ruff15/bin/ruff check --no-cache --output-format concise glue/viewers/profile/)   # H-P7
glue/viewers/profile/tests/test_state.py:229:5: RUF059 Unpacked variable `x` is never used
glue/viewers/profile/tests/test_state.py:257:5: RUF059 Unpacked variable `x` is never used
glue/viewers/profile/tests/test_viewer.py:336:8: RUF059 Unpacked variable `y` is never used
$ (cd /Users/nabil/Git/glue && ruff15 check glue/viewers/profile/)  -> All checks passed!
$ (cd <scratchpad>/wt-wp0-ape14 && <scratchpad>/ruffpkg/bin/ruff check --no-cache --output-format concise glue/plugins/wcs_autolinking/)   # H-A8 (ruff 0.16.5)
glue/plugins/wcs_autolinking/wcs_autolinking.py:82:5: PLR0917 Too many positional arguments (6 > 5)
glue/plugins/wcs_autolinking/wcs_autolinking.py:148:9: PLR0917 Too many positional arguments (7 > 5)
(+4 CPY001 that main also reports)
$ (cd <scratchpad>/wt-wp0-ape14 && ruff15 check glue/plugins/wcs_autolinking/)  -> All checks passed!
```

```
$ .venv/bin/python <scratchpad>/chk_branch.py            # H-M1/H-M3 (editable glue-qt = macos-integration)
CFBundleName before Python __NSDictionaryM
CFBundleName after glue
applicationName glue | displayName glue | argv ['glue']
settings.FONT_SIZE after -1.0            (isolated HOME; user's ~/.glue/settings.cfg read-only: font_size = -1.0, unit_converter = "default")
```

```
$ .venv/bin/python -m pytest glue_solar -q -o addopts='' -p no:cacheprovider
27 passed, 2 warnings in 1.48s                          # checker re-run: 27 passed, 2 warnings in 1.56s
```

```
# checker: A14 / section C default Image Viewer axes (<scratchpad>/wp9chk_axes.py)
$ cat > <scratchpad>/wp9chk_axes.py <<'EOF'
import warnings; warnings.filterwarnings("ignore")
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from glue_qt.app import GlueApplication
from glue_qt.viewers.image import ImageViewer
fs = sorted(str(f) for f in get_test_data_filenames() if "20140329" in str(f) and str(f).endswith(".fits"))
[ras] = raster_data(fs[:1], ["Mg II k 2796"])
[stack] = raster_data(fs[:3], ["Mg II k 2796"], stack=True)
app = GlueApplication()
for d in (ras, stack):
    app.data_collection.append(d)
    v = app.new_data_viewer(ImageViewer, data=d)
    s = v.state
    sliders = [d.world_component_ids[i].label for i in range(d.ndim) if i not in (s.x_att.axis, s.y_att.axis)]
    print(f"{d.label} shape={d.shape}: x={s.x_att_world.label!r} y={s.y_att_world.label!r} sliders={sliders}")
app.close()
EOF
$ env HOME=<scratchpad>/home-wp9chk QT_QPA_PLATFORM=offscreen MPLBACKEND=agg GLUE_TESTING=True .venv/bin/python <scratchpad>/wp9chk_axes.py
Mg_II_k_2796-3860258481-2014-03-29T14:09:38-scan-0 shape=(8, 109, 63): x='Wavelength' y='Helioprojective Latitude' sliders=['Helioprojective Longitude']
Mg_II_k_2796-3860258481-2014-03-29T14:09:38-stack shape=(3, 8, 109, 63): x='Wavelength' y='Helioprojective Latitude' sliders=['Scan', 'Helioprojective Longitude']
```

```
# checker: H-A6 (_GlueWCS object classes still in deg while values are arcsec)
$ .venv/bin/python -c "
import warnings; warnings.filterwarnings('ignore')
from astropy.wcs.wcsapi import HighLevelWCSWrapper
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
f=[str(p) for p in get_test_data_filenames() if 'sns/' in str(p) and 'raster' in str(p)][0]
d=raster_data([f],['Mg II k 2796'])[0]
print('units', d.coords.world_axis_units)
try: print(HighLevelWCSWrapper(d.coords).pixel_to_world(0,20,93))
except Exception as e: print(type(e).__name__, str(e)[:130])"
units ('m', 'arcsec', 'arcsec')
ValueError Latitude angle(s) must be within -90 deg <= angle <= 90 deg, got -399.82807052472174 deg
```

```
# checker: step 4 rst check with a scratch docutils (0.23); the two "class" role errors pre-exist (Sphinx-only role)
$ .venv/bin/pip install --quiet --target <scratchpad>/docutils-pkg docutils
$ cd docs && for f in user_guide/loading-iris-level-2-raster-and-sji-data.rst user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst user_guide/loading-aia-and-hmi.rst dev_guide/loader-customization.rst; do echo "--- $f"; PYTHONPATH=<scratchpad>/docutils-pkg ../.venv/bin/python -m docutils --halt=5 $f /dev/null; done
--- user_guide/loading-iris-level-2-raster-and-sji-data.rst
--- user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst
--- user_guide/loading-aia-and-hmi.rst
--- dev_guide/loader-customization.rst
dev_guide/loader-customization.rst:19: (ERROR/3) Unknown interpreted text role "class".
dev_guide/loader-customization.rst:35: (ERROR/3) Unknown interpreted text role "class".
```

```
# checker: glue-qt pins ruff v0.14.14, not 0.15.20 (grep rev .pre-commit-config.yaml: glue "v0.15.20", glue-qt "v0.14.14")
$ (cd <scratchpad>/wt-wp0-qtpw && <scratchpad>/ruff14/bin/ruff check --no-cache --output-format concise glue_qt/)   # ruff 0.14.14
All checks passed!
$ .venv/bin/python -c "from importlib.metadata import requires; print([r for r in requires('irispy-lmsal') if r.split('[')[0].split('>')[0] in ('ndcube','astropy','dask')])"   # E, A17
['astropy>=7.2.0', 'dask[array]>=2024.7.0', 'ndcube>=2.4.0']
$ gh pr view 2248 -R glue-viz/glue --json isDraft,mergeable,updatedAt,commits --jq '{isDraft,mergeable,updatedAt,lastCommit:(.commits[-1].committedDate)}'   # H-P1
{"isDraft":true,"lastCommit":"2022-05-07T00:14:22Z","mergeable":"CONFLICTING","updatedAt":"2022-06-28T20:30:53Z"}
$ grep -n "AA_UseHighDpiPixmaps" /Users/nabil/Git/glue-qt/glue_qt/utils/app.py; sed -n 104,107p /Users/nabil/Git/glue-qt/glue_qt/utils/app.py   # H-M6
105:        qapp.setAttribute(QtCore.AA_UseHighDpiPixmaps)
    try:
        qapp.setAttribute(QtCore.AA_UseHighDpiPixmaps)
    except AttributeError:  # PyQt6/PySide6 don't have this setting as it is default
        pass
```

**Tests to add.** None: every edit is prose. Guards that already exist and must stay green: `pytest glue_solar -q -o addopts=''` (27 passed). If the maintainer wants the user-guide label claim pinned, add `glue_solar/tests/test_loaders.py::test_world_axis_labels` (new file; `glue_solar/tests/` holds only `test_importer.py`, `test_plugin.py`, `test_scan.py` today) asserting `[c.label for c in raster.world_component_ids] == ['Helioprojective Longitude', 'Helioprojective Latitude', 'Wavelength']` on `irispy_test_files` and the SJI labels `['Time (Utc)', 'Latitude', 'Longitude']` (or the normalised names if WP1 changes `_GlueWCS.world_axis_names`); do this in WP1, not here, since WP1 decides the names.

**Pitfalls (verified).**
- The Bash shell here is zsh: `--include=*.py` fails with "no matches found"; quote it (`--include='*.py'`). Hit today on the export grep.
- `sv2_probe.py` reuses Data objects across `DataCollection`s, so its serialization lines print "Data has already been assigned to a different hub"; use `sv2_probe_b.py` (fresh objects) for session facts. Hit today.
- `pytest` needs `-o addopts=''`: `pytest.ini` passes `--doctest-rst`, which requires pytest-doctestplus (not installed). Verified by browser-ux and science-moments verifiers; reproduced by the 27-pass run above.
- Run glue code with an isolated `HOME`: main-based `get_qapp()` outside pytest writes `font_size = 9.0` to `~/.glue/settings.cfg`, and a persisted non-default `unit_converter` makes `import glue` raise `KeyError` (units-lines-blink P3.3, macOS MACOS-2). Today the user's file is clean (`-1.0`, `"default"`); keep it so.
- Line numbers in some findings are off by two for the audit table (slit-overlay cites ":180" for the row at L182; "Audit L88-90" etc. are right). All numbers in this brief were re-derived from today's `cat -n`.
- CI-pinned ruff is 0.15.20 in glue (`.pre-commit-config.yaml:54`) but 0.14.14 in glue-qt (`:57`); scratch binaries exist for both (`<scratchpad>/ruff15/bin/ruff`, `<scratchpad>/ruff14/bin/ruff`) plus 0.16.5 (`<scratchpad>/ruffpkg/bin/ruff`). The PLR0917 hits appear only with 0.16.5. The 3 RUF059 hits appear with glue's pinned version and `--fix` cannot fix them (unsafe). glue-qt `profile-wcs` is clean on 0.14.14 and 0.15.20.
- Neither `sphinx` nor `docutils` is in the venv; `tox -e build_docs` needs network. Use the scratch-docutils recipe in step 4 (verified today) and expect the two pre-existing `:class:` role errors in `dev_guide/loader-customization.rst`; the docs CI job of PR #44 is the final check.
- WP9 shifts line numbers. Audit: A0 inserts 3 lines after L15; A1 +3, A2 +7, A3 +7, A4 +13, A5 +3, A6 +1 (rows in the table sit about 37 lines lower afterwards); rst `loading-iris...`: B1 +1, B2 +1, B3 +4, B4 +1. Every later brief (wp2/3/4/7/8) cites pre-WP9 numbers; find their targets by quoted text (`grep -n`), never by line.
- `sv2_probe.py` and `ver_sess3.py` reuse Data objects across `DataCollection`s, so their later lines print "Data has already been assigned to a different hub" (`ver_sess3.py`'s final "cmap=None SAVE+RELOAD" check therefore does not run; the `SAVE FAIL: TypeError ... LinearSegmentedColormap` line before it is the fact cited by A4).
- Do not remove or modify the `wt-wp0-*` worktrees in the scratchpad; they belong to the concurrently running WP0 agent (read-only ruff runs are fine).

**Acceptance criteria.**
- [ ] `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`: A0-A22 applied; `grep -c "| Partial |" IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` goes 12 -> 15 and `grep -c "| Missing |"` goes 5 -> 2 (GOES row and log row stay Missing); `grep -n "0.8.1"` shows only the "pins >= 0.8.1" context (A15) and the A0 date line; `grep -c "sequence export\|movie or sequence"` = 3 (the IDL L90 line, the A6 bullet, the A9 row); `grep -c "ObsID("` = 1 (A7, metadata row); `grep -c "2026-09-02"` >= 1 (A0).
- [ ] rst: B1-B4, C1, D1, G1 applied; `grep -n "_SDO\` folder\|AMI and HMI\|restored reliably\|manually pair" docs -r` returns nothing; `grep -n "Longitude" docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst` shows both label sets.
- [ ] `pytest glue_solar -q -o addopts=''` -> 27 passed; docs CI job of PR #44 green after the doc commit.
- [ ] `IRIS_GLUE_GAP_PLAN.md` unchanged (`git status` still lists it untracked, `md5` unchanged).
- [ ] `changelog/` unchanged.
- [ ] TODO files: only the section-H edits that WP0's brief does not already cover; `grep -c '\[x\]'` on APE14 >= 13, PROFILE >= 13 after H; no `§4a` left (`grep -rn "§4a" /Users/nabil/Git/glue /Users/nabil/Git/glue-qt --include='*.md'` empty); no "Delete .* link helper" / "Phase 1 item 4" text left.
- [ ] No branch checkout, stash, commit or push in `/Users/nabil/Git/glue` or `/Users/nabil/Git/glue-qt`; in glue-solar exactly one doc commit on `iris-observation-browser` (or none if the user prefers to fold it into the next commit).

**Dropped / out of scope.**
- `IRIS_GLUE_GAP_PLAN.md` edits (every plan-side doc_correction: status paragraph, L38/L41/L51-53, L102-135, L142-171, L194-198): the plan is being rewritten wholesale.
- ndcube changelog fragment: verifier ruling (no-op declaration; irispy already pins ndcube >= 2.4).
- README rewrite: no finding; optional one-liner given in F.
- `44.feature.rst` wording about wavelength units: belongs to WP1's fragment (D3).
- Time-aware SJI wrapper text in the audit: critic §2 says the all-ones matrix breaks `format_coord`; the audit only states the direction facts, no recommendation.
- Audit "Environment" notes about `settings.cfg`: stale per critic §2; nothing to write.
- IDL/SolarSoft rows and the launch hierarchy: not re-verified by anyone; untouched.
- MACOS TODO L13-18 "Cause": correct as a description of `main` (verifier).
- A regression test for the label names: deferred to WP1 (owner of `_GlueWCS` names).

**Docs.** All edits in this brief are the docs. Summary of the rst/changelog delta for the PR #44 commit message: `loading-iris-level-2-raster-and-sji-data.rst` (SDO cutout discovery, stack NaN/float32 note, Linking labels and selection direction, Save Session fails), `guide-to-glue-1dprofile-viewer-for-iris-data.rst` (stack note), `loading-aia-and-hmi.rst` (AMI -> AIA), `dev_guide/loader-customization.rst` (stack dtype/NaN). No changelog fragment (doc-only, PR #44 already has `44.feature.rst`).
