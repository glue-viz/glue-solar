"""Compare irispy.utils.wavelength_drift with the IDL reference run."""
import glob
import time

import numpy as np
from scipy.io import readsav

import irispy
from irispy.io.spectrograph import read_spectrograph_lvl2
from irispy.utils import wavelength_drift as W

IDL = "~/Git/irispy/iris_ref_out/iris_ref_out/"
FILES = {
    "4000005156": glob.glob("~/DATA/IRIS/*4000005156_raster/*r00000.fits")[0],
    "3824262996": glob.glob("~/DATA/IRIS/*3824262996_raster/*r00000.fits")[0],
}
print("irispy from", irispy.__file__)
for obs, f in FILES.items():
    r = readsav(IDL + f"wavecorr_{obs}_r00000.sav").r[0]
    rc = read_spectrograph_lvl2(f)
    t = time.perf_counter()
    table = W.calculate_wavelength_drift(rc)
    print(f"== {obs}: {time.perf_counter() - t:.2f} s (IDL {readsav(IDL + f'wavecorr_{obs}_r00000.sav')['seconds']:.2f} s), {len(table)} rows")
    for j, name in enumerate(W._LINES):
        ours, idl = table[name].value, r.corrs[j, :, 0]
        both = np.isfinite(ours) & np.isfinite(idl)
        d = np.abs(ours - idl)[both]
        mis = np.flatnonzero(np.isfinite(ours) != np.isfinite(idl))
        print(f"  {name:6s} finite ours {np.isfinite(ours).sum():4d} IDL {np.isfinite(idl).sum():4d} | |d| med {np.median(d):.2e} p99 {np.percentile(d, 99):.2e} max {d.max():.2e} | NaN mismatch {mis.tolist()[:6]} ours {ours[mis][:3]} IDL {idl[mis][:3]}")
    for k in ["nuv", "fuv"]:
        idl = getattr(r, f"corr_{k}")
        print(f"  {k}: max|ours - IDL| {np.abs(table[k].value - idl).max():.2e}  ours range [{table[k].value.min():.4f}, {table[k].value.max():.4f}]  IDL [{idl.min():.4f}, {idl.max():.4f}]")
    # the fit stage alone, on IDL's own shifts
    seconds = r.corr_tai - r.corr_tai[0]
    for k, j, cut in [("nuv", 0, 0.08), ("fuv", 3, 0.05)]:
        idl_curve = getattr(r, f"corr_{k}")
        fit = W._fit_drift(seconds, r.corrs[j, :, 0], cut, k)
        print(f"  fit stage on IDL shifts, {k}: max|d| {np.abs(fit - idl_curve).max():.2e}")
