import dask.array as da, numpy as np
x = da.from_array(np.arange(60).reshape(3,4,5), chunks=2)
i, j = np.array([0,1,2]), np.array([1,2,3])
print("arrays only", x.vindex[i, j].shape)
try:
    print("slice+arrays", x.vindex[slice(None), i, j].shape)
except Exception as e: print("slice+arrays", type(e).__name__, e)
try:
    print("int+arrays", x.vindex[0, i, j].shape)
except Exception as e: print("int+arrays", type(e).__name__, e)
try:
    print("plain", x[i, j].shape)
except Exception as e: print("plain", type(e).__name__, str(e)[:60])
