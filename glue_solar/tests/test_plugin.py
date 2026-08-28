from glue.config import data_factory
from irispy.data.test import get_test_data_filenames

from glue_solar.sources.iris import read_iris_files


def _fixture(name):
    return str(next(path for path in get_test_data_filenames() if path.name == name))


def test_data_factories_are_registered():
    labels = {item.label for item in data_factory}
    assert {"IRIS FITS", "sunpy Map"} <= labels


def test_read_real_sji():
    data = read_iris_files(_fixture("iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"))
    assert data.label == "IRIS-SJI-1400-3620258102"
    assert data.shape == (62, 40, 37)
    assert data.style.preferred_cmap.name == "irissji1400"


def test_read_real_raster_gives_one_dataset_per_window_and_scan():
    datasets = read_iris_files(_fixture("iris_l2_20140329_140938_3860258481_raster_t000_r00000.fits"))
    assert [d.label for d in datasets][:2] == ["C_II_1336-3860258481-scan-0", "1343-3860258481-scan-0"]
    assert len(datasets) == 9
    assert datasets[0].shape == (8, 109, 17)
