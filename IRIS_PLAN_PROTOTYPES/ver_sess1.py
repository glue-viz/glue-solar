import os, sys, glob, io, pickle, warnings, json, traceback
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg")
warnings.simplefilter("ignore")
import numpy as np
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import image_data, raster_data, _GlueWCS
from glue.core import DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer, GlueSerializeError, saver, loader
from glue.core.visual import VisualAttributes
from astropy.wcs import WCS
import gwcs, asdf, astropy, ndcube
print("versions astropy", astropy.__version__, "asdf", asdf.__version__, "gwcs", gwcs.__version__, "ndcube", ndcube.__version__)
import asdf_astropy; print("asdf_astropy", asdf_astropy.__version__)

files = [str(f) for f in get_test_data_filenames()]
sji = [f for f in files if "sns/" in f and "SJI_1330" in f][0]
rdir = os.path.dirname([f for f in files if "3860258481_raster_t000_r00000" in f][0]); rfiles = sorted(glob.glob(rdir + "/*.fits"))[:3]
sji_d = image_data(sji); ras = raster_data(rfiles[:1])[0]; stk = raster_data(rfiles, stack=True)[0]
print("SJI inner:", type(sji_d.coords._wcs), "shape", sji_d.shape)
print("raster inner:", type(ras.coords._wcs), "ctype", ras.coords._wcs.wcs.ctype, "shape", ras.shape)
print("stack inner:", type(stk.coords._wcs), "shape", stk.shape)

w = ras.coords._wcs
print("\n== astropy -TAB export ==")
for name, fn in [("to_header_string", lambda: w.to_header_string()), ("to_header(relax)", lambda: str(w.to_header(relax=True))[:80]), ("to_fits", lambda: [h.name for h in w.to_fits()]), ("to_fits(relax)", lambda: [h.name for h in w.to_fits(relax=True)])]:
    try: print(name, "->", fn())
    except Exception as e: print(name, "-> EXC", type(e).__name__, str(e)[:120])
print("\n== pickle -TAB WCS ==")
try:
    b = pickle.dumps(w); w2 = pickle.loads(b)
    px = tuple(np.random.default_rng(1).uniform(0, n-1, 200) for n in ras.shape[::-1])
    a = w.pixel_to_world_values(*px); c = w2.pixel_to_world_values(*px)
    print("pickle OK", len(b), "bytes; p2w equal:", all(np.allclose(x, y, atol=0, rtol=0) for x, y in zip(a, c)), "ctype", w2.wcs.ctype)
except Exception as e: print("pickle EXC", type(e).__name__, str(e)[:200]); traceback.print_exc(limit=2)
print("\n== pickle compound (stack) ==")
try:
    b = pickle.dumps(stk.coords._wcs); w2 = pickle.loads(b); print("pickle compound OK", len(b), type(w2))
except Exception as e: print("pickle compound EXC", type(e).__name__, str(e)[:200])
print("\n== pickle gwcs ==")
try:
    b = pickle.dumps(sji_d.coords._wcs); w2 = pickle.loads(b); print("pickle gwcs OK", len(b), type(w2))
except Exception as e: print("pickle gwcs EXC", type(e).__name__, str(e)[:200])
print("\n== asdf-astropy on -TAB ==")
try:
    b = io.BytesIO(); asdf.AsdfFile({"wcs": w}).write_to(b); print("asdf -TAB write OK", len(b.getvalue()))
    with asdf.open(io.BytesIO(b.getvalue()), lazy_load=False, memmap=False) as af: w3 = af["wcs"]; print("asdf -TAB reload", type(w3), w3.wcs.ctype)
except Exception as e: print("asdf -TAB EXC", type(e).__name__, str(e)[:200])
print("\n== Tabprm attrs ==")
t = w.wcs.tab[0]; print([a for a in dir(t) if not a.startswith('_')]); print("coord shape", t.coord.shape, "K", t.K, "M", t.M, "map", t.map, "crval", t.crval)
print("wtb:", [(x.i, x.m, x.kind, x.extnam, x.extver, x.ttype, x.row, x.ndim) for x in w.wcs.wtb])

print("\n== prototype -TAB rebuild: FULL grid comparison ==")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sess_proto_savers as P
w4 = P.tab_from_bytes(P.tab_to_bytes(w))
grid = np.meshgrid(*[np.arange(n) for n in ras.shape[::-1]], indexing='ij')
a = w.pixel_to_world_values(*grid); c = w4.pixel_to_world_values(*grid)
print("full grid max abs diff per axis:", [float(np.nanmax(np.abs(x - y))) for x, y in zip(a, c)], "nan count", [int(np.isnan(x).sum()) for x in a], [int(np.isnan(y).sum()) for y in c])
# also compare at half-pixel offsets (interpolation)
grid2 = [g + 0.37 for g in grid]
a = w.pixel_to_world_values(*grid2); c = w4.pixel_to_world_values(*grid2)
print("offset grid max abs diff per axis:", [float(np.nanmax(np.abs(x - y))) for x, y in zip(a, c)])
print("rebuilt header PS/PV:", [(k, w4.to_header(relax=True).get(k)) for k in ("PS1_0","PS1_1","PS2_0","PS2_1","PS2_2","PS3_0","PS3_1","PS3_2","PV2_3","PV3_3")][:12])

print("\n== SJI: gwcs saver only + cmap=None, meta untouched ==")
d = image_data(sji); d.style.preferred_cmap = None
try:
    s = GlueSerializer(DataCollection([d])).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); print("OK", len(s)//1024, "KB; reloaded inner", type(dc2[0].coords._wcs), "meta", len(dc2[0].meta))
except Exception as e: print("EXC", type(e).__name__, str(e)[:200])

print("\n== raster: proto saver + drop only Quantity from meta (Time/SkyCoord kept) ==")
d = raster_data(rfiles[:1])[0]; d.style.preferred_cmap = None
import astropy.units as u
print("non-scalar meta:", {k: type(v).__name__ for k, v in d.meta.items() if not isinstance(v, (str, int, float, bool, type(None)))})
d.meta = {k: v for k, v in d.meta.items() if not isinstance(v, u.Quantity)}
try:
    s = GlueSerializer(DataCollection([d])).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); m = dc2[0].meta
    print("OK", len(s)//1024, "KB; reloaded meta", len(m), "of", len(d.meta), "; dropped:", [k for k in d.meta if k not in m]); print(" orbital phase type:", type(m.get('orbital phase')))
except Exception as e: print("EXC", type(e).__name__, str(e)[:200])

print("\n== version-2 VisualAttributes saver/loader workaround ==")
@saver(VisualAttributes, version=2)
def _save_style2(style, context):
    r = dict((a, getattr(style, a)) for a in style._atts); r['preferred_cmap'] = getattr(r['preferred_cmap'], 'name', r['preferred_cmap']); return r
@loader(VisualAttributes, version=2)
def _load_style2(rec, context):
    result = VisualAttributes()
    for attr in result._atts: setattr(result, attr, rec[attr])
    return result
d = image_data(sji)
try:
    s = GlueSerializer(DataCollection([d])).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); print("OK", len(s)//1024, "KB; cmap restored:", dc2[0].style.preferred_cmap, "protocol", json.loads(s)[[k for k,v in json.loads(s).items() if v.get('_type','').endswith('VisualAttributes')][0]]['_protocol'])
except Exception as e: print("EXC", type(e).__name__, str(e)[:200]); traceback.print_exc(limit=3)
