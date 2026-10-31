"""Run source-worktree tests with isolated caches and explicit import paths."""
import atexit
import os
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(tempfile.mkdtemp(prefix="glue-fix-checks-"))
atexit.register(shutil.rmtree, root, ignore_errors=True)
for directory in ("home", "mpl", "cache", "config", "sunpy"):
    (root / directory).mkdir()
# two caches kept between runs: astropy's, so its IERS tables download about monthly, not each run (a DNS failure of
# datacenter.iers.org failed test_quicklook_opens_each_kind), and pooch's, so the remote-data files (about 1 GB,
# hash-checked by pooch on each use) download once; both under XDG_CACHE_HOME, which platformdirs honors on macOS too
caches = "Library/Caches" if sys.platform == "darwin" else ".cache"
kept = Path(os.path.expanduser("~")) / caches / "glue-solar-checks"
for name in ("astropy", "pooch"):
    (kept / name).mkdir(parents=True, exist_ok=True)
    (root / "cache" / name).symlink_to(kept / name)
paths, *args = sys.argv[1:]
tree = Path(paths.split(os.pathsep)[0])
if (tree / "pyproject.toml").exists() and not (tree / "glue_solar" / "version.py").exists():  # a fresh worktree's
    import subprocess

    subprocess.run([sys.executable, "-m", "setuptools_scm", "--root", tree, "--config", tree / "pyproject.toml",
                    "--force-write-version-files"], check=True, capture_output=True)
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
# glue-core 1.28 registers a pytest plugin (glue#2587), and glue is imported above: pytest warns it cannot rewrite it,
# which pytest.ini's filterwarnings = error makes fatal
raise SystemExit(pytest.main(["-q", "-o", "addopts=", "-p", "no:cacheprovider",
                              "-W", "ignore::pytest.PytestAssertRewriteWarning", *args]))
