"""Codereview paylogic custom views tests."""
import urllib

import pytest

from django import db
from django.core import urlresolvers

from codereview import models

from paylogic import views


def test_process_codereview_from_fogbugz_processing(
        user, rf, target_test_file_name, target_test_file_content, target_test_file_source_content,
        source_test_file_name, source_test_file_content, mocked_fogbugz_info, case_id):
    """Test creating issue using the data from fogbugz case when there is another process doing the same."""
    request = rf.get(urlresolvers.reverse('process_from_fogbugz') + '?' + urllib.urlencode(dict(case=case_id)))
    request.user = user
    response = views.process_codereview_from_fogbugz(request)
    url = response._headers['location'][1]
    match = urlresolvers.resolve(url)
    issue_id = match.args[0]

    db.connection.cursor().execute(
        'update codereview_issue set processing=%s where id=%s', [
            True,
            issue_id
        ])

    # now try to process codereview immediately again, it should fail
    with pytest.raises(RuntimeError) as exc_info:
        views.process_codereview_from_fogbugz(request)
    assert exc_info.value.args == ('Cannot handle multiple submit requests for the same Fogbugz case.',)
