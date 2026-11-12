import ast
import importlib

import pytest


def test_the_names_the_app_check_takes_from_glue_solar_exist(request):
    """#336's rename broke the app's check unseen until its next build (#344): only a Mac app build runs it."""
    # pytest's root folder, not this file's: tox runs the installed copy of this file, with the checkout as the root
    smoke = request.config.rootpath / "packaging" / "macos" / "smoke.py"
    if not smoke.exists():
        pytest.skip("the package is installed without its checkout")
    for node in ast.walk(ast.parse(smoke.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module.startswith("glue_solar"):
            module = importlib.import_module(node.module)
            for alias in node.names:
                assert hasattr(module, alias.name), f"{node.module} has no {alias.name}"
