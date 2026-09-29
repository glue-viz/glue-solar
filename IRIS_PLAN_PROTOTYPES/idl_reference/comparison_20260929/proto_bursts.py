"""Scratch: port numerics on irispy objects, compared against the IDL reference run."""
import time

import numpy as np
from astropy import units as u
from astropy.constants import c
from astropy.time import Time
from scipy import ndimage
from scipy.io import readsav

from irispy.io.sji import read_sji_lvl2
from irispy.io.spectrograph import read_spectrograph_lvl2
from irispy.utils.response import get_latest_response

IDL = "~/Git/irispy/iris_ref_out/iris_ref_out/"
RASTER = "~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits"
SJI = "~/DATA/IRIS/534d789bb0a2821fb2b78eb36d1d6753-iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz"
SI_IV = 1402.77 * u.AA
EIGHT = np.ones((3, 3), bool)


def area(t):
    r = get_latest_response(Time(t))
    lam = r["LAMBDA"].to_value(u.AA)
    return r["AREA_SG"][0, np.argmin(np.abs(lam - SI_IV.value))]


def si_iv(cube, threshold=None, vmax=50 * u.km / u.s, median_factor=10):
    wave = cube.axis_world_coords(cube.wavelength_axis)[0].to(u.AA)
    vel = ((wave - SI_IV) / SI_IV * c).to(u.km / u.s)
    k = np.flatnonzero(np.abs(vel) <= vmax)
    data = cube.data[..., k[0] : k[-1] + 1]
    missing = data < -10 if cube.mask is None else (data < -10) | cube.mask[..., k[0] : k[-1] + 1]
    n = (~missing).sum(-1)
    exptime = cube.meta["exposure time"].to_value(u.s)[:, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(missing, 0, data).sum(-1, dtype=float) / n / exptime
    if threshold is None:
        threshold = 500 * area(cube.meta.date_reference) / area("2013-10-22T21:00")
    thr = threshold * cube.meta.spatial_summing_factor * cube.meta.spectral_summing_factor / 2
    cand = mean >= thr
    # the median only for candidates: sort NaN-filled bins, take the middle of the valid ones
    sub = np.where(missing[cand], np.nan, data[cand])
    med = np.nanmedian(sub, axis=-1) / np.broadcast_to(exptime, mean.shape)[cand]
    hit = cand.copy()
    hit[cand] = mean[cand] < median_factor * med
    labels, ng = ndimage.label(hit, structure=EIGHT)
    return labels, ng, mean, thr, threshold


def sji_bursts(sji, sigma_factor=10, min_pixels=2):
    data = np.where(sji.mask, np.nan, sji.data) if sji.mask is not None else sji.data
    flat = data.reshape(len(data), -1)
    med = np.nanmedian(flat, axis=1)
    sig = np.nanstd(flat, axis=1, ddof=1, dtype=float)
    thr = (med + sigma_factor * sig)[:, None, None]
    with np.errstate(invalid="ignore"):
        hit = data >= thr
    structure = np.zeros((3, 3, 3), bool)
    structure[1] = True
    labels, _ = ndimage.label(hit, structure=structure)
    npix = np.bincount(labels.ravel())
    keep = npix >= min_pixels
    keep[0] = False
    labels = np.where(keep[labels], labels, 0)
    return labels, med, sig, thr


def check_si_iv():
    cube = read_spectrograph_lvl2(RASTER, spectral_windows="Si IV 1403")["Si IV 1403"][0]
    ref = readsav(IDL + "burst_4000005156_r00000_thr40.sav")
    t = time.perf_counter()
    labels, ng, mean, thr, threshold = si_iv(cube, threshold=80)  # SUMSPTRF=1: 80 * 1/2 == IDL 40
    print(f"si_iv {time.perf_counter() - t:.3f}s  thr {thr}  groups {ng}  pix {(labels > 0).sum()}")
    o = ref["output"]
    ours = set(zip(*np.nonzero(labels)))
    idl = set(zip(o["XPIX"].tolist(), o["YPIX"].tolist()))
    print("  pixel sets equal:", ours == idl, "only ours", ours - idl, "only IDL", idl - ours)
    d = [mean[x, y] - i for x, y, i in zip(o["XPIX"], o["YPIX"], o["INTENSITY"])]
    print("  max |intensity - IDL|", np.max(np.abs(d)), "rel", np.max(np.abs(d) / o["INTENSITY"]))
    ref0 = readsav(IDL + "burst_4000005156_r00000.sav")
    labels0, ng0, _, thr0, threshold0 = si_iv(cube)
    print("  default threshold ours", threshold0, "IDL", ref0["threshold"], "rel", threshold0 / ref0["threshold"] - 1, "groups", ng0, "eff thr", thr0)


def check_sji():
    t = time.perf_counter()
    sji = read_sji_lvl2(SJI)
    print(f"read sji {time.perf_counter() - t:.2f}s", sji.data.shape, sji.data.dtype)
    t = time.perf_counter()
    labels, med, sig, thr = sji_bursts(sji)
    print(f"sji_bursts {time.perf_counter() - t:.2f}s")
    # IDL text: header, seconds, then per frame "im nevents npix" + npix lines "index group int"
    lines = open(IDL + "sji_burst_4000255147.txt").read().split("\n")[2:]
    i, idl = 0, {}
    while i < len(lines) and lines[i].strip():
        im, nev, npix = map(int, lines[i].split())
        rows = np.array([lines[i + 1 + j].split() for j in range(npix)], float)
        idl[im] = (nev, rows)
        i += 1 + npix
    nframe_diff = 0
    for im in range(len(labels)):
        fl = labels[im].ravel()
        ours = set(np.flatnonzero(fl).tolist())
        nev, rows = idl.get(im, (0, np.zeros((0, 3))))
        theirs = set(rows[:, 0].astype(int).tolist())
        if ours != theirs or len(np.unique(fl[fl > 0])) != nev:
            nframe_diff += 1
            extra = ours ^ theirs
            vals = [(p, float(sji.data[im].ravel()[p]), float(thr[im, 0, 0])) for p in list(extra)[:5]]
            print(f"  frame {im}: ours {len(ours)} px / {len(np.unique(fl[fl > 0]))} ev, IDL {len(theirs)} px / {nev} ev; diff {vals}")
    print("frames differing:", nframe_diff, "of", len(labels))


if __name__ == "__main__":
    check_si_iv()
    check_sji()
