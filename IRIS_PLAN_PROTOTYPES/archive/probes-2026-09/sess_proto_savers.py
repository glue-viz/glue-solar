"""Prototype: one __gluestate__ pair for glue_solar's _GlueWCS covering gwcs (asdf), astropy -TAB (Tabprm rebuild), Sliced and Compound wrappers."""
import io, base64, warnings; warnings.simplefilter("ignore")
import numpy as np, asdf, gwcs
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcsapi.wrappers import SlicedLowLevelWCS
from ndcube.wcs.wrappers import CompoundLowLevelWCS
from glue.core.state import saver, loader, GlueSerializeError
from glue_solar.sources.loaders.iris import _GlueWCS

def tab_to_bytes(w):
    # astropy exposes the -TAB coordinate array (Tabprm.coord) but not the index vectors;
    # irispy's index vectors are the linear intermediate coords at pixel 1..NAXIS (K samples).
    hdr = fits.Header.fromstring(w.wcs.to_header(relax=True))
    t = w.wcs.tab[0]
    cols = {hdr["PS2_1"]: np.ascontiguousarray(t.coord)}
    for ax in (2, 3):
        p = np.array([1, w.pixel_shape[ax - 1]], dtype=float)
        psi = w.wcs.crval[ax - 1] + w.wcs.cdelt[ax - 1] * (p - w.wcs.crpix[ax - 1])
        cols[hdr[f"PS{ax}_2"]] = np.linspace(psi[0], psi[1], t.K[ax - 2])
    dtype = [(k, float, v.shape) for k, v in cols.items()]
    rec = np.array([tuple(cols[k] for k, *_ in dtype)], dtype=dtype)
    hl = fits.HDUList([fits.PrimaryHDU(header=hdr), fits.BinTableHDU(rec, name=hdr["PS2_0"])])
    b = io.BytesIO(); hl.writeto(b); return b.getvalue()

def tab_from_bytes(b):
    hl = fits.open(io.BytesIO(b)); return WCS(hl[0].header, hl)

def to_rec(lw):
    if isinstance(lw, gwcs.WCS):
        b = io.BytesIO(); asdf.AsdfFile({"wcs": lw}).write_to(b)
        return {"kind": "asdf", "b64": base64.b64encode(b.getvalue()).decode()}
    if isinstance(lw, WCS):
        if any("-TAB" in c for c in lw.wcs.ctype):
            return {"kind": "fits-tab", "b64": base64.b64encode(tab_to_bytes(lw)).decode()}
        return {"kind": "fits", "header": lw.to_header_string()}
    if isinstance(lw, SlicedLowLevelWCS):
        return {"kind": "sliced", "wcs": to_rec(lw._wcs), "slices": [s if isinstance(s, int) else [s.start, s.stop, s.step] for s in lw._slices_pixel]}
    if isinstance(lw, CompoundLowLevelWCS):
        return {"kind": "compound", "parts": [to_rec(p) for p in lw._wcs], "mapping": list(map(int, lw.mapping.mapping))}
    raise GlueSerializeError(f"no WCS saver for {type(lw)}")

def from_rec(r):
    k = r["kind"]
    if k == "asdf":
        with asdf.open(io.BytesIO(base64.b64decode(r["b64"])), lazy_load=False, memmap=False) as af: return af["wcs"]
    if k == "fits-tab": return tab_from_bytes(base64.b64decode(r["b64"]))
    if k == "fits": return WCS(fits.Header.fromstring(r["header"]))
    if k == "sliced": return SlicedLowLevelWCS(from_rec(r["wcs"]), [s if isinstance(s, int) else slice(*s) for s in r["slices"]])
    if k == "compound": return CompoundLowLevelWCS(*[from_rec(p) for p in r["parts"]], mapping=r["mapping"])

@saver(_GlueWCS)
def _save_gluewcs(obj, context): return {"wcs": to_rec(obj._wcs)}
@loader(_GlueWCS)
def _load_gluewcs(rec, context): return _GlueWCS(from_rec(rec["wcs"]))
