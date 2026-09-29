"""Switch each deliberate fix back to IDL behaviour and measure agreement of the line centres with IDL."""
import sys

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import convolve1d

import cmp_mg
from irispy.utils import mg_features as M

cube, wave, ref = cmp_mg.load(sys.argv[1])
nsteps = int(sys.argv[2])
sub = cube[:nsteps]
original = {name: getattr(M, name) for name in ["_extrema", "_slit_features"]}


def idl_minima_extrema(spectra, *, maxima):
    if maxima:
        return original["_extrema"](spectra, maxima=True)
    # IDL: minima ranked by |value|, i.e. the higher of two close minima counts
    strength = np.abs(spectra)
    turn = np.diff(np.sign(np.diff(spectra, axis=-1)), axis=-1)
    candidate = np.zeros(spectra.shape, dtype=bool)
    candidate[:, 1:-1] = turn > 0
    flat = ~candidate.any(axis=-1)
    candidate[flat, np.argmin(spectra[flat], axis=-1)] = True
    order = np.argsort(np.where(candidate, -strength, np.inf), axis=-1)[:, : candidate.sum(axis=-1).max()]
    kept = np.take_along_axis(candidate, order, axis=-1)
    for rank in range(1, order.shape[1]):
        close = np.abs(order[:, :rank] - order[:, rank, np.newaxis]) <= M._SPACING
        kept[:, rank] &= ~(close & kept[:, :rank]).any(axis=-1)
    extrema = np.zeros_like(candidate)
    np.put_along_axis(extrema, order, kept, axis=-1)
    return extrema


def score(label):
    res = M.calculate_mg_features(sub)
    parts = []
    for li, line in enumerate("kh"):
        ours = res[f"{line}3_velocity"].data
        idl = ref["lc"][:nsteps, :, 0, li]
        both = np.isfinite(ours) & np.isfinite(idl)
        d = np.abs(ours - idl)[both]
        parts.append(f"{line}3 >0.1: {(d > 0.1).mean():.4f} >1: {(d > 1).mean():.4f} only-ours {(np.isfinite(ours) & ~np.isfinite(idl)).sum()} only-IDL(valid) {(~np.isfinite(ours) & np.isfinite(idl) & np.isfinite(res['k3_intensity'].data + 0) ).sum()}")
    print(f"{label:28s}", " | ".join(parts))


score("all fixes")
M._extrema = idl_minima_extrema
score("IDL minima ranking")
M._extrema = original["_extrema"]

# IDL-like clamped spline (3-point end slopes) instead of not-a-knot
orig_cs = M.CubicSpline


def clamped(x, y, axis=0):
    y = np.moveaxis(np.asarray(y, float), axis, 0)
    h1, h2, h12 = x[1] - x[0], x[2] - x[1], x[2] - x[0]
    s1 = -(h12 + h1) / h12 / h1 * y[0] + h12 / h1 / h2 * y[1] - h1 / h12 / h2 * y[2]
    hn, hm, hnn = x[-1] - x[-2], x[-2] - x[-3], x[-1] - x[-3]
    sn = hn / hnn / hm * y[-3] - hnn / hn / hm * y[-2] + (hnn + hn) / hnn / hn * y[-1]
    spline = orig_cs(x, y, axis=0, bc_type=((1, s1), (1, sn)))
    return lambda t: np.moveaxis(spline(t), 0, axis)


M.CubicSpline = lambda x, y, axis=0: clamped(x, y, axis) if np.ndim(y) > 1 else orig_cs(x, y)
score("IDL clamped spline")
M.CubicSpline = orig_cs

# IDL-like: rows with -200 are processed like the others
M.BAD_PIXEL_VALUE_SCALED = 1e30
_mask = sub.mask
sub._mask = None
score("rows with -200 processed")


def idl_slit_features(grid, spectra, positions):
    maxima, minima = M._extrema(spectra, maxima=True), M._extrema(spectra, maxima=False)
    centre = M._centres(grid, spectra, maxima, minima, 0.0)
    kernel = M._KERNEL if positions[-1] + 1 >= M._KERNEL.size else np.ones(1)
    for _ in range(2):
        lci = centre[:, 0].copy()
        lcc = lci.copy()
        bad = ~np.isfinite(lcc)
        if bad.any():
            lcc[bad] = 0
        else:
            lcc[-1] = 0  # IDL: lcc[where(~finite(lcc))] = 0 with no match zeroes the last element
        diff = np.abs(lcc - convolve1d(lcc, kernel, mode="nearest"))
        lci[diff > 3] = np.nan
        good = np.isfinite(lci)
        if good.sum() >= 3:
            guess = CubicSpline(positions[good], lci[good])(positions)
            redo = ~good
            centre[redo] = M._centres(grid, spectra[redo], maxima[redo], minima[redo], guess[redo], forced=True)
    redo = np.isnan(centre[:, 0])
    centre[redo] = M._centres(grid, spectra[redo], maxima[redo], minima[redo], 5.0, use_derivative=True)
    blue, red = M._peaks(grid, spectra, maxima, centre[:, 0])
    return np.stack([blue, centre, red], axis=1)


M._slit_features = idl_slit_features
score("+ IDL zero-filled cleaning")
