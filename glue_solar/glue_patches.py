"""
Gated fixes for glue-core bugs that IRIS data hits.

Each fix installs only when a probe finds the bug, and names the upstream change that retires it.
"""

from types import SimpleNamespace

import numpy as np
from glue.core import component_link, coordinate_helpers
from glue.core.coordinate_helpers import unbroadcast

__all__ = ["needs_inverse_workaround", "world2pixel_single_axis"]

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
