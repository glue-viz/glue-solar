"""Throwaway prototype of iris_burst_check / iris_sji_burst_check (SSW nrl/, 2017) on local L2 data.

Reads only the needed slices (FITS sections), never a whole raster.
"""
import sys

import numpy as np
from astropy.io import fits
from astropy.time import Time
from scipy import ndimage

from irispy.utils.response import get_latest_response

C_KMS = 299792.458
EIGHT = np.ones((3, 3), bool)  # region_grow /all_neigh == 8-connectivity


def area_1402(t):
    r = get_latest_response(Time(t))
    lam = r["LAMBDA"].to_value("nm")
    return r["AREA_SG"][0, np.argmin(np.abs(lam - 140.277))].value


def _scaled(hdu, sl):
    raw = hdu.section[sl]
    hd = hdu.header
    out = raw * hd.get("BSCALE", 1.0) + hd.get("BZERO", 0.0)
    if "BLANK" in hd:
        out[raw == hd["BLANK"]] = -200.0
    return out


def burst_check(fname, lref=1402.77, threshold=None, vmax=50.0, med_factor=10.0):
    with fits.open(fname, memmap=True, do_not_scale_image_data=True) as h:
        hdr0 = h[0].header
        iwin = [i for i in range(1, hdr0["NWIN"] + 1)
                if hdr0[f"TWMIN{i}"] <= lref <= hdr0[f"TWMAX{i}"]][0]
        hw = h[iwin].header
        lam = hw["CRVAL1"] + (np.arange(hw["NAXIS1"]) + 1 - hw["CRPIX1"]) * hw["CDELT1"]
        v = C_KMS * (lam - lref) / lref
        k = np.flatnonzero((v >= -vmax) & (v <= vmax))
        # data array is (step, y, lambda); read only the +-vmax bins
        cube = _scaled(h[iwin], np.s_[:, :, k[0]:k[-1] + 1])
        aux = h[-2]
        exptime = aux.data[:, aux.header["EXPTIMEF"]]
        date = hdr0["DATE_OBS"]
        ybin = round(hw["CDELT2"] / 0.166)
        sumsptrf = hdr0.get("SUMSPTRF")
    cube[cube <= -10] = np.nan  # iris_getwindata: -200 and (-200,-10) are missing; /keep_sat keeps 16183
    cube /= exptime[:, None, None]  # /normalize -> DN/s
    intensity = np.nanmean(cube, axis=-1)  # average(..., missing=)
    med = np.nanmedian(cube, axis=-1)  # IDL median ignores nothing; see report
    if threshold is None:
        threshold = 500.0 * area_1402(date) / area_1402("2013-10-22T21:00")
    thr = threshold * ybin
    hit = (intensity >= thr) & (intensity < med_factor * med)
    labels, ngroups = ndimage.label(hit, structure=EIGHT)
    return dict(date=date, nbins=k.size, ybin=ybin, sumsptrf=sumsptrf, thr=thr,
                shape=intensity.shape, npix=int(hit.sum()), ngroups=ngroups, labels=labels)


def sji_burst_check(fname, sig_factor=10.0):
    out = []
    with fits.open(fname, memmap=True, do_not_scale_image_data=True) as h:
        n = h[0].header["NAXIS3"]
        for i in range(n):
            img = _scaled(h[0], np.s_[i])
            good = img != -200.0
            med, sig = np.median(img[good]), np.std(img[good], ddof=1)
            mask = img >= sig_factor * sig + med
            labels, _ = ndimage.label(mask, structure=EIGHT)
            sizes = np.bincount(labels.ravel())
            keep = sizes >= 2  # isolated single pixels are ignored
            keep[0] = False
            labels = np.where(keep[labels], labels, 0)
            ng = int(keep.sum())
            if ng:
                out.append(dict(im_index=i, npix=int((labels > 0).sum()), nevents=ng, med=med, sig=sig))
    return n, out


def _selftest():
    # 8-connectivity: diagonal neighbours form one group; a lone pixel is its own group.
    m = np.zeros((5, 5), bool)
    m[0, 0] = m[1, 1] = m[4, 4] = True
    _, n = ndimage.label(m, structure=EIGHT)
    assert n == 2


if __name__ == "__main__":
    _selftest()
    which = sys.argv[1]
    if which == "sg":
        r = burst_check(sys.argv[2])
        r.pop("labels")
        print(r)
    else:
        n, out = sji_burst_check(sys.argv[2])
        print("frames", n, "frames with bursts", len(out),
              "total burst pixels", sum(o["npix"] for o in out),
              "total events", sum(o["nevents"] for o in out))
        for o in out[:5]:
            print(o)
