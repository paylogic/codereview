"""Codereview views tests."""
import pytest

from django.conf import settings


@pytest.mark.parametrize('user_permissions', ([],))
def test_index(app, issue):
    """Test that index is open for everyone."""
    response = app.get('/')
    assert response.status_code == 200


@pytest.mark.parametrize('user_permissions', ([],))
def test_show_protected(app, issue):
    """Test show issue view protection."""
    response = app.get('/{issue.id}/show'.format(issue=issue))
    assert response.status_code == 302


def test_show(app, issue, patch, patch_filename):
    """Test show issue view."""
    response = app.get('/{issue.id}/show'.format(issue=issue))
    response.click(patch_filename)
    assert response.status_code == 200


def test_patch(app, issue, patchset, patch, patch_filename, patch_text):
    """Test patch view."""
    response = app.get('/{issue.id}/patch/{patchset.id}/{patch.id}'.format(**locals()))
    assert patch_filename in response.pyquery('h2').text()
    assert patch_text.splitlines()[1] in response.pyquery('.code').text()


def test_diff(app, issue, patchset, patch, patch_filename, patch_text, patch_content):
    """Test diff view."""
    response = app.get('/{issue.id}/diff/{patchset.id}/{patch_filename}'.format(**locals()))
    assert patch_filename in response.pyquery('h2').text()
    assert 'OLD NEW (Empty) 1 {patch_content} OLD NEW'.format(
        patch_content=patch_content) in response.pyquery('#thecode').text()


def test_diff2(app, issue, patchset, patch, patch_filename, patch_text, patch_content):
    """Test delta diff view."""
    response = app.get('/{issue.id}/diff2/{patchset.id}:{patchset.id}/{patch_filename}'.format(**locals()))
    assert patch_filename in response.pyquery('h2').text()
    assert 'LEFT RIGHT 1 {patch_content} 1 {patch_content} LEFT RIGHT'.format(
        patch_content=patch_content) in response.pyquery('#thecode').text()


@pytest.mark.parametrize('user_permissions', (['view_issue', 'approve_patchset'],))
def test_gatekeepers_approve(app, issue, patch, patchset_revision):
    """Test gatekeeper approval form."""
    response = app.get('/{issue.id}/'.format(**locals()))
    form = response.forms['gatekeeper-approval']
    form['target_branch'] = 'r1111'
    response = form.submit().follow()
    issue = issue.objects.get(id=issue.id)
    assert issue.latest_reviewed_rev == patchset_revision
    assert 'was sucesssfully approved' in response.content


@pytest.mark.parametrize(
    ['user_permissions', 'ci_project'],
    [
        (['view_issue', 'approve_patchset'], '--')
    ])
def test_gatekeepers_approve_no_ci_project(app, issue, patch, ci_project):
    """Test gatekeeper approval form."""
    response = app.get('/{issue.id}/'.format(**locals()))
    form = response.forms['gatekeeper-approval']
    form['target_branch'] = 'r1111'
    response = form.submit().follow()
    issue = issue.objects.get(id=issue.id)
    assert not issue.latest_reviewed_rev
    assert 'You need to set CI Project field' in response.content
