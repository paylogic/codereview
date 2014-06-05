"""Template tags for paylogic customizations."""
import django.template

register = django.template.Library()

from paylogic.forms import GatekeeperApprove
from paylogic.views import get_case_id


@register.inclusion_tag('gatekeeper_approve_form.html', takes_context=True)
def gatekeeper_approve_form(context, request):
    """Render gatekeeper approval form."""
    issue = context['issue']
    case_id = get_case_id(issue)

    form = GatekeeperApprove(case_id)

    return {'form': form, 'issue': issue}
