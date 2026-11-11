"""wp10-l-big-stack-load: astropy.io.fits reads a ConfigItem (conf.strip_header_whitespace) at each card's value and
comment, through get_config, as irispy's SGMeta walks a raster file's primary header once per window.

Run: python -I fits_conf_reads.py RASTER_FILE
"""

import cProfile
import pstats
import sys
import time

import astropy
from astropy.io import fits
from astropy.io.fits import conf

header = fits.getheader(sys.argv[1])
print("astropy", astropy.__version__, "| cards:", len(header))


def walk():  # what a dict of the header, or a lookup of every key, costs
    return {card.keyword: (card.value, card.comment) for card in header.cards}


def best(f, n=50):
    t = time.perf_counter()
    for _ in range(n):
        f()
    return (time.perf_counter() - t) / n * 1e3


print(f"one walk of the header: {best(walk):.2f} ms; one conf.strip_header_whitespace read: "
      f"{best(lambda: conf.strip_header_whitespace, 20000) * 1e3:.1f} us")
profile = cProfile.Profile()
profile.runcall(lambda: [walk() for _ in range(20)])
stats = pstats.Stats(profile)
total = stats.total_tt
config = sum(tt for (path, _, name), (_, _, tt, _, _) in stats.stats.items() if "astropy/config" in path)
config_cum = max(ct for (path, _, name), (_, _, _, ct, _) in stats.stats.items()
                 if "astropy/config/configuration" in path and name == "__get__")
print(f"time inside ConfigItem.__get__ (cumulative): {config_cum / total:.0%} of the walk; own time in astropy/config:"
      f" {config / total:.0%}")
