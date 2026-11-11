# WCSLIB -TAB inverse: email to Mark Calabretta

The user's email to WCSLIB's author about the slow, and for sit-and-stare rasters ambiguous, -TAB inverse (`tabs2x()` in `tab.c`) on the 2-D coordinate tables irispy builds for IRIS spectrograph rasters (performance finding R8, plan item `wp0-wcslib-tab-inverse`, D54, D97). Written fresh on Linux on 2026-10-29; the earlier Mac draft was not seen. Nothing has been sent. The email has no address: the user fills it in.

## Files

- `email.md`: subject and plain-text body (497 words plus a 4-line table), to send with the two attachments below.
- `tab_inverse_repro.py`: the attachment. numpy and astropy only, no data. It builds two 1600-exposure WCSes laid out as irispy's `_create_tabular_wcs` does (WAVE linear; HPLT-TAB and HPLN-TAB from one `COORDS` array of shape (exposure, slit end, lat/lon) in degrees; K1 = 2 with index vector `SPATIAL`, K2 = 1600 without one; `CRPIX3 = CRVAL3 = CDELT3 = 1`; PC the identity). (a) is a sit-and-stare: 0.05" every 6 exposures plus 0.001" white jitter. (b) is a scan: 0.35" steps plus 0.003" jitter. The slit is tilted by 0.0112 (IRIS's `PC3_2`, 0.64 deg). For each it times the forward and the inverse on random pixels inside the table (all at once, and the first 200 one at a time for the spread) and on a 60x60 lon/lat grid over the footprint and 5" around it. It also prints the round-trip errors and versions.
- `tab_inverse_repro.out`: its output, the second attachment.
- `real_iris.out`: the same `report()` on real rasters through the WCS that irispy f058705 builds.
- `probes/`: the scripts behind the email's other claims, each with its `.out` file:
  - `scale.py`: cost against table length (scan) and against jitter (sit-and-stare), and the sit-and-stare without the tilt.
  - `tilt.py`: one-cell table and sit-and-stare against the tilt.
  - `spread.py`: per-point spread.
  - `pointing.py` and `pointing2.py`: which local rasters are sit-and-stares, and their pointing, `PC3_2` and slit size.
  - `real.py`: makes `real_iris.out`.

## How to run

```
python -I -B tab_inverse_repro.py [n_points]           # about 12 s; default 1000 points per case
python -I -B probes/real.py DIR FILE,n,grid,rows ...   # DIR holds tab_inverse_repro.py; rows > 0 also rebuilds the WCS from the first `rows` exposures with irispy's _create_tabular_wcs
python -I -B probes/scale.py DIR                       # likewise tilt.py, spread.py; pointing*.py take raster files
```

The outputs here came from `/home/nabil/.local/share/mamba/envs/iris-plan-latest-1028/bin/python -I -B`, under `systemd-run --user --scope -q -p MemoryMax=24G -p MemorySwapMax=0 --`, on an AMD Ryzen 9 9950X with Fedora Linux. Each ran in the foreground, one at a time. Versions: Python 3.13.16, numpy 2.5.4, astropy 8.0.2, bundled WCSLIB 8.6, irispy 0.9.1.post2.dev223+gf0587057b.

## WCSLIB versions and code

- astropy 8.0.0, 8.0.1 and 8.0.2 bundle WCSLIB 8.6 (2026/03/30): from `cextern/wcslib/CHANGES` at each tag. At runtime, `astropy.wcs.wcs.WCSLIB_VERSION` is `8.6`, statically built in.
- astropy main (d3ad3b6, 2026-10-29) bundles WCSLIB 8.10 (2026/09/27), since 2bf66da (2026-09-28). No astropy release has 8.7 or later yet.
- In tab.c at 8.10 (8.6 in brackets):
  - `tabs2x()` 1307 (1279). The row loop is at 1356 (1323). The first `tabvox()` success breaks out at 1407 (1374). Extrapolation for M > 1 is `>>> TBD <<<` at 1451 (1418).
  - `tabedge()` 1521 (1488).
  - `tabrow()` 1572 (1539).
  - `tabvox()` 1661 (1628). Its recursion stops at `level == 31`, 1753 (1720).
- `diff` of `tabs2x()` through the end of the file, 8.6 against 8.10: an `M < 1` guard, two casts and an `int` to `ptrdiff_t` offset, all from 8.7's static-analysis pass. CHANGES 8.7-8.10 has no -TAB entry beyond `tabini()`'s size check (8.7, 8.8). So the inverse's algorithm has not changed since the version measured.

## Measured (2026-10-29, Linux, WCSLIB 8.6), with 2026-10-09 (Mac, R8) for comparison

```
                                        2026-10-29 synthetic   2026-10-29 real (irispy's WCS)            2026-10-09 real (Mac)
sit-and-stare, random points, mean      7.8 ms (1600 exp.)     11.5 ms 4204700143 first 1600 exp.;       6154 us 4000255147 (1600 exp.)
                                                               12.6 ms all 9495
  median / max (one at a time)          0.43 / 120 ms          4.7 / 166 ms (first 1600); 0.98 / 722 ms (9495)
grid inside the footprint               0.56 ms                0.96 ms (first 1600); 1.36 ms (9495)      176 us (SJI 1400 screen grid)
grid outside                            83 us                  88 us (first 1600); 491 us (9495)         25.5 us
round trip, exposure off by up to       5.03 (64% > 0.01,      25.9 / 26.7 (62% / 61% > 0.01,            ~6 (55% > 0.01)
                                        all earlier)           all earlier)
pixel maps back to its world point      4.0e-7"                3.8e-7"
scan, random points                     41.9 us (1600 x 0.35") 35.9 us 3400606077 (320 x 0.35")          29.7 us 3824262996 (400); 7.6 us 4000005156 (64 x 2")
scan, grid inside / outside             42.2 / 22.0 us         36.0 / 6.6 us
forward                                 0.024-0.028 us         0.022-0.025 us                            0.02-0.04 us
```

From `probes/`:

- Scan against table length (`scale.out`): 28.7 us for 2 exposures, 42.4 for 1600, 71.6 for 6400. That is about 29 us for the one-cell solve plus about 7 ns a row.
- Tilt (`tilt.out`), one 0.35" cell: 5.0 us at tilt 0, 29.2 us at 0.0112, 97.3 us at 0.05. The 1600-exposure sit-and-stare: 15 us, 4.3 ms and 22.7 ms. The slit's tilt drives the sit-and-stare cost.
- Jitter (`scale.out`), sit-and-stare: 0.41 ms with no jitter (degenerate cells), 49 ms at 0.0001", 16 ms at 0.0003", 4.1 ms at 0.001", 3.0 ms at 0.003". Thinner cells are slower. Means over 300 points, so noisy given the tail.
- In every run, the off-by-more-than-0.01 round trips all land on an earlier exposure ("first match wins").

The 2026-10-09 numbers are performance finding R8's, whose outputs are not kept. They were taken on Apple Silicon with astropy 8.0.x (WCSLIB 8.6 in every 8.0 release) and irispy 3352413, on other observations, so they compare in kind, not digit for digit.

## Not verified

- WCSLIB 8.10 was not run: no astropy release bundles it, and no code from a cloned repository was run. The claim that the numbers carry over rests on the `tab.c` diff above.
- The mechanism is inferred from reading `tabvox()` and from the black-box tilt and jitter probes. `tab.c` was not instrumented or built. The mechanism: a tilted, thin cell's bounding box admits the point, and rejecting the cell takes many levels of subdivision. The email says "seems to".
- R8's sit-and-stare, 4000255147, and its SJI are not on this machine. The real sit-and-stare here is 4204700143: High-Cadence Flare Program, STEPS_AV 0, 9495 exposures, a 204-pixel slit, 0.025-0.05" jumps every 10-30 exposures. The SJI screen path (R8's 13.2 s per quicklook SJI panel) was not re-measured. The lon/lat grid stands in for it.
- The synthetic sit-and-stare uses white jitter of 0.001". Real pointing drifts smoothly (median step 0.0003" in 4204700143, 0.0001" in 4000255147). 0.001" was chosen because its cost is close to the real tables', and the cost depends strongly on it (see the jitter probe).
- Per-point means have a long tail (99th percentile 50-150 ms), so they shift with the point sample: 2.7 ms for 50 points against 7.8 ms for 1000 on the same table.
- The one-at-a-time timings include 5-20 us of Python and astropy overhead per call. That is why the scan's median (61 us) is above its mean (42 us).
- `probes/real.py` uses irispy's private `_create_tabular_wcs` for the 1600-exposure slice, with the aux table cut to its first 1600 rows.
- Mark Calabretta's views and current address: unknown. The email asks rather than assumes.
