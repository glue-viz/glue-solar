"""Proposed glue_solar/tests/test_fitting.py (imports point at the scratchpad prototype here)."""

import numpy as np
import pytest
from glue.core import DataCollection
from glue.core.component import Component
from glue.core.data import Data
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState

from astropy.wcs import WCS

from glue_solar.sources.loaders.iris import _GlueWCS, image_data, raster_data
from wp6_fitting import _WORKERS, add_fit_products, fit_gaussians, gaussian_fit_data, start_fit, wavelength_angstrom

WAVELENGTH = 1402.0 + 0.025 * np.arange(40)  # one Angstrom of an IRIS FUV window


def gaussian(x, amplitude, mean, stddev):
    return amplitude * np.exp(-0.5 * ((x - mean) / stddev) ** 2)


def synthetic_cube(n_gaussians, shape=(6, 5)):
    """Spectra with smoothly varying parameters; returns (cube, {component name: truth map})."""
    x, y = np.meshgrid(np.linspace(0, 1, shape[0]), np.linspace(0, 1, shape[1]), indexing="ij")
    truth = {"background": 5 + 2 * x}
    if n_gaussians == 1:
        truth |= {"amplitude": 100 + 50 * x, "centroid": 1402.45 + 0.1 * y, "width": 0.06 + 0.02 * x}
    else:  # Mg II k like: two peaks either side of a central reversal
        truth |= {"amplitude 1": 100 + 50 * x, "centroid 1": 1402.35 + 0.04 * y, "width 1": 0.08 + 0.01 * x}
        truth |= {"amplitude 2": 70 + 20 * y, "centroid 2": 1402.65 - 0.04 * x, "width 2": 0.08 + 0.005 * y}
    cube = truth["background"][..., None] + np.zeros(WAVELENGTH.size)
    for i in range(1, n_gaussians + 1):
        suffix = f" {i}" if n_gaussians > 1 else ""
        cube = cube + gaussian(
            WAVELENGTH, *(truth[f"{name}{suffix}"][..., None] for name in ("amplitude", "centroid", "width"))
        )
    return cube, truth


@pytest.fixture
def synthetic_raster():
    """A glue-solar-like raster dataset: WAVE first in WCS order, helioprojective TAN axes, Angstrom."""
    cube, truth = synthetic_cube(1)
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]
    wcs.wcs.cunit = ["Angstrom", "arcsec", "arcsec"]
    wcs.wcs.crpix = [1, 1, 1]
    wcs.wcs.crval = [WAVELENGTH[0], 0, 0]
    wcs.wcs.cdelt = [WAVELENGTH[1] - WAVELENGTH[0], 0.33, 0.35]
    data = Data(label="synthetic")
    data.coords = _GlueWCS(wcs)
    data.add_component(Component(cube, units="DN_IRIS_FUV"), "synthetic")
    return data, truth


@pytest.mark.parametrize("n_gaussians", [1, 2])
def test_fit_gaussians_recovers_synthetic_parameters(n_gaussians):
    cube, truth = synthetic_cube(n_gaussians)
    fit, residual = fit_gaussians(cube, WAVELENGTH, n_gaussians, scheduler="single-threaded")
    np.testing.assert_allclose(fit.amplitude_0.value, truth["background"], rtol=1e-4)
    for i in range(1, n_gaussians + 1):
        suffix = f" {i}" if n_gaussians > 1 else ""
        np.testing.assert_allclose(getattr(fit, f"amplitude_{i}").value, truth[f"amplitude{suffix}"], rtol=1e-4)
        np.testing.assert_allclose(getattr(fit, f"mean_{i}").value, truth[f"centroid{suffix}"], rtol=1e-6)
        np.testing.assert_allclose(getattr(fit, f"stddev_{i}").value, truth[f"width{suffix}"], rtol=1e-4)
    assert residual.shape == cube.shape
    assert np.sqrt(np.mean(residual**2)) < 1e-3


def test_double_gaussian_seeds_at_the_given_centre():
    cube, truth = synthetic_cube(2)
    fit, _ = fit_gaussians(cube, WAVELENGTH, 2, rest=1402.5, scheduler="single-threaded")  # gallery 07 recipe
    np.testing.assert_allclose(fit.mean_1.value, truth["centroid 1"], rtol=1e-6)
    np.testing.assert_allclose(fit.mean_2.value, truth["centroid 2"], rtol=1e-6)


def test_wavelength_axis_is_read_in_cartesian_order(synthetic_raster):
    data, _ = synthetic_raster
    np.testing.assert_allclose(wavelength_angstrom(data), WAVELENGTH)
    wrong = data.coords.pixel_to_world_values(0, 0, np.arange(WAVELENGTH.size))[0]  # wavelength index passed last
    assert np.unique(np.asarray(wrong)).size == 1  # silently constant: the trap the helper avoids


def test_maps_share_the_spatial_grid_and_link_back(synthetic_raster):
    data, truth = synthetic_raster
    maps, residual = gaussian_fit_data(data, 1, scheduler="single-threaded")
    assert maps.label == "synthetic-gauss1"
    assert maps.shape == data.shape[:-1]
    assert [c.label for c in maps.main_components] == ["background", "amplitude", "centroid", "width"]
    assert [maps.get_component(c).units for c in maps.main_components] == [
        "DN_IRIS_FUV",
        "DN_IRIS_FUV",
        "Angstrom",
        "Angstrom",
    ]
    assert [c.label for c in maps.world_component_ids] == ["Helioprojective Longitude", "Helioprojective Latitude"]
    assert list(maps.coords.world_axis_units) == ["arcsec", "arcsec"]
    assert maps.coords.pixel_to_world_values(3, 2) == pytest.approx(data.coords.pixel_to_world_values(0, 3, 2)[1:])
    np.testing.assert_allclose(maps["centroid"], truth["centroid"], rtol=1e-6)

    collection = DataCollection([data])
    add_fit_products(data, collection, maps, residual)
    assert [d.label for d in collection] == ["synthetic", "synthetic-gauss1"]
    assert data.get_component(data.id["synthetic-gauss1 residual"]).units == "DN_IRIS_FUV"
    box = RoiSubsetState(maps.pixel_component_ids[1], maps.pixel_component_ids[0], RectangularROI(0.5, 2.5, 0.5, 3.5))
    collection.new_subset_group("box", box)
    n_map = maps.subsets[0].to_mask().sum()
    assert n_map == 6
    assert data.subsets[0].to_mask().sum() == n_map * WAVELENGTH.size


def test_real_raster_smoke(irispy_test_files):
    path = next(p for p in irispy_test_files if p.name == "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits")
    data = raster_data([path], ["Si IV 1403"])[0]
    wavelength = wavelength_angstrom(data)
    assert wavelength.shape == (29,)
    assert (
        1398 < wavelength[0] < wavelength[-1] < 1400
    )  # the bundled window is cropped; the line core (1402.77) is outside
    maps, residual = gaussian_fit_data(data, 1, scheduler="single-threaded")
    assert maps.shape == (8, 109)
    assert residual.shape == (8, 109, 29)
    assert [c.label for c in maps.main_components] == ["background", "amplitude", "centroid", "width", "Time"]
    assert [maps.get_component(c).units for c in maps.main_components[:4]] == [
        "DN_IRIS_FUV",
        "DN_IRIS_FUV",
        "Angstrom",
        "Angstrom",
    ]
    assert [c.label for c in maps.world_component_ids] == ["Helioprojective Longitude", "Helioprojective Latitude"]
    np.testing.assert_array_equal(maps["Time"], data["Time"][..., 0])
    centroid = maps["centroid"]
    assert np.isnan(centroid).mean() < 0.05  # failed fits are NaN, not exceptions
    assert wavelength[0] < np.nanmedian(centroid) < wavelength[-1]


def test_image_cubes_are_rejected(irispy_test_files):
    path = next(p for p in irispy_test_files if p.name == "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits")
    with pytest.raises(ValueError, match="no wavelength axis"):
        wavelength_angstrom(image_data(path))


def test_start_fit_adds_products_when_the_worker_finishes(qtbot, synthetic_raster):
    data, truth = synthetic_raster
    collection = DataCollection([data])
    worker = start_fit(data, collection, 1, None, scheduler="single-threaded")
    assert worker in _WORKERS
    worker.wait()
    qtbot.waitUntil(lambda: len(collection) == 2)  # result/finished signals are delivered on the main thread
    assert _WORKERS == []
    np.testing.assert_allclose(collection[1]["centroid"], truth["centroid"], rtol=1e-6)
    assert data.id["synthetic-gauss1 residual"] is not None
