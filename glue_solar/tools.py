"""
Toolbar tools for glue's viewers.
"""

import os
import re
from contextlib import nullcontext
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
from glue.core.state import GlueSerializer, loader, saver
from glue.core.subset import SliceSubsetState, SubsetState
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
from matplotlib import animation, rcParams
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseButton, ResizeEvent
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.patheffects import withStroke
from matplotlib.transforms import ScaledTranslation, blended_transform_factory
from qtpy import QtCore, QtWidgets

import astropy.units as u
from astropy.coordinates import Angle, SkyCoord, angular_separation
from astropy.table import Column, Table, hstack
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar.quicklook import (
    _across,
    _half_cadence,
    _is_sit_and_stare,
    _light_curve,
    _place,
    _point_curves,
    _role,
    _seconds_text,
    _shown,
    _spectral_axes,
    _sync_text,
    _time_axis,
    _time_text,
    _timed,
    _times,
    _value_text,
    _world_text,
    coordinator,
    nearest,
    observation_key,
)
from glue_solar.sources.iris import _write_ecsv
from glue_solar.sources.loaders.iris import _GlueWCS
from glue_solar.sources.loaders.stack_spectrograms import _PerScanWCS
from glue_solar.sources.moments import _accepted

__all__ = [
    "BandTool",
    "ColourBarTool",
    "CoordinateTool",
    "CursorReadoutTool",
    "FollowLockTool",
    "FrameTimeTool",
    "HideAxesTool",
    "MeasureTool",
    "ModesTool",
    "PathCrosshairTool",
    "PathData",
    "PathTool",
    "PerFrameLimitsTool",
    "PhysicalAspectTool",
    "SaveProfileTool",
    "SaveSequenceTool",
    "SlopeTool",
    "ViewTool",
    "ZoomOneToOneTool",
    "sky_length",
]

# Whether a new Image viewer shows its axes; the user guide says how to change it
settings.add("SOLAR_SHOW_AXES", True, validator=bool)

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
    Make the viewer's slice sliders follow a drag with its latest position instead of every position.

    glue-qt applies every value a slider passes through, and each one recomputes and redraws the
    image, so on a large cube a drag queues redraws and lags behind the mouse. With tracking off a
    drag reports only its release, and a 0 ms timer applies the latest dragged position in between, as
    soon as Qt has handled the input queued behind the previous one. Keys, clicks and playback still
    apply at once.

    Always on, until glue-qt coalesces a drag itself (``wp0-perf-qt``). It finds the sliders by glue-qt's
    object name ``value_slice_center``, which the drag test pins.
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


def _world_position(axes, x, y, keep=None):
    """
    The world position WCSAxes reads out at ``x, y`` of the WCSAxes ``axes``, with each coordinate it shows in arcsec
    (a helioprojective longitude or latitude) to 0.01" and each it shows in Å (an IRIS wavelength) to 0.001 Å, a tenth
    of an IRIS pixel or finer, where WCSAxes gives each the precision of its ticks (2834 for a wavelength of an NUV
    window, of 0.025 Å pixels); other coordinates, such as a right ascension or a Carrington longitude, keep WCSAxes'
    text. Given ``keep``, one of the coordinates of ``axes``, the other angles are left out.
    """
    world = axes.coords[0].transform.transform(np.array([[x, y]]))[0]
    texts = []
    for coord in axes.coords:
        if coord.coord_index is None:  # not on these axes
            continue
        if coord.coord_type in ("longitude", "latitude") and keep not in (None, coord):
            continue
        value = world[coord.coord_index] * coord.coord_unit
        if coord.get_format_unit() == u.arcsec:
            angle = Angle(value) if coord.coord_wrap is None else Angle(value).wrap_at(coord.coord_wrap)
            texts.append(_world_text(angle))
        elif coord.get_format_unit() == u.AA:
            texts.append(_world_text(value))
        else:
            texts.append(coord.format_coord(world[coord.coord_index], format="ascii"))
    return " ".join(texts) + " (world)"


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
    Give the x (``index`` 0) or y (1) axis of the WCSAxes ``axes`` integer pixel-index ticks, instead of
    the world coordinates, and return that axis' coordinate helper.

    The ticks are a pixel overlay of WCSAxes. Of the world coordinates only ``shown``, glue's coordinate
    along the other axis, keeps ticks, at fixed places on that axis; left to WCSAxes' automatic
    placement, the others would move to free edges as the limits change, and glue's labels to
    whichever coordinate holds an axis' edge.
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
    Hide the tick labels of a longitude or latitude, of any celestial frame, of the WCSAxes ``axes`` that barely
    changes across the displayed array of ``shape`` (x, y) while another coordinate, such as wavelength or time, is
    shown beside the two, as the latitude along a raster's steps does: pointing jitter takes it back and forth across
    each tick value, and WCSAxes labels every crossing, one over another. Beside two other coordinates, such as a
    stack's wavelength and scan, along which only each scan's pointing moves them, both angles lose their tick labels.
    An image of the two angles alone, such as a map or a slit-jaw image, keeps both. Decided on the array's edges, so
    zooming keeps it, with a longitude across 0° unwrapped rather than 360° wide.
    """
    shown = [coord for coord in axes.coords if coord.coord_index is not None]  # the others are not on these axes
    angles = [coord for coord in shown if coord.coord_type in ("longitude", "latitude")]
    if len(angles) != 2 or len(shown) == 2:  # an image of the two angles alone: both change across it
        return
    if len(shown) > 3:
        for coord in angles:
            coord.set_ticklabel_position("")
        return
    x, y = (np.linspace(0, n - 1, 64) for n in shape)  # -TAB rasters have no coordinates past the outer centres
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


def _shown_slice(state):
    """The index of the Image viewer's displayed slice of its reference data, or None while it shows none."""
    data = state.reference_data
    if data is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
        return None
    shown = (state.x_att.axis, state.y_att.axis)
    # an aggregated slider range carries its slice on the AggregateSlice object
    return tuple(slice(None) if i in shown else getattr(s, "slice", s) for i, s in enumerate(state.slices))


def _frame_time(data, view, decimals=3):
    """
    The time of ``view``, a `_shown_slice`, of ``data`` from its first datetime component, in UTC to ``decimals`` of a
    second, or the first and last of several; '' without one.
    """
    cid = None if view is None else _time_component(data)
    if cid is None:
        return ""
    times = data[cid, view]
    times = times[~np.isnat(times)]  # NaT: a gap of data regridded on time
    if times.size == 0:  # a Collapse range narrower than one sample, or a gap
        return ""
    # 'YYYY-MM-DDThh:mm:ss.' and the decimals
    first, last = (np.datetime_as_string(t, unit="ms")[: 20 + decimals] for t in (times.min(), times.max()))
    return f"{first} UTC" if first == last else f"{first} – {last} UTC"


@viewer_tool
class FrameTimeTool(Tool, HubListener):
    """
    Show the acquisition time of the displayed frame in the Image Viewer's status bar.

    The readout follows the sliders and reads the first datetime component of the reference
    data, whichever loader attached it (the IRIS loaders add ``Time``, one per SJI exposure or
    raster step); its entry of the View menu (`ViewTool`) hides and shows it. A frame spanning several exposures,
    such as a raster shown as step against slit, shows the range. Data with an ``Exposure time``
    component also show it, and an SJI frame's pointing is in the tooltip. For an IRIS observation
    the readout also says which dataset is the time master (with its timing step for a raster), the
    signed offset of a matched follower's time from the master's, or NO MATCH with that offset,
    when the follower keeps its frame and is greyed.

    The tool exists for every Image viewer, so it also throttles the viewer's slice sliders, labels
    a displayed sit-and-stare exposure axis 'Exposure (acquisition order)' with the UTC range of its
    exposures, in glue's own axis label, with integer exposure ticks instead of the helioprojective
    coordinates glue would show along it, and hides the tick labels of a longitude or latitude that
    barely changes across an image showing another coordinate beside the two, such as the latitude on
    a raster's wavelength-against-step panel (`_hide_flat_angles`). glue resets these whenever it resets
    the axes (an axis or data change, or a slice the displayed coordinates depend on, such as the slit
    on the wavelength panel), and the tool applies them again; a label typed in the viewer's axes
    options is kept until then, as glue's own labels are.

    It also gives the mouse-over readout (the axes' ``format_coord``, which glue-solar's Cursor readout and
    glue-qt's own show), which follows the mouse, the hovered pixel's time and exposure, from the same
    components: on a raster map each step's, on a slit-jaw image or a sit-and-stare raster the frame's or
    exposure's. Its position has fixed precision (`_world_position`), and on a displayed sit-and-stare
    exposure axis reads only the coordinate along the other axis, as the ticks do, with the time and
    exposure in place of the slit's position along the exposures. The View menu entry hides the frame time only.
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
        # greys a follower with no frame near the time master's
        self._grey = viewer.axes.add_patch(
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
        text, state = self._format_coord(x, y), self.viewer.state
        data = state.reference_data
        if data is None or state.x_att is None or state.y_att is None:
            return text
        if text.endswith(" (world)"):  # not a pixel position or an overlay, which W switches to
            axes, shown = self.viewer.axes, (state.x_att.axis, state.y_att.axis)
            # glue's own mapping of the axis beside the exposures to its world coordinate, as for the ticks
            keep = axes.coords[data.ndim - 1 - max(shown)] if 0 in shown and _sit_and_stare_raster(data) else None
            text = _world_position(axes, x, y, keep)
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
        Hide the tick labels of a flat angle, and label a displayed sit-and-stare exposure axis and give it
        exposure ticks (see the class).
        """
        state = self.viewer.state
        data = state.reference_data
        axes, shown = self.viewer.axes, (state.x_att, state.y_att)
        if data is not None and None not in shown and axes.coords is not self._flat_checked:  # glue reset the axes
            self._flat_checked = axes.coords
            _hide_flat_angles(axes, [data.shape[att.axis] for att in shown])
        if not _sit_and_stare_raster(data):
            return
        for index, axis in enumerate("xy"):
            att, world = getattr(state, f"{axis}_att"), getattr(state, f"{axis}_att_world")
            other = getattr(state, f"{'yx'[index]}_att")
            if att is None or other is None or att.axis != 0:
                continue
            label = getattr(state, f"{axis}_axislabel")
            if label in ("", getattr(world, "label", None)):  # glue's reset
                setattr(state, f"{axis}_axislabel", _exposure_label(data))  # which calls this again
                return
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
        self._refresh()

    def _forget(self, *_):
        self.coordinator.remove_listener(self._synced)
        self._hub.unsubscribe_all(self)

    def _refresh(self, *_):
        state = self.viewer.state
        data = state.reference_data
        status = self.coordinator.time_status(self.viewer)
        unmatched = status is not None and status[0] == "no match"
        if self._grey.get_visible() != unmatched:
            self._grey.set_visible(unmatched)
            self.viewer.figure.canvas.draw_idle()
        self.label.setStyleSheet("color: gray" if unmatched else "")
        view = _shown_slice(state)
        text = _frame_time(data, view)
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
        self.label.setToolTip(_pointing(data.meta, view[0]))


def _pointing(meta, frame):
    """The SJI pointing of one frame, or nothing when several frames or no pointing are shown."""
    if not isinstance(frame, int | np.integer) or "pztx" not in meta:
        return ""
    return (
        f"PZT offset {meta['pztx'][frame]:.2f}″, {meta['pzty'][frame]:.2f}″; "
        f"FOV centre {meta['xcenix'][frame]:.2f}″, {meta['ycenix'][frame]:.2f}″; "
        f"slit at x = {meta['slit x position'][frame]:.1f} px"
    )


@viewer_tool
class CursorReadoutTool(Tool):
    """
    Show the world position and the data value under the mouse in the Image Viewer's status bar.

    The position is whatever the reference data's WCS maps the displayed axes to (helioprojective
    position, wavelength, ...), as the viewer's WCSAxes reads it out, with the time and exposure the
    Frame time tool adds; the value is the reference layer's displayed attribute at that pixel of the
    current slice. Pressing ``w`` over the image switches WCSAxes between world and pixel positions.
    Its View menu entry hides and shows the readout.
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
        value = _value_text(data[layer.attribute, view])
        # IRIS components are named after their dataset; say 'value' rather than repeat it
        name = "value" if layer.attribute.label == data.label else layer.attribute.label
        return f"{text} | {name} = {value}"


@viewer_tool
class HideAxesTool(Tool):
    """
    Hide or show the Image viewer's axes: their ticks, tick labels, axis labels and frame.

    Its entry switches glue's own ``show_axes`` viewer state, which glue-qt 0.4.2 has no control for
    and sessions save; a new viewer starts from the ``SOLAR_SHOW_AXES`` glue setting. Without its axes
    WCSAxes places no ticks when the viewer draws, so slice steps and redraws are faster. The image,
    subsets, links and the readouts are unchanged; the mouse-over position stays in world coordinates.
    A plain tool, since a checkable glue tool is a mouse mode, which would end Pixel; glue-qt ends the
    mouse mode before running a plain tool too, so the tool switches it back on, as glue-solar's
    other tools do.
    """

    icon = "glue_image"
    tool_id = "solar:hide_axes"
    action_text = "Hide axes"
    tool_tip = "Hide or show the axes, which makes slice steps and redraws faster"

    def __init__(self, viewer):
        super().__init__(viewer)
        if not viewer.state.layers:  # a new viewer; a restored one already has its session's layers and axes
            viewer.state.show_axes = settings.SOLAR_SHOW_AXES
        viewer.state.add_callback("show_axes", self._show)
        self._show()
        self._placed = None  # the WCSAxes coordinates, view and size for which the readout placed the ticks
        self._format_coord = viewer.axes.format_coord  # WCSAxes' world readout, set on the axes
        viewer.axes.format_coord = self._readout

    @property
    def checked(self):
        """Whether the axes are hidden, as the View menu entry's check mark says."""
        return not self.viewer.state.show_axes

    def activate(self):
        self.viewer.state.show_axes = not self.viewer.state.show_axes
        _keep_mouse_mode(self.viewer)

    def close(self):
        self.viewer.state.remove_callback("show_axes", self._show)
        self.viewer.axes.format_coord = self._format_coord
        super().close()

    def _readout(self, x, y):
        """
        WCSAxes' mouse-over readout, which formats each world coordinate as its last tick placement does.
        Without axes no draw places the ticks, and before its first draw nothing places those of the
        coordinates glue makes when it resets the axes, so the first readout after a reset, a zoom, a pan
        or a resize places them once. Always on, with no upstream change tracked.
        """
        axes = self.viewer.axes
        placed = (axes.coords, axes.viewLim.bounds, axes.bbox.bounds)
        if placed != self._placed:
            axes._update_tick_and_label_positions()
            self._placed = placed
        return self._format_coord(x, y)

    def _show(self, *_):
        axes, shown = self.viewer.axes, self.viewer.state.show_axes
        if axes.axison != shown:
            axes.set_axis_on() if shown else axes.set_axis_off()
            self.viewer.figure.canvas.draw_idle()


@viewer_tool
class PerFrameLimitsTool(Tool):
    """
    Take the colour limits of the Image viewer's reference data from the displayed slice, so each slice step, such as
    a wavelength step of a raster map, gives that slice's limits, or again from the whole cube.

    Its entry switches glue's own ``stretch_global`` of each layer of the reference data, which glue-qt 0.4.2 has no
    control for: to per frame for every layer unless all already are. The layer's percentile, such as 99.5%, applies
    to the slice, and on lazily loaded IRIS data the limits count every value of it (`LazyData`). A layer of another
    dataset keeps its limits, and one of the previous reference data takes its whole cube's again, since glue would
    take them from its values at the reference data's slice indices: the wrong slice, or an IndexError for a cube of
    another shape. A plain tool, as Hide axes is, since a checkable glue tool is a mouse mode, which would end
    Pixel; it leaves the mouse mode on. glue-core 1.27.0 fails to restore a session saved with per-frame limits on
    (``wp0-core-session-reports``).
    """

    icon = "glue_rainbow"
    tool_id = "solar:per_frame_limits"
    action_text = "Per-frame limits"
    tool_tip = "Take the colour limits from the displayed slice, or again from the whole cube"

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
    Show the Image viewer's map as the mean over a band of 5, 9 or 15 wavelength pixels about the wavelength slider, or
    again at the slider's wavelength alone.

    The band is glue's own ``AggregateSlice`` with ``np.nanmean``, which the Profile viewer's Collapse with Mean sets,
    on each wavelength axis of the reference data the viewer does not show, cut at the ends of the axis. glue-qt
    0.4.2 makes it a single wavelength again whenever any slider moves (``wp0-qt-aggregate-slice``), so a validator
    of the viewer's ``slices`` turns a wavelength index into the band about it: the slider, A and S, scan and step
    moves and the time sync keep the band. A session saves the band shown, not the choice. A plain tool, as Hide
    axes is, offered for data with a wavelength axis.
    """

    icon = "glue_xrange_select"
    tool_id = "solar:band"
    action_text = "Wavelength band…"
    tool_tip = "Show the mean over 5, 9 or 15 wavelength pixels about the slider's"

    WIDTHS = (1, 5, 9, 15)

    def __init__(self, viewer):
        super().__init__(viewer)
        self.width = 1
        viewer.state.add_callback("slices", self._band, validator=True)
        viewer.state.add_callback("reference_data", self._enable)
        self._enable(viewer.state.reference_data)

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
        self.viewer.state.remove_callback("reference_data", self._enable)
        super().close()

    def _enable(self, data):
        self.enabled = data is not None and bool(_spectral_axes(data))

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
    through the view centre, or None off the sky (`_sky_coords`). Averaged between the outer pixel centres, since -TAB
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


_ASPECT_HOOKS = ("_set_axes_aspect_ratio", "_axes_aspect_ratio", "_adjust_limits_aspect")


@viewer_tool
class PhysicalAspectTool(Tool):
    """
    Show the Image viewer's image in its proportions on the sky: an arcsecond as long on screen along x as along y.

    Its entry switches glue's 'Square Pixels' aspect on, scaled by the angle a pixel spans along y over the angle
    along x (`_arcsec_ratio`), so that a raster map of 2″ steps along a slit of 0.17″ pixels shows each step 12 times
    as wide as a slit pixel. glue keeps these proportions as it keeps square pixels, through resizes, zooms, pans and
    slices; the ratio is taken again when the displayed axes change, as glue shows the whole image again. On axes
    other than a longitude and a latitude alone, such as a spectrogram's or a sit-and-stare raster's exposures against
    its slit, the pixels are square. Pressed again, or with 'Automatic' chosen in the viewer's options, the viewer
    returns to the aspect it had; back to 'Automatic' from the entry, the image fills the axes again, keeping a
    zoom. A plain tool, as 'Hide axes' is, which leaves the mouse mode on.
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
        # glue's private aspect hooks this scales; a glue without them gets an entry that does nothing, not no viewer
        self._hooked = all(hasattr(state, name) for name in _ASPECT_HOOKS) and hasattr(viewer, "axes_ratio")
        if not self._hooked:
            return
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
        if not self._hooked:
            return _keep_mouse_mode(self.viewer)
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
        if not self._hooked:
            return super().close()
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


@viewer_tool
class ZoomOneToOneTool(Tool):
    """
    Zoom the Image viewer about the view centre so that one pixel of its reference data along x spans one screen pixel.

    A screen pixel is a device pixel, as matplotlib's display coordinates are: on a HiDPI screen, with a device pixel
    ratio of 2, the image shows at half its size in Qt's logical pixels. glue's x and y limits are in the pixels of
    whichever axes are shown, so a wavelength or swapped axis zooms the same way. A y pixel also spans one screen pixel,
    unless 'Physical aspect' is on, which keeps the sky's proportions: there it spans the angle it covers over that of
    an x pixel, such as 1/12 of a screen pixel on a raster map of 2″ steps along a slit of 0.17″ pixels. glue draws
    the image through a buffer of 72 dots per inch, so at 1:1 it skips data pixels, 28 in 100 on a figure of 100 dots
    per inch (``wp0-perf-core-draw``). A plain tool, as 'Hide axes' is, which leaves the mouse mode on.
    """

    icon = "glue_zoom_to_rect"
    tool_id = "solar:zoom_1_1"
    action_text = "Zoom 1:1"
    tool_tip = "Zoom about the view centre to one data pixel per screen pixel"

    def activate(self):
        state, box = self.viewer.state, self.viewer.axes.bbox  # in device pixels
        if None not in (state.x_min, state.x_max, state.y_min, state.y_max):
            # under 'Square Pixels' glue fits y to x by this ratio, which 'Physical aspect' scales
            height = box.width * state._axes_aspect_ratio if state.aspect == "equal" else box.height
            x, y = (state.x_min + state.x_max) / 2, (state.y_min + state.y_max) / 2
            with delay_callback(state, "x_min", "x_max", "y_min", "y_max"):
                state.x_min, state.x_max = x - box.width / 2, x + box.width / 2
                state.y_min, state.y_max = y - height / 2, y + height / 2
        _keep_mouse_mode(self.viewer)


# A colour bar's gap from the Image viewer's axes and width, and the room it takes with its ticks, in inches
_BAR = (0.1, 0.15)
_BAR_ROOM = 0.9


class _ColourBarAxes(Axes):
    """
    The axes of a colour bar, which take the colours of the viewer's reference data from glue's own image as they draw:
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
        # glue's limits, contrast and bias, stretch and colormap, or colour, on the values from one limit to the other
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
class ColourBarTool(Tool):
    """
    Show or hide a colour bar right of the Image viewer's image: the colours of its reference data from one colour
    limit to the other, with value ticks.

    The bar takes glue's own colouring of the reference data's layer as it draws (`_ColourBarAxes`), so it follows
    the limits, per frame too, the stretch, contrast and bias, the colormap, or the colour in 'One color per layer'
    mode, and the slices; it is part of the figure, so saved plots show it. Its room comes from the axes, as from a
    resize, so 'Square Pixels' and 'Physical aspect' keep their proportions. A plain tool, as 'Hide axes' is, which
    leaves the mouse mode on.
    """

    icon = "glue_yrange_select"
    tool_id = "solar:colour_bar"
    action_text = "Colour bar"
    tool_tip = "Show or hide a colour bar of the displayed data's colours"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.bar = None  # made at the first press

    @property
    def checked(self):
        """Whether the colour bar shows, as the View menu entry's check mark says."""
        return self.bar is not None and self.bar.get_visible()

    def activate(self):
        axes = self.viewer.axes
        if self.bar is None:
            right = axes.figure.dpi_scale_trans + ScaledTranslation(1, 0, axes.transAxes)  # inches right of the axes
            gap, width = _BAR
            where = blended_transform_factory(right, axes.transAxes)
            self.bar = axes.inset_axes([gap, 0, width, 1], transform=where, axes_class=_ColourBarAxes, visible=False)
            self.bar.viewer = self.viewer
            self.bar.imshow(np.zeros((1, 1, 4)), origin="lower", aspect="auto", interpolation="nearest")
            self.bar.set_xticks([])
            self.bar.yaxis.tick_right()
            update_appearance_from_settings(self.bar)  # glue's colours for its axes
        shown = not self.bar.get_visible()
        self.bar.set_visible(shown)
        left, right, bottom, top = axes.resizer.margins  # glue's, in inches
        axes.resizer.margins = [left, right + (_BAR_ROOM if shown else -_BAR_ROOM), bottom, top]
        canvas = self.viewer.figure.canvas  # glue places the axes and fits their aspect at a resize
        canvas.callbacks.process("resize_event", ResizeEvent("resize_event", canvas))
        _keep_mouse_mode(self.viewer)


def sky_length(viewer, x, y):
    """
    The length of the line through the points ``x``, ``y`` (two or more) of the Image viewer's displayed axes, as
    ``(pixels, arcsec, km)``: in data pixels; on the sky, the great-circle angles between the world coordinates at the
    ends of its segments, added up; and on the Sun, that angle in radians times the reference data's ``DSUN_OBS``, the
    observer's distance from the Sun's centre: a length in the plane of the sky through the Sun's centre, with no
    correction for foreshortening. The arcsec are None off the sky (`_sky_coords`) or past the outer steps of a -TAB
    raster, which has no coordinates there; the km also without ``DSUN_OBS``.
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
    Measure a line dragged on the Image viewer's image: its length in data pixels, on the sky in arcsec and on the Sun
    in km (`sky_length`), in the status bar beside the mouse-over readout, which each mouse move replaces. Where the
    displayed axes are not a longitude and a latitude alone, such as a spectrogram, a slit-jaw image's x against time
    or a sit-and-stare raster's exposures against its slit, in pixels only. The line and its length stay until the
    next drag, or until other axes or reference data are shown, which they would not describe; another mouse mode
    hides them while it is on.
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
    glue-core's `~glue.plugins.tools.path_slicer.path_sliced_data.PathSlicedData`, a dataset's values along a path, for
    IRIS data: NaN where the path leaves the data, and ``Time`` as times, NaT there, where glue-core 1.27.0 gives 0 and
    casts times to float; its own world coordinates, which glue-core asks the parent for; a scalar for one pixel. The
    positions given are the path's samples, which `PathTool` places in each dataset's own pixels, not vertices to
    sample. A slit-jaw image's longitude and latitude depend on its frame, so its diagram, with more world axes than
    pixel axes, on which glue-core's coordinates fail, has pixel coordinates only; a raster's keeps its wavelength, and
    a stack's its scan too, from scan 0's WCS, as its longitude and latitude depend on its scan.

    ``sampling`` is one of `SAMPLINGS`: 'truncate', glue-core's, the pixel whose index each position rounds down to;
    'nearest', the nearest pixel, halfway up, as `scipy.ndimage.map_coordinates` with ``order=0``, NaN beyond half a
    pixel off the data; 'linear', bilinear between the four pixels around each sample, as ``order=1`` with
    ``mode="constant"``, NaN where any is NaN or off the data, with times and categories the nearest pixel's.

    A session keeps the path, its parent and its sampling, where glue-core 1.27.0 cannot save a diagram, and the
    restored diagram reads its values from the parent again.
    """

    SAMPLINGS = ("truncate", "nearest", "linear")

    def __init__(self, *args, sampling="truncate", **kwargs):
        if sampling not in self.SAMPLINGS:
            raise ValueError(f"sampling must be one of {self.SAMPLINGS}, not {sampling!r}")
        self.sampling = sampling
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
            "sampling": self.sampling,
            "pixel_component_ids": [context.id(cid) for cid in self.pixel_component_ids],
            "world_component_ids": [context.id(cid) for cid in self.world_component_ids],
            "subsets": [context.id(subset) for subset in self.subsets],
        }

    @classmethod
    def __setgluestate__(cls, rec, context):
        data = context.object(rec["original_data"])
        (cid_x, cid_y), x, y = map(context.object, rec["cids"]), context.object(rec["x"]), context.object(rec["y"])
        path = cls(data, cid_x, x, cid_y, y, label=rec["label"], sampling=rec["sampling"])
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
        # glue-core's truncation, or the nearest pixel, floor(position + 0.5), as scipy's map_coordinates rounds
        if self.sampling == "truncate":
            return super()._get_pix_coords(view)
        pixel = [np.floor(position + 0.5) for position in self._pixels(self._cells(view), self.x, self.y)]
        keep = np.all([(p >= 0) & (p < n) for p, n in zip(pixel, self.original_data.shape, strict=True)], axis=0)
        return [p[keep].astype(int) for p in pixel], keep, keep.shape

    def _linear(self, cid, view):
        """
        ``cid`` bilinear between the four pixels around each path position ``view`` selects: the diagram within the
        cells' bounding box, as glue's fixed-resolution buffer reads dask data, from one read of the distinct pixels
        around its samples, about twice the pixels truncation reads.
        """
        cells = self._cells(view)
        if not cells[0].size:
            return np.full(cells[0].shape, np.nan)
        box = [np.arange(cell.min(), cell.max() + 1) for cell in cells]
        corners, weights = [], 1
        for path, axis, high in zip((self.x, self.y), self.sliced_dims, ([0, 1, 0, 1], [0, 0, 1, 1]), strict=True):
            n, position = self.original_data.shape[axis], path[box[-1]]
            inside = (position >= 0) & (position <= n - 1)  # not NaN
            low = np.minimum(np.floor(np.where(inside, position, 0)), max(n - 2, 0))  # n - 1 is the upper pixel's
            fraction = np.where(inside, position - low, np.nan)
            corners.append(np.minimum(np.add.outer(high, low), n - 1).astype(int).ravel())
            weights = weights * np.where(np.reshape(high, (4, 1)), fraction, 1 - fraction)
        (x, y), inverse = np.unique(corners, axis=1, return_inverse=True)
        values = self.original_data.get_data(cid, view=tuple(self._pixels(np.ix_(*box[:-1], np.arange(x.size)), x, y)))
        values = np.asarray(values)
        diagram = sum(weight * values[..., index] for weight, index in zip(weights, inverse.reshape(4, -1)))
        diagram = diagram.astype(np.result_type(values.dtype, np.float32), copy=False)
        return diagram[tuple(cell - axis[0] for cell, axis in zip(cells, box, strict=True))]

    def get_data(self, cid, view=None):
        if cid in self.pixel_component_ids or cid in self.world_component_ids:
            return BaseCartesianData.get_data(self, cid, view)
        if self.sampling == "linear" and self.get_kind(cid) == "numerical":
            return self._linear(cid, view)[()]
        pixel, keep, shape = self._get_pix_coords(view=view)
        values = np.asarray(self.original_data.get_data(cid, view=tuple(pixel)))
        if values.dtype.kind == "M":
            result = np.full(shape, "NaT", values.dtype)
        else:
            result = np.full(shape, np.nan, np.result_type(values.dtype, np.float32))
        result[keep] = values
        if isinstance(view, tuple) and any(np.isscalar(index) for index in view):  # glue-core keeps their axes
            result = result.reshape(np.broadcast_to(0, self.shape)[view].shape)
        return result[()]


# glue-core 1.27.0 saves the link between two diagrams' paths as a ComponentLink through its own methods, which no
# session opens: save the diagrams it links instead
if PathRelativeLink not in GlueSerializer.dispatch:

    @saver(PathRelativeLink)
    def _save_path_link(link, context):
        return {"paths": [context.id(link._slice_from), context.id(link._slice_to)]}

    @loader(PathRelativeLink)
    def _load_path_link(rec, context):
        return PathRelativeLink(*map(context.object, rec["paths"]))


def _placed(viewer, data, x, y):
    """
    The two pixel components of ``data`` along which the path of samples ``x, y`` on the Image viewer's displayed axes
    runs, each with the path's positions along it (NaN where the path leaves ``data``), through glue's links from the
    reference data at the viewer's slices; None if glue cannot place them from the reference data. A stack's scan,
    its first axis, which `~glue_solar.sources.loaders.iris.link_hpc` makes the one nearest the time shown, is not
    along the path.
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


def _diagrams(collection, placed, sampling, made=()):
    """
    glue-core's create_trace, of samples: a `PathData` diagram, sampled with ``sampling``, of each dataset of
    ``placed`` with its two pixel components and the positions along them (`_placed`), added to ``collection`` and
    linked to its parent and sample by sample to the others. Each is numbered past its parent's diagrams in the
    collection, such as a restored session's or another viewer's, and ``made``, kept or deleted.
    """
    trace = []
    for data, ((cid_x, x), (cid_y, y)) in placed:
        count = sum(path.original_data is data for path in {*made, *(d for d in collection if isinstance(d, PathData))})
        label = f"{data.label} [slice {count + 1}{'' if sampling == 'truncate' else ', ' + sampling}]"
        path = PathData(data, cid_x, x, cid_y, y, label=label, sampling=sampling)
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
    glue-core's path slicer, for 3D and 4D data: draw a path on the Image viewer's image and press Enter for a dataset
    of the values along it, of each dataset shown, the reference data's opened in a new Image viewer and the others' in
    the data collection, as glue cannot show them on its axes; a slit-jaw image gives frames against the path, a raster
    window wavelength against the path, a stack scans and wavelength against the path. The path is sampled once a pixel
    of the reference data and placed in each other dataset through glue's links, such as
    `~glue_solar.sources.loaders.iris.link_hpc`'s, at the frame shown, so a time-synced viewer samples them at the time
    master's exposure; a dataset glue cannot place from the reference data, as a slit-jaw image on a raster's axes, has
    no diagram. Each Enter makes a new set of diagrams, in a new viewer, sampled as `PathData` is with ``sampling``,
    which the "Path sampling" submenu of `ModesTool` sets, as does a path opened from ECSV with its own sampling.

    The path of each diagram of the image in the data collection, on the axes shown, is drawn as glue-core draws its
    paths, the latest brightest: in every Image viewer of it, whichever made it, Enter, "Open path from ECSV…", "Path on
    other data…" or a restored session.
    """

    tool_id = "solar:path"
    action_text = "Path diagram"
    tool_tip = "Draw a path, then press Enter for the data along it (Esc clears the path)"
    shortcut = "L"
    slice_viewer_cls = ImageViewer
    sampling = "truncate"

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
        self._extract(x, y, self.sampling)

    def _extract(self, x, y, sampling):
        # PathData of the samples x, y placed in each dataset. Every Enter makes a new set: glue-qt 0.4.2 has no menu
        # to pick a path to update instead (glue-viz/glue-qt#66, draft, adds one)
        state = self.viewer.state
        datasets = [layer.layer for layer in state.layers if isinstance(layer.layer, Data)]
        # the reference data's first, which the crosshair follows
        datasets.sort(key=lambda data: data is not state.reference_data)
        placed = [(data, at) for data in datasets if (at := _placed(self.viewer, data, x, y)) is not None]
        made = [path for old in self._traces for path in old]
        trace = _diagrams(self.viewer.session.data_collection, placed, sampling, made)
        trace[0].parent_viewer = self.viewer
        self._traces.append(trace)
        # the reference data's only: glue cannot show the others on its axes, such as a raster window's wavelength
        # on a slit-jaw image's frames, and lists them disabled
        self._slice_viewer = open_slice_viewer_for(self.viewer, self.slice_viewer_cls, trace[:1])
        self._slice_viewers.append(self._slice_viewer)


@viewer_tool
class PathCrosshairTool(BasePathSlicerCrosshairMode):
    """
    glue-core's crosshair of a `PathTool` diagram: drag along the diagram to mark the point on the path in the viewer
    it was drawn in, which moves that viewer's slider of the axis the diagram's y axis shows, and only that one.
    """

    tool_id = "solar:path_crosshair"

    def _on_move(self, mode):
        x, y, path = self._event_xdata, self._event_ydata, self.data
        if not self._active or path is None or x is None or y is None:
            return
        index = round(np.clip(x, 0, path.shape[-1] - 1))
        self._crosshair.set_data([path.x[index]], [path.y[index]])
        source = path.parent_viewer.state
        kept = [axis for axis in range(path.original_data.ndim) if axis not in path.sliced_dims]
        if source.reference_data is path.original_data and self.viewer.state.y_att.axis < len(kept):
            axis = kept[self.viewer.state.y_att.axis]
            slices = list(source.slices)
            slices[axis] = int(np.clip(np.round(y), 0, path.original_data.shape[axis] - 1))
            source.slices = tuple(slices)
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
    The samples of the `PathData` diagram ``path`` as a table: ``x`` and ``y``, the parent's pixels along its axes
    ``meta["axes"]``, and, on the parent's coordinates at the first index of its other axes, such as a slit-jaw
    image's first frame, ``lon`` and ``lat`` and the ``distance`` along the path from its first sample, in arcsec, as
    `sky_length` measures it, and with ``DSUN_OBS`` in km, ``distance_km``. Its meta also give the parent's label and
    the ``sampling``, with which `PathTool` makes the diagram again.
    """
    data = path.original_data
    meta = {"data": data.label, "axes": list(path.sliced_dims), "sampling": path.sampling}
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
    make its diagrams as Enter does, sampled as before.
    """
    start = os.path.expanduser(rcParams["savefig.directory"])
    name, _ = QtWidgets.QFileDialog.getOpenFileName(tool.viewer, "Open path from ECSV", start, "ECSV table (*.ecsv)")
    if not name:
        return
    table, state = Table.read(name, format="ascii.ecsv"), tool.viewer.state
    along = dict(zip(table.meta["axes"], (table["x"], table["y"]), strict=True))
    if {state.x_att.axis, state.y_att.axis} != set(along):
        raise ValueError(f"The path is on pixel axes {table.meta['axes']} of {table.meta['data']}: show those.")
    tool._extract(np.asarray(along[state.x_att.axis]), np.asarray(along[state.y_att.axis]), table.meta["sampling"])


_SKY = ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat")


def _on_sky(data, lon, lat, when):
    """
    The two pixel components of ``data`` along which its helioprojective longitude and latitude vary and no other world
    coordinate does, each with the positions along it of the longitudes and latitudes ``lon, lat`` (Quantity), on its
    coordinates at its first pixel along its other axes but the frame or scan with the ``Time`` nearest ``when``, where
    its pointing changes; None if there are not two, as on a raster's wavelengths against its slit.
    """
    types = list(getattr(data.coords, "world_axis_physical_types", None) or ())
    if not set(_SKY) <= set(types):
        return None
    wcs, sky = data.coords, [types.index(kind) for kind in _SKY]
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
    Make a diagram of the path `_reused` gives on each 3D or 4D dataset ticked of those it can be placed in (`_on_sky`)
    by its longitudes and latitudes as `_save_path` saves them, at the parent's first index of its other axes, and the
    ``Time`` of its first sample on the data there: each opened in a new Image viewer, sampled as the path is and linked
    to it sample by sample.
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
    for diagram in _diagrams(collection, ticked, path.sampling):
        link_path_sliced_pair_paths(collection, diagram, path)
        open_slice_viewer_for(viewer, ImageViewer, [diagram])


def _track(viewer, x, y):
    """
    The motion along the path of a feature whose track passes through the points ``x, y`` (two or more) of the Image
    viewer's `PathData` diagram, shown with the path along x and one ``Time`` on each row, as a slit-jaw image's frames
    against its path: the times of the earliest and latest points, their distances along the path in km, and the speed
    along the path in km/s at the earliest point and the acceleration in m/s², of the least-squares straight line
    through the distances against time of points at two times, with NaN acceleration, or parabola through points at
    three or more. A distance is that from the path's first sample, measured as `sky_length` measures, on the data's
    coordinates at the point's row. None unless each point is on a row of one time with sky coordinates and the data
    have ``DSUN_OBS``, at two times or more.
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
_SLOPES = ("t0 (UTC)", "t1 (UTC)", "d0 (km)", "d1 (km)", "speed (km/s)", "acceleration (m/s²)")


@viewer_tool
class SlopeTool(PathMode):
    """
    glue's path drawing mode on a `PathTool` diagram: click points along a feature's track on a distance-time diagram,
    such as a slit-jaw image's frames against its path, or drag along it, and press Enter for its motion (`_track`) as
    a row of the diagram's table, the dataset '<diagram> slopes', which the first row adds to the data collection and
    opens in a Table viewer; Esc clears the points. The status bar gives the speed and acceleration of the points so
    far, and of the last row.
    """

    icon = "pencil"
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
        text = f"Speed {speed:,.2f} km/s"
        self.label.setText(text if np.isnan(acceleration) else f"{text} · acceleration {acceleration:,.1f} m/s²")
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
    Move the point with the mouse, as CRISPEX's cursor does, and lock it with a click.

    While the edit subset is an unlocked point, or empty, the mouse moving over the image moves it to the pixel under
    the mouse, as a Pixel click there would, with no Undo step and at most once in 50 ms, to the latest position: a
    quicklook's panels and spectrum follow, and on a quicklook's slit-jaw image the point moves to the raster pixel
    there (`~glue_solar.quicklook.sji_to_raster`). A left click moves it there and locks it, in one Undo step, which
    unlocks it too; a right click, or Esc once a click has given the image the keyboard, unlocks it. A locked point
    stays as the mouse moves over any viewer, and stays locked as sliders or Pixel clicks move it or Clear point
    empties it. The mouse alone never moves a region being edited; a click replaces it, as a Pixel click does.
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
    """An entry of the ``solar:coordinate`` menu; the viewer's mouse mode, such as Pixel, stays on."""

    def __init__(self, viewer, menu):
        super().__init__(viewer)
        self.menu = menu

    def activate(self):
        self.run(self.menu.coordinator)
        _keep_mouse_mode(self.viewer)


class _TimeMasterEntry(_CoordinateEntry):
    tool_id = "solar:time_master"
    action_text = "Time master"
    tool_tip = "Make the displayed dataset the time master of its observation"

    def run(self, coordinator):
        coordinator.set_master(self.viewer.state.reference_data)


class _OverlaysEntry(_CoordinateEntry):
    """
    Show or hide the raster overlays of the viewer's observation on all its viewers: on each slit-jaw image the slit of
    each raster step or exposure, a stack's at the scan its panels show, placed through the frame nearest that step's
    time, and on each map of the raster, its steps or exposures against slit, a dashed line at the one nearest the time
    master's time, hidden beyond half their cadence. Plain matplotlib lines: 'Save plot' shows them, and sessions and
    Python scripts leave them out.
    """

    tool_id = "solar:raster_overlays"
    action_text = "Raster overlays"
    tool_tip = "Show or hide each raster step's slit on the slit-jaw images and the step at the master's time on maps"

    def run(self, coordinator):
        coordinator.toggle_overlays(observation_key(self.viewer.state.reference_data))


class _ClearPointEntry(_CoordinateEntry):
    tool_id = "solar:clear_point"
    action_text = "Clear point"
    tool_tip = "Clear the selected point"

    def run(self, coordinator):
        coordinator.clear_point()


class _LightCurveEntry(_CoordinateEntry):
    tool_id = "solar:light_curve"
    action_text = "Light curve at the point"
    tool_tip = "Open the mean over the wavelength or band shown here at the point, against exposure or scan"

    @messagebox_on_error("Could not open the light curve")
    def run(self, coordinator):
        _light_curve(self.viewer)


class _PointCurvesEntry(_CoordinateEntry):
    tool_id = "solar:point_curves"
    action_text = "Light curves at this point (windows, SJI)"
    tool_tip = "Plot each raster window and slit-jaw image at the point against time, as new datasets that follow it"

    @messagebox_on_error("Could not add the light curves")
    def run(self, coordinator):
        _point_curves(self.viewer)


def _first_slider(viewer):
    """
    glue-qt's slice slider of the Image viewer's first array axis (an IRIS dataset's frames, exposures, steps or
    scans), or None where it has none, as while the viewer shows that axis.
    """
    sliders = viewer.options_widget().slice_helper._sliders
    return sliders[0] if sliders else None


class _GoToUTCEntry(_CoordinateEntry):
    """
    Move the time master of the viewer's observation, typed in any of its viewers, to its frame, exposure, step or
    scan nearest a typed UTC time, the earlier of two as near: the others follow it, as after a move of its slider. A
    stack's scans are timed at the point's step. A viewer of an observation without a time master moves its own
    frame, exposure, step or scan slider instead. The dialog opens on the time master's time, or the viewer's own; a
    time more than half the master's cadence from its nearest moves nothing (D7), and glue says why, as for a viewer
    with neither a time master nor such a slider.
    """

    tool_id = "solar:go_to_utc"
    action_text = "Go to UTC…"
    tool_tip = "Move the time master to its frame, exposure, step or scan nearest a UTC time"

    @messagebox_on_error("Could not go to UTC")
    def run(self, coordinator):
        viewer = self.viewer
        state = viewer.state
        data = state.reference_data
        master = coordinator._master(observation_key(data)) if _timed(data) else None
        if master is None and (_first_slider(viewer) is None or not _timed(data)):
            raise ValueError("The viewer has no frame, exposure, step or scan slider of IRIS data.")
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
    Make the playback of ``slider``, a glue-qt slice slider, go round ``lo`` to ``hi`` only, both included, either way,
    ``every`` indices a step: past an end it starts again at ``lo`` forwards and ``hi`` backwards, or with ``bounce``
    turns back at the last index it reaches; from outside them it starts at ``lo`` forwards and ``hi`` backwards.
    glue-qt's play timer steps through the slider's ``_browse_slice``, which this replaces; its buttons keep the method
    they were connected to.
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
    The first and last index of ``slider``, a glue-qt slice slider, typed in a dialog that opens on its loop (Loop…)
    or else its whole range, or None if the dialog is cancelled; ``±N`` (or ``+-N``) types the N indices either side
    of the current one, cut to 0 and the last. ``rows``, each the arguments of a ``QFormLayout.addRow``, go below; read
    their widgets as soon as this returns.
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
# The lengths a scale bar takes, in arcsec
_SCALE_BARS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)


def _place_scale_bar(viewer, line, label):
    """
    Put ``line`` and ``label``, in data x and axes y, at the Image viewer's lower right, as a scale bar ending at 95 %
    of the axes' width: the largest of `_SCALE_BARS` the right quarter of the view spans, at the angle an x pixel
    spans on the sky (`sky_length`) at the slice shown, on average across the image through the view centre, as
    `_arcsec_ratio` takes it, so a rolled or stretched image gets it too; hidden off the sky.
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
    Save the Image viewer's figure at each index of one slider, from a first to a last, as PNG files or a movie.

    An entry of glue's save menu. Each PNG frame is what 'Save plot to file' writes at that index, named after the file
    chosen with the index added (``sji_0007.png`` for ``sji.png``); a movie is an MP4 through matplotlib's
    ``FFMpegWriter``, offered where ffmpeg is installed, or a GIF through its ``PillowWriter``, at 10 frames per
    second. Of several sliders one is picked, the first (an IRIS dataset's frames, exposures, steps or scans) offered
    first, and the indices are typed as for Loop…, whose range the dialog opens on. Its playback, and the time
    master's, stops; the slider moves as in playback, on the GUI thread, and each frame is saved once Qt has run the
    time sync, so the other viewers follow and the overlays are drawn; per-frame limits are off during the run, so
    every frame has the same colour limits. Ticked in the range dialog, 'UTC time on each frame' draws the frame's
    time (`_frame_time`, to 0.01 s) at the image's lower left during the run only, 'Frame numbers' the slider's index
    and last index at its upper left (``frame 7/399``), and 'Scale bar' a bar of a round length in arcsec at its lower
    right (`_place_scale_bar`), or, where the displayed axes are not a longitude and a latitude, a message in the
    application's status bar. The file dialog offers a name from the reference data's label and the indices. Cancel
    keeps the frames saved so far, a movie of them too, and the viewer returns to its slice and limits.
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
        progress = QtWidgets.QProgressDialog("Saving frames…", "Cancel", 0, len(indices), viewer)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()  # at once, keeping input from the viewer's window while the events below run
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
            # unsnapped, its ends where measured, not on pixel centres
            line = Line2D([], [], lw=3, solid_capstyle="butt", snap=False, transform=where, **edged)
            bar = viewer.axes.add_line(line), viewer.axes.text(0, 0, "", ha="center", transform=where, **style)
        try:
            # FFMpegWriter evens out an odd frame size through the canvas' manager, which would resize the canvas, and
            # glue would zoom to it: without one only the figure changes, until the end
            canvas.manager = None
            for layer in per_frame:
                layer.stretch_global = True
            saving = nullcontext() if movie is None else movie(fps=_MOVIE_FPS).saving(figure, stem + suffix, None)
            with saving as writer:
                for count, index in enumerate(indices, 1):
                    state.slices = tuple(index if i == axis else s for i, s in enumerate(state.slices))
                    QtWidgets.QApplication.processEvents()  # the time sync, its overlays and Cancel, as in playback
                    if stamp is not None:
                        stamp.set_text(_frame_time(data, _shown_slice(state), 2))
                    if number is not None:
                        number.set_text(f"frame {index}/{top}")
                    if bar is not None:
                        _place_scale_bar(viewer, *bar)
                    if writer is None:
                        figure.savefig(f"{stem}_{index:04d}.png")  # as 'Save plot to file' does
                    else:
                        writer.grab_frame()
                    progress.setValue(count)
                    if progress.wasCanceled():
                        break
        finally:
            progress.deleteLater()
            for artist in [stamp, number, *(bar or ())]:
                if artist is not None:
                    artist.remove()
            state.slices = slices
            for layer in per_frame:
                layer.stretch_global = False
            canvas.manager = manager
            figure.set_size_inches(size, forward=False)
            canvas.draw_idle()


def _profile_table(viewer):
    """
    The profiles of the Profile viewer's visible layers as one astropy table, and the labels of the visible layers
    without one (empty, disabled or still computing), which it leaves out. The ``i``-th layer kept, from 1, gives
    ``x<i>`` and ``y<i>`` as glue draws them, in the viewer's x and y units (or normalized), described by the x axis's
    name and the layer's label, ``y<i>`` with its attribute and, for a Pixel subset, the pixel of each axis it fixes and
    the sky position there at the first sample (``lon`` and ``lat``, in arcsec); a shorter profile is padded with
    masked values. Where x is the axis along which the data step through time (`_time_axis`: a sit-and-stare raster's
    exposures, a stack's scans, a slit-jaw image's frames), ``time<i>`` gives each sample's ``Time``, at the pixel or
    slice of a Pixel subset or light curve, else at the first index of the other axes. Its meta give the function.
    """
    state = viewer.state
    tables, skipped = [], []
    for artist in viewer.layers:
        layer = artist.state
        if not layer.visible:
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
        y_unit = None if state.normalize or not y_unit else state.y_display_unit or y_unit
        y = layer.normalize_values(y) if state.normalize else y
        meta = {"attribute": layer.attribute.label}
        subset = getattr(layer.layer, "subset_state", None)
        fixed = [None] * data.ndim
        if isinstance(subset, PixelSubsetState):
            fixed = subset._to_linked_pixel_coords(data)
            meta["pixel"] = {c.label: p for c, p in zip(data.pixel_component_ids, fixed, strict=True) if p is not None}
            sky = None if data.coords is None else _sky(data.coords, [p or 0 for p in fixed])
            if sky is not None:
                meta["lon"] = u.Quantity(sky.spherical.lon.wrap_at(180 * u.deg), u.arcsec)
                meta["lat"] = u.Quantity(sky.spherical.lat, u.arcsec)
        elif isinstance(subset, SliceSubsetState) and subset.reference_data is data:  # a light curve
            fixed = [s.start for s in subset.slices]
        i = len(tables) + 1
        columns = [
            Column(x, f"x{i}", unit=x_unit, description=state.x_att.label),
            Column(y, f"y{i}", unit=y_unit, description=layer.layer.label, meta=meta),
        ]
        axis = is_convertible_to_single_pixel_cid(data, state.x_att_pixel).axis
        if _time_component(data) is not None and _time_axis(data) == axis:
            view = tuple(slice(None) if a == axis else p or 0 for a, p in enumerate(fixed))
            columns.append(Column(data[_time_component(data), view], f"time{i}"))
        tables.append(Table(columns))
    if not tables:
        raise ValueError("No visible layer has a profile.")
    table = hstack(tables, join_type="outer")
    table.meta["function"] = state.function
    return table, skipped


@viewer_tool
class SaveProfileTool(Tool):
    """
    Save the Profile viewer's visible profiles, as glue draws them, to one ECSV table (`_profile_table`), its ``Time``
    columns as `~astropy.time.Time` and the reference data's OBSID and STARTOBS in its meta. An entry of glue's save
    menu; the application's status bar names the layers left out.
    """

    icon = "glue_filesave"
    tool_id = "solar:save_profile"
    action_text = "Save profiles as ECSV…"
    tool_tip = "Save the visible profiles, as drawn, to an ECSV table"

    @messagebox_on_error("Could not save the profiles")
    def activate(self):
        viewer = self.viewer
        table, skipped = _profile_table(viewer)
        start = os.path.expanduser(rcParams["savefig.directory"])
        name, _ = QtWidgets.QFileDialog.getSaveFileName(viewer, "Save profiles as ECSV", start, "ECSV table (*.ecsv)")
        if not name:
            return
        _write_ecsv(name, table, viewer.state.reference_data.meta)
        if skipped:
            # the application's, which glue-qt's toolbar does not clear after the entry, as it does the viewer's
            viewer.session.application.statusBar().showMessage(f"Left out, without a profile: {', '.join(skipped)}")


def _position(viewer):
    """The Image viewer's position, D41's A or B: its reference data and slider position."""
    return viewer.state.reference_data, tuple(viewer.state.slices)


def _layers_of(state, data):
    """The viewer's layers of ``data`` and of its subsets."""
    return [layer for layer in state.layers if layer.layer.data is data]


def _show_position(viewer, coordinator, data, slices):
    """
    Show ``data`` at ``slices`` in the Image viewer as a blink flip: the shown axes, by pixel axis, the zoom, the point
    and the time sync stay. Another dataset that follows the time master shows the frame, exposure or scan the time
    sync gives it now instead of its own, a collapse staying, so two slit-jaw channels blink at one time in playback.
    For another dataset glue resets the axes, slices and limits, so they are set again after it, x before y; the
    dataset left is hidden, since glue would retry its disabled layer at every draw through the helioprojective link,
    about a second on a full raster.
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
    tab, pressed on any of its viewers, that of each of its panels; nothing else moves.
    """
    viewer, sync, _ = _pressed(session)
    app = session.application
    group = getattr(app, "_solar_points", {}).get(app.current_tab)
    for each in dict.fromkeys([viewer, *sync._owners.get(group, ())]):
        data = each.state.reference_data
        if isinstance(each, ImageViewer) and data is not None:
            sliders = each.options_widget().slice_helper._sliders
            for axis in _spectral_axes(data):
                _step(sliders[axis] if axis < len(sliders) else None, delta)


def _play_key(session):
    """
    Space: play the time forwards, as glue-qt's play button does, or pause it. The time is the first slider of a viewer
    of the time master of the active viewer's observation, one with a loop (Loop…), which it goes round, before the
    active viewer's own, or without a time master, the active Image viewer's own. Space pauses any of these playing,
    the active viewer's own too.
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


@viewer_tool
class CoordinateTool(SimpleToolMenu):
    """
    Coordinate the Image viewer with the others of its IRIS observation.

    The tool registers its viewer with the data collection's
    `~glue_solar.quicklook.Coordinator`, which keeps the viewers on the point selected with the
    Pixel tool, and unregisters it when the viewer closes. Its menu makes the displayed dataset the
    time master of its observation, clears the point, moves the time master to a typed UTC time, or
    makes the frame, exposure, step or scan slider's playback loop over a range, or shows the raster
    overlays, or opens the light curve at the point, or plots the light curves of every window and
    slit-jaw image at the point, or blinks the viewer between its position and a stored partner. On a
    slit-jaw image it draws the displayed frame's slit, and the point of a raster of the same
    observation placed with that frame's coordinates while it is on the image.
    """

    icon = "glue_link"
    tool_id = "solar:coordinate"
    # no action_text, which glue-qt would show beside the icon, so that the toolbar fits a viewer 700 px wide
    tool_tip = "Coordinate this viewer with the others of its IRIS observation"

    def __init__(self, viewer, subtools=None):
        entries = (
            _TimeMasterEntry,
            _ClearPointEntry,
            _GoToUTCEntry,
            _LoopEntry,
            _OverlaysEntry,
            _LightCurveEntry,
            _PointCurvesEntry,
            _PartnerEntry,
            _BlinkEntry,
        )
        super().__init__(viewer, subtools=subtools or [entry(viewer, self) for entry in entries])
        self.coordinator = coordinator(viewer._data)
        self.coordinator.register(viewer)
        viewer.destroyed.connect(self._forget)
        self.partner = None  # the position the viewer does not show, which the blink shows next (D41)
        self._blink = QtCore.QTimer(viewer)
        self._blink.setInterval(500)
        self._blink.timeout.connect(self._flip)
        viewer.toolbar_added.connect(self._add_blink_menu)
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

    def _add_blink_menu(self):
        """
        Make "Blink" a checkable entry and add the "Blink interval" submenu, neither of which glue-qt 0.4.2's tool
        menus can hold, once glue-qt has built the menu, as its own Profile viewer tools edit theirs.
        """
        button = self.toolbar.widgetForAction(self.toolbar.actions[self.tool_id])
        button.setToolTip(self.tool_tip)  # glue-qt 0.4.2 sets it on the button's action, which shows none
        menu = button.menu()
        self._action = next(action for action in menu.actions() if action.text() == _BlinkEntry.action_text)
        self._action.setCheckable(True)
        intervals = menu.addMenu("Blink interval")
        group = QtWidgets.QActionGroup(intervals)
        for seconds in (0.25, 0.5, 1, 2):
            action = group.addAction(f"{seconds:g} s")
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


class _ToolMenu(SimpleToolMenu):
    """
    A toolbar menu of glue-solar tools, glue's own kind of menu: the viewer's ``subtools`` name its tools, which
    glue-qt 0.4.2 makes its entries. Once glue-qt has built it, each tool is also in the toolbar's ``tools`` and
    ``actions`` with its entry, as a button's would be, so glue-qt switches a mouse mode of the menu on and off and
    scripts find a tool by its id as before. An entry shows only while its tool is ``enabled``, which glue-qt does for
    buttons only (glue-viz/glue-qt#72, draft, adds it), has a check mark for a tool with a ``checked`` state, and takes
    its tool's key while the toolbar has the keyboard, as a button does.
    """

    def __init__(self, viewer, subtools=None):
        super().__init__(viewer, subtools=subtools)
        viewer.toolbar_added.connect(self._add_entries)

    def _add_entries(self):
        toolbar = self.viewer.toolbar
        button = toolbar.widgetForAction(toolbar.actions[self.tool_id])
        button.setToolTip(self.tool_tip)  # glue-qt 0.4.2 sets it on the button's action, which shows none
        menu = button.menu()
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
            if hasattr(tool, "checked"):
                self.viewer.toolbar.actions[tool.tool_id].setChecked(tool.checked)


@viewer_tool
class ModesTool(_ToolMenu):
    """
    The Image viewer's menu of glue-solar's mouse modes: Measure, Path diagram, its crosshair and Slope; "Save path as
    ECSV…" on a diagram (`_save_path`), "Open path from ECSV…" (`_open_path`) and "Path on other data…" on a diagram
    or an image with a path drawn (`_reuse_path`); and the "Path sampling" submenu, which sets `PathTool`'s
    ``sampling`` for the next Enter.
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
        for text, run, shown in (
            ("Save path as ECSV…", lambda: _save_path(self.viewer), toolbar.tools[SlopeTool.tool_id]),
            ("Open path from ECSV…", lambda: _open_path(path), path),
        ):
            action = modes.addAction(text)
            action.triggered.connect(run)
            add_callback(shown, "enabled", action.setVisible)
            action.setVisible(shown.enabled)
        # on a diagram, or an image with a path drawn
        reuse = modes.addAction("Path on other data…")
        reuse.triggered.connect(lambda: _reuse_path(self.viewer))

        def offer():
            reuse.setVisible(_reused(self.viewer) is not None)

        modes.aboutToShow.connect(offer)
        offer()
        # a submenu, which glue-qt 0.4.2's tool menus cannot hold, as the Coordinate menu's "Blink interval"
        menu = modes.addMenu("Path sampling")
        group = QtWidgets.QActionGroup(menu)
        for sampling in PathData.SAMPLINGS:
            action = group.addAction(sampling.capitalize())
            action.setCheckable(True)
            action.setChecked(sampling == path.sampling)
            action.setData(sampling)
            menu.addAction(action)
        # not through glue-qt's toolbar, so the mouse mode stays
        group.triggered.connect(lambda action: setattr(path, "sampling", action.data()))
        add_callback(path, "enabled", menu.menuAction().setVisible)
        menu.menuAction().setVisible(path.enabled)


@viewer_tool
class ViewTool(_ToolMenu):
    """
    The Image viewer's View menu: glue-solar's display tools, which leave the mouse mode on, each checked while on.
    """

    icon = "glue_settings"
    tool_id = "solar:view"
    tool_tip = "View: frame time, axes, colour limits, wavelength band, aspect, zoom, colour bar and cursor readout"
