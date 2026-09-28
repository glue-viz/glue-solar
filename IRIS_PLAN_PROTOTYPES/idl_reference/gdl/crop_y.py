"""Crop every spectral window of an IRIS L2 raster to slit rows [y0, y1) with memmap slab reads."""
import sys
from astropy.io import fits
src, dst, y0, y1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
with fits.open(src, memmap=True, do_not_scale_image_data=True) as h:
    out = fits.HDUList([fits.PrimaryHDU(header=h[0].header)])
    nwin = h[0].header['NWIN']
    for i in range(1, nwin + 1):
        hdr = h[i].header.copy()
        hdr['CRPIX2'] = hdr['CRPIX2'] - y0
        hdu = fits.ImageHDU(data=h[i].data[:, y0:y1, :].copy(), header=hdr, do_not_scale_image_data=True)
        for k in ('BSCALE', 'BZERO'):  # keep the raw int16 values and their scaling cards
            if k in hdr: hdu.header[k] = hdr[k]
        out.append(hdu)
        p = out[0].header
        p[f'TSR{i}'] = p[f'TSR{i}'] + y0
        p[f'TER{i}'] = p[f'TSR{i}'] + (y1 - y0) - 1
    for k in ('BSCALE', 'BZERO'):  # iris_data::descale_array reads these from the primary header
        if k in h[0].header: out[0].header[k] = h[0].header[k]
    out.append(h[nwin + 1].copy())  # auxiliary per-exposure table
    out.writeto(dst, overwrite=True, output_verify='silentfix')
    # the level 1 filename table has a malformed TFIELDS in real files: copy its raw bytes
    loc = h.fileinfo(nwin + 2)['hdrLoc']
with open(src, 'rb') as f, open(dst, 'ab') as o:
    f.seek(loc)
    o.write(f.read())
