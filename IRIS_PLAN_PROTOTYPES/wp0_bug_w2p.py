import numpy as np
from astropy.wcs.wcsapi import BaseLowLevelWCS
from glue.core.coordinate_helpers import world2pixel_single_axis

class W(BaseLowLevelWCS):
    """2 pixel axes (x, t); world lon = x + 10*t depends on both, world time = t."""
    pixel_n_dim = world_n_dim = 2
    world_axis_physical_types = ['custom:pos.helioprojective.lon', 'time']
    world_axis_units = ['arcsec', 's']
    world_axis_object_components = [('c', 0, 'value'), ('t', 0, 'value')]
    world_axis_object_classes = {'c': (float, (), {}), 't': (float, (), {})}
    array_shape = pixel_shape = None
    axis_correlation_matrix = np.array([[True, True], [False, True]])
    def pixel_to_world_values(self, x, t): return x + 10 * t, t
    def world_to_pixel_values(self, lon, t): return lon - 10 * t, t

w = W()
lon = np.array([5., 15., 25.]); t = np.array([0., 1., 2.])   # all three points sit at pixel x = 5
print('direct world_to_pixel x:', w.world_to_pixel_values(lon, t)[0])
print('world2pixel_single_axis x:', world2pixel_single_axis(w, lon, t, pixel_axis=0))
