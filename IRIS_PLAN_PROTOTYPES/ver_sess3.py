import os, warnings; os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
import numpy as np, sunpy.map, astropy.units as u
from astropy.coordinates import SkyCoord
from sunpy.coordinates import frames
from glue.core import DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
import glue_solar.sources.maps as M
print([n for n in dir(M) if not n.startswith('_')])
coord = SkyCoord(0*u.arcsec, 0*u.arcsec, obstime='2020-01-01', observer='earth', frame=frames.Helioprojective)
hdr = sunpy.map.make_fitswcs_header(np.random.rand(16, 16), coord, scale=[2, 2]*u.arcsec/u.pix, instrument='AIA', wavelength=171*u.angstrom, telescope='SDO')
m = sunpy.map.Map(np.random.rand(16, 16), hdr)
fn = [getattr(M, n) for n in dir(M) if not n.startswith('_') and callable(getattr(M, n)) and 'map' in n.lower()]
print("loader candidates:", [f.__name__ for f in fn])
import inspect; print(inspect.getsource(M).count('def '))
# call the sunpy-map->Data converter directly
src = inspect.getsource(M)
import re; conv = [n for n in re.findall(r'def (\w+)\(', src)]; print("defs:", conv)
d = None
for n in conv:
    f = getattr(M, n)
    try:
        d = f(m); print("converted via", n, type(d)); break
    except Exception as e: print(n, "->", type(e).__name__, str(e)[:80])
if d is not None:
    if isinstance(d, list): d = d[0]
    print("meta type", type(d.meta), "coords", type(d.coords).__name__, "cmap", type(d.style.preferred_cmap).__name__)
    try:
        s = GlueSerializer(DataCollection([d])).dumps(); print("SAVE OK", len(s)//1024, "KB")
    except Exception as e: print("SAVE FAIL:", type(e).__name__, str(e)[:120])
    d.style.preferred_cmap = None
    try:
        s = GlueSerializer(DataCollection([d])).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); print("cmap=None: SAVE+RELOAD OK; meta keys", len(dc2[0].meta), "coords", type(dc2[0].coords).__name__)
    except Exception as e: print("cmap=None SAVE FAIL:", type(e).__name__, str(e)[:120])
