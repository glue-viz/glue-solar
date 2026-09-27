import sys, warnings
sys.path.insert(0, "<session-scratch>/tools")
import qs_isolate  # noqa
import numpy as np
warnings.simplefilter("ignore")
from irispy.io import read_files
p = "~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits"
a = read_files(p, spectral_windows=["Si IV 1403"], memmap=False, uncertainty=False)["Si IV 1403"][0]
b = read_files(p, spectral_windows=["Si IV 1403"], memmap=True, uncertainty=False)["Si IV 1403"][0]
i = (5, 300, slice(100, 104))
print("memmap=False", a.data[i], a.unit, "mask any", None if a.mask is None else bool(np.any(a.mask)))
print("memmap=True ", b.data[i], b.unit, "mask", None if b.mask is None else bool(np.any(b.mask)), "raw*0.25+7992 =", b.data[i] * 0.25 + 7992)
print("count of -200 in memmap=False data:", int((a.data == -200).sum()), "NaN:", int(np.isnan(a.data).sum()), " raw fill (-200-7992)/0.25 =", (-200 - 7992) / 0.25, "count", int((b.data == int((-200 - 7992) / 0.25)).sum()))
