import pytest
from glue.core import DataCollection
from glue.plugins.wcs_autolinking.wcs_autolinking import IncompatibleWCS, WCSLink

import astropy.units as u
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar.sources.loaders.iris import image_data, raster_data

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
HPC = ["Helioprojective Longitude", "Helioprojective Latitude"]


def _real(files, name):
    return next(
        path for path in files if path.name.replace("_test.fits", ".fits") == name and path.parent.name == "sns"
    )


@pytest.fixture
def sns(irispy_test_files):
    """The matched sit-and-stare SJI 1400 + Si IV 1403 raster pair shipped with irispy."""
    [raster] = raster_data([_real(irispy_test_files, RASTER)], ["Si IV 1403"])
    return image_data(_real(irispy_test_files, SJI)), raster


def test_sji_and_raster_share_axis_names(sns):
    sji, raster = sns
    assert [c.label for c in sji.world_component_ids] == ["Time (Utc)", *HPC[::-1]]
    assert [c.label for c in raster.world_component_ids] == [*HPC, "Wavelength"]
    assert [c.label for c in sji.components].count("Time") == 1


def test_link_editor_wcs_link_works_or_refuses_cleanly(sns, irispy_test_files):
    # The link editor's "WCS link" between IRIS datasets raised AttributeError: 'has_celestial'
    sji, raster = sns
    sji_2796 = image_data(_real(irispy_test_files, SJI.replace("1400", "2796")))
    DataCollection([sji, raster, sji_2796]).add_link(WCSLink(sji, sji_2796))
    assert [sji[cid][3, 20, 10] for cid in sji_2796.pixel_component_ids[1:]] == pytest.approx([20, 10], abs=0.01)
    try:
        link = WCSLink(sji, raster)
    except IncompatibleWCS:  # glue-core 1.27.0: SJI and raster share only lon/lat, which link_hpc links
        return
    # glue-viz/glue#2595 links the SJI image axes to the raster's step and slit
    assert {cid.axis for cid in link.cids1} == {1, 2}
    assert {cid.axis for cid in link.cids2} == {0, 1}


def test_sji_high_level_api_round_trips(sns):
    sji, _ = sns
    pixel = (10, 10, 5)
    wcs = HighLevelWCSWrapper(sji.coords)
    objects = wcs.pixel_to_world(*pixel)
    values = sji.coords.pixel_to_world_values(*pixel)
    types = list(sji.coords.world_axis_physical_types)
    sky = next(o for o in objects if hasattr(o, "Tx"))
    assert sky.Tx.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lon")])
    assert sky.Ty.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lat")])
    assert wcs.world_to_pixel(*objects) == pytest.approx(pixel, abs=1e-4)
