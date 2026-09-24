import shutil

import numpy as np
import pytest
from glue.core import Data, DataCollection
from glue.core.exceptions import IncompatibleAttribute
from glue.core.link_helpers import LinkSame
from glue.core.roi import RectangularROI
from glue.core.subset import RoiSubsetState
from qtpy import QtWidgets
from qtpy.QtCore import Qt

import astropy.units as u
from astropy.wcs import WCS
from astropy.wcs.wcsapi import HighLevelWCSWrapper

from glue_solar.sources.iris import browse_iris
from glue_solar.sources.loaders.iris import QtIRISImporter, _GlueWCS, _cube_data, image_data, link_hpc, raster_data

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"
HPC = ["Helioprojective Longitude", "Helioprojective Latitude"]
def supports_wrapped_wcs_autolink():
    from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink

    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]
    datasets = [Data(coords=_GlueWCS(wcs), flux=np.zeros((2, 2))) for _ in range(2)]
    return bool(wcs_autolink(DataCollection(datasets)))


AUTOLINKS_IRIS = supports_wrapped_wcs_autolink()


def _real(files, name):
    return next(path for path in files if path.name == name and path.parent.name == "sns")


def _cid(data, label):
    return next(cid for cid in data.world_component_ids if cid.label == label)


@pytest.fixture
def sns(irispy_test_files):
    """The matched sit-and-stare SJI 1400 + Si IV 1403 raster pair shipped with irispy."""
    [raster] = raster_data([_real(irispy_test_files, RASTER)], ["Si IV 1403"])
    return image_data(_real(irispy_test_files, SJI)), raster


def test_wavelength_axis_is_in_angstrom(sns):
    _, raster = sns
    assert raster.coords.world_axis_units == ("Angstrom", "arcsec", "arcsec")
    wavelength = _cid(raster, "Wavelength")
    assert raster.get_component(wavelength).units == "Angstrom"
    assert 1380 < np.nanmin(raster[wavelength]) < np.nanmax(raster[wavelength]) < 1420
    world = raster.coords.pixel_to_world_values(3, 20, 50)
    assert world[0] == pytest.approx(raster.coords._wcs.pixel_to_world_values(3, 20, 50)[0] * 1e10)
    assert raster.coords.world_to_pixel_values(*world) == pytest.approx((3, 20, 50), abs=1e-4)  # float32 -TAB


def test_sji_and_raster_share_axis_names(sns):
    sji, raster = sns
    assert [c.label for c in sji.world_component_ids] == ["Time (Utc)", *HPC[::-1]]
    assert [c.label for c in raster.world_component_ids] == [*HPC, "Wavelength"]


@pytest.mark.parametrize(("which", "pixel"), [("sji", (10, 10, 5)), ("raster", (3, 20, 50))])
def test_high_level_api_round_trips_in_display_units(sns, which, pixel):
    data = sns[which == "raster"]
    wcs = HighLevelWCSWrapper(data.coords)
    objects = wcs.pixel_to_world(*pixel)
    values = data.coords.pixel_to_world_values(*pixel)
    types = list(data.coords.world_axis_physical_types)
    sky = next(o for o in objects if hasattr(o, "Tx"))
    assert sky.Tx.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lon")])
    assert sky.Ty.to_value(u.arcsec) == pytest.approx(values[types.index("custom:pos.helioprojective.lat")])
    if which == "raster":
        assert objects[0].to_value(u.AA) == pytest.approx(values[0])
    assert wcs.world_to_pixel(*objects) == pytest.approx(pixel, abs=1e-4)


def test_link_hpc_pairs_lon_lat_by_physical_type(sns):
    sji, raster = sns
    dc = DataCollection([sji, raster])
    links = link_hpc(dc)
    assert len(links) == 2
    assert all(isinstance(link, LinkSame) for link in links)
    dc.add_link(links)
    assert link_hpc(dc) == []  # idempotent
    for label in HPC:
        np.testing.assert_allclose(raster[_cid(sji, label)], raster[_cid(raster, label)])
    # propagated: subsets drawn on the raster map, and subsets on world coordinates
    raster_roi = RoiSubsetState(
        xatt=raster.pixel_component_ids[0], yatt=raster.pixel_component_ids[1], roi=RectangularROI(40, 120, 10, 30)
    )
    assert 0 < sji.get_mask(raster_roi).sum() < sji.size
    lon = _cid(sji, HPC[0])
    assert 0 < raster.get_mask(lon > float(np.nanmedian(sji[lon]))).sum() < raster.size
    # not propagated: a subset drawn on the SJI image needs the SJI exposure time, which the raster cannot supply
    sji_roi = RoiSubsetState(
        xatt=sji.pixel_component_ids[2], yatt=sji.pixel_component_ids[1], roi=RectangularROI(10, 25, 10, 30)
    )
    with pytest.raises(IncompatibleAttribute):
        raster.get_mask(sji_roi)


def test_link_hpc_chains_every_dataset_through_the_first(sns, irispy_test_files):
    sji, raster = sns
    [other] = raster_data([_real(irispy_test_files, RASTER)], ["C II 1336"])
    dc = DataCollection([sji, raster, other])
    dc.add_link(link_hpc(dc))
    assert len(dc.external_links) == 4
    np.testing.assert_allclose(other[_cid(raster, HPC[1])], other[_cid(other, HPC[1])])


def test_world_links_into_the_sji_use_each_exposure_time(sns):
    """glue-core 1.27 inverts a time-dependent gWCS at exposure 0; glue_solar.glue_patches keeps the time."""
    sji, _ = sns
    frames = np.arange(sji.shape[0], dtype=float)
    lon, lat, time = sji.coords.pixel_to_world_values(10.0, 10.0, frames)
    points = Data(label="points", lon=lon, lat=lat, t=time)
    dc = DataCollection([sji, points])
    dc.add_link([LinkSame(points.id[k], _cid(sji, label)) for k, label in zip("lon lat t".split(), [*HPC, "Time (Utc)"])])
    np.testing.assert_allclose(points[sji.pixel_component_ids[2]], 10, atol=1e-6)
    np.testing.assert_allclose(points[sji.pixel_component_ids[1]], 10, atol=1e-6)


def test_link_hpc_leaves_datasets_in_other_units_alone(sns):
    import sunpy.data.test
    import sunpy.map

    from glue_solar.sources.maps import _parse_sunpy_map

    aia = _parse_sunpy_map(sunpy.map.Map(sunpy.data.test.get_test_filepath("aia_171_level1.fits")), "aia")
    assert set(aia.coords.world_axis_units) == {"deg"}
    assert len(link_hpc(DataCollection([*sns, aia]))) == 2


def test_wcs_autolink_does_not_crash_on_iris_data(sns):
    from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink

    assert len(wcs_autolink(DataCollection(list(sns)))) <= 1  # 0 on glue-core 1.27.0, 1 with the APE-14 autolinker


@pytest.mark.skipif(not AUTOLINKS_IRIS, reason="needs the APE-14 WCS autolinker (glue-viz/glue ape14-wcs-autolink)")
def test_wcs_autolink_pairs_iris_datasets(sns, irispy_test_files):
    from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, wcs_autolink
    from irispy.io import read_files
    from irispy.utils.moments import calculate_moments

    sji, raster = sns
    [link] = wcs_autolink(DataCollection([sji, raster]))
    assert isinstance(link, WCSLink)
    assert [c.label for c in link.cids1] == ["Pixel Axis 2 [x]", "Pixel Axis 1 [y]"]  # SJI x, y
    assert [c.label for c in link.cids2] == ["Pixel Axis 1 [y]", "Pixel Axis 0 [z]"]  # raster slit, step
    paths = sorted(p for p in irispy_test_files if "3860258481_raster_t000_r0000" in p.name)[:2]
    scan0, scan1 = raster_data(paths, ["Mg II k 2796"])
    assert len(wcs_autolink(DataCollection([scan0, scan1]))) == 1
    cube = read_files(paths[:1], spectral_windows=["Mg II k 2796"], memmap=False, uncertainty=False)["Mg II k 2796"][0]
    velocity = _cube_data(calculate_moments(cube)["velocity"], "velocity")
    [scan0] = raster_data(paths[:1], ["Mg II k 2796"])  # a Data belongs to one DataCollection
    assert len(wcs_autolink(DataCollection([scan0, velocity]))) == 1


def test_browse_iris_links_what_it_loads(qtbot, tmp_path, irispy_test_files, monkeypatch):
    from glue_qt.app import GlueApplication

    for name in (SJI, RASTER):
        shutil.copy2(_real(irispy_test_files, name), tmp_path / name)
    monkeypatch.setattr(QtWidgets.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    # glue-qt pops a modal autolink dialog when glue suggests links (the APE-14 fork does); this test is about link_hpc
    monkeypatch.setattr("glue_qt.app.application.run_autolinker", lambda data_collection: None)

    def tick_everything_and_load(dialog):
        dialog.obs_tree.topLevelItem(0).setCheckState(0, Qt.Checked)
        dialog.finalize()
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(QtIRISImporter, "exec", tick_everything_and_load)
    app = GlueApplication()
    browse_iris(app.session, app.data_collection)
    dc = app.data_collection
    assert len(dc) > 2  # the SJI and every raster window
    assert all(isinstance(link, LinkSame) for link in dc.external_links)
    assert len(dc.external_links) == 2 * (len(dc) - 1)
    viewer = app.viewers[0][0]
    viewer.figure.canvas.draw()
    assert viewer.axes.format_coord(18, 20).endswith("(world)")  # the patched inverse leaves WCSAxes readouts intact
    app.close()
