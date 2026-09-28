"""
Throwaway port of SSW iris_prep_wavecorr_l2 (per-step fits only + smoothing + sine fit).

Reads only the few wavelength columns around each reference line from a memmapped
Level 2 raster, never the full window.
"""

import sys

import numpy as np
from astropy.io import fits
from astropy.time import Time, TimeDelta
from scipy.ndimage import uniform_filter1d
from scipy.optimize import curve_fit

# name, wave0, wmin, wmax, lmin (DN), sign (+1 emission, -1 absorption)
LINES = [
    ("Ni I", 2799.474, 2799.3, 2799.8, 5, -1),
    ("Mn I", 2801.902, 2801.6, 2802.4, 5, -1),
    ("Fe I", 2805.346, 2805.1, 2805.7, 5, -1),
    ("O I", 1355.60, 1355.4, 1355.9, 0.5, 1),
    ("Fe II", 1392.82, 1392.6, 1393.1, 0.5, 1),
]
ORBIT = 5856.0  # s, hard coded in SSW


def gauss(x, a0, a1, a2, a3, a4=0.0):
    return a0 * np.exp(-0.5 * ((x - a1) / a2) ** 2) + a3 + a4 * x


def idl_gaussfit_estimate(x, y, nterms):
    # IDL GAUSSFIT: subtract const (nterms=4) or line (nterms=5) then take extreme
    c = np.polyfit(x, y, 0 if nterms == 4 else 1)[::-1]
    yd = y - np.polyval(c[::-1], x)
    imax, imin = np.argmax(yd), np.argmin(yd)
    i0 = imax if abs(yd[imax]) > abs(yd[imin]) else imin
    i0 = min(max(i0, 1), len(x) - 2)
    dy = yd[i0]
    i = 0
    while i0 + i + 1 < len(x) and i0 - i > 0 and abs(yd[i0 + i]) > abs(dy / np.e) and abs(yd[i0 - i]) > abs(dy / np.e):
        i += 1
    p = [dy, x[i0], abs(x[i0] - x[i0 + i]) or (x[1] - x[0]), c[0]]
    if nterms == 5:
        p.append(c[1])
    return p


def window_wave(hdr):
    n = hdr["NAXIS1"]
    return hdr["CRVAL1"] + hdr["CDELT1"] * (np.arange(n) + 1 - hdr["CRPIX1"])


def measure(filename):
    with fits.open(filename, memmap=True, do_not_scale_image_data=True) as hdul:
        p = hdul[0].header
        aux, auxh = hdul[-2].data, hdul[-2].header
        times = Time(p["STARTOBS"]) + TimeDelta(aux[:, auxh["TIME"]], format="sec")
        obs_vr = aux[:, auxh["OBS_VRIX"]].astype(float)
        nt = aux.shape[0]
        corrs = np.full((nt, len(LINES)), np.nan)
        for j, (name, w0, wmin, wmax, lmin, sign) in enumerate(LINES):
            win = next(
                (i for i in range(1, p["NWIN"] + 1) if p[f"TWMIN{i}"] <= w0 <= p[f"TWMAX{i}"]),
                None,
            )
            if win is None:
                continue
            h = hdul[win]
            lam = window_wave(h.header)
            sub = np.nonzero((lam >= wmin) & (lam <= wmax))[0]
            if sub.size < 5:
                sub = np.arange(5) + (sub[0] if sub.size else 0)
            nterms = 4 if sub.size < 7 else 5
            raw = np.asarray(h.data[:, :, sub[0] : sub[-1] + 1], dtype=float)
            data = raw * h.header.get("BSCALE", 1.0) + h.header.get("BZERO", 0.0)
            bad = ~np.isfinite(data) | (data == -200)
            data[bad] = 0.0
            ny = data.shape[1]
            prof = np.clip(data, 0, None).sum(axis=1) / ny  # (nt, nsub), mean along slit
            x = lam[sub]
            for k in range(nt):
                y = prof[k]
                if y.mean() <= lmin:
                    continue
                try:
                    p0 = idl_gaussfit_estimate(x, y, nterms)
                    popt, _ = curve_fit(gauss, x, y, p0=p0, maxfev=2000)
                except Exception:  # noqa: BLE001
                    continue
                abscor = w0 - popt[1]
                if abs(abscor) <= (wmax - wmin) / 4 and popt[0] * sign > 0:
                    corrs[k, j] = abscor
    return times, obs_vr, corrs


def recommended(tai, corr, outlier):
    """
    Outlier cut, 5-min boxcar, fixed-period sine + polynomial (SSW defaults).
    """
    corr = corr.copy()
    med = np.nanmedian(corr)
    corr[(corr - med) > outlier] = np.nan  # SSW cut is one sided, kept as is
    good = ~((corr - med) > outlier)
    swidth = int(np.floor(300.0 / np.mean(np.gradient(tai))))
    if swidth % 2 == 0:
        swidth += 1  # IDL SMOOTH uses width+1 when even
    if swidth < good.sum():
        # IDL SMOOTH(/nan,/edge_truncate): mean of finite neighbours
        finite = np.isfinite(corr)
        num = uniform_filter1d(np.where(finite, corr, 0.0), swidth, mode="nearest")
        den = uniform_filter1d(finite.astype(float), swidth, mode="nearest")
        corr = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    x = tai - tai[0]
    norbit = min(int(np.floor((tai.max() - tai.min()) / ORBIT)), 3)
    freq = 2 * np.pi / ORBIT

    def model(x, amp, phase, offset, *poly):
        y = offset + amp * np.sin(freq * x + phase)
        for i, c in enumerate(poly, start=1):
            y = y + c * x**i
        return y

    ok = good & np.isfinite(corr)
    # ponytail: scaled-free polynomial like SSW; poorly conditioned x**n in seconds, fine for <= 3 terms
    p0 = [0.01, 1.0, 0.1] + [0.0] * norbit
    popt, _ = curve_fit(model, x[ok], corr[ok], p0=p0, maxfev=20000)
    return model(x, *popt), popt


if __name__ == "__main__":
    fn = sys.argv[1]
    times, obs_vr, corrs = measure(fn)
    tai = times.tai.unix  # seconds, any monotonic scale is fine for relative fits
    np.savez(fn.split("/")[-1] + ".npz", tai=tai, obs_vr=obs_vr, corrs=corrs)
    for j, line in enumerate(LINES):
        c = corrs[:, j]
        f = np.isfinite(c)
        if f.any():
            print(f"{line[0]:6s} n={f.sum():4d} mean={np.nanmean(c):+.4f} min={np.nanmin(c):+.4f} max={np.nanmax(c):+.4f} A")
    for j, cut, label in ((0, 0.08, "NUV"), (3, 0.05, "FUV")):
        if np.isfinite(corrs[:, j]).sum() > 10:
            rec, popt = recommended(tai, corrs[:, j], cut)
            print(f"corr_{label}: min={rec.min():+.4f} max={rec.max():+.4f} amp={popt[0]:+.4f} offset={popt[2]:+.4f}")
            # correlate raw measurement with OBS_VR Doppler term
            w0 = LINES[j][1]
            dop = obs_vr / 2.99792458e8 * w0
            f = np.isfinite(corrs[:, j])
            slope = np.polyfit(dop[f], corrs[f, j], 1)[0]
            print(f"  OBS_VR*lambda/c range {dop.min():+.4f}..{dop.max():+.4f} A; slope corr vs it = {slope:+.3f}; r={np.corrcoef(dop[f], corrs[f, j])[0, 1]:+.3f}")
