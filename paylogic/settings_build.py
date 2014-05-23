import os.path
from settings_paylogic import *


STATIC_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static_build')
