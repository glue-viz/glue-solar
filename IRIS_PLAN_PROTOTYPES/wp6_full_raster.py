"""Full-raster timing through the glue-solar path (raster_data -> gaussian_fit_data) on the gallery raster."""
import sys, time, glob, warnings; warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
from glue_solar.sources.loaders.iris import raster_data
from wp6_fitting import gaussian_fit_data
f = sorted(glob.glob("/Users/nabil/DATA/IRIS/561757a1b84e36def2ed9e2d89103117-iris_l2_20180102_153155_3610108077_raster/*.fits"))[0]
if __name__ == "__main__":
    for win, n, schedulers in (("Si IV 1403", 1, ("processes", "single-threaded")), ("Mg II k 2796", 2, ("processes",))):
        t = time.perf_counter(); d = raster_data([f], [win])[0]; print(f"{win}: {d.label} {d.shape} loaded in {time.perf_counter()-t:.1f} s", flush=True)
        for s in schedulers:
            t = time.perf_counter(); maps, resid = gaussian_fit_data(d, n, None, s); dt = time.perf_counter() - t
            cen = maps["centroid" if n == 1 else "centroid 1"]; nspec = cen.size
            print(f"  n={n} {s:16s} {dt:7.1f} s ({1e3*dt/nspec:.2f} ms/spec, {nspec} spectra x {d.shape[-1]} px) nan={np.isnan(cen).sum()} ({100*np.isnan(cen).mean():.2f}%) centroid median={np.nanmedian(cen):.3f} A", flush=True)
