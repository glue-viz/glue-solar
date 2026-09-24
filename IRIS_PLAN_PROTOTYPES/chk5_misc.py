"""Checker: rest_wavelength on a SpectrogramCube (stack branch input), y-choice pollution, install() idempotency."""
import warnings; warnings.simplefilter("ignore")
from glue.config import settings; settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp5_units; from wp5_units import rest_wavelength, IRISUnitConverter
import astropy.units as u, numpy as np
from irispy.io import read_files
from glue.core import Data, DataCollection
from glue.core.component import Component
from glue.config import unit_converter
from glue_solar.sources.loaders.iris import raster_data
P = lambda *a: print(*a, flush=True)
base = "/Users/nabil/Git/glue-solar/.venv/lib/python3.14/site-packages/irispy/data/test/"
f14 = [base + f"raster/iris_l2_20140329_140938_3860258481_raster/iris_l2_20140329_140938_3860258481_raster_t000_r0000{n}.fits" for n in range(3)]
coll = read_files(f14, spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)
for window, sequence in coll.items():
    P("window:", window, "| sequence[0]:", type(sequence[0]).__name__, "| meta:", type(sequence[0].meta).__name__, "| rest_wavelength(sequence[0]):", rest_wavelength(sequence[0]))
stack = raster_data(f14, ["Mg II k 2796"], stack=True)[0]
P("stack label:", stack.label, "| meta type:", type(stack.meta).__name__, "| 'rest_wavelength' in meta:", "rest_wavelength" in stack.meta)
# y-choice pollution
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from glue.viewers.profile.state import ProfileViewerState
import wp5_linelist_mod  # noqa
f21 = base + "sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
for units in ("", "Angstrom"):
    lines = Data(label="lines"); lines.add_component(Component(np.array([1334.53, 1335.71]), units=units), "wavelength"); lines.add_component(np.array(["a", "b"]), "name")
    d2 = raster_data([f21], ["C II 1336"])[0]
    app = GlueApplication(DataCollection([d2, lines]))
    v = app.new_data_viewer(ProfileViewer, data=d2); v.state.x_att = next(c for c in d2.world_component_ids if c.label == "Wavelength")
    v.add_data(lines)
    P(f"wavelength column units={units!r} -> y_display_unit choices:", ProfileViewerState.y_display_unit.get_choices(v.state))
    v.close(warn=False); app.close()
# install() idempotency (scratch modules stand in for glue_solar.viewers.install)
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile.data_viewer import ProfileViewer as PV
import wp5_blink  # noqa: registers image:blink once (module runs its own demo; ignore)
