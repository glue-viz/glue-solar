"""Shrink an ITN32 SOT cube: spatial stride, keep every frame; aux rows unchanged. Drops the A0 filename table."""
import sys
from pathlib import Path
from astropy.io import fits

STRIDE = 8
for name in sys.argv[1:]:
    src = Path(name)
    with fits.open(src) as hl:
        h = hl[0].header.copy()
        data = hl[0].data[:, ::STRIDE, ::STRIDE]
        for axis in (1, 2):
            h[f"CDELT{axis}"] *= STRIDE
            h[f"CRPIX{axis}"] = (h[f"CRPIX{axis}"] - 1) / STRIDE + 1
        out = fits.HDUList([fits.PrimaryHDU(data, h), fits.ImageHDU(hl[1].data, hl[1].header)])
        out.writeto(src.with_name(src.name.replace(".fits", "_test.fits")), overwrite=True)
