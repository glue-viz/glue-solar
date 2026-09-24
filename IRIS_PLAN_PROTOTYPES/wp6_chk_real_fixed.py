"""Real-file checks for WP6 on the bundled irispy rasters: units, timings, NaNs, stack, bad copy."""
import sys, time, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
from irispy.data.test import get_test_data_filenames
from glue.core import DataCollection
from glue_solar.sources.loaders.iris import raster_data
from wp6_fitting import fit_gaussians, gaussian_fit_data, add_fit_products, wavelength_angstrom

files = [str(f) for f in get_test_data_filenames()]
sns = [f for f in files if "/sns/" in f and "raster" in f][0]
bad = [f for f in files if "/raster/iris_l2_20210905" in f][0]
r2014 = sorted(f for f in files if "3860258481_raster_t000_r" in f)

def twave(d):
    rest = getattr(d.meta, "rest_wavelength", None)
    return None if rest is None else float(rest.to_value("Angstrom"))

def timed(label, data, n, scheduler, rest=None):
    t = time.perf_counter()
    maps, resid = gaussian_fit_data(data, n, rest, scheduler)
    dt = time.perf_counter() - t
    nspec = int(np.prod(data.shape[:-1]))
    cen = maps["centroid" if n == 1 else "centroid 1"]
    print(f"  {label:34s} n={n} {scheduler:16s} {dt:6.2f} s ({1e3*dt/nspec:.2f} ms/spec) nan={np.isnan(cen).sum():3d} centroid median={np.nanmedian(cen):.3f} A")
    return maps, resid

if __name__ == "__main__":
    print("bad copy under raster/:")
    try:
        raster_data([bad], ["Si IV 1403"])
    except Exception as e:
        print("  ", type(e).__name__, str(e)[:90])
    d = raster_data([sns], ["Si IV 1403"])[0]
    cid = d.main_components[0]
    print("sns Si IV:", d.label, d.shape, "units", d.get_component(cid).units, "world_axis_units", d.coords.world_axis_units)
    wl = wavelength_angstrom(d)
    print("  wavelength A:", wl[[0, -1]], "step", np.diff(wl).mean(), "rest (TWAVE) A:", twave(d), "-> outside window, argmax seed used")
    wrong = d.coords.pixel_to_world_values(0, 0, np.arange(d.shape[-1]))[0]
    print("  WRONG order (wavelength index last): unique =", np.unique(np.asarray(wrong)))
    for s in ("single-threaded", "threads", "processes"):
        maps, resid = timed("sns Si IV 1403 (187,40,29)", d, 1, s)
    print("  maps:", maps.label, maps.shape, [(c.label, maps.get_component(c).units) for c in maps.main_components])
    print("  maps world:", [c.label for c in maps.world_component_ids], maps.coords.world_axis_units)
    print("  residual", resid.shape, "rms", float(np.sqrt(np.nanmean(resid**2))))
    dc = DataCollection([d]); add_fit_products(d, dc, maps, resid)
    print("  dc:", [x.label for x in dc], "links:", len(dc.links), "source comps:", [c.label for c in d.main_components])
    mg = raster_data([sns], ["Mg II k 2796"])[0]
    print("sns Mg II k:", mg.shape, "rest A:", twave(mg), "window", wavelength_angstrom(mg)[[0, -1]])
    for s in ("single-threaded", "processes"):
        timed("sns Mg II k (187,40,52)", mg, 2, s)
    timed("sns Mg II k (187,40,52)", mg, 1, "single-threaded")
    d14 = raster_data(r2014[:1], ["Si IV 1403"])[0]
    print("2014 r00000 Si IV:", d14.label, d14.shape)
    for s in ("single-threaded", "processes"):
        timed("2014 Si IV 1403 (8,109,29)", d14, 1, s)
    # scaling: tile the sns cube 4x (29920 spectra) to see the processes gain beyond pool start-up
    big = np.tile(d[cid], (4, 1, 1))
    for s in ("single-threaded", "processes"):
        t = time.perf_counter(); fit, _ = fit_gaussians(big, wl, 1, scheduler=s); dt = time.perf_counter() - t
        print(f"  tiled x4 {big.shape} n=1 {s:16s} {dt:6.2f} s ({1e3*dt/big[...,0].size:.2f} ms/spec)")
    # 4D stack: generic code path (fitting_axes = ndim-1, sliced compound WCS, 3 links)
    st = raster_data(r2014, ["C II 1336"], stack=True)[0]
    print("stack:", st.label, st.shape, "meta type", type(st.meta).__name__, "rest:", twave(st))
    try:
        t = time.perf_counter(); maps, resid = gaussian_fit_data(st, 1, None, "single-threaded"); dt = time.perf_counter() - t
        print(f"  stack fit {dt:.2f} s maps {maps.shape} world {[c.label for c in maps.world_component_ids]} {maps.coords.world_axis_units} nan={np.isnan(maps['centroid']).sum()}")
        dc = DataCollection([st]); add_fit_products(st, dc, maps, resid); print("  stack links:", len(dc.links))
    except Exception as e:
        print("  stack FAILS:", type(e).__name__, str(e)[:200])
