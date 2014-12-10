"""Codereview views tests."""
import pytest

from paylogic import views


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
    assert 'OLD NEW (Empty) {patch_content} OLD NEW'.format(
        patch_content=patch_content) in response.pyquery('#thecode').text()


def test_diff2(app, issue, patchset, patch, patch_filename, patch_text, patch_content):
    """Test delta diff view."""
    response = app.get('/{issue.id}/diff2/{patchset.id}:{patchset.id}/{patch_filename}'.format(**locals()))
    assert patch_filename in response.pyquery('h2').text()
    assert 'LEFT RIGHT {patch_content} {patch_content} LEFT RIGHT'.format(
        patch_content=patch_content) in response.pyquery('#thecode').text()


def test_publish(app, issue2, monkeypatch):
    """Test publishing comments.

    Comments are made by user on an issue created by user2. In addition, user will assign the case back to user2.
    """
    def fake_fogbugz_assign_case(request, case_id, target, message, tags):
        setattr(fake_fogbugz_assign_case, 'case_id', case_id)
        setattr(fake_fogbugz_assign_case, 'target', target)
        setattr(fake_fogbugz_assign_case, 'message', message)
        setattr(fake_fogbugz_assign_case, 'tags', tags)

    fogbugz_users = (
        (5, 'User one'),
        (10, 'User two'),
        (15, 'user three'),
    )
    assign_to = fogbugz_users[0]

    fogbugz_tags = ['tag1', 'tag2']
    message = 'test message'

    monkeypatch.setattr(views, 'get_fogbugz_assignees', lambda case_number: fogbugz_users)
    monkeypatch.setattr(views, 'fogbugz_assign_case', fake_fogbugz_assign_case)

    response = app.get('/{0}/publish'.format(issue2.id))
    response.forms['publish-form']['assign_to'] = assign_to[0]
    response.forms['publish-form']['message'] = message
    response.forms['publish-form']['tags'] = fogbugz_tags
    submit_response = response.forms['publish-form'].submit()

    assert submit_response.status_code == 302
    assert fake_fogbugz_assign_case.target == unicode(assign_to[0])
    assert fake_fogbugz_assign_case.message == unicode(message)
    assert fake_fogbugz_assign_case.tags == fogbugz_tags
    assert views.get_case_id(issue2) == fake_fogbugz_assign_case.case_id


@pytest.mark.parametrize('user_permissions', (['view_issue', 'approve_patchset'],))
def test_gatekeepers_approve(app, issue, patch, patchset_revision, monkeypatch):
    """Test gatekeeper approval form."""
    fogbugz_tags = ['tag1', 'tag2']
    monkeypatch.setattr(views, 'get_fogbugz_tags', lambda request, case_number: fogbugz_tags)
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
