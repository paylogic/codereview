"""Lookups tests."""
import pytest
import json
from django.conf import settings


@pytest.fixture
def taget_branch_getter_settings(ci_project):
    """Target branch getter settings."""
    def get_target_branches_choices(_ci_project, original_branch, branches):
        assert _ci_project == ci_project
        return [('test-branch', 'test-branch-title')]
    settings.CODEREVIEW_TARGET_BRANCH_CHOICES_GETTER = get_target_branches_choices


def test_target_branches(app, case_id, taget_branch_getter_settings, mocked_fogbugz_info):
    """Test target branches lookup used for gatekeeper approval form."""
    response = app.get('/lookup/target_branches/{case_id}?term=test&page=1'.format(**locals()))
    content = json.loads(response.content)
    assert content == {'results': [{'id': 'test-branch', 'text': 'test-branch-title'}], u'err': u'nil', u'more': False}
