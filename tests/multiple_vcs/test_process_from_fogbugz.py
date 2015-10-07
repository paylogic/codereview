"""Codereview paylogic custom views tests."""
import subprocess
import urllib

from django.core import urlresolvers

from codereview import models

from paylogic import views


def test_process_codereview_from_fogbugz(
        user, rf, target_test_file_name, target_test_file_content, target_test_file_source_content,
        source_test_file_name, source_test_file_content, mocked_fogbugz_info, case_id):
    """Test creating issue using the data from fogbugz case."""
    request = rf.get(urlresolvers.reverse('process_from_fogbugz') + '?' + urllib.urlencode(dict(case=case_id)))
    request.user = user
    response = views.process_codereview_from_fogbugz(request)
    assert response.status_code == 302
    url = response._headers['location'][1]
    match = urlresolvers.resolve(url)
    issue_id = match.args[0]
    issue = models.Issue.objects.get(id=issue_id)
    assert len(issue.patchsets) == 1
    patches = sorted(issue.patchsets[0].patch_set.all(), key=lambda patch: patch.filename)
    assert len(patches) == 2

    assert patches[0].filename == source_test_file_name
    assert patches[0].text.startswith(
        'Index: {0}'.format(source_test_file_name))
    assert source_test_file_content in patches[0].text
    assert patches[0].content.text == ''
    assert patches[0].patched_content.text == source_test_file_content

    assert patches[1].filename == target_test_file_name
    assert patches[1].content.text == target_test_file_content
    assert patches[1].patched_content.text == target_test_file_source_content
    assert target_test_file_source_content in patches[1].text


def test_download(
        user, rf, app, target_test_file_name, target_test_file_content, target_test_file_source_content,
        source_test_file_name, source_test_file_content, mocked_fogbugz_info, case_id, target_repo, tmpdir):
    """Test download raw patch view after process from fogbugz."""
    request = rf.get(urlresolvers.reverse('process_from_fogbugz') + '?' + urllib.urlencode(dict(case=case_id)))
    request.user = user
    response = views.process_codereview_from_fogbugz(request)
    assert response.status_code == 302
    url = response._headers['location'][1]
    match = urlresolvers.resolve(url)
    issue_id = match.args[0]
    issue = models.Issue.objects.get(id=issue_id)
    response = app.get(
        '/download/issue{issue.id}_{patchset.id}.diff'.format(issue=issue, patchset=issue.patchsets[0]))
    assert not target_repo.join(source_test_file_name).exists()
    patch_file = tmpdir.join('patch.diff')
    patch_file.open('w').write(response.content)
    process = subprocess.Popen(['patch', '-i', patch_file.strpath], stdin=subprocess.PIPE, cwd=target_repo.strpath)
    process.communicate()
    assert target_repo.join(source_test_file_name).read() == source_test_file_content
