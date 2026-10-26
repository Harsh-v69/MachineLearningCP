import pytest


def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", help="also run tests marked slow (e.g. the cube3 PDB cold build)")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long-running; skipped unless --runslow")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip = pytest.mark.skip(reason="slow: pass --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
