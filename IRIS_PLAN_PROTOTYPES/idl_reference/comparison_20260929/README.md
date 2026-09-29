# IDL reference run: checks and irispy ports, 2026-09-29

The user ran `../iris_ref_run.pro` in IDL 9.2 (Linux, SolarSoft of 2026-09-28) and returned
`iris_ref_out/` and `iris_ref_console.log` in `~/Git/irispy/iris_ref_out/`. The copy of the runner
there has local edits (`compile_opt idl2`, tracebacks, `critical_paths.txt`) that do not change the
outputs. The IDL machine's `iris_get_response.pro` is not the SolarSoft one (11085 bytes, dated
2025-08-07); the burst thresholds still match GDL's. The paths in these scripts were rewritten to `~`
and the scripts expect the session's scratch layout, so they are records, not runnable as they are.

## IDL against GDL (`cmp_sav.py`)

All 8 tasks ran. Each output was compared with the GDL run in `../gdl_out_20260927/`:

- **Si IV bursts** (default and threshold 40): identical.
- **SJI bursts, 4000255147**: identical except one pixel in frame 69. The pixel is 2100.50 DN and
  the threshold is 2100.539 DN; GDL's single-precision STDEV includes it, and IDL correctly does not.
- **Probes:** the Gaussian parameters agree to single precision. GDL's `CURVEFIT` returns an
  unreduced chi-square (16× IDL's here) and status 1.
  - IDL's `SPLINE` on a decreasing T extrapolates one interval: up to −3.3 at tension 0 and 4.8e5 at
    tension 1.
  - Single-precision `SPLINE` at tension 0 is wrong between nodes (3.33 instead of 1.00).
  - `WHERE(-1)` as a subscript changes the last element.
- **Wavelength drift, 4000005156**: IDL's `corr_nuv` and `corr_fuv` are both exactly MPFIT's starting
  guess, 0.1 + 0.01 sin(2πt/5856 + 1) Å (to 2e-11). The NaN step stays in the fit and MPFIT fails
  without an error. GDL fits a real curve.
- **Wavelength drift, 3824262996**: the curves agree to 1.8 mÅ (NUV) and 0.2 mÅ (FUV).
- **Mg II**: the differences come from the decreasing-T `SPLINE` in the peak refinement.

So GDL can stand in for the burst routines only.

## irispy ports (draft PRs, branched from LM-SAL/irispy main 51c0ec2)

| PR | Branch / worktree | Function | Agreement with IDL | Speed vs IDL |
| --- | --- | --- | --- | --- |
| #197 | `uv-burst-detection`, `~/Git/irispy-bursts` | `irispy.utils.bursts.find_si_iv_bursts`, `find_sji_bursts` | Identical pixels and events: Si IV at threshold 40, SJI in all 400 frames | Si IV 0.03 s vs 0.7 s; SJI 400 frames in 0.85 s |
| #198 | `wavelength-drift`, `~/Git/irispy-wavecorr` | `irispy.utils.wavelength_drift.calculate_wavelength_drift` | Drift fit on IDL's shifts to 3e-9 Å; per-step shifts within 2 mÅ (IDL's CURVEFIT stops early; our chi-square is 4× lower for Ni I) | about 3× |
| #199 | `mg-features`, `~/Git/irispy-mg-features` | `irispy.utils.mg_features.calculate_mg_features` | k3/h3 to 1e-5 km/s (p99); peaks median 0.1 and p99 0.66 km/s (IDL's broken refinement) | about 7× |

The fixtures in irispy were made with `make_*_test_data.py`. The comparisons are in `cmp_*.py` and
`run_mg.py`, and the Mg II choices were settled with `ablate_mg.py`, `guess_mg.py` and `grid_mg.py`:

- IDL's zero-filled slit cleaning is kept.
- The tension-1 guess spline is kept; SciPy's cubic, PCHIP, Akima and linear interpolation all move
  0.5–1.1 % of k3 centres by more than 1 km/s.
- IDL's clamped grid spline is kept; a not-a-knot spline moves peaks near the grid edges.

Decisions (user, 2026-09-29):
- Fix IDL quirks and test with tolerances.
- Si IV threshold scaled by SUMSPTRF/2.
- Wavelength drift: measurement plus fit, no apply function.
- Draft PRs.
- No gallery examples.

Next, not started: glue-solar layer actions (`wp2-burst-detection`, `wp2-m3-mg-features`), once the
ports are merged and pinned and the D4 layer-action infrastructure (`wp2-m2-moment-maps`) exists.
