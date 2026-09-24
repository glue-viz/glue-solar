import numpy as np
from glue.config import settings, unit_converter
settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
from astropy import units as u
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from glue.core import DataCollection
from glue.core.units import SimpleAstropyUnitConverter, find_unit_choices
from glue.viewers.profile.state import ProfileViewerState
P = lambda *a: print(*a, flush=True)

f = [p for p in get_test_data_filenames() if p.name == 'iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits'][0]
ds = raster_data(str(f))
P("n datasets from raster_data:", len(ds), [d.label for d in ds])
d = ds[0]
wl = [c for c in d.world_component_ids if c.label == 'Wavelength'][0]
P("wavelength cid units:", repr(d.get_component(wl).units), "| meta type:", type(d.meta).__name__, "| rest:", d.meta.rest_wavelength)
P("default 'm' choices count:", len(find_unit_choices([(d, wl, 'm')])), find_unit_choices([(d, wl, 'm')])[:8])

class IRISVelocityConverter(SimpleAstropyUnitConverter):
    def _eq(self, data):
        rest = getattr(getattr(data, 'meta', None), 'rest_wavelength', None)
        return u.doppler_optical(rest) if rest is not None else []
    def equivalent_units(self, data, cid, units):
        eq = self._eq(data)
        return list(super().equivalent_units(data, cid, units)) + (['km / s'] if eq and u.Unit(units).is_equivalent(u.m) else [])
    def to_unit(self, data, cid, values, original_units, target_units):
        return (values * u.Unit(original_units)).to_value(target_units, equivalencies=self._eq(data))
unit_converter.members['default'] = IRISVelocityConverter
P("settings.UNIT_CONVERTER:", settings.UNIT_CONVERTER)

from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
app = GlueApplication(DataCollection([d]))
v = app.new_data_viewer(ProfileViewer, data=d)
v.state.x_att = wl
ch = ProfileViewerState.x_display_unit.get_choices(v.state)
P("km / s in choices:", 'km / s' in ch, "| n choices:", len(ch))
x0 = v.layers[0].state.profile[0][:2]; P("x native:", x0, "| xlim:", v.state.x_min, v.state.x_max, "| label:", v.state.x_axislabel)
v.state.x_display_unit = 'km / s'
P("x km/s:", v.layers[0].state.profile[0][:2], "| xlim:", v.state.x_min, v.state.x_max, "| label:", v.state.x_axislabel)
# round trip via to_native as apply_roi does
from glue.core.units import UnitConverter
P("to_native(-675 km/s) m:", UnitConverter().to_native(d, wl, np.array([-675.66]), 'km / s'))
v.axes.figure.canvas.draw(); P("draw OK; ax xlabel:", v.axes.get_xlabel())
P("DONE")
