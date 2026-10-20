"""
Toolbar tools for glue's viewers.
"""

import os
import re
from functools import partial

import numpy as np
from echo import add_callback, delay_callback
from glue.config import settings, viewer_tool
from glue.core import Data, Subset
from glue.core.command import ApplySubsetState
from glue.core.data import BaseCartesianData
from glue.core.edit_subset_mode import ReplaceMode
from glue.core.fixed_resolution_buffer import invalidate_cache, translate_pixel
from glue.core.hub import HubListener
from glue.core.link_manager import is_convertible_to_single_pixel_cid
from glue.core.message import (
    DataCollectionAddMessage,
    DataCollectionDeleteMessage,
    NumericalDataChangedMessage,
    SettingsChangeMessage,
)
from glue.core.state import loader, saver
from glue.core.subset import SliceSubsetState, SubsetState
from glue.core.util import disambiguate
from glue.plugins.tools.path_slicer.common import open_slice_viewer_for
from glue.plugins.tools.path_slicer.matplotlib_mode import (
    _PATH_ALPHA_ACTIVE,
    _PATH_ALPHA_INACTIVE,
    _PATH_COLOR,
    BasePathSlicerCrosshairMode,
    BasePathSlicerMode,
)
from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedCoordinates, PathSlicedData, sample_points
from glue.plugins.tools.path_slicer.path_sliced_data_links import (
    PathRelativeLink,
    link_path_sliced_pair_paths,
    link_path_sliced_to_parent,
)
from glue.utils import as_variable_name, unbroadcast
from glue.viewers.common.tool import SimpleToolMenu, Tool
from glue.viewers.image.composite_array import CompositeArray
from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.image.pixel_selection_mode import PixelSelectionTool
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from glue.viewers.matplotlib.mpl_axes import update_appearance_from_settings
from glue.viewers.matplotlib.toolbar_mode import PathMode, ToolbarModeBase
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.table import TableViewer
from matplotlib import animation, rc_context, rcParams
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseButton, ResizeEvent
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.patheffects import withStroke
from matplotlib.transforms import ScaledTranslation, blended_transform_factory
from mpl_scatter_density.base_image_artist import BaseImageArtist
from qtpy import QtCore, QtWidgets

import astropy.units as u
from astropy.coordinates import Angle, SkyCoord, angular_separation
from astropy.table import Column, Table, hstack
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar.glue_patches import _takes
from glue_solar.lines import KM_S, _icon, rest_wavelength
from glue_solar.quicklook import (
    _IRIS_ROLES,
    QuicklookImageViewer,
    _across,
    _check_cut,
    _curve_sources,
    _cut,
    _half_cadence,
    _is_sit_and_stare,
    _off,
    _place,
    _point_curves,
    _role,
    _seconds_text,
    _shown,
    _spectral_axes,
    _switch,
    _sync_text,
    _time_axis,
    _time_text,
    _timed,
    _times,
    _value_text,
    _wing,
    _world_text,
    coordinator,
    nearest,
    observation_key,
)
from glue_solar.sources.iris import _write_ecsv
from glue_solar.sources.loaders.iris import _HPC, _GlueWCS
from glue_solar.sources.loaders.stack_spectrograms import _PerScanWCS
from glue_solar.sources.moments import _accepted, _start

_WATCHED = ("reference_data", "x_att", "y_att", "slices")
# glue sets both axis labels whenever it resets the WCSAxes, which also drops their tick settings
_LABELS = tuple(f"{axis}_{prop}" for axis in "xy" for prop in ("axislabel", "axislabel_size", "axislabel_weight"))
_LABELS += ("x_ticklabel_size", "y_ticklabel_size")
_PIXEL_COORDS = {"type": ("scalar", "scalar"), "wrap": (None, None), "unit": (u.one, u.one), "name": ("x", "y")}
# glue-qt rebuilds the slice sliders when these change
_SLIDER_REBUILDS = ("reference_data", "x_att", "y_att")
# Beside another coordinate, an angle changing by less than this fraction of the other across a panel has no tick labels
_FLAT = 0.05


def _throttle_slice_sliders(viewer):
    """
    Make a slider drag apply its latest position once Qt is idle: glue-qt redraws at every value a slider passes, so a
    drag on a large cube lags (``wp0-perf-qt``). The sliders are glue-qt's ``value_slice_center``, as a test pins.
    """
    for slider in viewer.options_widget().findChildren(QtWidgets.QSlider, "value_slice_center"):
        if not slider.hasTracking():
            continue  # already throttled
        slider.setTracking(False)
        timer = QtCore.QTimer(slider)
        timer.setSingleShot(True)
        timer.setInterval(0)
        timer.timeout.connect(lambda slider=slider: slider.setValue(slider.sliderPosition()))
        slider.sliderMoved.connect(lambda _position, timer=timer: timer.isActive() or timer.start())


def _keep_mouse_mode(viewer):
    """
    Switch the viewer's mouse mode, such as Pixel, back on: glue-qt ends it before running any plain
    toolbar button or menu entry. The mode is the one the viewer's Coordinate tool remembers.
    """
    mode = viewer.toolbar.tools["solar:coordinate"].mode
    if mode is not None:
        viewer.toolbar.active_tool = mode


def _time_component(data):
    """The first datetime component of ``data``, or None."""
    return next((cid for cid in data.main_components if data.get_kind(cid) == "datetime"), None)


def _sit_and_stare_raster(data):
    """Whether ``data`` is a sit-and-stare raster window, whose leading axis is its exposures."""
    return data is not None and _role(data) == "raster" and data.ndim == 3 and _is_sit_and_stare(data)


def _hovered(state, x, y):
    """
    The index of the reference data's pixel at ``x, y`` of the Image viewer's displayed axes, in the displayed slice, or
    None off the image.
    """
    data = state.reference_data
    if data is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
        return None
    ix, iy = int(round(x)), int(round(y))
    if not (0 <= ix < data.shape[state.x_att.axis] and 0 <= iy < data.shape[state.y_att.axis]):
        return None
    # an aggregated slider range carries its middle slice on the AggregateSlice object
    return tuple(
        ix if i == state.x_att.axis else iy if i == state.y_att.axis else getattr(s, "center", s)
        for i, s in enumerate(state.slices)
    )


def _world_position(axes, x, y, keep=None, rest=None):
    """
    WCSAxes' world readout at ``x, y``, arcsec to 0.01" and Å to 0.001 Å where WCSAxes gives its ticks' precision (D31);
    ``keep``, a coordinate of ``axes``, leaves the other angles out, and ``rest`` (Å) adds the Doppler velocity (#264).
    """
    world = axes.coords[0].transform.transform(np.array([[x, y]]))[0]
    wavelength = axes.coords["em.wl"] if rest is not None and "em.wl" in axes.coords else None  # by physical type
    texts, velocity = [], ""
    for coord in axes.coords:
        if coord.coord_index is None:  # not on these axes
            continue
        if coord.coord_type in ("longitude", "latitude") and keep not in (None, coord):
            continue
        value = world[coord.coord_index] * coord.coord_unit
        if coord is wavelength:
            velocity = f" · {value.to_value(KM_S, u.doppler_optical(rest * u.AA)):z.1f} {KM_S}"
        if coord.get_format_unit() == u.arcsec:
            angle = Angle(value) if coord.coord_wrap is None else Angle(value).wrap_at(coord.coord_wrap)
            texts.append(_world_text(angle))
        elif coord.get_format_unit() == u.AA:
            texts.append(_world_text(value))
        else:
            texts.append(coord.format_coord(world[coord.coord_index], format="ascii"))
    return " ".join(texts) + " (world)" + velocity


def _exposure_label(data):
    """
    'Exposure (acquisition order)', or 'Time (<step> s per pixel)' once regridded on time, and on a second line
    '<first> – <last> UTC' for the exposure axis of a sit-and-stare raster; one line would not fit a quicklook panel.
    """
    step = data.meta.get("time_step")
    name = "Exposure (acquisition order)" if step is None else f"Time ({step:.3g} s per pixel)"
    cid = _time_component(data)
    if cid is None:
        return name
    times = data[cid, (slice(None), 0, 0)]
    first, last = (np.datetime_as_string(t, unit="s") for t in (np.nanmin(times), np.nanmax(times)))  # NaT: gaps
    if last[:10] == first[:10]:
        last = last[11:]  # the same day: the time only
    return f"{name}\n{first} – {last} UTC"


def _index_ticks(axes, index, shown):
    """
    Give the x (``index`` 0) or y (1) axis of ``axes`` integer pixel ticks and return their coordinate helper (D29);
    only ``shown``, the world coordinate along the other axis, keeps ticks, fixed there, as WCSAxes would move the
    others and glue's labels to whichever edge is free.
    """
    near, far = "bt" if index == 0 else "lr"
    other_near, other_far = "lr" if index == 0 else "bt"
    for coord in axes.coords:
        coord.set_ticks_position(other_near + other_far if coord is shown else "")
        coord.set_ticklabel_position(other_near if coord is shown else "")
        coord.set_axislabel_position(other_near if coord is shown else "")
    pixel = axes.get_coords_overlay("pixel", coord_meta=_PIXEL_COORDS)
    pixel[1 - index].set_visible(False)
    coord = pixel[index]
    coord.set_ticks_position(near + far)
    coord.set_ticklabel_position(near)
    coord.set_axislabel_position(near)
    coord.set_major_formatter("x")  # integers
    return coord


def _hide_flat_angles(axes, shape):
    """
    Hide the tick labels of an angle that barely changes across the ``shape`` (x, y) shown beside another coordinate,
    such as a raster's latitude along its steps, whose jitter WCSAxes labels at every crossing; beside two others both
    angles go. Decided on the array's edges, so zooming keeps it.
    """
    shown = [coord for coord in axes.coords if coord.coord_index is not None]  # the others are not on these axes
    angles = [coord for coord in shown if coord.coord_type in ("longitude", "latitude")]
    if len(angles) != 2 or len(shown) == 2:  # an image of the two angles alone: both change across it
        return
    if len(shown) > 3:
        for coord in angles:
            coord.set_ticklabel_position("")
        return
    x, y = (np.linspace(0, n - 1, 64) for n in shape)  # -TAB rasters have no coordinates past the outer centers
    pixel = np.concatenate([
        np.column_stack([x, np.zeros(64)]), np.column_stack([x, np.full(64, shape[1] - 1)]),
        np.column_stack([np.zeros(64), y]), np.column_stack([np.full(64, shape[0] - 1), y]),
    ])
    world = angles[0].transform.transform(pixel)
    for coord in angles:  # a FITS WCS gives longitudes from 0° to 360°, so one across 0° would span the circle
        if coord.coord_type == "longitude":  # measured from its least value, which a sample off the sky (NaN) keeps
            full_circle = (360 * u.deg).to_value(coord.coord_unit)
            values = world[:, coord.coord_index]
            world[:, coord.coord_index] = (values - np.nanmin(values) + full_circle / 2) % full_circle
    spans = [np.nanmax(world[:, coord.coord_index]) - np.nanmin(world[:, coord.coord_index]) for coord in angles]
    for coord, span, other in zip(angles, spans, spans[::-1]):
        if span < _FLAT * other:
            coord.set_ticklabel_position("")


def _diagram_axes(axes):
    """
    Keep a path diagram's first coordinate along each axis, hiding any other, such as an SST cube's scan time, which
    varies with its tunings and which WCSAxes would place on the free right edge, past the viewer's margin.
    """
    for coord in [coord for coord in axes.coords if coord.coord_index is not None][2:]:
        coord.set_ticks_position("")
        coord.set_ticklabel_position("")
        coord.set_axislabel_position("")


def _diagram_label(data, axis):
    """
    The name and unit of a path diagram's first named world axis along its numpy ``axis``, or None: glue labels such
    an axis without its unit, or 'World N' where it has two world axes, such as an SST cube's tunings, each timed.
    """
    coords, pixel = data.coords, data.ndim - 1 - axis
    if coords is None:  # a mosaic's, whose pointing moves with the scan
        return None
    names, units = coords.world_axis_names, coords.world_axis_units
    world = next((i for i, name in enumerate(names) if name and coords.axis_correlation_matrix[i, pixel]), None)
    return None if world is None else f"{names[world]} [{units[world]}]" if units[world] else names[world]


def _shown_slice(state):
    """The index of the Image viewer's displayed slice of its reference data, or None while it shows none."""
    data = state.reference_data
    if data is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
        return None
    shown = (state.x_att.axis, state.y_att.axis)
    # an aggregated slider range carries its slice on the AggregateSlice object
    return tuple(slice(None) if i in shown else getattr(s, "slice", s) for i, s in enumerate(state.slices))


def _frame_time(data, view, decimals=3, clock=False):
    """
    The time of ``view``, a `_shown_slice`, of ``data`` from its first datetime component, in UTC to ``decimals`` of a
    second, or with ``clock`` its time of day to the second (D90), or the first and last of several; '' without one.
    """
    cid = None if view is None else _time_component(data)
    if cid is None:
        return ""
    times = unbroadcast(data[cid, view])  # one per frame, not per pixel: an SST cube's took 22 ms a slider step
    times = times[~np.isnat(times)]  # NaT: a gap of data regridded on time
    if times.size == 0:  # a Collapse range narrower than one sample, or a gap
        return ""
    if clock:
        first, last = (np.datetime_as_string(t, unit="s")[11:] for t in (times.min(), times.max()))
        return first if first == last else f"{first} – {last}"
    # 'YYYY-MM-DDThh:mm:ss.' and the decimals
    first, last = (np.datetime_as_string(t, unit="ms")[: 20 + decimals] for t in (times.min(), times.max()))
    return f"{first} UTC" if first == last else f"{first} – {last} UTC"


@viewer_tool
class FrameTimeTool(Tool, HubListener):
    """
    The frame time and time sync in the status bar (D21), and each Image viewer's setup glue lacks: throttled sliders,
    sit-and-stare exposure labels and ticks (D29) and flat-angle labels, set again as glue resets the axes, and the
    mouse-over readout with time, exposure and Doppler velocity (D31, #264).
    """

    icon = "window_tab"
    tool_id = "solar:frame_time"
    action_text = "Frame time"
    tool_tip = "Show or hide the acquisition time of the displayed frame"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.label = QtWidgets.QLabel()
        self.label.setContentsMargins(0, 0, 12, 0)  # keep clear of the window edge and size grip
        viewer.statusBar().addPermanentWidget(self.label)
        # grays a follower with no frame near the time master's
        self._gray = viewer.axes.add_patch(
            Rectangle((0, 0), 1, 1, transform=viewer.axes.transAxes, color="0.6", alpha=0.6, zorder=1000, visible=False)
        )
        self.coordinator = coordinator(viewer._data)
        self.coordinator.add_listener(self._synced)
        # a viewer torn down without closing its tools must not be called back
        self.label.destroyed.connect(self._forget)
        for prop in _WATCHED:
            viewer.state.add_callback(prop, self._refresh)
        self._refresh()
        _throttle_slice_sliders(viewer)
        for prop in _SLIDER_REBUILDS:
            viewer.state.add_callback(prop, self._throttle_sliders)
        self._exposure_ticks = (None, None)  # the WCSAxes coordinates they were added to, and their helper
        self._flat_checked = None  # the WCSAxes coordinates last checked for a flat angle
        self._placed = None  # the WCSAxes coordinates, view and size for which the readout placed the ticks
        for prop in _LABELS:
            viewer.state.add_callback(prop, self._label_exposures)
        # glue's Preferences restyle only the WCS coordinates
        self._hub = viewer.session.hub
        self._hub.subscribe(self, SettingsChangeMessage, handler=self._label_exposures)
        self._label_exposures()
        self._format_coord = viewer.axes.format_coord  # WCSAxes' world readout, set on the axes
        viewer.axes.format_coord = self._readout

    @property
    def checked(self):
        """Whether the frame time shows, as its View menu entry's check mark says."""
        return not self.label.isHidden()

    def activate(self):
        self.label.setHidden(not self.label.isHidden())
        _keep_mouse_mode(self.viewer)

    def close(self):
        self._forget()
        for prop in _WATCHED:
            self.viewer.state.remove_callback(prop, self._refresh)
        for prop in _SLIDER_REBUILDS:
            self.viewer.state.remove_callback(prop, self._throttle_sliders)
        for prop in _LABELS:
            self.viewer.state.remove_callback(prop, self._label_exposures)
        self.viewer.axes.format_coord = self._format_coord
        super().close()

    def _readout(self, x, y):
        """The mouse-over readout at ``x, y`` of the displayed axes (see the class)."""
        axes = self.viewer.axes
        placed = (axes.coords, axes.viewLim.bounds, axes.bbox.bounds)
        if placed != self._placed:  # WCSAxes formats as its last ticks, unplaced on hidden axes or after a reset (#90)
            axes._update_tick_and_label_positions()
            self._placed = placed
        text, state = self._format_coord(x, y), self.viewer.state
        data = state.reference_data
        if data is None or state.x_att is None or state.y_att is None:
            return text
        if text.endswith(" (world)"):  # not a pixel position or an overlay, which W switches to
            shown = (state.x_att.axis, state.y_att.axis)
            # glue's own mapping of the axis beside the exposures to its world coordinate, as for the ticks
            keep = axes.coords[data.ndim - 1 - max(shown)] if 0 in shown and _sit_and_stare_raster(data) else None
            text = _world_position(axes, x, y, keep, rest_wavelength(data))
        pixel = _hovered(state, x, y)
        if pixel is None:
            return text
        cid, exposure = _time_component(data), data.find_component_id("Exposure time")
        if cid is not None:
            text += f" · {_time_text(data[cid, pixel])}"
        if exposure is not None:
            text += f" · exp {_seconds_text(data[exposure, pixel])}"
        return text

    def _label_exposures(self, *_):
        """
        Hide the tick labels of a flat angle, label a displayed sit-and-stare exposure axis and give it exposure ticks,
        and on a quicklook panel give glue's other axis labels their units (D90; see the class).
        """
        state = self.viewer.state
        data = state.reference_data
        axes, shown = self.viewer.axes, (state.x_att, state.y_att)
        if data is None or None in shown:
            return
        if axes.coords is not self._flat_checked:  # glue reset the axes
            self._flat_checked = axes.coords
            _hide_flat_angles(axes, [data.shape[att.axis] for att in shown])
            if isinstance(data, PathData):
                _diagram_axes(axes)
        sit_and_stare, panel = _sit_and_stare_raster(data), isinstance(self.viewer, QuicklookImageViewer)
        for index, axis in enumerate("xy"):
            att, world = getattr(state, f"{axis}_att"), getattr(state, f"{axis}_att_world")
            other = getattr(state, f"{'yx'[index]}_att")
            exposures = sit_and_stare and att.axis == 0
            label = getattr(state, f"{axis}_axislabel")
            if label in ("", getattr(world, "label", None)):  # glue's reset
                unit = panel and world is not None and data.get_component(world).units
                new = _exposure_label(data) if exposures else f"{world.label} [{unit}]" if unit else label
                if isinstance(data, PathData):
                    new = _diagram_label(data, att.axis) or new
                if new != label:
                    setattr(state, f"{axis}_axislabel", new)  # which calls this again
                    return
            if not exposures:
                continue
            coords, ticks = self._exposure_ticks
            if coords is not axes.coords:  # glue reset the axes, and the ticks with them
                # glue's own mapping of a pixel axis to its world coordinate, as in its tick label sizes
                ticks = _index_ticks(axes, index, axes.coords[data.ndim - 1 - other.axis])
                self._exposure_ticks = (axes.coords, ticks)
            # glue styles and labels only the WCS coordinates
            color = settings.FOREGROUND_COLOR
            ticks.set_ticks(color=color)
            ticks.set_ticklabel(color=color, size=getattr(state, f"{axis}_ticklabel_size"))
            size, weight = getattr(state, f"{axis}_axislabel_size"), getattr(state, f"{axis}_axislabel_weight")
            ticks.set_axislabel(label, color=color, size=size, weight=weight)
            self.viewer.figure.canvas.draw_idle()

    def _throttle_sliders(self, *_):
        _throttle_slice_sliders(self.viewer)

    def _synced(self, key, time, exposure):
        if not _off(self.viewer):  # a quicklook panel turned off, refreshed once on
            self._refresh()

    def _forget(self, *_):
        self.coordinator.remove_listener(self._synced)
        self._hub.unsubscribe_all(self)

    def _refresh(self, *_):
        state = self.viewer.state
        data = state.reference_data
        self.enabled = data is not None and _time_component(data) is not None
        status = self.coordinator.time_status(self.viewer)
        unmatched = status is not None and status[0] == "no match"
        if self._gray.get_visible() != unmatched:
            self._gray.set_visible(unmatched)
            self.viewer.figure.canvas.draw_idle()
        self.label.setStyleSheet("color: gray" if unmatched else "")
        view = _shown_slice(state)
        text = _frame_time(data, view, clock=True)  # short, as a narrow quicklook panel shows it (D90)
        if not text:
            self.label.setText("")
            return
        exposure = data.find_component_id("Exposure time")
        if exposure is not None:
            seconds = data[exposure, view]
            shortest, longest = f"{np.nanmin(seconds):.4g}", f"{np.nanmax(seconds):.4g}"
            text += f" · exp {shortest} s" if shortest == longest else f" · exp {shortest}–{longest} s"
        where = self.coordinator.point_on(self.viewer)
        if where is not None:
            ny, nx = data.shape[1:]
            if not (-0.5 <= where[0] <= nx - 0.5 and -0.5 <= where[1] <= ny - 0.5):
                text += " · outside SJI FOV"
        if self.coordinator.outside_raster(self.viewer):
            text += " · outside raster FOV"
        if status is not None:
            text += f" · {_sync_text(status)}"
        self.label.setText(text)
        self.label.setToolTip("\n".join(filter(None, (_frame_time(data, view), _pointing(data.meta, view[0])))))


def _pointing(meta, frame):
    """The SJI pointing of one frame, or nothing when several frames or no pointing are shown."""
    if not isinstance(frame, int | np.integer) or "pztx" not in meta:
        return ""
    return (
        f"PZT offset {meta['pztx'][frame]:.2f}″, {meta['pzty'][frame]:.2f}″; "
        f"FOV center {meta['xcenix'][frame]:.2f}″, {meta['ycenix'][frame]:.2f}″; "
        f"slit at x = {meta['slit x position'][frame]:.1f} px"
    )


@viewer_tool
class CursorReadoutTool(Tool):
    """
    The mouse-over readout and the value under the mouse in the status bar, which glue-qt 0.4.2 never shows
    (glue-viz/glue-qt#74, draft, adds its own; #109).
    """

    icon = "glue_cross"
    tool_id = "solar:cursor_readout"
    action_text = "Cursor readout"
    tool_tip = "Show or hide the position and value under the mouse (press W over the image for pixels)"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = True
        self._motion = viewer.axes.figure.canvas.mpl_connect("motion_notify_event", self._on_move)

    @property
    def checked(self):
        """Whether the readout shows, as its View menu entry's check mark says."""
        return self.shown

    def activate(self):
        self.shown = not self.shown
        if not self.shown:
            self.viewer.set_status("")
        _keep_mouse_mode(self.viewer)

    def close(self):
        self.viewer.axes.figure.canvas.mpl_disconnect(self._motion)
        super().close()

    def _on_move(self, event):
        if self.shown and event.inaxes is self.viewer.axes:
            self.viewer.set_status(self.describe(event.xdata, event.ydata))

    def describe(self, x, y):
        """The status text for pixel position ``x, y`` of the displayed axes."""
        state = self.viewer.state
        text = self.viewer.axes.format_coord(x, y)
        data, view = state.reference_data, _hovered(state, x, y)
        layer = next((ls for ls in state.layers if ls.layer is data and ls.visible), None)
        if layer is None or view is None:
            return text
        return f"{text} | {layer.attribute.label} = {_value_text(data[layer.attribute, view])}"


@viewer_tool
class HideAxesTool(Tool):
    """
    Switch glue's ``show_axes``, which glue-qt 0.4.2 has no control for, so draws place no ticks (D30, D71); on a
    quicklook panel, every image panel's (`~glue_solar.quicklook._Panels`, D83). A plain tool, as a checkable one is a
    mouse mode, which would end Pixel.
    """

    icon = "glue_image"
    tool_id = "solar:hide_axes"
    action_text = "Hide axes"
    tool_tip = "Hide or show the axes, which makes slice steps and redraws faster"

    def __init__(self, viewer):
        super().__init__(viewer)
        viewer.state.add_callback("show_axes", self._show)
        self._show()

    @property
    def checked(self):
        """Whether the axes are hidden, as the View menu entry's check mark says."""
        return not self.viewer.state.show_axes

    def activate(self):
        self.viewer.state.show_axes = not self.viewer.state.show_axes
        _keep_mouse_mode(self.viewer)

    def close(self):
        self.viewer.state.remove_callback("show_axes", self._show)
        super().close()

    def _show(self, *_):
        axes, shown = self.viewer.axes, self.viewer.state.show_axes
        if axes.axison != shown:
            axes.set_axis_on() if shown else axes.set_axis_off()
            self.viewer.figure.canvas.draw_idle()


@viewer_tool
class PerFrameLimitsTool(Tool):
    """
    Switch glue's ``stretch_global`` of the reference data's layers, which glue-qt 0.4.2 has no control for; other data
    take their whole cube's limits again, as glue would take theirs at the reference data's slice indices (an
    IndexError for another shape). glue-core 1.27.0 cannot restore it (``wp0-core-session-reports``).
    """

    icon = "glue_rainbow"
    tool_id = "solar:per_frame_limits"
    action_text = "Per-frame limits"
    tool_tip = "Take the color limits from the displayed slice, or again from the whole cube"

    def __init__(self, viewer):
        super().__init__(viewer)
        # before glue sets the sliders of the new reference data
        viewer.state.add_callback("reference_data", self._whole_cube_again, priority=10000)

    @property
    def checked(self):
        """Whether every layer of the reference data is per frame, as the View menu entry's check mark says."""
        state = self.viewer.state
        layers = [layer for layer in state.layers if layer.layer is state.reference_data]
        return bool(layers) and not any(layer.stretch_global for layer in layers)

    def activate(self):
        state = self.viewer.state
        layers = [layer for layer in state.layers if layer.layer is state.reference_data]
        per_frame = any(layer.stretch_global for layer in layers)
        for layer in layers:
            layer.stretch_global = not per_frame
        _keep_mouse_mode(self.viewer)

    def close(self):
        self.viewer.state.remove_callback("reference_data", self._whole_cube_again)
        super().close()

    def _whole_cube_again(self, reference_data):
        """Give the layers of every dataset but the new reference data their whole cube's limits again."""
        for layer in self.viewer.state.layers:
            if layer.layer is not reference_data and not getattr(layer, "stretch_global", True):
                layer.stretch_global = True


@viewer_tool
class BandTool(Tool):
    """
    The map as glue's own ``AggregateSlice`` mean over 5, 9 or 15 wavelength pixels about the slider's (#169), made
    again by a ``slices`` validator, as glue-qt 0.4.2 makes it one wavelength at any slider move
    (``wp0-qt-aggregate-slice``).
    """

    icon = _icon("solar_wavelength_band")
    tool_id = "solar:band"
    action_text = "Wavelength band…"
    tool_tip = "Show the mean over 5, 9 or 15 wavelength pixels about the slider's"

    WIDTHS = (1, 5, 9, 15)

    def __init__(self, viewer):
        super().__init__(viewer)
        self.width = 1
        viewer.state.add_callback("slices", self._band, validator=True)
        for prop in _SLIDER_REBUILDS:
            viewer.state.add_callback(prop, self._enable)
        self._enable()

    @property
    def checked(self):
        """Whether a band is on, as the View menu entry's check mark says."""
        return self.width > 1

    def activate(self):
        items = [str(width) for width in self.WIDTHS]
        text, ok = QtWidgets.QInputDialog.getItem(
            self.viewer, "Wavelength band", "Wavelength pixels:", items, self.WIDTHS.index(self.width), False
        )
        if ok:
            self.width = int(text)
            state = self.viewer.state
            axes = self._axes(state.slices)  # the validator makes the band about the slider's index
            state.slices = tuple(int(getattr(s, "center", s)) if i in axes else s for i, s in enumerate(state.slices))
        _keep_mouse_mode(self.viewer)

    def close(self):
        self.viewer.state.remove_callback("slices", self._band)
        for prop in _SLIDER_REBUILDS:
            self.viewer.state.remove_callback(prop, self._enable)
        super().close()

    def _enable(self, *_):
        state = self.viewer.state
        self.enabled = state.reference_data is not None and bool(_spectral_axes(state.reference_data) - _shown(state))

    def _axes(self, slices):
        """The wavelength axes of the reference data that the viewer does not show, for ``slices``."""
        state = self.viewer.state
        data = state.reference_data
        return set() if data is None or len(slices) != data.ndim else _spectral_axes(data) - _shown(state)

    def _band(self, slices):
        half = self.width // 2
        if not half:
            return slices
        slices = list(slices)
        for axis in self._axes(slices):
            index = slices[axis]
            if not isinstance(index, AggregateSlice):  # a Collapse stays until a slider moves, as in glue-qt
                band = slice(max(index - half, 0), index + half + 1)  # glue cuts the stop at the end of the axis
                slices[axis] = AggregateSlice(band, index, np.nanmean)
        return tuple(slices)


def _sky_coords(viewer):
    """
    The WCSAxes longitude and latitude, of any celestial frame, of the Image viewer's displayed axes, or None unless
    the axes show these two alone and neither is the exposures of a sit-and-stare raster, which the pointing and the
    solar rotation move by a fraction of a slit pixel.
    """
    state = viewer.state
    data = state.reference_data
    if data is None or None in (state.x_att, state.y_att):
        return None
    if _is_sit_and_stare(data) and 0 in (state.x_att.axis, state.y_att.axis):  # an index, as its ticks show
        return None
    angles = {coord.coord_type: coord for coord in viewer.axes.coords if coord.coord_index is not None}
    if sorted(angles) != ["latitude", "longitude"]:  # also no wavelength or time beside them
        return None
    return angles["longitude"], angles["latitude"]


def _arcsec_ratio(viewer):
    """
    The angle a pixel spans along the viewer's y axis over the angle it spans along x, on average across the image
    through the view center, or None off the sky (`_sky_coords`). Averaged between the outer pixel centers, since -TAB
    rasters have no coordinates past them and their steps differ by up to 15 % from one to the next.
    """
    state, angles = viewer.state, _sky_coords(viewer)
    if angles is None or None in (state.x_min, state.y_min):
        return None
    lon, lat = angles
    nx, ny = (state.reference_data.shape[att.axis] - 1 for att in (state.x_att, state.y_att))
    x, y = np.clip((state.x_min + state.x_max) / 2, 0, nx), np.clip((state.y_min + state.y_max) / 2, 0, ny)
    world = lon.transform.transform(np.array([[0, y], [nx, y], [x, 0], [x, ny]]))
    lons, lats = (u.Quantity(world[:, coord.coord_index], coord.coord_unit) for coord in (lon, lat))
    along_x, along_y = angular_separation(lons[::2], lats[::2], lons[1::2], lats[1::2]) / [nx, ny]
    ratio = (along_y / along_x).to_value(u.one)
    return ratio if np.isfinite(ratio) and ratio > 0 else None


@viewer_tool
class PhysicalAspectTool(Tool):
    """
    glue's 'Square Pixels' scaled by `_arcsec_ratio`, so an arcsec spans as far along x as y (#103): through glue's
    private aspect hooks, glue keeps it through resizes, zooms and slices. Square pixels off the sky.
    """

    icon = "glue_move_x"
    tool_id = "solar:physical_aspect"
    action_text = "Physical aspect"
    tool_tip = "Show the image in its proportions on the sky, or with the aspect it had"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.ratio = None  # `_arcsec_ratio`, or 1, while on
        self._aspect = None  # glue's aspect before
        state = viewer.state
        # glue gives the state the axes' height over width through this at each resize, and 'Square Pixels' fits the
        # limits to it: scaled by the ratio, it fits them to the sky's proportions
        set_axes_ratio = state._set_axes_aspect_ratio
        state._set_axes_aspect_ratio = lambda ratio: set_axes_ratio(ratio / (self.ratio or 1))
        for prop in ("x_att", "y_att"):
            state.add_callback(prop, self._update)
        state.add_callback("aspect", self._aspect_changed)

    @property
    def checked(self):
        """Whether the image shows in its proportions on the sky, as the View menu entry's check mark says."""
        return self.ratio is not None

    def activate(self):
        state = self.viewer.state
        if self.ratio is None:
            self._aspect, self.ratio = state.aspect, _arcsec_ratio(self.viewer) or 1.0
            self._fit()  # glue widens the limits to it now under 'Square Pixels' already,
            state.aspect = "equal"  # else as it switches to it
        else:
            self.ratio = None
            state.aspect = self._aspect
            self._fit()
            data = state.reference_data
            if self._aspect == "auto" and None not in (data, state.x_att, state.y_att, state.x_min):
                nx, ny = data.shape[state.x_att.axis], data.shape[state.y_att.axis]
                with delay_callback(state, "x_min", "x_max", "y_min", "y_max"):  # the image fills the axes again
                    state.x_min, state.x_max = max(state.x_min, -0.5), min(state.x_max, nx - 0.5)
                    state.y_min, state.y_max = max(state.y_min, -0.5), min(state.y_max, ny - 0.5)
        _keep_mouse_mode(self.viewer)

    def close(self):
        state = self.viewer.state
        del state._set_axes_aspect_ratio
        for prop in ("x_att", "y_att"):
            state.remove_callback(prop, self._update)
        state.remove_callback("aspect", self._aspect_changed)
        super().close()

    def _aspect_changed(self, aspect):
        if aspect != "equal" and self.ratio is not None:  # 'Automatic' chosen in the viewer's options
            self.ratio = None
            self._fit()

    def _update(self, *_):
        if self.ratio is not None:  # glue has shown the whole image of the new axes, at the old ratio
            self.ratio = _arcsec_ratio(self.viewer) or 1.0
            self._fit(whole=True)

    def _fit(self, whole=False):
        """
        Give glue the axes' ratio, scaled while on, and let 'Square Pixels' widen the limits to it, or show the whole
        image with it, as glue does.
        """
        state = self.viewer.state
        state._axes_aspect_ratio = self.viewer.axes_ratio / (self.ratio or 1)
        state.reset_limits() if whole else state._adjust_limits_aspect()


# A color bar's gap from the Image viewer's axes and width, and the room it takes with its ticks, in inches
_BAR = (0.1, 0.15)
_BAR_ROOM = 0.9


class _ColorBarAxes(Axes):
    """
    The axes of a color bar, which take the colors of the viewer's reference data from glue's own image as they draw:
    whatever glue draws the image with, they draw the bar with.
    """

    viewer = None

    def draw(self, renderer):
        if not self.get_visible():  # its parent draws it hidden too
            return
        state = self.viewer.state
        artist = next(
            (a for a in self.viewer.layers if isinstance(a, ImageLayerArtist) and a.layer is state.reference_data), None
        )
        layer = None if artist is None else artist.composite.layers.get(artist.uuid)
        if layer is None:
            return
        # glue's limits, contrast and bias, stretch and colormap, or color, on the values from one limit to the other
        bar = CompositeArray()
        bar.mode, bar.cmap_bad = artist.composite.mode, artist.composite.cmap_bad
        bar.allocate("bar")
        bar.set("bar", **{**layer, "array": np.linspace(*layer["clim"], 256)[:, np.newaxis]})
        rgba = bar()
        if rgba is None:  # a hidden layer
            return
        [image] = self.images
        image.set_data(rgba)
        low, high = artist.state.v_min, artist.state.v_max
        if low == high:  # a constant frame's, widened as matplotlib widens them, without its warning at each draw
            low, high = self.yaxis.get_major_locator().nonsingular(low, high)
        image.set_extent((0, 1, low, high))
        self.tick_params(labelsize=state.y_ticklabel_size)
        super().draw(renderer)


@viewer_tool
class ColorBarTool(Tool):
    """
    A color bar right of the image, which glue lacks (D50, #144): glue's own coloring of the reference layer
    (`_ColorBarAxes`), its room taken from the axes' margins so that the aspect keeps its proportions.
    """

    icon = _icon("solar_color_bar")
    tool_id = "solar:color_bar"
    action_text = "Color bar"
    tool_tip = "Show or hide a color bar of the displayed data's colors"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.bar = None  # made at the first press

    @property
    def checked(self):
        """Whether the color bar shows, as the View menu entry's check mark says."""
        return self.bar is not None and self.bar.get_visible()

    def activate(self):
        axes = self.viewer.axes
        if self.bar is None:
            right = axes.figure.dpi_scale_trans + ScaledTranslation(1, 0, axes.transAxes)  # inches right of the axes
            gap, width = _BAR
            where = blended_transform_factory(right, axes.transAxes)
            self.bar = axes.inset_axes([gap, 0, width, 1], transform=where, axes_class=_ColorBarAxes, visible=False)
            self.bar.viewer = self.viewer
            self.bar.imshow(np.zeros((1, 1, 4)), origin="lower", aspect="auto", interpolation="nearest")
            self.bar.set_xticks([])
            self.bar.yaxis.tick_right()
            update_appearance_from_settings(self.bar)  # glue's colors for its axes
        shown = not self.bar.get_visible()
        self.bar.set_visible(shown)
        left, right, bottom, top = axes.resizer.margins  # glue's, in inches
        axes.resizer.margins = [left, right + (_BAR_ROOM if shown else -_BAR_ROOM), bottom, top]
        canvas = self.viewer.figure.canvas  # glue places the axes and fits their aspect at a resize
        canvas.callbacks.process("resize_event", ResizeEvent("resize_event", canvas))
        _keep_mouse_mode(self.viewer)


@viewer_tool
class RasterOverlaysTool(Tool):
    """
    Show or hide the raster overlays of the viewer's observation on all its viewers (D40, #257): plain matplotlib
    lines, which sessions leave out.
    """

    tool_id = "solar:raster_overlays"
    action_text = "Raster overlays"
    tool_tip = "Show or hide each raster step's slit on the slit-jaw images and the step at the synced time on maps"

    @property
    def checked(self):
        """Whether the overlays of the viewer's observation show, as the View menu entry's check mark says."""
        return observation_key(self.viewer.state.reference_data) in coordinator(self.viewer._data).overlays

    def activate(self):
        coordinator(self.viewer._data).toggle_overlays(observation_key(self.viewer.state.reference_data))
        _keep_mouse_mode(self.viewer)

    def offered(self):
        """Whether a raster of the viewer's observation is loaded, which the View menu checks as it opens."""
        key = observation_key(self.viewer.state.reference_data)
        rasters = (data for data in self.viewer._data if _role(data) == "raster")
        return key is not None and any(observation_key(data) == key for data in rasters)


def sky_length(viewer, x, y):
    """
    The length of the line through ``x``, ``y`` on the viewer's axes as ``(pixels, arcsec, km)``: great-circle arcsec,
    and km at ``DSUN_OBS`` in the plane of the sky, without foreshortening (#147); None off the sky (`_sky_coords`).
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    pixels = float(np.hypot(np.diff(x), np.diff(y)).sum())
    angles = _sky_coords(viewer)
    if angles is None:
        return pixels, None, None
    world = angles[0].transform.transform(np.column_stack([x, y]))
    lon, lat = (u.Quantity(world[:, coord.coord_index], coord.coord_unit) for coord in angles)
    arcsec = angular_separation(lon[:-1], lat[:-1], lon[1:], lat[1:]).sum().to_value(u.arcsec)
    if not np.isfinite(arcsec):
        return pixels, None, None
    distance = viewer.state.reference_data.meta.get("DSUN_OBS")  # in m, as FITS gives it
    return pixels, float(arcsec), float((arcsec * u.arcsec).to_value(u.rad) * distance / 1000) if distance else None


@viewer_tool
class MeasureTool(ToolbarModeBase):
    """
    The length of a dragged line (`sky_length`) in the status bar (#147), until the next drag or other axes or data.
    """

    icon = "pencil"
    tool_id = "solar:measure"
    action_text = "Measure"
    tool_tip = "Drag a line to measure its length in pixels, arcsec and km"
    status_tip = "DRAG a line to measure its length in pixels, arcsec and km"
    shortcut = "U"

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)
        self._start = None  # the position the drag started at
        self._line = viewer.axes.add_line(Line2D([], [], color="#669dff", lw=1.5, zorder=100, visible=False))
        self.label = QtWidgets.QLabel()
        viewer.statusBar().insertPermanentWidget(0, self.label)
        self.label.hide()
        for prop in ("reference_data", "x_att", "y_att"):
            viewer.state.add_callback(prop, self._clear)

    def activate(self):
        # the last line again, as after glue-solar's plain tools, which glue-qt ends the mode for
        self.label.show()
        self._line.set_visible(len(self._line.get_xdata()) > 0)
        self.viewer.figure.canvas.draw_idle()
        super().activate()

    def close(self):
        for prop in ("reference_data", "x_att", "y_att"):
            self.viewer.state.remove_callback(prop, self._clear)
        super().close()

    def _clear(self, *_):
        self._start = None
        self._line.set_data([], [])
        self._line.set_visible(False)
        self.label.setText("")
        self.viewer.figure.canvas.draw_idle()

    def deactivate(self):
        self._start = None
        self.label.hide()
        if self.viewer is not None:  # None as the viewer closes
            self._line.set_visible(False)
            self.viewer.figure.canvas.draw_idle()
        super().deactivate()

    def press(self, event):
        if event.button == MouseButton.LEFT and event.inaxes is self.viewer.axes:
            self._start = event.xdata, event.ydata
            self.move(event)

    def move(self, event):
        if self._start is None or event.inaxes is not self.viewer.axes:
            return
        x, y = (self._start[0], event.xdata), (self._start[1], event.ydata)
        self._line.set_data(x, y)
        self._line.set_visible(True)
        pixels, arcsec, km = sky_length(self.viewer, x, y)
        text = f"Length {pixels:.1f} px"
        if arcsec is None:
            text += " (no sky length here)"
        else:
            text += f" · {_world_text(arcsec * u.arcsec)}" + ("" if km is None else f" · {km:,.0f} km")
        self.label.setText(text)
        self.viewer.figure.canvas.draw_idle()

    def release(self, event):
        self.move(event)
        self._start = None


class PathData(PathSlicedData):
    """
    glue-core's ``PathSlicedData`` of `PathTool`'s samples as given, each at its nearest pixel where glue-core 1.27.0
    truncates (D90): NaN and NaT off the data, where glue-core gives 0 and casts times to float, its own world
    coordinates (none where glue-core's fail) and a session record (#151, #191, #218).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stack = getattr(self.original_data.coords, "_wcs", None)
        if isinstance(stack, _PerScanWCS):  # scan 0's WCS with its Scan axis, which leaves no angles here
            self._coords = PathSlicedCoordinates(_GlueWCS(stack._wcs), self.sliced_dims)
        if self._coords is not None and self._coords.world_n_dim != self._coords.pixel_n_dim:
            self._coords = None

    def component_ids(self):
        # glue-core 1.27.0's session saver lists every dataset's, which only Data has: a diagram has none of its own
        return []

    def __gluestate__(self, context):
        return {
            "original_data": context.id(self.original_data),
            "cids": [context.id(self.cid_x), context.id(self.cid_y)],
            "x": context.do(self.x),
            "y": context.do(self.y),
            "label": self.label,
            "pixel_component_ids": [context.id(cid) for cid in self.pixel_component_ids],
            "world_component_ids": [context.id(cid) for cid in self.world_component_ids],
            "subsets": [context.id(subset) for subset in self.subsets],
        }

    @classmethod
    def __setgluestate__(cls, rec, context):
        data = context.object(rec["original_data"])
        (cid_x, cid_y), x, y = map(context.object, rec["cids"]), context.object(rec["x"]), context.object(rec["y"])
        path = cls(data, cid_x, x, cid_y, y, label=rec["label"])
        # its own components as saved, which its links, subsets and viewers name and may have restored first, as
        # glue's Data loader sets them
        pixel = [context.object(name) for name in rec["pixel_component_ids"]]
        world = [context.object(name) for name in rec["world_component_ids"]]
        for cid in pixel + world:
            cid.parent = path
        path._pixel_component_ids = pixel
        if world:  # in place of those made from the coordinates, with their values
            made = path.world_component_ids
            path._world_components = {cid: path._world_components[old] for cid, old in zip(world, made, strict=True)}
            path._world_component_ids = world
        for subset in rec["subsets"]:
            path.add_subset(context.object(subset))
        return path

    def set_xy(self, x, y, spacing=1):
        # the samples as they are, which glue-core would sample again as vertices; the rest is glue-core's
        self.x, self.y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        invalidate_cache(self)
        if getattr(self.original_data, "hub", None) is not None:
            self.original_data.hub.broadcast(NumericalDataChangedMessage(self))

    def _cells(self, view):
        """
        The index along each axis, the path's last, of the cells ``view`` selects, in NumPy's indexing, which drops an
        axis an integer selects, where glue-core's ``_get_pix_coords`` keeps it.
        """
        cells = np.ix_(*map(np.arange, self.shape))
        if view is not None and view is not Ellipsis:
            cells = [np.broadcast_to(cell, self.shape)[view] for cell in cells]
        return np.broadcast_arrays(*cells)

    def _pixels(self, cells, x, y):
        """The parent's pixel along each of its axes at ``cells``, of a path at ``x, y``."""
        *kept, path = cells
        kept = iter(kept)
        return [
            x[path] if axis == self.cid_x.axis else y[path] if axis == self.cid_y.axis else next(kept)
            for axis in range(self.original_data.ndim)
        ]

    def _get_pix_coords(self, view=None):
        # the nearest pixel, floor(position + 0.5), as scipy's map_coordinates rounds
        pixel = [np.floor(position + 0.5) for position in self._pixels(self._cells(view), self.x, self.y)]
        keep = np.all([(p >= 0) & (p < n) for p, n in zip(pixel, self.original_data.shape, strict=True)], axis=0)
        return [p[keep].astype(int) for p in pixel], keep, keep.shape

    def get_data(self, cid, view=None):
        if cid in self.pixel_component_ids or cid in self.world_component_ids:
            return BaseCartesianData.get_data(self, cid, view)
        pixel, keep, shape = self._get_pix_coords(view=view)
        values = np.asarray(self.original_data.get_data(cid, view=tuple(pixel)))
        if values.dtype.kind == "M":
            result = np.full(shape, "NaT", values.dtype)
        else:
            result = np.full(shape, np.nan, np.result_type(values.dtype, np.float32))
        result[keep] = values
        return result[()]


# glue-core 1.27.0 saves the link between two diagrams' paths as a ComponentLink through its own methods, which no
# session opens: save the diagrams it links instead
@saver(PathRelativeLink)
def _save_path_link(link, context):
    return {"paths": [context.id(link._slice_from), context.id(link._slice_to)]}


@loader(PathRelativeLink)
def _load_path_link(rec, context):
    return PathRelativeLink(*map(context.object, rec["paths"]))


def _placed(viewer, data, x, y):
    """
    The two pixel components of ``data`` the path ``x, y`` on the viewer's axes runs along, each with the path's
    positions (NaN off ``data``), through glue's links at the viewer's slices, or None; a stack's scan is not along it.
    """
    state = viewer.state
    if data is state.reference_data:
        return [(state.x_att, x), (state.y_att, y)]
    pixel = [np.full(x.shape, float(getattr(s, "center", s))) for s in state.slices]
    pixel[state.x_att.axis], pixel[state.y_att.axis] = x, y
    placed = []
    first = 1 if any(cid.label == "Scan" for cid in data.world_component_ids) else 0
    for cid in data.pixel_component_ids[first:]:
        try:
            values, axes = translate_pixel(state.reference_data, pixel, cid)
        except Exception:  # noqa: BLE001 - IncompatibleAttribute, or glue's bare Exception for other components
            continue
        if {state.x_att.axis, state.y_att.axis} & set(axes):
            placed.append((cid, np.broadcast_to(values, x.shape).astype(float)))
    return placed if len(placed) == 2 else None


def _diagrams(collection, placed, made=()):
    """
    glue-core's ``create_trace`` of samples: a `PathData` of each of ``placed`` (`_placed`), linked to its parent and
    sample by sample to the others, numbered past its parent's diagrams in ``collection`` and ``made``.
    """
    trace = []
    for data, ((cid_x, x), (cid_y, y)) in placed:
        count = sum(path.original_data is data for path in {*made, *(d for d in collection if isinstance(d, PathData))})
        path = PathData(data, cid_x, x, cid_y, y, label=f"{data.label} [slice {count + 1}]")
        collection.append(path)
        link_path_sliced_to_parent(collection, path)
        for other in trace:  # sample by sample
            link_path_sliced_pair_paths(collection, path, other)
        trace.append(path)
    return trace


def _drawn(state, collection):
    """The `PathData` diagrams in ``collection`` of the Image viewer's reference data on the axes it shows, oldest first."""
    shown = {getattr(state.x_att, "axis", None), getattr(state.y_att, "axis", None)}
    return [
        data
        for data in collection
        if isinstance(data, PathData) and data.original_data is state.reference_data and set(data.sliced_dims) == shown
    ]


@viewer_tool
class PathTool(BasePathSlicerMode, HubListener):
    """
    glue-core's path slicer for 3D and 4D data (#151, #165): sampled once a reference-data pixel and placed in each
    other dataset shown through glue's links (`_placed`), a new set of diagrams at each Enter; every viewer of an image
    draws the paths of its diagrams in the collection (#175), where glue-core draws only its own viewer's.
    """

    icon = _icon("solar_path_diagram")  # glue_path is glue's "Show position on original path"
    tool_id = "solar:path"
    action_text = "Path diagram"
    tool_tip = "Draw a path, then press Enter for the data along it (Esc clears the path)"
    status_tip = "CLICK the vertices of a path, then press ENTER for the data along it, or ESC to clear it"
    shortcut = "L"
    slice_viewer_cls = ImageViewer

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)
        for prop in ("x_att", "y_att"):
            viewer.state.add_callback(prop, self._refresh_overlays)
        hub = viewer.session.hub
        for message in (DataCollectionAddMessage, DataCollectionDeleteMessage):
            hub.subscribe(self, message, handler=self._refresh_overlays, filter=lambda m: isinstance(m.data, PathData))
        # also for a viewer torn down without closing its tools
        viewer.figure.canvas.destroyed.connect(lambda *_: hub.unsubscribe_all(self))

    def _on_reference_data_change(self, *args):
        # Data only: a stack's diagram is 3D too, but a PathData, which _open_or_update has nothing to sample in
        if self.viewer is not None and (reference := self.viewer.state.reference_data) is not None:
            self.enabled = isinstance(reference, Data) and reference.ndim >= 3
        self._refresh_overlays()

    def _refresh_overlays(self, *_):
        # glue-core's overlays, of the paths in the collection (_drawn), where glue-core draws its own traces in the
        # viewer they were drawn in
        if self.viewer is None:  # closed
            return
        state = self.viewer.state
        drawn = _drawn(state, self.viewer.session.data_collection)
        gone = [self._overlays.pop(path) for path in set(self._overlays) - set(drawn)]
        for line in gone:
            line.remove()
        for path in drawn:
            if path not in self._overlays:
                self._overlays[path] = self.viewer.axes.add_line(Line2D([], [], color=_PATH_COLOR, lw=2, zorder=100))
            along = {path.cid_x.axis: path.x, path.cid_y.axis: path.y}
            self._overlays[path].set_data(along[state.x_att.axis], along[state.y_att.axis])
            self._overlays[path].set_alpha(_PATH_ALPHA_ACTIVE if path is drawn[-1] else _PATH_ALPHA_INACTIVE)
        if gone or drawn:
            self.viewer.figure.canvas.draw_idle()

    def _finish_roi(self, event):
        # glue-core 1.27.0's path ROI blits the patch it has just removed, None, if it cached a background, which raises
        # before the path is extracted; without one it redraws
        self._roi_tool._background_cache = None
        super()._finish_roi(event)

    def _open_or_update(self, vx, vy):
        try:
            x, y = sample_points(vx, vy)
        except ValueError:  # fewer than two vertices, or under a pixel long
            return
        self._extract(x, y)

    def _extract(self, x, y):
        # PathData of the samples x, y placed in each dataset. Every Enter makes a new set: glue-qt 0.4.2 has no menu
        # to pick a path to update instead (glue-viz/glue-qt#66, draft, adds one)
        state = self.viewer.state
        datasets = [layer.layer for layer in state.layers if isinstance(layer.layer, Data)]
        # the reference data's first, which the crosshair follows
        datasets.sort(key=lambda data: data is not state.reference_data)
        placed = [(data, at) for data in datasets if (at := _placed(self.viewer, data, x, y)) is not None]
        made = [path for old in self._traces for path in old]
        trace = _diagrams(self.viewer.session.data_collection, placed, made)
        trace[0].parent_viewer = self.viewer
        self._traces.append(trace)
        # the reference data's only: glue cannot show the others on its axes, such as a raster window's wavelength
        # on a slit-jaw image's frames, and lists them disabled
        self._slice_viewer = open_slice_viewer_for(self.viewer, self.slice_viewer_cls, trace[:1])
        self._slice_viewers.append(self._slice_viewer)

    def _close_slice_viewers(self):
        # as the viewer closes, without the prompt of glue-qt's close, which glue-core 1.27.0 gives: Cancel would leave
        # a diagram without the viewer it was drawn in
        for slice_viewer in self._slice_viewers:
            slice_viewer.close(warn=False)
        self._slice_viewers.clear()
        self._slice_viewer = None


@viewer_tool
class PathCrosshairTool(BasePathSlicerCrosshairMode):
    """
    glue-core's diagram crosshair, also moving the parent viewer's other sliders to the diagram's y index, rounded
    within each axis, where glue-core 1.27.0 truncates and passes a stack's last scan (#262).
    """

    tool_id = "solar:path_crosshair"

    def _on_move(self, mode):
        x, y, path = self._event_xdata, self._event_ydata, self.data
        if not self._active or path is None or x is None or y is None:
            return
        index = round(np.clip(x, 0, path.shape[-1] - 1))
        self._crosshair.set_data([path.x[index]], [path.y[index]])
        source = path.parent_viewer.state
        if source.reference_data is path.original_data and self.viewer.state.y_att.axis < path.ndim - 1:
            source.slices = tuple(
                s if axis in path.sliced_dims else int(np.clip(np.round(y), 0, n - 1))
                for axis, (s, n) in enumerate(zip(source.slices, path.original_data.shape, strict=True))
            )
        path.parent_viewer.figure.canvas.draw_idle()


def _sky(coords, pixels):
    """The sky coordinates ``coords`` give at ``pixels``, a pixel or array of each axis in numpy order; None if none."""
    world = HighLevelWCSWrapper(coords).pixel_to_world(*pixels[::-1])
    return next((w for w in (world if isinstance(world, list) else [world]) if isinstance(w, SkyCoord)), None)


def _path_sky(path, row):
    """
    The sky coordinates of the samples of the `PathData` diagram ``path`` on its parent's coordinates at ``row``, an
    index of each other axis of the diagram and ``slice(None)``; None if they give none.
    """
    return _sky(path.original_data.coords, path._pixels(path._cells(row), path.x, path.y))


def _path_table(path):
    """
    The samples of ``path`` as a table: ``x`` and ``y``, and on the parent's coordinates at the first index of its other
    axes ``lon``, ``lat``, ``distance`` and ``distance_km``; its meta keep what `PathTool` remakes the diagram from.
    """
    data = path.original_data
    meta = {"data": data.label, "axes": list(path.sliced_dims)}
    table = Table({"x": path.x, "y": path.y}, meta=meta)
    sky = None if data.coords is None else _path_sky(path, (0,) * (path.ndim - 1) + (slice(None),))
    if sky is not None:
        table["lon"] = sky.spherical.lon.wrap_at(180 * u.deg).to(u.arcsec)
        table["lat"] = sky.spherical.lat.to(u.arcsec)
        table["distance"] = np.append(0, np.cumsum(sky[:-1].separation(sky[1:]).arcsec)) * u.arcsec
        if observer := data.meta.get("DSUN_OBS"):  # in m
            table["distance_km"] = table["distance"].to(u.rad).value * observer / 1000 * u.km
    return table


@messagebox_on_error("Could not save the path")
def _save_path(viewer):
    """Save the path of the Image viewer's `PathData` diagram as an ECSV table (`_path_table`)."""
    start = os.path.expanduser(rcParams["savefig.directory"])
    name, _ = QtWidgets.QFileDialog.getSaveFileName(viewer, "Save path as ECSV", start, "ECSV table (*.ecsv)")
    if name:
        _path_table(viewer.state.reference_data).write(name, format="ascii.ecsv", overwrite=True)


@messagebox_on_error("Could not open the path")
def _open_path(tool):
    """
    Open a path `_save_path` saved on the viewer of `PathTool` ``tool``, which shows the dataset it was drawn on, and
    make its diagrams as Enter does.
    """
    start = os.path.expanduser(rcParams["savefig.directory"])
    name, _ = QtWidgets.QFileDialog.getOpenFileName(tool.viewer, "Open path from ECSV", start, "ECSV table (*.ecsv)")
    if not name:
        return
    table, state = Table.read(name, format="ascii.ecsv"), tool.viewer.state
    along = dict(zip(table.meta["axes"], (table["x"], table["y"]), strict=True))
    if {state.x_att.axis, state.y_att.axis} != set(along):
        raise ValueError(f"The path is on pixel axes {table.meta['axes']} of {table.meta['data']}: show those.")
    tool._extract(np.asarray(along[state.x_att.axis]), np.asarray(along[state.y_att.axis]))


def _on_sky(data, lon, lat, when):
    """
    The two pixel components of ``data`` along which only its helioprojective angles vary, each with the positions of
    ``lon, lat`` along it at the frame or scan nearest ``when``; None unless there are two.
    """
    types = list(getattr(data.coords, "world_axis_physical_types", None) or ())
    if not set(_HPC) <= set(types):
        return None
    wcs, sky = data.coords, [types.index(kind) for kind in _HPC]
    matrix = np.asarray(wcs.axis_correlation_matrix)[:, ::-1]  # numpy's axis order
    on_sky, other = matrix[sky].any(axis=0), np.delete(matrix, sky, axis=0).any(axis=0)
    axes = np.flatnonzero(on_sky & ~other)
    if axes.size != 2:
        return None
    index, time = [0] * data.ndim, _time_component(data)
    for axis in np.flatnonzero(on_sky & other) if time is not None and when is not None else ():
        along = [0] * data.ndim
        along[axis] = slice(None)
        [index[axis]], _ = nearest([when], data[time, tuple(along)])
    world = list(wcs.pixel_to_world_values(*index[::-1]))
    for axis, angle in zip(sky, (lon, lat), strict=True):
        world[axis] = angle.to_value(wcs.world_axis_units[axis])
    pixel = wcs.world_to_pixel_values(*np.broadcast_arrays(*world))[::-1]
    return [(data.pixel_component_ids[axis], np.asarray(pixel[axis], float)) for axis in axes]


def _reused(viewer):
    """The path "Path on other data…" places: the Image viewer's `PathData` diagram, or the latest drawn on its image."""
    reference = viewer.state.reference_data
    drawn = [reference] if isinstance(reference, PathData) else _drawn(viewer.state, viewer.session.data_collection)
    return drawn[-1] if drawn else None


@messagebox_on_error("Could not place the path on other data")
def _reuse_path(viewer):
    """
    Diagrams of `_reused`'s path on each ticked dataset it can be placed in by longitude and latitude (`_on_sky`), each
    in a new viewer and linked to it sample by sample (#200).
    """
    path, collection = _reused(viewer), viewer.session.data_collection
    table = _path_table(path)
    if "lon" not in table.colnames:
        raise ValueError(f"{path.label} has no helioprojective coordinates to place its path by.")
    time = _time_component(path)
    at = np.asarray(path[time, (0,) * (path.ndim - 1) + (slice(None),)]) if time is not None else np.array([], "M8")
    when = next(iter(at[~np.isnat(at)]), None)
    sky = table["lon"].quantity, table["lat"].quantity, when
    offered = [
        (data, placed)
        for data in collection
        if isinstance(data, Data) and data is not path.original_data and data.ndim >= 3
        if (placed := _on_sky(data, *sky)) is not None
    ]
    if not offered:
        raise ValueError("No other 3D or 4D dataset has helioprojective coordinates to place the path in.")
    dialog = QtWidgets.QDialog(viewer, windowTitle="Path on other data")
    form = QtWidgets.QFormLayout(dialog)
    form.addRow(QtWidgets.QLabel(f"Diagrams of the path of {path.label} on:"))
    ticks = [QtWidgets.QCheckBox(data.label) for data, _ in offered]
    for tick in ticks:
        form.addRow(tick)
    if not _accepted(dialog, form):
        return
    ticked = [placed for placed, tick in zip(offered, ticks, strict=True) if tick.isChecked()]
    for diagram in _diagrams(collection, ticked):
        link_path_sliced_pair_paths(collection, diagram, path)
        open_slice_viewer_for(viewer, ImageViewer, [diagram])


def _track(viewer, x, y):
    """
    The motion through ``x, y`` on a distance-time `PathData` diagram (path along x, one time a row): the first and last
    times and km, and the speed (km / s) and acceleration (m / s2, NaN at two times) of the least-squares line or
    parabola; None without times, sky coordinates or ``DSUN_OBS`` (#175).
    """
    state, path = viewer.state, viewer.state.reference_data
    if not isinstance(path, PathData) or getattr(state.x_att, "axis", None) != path.ndim - 1:
        return None
    data, time = path.original_data, _time_component(path)
    observer = data.meta.get("DSUN_OBS")  # in m
    if time is None or not observer or data.coords is None:
        return None
    rows, times, km = {}, [], []
    for px, py in zip(x, y, strict=True):
        cell = _hovered(state, px, py)
        if cell is None:
            return None
        if cell[:-1] not in rows:  # each row once: a drag gives many points on one
            row = (*cell[:-1], slice(None))
            at = path[time, row]
            at = at[~np.isnat(at)]
            sky = _path_sky(path, row)
            if sky is None or at.size == 0 or at.min() != at.max():  # a raster map's times change along its path
                return None
            rows[cell[:-1]] = at[0], np.append(0, np.cumsum(sky[:-1].separation(sky[1:]).rad)) * observer / 1000
        when, along = rows[cell[:-1]]
        times.append(when)
        km.append(np.interp(px, np.arange(along.size), along))
    order = np.argsort(times, kind="stable")
    times, km = np.array(times)[order], np.array(km)[order]
    seconds = (times - times[0]) / np.timedelta64(1, "s")
    degree = min(np.unique(seconds).size - 1, 2)
    if degree < 1 or not np.isfinite(km).all():
        return None
    fit = np.polyfit(seconds, km, degree)[::-1]  # the lowest power first
    return times[0], times[-1], km[0], km[-1], fit[1], 2000 * fit[2] if degree == 2 else np.nan


# The columns of a diagram's table of slopes
_SLOPES = ("t0 (UTC)", "t1 (UTC)", "d0 (km)", "d1 (km)", "speed (km / s)", "acceleration (m / s2)")


@viewer_tool
class SlopeTool(PathMode):
    """
    glue's path mode on a distance-time diagram: Enter adds the track's motion (`_track`) as a row of the dataset
    '<diagram> slopes', shown in a Table viewer (#175).
    """

    icon = _icon("solar_slope")
    tool_id = "solar:slope"
    action_text = "Slope"
    tool_tip = "Click points along a track on a distance-time diagram, then press Enter for its speed (Esc clears them)"
    status_tip = "CLICK points along a track, then press ENTER for its speed and acceleration, or ESC to clear them"
    disable_on_finalize = False  # on for the next track

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, roi_callback=self._add_row, **kwargs)
        self.label = QtWidgets.QLabel()
        viewer.statusBar().insertPermanentWidget(0, self.label)
        self.label.hide()
        viewer.state.add_callback("reference_data", self._on_reference_data_change)
        self._on_reference_data_change()

    def _on_reference_data_change(self, *_):
        if self.viewer is not None:  # None once the viewer closes
            self.enabled = isinstance(self.viewer.state.reference_data, PathData)

    def activate(self):
        self.label.show()
        super().activate()

    def deactivate(self):
        self.label.hide()
        super().deactivate()

    def release(self, event):
        super().release(event)
        self._readout()

    def key(self, event):
        super().key(event)
        if event.key == "escape":
            self.clear()
            self.label.setText("")
            self.viewer.figure.canvas.draw_idle()  # glue's reset leaves the track drawn

    def _readout(self):
        """Show the motion of the points drawn, and return it, or None."""
        x, y = self.roi().to_polygon()
        motion = _track(self.viewer, x, y) if len(x) > 1 else None
        if motion is None:
            self.label.setText("No speed here" if len(x) > 1 else "")
            return None
        speed, acceleration = motion[-2:]
        text = f"Speed {speed:,.2f} km / s"
        self.label.setText(text if np.isnan(acceleration) else f"{text} · acceleration {acceleration:,.1f} m / s2")
        return motion

    def _add_row(self, mode):
        motion = self._readout()
        self.clear()  # a second Enter adds no second row
        if motion is None:
            return
        path, app = self.viewer.state.reference_data, self.viewer.session.application
        row = [np.datetime_as_string(t, unit="ms") for t in motion[:2]] + list(motion[2:])
        table = getattr(path, "slopes", None)
        new = table not in app.data_collection
        if not new:
            row = [np.append(table[name], value) for name, value in zip(_SLOPES, row, strict=True)]
        rows = Data(label=f"{path.label} slopes" if new else table.label)
        for name, values in zip(_SLOPES, row, strict=True):  # in this order, where Data(**columns) sorts them
            rows.add_component(np.atleast_1d(values), name)
        if new:
            path.slopes = rows
            app.data_collection.append(rows)
            app.new_data_viewer(TableViewer, data=rows)
            self.viewer.toolbar.active_tool = self  # glue-qt ends it as the new viewer takes the focus
            return
        table.update_values_from_data(rows)
        # glue-qt 0.4.2's Table viewer shows the rows its dataset had when shown, and fails to sort more: show them all
        for viewer in (viewer for tab in app.viewers for viewer in tab):
            if isinstance(viewer, TableViewer) and viewer.data is table:
                viewer.data = None
                viewer._on_layers_changed()


def _follows_mouse(group):
    """Whether the mouse may move the subset group ``group`` in Follow/lock: an unlocked point, or an empty group."""
    state = group.subset_state
    return not getattr(group, "_solar_locked", False) and (
        isinstance(state, PixelSubsetState) or type(state) is SubsetState
    )


class _LockPoint(ApplySubsetState):
    """glue's ``ApplySubsetState`` of a Pixel click, also locking the edit subset in Follow/lock; undo unlocks it."""

    label = "lock point"

    def do(self, session):
        super().do(session)
        # the edit subset after, which glue has made a new group if there was none
        edit = session.edit_subset_mode.edit_subset
        self.locked = [group for group in edit if not getattr(group, "_solar_locked", False)]
        for group in self.locked:
            group._solar_locked = True

    def undo(self, session):
        super().undo(session)
        for group in self.locked:
            group._solar_locked = False


@viewer_tool
class FollowLockTool(PixelSelectionTool):
    """
    CRISPEX's cursor (D6, D39, #119): the mouse moves an unlocked or empty edit subset as a Pixel click would, with no
    Undo step and at most once in 50 ms; a left click locks it in one Undo step, a right click or Esc unlocks it.
    """

    icon = "glue_point"
    tool_id = "solar:follow_lock"
    action_text = "Follow/lock"
    tool_tip = "Move the point with the mouse; click to lock it there, right-click or press Esc to unlock it"
    status_tip = "MOVE the mouse to move the point, CLICK to lock it there, RIGHT-CLICK or ESC to unlock it"

    def __init__(self, viewer):
        super().__init__(viewer)
        # each move asks for the point at the latest position, unless a move is already waiting for the throttle; the
        # timer is the viewer's, so that it goes with it
        self._timer = QtCore.QTimer(viewer)
        self._timer.setSingleShot(True)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._follow)
        self._move_callback = lambda mode: self._timer.isActive() or self._timer.start()

    def deactivate(self):
        self._timer.stop()  # no move once the tool is off
        super().deactivate()

    def press(self, event):
        self._log_position(event)
        if event.button == MouseButton.RIGHT:
            self._unlock()
            return
        state = self._pixel()
        if event.button == MouseButton.LEFT and state is not None:
            command = _LockPoint(data_collection=self.viewer._data, subset_state=state, override_mode=ReplaceMode)
            self.viewer.session.command_stack.do(command)

    def key(self, event):
        if event.key == "escape":
            self._unlock()

    def _unlock(self):
        for group in self.viewer.session.edit_subset_mode.edit_subset:
            group._solar_locked = False

    def _pixel(self):
        """The Pixel selection a Pixel click at the mouse's position would make, or None off the image."""
        state, x, y = self.viewer.state, self._event_xdata, self._event_ydata
        if x is None or y is None or _hovered(state, x, y) is None:
            return None
        slices = [slice(None)] * state.reference_data.ndim
        for att, index in ((state.x_att, round(x)), (state.y_att, round(y))):
            slices[att.axis] = slice(index, index + 1)
        return PixelSubsetState(state.reference_data, slices)

    def _follow(self):
        """Move the edit subset to the pixel under the mouse, unless it is locked or a region (see the class)."""
        mode, state = self.viewer.session.edit_subset_mode, self._pixel()
        if state is not None and all(_follows_mouse(group) for group in mode.edit_subset):
            mode.update(self.viewer._data, state, override_mode=ReplaceMode)


class _CoordinateEntry(Tool):
    """
    An entry of the ``solar:coordinate`` menu, shown while it is `offered`; the viewer's mouse mode, such as Pixel,
    stays on.
    """

    def __init__(self, viewer, menu):
        super().__init__(viewer)
        self.menu = menu

    def activate(self):
        self.run(self.menu.coordinator)
        _keep_mouse_mode(self.viewer)

    def offered(self):
        """Whether the entry can act on the viewer as it is now, which the menu checks as it opens."""
        return True


class _TimeMasterEntry(_CoordinateEntry):
    tool_id = "solar:time_master"
    action_text = "Lead the time"
    tool_tip = "Make the other datasets of this observation follow this one's time"

    def run(self, coordinator):
        coordinator.set_master(self.viewer.state.reference_data)

    def offered(self):
        data = self.viewer.state.reference_data
        return _timed(data) and observation_key(data) is not None


class _ClearPointEntry(_CoordinateEntry):
    tool_id = "solar:clear_point"
    action_text = "Clear point"
    tool_tip = "Clear the selected point"

    def run(self, coordinator):
        coordinator.clear_point()


class _LinkPointsEntry(_CoordinateEntry):
    tool_id = "solar:link_points"
    action_text = "Link points across cubes"
    tool_tip = "Move the points of the other linked cubes of the observation to the point's place on the Sun"

    @property
    def checked(self):
        return self.menu.coordinator.link_points

    def run(self, coordinator):
        coordinator.link_points = not coordinator.link_points

    def offered(self):
        # on a quicklook panel of a cube that is not IRIS data, the points it links
        owned = any(self.viewer in viewers for viewers in self.menu.coordinator._owners.values())
        return owned and _role(self.viewer.state.reference_data) not in _IRIS_ROLES


class _PointCurvesEntry(_CoordinateEntry):
    tool_id = "solar:point_curves"
    action_text = "Light curves at the point"  # the only one, against Time (D90)
    tool_tip = "Plot each window and slit-jaw image shown at the point against time, as new datasets that follow it"

    @messagebox_on_error("Could not add the light curves")
    def run(self, coordinator):
        _point_curves(self.viewer)

    def offered(self):
        # on a viewer of IRIS, AIA or SOT data, where the point has curves to plot, as `_point_curves` checks
        role = _role(self.viewer.state.reference_data)
        return role in ("raster", "sji", "aia") and _takes(_curve_sources, self.viewer.session.application)


class _RowEntry(_CoordinateEntry):
    tool_id = "solar:row"
    action_text = "Row at the point"
    tool_tip = "Open the row through the point along x (raster step or exposure), at the wavelength or band shown"
    label, back = "Row", 3  # along the raster's step or exposure axis, the third from the end

    @messagebox_on_error("Could not open the cut")
    def run(self, coordinator):
        _cut(self.viewer, self.viewer.state.reference_data.ndim - self.back, self.label)

    def offered(self):
        return _takes(_check_cut, self.viewer)


class _ColumnEntry(_RowEntry):
    tool_id = "solar:column"
    action_text = "Column at the point"
    tool_tip = "Open the column through the point along y (slit position), at the wavelength or band shown"
    label, back = "Column", 2  # along the slit


def _first_slider(viewer):
    """
    glue-qt's slice slider of the Image viewer's first array axis (an IRIS dataset's frames, exposures, steps or
    scans), or None where it has none, as while the viewer shows that axis.
    """
    sliders = viewer.options_widget().slice_helper._sliders
    return sliders[0] if sliders else None


class _GoToUTCEntry(_CoordinateEntry):
    """
    Move the observation's time master, or without one the viewer's first slider, to its index nearest a typed UTC
    time; nothing past half its cadence (D7, D38).
    """

    tool_id = "solar:go_to_utc"
    action_text = "Go to UTC…"
    tool_tip = "Move the dataset that leads the time to its frame, exposure, step or scan nearest a UTC time"

    def _master(self):
        data = self.viewer.state.reference_data
        return self.menu.coordinator._master(observation_key(data)) if _timed(data) else None

    def offered(self):
        timed = _timed(self.viewer.state.reference_data)
        return self._master() is not None or (timed and _first_slider(self.viewer) is not None)

    @messagebox_on_error("Could not go to UTC")
    def run(self, coordinator):
        viewer = self.viewer
        state = viewer.state
        data = state.reference_data
        master = self._master()
        if not self.offered():
            raise ValueError("The viewer has no frame, exposure, step or scan slider of timed data.")
        moved = data if master is None else master
        index, step = coordinator._timing(moved)
        if master is None:
            index = getattr(state.slices[0], "center", state.slices[0])
        times = _times(moved, step)
        shown = np.datetime_as_string(times[index], unit="ms")
        text, ok = QtWidgets.QInputDialog.getText(viewer, "Go to UTC", "UTC time:", text=shown)
        if not ok:
            return
        try:
            when = np.datetime64(text.strip(), "ns")
        except ValueError:
            when = np.datetime64("NaT", "ns")
        if np.isnat(when):
            raise ValueError(f"'{text}' is not a UTC time, such as 2013-09-02T17:00:00.")
        [index], [offset] = nearest([when], times)
        if abs(offset) > _half_cadence(times):
            seconds = offset / np.timedelta64(1, "s")
            raise ValueError(
                f"Nothing in {moved.label} is within half a cadence of {text}: the nearest, {index}, is "
                f"{seconds:+.1f} s off."
            )
        if master is None:
            state.slices = (int(index), *state.slices[1:])
        else:
            coordinator.move_master(master, int(index))


def _loop(slider, lo, hi, every=1, bounce=False):
    """
    Make glue-qt's playback of ``slider`` go round ``lo`` to ``hi``, ``every`` indices a step, or turn back with
    ``bounce`` (#166), replacing the ``_browse_slice`` its play timer calls; its step buttons keep glue-qt's.
    """

    def step(action, play=True):
        box = slider.value_slice_center
        value, by = box.value(), every if action == "next" else -every
        if lo <= value + by <= hi:
            box.setValue(value + by)
        elif bounce and lo <= value <= hi:
            slider._play_speed *= -1  # glue-qt's direction, so its timer plays the other way from now on
            box.setValue(min(max(value - by, lo), hi))
        else:
            box.setValue(lo if by > 0 else hi)

    slider._browse_slice, slider._solar_loop = step, (lo, hi, every, bounce)


class _LoopEntry(_CoordinateEntry):
    """
    Make glue-qt's playback of the viewer's frame, exposure, step or scan slider loop over a typed range of indices,
    every Nth index, going round or back and forth (bounce), until glue-qt rebuilds the slider for other data or axes.
    The dialog opens on the current loop.
    """

    tool_id = "solar:loop"
    action_text = "Loop…"
    tool_tip = "Make the frame, exposure, step or scan slider's playback loop over a range"

    def offered(self):
        return _first_slider(self.viewer) is not None

    @messagebox_on_error("Could not loop")
    def run(self, coordinator):
        slider = _first_slider(self.viewer)
        if slider is None:
            raise ValueError("The viewer has no frame, exposure, step or scan slider.")
        _, _, every, bounce = getattr(slider, "_solar_loop", (0, 0, 1, False))
        step = QtWidgets.QSpinBox()
        step.setRange(1, slider.value_slice_center.maximum())
        step.setValue(every)
        back = QtWidgets.QCheckBox("Bounce: play back and forth, not round")
        back.setChecked(bounce)
        picked = _ask_range(self.viewer, "Loop", slider, ("Play every Nth index:", step), (back,))
        if picked is not None:
            _loop(slider, *picked, step.value(), back.isChecked())


def _ask_range(viewer, title, slider, *rows):
    """
    The first and last index of ``slider`` typed in a dialog, or ``±N`` about the current one, or None if canceled;
    ``rows``, ``QFormLayout.addRow`` arguments, go below, their widgets to read as soon as this returns.
    """
    last, current = slider.value_slice_center.maximum(), slider.value_slice_center.value()
    lo, hi = getattr(slider, "_solar_loop", (0, last))[:2]
    dialog = QtWidgets.QDialog(viewer, windowTitle=title)
    form = QtWidgets.QFormLayout(dialog)
    line = QtWidgets.QLineEdit(f"{lo} {hi}")
    line.selectAll()  # as QInputDialog does, so typing replaces it
    form.addRow(f"First and last index (0–{last}), or ±N around {current}:", line)
    for row in rows:
        form.addRow(*row)
    if not _accepted(dialog, form):
        return None
    text = line.text()
    try:
        if text.strip().startswith(("±", "+-")):
            around = int(text.strip().removeprefix("±").removeprefix("+-"))
            lo, hi = max(current - around, 0), min(current + around, last)
        else:
            lo, hi = (int(value) for value in text.replace(",", " ").split())
    except ValueError:
        lo = hi = -1
    if not 0 <= lo <= hi <= last:
        raise ValueError(f"'{text}' is not two indices from 0 to {last}, the first not after the last, or ±N.")
    return lo, hi


# What `SaveSequenceTool` writes, by file name suffix; MP4 only where matplotlib finds ffmpeg
_SEQUENCE_FILTERS = {".png": "PNG frames (*.png)", ".mp4": "MP4 movie (*.mp4)", ".gif": "GIF movie (*.gif)"}
_MOVIE_FPS = 10
_SAVING = set()  # the viewers whose frames `SaveSequenceTool` is drawing: one at a time
# The lengths a scale bar takes, in arcsec
_SCALE_BARS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)


def _place_scale_bar(viewer, line, label):
    """
    Place ``line`` and ``label`` as a scale bar at the viewer's lower right: the largest of `_SCALE_BARS` the right
    quarter of the view spans at an x pixel's angle across the image (`sky_length`); hidden off the sky.
    """
    state, axes = viewer.state, viewer.axes
    nx, ny = (state.reference_data.shape[att.axis] - 1 for att in (state.x_att, state.y_att))
    y = np.clip((state.y_min + state.y_max) / 2, 0, ny)
    per_pixel = (sky_length(viewer, [0, nx], [y, y])[1] or 0) / max(nx, 1)
    (x0, _), (x1, _) = (axes.transAxes + axes.transData.inverted()).transform([(0.7, 0), (0.95, 0)])
    length = max((n for n in _SCALE_BARS if n <= abs(x1 - x0) * per_pixel), default=None)
    line.set_visible(length is not None)
    label.set_visible(length is not None)
    if length:
        x0 = x1 - np.sign(x1 - x0) * length / per_pixel
        line.set_data([x0, x1], [0.05, 0.05])
        label.set_position(((x0 + x1) / 2, 0.065))
        label.set_text(f'{length}"')


@viewer_tool
class SaveSequenceTool(Tool):
    """
    Save the figure at each index of one slider as PNG frames, an MP4 (where ffmpeg is) or a GIF, which glue lacks
    (#145, #265): a frame a turn of the event loop, after the time sync, so glue stays usable, with the viewer grayed
    and its limits fixed; Cancel, a close or a resize keeps the frames so far.
    """

    icon = "glue_filesave"
    tool_id = "solar:save_sequence"
    action_text = "Save frames or movie…"
    tool_tip = "Save the image at each index of a slider as PNG files or a movie"

    @messagebox_on_error("Could not save the frames or movie")
    def activate(self):
        try:
            self._save()
        finally:
            _keep_mouse_mode(self.viewer)

    def _save(self):
        if _SAVING:
            raise ValueError("Frames are being saved: wait for them, or press Cancel in their progress dialog.")
        viewer = self.viewer
        state, figure = viewer.state, viewer.figure
        sliders = [(axis, s) for axis, s in enumerate(viewer.options_widget().slice_helper._sliders) if s is not None]
        if not sliders:
            raise ValueError("The viewer has no slider.")
        labels = [slider.state.label for _, slider in sliders]
        label = labels[0]
        if len(sliders) > 1:
            label, ok = QtWidgets.QInputDialog.getItem(viewer, "Save frames or movie", "Slider:", labels, 0, False)
            if not ok:
                return
        axis, slider = sliders[labels.index(label)]
        boxes = [QtWidgets.QCheckBox(text) for text in ("UTC time on each frame", "Frame numbers", "Scale bar")]
        picked = _ask_range(viewer, "Save frames or movie", slider, *[(box,) for box in boxes])
        if picked is None:
            return
        (first, last), (timed, numbered, scaled) = picked, [box.isChecked() for box in boxes]
        ffmpeg = animation.writers.is_available("ffmpeg")
        filters = [text for suffix, text in _SEQUENCE_FILTERS.items() if suffix != ".mp4" or ffmpeg]
        name = re.sub(r"[^\w-]+", "_", f"{state.reference_data.label}_{first}-{last}")  # its suffix the filter's
        start = os.path.join(os.path.expanduser(rcParams["savefig.directory"]), name)
        path, chosen = QtWidgets.QFileDialog.getSaveFileName(viewer, "Save frames or movie", start, ";;".join(filters))
        if not path:
            return
        rcParams["savefig.directory"] = os.path.dirname(path)  # as glue's "Save plot to file" remembers it
        stem, suffix = os.path.splitext(path)
        if suffix.lower() not in _SEQUENCE_FILTERS:  # none typed: the chosen filter's
            stem, suffix = path, next((s for s, text in _SEQUENCE_FILTERS.items() if text == chosen), ".png")
        # ponytail: PillowWriter holds every GIF frame in memory until the end (+0.7 GiB for 400 frames of 788 × 597),
        # where an MP4 streams to ffmpeg; stream the frames to Pillow if long GIFs matter
        movie = {".mp4": animation.FFMpegWriter, ".gif": animation.PillowWriter}.get(suffix.lower())
        indices = range(first, last + 1)
        canvas = figure.canvas
        slices, size, manager = state.slices, figure.get_size_inches(), canvas.manager
        data = state.reference_data
        # playback, of the slider or of the time master it follows, would move the frame between a move and its save
        sync = coordinator(viewer._data)
        master = sync._master(observation_key(data)) if _timed(data) else None
        masters = [] if master is None else sync._viewers_of(master)
        for each in [s for _, s in sliders] + [_first_slider(v) for v in masters if isinstance(v, ImageViewer)]:
            if each is not None and each._play_timer.isActive():
                each.button_stop.click()
        per_frame = [ls for ls in state.layers if ls.layer is data and not getattr(ls, "stretch_global", True)]
        progress = QtWidgets.QProgressDialog("Saving frames…", "Cancel", 0, len(indices), viewer.session.application)
        progress.show()  # at once
        # white edged in black, to read on any colormap
        style = {"color": "white", "path_effects": [withStroke(linewidth=2, foreground="black")]}
        stamp = figure.text(0.01, 0.01, "", transform=viewer.axes.transAxes, **style) if timed else None
        top = slider.value_slice_center.maximum()
        number = figure.text(0.01, 0.99, "", va="top", transform=viewer.axes.transAxes, **style) if numbered else None
        bar = None
        if scaled and _sky_coords(viewer) is None:
            # the application's, which glue-qt's toolbar does not clear after the entry, as it does the viewer's
            viewer.session.application.statusBar().showMessage(
                "No scale bar: the displayed axes are not a longitude and a latitude"
            )
        elif scaled:
            where = blended_transform_factory(viewer.axes.transData, viewer.axes.transAxes)
            edged = {"color": "white", "path_effects": [withStroke(linewidth=5, foreground="black")]}
            # unsnapped, its ends where measured, not on pixel centers
            line = Line2D([], [], lw=3, solid_capstyle="butt", snap=False, transform=where, **edged)
            bar = viewer.axes.add_line(line), viewer.axes.text(0, 0, "", ha="center", transform=where, **style)
        # grayed, so that only the run moves the slider and changes the view: its sub-window too, which then cannot be
        # resized
        held = viewer.parent(), viewer.options_widget(), viewer.layer_view()
        steps = enumerate(indices, 1)
        timer = QtCore.QTimer(progress, singleShot=True)  # a frame a turn of the event loop
        writer = None
        ended = False

        def end():  # once: after the last frame, Cancel, an error, the viewer's close or a resize
            nonlocal ended
            ended = True
            _SAVING.discard(viewer)
            viewer.window_closed.disconnect(end)  # which holds the writer, a GIF's frames too
            canvas.resize_begin.disconnect(end)
            timer.stop()
            if writer is not None:
                text = f"Saving {os.path.basename(writer.outfile)}…"
                _start(viewer._data, text, "Could not save the frames or movie", writer.finish, add=lambda _: None)
            progress.deleteLater()
            for widget in held:
                widget.setEnabled(True)
            for artist in [stamp, number, *(bar or ())]:
                if artist is not None:
                    artist.remove()
            state.slices = slices
            for layer in per_frame:
                layer.stretch_global = False
            canvas.manager = manager
            figure.set_size_inches(size, forward=False)  # the start's, which a resize then changes
            canvas.draw_idle()

        @messagebox_on_error("Could not save the frames or movie")
        def tick():
            try:
                if progress.wasCanceled():
                    return
                count, index = next(steps)
                state.slices = tuple(index if i == axis else s for i, s in enumerate(state.slices))
                QtWidgets.QApplication.processEvents()  # the time sync, its overlays and Cancel, as in playback
                if ended:  # the viewer closed meanwhile
                    return
                if stamp is not None:
                    stamp.set_text(_frame_time(data, _shown_slice(state), 2))
                if number is not None:
                    number.set_text(f"frame {index}/{top}")
                if bar is not None:
                    _place_scale_bar(viewer, *bar)
                for image in viewer.axes.images:
                    if isinstance(image, BaseImageArtist):  # glue's image or density map, held 0.5 s after a resize
                        image.on_release()
                if writer is None:
                    figure.savefig(f"{stem}_{index:04d}.png")  # as 'Save plot to file' does
                else:
                    with rc_context({"savefig.bbox": None}):  # as the writer's saving() keeps it
                        writer.grab_frame()
                progress.setValue(count)
                if count < len(indices) and not progress.wasCanceled():
                    timer.start()
            finally:
                if not ended and not timer.isActive():  # the timer dies with the dialog once ended
                    end()

        _SAVING.add(viewer)
        viewer.window_closed.connect(end)
        # and a resize from outside the grayed sub-window (glue's Gather Windows, or the main window's with it
        # maximized), before the canvas takes its size: the frames, a movie's, keep one size and view
        canvas.resize_begin.connect(end)
        try:
            for widget in held:
                widget.setEnabled(False)
            # FFMpegWriter evens out an odd frame size through the canvas' manager, which would resize the canvas, and
            # glue would zoom to it: without one only the figure changes, until the end
            canvas.manager = None
            for layer in per_frame:
                layer.stretch_global = True
            if movie is not None:
                started = movie(fps=_MOVIE_FPS)
                started.setup(figure, stem + suffix)
                writer = started  # finished once set up
        except BaseException:
            end()
            raise
        timer.timeout.connect(tick)
        tick()  # the first frame at once: a movie has one, however soon the viewer closes


def _profile_table(viewer):
    """
    The Profile viewer's visible profiles as one table, ``<label>_x`` and ``<label>_y`` as glue computes them, with
    ``_y_normalized``, ``_time`` and ``_lon``/``_lat`` where they apply (#209, #239), and the labels left out: hidden
    layers but glue-solar's own (``_solar_own``), and visible ones without a profile.
    """
    state = viewer.state
    tables, names, hidden, skipped = [], [], [], []
    for artist in viewer.layers:
        layer = artist.state
        if not layer.visible:
            if not getattr(layer, "_solar_own", False):
                hidden.append(layer.layer.label)
            continue
        try:
            profile = None if artist.is_computing or not artist.enabled else layer.profile
        except Exception:  # glue's own limits skip a layer whose profile raises
            profile = None
        # glue 1.27.0 gives a subset one sample wide along x a single value, which it cannot draw
        if profile is None or not 0 < len(profile[0]) == len(profile[1]):
            skipped.append(layer.layer.label)
            continue
        x, y = profile
        data = layer.layer.data if isinstance(layer.layer, Subset) else layer.layer
        x_unit = state.reference_data.get_component(state.x_att).units
        y_unit = data.get_component(layer.attribute).units
        # glue converts only values with a unit
        x_unit = (state.x_display_unit or x_unit) if x_unit else None
        y_unit = (state.y_display_unit or y_unit) if y_unit else None
        meta = {"attribute": layer.attribute.label}
        subset = getattr(layer.layer, "subset_state", None)
        fixed = [None] * data.ndim
        if isinstance(subset, PixelSubsetState):
            fixed = subset._to_linked_pixel_coords(data)
            meta["pixel"] = {c.label: p for c, p in zip(data.pixel_component_ids, fixed, strict=True) if p is not None}
        elif isinstance(subset, SliceSubsetState) and subset.reference_data is data:  # a cut (D58)
            fixed = [s.start for s in subset.slices]
        name = disambiguate(as_variable_name(layer.layer.label), names)
        names.append(name)
        columns = [
            Column(x, f"{name}_x", unit=x_unit, description=state.x_att.label),
            Column(y, f"{name}_y", unit=y_unit, description=layer.layer.label, meta=meta),
        ]
        if state.normalize:
            columns.append(Column(layer.normalize_values(y), f"{name}_y_normalized", description=layer.layer.label))
        axis = is_convertible_to_single_pixel_cid(data, state.x_att_pixel).axis
        if _time_component(data) is not None and _time_axis(data) == axis:
            view = tuple(slice(None) if a == axis else p or 0 for a, p in enumerate(fixed))
            columns.append(Column(data[_time_component(data), view], f"{name}_time"))
        if any(p is not None for p in fixed) and data.coords is not None:
            sky = _sky(data.coords, [np.arange(len(x)) if a == axis else p or 0 for a, p in enumerate(fixed)])
            if sky is not None:
                columns.append(Column(sky.spherical.lon.wrap_at(180 * u.deg).to(u.arcsec), f"{name}_lon"))
                columns.append(Column(sky.spherical.lat.to(u.arcsec), f"{name}_lat"))
        tables.append(Table(columns))
    if not tables:
        raise ValueError("No visible layer has a profile.")
    table = hstack(tables, join_type="outer")
    table.meta["function"] = state.function
    return table, hidden, skipped


@viewer_tool
class SaveProfileTool(Tool):
    """
    Save the visible profiles (`_profile_table`) to ECSV, with the OBSID and STARTOBS (#209); the application's status
    bar names the layers left out.
    """

    icon = "glue_filesave"
    tool_id = "solar:save_profile"
    action_text = "Save profiles as ECSV…"
    tool_tip = "Save the visible profiles, as drawn, to an ECSV table"

    @messagebox_on_error("Could not save the profiles")
    def activate(self):
        viewer = self.viewer
        table, hidden, skipped = _profile_table(viewer)
        data = viewer.state.reference_data
        stem = re.sub(r"[^\w-]+", "_", str(data.meta.get("OBSID") or data.label))
        name = f"{stem} {table.meta['function']} profiles.ecsv"
        start = os.path.join(os.path.expanduser(rcParams["savefig.directory"]), name)
        name, _ = QtWidgets.QFileDialog.getSaveFileName(viewer, "Save profiles as ECSV", start, "ECSV table (*.ecsv)")
        if not name:
            return
        _write_ecsv(name, table, data.meta)
        # the application's, which glue-qt's toolbar does not clear after the entry, as it does the viewer's
        status = viewer.session.application.statusBar()
        left = {"hidden": hidden, "without a profile": skipped}
        left = "; ".join(f"{why}: {', '.join(labels)}" for why, labels in left.items() if labels)
        if left:
            status.showMessage(f"Left out, {left}")
        elif status.currentMessage().startswith("Left out, "):
            status.clearMessage()  # an earlier save's


@viewer_tool
class MainWindowTool(Tool):
    """
    'Show this window's panels' on a quicklook's spectrum panel of a window other than its main one, which makes it the
    main window (`~glue_solar.quicklook._switch`); hidden on every other Profile viewer.
    """

    icon = "glue_triangle_up"  # glue_slice is glue's Slice Extraction's
    tool_id = "solar:main_window"
    action_text = "Show this window's panels"
    tool_tip = "Make this window the quicklook's main window, with the map, spectrogram and wavelength panels"

    def __init__(self, viewer):
        super().__init__(viewer)
        viewer.toolbar_added.connect(partial(setattr, self, "enabled", False))  # until its quicklook offers it

    def activate(self):
        QtCore.QTimer.singleShot(0, self.switch)  # once glue-qt's toolbar is done with the click: the viewer closes

    @messagebox_on_error("Could not show this window's panels")
    def switch(self):
        if not self.viewer._closed:  # by a click before
            _switch(self.viewer)


def _position(viewer):
    """The Image viewer's position, D41's A or B: its reference data and slider position."""
    return viewer.state.reference_data, tuple(viewer.state.slices)


def _layers_of(state, data):
    """The viewer's layers of ``data`` and of its subsets."""
    return [layer for layer in state.layers if layer.layer.data is data]


def _show_position(viewer, coordinator, data, slices):
    """
    Show ``data`` at ``slices`` as a blink flip (D41): axes, zoom, point and time sync stay, a follower at its time
    sync index; glue resets them for other data, so they are set again, and the data left is hidden, as glue would
    retry its disabled layer at every draw (about a second on a full raster).
    """
    state = viewer.state
    shown = state.reference_data
    with coordinator.showing(viewer, data):
        if data is shown:
            state.slices = slices
            return
        index = coordinator.following(data)
        if index is not None and not isinstance(slices[0], AggregateSlice):
            slices = (index, *slices[1:])
        for layer in _layers_of(state, data):
            layer.visible = True
        x, y = state.x_att.axis, state.y_att.axis
        limits = state.x_min, state.x_max, state.y_min, state.y_max
        state.reference_data = data
        state.x_att = data.pixel_component_ids[x]
        state.y_att = data.pixel_component_ids[y]
        state.slices = slices
        with delay_callback(state, "x_min", "x_max", "y_min", "y_max"):
            state.x_min, state.x_max, state.y_min, state.y_max = limits
        for layer in _layers_of(state, shown):
            layer.visible = False


class _PartnerEntry(_CoordinateEntry):
    tool_id = "solar:blink_partner"
    action_text = "Set blink partner here"
    tool_tip = "Keep the displayed dataset and slider position as the one to blink against"

    def run(self, coordinator):
        if self.menu._blink.isActive():
            self.menu.blink(False)  # else the partner left would stay hidden
        self.menu.partner = _position(self.viewer)


class _BlinkEntry(_CoordinateEntry):
    tool_id = "solar:blink"
    action_text = "Blink"
    tool_tip = "Alternate the viewer between its position and its blink partner, or stop"

    @property
    def checked(self):
        """Whether the viewer blinks, as the entry's check mark says."""
        return self.menu._blink.isActive()

    def offered(self):
        return self.menu._valid()  # a blink whose partner goes stops at its next flip (`_flip`)

    @messagebox_on_error("Could not blink")
    def run(self, coordinator):
        self.menu.blink(not self.menu._blink.isActive())


def _pressed(session):
    """
    The viewer of the current tab's active window, which glue-qt gives a key, the coordinator, and the time master of
    the viewer's observation, as Go to UTC moves it, or None.
    """
    viewer = session.application.current_tab.activeSubWindow().widget()
    data, sync = viewer.state.reference_data, coordinator(session.data_collection)
    return viewer, sync, sync._master(observation_key(data)) if _timed(data) else None


def _step(slider, delta):
    """Step a glue-qt slice slider, or None, by ``delta``, round from either end as its own step buttons do."""
    if slider is not None:
        box = slider.value_slice_center
        box.setValue((box.value() + delta) % (box.maximum() + 1))


def _frame_key(delta, session):
    """
    D and F: move the time master of the active viewer's observation a frame, exposure, step or scan back or on, round
    from either end, as Go to UTC moves it, and the others follow; without one, the viewer's own first slider.
    """
    viewer, sync, master = _pressed(session)
    if master is not None:
        index, _ = sync._timing(master)
        sync.move_master(master, (index + delta) % master.shape[0])
    elif isinstance(viewer, ImageViewer):
        _step(_first_slider(viewer), delta)


def _wavelength_key(delta, session):
    """
    A and S: step the active Image viewer's wavelength slider back or on, round from either end, and in a quicklook's
    tab, pressed on any of its viewers, that of each of its panels but an SST quicklook's second map, unless pressed on
    it; nothing else moves.
    """
    viewer, sync, _ = _pressed(session)
    app = session.application
    group = getattr(app, "_solar_points", {}).get(app.current_tab)
    for each in dict.fromkeys([viewer, *(other for other in sync._owners.get(group, ()) if not _wing(other))]):
        data = each.state.reference_data
        if isinstance(each, ImageViewer) and data is not None:
            sliders = each.options_widget().slice_helper._sliders
            for axis in _spectral_axes(data):
                _step(sliders[axis] if axis < len(sliders) else None, delta)


def _play_key(session):
    """
    Space: play the first slider of a viewer of the time master, one with a loop first, or without one the active
    viewer's, or pause any of these playing (D61).
    """
    viewer, sync, master = _pressed(session)
    viewers = dict.fromkeys([viewer, *([] if master is None else sync._viewers_of(master))])
    sliders = {each: _first_slider(each) for each in viewers if isinstance(each, ImageViewer)}
    sliders = {each: slider for each, slider in sliders.items() if slider is not None}
    playing = [slider for slider in sliders.values() if slider._play_timer.isActive()]
    for slider in playing:
        slider.button_stop.click()
    time = [slider for each, slider in sliders.items() if master is None or each.state.reference_data is master]
    if time and not playing:
        next((slider for slider in time if hasattr(slider, "_solar_loop")), time[0]).button_forw.click()


# The keys glue-solar gives viewers (`glue_solar.setup`), as glue-qt's keyboard shortcuts: functions of the session
KEYS = {
    QtCore.Qt.Key_D: partial(_frame_key, -1),
    QtCore.Qt.Key_F: partial(_frame_key, 1),
    QtCore.Qt.Key_A: partial(_wavelength_key, -1),
    QtCore.Qt.Key_S: partial(_wavelength_key, 1),
    QtCore.Qt.Key_Space: _play_key,
}


class _ToolMenu(SimpleToolMenu):
    """
    glue's tool menu, its tools also in the toolbar's ``tools`` and ``actions`` as a button's are (#222): an entry shows
    while ``enabled``, as glue-qt 0.4.2 does for buttons only (glue-viz/glue-qt#72, draft), from ``offered`` as the menu
    opens, with a check mark from ``checked`` and its key while the toolbar has the keyboard.
    """

    def __init__(self, viewer, subtools=None):
        super().__init__(viewer, subtools=subtools)
        viewer.toolbar_added.connect(self._add_entries)

    def _add_entries(self):
        toolbar = self.viewer.toolbar
        menu = toolbar.widgetForAction(toolbar.actions[self.tool_id]).menu()
        for tool, action in zip(self.subtools, menu.actions(), strict=True):
            toolbar.tools[tool.tool_id], toolbar.actions[tool.tool_id] = tool, action

            def show(enabled, action=action):
                action.setVisible(enabled)
                action.setEnabled(enabled)

            add_callback(tool, "enabled", show)
            show(tool.enabled)
            if hasattr(tool, "checked"):
                action.setCheckable(True)
            if not action.shortcut().isEmpty():  # glue-qt's, on the entry, needs the menu's button focused
                key = QtWidgets.QShortcut(action.shortcut(), toolbar)
                key.setContext(QtCore.Qt.WidgetShortcut)
                key.activated.connect(lambda action=action: action.isEnabled() and action.trigger())
        menu.aboutToShow.connect(self._check)

    def _check(self):
        for tool in self.subtools:
            if hasattr(tool, "offered"):
                tool.enabled = tool.offered()
            if hasattr(tool, "checked"):
                self.viewer.toolbar.actions[tool.tool_id].setChecked(tool.checked)


def _submenu(menu, title, tool_tip):
    """A submenu of ``menu`` titled ``title``, its tooltip and those of its entries shown, as the menu's."""
    submenu = menu.addMenu(title)
    submenu.menuAction().setToolTip(tool_tip)
    submenu.setToolTipsVisible(True)
    return submenu


@viewer_tool
class CoordinateTool(_ToolMenu):
    """
    Register the viewer with its collection's `~glue_solar.quicklook.Coordinator` (D9), with the menu of time entries
    and the 'Point' and 'Blink' submenus (D61); on a slit-jaw image draw the frame's slit, the raster point and the
    raster overlays.
    """

    icon = "glue_link"
    tool_id = "solar:coordinate"
    # no action_text, which glue-qt would show beside the icon, to keep the toolbar short
    tool_tip = "Coordinate this viewer with the others of its observation"
    # the entries of the menu, then of each submenu, by its title, with its tooltip
    ENTRIES = (_TimeMasterEntry, _GoToUTCEntry, _LoopEntry)
    SUBMENUS = {
        "Point": (
            "The point: clear it, link it across cubes, its light curves, or the map's row and column through it",
            (_ClearPointEntry, _LinkPointsEntry, _PointCurvesEntry, _RowEntry, _ColumnEntry),
        ),
        "Blink": ("Alternate the viewer between its position and a partner", (_PartnerEntry, _BlinkEntry)),
    }

    def __init__(self, viewer, subtools=None):
        entries = [*self.ENTRIES, *(entry for _, entries in self.SUBMENUS.values() for entry in entries)]
        super().__init__(viewer, subtools=subtools or [entry(viewer, self) for entry in entries])
        self.coordinator = coordinator(viewer._data)
        self.coordinator.register(viewer)
        viewer.destroyed.connect(self._forget)
        self.partner = None  # the position the viewer does not show, which the blink shows next (D41)
        self._blink = QtCore.QTimer(viewer)
        self._blink.setInterval(500)
        self._blink.timeout.connect(self._flip)
        self.toolbar = viewer.toolbar
        self.mode = self.toolbar.active_tool
        self.toolbar.tool_activated.connect(self._remember_mode)
        self.toolbar.tool_deactivated.connect(self._remember_mode)
        self._slit = viewer.axes.add_line(Line2D([], [], color="white", lw=0.8, ls="--", zorder=99, visible=False))
        # the style of glue's crosshair, but not glue's single crosshair artist, which the PV slicer moves and hides
        self._marker = viewer.axes.add_line(
            Line2D([], [], marker="+", ms=12, mfc="none", mec="#d32d26", mew=1, ls="", zorder=100, visible=False)
        )
        # the raster overlays: each step's slit on a slit-jaw image, the step at the master's time on a map
        self._footprint = viewer.axes.add_line(
            Line2D([], [], gid="solar:footprint", color="white", lw=0.5, alpha=0.6, zorder=98, visible=False)
        )
        self._step = viewer.axes.add_line(
            Line2D([], [], gid="solar:step", color="white", lw=0.8, ls="--", zorder=99, visible=False)
        )
        self.coordinator.add_listener(self._synced)
        for prop in _WATCHED:
            viewer.state.add_callback(prop, self._draw)
        self._draw()

    def close(self):
        self._blink.stop()
        self._forget()
        for prop in _WATCHED:
            self.viewer.state.remove_callback(prop, self._draw)
        super().close()

    def _add_entries(self):
        """
        Move the entries of each of `SUBMENUS` into it and add the "Blink interval" submenu, which glue-qt 0.4.2's
        tool menus cannot hold, once glue-qt has built the menu, as its own Profile viewer tools edit theirs.
        """
        super()._add_entries()
        menu = self.toolbar.widgetForAction(self.toolbar.actions[self.tool_id]).menu()
        submenus = {}
        for title, (tool_tip, entries) in self.SUBMENUS.items():
            submenus[title] = _submenu(menu, title, tool_tip)
            for entry in entries:
                action = self.toolbar.actions[entry.tool_id]
                menu.removeAction(action)
                submenus[title].addAction(action)
        self._action = self.toolbar.actions[_BlinkEntry.tool_id]
        intervals = _submenu(submenus["Blink"], "Blink interval", "How often the viewer alternates")
        group = QtWidgets.QActionGroup(intervals)
        for seconds in (0.25, 0.5, 1, 2):
            action = group.addAction(f"{seconds:g} s")
            action.setToolTip(f"Alternate every {seconds:g} s")
            action.setCheckable(True)
            action.setChecked(seconds * 1000 == self._blink.interval())
            action.setData(seconds)
            intervals.addAction(action)
        # not through glue-qt's toolbar, so the mouse mode stays
        group.triggered.connect(lambda action: self._blink.setInterval(round(action.data() * 1000)))

    def blink(self, on):
        """
        Start alternating the viewer between its position and ``partner``, with a flip now, or stop, showing the
        partner's layers again; the "Blink" entry is checked while it runs.
        """
        try:
            if not on:
                self._blink.stop()
                if self.partner is not None:
                    for layer in _layers_of(self.viewer.state, self.partner[0]):
                        layer.visible = True
            elif not self._valid():
                raise ValueError("Choose 'Set blink partner here' first, at the position to blink against.")
            else:
                self._flip()
                self._blink.start()
        finally:
            self._action.setChecked(self._blink.isActive())

    def _valid(self):
        """
        Whether the viewer can blink: its partner's dataset is still one of its layers, with as many axes as the shown
        one, and the shown one is not hidden, as it is once glue falls back to the partner's for a removed one.
        """
        state = self.viewer.state
        shown = state.reference_data
        if self.partner is None or shown is None:
            return False
        data = self.partner[0]
        return (
            any(layer.layer is data for layer in state.layers)
            and data.ndim == shown.ndim
            and any(layer.visible for layer in _layers_of(state, shown))
        )

    def _flip(self):
        """Show ``partner``, which the position left becomes; once it cannot, stop the blink and forget the partner."""
        if not self._valid():
            self.blink(False)
            self.partner = None
            return
        shown = _position(self.viewer)
        _show_position(self.viewer, self.coordinator, *self.partner)
        self.partner = shown

    def _forget(self, *_):
        # also for a viewer torn down without closing its tools
        self.coordinator.unregister(self.viewer)
        self.coordinator.remove_listener(self._synced)

    def _remember_mode(self):
        self.mode = self.toolbar.active_tool

    def _synced(self, key, time, exposure):
        if not _off(self.viewer):  # a quicklook panel turned off, drawn once on
            self._draw()

    def _draw(self, *_):
        """Draw the slit, the raster point and the raster overlays on a slit-jaw image, or hide them; and on a map."""
        viewer, coordinator = self.viewer, self.coordinator
        state = viewer.state
        slit, point = coordinator.slit_on(viewer), coordinator.point_on(viewer)
        footprint, step = coordinator.footprint_on(viewer), coordinator.step_on(viewer)
        line = None
        if state.reference_data is None or state.reference_data.ndim != 3:
            slit = point = None
        if slit is not None or point is not None:
            ny, nx = state.reference_data.shape[1:]
            if point is not None and not (-0.5 <= point[0] <= nx - 0.5 and -0.5 <= point[1] <= ny - 0.5):
                point = None
            if slit is not None:
                line = ([slit, slit], [-0.5, ny - 0.5])
        if state.x_att is not None and state.x_att.axis != 2:  # a slit-jaw image shown transposed
            line, point, footprint = (None if xy is None else xy[::-1] for xy in (line, point, footprint))
        marker = None if point is None else ([point[0]], [point[1]])
        step = None if step is None else _across(state, state.reference_data.ndim - 3, [step])
        drawn = ((self._slit, line), (self._marker, marker), (self._footprint, footprint), (self._step, step))
        if any([_place(artist, xy) for artist, xy in drawn]):  # each sync calls this: redraw only for a move
            viewer.figure.canvas.draw_idle()


@viewer_tool
class ModesTool(_ToolMenu):
    """
    The menu of glue-solar's mouse modes, with the path entries (`_save_path`, `_open_path`, `_reuse_path`).
    """

    icon = "pencil"
    tool_id = "solar:modes"
    tool_tip = "Mouse modes: measure a line, draw a path for the data along it, or a speed on its diagram"

    def _add_entries(self):
        super()._add_entries()
        toolbar = self.viewer.toolbar
        path = toolbar.tools[PathTool.tool_id]
        modes = toolbar.widgetForAction(toolbar.actions[self.tool_id]).menu()
        # not through glue-qt's toolbar, so the mouse mode stays: saving on a diagram, as Slope is, opening where Path
        # diagram is
        for text, tool_tip, run, shown in (
            (
                "Save path as ECSV…",
                "Save this diagram's path, with its longitude, latitude and distance, as an ECSV table",
                lambda: _save_path(self.viewer),
                toolbar.tools[SlopeTool.tool_id],
            ),
            ("Open path from ECSV…", "Make the diagrams of a path saved as ECSV", lambda: _open_path(path), path),
        ):
            action = modes.addAction(text)
            action.setToolTip(tool_tip)
            action.triggered.connect(run)
            add_callback(shown, "enabled", action.setVisible)
            action.setVisible(shown.enabled)
        # on a diagram, or an image with a path drawn
        reuse = modes.addAction("Path on other data…")
        reuse.setToolTip("Place this path on other datasets, at the same places on the Sun, for their diagrams")
        reuse.triggered.connect(lambda: _reuse_path(self.viewer))

        def offer():
            reuse.setVisible(_reused(self.viewer) is not None)

        modes.aboutToShow.connect(offer)
        offer()


@viewer_tool
class ViewTool(_ToolMenu):
    """
    The Image viewer's View menu: glue-solar's display tools, which leave the mouse mode on, each checked while on.
    """

    icon = "glue_settings"
    tool_id = "solar:view"
    tool_tip = (
        "View: frame time, axes, color limits, wavelength band, aspect, zoom, color bar, raster overlays and cursor "
        "readout"
    )
