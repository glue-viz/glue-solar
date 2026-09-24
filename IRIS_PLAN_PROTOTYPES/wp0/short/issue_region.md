Adding a `RegionData` layer to an image viewer crashes when the image `Data` has WCS coordinates; with `coords=None` the same layer draws.

```python
import numpy as np
import shapely
from astropy.wcs import WCS
from glue.core import Data
from glue.core.application_base import Application
from glue.core.data_region import RegionData
from glue.core.link_helpers import LinkSame
from glue.viewers.image.viewer import SimpleImageViewer

w = WCS(naxis=2)
w.wcs.ctype = ['HPLN-TAN', 'HPLT-TAN']
w.wcs.cunit = ['arcsec', 'arcsec']
w.wcs.cdelt = [1, 1]
w.wcs.crpix = [8, 8]
w.wcs.crval = [0, 0]

d = Data(label='img', x=np.zeros((16, 16)))
d.coords = w  # with d.coords = None everything below works
reg = RegionData(label='fov', regions=np.array([shapely.Polygon([(4, 4), (8, 4), (8, 9), (4, 9)])]))

app = Application()
dc = app.data_collection
dc.append(d)
dc.append(reg)
v = app.new_data_viewer(SimpleImageViewer, data=d)
dc.add_link(LinkSame(reg.center_x_id, d.pixel_component_ids[1]))
dc.add_link(LinkSame(reg.center_y_id, d.pixel_component_ids[0]))
v.add_data(reg)  # AttributeError below
```

```
  File "glue/viewers/scatter/layer_artist.py", line 698, in _update_data
  File "glue/core/data_region.py", line 283, in conv_function
  File "glue/core/data_region.py", line 219, in conv_function
  File "glue/core/component_link.py", line 393, in using
  File "glue/core/coordinate_helpers.py", line 42, in pixel2world_single_axis
    original_shape = pixel[0].shape
AttributeError: 'tuple' object has no attribute 'shape'
```

The transform chain is region centre -> pixel `LinkSame` -> the image's coordinate links, and the coordinate link's `using` receives a tuple where `pixel2world_single_axis` expects arrays. Wrapping the inputs of `conv_function` in `np.asarray` stops the crash, but the layer then disables itself ("depends on attributes that cannot be derived"), so this needs a real look rather than a one-line patch. Not the same as #2464.

glue-core 1.27.0 and current main (dae530c3), python 3.14, numpy 2.5, matplotlib 3.11, astropy 8.0, shapely 2.1.

Label: bug.
