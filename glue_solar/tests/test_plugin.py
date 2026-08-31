from glue.config import data_factory, menubar_plugin
from glue.core.data_factories import load_data

import glue_solar
from glue_solar.conftest import MD5, OBS_A
from glue_solar.sources.iris import is_iris_fits


def test_setup_registers_hooks():
    glue_solar.setup()
    assert "IRIS: browse observations…" in [label for label, _ in menubar_plugin]
    iris = next(f for f in data_factory if f.label == "IRIS Level 2 FITS")
    for label in ("FITS file", "sunpy Map"):  # both also match IRIS files; ours must win
        other = next(f for f in data_factory if f.label == label)
        assert iris.priority > (other.priority or 0)


def test_data_factory_claims_only_iris_files(iris_tree):
    d, t, o = OBS_A
    sji = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SJI_1400_t000.fits.gz"
    aia = iris_tree / f"{MD5}iris_l2_{d}_{t}_{o}_SDO" / f"aia_l2_{d}_{t}_{o}_171.fits"
    assert is_iris_fits(str(sji))
    assert not is_iris_fits(str(aia))  # TELESCOP is blank on the cutouts
    assert not is_iris_fits(str(iris_tree / "notes.txt"))


def test_open_real_sji_through_load_data(irispy_test_files):
    path = next(
        path for path in irispy_test_files if path.name == "iris_l2_20210905_001833_3620258102_SJI_1400_t000_test.fits"
    )
    data = load_data(str(path))
    assert data.label == "SJI_1400-3620258102-2021-09-05T00:18:33"
    assert data.shape == (62, 40, 37)
    assert data.style.preferred_cmap.name == "irissji1400"


def test_open_real_raster_through_load_data(irispy_test_files):
    path = next(
        path for path in irispy_test_files if path.name == "iris_l2_20140329_140938_3860258481_raster_t000_r00000_test.fits"
    )
    datasets = load_data(str(path))
    assert len(datasets) == 9
    assert datasets[0].label == "C_II_1336-3860258481-2014-03-29T14:09:38-scan-0"
    assert datasets[0].shape == (8, 109, 17)
    assert datasets[0].find_component_id("Time") is not None


def test_open_synthetic_sji_through_load_data(iris_tree):
    # The synthetic fixtures are complete enough for irispy's readers
    path = next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_SJI_1400_t000.fits.gz"))
    data = load_data(str(path))
    assert data.shape == (3, 4, 5)
    assert tuple(data.coords.world_axis_physical_types) == (
        "custom:pos.helioprojective.lon",
        "custom:pos.helioprojective.lat",
        "time",
    )


def test_open_synthetic_raster_through_load_data(iris_tree):
    raster_dir = next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_raster"))
    path = sorted(raster_dir.glob("*.fits"))[0]
    datasets = load_data(str(path))
    assert len(datasets) == 2
    for data in datasets:
        assert data.shape == (3, 4, 5)
        assert tuple(data.coords.world_axis_physical_types) == (
            "em.wl",
            "custom:pos.helioprojective.lat",
            "custom:pos.helioprojective.lon",
        )


def test_autolink_synthetic_sji_raster(iris_tree):
    # SJI + raster autolink with no manual step: glue must pair the
    # helioprojective axes across the two instruments (permuting the world
    # order and slicing the SJI time axis away).
    try:
        from glue.plugins.wcs_autolinking.wcs_autolinking import permuted_values_functions  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("glue-core without APE-14 low-level WCS autolinking")
    from glue.core import DataCollection
    from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink

    sji = load_data(str(next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_SJI_1400_t000.fits.gz"))))
    raster_dir = next(iris_tree.glob(f"{MD5}iris_l2_20250328_*_raster"))
    raster = load_data(str(sorted(raster_dir.glob("*.fits"))[0]))[0]

    links = wcs_autolink(DataCollection([sji, raster]))
    assert len(links) == 1
    link = links[0]
    assert len(link) == 4

    # The two celestial pixel axes on each side; the SJI time axis and the
    # raster wavelength axis are sliced away
    assert {cid.axis for cid in link.cids1} == {1, 2}
    assert {cid.axis for cid in link.cids2} == {0, 1}
