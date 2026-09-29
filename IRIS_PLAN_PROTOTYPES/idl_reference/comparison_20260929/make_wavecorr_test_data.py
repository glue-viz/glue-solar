"""
Build the wavelength-drift test data for irispy from local L2 files and the IDL reference run.

Crop: 4000005156 raster r00000, steps STEPS, the whole slit, and one window per reference line
cut to the line's fitted range. IDL references: the per-step shifts and drift curves of both runs.
"""
import glob
import re
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.table import QTable
from astropy.time import Time
import astropy.units as u
from scipy.io import readsav

IDL = Path("~/Git/irispy/iris_ref_out/iris_ref_out")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
RASTER = glob.glob("~/DATA/IRIS/*4000005156_raster/*r00000.fits")[0]
STEPS = [5, 22, 30, 40, 49, 60]
# new window name: (source window, fitted range in Å) as in iris_prep_wavecorr_l2.pro
LINES = {
    "Ni I 2799": ("Mg II k 2796", (2799.3, 2799.8)),
    "Mn I 2802": ("Mg II k 2796", (2801.6, 2802.4)),
    "Fe I 2805": ("Mg II k 2796", (2805.1, 2805.7)),
    "O I 1356": ("O I 1356", (1355.4, 1355.9)),
    "Fe II 1393": ("Si IV 1394", (1392.6, 1393.1)),
}
NAMES = ["Ni I", "Mn I", "Fe I", "O I", "Fe II"]


def per_window_keys(header):
    """{window number: [(prefix, value, comment)]} for the per-window primary keywords."""
    keys = {}
    for key in list(header):
        m = re.fullmatch(r"([A-Z]+\d*?_?)(\d)", key)
        if m and key.startswith(("T", "IPRP")) and 1 <= int(m.group(2)) <= header["NWIN"]:
            keys.setdefault(int(m.group(2)), []).append((m.group(1), header[key], header.comments[key]))
            del header[key]
    return keys


def crop():
    with fits.open(RASTER, do_not_scale_image_data=True) as hdus:
        table = hdus[-1].header
        table["TFIELDS"] = sum(1 for key in table if key.startswith("TTYPE"))
        hdus.verify("fix")
        primary = hdus[0].header
        names = [primary[f"TDESC{i}"] for i in range(1, primary["NWIN"] + 1)]
        keys = per_window_keys(primary)
        windows = []
        for i, (name, (source, (low, high))) in enumerate(LINES.items(), start=1):
            hdu = hdus[names.index(source) + 1]
            h = hdu.header.copy()
            lam = h["CRVAL1"] + (np.arange(h["NAXIS1"]) + 1 - h["CRPIX1"]) * h["CDELT1"]
            k = np.flatnonzero((lam >= low) & (lam <= high))
            h["CRPIX1"] -= k[0]
            raw = hdu.data[STEPS][:, :, k[0] : k[-1] + 1]
            window = fits.ImageHDU(raw * h["BSCALE"] + h["BZERO"], header=h)
            window.scale("int16", bscale=h["BSCALE"], bzero=h["BZERO"])  # exact: raw integers again
            windows.append(window)
            for prefix, value, comment in keys[names.index(source) + 1]:
                primary[prefix + str(i)] = (value, comment)
            primary[f"TDESC{i}"] = name
            primary[f"TWMIN{i}"], primary[f"TWMAX{i}"] = lam[k[0]], lam[k[-1]]
        primary["NWIN"] = len(LINES)
        aux, source_files = hdus[-2], hdus[-1]
        aux.data = aux.data[STEPS]
        source_files.data = source_files.data[STEPS]
        out = fits.HDUList([hdus[0], *windows, aux, source_files])
        name = Path(RASTER).name.replace(".fits", "_wavelength_drift_test.fits")
        out.writeto(OUT / name, overwrite=True)
        print(name, [w.data.shape for w in windows], (OUT / name).stat().st_size)


def references():
    for obs in ["4000005156", "3824262996"]:
        r = readsav(IDL / f"wavecorr_{obs}_r00000.sav").r[0]
        tai = Time("1958-01-01T00:00:00", scale="tai") + r.corr_tai * u.s
        t = QTable({"time": tai.utc})
        for j, name in enumerate(NAMES):
            t[name] = r.corrs[j, :, 0] * u.AA
        t["nuv"], t["fuv"] = r.corr_nuv * u.AA, r.corr_fuv * u.AA
        t.meta = {
            "comment": [
                f"r = iris_prep_wavecorr_l2(file) (IDL 9.2, SSW 2026-09-28) on",
                f"{Path(glob.glob(f'~/DATA/IRIS/*{obs}_raster/*r00000.fits')[0]).name}:",
                "per-step shifts r.corrs of the 5 reference lines and the drifts r.corr_nuv, r.corr_fuv.",
            ]
            + ([f"The _wavelength_drift_test.fits crop holds steps {STEPS}."] if obs == "4000005156" else []),
        }
        t.write(OUT / f"iris_prep_wavecorr_l2_{obs}_r00000.ecsv", overwrite=True)
        print(obs, len(t))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    crop()
    references()
