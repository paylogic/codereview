"""Lookups for paylogic customizations."""
import os.path

from django_select2 import Select2View, NO_ERR_RESP
from django.conf import settings

from paylogic import views
from paylogic.vcs import GuessVCS


class TargetBranchesView(Select2View):
    """Lookup for target branch field."""

    def get_results(self, request, term, page, context):
        """Get the list of possible target branch(es)."""
        case_id = self.kwargs['case_id']
        _, case_title, original_branch, feature_branch, ci_project = views.get_fogbugz_case_info(case_id)

        target_vcs, target_url, target_revision, target_branch_is_local, _ = views.parse_branch_vcs_info(
            original_branch, settings.ORIGINAL_BRANCH_DEFAULT_PREFIX)

        branches = []
        if os.path.isdir(target_url):
            target = GuessVCS(
                views.attrdict({'revision': target_revision, 'vcs': target_vcs}), target_url)
            try:
                branches = target.GetBranches()
            except Exception:
                # could be not yet supported by VCS
                pass

        if settings.CODEREVIEW_TARGET_BRANCH_CHOICES_GETTER:
            choices = settings.CODEREVIEW_TARGET_BRANCH_CHOICES_GETTER(ci_project, target_revision, branches)
        else:
            choices = []
        return (NO_ERR_RESP, False, choices)  # Any error response, Has more results, options list


class CaseAssignedView(Select2View):
    """Fetch people that a given case was assigned to."""

    def get_results(self, request, term, page, context):
        case_id = self.kwargs['case_id']
        possible_assignees = views.get_fogbugz_assignees(case_id)
        return (NO_ERR_RESP, False, possible_assignees)  # Any error response, Has more results, options list
