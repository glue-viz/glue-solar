"""
Throwaway prototype: line-by-line port of SSW iris_get_mg_features.pro
(https://sohoftp.nascom.nasa.gov/solarsoft/iris/idl/uio/utils/iris_get_mg_features.pro)
to numpy, to measure cost and sanity-check on synthetic profiles.

Spectra are (nslit, nwave) here (IDL: (nwave, nslit)).
IDL quirks are reproduced on purpose and marked "IDL quirk".
"""

import numpy as np
from scipy.linalg import solve_banded
from scipy.ndimage import correlate1d

C_KMS = 299792.4580
WAVE_REF_NM = {"k": 279.63509493, "h": 280.35297192}
WAVE_REF_ONLYK_NM = 279.644  # IDL quirk: /onlyk uses 279.644 nm, ~9.5 km/s off the vacuum k rest


# ---------------------------------------------------------------- IDL helpers
def lclxtrem(vec, width=5, maxima=False):
    """Buie lclxtrem: extrema sorted by decreasing |vec|, weaker ones within width removed."""
    s = np.sign(np.diff(vec))
    ss = np.diff(s)
    z = np.flatnonzero(ss < 0 if maxima else ss > 0)
    if z.size == 0:
        ext = vec.max() if maxima else vec.min()
        return np.flatnonzero(vec == ext)
    idx = z + 1
    keep = list(np.argsort(np.abs(vec[idx]), kind="stable")[::-1])  # IDL quirk: |vec| even for minima
    i = 0
    while i < len(keep) - 1:
        c = idx[keep[i]]
        keep = keep[: i + 1] + [k for k in keep[i + 1 :] if abs(idx[k] - c) > width]
        i += 1
    return idx[keep]


def peakdetect(y, x, lookahead):
    ma = np.sort(lclxtrem(y, lookahead, maxima=True))
    mi = np.sort(lclxtrem(y, lookahead))
    return np.column_stack([x[ma], y[ma]]), np.column_stack([x[mi], y[mi]])


def tension_spline(x, y, t, sigma=1.0):
    """
    Cline (1974) spline under tension, IDL SPLINE conventions as recalled (UNVERIFIED):
    sigma clamped to >= 1e-3, scaled by (n-1)/(x[-1]-x[0]); end slopes from 3-point
    quadratics; linear-in-interval extrapolation with end intervals. y may be (n,) or (n, m).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    t = np.asarray(t, float)
    n = x.size
    sig = max(sigma, 1e-3) * (n - 1) / (x[-1] - x[0])
    h = np.diff(x)
    d = np.diff(y, axis=0) / h.reshape(-1, *([1] * (y.ndim - 1)))
    sh = np.sinh(sig * h)
    a = (1 / h - sig / sh) / sig**2
    b = (sig * np.cosh(sig * h) / sh - 1 / h) / sig**2
    h1, h2, h12 = x[1] - x[0], x[2] - x[1], x[2] - x[0]
    s1 = -(h12 + h1) / h12 / h1 * y[0] + h12 / h1 / h2 * y[1] - h1 / h12 / h2 * y[2]
    hn, hm, hnn = x[-1] - x[-2], x[-2] - x[-3], x[-1] - x[-3]
    sn = hn / hnn / hm * y[-3] - hnn / hn / hm * y[-2] + (hnn + hn) / hnn / hn * y[-1]
    ab = np.zeros((3, n))
    ab[0, 1:] = a
    ab[2, :-1] = a
    ab[1, 0] = b[0]
    ab[1, -1] = b[-1]
    ab[1, 1:-1] = b[:-1] + b[1:]
    rhs = np.empty_like(y)
    rhs[0] = d[0] - s1
    rhs[-1] = sn - d[-1]
    rhs[1:-1] = d[1:] - d[:-1]
    m = solve_banded((1, 1), ab, rhs)
    i = np.clip(np.searchsorted(x, t, side="right") - 1, 0, n - 2)
    xl, xr, hi = x[i], x[i + 1], h[i]
    shape = (-1,) + (1,) * (y.ndim - 1)
    dl, dr, hh, shi = (t - xl).reshape(shape), (xr - t).reshape(shape), hi.reshape(shape), sh[i].reshape(shape)
    return (
        (m[i] * np.sinh(sig * dr) + m[i + 1] * np.sinh(sig * dl)) / (sig**2 * shi)
        + (y[i] - m[i] / sig**2) * dr / hh
        + (y[i + 1] - m[i + 1] / sig**2) * dl / hh
    )


def gaussian_kernel(sd):
    lw = int(4.0 * sd + 0.5)
    k = np.exp(-0.5 * np.arange(-lw, lw + 1) ** 2 / sd**2)
    return k / k.sum()


NAN2 = (np.nan, np.nan)


# ------------------------------------------------------------ per-spectrum
def mg_single(vel, spec, guess, use_deriv=False, force_guess=False):
    pts_min, pfit, wdiff_max, margin, lookahead = 15, 3, 4, 15, 10
    deriv_flag = False
    nsp = spec.size - 1
    pmax, pmin = peakdetect(spec, vel, lookahead)
    if not force_guess:
        fmax = pmax[(pmax[:, 0] > vel[0] + 10) & (pmax[:, 0] < vel[nsp] - 10)]
        fmin = pmin[(pmin[:, 0] > vel[0] + 10) & (pmin[:, 0] < vel[nsp] - 10)]
        lpmax, lpmin = len(fmax), len(fmin)
        pmax = fmax if lpmax else np.zeros((1, 2))
        tag = f"{lpmin}{lpmax}"
        if tag in ("12", "31", "32", "34", "54", "76"):
            guess = fmin[lpmin // 2, 0]
            pts_min //= 2
        elif tag in ("22", "23", "33", "42", "43", "44"):
            lo, hi = np.sort(fmax[np.argsort(fmax[:, 1], kind="stable")[-2:], 0])
            sel = fmin[(fmin[:, 0] > lo) & (fmin[:, 0] < hi)]
            if len(sel):
                guess = sel[np.argmin(sel[:, 1]), 0]
        elif tag == "21":
            if fmin[:, 1].max() / fmin[:, 1].min() > 1.3:
                guess = fmin[np.argmin(fmin[:, 1]), 0]
                pts_min //= 2
            else:
                deriv_flag = True
        elif lpmax == 1:
            deriv_flag = True
        elif lpmin == 1:
            guess = fmin[0, 0]
    elif np.count_nonzero((pmax[:, 0] > vel[0] + 20) & (pmax[:, 0] < vel[nsp] - 20)) == 1:
        deriv_flag = True

    if deriv_flag:
        if not use_deriv:
            return NAN2
        dd = np.abs(np.diff(spec))
        incr = int(15.0 / (vel[1] - vel[0]))
        idxm = int(np.argmin(np.abs(vel - pmax[0, 0])))
        v0, v1 = max(0, idxm - incr), min(idxm + incr, nsp)
        if spec[v0] > spec[v1]:
            if idxm - margin - 1 < v0 + margin:
                return NAN2
            pidx = v0 + int(np.argmin(dd[v0 + margin : idxm - margin])) + margin + 1
        else:
            if v1 - margin - 1 < idxm + margin:
                return NAN2
            pidx = idxm + int(np.argmin(dd[idxm + margin : v1 - margin])) + margin + 1
        return vel[pidx], spec[pidx]

    idg = int(np.argmin(np.abs(vel - guess)))
    isp = int(np.argmin(spec[max(0, idg - pts_min) : min(idg + pts_min - 1, nsp) + 1]))
    ini = max(0, isp + idg - pts_min)  # IDL quirk: wrong offset when idg < pts_min
    wi, wf = max(0, ini - pfit), min(ini + pfit, nsp)
    if wf - wi + 1 < 2:
        return NAN2
    c2, c1, c0 = np.polyfit(vel[wi : wf + 1], spec[wi : wf + 1], 2)
    lc = -c1 / (2.0 * c2)
    if abs(lc - vel[ini]) > wdiff_max * (vel[1] - vel[0]):
        return NAN2
    return lc, c0 - c2 * lc**2


def _refine(vel, spec, p, pp=45):
    nsp = spec.size - 1
    idg = int(np.argmin(np.abs(vel - p[0])))
    lo, hi = max(0, idg - 2), min(idg + 2, nsp)
    nvel = np.arange(pp) / (pp - 1.0) * (vel[lo] - vel[hi]) + vel[hi]  # decreasing, as in IDL
    lo, hi = max(0, idg - 3), min(idg + 3, nsp)
    if hi >= lo + 2:
        ns = tension_spline(vel[lo : hi + 1], spec[lo : hi + 1], nvel, 0.0)
        k = int(np.argmax(ns))
        return nvel[k], ns[k]
    return tuple(p)


def mg_peaks_single(vel, spec, lc):
    lookahead = 10
    bp = rp = NAN2
    if not np.isfinite(lc):
        lc = 0.0
    pmax, _ = peakdetect(spec, vel, lookahead)
    pmax = pmax[np.abs(pmax[:, 0] - lc) < 50]
    n = len(pmax)
    if n > 4:
        pmax = pmax[n // 2 - 2 : n // 2 + 2]
        n = 4
    p = pmax
    if n == 1:
        if p[0, 0] > lc:
            rp = p[0]
        else:
            bp = p[0]
    elif n == 2:
        bp, rp = p[0], p[1]
    elif n == 3:
        if p[0, 0] < lc < p[1, 0]:
            bp, rp = p[0], p[1 + np.argmax(p[1:, 1])]
        elif p[1, 0] < lc < p[2, 0]:
            bp, rp = p[np.argmax(p[:2, 1])], p[2]
        else:
            aa = p[p[:, 1] != p[:, 1].min()]
            bp, rp = aa[0], aa[1]
    elif n == 4:
        rt = p[0, 1] > 1.06 * p[1, 1] and p[3, 1] > 1.06 * p[2, 1]
        if p[3, 0] - p[0, 0] < 40 and p[2, 0] - p[1, 0] > 13 and rt:
            bp, rp = p[0], p[3]
        elif p[1, 0] < lc < p[2, 0] or lc > p[3, 0] or lc < p[0, 0]:
            bp, rp = p[1], p[2]
        elif lc < p[1, 0]:
            bp, rp = p[0], p[1 + np.argmax(p[1:, 1])]
        elif lc < p[3, 0]:
            bp, rp = p[np.argmax(p[:3, 1])], p[3]
    bp = _refine(vel, spec, bp) if np.isfinite(bp[0]) else bp
    rp = _refine(vel, spec, rp) if np.isfinite(rp[0]) else rp
    return bp, rp


# ------------------------------------------------------------ one slit
def get_mg_features(spec, wave_nm, vrange=(-40, 40), lines=("k", "h"), onlyk_quirk=False):
    """spec: (nslit, nwave). Returns dict line -> (lc, bp, rp) each (nslit, 2) [v, I]."""
    npi = 300
    nslit = spec.shape[0]
    kernel = gaussian_kernel(2.0)
    if nslit < kernel.size:
        kernel = np.array([1.0])
    out = {}
    for line in lines:
        ref = WAVE_REF_ONLYK_NM if (onlyk_quirk and line == "k" and len(lines) == 1) else WAVE_REF_NM[line]
        vaxis = C_KMS * (wave_nm - ref) / ref
        if not (vaxis[0] <= vrange[0] and vaxis[-1] >= vrange[1]):
            continue
        sel = (vaxis >= vrange[0] - 3) & (vaxis <= vrange[1] + 3)
        ivel = vaxis[sel]
        vel = np.arange(npi) / (npi - 1.0) * (ivel[-1] - ivel[0]) + ivel[0]
        spc = tension_spline(ivel, spec[:, sel].T, vel, 0.0).T.astype(np.float32)  # vectorised over slit
        lc = np.array([mg_single(vel, s, 0.0) for s in spc], dtype=np.float32)
        for _ in range(2):
            lci = lc[:, 0].copy()
            lcc = lci.copy()
            bad = ~np.isfinite(lcc)
            lcc[bad if bad.any() else -1] = 0.0  # IDL quirk: where()=-1 clips to element 0
            diff = np.abs(lcc - correlate1d(lcc, kernel, mode="nearest"))
            lci[diff > 3] = np.nan
            good = np.flatnonzero(np.isfinite(lci))
            if good.size >= 3:
                guess = tension_spline(good, lci[good], np.arange(nslit), 1.0)
                for i in np.flatnonzero(~np.isfinite(lci)):
                    lc[i] = mg_single(vel, spc[i], guess[i], force_guess=True)
        for i in np.flatnonzero(~np.isfinite(lc[:, 0])):
            lc[i] = mg_single(vel, spc[i], 5.0, use_deriv=True)
        bp = np.full((nslit, 2), np.nan, np.float32)
        rp = np.full((nslit, 2), np.nan, np.float32)
        for i in range(nslit):
            bp[i], rp[i] = mg_peaks_single(vel, spc[i], lc[i, 0])
        out[line] = (lc, bp, rp)
    return out


# ------------------------------------------------------------ self-checks
def _demo():
    from scipy.interpolate import CubicSpline

    # tension spline with ~zero tension equals a clamped cubic spline with the same end slopes
    x = np.linspace(0, 10, 12)
    y = np.sin(x) + 0.1 * x
    t = np.linspace(0, 10, 101)
    h1, h2, h12 = x[1] - x[0], x[2] - x[1], x[2] - x[0]
    s1 = -(h12 + h1) / h12 / h1 * y[0] + h12 / h1 / h2 * y[1] - h1 / h12 / h2 * y[2]
    hn, hm, hnn = x[-1] - x[-2], x[-2] - x[-3], x[-1] - x[-3]
    sn = hn / hnn / hm * y[-3] - hnn / hn / hm * y[-2] + (hnn + hn) / hnn / hn * y[-1]
    ref = CubicSpline(x, y, bc_type=((1, s1), (1, sn)))(t)
    assert np.max(np.abs(tension_spline(x, y, t, 0.0) - ref)) < 1e-5
    # interpolates the nodes at any tension
    assert np.allclose(tension_spline(x, y, x, 1.0), y)
    assert np.allclose(tension_spline(x, y, x, 5.0), y)

    # lclxtrem: |vec| ordering quirk for minima: higher-valued minimum wins within width
    v = np.array([5, 1, 5, 5, 5, 3, 5, 5.0])
    assert list(lclxtrem(v, 10)) == [5]
    assert sorted(lclxtrem(v, 0)) == [1, 5]
    print("self-checks passed")


if __name__ == "__main__":
    _demo()
