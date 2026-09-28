import sys, glob, numpy as np
sys.path.insert(0, '<scratch>/features/wavecorr')
import proto_wavecorr as P
for pat in ['*4000005156_raster/*r00000.fits', '*4000255147_raster/*r00000.fits', '*3602506433_raster/*r00000.fits', '*3400109360_raster/*r00000.fits', '*3893012099_raster/*r00000.fits']:
    f = glob.glob('~/DATA/IRIS/' + pat)[0]
    t, vr, c = P.measure(f)
    n = c.shape[0]
    print(f.split('/')[-1][8:34], 'nexp', n, ' '.join(f'{nm}:{np.isfinite(c[:,j]).sum()}/{n} med={np.nanmedian(c[:,j]) if np.isfinite(c[:,j]).any() else np.nan:+.4f} sd={np.nanstd(c[:,j]) if np.isfinite(c[:,j]).any() else np.nan:.4f}' for j,nm in enumerate(['Ni','Mn','Fe','OI','FeII'])))
