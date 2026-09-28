# Running the IRIS SolarSoft routines under GDL

GDL (GNU Data Language) runs `iris_prep_wavecorr_l2`, `iris_get_mg_features_lev2`,
`iris_burst_check` and `iris_sji_burst_check` on real Level 2 files. It needs SolarSoft and four
small patches. The outputs have not yet been checked against real IDL (see `../README.md`). Paths
in these files were rewritten to `~` and `<scratch>`; set them before running.

- **GDL:** GDL 1.1.3 from MacPorts (`gnudatalanguage`) or Ubuntu, or the macOS arm64 weekly
  `.dmg` from the GDL GitHub releases (used here: GDL v1.1.2-55-g7e299bbc). It is not on
  conda-forge, and Homebrew's `gdl` is a different project.
- **SolarSoft:** `sswgdl/setup.sh` downloads the swmaint tarballs `ssw_ssw_gen`, `ssw_ssw_iris`
  (including `iris/response`), `ssw_ssw_site` and `ssw_vobs_ontology`, about 510 MB, into a work
  directory. `sswgdl/sswgdl` is the launcher, following the
  [sswgdl](https://github.com/rbluosolar/sswgdl) README, which is only a recipe. SolarSoft is
  unversioned; `ssw_manifest_md5.txt` records the md5 of the 179 `.pro` files one run compiled.
- **Patches** (`sswgdl/patches/`, put first on `GDL_PATH`):
  - `mreadfits_header.pro`: GDL's `ON_IOERROR` misses a `READS` error.
  - `spline.pro`: GDL has no tension argument, so this is a natural cubic spline, not IDL's.
  - `strmatch.pro`: accepts a one-element array pattern.
  - `region_grow.pro`: GDL has none; built on `LABEL_REGION /all_neighbors`, tested by `test_region_grow.pro`.
- **Closer replacements from the verifier** (sensitivity probes, not certified):
  - `harness_verified_spline/`: a Cline tension spline (sigma clamped to 0.001, 3-point end slopes,
    always double precision). Its `spline.pro` sorts `T` first, so it does not model IDL's interval
    search on the decreasing `T` at `iris_get_mg_features.pro:339/354`; call `spline_core` directly
    for that.
  - `harness_verified_curvefit/`: `mpcurvefit` with IDL's CURVEFIT defaults (TOL 1e-3, ITMAX 20, no
    SIGMA). It is still MPFIT, not IDL's gradient expansion.

  Neither makes GDL output an IDL stand-in; the IDL run decides.
- **Drivers:** `../iris_ref_run.pro` itself runs under GDL and gives the outputs to compare with IDL.
  The 2026-09-27 run (all 8 tasks ok in about 15 min; Mg II on 3824262996 alone 13 min) is in
  `../gdl_out_20260927/`, whose `.sav` files are git-ignored and exist only on the Mac that ran it.
  To regenerate:
  1. Make copies of `sswgdl/setup.sh` and `sswgdl/sswgdl` with `<scratch>` replaced by a work
     directory `$W` outside the repositories.
  2. Run `sh setup.sh`.
  3. Put `sswgdl/sswgdl` (made executable), `sswgdl/patches/` and the data tree from
     `../make_sji_tree.sh` in `$W`.
  4. From the `idl_reference` directory, pipe
     `.run iris_ref_run` and `iris_ref_run, data_dir='<abs path of ~/DATA/IRIS>', out_dir='out', iris_data='<tree>'`
     into `SSWGDL_PATCHES=$W/patches $W/sswgdl`.

     Use an absolute data path: the launcher sets `HOME` to `$W/home`, so `~` does not reach your data.
- **Older runs:** `sswgdl/pro/run_*.pro` are the first 5-task runs, on 4000005156 scan 0 and the
  4000255147 SJI. They have no probes and nothing on 3824262996. `harness/` holds the first probe's
  drivers, which read the full 3602506433 files r00000-r00003, and its helpers `list_deps.pro` and
  `which_impl.pro`.
- **SJI bursts:** `iris_sji_burst_check` takes a date, so it needs an
  `$IRIS_DATA/level2/YYYY/MM/DD/<obs>/` tree (`../make_sji_tree.sh`).
