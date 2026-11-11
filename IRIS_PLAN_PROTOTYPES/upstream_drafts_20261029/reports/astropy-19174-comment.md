# astropy#19174: -TAB results corrupted by threads (comment)

- **Where:** a comment on astropy/astropy#19174 ("Thread-unsafe access to wcslib in astropy.wcs.WCS causes crashes and
  silent coordinate corruption under multithreading", open). Its last comments (2026-09-29): you said your case is
  -TAB, pllim asked whether #19819 is enough, and astrofrog asked whether problems remain on the developer version.
  This answers both with astropy's own test file.
- **Review rows:** others rows 1-3 (`wp0-astropy-19174`, REPORT now).
- **Reproducer:** `scripts/astropy_tab_threads.py`, run by `run.sh rel astropy_tab_threads.py`; outputs
  `out/astropy_tab_threads_rel_run{1,2,3}.txt` (astropy 8.0.2, WCSLIB 8.6).
- **Main not run:** building astropy main (e91800f) from the clone was refused twice by the session's permission
  classifier ("Code from External"): once with pip's build isolation and once without, using a venv in this folder.
  The check of this work was refused the same way. The comment therefore says it states main from its source only.
  Before posting, build main once (see the notes) and paste its output under the 8.0.2 block; then drop that
  sentence.

## Comment (paste)

Here is a reproducer for the -TAB case that needs no data beyond astropy's own test file. Eight threads share one
-TAB `WCS` and call `all_pix2world`, each with its own input array:

```python
import threading
import warnings

import numpy as np

import astropy
from astropy.io import fits
from astropy.utils.data import get_pkg_data_filename
from astropy.wcs import WCS, FITSFixedWarning, _wcs

warnings.simplefilter("ignore", FITSFixedWarning)
with fits.open(get_pkg_data_filename("data/tab-time-last-axis.fits", package="astropy.wcs.tests")) as hdul:
    tab = WCS(hdul[0].header, hdul)
tan = WCS(naxis=2)
tan.wcs.ctype = ["RA---TAN", "DEC--TAN"]
tan.wcs.crpix, tan.wcs.cdelt, tan.wcs.crval = [256, 256], [-0.066667, 0.066667], [0, 0]
print(f"astropy {astropy.__version__}, WCSLIB {_wcs.WCSLIB_VERSION}; -TAB file: {list(tab.wcs.ctype)}")


def run(wcs, pixel, nthreads, lock=None, shared=False):
    expected = wcs.all_pix2world(pixel.copy(), 0)
    wrong = []

    def work():
        mine = pixel if shared else pixel.copy()  # all_pix2world(array, 0) offsets its input in place
        for _ in range(300):
            if lock is None:
                world = wcs.all_pix2world(mine, 0)
            else:
                with lock:
                    world = wcs.all_pix2world(mine, 0)
            if not np.allclose(world, expected, rtol=0, atol=1e-9, equal_nan=True):
                wrong.append(np.nanmax(np.abs(world - expected)))

    threads = [threading.Thread(target=work) for _ in range(nthreads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    worst = f", worst difference {max(wrong):.3g}" if wrong else ""
    return f"{len(wrong)} of {300 * nthreads} calls wrong{worst}"


rng = np.random.default_rng(0)
for name, wcs in (("-TAB", tab), ("TAN", tan)):
    pixel = rng.random((2000, wcs.naxis)) * 10
    print(f"{name}, 1 thread: {run(wcs, pixel, 1)}")
    print(f"{name}, 8 threads: {run(wcs, pixel, 8)}")
    print(f"{name}, 8 threads with a lock: {run(wcs, pixel, 8, threading.Lock())}")

# Aside: all_pix2world(array, 0) adds 1 to the caller's array and subtracts it again, with the GIL released
pixel = rng.random((2000, 2)) * 10
before = pixel.copy()
tan.all_pix2world(pixel, 0)
print(f"TAN, one call: {np.count_nonzero(pixel != before)} of {pixel.size} input values changed (by rounding)")
print(f"TAN, 8 threads sharing one input array: {run(tan, pixel, 8, shared=True)}; "
      f"input values now off by up to {np.abs(pixel - before).max():.3g} pixels")
```

On astropy 8.0.2 (WCSLIB 8.6):

```
astropy 8.0.2, WCSLIB 8.6; -TAB file: ['RA---TAN', 'DEC--TAN', 'TIME-TAB']
-TAB, 1 thread: 0 of 300 calls wrong
-TAB, 8 threads: 1187 of 2400 calls wrong, worst difference 18.2
-TAB, 8 threads with a lock: 0 of 2400 calls wrong
TAN, 1 thread: 0 of 300 calls wrong
TAN, 8 threads: 0 of 2400 calls wrong
TAN, 8 threads with a lock: 0 of 2400 calls wrong
TAN, one call: 441 of 4000 input values changed (by rounding)
TAN, 8 threads sharing one input array: 2396 of 2400 calls wrong, worst difference 0.68; input values now off by up to 4 pixels
```

Two more runs gave 1207 and 1267 of 2400 wrong for -TAB. Only the time axis, the -TAB one, is wrong: by up to
19 s, on times from 0 to 10 s. Nothing crashes or warns.

So with #19819, TAN is clean on 8.0.2, but -TAB is not. The cause is in WCSLIB: `tabx2s` stores its interpolation indices in
the shared `tabprm` itself, in `tab->p0[m]` and `tab->delta[m]`, and reads them back a few lines later. `tabs2x` does
the same with `p0`. Two threads in one -TAB transform thus use each other's indices. This is so in 8.0.2 (WCSLIB 8.6,
`tab.c:1209-1210`) and on main (e91800f, WCSLIB 8.10, `cextern/wcslib/C/tab.c:1237-1247`, read back at `:1267-1272`;
`tabs2x` at `:1352`, `:1401`, `:1466`). On both, the wrapper runs the transform with the GIL released
(`astropy_wcs.c:285-293`). I have not built main, so this is from its source: besides WCSLIB 8.10, its wrapper has
changed since 8.0.2 (#19859, #19862 and others), but nothing in it locks around `wcsp2s` or `wcss2p`.

Possible fixes: per-call scratch space for `tabx2s` and `tabs2x` in WCSLIB, or, in astropy, a lock per `Wcsprm`
around the transforms of a WCS that has -TAB axes (`wcs.wcs.tab` not empty).

Separately, the last two lines of the output show that `all_pix2world(array, 0)` writes into the caller's array.
`Wcs_all_pix2world` takes the input with `PyArray_ContiguousFromAny`, which does not copy a C-contiguous float64
array, then adds 1 and subtracts 1 in place, with the GIL released (`preoffset_array` and `unoffset_array`,
`astropy_wcs.c:239, 286, 292`). One call changes about 11% of the values in their last bits. Threads that share one
input array race on it, which makes even TAN results wrong. That may be what some thread tests here still see. This
is #16244: #19859 (8.1.0) fixed it for `wcs_pix2world` only, and 8.0.2 does not have that fix. On main,
`Wcs_all_pix2world`, `Wcs_p4_pix2foc`, `Wcs_det2im` and `Wcs_pix2foc` still offset the caller's array in place
(`astropy_wcs.c:286/292`, `372/377`, `440/445`, `502/508`), as do `Sip_pix2foc`, `Sip_foc2pix` and `Wcsprm_mix`.

## Notes for the user (not to paste)

- **Correction to the review:** the review's 2371/2400 (8.0.2) and 2364-2388/2400 (main a64a40b) came from
  `runs/wcs_threads_check.py`, which shares one input array across the threads. They mix the -TAB race with the
  input-offset race. With an input array per thread, -TAB is wrong in 1187-1267 of 2400 on 8.0.2. The plan's "20
  unlocked runs give 0 crashes" retirement test (register row `_GlueWCS` `WCS_LOCK`) should become "0 wrong values in
  this script's -TAB, 8 threads line".
- The aside is a second bug (astropy's, not WCSLIB's): #16244 (closed), fixed by #19859 (merged 2026-07-15, milestone
  v8.1.0, not an ancestor of v8.0.2) for `wcs_pix2world` / `Wcsprm.p2s` only. The other sites were found by grepping
  `preoffset_array` in `astropy/wcs/src` on e91800f; the astropy_wcs.c lines are the same in v8.0.2. (The check named
  372/377 as `Wcs_pix2foc`; they are `Wcs_p4_pix2foc`, and `Wcs_pix2foc` is 502/508.) glue-solar hits it only where
  threads pass one shared array to one WCS. The `_LockedWCS` lock covers that case too.
- "#19859, #19862 and others": PRs on main's first-parent history touching `astropy/wcs/src` since the v8.0.x branch
  point and not in v8.0.2's log are #19859, #19862, #19971, #20223, #20492, #20495, #20675; #19720, #19774, #19819,
  #20418, #20422 and #20423 were backported to 8.0.x. The only lock in `astropy/wcs/src` on main is the
  `Py_BEGIN_CRITICAL_SECTION` in `Wcsprm_cset` (`wcslib_wrap.c:1982-1992`), around `wcsset`.
- To add a main run: build `clones/astropy` (e91800f) once permission allows (for example
  `venv/bin/python -m pip wheel --no-build-isolation --no-deps -w wheels clones/astropy`, with Cython and
  extension-helpers in `venv`) and unpack the wheel to a folder. Then put that folder in `P` of `run.sh`'s `main` case
  (`run.sh` runs `python -I`, which ignores PYTHONPATH, so it prepends to `sys.path`) and run
  `run.sh main astropy_tab_threads.py`. Paste its output under the 8.0.2 block.
