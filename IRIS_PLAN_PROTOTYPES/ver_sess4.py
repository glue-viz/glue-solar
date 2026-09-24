import os, warnings; os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
import numpy as np, sunpy.map, astropy.units as u
from astropy.coordinates import SkyCoord
from sunpy.coordinates import frames
from glue.core import DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue_solar.sources.maps import read_sunpy_map
coord = SkyCoord(0*u.arcsec, 0*u.arcsec, obstime='2020-01-01', observer='earth', frame=frames.Helioprojective)
hdr = sunpy.map.make_fitswcs_header(np.random.rand(16, 16), coord, scale=[2, 2]*u.arcsec/u.pix, instrument='AIA', wavelength=171*u.angstrom, telescope='SDO')
d = read_sunpy_map(sunpy.map.Map(np.random.rand(16, 16), hdr)); d.style.preferred_cmap = None
s = GlueSerializer(DataCollection([d])).dumps(); dc2 = GlueUnSerializer.loads(s).object("__main__")
print("sunpy map, cmap=None: SAVE+RELOAD OK; meta", len(dc2[0].meta), "of", len(d.meta), "coords", type(dc2[0].coords).__name__, "p2w equal", np.allclose(dc2[0].coords.pixel_to_world_values(3,4), d.coords.pixel_to_world_values(3,4)))
