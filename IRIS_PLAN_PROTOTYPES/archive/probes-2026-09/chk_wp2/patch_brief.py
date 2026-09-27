import re
S = "/private/tmp/claude-501/-Users-nabil-Git-glue-solar/72764293-8e82-4502-aeff-9f6c3d248202/scratchpad"
path = f"{S}/briefs/wp2-moments.md"
b = open(path).read()
module = open(f"{S}/chk_wp2/wp2_moments_module.py").read()
tests = open(f"{S}/chk_wp2/test_wp2_moments.py").read()

def rep(old, new, count=1):
    global b
    assert b.count(old) == count, (b.count(old), old[:80])
    b = b.replace(old, new)

# --- code blocks: swap in the checker-corrected module and tests
blocks = re.findall(r"```python\n(.*?)```", b, re.S)
assert len(blocks) == 2
b = b.replace("```python\n" + blocks[0] + "```", "```python\n" + module + "```")
b = b.replace("```python\n" + blocks[1] + "```", "```python\n" + tests + "```")

# --- Current state
rep('`gh pr view 44 --json state,reviewDecision,statusCheckRollup` today: `{"checks":[null,"SKIPPED","SUCCESS"],"reviewDecision":"","state":"OPEN"}`.',
    '`gh pr view 44 --json state,reviewDecision,statusCheckRollup` today (checker re-run, real HOME): `state OPEN`, `reviewDecision ""`, 21 check rows all `SUCCESS`/`SKIPPED` (one `null` conclusion row).')
rep("`-o addopts=''` because `pytest-doctestplus` is not installed in the venv; `pytest.ini:19` `--doctest-rst` needs it",
    "`-o addopts=''` because `pytest-doctestplus` is not installed in the venv; `pytest.ini:23` `--doctest-rst` needs it; `pytest.ini:26-28` `filterwarnings = error`")
rep("`utils/_spectral.py:49-73` `make_spatial_template` slices wavelength index 0",
    "`utils/_spectral.py:49-75` `make_spatial_template` slices wavelength index 0")
rep("glue-solar pins `>=0.8.1` (`pyproject.toml:19`).",
    "glue-solar pins `>=0.8.1` (`pyproject.toml:22`). `moments.py:109` converts the cube's wavelengths to nm whatever the WCS unit, so the rewrap works with a raw WCS in m or Angstrom. `moments.py:161-166` accepts `min_intensity` as a Quantity and converts it to the zeroth-moment unit (`DN nm` when `integrated=True`, `moments.py:146-151`); `saturation_limit` is compared in `cube.unit` (`:168-171`).")
rep("`glue.config.layer_action is glue_qt.config.layer_action` -> `True` (glue/config.py:950-951 re-export).",
    "`glue.config.layer_action is glue_qt.config.layer_action` -> `True` (glue/config.py:950-951 re-export). The editable install's metadata string is `0.1.dev6892+ga9c8a0640` (stale, from an earlier macos-integration commit); the code that runs is the working tree at `bd4dce6b9` (macos-integration HEAD today).\n- glue-core 1.27 Image viewer: `ImageLayerState.attribute_display_unit` (`glue/viewers/image/state.py:500, 629-642`) offers display-unit choices only for units astropy can parse on its own; `DN_IRIS_NUV nm` is not parseable outside irispy's `add_enabled_units` context, so wavelength-bearing outputs are converted to Angstrom at source (D3) instead of relying on the viewer.")

# --- Decisions
rep("- D3: the dialog takes Angstrom everywhere (rest wavelength, wings). Values become `astropy` Quantities (`* u.AA`) before reaching irispy, so the dialog does not care whether `_GlueWCS` reports metres (today) or Angstrom (after WP1). The rewrap passes `data.coords._wcs` (raw irispy WCS, metres) and irispy converts to nm internally. WP2 does not read wavelengths through `data.coords`.",
    "- D3: Angstrom in AND out. The dialog takes Angstrom everywhere (rest wavelength, wings); values become `astropy` Quantities (`* u.AA`) before reaching irispy. irispy returns `centroid`/`width` in nm and the integrated intensity in `DN nm`; the module converts every map with `_in_angstrom` (`NDCube.to`, replaces the `nm` base by `Angstrom`, verified below) so the stored components are `Angstrom`, `Angstrom`, and `Angstrom DN_IRIS_<band>`; `km / s` maps are untouched. With `integrated=True` the minimum-intensity threshold is passed as a Quantity in `DN Angstrom` (irispy would otherwise compare the typed number against `DN nm`, a silent factor 10). The rewrap passes `data.coords._wcs` (raw irispy WCS, metres today) and irispy converts to nm internally (`moments.py:109`), so WP2 does not care whether `_GlueWCS` reports metres or Angstrom and never reads wavelengths through `data.coords`. (Checker correction 2026-09-02: the writer's version left `nm` outputs, contradicting D3 and its own checkbox label.)")

# --- Dependencies
rep("- Code dependencies: none. Runs on released glue-core 1.27.0 + glue-qt main + irispy 0.8.1 (all verified today). Independent of WP1 (WP1 edits `_GlueWCS` only; WP2 uses `_wcs` and Quantities). Independent of the fork branches.",
    "- Code dependencies: none. Runs on released glue-core 1.27.0 + glue-qt main + irispy 0.8.1 (all verified today). Independent of WP1 (WP1 edits `_GlueWCS` only; WP2 uses `_wcs` and Quantities; the WP1 brief did not exist yet when this brief was checked, and irispy's own nm conversion makes WP2 robust to any raw-WCS unit). Independent of the fork branches.")

# --- Files to touch
rep("- `glue_solar/sources/moments.py` (NEW, 97 lines, verified text below)", "- `glue_solar/sources/moments.py` (NEW, 107 lines, verified text below)")

# --- Steps
rep("4. Create `glue_solar/tests/test_moments.py` from the verified test text, replacing the import line",
    "4. Create `glue_solar/tests/test_moments.py` from the verified test text (identical to `scratchpad/chk_wp2/test_wp2_moments.py`), replacing the import line")

# --- Verified code intro
rep("Scratch files: `scratchpad/wp2_moments_module.py` (the module), `scratchpad/test_wp2_moments.py` (the tests), `scratchpad/wp2_moments_proto.py` (module + extra checks), `scratchpad/wp2_collapse_reach.py`.",
    "Scratch files: the CORRECTED (Angstrom) module and tests are `scratchpad/chk_wp2/wp2_moments_module.py` and `scratchpad/chk_wp2/test_wp2_moments.py` (checker, 2026-09-02); the writer's pre-Angstrom originals `scratchpad/wp2_moments_module.py`, `scratchpad/test_wp2_moments.py` and `scratchpad/wp2_moments_proto.py` (module + extra checks) are still there and SHADOW the corrected module when a script runs with the scratchpad root as cwd (cwd is first on `sys.path`; the checker hit this). Run from `scratchpad/chk_wp2/`. `scratchpad/wp2_collapse_reach.py` is unaffected.")

# --- Notes on the module
rep("- `data.main_components[0]` is the science array",
    "- `_in_angstrom` (D3): `cube.to(u.CompositeUnit(1, [AA if base == nm else base ...], powers))` keeps mask, SGMeta and WCS (verified below); `km / s` maps go through an identity conversion. Cost: one array copy per 7480-px map.\n- `min_intensity` when integrating: `min_intensity * cube.unit * u.AA` so irispy's `min_intensity.to_value(intensity_unit)` (`moments.py:162`) compares in `DN nm` correctly. Verified: 50 DN Angstrom keeps 4472 of 7480 px finite, 50 DN (summed) keeps 6545; without the line, 50 is read as 50 DN nm and every pixel is NaN.\n- `data.main_components[0]` is the science array")

# --- Proto block header + superseded lines
rep("### Prototype run (module + checks): `python -u scratchpad/wp2_moments_proto.py`\n\n```",
    "### Prototype run (writer's script, embeds the PRE-Angstrom module): `python -u scratchpad/wp2_moments_proto.py`\n\nRe-run by the checker today; identical output except RBA timing (`0.29s ... 39 us/px; est 17s`). The two lines marked `# superseded` show `nm` units that the corrected module turns into Angstrom (see the next block); everything else holds for the corrected module.\n\n```")
rep("result: Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0-moments (187, 40) [('intensity', 'DN_IRIS_NUV'), ('intensity mask', ''), ('centroid', 'nm'), ('width', 'nm'), ('velocity', 'km / s'), ('velocity_width', 'km / s'), ('Time', '')]",
    "result: Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0-moments (187, 40) [('intensity', 'DN_IRIS_NUV'), ('intensity mask', ''), ('centroid', 'nm'), ('width', 'nm'), ('velocity', 'km / s'), ('velocity_width', 'km / s'), ('Time', '')]   # superseded: centroid/width are 'Angstrom' with the corrected module")
rep("integrated unit: DN_IRIS_NUV nm\n", "integrated unit: DN_IRIS_NUV nm   # superseded: 'Angstrom DN_IRIS_NUV' with the corrected module\n")

# --- new verified blocks after the proto explanation paragraph
anchor = "`app._layer_widget._actions[\"IRIS: line moments…\"]._can_trigger()`.)\n"
new_blocks = anchor + '''
### Corrected module, dialog run with the integrated checkbox (checker, `cd scratchpad/chk_wp2 && python - <<EOF ...`)

```python
# cwd = scratchpad/chk_wp2 (so the corrected module wins), HOME=<scratch>/home-chk2, QT_QPA_PLATFORM=offscreen
import numpy as np
from qtpy import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
from glue.core import DataCollection
from irispy.data.test import get_test_data_filenames
from glue_solar.sources.loaders.iris import raster_data
from wp2_moments_module import MomentsDialog
path = next(p for p in get_test_data_filenames() if p.name == "iris_l2_20210905_001833_3620258102_raster_t000_r00000.fits" and p.parent.name == "sns")
r = raster_data([path], ["Mg II k 2796"])[0]
dc = DataCollection([r])
d = MomentsDialog(r, dc)
d.rest.setText("2794.09"); d.low.setText("0.5"); d.high.setText("0.5"); d.minimum.setText("50"); d.integrated.setChecked(True)
d.run()
m = dc[1]
print("accepted:", d.result() == QtWidgets.QDialog.Accepted, "| label:", m.label, m.shape)
print("units:", [(c.label, m.get_component(c).units) for c in m.main_components])
print("centroid median [A]:", round(float(np.nanmedian(m['centroid'])), 3), "| width median [A]:", round(float(np.nanmedian(m['width'])), 4))
print("velocity finite:", int(np.isfinite(m['velocity']).sum()), "of", m['velocity'].size, "| finite iff intensity>=50 DN A:", bool((np.isfinite(m['velocity']) == (m['intensity'] >= 50)).all()))
print("links:", len(dc.external_links))
```
```
accepted: True | label: Mg_II_k_2796-3620258102-2021-09-05T00:18:33-scan-0-moments (187, 40)
units: [('intensity', 'Angstrom DN_IRIS_NUV'), ('intensity mask', ''), ('centroid', 'Angstrom'), ('width', 'Angstrom'), ('velocity', 'km / s'), ('velocity_width', 'km / s'), ('Time', '')]
centroid median [A]: 2794.064 | width median [A]: 0.3197
velocity finite: 4472 of 7480 | finite iff intensity>=50 DN A: True
links: 2
```

### `NDCube.to` keeps mask, meta and WCS (checker)

```
# calculate_moments(cube, rest_wavelength=2794.09*u.AA, wings=(0.5*u.AA, 0.5*u.AA), min_intensity=50, integrated=True), then per map:
intensity unit DN_IRIS_NUV nm -> target Angstrom DN_IRIS_NUV | has .to: True
centroid unit nm -> target Angstrom | has .to: True
velocity unit km / s -> target km / s | has .to: True
type after to: SpectrogramCube unit Angstrom DN_IRIS_NUV mask kept: True meta same type: SGMeta wcs same: True
values x10: True
_cube_data unit: Angstrom DN_IRIS_NUV comps ['intensity', 'intensity mask']
str units: ['Angstrom DN_IRIS_NUV', 'Angstrom', 'Angstrom', 'km / s', 'km / s']
```
(`str()` of the composite puts `Angstrom` first; the test asserts that exact string. That run also showed the min-intensity trap: `min_intensity=50` with `integrated=True` and no Quantity left every centroid NaN, because 50 was read as 50 DN nm.)

### The moments Data keeps a sliced `SGMeta` (verifier P2.1 note 3, checker re-run)

```
result.meta: SGMeta is source meta: False | rest_wavelength: 279.61999511700003 nm | OBSID: 3620258102
result.coords: _GlueWCS ('arcsec', 'arcsec') | raw: WCS ['deg', 'deg']
```
'''
rep(anchor, new_blocks)

# --- tests block result + ruff block
rep("5 passed, 2 warnings in 2.28s      # the 2 warnings are PytestConfigWarning for doctest_plus/text_file_format (plugin not installed)",
    "5 passed, 2 warnings in 2.21s      # checker re-run with the corrected files (PYTHONPATH=scratchpad/chk_wp2 --rootdir=scratchpad/chk_wp2); the 2 warnings are PytestConfigWarning for doctest_plus/text_file_format (plugin not installed)")
rep("""$ ruff check --config .ruff.toml --no-cache --output-format concise scratchpad/wp2_moments_module.py scratchpad/test_wp2_moments.py
scratchpad/test_wp2_moments.py:1:1: I001 [*] Import block is un-sorted or un-formatted   # only the scratch `from wp2_moments_module import ...` line; gone once it is `from glue_solar.sources.moments import ...`
Found 1 error.""",
    """$ sed 's/from wp2_moments_module import/from glue_solar.sources.moments import/' scratchpad/chk_wp2/test_wp2_moments.py > scratchpad/chk_wp2/test_moments_repoimport.py
$ ruff check --config .ruff.toml --no-cache --output-format concise scratchpad/chk_wp2/wp2_moments_module.py scratchpad/chk_wp2/test_moments_repoimport.py
All checks passed!
# with the scratch import line `from wp2_moments_module import ...` ruff reports I001 when run from the repo root (module not first-party there); irrelevant once the import is the repo one""")

# --- what each test pins
rep("component order and units exactly `intensity DN_IRIS_NUV, intensity mask, centroid nm, width nm, velocity km / s, velocity_width km / s, Time`",
    "component order and units exactly `intensity DN_IRIS_NUV, intensity mask, centroid Angstrom, width Angstrom, velocity km / s, velocity_width km / s, Time`")
rep("- `test_integrated_zeroth_moment_unit`: `\"DN_IRIS_NUV nm\"`.",
    "- `test_integrated_zeroth_moment_is_dn_angstrom`: unit string `\"Angstrom DN_IRIS_NUV\"`; the integrated map equals the summed map times the window step 0.02546 Angstrom (rtol 1e-3) where finite; the number of finite pixels equals the count of `summed * 0.02546 >= 50`, which pins the `DN Angstrom` threshold (would be 0 finite px if irispy compared 50 against `DN nm`).")

# --- pitfalls
rep("- `DN_IRIS_NUV`/`DN_IRIS_FUV` are irispy-defined units:",
    "- `min_intensity` with `integrated=True`: irispy compares the threshold against the zeroth moment in ITS unit, `DN nm` (`moments.py:146-151, 161-166`); a plain number typed as `DN Angstrom` is off by 10x (50 -> every pixel NaN on the sns window, hit by the checker). The module passes `min_intensity * cube.unit * u.AA` when integrating. Keep the dialog label \"Minimum zeroth moment [DN, or DN Angstrom when integrating]\".\n- Two copies of the module live in the scratchpad: `scratchpad/wp2_moments_module.py` (writer, nm outputs) and `scratchpad/chk_wp2/wp2_moments_module.py` (corrected). A script started with the scratchpad root as cwd imports the stale one even with `PYTHONPATH=scratchpad/chk_wp2` (cwd wins); pytest with `--rootdir=scratchpad/chk_wp2` imports the corrected one. The brief's module text is the corrected one.\n- `DN_IRIS_NUV`/`DN_IRIS_FUV` are irispy-defined units:")

# --- acceptance
rep("with units `DN_IRIS_<band>` (or `DN_IRIS_<band> nm` when integrated), `nm`, `nm`, `km / s`, `km / s`; world axes Helioprojective Longitude/Latitude in arcsec.",
    "with units `DN_IRIS_<band>` (or `Angstrom DN_IRIS_<band>` when integrated), `Angstrom`, `Angstrom`, `km / s`, `km / s` (D3: no `nm` anywhere); world axes Helioprojective Longitude/Latitude in arcsec.")
rep("- [ ] Dialog fields: rest wavelength [Angstrom] prefilled from TWAVE when present, blue/red wings [Angstrom], minimum summed intensity [DN], saturation limit [DN], integrated checkbox; OK runs, Cancel closes.",
    "- [ ] Dialog fields: rest wavelength [Angstrom] prefilled from TWAVE when present, blue/red wings [Angstrom], minimum zeroth moment [DN, or DN Angstrom when integrating], saturation limit [DN], integrated checkbox; OK runs, Cancel closes.")

# --- docs
rep("""in the data collection and choose "IRIS: line moments...". The dialog wraps
:func:`irispy.utils.moments.calculate_moments`:""",
    """in the data collection and choose "IRIS: line moments...". The dialog wraps
``irispy.utils.moments.calculate_moments`` (irispy-lmsal):""")
rep("- Minimum summed intensity [DN]: pixels whose summed intensity is below this value get NaN in every map.",
    "- Minimum zeroth moment [DN, or DN Angstrom when integrating]: pixels whose zeroth moment is below this\n  value get NaN in every map.")
rep("""components ``intensity``, ``centroid`` and ``width`` (nm), and, when a rest wavelength is known,
``velocity`` and ``velocity_width`` (km/s), plus the ``intensity mask`` and the per-step ``Time``.""",
    """components ``intensity`` (DN, or DN Angstrom when integrating), ``centroid`` and ``width`` (Angstrom),
and, when a rest wavelength is known, ``velocity`` and ``velocity_width`` (km/s), plus the
``intensity mask`` and the per-step ``Time``.""")
rep("maps of the window with `irispy.utils.moments.calculate_moments` (rest wavelength prefilled from ``TWAVE``, optional spectral wings, minimum intensity and saturation limit).",
    "maps of the window with ``irispy.utils.moments.calculate_moments`` (rest wavelength prefilled from ``TWAVE``, optional spectral wings in Angstrom, minimum intensity and saturation limit). Wavelength outputs are in Angstrom.")
rep("- `docs/dev_guide/loader-customization.rst:7-8` (optional, one sentence)",
    "- `docs/conf.py:74` `intersphinx_mapping` has only `python`, `default_role = \"py:obj\"` (:69), no `nitpicky`: unresolved `irispy` references render as literals without a warning under `-W`, so the texts above use double backticks. `https://docs.sunpy.org/projects/irispy-lmsal/en/stable/objects.inv` returned HTTP 404 today; do not add an intersphinx entry without finding the right URL.\n- `docs/dev_guide/loader-customization.rst:7-8` (optional, one sentence)")

open(path, "w").write(b)
print("patched OK, size", len(b))
