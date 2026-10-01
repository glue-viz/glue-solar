"""
Toolbar tools for glue's viewers.
"""

import numpy as np
from glue.config import settings, viewer_tool
from glue.core.component import DateTimeComponent
from glue.core.hub import HubListener
from glue.core.message import SettingsChangeMessage
from glue.viewers.common.tool import SimpleToolMenu, Tool
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from qtpy import QtCore, QtWidgets

import astropy.units as u

from glue_solar.quicklook import _is_sit_and_stare, _role, coordinator

__all__ = ["CoordinateTool", "CursorReadoutTool", "FrameTimeTool"]

_WATCHED = ("reference_data", "x_att", "y_att", "slices")
# glue sets both axis labels whenever it resets the WCSAxes, which also drops their tick settings
_LABELS = tuple(f"{axis}_{prop}" for axis in "xy" for prop in ("axislabel", "axislabel_size", "axislabel_weight"))
_LABELS += ("x_ticklabel_size", "y_ticklabel_size")
_PIXEL_COORDS = {"type": ("scalar", "scalar"), "wrap": (None, None), "unit": (u.one, u.one), "name": ("x", "y")}
# glue-qt rebuilds the slice sliders when these change
_SLIDER_REBUILDS = ("reference_data", "x_att", "y_att")
# A dragged slice slider applies its position at most this often, and on release
_DRAG_INTERVAL_MS = 100


def _throttle_slice_sliders(viewer):
    """
    Make the viewer's slice sliders follow a drag at most every 0.1 s instead of at every position.

    glue-qt applies every value a slider passes through, and each one recomputes and redraws the
    image, so on a large cube a drag queues redraws and lags behind the mouse. With tracking off a
    drag reports only its release, and a timer applies the dragged position in between. Keys,
    clicks and playback still apply at once.

    Always on, with no upstream change tracked. It finds the sliders by glue-qt's object name
    ``value_slice_center``, which the drag test pins.
    """
    for slider in viewer.options_widget().findChildren(QtWidgets.QSlider, "value_slice_center"):
        if not slider.hasTracking():
            continue  # already throttled
        slider.setTracking(False)
        timer = QtCore.QTimer(slider)
        timer.setSingleShot(True)
        timer.setInterval(_DRAG_INTERVAL_MS)
        timer.timeout.connect(lambda slider=slider: slider.setValue(slider.sliderPosition()))
        slider.sliderMoved.connect(lambda _position, timer=timer: timer.isActive() or timer.start())


def _time_component(data):
    """The first datetime component of ``data``, or None."""
    return next((cid for cid in data.main_components if isinstance(data.get_component(cid), DateTimeComponent)), None)


def _exposure_label(data):
    """
    'Exposure (acquisition order)' and, on a second line, '<first> – <last> UTC' for the exposure axis of
    a sit-and-stare raster; one line would not fit a quicklook panel.
    """
    cid = _time_component(data)
    if cid is None:
        return "Exposure (acquisition order)"
    times = data[cid, (slice(None), 0, 0)]
    first, last = (np.datetime_as_string(t, unit="s") for t in (times.min(), times.max()))
    if last[:10] == first[:10]:
        last = last[11:]  # the same day: the time only
    return f"Exposure (acquisition order)\n{first} – {last} UTC"


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

    The tool exists for every Image viewer, so it also throttles the viewer's slice sliders and labels
    a displayed sit-and-stare exposure axis 'Exposure (acquisition order)' with the UTC range of its
    exposures, in glue's own axis label, with integer exposure ticks instead of the helioprojective
    coordinates glue would show along it. glue resets both whenever it resets the axes (an axis or
    data change, or a slice the displayed coordinates depend on, such as the slit on the wavelength
    panel), and the tool applies them again; a label typed in the viewer's axes options is kept until
    then, as glue's own labels are.
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
        for prop in _LABELS:
            viewer.state.add_callback(prop, self._label_exposures)
        # glue's Preferences restyle only the WCS coordinates
        self._hub = viewer.session.hub
        self._hub.subscribe(self, SettingsChangeMessage, handler=self._label_exposures)
        self._label_exposures()

    def activate(self):
        self.label.setHidden(not self.label.isHidden())

    def close(self):
        self._forget()
        for prop in _WATCHED:
            self.viewer.state.remove_callback(prop, self._refresh)
        for prop in _SLIDER_REBUILDS:
            self.viewer.state.remove_callback(prop, self._throttle_sliders)
        for prop in _LABELS:
            self.viewer.state.remove_callback(prop, self._label_exposures)
        super().close()

    def _label_exposures(self, *_):
        """Label a displayed sit-and-stare exposure axis and give it exposure ticks (see the class)."""
        state = self.viewer.state
        data = state.reference_data
        if data is None or _role(data) != "raster" or data.ndim != 3 or not _is_sit_and_stare(data):
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
            axes = self.viewer.axes
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
        if times.size == 0:  # a Collapse range narrower than one sample
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
        if status is not None:
            kind, value = status
            if kind == "master":
                text += " · time master" + (f", step {value}" if value is not None else "")
            else:
                seconds = value / np.timedelta64(1, "s")
                text += f" · Δt {seconds:+.1f} s" if kind == "match" else f" · NO MATCH Δt = {seconds:+.1f} s"
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
    position, wavelength, ...), formatted by the viewer's WCSAxes; the value is the reference
    layer's displayed attribute at that pixel of the current slice. Pressing ``w`` over the image
    switches WCSAxes between world and pixel positions. The toolbar button hides and shows the
    readout.
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
        data = state.reference_data
        layer = next((ls for ls in state.layers if ls.layer is data and ls.visible), None)
        if layer is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
            return text
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= ix < data.shape[state.x_att.axis] and 0 <= iy < data.shape[state.y_att.axis]):
            return text
        # an aggregated slider range carries its middle slice on the AggregateSlice object
        view = tuple(
            ix if i == state.x_att.axis else iy if i == state.y_att.axis else getattr(s, "center", s)
            for i, s in enumerate(state.slices)
        )
        value = data[layer.attribute, view]
        try:
            value = f"{float(value):.6g}"
        except (TypeError, ValueError):  # datetime or string components
            value = str(value)
        # IRIS components are named after their dataset; say 'value' rather than repeat it
        name = "value" if layer.attribute.label == data.label else layer.attribute.label
        return f"{text} | {name} = {value}"


class _CoordinateEntry(Tool):
    """An entry of the ``solar:coordinate`` menu; the viewer's mouse mode, such as Pixel, stays on."""

    def __init__(self, viewer, menu):
        super().__init__(viewer)
        self.menu = menu

    def activate(self):
        # glue-qt switches the mouse mode off before running a menu entry, so switch it back on
        mode = self.menu.mode
        self.run(self.menu.coordinator)
        if mode is not None:
            self.viewer.toolbar.active_tool = mode


class _TimeMasterEntry(_CoordinateEntry):
    tool_id = "solar:time_master"
    action_text = "Time master"
    tool_tip = "Make the displayed dataset the time master of its observation"

    def run(self, coordinator):
        coordinator.set_master(self.viewer.state.reference_data)


class _ClearPointEntry(_CoordinateEntry):
    tool_id = "solar:clear_point"
    action_text = "Clear point"
    tool_tip = "Clear the selected point"

    def run(self, coordinator):
        coordinator.clear_point()


@viewer_tool
class CoordinateTool(SimpleToolMenu):
    """
    Coordinate the Image viewer with the others of its IRIS observation.

    The tool registers its viewer with the data collection's
    `~glue_solar.quicklook.Coordinator`, which keeps the viewers on the point selected with the
    Pixel tool, and unregisters it when the viewer closes. Its menu makes the displayed dataset the
    time master of its observation, or clears the point. On a slit-jaw image it draws the displayed
    frame's slit, and the point of a raster of the same observation placed with that frame's
    coordinates while it is on the image.
    """

    icon = "glue_link"
    tool_id = "solar:coordinate"
    action_text = "Coordinate"
    tool_tip = "Coordinate this viewer with the others of its IRIS observation"

    def __init__(self, viewer, subtools=None):
        super().__init__(viewer, subtools=subtools or [_TimeMasterEntry(viewer, self), _ClearPointEntry(viewer, self)])
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
        """Draw the slit and the raster point on a slit-jaw image, or hide them."""
        viewer = self.viewer
        state = viewer.state
        slit, point = self.coordinator.slit_on(viewer), self.coordinator.point_on(viewer)
        line = None
        if state.reference_data is None or state.reference_data.ndim != 3:
            slit = point = None
        if slit is not None or point is not None:
            ny, nx = state.reference_data.shape[1:]
            if point is not None and not (-0.5 <= point[0] <= nx - 0.5 and -0.5 <= point[1] <= ny - 0.5):
                point = None
            if slit is not None:
                line = ([slit, slit], [-0.5, ny - 0.5])
            if state.x_att.axis != 2:  # the image is shown transposed
                line = line[::-1] if line is not None else None
                point = point[::-1] if point is not None else None
        changed = False
        for artist, xy in ((self._slit, line), (self._marker, None if point is None else ([point[0]], [point[1]]))):
            before = (artist.get_visible(), artist.get_xydata().tolist())
            if xy is not None:
                artist.set_data(*xy)
            artist.set_visible(xy is not None)
            changed |= (artist.get_visible(), artist.get_xydata().tolist()) != before
        if changed:  # each sync calls this: redraw only for a move
            viewer.figure.canvas.draw_idle()
