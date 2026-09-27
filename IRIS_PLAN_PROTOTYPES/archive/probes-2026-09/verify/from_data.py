import warnings, time; warnings.simplefilter("ignore")
import numpy as np, astropy.units as u
from astropy.wcs.wcsapi import SlicedLowLevelWCS
from astropy.modeling import models as m
from astropy.modeling.fitting import LMLSQFitter, parallel_fit_dask
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data, _GlueWCS
if __name__ == "__main__":
    f = [str(x) for x in get_test_data_filenames() if "/sns/" in str(x) and "raster" in str(x)]
    datasets = raster_data(f, windows=["Si IV 1403"])
    d = datasets[0]
    print("label", d.label, "shape", d.shape, "components", [str(c) for c in d.main_components])
    cid = d.main_components[0]
    comp = d.get_component(cid)
    print("units", repr(comp.units), "meta type", type(d.meta).__name__, "rest", getattr(d.meta, "rest_wavelength", None))
    try: print("u.Unit(units) ->", u.Unit(comp.units))
    except Exception as e: print("u.Unit(units) FAILS:", type(e).__name__, str(e)[:80])
    print("coords", type(d.coords).__name__, "world_axis_units", d.coords.world_axis_units, "names", d.coords.world_axis_names)
    print("has _wcs", hasattr(d.coords, "_wcs"), type(getattr(d.coords, "_wcs", None)).__name__)
    print("cube handle attrs:", [a for a in ("cube", "_cube", "source", "path", "_path") if hasattr(d, a)])
    nz, ny, nwl = d.shape
    wl = d.coords.pixel_to_world_values(np.arange(nwl), np.zeros(nwl), np.zeros(nwl))[0]
    wl_nm = (wl*u.m).to_value(u.nm)
    print("wavelength nm ->", wl_nm[[0,-1]])
    arr = d[cid].astype(float)
    mean = np.nanmean(arr, axis=(0,1)); i = int(np.argmax(mean)); bg = float(np.nanpercentile(mean,10))
    model = m.Const1D(amplitude=bg) + m.Gaussian1D(amplitude=float(mean[i])-bg, mean=wl_nm[i], stddev=0.005)
    t=time.perf_counter()
    fit = parallel_fit_dask(data=np.nan_to_num(arr.clip(min=0)), fitting_axes=2, world=(wl_nm,), model=model, fitter=LMLSQFitter(), scheduler="processes")
    print("fit from Data: %.2f s" % (time.perf_counter()-t), fit.amplitude_1.shape)
    resid = arr - fit(wl_nm[:, None, None]).transpose(1,2,0)
    print("residual", resid.shape, np.nanstd(resid))
    sl = SlicedLowLevelWCS(d.coords._wcs, (slice(None), slice(None), 0))
    g = _GlueWCS(sl)
    print("2D wcs pixel_n_dim", g.pixel_n_dim, g.world_axis_names, g.world_axis_units)
