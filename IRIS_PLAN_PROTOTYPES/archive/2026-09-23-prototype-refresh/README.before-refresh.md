# IRIS prototype evidence index

Validated 2026-09-22 evening, America/Los_Angeles (2026-09-23 UTC).
The [active plan](../IRIS_GLUE_GAP_PLAN.md) owns requirements and status.
This directory contains historical experiments, proposed production tests,
patches and logs. It is not a second implementation of glue-solar.

The user selected **validate and index**, preserving the experiments rather
than repairing them. All 148 existing Python files parse under Python 3.14.7;
only the checks listed below were executed. Parsing does not establish that
imports, assertions, scientific assumptions or application behavior work.
The original scripts and archived documents remain unchanged.

## Selected reference implementations

| Package | Start here | Current interpretation / required porting |
| --- | --- | --- |
| WP0 upstream changes | [PR drafts](wp0/) and `wp0_*.diff` | Historical discussion/patches. Use the live PR heads in the active plan; do not reapply these diffs or publish their old bodies. |
| WP1 coordinates/links | [copied package](wp1/glue_solar/), [linking tests](wp1/glue_solar/tests/test_linking.py) | Its own package must precede main on the import path. Raster/stack `Time` exists here, but SJI `Time`, `tools.py` and transparent-NaN layer handling from #52/#53 do not. Port only the coordinate/link changes. |
| WP2 moments | [module](chk_wp2/wp2_moments_module.py), [tests](chk_wp2/test_wp2_moments.py) | Five tests pass with current main and irispy 0.8.1. The tests use an in-window wavelength; this is numerical regression evidence, not line-core science validation. |
| WP3 sessions | [WCS/style/Quantity patches](wp3_impl.py), [acceptance tests](wp3chk_test_sessions.py) | Importing the module patches the current process. It does not connect the browser to `load_data`; acceptance tests assume a complete port and fail on unmodified main. |
| WP4 quicklook | [shared module](wp4_common.py), `wp4_*.py` | Imports WP1's absent-on-main `link_hpc`. Image-slider synchronization only; no cursor-follow/lock, profile synchronization or spectral time panel. See semantic gaps below. |
| WP5 display units/lines | [units](wp5_units.py), [line artist](wp5_linelist_mod.py), [11-line asset](iris_lines.csv), [session demo](wp5_ll_session.py) | Units replace the default converter in the process. Line positions are numeric world coordinates; the artist has no WCSAxes pixel conversion. The session demo writes `wp5_lines.glu` beside itself and was not rerun. |
| WP5 blink | [layer blink](wp5_blink.py) | Cycles visible data layers, not wavelength slices of one cube. Contains a top-level GUI demo and a timeout; it is not an import-only library. |
| WP6 fitting | [module](wp6_fitting.py), [brief variant](wp6_fitting_brief.py), [tests](wp6_test_fitting.py) | Eight tests pass against main; the integration check round-trips products from both variants through WP3. Mask/weight handling and physical validation remain absent. |
| WP7 context | [scratch module](wp7chk/context_chk.py), [scratch tests](wp7chk/test_from_brief.py), [production-shaped tests](wp7chk/test_context.py) | Scratch tests are blocked by missing timeseries dependencies here; production-shaped tests import an unimplemented module. The scratch module duplicates `link_hpc`; port using WP1's shared helper. |
| WP8 browser | [scanner](wp8_scan.py), [dialog](wp8_proto.py), [corrected progress variant](wp8_chk_proto_fix.py), [UI](wp8_loader.ui), [tests](wp8_test_proto.py) | Eight tests pass against main. The primary dialog still lacks the progress-value correction present in `ProtoImporterFixed`; passing tests do not cover that visible-text defect. |
| Cross-package checks | [runner](review_20260905/run_checks.py), [integration tests](review_20260905/test_plan_integration.py) | Four checks pass with the copied WP1 package: UI loading, helper identity/link creation, and two synthetic fitted-map round trips. These do not exercise the full quicklook GUI. |

## Assumptions that must not be copied unchanged

- WP1's `AUTOLINKS_IRIS = Version(glue.__version__) > Version('1.27.0')`
  does not identify core #2595 reliably. Source snapshot imports can retain
  installed release metadata; future versions need not contain the PR.
  Its coordinate inverse monkeypatch also installs unconditionally.
  Production gates must identify actual supported capabilities/releases.
- WP4 `quicklook()` pairs datasets by OBSID alone. Include start time and
  observation membership: OBSID identifies an observing program, not a
  unique execution. `nearest()` assumes sorted finite times, clamps outside
  coverage, and has no maximum-offset policy. Those are prototype limits,
  not accepted scientific matching guarantees.
- WP4's slit-position division by inferred powers of ten is a fixture
  heuristic. Preserve explicit decimation evidence; an off-image coordinate
  in production must not trigger guessed rescaling. `cube_times`/`add_time`
  duplicate current main's time handling and should not be ported.
- `sync_slices()` only hooks `ImageViewerState`, wraps `app.new_data_viewer`,
  and retains hooked states. It needs lifecycle cleanup and explicit
  image/profile/point coordination to satisfy the active CRISPEX milestone.
- WP5 line-list tests on numeric axes do not prove alignment on core #2601's
  WCSAxes pixel axes. Layer blink is not two-wavelength blink. Full IRIS
  sessions remain WP3 work even if a synthetic line list can be saved.
- WP6 clips negative values and replaces NaNs with zero before fitting,
  ignores the source mask and has no uncertainty weights. A finite fitted
  centroid in a cropped fixture is not a validated physical measurement.
- Some scripts use deleted `/private/tmp/.../scratchpad` or checkout paths,
  install global patches/registries, write sessions, or perform network
  requests. Inspect an individual entry point before running it. Do not
  import or run the entire directory as one test suite.
- Headers such as “shipping code”, “final form” and “33 passed” describe
  their historical experiment, not the present production state. Proposed
  test imports like `glue_solar.sources.context` name future modules.

## Validation 2026-09-22

Main baseline: glue-solar `236f0a8`, released glue-core 1.27.0, editable
glue-qt source at #74 `6b579814eb7c`, irispy-lmsal 0.8.1, Astropy 8.0.1,
NumPy 2.5.2, Matplotlib 3.11.1, ndcube 2.4.1, pytest 9.1.1, Python 3.14.7.
The Qt installed version string is `0.1.dev6892+ga9c8a0640`; its source
path and Git SHA, not that stale metadata, identify the tested code.
CI status is intentionally excluded.

| Check | Result | What it establishes |
| --- | --- | --- |
| Current `glue_solar/tests` | 33 passed, 2 skipped | Production regression baseline; skips are core autolinking and the superseded solar cursor tool. |
| WP1 copied-package `test_linking.py` | 10 passed, 1 skipped | Prototype names/units, high-level round trips and world links; real autolink test skipped on released core. |
| WP2 `test_wp2_moments.py` + WP6 `wp6_test_fitting.py` on current main | 13 passed (5 + 8) | Numerical products, units, source links, error handling and fitting worker completion for the selected cases. |
| WP8 `wp8_test_proto.py` on current main | 8 passed | Filter, stop, rescan, extraction and worker lifecycle cases; not progress-text rendering. |
| `review_20260905/test_plan_integration.py` with copied WP1 | 4 passed | Helper contract, restored UI and both WP6 variants' synthetic WP3 round trips. |
| WP3 `wp3chk_test_sessions.py` on unmodified main | 5 failed, 1 passed | Missing WCS/Quantity/style persistence and browser LoadLogs; plain Data passes. Expected unimplemented behavior, not a new regression. |
| WP7 `test_context.py --collect-only` on main | Collection error | `glue_solar.sources.context` does not exist. |
| WP7 `test_from_brief.py` | Collection error | SunPy timeseries warns about missing `cdflib>=1.3.2` and `h5netcdf>=1.4.0`; warnings are errors in this test configuration. |
| Core #2595 `test_wcs_autolinking.py` at `c49aeb1af14a` | 31 passed, 1 xfailed, 1 xpassed | Current upstream autolink tests, not the complete downstream IRIS matrix. |
| Core #2601 `test_viewer.py` at `acaf4e1c0ef8`, with Qt #70 source | 9 passed, 1 skipped | Selected slice/WCSAxes viewer behavior; optional visual check skipped. |
| Qt #70 `test_data_viewer.py` at `f1471b7ad843`, with core #2601 source | 51 passed, 1 skipped | Profile UI on the combined two-PR source snapshot. |
| Three temporary focused probes | 3 passed | Default raster axes are wavelength × slit; WP4 import fails on main as expected; installing WP3 patches allows a real raster coordinate/Time round trip. |
| Python syntax | 148 / 148 parsed | Static syntax only; no historical scripts rewritten. |

The temporary probes and exported source trees were placed under
`/tmp/iris-plan-validation-20260922/`. They are disposable, not required
runtime files. Combining core and Qt test files into one pytest invocation
initially failed because both conftests register `--no-optional-skip`;
running those suites in separate processes produced the results above.

The runner disables repository `addopts` and pytest's cache provider and
isolates Glue/configuration caches with offscreen Qt. pytest-doctestplus
and pytest-mpl are not installed: no RST/doctest or visual-comparison
certification is implied. No dependencies were installed, science data
downloaded, native macOS session exercised, or production code changed.
The whole eleven-PR combination, WP5 demos, full WP3 relocation workflow
and larger real-data interaction remain unvalidated.

### Reproduce selected checks

Run from the repository root. Each command starts a fresh process so a
prototype's patches do not contaminate another baseline. The path order
is intentional: WP1 tests use the copied package; main tests use main.

```sh
iris_root="$PWD"
iris_protos="$iris_root/IRIS_PLAN_PROTOTYPES"
iris_runner="$iris_protos/review_20260905/run_checks.py"

.venv/bin/python -B "$iris_runner" "$iris_root" glue_solar/tests

.venv/bin/python -B "$iris_runner" "$iris_protos/wp1" \
  "$iris_protos/wp1/glue_solar/tests/test_linking.py"

.venv/bin/python -B "$iris_runner" "$iris_root:$iris_protos:$iris_protos/chk_wp2" \
  "$iris_protos/chk_wp2/test_wp2_moments.py" \
  "$iris_protos/wp6_test_fitting.py" -p glue_solar.conftest

.venv/bin/python -B "$iris_runner" "$iris_root:$iris_protos" \
  "$iris_protos/wp8_test_proto.py"

.venv/bin/python -B "$iris_runner" "$iris_protos/wp1:$iris_protos" \
  "$iris_protos/review_20260905/test_plan_integration.py"

# Expected failures until WP3 is implemented; do not import wp3_impl first.
.venv/bin/python -B "$iris_runner" "$iris_root:$iris_protos" \
  "$iris_protos/wp3chk_test_sessions.py" -p glue_solar.conftest

# Expected missing-production-module error:
.venv/bin/python -B "$iris_runner" "$iris_root:$iris_protos" \
  "$iris_protos/wp7chk/test_context.py" --collect-only

# Scratch import works only with the required SunPy timeseries environment:
.venv/bin/python -B "$iris_runner" "$iris_root:$iris_protos/wp7chk" \
  "$iris_protos/wp7chk/test_from_brief.py"
```

For upstream suites, export the exact PR commits into separate temporary
source directories using `git archive`; no checkout switch or merge is
needed. Pass `core-source:qt-source` to the runner, then run each
repository's test file in a separate invocation. The current export SHAs:

- Core APE-14: `c49aeb1af14a8504c8f75a42d3a36883be5e9776`.
- Core profile/WCSAxes (includes slice): `acaf4e1c0ef88d513aecc158f81c8b9dcef9c28b`.
- Qt profile: `f1471b7ad843b453bf0c8f4e92e743cce04c6e7d`.

Use `glue/plugins/wcs_autolinking/tests/test_wcs_autolinking.py`,
`glue/viewers/profile/tests/test_viewer.py` and
`glue_qt/viewers/profile/tests/test_data_viewer.py`, respectively.
Importing a source snapshot does not change installed package metadata;
inspect skips before interpreting results.

## Remaining directory inventory

- [archive/2026-09-05/](archive/2026-09-05/) preserves the original full
  plan, capability/branch audits and three upstream TODOs.
- [archive/2026-09-22/](archive/2026-09-22/) preserves the September 5
  consolidated plan. The directory date is the archival date.
- [IRIS_GLUE_GAP_PLAN.2026-08-29.md](IRIS_GLUE_GAP_PLAN.2026-08-29.md)
  is another historical plan, not an alternative current task list.
- [findings/](findings/), [wp9chk/](wp9chk/),
  [audit-findings-condensed.txt](audit-findings-condensed.txt) and
  [brief-checker-reports.txt](brief-checker-reports.txt) are prior review
  output. Their verdicts and test counts are dated evidence.
- `wp*chk*`, `chk*`, `cc_*`, `sv2_*`, `ulb_*`, `ver_sess*`, `v_*`,
  [verify/](verify/) and other root-level probes are investigations and
  variant checks; names alone do not select a maintained implementation.
- [wp3_sess/](wp3_sess/) holds historical session/data relocation fixtures.
  Cached/generated files and logs are retained; none is a release artifact.

Archived terminology and claims are deliberately preserved. In particular,
the old audit calls the wavelength × slit view a “spectroheliogram”; the
active plan corrects this to **spectrogram**, and reserves spectroheliogram
for the spatial raster map at a selected wavelength.
