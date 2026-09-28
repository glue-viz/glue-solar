import warnings
warnings.simplefilter("ignore")
import numpy as np
from astropy.io import fits
from irispy.io.sji import read_sji_lvl2
B = "<scratch>/features/itn32-sot/small/x/"
for f in [B + "sot_l2_20150830_070953_3603259402_20150830100400_Gband4305_FG.fits", "irispy/data/test/raster/iris_l2_20230408_110821_3880012095_SJI_1400_t000_test.fits"]:
    c = read_sji_lvl2(f)
    with fits.open(f) as hl:
        h = hl[0].header; a = np.atleast_2d(hl[1].data); ah = hl[1].header
        k = 0
        x0, y0 = a[k, ah["XCENIX"]], a[k, ah["YCENIX"]]
        for off in (1, 0):
            w = c.wcs.pixel_to_world(h["CRPIX1"] - off, h["CRPIX2"] - off, k)[0]
            print(f.split("/")[-1][:40], f"pix=CRPIX-{off}", "dTx", round(w.Tx.arcsec - x0, 4), "dTy", round(w.Ty.arcsec - y0, 4), "CDELT", h["CDELT1"])
