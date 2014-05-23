"""Measurement functions to be used when there is a need to monitor some code."""
import statsd
import socket
import types
import re

import importlib

CASE_ID_RE = re.compile('\(Case\s(\d+)\)')


HOSTNAME = socket.getfqdn().replace('.', '_')


def measure_comments_per_user(request, issue):
    """Sends number of published comments per issue and per user"".
       :param request: django request
       :param issue: object codereview issue

    """
    from codereview import models

    number_of_comments = models.Comment.objects.filter(
        patch__patchset__issue=issue, author=request.user.id,
        draft=False).count()
    try:
        case_id = CASE_ID_RE.match(issue.subject).groups()[0]
    except AttributeError:
        return
    gauge = statsd.Gauge(
        '{0}.codereview.number_of_comments.{case_id}'.format(HOSTNAME, case_id=case_id))
    gauge.send('{author_name}'.format(
        author_name=request.user.username.replace('.', '_')), number_of_comments)


timer = statsd.Timer('{0}.codereview'.format(HOSTNAME))


def set_timers(obj):
    """Set timers to every callable of the given obj."""
    if isinstance(obj, type('')):
        return set_timers(importlib.import_module(obj))
    for attr_name in dir(obj):
        if not attr_name.startswith('__'):
            attr = getattr(obj, attr_name)
            if isinstance(attr, types.FunctionType):
                setattr(obj, attr_name, timer.decorate(attr))
            elif isinstance(attr, type):
                set_timers(attr)
