> Historical snapshot, archived 2026-09-05. Not an active checklist.
> Original location: `glue-solar/IRIS_BRANCH_REVIEW.md`. Body preserved verbatim; paths and status claims describe that original context and may be stale.
> Current instructions: [the central work plan](../../../IRIS_GLUE_GAP_PLAN.md).

# Fix status — 2026-09-05

The review below is the pre-fix record. The branch fixes and Qt CI code/configuration repairs were **committed and pushed on 2026-09-05**, as requested. All eight remote tips were verified against the local commits. Planning/prototype corrections and these review notes remain local and untracked. Branch-specific worktrees live under `/Users/nabil/Git/glue-fixes/`; the original checkouts retain their branches. Fresh remote CI has not yet been validated.

- [x] Correct slice profile coordinates and Python export on both active core branches.
- [x] Correct negative fractional datetime round trips.
- [x] Make APE-14 linking pass on Astropy 6.1.7 as well as 8.0.1.
- [x] Make the fixture branch work with irispy 0.8.1 and recognize both fixture filename conventions.
- [x] Repair the Qt plugin-manager test and profile branch CI configuration.
- [x] Correct WP1/WP4 and WP3/WP6 integration contracts and add regressions.
- [x] Reconcile current plan/TODO status and missing artifact references; restore the WP8 UI from its inline diff.
- [x] Identify the CircleCI failures as two WCS-region image comparisons, not rendering crashes.
- [ ] Resolve the remaining visual-reference differences in a controlled environment and obtain fresh remote CI. No baselines, hashes or tolerances were changed.

## Where the fixes are

| Existing branch | Worktree / changed code |
| --- | --- |
| glue `profile-slice` | [core-profile-slice](/Users/nabil/Git/glue-fixes/core-profile-slice/glue/viewers/profile/state.py) — selected-view coordinates, export and regressions |
| glue `profile-wcsaxes` | [core-profile-wcsaxes](/Users/nabil/Git/glue-fixes/core-profile-wcsaxes/glue/viewers/profile/state.py) — same correction on the stacked branch |
| glue `fix-datetime-epoch` | [core-datetime](/Users/nabil/Git/glue-fixes/core-datetime/glue/utils/matplotlib.py) — floor whole seconds before adding the positive fractional remainder |
| glue `ape14-wcs-autolink` | [core-ape14](/Users/nabil/Git/glue-fixes/core-ape14/glue/plugins/wcs_autolinking/wcs_autolinking.py) — avoid no-op sliced WCS wrappers |
| glue-qt `ci-fixes` | [qt-ci](/Users/nabil/Git/glue-fixes/qt-ci/glue_qt/app/tests/test_plugin_manager.py) — genuine pending plugin edit before testing a failed save |
| glue-qt `profile-wcs-pr` | [qt-profile](/Users/nabil/Git/glue-fixes/qt-profile/pyproject.toml) — shared CI repairs and the permission-test correction |
| glue-qt `macos-integration` | [existing checkout](/Users/nabil/Git/glue-qt/glue_qt/app/tests/test_plugin_manager.py) — same permission-test correction |
| glue-solar `loadable-iris-fixtures` | [solar-fixtures](/Users/nabil/Git/glue-fixes/solar-fixtures/glue_solar/conftest.py) — valid rotated synthetic pointing and shared test-file lookup |
| glue-solar planning/prototypes | Existing checkout: [plan](/Users/nabil/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md), [WP4](/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp4_common.py), both WP6 fitting modules, [WP8 UI](/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp8_loader.ui), and [integration regressions](/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/review_20260905/test_plan_integration.py) |

The legacy unsplit/backup branches were not modified. Core main has no tracked code change. Shared fixes were committed on `profile-slice` and `ci-fixes`, then merged into their dependent branches without rewriting history. The WCSAxes conflict resolution exactly matches the previously tested files; the Qt profile merge additionally inherits the existing generated-version ignore rule. All affected indexes and tracked worktrees are clean. Temporary publication stashes were removed after verifying their contents were preserved in the pushed commits.

## Published branch tips — 2026-09-05

| Repository | Branch | Verified origin tip |
| --- | --- | --- |
| glue | `profile-slice` | `1c19021d593b192af5f6f4c6c8083506dcf5b6ca` |
| glue | `profile-wcsaxes` | `6cc8f20bd1ec62a188254d0e4507ab0e778a0a3b` |
| glue | `fix-datetime-epoch` | `a46cc24cbdec1d0a4275cd7ab77d8a8ea74888ef` |
| glue | `ape14-wcs-autolink` | `656017b972344a4291934c3a02af73a988728b95` |
| glue-qt | `ci-fixes` | `5cc9e23ee71e647984ed89e3d0ff6db003082ab0` |
| glue-qt | `macos-integration` | `0b16dd55f1cb9135ab384c4cc97d948ed838bf36` |
| glue-qt | `profile-wcs-pr` | `f5444473a1c390facd43e90acb21a75f016929fd` |
| glue-solar | `loadable-iris-fixtures` | `383dec253931c3c44569113994a3f35c9bf83deb` |

The post-merge checks repeated the WCSAxes profile suite (63 passed, 1 skipped), Qt macOS suite (622 passed, 4 skipped, 2 xfailed), and Qt profile suite (625 passed, 4 skipped, 2 xfailed). Logs are `publish-wcsaxes.log`, `publish-qt-mac.log`, and `publish-qt-profile.log` under `/private/tmp/glue-review-20260904-0oadCw/`. No force-push, main-branch update, PR merge or review request was made. The unchanged browser branch and historical `macos-integration-v2` alias were not pushed.

## Post-fix local validation

| Check | Result |
| --- | --- |
| Core slice profile suite, including linked/transposed coordinates and exported subsets | 42 passed, 1 skipped |
| Core WCSAxes profile suite | 63 passed, 1 skipped |
| Datetime branch: utility suite plus histogram/scatter viewer tests | 162 passed, 4 skipped |
| APE-14 plus related link suites, Astropy 8.0.1 | 69 passed, 1 xfailed, 1 xpassed |
| APE-14 suite on Astropy 6.1.7 / NumPy 2.2.6 | 31 passed, 1 xfailed, 1 xpassed |
| Qt CI branch full suite with development core | 619 passed, 4 skipped, 2 xfailed |
| Qt macOS branch full suite with development core | 622 passed, 4 skipped, 2 xfailed |
| Qt profile branch full suite with the core WCSAxes branch | 625 passed, 4 skipped, 2 xfailed |
| Solar fixture branch full suite with irispy 0.8.1 | 31 passed, 1 skipped |
| WP1/WP4 linking, both WP6 modules through WP3 save/load, and restored WP8 UI | 4 passed |
| WP6 fitting prototype: synthetic fits, real irispy raster, pixel links/subsets and worker completion | 8 passed |

The [runner](/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/review_20260905/run_checks.py) takes colon-separated source roots followed by pytest arguments and isolates configuration/caches. It also propagates import paths to export subprocesses. Core changed files pass the repository-pinned Ruff 0.15.20; Qt and solar changed files pass the newer local Ruff checks (newer copyright-only baseline rules excluded for Qt). Diff whitespace checks pass. These checks do not recreate every tox/platform environment; doctest plugins and pytest-mpl are absent from the main local environment, so the skipped visual tests are not certified by these counts. The existing xfail/xpass outcomes are retained, not suppressed.

## Remaining CircleCI validation item

[Build 6860](https://circleci.com/gh/glue-viz/glue/6860), along with checked builds 6861 and 6864, fails only `TestWCSRegionDisplay.test_image_wcs_viewer` and `test_image_flipped_wcs_viewer`: two image-hash/RMS comparisons, seven visual tests passing. The saved images show differences around WCS labels/ticks. This is distinct from the separately documented RegionData exception in issue #2600.

[Successful build 6853](https://circleci.com/gh/glue-viz/glue/6853) used the same Astropy 8.0.1, Matplotlib 3.11.1, NumPy 2.4.6 and pytest-mpl 0.19.0, but several other dependencies differ (including fonttools and kiwisolver). That is evidence of environment drift, not proof that a particular package caused the differences. No speculative dependency pin was added.

The repository's reference-image deployment job writes to the separate `glue-viz/glue-core-visual-tests` repository. A controlled comparison and any accepted reference update remain outstanding; no deployment, reference-image edit, hash replacement, tolerance relaxation or remote rerun was performed. Prototype corrections also do not ship WP1–WP8: production IRIS sessions remain unsupported, and the planned WP9 RST work remains future work.

---

# Glue planning and branch review

Reviewed 2026-09-04; remote PR heads/checks and upstream main tips refreshed 2026-09-05.

## Verdict

The documents are useful but are not yet a reliable, executable handoff. Several status entries are stale, and two proposed work-package integrations fail when connected. The active branches also have reproducible correctness/test-compatibility problems. Do not mark the whole collection ready to merge.

The current `glue-solar:iris-observation-browser` branch has the strongest validation: its full local suite passes (27 tests), and [PR #44](https://github.com/glue-viz/glue-solar/pull/44) has 16 successful checks and 5 skips. No new defect was confirmed in that branch during this review. This does not extend to the separate `loadable-iris-fixtures` branch or certify future quicklook/science features.

No repository files, indexes, commits, branches, or remote state were changed. Existing untracked work was preserved. Diagnostic snapshots, tests, dependencies and logs are confined to this temporary review directory.

## Confirmed branch findings

### 1. P2: slice profiles pair the selected intensity row with coordinates from row zero

Affected: `glue:profile-slice` and the numeric-axis path inherited by `profile-wcsaxes`.

The new slice path selects the correct data using `slice_view`, but subsequently constructs `axis_view = [0] * data.ndim` for its world-coordinate values. For a coordinate that depends on another pixel axis, moving the slice therefore changes the intensity without changing its corresponding coordinates. A small coupled-WCS regression gives x = `[1, 2, 3, 4]` for row 2, where the WCS gives `[21, 22, 23, 24]`; y is correctly taken from row 2.

Location: [profile-slice state.py:517](/private/tmp/glue-review-20260904-0oadCw/core-profile-slice/glue/viewers/profile/state.py:517), especially lines 529–531; inherited numeric path in [profile-wcsaxes state.py:602](/private/tmp/glue-review-20260904-0oadCw/core-profile-wcsaxes/glue/viewers/profile/state.py:602). The Python-export path also constructs its coordinate view at zero. This finding concerns numeric world-coordinate plotting, not a claim that the separate native WCSAxes tick formatter fails identically.

Required correction: derive the x-coordinate view from the same selected slice as y, including linked-layer translation; cover numeric display-unit overrides and Python export.

Evidence: [regression test](/private/tmp/glue-review-20260904-0oadCw/test_review_edges.py), [slice result](/private/tmp/glue-review-20260904-0oadCw/profile-edge.log), [WCSAxes-branch result](/private/tmp/glue-review-20260904-0oadCw/profile-wcs-edge.log). Both fail the added assertion although their existing profile suites pass.

### 2. P2: datetime conversion shifts negative fractional timestamps by one second

Affected: `glue:fix-datetime-epoch`, [PR #2599](https://github.com/glue-viz/glue/pull/2599).

[matplotlib.py:481](/private/tmp/glue-review-20260904-0oadCw/core-fix-datetime-epoch/glue/utils/matplotlib.py:481) truncates seconds toward zero while obtaining the fraction with positive modulo. With the default 1970 Matplotlib epoch, round-tripping `1969-12-31T23:59:59.500000000` returns `1970-01-01T00:00:00.500000000`. The same assertion passes on local main. More generally, fractional times before the configured epoch are affected.

Required correction: use consistent whole-second/fraction decomposition for negative values and retain a before-epoch regression.

Evidence: [branch failure](/private/tmp/glue-review-20260904-0oadCw/date-edge.log), [main control](/private/tmp/glue-review-20260904-0oadCw/date-edge-main.log), [regression test](/private/tmp/glue-review-20260904-0oadCw/test_review_edges.py). The branch's existing utility tests pass, so their coverage misses this case.

### 3. P2: APE-14 support fails on an existing supported dependency combination

Affected: `glue:ape14-wcs-autolink`, [PR #2595](https://github.com/glue-viz/glue/pull/2595).

The new `test_wcs_autolink_low_level_and_fits_wcs` expects one link but gets zero in all three Python 3.10 CI jobs. A local Python 3.12 probe with Astropy 6.1.7 and NumPy 2.2.6 reproduces zero links. Direct high-level transforms work; the branch's unconditional `SlicedLowLevelWCS` wrapping of these 1D WCSes triggers scalar-iteration `TypeError`s under Astropy 6.1.7. The probe catches these and rejects the link.

Location: [wcs_autolinking.py:288](/private/tmp/glue-review-20260904-0oadCw/core-ape14-wcs-autolink/glue/plugins/wcs_autolinking/wcs_autolinking.py:288) and the transform probe at lines 315–319.

Required correction: make the 1D path work with the supported Astropy range, or explicitly resolve the dependency/support policy before advertising the acceptance criterion as satisfied.

Evidence: [upstream failed job](https://github.com/glue-viz/glue/actions/runs/33636072401/job/100267501252), [local probe](/private/tmp/glue-review-20260904-0oadCw/ape14_probe.py), [local result](/private/tmp/glue-review-20260904-0oadCw/ape14-astropy617.log). The modern local stack passes the focused existing suite; that does not invalidate the older-stack failure.

### 4. P2: the fixture branch requires irispy behavior/test assets absent from its declared minimum

Affected: `glue-solar:loadable-iris-fixtures`, tip `d1ab3b3`.

The branch changes real fixture names to `*_test.fits`, which are not supplied by irispy-lmsal 0.8.1. Seven tests fail with `StopIteration`. Its new synthetic SJI fixture also uses identity-PC off-diagonal zeros; the irispy 0.8.1 reader treats these as missing samples and raises `ValueError: array of sample points is empty`. The fixture itself acknowledges the need for newer row-wise dropped-pointing handling, but `pyproject.toml` still allows `irispy-lmsal>=0.8.1`.

Locations: [test_importer.py:53](/private/tmp/glue-review-20260904-0oadCw/solar-loadable-iris-fixtures/glue_solar/tests/test_importer.py:53), [test_plugin.py:29](/private/tmp/glue-review-20260904-0oadCw/solar-loadable-iris-fixtures/glue_solar/tests/test_plugin.py:29), [conftest.py:90](/private/tmp/glue-review-20260904-0oadCw/solar-loadable-iris-fixtures/glue_solar/conftest.py:90), and [pyproject.toml:22](/private/tmp/glue-review-20260904-0oadCw/solar-loadable-iris-fixtures/pyproject.toml:22).

Required correction: retain compatibility with the declared test dependency, or record and validate the actual upstream dependency required by this branch. This is a fixture/test-compatibility finding, not a newly introduced production-loader regression.

Evidence: [full branch test result](/private/tmp/glue-review-20260904-0oadCw/solar-fixtures.log): **8 failed, 21 passed, 1 skipped**. No PR was found for this branch.

## CI/readiness blockers separate from new production defects

- **glue-qt #69 (`ci-fixes`) is incomplete; #68 inherits the same failure.** With development glue-core, `PluginConfig.save()` correctly skips unchanged configuration. `test_permission_fail` opens an empty plugin list and makes no change, so it never attempts the write expected to produce an error dialog. Its `qmb.call_count == 1` assertion fails. Reproduced locally: 1 failure, 2 passes. Make the test attempt a real configuration change; do not undo the production no-op-save optimization. The plan's description of the dropped checkbox tweak as a “no-op” is misleading. See [test_plugin_manager.py:66](/private/tmp/glue-review-20260904-0oadCw/qt-ci-fixes/glue_qt/app/tests/test_plugin_manager.py:66), [local result](/private/tmp/glue-review-20260904-0oadCw/qt-permission.log), and [CI failure](https://github.com/glue-viz/glue-qt/actions/runs/33636133805/job/100268822503). Seven regular development-dependency jobs fail on each PR, in addition to explicitly allowed-failure jobs.
- **glue-qt #70 does not contain the CI repairs.** It still loads pytest-flake8 1.3.0 with pytest 9 and fails collection with `PluginValidationError` for the removed `pytest_collect_file(path=...)` hook argument. Record its dependency on the CI repair work. This is inherited CI configuration, not evidence that the profile feature itself cannot run. See [failed job](https://github.com/glue-viz/glue-qt/actions/runs/33636424549/job/100287596010).
- **Every reviewed glue-core PR has a failed CircleCI `py311-test-visual` check.** The non-APE GitHub Actions checks are green, but the visual failures were not diagnosed here. Do not equate “GitHub Actions green” with “all checks green.”

## Confirmed plan integration defects

### 5. P2: WP4's link helper does not match WP1's actual interface

[The WP4 dependency statement](</Users/nabil/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md:2636>) claims an exact `link_hpc(data_collection, datasets)` interface. WP1 instead defines `link_hpc(data_collection) -> list[LinkSame]`; the caller must add the returned links. WP4's stand-in accepts two arguments and adds links itself, hiding both differences.

Replacing the stand-in with WP1's actual helper makes `quicklook()` fail immediately with `TypeError: link_hpc() takes 1 positional argument but 2 were given` at [wp4_common.py:182](</Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp4_common.py:182>) / plan line 2884.

Required correction: use WP1's actual import and `dc.add_link(link_hpc(dc))` contract, then rerun an integrated quicklook test. WP7 already documents the correct contract.

### 6. P2: WP3 does not serialize the map coordinate wrapper generated by WP6

[The plan says no extra saver is needed](</Users/nabil/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md:3794>), because WP3 recursively handles sliced WCSes. However, [WP6 assigns a bare `SlicedLowLevelWCS` to `maps.coords`](</Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp6_fitting_brief.py:103>), while WP3 only installs `_GlueWCS.__gluestate__`. Its recursive record function is not registered as a saver for the outer sliced object; that object also contains another `_GlueWCS` that the record function cannot encode as written.

A synthetic Gaussian fit followed by `GlueSerializer(maps).dumps()` still raises `GlueSerializeError` after loading WP3's implementation. Correct the wrapper/saver contract and demonstrate a fitted-map save/load round trip before claiming WP3 unblocks WP6 sessions.

Evidence for both integration defects: [runnable tests](/private/tmp/glue-review-20260904-0oadCw/test_plan_integration.py), [failure log](/private/tmp/glue-review-20260904-0oadCw/plan-integration.log). These are defects in the proposed implementation handoff, not claims that unimplemented work packages have already shipped.

## Documentation reconciliation

| Document/claim | Verified state / correction needed |
| --- | --- |
| `IRIS_GLUE_GAP_PLAN.md` top status, WP0, and `glue-qt/MACOS_INTEGRATION_TODO.md` say #68 rewrite/force-push/body/draft update is pending | Already done: local `macos-integration`, `macos-integration-v2`, origin branch and [PR #68](https://github.com/glue-viz/glue-qt/pull/68) all identify `4d93c64`. PR is draft and its body is updated. Retire the stale force-push/reset instructions; do not rerun them. |
| WP0 later “current state” says no upstream PRs, and its goal requests reviews on #44 | Superseded by the published draft PRs and the explicit decision not to request #44 reviews. Mark this material historical rather than leaving contradictory current instructions. |
| WP0 says local core main equals upstream main, with no drift | Local main remains `dae530c3`; upstream main is now `751871df`, two commits ahead. The additional change is in `glue/core/state_path_patches.txt`, with no touched-path overlap with these topic branches. No branch update was performed. |
| `APE14_AUTOLINK_TODO.md` marks acceptance complete | Main implementation and PR status are accurate, but the supported older-stack failure above must be recorded. Downstream coherence/session caveats remain relevant. |
| `PROFILE_WCS_RESTART_TODO.md` records the split and green local suites | The split/ancestry is correct, and existing local suites pass. Add the slice-coordinate regression and current CI limitations; local green suites alone are not readiness evidence. |
| Plan's implementation inventory | WP1–WP8 remain prototype/planned work, not production changes. The `loadable-iris-fixtures` branch is missing from the active-work inventory. WP9 audit text was applied, but the proposed user/developer-guide RST work remains outstanding. |
| Plan calls WP6 “sessions” in WP4/WP5/WP7 text | Sessions are WP3; fits are WP6. Correct cross-references such as lines 2638, 3141 and 4722. |
| Plan lines 25–29 say every referenced artifact was copied | `wp8_loader.ui` and `wp4_common.py.writer` are absent. `wp0/long/` does not exist; long draft bodies are directly under `wp0/`. `wp8_proto.py` expects the missing UI file, so its archived code is not directly runnable as supplied. Inline snippets/diffs mitigate but do not make the archive-completeness claim true. |
| `IRIS_IDL_GLUE_CAPABILITY_AUDIT.md` scope | The distinction between local browser/loading support and missing IDL quicklook/analysis features remains sound. Current loader representation and its manual-linking/session limitations match the implementation. Representative SolarSoft dispatch sources were checked; this was not a new line-by-line scientific audit of every IDL routine. |

The archived drafts, critic notes and old plan are historical evidence, not a second current instruction set. Their past observations should remain dated; the current plan should resolve rather than duplicate them.

## Branch map and validation

All published topic-branch heads below match the local tips inspected. All listed PRs remain open; all except solar #44 are drafts.

| Repository / active topic branch | Tip / PR | Local checks | Remote readiness |
| --- | --- | --- | --- |
| glue / `ape14-wcs-autolink` | `bad24b99` / [2595](https://github.com/glue-viz/glue/pull/2595) | Focused autolinking/link suites: 69 passed, 1 xfail, 1 xpass; older-stack probe fails | 3 Python 3.10 jobs + visual check fail |
| glue / `profile-slice` | `30d20d4e` / [2596](https://github.com/glue-viz/glue/pull/2596) | Profile suite: 36 passed, 1 skipped; added coordinate regression fails | GHA green; visual check fails |
| glue / `profile-wcsaxes` | `6b524544` / [2601](https://github.com/glue-viz/glue/pull/2601) | Profile suite: 57 passed, 1 skipped; inherited coordinate regression fails | GHA green; visual check fails |
| glue / `fix-session-style-meta` | `431c9433` / [2597](https://github.com/glue-viz/glue/pull/2597) | State suite: 42 passed; no new defect confirmed | GHA green; visual check fails |
| glue / `fix-world2pixel-correlated-axes` | `e6c28020` / [2598](https://github.com/glue-viz/glue/pull/2598) | Coordinate suite: 28 passed; no new defect confirmed | GHA green; visual check fails |
| glue / `fix-datetime-epoch` | `90fcdf18` / [2599](https://github.com/glue-viz/glue/pull/2599) | Utility suite: 13 passed, 1 skipped; added epoch regression fails | GHA green; visual check fails |
| glue-qt / `ci-fixes` | `5e1f0ee7` / [69](https://github.com/glue-viz/glue-qt/pull/69) | Plugin manager with core main: 2 passed, 1 failed | 12 failed checks, including 7 regular dev-dependency jobs |
| glue-qt / `macos-integration` | `4d93c64f` / [68](https://github.com/glue-viz/glue-qt/pull/68) | Full suite with released core: 622 passed, 4 skipped, 2 xfailed | 14 failed checks, including 7 regular dev-dependency jobs |
| glue-qt / `profile-wcs-pr` | `4c8d7b08` / [70](https://github.com/glue-viz/glue-qt/pull/70) | Profile + multi-slice tests: 46 passed/14 skipped on released core; 59 passed/1 skipped with core WCSAxes branch | 34 failed checks; pytest plugin collection blocker |
| glue-solar / `iris-observation-browser` | `d3a2bd31` / [44](https://github.com/glue-viz/glue-solar/pull/44) | Full suite: 27 passed | 16 successful checks, 5 skipped, none failed |
| glue-solar / `loadable-iris-fixtures` | `d1ab3b3c` / no PR found | Full suite on irispy 0.8.1: 8 failed, 21 passed, 1 skipped | No PR checks to assess |

Other local branches were reconciled as follows:

- Core `profile-wcs` (`c3bcd75b`) is the older unsplit version of the profile work. The split WCSAxes branch has the same production code, with unused-test-variable cleanup. `profile-wcsaxes` contains `profile-slice`, matching the documented C → A order.
- Qt `profile-wcs` (`1133c0e9`) is the old source for `profile-wcs-pr`; the published branch removes the tracked generated `_version.py`. `macos-integration-v2` and `macos-integration` are identical. The macOS branch contains `ci-fixes`; the profile branch does not.
- Solar `loadable-iris-fixtures` contains the browser branch plus two fixture commits. `backup/iris-observation-browser-pre-rebase` is a historical backup, not a merge candidate certified by this review.
- Local Qt main (`9780eaf9`) and solar main (`5b229fbc`) match upstream. Core main drift is described above. The obsolete [core PR #2248](https://github.com/glue-viz/glue/pull/2248) is closed, and [issue #2600](https://github.com/glue-viz/glue/issues/2600) exists.

## Reproduction and limits

The review used `git archive` snapshots to avoid checkout/index changes. [run_checks.py](/private/tmp/glue-review-20260904-0oadCw/run_checks.py) prepends the requested snapshot paths, uses offscreen Qt/Agg, isolates configuration/cache paths, disables pytest cache and bytecode generation, and prints actual core/Qt import locations.

Example from this directory:

```sh
/Users/nabil/Git/glue-solar/.venv/bin/python -B run_checks.py \
  "$PWD/core-fix-datetime-epoch" test_review_edges.py -k datetime

/Users/nabil/Git/glue-solar/.venv/bin/python -B run_checks.py \
  "$PWD/core-profile-slice" test_review_edges.py -k profile

/Users/nabil/Git/glue-solar/.venv/bin/python -B run_checks.py \
  "/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/wp1:/Users/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES" \
  test_plan_integration.py
```

The main local environment was Python 3.14.7, Astropy 8.0.1, NumPy 2.5.2, Matplotlib 3.11.1, pytest 9.1.1, irispy-lmsal 0.8.1 and ndcube 2.4.1. Released-core comparisons used glue-core 1.27.0. The older APE probe used a separate existing Python 3.12 interpreter and dependencies installed only into this scratch directory. The archived WP1 package's own suite additionally passed 37 tests with 1 skip.

These were source-snapshot checks, not recreated wheel/tox environments across every supported platform. Native interactive macOS menus, every future work-package prototype, full session/science workflows, full IDL parity, and CircleCI image differences were not exhaustively revalidated. No new defect confirmed means exactly that, not a guarantee of correctness.

Suggested next work is narrow: repair the four branch findings, fix/sequence the shared CI issues, reconcile the two prototype contracts, then update the current-status sections and rerun the relevant checks. Those edits require a separate implementation request.
