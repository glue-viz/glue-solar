import os, sys, glob, json, shutil, warnings
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("MPLBACKEND", "agg"); warnings.simplefilter("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import wp3_impl
from irispy.data.test import get_test_data_filenames
from glue.core import DataCollection
from glue.core.data_factories import load_data
from glue.core.state import GlueSerializer, GlueUnSerializer
from glue_solar.sources.iris import read_iris_file
files = [str(f) for f in get_test_data_filenames()]
sji = [f for f in files if "sns/" in f and "SJI_1330" in f][0]
rdir = os.path.dirname([f for f in files if "3860258481_raster_t000_r00000" in f][0]); rfiles = sorted(glob.glob(rdir + "/*.fits"))[:3]
root = os.path.join(HERE, "wp3_sess"); shutil.rmtree(root, ignore_errors=True); os.makedirs(os.path.join(root, "a", "data"))
for f in [sji, *rfiles]: shutil.copy2(f, os.path.join(root, "a", "data", os.path.basename(f)))
os.chdir(os.path.join(root, "a"))  # glue's save_session/restore_session chdir to the session folder
names = [os.path.basename(f) for f in rfiles]
loaded = {
    "SJI via read_iris_file": load_data("data/" + os.path.basename(sji), factory=read_iris_file),
    "raster file, all 9 windows": load_data("data/" + names[0], factory=wp3_impl.read_iris_rasters),
    "3 scans of C II 1336, stacked": load_data("data/" + names[0], factory=wp3_impl.read_iris_rasters, files=names, windows=["C II 1336"], stack=True),
    "3 scans of C II 1336, separate": load_data("data/" + names[0], factory=wp3_impl.read_iris_rasters, files=names, windows=["C II 1336"]),
}
saved = {}
for n, (label, ds) in enumerate(loaded.items()):
    ds = ds if isinstance(ds, list) else [ds]
    assert all(hasattr(d, "_load_log") for d in ds)
    dc = DataCollection(ds)
    small = GlueSerializer(dc, include_data=False, absolute_paths=False).dumps()
    big = GlueSerializer(dc, include_data=True).dumps()
    by_type = {}
    for v in json.loads(small).values():
        if isinstance(v, dict): by_type[v.get("_type", "?").split(".")[-1]] = by_type.get(v.get("_type", "?").split(".")[-1], 0) + len(json.dumps(v))
    log = [v for v in json.loads(small).values() if isinstance(v, dict) and v.get("_type", "").endswith("LoadLog")][0]
    print(f"{label}: {len(ds)} dataset(s) | relative-paths session {len(small) // 1024} KB (data embedded: {len(big) // 1024} KB) | biggest records {sorted(by_type.items(), key=lambda kv: -kv[1])[:2]}")
    print("   LoadLog record:", {k: v for k, v in log.items() if k in ("path", "kwargs", "factory")})
    with open(f"s{n}.glu", "w") as fh: fh.write(small)
    saved[label] = (ds, f"s{n}.glu")
print("-- relocate data + sessions to another folder and reload there --")
shutil.copytree(os.path.join(root, "a"), os.path.join(root, "b")); shutil.rmtree(os.path.join(root, "a")); os.chdir(os.path.join(root, "b"))
for label, (ds, fn) in saved.items():
    dc2 = GlueUnSerializer.loads(open(fn).read()).object("__main__")
    d, d2 = ds[0], dc2[0]
    grid = np.meshgrid(*[np.arange(n) for n in d.shape[::-1]], indexing="ij")
    diff = max(float(np.nanmax(np.abs(x - y))) for x, y in zip(d.coords.pixel_to_world_values(*grid), d2.coords.pixel_to_world_values(*grid)))
    same = all(np.array_equal(d2[d2.id[c.label]], d[c], equal_nan=d[c].dtype.kind == "f") for c in d.main_components)
    print(f"{label}: reloaded {len(dc2)} dataset(s) from {fn} | shape {d2.shape} | coords {type(d2.coords._wcs).__name__} | p2w maxdiff {diff:.1e} | components identical {same} | labels {[x.label for x in dc2][:2]}")
print("LOADLOG OK")
