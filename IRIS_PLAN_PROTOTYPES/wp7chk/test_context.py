import types

import numpy as np
import parfive
import pytest
from glue.config import menubar_plugin
from glue.core import Data, DataCollection
from irispy.io import read_files

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable

import sunpy.data.test
import sunpy.map
from sunpy.coordinates import Helioprojective
from sunpy.map.header_helper import make_fitswcs_header

import context_chk as context
from context_chk import aia_context, fov_polygon, goes_xrs
from glue_solar.sources.loaders.iris import _GlueWCS, image_data, link_hpc, raster_data

SJI = "iris_l2_20210905_001833_3620258102_SJI_1400_t000.fits"
RASTER = "sns/iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits"


def _results(*paths):
    results = parfive.Results()
    for path in paths:
        results.append(path=str(path), url=f"file://{path}")
    return results


def _sji(files):
    return image_data(str(next(f for f in files if f.name == SJI)))


def _synthetic_aia(sji, path):
    """An 800x800 AIA 171 map centred on the SJI field of view at STARTOBS, saved to ``path``."""
    lon, lat = fov_polygon(sji)
    frame = Helioprojective(obstime=str(sji.meta["STARTOBS"]), observer="earth")
    ref = SkyCoord(lon.mean() * u.arcsec, lat.mean() * u.arcsec, frame=frame)
    hdr = make_fitswcs_header(
        np.zeros((800, 800)), ref, scale=[0.6, 0.6] * u.arcsec / u.pix, instrument="AIA", telescope="SDO/AIA",
        observatory="SDO", wavelength=171 * u.AA, exposure=2 * u.s,
    )
    sunpy.map.Map(np.random.default_rng(0).random((800, 800)), hdr).save(path)
    return types.SimpleNamespace(search=lambda *a: None, fetch=lambda *a, **k: _results(path))


def test_setup_registers_context_actions():
    labels = [label for label, _ in menubar_plugin]
    assert "IRIS: GOES context…" in labels
    assert "IRIS: SDO context…" in labels


def test_goes_xrs_reads_one_satellite(monkeypatch):
    fetched = []

    def fetch(table, progress):
        fetched.append(table)
        return _results(sunpy.data.test.get_test_filepath("sci_xrsf-l2-avg1m_g16_d20210101_truncated.nc"))

    monkeypatch.setattr(
        context, "Fido", types.SimpleNamespace(search=lambda *a: [QTable({"SatelliteNumber": ["16", "17"]})], fetch=fetch)
    )
    data = goes_xrs("2021-01-01T22:30:00", "2021-01-01T23:10:00")
    assert len(fetched) == 1
    assert len(fetched[0]) == 1
    assert fetched[0]["SatelliteNumber"][0] == "16"
    assert data.label == "GOES-16 XRS"
    assert data.shape == (41,)
    assert [str(c) for c in data.main_components] == ["xrsa", "xrsb", "time"]
    assert data.get_kind(data.id["time"]) == "datetime"
    assert data.get_component(data.id["xrsb"]).units == "W / m2"
    assert data["time"][0] == np.datetime64("2021-01-01T22:30:00")
    assert data["time"][-1] == np.datetime64("2021-01-01T23:10:00")


def test_goes_xrs_without_data_raises(monkeypatch):
    called = []
    monkeypatch.setattr(
        context,
        "Fido",
        types.SimpleNamespace(search=lambda *a: [QTable({"SatelliteNumber": []})], fetch=lambda *a, **k: called.append(a)),
    )
    with pytest.raises(ValueError, match="No GOES XRS data"):
        goes_xrs("2021-01-01T22:30:00", "2021-01-01T23:10:00")
    assert not called


def test_fov_polygon_sji_first_exposure(irispy_test_files):
    path = next(f for f in irispy_test_files if f.name == SJI)
    lon, lat = fov_polygon(image_data(str(path)))
    m0 = read_files(path, memmap=False, uncertainty=False).to_maps(0)
    ny, nx = m0.data.shape
    expected = m0.wcs.pixel_to_world([0, nx - 1, nx - 1, 0], [0, 0, ny - 1, ny - 1])
    np.testing.assert_allclose(lon, expected.Tx.to_value(u.arcsec), atol=0.2)
    np.testing.assert_allclose(lat, expected.Ty.to_value(u.arcsec), atol=0.2)
    assert lon.max() < -50


def test_fov_polygon_raster_uses_slit_and_step(irispy_test_files):
    path = next(f for f in irispy_test_files if str(f).endswith(RASTER))
    data = raster_data([str(path)], ["Mg II k 2796"])[0]
    lon, lat = fov_polygon(data)
    assert np.ptp(lon) == pytest.approx(42.3, abs=0.5)
    assert np.ptp(lat) == pytest.approx(6.9, abs=0.5)
    assert len(set(zip(lon.round(2), lat.round(2)))) == 4


def test_fov_polygon_stack_uses_slit_and_step(irispy_test_files):
    paths = sorted(str(f) for f in irispy_test_files if "3860258481_raster_t000_r0000" in f.name)[:2]
    data = raster_data(paths, ["C II 1336"], stack=True)[0]
    assert data.shape == (2, 8, 109, 17)
    lon, lat = fov_polygon(data)
    assert np.ptp(lon) == pytest.approx(14.3, abs=0.5)
    assert np.ptp(lat) == pytest.approx(18.0, abs=0.5)


def test_fov_polygon_rejects_non_spatial_data():
    with pytest.raises(ValueError, match="no helioprojective coordinates"):
        fov_polygon(Data(x=np.zeros((3, 3))))


def test_aia_context_from_local_map(monkeypatch, tmp_path, irispy_test_files):
    sji = _sji(irispy_test_files)
    monkeypatch.setattr(context, "Fido", _synthetic_aia(sji, tmp_path / "aia.fits"))
    ctx, fov = aia_context(sji)
    assert isinstance(ctx.coords, _GlueWCS)
    assert [ctx.get_component(c).units for c in ctx.world_component_ids] == ["arcsec", "arcsec"]
    assert ctx.style.preferred_cmap.name == "sdoaia171"
    assert ctx.shape == (346, 344)
    assert ctx.label.startswith("AIA_171_context-3620258102-2021-09-05T00:18:33")
    dc = DataCollection([ctx, sji])
    dc.new_subset_group("FOV", fov)
    assert 80 <= ctx.subsets[0].to_mask().sum() <= 130
    dc.add_link(link_hpc(dc))
    mask = sji.subsets[0].to_mask()
    assert mask[0].sum() > 1300
    assert mask[-1].sum() == 0


def test_goes_context_shows_message_on_failure(monkeypatch, irispy_test_files):
    from glue_qt.app import GlueApplication
    from qtpy import QtWidgets

    sji = _sji(irispy_test_files)
    app = GlueApplication(DataCollection([sji]))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", staticmethod(lambda *a, **k: (sji.label, True)))

    def boom(*args):
        raise OSError("boom")

    monkeypatch.setattr(context, "goes_xrs", boom)
    shown = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", staticmethod(lambda parent, title, text: shown.append(text)))
    context.goes_context(app.session, app.data_collection)
    assert shown
    assert "boom" in shown[0]
    assert len(app.data_collection) == 1
    app.close()


def test_sdo_context_end_to_end(monkeypatch, tmp_path, irispy_test_files):
    """The full menubar action offscreen: dataset picker stubbed, Fido stubbed, viewer opened, FOV subset drawn."""
    from glue_qt.app import GlueApplication
    from qtpy import QtWidgets

    sji = _sji(irispy_test_files)
    monkeypatch.setattr(context, "Fido", _synthetic_aia(sji, tmp_path / "aia.fits"))
    app = GlueApplication(DataCollection([sji]))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getItem", staticmethod(lambda *a, **k: (sji.label, True)))
    context.sdo_context(app.session, app.data_collection)
    assert len(app.data_collection) == 2
    assert [sg.label for sg in app.data_collection.subset_groups] == ["IRIS FOV"]
    assert len(app.data_collection.links) >= 2
    viewer = app.viewers[0][-1]
    viewer.figure.canvas.draw()
    assert [type(layer).__name__ for layer in viewer.layers] == ["ImageLayerArtist", "ImageSubsetLayerArtist"]
    app.close()
