"""
Timing of WCSLIB's -TAB inverse (tabs2x) on a 2-D coordinate table shaped like
those of IRIS spectrograph rasters.  numpy and astropy only, no data files.

    python tab_inverse_repro.py [n_inverse]      (default 1000 points per case)

The WCS is built as the irispy package builds it for an IRIS raster:

    axis 1  WAVE      linear
    axis 2  HPLT-TAB  pixel along the slit      (table axis m=1, index vector SPATIAL)
    axis 3  HPLN-TAB  exposure number           (table axis m=2, no index vector)

Both -TAB axes share one coordinate array, COORDS[K2][K1][M] in C order, with
M = 2 (lat, lon in degrees), K1 = 2 (the two ends of the slit) and K2 = 1600
(one row per exposure).  So the table holds 1599 long, thin quadrilateral
cells, one per pair of consecutive exposures, each tilted like the slit:
0.64 deg, or 2 arcsec in longitude over the slit's 182 arcsec.

(a) sit-and-stare: the slit stays put; the pointing has 0.001" jitter and
    moves 0.05" every 6 exposures (13" over 1600 exposures), so cells overlap.
(b) scanning raster: the slit moves 0.35" per exposure; no cells overlap.
"""

import sys
import time

import astropy
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcs import WCSLIB_VERSION

N_EXPOSURES = 1600
N_SLIT = 548  # slit pixels
CDELT2 = 0.3327  # arcsec per slit pixel
TILT = 0.0112  # the slit's longitude change per unit latitude (IRIS's PC3_2)
N_WAVE = 200
X0, Y0 = 300.0, 200.0  # arcsec, the slit's center at the first exposure


def raster_wcs(x, y):
    """The FITS -TAB WCS of a raster whose exposures point at x, y (arcsec)."""
    ends = np.array([1.0, N_SLIT]) - (N_SLIT + 1) / 2  # slit ends, pixels from the center
    lat = y[:, None] + CDELT2 * ends
    lon = x[:, None] + CDELT2 * TILT * ends
    coords = np.stack((lat, lon), axis=-1) / 3600  # (exposure, slit end, lat/lon), deg
    spatial = (Y0 + CDELT2 * ends) / 3600  # psi_2 = CRVAL2 + x_2 at the slit ends
    table = fits.BinTableHDU(
        np.array([(coords, spatial)], dtype=[("COORDS", float, coords.shape), ("SPATIAL", float, spatial.shape)]),
        name="WCS-TABLE",
    )
    table.header["TUNIT1"] = table.header["TUNIT2"] = "deg"

    h = fits.Header()
    h["NAXIS"] = 3
    h["NAXIS1"], h["NAXIS2"], h["NAXIS3"] = N_WAVE, N_SLIT, len(x)
    h["CTYPE1"], h["CUNIT1"], h["CRPIX1"], h["CRVAL1"], h["CDELT1"] = "WAVE", "Angstrom", 1.0, 1400.0, 0.026
    h["CTYPE2"], h["CUNIT2"], h["CRPIX2"], h["CRVAL2"], h["CDELT2"] = "HPLT-TAB", "deg", (N_SLIT + 1) / 2, Y0 / 3600, CDELT2 / 3600
    h["CTYPE3"], h["CUNIT3"], h["CRPIX3"], h["CRVAL3"], h["CDELT3"] = "HPLN-TAB", "deg", 1.0, 1.0, 1.0
    for i in (2, 3):
        h[f"PS{i}_0"], h[f"PS{i}_1"], h[f"PV{i}_3"] = "WCS-TABLE", "COORDS", i - 1
    h["PS2_2"] = "SPATIAL"  # the exposure axis has no index vector: psi_3 is the exposure number
    h["DATE-OBS"], h["MJD-OBS"] = "2023-02-25T00:00:00", 60000.0
    return WCS(h, fits.HDUList([fits.PrimaryHDU(), table]))


def timed(f, *args):
    t = time.perf_counter()
    out = f(*args)
    return out, time.perf_counter() - t


def report(name, w, n, rng, grid=60):
    shape = w.pixel_shape  # (wave, slit, exposure)
    coord = np.asarray(w.wcs.tab[0].coord)  # (exposure, slit end, lat/lon), deg
    x = coord[:, :, 1].mean(axis=1) * 3600
    print(f"\n== {name}: {shape[2]} exposures, slit center spans {np.ptp(x):.2f}\" in lon, median |step| {np.median(np.abs(np.diff(x))):.4f}\"")

    # Random pixels inside the table: forward, inverse, round trip.
    pix = [rng.uniform(0, s - 1, n) for s in shape]
    world, _ = timed(w.pixel_to_world_values, *pix)
    big = [rng.uniform(0, s - 1, 200_000) for s in shape]
    _, t_fwd = timed(w.pixel_to_world_values, *big)
    back, t_inv = timed(w.world_to_pixel_values, *world)
    d_exp, d_slit = back[2] - pix[2], np.abs(back[1] - pix[1])
    again = w.pixel_to_world_values(*back)
    d_world = 3600 * max(np.nanmax(np.abs(again[k] - world[k])) for k in (1, 2))
    print(f"   forward  {t_fwd / 2e5 * 1e6:9.3f} us/pt   ({2e5:.0f} random pixels)")
    print(f"   inverse  {t_inv / n * 1e6:9.1f} us/pt   ({n} random pixels inside the table)")
    # One call per point for the first 200, for the spread behind that mean (each call adds 5-20 us of Python and astropy).
    each = np.array([timed(w.world_to_pixel_values, *(c[j:j + 1] for c in world))[1] for j in range(min(n, 200))]) * 1e6
    print(f"            median {np.median(each):.1f}, 99th percentile {np.percentile(each, 99):.1f}, max {each.max():.1f} us"
          f" ({each.size} points one at a time)")
    print(f"   round trip: exposure off by up to {np.nanmax(np.abs(d_exp)):.3g}, by > 0.01 for {np.mean(np.abs(d_exp) > 0.01):.0%}"
          f" of points ({np.mean(d_exp < -0.01):.0%} earlier, {np.mean(d_exp > 0.01):.0%} later);"
          f" slit pixel off by up to {np.nanmax(d_slit):.3g}; {np.isnan(back[2]).sum()} not found")
    print(f"   the pixel returned maps back to the world point within {d_world:.1e} arcsec")

    # A regular lon/lat grid over the table's footprint and 5" around it, as when every
    # pixel of a slit-jaw image is inverted through the raster's WCS.
    lat, lon, m = coord[..., 0], coord[..., 1], 5 / 3600
    glat, glon = np.meshgrid(np.linspace(lat.min() - m, lat.max() + m, grid), np.linspace(lon.min() - m, lon.max() + m, grid))
    glat, glon = glat.ravel(), glon.ravel()
    wave = np.full(glat.size, world[0][0])
    first, _ = timed(w.world_to_pixel_values, wave, glat, glon)
    inside = np.isfinite(first[2])
    for label, k in (("inside", inside), ("outside", ~inside)):
        if k.any():
            _, t = timed(w.world_to_pixel_values, wave[k], glat[k], glon[k])
            print(f"   grid {label:7s} {t / k.sum() * 1e6:9.1f} us/pt   ({k.sum()} of {glat.size} grid points)")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, astropy {astropy.__version__}, bundled WCSLIB {WCSLIB_VERSION}")
    rng = np.random.default_rng(0)
    k = np.arange(N_EXPOSURES)

    def jitter(s):
        return rng.normal(0, s, N_EXPOSURES)

    report("(a) sit-and-stare", raster_wcs(X0 + 0.05 * (k // 6) + jitter(0.001), Y0 + jitter(0.001)), n, rng)
    report("(b) scanning raster", raster_wcs(X0 + 0.35 * k + jitter(0.003), Y0 + jitter(0.003)), n, rng)


if __name__ == "__main__":
    main()
