import sys, subprocess, warnings, numpy as np, astropy
from astropy.io import fits
from astropy.wcs import WCS
warnings.simplefilter("ignore"); print("astropy", astropy.__version__)
path = sys.argv[1]
with fits.open(path) as hdul:
    w = WCS(hdul[0].header, hdul)
(tab,) = w.wcs.tab
print("TAB table: map", list(tab.map), "K", list(tab.K), "M", tab.M, "| axis_correlation_matrix:\n", w.axis_correlation_matrix.astype(int))
# SPECSYS: OBSGEO without SPECSYS on a spectral axis
h = fits.Header(); h["NAXIS"] = 2; h["CTYPE1"] = "WAVE"; h["CUNIT1"] = "nm"; h["CRVAL1"] = 500; h["CDELT1"] = 0.01; h["CRPIX1"] = 1
h["CTYPE2"] = "HPLT-TAN"; h["CUNIT2"] = "deg"; h["CDELT2"] = 1e-4; h["CRPIX2"] = 1; h["CRVAL2"] = 0
h["OBSGEO-X"] = 5327395.0; h["OBSGEO-Y"] = -1719170.0; h["OBSGEO-Z"] = 3051490.0; h["DATE-OBS"] = "2020-05-01T10:00:00"; h["MJD-OBS"] = 58970.4
try:
    WCS(h).world_axis_object_classes; print("empty SPECSYS with OBSGEO: OK (no raise)")
except Exception as e:
    print("empty SPECSYS with OBSGEO:", type(e).__name__, str(e)[:80])
# celestial sub of a WCS with a -TAB axis, in a subprocess (wcslib may crash)
code = f"""
import warnings; warnings.simplefilter('ignore')
from astropy.io import fits
from astropy.wcs import WCS
with fits.open({path!r}) as hdul: w = WCS(hdul[0].header, hdul)
print('sub celestial ok', w.celestial.naxis, '| sub dropping a TAB axis ok', w.sub([1, 3]).naxis)
"""
r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
print("celestial/sub of -TAB WCS: exit", r.returncode, r.stdout.strip()[:100], r.stderr.strip()[-120:])
