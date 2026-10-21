"""
hint_cost.py: the CPU time sst_hints.hint_view adds to a read (pages cached), for glue's buffer views of a panel's size
(88 x 205 bins, as here) and of a maximized panel (576 x 720), on a small synthetic map in this folder.
"""

import os
import time
from types import SimpleNamespace

import numpy as np
from glue.core.component import Component
from glue.core.component_id import ComponentID
from glue.utils import unbroadcast

import sst_hints

path = "synthetic.raw"
shape = (2, 34, 512, 1918)  # scan, tuning, y, x: rows as long as the 2022 cube's
if not os.path.exists(path):
    np.arange(np.prod(shape), dtype=">f4").reshape(shape).tofile(path)
values = np.memmap(path, ">f4", "r", shape=shape)
cid = ComponentID("values")
cube = SimpleNamespace(_components={cid: Component(values)}, ndim=4)


def frb_view(bounds):
    """The view glue's compute_fixed_resolution_buffer gives get_data, for these bounds."""
    coords = [np.linspace(*b) if isinstance(b, tuple) else b for b in bounds]
    grid = np.meshgrid(*coords, indexing="ij", copy=False)
    # as glue: each axis's coordinate rounded unbroadcast, then broadcast to the buffer's shape
    return tuple(np.broadcast_to(np.clip(np.round(unbroadcast(g)).astype(int), 0, n - 1), grid[0].shape)
                 for g, n in zip(grid, shape))


views = {
    "slit 205x88": frb_view([1, (-0.5, 33.5, 205), (-0.5, 511.5, 88), 959]),
    "map 88x205": frb_view([1, 16, (0.5, 511.5, 88), (-0.5, 1917.5, 205)]),
    "slit 720x576": frb_view([1, (-0.5, 33.5, 720), (-0.5, 511.5, 576), 959]),
    "map 576x720": frb_view([1, 16, (0.5, 511.5, 576), (-0.5, 1917.5, 720)]),
}
for name, view in views.items():
    # the check: the pages asked for cover every page the read touches
    starts, length = sst_hints.hint_view(cube, cid, view)
    asked = {p for page, n in sst_hints._ranges(starts, length) for p in range(page, page + n)}
    touched = set((sum(i.astype(np.int64) * s for i, s in zip(view, values.strides)) // sst_hints._PAGE).ravel().tolist())
    assert touched <= asked, name
    print(f"{name:14} pages touched {len(touched)}, asked for {len(asked)}, in {len(sst_hints._ranges(starts, length))} calls")
    np.asarray(values[view])  # cached and mapped
    import sst_hints_v1  # the first version, np.unique over every value

    for label, hint in (("read", None), ("hint + read", sst_hints.hint_view), ("v1 hint + read", sst_hints_v1.hint_view)):
        times = []
        for _ in range(20):
            t = time.perf_counter()
            if hint:
                hint(cube, cid, view)
            np.asarray(values[view])
            times.append((time.perf_counter() - t) * 1e3)
        print(f"{name:14} {label:12} {np.median(times):7.2f} ms  ({view[0].size} values)")
