Splits the CI repairs out of #68 so main goes green on its own:

- pytest-flake8 breaks collection with pytest 9 (`PluginValidationError`); ruff replaced flake8 already.
- tox requested a nonexistent `all` extra.
- Two tests leaked viewers, failing `TestImageViewer::test_removed_subset` (`assert 3 == 1`).
- Ignore the generated `glue_qt/_version.py`.

Label: bug.
