"""pytest plugin: redirect two-string QSettings(org, app) to an INI file in a temp dir."""
import os
import sys
import tempfile

from qtpy import QtCore

_ORIG = QtCore.QSettings
_DIR = tempfile.mkdtemp(prefix="qs-isolate-")


class IsolatedQSettings(_ORIG):
    def __init__(self, *args, **kwargs):
        if len(args) == 2 and all(isinstance(a, str) for a in args) and not kwargs:
            super().__init__(os.path.join(_DIR, f"{args[0]}-{args[1]}.ini"), _ORIG.IniFormat)
        else:
            super().__init__(*args, **kwargs)


def _patch():
    QtCore.QSettings = IsolatedQSettings
    for mod in list(sys.modules.values()):
        if getattr(mod, "QSettings", None) is _ORIG:
            mod.QSettings = IsolatedQSettings


_patch()


def pytest_configure(config):
    _patch()


def pytest_collection_finish(session):
    _patch()
