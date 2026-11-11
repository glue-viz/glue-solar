# Unravel and sanitize_index: treat a non-finite index as off the table

- Upstream: DKISTDC/dkist (branch is two commits on main a21dca3, reviewed in order)
- Fork branch: `nabobalis:nan-lookup-indices` at `354e66c5e769a10ec834148b8a9a4950ddef7005` (existing name: force-push); first commit `73c028b944c19ac1175348b161955b0a3c6c6ccc`
- Changelog fragment to rename: `changelog/PLACEHOLDER.bugfix.rst` to `<PR number>.bugfix.rst`

## Body

~~~~~markdown
`Unravel` called `int()` on each input row, so the inverse of a raveled dataset's WCS (for example Cryo-NIRSP steps and measurements) raised for a time outside its frames, where its time `Tabular1D` gives a NaN index, and for N-d world values; it now truncates the whole array and returns NaN for a NaN index or one outside the array, as `Ravel` does beyond its edges.
`sanitize_index` cast a NaN lookup index to int, which gives the least int64 on x86-64 but 0, the first row's pointing, on ARM; it now maps a non-finite index to -1, outside the table, before the cast.

On `Unravel((3, 3), order="F")` and dkist's `croppable_cryo` test file:

| call | main | this PR |
| --- | --- | --- |
| `Unravel` on `[[1, 2], [3, 4]]` | TypeError: only 0-dimensional arrays can be converted to Python scalars | the 1-D result, reshaped |
| `Unravel` on `[nan, 1, 9.2, -1.5]` | ValueError: cannot convert float NaN to integer | `[nan, 1, nan, nan], [nan, 0, nan, nan]` |
| cryo inverse of 2-D world values | TypeError | the pixels |
| cryo inverse, a time before its frames | ValueError | NaN on the four pixel axes coupled to time |
| cryo inverse, one NaN time of four | ValueError | NaN for that point, the others right |
| `sanitize_index([nan, inf, 0.4, 0.5])` | `[-9223372036854775808, -9223372036854775808, 0, 1]` and `RuntimeWarning: invalid value encountered in cast` | `[-1, -1, 0, 1]` |

The three new tests fail on main. ARM was not run; the test checks the index, -1, so it does not depend on the cast.

Code, unit tests, the changelog and this description were written via LLM.
~~~~~

## Notes for the owner (not to paste)

- Title: this is the tracker's. The earlier draft's title, "Return NaN for NaN lookup indices in Unravel and VaryingCelestialTransform", may read more clearly; your call.
- The last line follows the one in your merged #764 and #765 ("Code and unit tests were written via LLM."), extended to what is true here. dkist has no PR template or written LLM policy. If you rewrite the description or the changelog yourself, shorten that line to match.
- Changed from the fork branch: the fragment's second bullet and the second commit's message now make the ARM claim for a NaN index only. The first commit is unchanged. The code comment and the test docstring still say "A NaN or infinite index is outside the table", which describes the code and makes no ARM claim.
- ARM was not run: that a NaN cast gives 0 there is reasoning. For an infinite index nothing observable changes on x86-64 except the cast warning: it was already the least int64, outside the table.
- The drafted table's row "cryo inverse, a time before its frames" said "NaN pixels"; it now says "NaN on the four pixel axes coupled to time", because the separable Stokes pixel is still returned. "ViSP with repeats" is dropped from the first sentence, since only the Cryo-NIRSP case is shown by the test file.
- Run: `dkist/wcs/tests/test_models.py`, 96 passed.
- Run: upstream source with the branch's tests, 5 failed, 91 passed: `test_unravel_nd_input[C]` and `[F]` with `TypeError: only 0-dimensional arrays can be converted to Python scalars`; `test_unravel_nan_and_outside_the_array[True]` and `[False]` with `ValueError: cannot convert float NaN to integer`; `test_vct_non_finite_lookup_index_is_outside_the_table` with `array_equal(array([-9223372036854775808, -9223372036854775808, 1]), [-1, -1, 1])` False. First commit's source alone: 1 failed, 95 passed (the last of those).
- Run: every row of the table, on upstream and on the branch; all hold.
- Lint: ruff 0.16.1 check passes; upstream pins v0.17.3, which was not available.
- Not run: the whole suite, the docs build, towncrier, the other pre-commit hooks.
- No issue exists; add `Fixes #` only if you open one first.
