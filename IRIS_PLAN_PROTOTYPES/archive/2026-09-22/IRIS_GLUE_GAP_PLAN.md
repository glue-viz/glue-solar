# IRIS and Glue cross-repository work plan

Updated 2026-09-05 (America/Los_Angeles). This is the single maintained work
plan for `~/Git/glue`, `~/Git/glue-qt`, and `~/Git/glue-solar`.

It replaces the separate branch review, capability audit, APE-14 TODO,
profile-WCS TODO, and macOS TODO. Their full contents, including the previous
6,742-line plan, are preserved in the [archive](#archive). Do not maintain
parallel status lists or execute archived branch-publication instructions.
READMEs, changelogs, user/developer documentation and runnable prototypes
retain their own purposes and locations.

This plan and the prototype/archive directory remain local and untracked.
No documentation commit, push, PR merge, review request or implementation
of a future work package is authorized by this consolidation.

## How to use this plan

1. Check the dated branch/CI snapshot below before starting work. Refresh
   GitHub and the relevant checkout when acting on a PR or release gate.
2. Pick an unchecked task from WP0, WP9 or the implementation queue. Read
   its requirements and the linked prototype/evidence; trace current code
   before adapting historical snippets. This file takes precedence.
3. Preserve unrelated changes and the index. Stage named files only when
   committing is requested; never include the prototype archive incidentally.
4. Record completion here with the actual branch/commit, test command and
   result, validation limits, and remaining work. A prototype pass is not a
   production implementation; a pushed PR is not a merged release.

## Current branches and PRs

GitHub snapshot: 2026-09-06 00:35–00:37 UTC (2026-09-05 locally).
All eleven PRs below are open. The eight repaired branch heads match the
commits pushed on 2026-09-05; the browser and two unchanged core fixes are
included so the whole cross-repository dependency set is visible.

| Repository | Branch | PR | Review state | Head |
| --- | --- | --- | --- | --- |
| glue | `ape14-wcs-autolink` | [2595](https://github.com/glue-viz/glue/pull/2595) | Draft | `656017b972344a4291934c3a02af73a988728b95` |
| glue | `profile-slice` | [2596](https://github.com/glue-viz/glue/pull/2596) | Draft | `1c19021d593b192af5f6f4c6c8083506dcf5b6ca` |
| glue | `profile-wcsaxes` | [2601](https://github.com/glue-viz/glue/pull/2601) | Draft | `6cc8f20bd1ec62a188254d0e4507ab0e778a0a3b` |
| glue | `fix-session-style-meta` | [2597](https://github.com/glue-viz/glue/pull/2597) | Draft | `431c943373ad15ecc69d3fc2525dfa1d6ced80bb` |
| glue | `fix-world2pixel-correlated-axes` | [2598](https://github.com/glue-viz/glue/pull/2598) | Draft | `e6c2802010e539cdc1c77e09327b2e461b46a696` |
| glue | `fix-datetime-epoch` | [2599](https://github.com/glue-viz/glue/pull/2599) | Draft | `a46cc24cbdec1d0a4275cd7ab77d8a8ea74888ef` |
| glue-qt | `ci-fixes` | [69](https://github.com/glue-viz/glue-qt/pull/69) | Non-draft | `5cc9e23ee71e647984ed89e3d0ff6db003082ab0` |
| glue-qt | `macos-integration` | [68](https://github.com/glue-viz/glue-qt/pull/68) | Draft | `0b16dd55f1cb9135ab384c4cc97d948ed838bf36` |
| glue-qt | `profile-wcs-pr` | [70](https://github.com/glue-viz/glue-qt/pull/70) | Draft | `f5444473a1c390facd43e90acb21a75f016929fd` |
| glue-solar | `iris-observation-browser` | [44](https://github.com/glue-viz/glue-solar/pull/44) | Non-draft | `d3a2bd3135467262756a6f84b967eb8ad5302216` |
| glue-solar | `loadable-iris-fixtures` | [50](https://github.com/glue-viz/glue-solar/pull/50) | Non-draft | `383dec253931c3c44569113994a3f35c9bf83deb` |

PR #50 targets `iris-observation-browser`, not `main`; every other listed
PR targets `main`. The earlier claim that the fixture branch had no PR was
incorrect. Non-draft does not imply that CI or maintainer review is complete.

Branch dependencies and publication boundaries:

- Core `profile-wcsaxes` contains `profile-slice`; land #2596 before #2601.
  Qt #70 is feature-gated against core profile capabilities. Its current
  branch contains `ci-fixes`; land Qt #69 before #68/#70.
- Solar #50 is a fixture-only child of #44. Merge into its stated parent,
  or explicitly retarget/reconcile it if #44 merges first. Do not duplicate
  the browser implementation in a new PR.
- New commits and ordinary parent merges carried the fixes; no history
  rewrite or force-push was used. Do not rerun the old #68 reset procedure.
- The local legacy `profile-wcs` branches and `macos-integration-v2` alias
  were removed during the cleanup below. Their published history remains
  recoverable. The solar pre-rebase backup is retained for its unique
  history, not as an active delivery branch. Core #2248 is closed; the
  obsolete remote `1dprofile_wcs` was already deleted.
- At the final cleanup check, the core and Qt primary checkouts are on
  `main`, and solar is on `iris-observation-browser`. No main branch tip
  was advanced by cleanup. The review
  found core main `dae530c3` two commits behind upstream `751871df`, with
  drift in `glue/core/state_path_patches.txt`; recheck before a future rebase.

### Remote CI snapshot, not a readiness certificate

- All six core PRs report a failed `ci/circleci: py311-test-visual` check.
  The four newly updated PRs still have queued/running checks; unchanged
  #2597/#2598 each show 25 successful, 1 skipped, and that 1 failed check.
- Qt #69/#68 each show 7 successful and 37 queued checks. Qt #70 shows
  16 successful, 6 running, 18 queued and 6 failed: four `allowed_failures`
  jobs plus `codecov/patch` and `codecov/project`. Those failures have not
  been diagnosed as part of this documentation consolidation.
- Solar #44 shows 16 successful and 5 skipped checks. Solar #50 shows
  1 successful and 3 queued checks; its test matrix may expand later.
- These are time-specific observations, not a promise of eventual green CI.
  No workflow rerun, baseline deployment or tolerance change was requested.

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

The only remaining local-only branch is solar
`backup/iris-observation-browser-pre-rebase` at
`93d05f05c250dfb3f96b419069d046df8090f09a`. Its reflog records a safety copy
made from `iris-observation-browser` before the rewrite. It contains 11
commits not reachable from any refreshed remote ref, including
`docs/make_screenshots.py`, a 196-line generation utility absent from the
current branch and prototype archive. Those 11 old commit identities do
not imply 11 missing production fixes; much of the work was rewritten.
Nevertheless, it is not an exact duplicate and was not discarded.

- [ ] Decide whether the unique screenshot helper and remaining pre-rebase
  history should be retained in an archive or intentionally discarded before
  deleting the solar backup. Do not push it as another feature branch merely
  to make the unpublished-commit count zero.

## Completed work and evidence

- [x] Published the split APE-14, profile, macOS and supporting core fixes.
  PR publication, the #68 rewrite/body/draft update, and closure of #2248
  were already complete before the latest review.
- [x] Fixed slice profiles and exported profiles to use the selected view
  for both intensities and world coordinates, including linked/transposed
  layers, unit overrides, changing slices and subset masks (#2596/#2601).
- [x] Fixed negative fractional datetime round trips by flooring whole
  seconds before adding the fractional remainder (#2599).
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

## WP0: Existing PRs and release gates

Publication is complete. Remaining work is validation and review, not
creating replacement PRs or repeating completed branch operations.

- [ ] Check final CI for each current head, separating required jobs from
  explicitly allowed failures. Investigate Qt #70 coverage failures and
  retain their actual logs before deciding whether code needs correction.
- [ ] Resolve the core visual-reference issue in a controlled environment.
  Previously inspected [build 6860](https://circleci.com/gh/glue-viz/glue/6860)
  and builds 6861/6864 failed only
  `TestWCSRegionDisplay.test_image_wcs_viewer` and
  `test_image_flipped_wcs_viewer`: 7 visual tests passed, 2 image comparisons
  failed, with WCS tick/label placement differences rather than a crash.
  Fresh failed checks still require their own log comparison.
- [ ] Compare against [successful build 6853](https://circleci.com/gh/glue-viz/glue/6853).
  Astropy 8.0.1, Matplotlib 3.11.1, NumPy 2.4.6 and pytest-mpl 0.19.0 matched,
  but other packages, including fonttools and kiwisolver, differed. This
  is correlation, not a proven cause. Do not add speculative pins, loosen
  hashes/tolerances, or deploy to the separate `glue-core-visual-tests`
  repository without an accepted comparison and explicit authorization.
- [ ] User reviews each draft before it is marked ready. Do not request
  reviews on solar #44 automatically or merge any PR without direction.
- [ ] Track the releases containing core #2595/#2597/#2598/#2599 and the
  profile PRs. Replace development-only feature/version gates with actual
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
- [ ] WP5 line-list positions need explicit testing in both numeric and
  WCSAxes modes; archived numeric-axis tests do not establish pixel-mode
  alignment. Core slice support is not cross-viewer synchronization.

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

The implemented browser/loader branch is an `iris_xfiles`-inspired local
observation browser and Glue adapter, not a replacement for the SolarSoft
quicklook suite. Here, “implemented” means present on the listed branch,
not necessarily merged upstream or released.

- Discovery groups local files by OBSID/start time, displays metadata,
  selects raster windows/SJI channels/aligned AIA cutouts, recognizes pooch
  prefixes, and extracts supported archives transactionally.
- File interpretation belongs to `irispy.io.read_files`. Unstacked datasets
  retain detector arrays, masks, metadata, units, WCS and exact exposure
  times. The optional 4D stack is a float32 memmap with masked pixels stored
  as NaN; it uses scan 0's nominal spatial WCS without resampling. Load scans
  separately for their distinct absolute pointings.
- The checked released-core baseline was glue-core 1.27.0. It skips IRIS
  low-level WCS autolinking; the current loader still presents wavelength
  in metres and has different SJI/raster axis labels. Arcsec high-level
  object coherence, common names and Angstrom display are WP1 work.
- Production IRIS sessions remain unsupported: saving can fail before any
  file is written. The core metadata/style PR alone does not serialize
  `_GlueWCS` or FITS `-TAB` tables. Prototype round trips do not change this.

| Capability | Existing coverage / limitation | Remaining home |
| --- | --- | --- |
| Local search and grouping | Browser exists; no text filter or cooperative cancel | WP8 |
| Level-2 raster/SJI reading | irispy adapter implemented | Regression maintenance |
| Observation metadata | Basic rows and Glue metadata; no OBS XML viewer | `ObsID` enrichment deferred |
| SJI inspection | Image sliders and playback; alpha/mix already exist | WP4 slit overlay, WP5 blink |
| Detector mosaic | Generic window slicing; no full-detector reader/layout | Unscheduled |
| Coordinated raster browser | Separate viewers/manual links, not a coordinated quicklook | WP1/WP4 |
| Multi-scan navigation | Separate datasets or scan-0-WCS 4D stack | Per-scan stack inverse WCS deferred |
| Sit-and-stare / spectroheliogram | Loadable now; spectroheliogram is the default image layout | WP4 whisker/layout documentation |
| Per-pixel spectrum | Released baseline collapses other axes; one-pixel subset works | Core #2596, Qt #70 |
| Intensity/profile moments | Generic Profile Collapse tab exists, without IRIS scientific semantics | WP2 |
| Gaussian fits | Generic single-spectrum fit exists; no per-pixel parameter products | WP6 |
| Velocity and line IDs | Wavelength coordinate only | WP1/WP5 |
| Spatial/temporal coordination | Manual world links are partial; pixel autolink is frame-0 geometry | Core #2595, WP1/WP4 |
| GOES / SDO context | No GOES action; local aligned AIA cutouts load | WP7 |
| Sessions | Unsupported for IRIS datasets | WP3 |
| Movie / sequence export | Only current-frame export exists | Unscheduled |
| Pipeline log files | No logs in the inspected public Level-2/test data | Dropped absent a mirror-user need |
| Level-3 FITS writing / EIS | Outside the IRIS reader/viewer boundary | Permanent non-goals |

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
- `link_hpc(data_collection)` returns links; callers use
  `data_collection.add_link(link_hpc(data_collection))`. It is idempotent,
  pairs by physical type and accepts same-unit `_GlueWCS` datasets. Do not
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
- The WP5 line-list layer already round-trips with stock layer/state
  serializers on synthetic data. No extra line-list saver is needed.
  Full IRIS sessions still require WP3.

## Implementation queue

WP1–WP8 have prototypes, not shipped production implementations. WP9's old
local Markdown corrections were applied; its tracked RST work remains.
The order below is preferred sequencing, not invented hard dependencies.

| Order | Package | Prerequisite / sequencing reason |
| --- | --- | --- |
| Now | WP0: finish CI/review | Published PRs above; user controls merges |
| Now | WP9: correct tracked documentation | Browser branch; independent of science features |
| 1 | WP1: coordinate/linking basics | Browser loader; do first to settle names and units |
| 2 | WP2: line moments | Browser loader; first science PR; explicit conversions also work before WP1 |
| 3 | WP3: sessions | Prefer after WP1 to avoid overlapping `_GlueWCS` edits |
| 4 | WP4: quicklook and slice sync | WP1; WP3 only for session guarantees |
| 5 | WP5: velocity, line list, blink | Prefer WP1; WP3 for full IRIS session guarantees |
| 6 | WP6: Gaussian fit maps | Browser loader; WP3 for saved products; no hard WP1/WP2 dependency |
| 7 | WP7: GOES/SDO context | WP1 and the timeseries extra; WP3 for saved AIA context |
| Any | WP8: filter and stop scan | Browser loader; sequence importer-test edits with #50 and WP1 |

### WP1: Coordinate names, units and links

Primary paths: `glue_solar/sources/loaders/iris.py`, `sources/iris.py`,
package setup, and importer/linking tests. Start from the
[WP1 prototype package](IRIS_PLAN_PROTOTYPES/wp1/glue_solar/).

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
[session prototype](IRIS_PLAN_PROTOTYPES/wp3_impl.py).

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

- [ ] Use WP1's actual helper contract. Add SJI datetime64 `Time` and
  decimation-aware slit positions, then the per-frame slit subset, nearest
  index links, whisker preset, sync callbacks and browser quicklook.
- [ ] Use a data-only slit subset, not a collection-wide editable subset
  group. Use identity component links, not key joins; expose/remove them
  normally in the Link Editor. Pair time links within an observation.
- [ ] Open SJI, raster-map and wavelength Profile viewers for a matched
  selection. Use mean profiles on the released baseline, and gate slice
  profiles on the core feature. Whisker is wavelength versus step/time
  with a slit slider; spectroheliogram needs documentation, not a new preset.
- [ ] Sync only viewers/slice axes representing the matched frame/exposure,
  including newly opened viewers and the defined 4D stack mapping. Do not
  move wavelength or slit sliders inadvertently. Separate this from
  deferred ProfileViewer slice synchronization.
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
- [ ] Implement blink with the existing checkable tool and timer. Cycle
  enabled/visible data layers only, restore visibility on deactivation,
  and stop on close. Mix/alpha already exists. Make setup idempotent.
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
  Historical timings are machine-specific observations, not CI thresholds.
  Add action registration, docs/API entries and changelog; require WP3
  before claiming fitted IRIS products save in sessions.

### WP7: GOES and SDO context

Primary path: proposed `glue_solar/sources/context.py`, setup/dependencies,
context tests and user documentation. References:
[context prototype](IRIS_PLAN_PROTOTYPES/wp7chk/context_chk.py) and
[tests](IRIS_PLAN_PROTOTYPES/wp7chk/test_context.py).

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
  repeatedly and reconcile the fixture changes in #50.
- [ ] Document that the initial sorted directory walk is not interruptible
  in this prototype; cooperative stop is checked during file processing.
  No new dependency, persisted filter setting, log viewer, date widgets or
  extra filename-preset system is required.

### WP9: Tracked user/developer documentation

This consolidation completes the local planning-document cleanup, not the
remaining tracked RST edits. Those belong in a separate requested change
on #44 (or a follow-up if it has merged).

- [ ] `docs/user_guide/loading-iris-level-2-raster-and-sji-data.rst`: explain
  that aligned `aia_l2_*.fits` cutouts do not require an `_SDO` directory;
  clarify float32/NaN stack storage; use the actual distinct SJI/raster
  coordinate labels until WP1 normalizes them; state the directional
  linking limit and that saving can fail, not merely restoration.
- [ ] `docs/user_guide/guide-to-glue-1dprofile-viewer-for-iris-data.rst`:
  describe the same stack representation; distinguish released collapse
  profiles, a one-pixel subset, and the unreleased slice feature.
- [ ] `docs/user_guide/loading-aia-and-hmi.rst`: correct the image alt-text
  typo “AMI” to “AIA”.
- [ ] `docs/dev_guide/loader-customization.rst`: document the float32 memmap,
  NaN/mask reconstruction, exact acquisition times and scan-0 nominal WCS.
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
- Movie/sequence export and decoded `irispy.obsid.ObsID` enrichment are
  unscheduled. Alpha/mix, playback and the default spectroheliogram layout
  already exist and should not be reimplemented.
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

## Validation and working locations

Only the primary checkouts remain: `~/Git/glue`, `~/Git/glue-qt`, and
`~/Git/glue-solar`. The temporary `~/Git/glue-fixes/` worktrees were removed
after their commits were pushed. Historical logs still name those old paths.
For future source checks, first inspect the checkout/index and select the
intended branch safely; the runner tests the branch actually checked out,
not an inferred branch from a directory name.

The [test runner](IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py) accepts
colon-separated source roots and pytest arguments, prints import locations,
uses offscreen Qt/Agg, and isolates configuration/cache writes. For example,
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
- Logs from the review/fixes and post-merge runs remain under
  `/private/tmp/glue-review-20260904-0oadCw/`; they are disposable evidence,
  not a durable dependency. `publish-wcsaxes.log`, `publish-qt-mac.log`
  and `publish-qt-profile.log` record the repeated post-merge runs.

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
| [Branch review](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/IRIS_BRANCH_REVIEW.md) | `glue-solar/IRIS_BRANCH_REVIEW.md`; reproductions, fix/commit records and validation limits |
| [Capability audit](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/IRIS_IDL_GLUE_CAPABILITY_AUDIT.md) | `glue-solar/IRIS_IDL_GLUE_CAPABILITY_AUDIT.md`; detailed SolarSoft comparison, launch hierarchy and inspected source links |
| [APE-14 TODO](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/APE14_AUTOLINK_TODO.md) | `glue/APE14_AUTOLINK_TODO.md`; original design, tests and downstream caveats |
| [Profile TODO](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/PROFILE_WCS_RESTART_TODO.md) | `glue/PROFILE_WCS_RESTART_TODO.md`; split rationale, WCSAxes contract and acceptance |
| [macOS TODO](IRIS_PLAN_PROTOTYPES/archive/2026-09-05/MACOS_INTEGRATION_TODO.md) | `glue-qt/MACOS_INTEGRATION_TODO.md`; identity/font/icon evidence, manual gates and deferred work |

The rest of [IRIS_PLAN_PROTOTYPES/](IRIS_PLAN_PROTOTYPES/) remains in place.
Prototype source files were not moved or rewritten by this consolidation.
They are supporting experiments, not separately maintained work plans or
proof that the corresponding production feature has landed.
