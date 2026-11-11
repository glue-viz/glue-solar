import sys, time
t0 = time.perf_counter(); import pytest; t1 = time.perf_counter()
print(f"import pytest alone: {1e3*(t1-t0):.0f} ms")
