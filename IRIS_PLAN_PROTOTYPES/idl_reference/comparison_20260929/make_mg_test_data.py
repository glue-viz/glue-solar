"""
Build the Mg II features test data for irispy from a local L2 file and the IDL reference run.

Crop: 4000005156 raster r00000, steps STEPS, the whole slit, and the Mg II k 2796 window split
into two windows around k and h (+-46 km/s). IDL references: lc, bp, rp at those steps, and the
SPLINE probe of the reference run.
"""
import glob
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.table import Table
from scipy.io import readsav

from make_wavecorr_test_data import per_window_keys

IDL = Path("~/Git/irispy/iris_ref_out/iris_ref_out")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
RASTER = glob.glob("~/DATA/IRIS/*4000005156_raster/*r00000.fits")[0]
STEPS = [13, 32, 57]
C_KMS = 299792.458
LINES = {"Mg II k 2796": 2796.3509493, "Mg II h 2803": 2803.5297192}


def crop():
    with fits.open(RASTER, do_not_scale_image_data=True) as hdus:
        table = hdus[-1].header
        table["TFIELDS"] = sum(1 for key in table if key.startswith("TTYPE"))
        hdus.verify("fix")
        primary = hdus[0].header
        names = [primary[f"TDESC{i}"] for i in range(1, primary["NWIN"] + 1)]
        keys = per_window_keys(primary)
        source = names.index("Mg II k 2796") + 1
        hdu = hdus[source]
        windows = []
        for i, (name, rest) in enumerate(LINES.items(), start=1):
            h = hdu.header.copy()
            lam = h["CRVAL1"] + (np.arange(h["NAXIS1"]) + 1 - h["CRPIX1"]) * h["CDELT1"]
            k = np.flatnonzero(np.abs((lam - rest) / rest * C_KMS) <= 46)
            h["CRPIX1"] -= k[0]
            raw = hdu.data[STEPS][:, :, k[0] : k[-1] + 1]
            window = fits.ImageHDU(raw * h["BSCALE"] + h["BZERO"], header=h)
            window.scale("int16", bscale=h["BSCALE"], bzero=h["BZERO"])
            windows.append(window)
            for prefix, value, comment in keys[source]:
                primary[prefix + str(i)] = (value, comment)
            primary[f"TDESC{i}"] = name
            primary[f"TWMIN{i}"], primary[f"TWMAX{i}"] = lam[k[0]], lam[k[-1]]
        primary["NWIN"] = len(LINES)
        aux, source_files = hdus[-2], hdus[-1]
        aux.data = aux.data[STEPS]
        source_files.data = source_files.data[STEPS]
        out = fits.HDUList([hdus[0], *windows, aux, source_files])
        name = Path(RASTER).name.replace(".fits", "_mg_features_test.fits")
        out.writeto(OUT / name, overwrite=True)
        print(name, [w.data.shape for w in windows], (OUT / name).stat().st_size)


def references():
    ref = readsav(IDL / "mg_features_4000005156_r00000.sav")
    np.savez_compressed(
        OUT / "iris_get_mg_features_lev2_4000005156_r00000.npz",
        steps=np.array(STEPS),
        **{key: ref[key][STEPS].astype(np.float32) for key in ("lc", "bp", "rp")},
    )
    probes = readsav(IDL / "probes.sav")
    Table(
        {"t": probes["t_inc"], "tension_0": probes["spline_inc_s0"], "tension_1": probes["spline_inc_s1"]},
        meta={
            "comment": [
                "IDL 9.2 SPLINE(x, y, t, tension) with x = -2.5, -2.25, ..., 2.5 and y = exp(-x^2) + 0.1 x,",
                "from the probes of the IDL reference run (2026-09-28).",
            ]
        },
    ).write(OUT / "idl_spline.ecsv", overwrite=True)
    for f in OUT.glob("*.npz"):
        print(f.name, f.stat().st_size)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    crop()
    references()
