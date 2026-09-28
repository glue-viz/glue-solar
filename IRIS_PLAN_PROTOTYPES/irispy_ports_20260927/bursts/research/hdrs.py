import glob, os
from astropy.io import fits
files = sorted(glob.glob("~/DATA/IRIS/*_raster/*_r00000.fits")) + sorted(glob.glob("~/DATA/IRIS/*SJI_1400*.fits*"))
for f in files:
    h = fits.getheader(f, 0)
    nwin = h.get("NWIN", 0)
    wins = [h.get(f"TDESC{i}") for i in range(1, nwin+1)]
    nraster = len(glob.glob(os.path.join(os.path.dirname(f), "*_r*.fits")))
    print(os.path.basename(f)[:60], h.get("OBSID"), h.get("DATE_OBS"), "SUMSPAT", h.get("SUMSPAT"), "SUMSPTRF", h.get("SUMSPTRF"), "STEPS", h.get("NRASTERP"), "STEPSS", h.get("STEPSS"), "EXPTIME", h.get("EXPTIME"), "files", nraster)
    print("   ", h.get("OBS_DESC"), "|", [w for w in wins if w and ("Si" in w or "1403" in w or "FUV" in w)], "| SAT_ROT", h.get("SAT_ROT"), "| XCEN", h.get("XCEN"), h.get("YCEN"))
    if "SJI" in f:
        h1 = fits.getheader(f,0); print("    SJI NAXIS", h1.get("NAXIS1"), h1.get("NAXIS2"), h1.get("NAXIS3"), "BUNIT", h1.get("BUNIT"), "CDELT1", h1.get("CDELT1"))
