#!/usr/bin/env python
import os
import sys

import gae2django
# Use gae2django.install(server_software='Dev') to enable a link to the
# admin frontend at the top of each page. By default this link is hidden.
gae2django.install(server_software='Django')

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    # apply patches
    if '--settings=paylogic.settings_build' in sys.argv:
        settings = 'paylogic.settings_build'
    else:
        settings = 'paylogic.settings_paylogic'
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings)
    import paylogic.patches  # NOQA

    execute_from_command_line(sys.argv)
