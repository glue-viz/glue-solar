"""
reads.py CUBE NSCANS: the virtual slit's read (every tuning at one x, Stokes I, every y or the panel's 88 rows) by each
method, cold (file evicted from the page cache, fresh map), warm (cached, fresh map: first touch) and repeat (same map
again), on NSCANS scans spread over the cube. Lines to results/reads_CUBE.jsonl. Values checked against the memory map.
"""

import mmap
import os
import sys

import numpy as np
from astropy.io import fits

import sst_hints
from common import CUBES, LOAD_LIMIT, Meter, emit, evict, quiet

PAGE = mmap.PAGESIZE
key, nscans = sys.argv[1], int(sys.argv[2])
path = CUBES[key]
with fits.open(path, memmap=True) as h:
    hdr, start = h[0].header, h[0].fileinfo()["datLoc"]
shape = tuple(hdr[f"NAXIS{i}"] for i in range(5, 0, -1))  # scan, Stokes, tuning, y, x
S, P, K, NY, NX = shape
X = NX // 2  # the quicklook's first point
scans = np.unique(np.linspace(1, S - 1, nscans).round().astype(int))
PATTERNS = {"full": np.arange(NY), "panel": np.unique(np.clip(np.round(np.linspace(-0.5, NY - 0.5, 88)), 0, NY - 1)).astype(int)}
OUT = os.environ.get("READS_OUT", f"results/reads_{key}.jsonl")
os.makedirs("results", exist_ok=True)


def offsets(scan, rows):
    """File offset of each (tuning, row) value of the slit, Stokes I."""
    k, y = np.meshgrid(np.arange(K), rows, indexing="ij")
    return start + 4 * ((((scan * P + 0) * K + k) * NY + y) * NX + X)


def memmap():
    return np.memmap(path, dtype=">f4", mode="r", offset=start, shape=shape)


def m_mmap(mm, fd, scan, rows):
    return np.asarray(mm[scan, 0][:, rows, X])  # glue's fancy index of the memory map


def m_pread(mm, fd, scan, rows):
    offs = offsets(scan, rows).ravel().tolist()
    buf = b"".join([os.pread(fd, 4, o) for o in offs])
    return np.frombuffer(buf, ">f4").reshape(K, len(rows))


def m_fromfile(mm, fd, scan, rows):
    with open(path, "rb") as f:
        values = [np.fromfile(f, ">f4", count=1, offset=o - f.tell()) for o in offsets(scan, rows).ravel().tolist()]
    return np.concatenate(values).reshape(K, len(rows))


def m_band(mm, fd, scan, rows):
    """One read per tuning plane of rows min..max, then the column."""
    y0, y1 = rows.min(), rows.max() + 1
    buf = bytearray((y1 - y0) * NX * 4)
    out = np.empty((K, len(rows)), ">f4")
    for k in range(K):
        offset = start + 4 * (((scan * P) * K + k) * NY + y0) * NX
        if hasattr(os, "preadv"):
            os.preadv(fd, [buf], offset)
        else:  # macOS builds without preadv
            buf[:] = os.pread(fd, len(buf), offset)
        out[k] = np.frombuffer(buf, ">f4").reshape(y1 - y0, NX)[rows - y0, X]
    return out


def _willneed_pages(fd, scan, rows):
    """The file's read-ahead hint per page: posix_fadvise WILLNEED on Linux, fcntl F_RDADVISE (a radvisory) on macOS."""
    pages = np.unique(offsets(scan, rows) // PAGE).tolist()
    if sys.platform == "darwin":
        import fcntl
        import struct

        for page in pages:
            fcntl.fcntl(fd, getattr(fcntl, "F_RDADVISE", 44), struct.pack("qixxxx", page * PAGE, PAGE))
        return
    for page in pages:
        os.posix_fadvise(fd, page * PAGE, PAGE, os.POSIX_FADV_WILLNEED)


def m_fadvise_pread(mm, fd, scan, rows):
    """WILLNEED on each page the slit needs (the kernel reads them in parallel), then pread each value."""
    _willneed_pages(fd, scan, rows)
    return m_pread(mm, fd, scan, rows)


def m_fadvise_mmap(mm, fd, scan, rows):
    _willneed_pages(fd, scan, rows)
    return m_mmap(mm, fd, scan, rows)


def m_random(mm, fd, scan, rows):
    mm._mmap.madvise(mmap.MADV_RANDOM)  # no read-around on a fault
    return m_mmap(mm, fd, scan, rows)


def m_random_fadvise(mm, fd, scan, rows):
    mm._mmap.madvise(mmap.MADV_RANDOM)
    _willneed_pages(fd, scan, rows)
    return m_mmap(mm, fd, scan, rows)


def m_sequential(mm, fd, scan, rows):
    mm._mmap.madvise(mmap.MADV_SEQUENTIAL)
    return m_mmap(mm, fd, scan, rows)


def m_band_willneed(mm, fd, scan, rows):
    """WILLNEED on the scan's Stokes I band, every tuning plane whole, in 128 KB calls, then the memory map's read."""
    band = mm[scan, 0]
    sst_hints._will_need(band, [0], band.nbytes)
    return m_mmap(mm, fd, scan, rows)


def m_hints(mm, fd, scan, rows):
    """sst_hints.py's change: MADV_WILLNEED on the map for each page the slit touches, then the map's read."""
    band = mm[scan, 0]
    starts = np.arange(K)[:, None] * band.strides[0] + rows[None, :] * band.strides[1] + X * band.strides[2]
    sst_hints._will_need(band, starts, band.itemsize)
    return m_mmap(mm, fd, scan, rows)


METHODS = {"mmap": m_mmap, "pread": m_pread, "fromfile": m_fromfile, "band": m_band, "fadvise+pread": m_fadvise_pread,
           "fadvise+mmap": m_fadvise_mmap, "MADV_RANDOM": m_random, "MADV_RANDOM+fadvise": m_random_fadvise,
           "MADV_SEQUENTIAL": m_sequential, "band WILLNEED+mmap": m_band_willneed, "hints+mmap": m_hints}
only = sys.argv[3].split(",") if len(sys.argv) > 3 else list(METHODS)
fd = os.open(path, os.O_RDONLY)
emit(OUT, cube=key, shape=shape, x=X, scans=scans.tolist(), page=PAGE,
     read_ahead_kb=open("/sys/block/nvme0n1/queue/read_ahead_kb").read().strip() if sys.platform == "linux" else "n/a",
     platform=sys.platform)
for scan in scans.tolist():
    for pname, rows in PATTERNS.items():
        mm = memmap()
        reference = np.array(mm[scan, 0][:, rows, X])
        del mm
        for name in only:
            if name == "fromfile" and pname == "full" and scan not in scans[:2]:
                continue  # 5 us a value: two scans tell
            for attempt in range(5):  # a cold timing only under a load average of 8, else again
                quiet()
                evict(path)
                mm = memmap()
                with Meter() as cold:
                    got = METHODS[name](mm, fd, scan, rows)
                cold_load = os.getloadavg()[0]
                assert np.array_equal(got, reference, equal_nan=True), (name, pname, scan)
                del mm
                if cold_load < LOAD_LIMIT:
                    break
            mm = memmap()
            with Meter() as warm:
                METHODS[name](mm, fd, scan, rows)
            with Meter() as repeat:
                METHODS[name](mm, fd, scan, rows)
            del mm
            emit(OUT, cube=key, scan=scan, pattern=pname, values=reference.size, method=name, cold=cold.dict(),
                 cold_load=cold_load, attempts=attempt + 1,
                 warm=warm.dict(), repeat=repeat.dict())
os.close(fd)
