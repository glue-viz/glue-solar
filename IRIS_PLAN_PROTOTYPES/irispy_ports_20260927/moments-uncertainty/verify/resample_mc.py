"""Does L2-style linear resampling (correlated neighbours) break independent-sample propagation?"""
import numpy as np
rng = np.random.default_rng(1)
PH, RN = 4.0, 3.1
wvl = np.arange(-0.6, 0.6, 0.02596)
def mom(d, s, w):
    I = d.sum(-1); c = (d*w).sum(-1)/I; dl = w-c[:, None]; v = (dl**2*d).sum(-1)/I
    s2 = s**2
    eI = np.sqrt(s2.sum(-1)); ec = np.sqrt((dl**2*s2).sum(-1))/I
    ew = np.sqrt(((dl**2-v[:, None])**2*s2).sum(-1))/I/(2*np.sqrt(v))
    return I, c, np.sqrt(v), eI, ec, ew
for shift in (0.0, 0.25, 0.5):
    fine = np.arange(-0.7, 0.7, 0.02596)
    truth = 50 + 300*np.exp(-0.5*((fine)/0.05)**2)
    raw = rng.poisson(np.broadcast_to(truth*PH, (20000, fine.size)))/PH + rng.normal(0, RN, (20000, fine.size))
    # linear resample onto wvl grid offset by `shift` px
    x = (wvl - fine[0])/0.02596 + shift
    i0 = np.floor(x).astype(int); f = x - i0
    d = raw[:, i0]*(1-f) + raw[:, i0+1]*f
    sig = np.sqrt(np.clip(d*PH, 0, None) + (RN*PH)**2)/PH
    I, c, w, eI, ec, ew = mom(d, sig, wvl)
    print(f"shift {shift:4.2f} px: analytic/MC  I {np.median(eI)/I.std():.3f}  centroid {np.median(ec)/c.std():.3f}  width {np.median(ew)/w.std():.3f}")
