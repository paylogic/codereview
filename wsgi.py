import os
import sys

# os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(
    os.path.abspath(
        os.path.dirname(__file__)
    ))
sys.path.append(os.path.dirname(__file__))

import gae2django
# Use gae2django.install(server_software='Dev') to enable a link to the
# admin frontend at the top of each page. By default this link is hidden.
gae2django.install(server_software='Django')

os.environ['DJANGO_SETTINGS_MODULE'] = 'paylogic.settings_paylogic'

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
