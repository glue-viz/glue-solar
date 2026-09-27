# IRIS prototype evidence index

Refreshed 2026-09-23. The [active plan](../IRIS_GLUE_GAP_PLAN.md) owns
requirements and production status; its [GUI examples](../IRIS_GLUE_GAP_PLAN.md#what-the-missing-features-mean-at-the-keyboard)
explain the missing CRISPEX interactions.

The user selected **refresh existing prototypes**, leaving new interactions
planned. The selected entry points below were repaired and checked. Originals
are preserved under [archive/2026-09-23-prototype-refresh/](archive/2026-09-23-prototype-refresh/),
including the [previous index and validation record](archive/2026-09-23-prototype-refresh/README.before-refresh.md).
No tracked production code was changed. These prototypes are local experiments,
not shipped features or a package to copy over glue-solar.

## Existing-capability audit after the refresh

The [2026-09-23 audit](review_20260923/README.md) corrects the earlier gap
classification: native axis-swapped images, point-selected profiles,
profile Navigate, 3D slit extraction and playback already exist. It also
checks real-data WCS autolinking with #2595, including the main-versus-WP1
wrapper difference. Use that audit and the active plan when deciding what
new implementation is actually needed; the refresh results below remain
valid but do not define the feature gaps.

## Useful entry points

| Package | Start here | Refresh and remaining limits |
| --- | --- | --- |
| WP0 upstream | [historical drafts](wp0/) | Use the PR heads in the active plan. Old diffs/bodies remain historical; do not reapply them. |
| WP1 coordinates/links | [copied package](wp1/glue_solar/), [link tests](wp1/glue_solar/tests/test_linking.py) | Refreshed with main's timestamps, tools, transparent NaN layers and fixtures. Autolink tests detect actual wrapped-WCS support; the inverse workaround is conditional on a behavior probe. Put this package first on the import path for dependent experiments. |
| WP2 moments | [module](chk_wp2/wp2_moments_module.py), [tests](chk_wp2/test_wp2_moments.py) | Numerical implementation retained; checks pass with the refreshed WP1 package. Physical validation and production actions remain. |
| WP3 sessions | [module](wp3_impl.py), [tests](wp3chk_test_sessions.py) | Explicit `install_browser_factories()` enables file-referencing browser loads. Six cases pass, including twice-relocated inputs/re-saved sessions and real SJI/raster/stack WCS. Import the module to install WCS/Quantity/scoped-style support. Keep `wp3_impl` importable when restoring its sessions. |
| WP4 quicklook | [shared module](wp4_common.py) | Reuses current frame times, avoids duplicate `Time`, requires explicit slit decimation, validates nearest-time inputs, pairs quicklook observations by OBSID plus start, and disconnects closed viewers. Still image-slider synchronization only: no cursor follow/lock, profile coordination or time–wavelength panel. |
| WP5 units/lines | [units](wp5_units.py), [artist](wp5_linelist_mod.py), [line list](iris_lines.csv), [session demo](wp5_ll_session.py) | Artist converts wavelengths to profile pixels in WCSAxes mode and follows slice/unit changes. Ascending/descending grids and synthetic sessions tested on released core and profile PR sources. Non-monotonic traces and out-of-range markers are omitted. Demo uses a temporary session and closes its windows. |
| WP5 blink | [tool](wp5_blink.py) | Import no longer launches a GUI demo or starts a process timeout. Close restores layer visibility and stops the timer. Still blinks separate layers, not two wavelength slices of one cube. Run the file explicitly for its demo. |
| WP6 fitting | [module](wp6_fitting.py), [brief variant](wp6_fitting_brief.py), [tests](wp6_test_fitting.py) | Numerical code retained; removed the deleted scratchpad path from tests. Fitting and both variants' WP3 product round trips pass. Source-mask/uncertainty handling and physical validation remain absent. |
| WP7 context | [module](wp7chk/context_chk.py), [tests](wp7chk/test_context.py) | Tests now import the actual prototype; shared `link_hpc` comes from WP1. GOES-only timeseries import is deferred until needed. Ten mocked-network checks pass with temporary timeseries dependencies. No real science download or exact datetime-label check was performed. |
| WP8 browser | [scanner](wp8_scan.py), [dialog](wp8_proto.py), [UI](wp8_loader.ui), [tests](wp8_test_proto.py) | Progress text now survives a prior load/busy state without resetting successful extraction from 100 to 0. Eight existing checks plus two text-regression variants pass. Directory enumeration and waiting for a current header read still limit cancellation. |
| Cross-package checks | [runner](review_20260905/run_checks.py), [integration](review_20260905/test_plan_integration.py), [refresh regressions](review_20260905/test_refresh.py), [line positions](review_20260905/test_line_positions.py) | Isolated processes, explicit source paths and focused assertions; not a full interactive CRISPEX application test. |

## Contracts and limits

- WP1 supplies `link_hpc`, which main does not yet export. WP4/WP7 require
  this copied package on their import path. Source PR imports can retain
  installed release metadata: use capabilities and source paths to identify them.
- WP4 `nearest()` requires nonempty, sorted, finite reference times and
  finite query times. Equal-distance ties choose the earlier sample; outside
  coverage still clamps to an endpoint. No gap tolerance or “no match”
  policy was invented. Direct `link_time()` callers must select matching
  inputs; `quicklook()` checks OBSID and observation start conservatively.
- `slit_x(cube, pixel_stride=10)` explicitly handles a known stride-10
  fixture. The default is 1; an off-image slit does not imply decimation.
  Old one-off WP4 probes may rely on the removed heuristic.
- The image-sync experiment still wraps `app.new_data_viewer`. Disconnecting
  closed viewers does not provide persistent, coordinated image/profile/point
  state or resolve time-dependent geometry and scan-0 stack-WCS limitations.
- WP3 and WP5 install process-local patches/registries. Do not import every
  prototype into one application or interpret a patched process as main.
  Existing sessions naming historical factory/class paths are not migrated.
- WP6 clips negative samples and substitutes zero for NaNs before fitting;
  it does not use source masks or uncertainty weights. Passing numerical
  checks do not certify velocity calibration or a chosen line-profile model.
- Unselected `wp*chk*`, `chk*`, `cc_*`, `sv2_*`, `ulb_*`, `ver_sess*`, `v_*`
  and other probes remain historical. Some contain old paths, global patches,
  network calls or output files. Headers saying “shipping code”, old test
  totals and proposed production import paths are not current status.

## Validation 2026-09-23

Baseline: solar main `236f0a8`, glue-core 1.27.0, editable Qt #74
`6b579814eb7c`, irispy 0.8.1, Astropy 8.0.1, NumPy 2.5.2,
Matplotlib 3.11.1, ndcube 2.4.1, Python 3.14.7, pytest 9.1.1.
CI status is excluded. No full eleven-PR combination, native macOS GUI,
large-data latency/memory benchmark or physical-equivalence check was run.

| Configuration and focused check | Result |
| --- | --- |
| WP1 copied package: linking plus refreshed plugin/readout tests, released core | 18 passed, 3 skipped (two autolink checks need upstream support; solar cursor is superseded by Qt #74) |
| WP1 linking on core #2595 source | 11 passed, no autolink skip |
| WP2 moments + WP6 fitting + four integration checks, WP1 package | 17 passed |
| Refresh helpers/blink + numeric line positions/session + WP3 real sessions, WP1 package | 15 passed |
| Line positions/session on core #2601 + Qt #70 sources | 3 passed |
| WP7 context with WP1 and temporary timeseries dependencies | 10 passed; network mocked |
| WP8 existing behavior + progress-text regression, current solar main | 10 passed |
| Temporary smoke check of the refreshed line-session demo on the profile PRs | 1 passed |

Static checks parsed all 168 Python files (including the archived originals)
and resolved 69 local links/anchors across the active plan and this index.
All 252 original artifacts remain byte-identical either at their original
path or in the refresh archive; 17 original source files were refreshed.

The progress-text regression failed before the fix. An initial unconditional
reset also broke the extraction-at-100 check; the final fix only repairs an
invalid progress value, and both behaviors pass. Test counts above describe
separate configurations and overlap; they are not one full-suite total.

For WP7, `cdflib==1.3.12` and `h5netcdf==1.8.1` were installed with `--no-deps`
under `/tmp/iris-plan-validation-20260922/timeseries-deps`, using existing
h5py and other dependencies. No project dependency declaration or environment
was modified. A production port needs `sunpy[map,net,timeseries]`.
pytest-doctestplus/pytest-mpl remain absent; routine unknown-config warnings
were emitted. No docs/doctest or image-comparison coverage is claimed.

### Reproduce selected checks

Run from the repository root. Each invocation starts a fresh process;
WP8 uses main, while WP1-dependent checks use the copied package.

```sh
iris_root="$PWD"
iris_protos="$iris_root/IRIS_PLAN_PROTOTYPES"
iris_runner="$iris_protos/review_20260905/run_checks.py"

.venv/bin/python -B "$iris_runner" "$iris_protos/wp1" \
  "$iris_protos/wp1/glue_solar/tests/test_linking.py" \
  "$iris_protos/wp1/glue_solar/tests/test_plugin.py"

.venv/bin/python -B "$iris_runner" "$iris_protos/wp1:$iris_protos:$iris_protos/chk_wp2" \
  "$iris_protos/chk_wp2/test_wp2_moments.py" "$iris_protos/wp6_test_fitting.py" \
  "$iris_protos/review_20260905/test_plan_integration.py" -p glue_solar.conftest

.venv/bin/python -B "$iris_runner" "$iris_protos/wp1:$iris_protos" \
  "$iris_protos/review_20260905/test_refresh.py" \
  "$iris_protos/review_20260905/test_line_positions.py" \
  "$iris_protos/wp3chk_test_sessions.py" -p glue_solar.conftest

# Requires the SunPy timeseries dependencies; omit the temporary path if installed normally.
.venv/bin/python -B "$iris_runner" \
  "$iris_protos/wp1:$iris_protos/wp7chk:/tmp/iris-plan-validation-20260922/timeseries-deps" \
  "$iris_protos/wp7chk/test_context.py" -p glue_solar.conftest

.venv/bin/python -B "$iris_runner" "$iris_root:$iris_protos" \
  "$iris_protos/wp8_test_proto.py" "$iris_protos/wp8_chk_test_text.py"
```

For the upstream variants, prepend exported source paths to the runner's
colon-separated path argument. Exports used for this validation:

- Core #2595: `c49aeb1af14a8504c8f75a42d3a36883be5e9776`.
- Core #2601 (includes slice support): `acaf4e1c0ef88d513aecc158f81c8b9dcef9c28b`.
- Qt #70: `f1471b7ad843b453bf0c8f4e92e743cce04c6e7d`.

These disposable exports are under `/tmp/iris-plan-validation-20260922/`
as `core-ape14`, `core-profile`, `qt-profile`. No checkout switch is needed.
Run `test_linking.py` with the first, and `test_line_positions.py` with the
latter two. Do not combine upstream core/Qt repository suites into one
pytest invocation: their conftests register the same command-line option.

## Historical evidence

[Validation 2026-09-22](archive/2026-09-23-prototype-refresh/README.before-refresh.md#validation-2026-09-22)
records the original failing imports, session gaps and prior upstream tests.
It is superseded for the refreshed entry points, not deleted or rewritten.
[archive/2026-09-05/](archive/2026-09-05/) contains the original plans/audits;
[archive/2026-09-22/](archive/2026-09-22/) preserves the September 5 plan.
Other findings, session fixtures and logs remain at their existing paths.
