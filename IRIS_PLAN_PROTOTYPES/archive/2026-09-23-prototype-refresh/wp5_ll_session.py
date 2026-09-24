"""Does a line-list layer survive a glue session round trip? Synthetic spectrum only (IRIS data blocked by WP6)."""
import os, sys, warnings; warnings.simplefilter("ignore")
from glue.config import settings; settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp5_units  # noqa: F401
from wp5_linelist_mod import LineListArtist  # noqa: F401  (registers the maker, patches the style dict)
import numpy as np
from astropy.wcs import WCS
from glue.core import Data, DataCollection
from glue.core.data_factories import load_data
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
S = os.path.dirname(os.path.abspath(__file__))
w = WCS(naxis=1); w.wcs.ctype = ["WAVE"]; w.wcs.cunit = ["Angstrom"]; w.wcs.crval = [1330]; w.wcs.cdelt = [0.1]; w.wcs.crpix = [1]
spec = Data(label="spec", flux=np.random.random(100), coords=w); spec.meta["rest_wavelength"] = 1335.71
lines = load_data(os.path.join(S, "iris_lines.csv")); lines.label = "IRIS lines"
app = GlueApplication(DataCollection([spec, lines]))
v = app.new_data_viewer(ProfileViewer, data=spec)
v.state.x_att = spec.world_component_ids[0]; v.add_data(lines); v.state.x_display_unit = "km / s"
v.layers[1].state.color = "#00aa00"
print("before save: layers", [type(l).__name__ for l in v.layers], "| first line x:", round(v.layers[1].mpl_artists[0].get_xdata()[0], 2), flush=True)
path = os.path.join(S, "wp5_lines.glu")
app.save_session(path, include_data=True); print("saved", os.path.getsize(path), "bytes", flush=True)
app2 = GlueApplication.restore_session(path)
v2 = next(x for x in app2.viewers[0] if isinstance(x, ProfileViewer))
la = next(l for l in v2.layers if isinstance(l, LineListArtist))
print("restored: layers", [type(l).__name__ for l in v2.layers], "| x_display_unit", repr(v2.state.x_display_unit), "| artists:", len(la.mpl_artists), "| first line x:", round(la.mpl_artists[0].get_xdata()[0], 2), "| color:", la.state.color, "| _type in file:", "wp5_linelist_mod.LineListArtist" in open(path).read(), flush=True)
v2.state.x_display_unit = "Angstrom"; print("after reload unit switch -> first line x:", la.mpl_artists[0].get_xdata()[0], flush=True)
