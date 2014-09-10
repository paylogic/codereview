"""Forms for paylogic customizations."""
from django import forms

from django.core.urlresolvers import reverse
from django_select2.fields import HeavySelect2TagField
from codereview.views import (
    MAX_REVIEWERS,
    MAX_MESSAGE,
    MAX_CC,
    MAX_SUBJECT,
    AccountInput,
)


class GatekeeperApprove(forms.Form):

    """Gatekeeper approval form."""

    target_branch = HeavySelect2TagField(
        'target_branch',
        data_view='lookup_target_branches',
    )

    def __init__(self, case_id, *args, **kwargs):
        """Set the lookup url according to a given Fogbugz case_id.

        :param case_id: `int` Fogbugz case id.
        """
        super(GatekeeperApprove, self).__init__(*args, **kwargs)
        widget = self.fields['target_branch'].widget
        widget.options['minimumInputLength'] = 0
        widget.options['maximumSelectionSize'] = 1
        widget.options['width'] = '200px'
        widget.options['placeholder'] = 'Select target branch'

        widget.url = widget.options['ajax']['url'] = reverse(
            self.fields['target_branch'].widget.view, kwargs=dict(case_id=case_id))

    def clean_target_branch(self):
        """Make single value out of multiple."""
        value = self.cleaned_data['target_branch']
        if value:
            return value[0]


class PublishForm(forms.Form):

    """Publish comments forms."""

    subject = forms.CharField(max_length=MAX_SUBJECT,
                              widget=forms.TextInput(attrs={'size': 60}))
    reviewers = forms.CharField(required=False,
                                max_length=MAX_REVIEWERS,
                                widget=AccountInput(attrs={'size': 60}))
    cc = forms.CharField(required=False,
                         max_length=MAX_CC,
                         label='CC',
                         widget=AccountInput(attrs={'size': 60}))
    send_mail = forms.BooleanField(required=False)
    message = forms.CharField(required=False,
                              max_length=MAX_MESSAGE,
                              widget=forms.Textarea(attrs={'cols': 60}))
    message_only = forms.BooleanField(required=False,
                                      widget=forms.HiddenInput())
    no_redirect = forms.BooleanField(required=False,
                                     widget=forms.HiddenInput())

    assign_to = HeavySelect2TagField(
        'assign_to',
        data_view='lookup_case_assigned',
    )

    tags = HeavySelect2TagField(
        'tags',
        data_view='lookup_case_tags',
    )

    def __init__(self, case_id, *args, **kwargs):
        """Set the lookup url according to a given Fogbugz case_id.

        :param case_id: `int` Fogbugz case id.
        """
        super(PublishForm, self).__init__(*args, **kwargs)
        widget = self.fields['assign_to'].widget
        widget.options['minimumInputLength'] = 0
        widget.options['maximumSelectionSize'] = 1
        widget.options['width'] = '200px'
        widget.options['placeholder'] = 'Select new assignee'

        widget.url = widget.options['ajax']['url'] = reverse(
            self.fields['assign_to'].widget.view, kwargs=dict(case_id=case_id))
        self.fields['assign_to'].required = False

        widget = self.fields['tags'].widget
        widget.options['minimumInputLength'] = 0
        widget.options['width'] = '200px'
        widget.options['placeholder'] = 'Set the fogbugz case tags'

        widget.url = widget.options['ajax']['url'] = reverse(
            self.fields['tags'].widget.view, kwargs=dict(case_id=case_id))
        self.fields['tags'].required = False

    def clean_assign_to(self):
        value = self.cleaned_data.get('assign_to')
        if value:
            return value[0]
        else:
            return None

    def clean_tags(self):
        value = self.cleaned_data.get('tags')
        if value:
            return value
        else:
            return []
