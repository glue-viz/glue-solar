import os, sys, pytest, glue
assert "wt-wp1chk-ape14" in glue.__file__
mode = os.environ["MODE"]
if mode == "noop":
    import glue_qt.app.application as application
    application.run_autolinker = lambda data_collection: None
elif mode == "accept":
    from glue.config import settings
    settings.AUTOLINK["Astronomy WCS"] = "always_accept"
sys.exit(pytest.main([os.environ["TESTS"], "-q", "-o", "addopts=", "-p", "no:cacheprovider", "-W", "ignore", "-k", "browse", "-x"]))
