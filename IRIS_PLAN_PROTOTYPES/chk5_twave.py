"""Checker: TWAVE vs literature, missing TWAVE, DN unit string, y-choice pollution by a unit-carrying wavelength column."""
import warnings; warnings.simplefilter("ignore")
from glue.config import settings; settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wp5_units import rest_wavelength  # installs converter
import astropy.units as u
from astropy.io import fits
from irispy.data.test import get_test_data_filenames
from glue.core.units import find_unit_choices
from glue_solar.sources.loaders.iris import raster_data
P = lambda *a: print(*a, flush=True)
files = {p.name: str(p) for p in get_test_data_filenames()}
lit = {"Mg II k": 2796.35, "Si IV 1394": 1393.76, "Si IV 1403": 1402.77, "C II 1336": 1335.71, "O I 1356": 1355.60}
seen = {}
for name, path in sorted(files.items()):
    if "raster" not in name: continue
    h = fits.getheader(path, 0)
    for i in range(1, h.get("NWIN", 0) + 1):
        desc = h.get(f"TDESC{i}"); tw = h.get(f"TWAVE{i}")
        for key, val in lit.items():
            if desc and desc.startswith(key) and key not in seen and tw is not None:
                seen[key] = (tw, val, ((tw - val) / val * 299792.458))
for key, (tw, val, dv) in seen.items():
    P(f"{key:12s} TWAVE={tw:.4f} lit={val:.2f} -> zero-point offset {dv:+.1f} km/s")
# missing TWAVE
d = raster_data([files["iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"]], ["Mg II k 2796"])[0]
wl = next(c for c in d.world_component_ids if c.label == "Wavelength")
P("meta type:", type(d.meta).__name__, "| _iwin:", d.meta._iwin, "| TWAVE key:", f"TWAVE{d.meta._iwin}", "=", d.meta.get(f"TWAVE{d.meta._iwin}"))
del d.meta[f"TWAVE{d.meta._iwin}"]
try:
    d.meta.rest_wavelength
except Exception as e:
    P("SGMeta.rest_wavelength without TWAVE raises", type(e).__name__, e)
P("helper without TWAVE ->", rest_wavelength(d))
P("choices without TWAVE:", find_unit_choices([(d, wl, "m")]))
# DN unit string
dn = d.main_components[0]
P("data unit string:", repr(d.get_component(dn).units))
try:
    u.Unit(d.get_component(dn).units)
except ValueError as e:
    P("-> ValueError (caught by find_unit_choices):", str(e)[:60])
P("y choices for DN component:", find_unit_choices([(d, dn, d.get_component(dn).units)]))
# y-choice pollution: line list with a unit-carrying wavelength column
import numpy as np
from glue.core import Data, DataCollection
from glue.core.component import Component
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from glue.viewers.profile.state import ProfileViewerState
import wp5_linelist_mod  # noqa
for units in ("", "Angstrom"):
    lines = Data(label="lines"); lines.add_component(Component(np.array([1334.53, 1335.71]), units=units), "wavelength"); lines.add_component(np.array(["a", "b"]), "name")
    d2 = raster_data([files["iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"]], ["C II 1336"])[0]
    app = GlueApplication(DataCollection([d2, lines]))
    v = app.new_data_viewer(ProfileViewer, data=d2); v.state.x_att = next(c for c in d2.world_component_ids if c.label == "Wavelength")
    v.add_data(lines)
    P(f"wavelength column units={units!r} -> y_display_unit choices:", ProfileViewerState.y_display_unit.get_choices(v.state))
    v.close(warn=False); app.close()
P("DONE")
