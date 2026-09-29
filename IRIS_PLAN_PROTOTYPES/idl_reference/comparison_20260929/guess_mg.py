import sys
import numpy as np
import cmp_mg
import mg_features_proto as P
from irispy.utils import mg_features as M

cube, wave, ref = cmp_mg.load(sys.argv[1])
sub = cube[: int(sys.argv[2])]
orig = M.CubicSpline

def score(label):
    res = M.calculate_mg_features(sub)
    parts = []
    for li, line in enumerate("kh"):
        for feat, key in [("3", "lc"), ("2v", "bp"), ("2r", "rp")]:
            ours = res[f"{line}{feat}_velocity"].data
            idl = ref[key][: len(ours), :, 0, li]
            both = np.isfinite(ours) & np.isfinite(idl)
            d = np.abs(ours - idl)[both]
            parts.append(f"{line}{feat} >1: {(d > 1).mean():.4f}")
    print(f"{label:22s}", " ".join(parts))

score("cubic guess")
M.CubicSpline = lambda x, y, axis=0: (lambda t: np.interp(t, x, y)) if np.ndim(y) == 1 else orig(x, y, axis=axis)
score("linear guess")
M.CubicSpline = lambda x, y, axis=0: (lambda t: P.tension_spline(x, y, t, 1.0)) if np.ndim(y) == 1 else orig(x, y, axis=axis)
score("tension-1 guess (IDL)")
M.CubicSpline = orig
