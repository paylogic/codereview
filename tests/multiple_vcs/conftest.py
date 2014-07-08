"""Multiple VCS tests."""
import pytest


@pytest.fixture(params=['git', 'hg', 'bzr'])
def vcs(request):
    """Version control system to test support of."""
    return request.param


@pytest.fixture(params=['short', 'medium', 'long'])
def branch_url_mode(request):
    """Branch url mode. In short one, default prefixes will be used."""
    return request.param
