import warnings, os; warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM","offscreen"); os.environ.setdefault("MPLBACKEND","agg")
from irispy.data.test import get_test_data_filenames
from irispy.io import read_files
from glue.core import Data, DataCollection
from glue.core.state import GlueSerializer
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink
from astropy.wcs.wcsapi import BaseHighLevelWCS, BaseLowLevelWCS
from glue_solar.sources.loaders.iris import iris_data, _cube_data, _GlueWCS
files = [str(f) for f in get_test_data_filenames()]
sji_f = [f for f in files if "3620258102_SJI_1400" in f][0]; ras_f = [f for f in files if "3620258102_raster" in f][0]
def fresh_sji(): return iris_data(sji_f)
def fresh_ras(): return [d for d in iris_data(ras_f) if d.label.startswith("Mg_II_k")][0]
s = fresh_sji(); print("_GlueWCS isinstance High:", isinstance(s.coords, BaseHighLevelWCS), "Low:", isinstance(s.coords, BaseLowLevelWCS), "mro:", [c.__name__ for c in type(s.coords).__mro__][:4])
for name, mk in (("sji", fresh_sji), ("raster", fresh_ras)):
    d = mk()
    try: GlueSerializer(DataCollection([d])).dumps(); print("serialize", name, "OK")
    except Exception as e: print("serialize", name, "FAIL", type(e).__name__, str(e)[:160].replace("\n"," "))
rc = read_files(ras_f, memmap=False, uncertainty=False)["Mg II k 2796"][0]
d = _cube_data(rc, "r"); d.meta = {k:v for k,v in dict(rc.meta).items() if not hasattr(v,'unit')}
try: GlueSerializer(DataCollection([d])).dumps(); print("raster w/o Quantity meta OK")
except Exception as e: print("raster w/o Quantity meta FAIL", type(e).__name__, str(e)[:100])
d = _cube_data(rc, "r"); d.meta = {k:v for k,v in dict(rc.meta).items() if not hasattr(v,'unit')}; d.coords = rc.wcs
try: GlueSerializer(DataCollection([d])).dumps(); print("raster raw astropy -TAB WCS, clean meta: OK")
except Exception as e: print("raster raw astropy -TAB WCS, clean meta FAIL", type(e).__name__, str(e)[:100])
sc = read_files(sji_f, memmap=False, uncertainty=False)
for order in ("sji,ras", "ras,sji"):
    a = Data(label="a"); a.coords = sc.wcs; a.add_component(sc.data, "v")
    b = Data(label="b"); b.coords = rc.wcs; b.add_component(rc.data, "v")
    pair = [a,b] if order=="sji,ras" else [b,a]
    try: print("raw autolink", order, "links:", len(wcs_autolink(DataCollection(pair))))
    except Exception as e: print("raw autolink", order, "RAISED", type(e).__name__, str(e)[:100])
import astropy.modeling.fitting as f; print("parallel_fit_dask:", hasattr(f, "parallel_fit_dask"))
