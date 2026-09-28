import sys, glob, warnings
import numpy as np
from astropy.io import fits
warnings.simplefilter("ignore")
base = "../itn32-sot/"
files = sorted(glob.glob(base+"small/x/*.fits")) + sorted(glob.glob(base+"sotsp/*.fits"))[:2]
keys = ["TELESCOP","INSTRUME","TDET1","NWIN","TDESC1","TWAVE1","BTYPE","BUNIT","BSCALE","BITPIX","NAXIS","NAXIS1","NAXIS2","NAXIS3","DSUN_OBS","RSUN_OBS","CTYPE1","CTYPE2","CTYPE3","CDELT1","CDELT2","CDELT3","CRPIX1","CRPIX2","CRPIX3","CRVAL3","OBSID","DATE_OBS","DATE_END","STARTOBS","ENDOBS","OBS_DESC","CADEX_AV","DATA_LEV","OBS_VR","EXPTIME","SAT_ROT","NBFRAMES","TWMIN1","TWMAX1","XCEN","YCEN","FOVX","FOVY","CUNIT3","SOTSTART","SOTSEND"]
for f in files:
    with fits.open(f) as hl:
        h = hl[0].header
        print("==", f.split("/")[-1], [ (x.name, x.header.get("NAXIS1"), x.header.get("NAXIS2")) for x in hl])
        print({k: h.get(k) for k in keys})
        a = hl[1]
        print("aux shape", a.data.shape, "TIME col", a.header.get("TIME"), "time vals", np.atleast_2d(a.data)[:3, a.header["TIME"]], "XCENIX", np.atleast_2d(a.data)[0, a.header["XCENIX"]])
        if len(hl) > 2:
            print("hdu2 TFORMs", [hl[2].header.get(f"TFORM{i}") for i in range(1, 4)])
