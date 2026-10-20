import ast
import importlib
from pathlib import Path

import pytest

SMOKE = Path(__file__).parents[2] / "packaging" / "macos" / "smoke.py"


@pytest.mark.skipif(not SMOKE.exists(), reason="the checkout's packaging folder, absent from the installed package")
def test_the_names_the_app_check_takes_from_glue_solar_exist():
    """#336's rename broke the app's check unseen until its next build (#344): only a Mac app build runs it."""
    for node in ast.walk(ast.parse(SMOKE.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module.startswith("glue_solar"):
            module = importlib.import_module(node.module)
            for alias in node.names:
                assert hasattr(module, alias.name), f"{node.module} has no {alias.name}"
