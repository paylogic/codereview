"""Single VCS tests config."""
import pytest


@pytest.fixture
def vcs(request):
    """Version control system to test support of."""
    return 'git'


@pytest.fixture
def branch_url_mode(request):
    """Branch url mode. In short one, default prefixes will be used."""
    return 'short'
