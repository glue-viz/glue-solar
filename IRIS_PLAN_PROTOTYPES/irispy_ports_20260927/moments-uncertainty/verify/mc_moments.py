"""
Monte Carlo check of first-order moment-error propagation against irispy main's calculate_moments.

Run with PYTHONPATH pointing at an extracted irispy origin/main (49d705c).
"""

import numpy as np

import astropy.units as u

from irispy.tests.helpers import make_test_spectrogram_cube
from irispy.utils.constants import DN_UNIT, READOUT_NOISE
from irispy.utils.moments import calculate_moments

rng = np.random.default_rng(42)
PH_PER_DN = DN_UNIT["FUV"].to(u.photon)  # 4 photons/DN (gain 6 / yield 1.5)
RN_DN = READOUT_NOISE["FUV"].to_value(DN_UNIT["FUV"])  # 3.1 DN


def sigma_pr179(data):
    """calculate_uncertainty after LM-SAL/irispy#179: negative DN gets readout noise only."""
    return np.sqrt(np.clip(data * PH_PER_DN, 0, None) + (RN_DN * PH_PER_DN) ** 2) / PH_PER_DN


def propagate(data, sigma, wvl, *, clipped_sigma):
    """
    First-order errors of sum, centroid and stddev, mirroring moments.py:129-158.

    clipped_sigma: "zero" -> samples zeroed by the clip (d < 0) carry no error (exact linearisation);
                   "keep" -> they keep their sigma (readout-only floor from #179).
    """
    bad = ~np.isfinite(data)
    neg = (~bad) & (data < 0)
    d = np.where(bad | neg, 0.0, data)
    s = np.where(bad, 0.0, sigma)
    if clipped_sigma == "zero":
        s = np.where(neg, 0.0, s)
    intensity = d.sum(-1)
    centroid = (d * wvl).sum(-1) / intensity
    dl = wvl - centroid[..., None]
    var = (dl**2 * d).sum(-1) / intensity
    s2 = s**2
    err_i = np.sqrt(s2.sum(-1))
    err_c = np.sqrt((dl**2 * s2).sum(-1)) / intensity
    err_var = np.sqrt(((dl**2 - var[..., None]) ** 2 * s2).sum(-1)) / intensity
    err_w = err_var / (2 * np.sqrt(var))
    return err_i, err_c, err_w


def run(amplitude, *, n=20000, background=0.0, line_sigma=0.05, wing=0.3):
    rest = 1402.77
    wvl = np.arange(1402.0, 1403.5, 0.02596)  # native FUV dispersion, Angstrom
    truth = background + amplitude * np.exp(-0.5 * ((wvl - rest) / line_sigma) ** 2)
    photons = rng.poisson(np.broadcast_to(truth * PH_PER_DN, (n, wvl.size)))
    data = photons / PH_PER_DN + rng.normal(0, RN_DN, (n, wvl.size))
    cube = make_test_spectrogram_cube(data[None], wvl * u.AA)
    m = calculate_moments(cube, rest_wavelength=rest * u.AA, wings=wing * u.AA)
    I = m["intensity"].data[0]
    c = (m["centroid"].data[0] * u.nm).to_value(u.AA)
    w = (m["width"].data[0] * u.nm).to_value(u.AA)
    sel = np.abs(wvl - rest) <= wing + 1e-9
    wv = wvl[sel]
    frac_neg = np.mean(data[:, sel] < 0)
    ok = np.isfinite(c) & np.isfinite(w)
    rows = []
    for mode in ("zero", "keep"):
        ei, ec, ew = propagate(data[:, sel], sigma_pr179(data[:, sel]), wv, clipped_sigma=mode)
        rows.append(
            (
                mode,
                np.median(ei[ok]) / np.std(I[ok]),
                np.median(ec[ok]) / np.std(c[ok]),
                np.median(ew[ok]) / np.std(w[ok]),
            )
        )
    return frac_neg, ok.mean(), rows, (np.mean(c[ok]) - rest, np.mean(w[ok]) / line_sigma)


def main():
    print(f"FUV noise model: {PH_PER_DN} photon/DN, read noise {RN_DN} DN; ratio = median analytic / MC std")
    for bg in (0.0, 2.0):
        for amp in (1000, 100, 30, 10, 3):
            frac_neg, frac_ok, rows, (bias_c, w_ratio) = run(amp, background=bg)
            print(
                f"bg={bg:>3} amp={amp:>5} DN  neg samples={frac_neg:5.1%} valid={frac_ok:6.1%} "
                f"centroid bias={bias_c * 1e3:+6.2f} mA  width/true={w_ratio:5.2f}"
            )
            for mode, ri, rc, rw in rows:
                print(f"    clipped sigma={mode:4}: I {ri:5.2f}  centroid {rc:5.2f}  width {rw:5.2f}")
    # self-check: with no clipped samples (bright background) the linearisation must match MC to a few percent
    for amp in (1000, 100):
        frac_neg, _, rows, _ = run(amp, background=50.0)
        print(f"bg= 50 amp={amp:>5} DN  neg samples={frac_neg:5.1%}", [tuple(round(float(x), 3) for x in r[1:]) for r in rows])
        for _mode, ri, rc, rw in rows:
            assert abs(ri - 1) < 0.03 and abs(rc - 1) < 0.03 and abs(rw - 1) < 0.03, rows
    print("self-check passed")


if __name__ == "__main__":
    main()
