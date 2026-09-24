"""Seeding / fit-window experiment on the real full-window gallery raster (20180102_153155_3610108077), spatial sub-block."""
import sys, time, glob, warnings; warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np, astropy.units as u
from astropy.modeling import models
from astropy.modeling.fitting import LMLSQFitter, TRFLSQFitter, parallel_fit_dask
from irispy.io import read_files
from wp6_fitting import fit_gaussians

f = sorted(glob.glob("/Users/nabil/DATA/IRIS/561757a1b84e36def2ed9e2d89103117-iris_l2_20180102_153155_3610108077_raster/*.fits"))[0]
col = read_files(f, spectral_windows=["Si IV 1403", "Mg II k 2796"], memmap=False, uncertainty=False)  # memmap=True gives unscaled int16 in irispy 0.8.1
BLOCK = (slice(120, 160), slice(200, 400))  # 40 steps x 200 slit px = 8000 spectra

def block(win):
    c = col[win][0]
    wl = c.axis_world_coords("em.wl")[0].to_value(u.AA)
    return np.asarray(c.data[BLOCK], dtype=float), wl, c.meta.rest_wavelength.to_value(u.AA)

def report(label, fit, resid, wl, t, n):
    cen = fit.mean_1.value
    nan = int(np.isnan(cen).sum())
    print(f"  {label:52s} {t:6.2f} s ({1e3*t/cen.size:.2f} ms/spec, {len(wl)} px) nan={nan:4d} resid rms={np.sqrt(np.nanmean(resid**2)):8.2f} "
          + " ".join(f"mean_{i}={np.nanmedian(getattr(fit, f'mean_{i}').value):.3f}" for i in range(1, n + 1)))
    return fit

def run(label, cube, wl, n, rest=None, half=None):
    keep = np.abs(wl - (rest if rest else wl[cube.mean(axis=(0, 1)).argmax()])) <= half if half else slice(None)
    t = time.perf_counter(); fit, resid = fit_gaussians(cube[..., keep], wl[keep], n, rest, "single-threaded"); t = time.perf_counter() - t
    return report(label, fit, resid, wl[keep], t, n)

def agree(a, b, tol=0.05):
    x, y = a.mean_1.value, b.mean_1.value
    ok = np.isfinite(x) & np.isfinite(y)
    return f"{100 * np.mean(np.abs(x[ok] - y[ok]) < tol):.1f}% of finite centroids within {tol} A of reference"

if __name__ == "__main__":
    cube, wl, rest = block("Si IV 1403")
    print(f"Si IV 1403 block {cube.shape}, window {wl[0]:.2f}-{wl[-1]:.2f} A, TWAVE {rest:.2f} (inside), mean-spectrum argmax {wl[cube.mean(axis=(0,1)).argmax()]:.2f}")
    ref = run("n=1 rest=TWAVE, +/-1 A fit window (reference)", cube, wl, 1, rest, 1.0)
    a = run("n=1 argmax seed, whole 8.5 A window", cube, wl, 1)
    print("     ", agree(a, ref))
    b = run("n=1 rest=TWAVE seed, whole window", cube, wl, 1, rest)
    print("     ", agree(b, ref))
    c = run("n=1 argmax seed, +/-1 A fit window", cube, wl, 1, None, 1.0)
    print("     ", agree(c, ref))

    cube, wl, rest = block("Mg II k 2796")
    mean = cube.mean(axis=(0, 1))
    peaks = np.flatnonzero((mean[1:-1] > mean[:-2]) & (mean[1:-1] >= mean[2:])) + 1
    top = np.sort(peaks[np.argsort(mean[peaks])[-2:]])
    print(f"Mg II k block {cube.shape}, window {wl[0]:.2f}-{wl[-1]:.2f} A, TWAVE {rest:.2f}, argmax {wl[mean.argmax()]:.2f}, two highest local maxima {np.round(wl[top], 2)}")
    # gallery 07 reference: crop 2794-2798 A, fixed seeds, TRF prefit on the mean, LM per pixel
    keep = (wl >= 2794.0) & (wl <= 2798.0)
    m0 = models.Const1D(np.nanpercentile(mean[keep], 10)) + models.Gaussian1D(0.65 * mean[keep].max(), 2796.21, 0.08) + models.Gaussian1D(0.5 * mean[keep].max(), 2796.50, 0.08)
    avg = TRFLSQFitter()(m0, wl[keep], mean[keep]); print("  gallery prefit params:", np.round(avg.parameters, 3))
    t = time.perf_counter()
    g = parallel_fit_dask(data=np.nan_to_num(cube[..., keep].clip(min=0)), fitting_axes=2, world=(wl[keep],), model=avg, fitter=LMLSQFitter(), scheduler="single-threaded")
    resid = cube[..., keep] - np.moveaxis(g(wl[keep][:, None, None]), 0, -1)
    ref = report("n=2 gallery 07 (crop 2794-2798, fixed seeds, prefit)", g, resid, wl[keep], time.perf_counter() - t, 2)
    a = run("n=2 local-maxima seeds, whole 19 A window (k+h)", cube, wl, 2)
    print("     ", agree(a, ref))
    b = run("n=2 rest=TWAVE -/+0.15 seeds, whole window", cube, wl, 2, rest)
    print("     ", agree(b, ref))
    c = run("n=2 local-maxima seeds, +/-2 A fit window", cube, wl, 2, None, 2.0)
    print("     ", agree(c, ref))
    d = run("n=2 rest=2796.35 -/+0.15 seeds, +/-2 A window", cube, wl, 2, 2796.35, 2.0)
    print("     ", agree(d, ref))
