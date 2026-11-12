"""glue_patches' probes: one that raises, as on a glue change it did not foresee, installs its patch (D82)."""

import inspect
import re

import pytest

from glue_solar import glue_patches


def test_a_probe_that_raises_installs_its_patch():
    def probe():
        raise AttributeError("a glue internal the probe drives is gone")

    assert glue_patches._needs(probe) is True
    assert glue_patches._needs(lambda: False) is False
    # every patch asks its probe through `_needs`
    assert not re.findall(r"(?<!def )\bneeds_\w+_workaround\(\)", inspect.getsource(glue_patches))


def test_the_register_and_glue_patches_name_the_same_probes(request):
    # docs/dev_guide/workarounds.rst: each probe is the switch of an entry, and no entry names a probe that is gone
    register = request.config.rootpath / "docs" / "dev_guide" / "workarounds.rst"
    if not register.exists():
        pytest.skip("the package is installed without its docs")
    probes = re.findall(r"^def (needs_\w+)\(", inspect.getsource(glue_patches), re.MULTILINE)
    assert set(re.findall(r"\bneeds_\w+", register.read_text())) == set(probes)


def test_the_slider_patch_installs_where_glue_qt_reads_an_array_axis_for_a_world_axis(qapp):
    assert glue_patches.needs_slider_world_workaround()  # glue-qt 0.4.2's own method
    assert not glue_patches.needs_slider_world_workaround(glue_patches.sync_sliders_from_state)
