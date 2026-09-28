import shutil, tempfile, pathlib, numpy as np
from astropy.time import Time
import irispy.utils.response as R
def ratio(date, geny=None):
    if geny:
        d = pathlib.Path(tempfile.mkdtemp()); shutil.copy(geny, d / "iris_sra_c_20231106.geny"); R.ROOTDIR = d
    a = []
    for t in (date, "2013-10-22T21:00"):
        r = R.get_latest_response(Time(t)); lam = r["LAMBDA"].to_value("nm")
        a.append(r["AREA_SG"][0, np.argmin(np.abs(lam - 140.277))].value)
    return a[0] / a[1], r["VERSION"]
for g in (None, "irispy_main/irispy/data/test/iris_sra_c_20161022.geny"):
    rr, v = ratio("2015-05-02T02:34:47", g)
    print(f"version {v}: ratio {rr:.4f} -> threshold(ybin=2) {1000*rr:.1f} DN/s  (Young's page: 465.1)")
