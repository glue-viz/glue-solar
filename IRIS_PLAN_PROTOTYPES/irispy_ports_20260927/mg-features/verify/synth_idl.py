import sys; sys.path.insert(0,'../mg-features'); sys.path.insert(0,'.')
import numpy as np
import mg_features_proto as P
import run_checks as R
from idl_spline import idl_spline
def idl_refine(vel, spec, p, pp=45):
    nsp = spec.size - 1
    idg = int(np.argmin(np.abs(vel - p[0])))
    lo, hi = max(0, idg - 2), min(idg + 2, nsp)
    nvel = np.arange(pp) / (pp - 1.0) * (vel[lo] - vel[hi]) + vel[hi]
    lo, hi = max(0, idg - 3), min(idg + 3, nsp)
    if hi >= lo + 2:
        ns, _ = idl_spline(vel[lo:hi + 1], spec[lo:hi + 1], nvel, 0.0)
        k = int(np.argmax(ns)); return nvel[k], ns[k]
    return tuple(p)
s, w, p = R.synthetic()
R.score(s, w, p, "noiseless, prototype (order-independent spline eval)")
P._refine = idl_refine
R.score(s, w, p, "noiseless, IDL-faithful decreasing-T eval")
s, w, p = R.synthetic(dispersion_aa=0.05092)
R.score(s, w, p, "summed x2, IDL-faithful")
