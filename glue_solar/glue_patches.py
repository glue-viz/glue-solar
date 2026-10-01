"""
Gated fixes for glue-core and glue-qt bugs that IRIS data hits.

Each fix installs only when a probe finds the bug, and names the upstream change that retires it.
"""

from types import SimpleNamespace

import numpy as np
from glue.core import Data, DataCollection, component_link, coordinate_helpers
from glue.core.component_link import ComponentLink
from glue.core.coordinate_helpers import unbroadcast
from glue.core.exceptions import IncompatibleAttribute
from glue.utils import defer_draw
from glue.viewers.image.layer_artist import ImageSubsetLayerArtist
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState
from glue_qt.plugins.tools.pv_slicer import pv_slicer
from glue_qt.viewers.image import ImageViewer
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from astropy.visualization.wcsaxes import WCSAxes
from astropy.wcs import WCS

__all__ = [
    "needs_axis_label_workaround",
    "needs_crosshair_workaround",
    "needs_inverse_workaround",
    "needs_pixel_point_workaround",
    "needs_pv_slice_workaround",
    "sync_pv_slice",
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
            self.state.layer.subset_state.get_xy(self.layer.data, viewer.x_att.axis, viewer.y_att.axis)
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
        _viewer_state=SimpleNamespace(x_att=data.pixel_component_ids[1], y_att=data.pixel_component_ids[0]),
    )
    method(artist, redraw=False)
    return line_x.get_visible()


if needs_crosshair_workaround():
    ImageSubsetLayerArtist._update_visual_attributes = _update_visual_attributes


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
