import sys, importlib.util
import numpy as np
from astropy.io import fits
def load(path):
    spec = importlib.util.spec_from_file_location("m"+str(abs(hash(path))), path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
A = load('../mg-features/mg_features_proto.py'); B = load('q/mg_features_proto.py')
RASTER = "~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits"
with fits.open(RASTER, memmap=True, do_not_scale_image_data=True) as h:
    hdr = h[8].header
    raws = {s: np.asarray(h[8].section[s]) for s in (0, 100, 160, 200, 300, 399)}
wave_nm = (hdr["CRVAL1"] + (np.arange(hdr["NAXIS1"]) + 1 - hdr["CRPIX1"]) * hdr["CDELT1"]) / 10
for s, raw in raws.items():
    d = (raw * hdr["BSCALE"] + hdr["BZERO"]).astype(np.float32)
    a = A.get_mg_features(d, wave_nm); b = B.get_mg_features(d, wave_nm)
    for line in 'kh':
        lca = a[line][0][:,0]; lcb = b[line][0][:,0]
        ch = ~((lca == lcb) | (np.isnan(lca) & np.isnan(lcb)))
        print(s, line, 'NaN in first-pass? n_nan_final', np.isnan(lca).sum(), 'pixels differing (elt0 vs last):', np.flatnonzero(ch)[:10], ch.sum())
