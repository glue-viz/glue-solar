import sys, time, warnings
warnings.simplefilter("ignore")
import numpy as np
import astropy.units as u
from astropy.modeling import models as m
from astropy.modeling.fitting import LMLSQFitter, TRFLSQFitter, parallel_fit_dask
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files

def load(which):
    files = [str(f) for f in get_test_data_filenames()]
    if which == "sns":
        f = [x for x in files if "/sns/" in x and "raster" in x][0]
    else:
        f = sorted(x for x in files if "20140329" in x)[0]
    return read_files(f)

def seed_argmax(cube):
    mean = np.nanmean(cube.data, axis=(0, 1))
    wl = cube.axis_world_coords("em.wl")[0].to(u.nm)
    i = int(np.nanargmax(mean))
    bg = float(np.nanpercentile(mean, 10))
    return wl, m.Const1D(amplitude=bg) + m.Gaussian1D(amplitude=float(mean[i]) - bg, mean=wl[i].value, stddev=0.005)

def run(cube, wl, model, scheduler):
    data = np.nan_to_num(cube.data.clip(min=0)).astype(float)
    t = time.perf_counter()
    fit = parallel_fit_dask(data=data, fitting_axes=2, world=(wl.value,), model=model, fitter=LMLSQFitter(), scheduler=scheduler)
    dt = time.perf_counter() - t
    n = data.shape[0] * data.shape[1]
    nan = int(np.isnan(fit.amplitude_1.value).sum())
    print(f"  {scheduler:16s} {dt:6.2f} s  ({1e3*dt/n:.2f} ms/spec)  shape={fit.amplitude_1.shape} nan={nan}")
    return fit

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "sns"
    col = load(which)
    print({k: v[0].data.shape for k, v in col.items()})
    siiv = col["Si IV 1403"][0]
    wl = siiv.axis_world_coords("em.wl")[0].to(u.nm)
    print("Si IV window", wl.min(), wl.max(), "rest", siiv.meta.rest_wavelength)
    # H: gallery core-window seeding on this data
    core = 140.277 * u.nm
    win = np.abs(wl - core) < 0.15 * u.nm
    mean = np.nanmean(siiv.data, axis=(0, 1))
    try:
        np.nanmax(mean[win]); print("core-window seeding OK")
    except ValueError as e:
        print("core-window seeding fails:", e)
    # single Gaussian, argmax seed
    wl, model = seed_argmax(siiv)
    print("single Gaussian, argmax seed", siiv.data.shape)
    for s in ["single-threaded", "threads", "processes"]:
        run(siiv, wl, model, s)
    # irispy-style prefit seed (TRF on spatial mean) then LM per pixel
    fitter = TRFLSQFitter()
    avg = fitter(model, wl.value, np.nanmean(siiv.data, axis=(0, 1)))
    print("single Gaussian, prefit seed:", avg.parameters)
    run(siiv, wl, avg, "single-threaded")
    if "Mg II k 2796" in col and "--double" in sys.argv:
        mg = col["Mg II k 2796"][0]
        wl2 = mg.axis_world_coords("em.wl")[0].to(u.nm)
        mean = np.nanmean(mg.data, axis=(0, 1)); bg = float(np.nanpercentile(mean, 10)); pk = float(np.nanmax(mean)); i = int(np.nanargmax(mean))
        model2 = m.Const1D(amplitude=bg) + m.Gaussian1D(amplitude=0.65*pk, mean=wl2[i].value-0.01, stddev=0.008) + m.Gaussian1D(amplitude=0.5*pk, mean=wl2[i].value+0.01, stddev=0.008)
        print("double Gaussian", mg.data.shape, wl2.min(), wl2.max())
        for s in ["single-threaded", "processes"]:
            run(mg, wl2, model2, s)
