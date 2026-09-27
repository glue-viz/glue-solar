"""Load time, peak RSS and lambda-t slice cost: irispy read_files memmap=False (glue-solar today) vs memmap=True. argv: memmap(0/1) path window"""
import resource, sys, time, warnings
sys.path.insert(0, "<session-scratch>/tools")
import qs_isolate  # noqa
import numpy as np
warnings.simplefilter("ignore")
from irispy.io import read_files
mm, path, win = bool(int(sys.argv[1])), sys.argv[2], sys.argv[3]
rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
t = time.perf_counter()
cube = read_files(path, spectral_windows=[win], memmap=mm, uncertainty=False)[win][0]
tl = time.perf_counter() - t
data = cube.data
print(f"memmap={mm} {win} shape {data.shape} {data.dtype} type {type(data).__name__} base-memmap {isinstance(getattr(data, 'base', None), np.memmap) or isinstance(data, np.memmap)} load {tl:.2f}s", flush=True)
rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
t = time.perf_counter(); lt = np.asarray(data[:, data.shape[1] // 2, :]).sum(); tlt = time.perf_counter() - t
t = time.perf_counter(); sp = np.asarray(data[data.shape[0] // 2]).sum(); tsp = time.perf_counter() - t
t = time.perf_counter(); allsum = np.nansum(np.asarray(data, dtype=np.float32)); tall = time.perf_counter() - t
rss2 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
print(f"  lambda-t slice {tlt*1e3:.1f} ms, spectrogram slice {tsp*1e3:.1f} ms, full pass {tall:.2f}s; peak RSS MB: start {rss0:.0f} after load {rss1:.0f} after full pass {rss2:.0f}; array {data.nbytes/2**20:.0f} MB; mask {None if cube.mask is None else getattr(cube.mask, 'dtype', type(cube.mask))}")
