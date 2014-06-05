"""Template tags for paylogic customizations."""
import django.template

register = django.template.Library()

from django.conf import settings
from paylogic.views import get_case_id


@register.filter
def fogbugz_case_url(issue):
    """Get Fogbugz case url out of given issue."""
    case_id = get_case_id(issue)
    return '{settings.FOGBUGZ_URL}default.asp?{case_id}'.format(case_id=case_id, settings=settings)
