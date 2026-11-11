import sys, time, warnings, astropy
from astropy.io import fits
warnings.simplefilter("ignore"); p = sys.argv[1]
def t(fn):
    t0 = time.perf_counter(); fn(); return time.perf_counter() - t0
def plain():
    with fits.open(p) as h: h[0].data.sum(); h[1].data; h[2].data
def inmem():
    with fits.open(p, decompress_in_memory=True) as h: h[0].data.sum(); h[1].data; h[2].data
def header_only():
    fits.getheader(p)
print(f"astropy {astropy.__version__}: open+3 HDUs plain {t(plain):.2f} s, decompress_in_memory {t(inmem):.2f} s, getheader {t(header_only):.2f} s")
