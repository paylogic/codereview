"""Codereview paylogic custom views tests."""
import datetime
import re
import urllib

import pytest

from django.conf import settings
from django import db
from django.core import urlresolvers

from codereview import models

from paylogic import views


@pytest.fixture(autouse=True)
def django_settings(repo_base_dir, target_repo_name, source_repo_name, vcs):
    """Override django settings for tests purpose."""

    default_branches = {
        'hg': 'default',
        'git': 'master',
        'bzr': 'trunk'
    }

    settings.VCS = {
        vcs: {
            'base_dir': repo_base_dir.strpath,
            'regex': re.compile('^({base_dir}/|{vcs}\+)(.+)$'.format(
                base_dir=repo_base_dir.strpath, vcs=vcs)),
            'supports_direct_export': vcs != 'git',
            'default_branch': default_branches[vcs]
        },
    }

    settings.FEATURE_BRANCH_DEFAULT_PREFIX = '{vcs}+{path}#'.format(
        vcs=vcs, path=repo_base_dir.join(source_repo_name).strpath)
    settings.ORIGINAL_BRANCH_DEFAULT_PREFIX = '{vcs}+{path}#'.format(
        vcs=vcs, path=repo_base_dir.join(target_repo_name).strpath)


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
    patches = issue.patchsets[0].patch_set.all()
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


def test_process_codereview_from_fogbugz_too_fast(
        user, rf, target_test_file_name, target_test_file_content, target_test_file_source_content,
        source_test_file_name, source_test_file_content, mocked_fogbugz_info, case_id):
    """Test creating issue using the data from fogbugz case."""
    request = rf.get(urlresolvers.reverse('process_from_fogbugz') + '?' + urllib.urlencode(dict(case=case_id)))
    request.user = user
    response = views.process_codereview_from_fogbugz(request)
    url = response._headers['location'][1]
    match = urlresolvers.resolve(url)
    issue_id = match.args[0]

    # now try to process codereview immediately again, it should fail
    with pytest.raises(RuntimeError) as exc_info:
        views.process_codereview_from_fogbugz(request)
    assert exc_info.value.args == ('Cannot handle multiple submit requests for the same Fogbugz case.',)

    new_date = datetime.datetime.now() - datetime.timedelta(minutes=1, seconds=1)

    # but if we'll wait for a minute, it will be ok
    db.connection.cursor().execute(
        'update codereview_issue set created=%s, modified=%s where id=%s', [
            new_date,
            new_date,
            issue_id])

    assert views.process_codereview_from_fogbugz(request)
