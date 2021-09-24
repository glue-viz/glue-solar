try:
    from ._version import version
except Exception:
    import warnings
    warnings.warn(
        f'could not determine {__name__.split(".")[0]} package version; this indicates a broken installation'
    )
    del warnings
    version = '0.0.0'


# We use LooseVersion to define major, minor, micro, but ignore any suffixes.
def split_version(version):
    pieces = [0, 0, 0]
    try:
        from distutils.version import LooseVersion
        for j, piece in enumerate(LooseVersion(version).version[:3]):
            pieces[j] = int(piece)
    except Exception:
        pass
    return pieces


major, minor, bugfix = split_version(version)
del split_version  # clean up namespace.
release = 'dev' not in version
