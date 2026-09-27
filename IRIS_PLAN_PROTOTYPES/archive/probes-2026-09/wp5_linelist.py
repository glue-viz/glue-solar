"""WP5 (c): line-list layer for the glue-qt Profile viewer. Final-form artist + maker + style-widget dict.

Checks: add on real IRIS raster, x_display_unit tracking (Angstrom, nm, km/s via the WP5 converter),
visible toggle (profile/state.py:266 path), style editor kept for the real profile layer, legend,
subset on the reference data (line list gets a default subset artist), add-line-list-first ordering,
CSV loaded through glue's table factory, and the session save/restore behaviour.
"""
import os, sys, warnings; warnings.simplefilter("ignore")
import numpy as np
from glue.config import settings, layer_artist_maker, unit_converter
settings._save_to_disk = False; settings.SHOW_INFO_PROFILE_OPEN = False; settings.SHOW_WARN_PROFILE_DUPLICATE = False
from qtpy import QtWidgets
QtWidgets.QMessageBox.exec_ = lambda self: (print("MODAL DIALOG SUPPRESSED:", self.text(), self.informativeText(), flush=True), QtWidgets.QMessageBox.Ok)[1]
QtWidgets.QMessageBox.exec = QtWidgets.QMessageBox.exec_
import astropy.units as u
from glue.core import Data, DataCollection
from glue.core.data_factories import load_data
from glue.core.units import UnitConverter
from glue.viewers.common.state import LayerState
from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.profile.viewer import MatplotlibProfileMixin
from glue_qt.viewers.profile.data_viewer import ProfileViewer
from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist
from glue_qt.viewers.profile.layer_style_editor import ProfileLayerStyleEditor
P = lambda *a: print(*a, flush=True)
S = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- the code that ships (glue_solar/viewers.py)
from glue.viewers.profile.state import ProfileLayerState


class LineListState(ProfileLayerState):
    """State of a line-list layer.

    Reusing ProfileLayerState satisfies everything ProfileViewerState touches on its layers
    (``attribute`` at state.py:266/:292, ``reset_cache`` at :308, ``profile`` at :131/:221) and
    gives colour/alpha/linewidth for the style editor. ``attribute`` resolves to the numeric
    ``wavelength`` column on its own.
    """


class LineListArtist(MatplotlibLayerArtist):
    """Labelled vertical lines at the wavelengths (Angstrom) of a line-list table, in the viewer's display unit."""

    _layer_state_cls = LineListState
    is_computing = False  # read for every layer by glue_qt/viewers/matplotlib/data_viewer.py:59

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)
        for prop in ("x_att", "x_display_unit", "reference_data"):
            self._viewer_state.add_callback(prop, self.update)
        self.state.add_global_callback(self.update)
        self.update()

    def _clear(self):
        for artist in self.mpl_artists:
            artist.remove()
        self.mpl_artists = []

    def update(self, *args, **kwargs):
        self._clear()
        state, data = self._viewer_state, self.layer
        # the reference_data callback can fire while x_att still belongs to the previous reference
        if state.reference_data is None or state.reference_data is data or state.x_att not in state.reference_data.components:
            return
        native = state.reference_data.get_component(state.x_att).units or ""
        if not native or not u.Unit(native).is_equivalent(u.m):
            return  # x axis is not a wavelength axis (pixels, helioprojective angles, time): nothing to mark
        positions = (data["wavelength"] * u.AA).to_value(native)
        positions = UnitConverter().to_unit(state.reference_data, state.x_att, positions, state.x_display_unit)
        style = dict(color=self.state.color, alpha=self.state.alpha, zorder=self.state.zorder, visible=self.state.visible)
        for x, name in zip(positions, data["name"]):
            self.mpl_artists.append(self.axes.axvline(x, linewidth=self.state.linewidth, **style))
            self.mpl_artists.append(self.axes.annotate(str(name), (x, 0.98), xycoords=("data", "axes fraction"),
                                                       rotation=90, ha="right", va="top", fontsize="small", **style))
        self.redraw()

    def remove(self):
        for prop in ("x_att", "x_display_unit", "reference_data"):
            self._viewer_state.remove_callback(prop, self.update)
        super().remove()


@layer_artist_maker("iris-line-list")
def line_list_artist(viewer, data):
    if isinstance(viewer, MatplotlibProfileMixin) and isinstance(data, Data) \
            and {"wavelength", "name"} <= {c.label for c in data.main_components}:
        return LineListArtist(viewer.axes, viewer.state, layer=data)


# setup(): exact-class lookup in glue_qt/core/layer_artist_model.py:365 -> key on the Qt artist classes
if not isinstance(ProfileViewer._layer_style_widget_cls, dict):
    ProfileViewer._layer_style_widget_cls = {QThreadedProfileLayerArtist: ProfileLayerStyleEditor,
                                             LineListArtist: ProfileLayerStyleEditor}
# ---------------------------------------------------------------- end of shipping code

sys.path.insert(0, S)
from wp5_units import IRISUnitConverter  # noqa: E402  (installs itself as members['default'])
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from glue_qt.app import GlueApplication
from glue.core.roi import XRangeROI

f = next(str(p) for p in get_test_data_filenames() if p.name == "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits")
d = raster_data([f], ["C II 1336"])[0]
lines = load_data(os.path.join(S, "iris_lines.csv"))
lines.label = "IRIS lines"
app = GlueApplication(DataCollection([d, lines]))
v = app.new_data_viewer(ProfileViewer, data=d)
wl = next(c for c in d.world_component_ids if c.label == "Wavelength")
v.state.x_att = wl
P("add line list ->", v.add_data(lines), "| layers:", [type(l).__name__ for l in v.layers], "| n mpl artists:", len(v.layers[1].mpl_artists))
P("style widgets:", [type(k).__name__ for k in v._view.layout_style_widgets], "| layer list rows:", v._view.layer_list.model().rowCount())
first = lambda: v.layers[1].mpl_artists[0].get_xdata()[0]
P("C II 1334.53 in native m:", first())
v.state.x_display_unit = "Angstrom"; P("in Angstrom:", first())
v.state.x_display_unit = "nm"; P("in nm:", first())
v.state.x_display_unit = "km / s"; P("in km/s (rest = TWAVE 1335.71):", round(first(), 2), "| expected:", round(float((1334.53 * u.AA).to_value(u.km / u.s, u.doppler_optical(1335.70996094 * u.AA))), 2))
v.layers[1].state.visible = False; P("hidden -> artists visible:", {a.get_visible() for a in v.layers[1].mpl_artists})
v.layers[1].state.visible = True; P("shown  -> artists visible:", {a.get_visible() for a in v.layers[1].mpl_artists})
v.layers[1].state.color = "#ff0000"; v.layers[1].state.linewidth = 2
P("style change -> line color/width:", v.layers[1].mpl_artists[0].get_color(), v.layers[1].mpl_artists[0].get_linewidth(), "| attribute:", v.layers[1].state.attribute)
v.state.legend.visible = True; v.axes.figure.canvas.draw(); P("legend visible draw OK; entries:", [t.get_text() for t in v.axes.get_legend().get_texts()])
v.apply_roi(XRangeROI(-100, 100))
P("ROI on the profile -> layers:", [(type(l).__name__, l.layer.label, l.enabled) for l in v.layers], "| subsets on line list:", [s.label for s in lines.subsets])
v.remove_data(lines); P("after remove_data: layers:", [type(l).__name__ for l in v.layers], "| axvlines left on axes:", sum(1 for l in v.axes.lines if len(l.get_xdata()) == 2 and l.get_xdata()[0] == l.get_xdata()[1]))
v.state.x_display_unit = "Angstrom"; P("unit change after removal raised nothing")

# ordering: line list added FIRST becomes reference_data
v2 = app.new_data_viewer(ProfileViewer, data=lines)
P("line list first -> reference_data:", v2.state.reference_data.label, "| layers:", [type(l).__name__ for l in v2.layers], "| artists:", len(v2.layers[0].mpl_artists))
v2.add_data(d); v2.state.reference_data = d; v2.state.x_att = next(c for c in d.world_component_ids if c.label == "Wavelength")
P("after adding the raster and switching reference_data (x_att auto = Helioprojective Longitude) -> artists:", len(v2.layers[0].mpl_artists), "| x_att:", v2.state.x_att.label)
v2.state.x_att = next(c for c in d.world_component_ids if c.label == "Wavelength"); P("x_att = Wavelength -> artists:", len(v2.layers[0].mpl_artists))
v2.state.x_att = d.pixel_component_ids[2]; P("x_att = pixel axis -> artists:", len(v2.layers[0].mpl_artists))

# session: does the line-list layer survive save/restore? Use a WCS-free synthetic spectrum so only the line list is under test.
from astropy.wcs import WCS
w = WCS(naxis=1); w.wcs.ctype = ["WAVE"]; w.wcs.cunit = ["Angstrom"]; w.wcs.crval = [1330]; w.wcs.cdelt = [0.1]; w.wcs.crpix = [1]
spec = Data(label="spec", flux=np.random.random(100), coords=w)
spec.meta["rest_wavelength"] = 1335.71
app.data_collection.append(spec)
v3 = app.new_data_viewer(ProfileViewer, data=spec)
v3.state.x_att = spec.world_component_ids[0]; v3.add_data(lines); v3.state.x_display_unit = "km / s"
path = os.path.join(S, "wp5_lines.glu")
try:
    app.save_session(path, include_data=True); P("session save OK:", os.path.getsize(path) // 1024, "KB")
except Exception as e:
    P("session save FAILED:", type(e).__name__, str(e)[:200])
try:
    app2 = GlueApplication.restore_session(path)
    vs = [x for x in app2.viewers[0] if isinstance(x, ProfileViewer)]
    restored = [x for x in vs if any(type(l).__name__ == "LineListArtist" for l in x.layers)]
    P("restored viewers:", len(vs), "| with LineListArtist:", len(restored))
    for x in restored:
        la = next(l for l in x.layers if type(l).__name__ == "LineListArtist")
        P("  restored line-list: x_display_unit", repr(x.state.x_display_unit), "| artists:", len(la.mpl_artists), "| first x:", round(la.mpl_artists[0].get_xdata()[0], 2), "| reference:", x.state.reference_data.label)
except Exception as e:
    import traceback; traceback.print_exc(); P("session restore FAILED:", type(e).__name__, str(e)[:200])
P("DONE")
