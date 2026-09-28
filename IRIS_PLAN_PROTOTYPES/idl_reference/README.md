# IDL reference run for the irispy ports

These scripts produce reference outputs from four IRIS SolarSoft routines, so the Python ports in
irispy can be tested against real IDL:

- `iris_prep_wavecorr_l2`: wavelength-drift correction
- `iris_get_mg_features_lev2`: Mg II k/h features
- `iris_burst_check`: UV bursts in Si IV spectra
- `iris_sji_burst_check`: UV bursts in SJI 1400

The same drivers already run under GDL, where four library routines needed local patches (see
"Why the probes" below, and `gdl/README.md` for the GDL setup). The IDL outputs both certify or
correct the GDL results and serve as the parity references. The feasibility of the ports is in
`../irispy_ports_20260927/README.md`.

## What you need

- IDL 8.x with SolarSoft, including the `gen` and `iris` packages and `vobs/ontology`
  (`read_iris_l2` calls `create_struct_temp`, which lives in `ontology`). For example,
  `setenv SSW_INSTR "gen iris ontology"` before starting `sswidl`.
- The three input files. On another machine, `sh fetch_data.sh iris_ref_data` downloads them from
  the LMSAL IRIS archive (about 1 GB, 1.9 GB unpacked), checks their MD5 against the copies the GDL
  run used, and unpacks the rasters:
  - `iris_l2_20130902_182935_4000005156_raster.tar.gz` (raster scan 0 is used)
  - `iris_l2_20140708_114109_3824262996_raster.tar.gz`
  - `iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz`

  On the Mac that has them in `~/DATA/IRIS`, use that as the data directory instead.

## Steps

From the directory holding these files:

1. If the data is not local, download it: `sh fetch_data.sh iris_ref_data`.

2. Build the directory layout `iris_sji_burst_check` expects (it takes a date, not a file):

   ```sh
   sh make_sji_tree.sh iris_ref_data iris_ref_tree
   ```

3. Run everything and keep the console output. Pipe the commands into IDL. `sswidl` (SolarSoft's
   csh script `ssw_idl`) splits its arguments on spaces and expands `*`, so
   `sswidl -e "iris_ref_run, ..."` fails before IDL starts.

   In csh or tcsh:

   ```csh
   printf ".run iris_ref_run\niris_ref_run, data_dir='iris_ref_data', out_dir='iris_ref_out', iris_data='iris_ref_tree'\nexit\n" | sswidl >& iris_ref_console.log
   ```

   In sh or bash, `sswidl` is not defined; pipe into `$SSW/gen/setup/ssw_idl > iris_ref_console.log 2>&1` instead.

   Or interactively: start `sswidl` here, type `.run iris_ref_run` and the same `iris_ref_run, ...`
   call, and save the console output.

   Under GDL the other tasks took 2–10 s, and the Mg II runs took 1.5 min (4000005156) and 13 min
   (the 400-step 3824262996), about 15 min in all. To leave the Mg II runs out, add `, skip='mg*'`
   inside the `iris_ref_run` call. If an input file is missing, only the tasks that need it fail,
   and `status.txt` says which.

4. Send back the whole `iris_ref_out` directory and `iris_ref_console.log`.

## Outputs

| File | Contents | Used for |
| --- | --- | --- |
| `probes.sav` | SPLINE, GAUSSFIT/SILENT_GAUSSFIT, TOTAL/STDEV/MEDIAN, WHERE(-1) and REGION_GROW on fixed inputs | Checking the GDL patches and the numerical behaviour the ports must match |
| `wavecorr_4000005156_r00000.sav`, `wavecorr_3824262996_r00000.sav` | The `iris_prep_wavecorr_l2` result structure `r` | Wavelength-drift port |
| `mg_features_4000005156_r00000.sav`, `mg_features_3824262996_r00000.sav` | `lc`, `rp`, `bp` and the window index | Mg II features port |
| `burst_4000005156_r00000.sav`, `burst_4000005156_r00000_thr40.sav` | Event structure (or 0 if none) and the threshold the routine used | Si IV burst port |
| `sji_burst_4000255147.txt` | Events per image: image index, number of events, pixels, then pixel index, group and intensity | SJI burst port (same format as the GDL run) |
| `status.txt` | IDL version, `SSW_IRIS`, `IRIS_DATA`, and ok/FAILED per task | Provenance |
| `compiled_sources.txt` | Every compiled routine with its source path, size and date | Which SSW version produced the numbers |
| `response_files.txt` | The `iris_sra_c_*` response files present (the burst threshold uses the latest) | Provenance |

Each task runs even if another fails. Please send the outputs anyway and the failure will show in
`status.txt`.

## Why the probes

Under GDL four library routines behave differently or are missing:

- `SPLINE` ignores its tension argument. The Mg II code calls it with sigma 0 on a decreasing `T`
  (`iris_get_mg_features.pro` lines 339 and 354), on an increasing `T` (403), and with sigma 1 (419).
- `REGION_GROW` does not exist; the burst checks call it on byte masks with `/all_neighbors`.
- `STRMATCH` rejects a one-element array pattern.
- `ON_IOERROR` does not catch a `READS` error in `mreadfits_header`.

`CURVEFIT` (under `GAUSSFIT`) is also a different implementation in GDL. The probes pin down IDL's
behaviour on small fixed inputs, so the GDL patches and the Python ports can be checked
independently of the data.
