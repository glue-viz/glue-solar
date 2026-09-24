import sys
from glue.config import settings; settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False
from qtpy import QtWidgets
QtWidgets.QMessageBox.exec_ = lambda self: (print("MODAL DIALOG SUPPRESSED:", self.text(), self.informativeText(), flush=True), QtWidgets.QMessageBox.Ok)[1]
QtWidgets.QMessageBox.exec = QtWidgets.QMessageBox.exec_
import numpy as np
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from glue.config import layer_artist_maker
from glue.core import Data, DataCollection
from glue.core.units import UnitConverter
from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.profile.viewer import MatplotlibProfileMixin
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
P = lambda *a: print(*a, flush=True)

class LineListArtist(MatplotlibLayerArtist):
    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)
        self._viewer_state.add_callback('x_display_unit', self._draw)
        self._draw()
    def _draw(self, *a):
        self.clear()
        ref = self._viewer_state.reference_data
        w = self.layer['wavelength']
        if ref is not None:
            w = UnitConverter().to_unit(ref, self._viewer_state.x_att, w, self._viewer_state.x_display_unit)
        for x, lab in zip(w, self.layer['name']):
            self.mpl_artists.append(self.axes.axvline(x, color='C3', lw=0.8))
            self.mpl_artists.append(self.axes.annotate(lab, (x, 0.95), xycoords=('data', 'axes fraction'), rotation=90, fontsize=7))
        self.redraw()
    def update(self, **k): self._draw()
    def clear(self):
        for l in self.mpl_artists: l.remove()
        self.mpl_artists = []
    def remove(self): self.clear()

@layer_artist_maker('line-list')
def make(viewer, data):
    if isinstance(viewer, MatplotlibProfileMixin) and isinstance(data, Data) and 'name' in [c.label for c in data.components]:
        return LineListArtist(viewer.axes, viewer.state, layer=data)

f = [p for p in get_test_data_filenames() if p.name == 'iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits'][0]
d = raster_data(str(f))[0]
lines = Data(label='IRIS lines', wavelength=np.array([1334.53, 1335.71, 1336.0])*1e-10, name=np.array(['C II 1334', 'C II 1335', 'C II 1336']))
P("stage: data built; name component type:", type(lines.get_component('name')).__name__)
from glue.viewers.profile.layer_artist import ProfileLayerArtist
from glue_qt.viewers.profile.layer_style_editor import ProfileLayerStyleEditor
ProfileViewer._layer_style_widget_cls = {ProfileLayerArtist: ProfileLayerStyleEditor}
P("monkeypatched style widget dict")
app = GlueApplication(DataCollection([d, lines]))
v = app.new_data_viewer(ProfileViewer, data=d)
P("stage: viewer created")
v.state.x_att = [c for c in d.world_component_ids if c.label == 'Wavelength'][0]
P("stage: x_att set")
ok = v.add_data(lines)
P("add_data returned:", ok, "| layers:", [type(l).__name__ for l in v.layers])
P("n mpl artists:", len(v.layers[1].mpl_artists), "| first axvline x:", v.layers[1].mpl_artists[0].get_xdata())
v.state.x_display_unit = 'Angstrom'
P("after unit change first axvline x:", v.layers[1].mpl_artists[0].get_xdata())
v.axes.figure.canvas.draw(); P("draw OK; layer list rows:", v._view.layer_list.model().rowCount())
if len(sys.argv) > 1:
    from astropy import units as u
    from glue.config import unit_converter
    from glue.core.units import SimpleAstropyUnitConverter
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
    P("UNIT_CONVERTER setting still:", settings.UNIT_CONVERTER)
    v.state._update_x_display_unit_choices()
    from glue.viewers.profile.state import ProfileViewerState
    P("km / s in choices via default override:", 'km / s' in ProfileViewerState.x_display_unit.get_choices(v.state))
    v.state.x_display_unit = 'km / s'; P("profile x[:2] km/s:", v.layers[0].state.profile[0][:2], "| line x:", v.layers[1].mpl_artists[0].get_xdata())
P("DONE")
