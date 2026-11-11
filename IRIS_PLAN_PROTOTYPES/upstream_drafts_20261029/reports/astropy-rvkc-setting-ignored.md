# astropy.io.fits: the record-valued keyword setting is ignored for parsed cards (side finding of perf360 c4)

- **Where:** a new astropy issue (bug template); not filed. Reproducer: `code/astropy/rvkc_off.py`.

`enable_record_valued_keyword_cards = False` does not stop a parsed card image from becoming a RVKC.
`Card._parse_keyword` (card.py:737 on main) calls `_check_if_rvkc_image(keyword, rest)` without reading the setting.
The setting therefore acts only on `Card(keyword, value)`, and the read this PR skips in `_check_if_rvkc(image)` never
decides a result. Reproducer `probe/rvkc_off.py` (`out/rvkc_off_main.txt`, `out/rvkc_off_802.txt`, the same on main
d3ad3b66f2 and 8.0.2):

```
Card.fromstring: 'DP1.AXIS.1' 2.0
Card(keyword, value): 'DP1' 'AXIS.1: 2'
```

**Title:** `io.fits: enable_record_valued_keyword_cards = False does not apply to parsed card images`

**Body:**

````markdown
### Description

The `enable_record_valued_keyword_cards` setting says record-valued keyword cards are "otherwise treated as normal
keywords", but with it off a card read from a header is still parsed as a record-valued keyword card.
`Card._parse_keyword` calls `_check_if_rvkc_image` without checking the setting; only `Card(keyword, value)` honors it.

### Expected behavior

With the setting off, `Card.fromstring("DP1     = 'AXIS.1: 2'")` has keyword `DP1` and value `'AXIS.1: 2'`, as
`Card("DP1", "AXIS.1: 2")` does.

### How to Reproduce

```python
from astropy.io import fits

with fits.conf.set_temp("enable_record_valued_keyword_cards", False):
    c = fits.Card.fromstring("DP1     = 'AXIS.1: 2'")
    print(repr(c.keyword), repr(c.value))  # 'DP1.AXIS.1' 2.0
    c = fits.Card("DP1", "AXIS.1: 2")
    print(repr(c.keyword), repr(c.value))  # 'DP1' 'AXIS.1: 2'
```

### Versions

astropy 8.0.2 and main (d3ad3b66f2), Python 3.13.16, numpy 2.5.4, Linux.
````
