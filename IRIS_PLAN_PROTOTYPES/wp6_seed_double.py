"""Which double-Gaussian seed works on a synthetic k2v/k2r profile?"""
import sys, warnings; warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
from astropy.modeling import models
from astropy.modeling.fitting import LMLSQFitter, parallel_fit_dask
from wp6_check_synth import synthetic_cube, gauss

def run(cube, wl, centres, label):
    mean = cube.mean(axis=(0, 1)); bg = np.percentile(mean, 10)
    model = models.Const1D(amplitude=bg)
    for c in centres:
        model += models.Gaussian1D(amplitude=mean.max() - bg, mean=c, stddev=0.08)
    fit = parallel_fit_dask(data=cube, fitting_axes=2, world=(wl,), model=model, fitter=LMLSQFitter(), scheduler="single-threaded")
    resid = cube - np.moveaxis(fit(wl[:, None, None]), 0, -1)
    print(f"  {label:44s} seeds={np.round(centres, 3)} nan={np.isnan(fit.mean_1.value).sum()} resid rms={np.sqrt((resid**2).mean()):.2e} mean_1 med={np.nanmedian(fit.mean_1.value):.3f} mean_2 med={np.nanmedian(fit.mean_2.value):.3f}")

for sep in (0.3, 0.45):
    cube, wl, truth = synthetic_cube(2)
    if sep != 0.3:  # rebuild with a wider separation
        nx, ny, nwl = cube.shape; ix, iy = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
        cube = (5 + 0.5 * ix)[..., None] + gauss(wl, (100 + 10 * ix)[..., None], (1402.30 + 0.01 * iy)[..., None], 0.08) + gauss(wl, (70 + 5 * iy)[..., None], (1402.30 + sep - 0.01 * ix)[..., None], 0.08)
    mean = cube.mean(axis=(0, 1)); amax = wl[mean.argmax()]
    peaks = np.flatnonzero((mean[1:-1] > mean[:-2]) & (mean[1:-1] >= mean[2:])) + 1
    peaks = peaks[np.argsort(mean[peaks])[::-1]][:2]
    print(f"separation {sep} A: argmax={amax:.3f} local maxima={np.round(wl[peaks],3)}")
    run(cube, wl, [amax - 0.15, amax + 0.15], "argmax -/+ 0.15 (no centre given)")
    run(cube, wl, [amax, amax + 0.3], "argmax, argmax + 0.3")
    run(cube, wl, np.sort(wl[peaks]), "two highest local maxima")
    mid = amax + sep / 2
    run(cube, wl, [mid - 0.15, mid + 0.15], "user centre (between peaks) -/+ 0.15 (gallery)")
