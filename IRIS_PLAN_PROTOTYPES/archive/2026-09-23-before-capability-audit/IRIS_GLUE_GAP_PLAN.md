# IRIS and Glue cross-repository work plan

Updated 2026-09-23 (America/Los_Angeles); previous validation 2026-09-22. This
is the single maintained work plan for `~/Git/glue`, `~/Git/glue-qt`, and
`~/Git/glue-solar`.

Revalidated against solar `main` `236f0a8`, the eleven open upstream PR
heads below, and selected prototypes on 2026-09-22 evening (2026-09-23 UTC).
The agreed target is **IRIS-first CRISPEX functionality**. The follow-up
on 2026-09-23 refreshes selected existing prototypes and explains the missing
interactions. It does not implement the remaining production features.
CI status is outside this work's scope.
Start with the [CRISPEX acceptance criteria](#iris-first-crispex-target)
and the [prototype index](IRIS_PLAN_PROTOTYPES/README.md).

It replaces the separate branch review, capability audit, APE-14 TODO,
profile-WCS TODO, and macOS TODO. Their full contents, including the previous
6,742-line plan, are preserved in the [archive](#archive). Do not maintain
parallel status lists or execute archived branch-publication instructions.
READMEs, changelogs, user/developer documentation and runnable prototypes
retain their own purposes and locations.

This plan and the prototype/archive directory remain local and untracked.
No documentation commit, push, PR merge, review request or implementation
of a future production work package is authorized by this consolidation.
The user separately authorized refreshing the existing prototypes; original
versions are retained in the [refresh archive](IRIS_PLAN_PROTOTYPES/archive/2026-09-23-prototype-refresh/).

## How to use this plan

1. Check the dated branch snapshot below before starting work. Refresh
   GitHub and the relevant checkout when acting on a PR or release gate.
2. Pick an unchecked task from WP0, WP9 or the implementation queue. Read
   its requirements and the linked prototype/evidence; trace current code
   before adapting historical snippets. This file takes precedence.
3. Preserve unrelated changes and the index. Stage named files only when
   committing is requested; never include the prototype archive incidentally.
4. Record completion here with the actual branch/commit, test command and
   result, validation limits, and remaining work. A prototype pass is not a
   production implementation; a pushed PR is not a merged release.
5. The GitHub wiki (`glue-viz/glue-solar.wiki`, clone at
   `~/Git/glue-solar.wiki`) is a public digest refreshed from this file.
   Never record status there first, and keep local paths, prototype links
   and environment notes out of it.

## Current branches and PRs

GitHub PR state and heads rechecked 2026-09-23 ~03:40 UTC
(2026-09-22 evening locally). Merge dates in the table are UTC. The
four glue-solar PRs are merged. The six core PRs and Qt #68/#69/#70 from
the 2026-09-05 snapshot are still open and every head has moved; Qt #74
and #75 are new drafts opened on 2026-09-22. Heads are abbreviated to 12
hex digits; the 2026-09-05 revision with full hashes is archived under
[archive/2026-09-22](IRIS_PLAN_PROTOTYPES/archive/2026-09-22/IRIS_GLUE_GAP_PLAN.md).

| Repository | Branch | PR | State | Head |
| --- | --- | --- | --- | --- |
| glue | `ape14-wcs-autolink` | [2595](https://github.com/glue-viz/glue/pull/2595) | Draft | `c49aeb1af14a` |
| glue | `profile-slice` | [2596](https://github.com/glue-viz/glue/pull/2596) | Draft | `1deff2999c9a` |
| glue | `profile-wcsaxes` | [2601](https://github.com/glue-viz/glue/pull/2601) | Draft | `acaf4e1c0ef8` |
| glue | `fix-session-style-meta` | [2597](https://github.com/glue-viz/glue/pull/2597) | Draft | `bfe16085ea57` |
| glue | `fix-world2pixel-correlated-axes` | [2598](https://github.com/glue-viz/glue/pull/2598) | Draft | `ca3fb185e5a4` |
| glue | `fix-datetime-epoch` | [2599](https://github.com/glue-viz/glue/pull/2599) | Draft | `dd881a47bb40` |
| glue-qt | `ci-fixes` | [69](https://github.com/glue-viz/glue-qt/pull/69) | Ready for review | `b5778ef5027a` |
| glue-qt | `macos-integration` | [68](https://github.com/glue-viz/glue-qt/pull/68) | Ready for review (was draft) | `aefab0dda25c` |
| glue-qt | `profile-wcs-pr` | [70](https://github.com/glue-viz/glue-qt/pull/70) | Draft | `f1471b7ad843` |
| glue-qt | `status-bar-cursor-readout` | [74](https://github.com/glue-viz/glue-qt/pull/74) | Draft, new | `6b579814eb7c` |
| glue-qt | `slice-widget-time-axis` | [75](https://github.com/glue-viz/glue-qt/pull/75) | Draft, new | `8852fcd13ca8` |
| glue-solar | `iris-observation-browser` | [44](https://github.com/glue-viz/glue-solar/pull/44) | Merged 2026-09-22 | `d3a2bd313546` |
| glue-solar | `loadable-iris-fixtures` | [50](https://github.com/glue-viz/glue-solar/pull/50) | Merged 2026-09-22 into #44 | `383dec253931` |
| glue-solar | `iris-timestamp` | [52](https://github.com/glue-viz/glue-solar/pull/52) | Merged 2026-09-22 | `1f4cf985bda1` |
| glue-solar | `mask` | [53](https://github.com/glue-viz/glue-solar/pull/53) | Merged 2026-09-22 | `8eddfecb2926` |

Solar `main` is `236f0a8` (merge of #53). Only `main` remains locally.
"Ready for review" means the draft flag is off, not maintainer approval.

Commits added since the 2026-09-05 heads:

- Core #2595: links low-level WCS pairs with reordered or overcomplete
  matched axes, makes the transform options keyword-only, avoids redundant
  slicing for 1D links and trims dead code.
- Core #2596: disables a layer for NaN/out-of-range slice points and resets
  x limits along the slice spine. #2601 sits on it and additionally tracks
  whether profile x limits are pixel coordinates across sessions and keeps
  WCSAxes mode working for `IndexedData` and saved zooms.
- Core #2597: filters unserializable meta values for `RegionData` too.
  #2598: the regression test uses a plain WCS. #2599 delegates the forward
  datetime conversion to `matplotlib.dates` and derives the inverse from
  its configured epoch. It preserves pre-epoch fractional datetimes and
  raises the tox legacy Matplotlib pin to 3.3.
- Qt #69: makes the restart-prompt test perform a real plugin change.
  #68: captures the default font size when a host created the
  `QApplication` and shares one toolbar icon-size helper. #70: drops two
  gates that released glue-core already satisfies and keeps the
  pre-existing profile tests running on released glue-core.
- Qt #74 (one commit): `MatplotlibDataViewer.cursor_status` shows the
  position under the mouse in every matplotlib viewer's status bar.
  #75 (two commits): slice sliders of WCS time axes are labelled with
  absolute times, warning about a slider's world value only when that
  world axis is dependent. #75 edits `slice_widget.py`, which #70 also
  touches.
- Solar #52: datetime64 `Time` component on SJI frames, raster exposures
  and stacks; `solar:frame_time` and `solar:cursor_readout` Image Viewer
  tools. #53: transparent NaN pixels for IRIS image layers. Details under
  "Completed work".

Branch dependencies and publication boundaries:

- Core `profile-wcsaxes` contains `profile-slice`; land #2596 before #2601.
- Qt #68, #70, #74 and #75 do not contain the complete `ci-fixes`
  branch. These are separate PR boundaries, not missing solar features.
  CI repair/status is outside this review; no merge/rebase is requested.
- Solar #50 merged into #44, which merged into `main`; nothing remains to
  retarget. Solar registers `solar:cursor_readout` only while glue-qt
  lacks `cursor_status`, so releasing Qt #74 silently retires it.
- Core local `main` (`dae530c3`) is now seven commits behind upstream
  (`77dc9b88`): the one-line `glue/core/state_path_patches.txt` drift
  remains, plus image-viewer state changes from #2594. Qt local `main`
  equals upstream `main` (`9780eaf9`). Recheck before rebasing core branches.
- Primary checkouts: core on `fix-session-style-meta` (clean), Qt on
  `status-bar-cursor-readout` with an untracked generated
  `glue_qt/_version.py`, solar on `main` (clean apart from this plan and
  the prototype directory). The solar `.venv` imports glue-qt editable
  from the Qt checkout, so solar tests run against whichever Qt branch is
  checked out there.
- Releases: glue-core latest v1.27.0 (2026-06-25), glue-qt v0.4.2
  (2026-02-11), glue-solar unreleased, as recorded in the earlier snapshot.
  Release feeds were not refreshed in this validation. The feature PRs
  listed as open have not merged; installed metadata is not proof of them.

### What the upstream PRs provide

These are source capabilities on separate branches, not one combined,
installed application. Local branch heads matched the GitHub heads above.

| PR(s) | Provides | Does not provide |
| --- | --- | --- |
| Core #2595 | Low-level APE-14 WCS pixel linking | Solar wrapper unit coherence, time matching, or tracking moving SJI geometry at every exposure |
| Core #2596, #2601; Qt #70 | Selected-pixel slice profiles, optional WCSAxes and profile sliders; profile navigation in display units | Image-cursor-to-profile synchronization, cursor lock, or a complete quicklook |
| Core #2597 | Avoids colormap/metadata save crashes, including RegionData | IRIS WCS serialization, retention of otherwise skipped Quantity metadata, or restoration of preferred colormaps |
| Core #2598 | Correct correlated world inputs for inverse transforms | Observation pairing or temporal links |
| Core #2599 | Uses Matplotlib's epoch for datetime conversion | A temporal navigation controller |
| Qt #74 | Cursor coordinates and reference-layer scalar value | A spectrum following the cursor; #52's frame-time tool remains useful |
| Qt #75 | Absolute labels/typed times for WCS axes that yield Astropy Time | Labels derived from a standalone `Time` component; raster exposure/stack scan axes lack a time WCS; no cross-viewer sync |
| Qt #68 / #69 | Platform integration / test infrastructure work | Additional CRISPEX science or navigation features |

Qt #70 and #75 both modify `slice_widget.py`; validate their combined
profile/image behavior when integrated. No combined #70+#75 build was
tested here. Core #2601 contains #2596; use the former for the combined
profile capability, while preserving the PR landing order.

## Repository cleanup, 2026-09-05

All remotes were fetched with pruning before final branch decisions. No
remaining tracking branch is ahead of or divergent from its configured
origin branch. No remote branch, open PR, tag or primary checkout was deleted.

- [x] Removed all seven linked review worktrees after verifying no tracked,
  untracked or ignored changes: `core-ape14`, `core-datetime`,
  `core-profile-slice`, `core-profile-wcsaxes`, `qt-ci`, `qt-profile`, and
  `solar-fixtures`. Only the three primary repository checkouts remain.
- [x] Removed the empty `~/Git/glue-fixes` container and its Finder metadata.
  Worktree commits remain in their local branches and on origin.
- [x] Removed the untracked, generated `glue/glue/_version.py`; the build's
  `version_file` setting regenerates it, and runtime version discovery uses
  installed package metadata. No source change was committed.
- [x] Removed the three redundant local branch names listed below using
  Git's normal branch-deletion checks. No force deletion was needed.
- [x] Preserved the central plan, complete archive/prototypes, all open-PR
  branches, and the unique solar backup. No cleanup commit or push was made.

| Local branch removed | Old tip | Why it was unnecessary / recovery source |
| --- | --- | --- |
| glue `profile-wcs` | `c3bcd75be2e0592c454d5fb71f1efe29f39002a1` | Old unsplit work: production code matched the published WCSAxes split before the latest fixes; remaining differences were unused test variables. Exact original tip remains on `origin/profile-wcs`. |
| glue-qt `profile-wcs` | `1133c0e95a85f0abb9ffc709353649de6f173166` | Superseded by `profile-wcs-pr`; the pre-fix split differed only by removal of a generated version file. Exact original tip remains on `origin/profile-wcs`. |
| glue-qt `macos-integration-v2` | `4d93c64f6b90621d4541ecbeede3591272ed1eae` | Local-only rewrite alias with no unpublished commits; this tip is an ancestor of published `origin/macos-integration`. |

At the 2026-09-05 check the only remaining local-only branch was solar
`backup/iris-observation-browser-pre-rebase` at
`93d05f05c250dfb3f96b419069d046df8090f09a`, a safety copy made from
`iris-observation-browser` before the rewrite, with 11 commits not
reachable from any remote ref, including `docs/make_screenshots.py`, a
196-line utility that regenerates the 1D-profile user-guide screenshots
from a real multi-scan observation. Update 2026-09-22: that branch ref no
longer exists locally (it went with the merged solar feature branches), the
helper is on neither `main` nor in the prototype archive, but commit
`93d05f05` is still in the object store (`git cat-file -t` reports
`commit`) and can be recovered until garbage collection.

- [ ] Decide whether to keep `docs/make_screenshots.py`, e.g.
  `git show 93d05f05:docs/make_screenshots.py > IRIS_PLAN_PROTOTYPES/archive/make_screenshots.py`,
  or recreate the branch with
  `git branch backup/iris-observation-browser-pre-rebase 93d05f05c250dfb3f96b419069d046df8090f09a`,
  before `git gc` discards it. Do not push it as a feature branch.

## Completed work and evidence

- [x] Published the split APE-14, profile, macOS and supporting core fixes.
  PR publication, the #68 rewrite/body/draft update, and closure of #2248
  were already complete before the latest review.
- [x] Fixed slice profiles and exported profiles to use the selected view
  for both intensities and world coordinates, including linked/transposed
  layers, unit overrides, changing slices and subset masks (#2596/#2601).
- [x] Fixed negative fractional datetime round trips (#2599). The current
  head uses `dates.date2num` and rounded nanoseconds relative to
  `dates.get_epoch()`; the earlier floor-seconds implementation is superseded.
- [x] Avoided redundant sliced-WCS wrappers so mixed 1D APE-14/FITS linking
  works on Astropy 6.1.7 as well as 8.0.1 (#2595).
- [x] Corrected the Qt permission test to make an actual plugin change
  before saving; propagated the shared CI configuration/viewer cleanup
  into the profile branch (#69/#68/#70).
- [x] Made the solar fixtures compatible with irispy 0.8.1: non-degenerate
  synthetic pointing and lookup of both historical and `_test.fits` names
  (#50). This is fixture compatibility, not a production-loader defect.
- [x] Fixed the WP4 prototype to call WP1's real `link_hpc(dc)` and add its
  returned links. Fixed both WP6 variants to expose WP3's serializable
  outer `_GlueWCS`; added integrated regressions.
- [x] Reconstructed the missing WP8 UI from its inline diff. The historical
  `wp4_common.py.writer` was not retained; long PR drafts are under `wp0/`,
  not `wp0/long/`. No archive-completeness claim extends to missing files.
- [x] Committed/pushed the eight repaired branches and verified remote
  heads. Post-merge source hashes matched the tested files; the Qt profile
  merge additionally inherited the generated-version ignore rule.
- [x] Consolidated all six work-tracking documents here, preserving their
  bodies in a dated archive. Remaining repo-specific tasks are below.
- [x] Merged solar #44 (observation browser) with its fixture child #50
  into `main` on 2026-09-22 and deleted the merged local branches.
- [x] Merged solar #52 (2026-09-22): `_cube_data` attaches a datetime64
  `Time` component to SJI frames (gWCS time axis), raster exposures (extra
  coordinate) and stacks; `glue_solar/tools.py` adds the `solar:frame_time`
  status-bar readout and the `solar:cursor_readout` WCSAxes position/value
  readout, the latter registered only while glue-qt lacks `cursor_status`.
  Covered by `glue_solar/tests/test_plugin.py`. No changelog fragment or
  user-guide text was added (see WP9).
- [x] Merged solar #53 (2026-09-22): the `iris_image_layer` layer-artist
  maker sets `cmap_bad` fully transparent for image layers of datasets
  with `OBSID` in their metadata. No changelog fragment (see WP9).
- [x] Opened Qt drafts #74 (generic status-bar cursor readout) and #75
  (absolute-time slice-slider labels) off upstream `main`; pushed follow-up
  commits to all six core PRs and to Qt #68/#69/#70 as summarised above.

### Local validation, 2026-09-05

| Check | Result |
| --- | --- |
| Core slice profile suite | 42 passed, 1 skipped |
| Core WCSAxes profile suite, repeated after merge | 63 passed, 1 skipped |
| Datetime utilities plus histogram/scatter viewer tests | 162 passed, 4 skipped |
| APE-14 plus related links, Astropy 8.0.1 | 69 passed, 1 xfailed, 1 xpassed |
| APE-14 suite, Astropy 6.1.7 / NumPy 2.2.6 | 31 passed, 1 xfailed, 1 xpassed |
| Qt CI full suite with development core | 619 passed, 4 skipped, 2 xfailed |
| Qt macOS full suite with development core, repeated after merge | 622 passed, 4 skipped, 2 xfailed |
| Qt profile full suite with core WCSAxes, repeated after merge | 625 passed, 4 skipped, 2 xfailed |
| Solar browser full suite | 27 passed |
| Solar fixture full suite with irispy 0.8.1 | 31 passed, 1 skipped |
| WP1/WP4, both WP6/WP3 round trips, restored WP8 UI | 4 passed |
| WP6 fitting prototype, including real irispy raster and worker completion | 8 passed |
| Unchanged core session / coordinate suites during review | 42 / 28 passed |

Changed files passed the checked Ruff configurations and diff-whitespace
checks. These were source-worktree tests, not recreated wheel/tox matrices
on every supported platform. The main local environment lacks
pytest-doctestplus and pytest-mpl; skipped visual tests are not certified.
Existing xfail/xpass results were retained. Native interactive macOS
behavior, full science workflows and all prototype combinations remain
outside those test counts.

### Local validation, 2026-09-22

| Check | Result |
| --- | --- |
| Solar full suite on `main` `236f0a8` (glue-core 1.27.0, glue-qt editable at `status-bar-cursor-readout`, irispy 0.8.1, Python 3.14.7, isolated `HOME`) | 33 passed, 2 skipped |

`pytest.ini` passes `--doctest-rst`, which needs the uninstalled
pytest-doctestplus; the run used `-o addopts=""`. The 2026-09-05 table is
history: it predates #52/#53 and the branch updates.

The evening revalidation reproduced **33 passed, 2 skipped** on solar main
and ran selected prototype and current PR tests. Results and commands are
in the [prototype index](IRIS_PLAN_PROTOTYPES/archive/2026-09-23-prototype-refresh/README.before-refresh.md#validation-2026-09-22).
The two solar skips are low-level autolinking on released core and the
solar cursor tool superseded by the checked-out Qt #74 implementation.
Neither is a completed CRISPEX acceptance test. Source snapshots of core
#2601 and Qt #70 passed their selected viewer suites; #70+#75 integration,
native interactive behavior and a CRISPEX end-to-end session remain untested.

## WP0: Existing PRs and integration boundaries

Publication is complete. Remaining work is validation and review, not
creating replacement PRs or repeating completed branch operations.

- [ ] Validate the integrated core profile and Qt profile/time-slider
  branches against the solar workflow. Separate branch tests do not prove
  all open PRs work together. CI status/repair is excluded from this plan
  review at the user's request.
- [ ] User reviews each draft before it is marked ready; #68 and #69 are
  already ready, #70/#74/#75 and the six core PRs are drafts. Do not
  request reviews or merge any PR without direction.
- [ ] Track the releases containing core #2595/#2597/#2598/#2599 and the
  profile PRs; as of 2026-09-22 nothing is released (glue-core v1.27.0,
  glue-qt v0.4.2). Replace development-only feature/version gates with actual
  release floors when those versions exist; never assume any version
  greater than 1.27.0 necessarily contains a particular fix.

### APE-14 and profile follow-ups

- [ ] WP1 must add the downstream real-IRIS autolink regression, including
  raster-to-raster and raster-to-map high-level WCS coherence. Preserve the
  permanent world-coordinate `link_hpc` path alongside pixel WCS links.
- [ ] Keep the low-level-coordinate `clone(link)`/session limitation
  explicit: core's generic WCS saver does not serialize every low-level
  wrapper. WP3 covers the scoped IRIS representation, not a generic fix.
- [ ] Keep numeric/unit-overridden profiles distinct from WCSAxes mode:
  WCSAxes uses pixel x positions and pixel ROI/limits when display units
  equal native units; a unit override uses the numeric world-coordinate
  path. Preserve slice translation and `x_limits_pixel` session state.
- [ ] Reassess the independent `profile_tools.py` nearest-index/display-unit
  correction if a maintainer wants it split out of Qt #70. It is an optional
  PR-boundary decision, not an instruction to rewrite the branch now.
- [ ] Track the reference-slice out-of-range case: the prior review notes
  that an `IndexError` hides the profile artist without an explanation.
  Reproduce it against the intended base before adding another fix.
- [ ] Carry WP5's refreshed numeric/WCSAxes marker tests into production,
  including changed slices, descending wavelength grids and session restore.
  The prototype now passes these on core #2601 + Qt #70. Core slice
  support is not cross-viewer synchronization.

### macOS acceptance and deferred follow-ups

- [ ] Manually verify the application menu title, About/Hide/Quit labels,
  Cmd-Tab and Dock name. Automated bundle-name checks are not a substitute
  for this native UI pass.
- [ ] Check preferences, link editor, importers and other fixed-geometry
  dialogs for clipping at native font sizes, on PyQt6/Retina and supported
  PyQt5. Keep the slice label's 0.75x scale unless the manual pass shows it
  is unreadable. Verify Linux/Windows CI after the font changes as well.
- [ ] Before visual comparison, inspect the saved font override: an old
  9-point setting can mask the new default. Use isolated test configuration;
  do not silently edit the user's `~/.glue/settings.cfg` or QSettings.
- [ ] After the release, check conda-forge's Cocoa dependency and request
  `pyobjc-framework-cocoa` on macOS if still absent; do not open that issue
  merely as a side effect of this plan.
- [ ] Deferred, separate requests/PRs: native Preferences/About menu roles;
  `QFileOpenEvent`; Dock completion feedback; system dark-mode integration;
  trackpad pinch zoom. A notarized `.app` bundle and file associations are
  a separate distribution project, not part of #68.

## Capability boundary

The implemented browser/loader, on `main` since #44 merged on 2026-09-22,
is an `iris_xfiles`-inspired local observation browser and Glue adapter,
not yet an IRIS-first CRISPEX replacement. Here, “implemented” means present
on solar `main`; upstream PR and prototype capabilities are labelled
separately. Merged code is not necessarily released code.

- Discovery groups local files by OBSID/start time, displays metadata,
  selects raster windows/SJI channels/aligned AIA cutouts, recognizes pooch
  prefixes, and extracts supported archives transactionally.
- File interpretation belongs to `irispy.io.read_files`. Unstacked datasets
  retain detector arrays, masks, metadata, units, WCS and exact exposure
  times. The optional 4D stack is a floating memmap with masked pixels stored
  as NaN (`np.result_type(first_scan.dtype, np.float32)`, float32 for the
  tested IRIS arrays, not a universal float32 cast). It uses scan 0's
  nominal spatial WCS without resampling. Load scans
  separately for their distinct absolute pointings.
- The checked installed-core baseline is glue-core 1.27.0.
  It skips IRIS low-level WCS autolinking. On `main`
  (2026-09-22) the loader labels SJI axes `Longitude`/`Latitude`/`Time
  (UTC)` (gWCS names pass through) and raster axes `Wavelength`/
  `Helioprojective Latitude`/`Helioprojective Longitude` (names filled from
  physical type), shows helioprojective values in arcsec but wavelength in
  metres, and attaches a datetime64 `Time` component to every SJI, raster
  and stack dataset. Common names, Angstrom display and high-level object
  coherence remain WP1 work.
- Production IRIS sessions remain unsupported: saving can fail before any
  file is written. The core metadata/style PR alone does not serialize
  `_GlueWCS` or FITS `-TAB` tables. Prototype round trips do not change this.

| Capability | Existing coverage / limitation | Remaining home |
| --- | --- | --- |
| Local search and grouping | Browser exists; no text filter or cooperative cancel | WP8 |
| Level-2 raster/SJI reading | irispy adapter implemented | Regression maintenance |
| Observation metadata | Basic rows and Glue metadata; no OBS XML viewer | `ObsID` enrichment deferred |
| SJI inspection | Image sliders and playback; alpha/mix; frame-time and cursor readouts (#52); transparent NaN (#53) | WP4 slit overlay, WP5 blink |
| Detector mosaic | Generic window slicing; no full-detector reader/layout | Unscheduled |
| Coordinated raster browser | Separate viewers/manual links, not a coordinated quicklook | WP1/WP4 |
| Multi-scan navigation | Separate datasets or scan-0-WCS 4D stack | Per-scan stack inverse WCS deferred |
| Spectrogram / spectroheliogram / sit-and-stare | Default raster view is wavelength × slit (spectrogram); step × slit at selected wavelength (spectroheliogram/raster map) is available by changing axes; wavelength × step/time needs a whisker preset | WP4 layout and time semantics |
| Per-pixel spectrum | Released baseline collapses other axes; one-pixel subset works | Core #2596, Qt #70 |
| Intensity/profile moments | Generic Profile Collapse tab exists, without IRIS scientific semantics | WP2 |
| Gaussian fits | Generic single-spectrum fit exists; no per-pixel parameter products | WP6 |
| Velocity and line IDs | Wavelength coordinate only | WP1/WP5 |
| Spatial/temporal coordination | Manual world links are partial; pixel autolink is frame-0 geometry; datetime64 `Time` exists on every IRIS dataset (#52) but nothing links it yet | Core #2595, WP1/WP4 |
| GOES / SDO context | No GOES action; local aligned AIA cutouts load | WP7 |
| Sessions | Unsupported for IRIS datasets | WP3 |
| Movie / sequence export | Only current-frame export exists | Unscheduled |
| Pipeline log files | No logs in the inspected public Level-2/test data | Dropped absent a mirror-user need |
| Level-3 FITS writing / EIS | Outside the IRIS reader/viewer boundary | Permanent non-goals |

## IRIS-first CRISPEX target

CRISPEX is the reference for the **browsing workflow**, while `iris_xfiles`
is the reference for local observation discovery. The previous SolarSoft
audit primarily compared the latter's quicklook family; finishing that
audit's checklist alone would not establish CRISPEX equivalence.

The author's [CRISPEX repository](https://github.com/grviss/crispex) describes
its broader multi-instrument scope. The
[IRIS-9 CRISPEX exercises](https://tiagopereira.space/iris9/exercises/tutorials_idl.html#crispex)
demonstrate raster/SJI overlays, temporal navigation, selected line windows
and a locked-position spectral time slice. The
[CRISPEX entry point](https://github.com/grviss/crispex/blob/master/crispex.pro)
also documents sessions, reference cubes and slit-jaw inputs.
These are the reference behaviors, not evidence that Glue implements them.
No IDL application was launched during this review.

### First milestone: coordinated IRIS exploration

The following are proposed acceptance criteria derived from that workflow.
They are all still open; WP4's existing prototype implements only a subset.

- [ ] Open a matched Level-2 raster sequence, its selected spectral windows
  and SJI channels into a useful layout: monochromatic raster map,
  wavelength-versus-slit spectrogram, SJI with slit/selected-position overlay,
  and detailed spectrum. Show each panel's actual exposure time. A mean
  spectrum fallback is useful but does not satisfy selected-pixel browsing.
- [ ] Moving the selected point on the raster map updates the spectrum,
  slit position and corresponding SJI marker. Provide follow/lock behavior;
  locked position survives time stepping. Distinguish a fixed detector
  pixel from a fixed solar coordinate, and do not promise world tracking
  from the scan-0 stack WCS. Reuse existing point subsets/profile navigation.
- [ ] Coordinate scan, raster-step and SJI-frame navigation from an explicit
  master, with nearest-exposure matching, visible time offsets and a defined
  no-match policy. Pair by observation identity including start time,
  not OBSID alone. A repeated observing program can reuse its OBSID.
  Keep wavelengths/slit positions independent of temporal synchronization.
- [ ] Provide a time–wavelength view at the selected location and a light
  curve. For repeated rasters, time runs across scans at a selected step;
  for sit-and-stare, steps sample time. A raster's step axis mixes space
  and acquisition time and must not be presented as a stationary time series.
  Use the retained exposure timestamps, including irregular sampling/gaps.
- [ ] Select line windows with their own wavelength grids and scaling,
  navigate wavelength from the spectrum to the monochromatic map, and blink
  two selected wavelength positions in one cube. WP5's layer blink alone
  does not meet the last criterion. Doppler display needs an explicit,
  scientifically appropriate rest wavelength.
- [ ] Demonstrate this end to end on a sit-and-stare observation and a
  repeated raster with SJI, including mismatched cadence, masked samples,
  later-opened/closed viewers and a reopened session (WP3). Record input
  sizes, interaction latency and memory on a representative larger dataset;
  small fixture passes do not establish interactive performance.

Primary delivery is WP1 + WP4 + the relevant part of WP5, with core
#2596/#2601 and Qt #70 supplying profile capabilities. WP3 adds resumable
sessions. Qt #74/#75 improve readouts; they do not deliver the controller.
WP2/WP6 numerical analysis and WP7 remote context are useful extensions,
not prerequisites for basic CRISPEX-style exploration.

### What the missing features mean at the keyboard

These examples describe the target behavior. They are not claims that a
prototype already provides it. “In progress” below includes open upstream
PRs and local experiments; none of WP1–WP8 has been ported into solar main.

| Missing capability | What you would do and see | What exists; what still needs work |
| --- | --- | --- |
| Coordinated four-panel browser | Open one observation and get an SJI, a spatial raster map at one wavelength, a wavelength-versus-slit spectrogram and a detailed spectrum. Select a bright point in the map; all four indicate the same sample. | The loaders and individual viewers exist. WP4 opens a partial layout. The shared selection, full layout and cross-panel markers are missing. |
| Follow and lock a position | Move over the map and inspect the spectrum under the pointer. Click to lock the point so moving the mouse no longer changes it; advance time while keeping that selection. | Qt #74 reports cursor coordinates/intensity. Core #2596/#2601 and Qt #70 can show an individual sliced spectrum. Neither supplies the point-follow controller. Locking a detector pixel and tracking a solar coordinate are distinct choices; solar tracking also needs time-dependent geometry. |
| Honest time synchronization | Select a raster exposure and see the nearest SJI frame, with both timestamps and their offset. If there is no sufficiently close SJI, show “no matching frame” instead of implying simultaneity. | `Time` components already ship. WP4 experiments with nearest indices and image sliders, now with input checks and observation-start pairing. A master time control, gap tolerance, no-match display and profile/marker synchronization remain missing. |
| Time–wavelength plot and light curve | Lock a location. One panel shows how its entire line profile changes with time; another shows brightness versus time in a selected wavelength band. Click a time in either and return the other panels to that sample. | Image/Profile viewers are reusable. The extraction, links and controls are missing. For repeated rasters, hold the raster step fixed and vary the scan. For sit-and-stare, successive exposures sample time. Ordinary raster steps move across the Sun and cannot be relabelled as a stationary light curve. |
| Wavelength navigation and blink | Click the blue or red side of a spectral line and see the corresponding raster map. Choose two wavelengths and alternate between them while holding location/time/scaling fixed. | Generic profile navigation supplies a starting point. WP5 currently blinks separate data layers, such as two images; it does not alternate two slices of one spectral cube. The connected controls and two-wavelength state are missing. |
| Spectral units and line labels | Read a profile in Angstrom or as velocity relative to a stated line centre; identify nearby transitions with labels that stay aligned after changing units or selected pixel. | WP5 has conversion and marker experiments; refreshed markers handle numeric and WCSAxes plots. Production integration, rest-wavelength controls, scientific conventions and packaged line-list data remain. A velocity axis alone is not a fitted velocity map. |
| Resume an analysis session | Save the observation, selected points, windows, links, units and time selection. Reopen tomorrow, or move the folder with its data, and continue at the same place. | Stock sessions are not sufficient for IRIS WCS/metadata. WP3 now demonstrates real-data and relocated file-reference round trips. Production persistence and saving the future coordination controller remain missing. |
| Reliable moment and fit maps | Choose a line window and obtain maps of integrated intensity, centroid/velocity and width; optionally fit one or more Gaussian components and inspect failure/quality maps. | WP2/WP6 numerical experiments pass selected tests. User actions, masks/uncertainty policy, calibration and physical validation are still needed. Moments summarize the samples; Gaussian fits assume a profile model. These are extensions after basic browsing. |
| GOES/SDO context | Load a flare light curve spanning the observation or an AIA context image with the IRIS footprint, then relate a feature or time interval back to IRIS. | Local AIA cutouts already load. WP7 demonstrates requested remote context using mocked downloads. Production actions, declared dependencies, exact time labels and operational download behavior remain. |
| Drawn-path diagrams and movies | Draw a path along a loop and inspect brightness versus distance and time; export a sequence with the same displayed selections and annotations. | Core path extraction and current-frame export are starting points. Path editing, physical distance/time sampling and sequence/movie export are later, currently unscheduled work. |

For an illustrative cadence mismatch, a raster sample at 12:00:10 and the
nearest SJI at 12:00:13 differ by three seconds; show that difference. If
the next usable SJI is minutes away, the software needs an explicit rule
for whether to show it. This refresh deliberately does not invent that
scientific threshold. Likewise, no universal wavelength or Gaussian model
should be silently chosen for every IRIS line.

The next product milestone is the first five rows together, plus spectral
units/labels and session support. Faster browsing (WP8) can be delivered
independently. Fitting, remote context, path diagrams and movies should not
hold up the first useful coordinated browser.

### Later milestones and explicit omissions

Track drawn-path space–time diagrams/virtual slits and movie/sequence export
as remaining CRISPEX gaps after the first milestone. Core `PathSlicedData`
is a reusable extraction primitive; Qt path editing, solar distance/time
coordinates and sampling rules still need a scoped implementation.
Broader instrument loaders, Stokes workflows and multi-instrument alignment
remain later scope decisions. Pixel-identical IDL widgets, Level-3 FITS
generation and EIS support remain outside this IRIS plan. Direct Level-2
loading can meet the workflow without recreating CRISPEX's input format.

## Decisions and cross-package contracts

- **D1: keep `link_hpc` permanently.** APE-14 pixel links describe frame-0
  geometry, whereas time-aware world links serve a different purpose. The
  archived 4.8-hour sit-and-stare example drifted 42 arcsec; its measured
  reach was 14/187 raster steps for the pixel link versus 186/187 for the
  time-aware path. This is fixture evidence, not a universal performance claim.
- **D2: implement IRIS features in glue-solar through existing registries.**
  Reuse Glue viewers, unit converters, layer actions, tools and serializers;
  delegate numerical work to irispy/Astropy. Unreleased core/Qt features
  are not a blanket prerequisite. Version-gate temporary workarounds and
  remove them only when the required upstream fix is actually available.
- **D3: arcsec for helioprojective axes, Angstrom for wavelength.** Convert
  both the low-level values and high-level object classes/components.
  Constructors can be 3- or 4-tuples and getters can be callable or strings;
  changing only a celestial `unit` keyword is insufficient.
- **D4: moments and fitting are dataset `layer_action`s.** They add products
  and links, not viewers. Viewer-opening context actions use the existing
  menu-plugin/session application path.
- The proposed `link_hpc(data_collection)` returns links; callers use
  `data_collection.add_link(link_hpc(data_collection))`. It is idempotent,
  pairs by physical type and assumes `_GlueWCS` standardizes angular units
  to arcsec; it does not independently verify units or coordinate frames. Do not
  substitute a two-argument helper or link degrees to arcsec with `LinkSame`.
- Keep SJI `Time (Utc)` world coordinates distinct from a broadcast
  datetime64 `Time` component. Match physical types, not display labels.
- Never fake an all-ones `axis_correlation_matrix` to repair time-dependent
  inverses: it breaks WCSAxes readouts. Use the correlated-axis closure
  fix represented by core #2598, with a scoped release gate if needed.
- WP4 uses identity `ComponentLink`s on precomputed nearest-index
  components, not `JoinLink` and not lambda/closure links. Key joins made
  otherwise incompatible spatial ROIs select the whole partner dataset.
  Nearest-index slice sync alone does not make SJI pixel ROIs drive rasters.
- WP6 map coordinates must be
  `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))`: unwrap the source once,
  slice its raw WCS, and rewrap once. WP3's saver can then reach the sliced
  record. A bare outer sliced wrapper is not covered.
- WP3 must not globally replace the `VisualAttributes` serialization
  protocol for ordinary datasets. Use the accepted solar-scoped style
  handling when a workaround is needed; preserve plain-session portability.
- The historical WP5 line-list check round-tripped with stock layer/state
  serializers on synthetic data; it was not rerun in this validation.
  No extra line-list saver is currently justified.
  Full IRIS sessions still require WP3.

## Implementation queue

WP1–WP8 have prototypes, not shipped production implementations. WP9's old
local Markdown corrections were applied; its tracked RST work remains.
The order below is preferred sequencing, not invented hard dependencies.

| Order | Package | Prerequisite / sequencing reason |
| --- | --- | --- |
| Parallel | WP0: upstream integration | Preserve PR boundaries and validate combined behavior; user controls merges |
| Now | WP9: correct tracked documentation | On `main` since #44 merged; also owes the #52/#53 fragments |
| 1 | WP1: coordinate/linking basics | Browser loader; do first to settle names and units |
| 2 | WP4: coordinated exploration | WP1; complete the first-milestone interaction criteria, not just the existing image-slider prototype |
| 3 | WP5: spectral navigation, velocity, line list, blink | WP1; wavelength blink is additional work beyond layer blink |
| 4 | WP3: sessions | Can proceed after WP1 in parallel with WP4/WP5; required for resumable first-milestone sessions |
| Later / independent | WP2: line moments | Browser loader; first numerical-analysis PR; explicit conversions work before WP1 |
| Later / independent | WP6: Gaussian fit maps | Browser loader; WP3 for saved products; no hard WP1/WP2 dependency |
| Later | WP7: GOES/SDO context | WP1 and the timeseries extra; WP3 for saved AIA context |
| Any | WP8: filter and stop scan | Browser loader on `main` (#50 fixtures merged); sequence importer-test edits with WP1 |

### WP1: Coordinate names, units and links

Primary paths: `glue_solar/sources/loaders/iris.py`, `sources/iris.py`,
package setup, and importer/linking tests. The
[WP1 prototype package](IRIS_PLAN_PROTOTYPES/wp1/glue_solar/) is a copy of
the browser package refreshed with current #52/#53 timestamps, readout tools,
NaN layer behavior and fixtures. Its proposed coordinate/link changes remain
prototype-only. Autolink tests now detect wrapped-WCS support by behavior,
and the inverse workaround runs only when its behavior probe fails. Port the
coordinate/link delta onto current `main`; do not copy the package over it.

- [ ] Prefer the canonical helioprojective/wavelength names by physical
  type; retain SJI's distinct time-axis name. Convert wavelength to Angstrom
  and make both high-level object directions coherent, including compound
  stacks, sliced maps, callable getters and constructor pass-through.
- [ ] Add the real, idempotent `link_hpc(dc)` helper, browser invocation and
  a manual menu action for datasets loaded through File → Open. Ignore
  unwrapped sunpy maps in degrees; WP7 wraps its own context maps.
- [ ] Apply a supported-version workaround for the correlated-axis inverse
  only if the installed core lacks #2598. Preserve coordinate readouts and
  avoid changing user settings or the WCS correlation matrix.
- [ ] Verify high-/low-level round trips on real SJI, raster, stack and map
  data; names/units in image/profile viewers; repeated-link idempotency;
  raster ROI propagation; and each exposure's SJI inverse. Keep the missing
  SJI-world-time link limitation explicit for the reverse pixel ROI path.
- [ ] Gate the real autolink tests on the actual capability/release of
  #2595. Test SJI/raster, raster/raster, source/map, map/map and sunpy-map
  pairings without a modal autolink dialog. Retain scalar/array coverage on
  the older supported Astropy stack and update docs/changelog.

### WP2: Line-moment maps

Primary path: proposed `glue_solar/sources/moments.py`. Reference:
[moments module](IRIS_PLAN_PROTOTYPES/chk_wp2/wp2_moments_module.py) and
[tests](IRIS_PLAN_PROTOTYPES/chk_wp2/test_wp2_moments.py).

- [ ] Rewrap a per-scan raster Data as a `SpectrogramCube` and call
  `irispy.utils.moments.calculate_moments`; no loader-held cube handle,
  numerical reimplementation or new dependency. Reject SJI and 4D stacks
  with an actionable message in v1.
- [ ] Provide rest wavelength, blue/red wings, minimum intensity,
  saturation and integrated-mode fields. Blank rest uses irispy's default;
  blank wings use the whole window; one wing alone is an error. Convert
  the integrated threshold to DN Angstrom, not a number compared to DN nm.
- [ ] Add one Data with `intensity`, its mask, `centroid`, `width`,
  `velocity`, `velocity_width` and `Time`; preserve angular WCS. Convert
  nm-based outputs to Angstrom and use `km / s` for velocity products.
  Add exactly two spatial pixel links and do not open a viewer.
- [ ] Compare with irispy on real test rasters using an explicit in-window
  rest wavelength; test invalid input without partial publication, masks,
  units and bidirectional source/map spatial subsets. Reuse WP5's rest
  helper once it exists. Add the user-guide page, API entry and changelog.

### WP3: IRIS session save/restore

Primary paths: `_GlueWCS`, scoped style/Quantity serialization, browser
loading factories and session tests. Reference:
[session prototype](IRIS_PLAN_PROTOTYPES/wp3_impl.py). Importing this
prototype installs WCS/Quantity/style patches; the explicit
`install_browser_factories()` hook additionally routes browser reads through
`load_data`. The refreshed [session acceptance tests](IRIS_PLAN_PROTOTYPES/wp3chk_test_sessions.py)
install those patches and pass six cases, including moving source files and
restoring/re-saving twice. Sessions reference `wp3_impl`, which must stay
importable. These tests do not change production support or prove a full
coordinated quicklook session.

- [ ] Serialize the raw inner WCS: gWCS through ASDF; IRIS FITS `-TAB` with
  its reconstructed WCS-TABLE; compound/sliced WCS recursively, preserving
  mapping, slices and shape. A header-only `-TAB` record is insufficient.
- [ ] Retain Quantity metadata with values/units, without flattening or
  mutating live metadata. Preserve the existing documented omission of
  Time/SkyCoord metadata. Keep plain datasets' style records unchanged;
  do not install a global version-2 `VisualAttributes` saver.
- [ ] Route browser loads through `load_data`/LoadLog so sessions reference
  source files and relative-path sessions relocate with their data. Keep
  derived maps embedded. Preserve the scoped factory/module import paths.
- [ ] Round-trip real SJI, raster, multi-scan stack, sunpy Map and mixed
  collections twice: arrays/masks, units, labels, styles, metadata and full
  integer/fractional-grid WCS transforms. The prototype target is 1e-9
  original-versus-restored coordinate agreement; preserve shape metadata.
- [ ] Test relocating data plus session, small file-referencing sessions
  (prototype SJI/three-scan examples under 100 KB), and WP6 map round trips
  through the corrected wrapper contract. Explain that glue-solar and its
  Qt imports must be available to load these sessions. Add no generic
  `-TAB` framework or unnecessary dependencies.
- [ ] Only after production tests pass, replace the user-facing unsupported
  session warning. Core #2597 is useful but not sufficient by itself.

### WP4: Quicklook, slit overlay and slice synchronization

Primary paths: browser and loader integration, proposed quicklook helpers
and tests. Reference: [quicklook prototype](IRIS_PLAN_PROTOTYPES/wp4_common.py).
That prototype has no cursor-follow/lock controller, no profile-slice
synchronization and no linked time–wavelength panel. It is a starting point
for the first-milestone criteria, not their completed implementation.

- [ ] Use WP1's actual helper contract. The datetime64 `Time` component
  already ships on `main` (#52) for SJI, rasters and stacks, so drop the
  old duplicate time extraction. The refreshed helper reuses `_frame_times`
  and does not add a second `Time` component. Slit positions now require an
  explicit `pixel_stride` for known decimation; off-image values stay off
  image. Port the per-frame slit subset, nearest index links, whisker preset,
  sync callbacks and browser quicklook with these contracts.
- [ ] Use a data-only slit subset, not a collection-wide editable subset
  group. Use identity component links, not key joins; expose/remove them
  normally in the Link Editor. Pair time links using OBSID plus observation
  start/identity and overlapping coverage. Define sorted/duplicate/NaT,
  tie and maximum-offset behavior. The refreshed quicklook requires OBSID
  and start time; nearest matching rejects empty, unsorted or NaT references.
  It still clamps outside coverage and has no maximum-offset/no-match
  policy. Direct `link_time` callers remain responsible for matching inputs.
- [ ] Open SJI, raster-map and wavelength Profile viewers for a matched
  selection. Use mean profiles on the released baseline, and gate slice
  profiles on the core feature. Whisker is wavelength versus step/time
  with a slit slider. The default viewer is a spectrogram; the raster-map
  preset selects step × slit at one wavelength using the same Image Viewer.
- [ ] Sync only viewers/slice axes representing the matched frame/exposure,
  including newly opened viewers and the defined 4D stack mapping. Do not
  move wavelength or slit sliders inadvertently. Add explicit selected-point
  and ProfileViewer slice coordination for CRISPEX browsing; this was
  previously deferred, but belongs to the agreed first milestone. Reuse the
  existing profile Navigate tool for profile-to-image wavelength selection.
- [ ] Add the selected-location time–wavelength panel and light curve with
  the scan/step semantics above. Reuse Image/Profile viewers; choose a fixed
  pixel or solar-position policy explicitly. Remove callbacks when viewers
  close. The refreshed image helper now disconnects callbacks and drops
  closed states, but still wraps `app.new_data_viewer`; this is not a
  persistent application-wide controller.
- [ ] Test real-fixture slit motion, nearest-exposure mapping in both
  directions, late viewers, Link Editor visibility and serializable links.
  Unsupported spatial ROIs must stay incompatible, never select the whole
  partner. Raster-map ROIs should still reach SJI. Document the remaining
  time-dependent ROI and scan-0 stack-WCS limits.

### WP5: Velocity units, line lists and blink

Primary paths: proposed `glue_solar/viewers.py`, rest-wavelength helper,
packaged `iris_lines.csv`, setup and tests. References:
[units](IRIS_PLAN_PROTOTYPES/wp5_units.py),
[line-list module](IRIS_PLAN_PROTOTYPES/wp5_linelist_mod.py),
[blink](IRIS_PLAN_PROTOTYPES/wp5_blink.py), and
[line-list session check](IRIS_PLAN_PROTOTYPES/wp5_ll_session.py).
The refreshed artist handles WCSAxes by inverting the selected spectral
trace; markers outside the trace or on non-monotonic traces are omitted.
Numeric units, changed slices and synthetic sessions have focused checks.
Blink is now importable without launching its demo, and close restores
visibility. Both remain prototype implementations.

- [ ] Use the existing default unit-converter registration without
  persisting a new converter name. Use optical Doppler conversion consistent
  with moments; offer Angstrom/nm/velocity only when meaningful. Rest
  wavelength priority is an explicit Angstrom override, then irispy metadata,
  then unavailable. Copy a stack's rest value from the selected window in
  scan 0's `SGMeta`, never blindly from `TWAVE1` in a multi-window dict.
- [ ] Add the 11-line IRIS wavelength/name list and the existing registry
  layer/state pattern; use its actual Qt artist-class style keys. Positions
  must follow units, visibility, color and linewidth, disappear for a
  non-spectral x-axis, and convert to pixel positions in WCSAxes mode.
- [ ] Implement layer blink with the existing checkable tool and timer. Cycle
  enabled/visible data layers only, restore visibility on deactivation,
  and stop on close. Mix/alpha already exists. Make setup idempotent.
  Separately add two-wavelength blink for one cube, preserving its spatial
  point/time/scaling and restoring the wavelength when disabled; the
  archived layer-visibility prototype does not do this.
- [ ] Test Doppler ROI inversion, missing rest wavelengths, stack/window
  selection, user overrides, no settings writes, line removal, synthetic
  session restore and WCSAxes alignment. Check the line-list asset is in
  the wheel. Full IRIS sessions depend on WP3; add no line-list saver.
- [ ] Keep image-axis velocity and generic annotation frameworks out of
  this package. Update the user guide and changelog when the feature lands.

### WP6: Gaussian fit maps

Primary path: proposed `glue_solar/sources/fitting.py`. References:
[fitting module](IRIS_PLAN_PROTOTYPES/wp6_fitting.py),
[brief variant](IRIS_PLAN_PROTOTYPES/wp6_fitting_brief.py),
[tests](IRIS_PLAN_PROTOTYPES/wp6_test_fitting.py), and the
[integrated WP3 round trip](IRIS_PLAN_PROTOTYPES/review_20260905/test_plan_integration.py).

- [ ] Reuse `parallel_fit_dask` for single/double Gaussian plus background;
  keep numerical arrays plain and attach unit strings to output components.
  Wavelength/centroid/width are Angstrom. Seed from the mean spectrum's
  maximum or two highest interior local maxima; an optional in-window
  center overrides that. Do not prefill from nominal TWAVE or add the
  rejected mean-spectrum prefit.
- [ ] Run process scheduling inside the existing Qt Worker; tests use the
  deterministic single-threaded scheduler. Keep the GUI responsive and
  products added on the main thread. Show progress for the worker lifetime;
  do not advertise cancellation that the fitting API cannot provide.
- [ ] Put parameter maps in one new dataset, with one pixel link per
  non-spectral axis and source `Time`; put the residual cube on the source
  at its original shape. Support the tested 3D/4D shape contract. Use the
  corrected `_GlueWCS(SlicedLowLevelWCS(raw_wcs, slices))` form.
- [ ] Recover synthetic amplitudes/widths to rtol 1e-4 and centroids to
  1e-6; test real irispy raster shapes/units, source/map subset propagation,
  source residuals, worker completion and non-spectrogram rejection.
  Real-fixture finite/NaN behavior is a regression check, not physical
  fit certification; the bundled windows omit line cores.
- [ ] Keep masks/weights, fit-window controls, velocity/net-flux derived
  maps and diagnostics files out of v1. No dask/fitting extra is needed.
  This is a restricted, unweighted fitting prototype: it clips negative
  values and replaces NaNs with zero, and does not consume the source mask.
  Document that preprocessing and do not call its results calibrated science
  products. Revisit invalid-sample handling before making that claim.
  Historical timings are machine-specific observations, not CI thresholds.
  Add action registration, docs/API entries and changelog; require WP3
  before claiming fitted IRIS products save in sessions.

### WP7: GOES and SDO context

Primary path: proposed `glue_solar/sources/context.py`, setup/dependencies,
context tests and user documentation. References:
[context prototype](IRIS_PLAN_PROTOTYPES/wp7chk/context_chk.py) and
[prototype tests](IRIS_PLAN_PROTOTYPES/wp7chk/test_context.py).
The refreshed tests import `context_chk`, which reuses WP1's `link_hpc`
instead of a copied helper. Ten mocked-network checks pass with the missing
`cdflib`/`h5netcdf` dependencies installed in a temporary directory. The
project environment and dependencies were not changed. Actual downloads
and exact datetime plotting against core #2599 remain separate gates.

- [ ] Fetch only after the user confirms the observation picker; cancellation
  does no network work. Errors leave the collection unchanged with a clear
  message. Tests mock network responses.
- [ ] Declare the full `sunpy[map,net,timeseries]` extra when adding GOES,
  and verify warning-free imports with supported dependencies. Select one
  GOES satellite, trim to the observation interval, retain datetime and
  W/m2 units, and open a log-flux Scatter viewer rather than Profile.
  Link time ranges to raster/stack `Time`.
- [ ] Verify datetime labels against the installed core. #2599 now exists;
  do not blindly apply the archived global epoch workaround on a core that
  already has the fix. A necessary older-core workaround must be gated and
  preserve other plotting consumers.
- [ ] Retrieve nearest-start AIA 171 through VSO; crop to first-exposure
  footprint plus the planned 100-arcsec margin. Use the solar-surface
  propagation context around the relevant transform, not as a bare call.
  Wrap the cutout WCS in `_GlueWCS` before invoking WP1 links.
- [ ] Use a pixel `PolygonalROI` FOV subset, not `RegionData` (separate core
  [issue 2600](https://github.com/glue-viz/glue/issues/2600)). Test SJI,
  raster and stack footprints, invalid WCS errors, exact date labels and
  subset propagation without network. No JSOC credentials, aiapy,
  cross-correlation framework or extra outline dataset is required.
- [ ] Preserve the first-exposure FOV/time limitation; WP3 is needed for
  saved AIA context. Long-download threading, other bands/HMI and HEK
  overlays are deferred; document any synchronous wait honestly.

### WP8: Browser filter and cooperative stop

Primary paths: `glue_solar/sources/loaders/scan.py`, `iris.py`,
`iris_loader.ui`, and importer/scan tests. References:
[scanner](IRIS_PLAN_PROTOTYPES/wp8_scan.py),
[dialog prototype](IRIS_PLAN_PROTOTYPES/wp8_proto.py), and the
[restored UI](IRIS_PLAN_PROTOTYPES/wp8_loader.ui).
The primary dialog now repairs an invalid progress value after leaving
busy mode, making stop/failure text visible while preserving completed
archive extraction at 100. Ten checks pass, including the text regression.
The older `ProtoImporterFixed` remains historical comparison evidence.

- [ ] Add one case-insensitive text filter for STARTOBS/OBSID/description.
  ISO date substrings cover day/month/year filtering; this is not pre-scan
  time-range search. Hidden ticked observations still load, and the filter
  survives rescans. Keep UI object names `filter`, `stop_scan`, `progress`.
- [ ] Run header scanning through the existing Worker with a cooperative
  stop predicate. Keep grouped/sorted partial results. Populate on the GUI
  thread and use scan IDs to ignore stale queued results.
- [ ] Stop and await the previous worker on rescan, directory change,
  accept/reject/close; preserve archive-extraction messages. Initialize the
  busy bar with a valid value so stopped/failed text is actually visible.
- [ ] Update existing synchronous importer tests with deterministic waits;
  gate stop/rescan tests on counted header reads rather than sleep timing.
  Test cancellation, late results, GUI-thread population, filter semantics,
  extraction/rescan text and worker lifetime. Run the lifecycle suite
  repeatedly against the #50 fixtures now on `main`.
- [ ] Document that the initial sorted directory walk is not interruptible
  in this prototype; cooperative stop is checked during file processing.
  No new dependency, persisted filter setting, log viewer, date widgets or
  extra filename-preset system is required.

### WP9: Tracked user/developer documentation

This consolidation completed the local planning-document cleanup, not the
remaining tracked RST edits. #44 has merged, so those edits are a separate
requested PR against `main`. Checked 2026-09-22: every item below is still
open (the `AMI` alt-text, the `_SDO`-folder sentence, the restore-only
session warning and the missing float32/NaN text are all still there).

- [ ] `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: explain
  that aligned `aia_l2_*.fits` cutouts do not require an `_SDO` directory;
  clarify floating/NaN stack storage (float32 for the tested IRIS inputs,
  dtype is selected from the first scan via `np.result_type`); use the distinct SJI/raster
  coordinate labels (SJI `Longitude`/`Latitude`/`Time (UTC)`, raster
  `Wavelength`/`Helioprojective Latitude`/`Helioprojective Longitude`)
  until WP1 normalizes them; state the directional
  linking limit and that saving can fail, not merely restoration.
- [ ] `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst`:
  describe the same stack representation; distinguish released collapse
  profiles, a one-pixel subset, and the unreleased slice feature.
- [ ] `docs/user_guide/loading-aia-and-hmi.rst`: correct the image alt-text
  typo “AMI” to “AIA”.
- [ ] `docs/dev_guide/loader-customization.rst`: document the floating memmap,
  NaN/mask reconstruction, exact acquisition times and scan-0 nominal WCS.
- [ ] Add the towncrier fragments the merged PRs skipped: `52.feature.rst`
  (`Time` component, frame-time and cursor readouts) and `53.bugfix.rst`
  (transparent NaN pixels), and mention the two Image Viewer tools and the
  `Time` component in the IRIS user guide. `CHANGELOG.rst` is empty and
  `docs/whatsnew/changelog.rst` only renders fragments.
- [ ] Check Sphinx with warnings as errors and relevant existing tests.
  Locate targets by text, not archived line numbers. Do not add a redundant
  ndcube changelog fragment or edit README just to mirror this plan.
- [ ] Each later feature updates only its implemented capability/docs;
  do not claim planned sessions, quicklook or science features already ship.

## Deferred work and non-goals

Retain these decisions rather than silently losing them when old TODOs move:

- Permanent non-goals: Level-3 FITS product generation and EIS support.
- No full IDL widget/UI clone, OBS XML resolver, detector mosaic reader,
  PostScript workflow or generic annotation/plugin framework.
- Per-scan absolute WCS inside the 4D stack is deferred, not impossible:
  the demonstrated forward gWCS table model works; its inverse for links
  and subsets is the remaining problem. Load scans separately meanwhile.
- Movie/sequence export and path-based space–time extraction remain later
  CRISPEX gaps, without an implementation schedule. Decoded
  `irispy.obsid.ObsID` enrichment is unscheduled. Alpha/mix, per-viewer
  playback and the default spectrogram layout already exist; coordinate
  them rather than reimplementing their rendering.
- Moments follow-ups: red-blue asymmetry as a separate action with explicit
  rest wavelength and quality flags; 4D moments; prefilled wings from a
  profile range. Keep expensive RBA work responsive if implemented.
  Density diagnostics need two intensity maps plus fiasco/CHIANTI and are
  out of this plan, not an extra checkbox on the moments dialog.
- Pipeline logs are absent from the inspected public Level-2/sample data;
  reconsider only for a concrete pipeline-mirror request. Browser date
  widgets, pre-scan time-range search and persistent filter text are deferred.
- Native macOS extensions are listed under WP0, separately from #68's
  existing application identity/font/icon work.

## 2020 wiki roadmap, reconciled 2026-09-22

The wiki holds two pages from the 2020 GSoC period: "Short Term Roadmap"
(2020-03-27) and "Current Workplan" (2020-09-11, last edit by Kris Stern).
Their items map onto the current state as follows.

| 2020 item | 2026-09-22 status | Home |
| --- | --- | --- |
| HMI/AIA map docs (#17), IRIS raster+SJI docs (#18), loader-customization dev docs (#33) | Merged in 2020; the IRIS and dev pages are being corrected | WP9 |
| Auto selection of the solar colormap | Done: sunpy colormaps registered in `setup()`, `preferred_cmap` taken from the loaded map (#45), `irissji*`/`sdoaia*` for IRIS images | Maintained |
| N-D WCS autolinking (glue #2161, merged 2020) | Celestial autolink exists; IRIS low-level (APE-14) WCS needs core #2595; time axes are still not autolinked | Core #2595, WP1, WP4 |
| 1D profile sliders instead of collapsing (glue #2167, closed) | Reworked as core #2596/#2601 and Qt #70 | WP0 |
| Spectrum/value under the mouse (3D) | Scalar readout exists (#52 / Qt #74); point subsets can select profiles, but cursor-follow/lock and synchronized profile slices remain | WP4, core #2596/#2601, Qt #70 |
| Three viewers of one 4D dataset; wave/time plot under the cursor | The stacked-raster profile guide covers the viewers; the coordinated quicklook is WP4 | WP4, WP9 |
| Derived datasets from pixel selections with WCS and links; icon/UX | The 2020 `glue_solar/pixel_extraction` tool (an `IndexedData` extractor with its own user-guide screenshots) was removed by the 2024-09-19 retemplate (`0435fd4`) and is recoverable from history; core offers `image:point_selection` and `IndexedData` without a Qt extraction UI | Unscheduled |
| Derived dataset under a drawn path (slit extraction) | Core 1.26 ships `PathSlicedData` (glue #2579) with a front-end-agnostic path mode; glue-qt registers no tool for it yet | Unscheduled candidate |
| WCS info for derived datasets: raster + SJI time linking | Datetime64 `Time` is on every IRIS dataset (#52); nearest-exposure links are WP4 | WP4 |
| Dask support | Core has `DaskComponent` and random-view statistics; IRIS reads eagerly (`memmap=False`), stacks use floating memmaps; a representative interactive workload still needs measurement | First-milestone performance evidence; implementation deferred |
| Image/movie export with and without axes | Only single-frame export (`mpl:save`) exists | Unscheduled |
| Loaders: NDData/NDCube (glue #2164, closed), SST, IRIS, EIS, DKIST | IRIS and sunpy Map done; the empty SST module was removed (#46); EIS is a permanent non-goal; generic NDCube/NDData and DKIST loaders are unplanned | Unscheduled / non-goal |
| Stokes profiles | IRIS has no polarimetry; needs an SST/DKIST loader first | Non-goal for this plan |
| Pre-computed statistics (glue issue #2133, open) | Upstream core feature; nothing in glue-solar depends on it | Out of scope |
| glue-solar splash screen (glue #2139, closed) | Dropped | Dropped |

- [ ] Reconcile the public wiki digest with this CRISPEX-focused revision
  in a separate requested publication. The local clone is at `63f0400`
  with `master` equal to its `origin/master` tracking ref (0 ahead/behind).
  The previous "not yet pushed" instruction is not supported by that state;
  the remote wiki was not refreshed here. No wiki publication was performed.
- [ ] Decide whether any "unscheduled candidate" above (path slicing,
  generic NDCube loader, movie export) joins the implementation queue.

## Validation and working locations

The primary checkouts are `~/Git/glue`, `~/Git/glue-qt`, and
`~/Git/glue-solar`. The temporary `~/Git/glue-fixes/` worktrees were removed
after their commits were pushed. Historical logs still name those old paths.
On 2026-09-22 the checkouts were on core `fix-session-style-meta`, Qt
`status-bar-cursor-readout` and solar `main`.
For future source checks, first inspect the checkout/index and select the
intended branch safely; the runner tests the branch actually checked out,
not an inferred branch from a directory name.

The [test runner](IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py) accepts
colon-separated source roots and pytest arguments, prints import locations,
uses offscreen Qt/Agg, and isolates Glue configuration/cache writes. For example,
from `~/Git/glue-solar`:

```sh
# Tests the branch currently checked out in ../glue.
.venv/bin/python -B IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py \
  /Users/nabil/Git/glue \
  /Users/nabil/Git/glue/glue/viewers/profile

.venv/bin/python -B IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py \
  /Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp1:/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES \
  IRIS_PLAN_PROTOTYPES/review_20260905/test_plan_integration.py
```

- Main validation used Python 3.14.7, Astropy 8.0.1, NumPy 2.5.2,
  Matplotlib 3.11.1, pytest 9.1.1, irispy-lmsal 0.8.1 and ndcube 2.4.1.
  The older APE-14 check used Python 3.12 with Astropy 6.1.7/NumPy 2.2.6.
  These are recorded environments, not new dependency requirements.
- The solar `.venv` (used for the validation above)
  has released glue-core 1.27.0 and irispy 0.8.1 plus glue-qt editable from
  `~/Git/glue-qt`. The earlier snapshot recorded a second micromamba
  environment at `~/mamba/envs/glue-solar`, importing
  glue, glue-qt and irispy editable from the three checkouts; its irispy
  checkout was on `main` at 0.7.1.dev21 on 2026-09-22, below glue-solar's
  `>=0.8.1` floor. That environment was not refreshed during the evening
  validation; inspect its current imports before using it.
- Use repo-pinned checks when validating implementation: recorded Ruff pins
  are core 0.15.20, Qt 0.14.14 and solar 0.16.1. Recheck the configuration
  before installing tools; do not weaken a baseline for newer lint rules.
- Keep actual import paths and installed package metadata distinct when
  testing a source worktree. Do not spoof a version in production to bypass
  an unreleased feature gate. Mock modal dialogs in headless tests.
- Use real irispy fixtures; select the `sns/` copy when duplicate raster
  names exist, and support both old and `_test.fits` names. Bundled windows
  can omit TWAVE or the physical line core; choose explicit in-window
  wavelengths for numerical checks, and do not call them physical validation.
- The review/fix logs that were under `/private/tmp/glue-review-20260904-0oadCw/`
  (`publish-wcsaxes.log`, `publish-qt-mac.log`, `publish-qt-profile.log`)
  no longer exist as of 2026-09-22; their result counts survive only in
  the 2026-09-05 validation table.

## Archive

All six pre-consolidation bodies are retained verbatim below a short archive
banner in [IRIS_PLAN_PROTOTYPES/archive/2026-09-05/](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/).
The obsolete standalone files were moved, not discarded. The prior plan's
inline implementations, detailed test recipes, scientific source links and
historical findings remain available; this central file owns current tasks
and resolves superseded decisions. Archived line numbers, relative paths,
PR status claims and commands retain their original context and may be stale.

| Archived document | Original location / retained evidence |
| --- | --- |
| [Prior complete plan](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/IRIS_GLUE_GAP_PLAN.md) | `glue-solar/IRIS_GLUE_GAP_PLAN.md`; full WP0–WP9 briefs and historical execution logs |
| [Plan revision 2026-09-05](IRIS_PLAN_PROTOTYPES/archive/2026-09-22/IRIS_GLUE_GAP_PLAN.md) | `glue-solar/IRIS_GLUE_GAP_PLAN.md` as of 2026-09-05; full 40-character PR heads and the pre-merge branch/CI snapshot |
| [Branch review](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/IRIS_BRANCH_REVIEW.md) | `glue-solar/IRIS_BRANCH_REVIEW.md`; reproductions, fix/commit records and validation limits |
| [Capability audit](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/IRIS_IDL_GLUE_CAPABILITY_AUDIT.md) | `glue-solar/IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`; detailed SolarSoft comparison, launch hierarchy and inspected source links |
| [APE-14 TODO](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/APE14_AUTOLINK_TODO.md) | `glue/APE14_AUTOLINK_TODO.md`; original design, tests and downstream caveats |
| [Profile TODO](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/PROFILE_WCS_RESTART_TODO.md) | `glue/PROFILE_WCS_RESTART_TODO.md`; split rationale, WCSAxes contract and acceptance |
| [macOS TODO](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/MACOS_INTEGRATION_TODO.md) | `glue-qt/MACOS_INTEGRATION_TODO.md`; identity/font/icon evidence, manual gates and deferred work |

The rest of [IRIS_PLAN_PROTOTYPES/](IRIS_PLAN_PROTOTYPES/) remains in place.
The initial consolidation preserved prototype sources. Selected files were
subsequently refreshed with user authorization on 2026-09-23; their originals
and the pre-refresh index/plan are in
[the refresh archive](IRIS_PLAN_PROTOTYPES/archive/2026-09-23-prototype-refresh/).
They are supporting experiments, not separately maintained work plans or
proof that the corresponding production feature has landed.
