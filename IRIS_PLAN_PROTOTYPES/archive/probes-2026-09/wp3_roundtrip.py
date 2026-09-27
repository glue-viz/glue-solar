import os, sys, glob, json, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, astropy.units as u, sunpy.map
from astropy.coordinates import SkyCoord
from sunpy.coordinates import frames
import wp3_impl
from irispy.data.test import get_test_data_filenames
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue_solar.sources.loaders.iris import image_data, raster_data, _GlueWCS
from glue_solar.sources.maps import read_sunpy_map
import glue, astropy, asdf, gwcs, ndcube, irispy
print("versions:", {m.__name__: m.__version__ for m in (glue, astropy, asdf, gwcs, ndcube, irispy)})
files = [str(f) for f in get_test_data_filenames()]
sji = [f for f in files if "sns/" in f and "SJI_1330" in f][0]
rdir = os.path.dirname([f for f in files if "3860258481_raster_t000_r00000" in f][0]); rfiles = sorted(glob.glob(rdir + "/*.fits"))[:3]
sns_raster = [f for f in files if "sns/" in f and "raster" in f][0]

def roundtrip(label, data, w2p_atol=1e-5, **kw):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dc = data if isinstance(data, DataCollection) else DataCollection([data]); data = dc[0]
        s = GlueSerializer(dc, **kw).dumps()
        dc2 = GlueUnSerializer.loads(s).object("__main__"); d2 = dc2[0]
    grid = np.meshgrid(*[np.arange(n) for n in data.shape[::-1]], indexing="ij")
    for name, g in (("grid", grid), ("grid+0.37", [x + 0.37 for x in grid])):
        a = data.coords.pixel_to_world_values(*g); b = d2.coords.pixel_to_world_values(*g)
        diff = [float(np.nanmax(np.abs(x - y))) for x, y in zip(a, b)]
        assert max(diff) <= 1e-9, (label, name, diff)
        assert [int(np.isnan(x).sum()) for x in a] == [int(np.isnan(y).sum()) for y in b]
    world = data.coords.pixel_to_world_values(*grid)
    w2p = max(float(np.nanmax(np.abs(x - y))) for x, y in zip(data.coords.world_to_pixel_values(*world), d2.coords.world_to_pixel_values(*world)))
    assert w2p <= 1e-9, (label, w2p)  # restored inverse agrees with the original inverse
    closure = max(float(np.nanmax(np.abs(x - y))) for x, y in zip(grid, d2.coords.world_to_pixel_values(*world)))
    assert closure <= w2p_atol, (label, closure)  # wcslib's iterative -TAB inverse is ~1e-6 px, same on the original
    assert d2.coords.world_axis_names == data.coords.world_axis_names and d2.coords.world_axis_units == data.coords.world_axis_units
    assert [c.label for c in d2.world_component_ids] == [c.label for c in data.world_component_ids]
    print(f"{label}: {len(s) // 1024} KB | coords {type(d2.coords).__name__}({type(d2.coords._wcs).__name__}) | p2w<=1e-9 on {grid[0].size} px | w2p orig-vs-restored {w2p:.1e} (p2w->w2p closure {closure:.1e}) | meta {len(d2.meta)}/{len(data.meta)} | cmap {getattr(d2.style.preferred_cmap, 'name', None)} | caught {sorted({type(c.message).__name__ for c in caught})}")
    return s, dc2

print("-- browser path (arrays embedded) --")
s, _ = roundtrip("SJI_1330 (gwcs via asdf)", image_data(sji))
j = json.loads(s); coords = [v for v in j.values() if isinstance(v, dict) and v.get("_type", "").endswith("_GlueWCS")][0]
print("   coords record:", {k: (v if k != "wcs" else {kk: (vv if kk != 'b64' else f'<{len(vv)} chars b64 asdf>') for kk, vv in v.items()}) for k, v in coords.items()})
style = [v["style"] for v in j.values() if isinstance(v, dict) and "style" in v][0]; print("   style record (inline in the Data record):", style)
roundtrip("SJI_1400 3880012095 (raster/ dir)", image_data([f for f in files if "3880012095_SJI_1400" in f][0]))
ras = raster_data(rfiles[:1])[0]
s, dc_ras2 = roundtrip("raster C II 1336 (-TAB rebuild)", ras); ras2 = dc_ras2[0]
print("   meta Quantity round trip:", {k: (type(v).__name__, np.shape(v), str(getattr(v, 'unit', ''))) for k, v in ras2.meta.items() if isinstance(v, u.Quantity)},
      "| equal:", all(np.array_equal(ras.meta[k], ras2.meta[k]) for k in ras.meta if isinstance(ras.meta[k], u.Quantity)),
      "| dropped:", [k for k in ras.meta if k not in ras2.meta])
print("   Time component intact:", np.array_equal(ras2["Time"], ras["Time"]), ras2["Time"].dtype)
roundtrip("raster C II 1336 saved AGAIN from the restored dataset", dc_ras2)
print("   pixel_shape after reload:", ras2.coords._wcs.pixel_shape)
roundtrip("sit-and-stare raster 3620258102 C II 1336", raster_data([sns_raster], ["C II 1336"])[0])
stk = raster_data(rfiles, stack=True)[0]
s, dc_stk2 = roundtrip("stack 3 scans (compound + sliced + -TAB)", stk); stk2 = dc_stk2[0]
print("   stack Time intact:", np.array_equal(stk2["Time"], stk["Time"]), "| mask intact:", np.array_equal(stk2[f"{stk.label} mask"], stk[f"{stk.label} mask"]))
roundtrip("stack saved AGAIN from the restored dataset", dc_stk2)
print("-- sunpy Map (glue_solar.sources.maps) --")
coord = SkyCoord(0 * u.arcsec, 0 * u.arcsec, obstime="2020-01-01", observer="earth", frame=frames.Helioprojective)
hdr = sunpy.map.make_fitswcs_header(np.zeros((16, 16)), coord, scale=[2, 2] * u.arcsec / u.pix, instrument="AIA", wavelength=171 * u.angstrom, telescope="SDO")
m = read_sunpy_map(sunpy.map.Map(np.random.default_rng(0).random((16, 16)), hdr))
s, dc_m2 = roundtrip("sunpy AIA map", m); m2 = dc_m2[0]
print("   map meta keys", len(m2.meta), "of", len(m.meta), "| style type", type(m2.style).__name__)
print("-- plain glue Data in the same environment keeps the stock style record --")
plain = Data(x=[1, 2, 3], label="plain"); s = GlueSerializer(DataCollection([plain])).dumps()
print("   ", [v["style"] for v in json.loads(s).values() if isinstance(v, dict) and "style" in v][0])
print("ALL ROUND TRIPS OK")
