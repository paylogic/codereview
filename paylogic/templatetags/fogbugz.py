"""Template tags for paylogic customizations."""
import os.path

import django.template


from django.contrib.messages import api as messages_api
from django.core.urlresolvers import reverse
from django.conf import settings

from paylogic.vcs import GuessVCS

from paylogic.views import get_case_id, get_fogbugz_case_info, attrdict, parse_branch_vcs_info

register = django.template.Library()


@register.filter
def fogbugz_case_url(issue):
    """Get Fogbugz case url out of given issue."""
    case_id = get_case_id(issue)
    return '{settings.FOGBUGZ_URL}default.asp?{case_id}'.format(case_id=case_id, settings=settings)


@register.simple_tag
def create_codereview_if_neccessary_message(request, issue):
    """Create a message with a link to create patchset if it's necessary for the issue.

    If there are pushes after latest patchset, it's necessary to create another patchset to reflect the full set
    of changes.
    """
    case_id = get_case_id(issue)
    _, case_title, original_branch, feature_branch, ci_project, target_branch = get_fogbugz_case_info(request, case_id)

    if feature_branch and original_branch:
        source_vcs, source_url, source_revision, source_branch_is_local, _ = parse_branch_vcs_info(
            feature_branch, settings.FEATURE_BRANCH_DEFAULT_PREFIX)
        if os.path.isdir(source_url):
            source = GuessVCS(
                attrdict({'revision': source_revision, 'vcs': source_vcs}), source_url)

            try:
                source_revision = source.CheckRevision().strip()
            except RuntimeError:
                return ''

            if issue.latest_patch_rev != source_revision:
                messages_api.warning(
                    request, 'There are commits after the latest created patchset. '
                    'Please create a <a href="{0}?case={1}">new one</a>'.format(
                        reverse('process_from_fogbugz'),
                        case_id
                    )
                )
    return ''
