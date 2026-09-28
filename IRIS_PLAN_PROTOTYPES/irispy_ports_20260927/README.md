# irispy feature ports: feasibility, 2026-09-27

Five irispy features that the plan cites (`wp0-irispy-requests`, `wp2-m3-mg-features`,
`wp2-burst-detection`), plus the reference harness three of them need. A workflow researched each
one against irispy main 49d705c and the SolarSoft sources. A second agent then re-checked each report
and corrected it. `feasibility.json` holds both, verbatim (`reports`, `verdicts`). `verdicts[i]` checks
`reports[i]`, except that `verdicts[2]` (SOT/ITN32) checks `reports[3]` and `verdicts[3]` (Mg II) checks
`reports[2]`; the verdicts carry no feature name. The `research/`
and `verify/` folders hold their scripts and prototypes. These are working notes with paths rewritten
to `~` and `<scratch>`, not runnable as they are.

The user asked for this; nothing here is filed or opened upstream. Work targets irispy `main` only;
ignore the gWCS raster branches.

| Feature | SolarSoft reference | Verified effort | Plan first | Prototype |
| --- | --- | --- | --- | --- |
| Load Hinode/SOT cubes in the IRIS SJI format (ITN32) | `iris_time2files.pro`; [ITN 32](https://iris.lmsal.com/itn32/read_browse.html) | M, 2–3 days | No | `itn32-sot/research/sot_prototype.diff` (+37/−7 in 4 files) |
| Uncertainty propagation in `calculate_moments` | `iris_moment__moment.pro`, `eis_moment__moment.pro`, `iris_getwindata.pro` | M, 2–4 days | No | `moments-uncertainty/research/mc_moments.py` (Monte Carlo check) |
| Per-exposure wavelength-drift correction | [`iris_prep_wavecorr_l2.pro`](https://sohoftp.nascom.nasa.gov/solarsoft/iris/idl/lmsal/calibration/iris_prep_wavecorr_l2.pro) with `silent_gaussfit.pro`, `iris_mp_sinechisq.pro` | M, 5–8 days (2–3 for the measurement only) | Shared plan | `wavecorr/research/proto_wavecorr.py` |
| UV burst detection, Si IV spectra and SJI 1400 | [`iris_burst_check.pro`](https://sohoftp.nascom.nasa.gov/solarsoft/iris/idl/nrl/iris_burst_check.pro), [`iris_sji_burst_check.pro`](https://sohoftp.nascom.nasa.gov/solarsoft/iris/idl/nrl/iris_sji_burst_check.pro) | M, 5–7 days | Shared plan | `bursts/research/proto.py`, `bursts/verify/idlfaithful.py` |
| Mg II k/h features | [`iris_get_mg_features_lev2.pro`](https://sohoftp.nascom.nasa.gov/solarsoft/iris/idl/uio/utils/iris_get_mg_features_lev2.pro), `iris_get_mg_features.pro` | L, 7–12 days with IDL parity; M, 5–7 without | Yes | `mg-features/research/mg_features_proto.py`, `mg-features/verify/q/` |
| Reference harness (GDL, then one IDL run) | — | L, 5–8 days, plus the external IDL run | Yes | `../idl_reference/` |

Scale: S ≤ 1 day, M ≤ 1 week, L ≤ 3 weeks. Total about 26–42 working days.

## What the shared plan must settle (about a day; the verifier says more than the report's half day)

The wavelength-drift, burst and Mg II ports share their test crops, reference outputs and tolerance
rules, so decide once:

- **Parity policy.** Reproduce IDL's quirks or fix them and document the difference. Known quirks:
  - Mg II: when `lcc` has no non-finite value, `lcc[where(~finite(lcc))] = 0` zeroes the last slit pixel
    in IDL 8 and errors in IDL 7.1. It never fires on full real slits, but it does on clean crops and
    synthetic tests.
  - Mg II: `SPLINE` is called with a decreasing `T` and sigma 0.
  - Mg II: `/onlyk` uses 279.644 nm, a 9.55 km/s shift from the vacuum k rest; ask T. Pereira whether it is intentional.
  - Wavelength drift: NaN steps stay in the "good" set, and MPFIT can then return a silently wrong curve.
  - Bursts: the threshold scales with spectral summing; the SJI groups are bytes and wrap at 256.
- **Negative-step rasters.** `iris_data::getvar` reverses them on purpose. But `iris_prep_wavecorr_l2`
  then pairs the flipped data with unflipped times, and `iris_get_mg_features_lev2` descales them twice,
  so they cannot be parity data.
- **Tolerances.** Use absolute values in physical units (Å, km/s, pixels allowed to flip in a mask), not relative ones.
- **Test data.** Decide which crops go into `irispy/data/test` and their size budget, and whether remote-data tests may download large files (the Tian 2015 burst raster is 309 MB).
- **Output APIs:**
  - Wavelength drift: a per-step QTable and a separate apply function.
  - Mg II: a RasterCollection of named 2-D maps.
  - Bursts: an integer label cube plus an events QTable.
  - Moments: `StdDevUncertainty` attached to the existing maps.

## Per feature, what the verifiers added

- **SOT/ITN32:**
  - `read_files` keys cubes by `TDESC1`. The NFI Stokes I and V, and the MG cube of one OBS, would silently overwrite each other.
  - `SJIMeta` failed on these headers; irispy #180 fixes the metadata part.
  - The IRIS-only extra coordinates (`pztx`, slit positions) are all zero for SOT.
  - Shrunken fixtures must keep HDU 2.
  - SP cubes are not covered by ITN 32.
- **Moments uncertainty:**
  - Base the work on current main, after #179.
  - The raster reader computed uncertainty from memmap data; fixed in irispy #181.
  - Handle the `NDUncertainty` type and unit.
  - The "IDL cross-check" in the research report was circular: no independent reference exists.
  - The passing Monte Carlo output is `verify/mc_out_rerun.txt`. `research/mc_out.txt` comes from an
    earlier script and ends in an AssertionError.
- **Wavelength drift:**
  - The prototype's outlier cut differs from IDL's.
  - Memmap column reads page in the whole window, so they are not cheaper.
  - The routine fails on limb data: on 3400109360 the Ni I slit mean is below the 5 DN threshold.
  - The Level 2 auxiliary columns `POFFXNUV`/`POFFXFUV` show what the pipeline already corrected.
- **Bursts:**
  - The 3893012099 window named Si IV 1394 does contain 1402.77 Å.
  - Handle zero-exposure steps (all -200) and memmap SJIs.
  - The gallery sample data does not show the feature: the spectral detector finds 0 bursts on the
    sample raster, and the SJI 10σ rule flags all 20 sample SJI frames (135 events).
- **Mg II:** the prototype copies the `WHERE(-1)` error, and its synthetic accuracy numbers describe the corrected algorithm, not IDL's.
- **Harness:**
  - GDL's `CURVEFIT` is a wrapper around SSW's MPFIT.
  - GDL's `SPLINE` ignores the tension argument; a faithful version is in `../idl_reference/gdl/harness_verified_spline/`.
  - MacPorts has GDL 1.1.3.
  - The response file is picked as "latest", so pin it.

## Reference outputs

`../idl_reference/` holds the run package for one real-IDL run (`iris_ref_run.pro`, `README.md`). The
same drivers ran under GDL (`../idl_reference/gdl/`): all 8 tasks passed in about 15 minutes,
which needed four GDL patches. The user offered to run it in IDL on 2026-09-28. Compare that run
with the GDL outputs before treating GDL as a stand-in.
