"""R33-R35: dkist's VaryingCelestialTransform as irispy builds a slit-jaw gWCS (sji.py _create_gwcs), 400 frames.

Run: python -I dkist_vct.py [DKIST_SOURCE_DIR]  (no argument: the env's installed dkist)
"""

import sys
import time
import warnings

if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
warnings.simplefilter("ignore")

import numpy as np

import astropy.units as u

import dkist
from dkist.wcs.models import VaryingCelestialTransform

print("dkist", dkist.__file__.rsplit("/", 3)[-3] if len(sys.argv) > 1 else dkist.__version__)
n = 400
rng = np.random.default_rng(0)
angle = np.deg2rad(rng.uniform(-1, 1, n))
pc = np.stack([np.cos(angle), -np.sin(angle), np.sin(angle), np.cos(angle)], axis=1).reshape(-1, 2, 2)
crval = np.stack([rng.uniform(-200, -199, n), rng.uniform(100, 101, n)], axis=1)
vct = VaryingCelestialTransform(
    cdelt=[0.1663, 0.1663] * u.arcsec / u.pixel,
    pc_table=pc * u.pixel,
    crval_table=crval * u.arcsec,
    crpix_table=[208.0, 194.0] * u.pixel,
)

# R35: an off-table (NaN) frame index, as a time off the frames gives
print("NaN index cast to int on this CPU:", np.array(np.nan).astype(int))
lon, lat = vct(100 * u.pix, 100 * u.pix, 5 * u.pix)
for z in (np.nan, 400.0, -1.0):
    try:
        out = vct.inverse(lon, lat, z * u.pix)
        print(f"inverse at z={z}:", [float(np.asarray(getattr(o, "value", o))) for o in out])
    except Exception as e:  # noqa: BLE001
        print(f"inverse at z={z}: {type(e).__name__}: {e}")
    try:
        out = vct(100 * u.pix, 100 * u.pix, z * u.pix)
        print(f"forward at z={z}:", [float(np.asarray(getattr(o, "value", o))) for o in out])
    except Exception as e:  # noqa: BLE001
        print(f"forward at z={z}: {type(e).__name__}: {e}")


def best(f, k=7):
    times = []
    for _ in range(k):
        t = time.perf_counter()
        f()
        times.append(time.perf_counter() - t)
    return min(times) * 1e3


x = np.full(n, 100.0) * u.pix
z = np.arange(n) * u.pix
print(f"R33 forward, one point in each of {n} frames: {best(lambda: vct(x, x, z)):.1f} ms")
xs = rng.uniform(0, 400, 10_000) * u.pix
print(f"forward, 10,000 points of one frame: {best(lambda: vct(xs, xs, 5 * u.pix)):.2f} ms")
print(f"R34 inverse, one point: {best(lambda: vct.inverse(lon, lat, 5 * u.pix), 21):.2f} ms;"
      f" forward one point: {best(lambda: vct(100 * u.pix, 100 * u.pix, 5 * u.pix), 21):.2f} ms")
