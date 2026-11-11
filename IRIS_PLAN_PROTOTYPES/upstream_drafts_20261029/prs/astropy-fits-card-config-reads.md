# Card: test the value type and card image before reading two config items

- Upstream: astropy/astropy (branch is one commit on main 7732926be)
- Fork branch: `nabobalis:fits-card-config-reads` at `e7895ca6ec19d5c76c91079b062238f0d6960817` (existing name: force-push)
- Changelog fragment to rename: `docs/changes/io.fits/PLACEHOLDER.perf.rst` to `<PR number>.perf.rst`

## Body

~~~~~markdown
### Description

This pull request is to address two configuration reads per card when the values of a parsed FITS header are read. `Card.value` reads `conf.strip_header_whitespace` for every value, and the first read of a card's value reads `conf.enable_record_valued_keyword_cards` in `Card._check_if_rvkc`. Each read goes through `ConfigItem.__get__`, the slow lookup of #12504.

The change tests two cheap conditions first, so most cards do not read the config:

- `Card.value` tests `isinstance(value, str)` before reading `strip_header_whitespace`, as only a str value is stripped.
- `Card._check_if_rvkc` returns `False` for a card image without `": "` before reading `enable_record_valued_keyword_cards`. `_check_if_rvkc_image` returns `False` for such an image anyway, so the result is the same with the setting on or off.

Where the config can change the result it is still read at that moment, so `conf.set_temp` works as before. For a 412-card header (211 float, 138 int, 61 str, 2 bool) the config reads drop from 824 to 61, and reading every value takes 1.4 ms instead of 2.4 ms.

<details><summary>Timing script</summary>

```python
import collections
import timeit

import astropy
from astropy.config import ConfigItem
from astropy.io import fits

values = [0.1 * i for i in range(211)] + list(range(211, 349))
values += [f"text {i}" for i in range(349, 410)] + [True, False]
text = fits.Header([(f"KEY{i:04d}", v, f"comment {i}") for i, v in enumerate(values)]).tostring()


def read_all():
    return [card.value for card in fits.Header.fromstring(text).cards]


reads = collections.Counter()
get = ConfigItem.__get__
ConfigItem.__get__ = lambda self, obj, objtype=None: reads.update([self.name]) or get(self, obj, objtype)
assert read_all() == values
ConfigItem.__get__ = get

t = min(timeit.repeat(read_all, number=200, repeat=7)) / 200
print(f"astropy {astropy.__version__}: {t * 1e3:.2f} ms, config reads {dict(reads)}")
```

```
before: 2.44 ms, config reads {'enable_record_valued_keyword_cards': 412, 'strip_header_whitespace': 412}
after:  1.36 ms, config reads {'strip_header_whitespace': 61}
```

Measured on astropy 8.0.2 with and without this branch's `card.py` (the file is otherwise the same as on main), Python 3.14.

</details>

The new `test_card_value_config_reads` counts the reads of `fits.card.conf` and fails without the change.

This does not fix #12504: `ConfigItem.__get__` is as slow as before, and the value setter and `Card.comment` still read the config each time.

Ref #12504

### AI Disclosure
Written with Claude Code (Anthropic); model and version: **[OWNER TO FILL: model name and version, not recorded]**. Claude Code found these reads in a profile, wrote the code change, the test, the changelog fragment, the commit message, the timing script and this description, and ran the tests and timings. **[OWNER TO ADD: one line on your own review.]**

- [ ] I certify that I am human and that I take full responsibility for this pull request including all interactions with reviewers.

### Merge method
- [ ] By checking this box, the PR author has requested that maintainers do **NOT** use the "Squash and Merge" button. Maintainers should respect this when possible; however, the final decision is at the discretion of the maintainer that merges the PR.
~~~~~

## Notes for the owner (not to paste)

- Blanks to fill in the AI Disclosure: the model name and version (not recorded anywhere), and one line on your own review.
- The certification box is left unticked on purpose: you must tick it yourself. The Merge method box is optional.
- "Found these reads in a profile" comes from the earlier draft; no profile was rerun in this build. Cut it if you would rather not state it.
- The template's `Fixes #` line is removed, as the PR closes no issue; it says `Ref #12504` (open, "ConfigNamespace is slow").
- astropy's AI policy also requires that you engage with reviewers yourself and can explain every change.
- Changed from the fork branch: the old test (22 lines, passed with the source reverted) is dropped; the two `card.py` hunks are unchanged; the fragment and the commit subject and body are narrowed to what the change does, and the body says the value setter and `Card.comment` still read the config each time.
- New test `test_card_value_config_reads` (23 lines, next to `test_header_strip_whitespace`): it swaps `fits.card.conf` for a proxy that records each attribute read, reads the values of a 4-card parsed header (int, float, bool, str), and asserts the only read is `strip_header_whitespace`, once. It pins an implementation detail (the number of config reads). If a maintainer objects, it is the only change in `test_header.py` and drops cleanly; the PR would then have no test, because the change is not observable through results.
- The test reads `card.value` over `h.cards`, not `h.values()`, because `Header.values()` reads each card's value twice (a separate small inefficiency, left alone). It does not pin that a card containing `': '` still reads the RVKC setting, because for a parsed image that read cannot change the result (the tracker's side finding).
- Run: `astropy/io/fits/tests/test_header.py`, 180 passed. With `card.py` reverted to upstream: 1 failed, 179 passed: `AssertionError: assert ['enable_reco...tespace', ...] == ['strip_header_whitespace']`, "Left contains 7 more items".
- Run: the timing script, twice each way: 2.44 and 2.35 ms before, 1.36 and 1.41 ms after, 824 to 61 config reads. Measured on astropy 8.0.2 with the branch's `card.py`; main's `card.py` is byte-identical to 8.0.2's apart from this change.
- astropy main was not built, and the installed copy has no pytest config, so warnings-as-errors was not in force.
- Lint: ruff 0.16.1 check and format pass; upstream pins v0.17.3, which was not available.
- Not run: the whole suite, the docs build, towncrier, the other pre-commit hooks. CI's changelog check fails until the fragment is renamed.
