import os, warnings; warnings.filterwarnings("ignore")
from sunpy.timeseries import TimeSeries
cached = [f"/Users/nabil/sunpy/data/sci_xrsf-l2-avg1m_g15_d2012100{d}_v2-2-1.nc" for d in (5, 6)]
print([os.path.exists(c) for c in cached])
ts = TimeSeries(cached, source="xrs", concatenate=True)
print("concat:", type(ts).__name__, ts.time.min().isot, ts.time.max().isot, len(ts.to_dataframe()))
tr = ts.truncate("2012-10-05T23:00", "2012-10-06T01:00"); df = tr.to_dataframe()
print("truncate across midnight ->", len(df), df.index[0], df.index[-1], "| observatory:", ts.observatory, "| units:", ts.units["xrsb"])
