"""Run source-worktree tests with isolated caches and explicit import paths."""
import atexit
import os
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(tempfile.mkdtemp(prefix="glue-fix-checks-"))
atexit.register(shutil.rmtree, root, ignore_errors=True)  # its sunpy downloads are about 350 MB a run
for directory in ("home", "mpl", "cache", "config", "sunpy"):
    (root / directory).mkdir()
paths, *args = sys.argv[1:]
os.environ.update(
    HOME=str(root / "home"), QT_QPA_PLATFORM="offscreen", MPLBACKEND="agg", MPLCONFIGDIR=str(root / "mpl"),
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
