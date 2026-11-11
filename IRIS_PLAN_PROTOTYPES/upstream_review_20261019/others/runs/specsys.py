import warnings, astropy
from astropy.io import fits
from astropy.wcs import WCS
warnings.simplefilter("error", category=UserWarning)
h = fits.Header(); h["NAXIS"] = 3
for i, (ct, cu, cv, cd) in enumerate([("HPLN-TAN", "deg", 0, 1e-4), ("HPLT-TAN", "deg", 0, 1e-4), ("WAVE", "nm", 500, 0.01)], 1):
    h[f"CTYPE{i}"] = ct; h[f"CUNIT{i}"] = cu; h[f"CRVAL{i}"] = cv; h[f"CDELT{i}"] = cd; h[f"CRPIX{i}"] = 1
h["OBSGEO-X"] = 5327395.0; h["OBSGEO-Y"] = -1719170.0; h["OBSGEO-Z"] = 3051490.0; h["DATE-OBS"] = "2020-05-01T10:00:00"; h["MJD-OBS"] = 58970.4
try:
    WCS(h).world_axis_object_classes; print(f"astropy {astropy.__version__}: OBSGEO without SPECSYS: OK, no raise, no warning")
except Exception as e:
    print(f"astropy {astropy.__version__}: OBSGEO without SPECSYS: {type(e).__name__}: {str(e)[:90]}")
