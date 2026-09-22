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
        path for path in irispy_test_files if path.name == "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
    )
    data = load_data(str(path))
    assert data.label == "SJI_1400-3620258102-2021-09-05T00:18:33"
    assert data.shape == (62, 40, 37)
    assert data.style.preferred_cmap.name == "irissji1400"


def test_open_real_raster_through_load_data(irispy_test_files):
    path = next(
        path for path in irispy_test_files if path.name == "iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits"
    )
    datasets = load_data(str(path))
    assert len(datasets) == 9
    assert datasets[0].label == "C_II_1336-3860258481-2014-03-29T14:09:38-scan-0"
    assert datasets[0].shape == (8, 109, 17)
    assert datasets[0].find_component_id("Time") is not None
