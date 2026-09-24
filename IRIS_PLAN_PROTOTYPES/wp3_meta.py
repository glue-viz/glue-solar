import os, warnings, collections
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
import numpy as np, astropy.units as u
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import iris_data
scalars = (str, int, float, bool, type(None))
for f in sorted(str(p) for p in get_test_data_filenames() if str(p).endswith(".fits")):
    try:
        ds = iris_data(f); ds = ds if isinstance(ds, list) else [ds]
    except Exception as e:
        print(f"{os.path.basename(f)[:55]:55s} read_files FAIL {type(e).__name__}: {str(e)[:70]}"); continue
    for d in ds[:1]:
        odd = {k: (type(v).__name__ + (f"{np.shape(v)}" if hasattr(v, "shape") else "") + (f" [{v.unit}]" if isinstance(v, u.Quantity) else "")) for k, v in d.meta.items() if not isinstance(v, scalars)}
        print(f"{os.path.basename(f)[:55]:55s} {type(d.meta).__name__:8s} {len(d.meta):4d} keys  non-scalar: {odd}")
try: print("irispy units resolvable after import irispy:", u.Unit("DN_IRIS_NUV"))
except ValueError as e: print("u.Unit('DN_IRIS_NUV') ->", type(e).__name__, "(irispy does not enable its units globally; only Component.units strings carry them, no Quantity does)")
