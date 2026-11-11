"""The reproducer's report on real IRIS rasters, through the WCS irispy builds."""
import sys, types, warnings
import numpy as np
sys.path.insert(0, sys.argv[1])
import tab_inverse_repro as r
import irispy
from astropy.io import fits
from astropy.wcs import WCS
from irispy.io.spectrograph import read_spectrograph_lvl2, _create_tabular_wcs
warnings.simplefilter("ignore")
print("irispy", irispy.__version__)
rng = np.random.default_rng(0)
for spec in sys.argv[2:]:
    f, n, grid, rows = spec.split(",")
    rc = read_spectrograph_lvl2(f, memmap=True)
    key = next((k for k in rc.keys() if "1403" in k), list(rc.keys())[0])
    w = rc[key][0].wcs
    w = getattr(w, "low_level_wcs", w)
    assert isinstance(w, WCS), type(w)
    name = f.split("/")[-1][8:34] + f" [{key}]"
    print("\n", name, "ctype", list(w.wcs.ctype), "K", list(w.wcs.tab[0].K), "pixel_shape", w.pixel_shape)
    r.report(name, w, int(n), rng, int(grid))
    if int(rows):
        # The first `rows` exposures only, through irispy's own builder, to compare with the synthetic 1600.
        with fits.open(f, memmap=True) as h:
            aux = types.SimpleNamespace(data=h[-2].data[: int(rows)], header=h[-2].header)
            win = h[1].header.copy(); win["NAXIS3"] = int(rows)
            w2 = _create_tabular_wcs(win, aux, date_obs=h[0].header["DATE_OBS"])
        r.report(name + f" first {rows} exposures", w2, int(n), rng, int(grid))
