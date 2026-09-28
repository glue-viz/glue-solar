import numpy as np, astropy.units as u
from astropy.time import Time
import irispy
from irispy.utils.response import get_latest_response
print("irispy from", irispy.__file__)
ref = get_latest_response(Time("2013-10-22T21:00:00"))
print("version", ref["VERSION"], ref["VERSION_DATE"])
lam = ref["LAMBDA"].to_value(u.nm)
imin = np.argmin(np.abs(lam - 140.277))
print("nearest grid lambda", lam[imin])
a0 = ref["AREA_SG"][0, imin]
for d in ["2013-09-02T16:39:35","2014-07-08T11:41:09","2016-10-22","2018-01-02T15:31:55","2021-04-29T11:09:08","2025-03-28T22:56:28","2026-02-09T21:52:33"]:
    r = get_latest_response(Time(d))
    a = r["AREA_SG"][0, imin]
    print(d, f"area={a:.4f}", f"ratio={(a/a0).value:.4f}", f"threshold={500*(a/a0).value:.1f} DN/s")
