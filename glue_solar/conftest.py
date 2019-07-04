def pytest_configure(config):
    from glue_solar import setup
    setup()
