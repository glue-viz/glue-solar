import sys, glob, numpy as np
sys.path.insert(0, '<scratch>/features/wavecorr')
import proto_wavecorr as P
from scipy.ndimage import uniform_filter1d
from scipy.optimize import curve_fit

def idl_like(tai, corr, cut):
    corr = corr.copy()
    fin = np.isfinite(corr)
    s = np.sort(corr[fin]); med = s[len(s)//2]  # IDL MEDIAN (no /EVEN)
    out = (corr - med) > cut
    ngood = ~out  # includes NaN, like IDL
    corr[out] = np.nan
    sw = int(np.floor(300.0/np.mean(np.gradient(tai))))
    if sw % 2 == 0: sw += 1
    if sw < ngood.sum() and sw > 1:
        finite = np.isfinite(corr)
        num = uniform_filter1d(np.where(finite, corr, 0.0), sw, mode='nearest')
        den = uniform_filter1d(finite.astype(float), sw, mode='nearest')
        corr = np.where(den > 0, num/np.where(den > 0, den, 1), np.nan)
    remaining_nan_in_good = int((ngood & ~np.isfinite(corr)).sum())
    x = tai - tai[0]
    norbit = min(int(np.floor((tai.max()-tai.min())/5856.)), 3)
    freq = 2*np.pi/5856.
    def model(x, amp, phase, off, *poly):
        y = off + amp*np.sin(freq*x+phase)
        for i, c in enumerate(poly, 1): y = y + c*x**i
        return y
    ok = ngood & np.isfinite(corr)
    popt, _ = curve_fit(model, x[ok], corr[ok], p0=[0.01, 1.0, 0.1]+[0.0]*norbit, maxfev=20000)
    return model(x, *popt), remaining_nan_in_good, int(out.sum()), sw

for f in sorted(glob.glob('<scratch>/features/wavecorr/*.npz')):
    d = np.load(f); tai, c = d['tai'], d['corrs']
    print('==', f.split('/')[-1][8:23], 'n', len(tai))
    for j, name in enumerate(['Ni','Mn','Fe','OI','FeII']):
        cc = c[:, j]; ok = np.isfinite(cc)
        if ok.any(): print(f'  {name}: n={ok.sum()} mean={np.nanmean(cc):+.4f} min={np.nanmin(cc):+.4f} max={np.nanmax(cc):+.4f}')
    for j, cut, lab in ((0, .08, 'NUV'), (3, .05, 'FUV')):
        if np.isfinite(c[:, j]).sum() > 10:
            rp, _ = P.recommended(tai, c[:, j], cut)
            ri, nn, nout, sw = idl_like(tai, c[:, j], cut)
            print(f'  {lab}: proto {rp.min():+.4f}..{rp.max():+.4f}; idl-like {ri.min():+.4f}..{ri.max():+.4f}; max|diff|={np.max(np.abs(rp-ri)):.5f}; outliers={nout}; NaN-left-in-good={nn}; swidth={sw}')
