"""Startup import findings R22, R25, R26, R31: python -I imports.py release|main <check>."""
import os
import sys
import time

S = "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/df774a44-db13-4c72-b097-0d85fb986df9/scratchpad/upstream/glue-core"
if sys.argv[1] == "main":
    sys.path.insert(0, os.path.join(S, "glue-main"))
check = sys.argv[2]

if check == "R31":
    t = time.perf_counter()
    import glue.config  # noqa: F401
    print(f"R31 import glue.config: glue_qt imported: {'glue_qt' in sys.modules}; {time.perf_counter() - t:.2f} s")
    sys.exit()

sys.modules["glue_qt"] = None  # keep glue-qt's own imports out of the measurement
t = time.perf_counter()
if check == "R22":
    import glue.viewers.common.viewer  # noqa: F401
    print(f"R22 import glue.viewers.common.viewer: IPython imported: {'IPython' in sys.modules}; {time.perf_counter() - t:.2f} s")
elif check == "R25":
    import glue.plugins.wcs_autolinking.wcs_autolinking  # noqa: F401
    print(f"R25 import wcs_autolinking: scipy.optimize imported: {'scipy.optimize' in sys.modules}; {time.perf_counter() - t:.2f} s")
elif check == "R26":
    import glue.core.data  # noqa: F401
    print(f"R26 import glue.core.data: dask.array imported: {'dask.array' in sys.modules}; {time.perf_counter() - t:.2f} s")
elif check == "glue":
    import glue  # noqa: F401
    print(f"import glue without glue_qt: {time.perf_counter() - t:.2f} s")
