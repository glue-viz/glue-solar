"""
Build the burst test data for irispy from local L2 files and the IDL reference run.

Si IV: 4000005156 raster r00000, only the Si IV 1403 window, rows 385-575, the bins within
+-50 km/s of 1402.77 A plus 3 bins each side; all 64 steps, so step indices equal IDL's.
SJI: 4000255147 SJI 1400, a few whole frames.
"""
import re
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.table import Table
from scipy.io import readsav

IDL = Path("~/Git/irispy/iris_ref_out/iris_ref_out")
RASTER = "~/DATA/IRIS/0598beef2a051b4f371a4b09e439c4e4-iris_l2_20130902_182935_4000005156_raster/iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits"
SJI = "~/DATA/IRIS/534d789bb0a2821fb2b78eb36d1d6753-iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits.gz"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
WINDOW, Y0, Y1, MARGIN = 6, 385, 576, 3
C_KMS, LREF = 299792.458, 1402.77


def repair_tfields(hdus):
    # real spectrograph files understate TFIELDS in the source-filename table (see compress.py)
    header = hdus[-1].header
    header["TFIELDS"] = sum(1 for key in header if key.startswith("TTYPE"))


def single_window_header(header, iwin):
    """Keep only window ``iwin``'s per-window keywords, renumbered as window 1."""
    header = header.copy()
    nwin = header["NWIN"]
    for key in list(header):
        m = re.fullmatch(r"([A-Z]+\d*?_?)(\d)", key)
        if m and key.startswith(("T", "IPRP")) and 1 <= int(m.group(2)) <= nwin:
            value, comment = header[key], header.comments[key]
            del header[key]
            if int(m.group(2)) == iwin:
                header[m.group(1) + "1"] = (value, comment)
    header["NWIN"] = 1
    return header


def si_iv():
    with fits.open(RASTER, do_not_scale_image_data=True) as hdus:
        repair_tfields(hdus)
        hdus.verify("fix")
        win = hdus[WINDOW]
        h = win.header
        lam = h["CRVAL1"] + (np.arange(h["NAXIS1"]) + 1 - h["CRPIX1"]) * h["CDELT1"]
        k = np.flatnonzero(np.abs((lam - LREF) / LREF * C_KMS) <= 50)
        k0, k1 = k[0] - MARGIN, k[-1] + MARGIN + 1
        win.data = win.data[:, Y0:Y1, k0:k1].copy()  # raw integers: BSCALE and BZERO stay
        h["CRPIX1"] -= k0
        h["CRPIX2"] -= Y0
        hdus[0].header = single_window_header(hdus[0].header, WINDOW)
        hdus[0].header["TWMIN1"], hdus[0].header["TWMAX1"] = lam[k0], lam[k1 - 1]
        data = win.data
        out = fits.HDUList([hdus[0], win, hdus[-2], hdus[-1]])
        name = Path(RASTER).name.replace(".fits", "_si_iv_test.fits")
        out.writeto(OUT / name, overwrite=True)
        print(name, data.shape, f"bins {k0}:{k1}", (OUT / name).stat().st_size)
    ref = readsav(IDL / "burst_4000005156_r00000_thr40.sav")
    o = ref["output"]
    t = Table(
        {
            "step": o["XPIX"].astype(int),
            "y": o["YPIX"].astype(int),
            "group": o["GROUP"].astype(int),
            "intensity": o["INTENSITY"].astype(float),
            "median": o["MEDIAN"].astype(float),
        }
    )
    t.meta = {
        "comment": [
            "iris_burst_check, file, threshold=40., output=output (IDL 9.2, SSW 2026-09-28) on",
            "iris_l2_20130902_182935_4000005156_raster_t000_r00000.fits; one row per burst pixel.",
            "step and y index the full file; the _si_iv_test.fits crop starts at y = y_offset.",
        ],
        "threshold": 40.0,
        "default_threshold": float(readsav(IDL / "burst_4000005156_r00000.sav")["threshold"]),
        "y_offset": Y0,
    }
    t.write(OUT / "iris_burst_check_4000005156_r00000_thr40.ecsv", overwrite=True)


def parse_sji_txt():
    lines = (IDL / "sji_burst_4000255147.txt").read_text().split("\n")[2:]
    i, frames = 0, {}
    while i < len(lines) and lines[i].strip():
        im, nev, npix = map(int, lines[i].split())
        frames[im] = (nev, np.array([lines[i + 1 + j].split() for j in range(npix)], float))
        i += 1 + npix
    return frames


def sji(keep):
    frames = parse_sji_txt()
    summary = Table(
        {
            "frame": np.array(sorted(frames)),
            "nevents": np.array([frames[f][0] for f in sorted(frames)]),
            "npix": np.array([len(frames[f][1]) for f in sorted(frames)]),
        }
    )
    summary.meta = {
        "comment": [
            "iris_sji_burst_check, '2-sep-2013 17:00', output=output (IDL 9.2, SSW 2026-09-28) on",
            "iris_l2_20130902_163935_4000255147_SJI_1400_t000.fits: events and burst pixels per frame.",
        ]
    }
    summary.write(OUT / "iris_sji_burst_check_4000255147_summary.ecsv", overwrite=True)
    rows = [(i, f, *r) for i, f in enumerate(keep) for r in frames[f][1]]
    pixels = Table(rows=rows, names=("frame", "idl_frame", "pixel", "group", "intensity"),
                   dtype=(int, int, int, int, float))
    pixels.meta = {
        "comment": [
            "Burst pixels of iris_sji_burst_check (IDL 9.2) for the frames in the _test.fits subset;",
            "frame indexes the subset, idl_frame the full file, pixel is the flat index of (y, x).",
        ]
    }
    pixels.write(OUT / "iris_sji_burst_check_4000255147_pixels.ecsv", overwrite=True)
    with fits.open(SJI, do_not_scale_image_data=True) as hdus:
        hdus[0].data = hdus[0].data[keep]
        hdus[1].data = hdus[1].data[keep]
        hdus[2].data = hdus[2].data[keep]
        hdus[0].header["NEXP"] = len(keep)
        name = Path(SJI).name.split("-", 1)[1].replace(".fits.gz", "_test.fits")
        hdus.writeto(OUT / name, overwrite=True)
        print(name, hdus[0].data.shape, (OUT / name).stat().st_size)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    si_iv()
    frames = parse_sji_txt()
    counts = {f: frames[f][0] for f in frames}
    busiest = max(counts, key=counts.get)
    print("SJI events per frame: min", min(counts.values()), "max", counts[busiest], "at", busiest, "frame 69:", counts[69])
    sji(sorted({0, 69, busiest}))
