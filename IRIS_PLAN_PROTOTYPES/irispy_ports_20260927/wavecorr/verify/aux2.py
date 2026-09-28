import numpy as np
from astropy.io import fits
W='<scratch>/features/wavecorr/'
fs = {'20140708':'~/DATA/IRIS/c7600db2087c0f285587e416a9e55e3d-iris_l2_20140708_114109_3824262996_raster/iris_l2_20140708_114109_3824262996_raster_t000_r00000.fits',
 '20180102':'~/DATA/IRIS/561757a1b84e36def2ed9e2d89103117-iris_l2_20180102_153155_3610108077_raster/iris_l2_20180102_153155_3610108077_raster_t000_r00000.fits',
 '20210429':'~/DATA/IRIS/cf5f0f15e2b13ba82858a26ab2082df3-iris_l2_20210429_110908_3660259102_raster/iris_l2_20210429_110908_3660259102_raster_t000_r00000.fits'}
for k, f in fs.items():
    with fits.open(f, memmap=True, do_not_scale_image_data=True) as h:
        a, ah = h[-2].data, h[-2].header
        vr = a[:, ah['OBS_VRIX']]
        dop = vr/2.99792458e8*2799.474
        nuvwin = [i for i in range(1, h[0].header['NWIN']+1) if h[0].header[f'TWMIN{i}'] <= 2799.474 <= h[0].header[f'TWMAX{i}']][0]
        disp = h[nuvwin].header['CDELT1']
        sum_n = a[:, ah['SUMSPTRN']]
        px = a[:, ah['POFFXNUV']]*disp/np.maximum(sum_n,1)  # guess: pixels maybe unsummed
        px2 = a[:, ah['POFFXNUV']]*0.02546
        s1 = np.polyfit(dop, px2, 1)
        npz = np.load(W + [x for x in ['iris_l2_%s_114109_3824262996_raster_t000_r00000.fits.npz'%k, 'iris_l2_%s_153155_3610108077_raster_t000_r00000.fits.npz'%k,'iris_l2_%s_110908_3660259102_raster_t000_r00000.fits.npz'%k]][['20140708','20180102','20210429'].index(k)])
        c = npz['corrs'][:,0]; ok = np.isfinite(c)
        s2 = np.polyfit(px2[ok], c[ok], 1)
        print(k, 'disp', disp, 'SUMSPTRN', np.unique(sum_n), 'slope POFFXNUV*0.02546 vs OBS_VR*lam/c', s1.round(3), 'std Å', px2.std().round(4), dop.std().round(4),
              '| slope NiI corr vs POFFX Å', s2.round(3), 'r', np.corrcoef(px2[ok], c[ok])[0,1].round(3))
