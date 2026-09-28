import resource, time, numpy as np, mmap
from astropy.io import fits
f='~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits'
with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
    d = h[8].data
    print('window bytes', d.nbytes, 'shape', d.shape, 'page', mmap.PAGESIZE)
    r0 = resource.getrusage(resource.RUSAGE_SELF); t0 = time.time()
    x = np.asarray(d[:, :, 250:270], dtype=float)
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    print('slice bytes', x.size*2, 'minflt', r1.ru_minflt-r0.ru_minflt, 'majflt', r1.ru_majflt-r0.ru_majflt, 'pages*size MB', (r1.ru_minflt-r0.ru_minflt+r1.ru_majflt-r0.ru_majflt)*mmap.PAGESIZE/1e6, 't', round(time.time()-t0,2))
