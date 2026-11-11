import sys, warnings; warnings.simplefilter("ignore")
from astropy.io import fits
from astropy.wcs import WCS
import glue
from glue.core.state import _save_wcs, _load_wcs
with fits.open(sys.argv[1]) as hdul: w = WCS(hdul[0].header, hdul)
rec = _save_wcs(w, None)
try:
    _load_wcs(rec, None); print(f"glue {glue.__version__}: -TAB WCS session round trip OK")
except Exception as e:
    print(f"glue {glue.__version__}: -TAB WCS session round trip: {type(e).__name__}: {str(e)[:70]}")
