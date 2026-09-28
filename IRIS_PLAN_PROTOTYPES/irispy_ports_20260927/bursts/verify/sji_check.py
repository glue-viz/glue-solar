import sys, numpy as np
from astropy.io import fits
from scipy import ndimage
f = sys.argv[1]
with fits.open(f) as h:
    data = h[0].data; hd = h[0].header
    print(hd.get("NAXIS1"), hd.get("NAXIS2"), hd.get("NAXIS3"), hd.get("DATE_OBS"), hd.get("OBS_DESC"))
    tot_ev = frames = 0; edge = 0
    for i in range(data.shape[0]):
        img = data[i].astype(float)
        good = img != -200
        v = np.sort(img[good]); med = v[v.size // 2]; sig = v.std(ddof=1)
        m = img >= med + 10 * sig
        lab, n = ndimage.label(m, structure=np.ones((3, 3), bool))
        sz = np.bincount(lab.ravel()); keep = sz >= 2; keep[0] = False
        if keep.any(): frames += 1; tot_ev += int(keep.sum())
        border = np.zeros_like(m); border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
        edge += int((m & border).sum())
    print("frames", data.shape[0], "frames with events", frames, "events", tot_ev, "flagged edge pixels (IDL would hang/skip)", edge)
