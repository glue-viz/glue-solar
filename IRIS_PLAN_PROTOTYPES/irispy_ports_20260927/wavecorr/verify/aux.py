import numpy as np, glob
from astropy.io import fits
fs = ['~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits',
 '~/DATA/IRIS/561757a1b84e36def2ed9e2d89103117-iris_l2_20180102_153155_3610108077_raster/iris_l2_20180102_153155_3610108077_raster_t000_r00000.fits',
 '~/DATA/IRIS/cf5f0f15e2b13ba82858a26ab2082df3-iris_l2_20210429_110908_3660259102_raster/iris_l2_20210429_110908_3660259102_raster_t000_r00000.fits',
 '~/DATA/IRIS/38a343ccd839daf9565522c5aaff5ece-iris_l2_20250328_225628_3400109360_raster/iris_l2_20250328_225628_3400109360_raster_t000_r00000.fits']
with fits.open(fs[0]) as h:
    print([k for k in h[-2].header if k.endswith(('NUV','FUV')) or 'OFF' in k])
    print(repr(h[-2].header)[4000:6000])
for f in fs:
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        a, ah = h[-2].data, h[-2].header
        vr = a[:, ah['OBS_VRIX']]
        t = a[:, ah['TIME']]
        pz = a[:, ah['PZTX']]
        print('==', f.split('/')[-1][8:40], 'n', len(t), 'dt', np.mean(np.diff(t)).round(2), 'pztx0..2', pz[:3], 'time0..2', t[:3], 'time[-1]', t[-1])
        for k in ('POFFXFUV','POFFXNUV','POFFFFUV','POFFFNUV','POFFYNUV'):
            if k in ah:
                c = a[:, ah[k]]
                ok = np.isfinite(c)
                r = np.corrcoef(c[ok], vr[ok])[0,1] if c[ok].std() > 0 else np.nan
                print(f'  {k}: min {np.nanmin(c):.4f} max {np.nanmax(c):.4f} std {np.nanstd(c):.4f} r(vs OBS_VR)={r:+.3f}')
        print('  OBS_VR km/s', (vr.min()/1e3).round(2), (vr.max()/1e3).round(2))
