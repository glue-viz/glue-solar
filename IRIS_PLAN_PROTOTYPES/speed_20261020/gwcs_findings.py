"""Re-verification of the new upstream speed findings (GLUE_SPEED.md 'New upstream findings, 2026-10-20')."""
import cProfile, io, pstats, sys, timeit
import numpy as np
import astropy, astropy.units as u
from astropy.io import fits
from astropy.modeling import models as m
from astropy.wcs import WCS
import dkist, gwcs
from dkist.wcs.models import VaryingCelestialTransform
from irispy.io.sji import read_sji_lvl2

print("versions: dkist", dkist.__version__, "gwcs", gwcs.__version__, "astropy", astropy.__version__)
cube = read_sji_lvl2(sys.argv[1], memmap=True, uncertainty=False)
w = cube.wcs.low_level_wcs
n = cube.data.shape[0]


def per(fn, number=20, repeat=5):
    return min(timeit.repeat(fn, number=number, repeat=repeat)) / number * 1e3


vct = next(mm for mm in w.forward_transform.traverse_postorder() if isinstance(mm, VaryingCelestialTransform))
pc = vct.pc_table.to_value(u.pix)
crpix = vct.crpix_table.to_value(u.pix)
crval = vct.crval_table.to_value(u.deg)
cdelt = (vct.cdelt.value * u.arcsec).to_value(u.deg)
lon_pole = vct.lon_pole.value


TAN = m.Pix2Sky_Gnomonic()


def vectorized(x, y, z):
    """dkist's per-frame chain, Shift | PC | CDELT | TAN | rotation, with each element's frame's tables, in one pass."""
    i = np.round(z).astype(int)
    d = np.stack([x - crpix[i, 0], y - crpix[i, 1]], -1)
    p = np.einsum("nij,nj->ni", pc[i], d) * cdelt
    phi, theta = np.deg2rad(TAN.evaluate(p[:, 0], p[:, 1]))
    # native to celestial for a zenithal projection, each element at its own CRVAL (Calabretta & Greisen 2002, eq. 2)
    a0, d0, pole = np.deg2rad(crval[i, 0]), np.deg2rad(crval[i, 1]), np.deg2rad(lon_pole)
    dphi = phi - pole
    lat = np.arcsin(np.sin(theta) * np.sin(d0) + np.cos(theta) * np.cos(d0) * np.cos(dphi))
    lon = a0 + np.arctan2(-np.cos(theta) * np.sin(dphi), np.sin(theta) * np.cos(d0) - np.cos(theta) * np.sin(d0) * np.cos(dphi))
    lon, lat = np.rad2deg(lon), np.rad2deg(lat)
    return ((lon + 180) % 360 - 180) * 3600, lat * 3600


x, y, z = np.full(n, 100.0), np.full(n, 200.0), np.arange(n, dtype=float)
ref = w.pixel_to_world_values(x, y, z)
lon, lat = vectorized(x, y, z)
loop, vec = per(lambda: w.pixel_to_world_values(x, y, z), number=3), per(lambda: vectorized(x, y, z), number=50)
print(f"1. one point in each of {n} frames: gWCS {loop:.1f} ms, vectorized prototype {vec:.3f} ms ({loop / vec:.0f}x);"
      f" max difference {np.abs(lon - ref[0]).max():.1e}, {np.abs(lat - ref[1]).max():.1e} arcsec")
one = per(lambda: w.pixel_to_world_values(100.0, 200.0, 3.0))
many = per(lambda: w.pixel_to_world_values(np.full(10000, 100.0), np.full(10000, 200.0), np.full(10000, 3.0)), number=5)
print(f"   one point {one:.2f} ms; 10000 points of one frame {many:.2f} ms")

lon1, lat1, t1 = w.pixel_to_world_values(100.0, 200.0, 3.0)
inv = per(lambda: w.world_to_pixel_values(lon1, lat1, t1))
build = per(lambda: vct.transform_at_index(3).inverse, number=100)
model = vct.transform_at_index(3).inverse
built = per(lambda: model(lon1 / 3600, lat1 / 3600), number=100)
print(f"2. one point: forward {one:.2f} ms, inverse {inv:.2f} ms; a frame's inverse model built {build:.3f} ms,"
      f" one built evaluated {built:.3f} ms")

header = cube.meta["frame_wcs_headers"][3]
frame = WCS(header if isinstance(header, fits.Header) else fits.Header(header))
fits_one = per(lambda: frame.pixel_to_world_values(100.0, 200.0), number=200)
flon, flat = frame.pixel_to_world_values(100.0, 200.0)
fl = (np.array([flon, flat]) * u.Unit(frame.world_axis_units[0])).to_value(u.arcsec)
print(f"4. frame 3's FITS WCS: {fits_one * 1e3:.1f} us a point against the gWCS's {one * 1e3:.0f} us;"
      f" its position off the gWCS's by {((fl[0] - lon1 + 648000) % 1296000) - 648000:.2e}, {fl[1] - lat1:.2e} arcsec")

profile = cProfile.Profile()
profile.enable()
for _ in range(300):
    w.pixel_to_world_values(100.0, 200.0, 3.0)
profile.disable()
out = io.StringIO()
pstats.Stats(profile, stream=out).sort_stats("tottime").print_stats(10)
print("5. own time of 300 one-point forward calls, top 10:")
for line in out.getvalue().splitlines():
    if line.strip()[:1].isdigit():
        print("  ", line.strip()[:160])
