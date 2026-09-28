import glob, os
from astropy.io import fits
fs = sorted(glob.glob("~/DATA/IRIS/**/*raster*_r00000.fits", recursive=True))
for f in fs:
    h = fits.getheader(f, 0)
    wins = [(h[f"TDESC{i}"], round(h[f"TWMIN{i}"],1), round(h[f"TWMAX{i}"],1)) for i in range(1, h["NWIN"]+1)]
    w1403 = [w for w in wins if w[1] <= 1402.77 <= w[2]]
    nfiles = len(glob.glob(os.path.join(os.path.dirname(f), "*_r*.fits")))
    print(h["OBSID"], h["DATE_OBS"][:19], "SUMSPAT", h["SUMSPAT"], "SUMSPTRF", h["SUMSPTRF"], "STEPS_AV", round(h["STEPS_AV"],3), "NRASTERP", h["NRASTERP"], "files", nfiles, "1402.77 in:", w1403, "SAT_ROT", round(h["SAT_ROT"],1))
for f in sorted(glob.glob("~/DATA/IRIS/**/*SJI_1400*", recursive=True)):
    h = fits.getheader(f, 0); print("SJI", os.path.basename(f), h.get("NAXIS1"), h.get("NAXIS2"), h.get("NAXIS3"), h.get("SUMSPAT"))
