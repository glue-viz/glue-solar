"""Run with the archived WP1 package and prototype directory on PYTHONPATH."""
import numpy as np
import pytest
from pathlib import Path

from astropy.wcs import WCS
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue_solar.sources.loaders.iris import _GlueWCS, link_hpc


def test_wp8_archived_ui_loads(qtbot):
    from glue_qt.utils import load_ui

    dialog = load_ui("wp8_loader.ui", None, directory=str(Path(__file__).parents[1]))
    qtbot.addWidget(dialog)
    assert dialog.filter.isClearButtonEnabled()
    assert dialog.stop_scan.text() == "Stop scan"
    assert not dialog.stop_scan.isEnabled()


def test_quicklook_uses_wp1_link_contract(monkeypatch):
    import wp4_common
    from glue_qt.app import GlueApplication

    def image(label):
        wcs = WCS(naxis=2)
        wcs.wcs.ctype = ["HPLN-TAN", "HPLT-TAN"]
        return Data(label=label, image=np.ones((3, 4)), coords=_GlueWCS(wcs))

    first, second = image("first"), image("second")
    app = GlueApplication(DataCollection([first, second]))
    assert wp4_common.link_hpc is link_hpc
    # Isolate viewer creation; the integration under test is real link creation.
    monkeypatch.setattr(app, "new_data_viewer", lambda *args, **kwargs: None)
    try:
        wp4_common.quicklook(app, [])
        assert len(app.data_collection.external_links) == 2
        assert link_hpc(app.data_collection) == []
    finally:
        app.close()


@pytest.mark.parametrize("module_name", ["wp6_fitting", "wp6_fitting_brief"])
def test_wp3_roundtrips_wp6_fitted_map(module_name):
    import importlib
    import wp3_impl  # noqa: F401  installs the proposed WP3 savers

    fit_module = importlib.import_module(module_name)
    wave = 1402 + np.arange(40) * .025
    values = 5 + 100 * np.exp(-.5 * ((wave - 1402.45) / .06) ** 2)
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = ["WAVE", "HPLT-TAN", "HPLN-TAN"]
    wcs.wcs.cunit = ["Angstrom", "arcsec", "arcsec"]
    wcs.wcs.crpix = [1, 1, 1]
    wcs.wcs.crval = [wave[0], 0, 0]
    wcs.wcs.cdelt = [.025, .33, .35]
    data = Data(label="source", flux=np.broadcast_to(values, (2, 3, 40)), coords=_GlueWCS(wcs))
    maps, _ = fit_module.gaussian_fit_data(data, scheduler="single-threaded")
    assert isinstance(maps.coords, _GlueWCS)
    expected = data.coords.pixel_to_world_values(0, 1, 1)[1:]
    np.testing.assert_allclose(maps.coords.pixel_to_world_values(1, 1), expected)

    restored = GlueUnSerializer.loads(GlueSerializer(maps).dumps()).object("__main__")
    for cid in maps.main_components:
        np.testing.assert_allclose(restored[cid.label], maps[cid])
        assert restored.get_component(cid.label).units == maps.get_component(cid).units
    assert restored.meta == maps.meta
    assert tuple(restored.coords.world_axis_units) == ("arcsec", "arcsec")
    np.testing.assert_allclose(restored.coords.pixel_to_world_values(1, 1), expected)
    np.testing.assert_allclose(restored.coords.world_to_pixel_values(*expected), (1, 1), atol=1e-7)
