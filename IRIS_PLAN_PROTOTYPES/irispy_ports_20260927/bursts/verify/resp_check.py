import shutil, tempfile, pathlib, numpy as np
from astropy.time import Time
import irispy.utils.response as R
print(R.__file__)
V4 = "irispy_main/irispy/data/test/iris_sra_c_20161022.geny"
orig = R.ROOTDIR
def use(geny):
    if geny:
        d = pathlib.Path(tempfile.mkdtemp()); shutil.copy(geny, d / "iris_sra_c_20231106.geny"); R.ROOTDIR = d
    else:
        R.ROOTDIR = orig
def area_flat(t):
    r = R.get_latest_response(Time(t)); lam = r["LAMBDA"].to_value("nm")
    return r["AREA_SG"][0, np.argmin(np.abs(lam - 140.277))], r["VERSION"], lam[np.argmin(np.abs(lam - 140.277))]
def area_noflat(t):
    # IDL pre-v9: linear interpolation between C_F_LAMBDA[1:3] of fit_iris_xput at t
    r = R.get_latest_response(Time(t))
    lam = r["LAMBDA"].to_value("nm"); lg = lam[np.argmin(np.abs(lam - 140.277))]
    rr = [R._fit_xput_lite([Time(t)], r["C_F_TIME"], r["COEFFS_FUV"][j])[0] for j in range(3)]
    cf = r["C_F_LAMBDA"].to_value("nm")
    return np.interp(lg, cf[1:3], rr[1:3])
for g in (None, V4):
    use(g)
    for d in ("2015-05-02T02:34:47", "2013-09-02T16:39:35", "2021-04-29T11:09:08"):
        a, v, lg = area_flat(d); a0, _, _ = area_flat("2013-10-22T21:00")
        b = area_noflat(d); b0 = area_noflat("2013-10-22T21:00")
        print(f"v{v} {d} grid={lg:.4f} flattened ratio {a/a0:.4f} thr(ybin2) {1000*a/a0:.1f} | unflattened ratio {b/b0:.4f} thr(ybin2) {1000*b/b0:.1f}")
