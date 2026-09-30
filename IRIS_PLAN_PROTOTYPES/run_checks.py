"""Run source-worktree tests with isolated caches and explicit import paths."""
import os
from pathlib import Path
import sys
import tempfile

root = Path(tempfile.mkdtemp(prefix="glue-fix-checks-"))
for directory in ("mpl", "cache", "config", "sunpy"):
    (root / directory).mkdir()
paths, *args = sys.argv[1:]
os.environ.update(
    QT_QPA_PLATFORM="offscreen", MPLBACKEND="agg", MPLCONFIGDIR=str(root / "mpl"),
    XDG_CACHE_HOME=str(root / "cache"), XDG_CONFIG_HOME=str(root / "config"),
    SUNPY_CONFIGDIR=str(root / "sunpy"), PYTHONDONTWRITEBYTECODE="1",
    PYTHONPATH=paths + os.pathsep + os.environ.get("PYTHONPATH", ""),
)
sys.dont_write_bytecode = True
sys.path[:0] = paths.split(os.pathsep)

import glue
from glue import config

config.CFG_DIR = str(root)
config.settings._save_to_disk = False

import glue_qt
import pytest

print("IMPORTS", glue.__file__, glue_qt.__file__, flush=True)
raise SystemExit(pytest.main(["-q", "-o", "addopts=", "-p", "no:cacheprovider", *args]))
