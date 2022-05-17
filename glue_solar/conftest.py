app = None


def pytest_configure(config):
    global app
    from glue_solar import setup
    setup()
    from glue.utils.qt import get_qapp
    app = get_qapp()


def pytest_unconfigure(config):
    global app
    app.quit()
    app = None
