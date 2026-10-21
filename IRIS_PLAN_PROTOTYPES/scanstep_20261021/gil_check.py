"""
gil_check.py: does a worker's WILLNEED on a cold 393 MB scan band (2024 cube) stall the main thread? The main thread
spins in 1 ms Python steps while the worker asks by mmap.madvise or by os.posix_fadvise (128 KB a call); the longest gap
between its steps is how long it could not run Python.
"""

import mmap
import os
import threading
import time

from common import CUBES, emit, evict, quiet

path = CUBES["2024"]
start, length = 60480 + 7 * 392670720, 392670720  # scan 7's band
fd = os.open(path, os.O_RDONLY)
chunk = 128 << 10

def by_madvise():
    with open(path, "rb") as f:
        m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        first = start // mmap.PAGESIZE * mmap.PAGESIZE
        for offset in range(first, start + length, chunk):
            m.madvise(mmap.MADV_WILLNEED, offset, min(chunk, start + length - offset))
        m.close()

def by_fadvise():
    for offset in range(start, start + length, chunk):
        os.posix_fadvise(fd, offset, min(chunk, start + length - offset), os.POSIX_FADV_WILLNEED)

for name, work in (("mmap.madvise", by_madvise), ("os.posix_fadvise", by_fadvise)) * 2:
    quiet()
    evict(path)
    worker = threading.Thread(target=work)
    gaps, t0 = [], time.perf_counter()
    worker.start()
    last = time.perf_counter()
    while worker.is_alive():
        sum(range(1000))  # a little Python
        now = time.perf_counter()
        gaps.append(now - last)
        last = now
    emit("results/gil_check.jsonl", worker=name, worker_ms=round((time.perf_counter() - t0) * 1e3, 1),
         longest_main_gap_ms=round(max(gaps) * 1e3, 1), main_steps=len(gaps),
         stalled_ms=round(sum(g for g in gaps if g > 0.002) * 1e3, 1))
