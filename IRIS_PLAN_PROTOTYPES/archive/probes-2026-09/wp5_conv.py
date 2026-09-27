"""WP5 (a): velocity display units. Final-form converter, run against real irispy test files.

Covers: SGMeta rest wavelength, meta['rest_wavelength'] override (float Angstrom), 4-D stack
(plain dict meta, loader-side key), choice pruning, ROI round trip, refresh after override,
and the post-WP1 world where the native wavelength unit is Angstrom (simulated by a _GlueWCS
subclass that maps em.wl to Angstrom with the same pattern used for arcsec).
"""
import warnings; warnings.simplefilter("ignore")
import numpy as np
from glue.config import settings, unit_converter
settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
import astropy.units as u
from glue.core import DataCollection
from glue.core.message import NumericalDataChangedMessage
from glue.core.units import SimpleAstropyUnitConverter, UnitConverter, find_unit_choices
from glue.viewers.profile.state import ProfileViewerState
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import _GlueWCS, raster_data
P = lambda *a: print(*a, flush=True)

import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wp5_units import IRISUnitConverter, rest_wavelength  # noqa: E402  (installs itself as members['default'])


class _AngstromWCS(_GlueWCS):
    """Stand-in for WP1/D3: wavelength axis presented in Angstrom instead of metres."""

    @property
    def world_axis_units(self):
        return tuple("Angstrom" if pt == "em.wl" else unit
                     for unit, pt in zip(super().world_axis_units, self._wcs.world_axis_physical_types))

    def pixel_to_world_values(self, *pixel_arrays):
        values = list(super().pixel_to_world_values(*pixel_arrays))
        for i, pt in enumerate(self.world_axis_physical_types):
            if pt == "em.wl":
                values[i] = (np.asarray(values[i]) * u.Unit(self._wcs.world_axis_units[i])).to_value(u.AA)
        return tuple(values)

    def world_to_pixel_values(self, *world_arrays):
        values = list(world_arrays)
        for i, pt in enumerate(self.world_axis_physical_types):
            if pt == "em.wl":
                values[i] = (np.asarray(values[i]) * u.AA).to_value(u.Unit(self._wcs.world_axis_units[i]))
        return super().world_to_pixel_values(*values)


files = sorted(str(p) for p in get_test_data_filenames() if "20140329" in p.name and p.name.endswith((".fits")))
d = raster_data(files[:1], ["Mg II k 2796"])[0]
wl = next(c for c in d.world_component_ids if c.label == "Wavelength")
P("native units today:", repr(d.get_component(wl).units), "| rest_wavelength(data):", rest_wavelength(d))
P("pruned choices (m):", find_unit_choices([(d, wl, "m")]))
lat = next(c for c in d.world_component_ids if c.label == "Helioprojective Latitude")
P("pruned choices (arcsec):", find_unit_choices([(d, lat, "arcsec")]))
P("settings.UNIT_CONVERTER still:", settings.UNIT_CONVERTER)

# --- post-WP1 world: Angstrom native
d.coords = _AngstromWCS(d.coords._wcs)
wl = next(c for c in d.world_component_ids if c.label == "Wavelength")
P("native units after D3:", repr(d.get_component(wl).units), "| choices:", find_unit_choices([(d, wl, "Angstrom")]))

from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
app = GlueApplication(DataCollection([d]))
v = app.new_data_viewer(ProfileViewer, data=d)
v.state.x_att = wl
P("x_display_unit choices:", ProfileViewerState.x_display_unit.get_choices(v.state))
x, _ = v.layers[0].state.profile
P("x native Angstrom [:2]:", x[:2], "| xlim:", (v.state.x_min, v.state.x_max))
v.state.x_display_unit = "km / s"
x, _ = v.layers[0].state.profile
P("x km/s [:2]:", x[:2], "| xlim:", (round(v.state.x_min, 2), round(v.state.x_max, 2)), "| axis label:", v.state.x_axislabel)
# ROI round trip: apply_roi converts display -> native through to_native (profile/viewer.py:48-51)
from glue.core.roi import XRangeROI
v.apply_roi(XRangeROI(-50, 50))
ss = d.subsets[0].subset_state
P("ROI -50..50 km/s -> native subset range (Angstrom):", (round(ss.lo, 3), round(ss.hi, 3)), "att:", ss.att.label)
P("expected from doppler_optical:", [round(float((x * u.km / u.s).to_value(u.AA, u.doppler_optical(rest_wavelength(d)))), 3) for x in (-50, 50)])
# override: literature Mg II k 2796.35 instead of TWAVE 2796.20, then refresh the profile layers
d.meta["rest_wavelength"] = 2796.35
d.hub.broadcast(NumericalDataChangedMessage(d))
x2, _ = v.layers[0].state.profile
P("after override + NumericalDataChangedMessage: x km/s [:2]:", x2[:2], "| shift:", round(float(x2[0] - x[0]), 2), "km/s")
# 4-D stack: plain dict meta -> the loader sets meta['rest_wavelength'] from scan 0's SGMeta (TWAVE)
stack = raster_data(files[:3], ["Mg II k 2796"], stack=True)[0]
P("stack meta type:", type(stack.meta).__name__, "| hasattr rest_wavelength:", hasattr(stack.meta, "rest_wavelength"), "| rest_wavelength(stack) before loader key:", rest_wavelength(stack))
swl = next(c for c in stack.world_component_ids if c.label == "Wavelength")
P("stack choices without key:", find_unit_choices([(stack, swl, "m")]))
stack.meta["rest_wavelength"] = 2796.19995117  # what _raster_collection_data will do: sequence[0].meta.rest_wavelength.to_value(u.AA)
P("stack choices with key:", find_unit_choices([(stack, swl, "m")]))
v.axes.figure.canvas.draw()
P("DONE")
