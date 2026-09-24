"""Workarounds for glue-core bugs that IRIS data hits; each names the upstream change that makes it removable."""

import numpy as np
from glue.core import component_link, coordinate_helpers
from glue.core.coordinate_helpers import unbroadcast


def world2pixel_single_axis(wcs, *world, pixel_axis=None):
    # ponytail: monkeypatch, remove when glue-core fixes coordinate_helpers.world2pixel_single_axis. 1.27.0
    # (line 104) keeps only the world axes directly correlated with ``pixel_axis`` and collapses the others to
    # their first element, so a gWCS whose lon/lat depend on time (irispy SJI) is inverted at exposure 0 for
    # every frame. Only the three "needed" lines differ from upstream.
    if pixel_axis is None:
        raise ValueError("pixel_axis needs to be set")
    if np.size(world[0]) == 0:
        return np.array([], dtype=float)
    matrix = wcs.axis_correlation_matrix
    needed = matrix[:, pixel_axis].copy()
    for _ in range(matrix.shape[0]):  # transitive closure: world axes sharing a pixel axis with a needed one
        needed |= (matrix & matrix[needed].any(axis=0)).any(axis=1)
    original_shape = world[0].shape
    world = np.broadcast_arrays(*[unbroadcast(w) if keep else w.flat[0] for w, keep in zip(world, needed)])
    if len(world) == 1 and world[0].ndim > 1:  # astropy#12154: a 1D WCS cannot take arbitrary shapes
        result = wcs.world_to_pixel_values(world[0].ravel()).reshape(world[0].shape)
    else:
        result = wcs.world_to_pixel_values(*world)
        if len(world) > 1:
            result = result[pixel_axis]
    return np.broadcast_to(result, original_shape)


coordinate_helpers.world2pixel_single_axis = world2pixel_single_axis
component_link.world2pixel_single_axis = world2pixel_single_axis  # imported there by name
