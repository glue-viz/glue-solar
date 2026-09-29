"""Compare a Mg II features implementation with the IDL reference run, per feature."""
import glob
import sys
import time

import numpy as np
from scipy.io import readsav

from irispy.io.spectrograph import read_spectrograph_lvl2

IDL = "~/Git/irispy/iris_ref_out/iris_ref_out/"
FILES = {
    "4000005156": glob.glob("~/DATA/IRIS/*4000005156_raster/*r00000.fits")[0],
    "3824262996": glob.glob("~/DATA/IRIS/*3824262996_raster/*r00000.fits")[0],
}


def load(obs):
    cube = read_spectrograph_lvl2(FILES[obs], spectral_windows="Mg II k 2796")["Mg II k 2796"][0]
    wave = cube.axis_world_coords(cube.wavelength_axis)[0].to_value("nm")
    ref = readsav(IDL + f"mg_features_{obs}_r00000.sav")
    return cube, wave, ref


def compare(name, ours, idl, vel_tol=0.1):
    """ours/idl: (..., 2) arrays [velocity, intensity]."""
    a, b = ours[..., 0], idl[..., 0]
    fa, fb = np.isfinite(a), np.isfinite(b)
    both = fa & fb
    d = np.abs(a - b)[both]
    di = (np.abs(ours[..., 1] - idl[..., 1]) / np.abs(idl[..., 1]))[both]
    print(f"  {name}: finite ours {fa.sum()} IDL {fb.sum()} only-ours {(fa & ~fb).sum()} only-IDL {(fb & ~fa).sum()} | "
          f"|dv| p50 {np.median(d):.3g} p90 {np.percentile(d, 90):.3g} p99 {np.percentile(d, 99):.3g} max {d.max():.3g} >{vel_tol}: {(d > vel_tol).mean():.4f} | "
          f"rel dI p50 {np.median(di):.2g} p99 {np.percentile(di, 99):.2g}")


def run(obs, features, steps):
    cube, wave, ref = load(obs)
    t = time.perf_counter()
    out = features(cube, wave, steps)  # dict line -> (lc, bp, rp) each (nstep, ny, 2)
    print(f"== {obs} steps {steps[0]}..{steps[-1]} ({len(steps)}): {time.perf_counter() - t:.1f} s")
    for li, line in enumerate(["k", "h"]):
        lc, bp, rp = out[line]
        for fname, arr in zip(["lc", "bp", "rp"], [lc, bp, rp]):
            compare(f"{line} {fname}", arr, ref[fname][steps, :, :, li])
    return out
