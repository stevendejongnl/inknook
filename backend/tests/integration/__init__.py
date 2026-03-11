"""Integration tests with testcontainers."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Mark all tests in this directory as integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
