import time
from pathlib import Path
from glue_solar.sources.loaders.scan import scan_directory
root = "/Users/nabil/DATA/IRIS"
t0 = time.perf_counter(); obs = scan_directory(root); dt = time.perf_counter() - t0
nfiles = sum(1 for p in Path(root).rglob("*") if p.is_file())
print(f"{len(obs)} observations {sum(o.nfiles for o in obs)} files {sum(len(o.archives) for o in obs)} archives {dt:.2f} s")
print(f"total files on disk {nfiles} {1e3*dt/nfiles:.1f} ms/file")
