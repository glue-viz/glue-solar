"""Line positions must agree on numeric and WCSAxes profile axes."""
import numpy as np
import pytest
from astropy.wcs import WCS
from glue.core import Data, DataCollection
from glue_qt.app import GlueApplication
from glue_qt.viewers.profile import ProfileViewer
from wp5_linelist_mod import LineListArtist


@pytest.mark.parametrize('cdelt', [0.1, -0.1])
def test_lines_follow_units_and_wcs_slice(qtbot, cdelt):
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ['WAVE', 'LINEAR']
    wcs.wcs.cunit = ['Angstrom', '']
    wcs.wcs.crval = [1400, 0]
    wcs.wcs.crpix = [1, 1]
    wcs.wcs.cdelt = [cdelt, 1]
    wcs.wcs.pc = [[1, 0.5], [0, 1]]
    data = Data(flux=np.ones((3, 100)), coords=wcs)
    lines = Data(wavelength=[1400 + 5 * cdelt], name=['test line'])
    app = GlueApplication(DataCollection([data, lines])); qtbot.addWidget(app)
    viewer = app.new_data_viewer(ProfileViewer, data=data)
    viewer.state.x_att = data.world_component_ids[-1]
    viewer.add_data(lines)
    artist = next(layer for layer in viewer.layers if isinstance(layer, LineListArtist))
    def position():
        return artist.mpl_artists[0].get_xdata()[0]
    active = getattr(viewer.state, 'wcsaxes_active', False)
    expected = 5 if active else (1400 + 5 * cdelt) * 1e-10
    assert position() == pytest.approx(expected)
    if active:
        viewer.state.function = 'slice'
        viewer.state.slices = (2, 0)
        assert position() == pytest.approx(4)
    viewer.state.x_display_unit = 'Angstrom'
    assert position() == pytest.approx(1400 + 5 * cdelt)
    viewer.close(warn=False)


def test_line_session_preserves_position_and_unit(qtbot, tmp_path):
    wcs = WCS(naxis=1)
    wcs.wcs.ctype = ['WAVE']; wcs.wcs.cunit = ['Angstrom']
    wcs.wcs.crval = [1400]; wcs.wcs.crpix = [1]; wcs.wcs.cdelt = [0.1]
    data = Data(flux=np.ones(20), coords=wcs)
    lines = Data(wavelength=[1400.5], name=['test line'])
    app = GlueApplication(DataCollection([data, lines])); qtbot.addWidget(app)
    viewer = app.new_data_viewer(ProfileViewer, data=data)
    viewer.state.x_att = data.world_component_ids[0]
    viewer.add_data(lines)
    viewer.state.x_display_unit = 'Angstrom'
    path = tmp_path / 'lines.glu'
    app.save_session(str(path), include_data=True)
    restored = GlueApplication.restore_session(str(path)); qtbot.addWidget(restored)
    second = restored.viewers[0][0]
    artist = next(layer for layer in second.layers if isinstance(layer, LineListArtist))
    assert second.state.x_display_unit == 'Angstrom'
    assert artist.mpl_artists[0].get_xdata()[0] == pytest.approx(1400.5)
    # Back to the native unit after reopening exercises the 1D WCSAxes path too.
    second.state.x_display_unit = 'm'
    expected = 5 if getattr(second.state, 'wcsaxes_active', False) else 1400.5e-10
    assert artist.mpl_artists[0].get_xdata()[0] == pytest.approx(expected)
    second.close(warn=False); viewer.close(warn=False)
