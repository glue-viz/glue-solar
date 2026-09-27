"""Warm-cache wall time of glue-solar main's per-pick loaders (what QtIRISImporter.finalize runs on the GUI thread)."""
import resource, sys, time, warnings
sys.path.insert(0, "<session-scratch>/tools")
import qs_isolate  # noqa
warnings.simplefilter("ignore")
from glob import glob
import glue_solar.sources.loaders.iris as L
R = "~/DATA/IRIS/"
cases = [
    ("SJI 1400 sns .fits.gz (400x417x388)", lambda: L.image_data(R + "534d789bb0a2821fb2b78eb36d1d6753-iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz")),
    ("SJI 2796 deconv .fits.gz (32x771x1506)", lambda: L.image_data(R + "c844c41797b93a28fbad181337864edd-iris_l2_20130902_182935_4000005156_SJI_2796_t000_deconvolved.fits.gz")),
    ("raster sns Si IV 1403 (1600x417x262)", lambda: L.raster_data(sorted(glob(R + "2dd2d12db374b3466aa27a65bec235d3-*/*.fits")), ["Si IV 1403"])),
    ("raster 3824262996 Mg II k (400x1095x537)", lambda: L.raster_data(sorted(glob(R + "c7600db2087c0f285587e416a9e55e3d-*/*.fits")), ["Mg II k 2796"])),
    ("raster 4000005156 Si IV, all scans", lambda: L.raster_data(sorted(glob(R + "0598beef2a051b4f371a4b09e439c4e4-*/*.fits")), ["Si IV 1403"])),
    ("raster 4000005156 Si IV, all scans stacked", lambda: L.raster_data(sorted(glob(R + "0598beef2a051b4f371a4b09e439c4e4-*/*.fits")), ["Si IV 1403"], stack=True)),
]
for name, fn in cases:
    fn()  # warm the page cache
    t = time.perf_counter(); out = fn(); dt = time.perf_counter() - t
    out = out if isinstance(out, list) else [out]
    print(f"{name}: {dt:.2f}s, {len(out)} dataset(s), {sum(d.size for d in out)/1e6:.0f} M elements, peak RSS so far {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**30:.1f} GB", flush=True)
