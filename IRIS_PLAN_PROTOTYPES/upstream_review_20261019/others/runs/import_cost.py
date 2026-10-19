import sys, time
t0 = time.perf_counter(); import astropy.visualization.wcsaxes; t1 = time.perf_counter()
print(f"import astropy.visualization.wcsaxes: {1e3*(t1-t0):.0f} ms; pytest imported: {'pytest' in sys.modules}")
