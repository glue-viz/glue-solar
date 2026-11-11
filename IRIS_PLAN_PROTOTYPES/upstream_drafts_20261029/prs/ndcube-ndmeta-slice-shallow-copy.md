# Share values that are not axis-aware when slicing an NDMeta

- Upstream: sunpy/ndcube (branch is one commit on top of `ndmeta-copy`, which is one commit on main 23465f9)
- Fork branch: `nabobalis:ndmeta-slice-shallow-copy` at `5e630fa879415bf97adabbb963b3f682c0ddcc9b` (existing name: force-push); it sits on `ndmeta-copy` at `4dcbb35bd172fffda9688249480eddafb0169bb9`
- Changelog fragment to rename: `changelog/PLACEHOLDER.breaking.rst` to `<PR number>.breaking.rst` (the branch also carries `ndmeta-copy`'s `changelog/PLACEHOLDER.bugfix.rst`, which is renamed in that PR)

## Body

~~~~~markdown
## PR Description

Slicing an `NDMeta` deep-copied all of it and then replaced the axis-aware values with sliced ones. With a meta made from a FITS header, that copy is most of the time a cube slice takes: with a 412-card header, `cube[0]` takes 0.709 ms on main and 0.046 ms with this PR (0.014 ms with a plain `dict` meta).

The slicer now makes a shallow copy, so the slice shares the values that are not axis-aware with the original. A sliced `NDCube` already shares a `dict` meta in this way; `NDCubeSequence` and `NDCollection` deep-copy a `dict` meta when sliced, and still do. Setting, adding or deleting a key on the slice does not change the original. Changing a shared value in place does, which is why the changelog entry is `breaking` and `docs/explaining_ndcube/slicing.rst` gains a sentence.

This is the question of #815 (`copy` or `deepcopy` of `.meta`, asked there for `rebin`) applied to slicing; `rebin` is not touched here.

Built on #[PR NUMBER OF ndmeta-copy], whose `NDMeta.__copy__` keeps the slice's axes, key comments and data shape separate from the original's. Only the last commit is new.

<details><summary>Timing script</summary>

```python
import timeit

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from ndcube import NDCube, NDMeta

header = fits.Header([(f"KEY{i:04d}", 0.1 * i, f"comment {i}") for i in range(412)])
meta = NDMeta(header, data_shape=(8, 100, 40))
meta.add("exposure time", np.linspace(8, 8.5, 8), axes=0)
cube = NDCube(np.zeros((8, 100, 40)), wcs=WCS(naxis=3), meta=meta)
plain = NDCube(np.zeros((8, 100, 40)), wcs=WCS(naxis=3), meta=dict(header))
for name, c in [("an NDMeta", cube), ("a dict", plain)]:
    print(f"cube[0] with {name} meta: {min(timeit.repeat(lambda: c[0], number=300, repeat=7)) / 300 * 1e3:.3f} ms")
```

</details>

## AI Assistance Disclosure

AI tools were used for:
- [x] Code generation (e.g., when writing an implementation or fixing a bug)
- [x] Test/benchmark generation
- [x] Documentation (including examples)
- [x] Research and understanding
- [ ] No AI tools were used

> Regardless of AI use, the human contributor remains fully responsible for correctness, design choices, licensing compatibility, and long-term maintainability.
~~~~~

## Notes for the owner (not to paste)

- Do not paste this body as written. sunpy's AI policy, which ndcube's PR template links, lists "Pasting AI generated text in the description of issues, PRs or in comments" as inappropriate use. Rewrite the description in your own words; the policy does allow AI to help reword a summary you have written.
- The policy also says a PR that removes the AI Assistance Disclosure checklist may be closed without review, and one that leaves it incomplete is marked draft and not reviewed. Keep the checklist and the quoted line under it.
- The four ticked boxes are facts about how the work was made (code, tests, the changelog fragment and the sentence in `slicing.rst`, and the research); confirm them before posting.
- Blank to fill: `#[PR NUMBER OF ndmeta-copy]`. Open `ndmeta-copy` first; this branch is stacked on it and shows two commits until that one merges.
- ndcube's template asks for an issue before a PR. The tracker's unposted issue "Slicing deep-copies the whole NDMeta" goes with this PR.
- ndcube's template asks for commit subjects of 72 characters or less; this one is 59.
- #815 is open: "Decide on correct meta copying behaviour in `rebin`". The maintainer who opened it proposes `copy` over `deepcopy`. The body cites it as the same question for slicing.
- Changed from the fork branch: restacked on `ndmeta-copy`; the wording "as it shares a `dict` meta" is corrected in the breaking fragment, the comment in `ndcube/meta.py` and the commit message, to say that a sliced `NDCube` shares a dict meta and that `NDCubeSequence` and `NDCollection` deep-copy one; the subject is the tracker's; the commit body carries the timing.
- Checked on upstream: a sliced `NDCube` shares a dict meta's values; `NDCubeSequence` and `NDCollection` do not (`copy.deepcopy(self.meta)` in both).
- Run: `ndcube/tests/test_meta.py`, 21 passed. With `ndmeta-copy`'s `meta.py` (the slicer change reverted): 1 failed, 20 passed: `test_slice_shares_values_without_axes`, `AssertionError: assert {'KEY': 'value'} is {'KEY': 'value'}`.
- `test_slice_leaves_original_unchanged` passes with the slicer change reverted. It is kept because it guards the hazard the change introduces: with the slicer's `copy.copy` but without `ndmeta-copy`'s `__copy__`, it and five other tests fail (6 failed, 15 passed), which is also why this PR sits on `ndmeta-copy`. Say if you want it dropped, as was done for the astropy test.
- Timing in this build: 0.66 to 0.70 ms on main, 0.042 to 0.046 ms on the branch, 0.014 ms with a dict meta. That agrees with your 0.709 to 0.046, which the commit and the body use.
- Lint: ruff 0.16.1 check passes; upstream pins v0.17.4, which was not available.
- Not run: the whole suite, the docs build (so the new sentence in `slicing.rst` was not rendered), towncrier, the other pre-commit hooks.
