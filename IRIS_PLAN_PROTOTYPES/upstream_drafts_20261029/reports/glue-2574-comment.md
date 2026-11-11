# glue-core #77: world axes of data with more world axes than pixel axes (comment on glue#2574)

- **Where:** a comment on glue-viz/glue#2574 ("Component issue when using n-D data with an m-D coordinate system",
  open since 2026-02-12, 0 comments). #2573 (merged, in 1.27.0) by the same reporter fixed the units only.
- **Review row:** glue-core #77 (UPSTREAM_REVIEW, REPORT: a comment with probe 77 and a design proposal, then a
  medium-large PR). No fork branch exists for it; the register row's "on a fork branch (D89)" should read "glue#2574".
- **Reproducer:** `scripts/glue_world_axes.py`, run by `run.sh rel|main glue_world_axes.py`; outputs
  `out/glue_world_axes_{rel,main}.txt` (identical; main 3683f07c is the v1.28.0 tag).

## Comment (paste)

This still happens on glue-core 1.28.0, which is also main (3683f07c), and it is more than the units. Here is a
reproducer with astropy only: a (lon, lat, wavelength) WCS sliced at one latitude pixel, so 2 pixel axes and 3 world
axes, as for a slit spectrum.

```python
import numpy as np
from astropy.wcs import WCS
from astropy.wcs.wcsapi import HighLevelWCSMixin, SlicedLowLevelWCS

import glue
from glue.core import Data


class SlicedWCS(SlicedLowLevelWCS, HighLevelWCSMixin):
    """A sliced WCS with both APE 14 interfaces, as glue's coordinates need."""

    @property
    def low_level_wcs(self):
        return self


wcs3 = WCS(naxis=3)
wcs3.wcs.ctype = ["HPLN-TAN", "HPLT-TAN", "WAVE"]
wcs3.wcs.cunit = ["arcsec", "arcsec", "Angstrom"]
wcs3.wcs.cdelt = [1, 1, 0.1]
wcs3.wcs.crval = [0, 0, 6000]
wcs3.wcs.crpix = [1, 1, 1]
wcs = SlicedWCS(wcs3, (slice(None), 5, slice(None)))  # numpy order (wave, lat, lon): latitude pixel 5
data = Data(flux=np.zeros((4, 6)), coords=wcs, label="spectrum")

print("glue", glue.__version__, "from", glue.__file__)
print("pixel axes", wcs.pixel_n_dim, "world axes", wcs.world_n_dim, wcs.world_axis_physical_types)
print("axis correlation matrix (rows: world lon, lat, wave; columns: WCS pixel axes 0 and 1):",
      wcs.axis_correlation_matrix.astype(int).tolist())


def values(array):
    return [float(f"{v:.5g}") for v in array]


for axis, cid in enumerate(data.world_component_ids):  # glue's world component for each pixel axis (numpy order)
    along = data[cid][(slice(None), 0) if axis == 0 else (0, slice(None))]
    print(f"glue's {cid.label!r} for pixel axis {axis}: unit {data.get_component(cid).units!r}, values along "
          f"the axis {values(along)}")
lon, lat, wave = wcs.pixel_to_world_values(np.arange(6), np.zeros(6))
print("the WCS's world values along pixel axis 1: lon", values(lon), "lat", values(lat))
for link in data.coordinate_links:  # the links glue uses to link this dataset to others
    to = link.get_to_id()
    try:
        result = link.compute(data)
    except Exception as error:  # noqa: BLE001
        print(f"coordinate link to {to.label!r}: {type(error).__name__}: {error}")
        continue
    if to in data.world_component_ids:
        axis = data.world_component_ids.index(to)
        print(f"coordinate link to {to.label!r} gives {values(result[(slice(None), 0) if axis == 0 else (0, slice(None))])}")
```

The output (path shortened):

```
glue 1.28.0 from .../site-packages/glue/__init__.py
pixel axes 2 world axes 3 ['custom:pos.helioprojective.lon', 'custom:pos.helioprojective.lat', 'em.wl']
axis correlation matrix (rows: world lon, lat, wave; columns: WCS pixel axes 0 and 1): [[1, 0], [1, 0], [0, 1]]
glue's 'World 0' for pixel axis 0: unit 'm', values along the axis [6e-07, 6.0001e-07, 6.0002e-07, 6.0003e-07]
glue's 'World 1' for pixel axis 1: unit 'deg', values along the axis [0.0013889, 0.0013889, 0.0013889, 0.0013889, 0.0013889, 0.0013889]
the WCS's world values along pixel axis 1: lon [0.0, 0.00027778, 0.00055556, 0.00083333, 0.0011111, 0.0013889] lat [0.0013889, 0.0013889, 0.0013889, 0.0013889, 0.0013889, 0.0013889]
coordinate link to 'World 0' gives [0.0013889, 0.0013889, 0.0013889, 0.0013889]
coordinate link to 'Pixel Axis 0 [y]': IndexError: tuple index out of range
coordinate link to 'World 1' gives [0.0, 0.00027778, 0.00055556, 0.00083333, 0.0011111, 0.0013889]
coordinate link to 'Pixel Axis 1 [x]': IndexError: tuple index out of range
```

So:

1. glue makes one world component per pixel axis and gives pixel axis `i` world axis `world_n_dim - 1 - i`. Pixel
   axis 1 (x) gets latitude, which is constant along it, and longitude, the world axis that does vary along x, gets
   no component.
2. Since #2573 the components and the coordinate links disagree. The components use `world_n_dim - 1 - axis`
   (`component.py:248, 270`), while `CoordinateComponentLink` still uses `ndim - 1 - index` (`component_link.py:389,
   393, 395`). The link to 'World 0', whose component holds wavelength in m, computes latitude, and the link to
   'World 1' (latitude) computes longitude. Any link to another dataset through these components carries the wrong
   world axis.
3. The world-to-pixel links pass one value per world component (2) to a WCS that takes 3, so they raise IndexError,
   and nothing can link to this dataset's pixels through its world coordinates.

A design that would cover the case in this issue:

- **One world component per world axis**, `world_n_dim` of them, not one per pixel axis
  (`Data._update_world_components` and `_set_up_coordinate_component_links` in `data.py`). Each would be computed
  over the pixel axes its row of `axis_correlation_matrix` names. Lon would then exist.
- **Pixel axis to world axis by `axis_correlation_matrix`** wherever one world axis per pixel axis is needed. These
  are the axis label (`coordinate_helpers.axis_label`), the Image viewer's `x_att_world`/`y_att_world`
  (`image/state.py:248, 256`) and WCSAxes coordinate (`image/viewer.py:59, 68`), and glue-qt's slider values. For
  each pixel axis in WCS order (x first), take the first world axis in world order that is correlated with it and
  not taken yet. Here that is x → lon and y → wavelength. A world axis left over, here latitude, keeps its component with no pixel axis of its
  own.
- **World-to-pixel links that take every world component** (`component_link.py`), so linking works whatever the two
  numbers of axes are.

For a WCS with as many world axes as pixel axes, in the same order, as for most FITS images and cubes (lon, lat and
wavelength), this gives the same mapping as today. If this direction sounds right, I can work on a PR.

## Notes for the user (not to paste)

- Verified against v1.26.0: there, `CoordinateComponent` and `CoordinateComponentLink` both used `ndim - 1 - axis`,
  so point 2 (components and links disagreeing) came with #2573 in 1.27.0.
- The tie rule ("first world axis in world order not taken") gives x → lon here. A DKIST slit raster, where lon and
  lat both vary along the slit and the raster step, needs a better tie-break for `_glue_order`'s choice (by pointing
  span) to retire. That is a point for the PR's discussion; the comment does not promise it.
- Pasting the script makes the comment long. To shorten it, link a gist and paste only the output.
