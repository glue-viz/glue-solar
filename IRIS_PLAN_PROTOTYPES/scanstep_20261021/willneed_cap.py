"""willneed_cap.py: does one POSIX_FADV_WILLNEED of a scan's 524 MB band read it all, or only the readahead window?"""
import os, sys, time
from common import CUBES, evict, io
path = CUBES["2022"]
start, length = 51840 + 5 * 524826176, 524826176  # scan 5's band
fd = os.open(path, os.O_RDONLY)
for chunk in (length, 2 << 20, 128 << 10):
    evict(path)
    before = io()[0]
    t = time.perf_counter()
    for offset in range(start, start + length, chunk):
        os.posix_fadvise(fd, offset, min(chunk, start + length - offset), os.POSIX_FADV_WILLNEED)
    call = (time.perf_counter() - t) * 1e3
    time.sleep(1.5)
    print(f"chunk {chunk >> 10} KB: calls {call:.1f} ms, read {(io()[0] - before) / 1e6:.0f} MB of {length / 1e6:.0f}", os.getloadavg())
