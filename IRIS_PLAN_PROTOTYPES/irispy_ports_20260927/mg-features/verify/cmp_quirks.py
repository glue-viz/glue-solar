import sys; sys.path.insert(0,'../mg-features'); sys.path.insert(0,'.')
import numpy as np
from astropy.io import fits
import mg_features_proto as P
from idl_spline import idl_spline

RASTER = "~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits"
steps = [int(s) for s in sys.argv[1:]] or [160, 180, 200, 220]
with fits.open(RASTER, memmap=True, do_not_scale_image_data=True) as h:
    hdr = h[8].header
    raws = [np.asarray(h[8].section[s]) for s in steps]
wave_nm = (hdr["CRVAL1"] + (np.arange(hdr["NAXIS1"]) + 1 - hdr["CRPIX1"]) * hdr["CDELT1"]) / 10

orig_refine = P._refine
def idl_refine(vel, spec, p, pp=45):
    nsp = spec.size - 1
    idg = int(np.argmin(np.abs(vel - p[0])))
    lo, hi = max(0, idg - 2), min(idg + 2, nsp)
    nvel = np.arange(pp) / (pp - 1.0) * (vel[lo] - vel[hi]) + vel[hi]
    lo, hi = max(0, idg - 3), min(idg + 3, nsp)
    if hi >= lo + 2:
        ns, _ = idl_spline(vel[lo:hi + 1], spec[lo:hi + 1], nvel, 0.0)
        k = int(np.argmax(ns))
        return nvel[k], ns[k]
    return tuple(p)

res = {}
for mode in ("proto", "idl_refine"):
    P._refine = orig_refine if mode == "proto" else idl_refine
    outs = []
    for raw in raws:
        data = (raw * hdr["BSCALE"] + hdr["BZERO"]).astype(np.float32)
        outs.append(P.get_mg_features(data, wave_nm))
    res[mode] = outs
fill = [((raw * hdr["BSCALE"] + hdr["BZERO"]) == -200).all(axis=1) for raw in raws]
for line in ("k", "h"):
    for j, name in ((1, "2v"), (2, "2r")):
        dv = np.concatenate([(a[line][j][:, 0] - b[line][j][:, 0])[~f] for a, b, f in zip(res["proto"], res["idl_refine"], fill)])
        di = np.concatenate([((a[line][j][:, 1] - b[line][j][:, 1]) / b[line][j][:, 1])[~f] for a, b, f in zip(res["proto"], res["idl_refine"], fill)])
        fin = np.isfinite(dv)
        print(f"{line}{name}: n={fin.sum()}  |dv|>1e-3: {np.mean(np.abs(dv[fin])>1e-3):.3f}  median|dv| {np.median(np.abs(dv[fin])):.4f}  p95 {np.percentile(np.abs(dv[fin]),95):.4f}  max {np.abs(dv[fin]).max():.3f} km/s;  |dI/I|>1e-4: {np.mean(np.abs(di[fin])>1e-4):.3f} max {np.abs(di[fin]).max():.2e}")
