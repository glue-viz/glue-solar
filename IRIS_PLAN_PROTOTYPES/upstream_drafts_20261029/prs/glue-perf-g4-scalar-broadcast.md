# Return float32, not float64, for a float32 component and a scalar

- Upstream: glue-viz/glue
- Fork branch: `nabobalis:perf-g4-scalar-broadcast`, commit ca560c01 (pushed 2026-11-12)
- Label: enhancement

## Body

~~~~~markdown
`BinaryComponentLink.compute` passes every operand pair through `np.broadcast_arrays`, which turns a Python scalar into a full-shape int64 or float64 array. NumPy then promotes array with array, so `d.id['x'] * 2` on float32 data returns float64: twice the memory of the data, and more time to compute.

A scalar operand is now left as a scalar when the other operand is a floating-point array, so NumPy's scalar promotion keeps the array's dtype. An integer array is still broadcast against the scalar, so that `int16 * 1000` is still upcast to int64 and does not overflow. Array with array is broadcast as before.

**This changes results** for float32, float16 and complex64 components combined with a Python scalar. They are now computed at the data's own precision, as NumPy does for `array * scalar`: they are rounded to that precision, and values beyond its range become inf where a 64-bit result kept them.

For a float32 cube of shape (800, 417, 262), `x * 2` goes from about 48 ms and a 699 MB peak to about 21 ms and a 350 MB peak.

`test_arithmetic_id_scalar_dtype` fails on main, where the result is float64.
~~~~~

## Notes for the owner (not to paste)

- Only the commit subject changed: it was "Keep float data dtype when combining a component with a scalar". The tree is identical to the fork branch's.
- The tracker's title for this row is "Keep float32 when a float32 component is combined with a scalar". I chose a subject that names both dtypes, so the changelog line itself says the result changes. Say if you prefer the tracker's.
- The 48 and 21 ms are the commit message's numbers, not measured again.
- Tests: `glue/core/tests/test_component_link.py` 27 passed. On upstream/main: `AssertionError: assert dtype('float64') == <class 'numpy.float32'>`.
