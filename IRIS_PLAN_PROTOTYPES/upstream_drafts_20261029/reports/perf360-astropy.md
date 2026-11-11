# astropy.io.fits: a ConfigItem read for every card (perf360 c4)

- **Where:** a PR on astropy/astropy (io.fits), referencing the open issue #12504 ("ConfigNamespace
  is slow", embray, 2021; it names io.fits header parsing). The fix is a few lines in `card.py`
  and safe: the same config is read wherever it can change the result, so behavior does not change. Prior work: #17461
  cached values on the ConfigItem and was reverted in #18144, as it broke `reload_config` (#18138); mhvk then
  suggested a cache that a reload clears. Open: #20471 (experimental, a ContextVar for `set_temp`) and #16476
  (traitlets). This PR touches neither; `ConfigItem.__get__` stays slow, so it says "Ref", not "Fixes". If you prefer
  not to open a PR, the numbers fit as a comment on #12504.
- **Why not a snapshot per header parse:** `test_header_strip_whitespace` (`io/fits/tests/test_header.py:2369`)
  builds a header, then reads it inside `conf.set_temp("strip_header_whitespace", False)` and expects unstripped
  values. A value read must therefore still see the config at that moment. The snapshot (`patches360.fits_conf`) is
  measured below only as the ceiling.
- **Review row:** perf360 REPORT (c) c4.
- **Reproducer:** `scripts/perf360_astropy.py` (synthetic 412-card header with an IRIS primary header's value types:
  211 float, 138 int, 61 str, 2 bool); output `out/perf360_astropy_rel.txt`; peak 61 MB. Release: astropy 8.0.2 in
  iris-plan-latest-1028, `python -I -B`, 24G cap.
- **Tests with the prototype:** `scripts/perf360_astropy_plugin.py` applies the two changes;
  `pytest -n 4 --pyargs astropy.io.fits` gives 1563 passed, 17 skipped, 100 xfailed, 1 error with and without it
  (`out/perf360_astropy_tests_{stock,proto}.txt`; the error is `test_compressed.py`, which needs hypothesis, not in
  the env; peak 8.7 GB, one test's arrays).
- **Real data:** `scripts/perf360_astropy_irisread.py`, irispy #360 (9e1eef3) `read_files` of the 1230 raster files in
  one call, env iris-plan-irispy-360, interleaved: stock 20.53 / 20.36 s, prototype 17.56 / 17.59 s, snapshot
  16.99 / 16.84 s; peak 1.13 GB; load average 0.2-0.9 (`out/perf360_astropy_irisread.txt`).
- **Main (d3ad3b66f2) not run:** astropy is compiled, and the permission classifier refused to run cloned code in
  this session ("Code from External"). From the source: `io/fits/card.py` and `header.py` are identical to v8.0.2
  (the reads are still lines 300 and 629). In `config/configuration.py`, main changed type hints, a docstring and a local
  name, and takes configobj from the configobj package rather than `astropy.extern` (#20172); `ConfigItem.__get__`
  is unchanged.

## Title

Read the FITS config in Card only where it can change the result

## Body (paste)

### Description

Every `Card.value` read checks `conf.strip_header_whitespace` (`card.py:300`), and every card's first value parse
checks `conf.enable_record_valued_keyword_cards` (`card.py:629`, from `_parse_value`). Each check is a
`ConfigItem.__get__`, the slow lookup of #12504 (about 0.8 us here). Reading every value of a 412-card header reads
the config 824 times, close to 40% of the time.

This PR reads each one only where it can matter:

- `Card.value`: test `isinstance(value, str)` before reading `strip_header_whitespace`, as only a str value is
  stripped.
- `Card._check_if_rvkc`: a card image without `": "` cannot be a record-valued keyword card
  (`_check_if_rvkc_image` returns `False` for it), so return `False` before reading
  `enable_record_valued_keyword_cards`.

Both still read the config at the time of the call, so `conf.set_temp` keeps working as before
(`test_header_strip_whitespace`).

```diff
--- a/astropy/io/fits/card.py
+++ b/astropy/io/fits/card.py
@@ -297,7 +297,8 @@
             else:
                 self._value = value = UNDEFINED
 
-        if conf.strip_header_whitespace and isinstance(value, str):
+        # Read the config only for a str value: a ConfigItem read costs about 1 us (#12504)
+        if isinstance(value, str) and conf.strip_header_whitespace:
             value = value.rstrip()
 
         return value
@@ -626,6 +627,9 @@
             self._check_if_rvkc('DP1.AXIS.1', 2)
             self._check_if_rvkc('DP1     = AXIS.1: 2')
         """
+        if len(args) == 1 and ": " not in args[0]:
+            # A card image without ': ' cannot be a RVKC, so skip the config read (#12504)
+            return False
         if not conf.enable_record_valued_keyword_cards:
             return False
 
```

With `docs/changes/io.fits/<PR>.perf.rst`:

```rst
Reading the values of a FITS header is faster: ``Card`` reads the ``strip_header_whitespace`` and
``enable_record_valued_keyword_cards`` configuration items only for the cards they can affect. Reading every value
of a 400-card header of mostly numbers takes about 40% less time.
```

This script parses a 412-card header with the value types of an IRIS level 2 header and reads every value. It runs
the code as released, the change in this PR (applied as a patch), and a snapshot of `fits.conf` as the ceiling:

```python
"""astropy.io.fits reads a ConfigItem for every card: parse a 412-card header and read every value.

The header has the value types of an IRIS level 2 primary header (211 float, 138 int, 61 str, 2 bool). The script
counts the config reads and times three ways: as released; a prototype that reads the config only where it can matter
(a str value in Card.value, a card that can be a record-valued keyword card in Card._check_if_rvkc); and a snapshot of
fits.conf in the card module, the ceiling (which would break conf.set_temp).
"""

import collections
import resource
import sys
import timeit
import types

import numpy as np

import astropy
import astropy.io.fits.card as card_module
from astropy.config import ConfigItem
from astropy.io import fits
from astropy.io.fits.card import UNDEFINED, Card

conf = card_module.conf


def header_string():
    cards = []
    for i in range(412):
        if i < 211:
            value = 0.1 * i
        elif i < 349:
            value = i
        elif i < 410:
            value = f"text {i}" if i % 2 else f"t{i}"  # short strings are padded with spaces in the card
        else:
            value = bool(i % 2)
        cards.append((f"KEY{i:04d}", value, f"comment {i}"))
    return fits.Header(cards).tostring()


TEXT = header_string()
KEYS = list(fits.Header.fromstring(TEXT).keys())


def parse_and_read():
    header = fits.Header.fromstring(TEXT)
    return [header[key] for key in KEYS]


def per_call(fn, number=200):
    return min(timeit.repeat(fn, number=number, repeat=7)) / number


def count_reads():
    counts = collections.Counter()
    original = ConfigItem.__get__

    def counting(self, obj, objtype=None):
        if obj is not None:
            counts[self.name] += 1
        return original(self, obj, objtype)

    ConfigItem.__get__ = counting
    try:
        parse_and_read()
    finally:
        ConfigItem.__get__ = original
    return dict(counts)


# Prototype: the same code as astropy 8.0.2, with the config read moved after the cheap checks.
stock_value, stock_rvkc = Card.value, Card._check_if_rvkc


def value(self):
    if self.field_specifier:
        return float(self._value)
    if self._value is not None:
        value = self._value
    elif self._valuestring is not None or self._image:
        value = self._value = self._parse_value()
    elif self._keyword == "":
        self._value = value = ""
    else:
        self._value = value = UNDEFINED
    if isinstance(value, str) and conf.strip_header_whitespace:  # 8.0.2 reads the config first
        value = value.rstrip()
    return value


def check_if_rvkc(self, *args):
    if len(args) == 1 and ": " not in args[0]:  # such a card image cannot be a RVKC: no config read
        return False
    return stock_rvkc(self, *args)


def use(variant):
    card_module.conf = conf
    Card.value, Card._check_if_rvkc = stock_value, stock_rvkc
    if variant == "prototype":
        Card.value, Card._check_if_rvkc = stock_value.getter(value), check_if_rvkc
    elif variant == "snapshot":
        names = [n for n in dir(type(conf)) if isinstance(getattr(type(conf), n, None), ConfigItem)]
        card_module.conf = types.SimpleNamespace(**{n: getattr(conf, n) for n in names})


print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, astropy {astropy.__version__} from {astropy.__file__}")
read = per_call(lambda: conf.strip_header_whitespace, 100000)
print(f"one read of fits.conf.strip_header_whitespace: {read * 1e6:.2f} us")
results = {}
for variant in ("stock", "prototype", "snapshot"):
    use(variant)
    results[variant] = parse_and_read()
    t_parse = per_call(lambda: fits.Header.fromstring(TEXT))
    t_all = per_call(parse_and_read)
    reads = count_reads()
    print(f"{variant}: Header.fromstring {t_parse * 1e3:.3f} ms; fromstring and every value {t_all * 1e3:.3f} ms; "
          f"config reads {reads}")
    results[variant + " time"] = t_all
use("stock")
base = results["stock time"]
for variant in ("prototype", "snapshot"):
    print(f"{variant}: {(1 - results[variant + ' time'] / base) * 100:.0f}% less time than stock; "
          f"values equal to stock: {results[variant] == results['stock']}")
print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB")
```

Output with astropy 8.0.2 (`card.py` on main is the same), paths shortened:

```
Python 3.13.16, numpy 2.5.4, astropy 8.0.2 from .../site-packages/astropy/__init__.py
one read of fits.conf.strip_header_whitespace: 0.82 us
stock: Header.fromstring 0.355 ms; fromstring and every value 2.509 ms; config reads {'enable_record_valued_keyword_cards': 412, 'strip_header_whitespace': 412}
prototype: Header.fromstring 0.357 ms; fromstring and every value 1.540 ms; config reads {'strip_header_whitespace': 61}
snapshot: Header.fromstring 0.360 ms; fromstring and every value 1.560 ms; config reads {}
prototype: 39% less time than stock; values equal to stock: True
snapshot: 38% less time than stock; values equal to stock: True
peak RSS: 61 MB
```

The change gets the snapshot's gain without freezing the config: 61 reads are left, one per str value. On real data,
irispy reading the 1230 files of an IRIS raster observation in one call took 20.4-20.5 s with 8.0.2, 17.6 s with
this change and 16.8-17.0 s with the snapshot. `pytest --pyargs astropy.io.fits` gives the same results with the
change as without, on 8.0.2.

This does not fix #12504 (`ConfigItem.__get__` is still slow, and `Card.comment` still reads the config each time),
so: Ref #12504.

### AI Disclosure

_(to fill in: the profile, reproducer, patch and this description were drafted with Claude Code)_

- [ ] I certify that I am human and that I take full responsibility for this pull request including all
  interactions with reviewers.

## Notes for the user (not to paste)

- The PR template's "Merge method" box is left out (unchecked by default). Fill the AI Disclosure section in your own
  words, and tick the certification yourself.
- To open it: branch from main in your astropy fork, apply the diff, add the changelog file once the PR number is
  known, then run `pytest astropy/io/fits` on a build of main (not done here; see "Main not run").
- The REPORT's figures (14% of the best variant's read; snapshot 19.3 → 16.0 s on the irispy prototype) were on
  irispy-proto. The real-data check above is on stock #360, which is why the stock time differs (20.4 s).
- Comment-only variant for #12504: the first and last paragraphs of the Description, the script and its output, and
  the real-data line.
