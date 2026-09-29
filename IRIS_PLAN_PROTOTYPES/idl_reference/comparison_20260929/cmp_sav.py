"""Compare IDL and GDL reference .sav outputs variable by variable."""
import sys
from pathlib import Path

import numpy as np
from scipy.io import readsav

IDL = Path("~/Git/irispy/iris_ref_out/iris_ref_out")
GDL = Path("~/Git/glue-solar/IRIS_PLAN_PROTOTYPES/idl_reference/gdl_out_20260927")
SKIP = {"seconds", "file"}  # runtime and path differ by design


def leaves(obj, name=""):
    """Yield (path, ndarray-or-scalar) for every leaf of a readsav result."""
    if isinstance(obj, np.recarray) or (isinstance(obj, np.ndarray) and obj.dtype.names):
        for field in obj.dtype.names:
            col = obj[field]
            if col.dtype == object and col.size == 1:
                col = col[0]
            yield from leaves(col, f"{name}.{field.lower()}")
    elif isinstance(obj, np.ndarray) and obj.dtype == object:
        if obj.size == 1:
            yield from leaves(obj.flat[0], name)
        else:
            for i, o in enumerate(obj.flat):
                yield from leaves(o, f"{name}[{i}]")
    else:
        yield name, obj


def describe(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return f"SHAPE {a.shape} vs {b.shape}"
    if a.dtype.kind in "SUO" or b.dtype.kind in "SUO":
        return "same" if np.array_equal(a, b) else f"DIFF {a.ravel()[:3]} vs {b.ravel()[:3]}"
    a64, b64 = a.astype(float), b.astype(float)
    fa, fb = np.isfinite(a64), np.isfinite(b64)
    nanmis = int((fa != fb).sum())
    both = fa & fb
    d = np.abs(a64[both] - b64[both])
    ndiff = int((d > 0).sum())
    if ndiff == 0 and nanmis == 0:
        return f"identical ({a.size} el, {a.dtype})"
    scale = np.nanmax(np.abs(b64[both])) if both.any() else 0
    msg = f"{ndiff}/{both.sum()} differ, max|d|={d.max():.4g}, med|d|={np.median(d[d > 0]) if ndiff else 0:.3g}, |ref|max={scale:.4g}"
    if nanmis:
        msg += f", NaN-pattern mismatches={nanmis}"
    return msg + f" [{a.dtype}/{b.dtype}]"


def compare(fname):
    print(f"== {fname}")
    ri = readsav(IDL / fname, python_dict=True)
    rg = readsav(GDL / fname, python_dict=True)
    if set(ri) != set(rg):
        print("  variable sets differ:", sorted(ri), sorted(rg))
    for var in sorted(set(ri) & set(rg) - SKIP):
        li, lg = dict(leaves(ri[var], var)), dict(leaves(rg[var], var))
        for key in sorted(set(li) | set(lg)):
            if key not in li or key not in lg:
                print(f"  {key}: only in {'IDL' if key in li else 'GDL'}")
                continue
            print(f"  {key}: {describe(li[key], lg[key])}")
    print("  seconds IDL/GDL:", ri.get("seconds"), rg.get("seconds"))


if __name__ == "__main__":
    for f in sys.argv[1:] or sorted(p.name for p in IDL.glob("*.sav")):
        compare(f)
