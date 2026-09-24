import time, warnings; warnings.simplefilter("ignore")
import numpy as np, astropy.units as u
from astropy.modeling import models as m
from astropy.modeling.fitting import LMLSQFitter, TRFLSQFitter, parallel_fit_dask
from irispy.io import read_files
from irispy.data.test import get_test_data_filenames
def main():
    f = [str(x) for x in get_test_data_filenames() if str(x).endswith("sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")][0]
    cube = read_files(f, spectral_windows=["Si IV 1403"], memmap=False, uncertainty=False)["Si IV 1403"][0]
    wl = cube.axis_world_coords("em.wl")[0].to(u.nm)
    data = np.nan_to_num(cube.data.clip(min=0))
    # identical seed for all variants: irispy-style prefit on the raw (unclipped) spatial mean
    sm = cube.rebin((*cube.data.shape[:-1], 1))[0, 0, :]
    core = wl[int(np.nanargmax(np.nan_to_num(sm.data)))]; win = np.abs(wl - core) < 0.02 * u.nm
    init = m.Const1D(amplitude=np.nanpercentile(sm.data[~win], 10) * cube.unit) + m.Gaussian1D(amplitude=np.nanmax(sm.data[win]) * cube.unit, mean=core, stddev=0.005 * u.nm)
    avg = TRFLSQFitter()(init, wl, sm.data * sm.unit)
    print("cube.unit =", repr(cube.unit), "seed:", avg.parameters)
    plain = m.Const1D(amplitude=avg.amplitude_0.value) + m.Gaussian1D(amplitude=avg.amplitude_1.value, mean=avg.mean_1.value, stddev=avg.stddev_1.value)
    dn = u.def_unit("DN")
    dnm = m.Const1D(amplitude=avg.amplitude_0.value * dn) + m.Gaussian1D(amplitude=avg.amplitude_1.value * dn, mean=avg.mean_1.value * u.nm, stddev=avg.stddev_1.value * u.nm)
    for label, kw in [("DN_IRIS_FUV unit", dict(data_unit=cube.unit, world=(wl,), model=avg)),
                      ("def_unit DN", dict(data_unit=dn, world=(wl,), model=dnm)),
                      ("plain floats", dict(world=(wl.value,), model=plain))]:
        t0 = time.perf_counter()
        fit = parallel_fit_dask(data=data, fitting_axes=2, fitter=LMLSQFitter(), scheduler="single-threaded", **kw)
        print(f"{label:18s} single-threaded {time.perf_counter()-t0:6.2f}s  mean_1 median={np.nanmedian(fit.mean_1.value):.4f} nan={np.isnan(fit.mean_1.value).sum()}")
if __name__ == "__main__":
    main()
