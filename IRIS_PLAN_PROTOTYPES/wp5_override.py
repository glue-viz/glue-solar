"""WP5 (a) optional: per-dataset rest-wavelength override as a glue-qt layer_action (right-click on a dataset)."""
import warnings; warnings.simplefilter("ignore")
from glue.config import settings; settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wp5_units import rest_wavelength  # noqa: F401  (installs the converter)
import astropy.units as u
from glue.core.message import NumericalDataChangedMessage
from glue_qt.config import layer_action
from qtpy import QtWidgets


# ---------------------------------------------------------------- the code that ships (glue_solar/viewers.py)
@layer_action("Set rest wavelength…", single=True, data=True)
def set_rest_wavelength(data, data_collection, value=None):
    """Store a rest wavelength (Angstrom) on ``data.meta`` and refresh open viewers."""
    current = rest_wavelength(data)
    if value is None:
        value, ok = QtWidgets.QInputDialog.getDouble(
            None, "Rest wavelength", "Rest wavelength [Angstrom] (0 removes the override):",
            0.0 if current is None else current.to_value(u.AA), 0.0, 1e5, 3)
        if not ok:
            return
    if value:
        data.meta["rest_wavelength"] = float(value)
    else:
        data.meta.pop("rest_wavelength", None)
    if data.hub is not None:
        data.hub.broadcast(NumericalDataChangedMessage(data))  # profile layers recompute (common/viewer.py:288-293)
# ---------------------------------------------------------------- end of shipping code

from glue.core import DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
f = next(str(p) for p in get_test_data_filenames() if p.name == "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
d = raster_data([f], ["Mg II k 2796"])[0]
print("registered:", [a.label for a in layer_action if a.label.startswith("Set rest")], "| callback signature: (layer, data_collection)", flush=True)
app = GlueApplication(DataCollection([d]))
v = app.new_data_viewer(ProfileViewer, data=d)
v.state.x_att = next(c for c in d.world_component_ids if c.label == "Wavelength")
v.state.x_display_unit = "km / s"
x0 = v.layers[0].state.profile[0][0]
set_rest_wavelength(d, app.data_collection, value=2796.35)       # what the dialog would return
x1 = v.layers[0].state.profile[0][0]
print(f"TWAVE rest -> x[0] = {x0:.2f} km/s; override 2796.35 -> x[0] = {x1:.2f} km/s; shift {x1 - x0:+.2f} km/s", flush=True)
set_rest_wavelength(d, app.data_collection, value=0)
print("override removed -> rest_wavelength(data):", rest_wavelength(d), "| x[0] back:", round(float(v.layers[0].state.profile[0][0]), 2), flush=True)
