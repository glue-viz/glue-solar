"""WP5 line-list experiment for numeric and WCSAxes profile viewers."""
import numpy as np
from scipy.optimize import brentq

import astropy.units as u
from glue.config import layer_artist_maker
from glue.core import Data
from glue.core.units import UnitConverter
from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist
from glue.viewers.profile.viewer import MatplotlibProfileMixin
from glue_qt.viewers.profile.data_viewer import ProfileViewer
from glue_qt.viewers.profile.layer_artist import QThreadedProfileLayerArtist
from glue_qt.viewers.profile.layer_style_editor import ProfileLayerStyleEditor

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
        self._watched = ["x_att", "x_display_unit", "reference_data"]
        if hasattr(viewer_state, "slices"):
            self._watched += ["slices", "function"]
        for prop in self._watched:
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
        if getattr(state, "wcsaxes_active", False):
            positions = self._world_to_profile_pixels(positions)
        else:
            positions = UnitConverter().to_unit(state.reference_data, state.x_att, positions, state.x_display_unit)
        style = dict(color=self.state.color, alpha=self.state.alpha, zorder=self.state.zorder, visible=self.state.visible)
        for x, name in zip(positions, data["name"]):
            if not np.isfinite(x):
                continue
            self.mpl_artists.append(self.axes.axvline(x, linewidth=self.state.linewidth, **style))
            self.mpl_artists.append(self.axes.annotate(str(name), (x, 0.98), xycoords=("data", "axes fraction"),
                                                       rotation=90, ha="right", va="top", fontsize="small", **style))
        self.redraw()

    def _world_to_profile_pixels(self, wavelengths):
        """Invert the selected 1D spectral trace, keeping other pixel axes fixed.

        WCSAxes draws in pixels even though its ticks show wavelength. Using the
        trace avoids assuming a separable full-WCS inverse. Markers outside the
        sampled range or on non-monotonic traces are omitted.
        """
        state = self._viewer_state
        data = state.reference_data
        pixel_axis = data.ndim - 1 - state.x_att_pixel.axis
        world_axis = len(data.world_component_ids) - 1 - data.world_component_ids.index(state.x_att)
        fixed = [0 if value == "x" else value for value in state.wcsaxes_slice]
        def wavelength(pixel):
            pixels = list(fixed)
            pixels[pixel_axis] = pixel
            values = data.coords.pixel_to_world_values(*pixels)
            return values[world_axis] if data.coords.world_n_dim > 1 else values
        last = data.shape[state.x_att_pixel.axis] - 1
        trace = np.asarray(wavelength(np.arange(last + 1)))
        delta = np.diff(trace)
        positions = np.full(len(wavelengths), np.nan)
        if last < 1 or not np.isfinite(trace).all() or not (np.all(delta > 0) or np.all(delta < 0)):
            return positions
        low, high = sorted((trace[0], trace[-1]))
        for i, value in enumerate(wavelengths):
            if low <= value <= high:
                positions[i] = brentq(lambda pixel: float(wavelength(pixel)) - value, 0, last)
        return positions

    def remove(self):
        for prop in self._watched:
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
