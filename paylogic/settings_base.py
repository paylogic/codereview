# Django settings for django_gae2django project.

# NOTE: Keep the settings.py in examples directories in sync with this one!
# from settings import *

import re
import os
import statsd
ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Admin', 'admin@example.com'),
)

EMAIL_HOST = 'localhost'

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Amsterdam'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True


# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(ROOT, 'static')

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOT, 'static'),
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'some-secret'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    #  'django.template.loaders.eggs.load_template_source',
)


MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'gae2django.middleware.FixRequestUserMiddleware',
    # Keep in mind, that CSRF protection is DISABLED!
    'rietveld_helper.middleware.DisableCSRFMiddleware',
    'rietveld_helper.middleware.AddUserToRequestMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',    # required by admin panel
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.static',
)

ROOT_URLCONF = 'paylogic.urls'

TEMPLATE_DIRS = (
    os.path.join(ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django_openid_auth',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'jquery',
    'django_select2',
    'gae2django',
    'rietveld_helper',

    'paylogic',
    'codereview',
)

OPENID_CREATE_USERS = True
OPENID_SSO_SERVER_URL = 'https://google.com/accounts/o8/site-xrds?hd=paylogic.eu'
OPENID_USE_AS_ADMIN_LOGIN = False

LOGIN_URL = '/openid/login/'
LOGIN_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_openid_auth.auth.OpenIDBackend',
)

# Set your DSN value
RAVEN_CONFIG = {
    'dsn': 'https://yor-dsn',
}

# Add raven to the list of installed apps
INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
)

INTERNAL_IPS = ('127.0.0.1',)

AUTH_PROFILE_MODULE = 'codereview.Account'
LOGIN_REDIRECT_URL = '/'

# This won't work with gae2django.
RIETVELD_INCOMING_MAIL_ADDRESS = None

RIETVELD_REVISION = ''

UPLOAD_PY_SOURCE = os.path.join(ROOT, 'upload.py')

VCS = {
    'hg': {
        'base_dir': '/var/codereview/hg/',
        'regex': re.compile('^((ssh://code\.(?:example\.com)/)?/var/codereview/hg/|hg\+)(.+)$'),
        'supports_direct_export': True,
        'default_branch': 'default',
    },
    'bzr': {
        'base_dir': '/var/codereview/bzr/',
        'regex': re.compile('^((ssh://code\.(?:example\.com)/)?/var/codereview/bzr/|bzr\+)(.+)$'),
        'supports_direct_export': True,
        'default_branch': 'trunk',
    },
    'git': {
        'base_dir': '/var/codereview/git/',
        'regex': re.compile('^((ssh://code\.(?:example\.com)/)?/var/codereview/git/|git\+)(.+)$'),
        'supports_direct_export': False,
        'default_branch': 'master',
    }
}

FEATURE_BRANCH_DEFAULT_PREFIX = 'hg+/var/codereview/hg/users/'
ORIGINAL_BRANCH_DEFAULT_PREFIX = 'hg+/var/hg/codereview/example.com#'

TEMP_FOLDER = '/var/tmp/codereview/'

FOGBUGZ_URL = 'https://fogbugz.example.com'
FOGBUGZ_TOKEN = 'fogbugz-token'

# Override this token in your settings_local.py file in order to
# API functions
API_TOKEN = 'some-token'

FOGBUGZ_MERGEKEEPER_USER_ID = 999
FOGBUGZ_APPROVED_REVISION_FIELD_ID = "plugin_customfields_at_fogcreek_com_approvedxrevision"
FOGBUGZ_TARGET_BRANCH_FIELD_ID = "plugin_customfields_at_fogcreek_com_targetxbranch"
FOGBUGZ_ORIGINAL_BRANCH_FIELD_ID = "plugin_customfields_at_fogcreek_com_originalxbranch"
FOGBUGZ_FEATURE_BRANCH_FIELD_ID = "plugin_customfields_at_fogcreek_com_featurexbranch"
FOGBUGZ_CI_PROJECT_FIELD_ID = "cixproject"

CODEREVIEW_IGNORED_FILES = ['.hg_archival.txt']

CODEREVIEW_MAX_FILE_SIZE = 1024 * 1024

CODEREVIEW_VALIDATORS = [
]

CODEREVIEW_TARGET_BRANCH_CHOICES_GETTER = lambda ci_project, original_branch, branches: []

AUTO_RENDER_SELECT2_STATICS = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
    },
    'loggers': {
    }
}

DEFAULT_MAIL_CC = 'fogbugz@example.com'

statsd.Connection.set_defaults(host='localhost', port=8125)

try:
    from paylogic.settings_local import *
except ImportError:
    pass
