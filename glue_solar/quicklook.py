"""
The IRIS quicklook: a preset of glue viewers for one observation, kept on one selected point.
"""

import sys
import weakref
from contextlib import contextmanager
from functools import partial
from itertools import pairwise

import numpy as np
from echo import delay_callback
from glue.config import layer_artist_maker
from glue.core import Data
from glue.core.command import Command
from glue.core.hub import HubListener
from glue.core.link_helpers import LinkSame
from glue.core.link_manager import is_equivalent_cid
from glue.core.message import ComputationEndedMessage, SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from glue.core.roi import PolygonalROI
from glue.core.subset import RangeSubsetState, RoiSubsetState, SliceSubsetState, SubsetState
from glue.core.units import UnitConverter
from glue.viewers.image.pixel_selection_mode import PixelSelectionTool
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from glue.viewers.profile.state import ProfileLayerState
from glue.viewers.scatter.state import ScatterViewerState
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.profile import ProfileViewer
from glue_qt.viewers.scatter import ScatterViewer
from matplotlib.colors import to_hex
from matplotlib.lines import Line2D
from matplotlib.path import Path
from matplotlib.transforms import Bbox
from qtpy.QtCore import QEventLoop, QObject, Qt, QTimer
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QHeaderView,
    QMdiSubWindow,
    QTableWidget,
    QTableWidgetItem,
)

import astropy.units as u

from glue_solar.sources.loaders.iris import keep_hpc_linked

__all__ = [
    "Coordinator",
    "QuicklookImageViewer",
    "coordinator",
    "nearest",
    "observation_key",
    "quicklook",
    "sji_to_raster",
]

# The window the quicklook shows when the browser did not pick one
DEFAULT_WINDOW = "Mg II k 2796"
PERCENTILE = 99.5


def observation_key(data):
    """
    The ``(OBSID, STARTOBS)`` pair that identifies the IRIS observation ``data`` belongs to, or None.

    The OBSID alone names an observing program, which runs many times, so both are needed.
    """
    meta = getattr(data, "meta", None) or {}
    obsid, start = meta.get("OBSID"), meta.get("STARTOBS")
    if obsid is None or start is None:
        return None
    try:
        start = np.datetime64(str(start), "ns")
    except ValueError:
        return None
    # AIA cutouts spell the OBSID as date_time_obsid
    return None if np.isnat(start) else (str(obsid).split("_")[-1], start)


def nearest(query, reference):
    """
    The index of the reference time nearest each query time, and the signed offset reference − query.

    The reference may be unsorted or descending, as a negative-step raster's times are. Ties go to the
    earlier time and equal times to the first index. Queries outside the reference's span get its
    nearest end, with the offset showing how far off it is.

    Parameters
    ----------
    query, reference : array-like of `numpy.datetime64`
        ``reference`` is one-dimensional and holds a time; its NaT, the gaps of data regridded on time, are never
        the nearest.

    Returns
    -------
    index : `numpy.ndarray` of int
    offset : `numpy.ndarray` of `numpy.timedelta64`
    """
    reference = np.asarray(reference, dtype="datetime64[ns]")
    query = np.asarray(query, dtype="datetime64[ns]")
    if reference.ndim != 1 or np.isnat(reference).all():
        raise ValueError("the reference times must be one-dimensional and hold a time")
    order = np.argsort(reference, kind="stable")  # equal times keep their order, so the first comes first
    order = order[~np.isnat(reference[order])]  # NaT sorts last
    ref = reference[order].view("int64")
    q = query.view("int64")
    if len(ref) == 1:
        pick = np.zeros(q.shape, dtype=int)
    else:
        after = np.clip(np.searchsorted(ref, q), 1, len(ref) - 1)
        before = after - 1
        pick = np.where(q - ref[before] <= ref[after] - q, before, after)  # a tie goes to the earlier time
    index = order[np.searchsorted(ref, ref[pick])]  # the first of equal times
    return index, reference[index] - query


def _lon_lat(data, pixel):
    """Helioprojective longitude and latitude (arcsec) of ``data`` at the numpy-ordered ``pixel``."""
    world = data.coords.pixel_to_world_values(*pixel[::-1])
    types = list(data.coords.world_axis_physical_types)
    return (
        np.asarray(world[types.index("custom:pos.helioprojective.lon")]),
        np.asarray(world[types.index("custom:pos.helioprojective.lat")]),
    )


def _placeable(data):
    """Whether helioprojective positions can be placed in ``data``'s frames through its coordinates."""
    types = getattr(data.coords, "world_axis_physical_types", None) or ()
    return {"custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat", "time"} <= set(types)


def _sji_pixels(sji, frame, lon, lat):
    """The (x, y) pixels of ``sji``'s frame ``frame`` at helioprojective ``lon`` and ``lat`` (arcsec)."""
    types = list(sji.coords.world_axis_physical_types)
    when = sji.coords.pixel_to_world_values(0, 0, frame)[types.index("time")]
    world = [None] * 3
    world[types.index("custom:pos.helioprojective.lon")] = lon
    world[types.index("custom:pos.helioprojective.lat")] = lat
    world[types.index("time")] = np.broadcast_to(when, np.shape(lon))
    x, y, _ = sji.coords.world_to_pixel_values(*world)
    return x, y


def sji_to_raster(sji, frame, x, y, raster):
    """
    The pixel of ``raster`` under pixel ``x, y`` of the slit-jaw image ``sji``'s frame ``frame``, placed with that
    frame's own pointing.

    A scanning raster's step and slit row are those nearest that place. A sit-and-stare raster's exposure is the one
    nearest the frame's time, as its slit stays in place, if within half its cadence (D7), and its slit row the one
    level with the pixel, beside the slit too. A stack's scan is the one nearest the frame's time at the step scan 0
    places there, however far from it, and its step and slit row are those nearest that place with that scan's own
    pointing.

    Parameters
    ----------
    sji : `~glue.core.data.Data`
        A slit-jaw image as glue-solar loads it.
    frame : int
    x, y : float
    raster : `~glue.core.data.Data`
        A raster or a stack of scans as glue-solar loads them, of the same observation.

    Returns
    -------
    tuple of int, or None
        ``(step, slit)``, a stack's ``(scan, step, slit)``, or None outside the raster: past its first or last step
        or either end of its slit, or for a sit-and-stare more than half a cadence from its exposures.
    """
    lon, lat = _lon_lat(sji, (frame, y, x))
    when = _times(sji, None)[frame]
    steps, rows = raster.shape[-3:-1]
    if raster.ndim == 3 and _is_sit_and_stare(raster):
        # the slit row from the slit's ends: the raster's world-to-pixel is slow here, and ambiguous along time
        times = _times(raster, None)
        [step], [offset] = nearest([when], times)
        if abs(offset) > _half_cadence(times):
            return None
        lons, lats = _lon_lat(raster, (np.full(2, step), [0, rows - 1], np.zeros(2)))
        along = np.array([lons[1] - lons[0], lats[1] - lats[0]]) / (rows - 1)  # one slit pixel
        slit = np.dot([lon - lons[0], lat - lats[0]], along) / np.dot(along, along)
    else:
        types = list(raster.coords.world_axis_physical_types)
        world = list(raster.coords.pixel_to_world_values(*[0] * raster.ndim))  # any wavelength, and scan 0
        world[types.index("custom:pos.helioprojective.lon")] = lon
        world[types.index("custom:pos.helioprojective.lat")] = lat
        *_, step, slit, _ = raster.coords.world_to_pixel_values(*world)[::-1]  # NaN off the raster
        if raster.ndim == 4 and 0 <= np.round(step) < steps:  # again in the scan's own pointing; Scan is last
            [world[-1]], _ = nearest([when], _times(raster, int(np.round(step))))
            *_, step, slit, _ = raster.coords.world_to_pixel_values(*world)[::-1]
    step, slit = np.round(step), np.round(slit)
    if not (0 <= step < steps and 0 <= slit < rows):
        return None
    index = (int(step), int(slit))
    return index if raster.ndim == 3 else (int(world[-1]), *index)


def _time_axis(data):
    """
    The axis along which ``data`` steps through time, or None for a scanning raster, which has none.

    A slit-jaw image or AIA cutout steps through frames, a sit-and-stare raster through exposures and
    a stack through scans; a scanning raster's steps are places on the Sun.
    """
    role = _role(data)
    if role in ("sji", "aia") or (role == "raster" and (data.ndim == 4 or _is_sit_and_stare(data))):
        return 0
    return None


def _timed(data):
    """Whether ``data`` takes part in time sync: an IRIS dataset or aligned AIA cutout with times."""
    return bool(_role(data)) and data.find_component_id("Time") is not None


def _times(data, step):
    """The 1-D times of ``data``: per frame, exposure or step, or per scan at raster step ``step`` of a stack."""
    index = [0] * data.ndim
    index[0] = slice(None)
    if data.ndim == 4:
        index[1] = step
    return data[data.find_component_id("Time"), tuple(index)]


def _cadence(times):
    """The median interval between successive times, NaT left out, or 0 without two different times."""
    steps = np.diff(np.sort(times)).astype("timedelta64[ns]").view("int64")
    steps = steps[steps > 0]  # NaT sorts last, and its intervals are the least int64
    return np.timedelta64(int(np.median(steps)) if len(steps) else 0, "ns")


def _half_cadence(times):
    """Half the median interval between successive times: the widest offset that still matches."""
    return _cadence(times) / 2


def coordinator(data_collection):
    """The `Coordinator` of ``data_collection``, created on first use and kept on the collection."""
    if not hasattr(data_collection, "_solar_coordinator"):
        # the hub holds its listeners weakly
        data_collection._solar_coordinator = Coordinator(data_collection)
    return data_collection._solar_coordinator


def _spectral_axes(data):
    """The array axes of ``data`` along which the wavelength varies."""
    wcs = data.coords
    types = getattr(wcs, "world_axis_physical_types", None) or ()
    matrix = getattr(wcs, "axis_correlation_matrix", None)
    return {
        data.ndim - 1 - pixel  # APE 14 orders pixel axes opposite to numpy
        for world, kind in enumerate(types)
        if kind == "em.wl"
        for pixel in np.nonzero(matrix[world])[0]
    }


def _pixel_tool_on(viewer):
    return isinstance(viewer.toolbar.active_tool, PixelSelectionTool)  # Pixel, or glue-solar's Follow/lock


def _shown(state):
    """The array axes an Image viewer state displays."""
    return {att.axis for att in (state.x_att, state.y_att) if att is not None}


def _sji_frame(state):
    """The frame a slit-jaw viewer shows, a collapse's centre, or None while it displays the frame axis."""
    data = state.reference_data
    if data is None or state.x_att is None or state.y_att is None or len(state.slices) != data.ndim:
        return None
    if 0 in _shown(state):
        return None
    return int(getattr(state.slices[0], "center", state.slices[0]))


class Coordinator(HubListener):
    """
    Keep the Image viewers of each IRIS observation on one selected point.

    The point is the Pixel tool's selection: the coordinator follows the last subset group given a
    `~glue.viewers.image.pixel_selection_subset_state.PixelSubsetState` on IRIS data. On a
    spectral cube the point is a detector pixel at every wavelength: a click takes the axes the
    clicked viewer does not show, such as a stack's scan, from its sliders. A click on a panel that
    shows wavelength moves the cube's maps to the clicked wavelength instead of fixing it. Every
    other viewer of the cube, or of another window of its file (`_same_file`), then shows the point's
    step, exposure, scan and slit, after a drag only its last position, and editing one of those
    sliders moves the point. No other wavelength slider is moved, and a Profile's collapse is left in
    place. A viewer whose sliders glue resets for new data joins the point. A quicklook's point drives
    only the viewers it `owns`, and shows only on those of its own file's windows; viewers no
    quicklook owns follow whichever point is followed. A click on a quicklook's slit-jaw image moves
    its point to the raster there (`_to_raster`). A datetime Scatter plot shows the time master's
    exposure (`_mark`). Each data collection has one coordinator (`coordinator`), and the
    ``solar:coordinate`` tool registers every Image viewer with it.
    """

    def __init__(self, data_collection):
        self.data_collection = data_collection
        self.group = None
        self.masters = {}  # observation key -> the dataset chosen as its time master
        self._master_times = {}  # observation key -> (master, its time, timing step) at the last sync
        self._steps = {}  # raster -> its timing step when the point last was on it
        self._listeners = []  # called with (observation key, master time, exposure) after each sync
        self._pairs = {}  # (master, follower, raster step) -> nearest() of every master time
        self._viewers = {}  # registered viewer -> its callbacks
        self._shows = {}  # registered viewer -> the reference data its sliders were last set for
        self._owners = {}  # a quicklook's point group -> the viewers it drives
        self._placed = (None, None)  # point_on's last (raster, pixel, slit-jaw, frame) and answer
        self.overlays = set()  # the observation keys whose raster overlays show (`footprint_on`, `step_on`)
        self._footprint = (None, None)  # footprint_on's last (raster, scan, slit-jaw) and answer
        self._before = {}  # point group -> its last state other than a slit-jaw point (see _to_raster)
        # a slit-jaw image clicked, the point its click set or left, and the viewer and frame clicked (see _to_raster)
        self._kept = (None, None, None, None)
        self._outside = (None, None)  # a slit-jaw viewer clicked outside the raster, and the point its click left
        self._busy = False
        self.marker = None  # the 'Master exposure' subset group (`_mark`), once made
        self._drag = None  # while a mouse button is down on a viewer: whether a point was clicked
        # a drag moves the point at every mouse event: show only its latest position
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._update)
        hub = data_collection.hub
        hub.subscribe(self, SubsetCreateMessage, handler=self._subset_changed)
        hub.subscribe(self, SubsetDeleteMessage, handler=self._subset_deleted)
        hub.subscribe(
            self, SubsetUpdateMessage, handler=self._subset_changed, filter=lambda m: m.attribute == "subset_state"
        )

    @property
    def point(self):
        """The followed group's subset state if it is still a Pixel selection, else None."""
        group = self.group
        if group is None or group not in self.data_collection.subset_groups:
            return None
        state = group.subset_state
        return state if isinstance(state, PixelSubsetState) else None

    def register(self, viewer):
        """Coordinate ``viewer``, an Image viewer of this data collection."""
        if viewer in self._viewers:
            return

        def axes_changed(*_):
            self._apply_point(viewer)

        def slices_changed(old, new):
            data = viewer.state.reference_data
            if data is not self._shows.get(viewer):
                # glue reset the sliders for new data: join the point rather than move it
                self._shows[viewer] = data
                self._apply_point(viewer)
                self._timer.start()  # and the time master
                return
            self._move_point(viewer)
            # a master's time is along its first axis, or at the point, which _move_point follows
            moved = (old or ())[:1] != (new or ())[:1]
            if moved and not self._busy and self._master(observation_key(data)) is data:
                self._timer.start()  # the time master moved

        def mouse_button(event):
            self._drag = False if event.name == "button_press_event" else None

        for prop in ("reference_data", "x_att", "y_att"):
            viewer.state.add_callback(prop, axes_changed)
        viewer.state.add_callback("slices", slices_changed, echo_old=True)
        canvas = viewer.figure.canvas
        buttons = [canvas.mpl_connect(name, mouse_button) for name in ("button_press_event", "button_release_event")]
        self._viewers[viewer] = (axes_changed, slices_changed, buttons)
        self._shows[viewer] = viewer.state.reference_data
        self._timer.start()  # join the time master

    def unregister(self, viewer):
        """Stop coordinating ``viewer``; unregistering it again does nothing."""
        for owned in self._owners.values():
            owned.discard(viewer)  # or its quicklook's point would add layers to it after it closed
        callbacks = self._viewers.pop(viewer, None)
        if callbacks is not None:
            axes_changed, slices_changed, buttons = callbacks
            for prop in ("reference_data", "x_att", "y_att"):
                viewer.state.remove_callback(prop, axes_changed)
            viewer.state.remove_callback("slices", slices_changed)
            for connection in buttons:
                viewer.figure.canvas.mpl_disconnect(connection)
            self._shows.pop(viewer, None)
            self._timer.start()  # the time master may have gone with it

    def own(self, group, viewers):
        """Let the point group ``group`` drive only the viewers it owns, ``viewers`` too, and those follow only it."""
        self._owners.setdefault(group, set()).update(viewers)

    def follow(self, group):
        """Make ``group`` the followed point, as when its quicklook's tab is shown."""
        self.group = group
        self._timer.start()

    def _follows(self, viewer):
        """Whether ``viewer`` follows the followed point: it owns the viewer, or no point does."""
        owners = self._owners.get(self.group)
        if owners is not None and viewer in owners:
            return True
        return not any(viewer in viewers for viewers in self._owners.values())

    def set_master(self, data):
        """Make ``data`` the time master of its observation."""
        key = observation_key(data)
        if key is not None:
            self.masters[key] = data
            self._timer.start()

    def toggle_overlays(self, key):
        """Show or hide the raster overlays of observation ``key`` (`footprint_on`, `step_on`)."""
        if key is not None:
            self.overlays ^= {key}
            self._timer.start()  # the sync redraws them

    def add_listener(self, listener):
        """Call ``listener(key, time, exposure)`` whenever the time master of observation ``key`` moves."""
        self._listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def place_again(self):
        """Place the point and the raster overlays again, as after a pointing changed ('IRIS: shift pointing…')."""
        self._placed = self._footprint = (None, None)
        self._timer.start()  # the sync redraws them

    def clear_point(self):
        """Empty the followed group, which hides its crosshairs."""
        if self.point is not None:
            self.group.subset_state = SubsetState()
            self._timer.start()  # time sync continues from the sliders

    def move_master(self, data, index):
        """
        Move ``data``, the time master of its observation, to ``index`` along its first axis: its frame, exposure,
        step or scan, on the point if it holds one. The others follow it, as after a move of its slider.
        """
        if _role(data) == "raster" and data.ndim == 3:
            self._steps[data] = index  # its time without a point, unless a sit-and-stare's exposure slider gives it
        with self._writing():
            self._move_in_time(data, 0, index)
        self._timer.start()

    @contextmanager
    def _writing(self):
        self._busy = True
        try:
            yield
        finally:
            self._busy = False

    @contextmanager
    def showing(self, viewer, data):
        """Let ``viewer`` turn to ``data`` and its slices as a blink flip: the point and the time master stay (D41)."""
        self._shows[viewer] = data  # not new data for register's slices_changed to join the point on
        with self._writing():
            yield

    def _subset_changed(self, message):
        subset = message.subset
        state = subset.subset_state
        if _role(getattr(state, "reference_data", None)) != "sji":
            self._before[getattr(subset, "group", None)] = state
        if getattr(subset, "group", None) is self.group and not isinstance(state, PixelSubsetState):
            self._timer.start()  # another selection replaced the point: readouts follow
        # a group sends one message per dataset; answer the one of the point's own dataset
        if self._busy or not isinstance(state, PixelSubsetState) or subset.data is not state.reference_data:
            return
        group = getattr(subset, "group", None)
        if group is None or observation_key(subset.data) is None:
            return
        self.group = group
        self._pin(state)
        self._to_raster(state)
        # an Undo or Redo back to a slit-jaw click's point: under a raster master, its viewer back to the frame clicked
        sji, clicked, viewer, frame = self._kept
        master = self._master(observation_key(state.reference_data))
        if state is clicked and viewer.state.reference_data is sji and _role(master) == "raster":
            with self._writing():
                self._set_slices(viewer, {0: frame})
        if self._drag:
            self._timer.start()
            return
        if self._drag is False:
            self._drag = True  # the press: until the release, a drag
        # a click, or a point set by code: move the panels before glue draws the point, so each draws once
        self._timer.stop()
        try:
            self._update()
        except Exception:  # reported as from the timer: matplotlib's mouse events would only print it
            sys.excepthook(*sys.exc_info())

    def _subset_deleted(self, message):
        if getattr(message.subset, "group", None) is self.group:
            self._timer.start()  # the point's group went: readouts follow

    def _viewers_of(self, data):
        """The registered viewers of ``data`` that follow the point."""
        return [viewer for viewer in self._viewers if viewer.state.reference_data is data and self._follows(viewer)]

    def _pin(self, state):
        """
        Make a click the point: a detector pixel at every wavelength.

        The point's other free axes come from the sliders of the viewer it was clicked in. A click on
        a panel showing wavelength frees the wavelength and moves the cube's maps to it.
        """
        data = state.reference_data
        spectral = _spectral_axes(data)
        if not spectral:
            return  # a slit-jaw point is a detector pixel in every frame
        clicked = {axis for axis, s in enumerate(state.slices) if s.start is not None}
        candidates = [v for v in self._viewers_of(data) if _shown(v.state) == clicked]
        # the viewer whose Pixel tool is on, if several show the clicked axes
        viewer = next((v for v in candidates if _pixel_tool_on(v)), candidates[0] if candidates else None)
        if viewer is None:
            return
        slices = list(state.slices)
        wavelengths = {axis: s.start for axis, s in enumerate(state.slices) if axis in spectral and s.start is not None}
        for axis, s in enumerate(state.slices):
            if axis in wavelengths:
                slices[axis] = slice(None)
            elif s.start is None and axis not in spectral:
                index = getattr(viewer.state.slices[axis], "center", viewer.state.slices[axis])
                slices[axis] = slice(index, index + 1)
        with self._writing():
            for other in self._viewers_of(data):
                self._set_slices(other, wavelengths)
            if slices != list(state.slices):
                self.group.subset_state = PixelSubsetState(data, slices)

    def _to_raster(self, state):
        """
        Make a click on a slit-jaw image of a quicklook the point of the quicklook's raster there, placed with the frame
        the clicked viewer shows (`sji_to_raster`). Under a raster time master that frame stays while the point is the
        click's, rather than move to the time the click gave the raster, and an Undo or Redo back to the click's point
        moves the viewer back to it. A click outside the raster leaves the point as
        it was, and the viewer's readout says so (`outside_raster`). A click on an image showing its frame axis, or
        outside a quicklook, stays a slit-jaw point.
        """
        sji, owners = state.reference_data, self._owners.get(self.group, ())
        clicked = {axis for axis, s in enumerate(state.slices) if s.start is not None}
        if _role(sji) != "sji" or clicked != {1, 2} or not _placeable(sji):
            return
        rasters = [viewer.state.reference_data for viewer in self._viewers if viewer in owners]
        key = observation_key(sji)
        raster = next((data for data in rasters if _role(data) == "raster" and observation_key(data) == key), None)
        viewers = [viewer for viewer in self._viewers_of(sji) if _sji_frame(viewer.state) is not None]
        viewer = next((v for v in viewers if _pixel_tool_on(v)), viewers[0] if viewers else None)
        if raster is None or viewer is None:
            return
        index = sji_to_raster(sji, _sji_frame(viewer.state), state.slices[2].start, state.slices[1].start, raster)
        with self._writing():  # within glue's undo step for the click, which restores the point before it
            if index is None:
                self.group.subset_state = self._before.get(self.group, SubsetState())
            else:
                self.group.subset_state = PixelSubsetState(raster, [slice(i, i + 1) for i in index] + [slice(None)])
        # without a point the sliders keep driving the time
        self._kept = (sji, self.point, viewer, _sji_frame(viewer.state))
        self._outside = (viewer if index is None else None, self.group.subset_state)

    def outside_raster(self, viewer):
        """Whether the last click on the slit-jaw ``viewer`` fell outside the raster, while the point is as it left it."""
        clicked, point = self._outside
        return clicked is viewer and self.group.subset_state is point

    @staticmethod
    def _set_slices(viewer, indices):
        """
        Move the viewer's sliders on the axes it does not show to ``indices``, leaving a collapse in place but moving a
        wavelength band (``solar:band``), which the band re-makes about the index.
        """
        state = viewer.state
        if len(state.slices) != state.reference_data.ndim:
            return  # mid-way through an axis change
        shown = _shown(state)
        band = viewer.toolbar.tools.get("solar:band")
        banded = _spectral_axes(state.reference_data) if band is not None and band.checked else set()
        slices = list(state.slices)
        for axis, index in indices.items():
            if axis not in shown and (axis in banded or not isinstance(slices[axis], AggregateSlice)):
                slices[axis] = index
        if slices != list(state.slices):
            state.slices = tuple(slices)

    def _update(self):
        """Follow each observation's time master, then move every viewer of the point's cube to it."""
        # an observation in a hidden quicklook tab keeps its times until it is shown
        followed = {observation_key(viewer.state.reference_data) for viewer in self._viewers if self._follows(viewer)}
        for key in followed - {None}:
            self._sync(key)
        point = self.point
        if point is None:
            return
        for viewer in list(self._viewers):
            self._apply_point(viewer)
        # among its quicklook's viewers, the point shows on those of its own file's windows: glue 1.27.0 would
        # draw a slit-jaw point's crosshair on the raster panels, and a raster point's on the slit-jaw
        for viewer in self._owners.get(self.group, ()):
            _show(viewer, self.group, _same_file(viewer.state.reference_data, point.reference_data))

    def _datasets(self, key):
        seen = {}
        for viewer in self._viewers:
            data = viewer.state.reference_data
            if data is not None and observation_key(data) == key and _timed(data):
                seen.setdefault(id(data), data)
        return list(seen.values())

    def _master(self, key):
        """
        The time master of observation ``key``: the chosen one, else the point's raster, else the first raster the
        followed point's viewers show, else the first raster.
        """
        if key is None:
            return None
        datasets = self._datasets(key)
        chosen = self.masters.get(key)
        if chosen is not None and chosen in datasets:
            return chosen
        point = self.point
        if point is not None and point.reference_data in datasets and _role(point.reference_data) == "raster":
            return point.reference_data
        # else a raster of the followed point's viewers, as after Clear point, not one of a hidden tab
        rasters = [data for data in datasets if _role(data) == "raster"]
        followed = {id(viewer.state.reference_data) for viewer in self._viewers if self._follows(viewer)}
        return next((data for data in rasters if id(data) in followed), next(iter(rasters), None))

    def master_time(self, key):
        """The time of observation ``key``'s time master now, as the coming time sync takes it, or None."""
        master = self._master(key)
        if master is None:
            return None
        index, step = self._timing(master)
        times = _times(master, step)
        return times[min(max(index, 0), len(times) - 1)]

    def _timing(self, data):
        """
        The index of ``data``'s time along its first axis and, for rasters, the timing step.

        A raster's timing step is the point's step, or the one it had when the point left the raster
        (mid-raster before any); a sit-and-stare's exposure and a stack's scan otherwise come from the
        sliders. A slit-jaw image's time is its frame.
        """
        point = self.point
        if _role(data) != "raster":
            return self._slider(data, 0), None
        step_axis = data.ndim - 3
        # a click is the point before _pin gives it the axes it was not clicked on
        on_data = point is not None and _same_file(point.reference_data, data)
        if on_data and point.slices[0].start is not None and point.slices[step_axis].start is not None:
            step = self._steps[data] = point.slices[step_axis].start
            scan = point.slices[0].start
        else:
            step = self._steps.get(data, data.shape[step_axis] // 2)
            if data.ndim == 3 and _time_axis(data) == 0:
                step = self._slider(data, 0, step)
            scan = self._slider(data, 0)
        return (scan if data.ndim == 4 else step), step

    def _slider(self, data, axis, default=0):
        """The slider of a viewer of ``data`` that does not show ``axis``, at the centre of a collapse."""
        for viewer in self._viewers_of(data):
            if axis not in _shown(viewer.state) and len(viewer.state.slices) == data.ndim:
                index = viewer.state.slices[axis]
                return int(getattr(index, "center", index))
        return default

    def _pair(self, master, follower, master_step, follower_step):
        """nearest() of every master time among the follower's, cached per pair."""
        # only a stack's times depend on the raster step
        key = (id(master), id(follower), master_step if master.ndim == 4 else None)
        key += (follower_step if follower.ndim == 4 else None,)
        if key not in self._pairs:
            self._pairs[key] = nearest(_times(master, master_step), _times(follower, follower_step))
        return self._pairs[key]

    def _follow(self, master, index, step, data):
        """
        The index along the time axis of ``data`` nearest the time of ``master`` at ``index`` and timing ``step``, or
        None past half its cadence (NO MATCH), in a gap of a master regridded on time, without a time axis, or for the
        slit-jaw image clicked while the point is the click's and a raster the master.
        """
        kept, clicked, *_ = self._kept
        if data is kept and _role(master) == "raster" and getattr(self.group, "subset_state", None) is clicked:
            return None  # a slit-jaw master rules, and once the point moves the image clicked follows it
        follower_step = self._timing(data)[1]
        nearest_index, offset = (value[index] for value in self._pair(master, data, step, follower_step))
        # NaT, a gap's offset, is never within the cadence
        if _time_axis(data) is not None and abs(offset) <= _half_cadence(_times(data, follower_step)):
            return int(nearest_index)
        return None

    def following(self, data):
        """
        The index along the time axis of ``data`` that the time sync gives it now as a follower of its observation's
        time master, as a blink flip to it shows (D7), or None: no match, no times or time axis, no other time master,
        or the slit-jaw image clicked.
        """
        master = self._master(observation_key(data))
        if master is None or master is data or not _timed(data):
            return None
        index, step = self._timing(master)
        return self._follow(master, min(max(index, 0), len(_times(master, step)) - 1), step, data)

    def _sync(self, key):
        """Move the followers of observation ``key`` to its time master, or mark them NO MATCH."""
        master = self._master(key)
        if master is None:
            return
        index, step = self._timing(master)
        times = _times(master, step)
        index = min(max(index, 0), len(times) - 1)
        self._master_times[key] = (master, times[index], step)
        moved = {}
        for data in self._datasets(key):
            if data is master:
                continue
            frame = self._follow(master, index, step, data)
            if frame is not None:
                moved[data] = (_time_axis(data), frame)
        with self._writing():
            for data, (axis, frame) in moved.items():
                self._move_in_time(data, axis, frame)
        exposure = master.find_component_id("Exposure time")
        seconds = None
        if exposure is not None:
            view = [0] * master.ndim
            view[0] = index
            if master.ndim == 4:
                view[1] = step
            seconds = float(master[exposure, tuple(view)])
        self._mark(key, times[index], seconds)
        for listener in list(self._listeners):
            listener(key, times[index], seconds)

    def _mark(self, key, time, seconds):
        """
        Select the exposure of observation ``key``'s time master, from ``time`` for ``seconds``, on the first open
        datetime Scatter plot of an observation's data (by OBSID and STARTOBS) while that observation is ``key``: as
        the subset group 'Master exposure', glue's own range on that axis, as a range dragged there gives. The group
        is a session's, found by its label, or made at the first such sync and removed from the other viewers open
        then; deleting it stops it.
        """
        groups = self.data_collection.subset_groups
        if self.marker is not None and self.marker not in groups:
            return  # deleted
        app = next(iter(self._viewers)).session.application
        viewers = [viewer for tab in app.viewers for viewer in tab if not viewer._closed]  # glue-qt keeps closed ones
        plots = [viewer.state for viewer in viewers if isinstance(viewer.state, ScatterViewerState)]
        # ponytail: the first such plot's axis only, unlinked times on another stay unmarked; a range per axis if needed
        times = [state.x_att for state in plots if state.x_att is not None and "datetime" in state.x_kinds]
        # one observation's, or each observation's sync would move the one group in turn
        x = next((att for att in times if observation_key(att.parent) is not None), None)
        if x is None or observation_key(x.parent) != key:
            return
        end = time + np.timedelta64(int(np.nan_to_num((seconds or 0) * 1e9)), "ns")
        state = RangeSubsetState(time, end, x)
        if self.marker is None:
            self.marker = next((group for group in groups if group.label == "Master exposure"), None)
        if self.marker is None:
            mode = app.session.edit_subset_mode
            edit = mode.edit_subset
            self.marker = self.data_collection.new_subset_group(label="Master exposure", subset_state=state)
            mode.edit_subset = edit  # glue-qt makes a new group the edit subset
            for viewer in viewers:
                if not isinstance(viewer.state, ScatterViewerState):
                    _show(viewer, self.marker, False)  # as a light curve is: they would update it at each step
        old = self.marker.subset_state
        if not (isinstance(old, RangeSubsetState) and old.att is x and old.lo == time and old.hi == end):
            self.marker.subset_state = state

    def time_status(self, viewer):
        """
        What ``viewer``'s readout says about time: ("master", timing step or None), ("match", offset) or
        ("no match", offset), with the offset of its time from the master's; None outside time sync.

        A follower with no frame within half its cadence of the master's time is NO MATCH with the
        nearest frame's offset; otherwise the offset is its displayed frame's, a match if that frame is
        within half a cadence. A scanning raster's offset is its timing step's, a match while the
        master's time is within its steps' span.
        """
        data = viewer.state.reference_data
        key = observation_key(data) if data is not None else None
        master, when, step = self._master_times.get(key, (None, None, None))
        if master is None or master is not self._master(key) or not _timed(data):
            return None
        if data is master:
            return ("master", step)
        follower_step = self._timing(data)[1]
        times = _times(data, follower_step)
        margin = _half_cadence(times)
        axis = _time_axis(data)
        if axis is None:
            offset = times[follower_step] - when
            return ("match" if times.min() - margin <= when <= times.max() + margin else "no match", offset)
        _, [offset] = nearest([when], times)
        if abs(offset) > margin:
            return ("no match", offset)
        state = viewer.state
        if axis not in _shown(state) and len(state.slices) == data.ndim:
            offset = times[int(getattr(state.slices[axis], "center", state.slices[axis]))] - when
        return ("match" if abs(offset) <= margin else "no match", offset)

    def point_on(self, viewer):
        """
        Where the point of a raster of the same observation falls in ``viewer``'s slit-jaw frame, as
        (x, y) pixels projected through that frame's own coordinates, or None.
        """
        point, sji = self.point, viewer.state.reference_data
        if point is None or sji is None or _role(sji) != "sji" or _role(point.reference_data) != "raster":
            return None
        frame = _sji_frame(viewer.state)
        if observation_key(sji) != observation_key(point.reference_data) or frame is None or not _placeable(sji):
            return None
        pixel = [s.start if s.start is not None else 0 for s in point.slices]
        # the frame-time readout and the slit-jaw marker both ask for each move
        key = (point.reference_data, pixel, sji, frame)
        if self._placed[0] != key:
            lon, lat = _lon_lat(point.reference_data, pixel)
            x, y = _sji_pixels(sji, frame, lon, lat)
            self._placed = (key, (float(x), float(y)))
        return self._placed[1]

    def footprint_on(self, viewer):
        """
        With the raster overlays of ``viewer``'s slit-jaw image's observation on: the slit of each step or exposure of
        its raster, a stack's at its timing scan, placed through the slit-jaw frame nearest that step's time, as x and y
        pixels of each slit's ends, the slits split by NaN; else None.
        """
        sji = viewer.state.reference_data
        key = observation_key(sji) if sji is not None else None
        if key not in self.overlays or _role(sji) != "sji" or _sji_frame(viewer.state) is None or not _placeable(sji):
            return None
        raster = self._master(key)
        if _role(raster) != "raster":
            raster = next((data for data in self._datasets(key) if _role(data) == "raster"), None)
        if raster is None:
            return None
        scan = self._timing(raster)[0] if raster.ndim == 4 else None
        if self._footprint[0] != (raster, scan, sji):  # the same at every frame step
            steps, rows = raster.shape[-3:-1]
            lead = () if scan is None else (scan,)
            times = raster[raster.find_component_id("Time"), (*lead, slice(None), 0, 0)]
            frames, _ = nearest(times, _times(sji, None))
            n = 2 * steps  # each slit's two ends
            ends = (*(np.full(n, i) for i in lead), np.arange(n) // 2, np.tile([-0.5, rows - 0.5], steps), np.zeros(n))
            x, y = _sji_pixels(sji, np.repeat(frames, 2), *_lon_lat(raster, ends))
            gaps = np.full((steps, 1), np.nan)
            xy = tuple(np.hstack([v.reshape(steps, 2), gaps]).ravel() for v in (x, y))
            self._footprint = ((raster, scan, sji), xy)
        return self._footprint[1]

    def step_on(self, viewer):
        """
        With the raster overlays of ``viewer``'s raster's observation on, while ``viewer`` shows its steps or exposures
        against slit: the step or exposure, of a stack at the scan shown, nearest the time master's time, or None beyond
        half their cadence (NO MATCH); else None.
        """
        state, data = viewer.state, viewer.state.reference_data
        key = observation_key(data) if data is not None else None
        if key not in self.overlays or _role(data) != "raster" or len(state.slices) != data.ndim:
            return None
        axis = data.ndim - 3
        when = self.master_time(key)
        if _shown(state) != {axis, axis + 1} or when is None:
            return None
        lead = (int(getattr(state.slices[0], "center", state.slices[0])),) if axis else ()
        times = data[data.find_component_id("Time"), (*lead, slice(None), 0, 0)]
        [index], [offset] = nearest([when], times)
        return int(index) if abs(offset) <= _half_cadence(times) else None

    @staticmethod
    def slit_on(viewer):
        """The slit's x pixel in ``viewer``'s slit-jaw frame, or None where the frame gives none (0 or NaN)."""
        sji = viewer.state.reference_data
        frame = _sji_frame(viewer.state)
        if frame is None or _role(sji) != "sji" or "slit x position" not in sji.meta:
            return None
        x = float(sji.meta["slit x position"][frame])
        return None if x == 0 or np.isnan(x) else x - 1  # irispy gives the header's 1-based pixel

    def _move_in_time(self, data, axis, frame):
        """
        Put ``data`` at ``frame`` along its time axis: on its viewers, and on the point if it is on any window of
        ``data``'s file (`_same_file`), which stays the point's window.
        """
        point = self.point
        if point is not None and _same_file(point.reference_data, data) and point.slices[axis].start is not None:
            slices = list(point.slices)
            if slices[axis].start != frame:
                slices[axis] = slice(frame, frame + 1)
                self.group.subset_state = PixelSubsetState(point.reference_data, slices)
        for viewer in self._viewers_of(data):
            self._set_slices(viewer, {axis: frame})

    def _move_point(self, viewer):
        """Move the point along the axes whose sliders the user moved in ``viewer``."""
        point = self.point
        state = viewer.state
        if self._busy or point is None or not _same_file(state.reference_data, point.reference_data):
            return
        if len(state.slices) != point.reference_data.ndim or not self._follows(viewer):
            return
        shown, spectral = _shown(state), _spectral_axes(point.reference_data)
        slices = list(point.slices)
        for axis, s in enumerate(point.slices):
            index = state.slices[axis]
            if s.start is not None and axis not in shown | spectral and not isinstance(index, AggregateSlice):
                slices[axis] = slice(index, index + 1)
        if slices != list(point.slices):
            with self._writing():
                self.group.subset_state = PixelSubsetState(point.reference_data, slices)
            self._timer.start()

    def _apply_point(self, viewer):
        """Move the sliders of a viewer of the point's file along the point's fixed axes, wavelength aside."""
        state, point = viewer.state, self.point
        data, shown = state.reference_data, _shown(state)
        # mid-way through an axis change a viewer can show fewer than two axes
        if self._busy or point is None or not _same_file(data, point.reference_data) or len(shown) < 2:
            return
        if not self._follows(viewer):
            return
        spectral = _spectral_axes(data)
        fixed = {axis: s.start for axis, s in enumerate(point.slices) if s.start is not None and axis not in spectral}
        with self._writing():
            self._set_slices(viewer, fixed)


def _within_half_turn(lon, lat):
    """Longitudes (arcsec) within ±180°, as glue-solar gives IRIS data's: a sunpy map's can run from 0 to 360°."""
    return (lon + 648000) % 1296000 - 648000, lat


def _outline_region(raster, roi, x_axis, y_axis, slices):
    """
    ``roi``, drawn on the pixel axes ``x_axis`` and ``y_axis`` of ``raster`` at ``slices``, as a region of
    helioprojective longitude and latitude.

    Its outline runs within the raster's first and last pixel centres, past which glue's inverse of its coordinates
    places nothing, and has a corner wherever it crosses a whole step: between steps those coordinates are linear.
    ``raster`` can also be a slit-jaw image, at the frame in ``slices``: across a frame its coordinates are linear to
    1.3e-4 pixel, so the outline has no other corners.
    """
    margin = 1e-6  # so that pixel centres on the edge, such as another window's of the raster, are inside
    box = Bbox([[-margin, -margin], [raster.shape[x_axis] - 1 + margin, raster.shape[y_axis] - 1 + margin]])
    vertices = np.column_stack(roi.to_polygon())
    clipped = Path(np.vstack([vertices, vertices[:1]]), closed=True).clip_to_bbox(box).to_polygons()
    along = int(y_axis == raster.ndim - 3)  # the outline's coordinate along the steps
    points = []
    for start, end in pairwise(clipped[0] if clipped else ()):
        if _role(raster) != "raster":  # a slit-jaw frame, which has no steps
            points.append(start)
            continue
        low, high = sorted((start[along], end[along]))
        crossings = (np.arange(np.floor(low) + 1, np.ceil(high)) - start[along]) / (end[along] - start[along])
        points += [start, *(start + np.sort(crossings)[:, None] * (end - start))]
    x, y = np.reshape(points, (-1, 2)).T
    pixel = [np.full(len(x), getattr(s, "center", s)) for s in slices]
    pixel[x_axis], pixel[y_axis] = x, y
    lon, lat = _lon_lat(raster, pixel)
    types = list(raster.coords.world_axis_physical_types)
    lon_id, lat_id = (
        raster.world_component_ids[raster.ndim - 1 - types.index(f"custom:pos.helioprojective.{angle}")]
        for angle in ("lon", "lat")
    )
    return RoiSubsetState(lon_id, lat_id, PolygonalROI(lon, lat), pretransform=_within_half_turn)


class _RasterRoiSubsetState(RoiSubsetState):
    """
    A region drawn on a raster map or a slit-jaw frame: that dataset's pixels inside it, as glue's own region, also in
    data whose pixels glue links to them as the same (`_link_windows`), and on other data ``world``, the region inside
    its outline (`_outline_region`). glue places that without inverting the raster's coordinates at each of their
    pixels, and would place a slit-jaw image's own region nowhere else, as time is not linked.
    """

    def __init__(self, xatt, yatt, roi, world):
        super().__init__(xatt, yatt, roi)
        self.world = world

    def to_mask(self, data, view=None):
        if any(is_equivalent_cid(data, self.xatt, cid) for cid in data.pixel_component_ids):
            return super().to_mask(data, view)
        view = (slice(None),) * data.ndim if view is None else view
        types = getattr(data.coords, "world_axis_physical_types", None) or ()
        hpc = ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat")
        angles = [i for i, kind in enumerate(types) if kind in hpc]
        if len(angles) != 2 or len(view) != data.ndim or not all(isinstance(s, slice) for s in view):
            return self.world.to_mask(data, view)
        # as glue does for a region of pixels, place one plane along the axes on which longitude and latitude do not
        # depend, such as a raster's wavelength, and spread it along them: a spectrum over every pixel takes seconds
        flat = ~data.coords.axis_correlation_matrix[angles].any(axis=0)[::-1]
        ranges = [range(*s.indices(n)) for s, n in zip(view, data.shape)]
        plane = tuple(slice(r.start, r.start + 1) if f else s for f, r, s in zip(flat, ranges, view))
        return np.broadcast_to(self.world.to_mask(data, plane), [len(r) for r in ranges])

    def copy(self):  # glue applies a copy
        return _RasterRoiSubsetState(self.xatt, self.yatt, self.roi, self.world)


class _NewSubset(Command):
    """
    A new subset group of ``subset_state``, leaving the edit subset as it is; undo removes the group.

    glue-qt's data collection selects every new group, which makes it the edit subset, and empties the edit subset
    when a group is removed; glue's undo of a new subset leaves its emptied group there.
    """

    kwargs = ["data_collection", "subset_state"]
    label = "new subset"

    def do(self, session):
        edit = session.edit_subset_mode.edit_subset
        self.group = self.data_collection.new_subset_group(subset_state=self.subset_state.copy())
        session.edit_subset_mode.edit_subset = edit

    def undo(self, session):
        edit = session.edit_subset_mode.edit_subset
        self.data_collection.remove_subset_group(self.group)
        session.edit_subset_mode.edit_subset = [group for group in edit if group is not self.group]


class QuicklookImageViewer(ImageViewer):
    """
    The quicklook's Image viewer, whose regions on a raster map or a slit-jaw frame reach other data by their outline.

    glue would place a region drawn on a raster map in a linked slit-jaw image by inverting the raster's coordinates
    at each screen pixel, which takes seconds per frame, and one drawn on a slit-jaw image nowhere else, as time is
    not linked. Here the region selects the raster's pixels inside it, and on other data, such as each slit-jaw frame
    at its own pointing, what lies inside its outline in helioprojective longitude and latitude. One on a slit-jaw
    image selects its pixels inside it in every frame, as glue's own does, and on other data, such as the raster, what
    lies inside its outline at the pointing of the frame it was drawn on. A region on any other panel is glue's own.
    While a quicklook's point is the edit subset, a region on any panel is a new subset and the point stays the edit
    subset, so the Pixel tool keeps moving it; a region picked to edit takes glue's selection mode. A session saves and
    restores the viewer with its quicklook's point group and its observation's time master.
    """

    def apply_subset_state(self, subset_state, override_mode=None):
        session = self.session
        points = coordinator(session.data_collection)._owners
        if any(group in points for group in session.edit_subset_mode.edit_subset):
            session.command_stack.do(_NewSubset(data_collection=session.data_collection, subset_state=subset_state))
        else:
            super().apply_subset_state(subset_state, override_mode=override_mode)

    def apply_roi(self, roi, override_mode=None):
        state = self.state
        data = state.reference_data
        on_map = _role(data) == "raster" and _shown(state) == {data.ndim - 3, data.ndim - 2}
        on_frame = _role(data) == "sji" and _sji_frame(state) is not None and _placeable(data)
        if not (on_map or on_frame):
            return super().apply_roi(roi, override_mode=override_mode)
        self.redraw()  # as glue's own does, which clears the drawn region
        world = _outline_region(data, roi, state.x_att.axis, state.y_att.axis, state.slices)
        region = _RasterRoiSubsetState(state.x_att, state.y_att, roi, world)
        self.apply_subset_state(region, override_mode=override_mode)

    def __gluestate__(self, context):
        """glue's record of the viewer, with its quicklook's point group and its observation's time master."""
        rec = super().__gluestate__(context)
        collection, data = self.session.data_collection, self.state.reference_data
        coord = coordinator(collection)
        point = next((group for group, viewers in coord._owners.items() if self in viewers), None)
        master = coord.masters.get(observation_key(data)) if data is not None else None
        rec["solar_quicklook"] = {
            "point": context.id(point) if point in collection.subset_groups else None,
            "master": context.id(master) if master in collection else None,
        }
        return rec

    @classmethod
    def __setgluestate__(cls, rec, context):
        viewer = super().__setgluestate__(rec, context)
        saved = rec.get("solar_quicklook", {})
        viewer._solar_restored = [context.object(saved.get(key)) for key in ("point", "master")]
        return viewer

    def __setgluestate_callback__(self, context):
        """
        Register the restored viewer with the coordinator as `__gluestate__` saved it, once glue has put it in its tab:
        glue calls this after each object it restores until it passes.
        """
        app = self.session.application
        [tab] = [app.tab(i) for i, viewers in enumerate(app.viewers) if self in viewers]  # ValueError until then
        point, master = self._solar_restored
        coord = coordinator(self.session.data_collection)
        if master is not None:
            coord.set_master(master)
        if point is not None:
            coord.own(point, [self])
            _edit_in_tab(app, tab, point)


def _role(data):
    """
    'raster', 'sji', 'aia' or None, from the INSTRUME keyword: AIA cutouts and Hinode/SOT cubes load as slit-jaw cubes
    and follow the time as they do, without their quicklook panel, raster point or overlays.
    """
    instrument = str((getattr(data, "meta", None) or {}).get("INSTRUME", ""))
    return "aia" if instrument.startswith(("AIA", "SOT")) else {"SPEC": "raster", "SJI": "sji"}.get(instrument)


def _same_file(data, other):
    """
    Whether ``data`` and ``other`` are windows of one raster file, or of one stack of the same scans, which share their
    scans, steps or exposures and slit pixels: rasters of one observation, shaped alike but for wavelength, from the
    same DATE_OBS and the same raster files in the same order (the loader's ``meta['raster files']``). A dataset is a
    window of its own file.
    """
    if data is other:
        return data is not None
    return (
        _role(data) == _role(other) == "raster"
        and observation_key(data) == observation_key(other)
        and data.shape[:-1] == other.shape[:-1]
        and all(data.meta.get(key) == other.meta.get(key) for key in ("DATE_OBS", "raster files"))
    )


def _wavelengths(data):
    """The wavelength of each pixel along the spectral axis of ``data``, in Angstrom, and that axis."""
    [axis] = _spectral_axes(data)
    index = [0] * data.ndim
    index[axis] = slice(None)
    unit = u.Unit(data.coords.world_axis_units[data.ndim - 1 - axis])
    return (data[data.world_component_ids[axis], tuple(index)] * unit).to_value(u.AA), axis


def _window(data):
    """
    The name and TWAVE of the spectral window ``data`` holds.

    The window keywords of every raster window describe window 1, so this takes the TWAVEn that
    lies inside the data's own wavelength range. (None, None) if none does.
    """
    meta = data.meta
    wave, _ = _wavelengths(data)
    for n in range(1, int(meta.get("NWIN", 0) or 0) + 1):
        twave = meta.get(f"TWAVE{n}")
        if twave is not None and np.nanmin(wave) <= float(twave) <= np.nanmax(wave):
            return str(meta.get(f"TDESC{n}")), float(twave)
    return None, None


def _line_core(raster):
    """The wavelength pixel of ``raster`` nearest its window's TWAVE, or mid-window; never 0, a window edge."""
    wave, _ = _wavelengths(raster)
    _, twave = _window(raster)
    return int(np.nanargmin(np.abs(wave - twave))) if twave is not None else len(wave) // 2


def _is_sit_and_stare(data):
    meta = data.meta
    return float(meta.get("STEPS_AV", -1) or 0) == 0 and int(meta.get("NRASTERP", 0) or 0) == 1


def _pick_raster(rasters, window):
    """The raster to show: of the browser's window, else Mg II k, else the first; a stack before a scan."""
    windows = {id(data): _window(data)[0] for data in rasters}
    for name in (window, DEFAULT_WINDOW, windows[id(rasters[0])]):
        chosen = [data for data in rasters if name is not None and windows[id(data)] == name]
        if chosen:
            return next((data for data in chosen if data.ndim == 4), chosen[0])
    return rasters[0]


def _pick_windows(rasters, window, main=None):
    """
    The raster to show (`_pick_raster`) of ``window``, a window name or a list of them, ``main`` if among them, and of
    each other window of the list a dataset of the same file or stack (`_same_file`), in the order of ``rasters``.
    """
    names = [window] if isinstance(window, str) else list(window or ())
    named = [data for data in rasters if _window(data)[0] in names]
    raster = _pick_raster(named or rasters, main)
    others = {}
    for data in named:
        name = _window(data)[0]
        if name != _window(raster)[0] and _same_file(data, raster):
            others.setdefault(name, data)
    return raster, list(others.values())


def _link_windows(collection, raster, others):
    """
    Link the scan, step or exposure, and slit pixels of each of ``others`` to those of ``raster``, a window of the
    same file, with `~glue.core.link_helpers.LinkSame`, skipping pairs already linked.
    """
    linked = {frozenset((link.get_to_id(), *link.get_from_ids())) for link in collection.links}
    pairs = [(raster.pixel_component_ids[axis], data.pixel_component_ids[axis])
             for data in others for axis in range(raster.ndim - 1)]
    links = [LinkSame(*pair) for pair in pairs if frozenset(pair) not in linked]
    if links:  # glue rediscovers every dataset's links on each add_link, even an empty one
        collection.add_link(links)


def _sji_title(data):
    """'SJI 1400', or 'SJI 2796 (deconvolved)'."""
    title = str(data.meta.get("TDESC1") or data.label).replace("_", " ")
    return f"{title} (deconvolved)" if "_deconvolved" in data.label else title


def _footprint_limits(viewer, raster):
    """Zoom a slit-jaw viewer to the raster's field of view in its first frame, with a margin."""
    shape = raster.shape
    step_axis = raster.ndim - 3
    corners = []
    for step in (0, shape[step_axis] - 1):
        for slit in (0, shape[step_axis + 1] - 1):
            pixel = [0] * raster.ndim
            pixel[step_axis], pixel[step_axis + 1] = step, slit
            corners.append(_lon_lat(raster, pixel))
    lon, lat = (np.array([corner[i] for corner in corners], dtype=float) for i in (0, 1))
    x, y = _sji_pixels(viewer.state.reference_data, 0, lon, lat)
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return
    margin = max(10.0, 0.1 * max(np.ptp(x), np.ptp(y)))
    # limits at the axes' aspect, so that glue's equal aspect keeps them; a later resize keeps their
    # area, so it can crop the footprint
    box = viewer.axes.get_window_extent()
    ratio = box.height / box.width if box.width else 1.0
    width = max(np.ptp(x) + 2 * margin, (np.ptp(y) + 2 * margin) / ratio)
    x_mid, y_mid = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
    state = viewer.state
    with delay_callback(state, "x_min", "x_max", "y_min", "y_max"):
        state.x_min, state.x_max = x_mid - width / 2, x_mid + width / 2
        state.y_min, state.y_max = y_mid - width * ratio / 2, y_mid + width * ratio / 2


def _pick_sjis(sjis):
    """One slit-jaw cube per channel, the plain one before the deconvolved, and the ones left out."""
    chosen = {}
    for data in sorted(sjis, key=lambda data: "_deconvolved" in data.label):
        chosen.setdefault(str(data.meta.get("TDESC1")), data)
    shown = list(chosen.values())
    return shown, [data for data in sjis if data not in shown]


def _image(app, cls, data, x, y, slices, title, aspect):
    # a turn of the event loop before each viewer, user input aside, so that glue keeps drawing as the quicklook opens
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
    viewer = app.new_data_viewer(cls, data=data)
    state = viewer.state
    pixel = data.pixel_component_ids
    state.x_att = pixel[x]  # x before y: glue swaps the other axis when both would match
    state.y_att = pixel[y]
    state.slices = tuple(slices)
    state.aspect = aspect
    state.reset_limits()  # glue pads the limits of a new viewer
    state.title = title
    state.layers[0].stretch = _stretch(data)
    state.layers[0].percentile = PERCENTILE
    return viewer


def _stretch(data):
    """
    The default stretch of the band of ``data``, a raster window or a slit-jaw image (D43): log in the FUV, sqrt about
    Mg II k and h, linear for the other NUV windows and slit-jaw 2832, and for anything else.
    """
    twave = _window(data)[1] if _role(data) == "raster" else data.meta.get("TWAVE1") if _role(data) == "sji" else None
    if twave is None:
        return "linear"
    return "log" if float(twave) < 2000 else "sqrt" if abs(float(twave) - 2800) <= 10 else "linear"


def _raster_panels(app, raster, window, roles=("map", "spectrogram", "wavelength")):
    """
    The map, spectrogram and wavelength panels of the table in the plan, or those of ``roles``, with the point at the
    map centre.
    """
    _, spectral = _wavelengths(raster)
    wl0 = _line_core(raster)
    shape = raster.shape
    if raster.ndim == 4:  # scan, step, slit, wavelength
        point = (0, shape[1] // 2, shape[2] // 2, wl0)
        axes = {"map": (1, 2), "spectrogram": (3, 2), "wavelength": (3, 0)}
        names = {"map": "map", "spectrogram": "spectrogram", "wavelength": "λ–scan"}
    else:  # step or exposure, slit, wavelength
        point = (shape[0] // 2, shape[1] // 2, wl0)
        axes = {"map": (0, 1), "spectrogram": (2, 1), "wavelength": (2, 0)}
        if _is_sit_and_stare(raster):
            names = {"map": "slit vs time", "spectrogram": "spectrogram", "wavelength": "λ–time"}
        else:
            names = {"map": "map", "spectrogram": "spectrogram", "wavelength": "λ–step"}
    viewers = {
        role: _image(app, QuicklookImageViewer, raster, x, y, point, f"{window} {names[role]}", "auto")
        for role, (x, y) in axes.items()
        if role in roles
    }
    slices = [slice(i, i + 1) for i in point]
    slices[spectral] = slice(None)
    return viewers, PixelSubsetState(raster, slices)


@layer_artist_maker("IRIS: quicklook spectrum without the cube's own")
def hidden_cube_profile(viewer, data):
    """
    Add the raster to a quicklook's spectrum panel hidden, so glue never computes the mean spectrum of the
    whole cube, which the panel would only hide (0.4 s of opening a quicklook on 4000255147, a full read of
    lazily loaded data).
    """
    if getattr(viewer, "_solar_hidden", None) is not data:
        return None
    return viewer.get_data_layer_artist(data, ProfileLayerState(layer=data, viewer_state=viewer.state, visible=False))


def _profile(app, raster, window):
    """A Profile of the point's mean spectrum, with the raster itself hidden and no large-data prompt."""
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # as before each Image viewer
    viewer = app.new_data_viewer(ProfileViewer)
    viewer.state.title = f"{window} spectrum"
    viewer.state.function = "mean"
    # glue asks 'Add large data set?' above 1e8 elements, defaulting to Cancel; only this viewer skips it
    viewer.large_data_size = None
    viewer._solar_hidden = raster  # only the point's spectrum shows, not the whole cube's
    added = viewer.add_data(raster)
    viewer._solar_hidden = None
    if not added:
        return viewer, f"The spectrum panel could not add {raster.label}."
    viewer.state.x_att = raster.world_component_ids[_wavelengths(raster)[1]]
    viewer.axes.axhline(0, color="0.5", lw=0.8, zorder=0)
    return viewer, f"Spectrum of {raster.label} ({raster.size:.3g} elements)."


def quicklook(app, datasets, window=None, main=None):
    """
    Open the IRIS quicklook of one observation in a new tab.

    A raster (or a stack of scans) opens as a map, a spectrogram and a wavelength panel (wavelength
    against step, exposure or scan), each slit-jaw channel in its own viewer, and a spectrum panel
    showing the mean spectrum of the point. The point starts at the centre of the map, in a new
    subset group 'Point' that is the edit subset while the tab is shown, with the Pixel tool active
    on the map. A read-only 'Point' window below the panels gives the point's pixel, position, time,
    exposure, value and time sync in each dataset they show. Lines on the spectrogram, the wavelength
    panel and the spectrum panel mark the point, the map's wavelength and the time master's time, and
    a zoom on the spectrum panel is the wavelength panel's too (`_SpectralLines`). Clicks and keys
    wait until it is open.

    Each other window named in ``window`` adds the spectrum of the point and, on a sit-and-stare raster
    or a stack, its own wavelength panel (λ–time or λ–scan), to a row below. Its scan, step or exposure,
    and slit pixels are linked to the shown window's with `~glue.core.link_helpers.LinkSame` (once,
    however often the quicklook opens), so the point is the same pixel in every window. Its spectrum
    panel's 'Show this window's panels' makes it the main window (`_switch`).

    Parameters
    ----------
    app : `~glue_qt.app.GlueApplication`
    datasets : list of `~glue.core.data.Data`
        IRIS datasets of one observation. Those not yet in the data collection are added and linked.
    window : str or list of str, optional
        The spectral window to show, by its ``TDESC`` name. By default Mg II k 2796, else the first.
        Of several, ``main`` if named, else Mg II k 2796 if named, else the first, and the others of
        the same raster file or stack beside it.
    main : str, optional
        The main window, among ``window``: the one the map, spectrogram and wavelength panels show.

    Returns
    -------
    dict
        The viewers: ``map``, ``spectrogram``, ``wavelength``, ``spectrum`` (absent without a raster),
        ``sji``, a list, and ``windows``, a list of each other window's ``spectrum`` and any ``wavelength``.

    Raises
    ------
    ValueError
        For an observation with neither a raster nor a slit-jaw image.
    """
    rasters = [data for data in datasets if _role(data) == "raster"]
    shown = rasters or [data for data in datasets if _role(data) == "sji"]
    if not shown:
        raise ValueError(f"{datasets[0].label} has no raster or slit-jaw image for a quicklook")
    collection = app.data_collection
    new = [data for data in datasets if data not in collection]
    if new:  # one link update for all, where each append runs one
        collection.extend(new)
    keep_hpc_linked(collection)
    app.new_tab()
    tab = app.current_tab
    key = observation_key(shown[0])
    names = app.tab_names
    names[-1] = f"IRIS {key[0]}" if key else "IRIS"
    app.tab_names = names
    return _fill(app, tab, datasets, window, main)


def _fill(app, tab, datasets, window, main, group=None):
    """
    Open `quicklook`'s viewers of ``datasets`` in ``tab``, the current tab, with ``group`` as its point's group, or a
    new one.
    """
    rasters = [data for data in datasets if _role(data) == "raster"]
    sjis, offered = _pick_sjis([data for data in datasets if _role(data) == "sji"])
    collection = app.data_collection
    key = observation_key((rasters or sjis)[0])
    coordinator(collection)  # before the point, so it follows it

    viewers, notes = {"sji": [], "windows": []}, []
    if rasters:
        raster, others = _pick_windows(rasters, window, main)
        _link_windows(collection, raster, others)
        name = _window(raster)[0] or raster.label
        panels, point = _raster_panels(app, raster, name)
        viewers.update(panels)
        viewers["spectrum"], note = _profile(app, raster, name)
        notes.append(note)
        for other in others:
            name = _window(other)[0]
            # a scanning raster's steps are places, not times: no λ–t panel
            roles = ("wavelength",) if _time_axis(other) is not None else ()
            panels = _raster_panels(app, other, name, roles)[0]
            panels["spectrum"], note = _profile(app, other, name)
            panels["spectrum"].toolbar.tools["solar:main_window"].enabled = True  # 'Show this window's panels'
            viewers["windows"].append(panels)
            notes.append(note)
    for sji in sjis:
        frame = (0,) * sji.ndim
        viewers["sji"].append(
            _image(app, QuicklookImageViewer, sji, sji.ndim - 1, sji.ndim - 2, frame, _sji_title(sji), "equal")
        )
    notes += [f"{data.label} is loaded too: drag it onto a slit-jaw viewer to see it." for data in offered]

    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # and after the last (see _image)
    if rasters:
        if group is None:
            group = collection.new_subset_group(label="Point", subset_state=point)
        own = [viewers[role] for role in ("map", "spectrogram", "wavelength")] + viewers["sji"]
        lambda_t = [panels["wavelength"] for panels in viewers["windows"] if "wavelength" in panels]
        coordinator(collection).own(group, own + lambda_t)
        _edit_in_tab(app, tab, group)
        spectra = [viewers["spectrum"]] + [panels["spectrum"] for panels in viewers["windows"]]
        _show_point(app, group, own[:3] + lambda_t + spectra)
        for spectrum in spectra:
            _fit_spectrum(spectrum, group)
        _point_window(app, tab, group, key, own)
        _SpectralLines(coordinator(collection), group, key, own[:3], viewers["spectrum"], tab)
        for panels in viewers["windows"]:
            if "wavelength" in panels:
                _SpectralLines(coordinator(collection), group, key, [panels["wavelength"]], panels["spectrum"], tab)
    app.statusBar().showMessage(" ".join(notes))
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # let the tab take its final size
    _arrange(tab, viewers)
    # and the panels theirs, before the slit-jaw limits take the axes' aspect
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
    for viewer in viewers["sji"]:
        if rasters and _placeable(viewer.state.reference_data):
            _footprint_limits(viewer, raster)
    if rasters:
        tab.setActiveSubWindow(viewers["map"].parent())
        viewers["map"].toolbar.active_tool = "image:point_selection"
    tab._solar_quicklook = (datasets, window, viewers)  # for `_switch`
    return viewers


def _viewers(viewers):
    """Every viewer of `quicklook`'s ``viewers``."""
    roles = [viewers[role] for role in ("map", "spectrogram", "wavelength", "spectrum") if role in viewers]
    return roles + viewers["sji"] + [viewer for panels in viewers["windows"] for viewer in panels.values()]


# what a switch of the main window keeps of each Image panel's layer (`_switch`)
_COLOURS = ("cmap", "stretch", "percentile", "v_min", "v_max", "contrast", "bias")


def _switch(viewer):
    """
    Make the window of ``viewer``, a quicklook's spectrum panel of another window, the quicklook's main window: open the
    quicklook again in its tab, in place of its viewers, as `quicklook` opens it with that window as ``main``, with its
    point's group, the point at the same pixel of that window, the time master at the same frame, exposure, step or
    scan, and the colours of each Image panel that shows the same data on the same axes again. The links stay, as do
    the viewers added to the tab.
    """
    app = viewer.session.application
    tab, collection = viewer.parent().mdiArea(), app.data_collection
    coord = coordinator(collection)
    datasets, window, viewers = tab._solar_quicklook
    group, raster = app._solar_points[tab], viewer.state.reference_data
    master = coord._master(observation_key(raster))
    index, _ = coord._timing(master)
    colours = {}
    for panel in _viewers(viewers):
        state = panel.state
        layer = next((layer for layer in state.layers if layer.layer is state.reference_data), None)
        if isinstance(panel, ImageViewer) and layer is not None:
            colours[state.reference_data, state.x_att, state.y_att] = {att: getattr(layer, att) for att in _COLOURS}
        panel.close(warn=False)
        coord.unregister(panel)  # now rather than once glue-qt deletes it
    for sub in tab.subWindowList():
        if isinstance(sub.widget(), _PointWindow):
            sub.close()
    for lines in tab.findChildren(_SpectralLines):
        coord.remove_listener(lines._synced)
        lines.deleteLater()
    point = group.subset_state
    group.subset_state = SubsetState()  # while the panels open: each one's sliders would move it, and what follows it
    viewers = _fill(app, tab, [data for data in datasets if data in collection], window, _window(raster)[0], group)
    if isinstance(point, PixelSubsetState) and _same_file(point.reference_data, raster):  # wavelength is last
        point = PixelSubsetState(raster, [*point.slices[:-1], slice(None)])
    group.subset_state = point
    for panel in _viewers(viewers):
        state = panel.state
        if isinstance(panel, ImageViewer):
            layer = next(layer for layer in state.layers if layer.layer is state.reference_data)
            layer.update_from_dict(colours.get((state.reference_data, state.x_att, state.y_att), {}))
    now = coord._master(observation_key(raster))
    if _same_file(now, master):  # the same, or another window of its file
        coord.move_master(now, index)
    return viewers


def _edit_in_tab(app, tab, group):
    """Make ``group`` the edit subset now and whenever its tab is shown again."""
    points = getattr(app, "_solar_points", None)
    if points is None:
        points = app._solar_points = weakref.WeakKeyDictionary()

        def follow(index):
            group = points.get(app.tab_widget.widget(index))
            if group is not None and group in app.data_collection.subset_groups:
                app.session.edit_subset_mode.edit_subset = [group]
                coordinator(app.data_collection).follow(group)

        app.tab_widget.currentChanged.connect(follow)
    points[tab] = group
    app.session.edit_subset_mode.edit_subset = [group]
    coordinator(app.data_collection).follow(group)


def _show(viewer, group, shown):
    """
    Give ``viewer`` the layers of ``group`` for the datasets it shows, or remove them all.

    Removed rather than hidden: glue still updates and redraws a hidden layer whenever its subset changes.
    """
    if shown:
        for subset in group.subsets:
            if any(layer.layer is subset.data for layer in viewer.state.layers):
                viewer.add_subset(subset)
        return
    for layer in list(viewer.state.layers):
        if getattr(layer.layer, "group", None) is group:
            viewer.remove_subset(layer.layer)


def _show_point(app, group, own):
    """
    Show the point only in its quicklook's raster and spectrum panels, and no other subset there.

    Elsewhere glue 1.27.0 would draw its crosshair on a dataset it does not belong to, and an
    earlier quicklook's point would show in this one's panels. Quicklook points are removed where
    they must not show, as they move at every click; other subsets are only hidden.
    """
    points = coordinator(app.data_collection)._owners  # every quicklook's point
    for viewer in (viewer for tab in app.viewers for viewer in tab):
        for layer in list(viewer.state.layers):
            other = getattr(layer.layer, "group", None)
            if other is None or (other is group) == (viewer in own):
                continue
            if other in points:
                viewer.remove_subset(layer.layer)  # see _show
            else:
                layer.visible = False


# glue-qt computes the profile of a layer above this size on a worker thread
_THREADED_SIZE = 1e7


def _fit(viewer):
    """Fit the spectrum panel's y range to its profiles and the y = 0 line."""
    state = viewer.state
    state.reset_limits()
    state.y_min, state.y_max = min(state.y_min, 0), max(state.y_max, 0)


class _FitOnceComputed(HubListener):
    """Fit a spectrum panel once glue has computed the point's spectrum on a worker thread."""

    def __init__(self, viewer, subset):
        self.viewer, self.subset = viewer, subset
        subset.data.hub.subscribe(self, ComputationEndedMessage, handler=self._ended, filter=self._is_point)

    def _is_point(self, message):
        return message.sender in self.viewer.layers and message.sender.state.layer is self.subset

    def _ended(self, message):
        self.subset.data.hub.unsubscribe(self, ComputationEndedMessage)
        _fit(self.viewer)


def _fit_spectrum(viewer, group):
    """Fit the spectrum panel to the point's spectrum, now or when glue's worker thread has computed it."""
    data = viewer.state.reference_data
    if data is None:
        return  # the panel could not add the raster
    _fit(viewer)
    if data.size > _THREADED_SIZE:
        [subset] = [subset for subset in group.subsets if subset.data is data]
        viewer._solar_fit = _FitOnceComputed(viewer, subset)  # the hub holds its listeners weakly


class _Cut(HubListener):
    """
    Keep a cut's subset group (`_cut`) along array axis ``axis`` at the point's other axes but wavelength, and on the
    wavelength or band its map shows: a Collapse, a Wavelength band or the slider's wavelength. While the point is no
    Pixel selection on the map's file, or the map shows other data, it stays where it was.
    """

    def __init__(self, group, point, band, axis):
        self.group, self.point, self.band, self.axis, self.data = group, point, band, axis, band.state.reference_data
        band.state.add_callback("slices", self.refresh)
        self.data.hub.subscribe(self, SubsetUpdateMessage, handler=self.refresh, filter=self._moved)
        self.refresh()

    def _moved(self, message):
        return getattr(message.subset, "group", None) is self.point and message.subset.data is self.data

    def refresh(self, *_):
        point, state, data = self.point.subset_state, self.band.state, self.data
        if not isinstance(point, PixelSubsetState) or not _same_file(point.reference_data, data):
            return
        if state.reference_data is not data or len(state.slices) != data.ndim:
            return
        slices = list(point.slices)
        if any(s.start is None for i, s in enumerate(slices[:-1]) if i != self.axis):
            return  # a click before the coordinator gives it the axes it was not clicked on (`Coordinator._pin`)
        band = getattr(state.slices[-1], "slice", state.slices[-1])  # IRIS wavelengths are the last axis
        slices[self.axis], slices[-1] = slice(None), band if isinstance(band, slice) else slice(band, band + 1)
        if slices != getattr(self.group.subset_state, "slices", None):
            self.group.subset_state = SliceSubsetState(data, slices)


def _cut_map(viewer):
    """Whether ``viewer``, an Image viewer, shows a raster with a wavelength slider."""
    data = viewer.state.reference_data
    return _role(data) == "raster" and not _spectral_axes(data) & _shown(viewer.state)


def _curve_map(viewer):
    """Whether ``viewer``, an Image viewer, shows a sit-and-stare raster or a stack with a wavelength slider."""
    return _cut_map(viewer) and _time_axis(viewer.state.reference_data) == 0


def _cut(viewer, axis, label):
    """
    Open a Profile of the cut through the point along array axis ``axis``: the mean, NaN left out, over the
    wavelength or band that ``viewer``, an Image viewer of a raster with a wavelength slider, shows, at the point's
    other axes, against ``axis``. The cut is the new subset group ``label``, a `~glue.core.subset.SliceSubsetState`
    that follows the point and the band (`_Cut`), shown in that Profile and removed from the other viewers open then.
    """
    app, data = viewer.session.application, viewer.state.reference_data
    coord = coordinator(app.data_collection)
    if not _cut_map(viewer):
        raise ValueError("Choose it on the map of a raster, whose wavelength or band it averages.")
    if coord.point is None or not _same_file(coord.point.reference_data, data):
        raise ValueError(f"Select a point on {data.label} first.")
    mode = app.session.edit_subset_mode
    edit = mode.edit_subset
    group = app.data_collection.new_subset_group(label=label)
    mode.edit_subset = edit  # glue-qt makes a new group the edit subset
    # glue 1.27.0 profiles a slice subset with only its band's samples, which a spectrum panel cannot draw
    for viewers in app.viewers:
        for other in viewers:
            _show(other, group, False)
    group._solar_cut = _Cut(group, coord.group, viewer, axis)  # until the group is deleted
    profile = app.new_data_viewer(ProfileViewer)
    profile.state.function = "mean"
    profile.add_subset(next(subset for subset in group.subsets if subset.data is data))
    profile.state.x_att = data.pixel_component_ids[axis]
    profile.state.title = f"{_window(data)[0] or data.label} {label.lower()}"
    _fit_spectrum(profile, group)
    return profile


def _light_curve(viewer):
    """
    Open the light curve at the point (`_cut` along exposure or scan, 'Light curve') on ``viewer``, the map of a
    sit-and-stare raster or a stack.
    """
    if not _curve_map(viewer):
        raise ValueError(
            "Choose it on the map of a sit-and-stare raster or a stack, whose wavelength or band it averages."
        )
    return _cut(viewer, 0, "Light curve")


def _curve(source, raster, pixel, wavelength):
    """
    The times and values of ``source`` at ``pixel``, a pixel of ``raster`` but its wavelength: a raster window's along
    its first axis at the pixel's slit position, and a stack's step, and at wavelength pixel ``wavelength``; a slit-jaw
    image's in each frame at the place of the raster's pixel at the exposure, or a stack's scan at that step, nearest
    the frame's time, placed with the frame's own pointing, NaN past half the raster's cadence (D7) or off the frame. A
    scanning raster's pixel is one place at every frame.
    """
    main = source.main_components[0]
    if _role(source) == "raster":
        view = (slice(None), *pixel[1:], wavelength)
        return source[source.id["Time"], view], source[main, view]
    frames = np.arange(source.shape[0])
    times, lead, match = _times(source, None), list(pixel), True
    if _time_axis(raster) == 0:
        exposures = _times(raster, pixel[1] if raster.ndim == 4 else None)
        lead[0], offset = nearest(times, exposures)
        match = abs(offset) <= _half_cadence(exposures)  # NaT, a gap, never is
    lon, lat = _lon_lat(raster, [np.broadcast_to(index, frames.shape) for index in (*lead, 0)])
    x, y = (np.round(xy) for xy in _sji_pixels(source, frames, lon, lat))
    inside = match & (0 <= y) & (y < source.shape[1]) & (0 <= x) & (x < source.shape[2])  # NaN never is
    values = np.full(frames.shape, np.nan)
    values[inside] = source[main, (frames[inside], y[inside].astype(int), x[inside].astype(int))]
    return times, values


class _PointCurves(QObject):
    """
    Keep the light curves at the point (`_point_curves`) at the point of ``group`` while it is a Pixel selection on
    ``raster``'s file: a moment after the point moves to another slit position, or a stack's step, or a scanning
    raster's step, so that a drag or playback does not wait for them. They stop once they leave the data collection.
    """

    def __init__(self, coordinator, group, raster):
        super().__init__()
        self.coordinator, self.group, self.raster = coordinator, group, raster
        self.curves, self.pixel = [], None  # (curve, its dataset, its wavelength pixel), and the pixel they show
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.refresh)

    def point(self):
        """The point's pixel on the raster's file, its wavelength left out and, along time, 0: what `_curve` takes."""
        state = self.group.subset_state
        if not isinstance(state, PixelSubsetState) or not _same_file(state.reference_data, self.raster):
            return None
        pixel = tuple(s.start for s in state.slices[:-1])  # IRIS wavelengths are the last axis
        if None in pixel:
            return None  # a click before the coordinator gives it the axes it was not clicked on (`Coordinator._pin`)
        return (0, *pixel[1:]) if _time_axis(self.raster) == 0 else pixel

    def _synced(self, *_):
        self.curves = [entry for entry in self.curves if entry[0] in self.coordinator.data_collection]
        if not self.curves:
            self.coordinator.remove_listener(self._synced)
        elif self.point() not in (None, self.pixel):
            self._timer.start()

    def refresh(self):
        pixel = self.point()
        if pixel in (None, self.pixel):
            return
        self.pixel = pixel
        for curve, source, wavelength in self.curves:
            times, values = _curve(source, self.raster, pixel, wavelength)
            curve.update_components({curve.id["Time"]: times, curve.id["Value"]: values})


def _point_curves(viewer):
    """
    Add the light curves at the point, a raster pixel, as 1-D datasets of ``Time`` and ``Value`` (`_curve`), and plot
    them against time in a new Scatter viewer: one of each window of the point's raster file with exposures or scans,
    at the wavelength the map shows or else nearest its TWAVE, and one of each slit-jaw channel of its observation.
    Each takes its dataset's OBSID and STARTOBS, so that the time master's exposure marks them (`Coordinator._mark`),
    and the first's ``Time`` and ``Value`` are the others' through `~glue.core.link_helpers.LinkSame`. They follow
    the point (`_PointCurves`); ``viewer`` is any Image viewer of the data collection.
    """
    app = viewer.session.application
    collection = app.data_collection
    coord = coordinator(collection)
    raster = getattr(coord.point, "reference_data", None)
    follower = _PointCurves(coord, coord.group, raster)
    pixel = follower.point() if _role(raster) == "raster" else None
    if pixel is None:
        raise ValueError("Select a point on a raster first.")
    key = observation_key(raster)
    sources = [data for data in collection if _same_file(data, raster) and _time_axis(data) == 0]
    sjis = [data for data in collection if _role(data) == "sji" and observation_key(data) == key and _placeable(data)]
    sources += _pick_sjis(sjis)[0]
    for i, source in enumerate(sources):
        if _role(source) == "raster":
            [axis] = _spectral_axes(source)
            wavelength = coord._slider(source, axis, _line_core(source))
            label = f"{_window(source)[0] or source.label} {_wavelengths(source)[0][wavelength]:.2f} Å light curve"
        else:
            wavelength, label = None, f"{_sji_title(source)} light curve"
        times, values = _curve(source, raster, pixel, wavelength)
        curve = Data(label=label, Time=times, Value=values)
        curve.get_component("Value").units = source.get_component(source.main_components[0]).units
        curve.meta = {name: source.meta[name] for name in ("OBSID", "STARTOBS")}
        curve.style.color = to_hex(f"C{i % 10}")  # glue gives every dataset the same grey
        follower.curves.append((curve, source, wavelength))
    follower.pixel = pixel
    if not follower.curves:
        raise ValueError(f"{raster.label} has no exposures or scans, and its observation no slit-jaw image loaded.")
    curves = [curve for curve, *_ in follower.curves]
    mode = app.session.edit_subset_mode
    edit = mode.edit_subset
    collection.extend(curves)
    links = [LinkSame(curves[0].id[name], curve.id[name]) for curve in curves[1:] for name in ("Time", "Value")]
    if links:
        collection.add_link(links)
    plot = app.new_data_viewer(ScatterViewer, data=curves[0])
    plot.state.x_att, plot.state.y_att = curves[0].id["Time"], curves[0].id["Value"]  # before the others join
    for curve in curves[1:]:
        plot.add_data(curve)
    mode.edit_subset = edit  # glue-qt makes the last subset group the edit subset as data are added
    plot.state.title = "Light curves at the point"
    for layer in plot.state.layers:
        if isinstance(layer.layer, Data):
            layer.markers_visible, layer.line_visible = False, True
    for group in coord._owners:
        _show(plot, group, False)  # the quicklooks' points, which move at every click (`_show_point`)
    coord.add_listener(follower._synced)  # which keeps it
    coord._timer.start()  # the time master's exposure, at once
    return plot


# the raster panels' lines, the last on top: the point's thin, in the colour of glue's crosshair, the others as a
# slit-jaw image's slit
_LINES = {
    "wavelength": dict(color="white", lw=0.8, ls="--"),
    "time": dict(color="white", lw=0.8, ls=":"),
    "point": dict(color="#d32d26", lw=0.8),
}


def _segments(at, ends):
    """Lines at each of ``at``, from ``ends[0]`` to ``ends[1]`` across, as one artist's positions along and across."""
    along = np.repeat(np.asarray(at, dtype=float), 3)
    along[2::3] = np.nan  # between two lines
    return along, np.tile([*ends, np.nan], len(along) // 3)


def _across(state, axis, at):
    """Lines across the image of an Image viewer's ``state`` at ``at`` along its shown array axis ``axis``, as x, y."""
    shown = [state.x_att.axis, state.y_att.axis]
    along, across = _segments(at, (-0.5, state.reference_data.shape[shown[shown.index(axis) - 1]] - 0.5))
    return (along, across) if axis == shown[0] else (across, along)


def _place(artist, xy):
    """Draw ``artist`` at ``xy``, or hide it for None; whether what it shows changed."""
    before = artist.get_xydata() if artist.get_visible() else None
    if xy is not None:
        artist.set_data(*xy)
    artist.set_visible(xy is not None)
    if before is None or xy is None:
        return (before is None) != (xy is None)
    return not np.array_equal(before, artist.get_xydata(), equal_nan=True)


class _SpectralLines(QObject):
    """
    A quicklook's lines on its raster and spectrum panels, and its spectrum panel's wavelength range on the wavelength
    panel.

    A raster panel showing wavelength against another axis has a thin red line at the point there: its slit on the
    spectrogram, its step, exposure or scan on the wavelength panel. One showing wavelength against step, exposure or
    scan, the wavelength panel, also has a dashed white line at the wavelength of each raster panel with a wavelength
    slider, the map, and a dotted white line at the step, exposure or scan nearest the time master's time, hidden when
    none is within half its cadence. The spectrum panel has a dashed grey line at each of those wavelengths, in its x
    unit, while its x axis is the raster's wavelength or wavelength pixel; whenever its x range changes, the wavelength
    panel takes it. The lines follow the point, the time master, the sliders, axis changes and the x unit, and are
    plain matplotlib lines: 'Save plot' shows them, and sessions and Python scripts leave them out.
    """

    def __init__(self, coordinator, group, key, panels, spectrum, tab):
        super().__init__(tab)  # kept, and deleted, with the tab
        self.coordinator, self.group, self.key, self.panels, self.spectrum = coordinator, group, key, panels, spectrum
        self.data = panels[0].state.reference_data
        [self.axis] = _spectral_axes(self.data)
        self.lines = {
            viewer: {
                name: viewer.axes.add_line(Line2D([], [], gid=f"solar:{name}", zorder=99, visible=False, **style))
                for name, style in _LINES.items()
            }
            for viewer in panels
        }
        axes = spectrum.axes
        self.marks = axes.add_line(Line2D([], [], gid="solar:wavelength", color="0.5", lw=0.8, ls="--", visible=False))
        self.marks.set_transform(axes.get_xaxis_transform())  # from bottom to top
        coordinator.add_listener(self._synced)
        self.destroyed.connect(partial(coordinator.remove_listener, self._synced))  # with its tab
        for viewer in panels:
            for prop in ("reference_data", "x_att", "y_att", "slices"):
                # after the coordinator's own, which moves the point: the lines move before glue redraws the panel
                viewer.state.add_callback(prop, self.refresh, priority=-1)
        for prop in ("reference_data", "x_att", "x_display_unit"):
            spectrum.state.add_callback(prop, self.refresh)
        for prop in ("x_min", "x_max"):
            spectrum.state.add_callback(prop, self._copy_range)
        self.refresh()

    def _synced(self, key, time, exposure):
        if key == self.key:
            self.refresh()

    def _raster_panels(self):
        """The open panels showing the raster on two axes."""
        return [
            viewer for viewer in self.panels
            if not viewer._closed and viewer.state.reference_data is self.data and len(_shown(viewer.state)) == 2
        ]

    def _spectrum_x(self):
        """The spectrum panel's x at each wavelength of the raster, in the data's unit, or None for another x axis."""
        state, data = self.spectrum.state, self.data
        if self.spectrum._closed or state.reference_data is not data:
            return None
        if state.x_att_pixel is not data.pixel_component_ids[self.axis]:
            return None
        view = [0] * data.ndim
        view[self.axis] = slice(None)
        return data[state.x_att, tuple(view)]  # as glue's profile takes its x

    def _time_index(self):
        """The raster's step, exposure or scan nearest the time master's time, or None beyond half its cadence."""
        # the master's time now, as the coming time sync takes it: a step moves the lines in glue's own redraw
        when = self.coordinator.master_time(self.key)
        if when is None:
            return None
        times = _times(self.data, self.coordinator._timing(self.data)[1])
        [index], [offset] = nearest([when], times)
        return int(index) if abs(offset) <= _half_cadence(times) else None  # NaT, a gap, is never within

    def refresh(self, *_):
        """Move the lines (see the class)."""
        panels, axis = self._raster_panels(), self.axis
        wavelengths = sorted({
            int(getattr(viewer.state.slices[axis], "center", viewer.state.slices[axis]))
            for viewer in panels if axis not in _shown(viewer.state)
        })
        point = self.group.subset_state if self.group in self.coordinator.data_collection.subset_groups else None
        if not isinstance(point, PixelSubsetState) or not _same_file(point.reference_data, self.data):
            point = None
        time = self._time_index()
        for viewer, lines in self.lines.items():
            if viewer._closed:
                continue
            state, xy = viewer.state, dict.fromkeys(lines)  # None: hidden
            if viewer in panels and axis in _shown(state):
                [other] = _shown(state) - {axis}
                if point is not None and point.slices[other].start is not None:
                    xy["point"] = _across(state, other, [point.slices[other].start])
                if other == 0 and wavelengths:
                    xy["wavelength"] = _across(state, axis, wavelengths)
                if other == 0 and time is not None:
                    xy["time"] = _across(state, other, [time])
            if any([_place(lines[name], xy[name]) for name in lines]):  # every line, not up to the first changed
                viewer.figure.canvas.draw_idle()
        values, state = self._spectrum_x(), self.spectrum.state
        marks = None
        if values is not None and wavelengths:
            x = UnitConverter().to_unit(self.data, state.x_att, values[wavelengths], state.x_display_unit)
            marks = _segments(x, (0, 1))
        if _place(self.marks, marks) and not self.spectrum._closed:
            self.spectrum.figure.canvas.draw_idle()

    def _copy_range(self, *_):
        """Give each open panel showing wavelength against step, exposure or scan the spectrum panel's x range."""
        values, state = self._spectrum_x(), self.spectrum.state
        if values is None or None in (state.x_min, state.x_max):
            return
        ends = np.array([state.x_min, state.x_max])
        ends = UnitConverter().to_native(self.data, state.x_att, ends, state.x_display_unit)
        ends = (ends - values[0]) / (values[-1] - values[0]) * (len(values) - 1)  # IRIS wavelengths are linear in pixel
        for viewer in self._raster_panels():
            panel = viewer.state
            if _shown(panel) == {self.axis, 0}:
                xy = "x" if panel.x_att.axis == self.axis else "y"
                with delay_callback(panel, f"{xy}_min", f"{xy}_max"):
                    setattr(panel, f"{xy}_min", ends[0])
                    setattr(panel, f"{xy}_max", ends[1])


def _arrange(tab, viewers):
    """
    Raster panels in a top row, slit-jaw viewers and the spectrum in a second row, each other window's wavelength
    panel and spectrum in rows of four below, at least 400 pixels tall each and 800 together, and the Point window
    below them, as tall as its rows.
    """
    others = [viewer for panels in viewers["windows"] for viewer in panels.values()]
    rows = [
        [viewers[role] for role in ("map", "spectrogram", "wavelength") if role in viewers],
        viewers["sji"] + [viewers[role] for role in ("spectrum",) if role in viewers],
        *(others[i : i + 4] for i in range(0, len(others), 4)),
    ]
    rows = [row for row in rows if row]
    size = tab.viewport().size()
    least = 400 * max(len(rows), 2)
    width, height = max(size.width(), 1200), max(size.height(), least)
    for window in tab.subWindowList():
        if isinstance(window.widget(), _PointWindow):
            height = max(size.height() - window.sizeHint().height(), least)
            window.setGeometry(0, height, width, window.sizeHint().height())
    for r, row in enumerate(rows):
        for c, viewer in enumerate(row):
            viewer.move(c * width // len(row), r * height // len(rows))
            viewer.viewer_size = (width // len(row), height // len(rows))


def _time_text(time):
    """A time as the readouts give it: in UTC to the millisecond."""
    return f"{np.datetime_as_string(time, unit='ms')} UTC"


def _seconds_text(seconds):
    """An exposure time as the readouts give it: in seconds to 4 significant figures."""
    return f"{seconds:.4g} s"


def _world_text(value):
    """A helioprojective angle or a wavelength as the readouts give it: in arcsec to 0.01", or in Å to 0.001 Å."""
    if value.unit.physical_type == "angle":
        return f'{value.to_value(u.arcsec):.2f}"'
    return f"{value.to_value(u.AA):.3f} Å"


def _value_text(value):
    """A data value as the readouts give it: to 6 significant figures, or as it is for a datetime or a string."""
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)


def _sync_text(status):
    """A `Coordinator.time_status` as the Frame time readout gives it."""
    kind, value = status
    if kind == "master":
        return "time master" + (f", step {value}" if value is not None else "")
    if kind == "match":
        return f"Δt {value / np.timedelta64(1, 's'):+.1f} s"
    # a master in a gap of data regridded on time has no time, so no offset
    return "NO MATCH" + ("" if np.isnat(value) else f" Δt = {value / np.timedelta64(1, 's'):+.1f} s")


_POINT_COLUMNS = ("Dataset", "Pixel", "Position", "Time", "Exposure", "Value", "Time sync")
# the Position column's coordinates, in this order whatever the dataset's own
_POSITION = ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat", "em.wl")


class _PointWindow(QTableWidget):
    """
    A quicklook's read-only 'Point' window: a row for each dataset its Image panels show, with the point's pixel in
    that dataset, the pixel's helioprojective position and wavelength, time, exposure time and value (of the panel's
    displayed component), and the dataset's time sync, as the readouts give them.

    On the point's own dataset, the axes the point leaves free, the wavelength, are those of the first panel that does
    not show them, the map; on a slit-jaw image the point of a raster is placed in the displayed frame, as its cross
    is (`Coordinator.point_on`). A dataset of another observation shows 'no match'. The window refreshes once for
    each change of the point, the time sync or its panels' sliders or layers, only while its tab is shown.
    """

    def __init__(self, coordinator, group, key, viewers):
        super().__init__(0, len(_POINT_COLUMNS))
        self.coordinator, self.group, self.key, self.viewers = coordinator, group, key, viewers
        self.setHorizontalHeaderLabels(_POINT_COLUMNS)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # the width left, labels elided
        self.setTextElideMode(Qt.ElideMiddle)  # on one line, keeping their ends, such as '-scan-0' or '-stack'
        self.setWordWrap(False)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        # a click or a slider step changes several panels, then syncs the time: one refresh for all
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self.refresh)
        coordinator.add_listener(self._schedule)
        for viewer in viewers:
            for prop in self._PROPS:
                # after the coordinator's own, which may start its sync
                viewer.state.add_callback(prop, self._schedule, priority=-1)
        # closed alone or with its tab; a partial, which Qt keeps, as it would not a function
        self.destroyed.connect(partial(self._detach, coordinator, viewers, self._schedule))

    _PROPS = ("reference_data", "x_att", "y_att", "slices", "layers")  # layers: such as the shown component

    @staticmethod
    def _detach(coordinator, viewers, schedule):
        """Stop ``schedule`` listening to the coordinator and the viewers, which may stay open."""
        coordinator.remove_listener(schedule)
        for viewer in viewers:
            for prop in _PointWindow._PROPS:
                viewer.state.remove_callback(prop, schedule)

    def _schedule(self, *_):
        # not in a hidden tab, nor before the coordinator's pending sync, which moves the panels: both call this again
        if self.isVisibleTo(self.window()) and not self.coordinator._timer.isActive():
            self._timer.start()

    def refresh(self):
        """Fill the rows (see the class)."""
        point = self.coordinator.point if self.coordinator.group is self.group else None
        shows = {}  # each dataset the open panels show, and those panels
        for viewer in self.viewers:
            if viewer in self.coordinator._viewers and viewer.state.reference_data is not None:
                shows.setdefault(viewer.state.reference_data, []).append(viewer)
        self.setRowCount(len(shows))
        for row, (data, viewers) in enumerate(shows.items()):
            for column, text in enumerate([data.label, *self._cells(point, data, viewers)]):
                self.setItem(row, column, QTableWidgetItem(text))

    def _cells(self, point, data, viewers):
        """The point's pixel, position, time, exposure and value in ``data``, and its time sync."""
        if observation_key(data) != self.key:
            return ["no match", "", "", "", "", ""]
        viewer = next((v for v in viewers if not _spectral_axes(data) & _shown(v.state)), viewers[0])
        status = self.coordinator.time_status(viewer)
        sync = "" if status is None else _sync_text(status)
        pixel = None if point is None else self._pixel(point, data, viewer)
        if pixel is None:
            return ["", "", "", "", "", sync]
        if not all(0 <= index < n for index, n in zip(pixel, data.shape)):
            return ["outside SJI FOV", "", "", "", "", sync]
        if _role(data) == "sji":
            names = ("frame", "y", "x")
        elif data.ndim == 3 and _is_sit_and_stare(data):
            names = ("exposure", "slit", "λ")
        else:
            names = ("scan", "step", "slit", "λ")[-data.ndim :]
        position = []
        if data.coords is not None:  # a slit-jaw image without coordinates has no position
            world = data.coords.pixel_to_world_values(*pixel[::-1])
            units = [u.Unit(unit) for unit in data.coords.world_axis_units]
            types = list(data.coords.world_axis_physical_types)
            position = [_world_text(world[types.index(t)] * units[types.index(t)]) for t in _POSITION if t in types]
        time, exposure = data.find_component_id("Time"), data.find_component_id("Exposure time")
        layer = next((layer for layer in viewer.state.layers if layer.layer is data), None)
        return [
            ", ".join(f"{name} {index}" for name, index in zip(names, pixel)),
            " ".join(position),
            "" if time is None else _time_text(data[time, pixel]),
            "" if exposure is None else _seconds_text(data[exposure, pixel]),
            "" if layer is None else _value_text(data[layer.attribute, pixel]),
            sync,
        ]

    def _pixel(self, point, data, viewer):
        """The point's pixel in ``data``, shown by ``viewer`` (see the class), or None."""
        slices = viewer.state.slices
        if len(slices) != data.ndim:
            return None  # mid-way through an axis change
        if _same_file(point.reference_data, data):
            return tuple(
                s.start if s.start is not None else int(getattr(index, "center", index))
                for s, index in zip(point.slices, slices)
            )
        where = self.coordinator.point_on(viewer)
        return None if where is None else (_sji_frame(viewer.state), round(where[1]), round(where[0]))


def _point_window(app, tab, group, key, viewers):
    """Add the Point window (`_PointWindow`) of the quicklook of observation ``key`` to its tab, filled."""
    window = _PointWindow(coordinator(app.data_collection), group, key, viewers)
    sub = QMdiSubWindow()
    sub.setWidget(window)
    sub.setAttribute(Qt.WA_DeleteOnClose)  # with its tab too, as glue closes every window of a tab it closes
    sub.setWindowTitle("Point")
    tab.addSubWindow(sub)
    sub.show()
    window.refresh()  # its rows, before the quicklook makes it as tall as they are
