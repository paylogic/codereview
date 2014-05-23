DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3'.
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.db',       # Or path to database file if using sqlite3.
    }
}

RAVEN_CONFIG = {}
