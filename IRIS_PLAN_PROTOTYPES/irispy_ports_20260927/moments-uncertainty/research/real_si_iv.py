"""
Real-data prototype: Si IV 1394 (3400109360 scan 0) moments with first-order errors, main vs #179 sigma.
"""

import numpy as np

import astropy.units as u

from irispy.io.utils import read_files
from irispy.utils.constants import DN_UNIT, READOUT_NOISE
from irispy.utils.moments import calculate_moments
from mc_moments import propagate

F = "~/DATA/IRIS/38a343ccd839daf9565522c5aaff5ece-iris_l2_20250328_225628_3400109360_raster/iris_l2_20250328_225628_3400109360_raster_t000_r00000.fits"
REST = 1393.755 * u.AA
WING = 0.4 * u.AA

cube = read_files(F, spectral_windows=["Si IV 1394"], uncertainty=True)["Si IV 1394"][0]
print(cube.shape, type(cube.uncertainty).__name__, "mask frac", cube.mask.mean())
m = calculate_moments(cube, rest_wavelength=REST, wings=WING)
wvl = cube.axis_world_coords(cube.wavelength_axis)[0].to_value(u.AA)
sel = np.abs(wvl - REST.value) <= WING.value
data = np.where(cube.mask, np.nan, cube.data)[..., sel]
sig_main = cube.uncertainty.array[..., sel]  # main: NaN where DN < 0
ph = DN_UNIT["FUV"].to(u.photon)
sig_179 = np.sqrt(np.clip(data * ph, 0, None) + (READOUT_NOISE["FUV"].to_value(DN_UNIT["FUV"]) * ph) ** 2) / ph
print("valid samples < 0:", np.nanmean(data < 0), " main sigma NaN among valid:", np.mean(np.isnan(sig_main[np.isfinite(data)])))
I = m["intensity"].data
bright = I > np.nanpercentile(I, 90)
for name, sig, mode in (("main sigma, nansum", np.where(np.isnan(sig_main), 0, sig_main), "zero"), ("#179, zero", sig_179, "zero"), ("#179, keep", sig_179, "keep")):
    ei, ec, ew = propagate(data, sig, wvl[sel], clipped_sigma=mode)
    ev = ec / REST.value * 299792.458
    print(f"{name:20s} median rel I err (top10%) {np.nanmedian(ei[bright] / I[bright]):.3f}  "
          f"median v err top10% {np.nanmedian(ev[bright]):.2f} km/s  all {np.nanmedian(ev):.2f} km/s  "
          f"median width err top10% {np.nanmedian(ew[bright]) * 1e3:.2f} mA")
