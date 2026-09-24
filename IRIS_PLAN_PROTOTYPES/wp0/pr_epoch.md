### Description

`glue.utils.matplotlib.datetime64_to_mpl` / `mpl_to_datetime64` count days from `0001-01-01` plus one day, which was matplotlib's date convention before 3.3. Since matplotlib 3.3, dates are days from a configurable epoch (`rcParams['date.epoch']`, default `1970-01-01T00:00:00`; `matplotlib.dates.get_epoch` / `set_epoch`), and glue never calls `set_epoch`, so every datetime axis in glue lands about 1969 years in the future as far as matplotlib's date locators and formatters are concerned:

```python
import numpy as np
import matplotlib.dates as mdates
from glue.utils.matplotlib import datetime64_to_mpl

d = np.array(['2021-09-05T00:18:47'], dtype='datetime64[s]')
mdates.get_epoch()                 # '1970-01-01T00:00:00'
num = datetime64_to_mpl(d)         # [738038.01304398]
mdates.num2date(num)[0]            # 3990-09-06 00:18:47+00:00
mdates.date2num(d)                 # [18875.01304398]
```

In a `SimpleScatterViewer` with a datetime `x_att` (data from 2021-09-05) the x tick labels read `06 00:20`, `06 00:30`, ... and `num2date(ax.get_xlim())` gives 3990-09-06. With this PR: `datetime64_to_mpl(d)` = `[18875.01304398]` -> `2021-09-05T00:18:47`, tick labels `05 00:20`, ..., limits 2021-09-05.

### Changes

- `_t0()` returns `np.datetime64(dates.get_epoch())`; both conversions use it and drop the `+1` / `-1` day.
- `matplotlib>=3.2` -> `matplotlib>=3.3` in `pyproject.toml` (`get_epoch` was added in 3.3, released in 2020). `tox.ini`'s `legacy` env, which is not run in CI, still pins `matplotlib==3.2.*`; left untouched here.
- `test_mpl_datetime64`: the old round-trip value 719313 encoded the old epoch (from 1970 it is year 3939 and overflows `timedelta64[ns]`); it now round-trips 18875.5 and asserts `datetime64_to_mpl(dt) == mdates.date2num(dt)` and the reverse. The new assertions fail on `main`.

Checks: ruff v0.15.20 clean on the changed files; `pytest glue/core/tests/test_state.py glue/core/tests/test_component_link.py glue/core/tests/test_coordinate_links.py glue/core/tests/test_coordinates.py glue/core/tests/test_data_region.py glue/utils/tests/test_matplotlib.py glue/utils/tests/test_array.py`: 248 passed, 1 skipped (matplotlib 3.11.1). No existing issue found (searched "datetime epoch", "date2num").

Label: bug
