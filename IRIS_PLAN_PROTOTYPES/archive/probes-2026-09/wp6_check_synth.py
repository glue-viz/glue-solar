"""Synthetic-cube checks for WP6: parameter recovery, Data path, links, wrong-axis-order pitfall."""
import sys, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad")
import numpy as np
import astropy.units as u
from astropy.wcs import WCS
from glue.core import DataCollection
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from glue_solar.sources.loaders.iris import _GlueWCS
from wp6_fitting import fit_gaussians, gaussian_fit_data, add_fit_products, wavelength_angstrom


def gauss(x, a, m, s):
    return a * np.exp(-0.5 * ((x - m) / s) ** 2)


def synthetic_cube(n_gaussians, shape=(6, 5, 40)):
    """(cube, wavelength_angstrom, truth dict); parameters vary smoothly across the field."""
    nx, ny, nwl = shape
    wl = 1402.0 + 0.025 * np.arange(nwl)  # IRIS-like FUV window, 1 Angstrom wide
    ix, iy = np.meshgrid(np.linspace(0, 1, nx), np.linspace(0, 1, ny), indexing="ij")  # 0..1 across the field
    bg = 5.0 + 2 * ix
    if n_gaussians == 1:
        amp, cen, sig = 100.0 + 50 * ix, 1402.45 + 0.10 * iy, 0.06 + 0.02 * ix
        cube = bg[..., None] + gauss(wl, amp[..., None], cen[..., None], sig[..., None])
        truth = {"background": bg, "amplitude": amp, "centroid": cen, "width": sig}
    else:  # Mg II k like: two peaks either side of a central reversal
        amp1, cen1, sig1 = 100.0 + 50 * ix, 1402.35 + 0.04 * iy, 0.08 + 0.01 * ix
        amp2, cen2, sig2 = 70.0 + 20 * iy, 1402.65 - 0.04 * ix, 0.08 + 0.005 * iy
        cube = bg[..., None] + gauss(wl, amp1[..., None], cen1[..., None], sig1[..., None]) + gauss(wl, amp2[..., None], cen2[..., None], sig2[..., None])
        truth = {"background": bg, "amplitude 1": amp1, "centroid 1": cen1, "width 1": sig1,
                 "amplitude 2": amp2, "centroid 2": cen2, "width 2": sig2}
    return cube, wl, truth


def synthetic_data(cube, wl, label="synthetic"):
    """A glue-solar-like raster Data: FITS WCS with WAVE first (WCS order), helioprojective TAN axes."""
    from glue.core import Data
    from glue.core.component import Component
    w = WCS(naxis=3)
    w.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]
    w.wcs.cunit = ["Angstrom", "arcsec", "arcsec"]
    w.wcs.crpix = [1, 1, 1]
    w.wcs.crval = [wl[0], 0, 0]
    w.wcs.cdelt = [wl[1] - wl[0], 0.33, 0.35]
    d = Data(label=label)
    d.coords = _GlueWCS(w)
    d.add_component(Component(cube, units="DN_IRIS_FUV"), label)
    return d


if __name__ == "__main__":
    for n in (1, 2):
        cube, wl, truth = synthetic_cube(n)
        fit, resid = fit_gaussians(cube, wl, n, scheduler="single-threaded")
        got = {"background": fit.amplitude_0.value}
        for i in range(1, n + 1):
            sfx = f" {i}" if n > 1 else ""
            got[f"amplitude{sfx}"] = getattr(fit, f"amplitude_{i}").value
            got[f"centroid{sfx}"] = getattr(fit, f"mean_{i}").value
            got[f"width{sfx}"] = getattr(fit, f"stddev_{i}").value
        worst = max(np.nanmax(np.abs(got[k] - truth[k]) / np.abs(truth[k])) for k in truth)
        print(f"n={n}: cube {cube.shape} nan={np.isnan(fit.amplitude_0.value).sum()} worst rel err={worst:.2e} residual rms={np.sqrt((resid**2).mean()):.2e}")
        assert worst < 1e-4 and np.sqrt((resid**2).mean()) < 1e-3

    # Data path: wavelength extraction, maps Data, links, ROI propagation
    cube, wl, truth = synthetic_cube(1)
    d = synthetic_data(cube, wl)
    print("world_axis_units", d.coords.world_axis_units, "physical", d.coords.world_axis_physical_types)
    np.testing.assert_allclose(wavelength_angstrom(d), wl)
    wrong = d.coords.pixel_to_world_values(0, 0, np.arange(cube.shape[-1]))[0]  # wavelength index passed LAST
    print("wrong-order wavelength: unique values =", np.unique(np.asarray(wrong)).size, "->", np.unique(np.asarray(wrong)))
    maps, resid = gaussian_fit_data(d, 1, None, scheduler="single-threaded")
    print("maps", maps.label, maps.shape, [c.label for c in maps.main_components], [maps.get_component(c).units for c in maps.main_components])
    print("maps world", [c.label for c in maps.world_component_ids], maps.coords.world_axis_units)
    print("maps lon/lat at (2,3):", maps.coords.pixel_to_world_values(3, 2), "source:", d.coords.pixel_to_world_values(0, 3, 2)[1:])
    dc = DataCollection([d])
    add_fit_products(d, dc, maps, resid)
    print("dc", [x.label for x in dc], "links", len(dc.links), "source components", [c.label for c in d.main_components])
    state = RoiSubsetState(maps.pixel_component_ids[1], maps.pixel_component_ids[0], RectangularROI(0.5, 2.5, 0.5, 3.5))
    sg = dc.new_subset_group("box", state)
    n_map, n_src = maps.subsets[0].to_mask().sum(), d.subsets[0].to_mask().sum()
    print(f"ROI on maps {n_map} px -> source {n_src} px (= {n_map} x {cube.shape[-1]} = {n_map * cube.shape[-1]})")
    assert n_src == n_map * cube.shape[-1]
    np.testing.assert_allclose(maps["centroid"], truth["centroid"], rtol=1e-5)
    print("SYNTH OK")
