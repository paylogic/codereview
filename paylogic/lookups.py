"""Lookups for paylogic customizations."""
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

        target_vcs, target_url, target_revision, target_branch_is_local = views.parse_branch_vcs_info(
            original_branch, settings.ORIGINAL_BRANCH_DEFAULT_PREFIX)

        branches = []
        if target_branch_is_local:

            target = GuessVCS(
                views.attrdict({'revision': target_revision, 'vcs': target_vcs}), target_url)
            try:
                branches = target.GetBranches()
            except NotImplementedError:
                # could be not yet supported by VCS
                pass

        if settings.CODEREVIEW_TARGET_BRANCH_CHOICES_GETTER:
            choices = settings.CODEREVIEW_TARGET_BRANCH_CHOICES_GETTER(ci_project, target_revision, branches)
        else:
            choices = []
        return (NO_ERR_RESP, False, choices)  # Any error response, Has more results, options list
