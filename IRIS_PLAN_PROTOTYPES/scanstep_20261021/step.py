"""
step.py CUBE VARIANT STATE [WAIT]: an SST quicklook's scan steps to idle, as sst_perf_survey.py's quicklook part times
them (point click and drag first), with the slit panel's own buffer and draw times, disk reads, faults and memory.

VARIANT  today: glue-solar main as it is.
         pread: the cube's fancy reads (every Image panel's buffer) by os.pread of each row's span, not the map.
         hints: sst_hints.py, the proposed change: MADV_WILLNEED on every page a read of the map will touch, first.
         prefetch: on a scan step, a worker thread reads the next and previous scans' slit column from the map.
         prefetch+band: the worker first asks for their whole band (every tuning of the shown Stokes), 128 KB a call.
         prefetch+fband: the same, by os.posix_fadvise on a file descriptor, which releases the GIL (mmap.madvise
         holds it while the kernel queues the reads, about 70 ms a cold band, and the GUI thread waits).
         readahead: on a scan step, that band request on the GUI thread, no worker.
         Joined with '+': pread+hints, prefetch+band+hints.
STATE    cold: the file evicted from the page cache before the quicklook opens; warm: as left by the last run.
WAIT     ms between a step's idle and the next step (default 300), or 'done': until the prefetch has finished too.
Each step's line goes to results/step_CUBE.jsonl; a second pass over the scans (all mapped by then) is 'repeat'.
"""

import mmap
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, "/home/nabil/Git/glue-solar/IRIS_PLAN_PROTOTYPES/scale_checks")
import sst_perf_survey as survey  # noqa: E402
from astropy.io import fits  # noqa: E402
from common import CUBES, LOAD_LIMIT, Meter, emit, evict, memory, quiet  # noqa: E402
from glue.core.component import Component  # noqa: E402
from glue.core.data import Data  # noqa: E402
from glue.viewers.image.pixel_selection_subset_state import PixelSubsetState  # noqa: E402
from glue_qt.app import GlueApplication  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

import glue_solar  # noqa: E402
import sst_hints  # noqa: E402
from glue_solar.quicklook import coordinator, quicklook  # noqa: E402
from glue_solar.sources.sst import _Cube, sst_data  # noqa: E402

key, variant, state = sys.argv[1:4]
wait = sys.argv[4] if len(sys.argv) > 4 else "300"
path = CUBES[key]
OUT = f"results/step_{key}.jsonl"
run = f"{variant} {state} wait={wait}"
PAGE = mmap.PAGESIZE
with fits.open(path, memmap=True) as h:
    DATLOC = h[0].fileinfo()["datLoc"]
FD = os.open(path, os.O_RDONLY)


def _pointer(array):
    return array.__array_interface__["data"][0]


def file_offsets(array, view):
    """The file offset of each value of ``array[view]``, ``array`` a view of the file's memory-mapped HDU data."""
    root = array
    while isinstance(root.base, np.ndarray):
        root = root.base
    offs = DATLOC + _pointer(array) - _pointer(root)
    for index, stride in zip(np.broadcast_arrays(*view), array.strides):
        offs = offs + index.astype(np.int64) * stride
    return offs


def _fancy(self, cid, view):
    comp = self._components.get(cid)
    if type(comp) is Component and isinstance(view, tuple) and len(view) == self.ndim:
        if all(isinstance(v, np.ndarray) and v.dtype.kind == "i" for v in view):
            return comp.data
    return None


def pread_take(array, view):
    """``array[view]`` by os.pread: one read per run of values less than a page apart."""
    offs = file_offsets(array, view)
    u, inverse = np.unique(offs, return_inverse=True)
    cut = np.flatnonzero(np.diff(u) >= PAGE) + 1
    values = np.empty(len(u), array.dtype)
    for a, b in zip(np.r_[0, cut].tolist(), np.r_[cut, len(u)].tolist()):
        lo = int(u[a])
        buf = os.pread(FD, int(u[b - 1]) - lo + array.itemsize, lo)
        values[a:b] = np.frombuffer(buf, array.dtype)[(u[a:b] - lo) // array.itemsize]
    return values[inverse].reshape(offs.shape)


original_get_data = _Cube.get_data
checked = [0]


def get_data(self, cid, view=None):
    if "hints" in variant:
        sst_hints.hint_view(self, cid, view)
    array = _fancy(self, cid, view)
    if array is None:
        return original_get_data(self, cid, view=view)
    if "pread" in variant:
        result = pread_take(array, view)
        if checked[0] < 50:  # the first reads checked against the map's
            checked[0] += 1
            assert np.array_equal(result, array[view], equal_nan=True)
        return result
    return original_get_data(self, cid, view=view)


_Cube.get_data = get_data
original_statistic = _Cube.compute_statistic
stat_ms = [0.0]


def compute_statistic(self, statistic, cid, subset_state=None, **kwargs):
    t = time.perf_counter()
    if "hints" in variant:
        sst_hints.hint_subset(self, cid, subset_state)
    try:
        return original_statistic(self, statistic, cid, subset_state=subset_state, **kwargs)
    finally:
        stat_ms[0] += (time.perf_counter() - t) * 1e3


_Cube.compute_statistic = compute_statistic

survey.QApplication, survey.PixelSubsetState, survey.PART = QApplication, PixelSubsetState, "step"
glue_solar.setup()
survey.answer_dialogs()
app = GlueApplication()
app.resize(1600, 1000)
app.show()
qt = QApplication.instance()
quiet()
if state == "cold":
    evict(path)
cube = sst_data(path)
coord = coordinator(app.data_collection)
views = {}
with Meter() as opened:
    views.update(quicklook(app, [cube]))
    survey.to_idle(app, coord, time.perf_counter())
# the survey's point click and drag, then the panels' resize timers (mpl-scatter-density draws no new image for 0.5 s
# after a resize)
group = next(g for g in coord._owners if g.subset_state.reference_data is cube)
*_, rows, columns = cube.shape
y, x = rows // 3, columns // 3
for i in range(11):
    group.subset_state = survey.point(cube, y + 2 * i, x + 3 * i)
    survey.to_idle(app, coord, time.perf_counter())
start = time.perf_counter()
while time.perf_counter() - start < 1.0:
    qt.processEvents()
    time.sleep(0.005)
survey.to_idle(app, coord, time.perf_counter())
assert not any(image._pressed for tab in app.viewers for v in tab for image in v.axes.images)

# each panel's buffer times and the slit's draw times, per step
panel_of = {getattr(layer.state, "uuid", None): name for name, viewer in views.items() if hasattr(viewer, "layers") for layer in viewer.layers}
frb_ms, draw_ms = {}, {}
original_frb = Data.compute_fixed_resolution_buffer


def frb(self, bounds, **kwargs):
    t = time.perf_counter()
    result = original_frb(self, bounds, **kwargs)
    name = panel_of.get(kwargs.get("cache_id"), "other")
    frb_ms[name] = frb_ms.get(name, 0) + (time.perf_counter() - t) * 1e3
    return result


Data.compute_fixed_resolution_buffer = frb
slit_canvas = views["slit"].figure.canvas


def slit_draw(*a, _original=slit_canvas.draw, **k):
    t = time.perf_counter()
    result = _original(*a, **k)
    draw_ms["slit"] = draw_ms.get("slit", 0) + (time.perf_counter() - t) * 1e3
    return result


slit_canvas.draw = slit_draw

# the prefetch: the slit column of the next and previous scans, from the map, on one worker
array = cube.get_component(cube.main_components[0]).data
worker = ThreadPoolExecutor(max_workers=1)
futures, fetched, prefetch_ms = [], {}, {}


def touch(scan, stokes, x):
    t = time.perf_counter()
    column = array[scan, stokes, :, :, x] if stokes is not None else array[scan, :, :, x]
    if "fband" in variant:  # the band by posix_fadvise, 128 KB a call, the GIL released in each
        values, _, length = band(scan, stokes)
        root = values
        while isinstance(root.base, np.ndarray):
            root = root.base
        offset = DATLOC + _pointer(values) - _pointer(root)
        for chunk in range(offset, offset + length, 128 << 10):
            os.posix_fadvise(FD, chunk, min(128 << 10, offset + length - chunk), os.POSIX_FADV_WILLNEED)
    elif "band" in variant:  # the band, the kernel reading it in parallel, then the column
        sst_hints._will_need(*band(scan, stokes))
    np.array(column)  # reads every page of the column, so the panel's reads find it mapped
    prefetch_ms.setdefault(scan, (time.perf_counter() - t) * 1e3)  # the first, cold, one
    fetched[scan] = time.perf_counter()


def band(scan, stokes):
    """Scan ``scan``'s band of the shown Stokes parameter, every tuning plane, as `sst_hints._will_need`'s arguments."""
    values = array[scan, stokes] if stokes is not None else array[scan]
    return values, [0], values.nbytes


def on_slices(slices):
    scan = slices[0]
    stokes = slices[1] if cube.ndim == 5 else None
    for future in futures:
        future.cancel()  # not started: the user stepped on
    futures.clear()
    for other in (scan + 1, scan - 1):
        if 0 <= other < cube.shape[0]:
            if "prefetch" in variant:
                futures.append(worker.submit(touch, other, stokes, slices[-1]))
            if variant == "readahead":
                t = time.perf_counter()
                sst_hints._will_need(*band(other, stokes))
                prefetch_ms.setdefault(other, (time.perf_counter() - t) * 1e3)  # the GUI thread's wait


if "prefetch" in variant or variant == "readahead":
    views["slit"].state.add_callback("slices", on_slices)


def step(index, label):
    slices = list(views["map"].state.slices)
    slices[0] = index
    frb_ms.clear(), draw_ms.clear()
    stat_ms[0] = 0.0
    ready = index in fetched
    with Meter() as m:
        t = time.perf_counter()
        views["map"].state.slices = tuple(slices)
        idle = survey.to_idle(app, coord, t)
    lines.append(dict(run=run, cube=key, pass_=label, scan=index, step_ms=round(idle * 1e3, 1),
         slit_frb_ms=round(frb_ms.get("slit", 0), 2), slit_draw_ms=round(draw_ms.get("slit", 0), 2), stat_ms=round(stat_ms[0], 1),
         frb_ms={k: round(v, 1) for k, v in frb_ms.items()}, prefetched=ready, prefetch_ms=prefetch_ms.get(index),
         read_mb=round(m.read_mb, 1), majflt=m.majflt, minflt=m.minflt, rss_gb=round(memory()[0] / 1e9, 2),
         anon_gb=round(memory()[1] / 1e9, 3)))
    if wait == "done":
        for future in list(futures):
            future.result()
        survey.to_idle(app, coord, time.perf_counter())
    else:
        end = time.perf_counter() + float(wait) / 1e3
        while time.perf_counter() < end:
            qt.processEvents()
            time.sleep(0.002)
    return idle


lines = []
order = list(range(1, cube.shape[0])) + [0]
summary = {}
for label in ("first", "repeat"):
    steps = []
    for index in order:
        steps.append(step(index, label))
        lines[-1]["load"] = [round(v, 2) for v in os.getloadavg()]
    summary[label] = round(statistics.median(steps) * 1e3, 1)
worker.shutdown(wait=True)
# a cold run with a step under a load average of 8 or more is set aside, and run_steps.sh runs it again
loaded = state == "cold" and max(line["load"][0] for line in lines) >= LOAD_LIMIT
if loaded:
    OUT = f"results/loaded_{key}.jsonl"
for line in lines:
    emit(OUT, **{k: v for k, v in line.items() if k != "load"}, step_load=line["load"])
emit(OUT, run=run, cube=key, summary=summary, open=opened.dict(), checked_reads=checked[0],
     prefetch_ms_all=sorted(round(v, 1) for v in prefetch_ms.values()),
     memory_gb=round(memory()[0] / 1e9, 2), anon_gb=round(memory()[1] / 1e9, 3))
sys.exit(3 if loaded else 0)
