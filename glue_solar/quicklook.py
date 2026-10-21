"""
The IRIS quicklook: a preset of glue viewers for one observation, kept on one selected point; and the SST quicklook, of
one CRISP or CHROMIS cube.
"""

import sys
import weakref
from contextlib import contextmanager
from functools import partial
from itertools import pairwise
from typing import NamedTuple

import numpy as np
from echo import delay_callback
from glue.config import layer_artist_maker, session_patch
from glue.core import Data, Subset
from glue.core.command import Command
from glue.core.hub import HubListener
from glue.core.link_helpers import LinkSame
from glue.core.link_manager import is_equivalent_cid
from glue.core.message import (
    ComputationEndedMessage,
    DataCollectionAddMessage,
    DataCollectionDeleteMessage,
    EditSubsetMessage,
    SubsetCreateMessage,
    SubsetDeleteMessage,
    SubsetUpdateMessage,
)
from glue.core.roi import PolygonalROI
from glue.core.subset import RangeSubsetState, RoiSubsetState, SliceSubsetState, SubsetState
from glue.core.units import UnitConverter
from glue.utils import compute_statistic
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
from qtpy.QtCore import QCoreApplication, QEvent, QEventLoop, QObject, QSize, Qt, QTimer
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QHeaderView,
    QMdiSubWindow,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
)

import astropy.units as u

from glue_solar.sources.loaders.iris import _HPC, keep_hpc_linked
from glue_solar.sources.loaders.scan import _observation

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
# The subset group of the exposure that leads the time, on the light curves (`Coordinator._mark`); sessions from before
# D90 name it 'Master exposure'
MARK = "Current exposure"


def observation_key(data):
    """
    The ``(OBSID, STARTOBS)`` pair that identifies the IRIS observation ``data`` belongs to, or None.

    The OBSID alone names an observing program, which runs many times, so both are needed. An SST cube's is that of the
    IRIS observation it is linked to (`~glue_solar.sources.loaders.iris.link_hpc`), else the one it shares with the SST
    cubes whose scan times overlap, or lie within a cadence of, its own (`Coordinator`), or before its collection has a
    coordinator ``('SST', DATE-OBS)``.
    """
    meta = getattr(data, "meta", None) or {}
    obsid, start = meta.get("OBSID"), meta.get("STARTOBS")
    if _role(data) == "sst":
        obsid, start = (
            meta.get("IRIS observation") or vars(data).get("_solar_time_key") or ("SST", meta.get("DATE-OBS"))
        )
    if obsid is None or start is None:
        return None
    try:
        start = np.datetime64(str(start), "ns")
    except ValueError:
        return None
    return None if np.isnat(start) else (_observation(obsid, start)[0], start)


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
    return tuple(np.asarray(world[types.index(kind)]) for kind in _HPC)


def _placeable(data):
    """Whether helioprojective positions can be placed in ``data``'s frames through its coordinates."""
    types = getattr(data.coords, "world_axis_physical_types", None) or ()
    return {*_HPC, "time"} <= set(types)


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
    The axis along which ``data`` steps through time (frames, exposures or scans), or None for a scanning raster, whose
    steps are places on the Sun.
    """
    role = _role(data)
    if role in ("sji", "aia", "sst") or (role == "raster" and (data.ndim == 4 or _is_sit_and_stare(data))):
        return 0
    return None


def _timed(data):
    """Whether ``data`` takes part in time sync: an IRIS dataset, aligned AIA cutout or SST cube with times."""
    return _role(data) in ("raster", "sji", "aia", "sst") and data.find_component_id("Time") is not None


def _times(data, step):
    """
    The 1-D times of ``data``: per frame, exposure or step, per scan at raster step ``step`` of a stack, or per scan of
    an SST cube at its line core, as `~glue_solar.sources.loaders.iris.link_hpc` times them.
    """
    index = [0] * data.ndim
    index[0] = slice(None)
    if _role(data) == "sst":
        index[-3] = data.coords.core  # its tuning (`glue_solar.sources.sst.sst_data`)
    elif data.ndim == 4:
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
    """The frame a slit-jaw viewer shows, a collapse's center, or None while it displays the frame axis."""
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
    `~glue.viewers.image.pixel_selection_subset_state.PixelSubsetState` on IRIS data, an SST cube or, in its quicklook,
    any cube (`_cube_table`), and a quicklook's point group again once it is the edit subset alone, as after picking it
    as glue's Active Subset. On a spectral cube the point is a detector pixel at every wavelength: a click takes the
    axes the clicked viewer does not show, such as a stack's scan or an SST cube's scan and Stokes parameter, from its
    sliders.
    A click on a panel that shows wavelength moves the cube's maps to the clicked wavelength instead of fixing it. Every
    other viewer of the cube, or of another window of its file (`_same_file`), then shows the point's
    step, exposure, scan and slit, after a drag only its last position, and editing one of those
    sliders moves the point. No other wavelength slider is moved, and a Profile's collapse is left in
    place. A viewer whose sliders glue resets for new data joins the point. A quicklook's point drives
    only the viewers it `owns`, and shows only on those of its own file's windows; viewers no
    quicklook owns follow whichever point is followed. A click on a quicklook's slit-jaw image moves
    its point to the raster there (`_to_raster`). A datetime Scatter plot shows the time master's
    exposure (`_mark`). Each data collection has one coordinator (`coordinator`), and the
    ``solar:coordinate`` tool registers every Image viewer with it. It gives the SST cubes their time keys as they come
    and go (`_share_times`).
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
        self.link_points = True  # 'Link points across cubes' (D97)
        self.marker = None  # the `MARK` subset group (`_mark`), once made
        self._drag = None  # while a mouse button is down on a viewer: whether a point was clicked
        # a drag moves the point at every mouse event: show only its latest position. The application owns the timer:
        # PyQt frees the QObjects Python owns at exit in any order, then the application, so a viewer freed at exit
        # still finds it. ponytail: one timer per data collection is kept until exit
        self._timer = QTimer(QCoreApplication.instance())
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._update)
        hub = data_collection.hub
        hub.subscribe(self, SubsetCreateMessage, handler=self._subset_changed)
        hub.subscribe(self, SubsetDeleteMessage, handler=self._subset_deleted)
        hub.subscribe(self, EditSubsetMessage, handler=self._edited)
        hub.subscribe(
            self, SubsetUpdateMessage, handler=self._subset_changed, filter=lambda m: m.attribute == "subset_state"
        )
        hub.subscribe(self, DataCollectionAddMessage, handler=self._share_times)
        hub.subscribe(self, DataCollectionDeleteMessage, handler=self._forget)
        self._share_times()

    def _forget(self, message):
        """
        Let a removed dataset go, with its memory map and file handle: drop what names it, and empty a quicklook point
        on it as Clear point does; then give the SST cubes left their time keys (`_share_times`).
        """
        data = message.data

        def names(value):  # the dataset, a subset state on it or its components (a region), or a tuple holding either
            items = value if isinstance(value, tuple) else (value,)
            return any(
                item is data
                or getattr(item, "reference_data", None) is data
                or any(cid.parent is data for cid in getattr(item, "attributes", ()))
                for item in items
            )

        for cache in (self.masters, self._master_times, self._steps, self._pairs, self._before):
            for key in [key for key, value in cache.items() if names(key) or names(value)]:
                del cache[key]
        for group in self._owners:
            if names(group.subset_state):
                group.subset_state = SubsetState()
        if names(self._kept) or names(self._outside):
            self._kept, self._outside = (None, None, None, None), (None, None)
        self._placed = self._footprint = (None, None)
        self._share_times()

    def _share_times(self, *_):
        """
        Give each SST cube its time key (`observation_key`): cubes whose scan times overlap or lie within the larger
        cadence of each other share ``('SST', their first time)``, so co-temporal CRISP and CHROMIS share one (253-2).
        """
        spans = []
        for data in self.data_collection:
            if _role(data) == "sst" and _timed(data):
                index = (slice(None), *[0] * (data.ndim - 4), slice(None), 0, 0)  # every scan and tuning
                times = data[data.find_component_id("Time"), index]
                spans.append((times.min(), times.max(), _cadence(_times(data, None)), data))
        spans.sort(key=lambda span: span[0])
        starts = {}  # cube -> the first time of its group
        for i, (first, _, cadence, cube) in enumerate(spans):
            # the groups of the cubes before it that it overlaps or follows within the larger cadence merge into one
            near = {starts[other] for _, last, step, other in spans[:i] if first - last <= max(cadence, step)}
            start = min(near, default=first)
            starts = {other: start if when in near else when for other, when in starts.items()}
            starts[cube] = start
        for cube, start in starts.items():
            old = observation_key(cube)
            cube._solar_time_key = ("SST", start)
            if self.masters.get(old) is cube:  # a chosen time master stays one under its group's new key
                self.masters[observation_key(cube)] = self.masters.pop(old)

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
        """
        Make ``group`` the followed point, as when its quicklook's tab is shown. Where an SST cube takes over the time
        from its observation's master then, or hands it over, the new master moves to its scan, frame or exposure
        nearest the old one's time, unless within half the longer of their cadences already, so that each quicklook's
        cube leads the time while shown and starts at the time the last one left (D68).
        """
        keys = {observation_key(viewer.state.reference_data) for viewer in self._viewers if self._follows(viewer)}
        before = {}
        for key in keys - {None}:
            if any(_role(data) == "sst" for data in self._datasets(key)):
                old = self._master(key)
                before[key] = (old, self.master_time(key), _half_cadence(_times(old, self._timing(old)[1])))
        # one shown again after another observation's tab: from its master's time when its tab was last shown
        shown = {observation_key(viewer.state.reference_data) for viewer in self._owners.get(group, ())}
        for key in shown - set(before):
            if key in self._master_times and any(_role(data) == "sst" for data in self._datasets(key)):
                old, when, step = self._master_times[key]
                before[key] = (old, when, _half_cadence(_times(old, step)))
        self.group = group
        for key, (old, when, margin) in before.items():
            new = self._master(key)
            if new in (None, old) or "sst" not in (_role(new), _role(old)) or _time_axis(new) != 0:
                continue
            index, step = self._timing(new)
            times, half = _times(new, step), _half_cadence(_times(new, step))
            [nearest_index], [offset] = nearest([when], times)
            moved = abs(times[min(max(index, 0), len(times) - 1)] - when) > max(margin, half)
            if moved and abs(offset) <= half:  # NaT, a gap's, is neither
                self.move_master(new, int(nearest_index))
        self._timer.start()

    def _follows(self, viewer):
        """Whether ``viewer`` follows the followed point: it owns the viewer, or no point does, deleted ones aside."""
        owners = self._owners.get(self.group)
        if owners is not None and viewer in owners:
            return True
        groups = self.data_collection.subset_groups
        return not any(viewer in viewers for group, viewers in self._owners.items() if group in groups)

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
        """
        Call ``listener(key, time, exposure)`` whenever the time master of observation ``key`` moves, and
        ``listener(None, None, None)`` whenever the point on a cube of neither instrument, which has no observation to
        sync, may have moved.
        """
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
            self._move_in_time(data, 0, index, self._master_viewers(data))
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
        # a cube of neither instrument has no observation, but its quicklook's point is followed
        if group is None or (observation_key(subset.data) is None and group not in self._owners):
            return
        self.group = group
        self._pin(state)
        self._link_points()
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

    def _edited(self, message):
        group = message.subset[0] if len(message.subset) == 1 else None
        if group in self._owners and group is not self.group:
            self.follow(group)  # as picked in glue's Active Subset after a Pixel click on another group

    def _subset_deleted(self, message):
        group = getattr(message.subset, "group", None)
        self._before.pop(group, None)  # not to hold a deleted group; glue-qt 0.4.2's style editors still keep a cut's
        if group not in self.data_collection.subset_groups:  # deleted, not a removed dataset's subset freed
            self._owners.pop(group, None)  # its panels follow the next point
        if group is self.group:
            self._timer.start()  # the point's group went: readouts follow

    def _viewers_of(self, data):
        """The registered viewers of ``data`` that follow the point."""
        return [viewer for viewer in self._viewers if viewer.state.reference_data is data and self._follows(viewer)]

    def _master_viewers(self, data):
        """
        The viewers of ``data`` that follow the point, else those in tabs not shown: a time master shown only there
        leads from them (D39).
        """
        return self._viewers_of(data) or [
            viewer
            for viewer in self._viewers
            if viewer.state.reference_data is data
            and viewer.parent().mdiArea() is not viewer.session.application.current_tab
        ]

    def _pin(self, state):
        """
        Make a click the point, a detector pixel at every wavelength, its other free axes from the clicked viewer's
        sliders; a click on a panel showing wavelength moves the maps, but the second (`_wing`), to it instead.
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
                if not _wing(other):
                    self._set_slices(other, wavelengths)
            if slices != list(state.slices):
                self.group.subset_state = PixelSubsetState(data, slices)

    def _link_points(self, state=None, groups=None):
        """
        With `link_points` (D97), move the point of each other quicklook of a non-IRIS cube linked to the followed
        point's, or ``state``'s, of its observation, of ``groups`` if given, to the point's place on the Sun, at that
        cube's own other slices; a place off that cube leaves its point.
        """
        state = self.group.subset_state if state is None else state
        data = state.reference_data
        place = _hpc(data)
        if not self.link_points or _role(data) in _IRIS_ROLES or place is None:
            return
        world = data.coords.pixel_to_world_values(*[s.start or 0 for s in state.slices][::-1])
        units = data.coords.world_axis_units
        sun = [u.Quantity(world[axis], units[axis]) for axis in place[0]]
        lon = data.world_component_ids[len(units) - 1 - place[0][0]]
        with self._writing():
            for group in self._owners if groups is None else groups:
                point = group.subset_state
                other = getattr(point, "reference_data", None)
                if other in (None, data) or lon not in other.externally_derivable_components:
                    continue
                found = _hpc(other)
                if found is None or observation_key(other) != observation_key(data) or _role(other) in _IRIS_ROLES:
                    continue
                axes, spatial = found
                values = list(other.coords.pixel_to_world_values(*[s.start or 0 for s in point.slices][::-1]))
                for axis, at in zip(axes, sun, strict=True):
                    values[axis] = at.to_value(other.coords.world_axis_units[axis])
                pixel = np.asarray(other.coords.world_to_pixel_values(*values), float)[::-1]
                slices = list(point.slices)
                for axis in spatial:
                    index = round(pixel[axis]) if np.isfinite(pixel[axis]) else -1
                    if not 0 <= index < other.shape[axis]:
                        break
                    slices[axis] = slice(index, index + 1)
                else:
                    group.subset_state = PixelSubsetState(other, slices)
                    # and its own panels, which follow only it (D19), or a session saves their old sliders
                    for viewer in self._owners[group]:
                        if viewer.state.reference_data is other:
                            self._set_slices(viewer, {axis: slices[axis].start for axis in spatial})

    def _to_raster(self, state):
        """
        Make a click on a quicklook's slit-jaw frame the point of its raster there (`sji_to_raster`, D19, #114); outside
        the raster the point stays (`outside_raster`), and under a raster master the frame clicked stays while the point
        is the click's, Undo and Redo too (#182, #193).
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
        if observation_key(point.reference_data) is None:  # a cube of neither instrument, which no time sync tells them
            for listener in list(self._listeners):
                listener(None, None, None)

    def _datasets(self, key):
        shown = dict.fromkeys(viewer.state.reference_data for viewer in self._viewers)
        return [data for data in shown if data is not None and observation_key(data) == key and _timed(data)]

    def _master(self, key):
        """
        The time master of observation ``key``: the chosen one, else the point's raster or SST cube, else the first
        raster, else SST cube, the followed point's viewers show, else the first raster, else SST cube.
        """
        if key is None:
            return None
        datasets = self._datasets(key)
        chosen = self.masters.get(key)
        if chosen is not None and chosen in datasets:
            return chosen
        point = self.point
        if point is not None and point.reference_data in datasets and _role(point.reference_data) in ("raster", "sst"):
            return point.reference_data
        # else a raster of the followed point's viewers, as after Clear point, not one of a hidden tab
        rasters = [data for data in datasets if _role(data) == "raster"]
        rasters += [data for data in datasets if _role(data) == "sst"]
        followed = {viewer.state.reference_data for viewer in self._viewers if self._follows(viewer)}
        return next((data for data in rasters if data in followed), next(iter(rasters), None))

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
        The index of ``data``'s time along its first axis and, for a raster, its timing step: the point's step, or the
        one it had when the point left (mid-raster before any), the sliders giving the rest (D22).
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
        """The slider of a viewer of ``data`` that does not show ``axis``, at the center of a collapse."""
        for viewer in self._master_viewers(data):
            if axis not in _shown(viewer.state) and len(viewer.state.slices) == data.ndim:
                index = viewer.state.slices[axis]
                return int(getattr(index, "center", index))
        return default

    def _band(self, data, axis, default):
        """The pixels along ``axis`` a viewer of ``data`` not showing it averages (a band or Collapse) or shows, a slice."""
        for viewer in self._viewers_of(data):
            if axis not in _shown(viewer.state) and len(viewer.state.slices) == data.ndim:
                index = viewer.state.slices[axis]
                return getattr(index, "slice", None) or slice(index, index + 1)
        return slice(default, default + 1)

    def _pair(self, master, follower, master_step, follower_step):
        """nearest() of every master time among the follower's, cached per pair."""
        # only a stack's times depend on the raster step; keyed by the datasets, as a freed one's id() can be reused
        key = (master, follower, master_step if master.ndim == 4 else None)
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
        Select the time master's exposure, ``time`` for ``seconds``, as glue's own range subset `MARK` on the
        first open datetime Scatter plot of observation ``key`` (D27, #207), found by its label; deleted, not remade.
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
            self.marker = next((group for group in groups if group.label in (MARK, "Master exposure")), None)
        if self.marker is None:
            self.marker = _new_group(app.session, self.data_collection, label=MARK, subset_state=state)
        # off every other viewer before it moves, also those opened since, which glue gives every subset: they would
        # update it at each step
        for viewer in viewers:
            if not isinstance(viewer.state, ScatterViewerState):
                _show(viewer, self.marker, False)
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
        """The slit's x pixel in ``viewer``'s slit-jaw frame, or None where the frame gives none (-1 or NaN)."""
        sji = viewer.state.reference_data
        frame = _sji_frame(viewer.state)
        if frame is None or _role(sji) != "sji" or "slit x position" not in sji.meta:
            return None
        x = float(sji.meta["slit x position"][frame])
        return None if x < 0 or np.isnan(x) else x  # 0-based since LM-SAL/irispy#247: a header's 0, no slit, is -1

    def _move_in_time(self, data, axis, frame, viewers=None):
        """
        Put ``data`` at ``frame`` along its time axis: on its viewers, or ``viewers``, and on the point, or that of the
        quicklook owning ``viewers``, if it is on any window of ``data``'s file (`_same_file`), which stays the point's
        window.
        """
        group, groups = self.group, self.data_collection.subset_groups
        if viewers is not None:  # a hidden tab's, which its point would put back once shown (`_apply_point`)
            group = next((owner for owner in groups if not self._owners.get(owner, set()).isdisjoint(viewers)), group)
        state = group.subset_state if group in groups else None
        point = state if isinstance(state, PixelSubsetState) else None  # as `point`
        if point is not None and _same_file(point.reference_data, data) and point.slices[axis].start is not None:
            slices = list(point.slices)
            if slices[axis].start != frame:
                slices[axis] = slice(frame, frame + 1)
                group.subset_state = PixelSubsetState(point.reference_data, slices)
        for viewer in self._viewers_of(data) if viewers is None else viewers:
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
    ``roi`` on ``raster``'s pixel axes at ``slices`` as a helioprojective region (#116): within the outer pixel centers,
    past which glue's inverse places nothing, with a corner at each step crossed, between which the coordinates are
    linear; a slit-jaw frame's are linear throughout.
    """
    margin = 1e-6  # so that pixel centers on the edge, such as another window's of the raster, are inside
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
    A region on a raster map or slit-jaw frame: glue's own on that data and data linked to its pixels, and elsewhere
    ``world``, its outline (`_outline_region`), which glue places without inverting the coordinates at each pixel (D39).
    """

    def __init__(self, xatt, yatt, roi, world):
        super().__init__(xatt, yatt, roi)
        self.world = world

    def to_mask(self, data, view=None):
        if any(is_equivalent_cid(data, self.xatt, cid) for cid in data.pixel_component_ids):
            return super().to_mask(data, view)
        view = (slice(None),) * data.ndim if view is None else view
        types = getattr(data.coords, "world_axis_physical_types", None) or ()
        angles = [i for i, kind in enumerate(types) if kind in _HPC]
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


def _new_group(session, collection, **kwargs):
    """A new subset group of ``collection``, leaving the edit subset, which glue-qt makes the new group, as it was."""
    mode = session.edit_subset_mode
    edit, group = mode.edit_subset, collection.new_subset_group(**kwargs)
    mode.edit_subset = edit
    return group


class _NewSubset(Command):
    """
    A new subset group, the edit subset left as it is (D38); undo removes the group, which glue's undo leaves emptied,
    and keeps the edit subset, which glue-qt's removal empties.
    """

    kwargs = ["data_collection", "subset_state"]
    label = "new subset"

    def do(self, session):
        self.group = _new_group(session, self.data_collection, subset_state=self.subset_state.copy())

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
    subset, so the Pixel tool keeps moving it; a region picked to edit takes glue's selection mode.

    The panel takes the Pixel tool whenever it becomes the active window, unless it has another mouse mode on: glue-qt
    turns a viewer's mouse mode off as another window becomes active, and a click with none would run glue-qt's region
    selection and empty the edit subset rather than move the point.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # before the mouse modes' own presses, which glue connects as each is turned on
        self.figure.canvas.mpl_connect("button_press_event", self._edit_point)

    def _edit_point(self, event):
        """
        Make the panel's point the edit subset as a Pixel click starts, or the mouse moves in Follow/lock, while a
        dataset is selected in the data collection: glue-qt empties the edit subset then, and the click made a new
        subset (D82). After glue's "None/Create New", which leaves nothing selected there, the click still makes one.
        """
        session = self.session
        mode, groups = session.edit_subset_mode, session.data_collection.subset_groups
        if mode.edit_subset or not _pixel_tool_on(self) or not session.application._layer_widget.selected_layers():
            return
        owners = coordinator(session.data_collection)._owners
        point = next((group for group, viewers in owners.items() if self in viewers and group in groups), None)
        if point is not None:
            mode.edit_subset = [point]

    def set_status(self, message):
        """glue-qt's status line but for the mouse modes' hints, which a narrow panel's frame time clips (D90)."""
        if self.toolbar is None or message != getattr(self.toolbar.active_tool, "status_tip", None):
            super().set_status(message)

    def set_focus(self, state):  # glue-qt's call once it has turned the last active viewer's mouse mode off
        super().set_focus(state)
        if state and self.toolbar.active_tool is None:
            self.toolbar.active_tool = "image:point_selection"

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
        """glue's record of the panel; its quicklook's first Image panel's holds the quicklook's recipe (`_recipe`)."""
        rec, tab = super().__gluestate__(context), self.parent().mdiArea()
        if not hasattr(tab, "_solar_quicklook"):  # a panel of a session saved before D83, saved as a plain viewer
            return rec
        first = next(p for p in _viewers(tab._solar_quicklook[-1]) if isinstance(p, ImageViewer) and not p._closed)
        return {**rec, "quicklook": _recipe(self.session.application, tab, context)} if self is first else rec


def _role(data):
    """
    'raster', 'sji', 'aia', 'sst' or None, from the INSTRUME keyword: AIA cutouts and Hinode/SOT cubes load as slit-jaw
    cubes and follow the time as they do, without their quicklook panel, raster point or overlays; SST CRISP and
    CHROMIS cubes step through time by scan, and have a quicklook of their own (`_cube_table`).
    """
    instrument = str((getattr(data, "meta", None) or {}).get("INSTRUME", ""))
    if instrument.startswith(("AIA", "SOT")):
        return "aia"
    return {"SPEC": "raster", "SJI": "sji", "CRISP": "sst", "CHROMIS": "sst"}.get(instrument)


_IRIS_ROLES = ("raster", "sji", "aia")  # an IRIS observation's own data, whose point `_link_points` leaves alone


def _hpc(data):
    """
    The world axes of the helioprojective longitude and latitude of ``data``, in WCS order, and its pixel axes along
    which only they vary, in glue's order, or None.
    """
    wcs = data.coords
    types = list(getattr(wcs, "world_axis_physical_types", None) or ())
    if not set(_HPC) <= set(types):
        return None
    world = [types.index(physical_type) for physical_type in _HPC]
    matrix = np.asarray(wcs.axis_correlation_matrix)
    spatial = matrix[world].any(axis=0) & ~np.delete(matrix, world, axis=0).any(axis=0)
    return world, [data.ndim - 1 - axis for axis in np.nonzero(spatial)[0]]


def _same_file(data, other):
    """
    Whether ``data`` and ``other`` are windows of one raster file or stack, which share their scans, steps or exposures
    and slit pixels: one observation, shape but wavelength, DATE_OBS and ``meta['raster files']``.
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
    The name and TWAVE of the window ``data`` holds, from the TWAVEn inside its wavelengths, as every window's keywords
    describe window 1; (None, None) if none is.
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
    windows = {data: _window(data)[0] for data in rasters}
    for name in (window, DEFAULT_WINDOW, windows[rasters[0]]):
        chosen = [data for data in rasters if name is not None and windows[data] == name]
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
    return f"{title} (deconvolved)" if " deconvolved" in data.label else title


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
    _zoom(viewer, x, y, max(10.0, 0.1 * max(np.ptp(x), np.ptp(y))))


def _zoom(viewer, x, y, margin):
    """
    Zoom an Image viewer to pixel positions ``x`` and ``y`` with ``margin``, at the axes' aspect, so that glue's equal
    aspect keeps the limits; a later resize keeps their area, which can crop them, so `_arrange` zooms again unless
    they moved (P9).
    """
    box = viewer.axes.get_window_extent()
    ratio = box.height / box.width if box.width else 1.0
    width, height = np.ptp(x) + 2 * margin, np.ptp(y) + 2 * margin
    if height > width * ratio:  # so the rows span the view exactly, not a rounding short of it (P9)
        width = height / ratio
    else:
        height = width * ratio
    x_mid, y_mid = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
    state = viewer.state
    with delay_callback(state, "x_min", "x_max", "y_min", "y_max"):
        state.x_min, state.x_max = x_mid - width / 2, x_mid + width / 2
        state.y_min, state.y_max = y_mid - height / 2, y_mid + height / 2
    viewer._solar_zoom = (x, y, margin), (state.x_min, state.x_max, state.y_min, state.y_max)


def _pick_sjis(sjis):
    """One slit-jaw cube per channel, the plain one before the deconvolved, and the ones left out."""
    chosen = {}
    for data in sorted(sjis, key=lambda data: " deconvolved" in data.label):
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
    state.show_axes = False  # as 'Hide axes' does, so no draw places ticks; 'Hide axes' on any panel shows them (D71)
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


class _Panel(NamedTuple):
    """
    A row of a quicklook's panel table (`_fill`, D78): an Image panel showing array axes ``x`` and ``y`` at ``at``;
    without ``x`` a spectrum (`_profile`), or with ``cut``, ``(label, axis, at, band, x_att)``, a `_Cut` Profile;
    ``window`` names another raster window's panel.
    """

    role: str
    data: Data
    title: str
    x: int = None
    y: int = None
    at: tuple = None
    aspect: str = None
    window: str = None
    cut: tuple = None


def _raster_panels(raster, window, roles=("map", "spectrogram", "wavelength"), other=False):
    """
    The map, spectrogram and wavelength panels (`_Panel`) of the table in the plan, or those of ``roles``, of another
    window with ``other``, and the point at the map center.
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
    panels = [
        _Panel(role, raster, f"{window} {names[role]}", x, y, point, "auto", window if other else None)
        for role, (x, y) in axes.items()
        if role in roles
    ]
    slices = [slice(i, i + 1) for i in point]
    slices[spectral] = slice(None)
    return panels, PixelSubsetState(raster, slices)


@layer_artist_maker("IRIS: Profiles without a large cube's own")
def hidden_cube_profile(viewer, data):
    """
    Add a quicklook spectrum panel's raster, and a non-IRIS cube of ``large_data_size`` or more, hidden, so glue never
    profiles the whole cube on the main thread (30 s and 11 GB on SST obs 492; #95, #233); the viewer fits its range
    to its first subset profile instead.
    """
    if getattr(viewer, "_solar_hidden", None) is not data:
        large = isinstance(viewer, ProfileViewer) and isinstance(data, Data) and viewer.large_data_size is not None
        if not large or data.size < viewer.large_data_size or _role(data) in ("raster", "sji", "aia"):
            return None
        # the application's, which glue-qt's toolbar does not clear on a change of tool, as it does the viewer's
        (viewer.session.application or viewer).statusBar().showMessage(
            f"{data.label} is hidden, as its own profile reads all {data.size:.3g} values: tick it in the layer list to"
            " show it."
        )
        viewer._solar_fit = _FitOnceComputed(viewer, data, fit=lambda viewer: viewer.state.reset_limits())
    state = ProfileLayerState(layer=data, viewer_state=viewer.state, visible=False)
    state._solar_own = True  # hidden by glue-solar: 'Save profiles as ECSV…' does not name it
    return viewer.get_data_layer_artist(data, state)


def _profile(app, raster, title):
    """
    A Profile of the point's mean spectrum, with the raster itself hidden and no large-data prompt, and a status-bar note
    if it could not add the raster, else None.
    """
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # as before each Image viewer
    viewer = app.new_data_viewer(ProfileViewer)
    viewer.state.title = title
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
    return viewer, None


def quicklook(app, datasets, window=None, main=None):
    """
    Open the IRIS quicklook of one observation in a new tab.

    A raster (or a stack of scans) opens as a map, a spectrogram and a wavelength panel (wavelength
    against step, exposure or scan), each slit-jaw channel in its own viewer, and a spectrum panel
    showing the mean spectrum of the point. The point starts at the center of the map, in a new
    subset group 'Point' that is the edit subset while the tab is shown, with the Pixel tool active
    on the map. A read-only 'Point' window below the panels gives the point's pixel, position, time,
    exposure, value and time sync in each dataset they show, and the 'Panels' list beside it turns each
    panel on and off (`_Panels`). The Image panels open without axes, which 'Hide axes' shows on all. Lines on the
    spectrogram, the wavelength panel and the spectrum panel mark the point, the map's wavelength and
    the time master's time, and a zoom on the spectrum panel is the wavelength panel's too
    (`_SpectralLines`). Clicks and keys wait until it is open.

    Of an SST CRISP or CHROMIS cube, or a cube of neither instrument with one wavelength axis and two spatial axes
    (`_cube_axes`), alone in ``datasets``, it opens that cube's quicklook instead (`_cube_table`), one cube to a tab,
    whose panels follow the point, and an SST cube's the time, as the IRIS quicklook's do.

    Each other window named in ``window`` gets an unticked box in the Panels list, which adds the spectrum of the point
    and, on a sit-and-stare raster or a stack, its own wavelength panel (λ–time or λ–scan), to a row below once ticked
    (D83). Its scan, step or exposure, and slit pixels are linked to the shown window's with
    `~glue.core.link_helpers.LinkSame` (once, however often the quicklook opens), so the point is the same pixel in
    every window. Its spectrum panel's 'Show this window's panels' makes it the main window (`_switch`).

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
        ``sji``, a list, and ``windows``, a list of each other window's ``spectrum`` and any ``wavelength``, joined as
        the Panels list makes them; of a cube, those `_cube_table` gives.

    Raises
    ------
    ValueError
        For an observation with neither a raster nor a slit-jaw image, nor a single cube.
    """
    rasters = [data for data in datasets if _role(data) == "raster"]
    shown = rasters or [data for data in datasets if _role(data) == "sji"]
    cubes = [data for data in datasets if _role(data) == "sst" or (_role(data) is None and _cube_axes(data))]
    if not shown and len(cubes) > 1:
        raise ValueError("A quicklook shows one cube: open one for each.")
    if not shown and not cubes:
        raise ValueError(f"{datasets[0].label} has no raster or slit-jaw image for a quicklook")
    collection = app.data_collection
    new = [data for data in datasets if data not in collection]
    if new:  # one link update for all, where each append runs one
        collection.extend(new)
    keep_hpc_linked(collection)
    app.new_tab()
    names, key = app.tab_names, observation_key(shown[0]) if shown else None
    if shown:
        names[-1] = f"IRIS {key[0]}" if key else "IRIS"
    else:
        names[-1] = f"SST {_sst_line(cubes[0])}" if _role(cubes[0]) == "sst" else cubes[0].label.replace("&", "and")
    app.tab_names = names
    return _fill(app, app.current_tab, datasets if shown else cubes, window, main)


def _iris_table(app, datasets, window, main):
    """
    The panel table (`_fill`) of IRIS ``datasets``: the main window's panels and spectrum, each other window's
    wavelength panel (if timed) and spectrum, linked (`_link_windows`), and a panel per slit-jaw channel (D42, D60).
    """
    rasters = [data for data in datasets if _role(data) == "raster"]
    sjis, offered = _pick_sjis([data for data in datasets if _role(data) == "sji"])
    panels, point = [], None
    if rasters:
        raster, others = _pick_windows(rasters, window, main)
        _link_windows(app.data_collection, raster, others)
        name = _window(raster)[0] or raster.label
        panels, point = _raster_panels(raster, name)
        panels.append(_Panel("spectrum", raster, f"{name} spectrum"))
        for other in others:
            name = _window(other)[0]
            # a scanning raster's steps are places, not times: no λ–t panel
            roles = ("wavelength",) if _time_axis(other) is not None else ()
            panels += _raster_panels(other, name, roles, other=True)[0]
            panels.append(_Panel("spectrum", other, f"{name} spectrum", window=name))
    for sji in sjis:
        panels.append(_Panel("sji", sji, _sji_title(sji), sji.ndim - 1, sji.ndim - 2, (0,) * sji.ndim, "equal"))
    return {
        "panels": panels,
        "point": point,
        "viewers": {"sji": [], "windows": []},
        "notes": [f"{data.label} is loaded too: drag it onto a slit-jaw viewer to see it." for data in offered],
    }


def _cube_axes(data):
    """
    The array axes of ``data`` by the world coordinates along them, ``(time, Stokes, wavelength, y, x)``, None for
    those it does not have: one wavelength axis, of two wavelengths or more, two others of position, on the sky or the
    Sun, and any of time and Stokes parameter; or None for data of other axes.
    """
    types = [str(kind) for kind in getattr(data.coords, "world_axis_physical_types", None) or ()]
    matrix = getattr(data.coords, "axis_correlation_matrix", None)
    if not types or np.shape(matrix) != (len(types), data.ndim):
        return None

    def along(*kinds):  # APE 14 orders pixel axes opposite to numpy
        worlds = [world for world, kind in enumerate(types) if kind.startswith(kinds)]
        return {data.ndim - 1 - pixel for pixel in np.flatnonzero(matrix[worlds].any(axis=0)).tolist()}

    wave = along("em.wl")
    stokes = along("phys.polarization.stokes") - wave
    time = along("time") - wave - stokes  # a moving pointing's position depends on time too
    place = along("pos.", "custom:pos.") - wave - stokes - time
    sizes = len(time), len(stokes), len(wave), len(place)
    if sizes[2:] != (1, 2) or max(sizes[:2]) > 1 or sum(sizes) != data.ndim or data.shape[min(wave)] < 2:
        return None  # one wavelength has no spectrum
    return (next(iter(time), None), next(iter(stokes), None), *wave, *sorted(place))


def _sst_line(cube):
    """
    The line an SST cube shows, as its header names it, such as 'Ca II 8542', else its prefilter or label; an '&' as
    'and', which Qt's tab and window titles would take for a shortcut: 'Ca II H and K'.
    """
    return str(cube.meta.get("WAVEBAND") or cube.meta.get("FILTER1") or cube.label).replace("&", "and")


def _cube_table(app, cube):
    """
    The panel table (`_fill`) of a cube's quicklook (D65, D68, D78): ``map``, ``wing`` (SST only) and ``slit``; the
    ``spectra`` of the point's Stokes parameters; for a time axis ``wavelength`` and ``curve``; laid out in ``rows``.
    The spectra and curve are `_Cut` groups following the point, so no panel profiles the whole cube.
    """
    sst = _role(cube) == "sst"
    if sst:  # scan, Stokes, wavelength, y and x, or a cube of intensities' scan, wavelength, y and x
        w = cube.ndim - 3
        t, s, y, x = 0, 1 if w == 2 else None, w + 1, w + 2
        name, core = _sst_line(cube), cube.coords.core
    else:
        t, s, w, y, x = _cube_axes(cube)
        name, core = cube.label.replace("&", "and"), cube.shape[w] // 2
    start = [0] * cube.ndim
    start[w], start[y], start[x] = core, cube.shape[y] // 2, cube.shape[x] // 2
    if t is not None:
        start[t] = coordinator(app.data_collection).following(cube) or 0
    panels = [_Panel("map", cube, f"{name} map", x, y, tuple(start), "equal")]
    if sst:
        wing = (*start[:w], 0, *start[w + 1 :])
        panels.append(_Panel("wing", cube, f"{name} second map", x, y, wing, "equal"))
    panels.append(_Panel("slit", cube, f"{name} virtual slit", w, y, tuple(start), "auto"))
    if t is not None:
        panels.append(_Panel("wavelength", cube, f"{name} λ–time", w, t, tuple(start), "auto"))
    spectra = {"spectrum": None}
    if s is not None:  # ponytail: I, Q, U and V in that order, as SST's; from the WCS for a Stokes axis of others
        spectra = {f"Stokes {stokes}": {s: k} for k, stokes in enumerate("IQUV"[: cube.shape[s]])}
    for label, at in spectra.items():
        cut = (f"{name} {label} at the point", w, at, None, cube.world_component_ids[w])
        panels.append(_Panel("spectra", cube, f"{name} {label}", cut=cut))
    if t is not None:
        curve = (f"{name} light curve", t, None, "map", cube.world_component_ids[t])  # its time, not index (D90)
        panels.append(_Panel("curve", cube, f"{name} light curve", cut=curve))
    slices = [slice(i, i + 1) for i in start]
    slices[w] = slice(None)  # a pixel at every wavelength
    return {
        "panels": panels,
        "point": PixelSubsetState(cube, slices),
        "viewers": {"spectra": []},
        "rows": (("map", "wing", "slit"), ("spectra",), ("wavelength", "curve")),  # maps on top (D68)
        "limits": sst and s is not None,
    }


def _fill(app, tab, datasets, window=None, main=None, group=None, shown=()):
    """
    Open the panels of the panel table of ``datasets`` (`_iris_table`, or a cube's `_cube_table`; D78) in ``tab`` and
    return their viewers (`quicklook`); with a point, its group (``group`` or a new 'Point'), the cut Profiles, the
    Point window and the lines (`_SpectralLines`); the Panels list; then lay them out (`_arrange`). Other windows'
    panels, those of ``shown`` aside, wait until ticked in the Panels list, as each viewer takes 0.34 s to open (D83).
    """
    iris = any(_role(data) in ("raster", "sji") for data in datasets)
    table = _iris_table(app, datasets, window, main) if iris else _cube_table(app, datasets[0])
    collection = app.data_collection
    coord = coordinator(collection)  # before the point, so it follows it
    viewers, windows, made, notes = table["viewers"], {}, [], []

    def add(panel, viewer):
        made.append((panel, viewer))
        viewer.window_closed.connect(partial(setattr, viewer, "_closed", True))  # glue-qt's close box does not mark it
        viewer.toolbar.setIconSize(QSize(16, 16))  # glue-qt's are 25 px: more of the narrow panels' tools in sight (P8)
        viewer.parent().setWindowIcon(viewer.windowIcon())  # glue-solar's (`_init`) on its title bar, not Qt's logo
        if panel.window is not None and panel.window not in windows:
            windows[panel.window] = {}
            viewers["windows"].append(windows[panel.window])
        into = viewers if panel.window is None else windows[panel.window]
        if isinstance(into.get(panel.role), list):
            into[panel.role].append(viewer)
        else:
            into[panel.role] = viewer

    def make(panel):
        if panel.x is None:
            viewer, note = _profile(app, panel.data, panel.title)
            notes.append(note)
            if panel.window is not None:
                viewer.toolbar.tools["solar:main_window"].enabled = True  # 'Show this window's panels'
        else:
            viewer = _image(
                app, QuicklookImageViewer, panel.data, panel.x, panel.y, panel.at, panel.title, panel.aspect
            )
            if table.get("limits"):
                layer = viewer.state.layers[0]
                limits = partial(_stokes_limits, layer, wing=panel.role == "wing")
                viewer.state.add_callback("slices", limits)
                layer.add_callback("stretch_global", lambda *_: limits(viewer.state.slices))
        add(panel, viewer)
        return viewer

    def open_window(name):
        """Make the panels of window ``name`` with the point, the spectrum's fit and the lines; by their rows."""
        state, new = group.subset_state, {}
        for row in [panel for panel in table["panels"] if panel.window == name]:
            at = row.at
            if at is not None and isinstance(state, PixelSubsetState) and _same_file(state.reference_data, row.data):
                # at the point, which its sliders would move otherwise (`Coordinator._move_point`)
                at = tuple(index if s.start is None else s.start for s, index in zip(state.slices, at))
            new[row] = make(row._replace(at=at))
        images = [viewer for row, viewer in new.items() if row.x is not None]
        coord.own(group, images)
        _show_point(app, group, [viewer for panel, viewer in made if _same_file(panel.data, point.reference_data)])
        spectrum = next(viewer for row, viewer in new.items() if row.x is None)
        _fit_spectrum(spectrum, group)
        if images:
            _SpectralLines(coord, group, images, spectrum, tab)
        return new

    for panel in table["panels"]:
        if panel.cut is None and panel.window is None:  # cuts once the point is there
            make(panel)
    if "wing" in viewers:
        viewers["wing"]._solar_wing = True  # its wavelength stays (`_wing`)
        # per frame, as glue's whole cube's limits, mostly the line's, washed the far brighter wing out (P9)
        viewers["wing"].state.layers[0].stretch_global = False
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # and after the last (see _image)
    point = table["point"]
    if point is not None:
        new, followed = group not in collection.subset_groups, coord.point  # None, or deleted by the user
        if new:
            linked, coord.link_points = coord.link_points, False  # opening a tab moves no other point (D97)
            try:
                group = collection.new_subset_group(label="Point", subset_state=point)
            finally:
                coord.link_points = linked
        coord.own(group, [viewer for panel, viewer in made if panel.x is not None])
        if new and followed is not None:
            coord._link_points(followed, [group])  # it starts at the followed point's place, if on its cube
        _edit_in_tab(app, tab, group)
        _show_point(app, group, [viewer for panel, viewer in made if _same_file(panel.data, point.reference_data)])
        for spectrum in [viewer for panel, viewer in made if panel.x is None]:
            _fit_spectrum(spectrum, group)
        for panel in [panel for panel in table["panels"] if panel.cut is not None]:
            label, axis, at, band, x_att = panel.cut
            cut = partial(_Cut, point=group, band=viewers.get(band), axis=axis, data=panel.data, at=at)
            add(panel, _cut_profile(app, label, cut, x_att, panel.title))
        if table.get("limits"):  # Q, U and V spectra at least the maps' range, their noise level shaded (F173)
            for stokes, spectrum in enumerate(viewers["spectra"][1:], 1):
                noise = datasets[0]._noise[stokes]
                spectrum.axes.axhspan(-noise, noise, color="0.9", zorder=0, gid="solar:noise")
                spectrum._solar_limit = _stokes_limit(datasets[0], stokes)
                _fit(spectrum)
        if "rows" in table:
            rows = ([viewer for panel, viewer in made if panel.role in row] for row in table["rows"])
            viewers["rows"] = [row for row in rows if row]
        mains = [viewer for panel, viewer in made if panel.window is None and panel.x is not None]
        _add_window(tab, _PointWindow(coord, group, point.reference_data, mains), "Point")  # filled by `_arrange`
        panels = [(panel, viewer) for panel, viewer in made if panel.window is None]
        images = [viewer for panel, viewer in panels if panel.x is not None and _spectral_axes(panel.data)]
        if images:
            _SpectralLines(coord, group, images, next(viewer for panel, viewer in panels if panel.x is None), tab)
    entries = _viewers({**viewers, "windows": []})  # each main panel and each slit-jaw image, with no point too (D66)
    for name in dict.fromkeys(panel.window for panel in table["panels"] if panel.window is not None):
        rows = [panel for panel in table["panels"] if panel.window == name]
        entries.append((name, list(open_window(name).values()) if name in shown else rows))
    sub = _add_window(tab, _Panels(entries, group, partial(_arrange, tab, viewers), open_window), "Panels")
    # a click on a box leaves the panel active, with its tool: glue-qt resets both for the window Qt focuses
    for widget in (sub, sub.widget(), sub.widget().viewport()):
        widget.setFocusPolicy(Qt.NoFocus)
    if "notes" in table:
        app.statusBar().showMessage(" ".join(note for note in notes + table["notes"] if note))
    if point is not None:  # first, as glue-qt then fills its side panels for the map, which can widen them
        tab.setActiveSubWindow(viewers["map"].parent())
        viewers["map"].toolbar.active_tool = "image:point_selection"
    QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # let the tab take its final size
    _arrange(tab, viewers)
    if "sji" in viewers or "wing" in viewers:  # an IRIS or SST quicklook
        # and the panels theirs, before the slit-jaw or map limits take the axes' aspect
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        for viewer in viewers.get("sji", ()):
            if point is not None and _placeable(viewer.state.reference_data):
                _footprint_limits(viewer, point.reference_data)
        if "wing" in viewers and (field := datasets[0]._field):
            for viewer in (viewers["map"], viewers["wing"]):  # the field, not a mosaic's frame (P9)
                _zoom(viewer, *np.array(field[::-1], dtype=float), 0.5)
    tab._solar_quicklook = (datasets, window, main, viewers)  # for `_recipe`
    return viewers


def _stokes_limit(cube, stokes):
    """
    The limit about 0 of Stokes parameter ``stokes`` of an SST cube's panels: 5 times its noise level for Q and U, 10 for
    V, as linear polarization is the weaker (`~glue_solar.sources.sst._Cube._noise`, F173).
    """
    return (5 if stokes < 3 else 10) * cube._noise[stokes]


def _stokes_limits(layer, slices, wing=False):
    """
    Give ``layer`` the limits of the Stokes parameter of ``slices``: glue's 99.5% for I, and `_stokes_limit` about 0 for
    Q, U and V, which glue's over the whole cube, I's values mostly, showed flat (230-6); on the second map (``wing``),
    per frame for its I (P9), those whatever its 'Per-frame limits' (D88).
    """
    # ponytail: set as the Stokes parameter or 'Per-frame limits' changes, over limits chosen in the style editor, and I
    # takes glue's 99.5% again; keep each parameter's last limits if that matters
    cube, stokes = layer.layer, getattr(slices[1], "center", slices[1])  # a Collapse at its center (D39)
    shown = stokes, layer.stretch_global
    if shown == vars(layer).get("_solar_stokes", (0, True)) or layer.attribute is not cube.main_components[0]:
        return
    layer._solar_stokes = shown
    limit = _stokes_limit(cube, stokes) if stokes and (layer.stretch_global or wing) else np.nan
    if not limit > 0:  # I, 'Per-frame limits', or a parameter constant or all NaN at the continuum
        layer.percentile = PERCENTILE
        return
    with delay_callback(layer, "v_min", "v_max"):
        layer.v_min, layer.v_max = -limit, limit


def _viewers(viewers):
    """Every viewer of `quicklook`'s ``viewers``."""
    if "rows" in viewers:  # a cube's quicklook's (`_cube_table`)
        return [viewer for row in viewers["rows"] for viewer in row]
    roles = [viewers[role] for role in ("map", "spectrogram", "wavelength", "spectrum") if role in viewers]
    return roles + viewers["sji"] + [viewer for panels in viewers["windows"] for viewer in panels.values()]


def _switch(viewer):
    """
    Make the window of ``viewer``, another window's spectrum panel, the main window (D60, #225): the quicklook opens
    again with it as ``main`` (`_reopen`), every panel on, keeping the axes, the point's pixel and master's index.
    """
    app, tab = viewer.session.application, viewer.parent().mdiArea()
    coord, raster = coordinator(app.data_collection), viewer.state.reference_data
    master = coord._master(observation_key(raster))
    index, _ = coord._timing(master)
    recipe, point = _recipe(app, tab), app._solar_points[tab].subset_state
    recipe.update(main=_window(raster)[0], panels=[[*panel[:2], False, panel[3]] for panel in recipe["panels"]])
    lists = tab.findChildren(_Panels)  # none once the user closed its window: the map's axes then
    axes = lists[-1].axes if lists else tab._solar_quicklook[-1]["map"].state.show_axes
    for panel in _viewers(tab._solar_quicklook[-1]):
        panel.close(warn=False)
    for widget in tab.findChildren((_PointWindow, _Panels)):
        widget.parentWidget().close()
    for lines in tab.findChildren(_SpectralLines):
        lines.deleteLater()  # its ``destroyed`` removes its listener
    _reopen(app, tab, recipe)
    if isinstance(point, PixelSubsetState) and _same_file(point.reference_data, raster):  # wavelength is last
        point = PixelSubsetState(raster, [*point.slices[:-1], slice(None)])
    app._solar_points[tab].subset_state = point  # a new group if the user deleted it
    tab.findChildren(_Panels)[-1].show_axes(axes)  # the new list's
    now = coord._master(observation_key(raster))
    if _same_file(now, master):  # the same, or another window of its file
        coord.move_master(now, index)


def _recipe(app, tab, context=None):
    """What `_reopen` opens the quicklook of ``tab`` again from (D83), objects named by glue's ``context`` if any."""
    name = getattr(context, "id", lambda value: value)
    datasets, window, main, viewers = tab._solar_quicklook
    shows = [panel.state.reference_data for panel in _viewers(viewers)]  # with the panels closed by hand, made again
    panels = [panel for panel in _viewers(viewers) if not panel._closed]
    point, collection = getattr(app, "_solar_points", {}).get(tab), app.data_collection
    master = coordinator(collection).masters.get(observation_key(shows[0]))
    firsts = [panel.layers[0].layer for panel in panels if panel.layers]  # a cube's spectra's and light curve's cuts

    def ids(state):  # as glue's `State.__gluestate__`, but the layers
        return {key: name(value) for key, value in state.as_dict().items() if key != "layers"}

    return {
        "datasets": [name(data) for data in datasets if data in collection],
        "window": window,
        "main": main,
        "shown": [_window(data)[0] for data in shows if _role(data) == "raster"],  # the other windows made
        "point": name(point if point in collection.subset_groups else None),
        "master": name(master if master in collection else None),
        "cuts": [name(first.group) for first in firsts if isinstance(first, Subset) and first.group is not point],
        "panels": [
            [name(panel), panel.state.title, _off(panel), [ids(panel.state), *map(ids, panel.state.layers)]]
            for panel in panels
        ],
    }


def _reopen(app, tab, recipe, context=None):
    """Open the quicklook of ``recipe`` (`_recipe`) in ``tab`` as `quicklook` does, as it was."""
    collection, find = app.data_collection, getattr(context, "object", lambda value: value)
    datasets = [find(name) for name in recipe["datasets"]]
    coordinator(collection).set_master(find(recipe["master"]))
    for group in map(find, recipe["cuts"]):
        collection.remove_subset_group(group)  # made again
    viewers = _fill(app, tab, datasets, recipe["window"], recipe["main"], find(recipe["point"]), recipe["shown"])
    saved = {title: (off, states) for _, title, off, states in recipe["panels"]}
    for panels in tab.findChildren(_Panels)[-1:]:  # the new list; first, as a panel off's stale sliders move the point
        for item, panel in panels.panels:
            if not isinstance(panel, _Panel) and saved.get(panel.state.title, (False,))[0]:
                item.setCheckState(0, Qt.Unchecked)
        panels.apply()
    for panel in _viewers(viewers):
        _, states = saved.get(panel.state.title, (False, [{}]))
        state, *layers = [{key: find(value) for key, value in each.items()} for each in states]
        panel.state.update_from_dict(state)
        for layer in panel.state.layers:
            layer.update_from_dict(next((each for each in layers if each["layer"] is layer.layer), {}))


@session_patch()
def _reopen_quicklooks(session):
    """Restore a session's quicklooks from their recipes (`_recipe`), not their panels, through `_Application`."""
    main = session.get("__main__", {})
    for i, names in enumerate(main.get("viewers", ())):
        for recipe in [session[name]["quicklook"] for name in names if "quicklook" in session[name]]:
            if recipe["datasets"]:  # none once its data were all removed: its tab opens empty
                main.setdefault("quicklooks", {})[i], main["_type"] = recipe, f"{__name__}.{_Application.__name__}"
            main["viewers"][i] = [name for name in names if name not in [panel[0] for panel in recipe["panels"]]]


class _Application:
    """glue-qt's application as a session restores it, each quicklook opened again before its tab's other viewers."""

    @staticmethod
    def __setgluestate__(rec, context):
        from glue_qt.app.application import GlueApplication

        app = GlueApplication.__setgluestate__({**rec, "viewers": [[] for _ in rec["viewers"]]}, context)
        for i, names in enumerate(rec["viewers"]):
            if i in rec["quicklooks"]:
                app.tab_widget.setCurrentIndex(i)  # glue opens viewers in the current tab
                _reopen(app, app.tab(i), rec["quicklooks"][i], context)
                app.tab(i).installEventFilter(_ArrangeShown(app.tab(i)))
            for name in names:  # as glue-qt adds them, over the panels
                app.add_widget(context.object(name), tab=i, hold_position=True)
        return app


class _ArrangeShown(QObject):
    """
    Lay out a restored quicklook's tab once shown: Qt sizes a hidden tab only as it shows it, and glue-qt's
    ``restore_session_and_close`` sizes the window after showing it, hence the timer.
    """

    def eventFilter(self, tab, event):
        if event.type() == QEvent.Type.Resize:
            tab.removeEventFilter(self)
            QTimer(self, singleShot=True, interval=0, timeout=partial(_arrange, tab, tab._solar_quicklook[-1])).start()
        return False


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


def _off(viewer):
    """Whether ``viewer`` is a quicklook panel turned off in its Panels list (`_turn`)."""
    return vars(viewer).get("_solar_off", False)  # not Qt's, which a deleted viewer no longer has


def _wing(viewer):
    """Whether ``viewer`` is an SST quicklook's second map, whose wavelength only its own slider moves (`_fill`)."""
    return vars(viewer).get("_solar_wing", False)


def _turn(viewer, on, group):
    """
    Show ``viewer``, a quicklook panel of point ``group``, or hide it (D66, #228): hidden, the coordinator leaves it and
    glue only notes the subsets that change, which it updates once shown, as the coordinator moves it to the point.
    """
    session = viewer.session
    coord = coordinator(session.data_collection)
    viewer._solar_off = not on
    viewer.parent().setVisible(on)
    if on:
        viewer.register_to_hub(session.hub)  # glue's own handling of subset changes again
        for layer in viewer.layers:
            if layer.layer in viewer._solar_changed:
                layer.update()
        if isinstance(viewer, ImageViewer):
            data = viewer.state.reference_data
            master = _role(data) == "sji" and coord.masters.get(observation_key(data)) is data
            frame = coord.following(data) if master else None  # the raster's time, while it leads
            if frame is not None:
                viewer.state.slices = (frame, *viewer.state.slices[1:])
            coord.register(viewer)
            if group is not None:  # a slit-jaw-only quicklook has no point (D78)
                coord.own(group, [viewer])
    else:
        changed = viewer._solar_changed = set()
        session.hub.subscribe(viewer, SubsetUpdateMessage, handler=lambda message: changed.add(message.subset))
        coord.unregister(viewer)
    coord._timer.start()  # the lines, readouts and Point window follow


def _show_point(app, group, own):
    """
    Show the point only in its quicklook's raster and spectrum panels, and no other subset there: glue 1.27.0 draws
    a crosshair on data it does not belong to (D19). Points are removed, as they move at every click; others hidden.
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
                layer._solar_own = True  # as hidden_cube_profile's


def _fit(viewer):
    """Fit the spectrum panel's y range to its profiles and the y = 0 line, and any Stokes limit about it (`_fill`)."""
    state, limit = viewer.state, getattr(viewer, "_solar_limit", 0)
    state.reset_limits()
    home = state.x_min, state.x_max, state.y_min, state.y_max  # what glue's Home gives
    state.y_min, state.y_max = min(state.y_min, -limit), max(state.y_max, limit)
    viewer._solar_fitted = home, (state.x_min, state.x_max, state.y_min, state.y_max)


def _refit(viewer):
    """
    `_fit` the panel again while it shows the last fit's range or Home's, not one panned, zoomed or typed since (D98).
    """
    state = viewer.state
    if not _off(viewer) and (state.x_min, state.x_max, state.y_min, state.y_max) in getattr(viewer, "_solar_fitted", ()):
        _fit(viewer)


class _Refit(HubListener):
    """
    `_refit` a spectrum or curve panel as its subset ``subset`` moves with the point, once glue has computed the
    subset's profile, on the main thread or a worker.
    """

    def __init__(self, viewer, subset):
        self.viewer, self.subset = viewer, subset
        hub = subset.data.hub
        hub.subscribe(self, ComputationEndedMessage, handler=self._computed, filter=self._of_layer)
        viewer.window_closed.connect(lambda: hub.unsubscribe_all(self))

    def _of_layer(self, message):
        return message.sender in self.viewer.layers and message.sender.state.layer is self.subset

    def _computed(self, message):
        _refit(self.viewer)


class _FitOnceComputed(HubListener):
    """
    Fit a Profile viewer with ``fit`` once glue has computed on a worker thread the profile of any subset of ``layer``,
    a dataset (`hidden_cube_profile`).
    """

    def __init__(self, viewer, layer, fit):
        self.viewer, self.layer, self.fit = viewer, layer, fit
        layer.hub.subscribe(self, ComputationEndedMessage, handler=self._ended, filter=self._of_layer)

    def _of_layer(self, message):
        if message.sender not in self.viewer.layers:
            return False
        layer = message.sender.state.layer
        return isinstance(layer, Subset) and layer.data is self.layer

    def _ended(self, message):
        # a subset of another, unlinked dataset ends its computation too, with no profile
        try:
            computed = message.sender.state.profile is not None
        except Exception:
            computed = False
        if not computed:
            return
        self.layer.hub.unsubscribe(self, ComputationEndedMessage)
        self.fit(self.viewer)


def _fit_spectrum(viewer, group):
    """Fit the spectrum panel to the point's spectrum, now and as the point moves (`_Refit`)."""
    data = viewer.state.reference_data
    if data is None:
        return  # the panel could not add the raster
    _fit(viewer)
    viewer.toolbar.actions["mpl:home"].triggered.connect(lambda *_: _fit(viewer))  # Home resumes the refits (D98)
    [subset] = [subset for subset in group.subsets if subset.data is data]
    viewer._solar_fit = _Refit(viewer, subset)  # the hub holds its listeners weakly


class _Cut(HubListener):
    """
    Keep a cut's subset group along ``axis`` at the point's other axes, on the wavelength or band its map ``band`` shows
    (without one, a spectrum of ``data``), and the axes of ``at`` at its indices (D58, #183); it stays put while the
    point is off the data's file or the map shows other data.
    """

    def __init__(self, group, point, band, axis, data=None, at=None):
        self.group, self.point, self.band, self.axis, self.at = group, point, band, axis, dict(at or {})
        self.data = data if band is None else band.state.reference_data
        if band is not None:
            band.state.add_callback("slices", self.refresh)
        self.data.hub.subscribe(self, SubsetUpdateMessage, handler=self.refresh, filter=self._moved)
        self.data.hub.subscribe(self, SubsetDeleteMessage, handler=self._deleted)
        self.refresh()

    def _moved(self, message):
        return getattr(message.subset, "group", None) is self.point and message.subset.data is self.data

    def _deleted(self, message):
        """
        Stop once the group is deleted, which the band and the point would go on setting: glue-qt 0.4.2's style editors
        keep its subsets' layer states, so the group and this `_Cut` are not freed.
        """
        if getattr(message.subset, "group", None) is self.group:
            if self.band is not None:
                self.band.state.remove_callback("slices", self.refresh)
            self.data.hub.unsubscribe_all(self)

    def refresh(self, *_):
        point, data = self.point.subset_state, self.data
        if not isinstance(point, PixelSubsetState) or not _same_file(point.reference_data, data):
            return
        [wavelength] = _spectral_axes(data)
        slices = list(point.slices)
        if any(s.start is None for i, s in enumerate(slices) if i not in (self.axis, wavelength)):
            return  # a click before the coordinator gives it the axes it was not clicked on (`Coordinator._pin`)
        if self.band is not None:
            state = self.band.state
            if state.reference_data is not data or len(state.slices) != data.ndim:
                return
            band = getattr(state.slices[wavelength], "slice", state.slices[wavelength])
            slices[wavelength] = band if isinstance(band, slice) else slice(band, band + 1)
        slices[self.axis] = slice(None)
        for axis, index in self.at.items():
            slices[axis] = slice(index, index + 1)
        if slices != getattr(self.group.subset_state, "slices", None):
            self.group.subset_state = SliceSubsetState(data, slices)


def _check_cut(viewer):
    """Raise why the Image viewer ``viewer`` has no cut through the point (`_cut`)."""
    data = viewer.state.reference_data
    if _role(data) != "raster" or _spectral_axes(data) & _shown(viewer.state):  # with a wavelength slider
        raise ValueError("Choose it on the map of a raster, whose wavelength or band it averages.")
    point = coordinator(viewer.session.data_collection).point
    if point is None or not _same_file(point.reference_data, data):
        raise ValueError(f"Select a point on {data.label} first.")


def _cut(viewer, axis, label):
    """
    Open a Profile of the cut through the point along ``axis``, over the wavelength or band ``viewer`` shows, as the new
    subset group ``label`` that a `_Cut` keeps (D58).
    """
    _check_cut(viewer)
    app, data = viewer.session.application, viewer.state.reference_data
    coord = coordinator(app.data_collection)
    title = f"{_window(data)[0] or data.label} {label.lower()}"
    cut = partial(_Cut, point=coord.group, band=viewer, axis=axis)
    return _cut_profile(app, label, cut, data.pixel_component_ids[axis], title)


def _cut_profile(app, label, cut, x_att, title):
    """
    A Profile, the mean, NaN left out, against ``x_att``, titled ``title``, of the new subset group ``label`` that
    ``cut(group)``, a `_Cut`, keeps, removed from the other viewers open then.
    """
    group = _new_group(app.session, app.data_collection, label=label)
    # glue 1.27.0 profiles a slice subset with only its band's samples, which a spectrum panel cannot draw
    for viewers in app.viewers:
        for other in viewers:
            _show(other, group, False)
    group._solar_cut = cut(group)  # until the group is deleted
    profile = app.new_data_viewer(ProfileViewer)
    profile.state.function = "mean"
    profile.add_subset(next(subset for subset in group.subsets if subset.data is group._solar_cut.data))
    profile.state.x_att = x_att
    profile.state.title = title
    _fit_spectrum(profile, group)
    return profile


def _curve(source, raster, pixel, band):
    """
    The times and values of ``source`` at ``pixel`` of ``raster`` (wavelength aside, D53): a raster window's along its
    first axis, the mean, NaN left out, over the wavelength pixels ``band``, as a cut's Profile (#183); a slit-jaw
    image's at the raster pixel's place in each frame at the nearest exposure or scan, NaN past half a cadence (D7) or
    off the frame.
    """
    main = source.main_components[0]
    if _role(source) == "raster":
        view = (slice(None), *pixel[1:])
        values = compute_statistic("mean", source[main, (*view, band)], axis=-1)
        return source[source.id["Time"], (*view, band.start)], values
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
    raster's step, so that a drag or playback does not wait for them. Each stops once it or its dataset leaves the data
    collection, and all once the raster does.
    """

    def __init__(self, coordinator, group, raster):
        super().__init__()
        self.coordinator, self.group, self.raster = coordinator, group, raster
        self.curves, self.pixel = [], None  # (curve, its dataset, its wavelength pixels), and the pixel they show
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.refresh)

    def point(self):
        return _curve_pixel(self.group, self.raster)

    def _synced(self, *_):
        collection = self.coordinator.data_collection
        self.curves = [entry for entry in self.curves if entry[0] in collection and entry[1] in collection]
        if not self.curves or self.raster not in collection:
            self.coordinator.remove_listener(self._synced)
        elif self.point() not in (None, self.pixel):
            self._timer.start()

    def refresh(self):
        pixel = self.point()
        if pixel in (None, self.pixel):
            return
        self.pixel = pixel
        for curve, source, band in self.curves:
            times, values = _curve(source, self.raster, pixel, band)
            curve.update_components({curve.id["Time"]: times, curve.id["Value"]: values})


def _curve_pixel(group, raster):
    """The pixel of ``group``'s point on ``raster``'s file, its wavelength left out and, along time, 0, or None."""
    state = group.subset_state
    if not isinstance(state, PixelSubsetState) or not _same_file(state.reference_data, raster):
        return None
    pixel = tuple(s.start for s in state.slices[:-1])  # IRIS wavelengths are the last axis
    if None in pixel:
        return None  # a click before the coordinator gives it the axes it was not clicked on (`Coordinator._pin`)
    return (0, *pixel[1:]) if _time_axis(raster) == 0 else pixel


def _curve_sources(app):
    """
    The point's raster, its pixel (`_curve_pixel`) and the light curves' datasets that the point's quicklook shows, or
    without one the raster and every slit-jaw image: each window of its file with a time axis, then one slit-jaw image
    a channel (`_pick_sjis`); ValueError for none (D53).
    """
    collection = app.data_collection
    coord = coordinator(collection)
    raster = getattr(coord.point, "reference_data", None)
    pixel = _curve_pixel(coord.group, raster) if _role(raster) == "raster" else None
    if pixel is None:
        raise ValueError("Select a point on a raster first.")
    points = getattr(app, "_solar_points", {})
    tab = next((viewers for i, viewers in enumerate(app.viewers) if points.get(app.tab(i)) is coord.group), None)
    if tab is None:
        shown = {raster, *(data for data in collection if _role(data) == "sji")}
    else:
        shown = {getattr(viewer.state, "reference_data", None) for viewer in tab if not _off(viewer)}
    shown = [data for data in collection if data in shown]  # in data collection order
    key = observation_key(raster)
    sources = [data for data in shown if _same_file(data, raster) and _time_axis(data) == 0]
    sjis = [data for data in shown if _role(data) == "sji" and observation_key(data) == key and _placeable(data)]
    sources += _pick_sjis(sjis)[0]
    if not sources:
        raise ValueError(f"No window of {raster.label}'s file with exposures or scans, nor slit-jaw image, is shown.")
    return raster, pixel, sources


def _point_curves(viewer):
    """
    Add the light curves at the point (`_curve_sources`, `_curve`) as 1-D datasets of ``Time`` and ``Value``, linked as
    the same and with their data's OBSID and STARTOBS for the master's exposure mark, in a new Scatter viewer; they
    follow the point (`_PointCurves`, D53, D90, #208).
    """
    app = viewer.session.application
    collection = app.data_collection
    coord = coordinator(collection)
    raster, pixel, sources = _curve_sources(app)
    follower = _PointCurves(coord, coord.group, raster)
    for i, source in enumerate(sources):
        if _role(source) == "raster":
            [axis] = _spectral_axes(source)
            band = coord._band(source, axis, _line_core(source))  # kept, as the label says, at later band changes
            wave = _wavelengths(source)[0][band]
            at = f"{wave[0]:.2f}–{wave[-1]:.2f}" if len(wave) > 1 else f"{wave[0]:.2f}"
            label = f"{source.label} light curve {at}"
        else:
            band, label = None, f"{source.label} light curve"
        times, values = _curve(source, raster, pixel, band)
        curve = Data(label=label, Time=times, Value=values)
        curve.get_component("Value").units = source.get_component(source.main_components[0]).units
        curve.meta = {name: source.meta[name] for name in ("OBSID", "STARTOBS")}
        curve.style.color = to_hex(f"C{i % 10}")  # glue gives every dataset the same gray
        follower.curves.append((curve, source, band))
    follower.pixel = pixel
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
    units = ", ".join(unit for unit in dict.fromkeys(curve.get_component("Value").units for curve in curves) if unit)

    def label(text):  # glue's 'Value', set again as layers join, as the curves' units (D90)
        if units and text == "Value":
            plot.state.y_axislabel = units

    plot.state.add_callback("y_axislabel", label)
    label(plot.state.y_axislabel)
    for layer in plot.state.layers:
        if isinstance(layer.layer, Data):
            layer.markers_visible, layer.line_visible = False, True
    for group in coord._owners:
        _show(plot, group, False)  # the quicklooks' points, which move at every click (`_show_point`)
    coord.add_listener(follower._synced)  # which keeps it
    coord._timer.start()  # the time master's exposure, at once
    return plot


# the raster panels' lines, the last on top: the point's thin, in the color of glue's crosshair, the others as a
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
    A quicklook's lines (D23, D39, #118): the point on panels showing wavelength, the maps' wavelengths and the time
    master's time on the wavelength panel and the wavelengths on the spectrum panel, whose x range the wavelength panel
    takes; plain matplotlib lines, which sessions leave out.
    """

    def __init__(self, coordinator, group, panels, spectrum, tab):
        super().__init__(tab)  # kept, and deleted, with the tab
        self.coordinator, self.group, self.panels, self.spectrum = coordinator, group, panels, spectrum
        self.data = panels[0].state.reference_data
        [self.axis] = _spectral_axes(self.data)
        self.along = 0 if _role(self.data) else (_cube_axes(self.data) or (None,))[0]
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

    @property
    def key(self):
        """The observation of the panels' data, as it is now: an SST cube's changes once linked to IRIS data."""
        return observation_key(self.data)

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
            if viewer._closed or _off(viewer):  # one turned off is refreshed once turned on (`_turn`)
                continue
            state, xy = viewer.state, dict.fromkeys(lines)  # None: hidden
            if viewer in panels and axis in _shown(state):
                [other] = _shown(state) - {axis}
                if point is not None and point.slices[other].start is not None:
                    xy["point"] = _across(state, other, [point.slices[other].start])
                if other == self.along and wavelengths:
                    xy["wavelength"] = _across(state, axis, wavelengths)
                if other == self.along and time is not None:
                    xy["time"] = _across(state, other, [time])
            if any([_place(lines[name], xy[name]) for name in lines]):  # every line, not up to the first changed
                viewer.figure.canvas.draw_idle()
        values, state = self._spectrum_x(), self.spectrum.state
        marks = None
        if values is not None and wavelengths:
            x = UnitConverter().to_unit(self.data, state.x_att, values[wavelengths], state.x_display_unit)
            marks = _segments(x, (0, 1))
        if not _off(self.spectrum) and _place(self.marks, marks) and not self.spectrum._closed:
            self.spectrum.figure.canvas.draw_idle()

    def _copy_range(self, *_):
        """Give each open panel showing wavelength against step, exposure or scan the spectrum panel's x range."""
        values, state = self._spectrum_x(), self.spectrum.state
        if values is None or None in (state.x_min, state.x_max):
            return
        ends = np.array([state.x_min, state.x_max])
        ends = UnitConverter().to_native(self.data, state.x_att, ends, state.x_display_unit)
        if np.allclose(np.diff(values), values[1] - values[0]):  # IRIS wavelengths are linear in pixel
            ends = (ends - values[0]) / (values[-1] - values[0]) * (len(values) - 1)
        else:  # an SST cube's tunings are not, nor can its pixels be found past them
            ends = np.interp(ends, values, np.arange(len(values)))
        for viewer in self._raster_panels():
            panel = viewer.state
            if _shown(panel) == {self.axis, self.along}:
                xy = "x" if panel.x_att.axis == self.axis else "y"
                with delay_callback(panel, f"{xy}_min", f"{xy}_max"):
                    setattr(panel, f"{xy}_min", ends[0])
                    setattr(panel, f"{xy}_max", ends[1])


def _arrange(tab, viewers):
    """
    Lay out the panels shown (D15): raster panels, then slit-jaw images and spectrum, other windows' in fours, or a
    cube's ``rows``, at least 280 pixels tall each, so that two IRIS rows or an SST cube's three keep the Point window
    and Panels list below in sight at 1800×1100 (D83). Out of sight, they draw once in sight (`_draw_in_sight`).
    """

    def shown(panels):
        return [viewer for viewer in panels if not viewer._closed and not _off(viewer)]

    if "rows" in viewers:
        rows = [shown(row) for row in viewers["rows"]]
    else:
        others = shown(viewer for panels in viewers["windows"] for viewer in panels.values())
        rows = [
            shown(viewers[role] for role in ("map", "spectrogram", "wavelength") if role in viewers),
            shown(viewers["sji"] + [viewers[role] for role in ("spectrum",) if role in viewers]),
            *(others[i : i + 4] for i in range(0, len(others), 4)),
        ]
    rows = [row for row in rows if row]
    strip = {
        type(sub.widget()): sub for sub in tab.subWindowList() if isinstance(sub.widget(), (_PointWindow, _Panels))
    }
    if _PointWindow in strip:
        strip[_PointWindow].widget().refresh()  # the rows of the panels shown, which its height follows
    tall = max((sub.sizeHint().height() for sub in strip.values()), default=0)  # no scroll bar in the list
    size = tab.maximumViewportSize()  # without the scroll bars, which the layout decides
    height = max(size.height() - tall, 280 * max(len(rows), 2))
    width = max(size.width(), 1200)
    bar = tab.verticalScrollBar()
    if height + tall > size.height() and not tab.style().styleHint(QStyle.SH_ScrollBar_Transient, None, bar):
        width = max(size.width() - bar.sizeHint().width(), 1200)  # beside its vertical scroll bar
    wide = strip[_Panels].sizeHint().width() if _Panels in strip else 0
    for kind, x, w in ((_PointWindow, 0, width - wide), (_Panels, width - wide, wide)):
        if kind in strip:
            strip[kind].setGeometry(x, height, w, tall)
    for r, row in enumerate(rows):
        for c, viewer in enumerate(row):
            zoom, state = vars(viewer).get("_solar_zoom"), viewer.state
            kept = zoom and zoom[1] == (state.x_min, state.x_max, state.y_min, state.y_max)  # not panned or zoomed
            viewer.move(c * width // len(row), r * height // len(rows))
            viewer.viewer_size = (width // len(row), height // len(rows))
            viewer.figure.canvas._draw_idle = partial(_draw_in_sight, viewer.figure.canvas, tab)
            if kept:
                _zoom(viewer, *zoom[0])


def _draw_in_sight(canvas, tab):
    """
    matplotlib's deferred draw of ``canvas`` unless its panel is shown in ``tab`` but out of sight, which matplotlib
    would draw at every step: the draw stays due until Qt paints it in sight (#235, #254; register).
    """
    try:
        out_of_sight = canvas.isVisibleTo(tab) and canvas.visibleRegion().isEmpty()  # none while the tab is hidden
    except RuntimeError:  # closed since the draw was posted, which matplotlib's own then skips
        out_of_sight = False
    if not out_of_sight or canvas.testAttribute(Qt.WA_WState_InPaintEvent):  # a paint, such as a grab's, draws it
        type(canvas)._draw_idle(canvas)


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
        return "leads time" + (f", step {value}" if value is not None else "")
    if kind == "match":
        return f"Δt {value / np.timedelta64(1, 's'):+.1f} s"
    # a master in a gap of data regridded on time has no time, so no offset
    return "NO MATCH" + ("" if np.isnat(value) else f" Δt = {value / np.timedelta64(1, 's'):+.1f} s")


_POINT_COLUMNS = ("Dataset", "Pixel", "Position", "Time", "Exposure", "Value", "Time sync")
# the Position column's coordinates, in this order whatever the dataset's own
_POSITION = ("custom:pos.helioprojective.lon", "custom:pos.helioprojective.lat", "em.wl")


class _PointWindow(QTableWidget):
    """
    A quicklook's read-only 'Point' window (D38, #113): per dataset its Image panels show, the point's pixel, position,
    time, exposure, value and time sync as the readouts give them, refreshed once a change while its tab is shown.
    """

    def __init__(self, coordinator, group, data, viewers):
        super().__init__(0, len(_POINT_COLUMNS))
        self.coordinator, self.group, self.data, self.viewers = coordinator, group, data, viewers
        self.setHorizontalHeaderLabels(_POINT_COLUMNS)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)  # sized by `_fit_labels`
        self.horizontalHeader().setStretchLastSection(True)  # the width left to the time sync
        self.setTextElideMode(Qt.ElideMiddle)  # on one line, keeping their ends, such as 'scan 0' or 'stack'
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_labels()

    def _fit_labels(self):
        """Make the labels as wide as the widest, or as the readouts after them leave, elided in the middle (P8)."""
        header = self.horizontalHeader()
        widths = [max(self.sizeHintForColumn(i), header.sectionSizeHint(i)) for i in range(self.columnCount())]
        left = self.viewport().width() - sum(widths[1:])
        self.setColumnWidth(0, max(min(widths[0], left), header.minimumSectionSize()))

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
        self._fit_labels()

    def _cells(self, point, data, viewers):
        """The point's pixel, position, time, exposure and value in ``data``, and its time sync."""
        if observation_key(data) != observation_key(self.data):  # an SST cube's changes once linked to IRIS data
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
        elif _role(data) == "sst":  # a cube of intensities has no Stokes axis
            names = ("scan", "Stokes", "λ", "y", "x") if data.ndim == 5 else ("scan", "λ", "y", "x")
        elif _role(data) is None and (axes := _cube_axes(data)):  # a cube of neither instrument
            named = dict(zip(axes, ("time", "Stokes", "λ", "y", "x")))  # and None, those it lacks
            names = [named[axis] for axis in range(data.ndim)]
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
        if time is not None and data.get_kind(time) != "datetime":  # such as a FITS cube's time coordinate
            time = None
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


class _Panels(QTreeWidget):
    """
    A quicklook's 'Panels' list (D66, #228): a box per panel, or per label of panels, turning them on or off (`_turn`),
    laid out once for changes made together. A panel not made yet, its `_Panel` row, is unticked: ``make`` makes its
    label's panels once one is ticked (D83). It gives every Image panel on the axes one was given (`show_axes`).
    """

    def __init__(self, entries, group, arrange, make):
        super().__init__()
        self.group, self.arrange, self.make, self.panels = group, arrange, make, []  # (its item, panel or row)
        self.setHeaderHidden(True)
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)  # as wide as its labels
        self.axes = False  # every Image panel's, as `_image` opens them (D71)
        self._followed = []  # the Image panels whose axes it follows (`_follow`)
        self.destroyed.connect(partial(self._detach, self._followed, self._follow_axes))  # closed alone or with its tab
        for entry in entries:
            label, panels = entry if isinstance(entry, tuple) else (None, [entry])
            parent = self.invisibleRootItem()
            if label is not None:
                parent = QTreeWidgetItem(parent, [label])
                parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            for panel in panels:
                made = not isinstance(panel, _Panel)
                item = QTreeWidgetItem(parent, [panel.state.title if made else panel.title])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Checked if made else Qt.Unchecked)
                self.panels.append((item, panel))
                if made:
                    self._follow(panel)
        # a label's box changes each of its panels' boxes
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self.apply)
        self.itemChanged.connect(lambda *_: self._timer.start())

    def _follow(self, panel):
        """Take ``panel`` off the list once closed, and follow an Image panel's axes, as its 'Hide axes' sets them."""
        panel.window_closed.connect(self._forget)
        if isinstance(panel, ImageViewer):
            panel.state.add_callback("show_axes", self._follow_axes)
            self._followed.append(panel)

    @staticmethod
    def _detach(images, follow):
        """Stop ``follow`` following the axes of ``images``, which may stay open."""
        for panel in images:
            panel.state.remove_callback("show_axes", follow)

    def _images(self):
        """The Image panels on: the spectrum panels have plain Matplotlib axes, which stay."""
        return [panel for _, panel in self.panels if isinstance(panel, ImageViewer) and not _off(panel)]

    def _follow_axes(self, shown):
        """Give every Image panel on the axes one of them was given; one off, which a session sets too, waits (`apply`)."""
        if shown != self.axes and any(panel.state.show_axes == shown for panel in self._images()):
            self.show_axes(shown)

    def show_axes(self, shown):
        """Show or hide the axes of every Image panel on, so that 'Hide axes' on one is the quicklook's (D83)."""
        self.axes = shown
        for panel in self._images():
            panel.state.show_axes = shown

    def apply(self):
        """Turn each panel on or off as its box says, then lay out the panels shown if any changed."""
        self._timer.stop()  # if called directly: the pending call would run mid-way, as making panels processes events
        tab = self.parentWidget().mdiArea()
        active, changed = tab.activeSubWindow(), False
        # Qt activates each window shown, and glue-qt would restyle every viewer and fill its side panels for each
        blocked = tab.blockSignals(True)
        try:
            ticked = [row for item, row in self.panels if isinstance(row, _Panel) and item.checkState(0) == Qt.Checked]
            for name in dict.fromkeys(row.window for row in ticked):  # each window's panels, made once
                made = self.make(name)
                self.panels = [(item, made.get(panel, panel)) for item, panel in self.panels]
                for panel in made.values():
                    self._follow(panel)
                    panel.set_focus(False)  # as glue-qt shows a viewer not active, which these signals would tell it
                changed = True
            for item, panel in self.panels:
                on = item.checkState(0) == Qt.Checked
                if not isinstance(panel, _Panel) and on == _off(panel):
                    _turn(panel, on, self.group)
                    changed = True
            if active is not None and not active.isHidden():
                tab.setActiveSubWindow(active)
        finally:
            tab.blockSignals(blocked)
        if tab.activeSubWindow() is not active:  # the active panel turned off
            tab.subWindowActivated.emit(tab.activeSubWindow())
        if changed:
            self.show_axes(self.axes)  # the panels made or turned on
            self.arrange()

    def _forget(self):
        """Take the panel closed by hand off the list, with its label once it has no other panel."""
        panel = self.sender()
        root = self.invisibleRootItem()
        for item in [item for item, each in self.panels if each is panel]:
            parent = item.parent() or root
            parent.removeChild(item)
            if parent is not root and not parent.childCount():
                root.removeChild(parent)
        self.panels = [(item, each) for item, each in self.panels if each is not panel]


def _add_window(tab, widget, title):
    """Add ``widget`` to ``tab`` in a window of its own, titled ``title``, and return the window."""
    sub = QMdiSubWindow()
    sub.setWidget(widget)
    sub.setAttribute(Qt.WA_DeleteOnClose)  # with its tab too, as glue closes every window of a tab it closes
    sub.setWindowTitle(title)
    sub.setWindowIcon(QApplication.windowIcon())  # glue-solar's, as on the panels
    tab.addSubWindow(sub)
    sub.show()
    return sub
