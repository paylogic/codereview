import sys
from django.conf.urls.defaults import *
from django.contrib import admin
from django.views import debug

from paylogic import patches  # NOQA
from paylogic import lookups

# from codereview.urls import urlpatterns

admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',   # There two are to
        {'document_root': 'static/'}),                  # fix the migration
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',  # from Django 1.1 to 1.3
        {'document_root': 'static/'}),                  # because of contrib.staticfiles
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='auth_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login', name='auth_logout'),
    url(r'^fogbugz/authorize/?$', 'paylogic.views.fogbugz_authorize', name='fogbugz_authorize'),
    ('^admin/', include(admin.site.urls)),
    (r'^openid/', include('django_openid_auth.urls')),
    ('^_ah/admin', 'rietveld_helper.views.admin_redirect'),
    url(r'^(\d+)/publish$', 'paylogic.views.publish'),
    url(r'^fogbugz$', 'paylogic.views.process_codereview_from_fogbugz',
        name='process_from_fogbugz'),
    url(r'^fogbugz_find$', 'paylogic.views.find_codereview_from_fogbugz',
        name='find_from_fogbugz'),
    url(r'^mergekeeper_close/(?P<case_id>\d+)/$',
        'paylogic.views.mergekeeper_close', name='mergekeeper_close'),
    url(r'^lookup/target_branches/(?P<case_id>\d+)$',
        lookups.TargetBranchesView.as_view(), name='lookup_target_branches'),
    url(r'^gatekeeper_mark_ok/(?P<issue_id>\d+)/$',
        'paylogic.views.gatekeeper_mark_ok', name="paylogic_mark_ok"),
    url(r'^lookup/case_assigned/(?P<case_id>\d+)$',
        lookups.CaseAssignedView.as_view(), name='lookup_case_assigned'),
    url(r'^lookup/case_tags/(?P<case_id>\d+)$',
        lookups.CaseTagsView.as_view(), name='lookup_case_tags'),
    ('', include('codereview.urls')),
)

handler500 = lambda request: debug.technical_500_response(
    request, *sys.exc_info())

import paylogic.measurements

paylogic.measurements.set_timers('paylogic.views')
paylogic.measurements.set_timers('codereview.views')
