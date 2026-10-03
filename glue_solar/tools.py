"""
Toolbar tools for glue's viewers.
"""

from functools import partial

import numpy as np
from echo import delay_callback
from glue.config import settings, viewer_tool
from glue.core.command import ApplySubsetState
from glue.core.component import DateTimeComponent
from glue.core.edit_subset_mode import ReplaceMode
from glue.core.hub import HubListener
from glue.core.message import SettingsChangeMessage
from glue.core.subset import SubsetState
from glue.viewers.common.tool import SimpleToolMenu, Tool
from glue.viewers.image.pixel_selection_mode import PixelSelectionTool
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.utils.decorators import messagebox_on_error
from glue_qt.viewers.image import ImageViewer
from matplotlib.backend_bases import MouseButton
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from qtpy import QtCore, QtWidgets

import astropy.units as u
from astropy.coordinates import Angle, angular_separation

from glue_solar.quicklook import (
    _across,
    _half_cadence,
    _is_sit_and_stare,
    _place,
    _role,
    _seconds_text,
    _spectral_axes,
    _sync_text,
    _time_text,
    _timed,
    _times,
    _value_text,
    _world_text,
    coordinator,
    nearest,
    observation_key,
)

__all__ = [
    "CoordinateTool",
    "CursorReadoutTool",
    "FollowLockTool",
    "FrameTimeTool",
    "HideAxesTool",
    "PerFrameLimitsTool",
    "PhysicalAspectTool",
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
    return next((cid for cid in data.main_components if isinstance(data.get_component(cid), DateTimeComponent)), None)


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
    each tick value, and WCSAxes labels every crossing, one over another. An image of the two angles alone, such as
    a map or a slit-jaw image, keeps both. Decided on the array's edges, so zooming keeps it, with a longitude across
    0° unwrapped rather than 360° wide.
    """
    shown = [coord for coord in axes.coords if coord.coord_index is not None]  # the others are not on these axes
    angles = [coord for coord in shown if coord.coord_type in ("longitude", "latitude")]
    if len(angles) != 2 or len(shown) == 2:  # an image of the two angles alone: both change across it
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


@viewer_tool
class FrameTimeTool(Tool, HubListener):
    """
    Show the acquisition time of the displayed frame in the Image Viewer's status bar.

    The readout follows the sliders and reads the first datetime component of the reference
    data, whichever loader attached it (the IRIS loaders add ``Time``, one per SJI exposure or
    raster step); the toolbar button hides and shows it. A frame spanning several exposures,
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
    exposure in place of the slit's position along the exposures. Doppler velocities wait for a rest
    wavelength (``wp5-m1-rest-wavelength-policy``). The toolbar button hides the frame time only.
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
        cid = _time_component(data) if data is not None else None
        status = self.coordinator.time_status(self.viewer)
        unmatched = status is not None and status[0] == "no match"
        if self._grey.get_visible() != unmatched:
            self._grey.set_visible(unmatched)
            self.viewer.figure.canvas.draw_idle()
        self.label.setStyleSheet("color: gray" if unmatched else "")
        if cid is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
            self.label.setText("")
            return
        shown = (state.x_att.axis, state.y_att.axis)
        # an aggregated slider range carries its slice on the AggregateSlice object
        view = tuple(slice(None) if i in shown else getattr(s, "slice", s) for i, s in enumerate(state.slices))
        times = data[cid, view]
        times = times[~np.isnat(times)]  # NaT: a gap of data regridded on time
        if times.size == 0:  # a Collapse range narrower than one sample, or a gap
            self.label.setText("")
            return
        first, last = (np.datetime_as_string(t, unit="ms") for t in (times.min(), times.max()))
        text = f"{first} UTC" if first == last else f"{first} – {last} UTC"
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
    The toolbar button hides and shows the readout.
    """

    icon = "glue_cross"
    tool_id = "solar:cursor_readout"
    action_text = "Cursor readout"
    tool_tip = "Show or hide the position and value under the mouse (press W over the image for pixels)"

    def __init__(self, viewer):
        super().__init__(viewer)
        self.shown = True
        self._motion = viewer.axes.figure.canvas.mpl_connect("motion_notify_event", self._on_move)

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

    The button switches glue's own ``show_axes`` viewer state, which glue-qt 0.4.2 has no control for
    and sessions save; a new viewer starts from the ``SOLAR_SHOW_AXES`` glue setting. Without its axes
    WCSAxes places no ticks when the viewer draws, so slice steps and redraws are faster. The image,
    subsets, links and the readouts are unchanged; the mouse-over position stays in world coordinates.
    A plain button, since a checkable glue tool is a mouse mode, which would end Pixel; glue-qt ends the
    mouse mode before running a plain button too, so the button switches it back on, as glue-solar's
    other buttons do.
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

    The button switches glue's own ``stretch_global`` of each layer of the reference data, which glue-qt 0.4.2 has no
    control for: to per frame for every layer unless all already are. The layer's percentile, such as 99.5%, applies
    to the slice, and on lazily loaded IRIS data the limits count every value of it (`LazyData`). A layer of another
    dataset keeps its limits, and one of the previous reference data takes its whole cube's again, since glue would
    take them from its values at the reference data's slice indices: the wrong slice, or an IndexError for a cube of
    another shape. A plain button, as Hide axes is, since a checkable glue tool is a mouse mode, which would end
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

def _arcsec_ratio(viewer):
    """
    The angle a pixel spans along the viewer's y axis over the angle it spans along x, on average across the image
    through the view centre, or None unless the displayed axes show a longitude and a latitude alone, of any celestial
    frame, and neither is the exposures of a sit-and-stare raster, which the pointing and the solar rotation move by
    a fraction of a slit pixel. Averaged between the outer pixel centres, since -TAB rasters have no coordinates past
    them and their steps differ by up to 15 % from one to the next.
    """
    state = viewer.state
    data = state.reference_data
    if data is None or None in (state.x_att, state.y_att, state.x_min, state.y_min):
        return None
    if _is_sit_and_stare(data) and 0 in (state.x_att.axis, state.y_att.axis):  # an index, as its ticks show
        return None
    angles = {coord.coord_type: coord for coord in viewer.axes.coords if coord.coord_index is not None}
    if sorted(angles) != ["latitude", "longitude"]:  # also no wavelength or time beside them
        return None
    lon, lat = angles["longitude"], angles["latitude"]
    nx, ny = (data.shape[att.axis] - 1 for att in (state.x_att, state.y_att))
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

    The button switches glue's 'Square Pixels' aspect on, scaled by the angle a pixel spans along y over the angle
    along x (`_arcsec_ratio`), so that a raster map of 2″ steps along a slit of 0.17″ pixels shows each step 12 times
    as wide as a slit pixel. glue keeps these proportions as it keeps square pixels, through resizes, zooms, pans and
    slices; the ratio is taken again when the displayed axes change, as glue shows the whole image again. On axes
    other than a longitude and a latitude alone, such as a spectrogram's or a sit-and-stare raster's exposures against
    its slit, the pixels are square. Pressed again, or with 'Automatic' chosen in the viewer's options, the viewer
    returns to the aspect it had; back to 'Automatic' from the button, the image fills the axes again, keeping a
    zoom. A plain button, as 'Hide axes' is, which leaves the mouse mode on.
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
        # glue's private aspect hooks this scales; a glue without them gets a button that does nothing, not no viewer
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


def _loop(slider, lo, hi):
    """
    Make the playback of ``slider``, a glue-qt slice slider, go round ``lo`` to ``hi`` only, both included, either way;
    from outside them it starts at ``lo`` forwards and ``hi`` backwards. glue-qt's play timer steps through the
    slider's ``_browse_slice``, which this replaces; its buttons keep the method they were connected to.
    """

    def step(action, play=True):
        value = slider.value_slice_center.value() + (1 if action == "next" else -1)
        slider.value_slice_center.setValue(value if lo <= value <= hi else lo if action == "next" else hi)

    slider._browse_slice, slider._solar_loop = step, (lo, hi)


class _LoopEntry(_CoordinateEntry):
    """
    Make glue-qt's playback of the viewer's frame, exposure, step or scan slider loop over a typed range of indices,
    until glue-qt rebuilds the slider for other data or axes. The dialog opens on the current range.
    """

    tool_id = "solar:loop"
    action_text = "Loop…"
    tool_tip = "Make the frame, exposure, step or scan slider's playback loop over a range"

    @messagebox_on_error("Could not loop")
    def run(self, coordinator):
        viewer, slider = self.viewer, _first_slider(self.viewer)
        if slider is None:
            raise ValueError("The viewer has no frame, exposure, step or scan slider.")
        last = slider.value_slice_center.maximum()
        lo, hi = getattr(slider, "_solar_loop", (0, last))
        text, ok = QtWidgets.QInputDialog.getText(
            viewer, "Loop", f"First and last index (0–{last}):", text=f"{lo} {hi}"
        )
        if not ok:
            return
        try:
            lo, hi = (int(value) for value in text.replace(",", " ").split())
        except ValueError:
            lo = hi = -1
        if not 0 <= lo <= hi <= last:
            raise ValueError(f"'{text}' is not two indices from 0 to {last}, the first not after the last.")
        _loop(slider, lo, hi)


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
    overlays. On a slit-jaw image it draws the displayed frame's slit, and the point of a raster of the
    same observation placed with that frame's coordinates while it is on the image.
    """

    icon = "glue_link"
    tool_id = "solar:coordinate"
    action_text = "Coordinate"
    tool_tip = "Coordinate this viewer with the others of its IRIS observation"

    def __init__(self, viewer, subtools=None):
        entries = (_TimeMasterEntry, _ClearPointEntry, _GoToUTCEntry, _LoopEntry, _OverlaysEntry)
        super().__init__(viewer, subtools=subtools or [entry(viewer, self) for entry in entries])
        self.coordinator = coordinator(viewer._data)
        self.coordinator.register(viewer)
        viewer.destroyed.connect(self._forget)
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
        self._forget()
        for prop in _WATCHED:
            self.viewer.state.remove_callback(prop, self._draw)
        super().close()

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
