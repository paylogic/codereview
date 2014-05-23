"""Django settings for paylogic customized rietveld codereview."""

from paylogic.settings_base import *


try:
    from paylogic.settings_local import *
except ImportError:
    pass
