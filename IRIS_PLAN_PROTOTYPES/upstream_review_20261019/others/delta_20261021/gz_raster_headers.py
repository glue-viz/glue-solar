"""#345/#352: the bytes astropy inflates to read a gzipped multi-window file's headers, then its data.

A raster-like file (primary + 8 int16 windows of 8x548x400). glue-solar's old order: `_window_scaling` reads every
window header through a plain fits.open, then irispy's read opens it again in memory; #345 opens it once in memory.

Run: python -I gz_raster_headers.py WORKDIR
"""

import gzip
import io
import sys
from pathlib import Path

import numpy as np

import astropy
from astropy.io import fits

work = Path(sys.argv[1])
path = work / "raster.fits.gz"
NWIN, shape = 8, (8, 548, 400)
if not path.exists():
    rng = np.random.default_rng(0)
    primary = fits.PrimaryHDU()
    primary.header["NWIN"] = NWIN
    hdus = [primary] + [fits.ImageHDU(rng.integers(-200, 4000, shape, dtype=np.int16)) for _ in range(NWIN)]
    raw = io.BytesIO()
    fits.HDUList(hdus).writeto(raw)
    path.write_bytes(gzip.compress(raw.getvalue(), 1))
inflated_size = NWIN * np.prod(shape) * 2

counted = [0, 0]  # bytes inflated, rewinds
read, rewind = gzip._GzipReader.read, gzip._GzipReader._rewind


def counting_read(self, size=-1):
    data = read(self, size)
    counted[0] += len(data)
    return data


def counting_rewind(self):
    counted[1] += 1
    rewind(self)


gzip._GzipReader.read, gzip._GzipReader._rewind = counting_read, counting_rewind


def report(label, fn):
    counted[:] = [0, 0]
    fn()
    print(f"{label}: {counted[0] / inflated_size:.2f}x the data inflated, {counted[1]} rewinds")


def headers(hdulist):
    return [hdulist[i].header.get("BZERO") for i in range(1, hdulist[0].header["NWIN"] + 1)]


def plain_headers():
    with fits.open(path) as hdulist:
        headers(hdulist)


def in_memory_all():
    with fits.open(path, decompress_in_memory=True, do_not_scale_image_data=True) as hdulist:
        headers(hdulist)
        for i in range(1, NWIN + 1):
            hdulist[i].data.sum()


print("astropy", astropy.__version__)
report("before #345: window headers through a plain fits.open, then irispy's in-memory read",
       lambda: (plain_headers(), in_memory_all()))
report("#345: one in-memory open for the headers and irispy's read", in_memory_all)
