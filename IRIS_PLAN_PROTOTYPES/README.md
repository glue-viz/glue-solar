# IRIS prototype index

Updated 2026-09-27. The [plan](../IRIS_GLUE_GAP_PLAN.md) owns requirements
and status, and its section "Prototypes: what to port" says what production
takes from each file. These are local experiments, not shipped features or a
package to copy over glue-solar.

On 2026-09-27, 186 historical probes, logs, diffs, WP0 PR drafts and review
reports moved to [archive/probes-2026-09/](archive/probes-2026-09/). Nothing
was deleted. The previous version of this index is
[archive/2026-09-27-restructure/README.md](archive/2026-09-27-restructure/README.md).

## Live files

| Area | Files | Role |
| --- | --- | --- |
| WP1 coordinates and links | [wp1/glue_solar/](wp1/glue_solar/) | Copy of the glue-solar package with the proposed `link_hpc`, axis names, Angstrom units and gated `glue_patches`. Port the delta, never the package (its `tests/test_importer.py` is stale) |
| WP2 moments | [chk_wp2/wp2_moments_module.py](chk_wp2/wp2_moments_module.py), [chk_wp2/test_wp2_moments.py](chk_wp2/test_wp2_moments.py), [wp2_moments_proto.py](wp2_moments_proto.py) | Moments layer action and tests; `wp2_moments_proto.py` holds two checks still to become tests |
| WP3 sessions | [wp3_impl.py](wp3_impl.py), [wp3chk_test_sessions.py](wp3chk_test_sessions.py) | WCS/-TAB, Quantity and scoped-style savers and browser factories; importing `wp3_impl` installs process-wide patches |
| WP4 quicklook | [wp4_common.py](wp4_common.py), [slit_check.py](slit_check.py) | Only `nearest`, `exposure_times`, `observation_key` and slit approach C are ported; the time links and sync wrapper are replaced (plan D8, D9) |
| WP5 spectral | [wp5_units.py](wp5_units.py), [wp5_override.py](wp5_override.py), [wp5_linelist_mod.py](wp5_linelist_mod.py), [iris_lines.csv](iris_lines.csv), [wp5_blink.py](wp5_blink.py), [wp5_label.py](wp5_label.py) | Velocity converter, rest override, line-list artist and data, blink skeleton, axis-label idea for an upstream PR |
| WP6 fits | [wp6_fitting.py](wp6_fitting.py), [wp6_test_fitting.py](wp6_test_fitting.py), [wp6_test_fitting_final.py](wp6_test_fitting_final.py), [wp6_fitting_brief.py](wp6_fitting_brief.py), `wp6_chk_real_fixed.{py,log}`, `wp6_full_raster.{py,log}` | Gaussian fit maps; the logs are 4-D stack and full-raster evidence. `wp6_fitting_brief.py` goes to the archive once `test_plan_integration.py` drops its parameter |
| WP7 context | [wp7chk/context_chk.py](wp7chk/context_chk.py), [wp7chk/test_context.py](wp7chk/test_context.py), [wp7chk/conftest.py](wp7chk/conftest.py), [wp0_bug_epoch_viewer.py](wp0_bug_epoch_viewer.py) | GOES/AIA context actions (network mocked); the epoch probe becomes the date-label test |
| WP8 browser | [wp8_scan.py](wp8_scan.py), [wp8_proto.py](wp8_proto.py), [wp8_loader.ui](wp8_loader.ui), [wp8_test_proto.py](wp8_test_proto.py), [wp8_test_shipped.py](wp8_test_shipped.py), [wp8_chk_test_text.py](wp8_chk_test_text.py), [wp8_chk_proto_fix.py](wp8_chk_proto_fix.py) | Filter, threaded stoppable scan and progress text; the Worker pattern also serves WP10's non-blocking load |
| Cross-package checks | [review_20260905/](review_20260905/) (`run_checks.py`, `qs_isolate.py`, integration/refresh/line-position tests), [review_20260923/](review_20260923/README.md) (existing-capability probes) | Runner and probes; the probe figures in review_20260923 are specific to the irispy 0.8.1 fixture |
| Review evidence | [review_20260927/](review_20260927/README.md) | Verified review, feasibility, prototype verdicts |

## Reproduce

Run from the glue-solar root in a micromamba environment (never `.venv`),
with `HOME` and QSettings isolated:

```sh
P="$PWD/IRIS_PLAN_PROTOTYPES"; R="$P/review_20260905"
run() { env HOME="$(mktemp -d)" PYTHONPATH="$R" "$PY" -B "$R/run_checks.py" "$1:$R" "${@:2}" -p qs_isolate; }

PY=~/mamba/envs/iris-plan-irispy081/bin/python
run "$P/wp1" "$P/wp1/glue_solar/tests/test_linking.py" "$P/wp1/glue_solar/tests/test_plugin.py"
run "$P/wp1:$P:$P/chk_wp2" "$P/chk_wp2/test_wp2_moments.py" "$P/wp6_test_fitting.py" "$R/test_plan_integration.py" -p glue_solar.conftest
run "$P/wp1:$P" "$R/test_refresh.py" "$R/test_line_positions.py" "$P/wp3chk_test_sessions.py" -p glue_solar.conftest
run "$P/wp1:$P/wp7chk" "$P/wp7chk/test_context.py" -p glue_solar.conftest
run "$PWD:$P" "$P/wp8_test_proto.py" "$P/wp8_chk_test_text.py" "$P/wp8_test_shipped.py"
run "$PWD" "$P/review_20260923/test_existing_workflows.py" -p glue_solar.conftest
```

Environments: `iris-plan` has released glue-core 1.27.0, glue-qt 0.4.2 and
irispy-lmsal 0.9.0. `iris-plan-irispy081` is the same with irispy-lmsal
0.8.1, which the prototypes were written against. Results on 2026-09-27:

| Check | irispy 0.8.1 | irispy 0.9.0 |
| --- | --- | --- |
| `glue_solar` on main | 34 passed, 1 skipped | 34 passed, 1 skipped |
| WP1 linking + plugin | 19 passed, 2 skipped | 9 passed, 1 failed, 2 skipped, 9 errors |
| WP2 + WP6 + integration | 17 passed | 11 passed, 3 failed, 3 errors |
| Refresh + line positions + WP3 sessions | 15 passed | 11 passed, 4 failed |
| WP7 context (network mocked) | 10 passed | 4 passed, 6 failed |
| WP8 browser | 12 passed | 12 passed |
| Existing-workflow probes | 7 passed, 2 skipped | 7 passed, 2 skipped |
| WCS probes, released core | 3 passed, 1 failed (needs #2595) | 3 errors, 1 failed |
| WCS probes, core #2601 + #2595 source | 4 passed (main and WP1) | errors (fixture names) |

The 0.9.0 failures come from the prototypes looking up bundled fixtures by
exact 0.8.1 names (0.9.0 renamed them to `*_test.fits`) and from values
measured on the old cropped windows (`wp1-links-4`, `wp2-wp6-science-17`).
Ported tests must use `glue_solar/conftest.py` `find_irispy_test_file` and
derive expected values from the fixture.

For upstream sources, prepend an export as an extra root. Exports are
disposable, and macOS cleanup purges `/tmp`. Regenerate one with
`git -C <repo> archive <head> | tar -x -C <dir>`, using the heads in the
plan. Drop roots that no longer exist, because an empty export directory
shadows the installed package.

## Contracts and limits

- WP3 and WP5 prototypes install process-wide patches or registries when
  imported. Do not import every prototype into one application, and do not
  mistake a patched process for `main`.
- `wp4_common.nearest` rejects unsorted references and clamps outside
  coverage. The plan replaces both behaviours (D7, D10).
- WP6 clips negative samples and replaces NaN with zero before fitting. The
  port removes this (`wp2-wp6-science-3`).
- Files in `archive/` keep their original relative links, some of which no
  longer resolve. They are historical records, not work lists.
