from astropy.io import fits
f='~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits'
with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
    for x in h[0].header.get('HISTORY', []): print('H:', x)
    for x in h[0].header.get('COMMENT', []): print('C:', x)
    print(repr(h[-2].header)[:4000])
    for i in range(1, h[0].header['NWIN']+1):
        hh = h[i].header
        print(i, h[0].header[f'TDESC{i}'], hh['NAXIS1'], hh['NAXIS2'], hh['NAXIS3'], hh['CRVAL1'], hh['CDELT1'], hh.get('BSCALE'), hh.get('BZERO'))
