import gzip, io, sys, time, warnings, numpy as np
warnings.simplefilter("ignore")
from irispy.io.sji import read_sji_lvl2
path = sys.argv[1]
t0 = time.perf_counter(); cube = read_sji_lvl2(path, memmap=True, uncertainty=False); t1 = time.perf_counter()
print(f"irispy read_sji_lvl2(path.gz, memmap=True): {t1-t0:.2f} s, data type {type(cube.data).__name__} dtype {cube.data.dtype} shape {cube.data.shape}")
t0 = time.perf_counter(); content = gzip.open(path).read(); cube2 = read_sji_lvl2(content, memmap=True, uncertainty=False); t1 = time.perf_counter()
print(f"glue-solar's bytes path: {t1-t0:.2f} s, data type {type(cube2.data).__name__} dtype {cube2.data.dtype}; equal: {np.array_equal(np.asarray(cube.data[0]), np.asarray(cube2.data[0]), equal_nan=True)}")
