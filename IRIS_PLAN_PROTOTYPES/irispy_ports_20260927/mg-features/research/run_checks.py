import sys
import time

import numpy as np
from astropy.io import fits

from mg_features_proto import C_KMS, WAVE_REF_NM, get_mg_features

rng = np.random.default_rng(1)
RASTER = "~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits"


def model(v, v3, sep, depth, amp):
    env = amp * np.exp(-((v - v3) / 25.0) ** 2) + 0.05 * amp
    return env * (1 - depth * np.exp(-((v - v3) / (sep / 2.2)) ** 2))


def truth(v3, sep, depth, amp):
    vf = np.linspace(-60, 60, 240001)
    f = model(vf, v3, sep, depth, amp)
    near = np.abs(vf - v3) < sep
    ib = np.argmax(np.where(near & (vf < v3), f, -np.inf))
    ir = np.argmax(np.where(near & (vf > v3), f, -np.inf))
    i3 = ib + np.argmin(f[ib:ir])
    return vf[[i3, ib, ir]]


def synthetic(dispersion_aa=0.02546, nslit=200, peak_counts=None):
    wave_nm = np.arange(2792.98, 2806.63, dispersion_aa) / 10
    spec = np.zeros((nslit, wave_nm.size))
    params = []
    for i in range(nslit):
        p = (8 * np.sin(i / 15.0), 20 + 5 * np.cos(i / 23.0), 0.5, 400.0)
        params.append(p)
        for line, scale in (("k", 1.0), ("h", 0.75)):
            v = C_KMS * (wave_nm - WAVE_REF_NM[line]) / WAVE_REF_NM[line]
            spec[i] += model(v, *p[:3], p[3] * scale) * (np.abs(v) < 150)
    if peak_counts is not None:  # Poisson noise with `peak_counts` photons at the k2 peaks
        s = peak_counts / spec.max()
        spec = rng.poisson(spec * s) / s
    return spec.astype(np.float32), wave_nm, params


def score(spec, wave_nm, params, label, show_bad=False):
    t0 = time.perf_counter()
    out = get_mg_features(spec, wave_nm)
    dt = time.perf_counter() - t0
    tv = np.array([truth(*p) for p in params])
    print(f"{label}: {spec.shape[0]} spectra, {1e3 * dt / spec.shape[0]:.2f} ms/spectrum (k+h)")
    for name, got, col in zip(("k3", "k2v", "k2r"), out["k"], range(3)):
        err = got[:, 0] - tv[:, col]
        print(
            f"   {name}: finite {np.isfinite(err).mean():.3f}  median|dv| {np.nanmedian(np.abs(err)):.3f}"
            f"  p95|dv| {np.nanpercentile(np.abs(err), 95):.3f}  n(|dv|>2) {np.sum(np.abs(err) > 2)}"
        )
        if show_bad:
            for i in np.flatnonzero(np.abs(err) > 2)[:4]:
                print("     ", i, np.round(params[i][:2], 2), "truth", np.round(tv[i], 2), "got", got[i])
    return out


def real(step):
    with fits.open(RASTER, memmap=True, do_not_scale_image_data=True) as h:
        hdr = h[8].header
        raw = np.asarray(h[8].section[step])
    data = (raw * hdr.get("BSCALE", 1.0) + hdr.get("BZERO", 0.0)).astype(np.float32)
    wave_nm = (hdr["CRVAL1"] + (np.arange(hdr["NAXIS1"]) + 1 - hdr["CRPIX1"]) * hdr["CDELT1"]) / 10
    fill = (data == -200).all(axis=1)
    t0 = time.perf_counter()
    out = get_mg_features(data, wave_nm)
    dt = time.perf_counter() - t0
    print(f"real 3824262996 step {step}: {data.shape} {1e3 * dt / data.shape[0]:.2f} ms/px (k+h); all-fill rows {fill.sum()}")
    for line in ("k", "h"):
        lc, bp, rp = out[line]
        ok = ~fill
        print(
            f"  {line}3 med {np.nanmedian(lc[ok, 0]):6.2f} km/s fin {np.isfinite(lc[ok, 0]).mean():.3f} |"
            f" {line}2v med {np.nanmedian(bp[ok, 0]):6.2f} fin {np.isfinite(bp[ok, 0]).mean():.3f} |"
            f" {line}2r med {np.nanmedian(rp[ok, 0]):6.2f} fin {np.isfinite(rp[ok, 0]).mean():.3f} |"
            f" fill rows: {line}3 finite {np.isfinite(lc[fill, 0]).sum()}/{fill.sum()}"
        )
    return out


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "synthetic":
        s, w, p = synthetic()
        score(s, w, p, "noiseless 0.02546 A/px", show_bad=True)
        for pc in (2500, 400, 100):
            s, w, p = synthetic(peak_counts=pc)
            score(s, w, p, f"Poisson {pc} counts at peak, 0.02546 A/px")
        s, w, p = synthetic(dispersion_aa=0.05092)
        score(s, w, p, "noiseless summed x2 0.05092 A/px")
    else:
        real(int(what))
