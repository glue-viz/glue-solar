import platform
import pytest
from glue_qt.utils import app


def test_mac_bundle_name():
    # The macOS menu-bar title and the About/Hide/Quit labels come from the
    # main bundle's CFBundleName (Qt reads it in qt_mac_applicationName),
    # which get_qapp rewrites through pyobjc before creating the QApplication.
    if platform.system() != 'Darwin':
        pytest.skip('macOS only')
    NSBundle = pytest.importorskip('Foundation').NSBundle
    app.get_qapp()
    bundle = NSBundle.mainBundle()
    info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
    assert info['CFBundleName'] == 'glue'
