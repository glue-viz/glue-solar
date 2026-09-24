import warnings; warnings.filterwarnings("ignore")
from collections import OrderedDict
import sunpy
from sunpy.net.dataretriever.client import QueryResponse
from sunpy.net.dataretriever.sources.goes import XRSClient
from sunpy.net.fido_factory import UnifiedResponse
from sunpy.time import parse_time
rows = [OrderedDict([("Start Time", parse_time("2021-09-05")), ("End Time", parse_time("2021-09-05T23:59:59")), ("Instrument", "XRS"),
                     ("Physobs", "irradiance"), ("Source", "GOES"), ("Provider", "NOAA"), ("Resolution", "avg1m"),
                     ("SatelliteNumber", sat), ("url", f"https://example.invalid/g{sat}.nc")]) for sat in ("16", "17")]
qr = QueryResponse(rows, client=XRSClient())
ur = UnifiedResponse(qr)
tbl = ur[0]
print("ur[0] type:", type(tbl).__name__, "len:", len(tbl), "cols:", tbl.colnames)
sub = tbl[tbl["SatelliteNumber"] == tbl["SatelliteNumber"][0]]
print("masked type:", type(sub).__name__, "len:", len(sub), "client kept:", type(sub.client).__name__, "sat:", list(sub["SatelliteNumber"]))
print("download_dir:", sunpy.config.get("downloads", "download_dir"))
print("empty UnifiedResponse len:", len(UnifiedResponse(QueryResponse([], client=XRSClient()))[0]))
