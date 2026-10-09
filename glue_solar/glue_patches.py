"""
Gated fixes for glue-core and glue-qt bugs that IRIS data hits.

Each fix installs, or acts, only when a probe finds the bug, and names the upstream change that retires it.
"""

import builtins
import os
from functools import cache
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import dask.array as da
import glue.utils.matplotlib
import numpy as np
from echo.qt import connect
from echo.qt.connect import UserDataWrapper
from glue.config import data_exporter
from glue.core import Data, DataCollection, Subset, component_link, coordinate_helpers
from glue.core.command import ApplySubsetState
from glue.core.component import DaskComponent, DerivedComponent
from glue.core.component_link import ComponentLink
from glue.core.coordinate_helpers import unbroadcast
from glue.core.data_exporters import gridded_fits
from glue.core.edit_subset_mode import EditSubsetMode
from glue.core.exceptions import IncompatibleAttribute
from glue.core.link_helpers import LinkSame, LinkSameWithUnits
from glue.core.state import GlueSerializeError, GlueSerializer, GlueUnSerializer, loader, saver
from glue.core.subset import SubsetState
from glue.utils import defer_draw
from glue.viewers.histogram import state as histogram_state
from glue.viewers.histogram import viewer as histogram_viewer
from glue.viewers.image.layer_artist import ImageSubsetLayerArtist
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice
from glue.viewers.matplotlib import viewer as matplotlib_viewer
from glue.viewers.profile.state import ProfileLayerState, ProfileViewerState
from glue.viewers.scatter import layer_artist as scatter_layer_artist
from glue.viewers.scatter import viewer as scatter_viewer
from glue_qt.plugins.tools.pv_slicer import pv_slicer
from glue_qt.utils import colors
from glue_qt.viewers.common.data_slice_widget import SliceWidget
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.matplotlib.widget import MplCanvas
from matplotlib import colormaps, dates, rcParams
from matplotlib.backend_bases import key_press_handler
from matplotlib.colors import Colormap, ListedColormap
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from qtpy import QtCore, QtGui, QtWidgets

import astropy.units as u
from astropy.io import fits
from astropy.visualization.wcsaxes import WCSAxes
from astropy.wcs import WCS

from sunpy.visualization.colormaps import cmlist

__all__ = [
    "aggregate_slice_init",
    "apply_subset_state",
    "canvas_init",
    "close_event",
    "datetime64_to_mpl",
    "derived_datetime",
    "export_fits",
    "load_link_with_units",
    "load_quantity",
    "find_combo_data",
    "mpl_to_datetime64",
    "needs_axis_label_workaround",
    "needs_combo_match_workaround",
    "needs_crosshair_workaround",
    "needs_date_epoch_workaround",
    "needs_derived_datetime_workaround",
    "needs_empty_collapse_workaround",
    "needs_fits_export_dask_workaround",
    "needs_icon_cache_workaround",
    "needs_inverse_workaround",
    "needs_link_restore_workaround",
    "needs_pixel_point_workaround",
    "needs_profile_restore_workaround",
    "needs_pv_dask_workaround",
    "needs_pv_slice_workaround",
    "needs_redo_workaround",
    "needs_reference_crosshair_workaround",
    "pv_slice_from_path",
    "save_link_with_units",
    "save_quantity",
    "sync_pv_slice",
    "update_icons",
    "update_x_axislabel",
    "update_y_axislabel",
    "world2pixel_single_axis",
]

_original_world2pixel_single_axis = coordinate_helpers.world2pixel_single_axis


def world2pixel_single_axis(wcs, *world, pixel_axis=None):
    """
    glue-core's ``world2pixel_single_axis`` with the fix from glue-viz/glue#2598 (draft).

    glue-core 1.27.0 keeps only the world axes that depend on ``pixel_axis`` and collapses the others
    to their first element. The longitude and latitude of an IRIS slit-jaw image depend on time, so
    every frame was inverted at exposure 0. The fix also keeps the world axes that share a pixel axis
    with those; the rest is unchanged from glue-core.
    """
    if pixel_axis is None:
        raise ValueError("pixel_axis needs to be set")
    if np.size(world[0]) == 0:
        return np.array([], dtype=float)
    original_shape = world[0].shape
    matrix = wcs.axis_correlation_matrix
    world_dep = matrix[:, pixel_axis].copy()
    for _ in range(matrix.shape[0]):  # transitive closure
        world_dep |= (matrix & matrix[world_dep].any(axis=0)).any(axis=1)
    world = np.broadcast_arrays(*[unbroadcast(w) if dep else w.flat[0] for w, dep in zip(world, world_dep)])
    # astropy/astropy#12154: a 1D WCS cannot take arbitrary shapes
    if len(world) == 1 and world[0].ndim > 1:
        result = wcs.world_to_pixel_values(world[0].ravel()).reshape(world[0].shape)
    else:
        result = wcs.world_to_pixel_values(*world)
        if len(world) > 1:
            result = result[pixel_axis]
    return np.broadcast_to(result, original_shape)


def needs_inverse_workaround(func=_original_world2pixel_single_axis):
    """
    Whether ``func`` inverts a world axis that depends on time at the first time only.
    """
    # Pixel (x, y, t) -> world (x + t, y, t), as an IRIS slit-jaw image's pointing moves with time
    wcs = SimpleNamespace(
        axis_correlation_matrix=np.array([[1, 1, 1], [1, 1, 1], [0, 0, 1]], dtype=bool),
        world_to_pixel_values=lambda x, y, t: (x - t, y, t),
    )
    x = func(wcs, np.array([10.0, 11.0]), np.zeros(2), np.array([0.0, 1.0]), pixel_axis=0)
    return not np.allclose(x, 10)


if needs_inverse_workaround():
    coordinate_helpers.world2pixel_single_axis = world2pixel_single_axis
    # glue.core.component_link imports it by name
    component_link.world2pixel_single_axis = world2pixel_single_axis


_original_sync_slice = pv_slicer.PVSliceWidget._sync_slice


@defer_draw
def sync_pv_slice(self, event):
    """
    glue-qt's ``PVSliceWidget._sync_slice``, keeping the Image viewer's own numbers on its displayed axes.

    A click in glue-qt 0.4.2's PV slice window moves the Image viewer to the clicked slice, but writes
    WCSAxes' ``'x'`` and ``'y'`` markers into ``state.slices`` on the displayed axes. They then break the
    next axis change (``int('y')`` in the slice sliders) and every reader of ``slices``. No upstream fix
    exists yet.
    """
    s = list(self._slc)
    _, _, z = self._pos_in_parent(event)
    s[pv_slicer._slice_index(self._parent.state.reference_data, s)] = int(z)
    current = self._parent.state.slices
    self._parent.state.slices = tuple(current[i] if isinstance(value, str) else value for i, value in enumerate(s))


def needs_pv_slice_workaround(func=_original_sync_slice):
    """Whether ``func`` writes ``'x'`` or ``'y'`` into the Image viewer's slices."""
    state = SimpleNamespace(reference_data=SimpleNamespace(ndim=3), slices=(0, 0, 0))
    widget = SimpleNamespace(_slc=[0, "y", "x"], _parent=SimpleNamespace(state=state), _pos_in_parent=lambda e: (0, 0, 1))
    func(widget, None)
    return any(isinstance(value, str) for value in state.slices)


if needs_pv_slice_workaround():
    pv_slicer.PVSliceWidget._sync_slice = sync_pv_slice


def _dask_probe(shape):
    """A dataset whose ``values`` are a glue DaskComponent of zeros, as lazily loaded IRIS values are."""
    data = Data(label="probe")
    data.add_component(DaskComponent(da.zeros(shape, chunks=2)), "values")
    return data


class _NumpyValues:
    """``data``, whose values come out as NumPy arrays."""

    def __init__(self, data):
        self._data = data

    def __getattr__(self, name):
        return getattr(self._data, name)

    def __getitem__(self, key):
        return np.asarray(self._data[key])


_original_slice_from_path = pv_slicer._slice_from_path


def pv_slice_from_path(x, y, data, attribute, slc):
    """
    glue-qt's PV slice (``_slice_from_path``) of a dataset of a dask array, as lazily loaded IRIS data are.

    glue-qt 0.4.2 passes the values it reads, here a dask array, to pvextractor, which takes anything but a NumPy
    array for a spectral cube and fails on its missing WCS. The slice reads the whole cube, as for eager data.
    The probe runs on the first slice, not at plugin load: pvextractor imports spectral-cube where it is installed
    (0.3-0.4 s). Retired once glue-qt passes NumPy values; no upstream fix exists yet.
    """
    if _pv_needs_workaround():
        data = _NumpyValues(data)
    return _original_slice_from_path(x, y, data, attribute, slc)


def needs_pv_dask_workaround(func=_original_slice_from_path):
    """Whether ``func`` fails on a dataset of a glue DaskComponent."""
    data = _dask_probe((3, 4, 5))
    try:
        func(np.array([0.0, 3.0]), np.array([1.0, 1.0]), data, data.id["values"], [0, "y", "x"])
    except Exception:  # noqa: BLE001 - any failure means the patch is needed
        return True
    return False


@cache
def _pv_needs_workaround():
    return needs_pv_dask_workaround()


pv_slicer._slice_from_path = pv_slice_from_path


_original_fits_writer = gridded_fits.fits_writer


def export_fits(filename, data, components=None, data_header=None, extensions=()):
    """
    glue-core's "FITS (1 component/HDU)" exporter (``fits_writer``), reading each component as a NumPy array.

    glue-core 1.27.0 sets the values outside an exported subset to NaN in place, which a dask array, as a lazily
    loaded IRIS component is, refuses with ``IndexError``. The rest is glue-core's, except that a subset's unsigned
    components, such as the mask, are exported unmasked where glue-core fails on them. Its registration as glue's
    exporter is retired once glue exports a DaskComponent's subset, no upstream fix exists yet; the function stays for
    `glue_solar.sources.iris.export_iris_fits`, with ``data_header`` in place of the data's astropy WCS header and
    ``extensions`` appended.
    """
    mask = None
    if isinstance(data, Subset):
        mask = data.to_mask()
        data = data.data
    if data_header is None:
        data_header = data.coords.to_header() if isinstance(data.coords, WCS) else fits.Header()
    hdus = fits.HDUList()
    for cid in data.main_components + data.derived_components:
        if (components is not None and cid not in components) or data.get_kind(cid) != "numerical":
            continue
        values = np.asarray(data[cid])
        blank = None
        if mask is not None:
            values = values.copy()
            if values.dtype.kind == "f":
                values[~mask] = np.nan
            elif values.dtype.kind == "i":
                blank = np.iinfo(values.dtype).min
                values[~mask] = blank
        if isinstance(data, Data):
            header = gridded_fits.make_component_header(data.get_component(cid), data_header)
        else:
            header = fits.Header()
        if blank is not None:
            header["BLANK"] = blank
        hdus.append(fits.ImageHDU(values, name=cid.label, header=header))
    for hdu in extensions:
        hdus.append(hdu)
    hdus.writeto(filename, overwrite=True)


def needs_fits_export_dask_workaround(func=_original_fits_writer):
    """Whether ``func`` fails to export a subset of a dataset of a glue DaskComponent."""
    data = _dask_probe((2, 2))
    subset = data.new_subset(PixelSubsetState(data, [slice(0, 1), slice(None)]))
    # to a file: astropy writes no dask array to an in-memory one, so a fix that keeps dask would still fail there
    with TemporaryDirectory() as directory:
        try:
            func(os.path.join(directory, "probe.fits"), subset)
        except Exception:  # noqa: BLE001 - any failure means the patch is needed
            return True
    return False


if needs_fits_export_dask_workaround():
    for i, exporter in enumerate(data_exporter.members):
        if exporter.function is _original_fits_writer:
            data_exporter.members[i] = exporter._replace(function=export_fits)


_original_to_linked_pixel_coords = PixelSubsetState._to_linked_pixel_coords


def _to_linked_pixel_coords(self, data):
    """
    glue-core's ``PixelSubsetState._to_linked_pixel_coords``, with a point off ``data`` incompatible with it.

    glue-core 1.27.0 rounds the point's linked pixel position with ``int()``, so a point that lies
    outside a linked dataset, where the position is NaN, raises ``ValueError`` and glue shows an error
    box, for its crosshair or its spectrum. Retired by the ``core-translate-pixel`` report's fix.
    """
    try:
        return _original_to_linked_pixel_coords(self, data)
    except ValueError:  # int() of NaN: the point is not on ``data``
        raise IncompatibleAttribute() from None


def needs_pixel_point_workaround(method=_original_to_linked_pixel_coords):
    """Whether ``method`` raises ``ValueError`` for a Pixel point with no finite pixel in a linked dataset."""
    first, second = Data(x=np.zeros((2, 2)), label="first"), Data(y=np.zeros((2, 2)), label="second")
    collection = DataCollection([first, second])
    for a, b in zip(first.pixel_component_ids, second.pixel_component_ids):
        collection.add_link(
            [ComponentLink([a], b, using=lambda v: v * np.nan), ComponentLink([b], a, using=lambda v: v * np.nan)]
        )
    try:
        method(PixelSubsetState(first, [slice(1, 2), slice(1, 2)]), second)
    except ValueError:
        return True
    except IncompatibleAttribute:
        pass
    return False


if needs_pixel_point_workaround():
    PixelSubsetState._to_linked_pixel_coords = _to_linked_pixel_coords


_original_apply_subset_state = ApplySubsetState.do


def apply_subset_state(self, session):
    """
    glue-core's ``ApplySubsetState.do``, whose Redo puts back the subset states its first run made.

    glue-core 1.27.0 applies the subset state again on Redo, to the edit subset and in the selection mode of then, and
    listeners rewrite it from the viewers of then: the quicklook places a slit-jaw click on the raster with the frame
    shown, so Redo after the frame moved gave another exposure or scan. A Redo whose subsets Undo deleted, as those of a
    new subset group, stays glue's. Retired by glue's ``ApplySubsetState`` keeping the subset states it made (report
    candidate).
    """
    made = getattr(self, "_solar_made", None)
    if made is None or any(subset not in subset.data.subsets for subset in made):
        _original_apply_subset_state(self, session)
        subsets = [subset for data in self.data_collection for subset in data.subsets]
        self._solar_made = {s: s.subset_state for s in subsets if s.subset_state is not self.old_states.get(s)}
        return
    self.old_states = {subset: subset.subset_state for data in self.data_collection for subset in data.subsets}
    for subset, state in made.items():
        getattr(subset, "group", subset).subset_state = state  # a group's, as glue's do sets it: one message a subset


def needs_redo_workaround(do=_original_apply_subset_state):
    """Whether ``do``, run again as Redo runs it, applies the subset state to the edit subset of then."""
    collection = DataCollection([Data(x=np.zeros(2), label="probe")])
    first, second = collection.new_subset_group(), collection.new_subset_group()
    mode = EditSubsetMode()
    mode.data_collection, mode.edit_subset = collection, [first]
    session = SimpleNamespace(edit_subset_mode=mode)
    command = ApplySubsetState(data_collection=collection, subset_state=SubsetState(), override_mode=None)
    do(command, session)
    made = first.subset_state
    command.undo(session)
    mode.edit_subset = [second]
    do(command, session)
    return first.subset_state is not made


if needs_redo_workaround():
    ApplySubsetState.do = apply_subset_state


_original_update_visual_attributes = ImageSubsetLayerArtist._update_visual_attributes


@defer_draw
def _update_visual_attributes(self, redraw=True):
    """
    glue-core's ``ImageSubsetLayerArtist._update_visual_attributes``, keeping a Pixel crosshair hidden
    where the point has no position.

    glue-core 1.27.0 hides the crosshair of a Pixel point that has no position on a displayed axis, as
    a raster point has none in wavelength, then shows it again here, at (0, 0) or where it last was.
    Retired by the ``core-pixel-crosshair`` fix (``wp0-core-image-artist-bugs``).
    """
    if not self.enabled:
        return
    _original_update_visual_attributes(self, redraw=False)
    if self._line_x.get_visible():
        viewer = self._viewer_state
        try:
            self.state.layer.subset_state.get_xy(viewer.reference_data, viewer.x_att.axis, viewer.y_att.axis)
        except IncompatibleAttribute:
            self._line_x.set_visible(False)
            self._line_y.set_visible(False)
    if redraw:
        self.redraw()


def needs_crosshair_workaround(method=_original_update_visual_attributes):
    """Whether ``method`` shows the Pixel crosshair of a point that has no position on a displayed axis."""
    data = Data(x=np.zeros((2, 2)), label="probe")
    point = PixelSubsetState(data, [slice(1, 2), slice(None)])  # no position along x
    image, line_x, line_y = Line2D([], []), Line2D([], [], visible=False), Line2D([], [], visible=False)
    artist = SimpleNamespace(
        enabled=True,
        image_artist=image,
        _line_x=line_x,
        _line_y=line_y,
        mpl_artists=[image, line_x, line_y],
        layer=SimpleNamespace(data=data),
        state=SimpleNamespace(visible=True, alpha=1.0, color="red", zorder=1, layer=SimpleNamespace(subset_state=point)),
        _viewer_state=SimpleNamespace(
            reference_data=data, x_att=data.pixel_component_ids[1], y_att=data.pixel_component_ids[0]
        ),
    )
    method(artist, redraw=False)
    return line_x.get_visible()


if needs_crosshair_workaround():
    ImageSubsetLayerArtist._update_visual_attributes = _update_visual_attributes


_original_update_data = ImageSubsetLayerArtist._update_data


@defer_draw
def _update_data(self):
    """
    glue-core's ``ImageSubsetLayerArtist._update_data``, placing a Pixel crosshair where the point lies in the
    viewer's reference data.

    glue-core 1.27.0 places each subset layer's crosshair at the point's pixel in the layer's own dataset, along the
    reference data's axes: a sunpy map linked to IRIS data and shown over a raster map adds a crosshair elsewhere, and
    over a slit-jaw image, which has one more axis, glue raises IndexError. Retired by the
    ``wp0-core-image-artist-bugs`` fix.
    """
    viewer, point = self._viewer_state, self.state.layer.subset_state
    try:
        if not isinstance(point, PixelSubsetState):
            raise IncompatibleAttribute()
        x, y = point.get_xy(viewer.reference_data, viewer.x_att.axis, viewer.y_att.axis)
    except IncompatibleAttribute:
        self._line_x.set_visible(False)
        self._line_y.set_visible(False)
    else:
        self._line_x.set_data([x, x], [0, 1])
        self._line_x.set_visible(True)
        self._line_y.set_data([0, 1], [y, y])
        self._line_y.set_visible(True)
    self.image_artist.invalidate_cache()


def needs_reference_crosshair_workaround(method=_original_update_data):
    """Whether ``method`` places the Pixel crosshair of a point that has no place in the viewer's reference data."""
    reference, data = Data(x=np.zeros((2, 2)), label="reference"), Data(y=np.zeros((2, 2)), label="probe")
    line_x, line_y = Line2D([], [], visible=False), Line2D([], [], visible=False)
    artist = SimpleNamespace(
        image_artist=SimpleNamespace(invalidate_cache=lambda: None),
        _line_x=line_x,
        _line_y=line_y,
        layer=SimpleNamespace(data=data),
        state=SimpleNamespace(layer=SimpleNamespace(subset_state=PixelSubsetState(data, [slice(1, 2)] * 2))),
        _viewer_state=SimpleNamespace(
            reference_data=reference, x_att=reference.pixel_component_ids[1], y_att=reference.pixel_component_ids[0]
        ),
    )
    method(artist)
    return line_x.get_visible()


if needs_reference_crosshair_workaround():
    ImageSubsetLayerArtist._update_data = _update_data


_original_update_axislabels = (ImageViewer.update_x_axislabel, ImageViewer.update_y_axislabel)


def _set_axislabel(viewer, axis):
    """Label the WCSAxes coordinate of the Image viewer's ``axis`` ('x' or 'y') with glue's label and style."""
    state = viewer.state
    data, att = state.reference_data, getattr(state, f"{axis}_att")
    index = "xy".index(axis)
    # glue's own mapping, as in its update_x_ticklabel, but not waiting for its _wcs_set: a restored viewer
    # sets its labels only once, on the axes of its first reset, before glue sets that flag
    if data is not None and att is not None and data.ndim - 1 - att.axis in viewer.axes.coords:
        index = data.ndim - 1 - att.axis
    viewer.axes.coords[index].set_axislabel(
        getattr(state, f"{axis}_axislabel"),
        weight=getattr(state, f"{axis}_axislabel_weight"),
        size=getattr(state, f"{axis}_axislabel_size"),
    )
    viewer.redraw()


@defer_draw
def update_x_axislabel(self, *event):
    """
    glue-qt's ``ImageViewer.update_x_axislabel``, labelling the WCSAxes coordinate of the x axis directly.

    glue-core 1.27.0 labels an Image viewer's axes with ``WCSAxes.set_xlabel`` and ``set_ylabel``, which
    place every tick at once to find the coordinate to label, and the next draw places them again. glue
    sets both labels twice whenever it resets the axes, as at each slit-jaw frame step, so that is four
    extra tick placements per step. The label goes to the coordinate glue already maps the axis to for
    its tick label sizes instead. That is the coordinate ``set_xlabel`` finds on the bottom spine, except
    where WCSAxes puts another one there, as latitude past a 45° roll: glue then names that one after
    the x axis, and here each coordinate keeps its own name. Retired by the ``wp0-perf-core-draw`` fix
    in glue-core, or by an astropy release whose ``set_xlabel`` places no ticks.
    """
    if not hasattr(self.axes, "coords"):  # not WCSAxes
        return _original_update_axislabels[0](self, *event)
    _set_axislabel(self, "x")


@defer_draw
def update_y_axislabel(self, *event):
    """glue-qt's ``ImageViewer.update_y_axislabel``, as `update_x_axislabel` is for the x axis."""
    if not hasattr(self.axes, "coords"):
        return _original_update_axislabels[1](self, *event)
    _set_axislabel(self, "y")


def needs_axis_label_workaround(updates=_original_update_axislabels):
    """Whether ``updates``, an Image viewer's x and y axis label updates, place the ticks of its WCSAxes."""
    data = Data(x=np.zeros((2, 2)), label="probe")
    state = SimpleNamespace(
        reference_data=data,
        x_att=data.pixel_component_ids[1],
        y_att=data.pixel_component_ids[0],
        x_axislabel="x",
        y_axislabel="y",
        x_axislabel_size=10,
        y_axislabel_size=10,
        x_axislabel_weight="normal",
        y_axislabel_weight="normal",
    )
    wcs = WCS(naxis=2)
    axes = WCSAxes(Figure(), [0, 0, 1, 1], wcs=wcs)
    viewer = SimpleNamespace(axes=axes, state=state, _wcs_set=True, redraw=lambda: None)
    # placing ticks evaluates the WCS, and labelling a coordinate does not
    evaluated, evaluate = [], wcs.pixel_to_world_values
    wcs.pixel_to_world_values = lambda *pixel: evaluated.append(pixel) or evaluate(*pixel)
    for update in updates:
        update(viewer)
    return bool(evaluated)


if needs_axis_label_workaround():
    ImageViewer.update_x_axislabel, ImageViewer.update_y_axislabel = update_x_axislabel, update_y_axislabel


# glue-core #2599: glue 1.27.0 counts dates in days from 0001-01-01, matplotlib's epoch before 3.3, so a Scatter or
# Histogram of 2021 times ticks in year 3990. The modules that import the conversions by name, glue.utils first.
_DATE_MODULES = (glue.utils, glue.utils.matplotlib, scatter_viewer, scatter_layer_artist, matplotlib_viewer,
                 histogram_viewer, histogram_state)
_original_datetime64_to_mpl = glue.utils.datetime64_to_mpl


def datetime64_to_mpl(d):
    """`numpy.datetime64` values as days since `matplotlib.dates.get_epoch`, as matplotlib's date ticks read them."""
    return dates.date2num(d)


def mpl_to_datetime64(dt):
    """Days since `matplotlib.dates.get_epoch` as `numpy.datetime64` values, to the nanosecond."""
    ns = np.round(np.asarray(dt, np.float64) * 86400e9).astype(np.int64)
    return np.datetime64(dates.get_epoch(), "ns") + ns.astype("timedelta64[ns]")


def needs_date_epoch_workaround(func=_original_datetime64_to_mpl):
    """Whether ``func`` gives a date other than matplotlib's own number for it."""
    when = np.datetime64("2021-09-05T00:00:00")
    return float(func(when)) != dates.date2num(when)


if needs_date_epoch_workaround():
    for module in _DATE_MODULES:
        for name, function in (("datetime64_to_mpl", datetime64_to_mpl), ("mpl_to_datetime64", mpl_to_datetime64)):
            if hasattr(module, name):
                setattr(module, name, function)


# A Profile Collapse range inside one sample gives glue-qt's `AggregateSlice` an empty range, which glue 1.27.0's image
# refuses to draw ("Number of steps in bounds should be >=1") in every redraw. Report candidate for glue.
_original_aggregate_init = AggregateSlice.__init__


def aggregate_slice_init(self, slice=None, center=None, function=None):  # glue's keywords, which sessions use
    """glue's `AggregateSlice`, with an empty range as its first sample, which glue can draw."""
    if isinstance(slice, builtins.slice) and slice.step is None and None not in (slice.start, slice.stop):
        if slice.stop <= slice.start:
            slice = builtins.slice(slice.start, slice.start + 1)
    _original_aggregate_init(self, slice, center, function)


def needs_empty_collapse_workaround():
    """Whether glue's image buffer refuses a range of no samples, as an empty Collapse range gives it."""
    data = Data(label="probe", values=np.zeros((2, 2)))
    try:
        data.compute_fixed_resolution_buffer([(0, 0, 0), (0, 1, 2)], target_cid=data.id["values"])
    except ValueError:
        return True
    return False


if needs_empty_collapse_workaround():
    AggregateSlice.__init__ = aggregate_slice_init


# glue 1.27.0 saves an astropy Quantity, such as the exposure times in irispy's metadata, as the ndarray it subclasses,
# which numpy.save refuses, so no session with an IRIS raster saves. Saved as its values and unit instead, a record for
# glue's own loader to take over (report candidate for glue), only while glue has no saver of its own.
def save_quantity(quantity, context):
    """
    A session's record of ``quantity``: its values, as nested lists, and its unit as glue saves one, which raises
    `GlueSerializeError` for a unit glue cannot read back (glue then leaves the value out of a dataset's meta).
    """
    return {"value": quantity.value.tolist(), "unit": context.do(quantity.unit)["unit_base"]}


def load_quantity(rec, context):
    """The Quantity of a `save_quantity` record."""
    return u.Quantity(rec["value"], rec["unit"])


if u.Quantity not in GlueSerializer.dispatch:
    saver(u.Quantity)(save_quantity)
    loader(u.Quantity)(load_quantity)


# glue 1.27.0 saves a `LinkSameWithUnits`, such as `link_hpc` gives a sunpy map, with its conversions, methods of the
# link itself, so no session holding one opens ("Circular Reference detected"). Saved by its two components instead,
# as glue saves a `LinkSame` (report candidate for glue, ``wp0-core-session-reports``).
def save_link_with_units(self, context):
    """A session's record of a `LinkSameWithUnits`: its two components, from which it makes its conversions again."""
    return {"cid1": context.id(self._cid1), "cid2": context.id(self._cid2)}


def load_link_with_units(cls, rec, context):
    """The `LinkSameWithUnits` of a `save_link_with_units` record."""
    return cls(context.object(rec["cid1"]), context.object(rec["cid2"]))


def needs_link_restore_workaround():
    """Whether a session holding a `LinkSameWithUnits` fails to open."""
    first, second = Data(x=np.zeros(1), label="first"), Data(y=np.zeros(1), label="second")
    collection = DataCollection([first, second])
    collection.add_link(LinkSameWithUnits(first.id["x"], second.id["y"]))
    try:
        GlueUnSerializer.loads(GlueSerializer(collection).dumps()).object("__main__")
    except GlueSerializeError:
        return True
    return False


if needs_link_restore_workaround():
    LinkSameWithUnits.__gluestate__ = save_link_with_units
    LinkSameWithUnits.__setgluestate__ = classmethod(load_link_with_units)


# glue 1.27.0 gives a time linked from another dataset, such as the first light curve's ``Time`` on the others (a
# `LinkSame`), no kind ("Unknown data kind"): it reads whether a derived component is numeric from its first value,
# which a datetime is not, and never whether it is a datetime. So no Scatter plot shows two datasets against linked
# times (report candidate for glue).
_original_datetime = DerivedComponent.datetime


def derived_datetime(self):
    """Whether a derived component holds datetimes, read from its first value as glue reads whether it is numeric."""
    return self[(0,) * self.ndim].dtype.kind == "M"


def needs_derived_datetime_workaround(datetime=_original_datetime):
    """Whether ``datetime``, a derived component's property, says a time linked from another dataset is none."""
    first, second = (Data(t=np.zeros(1, "datetime64[ns]"), label=label) for label in ("first", "second"))
    DataCollection([first, second]).add_link(LinkSame(first.id["t"], second.id["t"]))
    return not datetime.fget(second.get_component(first.id["t"]))


if needs_derived_datetime_workaround():
    DerivedComponent.datetime = property(derived_datetime)


_original_update_priority = ProfileViewerState._update_priority


def _update_priority(self, name):
    """
    glue-core's ``ProfileViewerState._update_priority``, restoring the display units after ``x_att``.

    glue-core 1.27.0 restores a Profile viewer's ``x_display_unit`` with its ``x_att``, while the units listed are still
    those of the reference data's first axis, so a session with a spectrum of an IRIS raster, whose wavelength is its
    last axis, does not open ("value Angstrom is not in valid choices"). The units now come between ``x_att`` and the
    limits, as glue's Matplotlib viewer states rank ``_log``. Retired by glue ranking the display units after ``x_att``
    (``core-profile-restore-priority`` report candidate).
    """
    if name.endswith("_display_unit"):
        return 0.5
    return _original_update_priority(self, name)


def needs_profile_restore_workaround(method=_original_update_priority):
    """Whether a Profile viewer state ranked by ``method`` fails to restore an x unit not of the first world axis."""
    wcs = WCS(naxis=2)
    wcs.wcs.cunit = ["count", ""]  # on the last axis; astropy lists the units equivalent to a count quickly
    data = Data(x=np.zeros((2, 2)), coords=wcs, label="probe")
    state = type("ProbeState", (ProfileViewerState,), {"_update_priority": method})
    try:  # as glue restores a viewer state
        state(
            layers=[ProfileLayerState(layer=data)],
            reference_data=data,
            x_att=data.world_component_ids[1],
            x_display_unit="count",
        )
    except ValueError:
        return True
    return False


if needs_profile_restore_workaround():
    ProfileViewerState._update_priority = _update_priority


_original_close_event = ImageViewer.closeEvent


def close_event(self, event):
    """
    glue-qt's ``ImageViewer.closeEvent``, stopping the playback of the viewer's slice sliders once it closes.

    glue-qt 0.4.2 leaves a slider's play timer running when its viewer closes: the viewer's options, sliders
    included, stay in the application's options panel, and the timer goes on stepping the closed viewer. Each close
    probes for a slider still playing after glue-qt's own close, so this stops nothing once glue-qt does. Retired by
    a glue-qt fix (report candidate).
    """
    _original_close_event(self, event)
    if not event.isAccepted():
        return  # cancelled at glue-qt's confirmation: the viewer stays, playing
    for slider in self.options_widget().findChildren(SliceWidget):
        if slider._play_timer.isActive():
            slider._adjust_play("stop")  # glue-qt's Stop button


ImageViewer.closeEvent = close_event


_original_canvas_init = MplCanvas.__init__


def _matplotlib_keys(event):
    """matplotlib's own key bindings, but for full screen and save, F and S alone or with Ctrl by default."""
    if event.key not in rcParams["keymap.fullscreen"] + rcParams["keymap.save"]:
        key_press_handler(event)


def canvas_init(self, *args, **kwargs):
    """
    glue-qt's ``MplCanvas.__init__``, leaving F and S over a viewer to glue-solar's frame and wavelength keys
    (`glue_solar.tools.KEYS`), which glue-qt gives them whatever the modifiers.

    glue-qt 0.4.2 gives each canvas a matplotlib figure manager, which connects matplotlib's own key bindings: F shows
    the manager's empty window full screen and S opens matplotlib's save dialog. The others, such as G for the grid,
    stay. Each canvas probes for the manager's bindings, so this changes nothing once glue-qt connects none. Retired
    by glue-qt dropping matplotlib's bindings from its canvases (report candidate).
    """
    _original_canvas_init(self, *args, **kwargs)
    manager = getattr(self, "manager", None)
    if getattr(manager, "key_press_handler_id", None) is not None:
        self.mpl_disconnect(manager.key_press_handler_id)
        manager.key_press_handler_id = self.mpl_connect("key_press_event", _matplotlib_keys)


MplCanvas.__init__ = canvas_init


_original_update_icons = colors.QColormapCombo._update_icons
_icons = {}  # (id(colormap), width): (colormap, icon), the colormap kept so that its id stays its own


def update_icons(self):
    """
    glue-qt's ``QColormapCombo._update_icons``, with the icons of each colormap and width shared by every combo.

    glue-qt 0.4.2 draws the icon of every colormap listed whenever it builds or resizes a combo, as for each Image
    layer's style editor: 0.3 ms a colormap, 30 ms with every sunpy colormap listed. The probe runs at the first combo,
    which needs Qt's application. Retired by glue-qt caching icons (``wp0-perf-qt``).
    """
    if not _icons_need_workaround():
        return _original_update_icons(self)
    width = self.width()
    self.setIconSize(QtCore.QSize(width, 15))
    for index in range(self.count()):
        cmap = self.itemData(index).data
        key = (id(cmap), width)
        if key not in _icons:
            if len(_icons) >= 1000:  # forget the oldest
                del _icons[next(iter(_icons))]
            _icons[key] = cmap, QtGui.QIcon(colors.cmap2pixmap(cmap, size=(width, 15), steps=200))
        self.setItemIcon(index, _icons[key][1])


def needs_icon_cache_workaround(method=_original_update_icons):
    """Whether ``method`` draws a colormap's icon again for a second combo of the same width."""
    drawn, draw = [], colors.cmap2pixmap
    colors.cmap2pixmap = lambda *args, **kwargs: drawn.append(args) or draw(*args, **kwargs)
    # a combo that lists only ``cmap``, not the colormaps glue-qt's __init__ lists and draws
    combo_class = type("ProbeCombo", (colors.QColormapCombo,), {"__init__": QtWidgets.QComboBox.__init__})
    cmap = ListedColormap(["black", "white"])
    try:
        for _ in range(2):
            combo = combo_class()
            combo.addItem("probe", userData=UserDataWrapper(cmap))
            method(combo)
    finally:
        colors.cmap2pixmap = draw
    return sum(args[0] is cmap for args in drawn) > 1  # not the colormap of a probe ``method`` itself runs


@cache
def _icons_need_workaround():
    return needs_icon_cache_workaround()


colors.QColormapCombo._update_icons = update_icons


_original_find_combo_data = connect._find_combo_data


def find_combo_data(widget, value):
    """
    echo's ``_find_combo_data``, matching a colormap to the entry that is it, then to one of its name or of the sunpy
    colormap of that key, before an earlier entry of equal colours.

    sunpy has colormaps of equal colours, such as AIA 171, SUVI 171 and EUI 174, and echo 0.15 matches the first
    listed: an AIA 171 map's menu showed SUVI 171, and picking AIA 171 gave SUVI 171 back. A sunpy map's colormap and
    the one glue restores from a session are matplotlib's copies, named by sunpy's key or by the saved name. Retired by
    echo matching the entry that is the value first (report candidate), once the readers and glue's restore give the
    listed colormap rather than a copy.
    """
    index = _original_find_combo_data(widget, value)
    if isinstance(value, Colormap):
        data = [widget.itemData(i) for i in range(widget.count())]
        data = [item.data if isinstance(item, UserDataWrapper) else item for item in data]
        names = value.name, cmlist.get(value.name, value).name
        equal = [i for i in range(index, len(data)) if data[i] is value or (data[i] == value) is True]
        index = min(equal, key=lambda i: (data[i] is not value, data[i].name not in names))
    return index


def needs_combo_match_workaround(find=_original_find_combo_data):
    """Whether ``find`` matches a sunpy map's AIA 171 colormap to SUVI 171 listed before AIA 171."""
    listed = [UserDataWrapper(cmlist[key]) for key in ("goes-rsuvi171", "sdoaia171")]
    combo = SimpleNamespace(count=lambda: len(listed), itemData=listed.__getitem__)
    return find(combo, colormaps["sdoaia171"]) == 0


if needs_combo_match_workaround():
    connect._find_combo_data = find_combo_data
