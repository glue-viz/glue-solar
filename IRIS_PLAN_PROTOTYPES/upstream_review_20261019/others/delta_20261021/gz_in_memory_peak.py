"""D95: astropy copies an HDU's data out of a decompress_in_memory BytesIO (io/fits/util.py _array_from_file).

Peak traced memory of fits.open(gz, decompress_in_memory=True, memmap=True, do_not_scale_image_data=True)[0].data,
as irispy's lazy read opens a .fits.gz, in units of the inflated file; then with _array_from_file viewing the buffer.

Run: python -I gz_in_memory_peak.py WORKDIR
"""

import gzip
import io
import sys
import tracemalloc
from pathlib import Path

import numpy as np

import astropy
from astropy.io import fits
from astropy.io.fits import file as fits_file

work = Path(sys.argv[1])
path = work / "cube.fits.gz"
if not path.exists():
    data = np.random.default_rng(0).integers(-200, 4000, (100, 400, 400), dtype=np.int16)  # 32 MB
    hdu = fits.PrimaryHDU(data)
    hdu.header["BSCALE"], hdu.header["BZERO"] = 0.25, 7992
    raw = io.BytesIO()
    hdu.writeto(raw)
    path.write_bytes(gzip.compress(raw.getvalue(), 1))
size = 100 * 400 * 400 * 2


def peak(**kwargs):
    tracemalloc.start()
    with fits.open(path, decompress_in_memory=True, do_not_scale_image_data=True, **kwargs) as hdulist:
        values = hdulist[0].data
        total = int(values.sum(dtype=np.int64))
    used = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return used / size, total, values.flags.writeable


print("astropy", astropy.__version__)
print("as is: peak %.2fx inflated size, sum %d, writeable %s" % peak(memmap=True))


def viewing(infile, dtype, count):  # the candidate fix: a read-only view of the in-memory buffer (getvalue shares it, no copy)
    if isinstance(infile, io.BytesIO):
        start = infile.tell()
        array = np.frombuffer(infile.getvalue(), dtype=dtype, count=count, offset=start)
        infile.seek(start + array.nbytes)
        return array
    return original(infile, dtype, count)


original, fits_file._array_from_file = fits_file._array_from_file, viewing
print("viewing: peak %.2fx inflated size, sum %d, writeable %s" % peak(memmap=True))
