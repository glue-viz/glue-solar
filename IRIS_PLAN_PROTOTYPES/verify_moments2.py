import warnings, glob, os, time, sys
warnings.simplefilter("ignore")
import numpy as np, astropy.units as u
from irispy.io import read_files
import irispy.data.test as t
from irispy.utils.moments import calculate_moments
from irispy.utils.red_blue import calculate_red_blue_asymmetry
from irispy.utils.density import density_diagnostic
from irispy.spectrograph import SpectrogramCube
from glue_solar.sources.loaders.iris import _cube_data, raster_data, image_data, _GlueWCS
from glue_solar.sources.loaders.stack_spectrograms import stack_spectrogram_sequence
from glue.core import DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink
import glue
from astropy.wcs.wcsapi import HighLevelWCSWrapper, BaseHighLevelWCS
print("glue from", glue.__file__)
base = os.path.dirname(t.__file__)
multi = sorted(glob.glob(f"{base}/raster/iris_l2_20140329_140938_3860258481_raster/*.fits"))
sns = [f"{base}/sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"]
seq = read_files(multi, spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"]
cube = seq[0]; mom = calculate_moments(cube)
sjif = f"{base}/raster/iris_l2_20230408_110821_3880012095_SJI_2796_t000.fits"

print("\nAUTOLINK with loader coords as-is")
print("  (maps, sji):", wcs_autolink(DataCollection([_cube_data(mom["intensity"], "maps"), image_data(sjif)])))
print("\nAUTOLINK with HighLevelWCSWrapper(_GlueWCS) on both")
def hl(d):
    d.coords = HighLevelWCSWrapper(d.coords); return d
for lab, pair in (("src3D,map2D", [raster_data(multi[:1], ["Mg II k 2796"])[0], _cube_data(mom["intensity"], "maps")]), ("map2D,sji", [_cube_data(mom["intensity"], "maps"), image_data(sjif)]), ("map2D,map2D", [_cube_data(mom["intensity"], "a"), _cube_data(mom["velocity"], "b")])):
    try:
        dc = DataCollection([hl(d) for d in pair]); links = wcs_autolink(dc)
        print(f"  {lab}: {links}")
        for l in links: print("     ", type(l).__name__, l.cids1, "<->", l.cids2)
    except Exception as e:
        print(f"  {lab}: {type(e).__name__}: {e}")

print("\nSTACK")
stack, times = stack_spectrogram_sequence(seq)
print("  stack:", type(stack).__name__, stack.shape, type(stack.meta).__name__)
try: calculate_moments(stack)
except Exception as e: print("  calculate_moments(stack) ->", type(e).__name__, e)
sc = SpectrogramCube(stack.data, stack.wcs, None, stack.unit, stack.meta, mask=stack.mask)
ms = calculate_moments(sc, rest_wavelength=seq[0].meta.rest_wavelength)
print("  wrapped OK wl_axis", sc.wavelength_axis, {k: c.shape for k, c in ms.items()}, ms["velocity"].wcs.world_axis_physical_types, "extra:", list(ms["velocity"].extra_coords.keys()) if ms["velocity"].extra_coords else None)
ds = _cube_data(ms["velocity"], "stack-v"); print("  ->Data", ds.shape, [str(w) for w in ds.world_component_ids], ds.coords.world_axis_units, [str(c) for c in ds.main_components])
single = calculate_moments(seq[0], rest_wavelength=seq[0].meta.rest_wavelength)["velocity"]
print("  scan0 == single:", np.allclose(np.asarray(ms["velocity"].data)[0], np.asarray(single.data), equal_nan=True))
print("  auto rest on wrapped (dict meta):", list(calculate_moments(sc).keys()))

print("\nRBA on 2021 sns Mg II k")
c21 = read_files(sns, spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"][0]
t0 = time.perf_counter(); rba = calculate_red_blue_asymmetry(c21); dt = time.perf_counter() - t0
print(f"  {dt:.2f}s keys={list(rba)} npx={c21.shape[0]*c21.shape[1]}")
for k, c in rba.items():
    d = _cube_data(c, f"rba-{k}")
    print(f"  {k}: {c.shape} unit={c.unit} dtype={np.asarray(c.data).dtype} types={c.wcs.world_axis_physical_types} meta={type(c.meta).__name__} extra={list(c.extra_coords.keys()) if c.extra_coords else None} -> Data world={[str(w) for w in d.world_component_ids]} {d.coords.world_axis_units} comps={[str(x) for x in d.main_components]}")
q = np.asarray(rba["quality"].data); print("  quality hist:", dict(zip(*[list(map(int, a)) for a in np.unique(q, return_counts=True)])), "finite rba:", int(np.isfinite(np.asarray(rba["red_blue_asymmetry"].data, dtype=float)).sum()))
t0 = time.perf_counter(); calculate_red_blue_asymmetry(c21, return_profiles=False); dt2 = time.perf_counter()-t0; print(f"  return_profiles=False: {dt2:.2f}s -> {dt2/q.size*1e6:.0f} us/px; 1096x400 est {dt2/q.size*1096*400:.0f}s")
try: calculate_red_blue_asymmetry(sc)
except Exception as e: print("  RBA on dict-meta cube ->", type(e).__name__, str(e)[:100])
# SGMeta without TWAVE (installed 0.8.1 path)
import copy
m = copy.copy(cube.meta); 
for k in list(m.keys()):
    if k.startswith("TWAVE"): del m[k]
c_notwave = SpectrogramCube(cube.data, cube.wcs, None, cube.unit, m, mask=cube.mask)
for f in (calculate_moments, calculate_red_blue_asymmetry):
    try: r = f(c_notwave); print(f"  {f.__name__} no-TWAVE SGMeta -> OK keys {list(r)}")
    except Exception as e: print(f"  {f.__name__} no-TWAVE SGMeta -> {type(e).__name__}: {str(e)[:80]}")

print("\nDENSITY")
try: density_diagnostic(np.ones(3), np.ones(3), np.logspace(9, 12, 10)/u.cm**3, ion=object(), numerator=1399.8*u.AA, denominator=1401.2*u.AA)
except Exception as e: print("  ->", type(e).__name__, e)
