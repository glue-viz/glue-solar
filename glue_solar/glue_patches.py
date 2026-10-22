"""
Gated fixes for glue-core and glue-qt bugs that IRIS data hits.

Each fix installs, or acts, only when its probe finds the bug (a `needs_*` probe that raises counts as finding it:
`_needs`), and names its PR, whose row in the plan's Workaround register names the switch and the upstream change that
retires it.
"""

import builtins
import inspect
import os
import re
from contextlib import nullcontext
from functools import cache, partial, wraps
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import dask
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
from glue.core.link_helpers import LinkSame, LinkSameWithUnits, MultiLink
from glue.core.link_manager import pixel_cid_to_pixel_cid_matrix
from glue.core.state import GlueSerializeError, GlueSerializer, GlueUnSerializer, loader, saver
from glue.core.subset import SubsetState
from glue.dialogs.link_editor.state import LinkEditorState
from glue.plugins.tools.path_slicer.path_sliced_data import PathSlicedData
from glue.plugins.tools.path_slicer.path_sliced_data_links import PathRelativeLink
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink
from glue.utils import defer_draw
from glue.viewers.common.state import LayerState
from glue.viewers.histogram import state as histogram_state
from glue.viewers.histogram import viewer as histogram_viewer
from glue.viewers.image.layer_artist import ImageSubsetLayerArtist
from glue.viewers.image.pixel_selection_mode import PixelSelectionTool
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue.viewers.image.state import AggregateSlice, ImageLayerState
from glue.viewers.matplotlib import viewer as matplotlib_viewer
from glue.viewers.profile.state import ProfileLayerState, ProfileViewerState
from glue.viewers.scatter import layer_artist as scatter_layer_artist
from glue.viewers.scatter import viewer as scatter_viewer
from glue.viewers.table.state import TableViewerState
from glue_qt.app import GlueApplication
from glue_qt.app.layer_tree_widget import LayerAction, UserAction
from glue_qt.config import LayerActionRegistry
from glue_qt.config import layer_action as glue_layer_action
from glue_qt.core.fitters import FitSettingsWidget
from glue_qt.utils import colors
from glue_qt.viewers.common.data_slice_widget import SliceWidget
from glue_qt.viewers.common.toolbar import BasicToolbar
from glue_qt.viewers.image import ImageViewer
from glue_qt.viewers.matplotlib.widget import MplCanvas
from glue_qt.viewers.profile import ProfileViewer, profile_tools
from glue_qt.viewers.profile.profile_tools import ProfileTools
from glue_qt.viewers.table.data_viewer import DataTableModel
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
from astropy.wcs.utils import pixel_to_pixel
from astropy.wcs.wcsapi import HighLevelWCSWrapper, SlicedLowLevelWCS

from sunpy.visualization.colormaps import cmlist

from glue_solar.sources.dkist import GlueWCS
from glue_solar.sources.loaders.iris import WCS_LOCK, _HeldWCS, _LockedWCS


def _needs(probe):
    """
    ``probe()``, or True where it raises, as on a glue change it did not foresee: the patch installs rather than the
    import failing, which glue logs at info level only, without glue-solar (D82).
    """
    try:
        return probe()
    except Exception:  # noqa: BLE001 - any failure installs the patch
        return True


_original_world2pixel_single_axis = coordinate_helpers.world2pixel_single_axis


def world2pixel_single_axis(wcs, *world, pixel_axis=None):
    """
    glue-core's ``world2pixel_single_axis``, also keeping the world axes that share a pixel axis with those of
    ``pixel_axis``: glue-core 1.27.0 inverted each slit-jaw frame, whose pointing moves with time, at exposure 0 (#71,
    glue-viz/glue#2598). Installed holding `WCS_LOCK` (`_hold_wcs_lock`).
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


_original_reset_wcs = WCSAxes.reset_wcs


def reset_wcs(self, wcs=None, *args, **kwargs):
    """
    astropy's ``WCSAxes.reset_wcs``, holding the lock of a WCS that has one (`_HeldWCS`): its ``wcsset``, at each slice
    of an SST cube, frees what a profile worker's transform of the same WCS reads (#226, #251, astropy/astropy#19174).
    """
    with wcs._held() if isinstance(wcs, _HeldWCS) else nullcontext():
        return _original_reset_wcs(self, wcs, *args, **kwargs)


WCSAxes.reset_wcs = reset_wcs


def _dask_probe(shape):
    """A dataset whose ``values`` are a glue DaskComponent of zeros, as lazily loaded IRIS values are."""
    data = Data(label="probe")
    data.add_component(DaskComponent(da.zeros(shape, chunks=2)), "values")
    return data


_original_fits_writer = gridded_fits.fits_writer


class _Sections:
    """``data[cid]`` as dask reads it, a section at a time: glue reads a derived component, such as the mask, whole."""

    def __init__(self, data, cid):
        self.data, self.cid, self.shape, self.ndim = data, cid, data.shape, data.ndim
        self.dtype = np.asarray(data[cid, (slice(0, 1),) * data.ndim]).dtype

    def __getitem__(self, key):
        return np.asarray(self.data[self.cid, key])


def export_fits(filename, data, components=None, data_header=None, extensions=()):
    """
    glue-core's "FITS (1 component/HDU)" exporter, writing each component a section at a time, as astropy writes dask
    to a file, so that a lazy window is never in memory whole (a subset's mask is): glue-core 1.27.0 masks a subset in
    place, which a dask array refuses; a subset's unsigned components, such as the mask, go unmasked (#96). Also for
    `glue_solar.sources.iris.export_iris_fits`, with ``data_header`` for the WCS header and ``extensions`` appended.
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
        sections = _Sections(data, cid)
        if sections.dtype.kind == "u" and sections.dtype.itemsize > 1:  # astropy writes these from NumPy only
            values = np.asarray(data[cid])
        else:
            values = da.from_array(sections, name=False, meta=np.empty((0,) * data.ndim, sections.dtype))
        blank = None
        if mask is not None:
            if values.dtype.kind == "f":
                values = da.where(mask, values, values.dtype.type(np.nan))
            elif values.dtype.kind == "i":
                blank = np.iinfo(values.dtype).min
                values = da.where(mask, values, values.dtype.type(blank))
        if isinstance(data, Data):
            # a copy: glue-core 1.27.0 updates and returns the header given, so a BLANK would reach later HDUs
            header = gridded_fits.make_component_header(data.get_component(cid), data_header.copy())
        else:
            header = fits.Header()
        if blank is not None:
            header["BLANK"] = blank
        hdus.append(fits.ImageHDU(values, name=cid.label, header=header))
    for hdu in extensions:
        hdus.append(hdu)
    with dask.config.set(scheduler="synchronous"):  # glue's reads on this thread, one section in memory at a time
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


if _needs(needs_fits_export_dask_workaround):
    for i, exporter in enumerate(data_exporter.members):
        if exporter.function is _original_fits_writer:
            data_exporter.members[i] = exporter._replace(function=export_fits)


_original_to_linked_pixel_coords = PixelSubsetState._to_linked_pixel_coords


def _to_linked_pixel_coords(self, data):
    """
    glue-core's ``PixelSubsetState._to_linked_pixel_coords``: a point off ``data``, at a NaN pixel, is incompatible
    rather than a ValueError (#76, #85), and one is placed where the axes its fixed axes reach reach back to fixed axes
    only, at least one, not to exactly those, as the SST quicklook's scan and Stokes reach no IRIS axis (#246, D73).
    Installed holding `WCS_LOCK` (`_hold_wcs_lock`).
    """
    dimensions = [axis for axis, s in enumerate(self.slices) if s.start is not None]
    try:
        matrix = pixel_cid_to_pixel_cid_matrix(self.reference_data, data)
        reached = np.nonzero(matrix[dimensions].any(axis=0))[0]
        back = np.nonzero(matrix[:, reached].any(axis=1))[0]
        if not set(back) <= set(dimensions) or (dimensions and not len(back)):
            raise IncompatibleAttribute()
        at = tuple(slice(0, 1) if s.start is None else s for s in self.slices)
        return [
            int(np.round(self.reference_data[cid, at].ravel()[0])) if axis in reached else None
            for axis, cid in enumerate(data.pixel_component_ids)
        ]
    except ValueError:  # int() of NaN: the point is not on ``data``
        raise IncompatibleAttribute() from None


def needs_pixel_point_workaround(method=_original_to_linked_pixel_coords):
    """
    Whether ``method`` raises ``ValueError`` for a Pixel point with no finite pixel in a linked dataset, or refuses one
    whose fixed axis reaches no pixel axis of it.
    """
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
    cube, image = Data(x=np.zeros((2, 2, 2)), label="cube"), Data(y=np.zeros((2, 2)), label="image")
    collection = DataCollection([cube, image])
    for a, b in zip(cube.pixel_component_ids[1:], image.pixel_component_ids):
        collection.add_link([ComponentLink([a], b), ComponentLink([b], a)])
    try:
        method(PixelSubsetState(cube, [slice(1, 2)] * 3), image)  # its first axis reaches no axis of the image
    except IncompatibleAttribute:
        return True
    return False


def _hold_wcs_lock():
    """
    Install glue's ``world2pixel_single_axis`` and ``PixelSubsetState._to_linked_pixel_coords``, or their fixes here,
    holding `WCS_LOCK` whatever the probes say: glue's profile workers call them beside the GUI thread (#232, D73,
    astropy/astropy#19174). A point to or on a WCS ``link_hpc`` has not locked takes none, so no unlinked map or SST
    cube waits for IRIS data's threads.
    """
    inverse = world2pixel_single_axis if _needs(needs_inverse_workaround) else _original_world2pixel_single_axis
    point = _to_linked_pixel_coords if _needs(needs_pixel_point_workaround) else _original_to_linked_pixel_coords

    @wraps(inverse)
    def locked_inverse(*args, **kwargs):
        with WCS_LOCK:
            return inverse(*args, **kwargs)

    @wraps(point)
    def locked_point(self, data):
        pair = self.reference_data, data
        unlinked = any(isinstance(d.coords, WCS) and not isinstance(d.coords, _LockedWCS) for d in pair)
        with nullcontext() if unlinked else WCS_LOCK:
            return point(self, data)

    # glue.core.component_link imports it by name
    coordinate_helpers.world2pixel_single_axis = component_link.world2pixel_single_axis = locked_inverse
    PixelSubsetState._to_linked_pixel_coords = locked_point


_hold_wcs_lock()

_original_select_pixel = PixelSelectionTool._select_pixel


def _select_pixel(self, mode):
    """
    glue's Pixel click or drag, skipped off the image, as Follow/lock skips it: in a panel's margin glue makes a point
    outside the data, which no viewer can draw (an IndexError in ``PixelSubsetState._to_linked_pixel_coords``).
    """
    if not self._pressed:  # glue's own first check: it is called on every mouse move, in an empty viewer too
        return
    state, x, y = self.viewer.state, self._event_xdata, self._event_ydata
    if None in (x, y) or all(
        0 <= round(at) < state.reference_data.shape[att.axis] for at, att in ((x, state.x_att), (y, state.y_att))
    ):
        _original_select_pixel(self, mode)


def needs_pixel_off_image_workaround(method=_original_select_pixel):
    """Whether ``method``, glue's Pixel selection, makes a point off the image."""
    data, done = Data(x=np.zeros((2, 2)), label="probe"), []
    state = SimpleNamespace(reference_data=data, x_att=data.pixel_component_ids[1], y_att=data.pixel_component_ids[0])
    session = SimpleNamespace(command_stack=SimpleNamespace(do=done.append))
    viewer = SimpleNamespace(state=state, _data=DataCollection([data]), _session=session)
    method(SimpleNamespace(_pressed=True, _event_xdata=2.0, _event_ydata=0.0, viewer=viewer), None)
    return bool(done)


if _needs(needs_pixel_off_image_workaround):
    PixelSelectionTool._select_pixel = _select_pixel


_original_apply_subset_state = ApplySubsetState.do


def apply_subset_state(self, session):
    """
    glue-core's ``ApplySubsetState.do``, whose Redo puts back the subset states its first run made: glue-core 1.27.0
    applies the state again, from the viewers of then, so a Redo after the quicklook's frame moved gave another exposure
    (#182). A Redo whose subsets Undo deleted, as a new subset group's, stays glue's.
    """
    made = getattr(self, "_solar_made", None)
    if made is None or any(subset not in subset.data.subsets for subset in made):
        _original_apply_subset_state(self, session)
        subsets = [subset for data in self.data_collection for subset in data.subsets]
        self._solar_made = {s: s.subset_state for s in subsets if s.subset_state is not self.old_states.get(s)}
        return
    self.old_states = {subset: subset.subset_state for data in self.data_collection for subset in data.subsets}
    with _putting_back(self):
        for subset, state in made.items():  # a group's, as glue's do sets it: one message a subset
            getattr(subset, "group", subset).subset_state = state


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


if _needs(needs_redo_workaround):
    ApplySubsetState.do = apply_subset_state


_original_undo_subset_state = ApplySubsetState.undo


def _putting_back(command):
    """The quicklooks' `Coordinator.restoring`, while ``command`` puts subset states back."""
    coordinator = getattr(command.data_collection, "_solar_coordinator", None)
    return nullcontext() if coordinator is None else coordinator.restoring()


def undo_subset_state(self, session):
    """
    glue-core's ``ApplySubsetState.undo``, which puts back each subset's state in turn: a quicklook's point put back is
    not a click, which other points would follow (D97).
    """
    with _putting_back(self):
        _original_undo_subset_state(self, session)


ApplySubsetState.undo = undo_subset_state


_original_update_visual_attributes = ImageSubsetLayerArtist._update_visual_attributes


@defer_draw
def _update_visual_attributes(self, redraw=True):
    """
    glue-core's ``ImageSubsetLayerArtist._update_visual_attributes``, keeping hidden the Pixel crosshair of a point
    with no position on a displayed axis, as a raster point in wavelength, which glue-core 1.27.0 shows at (0, 0) (#87).
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


if _needs(needs_crosshair_workaround):
    ImageSubsetLayerArtist._update_visual_attributes = _update_visual_attributes


_original_update_data = ImageSubsetLayerArtist._update_data


@defer_draw
def _update_data(self):
    """
    glue-core's ``ImageSubsetLayerArtist._update_data``, placing a Pixel crosshair where the point lies in the reference
    data: glue-core 1.27.0 places it from the layer's own dataset, elsewhere for a linked sunpy map, and raises
    IndexError over a slit-jaw image (#107).
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


if _needs(needs_reference_crosshair_workaround):
    ImageSubsetLayerArtist._update_data = _update_data


_original_update_slice_subset = ImageLayerState._update_slice_subset


def _update_slice_subset(self, slices):
    """
    glue-core's ``ImageLayerState._update_slice_subset``, skipped while the viewer has no reference data: glue-core
    1.27.0 raises TypeError there as the data of a layer with per-frame limits are removed, which stops their removal
    partway, as of an SST quicklook's second map (report candidate).
    """
    if self.viewer_state.reference_data is not None:
        _original_update_slice_subset(self, slices)


def needs_slice_subset_workaround(method=_original_update_slice_subset):
    """Whether ``method`` raises for a layer with per-frame limits in a viewer with no reference data."""
    viewer = SimpleNamespace(reference_data=None, numpy_slice_aggregation_transpose=None)
    layer = SimpleNamespace(viewer_state=viewer, attribute_lim_helper=SimpleNamespace(set_slice=lambda _: None))
    try:
        method(layer, ())
    except TypeError:
        return True
    return False


if _needs(needs_slice_subset_workaround):
    ImageLayerState._update_slice_subset = _update_slice_subset


_original_update_axislabels = (ImageViewer.update_x_axislabel, ImageViewer.update_y_axislabel)


def _set_axislabel(viewer, axis):
    """Label the WCSAxes coordinate of the Image viewer's ``axis`` ('x' or 'y') with glue's label and style."""
    state = viewer.state
    data, att = state.reference_data, getattr(state, f"{axis}_att")
    index = "xy".index(axis)
    # glue's own mapping, as in its update_x_ticklabel, but not waiting for its _wcs_set: a restored viewer
    # sets its labels only once, on the axes of its first reset, before glue sets that flag; to the world axis glue
    # gives the axis, world_n_dim - 1 - axis, which a DKIST dataset's world axes of no axis of their own precede (D102)
    world = getattr(getattr(data, "coords", None), "world_n_dim", getattr(data, "ndim", 0))
    if data is not None and att is not None and world - 1 - att.axis in viewer.axes.coords:
        index = world - 1 - att.axis
    viewer.axes.coords[index].set_axislabel(
        getattr(state, f"{axis}_axislabel"),
        weight=getattr(state, f"{axis}_axislabel_weight"),
        size=getattr(state, f"{axis}_axislabel_size"),
    )
    viewer.redraw()


@defer_draw
def update_x_axislabel(self, *event):
    """
    glue-qt's ``ImageViewer.update_x_axislabel``, labeling the WCSAxes coordinate glue maps the x axis to: WCSAxes'
    ``set_xlabel``, which glue-core 1.27.0 calls, places every tick to find it, four extra placements a slit-jaw frame
    step (#90). Past a 45° roll, where WCSAxes puts latitude on the bottom spine, each coordinate keeps its own name.
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
    # placing ticks evaluates the WCS, and labeling a coordinate does not
    evaluated, evaluate = [], wcs.pixel_to_world_values
    wcs.pixel_to_world_values = lambda *pixel: evaluated.append(pixel) or evaluate(*pixel)
    for update in updates:
        update(viewer)
    return bool(evaluated)


if _needs(needs_axis_label_workaround):
    ImageViewer.update_x_axislabel, ImageViewer.update_y_axislabel = update_x_axislabel, update_y_axislabel


# glue-core #2599: glue 1.27.0 counts dates in days from 0001-01-01, matplotlib's epoch before 3.3, so a Scatter or
# Histogram of 2021 times ticks in year 3990 (#128). The modules that import the conversions by name, glue.utils first.
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


if _needs(needs_date_epoch_workaround):
    for module in _DATE_MODULES:
        for name, function in (("datetime64_to_mpl", datetime64_to_mpl), ("mpl_to_datetime64", mpl_to_datetime64)):
            if hasattr(module, name):
                setattr(module, name, function)


# A Profile Collapse range inside one sample gives glue-qt's `AggregateSlice` an empty range, which glue 1.27.0's image
# refuses to draw ("Number of steps in bounds should be >=1") in every redraw (#132). Report candidate for glue.
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


if _needs(needs_empty_collapse_workaround):
    AggregateSlice.__init__ = aggregate_slice_init


# glue 1.27.0 saves an astropy Quantity, as irispy's exposure times, as the ndarray it subclasses, which numpy.save
# refuses, so no session with an IRIS raster saved (#186, D13)
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


# glue 1.27.0 saves a `LinkSameWithUnits`, as `link_hpc` gives a sunpy map, with its conversions, methods of the link
# itself, so no session holding one opened ("Circular Reference detected", #205)
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


if _needs(needs_link_restore_workaround):
    LinkSameWithUnits.__gluestate__ = save_link_with_units
    LinkSameWithUnits.__setgluestate__ = classmethod(load_link_with_units)


# glue 1.27.0 names both ends of a `LinkSameWithUnits` ``values`` and of a `PathRelativeLink` ``k``, and its link editor
# keeps one choice per name, so Link Data raised ValueError; its OK remakes a `LinkSameWithUnits` from ``cids1`` and
# ``cids2``, and a `PathRelativeLink` as a `ComponentLink` named from its conversions, ``self`` too (#245)
_original_link_with_units_init = LinkSameWithUnits.__init__
_original_path_link_init = PathRelativeLink.__init__


def link_with_units_init(self, cid1=None, cid2=None, **kwargs):
    """glue's ``LinkSameWithUnits.__init__``, its ends named ``x`` and ``y`` as a `LinkSame`'s, taking ``cids1`` too."""
    cid1 = kwargs["cids1"][0] if cid1 is None else cid1
    cid2 = kwargs["cids2"][0] if cid2 is None else cid2
    _original_link_with_units_init(self, cid1, cid2)
    self.labels1, self.labels2 = ["x"], ["y"]


def path_link_init(self, slice_from, slice_to):
    """glue's ``PathRelativeLink.__init__``, its ends named ``k_from`` and ``k_to`` as its conversions name them."""
    _original_path_link_init(self, slice_from, slice_to)
    self.input_names, self.output_name = ["k_from"], "k_to"


def needs_link_editor_workaround(units_init=_original_link_with_units_init, path_init=_original_path_link_init):
    """
    Whether glue's link editor, as Link Data and Link Suggestions open it, or its OK fails, at first or after an OK,
    on a `LinkSameWithUnits` made by ``units_init`` or a `PathRelativeLink` made by ``path_init``.
    """
    first, second = Data(x=np.zeros((2, 2)), label="first"), Data(y=np.zeros((2, 2)), label="second")
    paths = [
        PathSlicedData(data, data.pixel_component_ids[1], [0, 1], data.pixel_component_ids[0], [0, 1])
        for data in (first, second)
    ]
    collection = DataCollection([first, second, *paths])
    units = type("Probe", (LinkSameWithUnits,), {"__init__": units_init})
    path = type("Probe", (PathRelativeLink,), {"__init__": path_init})
    collection.add_link([units(first.id["x"], second.id["y"]), path(*paths)])
    try:
        for _ in range(2):  # Link Data again after an OK
            LinkEditorState(collection).update_links_in_collection()
    except (AttributeError, TypeError, ValueError):
        return True
    return False


if _needs(needs_link_editor_workaround):
    LinkSameWithUnits.__init__ = link_with_units_init
    PathRelativeLink.__init__ = path_link_init
    PathRelativeLink._forward.__signature__ = inspect.signature(lambda k_from: None)
    PathRelativeLink._backward.__signature__ = inspect.signature(lambda k_to: None)


# glue 1.28.0 links datasets whose world axes differ through has_celestial and wcs.lng, attributes of an astropy WCS
# only, taking world axis i to be pixel axis world_n_dim - 1 - i, so its autolinker raised AttributeError as DKIST
# datasets of different dimensions loaded (D102)
_original_wcs_link_init = WCSLink.__init__


def _wcs_link_axes(wcs, types):
    """The pixel axes of ``wcs`` along which world axes of physical types ``types`` vary, and no others."""
    matrix = np.asarray(wcs.axis_correlation_matrix)
    linked = np.array([kind in types for kind in wcs.world_axis_physical_types])
    return np.flatnonzero(matrix[linked].any(axis=0) & ~matrix[~linked].any(axis=0))


def wcs_link_init(self, data1=None, data2=None, cids1=None, cids2=None):
    """
    glue's ``WCSLink.__init__``, with its general path by APE-14 alone where glue's needs an astropy WCS: the physical
    types both datasets have, through the pixel axes of each along which only those vary, the others at pixel 0, fewer
    types until both keep the same ones; tried at pixel 0 with as many values as each takes, where glue gives the
    second as many as the first.
    """
    try:
        return _original_wcs_link_init(self, data1, data2, cids1, cids2)
    except AttributeError:  # an astropy WCS attribute
        pass
    pair, sliced = (data1, data2), None
    types = set(data1.coords.world_axis_physical_types) & set(data2.coords.world_axis_physical_types) - {None}
    while types:
        axes = [_wcs_link_axes(data.coords, types) for data in pair]
        if not all(map(len, axes)):
            break
        sliced = [
            SlicedLowLevelWCS(data.coords, tuple(slice(None) if p in kept else 0 for p in range(data.ndim))[::-1])
            for data, kept in zip(pair, axes)
        ]
        found = [set(wcs.world_axis_physical_types) for wcs in sliced]
        if found[0] == found[1]:
            break
        types, sliced = found[0] & found[1], None
    if sliced is None:
        raise IncompatibleWCS(f"Can't create WCS link between {data1.label} and {data2.label}")
    cids = [[data.pixel_component_ids[data.ndim - 1 - p] for p in kept] for data, kept in zip(pair, axes)]
    wcs1, wcs2 = map(HighLevelWCSWrapper, sliced)

    def forwards(*pixel):
        return pixel_to_pixel(wcs1, wcs2, *pixel)

    def backwards(*pixel):
        return pixel_to_pixel(wcs2, wcs1, *pixel)

    try:
        forwards(*[0] * len(cids[0]))
        backwards(*[0] * len(cids[1]))
    except Exception:  # noqa: BLE001 - glue's test: any failure
        raise IncompatibleWCS(f"Can't create WCS link between {data1.label} and {data2.label}") from None
    self._physical_types_1, self._physical_types_2 = (list(wcs.world_axis_physical_types) for wcs in sliced)
    MultiLink.__init__(self, *cids, forwards=forwards, backwards=backwards)
    self.data1, self.data2 = data1, data2


def needs_wcs_link_workaround(init=_original_wcs_link_init):
    """Whether ``init`` fails to link a cube and an image whose APE-14 coordinates are not an astropy WCS."""
    datasets = []
    for naxis in (3, 2):
        wcs = WCS(naxis=naxis)
        wcs.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "STOKES"][:naxis]
        data = Data(label="probe", coords=GlueWCS(wcs, list(range(naxis)), []))
        data.add_component(np.zeros((2,) * naxis), "x")
        datasets.append(data)
    try:
        init(WCSLink.__new__(WCSLink), *datasets)
    except AttributeError:
        return True
    return False


if _needs(needs_wcs_link_workaround):
    WCSLink.__init__ = wcs_link_init


# glue 1.27.0 gives a time linked from another dataset, as the first light curve's ``Time`` on the others, no kind: it
# reads whether a derived component is numeric, never a datetime, so no Scatter plot showed linked times (#208)
_original_datetime = DerivedComponent.datetime


def derived_datetime(self):
    """Whether a derived component holds datetimes, read from its first value as glue reads whether it is numeric."""
    return self[(0,) * self.ndim].dtype.kind == "M"


def needs_derived_datetime_workaround(datetime=_original_datetime):
    """Whether ``datetime``, a derived component's property, says a time linked from another dataset is none."""
    first, second = (Data(t=np.zeros(1, "datetime64[ns]"), label=label) for label in ("first", "second"))
    DataCollection([first, second]).add_link(LinkSame(first.id["t"], second.id["t"]))
    return not datetime.fget(second.get_component(first.id["t"]))


if _needs(needs_derived_datetime_workaround):
    DerivedComponent.datetime = property(derived_datetime)


_original_get_filter_mask = DataTableModel.get_filter_mask


def get_filter_mask(self):
    """
    glue-qt's ``DataTableModel.get_filter_mask``, searching each value as the text the table shows: glue-qt 0.4.2
    refused a dataset whose first searchable column is a time, as a burst table, even with the box empty (#260).
    """
    if self._state.filter is None or self._state.filter_att is None:
        self.filter_mask = np.ones(self.order.shape, dtype=bool)
        return
    values = [str(value) for value in self._data.get_component(self._state.filter_att).data]
    if self._state.regex:
        pattern = re.compile(self._state.filter)
        self.filter_mask = np.array([bool(pattern.search(value)) for value in values])
    else:
        self.filter_mask = np.array([self._state.filter in value for value in values])
    self.data_changed()


def needs_table_time_workaround(method=_original_get_filter_mask):
    """Whether ``method`` refuses a Table viewer's dataset with a time, with the viewer's empty search box."""
    data = Data(t=np.zeros(1, "datetime64[ns]"), label="probe")
    state = TableViewerState(layers=[LayerState(layer=data)], filter="")
    try:
        method(DataTableModel(SimpleNamespace(data=data, state=state, layers=[])))
    except TypeError:
        return True
    return False


if _needs(needs_table_time_workaround):
    DataTableModel.get_filter_mask = get_filter_mask


_original_update_priority = ProfileViewerState._update_priority


def _update_priority(self, name):
    """
    glue-core's ``ProfileViewerState._update_priority``, restoring the display units between ``x_att`` and the limits:
    glue-core 1.27.0 restores them with ``x_att``, so a session with a raster's spectrum did not open (#197).
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


if _needs(needs_profile_restore_workaround):
    ProfileViewerState._update_priority = _update_priority


_original_close_event = ImageViewer.closeEvent


def close_event(self, event):
    """
    glue-qt's ``ImageViewer.closeEvent``, stopping its slice sliders' playback: glue-qt 0.4.2 leaves their timers
    stepping the closed viewer, whose options stay in the options panel (#115).
    """
    _original_close_event(self, event)
    if not event.isAccepted():
        return  # canceled at glue-qt's confirmation: the viewer stays, playing
    for slider in self.options_widget().findChildren(SliceWidget):
        if slider._play_timer.isActive():
            slider._adjust_play("stop")  # glue-qt's Stop button


ImageViewer.closeEvent = close_event


_original_application_gluestate = GlueApplication.__gluestate__


def application_gluestate(self, context):
    """
    glue-qt's ``GlueApplication.__gluestate__``, leaving out the viewers closed but not yet deleted, as when their data
    are removed in the turn the session is saved: glue-qt 0.4.2 lists them, and glue cannot restore such an Image viewer
    (report candidate).
    """
    state = _original_application_gluestate(self, context)
    closed = {context.id(viewer) for tab in self.viewers for viewer in tab if viewer._closed}
    state["viewers"] = [[name for name in tab if name not in closed] for tab in state["viewers"]]
    return state


GlueApplication.__gluestate__ = application_gluestate


_original_canvas_init = MplCanvas.__init__


# matplotlib's key bindings that `canvas_init` drops, by their ``keymap.*`` settings, and those a Profile viewer keeps
_DROPPED_KEYMAPS = ("fullscreen", "save", "grid", "grid_minor", "yscale", "xscale", "pan", "zoom")
_PROFILE_KEYMAPS = ("grid", "grid_minor")


def _matplotlib_keys(event):
    """matplotlib's own key bindings, but for those of `_DROPPED_KEYMAPS`, a Profile viewer's grid keys kept."""
    widget = event.canvas
    while widget is not None and not isinstance(widget, ProfileViewer):
        widget = widget.parentWidget()
    kept = () if widget is None else _PROFILE_KEYMAPS
    if event.key not in [key for name in _DROPPED_KEYMAPS if name not in kept for key in rcParams[f"keymap.{name}"]]:
        key_press_handler(event)


def canvas_init(self, *args, **kwargs):
    """
    glue-qt's ``MplCanvas.__init__``, without matplotlib's keys of `_DROPPED_KEYMAPS`: glue-qt 0.4.2 binds F and S over
    glue-solar's (`glue_solar.tools.KEYS`), grid keys that raise from WCSAxes, and log-scale, pan and zoom keys behind
    glue's options; a Profile viewer keeps its grid keys (#120, #222, #257).
    """
    _original_canvas_init(self, *args, **kwargs)
    manager = getattr(self, "manager", None)
    if getattr(manager, "key_press_handler_id", None) is not None:
        self.mpl_disconnect(manager.key_press_handler_id)
        manager.key_press_handler_id = self.mpl_connect("key_press_event", _matplotlib_keys)


MplCanvas.__init__ = canvas_init


_original_add_tool = BasicToolbar.add_tool


def add_tool(self, tool):
    """
    glue-qt's ``BasicToolbar.add_tool``, with a menu tool's tooltip on its button and its entries' tooltips shown,
    which glue-qt 0.4.2 hides (#222).
    """
    action = _original_add_tool(self, tool)
    button = self.widgetForAction(action)
    if isinstance(button, QtWidgets.QToolButton) and button.menu() is not None:
        if not button.toolTip():  # each probed alone, as glue-qt may fix one and not the other
            button.setToolTip(action.toolTip())
        if not button.menu().toolTipsVisible():
            button.menu().setToolTipsVisible(True)
    return action


BasicToolbar.add_tool = add_tool


def _get_fitter(self, cls):
    """The one fitter of class ``cls`` for this ``ProfileTools``, so for this Profile viewer."""
    fitters = vars(self).setdefault("_fitters", {})
    if cls not in fitters:
        fitters[cls] = cls()
    return fitters[cls]


_original_on_settings = ProfileTools._on_settings


def _on_settings(self):
    """
    glue-qt's Settings, of `_get_fitter`'s fitter, in its own ``settings_widget`` where it has one, as the IRIS fitter's
    component list (D86; glue-qt fork branch ``fitter-settings-widget``).
    """
    fitter = _get_fitter(self, self.fit_function)
    getattr(fitter, "settings_widget", FitSettingsWidget)(fitter).exec_()


def needs_fitter_settings_workaround(method=_original_on_settings):
    """Whether ``method`` opens glue-qt's Settings dialog for a fitter with its own ``settings_widget``."""
    opened, default = [], profile_tools.FitSettingsWidget
    fitter = SimpleNamespace(settings_widget=lambda fitter: SimpleNamespace(exec_=lambda: opened.append(fitter)))
    profile_tools.FitSettingsWidget = lambda fitter: SimpleNamespace(exec_=lambda: None)  # no dialog, nor QApplication
    try:
        method(SimpleNamespace(fit_function=lambda: fitter, _get_fitter=lambda: fitter))
    finally:
        profile_tools.FitSettingsWidget = default
    return opened != [fitter]


_original_fit = ProfileTools._fit


def _fit(self, fitter, xlim=None):
    """
    glue-qt 0.4.2 makes a new fitter for Settings and for each fit, so no fit has what Settings set; both use
    `_get_fitter`'s. Retired by glue-qt's ``ProfileTools._get_fitter`` (``wp0-qt-fitter-settings``).
    """
    return _original_fit(self, _get_fitter(self, type(fitter)), xlim)


if not hasattr(ProfileTools, "_get_fitter") or _needs(needs_fitter_settings_workaround):
    ProfileTools._on_settings = _on_settings
if not hasattr(ProfileTools, "_get_fitter"):
    ProfileTools._fit = _fit

_original_plot_fit = ProfileTools._plot_fit


def _plot_fit(self, fitter, fit_result, x, y, normalize):
    """
    glue-qt's ``_plot_fit``, keeping every artist a fitter's ``plot`` returns, as glue's docstring asks, not only the
    first, so that Clear removes each line's curve of the IRIS fit (D86; glue-qt fork branch ``fit-artists``).
    """
    self._clear_fit()
    for layer in fit_result:
        self._fit_artists.extend(
            fitter.plot(
                fit_result[layer],
                self.axes,
                x,
                alpha=layer.state.alpha,
                linewidth=layer.state.linewidth * 0.5,
                color=layer.state.color,
                normalize=normalize.get(layer, None),
            )
        )
    self.canvas.draw_idle()


def needs_fit_artists_workaround(method=_original_plot_fit):
    """Whether ``method`` keeps fewer artists than a fitter's ``plot`` returns."""

    class Layer:  # a dictionary key, as glue-qt's layer artists
        state = SimpleNamespace(alpha=1, linewidth=1, color="k")

    tools = SimpleNamespace(
        _fit_artists=[], _clear_fit=lambda: None, axes=None, canvas=SimpleNamespace(draw_idle=lambda: None)
    )
    method(tools, SimpleNamespace(plot=lambda *args, **kwargs: ["first", "second"]), {Layer: None}, None, None, {})
    return tools._fit_artists != ["first", "second"]


if _needs(needs_fit_artists_workaround):
    ProfileTools._plot_fit = _plot_fit


_original_update_icons = colors.QColormapCombo._update_icons
_icons = {}  # (id(colormap), width): (colormap, icon), the colormap kept so that its id stays its own


def update_icons(self):
    """
    glue-qt's ``QColormapCombo._update_icons``, sharing each colormap's icon at each width between combos: glue-qt 0.4.2
    draws every listed colormap at each build or resize, 30 ms with sunpy's (#177). Probed at the first combo, which
    needs Qt's application.
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
    return _needs(needs_icon_cache_workaround)


colors.QColormapCombo._update_icons = update_icons


_original_find_combo_data = connect._find_combo_data


def find_combo_data(widget, value):
    """
    echo's ``_find_combo_data``, matching a colormap to the entry that is it, then to one of its name or sunpy key,
    before an earlier one of equal colors: echo 0.15 matched an AIA 171 map to SUVI 171 (#194). A map's colormap and a
    restored one are matplotlib's copies, named by sunpy's key or the saved name.
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


if _needs(needs_combo_match_workaround):
    connect._find_combo_data = find_combo_data


_original_can_trigger = UserAction._can_trigger
_APPLIES = {}  # a layer action's callback: its ``applies``, where glue-qt's layer actions take none


def user_action_can_trigger(self):
    """
    glue-qt's ``UserAction._can_trigger``, also false where the action's ``applies`` (`layer_action`) is: glue-qt 0.4.2
    shows each layer action on every layer of its kind, mostly ending in an error box (#223, #257).
    """
    if not _original_can_trigger(self):
        return False
    applies, layers = _APPLIES.get(self._callback), self.selected_layers()
    return applies is None or applies(layers[0] if self._single else layers)


def needs_layer_action_applies_workaround():
    """Whether glue-qt's layer actions take no ``applies``."""
    try:
        LayerActionRegistry()("probe", applies=bool)
    except TypeError:
        return True
    return False


_needs_applies_workaround = _needs(needs_layer_action_applies_workaround)
if _needs_applies_workaround:
    UserAction._can_trigger = user_action_can_trigger


def _application(data_collection):
    """The glue window of ``data_collection``, or None."""
    windows = QtWidgets.QApplication.topLevelWidgets()
    return next((window for window in windows if getattr(window, "data_collection", None) is data_collection), None)


def refresh_layer_actions(data_collection):
    """
    Show the right-click entries of the glue window of ``data_collection`` that take its selection now, and hide the
    others: glue-qt does so when the selection changes only, so a run that changes its own guard, as 'IRIS: radiometric
    calibration' does, left its entry offered.
    """
    app = _application(data_collection)
    for action in [] if app is None else app.findChildren(LayerAction):
        action.update_enabled()


def _takes(check, *args, **kwargs):
    """
    Whether ``check``, the guard an entry's run calls too (D61), takes these arguments, raising no ValueError: also
    true for any other error, so that running the entry shows it in the entry's own error box (D72 223-5).
    """
    try:
        check(*args, **kwargs)
    except ValueError:  # the guard's refusal
        return False
    except Exception:  # noqa: BLE001 - a fault, not a refusal
        return True
    return True


def layer_action(label, check, **kwargs):
    """
    glue-qt's ``layer_action``, shown only where ``check``, the action's own guard, takes the selection: the layer, or
    the layers of an action not ``single``; the entries are refreshed for the selection once it returns
    (`refresh_layer_actions`).
    """
    applies = partial(_takes, check)

    def adder(func):
        @wraps(func)
        def run(selection, data_collection):
            func(selection, data_collection)
            refresh_layer_actions(data_collection)

        if _needs_applies_workaround:
            _APPLIES[run] = applies
            return glue_layer_action(label, **kwargs)(run)
        return glue_layer_action(label, applies=applies, **kwargs)(run)

    return adder
