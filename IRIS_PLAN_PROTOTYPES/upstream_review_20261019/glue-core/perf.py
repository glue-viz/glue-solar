"""Key numbers of GLUE_SPEED's glue-core findings on synthetic data: python -I perf.py release|main."""
import os
import sys
import time
import tracemalloc

S = "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/df774a44-db13-4c72-b097-0d85fb986df9/scratchpad/upstream/glue-core"
if sys.argv[1] == "main":
    sys.path.insert(0, os.path.join(S, "glue-main"))

import numpy as np  # noqa: E402
import glue  # noqa: E402
from glue.core import Data, DataCollection  # noqa: E402
from glue.core.link_helpers import LinkSame  # noqa: E402
from glue.core.state import GlueSerializer  # noqa: E402
from glue.core.subset import SliceSubsetState  # noqa: E402
from glue.utils import view_shape  # noqa: E402

print("glue from", glue.__file__)


def timed(f):
    t = time.perf_counter()
    r = f()
    return time.perf_counter() - t, r


def star(n):
    datasets = [Data(x=np.zeros((2, 2)), y=np.zeros((2, 2)), label=f"d{i}") for i in range(n)]
    dc = DataCollection(datasets)
    links = []
    for d in datasets[1:]:
        links += [LinkSame(datasets[0].id["x"], d.id["x"]), LinkSame(datasets[0].id["y"], d.id["y"])]
    return dc, datasets, links


# R6: one link update on a star of N datasets; R24: append one at a time
for n in (36, 99):
    dc, datasets, links = star(n)
    dc.add_link(links)
    t, _ = timed(dc._link_manager.update_externally_derivable_components)
    print(f"R6 update_externally_derivable_components, star N={n}: {t:.3f} s")
    t, _ = timed(lambda: dc.append(Data(x=np.zeros((2, 2)), label="new")))
    print(f"R6/R24 append one dataset to a linked star of N={n}: {t:.3f} s")
    # R12: remove a leaf
    t, _ = timed(lambda: dc.remove(datasets[-1]))
    print(f"R12 remove a leaf from the star N={n}: {t:.3f} s")

dc = DataCollection()
t, _ = timed(lambda: [dc.append(Data(x=np.zeros((2, 2)), label=f"u{i}")) for i in range(102)])
print(f"R24 append 102 unlinked datasets one at a time: {t:.3f} s")
dc2 = DataCollection()
t, _ = timed(lambda: dc2.extend([Data(x=np.zeros((2, 2)), label=f"u{i}") for i in range(102)]))
print(f"R24 extend 102 unlinked datasets at once: {t:.3f} s")

# R21: compute_statistic mean over a float32 cube: time and peak
cube = Data(x=np.random.random((200, 300, 400)).astype(np.float32), label="cube")
tracemalloc.start()
t, r = timed(lambda: cube.compute_statistic("mean", cube.id["x"], axis=(1, 2)))
peak = tracemalloc.get_traced_memory()[1] / 2**20
tracemalloc.stop()
print(f"R21 compute_statistic mean over float32 (200,300,400) = {cube.size * 4 / 2**20:.0f} MiB: {t:.3f} s, peak {peak:.0f} MiB")

# R23: histogram of a SliceSubsetState (one pixel) on the cube
point = SliceSubsetState(cube, [slice(None), slice(10, 11), slice(20, 21)])
tracemalloc.start()
t, r = timed(lambda: cube.compute_histogram([cube.id["x"]], subset_state=point, range=[(0, 1)], bins=[10]))
peak = tracemalloc.get_traced_memory()[1] / 2**20
tracemalloc.stop()
print(f"R23 compute_histogram of a one-pixel SliceSubsetState on the cube: {t * 1000:.1f} ms, peak {peak:.0f} MiB")

# R27: float32 * 2 dtype
d = Data(x=np.zeros((100, 100), np.float32), label="d")
d["y"] = d.id["x"] * 2
print(f"R27 float32 * 2 derived dtype: {d['y'].dtype}")

# R20: do() calls per object in a session save; broadcast component bytes
d = Data(x=np.zeros((3, 4)), label="d")
dc = DataCollection([d])
calls = {}
original_do = GlueSerializer.do


def counting_do(self, obj):
    calls[id(obj)] = calls.get(id(obj), 0) + 1
    return original_do(self, obj)


GlueSerializer.do = counting_do
GlueSerializer(dc).dumps()
GlueSerializer.do = original_do
print(f"R20 do() calls per object in one save: max {max(calls.values())}, objects {len(calls)}, total {sum(calls.values())}")
b = Data(label="b")
b.add_component(np.broadcast_to(np.arange(100, dtype=np.float64), (300, 400, 100)), "t")  # 9.6 MB broadcast of 800 B
size = len(GlueSerializer(DataCollection([b])).dumps())
print(f"R20 session bytes for a (300,400,100) broadcast of 100 values: {size / 2**20:.1f} MiB")

# R10: view_shape with integer index arrays
shape = (333, 196, 100)
idx = (np.arange(333)[:, None, None], np.arange(196)[None, :, None], np.arange(100)[None, None, :])
t, r = timed(lambda: view_shape(shape, idx))
print(f"R10 view_shape with three index arrays on {shape}: {t * 1000:.1f} ms -> {r}")

# R13: gzipped FITS decompressed several times by glue's FITS reader
import gzip
import tempfile
from astropy.io import fits
from glue.core.data_factories import load_data
tmp = tempfile.mkdtemp(dir=S)
path = os.path.join(tmp, "big.fits.gz")
fits.writeto(path, np.random.random((3000, 3000)).astype(np.float32))
with open(path, "rb") as f:
    raw = f.read()
t_once, _ = timed(lambda: gzip.decompress(raw))
t_glue, _ = timed(lambda: load_data(path))
print(f"R13 36 MB FITS .gz: one decompression {t_once:.2f} s; glue load_data(auto) {t_glue:.2f} s = {t_glue / t_once:.1f} decompressions")
