"""glue_patches' probes: one that raises, as on a glue change it did not foresee, installs its patch (D82)."""

import inspect
import re

from glue_solar import glue_patches


def test_a_probe_that_raises_installs_its_patch():
    def probe():
        raise AttributeError("a glue internal the probe drives is gone")

    assert glue_patches._needs(probe) is True
    assert glue_patches._needs(lambda: False) is False
    # every patch asks its probe through `_needs`
    assert not re.findall(r"(?<!def )\bneeds_\w+_workaround\(\)", inspect.getsource(glue_patches))
