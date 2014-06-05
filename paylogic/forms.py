"""Forms for paylogic customizations."""
from django import forms

from django.core.urlresolvers import reverse
from django_select2.fields import HeavySelect2TagField


class GatekeeperApprove(forms.Form):
    """Gatekeeper approval form."""
    target_branch = HeavySelect2TagField(
        'target_branch',
        data_view='lookup_target_branches',
    )

    target_branch.widget.options['minimumInputLength'] = 0
    target_branch.widget.options['maximumSelectionSize'] = 1

    def __init__(self, case_id, *args, **kwargs):
        """Set the lookup url according to a given Fogbugz case_id.

        :param case_id: `int` Fogbugz case id.
        """
        super(GatekeeperApprove, self).__init__(*args, **kwargs)
        self.fields['target_branch'].widget.url = reverse(
            self.fields['target_branch'].widget.view, kwargs=dict(case_id=case_id))

    def clean_target_branch(self):
        """Make single value out of multiple."""
        value = self.cleaned_data['target_branch']
        if value:
            return value[0]
