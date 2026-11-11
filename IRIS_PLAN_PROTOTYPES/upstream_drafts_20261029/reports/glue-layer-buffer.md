# glue-core #85: a linked layer's Image buffer covers the whole view

- **Where:** a new issue on glue-viz/glue (bug template). No existing issue found (`gh search issues` for
  "fixed_resolution_buffer", "footprint", "mosaic", "WCSLink performance"). Draft PR #2507 (FRB performance) shares
  pixel transforms between the layers of one dataset; it does not cull to a layer's footprint.
- **Review row:** glue-core #85 (UPSTREAM_REVIEW, REPORT). Replaces the draft
  `scratchpad/fix13/wp13-dkist-read-path/glue-layer-buffers.md`.
- **Reproducer:** `scripts/glue_layer_buffer.py`, run by `run.sh rel|main glue_layer_buffer.py`; outputs
  `out/glue_layer_buffer_{rel,main}.txt`. Release: glue-core 1.28.0 (pip). Main: glue 3683f07c, from this folder's
  clone ahead on the path. main is at the v1.28.0 tag (3683f07c, no commits after it), so the body keeps one output
  block; the main run (`out/glue_layer_buffer_main.txt`) gave 20.6 and 20.5 ms each, 0.6 ms.

## Title

Image viewer: a WCS-linked layer's buffer is computed over the whole view, not over the layer's footprint

## Body (paste)

**Describe the bug**

In an Image viewer, each layer that is not the reference data gets a fixed-resolution buffer over the whole view:
`BaseImageLayerState.get_sliced_data` passes the full view to `compute_fixed_resolution_buffer` (`image/state.py:461`),
which translates every view pixel through the link to the layer's pixels (`translate_pixel`,
`fixed_resolution_buffer.py:212-228`) and only then drops the ones outside the layer. When the layer is a small image
in a large view, such as one tile of a mosaic, nearly all of that work is thrown away.

In the script below, 20 tiles of 40 x 40 pixels sit on a 2000 x 2000 reference image, each linked to it by `WCSLink`.
Each tile's buffer is about 95,000 view pixels, of which 25 fall inside the tile; it takes about 20 ms, against
0.6 ms for the tile's footprint alone at the same density. Every pan or zoom computes all 20 again (0.4 s of the
0.47 s redraw). With the 108 tiles of a DKIST DL-NIRSP mosaic on real WCSes, we measured 0.67 s per tile and about
37 s per pan or slider move.

The link is also evaluated once per pixel axis of the layer (`translate_pixel` is called for each of
`data.pixel_component_ids`), so for a `WCSLink` each buffer runs the full `pixel_to_pixel` twice and keeps one output
each time.

**To Reproduce**

```python
import time

import numpy as np
from astropy.wcs import WCS
from echo import delay_callback

import glue
from glue.core import Data
from glue.core.application_base import Application
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink
from glue.viewers.image.viewer import SimpleImageViewer


def make_wcs(crpix):
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]
    wcs.wcs.cunit = ["arcsec", "arcsec"]
    wcs.wcs.cdelt = [1, 1]
    wcs.wcs.crpix = crpix
    return wcs


app = Application()
ref = Data(x=np.zeros((2000, 2000)), coords=make_wcs([1000, 1000]), label="ref")
app.data_collection.append(ref)
tiles = []
for i in range(20):  # 20 tiles of 40 x 40 pixels, the first at reference pixel (x, y) = (100, 100)
    x0, y0 = 100 + 90 * i, 100 + 85 * i
    tile = Data(y=np.ones((40, 40)), coords=make_wcs([1000 - x0, 1000 - y0]), label=f"tile {i}")
    app.data_collection.append(tile)
    app.data_collection.add_link(WCSLink(ref, tile))
    tiles.append(tile)

calls = []
original = Data.compute_fixed_resolution_buffer


def recorded(self, bounds, target_data=None, **kwargs):
    start = time.perf_counter()
    array = original(self, bounds, target_data=target_data, **kwargs)
    if self is not target_data:
        calls.append((array.size, int(np.isfinite(array).sum()), time.perf_counter() - start))
    return array


Data.compute_fixed_resolution_buffer = recorded

viewer = app.new_data_viewer(SimpleImageViewer)
print("glue", glue.__version__, "from", glue.__file__)
for what in ("adding the 20 tiles and drawing", "a pan of 10 pixels and drawing"):
    calls.clear()
    start = time.perf_counter()
    if what.startswith("adding"):
        viewer.add_data(ref)
        for tile in tiles:
            viewer.add_data(tile)
    else:
        with delay_callback(viewer.state, "x_min", "x_max"):
            viewer.state.x_min, viewer.state.x_max = viewer.state.x_min + 10, viewer.state.x_max + 10
    viewer.figure.canvas.draw()
    total = time.perf_counter() - start
    computed = [c for c in calls if c[2] > 1e-3]  # cache hits return at once
    size, inside, seconds = computed[0]
    print(f"{what}: {total:.2f} s; {len(computed)} tile buffers computed, {size} pixels each with {inside} "
          f"inside the tile, {1000 * sum(c[2] for c in computed) / len(computed):.1f} ms each")

# The same density over one tile's footprint alone (tile 0 covers reference pixels 100-139 on both axes)
view = viewer.axes.get_window_extent()
step_x = (viewer.state.x_max - viewer.state.x_min) / round(view.width)
step_y = (viewer.state.y_max - viewer.state.y_min) / round(view.height)
footprint = [(100, 139, round(40 / step_y)), (100, 139, round(40 / step_x))]
start = time.perf_counter()
array = original(tiles[0], footprint, target_data=ref, target_cid=tiles[0].id["y"])
print(f"tile 0 over its footprint at the same density: {array.size} pixels, {int(np.isfinite(array).sum())} inside, "
      f"{1000 * (time.perf_counter() - start):.1f} ms")
```

Output on glue-core 1.28.0, paths shortened. main is the v1.28.0 tag commit (3683f07c), so this is main too:

```
glue 1.28.0 from .../site-packages/glue/__init__.py
adding the 20 tiles and drawing: 2.75 s; 20 tile buffers computed, 94962 pixels each with 25 inside the tile, 20.4 ms each
a pan of 10 pixels and drawing: 0.47 s; 20 tile buffers computed, 94962 pixels each with 25 inside the tile, 20.0 ms each
tile 0 over its footprint at the same density: 49 pixels, 49 inside, 0.6 ms
```

**Expected behavior**

A layer's buffer costs about as much as the part of the view the layer covers. Two possible changes:

- Translate the view's corners, or a coarse grid of it, first, and compute the buffer only over the layer's footprint
  in the view, NaN elsewhere.
- Translate all of a layer's pixel axes in one evaluation of a link that gives them together, such as `WCSLink`,
  rather than once per pixel axis.

**Details:**

- Operating System: Fedora Linux 44
- Python version (``python --version``): Python 3.13.16
- Glue version (``glue --version``): glue-core 1.28.0 (main is at its tag, 3683f07c)
- How you installed glue: pip

**Additional context**

astropy 8.0.2, numpy 2.5.4, matplotlib 3.11.2, echo 0.16.0. #2507 shares pixel transforms between the layers of one
dataset, which does not help here, as each tile is its own dataset.

## Notes for the user (not to paste)

- The DKIST figures (0.67 s per tile, about 37 s per move with 107 tiles) are the draft's, from glue-solar's
  profiling on CARJML (DL-NIRSP); they were not re-run here (they need the data). Drop that sentence if you prefer only
  re-run numbers.
- The once-per-pixel-axis evaluation was counted with cProfile: 5 buffers of one tile made 10 `WCSLink` `forwards`
  calls. Most of a buffer's time is astropy's `all_pix2world` and `all_world2pix` over the view's pixels.
- The draft's third idea (keep the spatial translation across a slider move) is left out: not measured here.
