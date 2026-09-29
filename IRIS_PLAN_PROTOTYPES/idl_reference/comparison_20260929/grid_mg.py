import numpy as np
import mg_features_proto as P
from irispy.utils import mg_features as M
from guess_mg import score, orig

def end_slopes(x, y):
    h1, h2, h12 = x[1] - x[0], x[2] - x[1], x[2] - x[0]
    s1 = -(h12 + h1) / h12 / h1 * y[..., 0] + h12 / h1 / h2 * y[..., 1] - h1 / h12 / h2 * y[..., 2]
    hn, hm, hnn = x[-1] - x[-2], x[-2] - x[-3], x[-1] - x[-3]
    sn = hn / hnn / hm * y[..., -3] - hnn / hn / hm * y[..., -2] + (hnn + hn) / hnn / hn * y[..., -1]
    return s1, sn

def patched(x, y, axis=0):
    if np.ndim(y) == 1:
        return lambda t: P.tension_spline(x, y, t, 1.0)
    s1, sn = end_slopes(x, y)
    return orig(x, y, axis=axis, bc_type=((1, s1), (1, sn)))

M.CubicSpline = patched
score("tension guess + clamped grid")
