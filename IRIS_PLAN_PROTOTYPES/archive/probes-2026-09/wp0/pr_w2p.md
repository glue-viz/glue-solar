### Description

`world2pixel_single_axis` decides which world inputs to keep per element with

```python
world_dep = wcs.axis_correlation_matrix[:, pixel_axis]
```

and collapses every other world input to its first element (`.flat[0]`). That is only correct when the requested pixel axis can be inverted from the world axes that depend on it directly. For a cube whose celestial axes depend on (x, y, t) - e.g. a scanning slit-jaw sequence described by a gWCS - inverting pixel axis x needs the time world value of every element, but the time world axis has a 0 in the x column of the matrix, so today the derived x uses the time of the first element only.

Synthetic repro: pixel axes (x, t), world lon = x + 10 t and time = t, correlation matrix `[[1, 1], [0, 1]]`; all three points sit at pixel x = 5:

```python
import numpy as np
from astropy.wcs.wcsapi import BaseLowLevelWCS
from glue.core.coordinate_helpers import world2pixel_single_axis

class W(BaseLowLevelWCS):
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
lon = np.array([5., 15., 25.]); t = np.array([0., 1., 2.])
w.world_to_pixel_values(lon, t)[0]                  # [5. 5. 5.]
world2pixel_single_axis(w, lon, t, pixel_axis=0)    # main: [ 5. 15. 25.]   this PR: [5. 5. 5.]
```

On a real IRIS SJI gWCS (lon/lat/time linked to a raster) the derived SJI pixel x for frames 0/30/61 comes out as [21.05, 144.96, 275.06] instead of the direct `world_to_pixel_values` result [21.05, 20.62, 21.24].

### Changes

- Take the transitive closure of the correlation matrix: also keep every world axis that shares a pixel axis with a world axis already kept (a loop bounded by the number of world axes). For the usual FITS WCS (celestial pair plus independent spectral axis, with or without a PC rotation) the closure of a column is that column, so results are unchanged.
- Test: `test_world2pixel_single_axis_correlated_axes` in `glue/core/tests/test_coordinates.py` (the `W` above; `pixel_axis=0` -> `[5, 5, 5]`, `pixel_axis=1` -> `[0, 1, 2]`); fails on `main` with `[5, 15, 25]`.

Checks: ruff v0.15.20 clean on the changed files; `pytest glue/core/tests/test_state.py glue/core/tests/test_component_link.py glue/core/tests/test_coordinate_links.py glue/core/tests/test_coordinates.py glue/core/tests/test_data_region.py glue/utils/tests/test_matplotlib.py glue/utils/tests/test_array.py`: 249 passed, 1 skipped. No existing issue found (searched for `axis_correlation_matrix` and `world2pixel_single_axis`).

Label: bug
