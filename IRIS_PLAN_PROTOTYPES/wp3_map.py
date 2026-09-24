import os, sys, json, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, astropy.units as u, sunpy.map, wp3_impl
from astropy.coordinates import SkyCoord
from sunpy.coordinates import frames
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue_solar.sources.maps import read_sunpy_map
coord = SkyCoord(0 * u.arcsec, 0 * u.arcsec, obstime="2020-01-01", observer="earth", frame=frames.Helioprojective)
hdr = sunpy.map.make_fitswcs_header(np.zeros((16, 16)), coord, scale=[2, 2] * u.arcsec / u.pix, instrument="AIA", wavelength=171 * u.angstrom, telescope="SDO")
m = read_sunpy_map(sunpy.map.Map(np.random.default_rng(0).random((16, 16)), hdr))
dc = DataCollection([m, Data(x=[1, 2, 3], label="plain")])
s = GlueSerializer(dc).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__"); m2 = dc2[0]
grid = np.meshgrid(np.arange(16), np.arange(16), indexing="ij")
print("sunpy AIA map:", len(s) // 1024, "KB | style", type(m2.style).__name__, "| cmap", m2.style.preferred_cmap.name, "| coords", type(m2.coords).__name__,
      "| p2w maxdiff", max(float(np.nanmax(np.abs(a - b))) for a, b in zip(m.coords.pixel_to_world_values(*grid), m2.coords.pixel_to_world_values(*grid))),
      "| meta", len(m2.meta), "of", len(m.meta), "| data equal", np.array_equal(m2[m2.main_components[0]], m[m.main_components[0]]))
styles = {v["label"]: v["style"] for v in json.loads(s).values() if isinstance(v, dict) and "style" in v}
for label, st in styles.items(): print(f"  style record of {label!r}: _type={st['_type']} _protocol={st.get('_protocol')} preferred_cmap={st['preferred_cmap']!r}")
